"""Live check against the real Europe PMC API through the MCP server (in memory).

    uv run python scripts/live_check.py
    uv run python scripts/live_check.py "CAR-T persistence" 3

Prints what the model would receive: identifiers, types, dates, and the full-text note.
Not part of the default test suite because it needs network access.
"""

from __future__ import annotations

import sys
from pathlib import Path

import anyio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import Client  # noqa: E402
from server import mcp  # noqa: E402

DEFAULT_QUERY = '"TCR" AND (clonotype OR "clonal repertoire") AND persistence AND "adoptive" AND NOT PUB_TYPE:review'


async def main(query: str, n: int) -> int:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("Tools:", ", ".join(t.name for t in tools.tools))

        search = await client.call_tool("search_literature", {"query": query, "max_results": n})
        if search.is_error:
            print("search_literature ERROR:", search.content[0].text)
            return 1
        data = search.structured_content
        print(f"\nQuery: {data['query']}\nTotal hits: {data['total_hits']}  returned: {data['returned']}")
        for rec in data["results"]:
            flags = [f for f, on in (("review", rec["review_in_metadata"]), ("preprint", rec["preprint"])) if on]
            print(
                f"- {rec['europepmc_id']:<16} PMID={rec['pmid']} DOI={rec['doi']} {rec['publication_date']} "
                f"{rec['article_types']} {flags}\n    {rec['title']}"
            )
        if not data["results"]:
            print(data["note"])
            return 0

        first = data["results"][0]["europepmc_id"]
        article = await client.call_tool("get_article", {"identifier": first})
        if article.is_error:
            print("get_article ERROR:", article.content[0].text)
            return 1
        a = article.structured_content
        print(f"\nget_article({first}): abstract_available={a['abstract_available']} "
              f"full_text_retrieved={a['full_text_retrieved']}")
        print("Note:", a["full_text_note"])
        print("Links:", a["article"]["links"]["europepmc"], a["article"]["links"]["doi"])
    return 0


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    raise SystemExit(anyio.run(main, q, k))
