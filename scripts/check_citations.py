"""Check a demo answer's citations against live Europe PMC records.

    uv run python scripts/check_citations.py                                # uses examples/demo-citations.json
    uv run python scripts/check_citations.py path/to/citations.json

For every cited paper it fetches the record with get_article (the same code the MCP tool uses)
and checks:
  * the identifier resolves to a Europe PMC record
  * the PMCID in the answer matches the record (if one was given)
  * the label in the answer (primary / review / preprint) agrees with the record's metadata
  * every quote attributed to the paper appears in its abstract (whitespace, case and
    punctuation normalised; nothing else)
  * optional fields, when given: DOI, first author's surname and publication year

A quote that is not in the abstract is reported as NOT FOUND. That means it can't be verified
from the abstract: it could be misquoted, paraphrased, or from the full text.

Results are written to verification/citations-<timestamp>.md and verification/citations-latest.md.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

import anyio

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from europepmc import ArticleNotFoundError, EuropePMCClient, EuropePMCError  # noqa: E402

DEFAULT_FILE = ROOT / "examples" / "demo-citations.json"


def normalise(text: str) -> str:
    """Lower-case, fold unicode, turn every run of non-alphanumerics into one space."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    return " ".join(re.sub(r"[^0-9a-z%<>.]+", " ", text).split())


def quote_in_abstract(quote: str, abstract: str | None) -> bool:
    return bool(abstract) and normalise(quote) in normalise(abstract)


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()


def first_author_matches(surname: str, author_string: str | None) -> bool:
    return bool(author_string) and _fold(author_string).lstrip().startswith(_fold(surname).strip())


def year_matches(year: str | int, *record_dates: str | None) -> bool:
    return any(d and str(d)[:4] == str(year) for d in record_dates)


def extra_field_problems(cite: dict, art) -> list[str]:
    """Check the optional doi / first_author / year fields against the record."""
    out = []
    if cite.get("doi") and (art.doi or "").lower() != cite["doi"].lower():
        out.append(f"DOI {cite['doi']} != record {art.doi}")
    if cite.get("first_author") and not first_author_matches(cite["first_author"], art.authors):
        out.append(f"first author {cite['first_author']!r} != record {(art.authors or '')[:40]!r}")
    if cite.get("year") and not year_matches(cite["year"], art.publication_year, art.publication_date):
        out.append(f"year {cite['year']} != record {art.publication_year} / {art.publication_date}")
    return out


async def check(spec: dict) -> tuple[list[str], int]:
    client = EuropePMCClient()
    lines: list[str] = []
    problems = 0

    lines += ["## Cited papers", "",
              "| Identifier | Resolves | PMCID matches | DOI / author / year | Label in answer | Metadata says | Quotes found |",
              "|---|---|---|---|---|---|---|"]
    details: list[str] = []
    for cite in spec.get("citations", []):
        ident = cite["identifier"]
        try:
            result = await client.get_article(ident)
        except (ArticleNotFoundError, EuropePMCError) as exc:
            problems += 1
            lines.append(f"| {ident} | NO ({exc}) | | | {cite.get('label', '')} | | |")
            continue
        art = result.article
        meta_label = "preprint" if art.preprint else ("review" if art.review_in_metadata else "not review")
        label = cite.get("label", "")
        label_ok = (label == "primary" and meta_label == "not review") or label == meta_label
        pmcid_ok = "n/a" if not cite.get("pmcid") else ("yes" if cite["pmcid"] == art.pmcid else f"NO (record: {art.pmcid})")
        quotes = cite.get("quotes", [])
        found = [q for q in quotes if quote_in_abstract(q, art.abstract)]
        missing = [q for q in quotes if q not in found]
        extra = extra_field_problems(cite, art)
        checked = [k for k in ("doi", "first_author", "year") if cite.get(k)]
        extra_cell = "n/a" if not checked else ("yes" if not extra else "NO: " + "; ".join(extra))
        problems += len(missing) + (0 if label_ok else 1) + (1 if pmcid_ok.startswith("NO") else 0) + len(extra)
        lines.append(
            f"| {ident} | yes | {pmcid_ok} | {extra_cell} | {label} | {meta_label} ({', '.join(art.article_types) or 'no types'})"
            f"{'' if label_ok else ' **MISMATCH**'} | {len(found)}/{len(quotes)} |"
        )
        details.append(f"### {ident}: {art.title}")
        details.append(f"{art.journal or ''} {art.publication_date or ''} · {art.links.europepmc}")
        for q in found:
            details.append(f"- FOUND: \"{q}\"")
        for q in missing:
            details.append(f"- **NOT FOUND in abstract**: \"{q}\"")
        details.append("")

    if spec.get("mentioned_only"):
        lines += ["", "## Mentioned but not relied on", "", "| Identifier | Resolves | Title |", "|---|---|---|"]
        for ident in spec["mentioned_only"]:
            try:
                art = (await client.get_article(ident)).article
                lines.append(f"| {ident} | yes | {art.title} |")
            except (ArticleNotFoundError, EuropePMCError) as exc:
                problems += 1
                lines.append(f"| {ident} | NO ({exc}) | |")

    return lines + ["", "## Quote details", "", *details], problems


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    spec = json.loads(path.read_text(encoding="utf-8"))
    body, problems = anyio.run(check, spec)
    now = dt.datetime.now().astimezone()
    header = [
        "# Citation check",
        "",
        f"- Run at: {now.isoformat(timespec='seconds')}",
        f"- Citations file: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}",
        f"- Source answer: {spec.get('source', 'not given')}",
        f"- Problems found: **{problems}**",
        "",
    ]
    text = "\n".join(header + body)
    out = ROOT / "verification"
    out.mkdir(exist_ok=True)
    (out / f"citations-{now.strftime('%Y%m%d-%H%M%S')}.md").write_text(text, encoding="utf-8")
    (out / "citations-latest.md").write_text(text, encoding="utf-8")
    print(text)
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
