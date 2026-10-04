"""Local verification: run every automated check on YOUR machine and record the results.

    uv sync
    uv run python scripts/verify_local.py              # all checks, including live Europe PMC
    uv run python scripts/verify_local.py --offline    # skip the live API checks

Checks
  1. environment        Python, platform, installed package versions; MCP SDK must equal the pin
  2. unit_tests         all offline tests: test_europepmc, test_check_citations, test_manual_checks (no MCP SDK)
  3. mcp_inmemory       tests/test_mcp_inmemory.py via the SDK's in-memory Client (REQUIRE_MCP=1)
  4. mcp_stdio          launch server.py as a subprocess over stdio and list its tools
  5. live_api           real Europe PMC: search + get_article through europepmc.py
  6. live_mcp           real Europe PMC through the MCP server (in-memory Client -> server -> API)

Results are written to verification/results-<timestamp>.md and verification/latest.md.
Copy the outcome into VERIFICATION.md; the Inspector and Claude Code checks are manual.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import os
import platform
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PINNED_MCP_VERSION = "2.2.0"
LIVE_QUERY = (
    '(TCR OR "T-cell receptor") AND (clonotype OR "clonal tracking" OR repertoire) AND persistence '
    'AND ("adoptive cell" OR "adoptive T-cell" OR "CAR-T" OR TIL) AND NOT PUB_TYPE:review'
)


@dataclass
class Check:
    name: str
    status: str = "NOT RUN"  # PASS | FAIL | SKIPPED | NOT RUN
    details: list[str] = field(default_factory=list)

    def ok(self, *lines: str) -> None:
        self.status = "PASS"
        self.details += lines

    def fail(self, *lines: str) -> None:
        self.status = "FAIL"
        self.details += lines

    def skip(self, *lines: str) -> None:
        self.status = "SKIPPED"
        self.details += lines


def version(pkg: str) -> str | None:
    try:
        return importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return None


OFFLINE_TESTS = ("tests/test_europepmc.py", "tests/test_check_citations.py", "tests/test_manual_checks.py")


def run_pytest(*paths: str, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    env = {**os.environ, **(extra_env or {})}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    out = (proc.stdout + proc.stderr).strip().splitlines()
    return proc.returncode, "\n".join(out[-15:])


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #


def check_environment(c: Check) -> bool:
    versions = {p: version(p) for p in ("mcp", "httpx", "pydantic", "anyio", "pytest", "typer")}
    c.details.append(f"Python {platform.python_version()} on {platform.platform()}")
    c.details.append("Installed: " + ", ".join(f"{k}={v}" for k, v in versions.items()))
    if versions["mcp"] != PINNED_MCP_VERSION:
        c.fail(f"MCP SDK must be {PINNED_MCP_VERSION} (pinned in pyproject.toml); found {versions['mcp']}. Run `uv sync`.")
        return False
    missing = [k for k, v in versions.items() if v is None]
    if missing:
        c.fail(f"Missing packages: {', '.join(missing)}. Run `uv sync`.")
        return False
    c.ok(f"MCP SDK matches pin ({PINNED_MCP_VERSION}).")
    return True


def check_unit_tests(c: Check) -> None:
    code, tail = run_pytest(*OFFLINE_TESTS)
    (c.ok if code == 0 else c.fail)(tail)


def check_mcp_inmemory(c: Check) -> None:
    code, tail = run_pytest("tests/test_mcp_inmemory.py", extra_env={"REQUIRE_MCP": "1"})
    (c.ok if code == 0 else c.fail)(tail)


async def check_mcp_stdio(c: Check) -> None:
    from mcp import Client, StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=str(ROOT))
    async with Client(params) as client:
        tools = sorted(t.name for t in (await client.list_tools()).tools)
    if tools == ["get_article", "search_literature"]:
        c.ok(f"stdio launch OK; tools listed: {tools}")
    else:
        c.fail(f"Unexpected tool list over stdio: {tools}")


async def check_live_api(c: Check) -> str | None:
    from europepmc import EuropePMCClient

    api = EuropePMCClient()
    search = await api.search(LIVE_QUERY, 5)
    c.details.append(f"Query: {LIVE_QUERY}")
    c.details.append(f"total_hits={search.total_hits} returned={search.returned}")
    if not search.results:
        c.fail("Live search returned no records; cannot check identifiers or get_article.")
        return None
    for r in search.results:
        c.details.append(
            f"- {r.europepmc_id} | PMID {r.pmid} | DOI {r.doi} | {r.publication_date} | "
            f"types={r.article_types} | review={r.review_in_metadata} | {(r.title or '')[:90]}"
        )
    missing_ids = [r.europepmc_id for r in search.results if not (r.pmid or r.pmcid or r.doi)]
    if missing_ids:
        c.details.append(f"Note: records with no PMID/PMCID/DOI (europepmc_id only): {missing_ids}")

    first = search.results[0].europepmc_id
    article = await api.get_article(first)
    c.details.append(
        f"get_article({first}): abstract_available={article.abstract_available} "
        f"full_text_retrieved={article.full_text_retrieved} other_matches={article.other_matching_records}"
    )
    if article.full_text_retrieved is not False or "NOT retrieved" not in article.full_text_note:
        c.fail("get_article did not carry the explicit full-text note.")
        return None
    if article.article.europepmc_id != first:
        c.fail(f"get_article returned {article.article.europepmc_id}, expected {first}.")
        return None
    c.ok("Live search and get_article returned identifiers, links and the full-text note.")
    return first


async def check_live_mcp(c: Check, identifier: str | None) -> None:
    from mcp import Client

    from server import mcp

    async with Client(mcp) as client:
        s = await client.call_tool("search_literature", {"query": LIVE_QUERY, "max_results": 3})
        if s.is_error:
            c.fail("search_literature returned a tool error: " + " ".join(getattr(x, "text", "") for x in s.content))
            return
        n = s.structured_content["returned"]
        c.details.append(f"search_literature via MCP: returned={n}, total_hits={s.structured_content['total_hits']}")
        if identifier:
            a = await client.call_tool("get_article", {"identifier": identifier})
            if a.is_error:
                c.fail("get_article returned a tool error: " + " ".join(getattr(x, "text", "") for x in a.content))
                return
            c.details.append(f"get_article via MCP: {a.structured_content['article']['europepmc_id']}, "
                             f"full_text_retrieved={a.structured_content['full_text_retrieved']}")
        bad = await client.call_tool("get_article", {"identifier": "not an identifier"})
        c.details.append(f"get_article('not an identifier') -> is_error={bad.is_error}")
        if not bad.is_error:
            c.fail("Invalid identifier was not reported as a tool error.")
            return
    c.ok("Live Europe PMC reachable through the MCP server.")


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


def write_report(checks: list[Check], offline: bool) -> Path:
    now = dt.datetime.now().astimezone()
    lines = [
        "# Local verification results",
        "",
        f"- Run at: {now.isoformat(timespec='seconds')}",
        f"- Platform: {platform.system()} {platform.release()}",  # host name deliberately not recorded
        f"- Mode: {'offline (live checks skipped)' if offline else 'full, including live Europe PMC'}",
        f"- Pinned MCP SDK: {PINNED_MCP_VERSION}",
        "",
        "| Check | Status |",
        "|---|---|",
        *[f"| {c.name} | {c.status} |" for c in checks],
        "",
    ]
    for c in checks:
        lines += [f"## {c.name}: {c.status}", "", "```", *(c.details or ["(no output)"]), "```", ""]
    out_dir = ROOT / "verification"
    out_dir.mkdir(exist_ok=True)
    text = "\n".join(lines)
    stamped = out_dir / f"results-{now.strftime('%Y%m%d-%H%M%S')}.md"
    stamped.write_text(text, encoding="utf-8")
    (out_dir / "latest.md").write_text(text, encoding="utf-8")
    return stamped


def main() -> int:
    import anyio

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="skip live Europe PMC checks")
    args = parser.parse_args()

    checks = {n: Check(n) for n in ("environment", "unit_tests", "mcp_inmemory", "mcp_stdio", "live_api", "live_mcp")}

    def guarded(name, fn, *a):
        try:
            return fn(*a)
        except Exception as exc:  # record, never hide
            checks[name].fail(f"{type(exc).__name__}: {exc}", traceback.format_exc(limit=3))
            return None

    def guarded_async(name, fn, *a):
        try:
            return anyio.run(fn, *a)
        except Exception as exc:
            checks[name].fail(f"{type(exc).__name__}: {exc}", traceback.format_exc(limit=3))
            return None

    env_ok = guarded("environment", check_environment, checks["environment"])
    guarded("unit_tests", check_unit_tests, checks["unit_tests"])

    if env_ok:
        guarded("mcp_inmemory", check_mcp_inmemory, checks["mcp_inmemory"])
        guarded_async("mcp_stdio", check_mcp_stdio, checks["mcp_stdio"])
    else:
        for n in ("mcp_inmemory", "mcp_stdio", "live_mcp"):
            checks[n].skip("Skipped: pinned MCP SDK not installed (see environment).")

    if args.offline:
        checks["live_api"].skip("Skipped: --offline.")
        if checks["live_mcp"].status == "NOT RUN":
            checks["live_mcp"].skip("Skipped: --offline.")
    else:
        ident = guarded_async("live_api", check_live_api, checks["live_api"])
        if env_ok:
            guarded_async("live_mcp", check_live_mcp, checks["live_mcp"], ident)

    report = write_report(list(checks.values()), args.offline)
    width = max(len(n) for n in checks)
    print()
    for c in checks.values():
        print(f"{c.name:<{width}}  {c.status}")
    print(f"\nFull report: {report.relative_to(ROOT)}  (also verification/latest.md)")
    return 0 if all(c.status in ("PASS", "SKIPPED") for c in checks.values()) and env_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
