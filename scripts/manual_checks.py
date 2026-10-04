"""Print the evidence needed to settle the open manual checks in examples/demo-evaluation.md.

    uv run python scripts/manual_checks.py                       # uses examples/manual-checks.json
    uv run python scripts/manual_checks.py path/to/checks.json

For each check it fetches the record (the same query get_article uses) and writes out:
  * title, article types, and the FULL abstract
  * whether each listed term appears in the abstract (same normalisation as check_citations.py)
  * funding agencies from Europe PMC's grant metadata, if any

It does not decide anything. A person (or Claude) reads the output and records the verdict in
examples/demo-evaluation.md. Output: verification/manual-checks-<timestamp>.md and manual-checks-latest.md.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import anyio

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from check_citations import quote_in_abstract  # noqa: E402
from europepmc import EuropePMCClient, EuropePMCError, identifier_to_query, parse_record  # noqa: E402

DEFAULT_FILE = ROOT / "examples" / "manual-checks.json"


def funders(raw: dict) -> list[str]:
    grants = (raw.get("grantsList") or {}).get("grant") or []
    return sorted({g.get("agency", "").strip() for g in grants if g.get("agency")})


def term_lines(terms: list[str], abstract: str | None) -> list[str]:
    return [f"- {'FOUND' if quote_in_abstract(t, abstract) else 'not found'}: \"{t}\"" for t in terms]


async def run(spec: dict) -> list[str]:
    client = EuropePMCClient()
    out: list[str] = []
    for chk in spec["checks"]:
        ident = chk["identifier"]
        out += [f"## {chk['id']}: PMID {ident}", "", f"**Claim in the answer:** {chk['claim']}", "",
                f"**Question to settle:** {chk['question']}", ""]
        try:
            data = await client._search_raw(identifier_to_query(ident), 5)
            raws = client._records(data)
        except EuropePMCError as exc:
            out += [f"Could not fetch: {exc}", ""]
            continue
        if not raws:
            out += ["No record found.", ""]
            continue
        raw = raws[0]
        rec = parse_record(raw)
        out += [f"**Title:** {rec.title}", "",
                f"**Types:** {', '.join(rec.article_types) or 'none'} · {rec.journal or ''} {rec.publication_date or ''}",
                f"**Funding (grant metadata):** {', '.join(funders(raw)) or 'none listed'}", "",
                "**Terms in abstract:**", *term_lines(chk.get("terms", []), rec.abstract), "",
                "**Abstract:**", "", f"> {rec.abstract or '(no abstract)'}", "",
                "**Verdict:** _to be filled in by the reader_", ""]
    return out


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    spec = json.loads(path.read_text(encoding="utf-8"))
    body = anyio.run(run, spec)
    now = dt.datetime.now().astimezone()
    text = "\n".join([f"# Manual checks", "", f"- Run at: {now.isoformat(timespec='seconds')}",
                      f"- Checks file: {path.name}", "", *body])
    out = ROOT / "verification"
    out.mkdir(exist_ok=True)
    (out / f"manual-checks-{now.strftime('%Y%m%d-%H%M%S')}.md").write_text(text, encoding="utf-8")
    (out / "manual-checks-latest.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
