"""Europe PMC literature MCP server (read-only).

Two tools:
  * search_literature: find candidate papers and return their source records.
  * get_article: fetch one record's metadata and full abstract.

The server retrieves and structures Europe PMC data. It deliberately does not
summarise findings or judge evidence: the model does the interpretation, so any
incorrect claim can be traced either to the source record or to the model.

Requires the pinned SDK: mcp[cli]==2.2.0 (see pyproject.toml).
Inspector:        uv run mcp dev server.py
Claude Code:      claude mcp add europepmc -- uv run --directory /ABS/PROJECT mcp run /ABS/PROJECT/server.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from europepmc import (
    DEFAULT_MAX_RESULTS,
    MAX_QUERY_LENGTH,
    MAX_RESULTS_LIMIT,
    ArticleNotFoundError,
    ArticleResult,
    EuropePMCClient,
    EuropePMCError,
    InvalidInputError,
    SearchResult,
)

mcp = MCPServer(
    "Europe PMC Literature",
    instructions=(
        "Read-only access to Europe PMC publication records. Tools return source data only: titles, "
        "abstracts, dates, publication types, identifiers and links. They do not assess evidence. "
        "Cite papers by the identifiers returned, and treat anything not in a returned abstract as unverified."
    ),
)

# Module-level client so tests can swap in one backed by httpx.MockTransport.
client = EuropePMCClient()

_READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True)


@mcp.tool(title="Search Europe PMC", annotations=_READ_ONLY)
async def search_literature(
    query: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_QUERY_LENGTH,
            description=(
                "A question or search terms. Europe PMC syntax is supported, e.g. "
                '"TCR clonotype" AND "adoptive cell transfer", TITLE:persistence, PUB_TYPE:review, '
                "NOT PUB_TYPE:review, (FIRST_PDATE:[2018 TO 2026])."
            ),
        ),
    ],
    max_results: Annotated[
        int,
        Field(ge=1, le=MAX_RESULTS_LIMIT, description=f"Maximum records to return (1-{MAX_RESULTS_LIMIT})."),
    ] = DEFAULT_MAX_RESULTS,
) -> SearchResult:
    """Search Europe PMC and return matching publication records.

    Each record has title, authors, journal, publication date, publication types (as listed by
    Europe PMC), abstract (truncated if long), and identifiers: europepmc_id, PMID, PMCID, DOI,
    plus source links. Results are in Europe PMC relevance order and are NOT filtered for
    quality or study design. Use get_article for a record's full abstract.
    """
    try:
        return await client.search(query, max_results)
    except (InvalidInputError, EuropePMCError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(title="Get one Europe PMC article", annotations=_READ_ONLY)
async def get_article(
    identifier: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description=(
                "Europe PMC identifier: the europepmc_id from search_literature (e.g. MED:12345678, "
                "PPR:PPR123456), a PMID, a PMCID (PMC1234567), or a DOI."
            ),
        ),
    ],
) -> ArticleResult:
    """Retrieve one article's metadata and full abstract from Europe PMC.

    Full text is never retrieved in this version: the result always states full_text_retrieved=false
    and explains what that means. If Europe PMC has no abstract, abstract_available is false.
    """
    try:
        return await client.get_article(identifier)
    except (InvalidInputError, ArticleNotFoundError, EuropePMCError) as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()
