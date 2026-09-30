# Europe PMC literature MCP server

A narrow, **read-only** [MCP](https://modelcontextprotocol.io) server that lets Claude search
[Europe PMC](https://europepmc.org) and inspect individual publication records. Built with the
official MCP Python SDK, **pinned to `mcp[cli]==2.2.0`** (`MCPServer` + `@mcp.tool()`), plus a Claude Code project skill for
evidence-careful literature answers, aimed at T-cell / cell-therapy research questions.

> **Verification status (see [`VERIFICATION.md`](VERIFICATION.md)):** unit tests, in-memory MCP tests,
> stdio launch and live Europe PMC checks **pass** on Windows with `mcp==2.2.0`. The Claude Code connection
> and project skill **pass**. The demonstration has been run and scored, and all its citations were verified
> against live Europe PMC (0 problems). A comparison run without the skill is in
> `examples/skill-comparison.md`. The MCP Inspector walkthrough passed (screenshots in `verification/inspector/`).
> Nothing is pending.

**Division of labour:** the server retrieves and structures Europe PMC data; Claude does the
interpretation. The tools never summarise findings, rank evidence or draw conclusions, so an
incorrect claim can be traced either to the source record or to the model's reading of it.

## Tools

| Tool | Input | Output |
|---|---|---|
| `search_literature` | `query` (question or Europe PMC search syntax, ≤500 chars); `max_results` (1–20, default 5) | Total hits plus one record per paper: title, authors, journal, publication date, article types, review/preprint flags from metadata, abstract (truncated past 1,500 chars), `europepmc_id`, PMID, PMCID, DOI, and Europe PMC / DOI / PubMed / full-text links. Also a link to the same search on europepmc.org. |
| `get_article` | `identifier`: `europepmc_id` (e.g. `MED:12345678`, `PPR:PPR123456`), PMID, PMCID, DOI, or a europepmc.org article URL | One record with the **full** abstract, `full_text_retrieved: false`, and an explicit `full_text_note` saying what can't be verified from an abstract. `abstract_available: false` when Europe PMC holds no abstract. Lists other records matching the same identifier (e.g. a preprint and its journal version). |

Both tools are annotated `read_only_hint=True` and declare Pydantic return types, so the SDK
publishes an output schema and returns structured content.

### Safeguards

- **Timeout:** 15 s per Europe PMC request.
- **Small result limit:** default 5, hard maximum 20, enforced by the JSON schema *and* in the API module.
- **Input validation:** empty or over-long queries and unrecognised identifiers are rejected before any request is sent. Identifiers are converted to strict Europe PMC field queries (`EXT_ID:… AND SRC:MED`, `PMCID:…`, `DOI:"…"`), so free text can't be injected through `get_article`.
- **Useful errors:** timeouts, connection failures, HTTP 429/4xx/5xx and non-JSON responses become MCP tool errors (`is_error: true`) with a message the model can act on. "No results" is *not* an error; it returns an empty list with a note that absence of results isn't evidence of absence.
- **Traceability:** every successful record carries `europepmc_id` plus whichever of PMID/PMCID/DOI exist, and links.
- **Metadata, not judgement:** `review_in_metadata` and `preprint` only reflect Europe PMC's publication-type fields. The schema says so, and says that `review_in_metadata: false` does not prove a paper is primary research.

## Repository layout

```
server.py                       MCP server: two tools, stdio entry point
europepmc.py                    Europe PMC REST client, validation, parsing, output models
tests/
  conftest.py                   Mock Europe PMC via httpx.MockTransport (no network, no MCP import)
  test_europepmc.py             Unit tests: validation, identifiers, parsing, HTTP client on fixtures
  test_mcp_inmemory.py          MCP integration: SDK in-memory Client -> server (needs mcp==2.2.0)
  fixtures/*.json               SYNTHETIC Europe PMC responses (fake PMIDs 990000xx, DOI prefix 10.5555)
scripts/verify_local.py         Runs all automated checks and writes verification/latest.md
scripts/live_check.py           Quick manual look at live results through the server
scripts/check_citations.py      Checks a demo answer's PMIDs, labels and quotes against live abstracts
VERIFICATION.md                 What has been verified, with evidence; everything else PENDING
examples/questions.md           Example questions, including the main demonstration
examples/demo-evaluation.md     How Claude used the tools in the recorded demo run
examples/demo-citations.json    Citations and quotes from that run, input to check_citations.py
examples/skill-comparison.md    Same question with vs without the skill, side by side
examples/demo-citations-noskill.json  Citations from the run without the skill
.claude/skills/literature-evidence/SKILL.md   Project skill for Claude Code
pyproject.toml
```

## Setup (your machine)

Requires Python ≥3.10 and [uv](https://docs.astral.sh/uv/). Node.js is needed only for the MCP Inspector.
The MCP SDK source is **not** included in this repository; `uv sync` installs the pinned release.

```powershell
cd C:\path\to\mcp-server
uv sync                     # mcp[cli]==2.2.0, httpx, pydantic + dev group (pytest, anyio); writes uv.lock
uv run python -c "import importlib.metadata as m; print(m.version('mcp'))"    # expect 2.2.0
```

Commit the generated `uv.lock` so the full dependency set is pinned too (it could not be generated
in the build environment because PyPI was unreachable there).

## 1. Run all automated checks

```powershell
uv run python scripts/verify_local.py            # includes live Europe PMC calls
uv run python scripts/verify_local.py --offline  # no network
```

It runs, in order: environment/pin check → unit tests → in-memory MCP tests → stdio launch →
live Europe PMC API → live Europe PMC through the MCP server, and writes
`verification/results-<timestamp>.md` plus `verification/latest.md`. Copy the summary into
[`VERIFICATION.md`](VERIFICATION.md) and change those rows from PENDING.

### Individual commands

```powershell
uv run pytest tests/test_europepmc.py            # unit tests, offline fixtures, no MCP SDK needed
uv run pytest tests/test_mcp_inmemory.py         # in-memory MCP tests (skipped if mcp!=2.2.0)
$env:REQUIRE_MCP="1"; uv run pytest tests/test_mcp_inmemory.py; Remove-Item Env:REQUIRE_MCP   # fail instead of skip
uv run python scripts/live_check.py              # live Europe PMC through the server, printed
```

**Unit tests** (`test_europepmc.py`) exercise validation, identifier → query mapping, HTML stripping,
record parsing, and the HTTP client's normal / no-results / failure paths (HTTP 503, 429, 400,
invalid JSON, `errMsg`, timeout, connection error) against synthetic fixtures via `httpx.MockTransport`.

**In-memory MCP tests** (`test_mcp_inmemory.py`) follow the SDK testing guide: `Client(server.mcp,
raise_exceptions=True)` talks to the server object directly, with Europe PMC mocked. They check the
tool list and read-only annotations, the schema's result limit, and for each tool normal results,
no results and API failure as `is_error: true` tool errors. They are skipped unless `mcp==2.2.0` is
installed, so a skip there means **not verified**, not passed.

## 2. MCP Inspector (manual)

```powershell
uv run mcp dev server.py
```

In the Inspector: **Connect** → **Tools** → **List Tools**, then call:

- `search_literature` with `query = "TCR clonotype" AND persistence AND "adoptive" AND NOT PUB_TYPE:review`, `max_results = 5`
- `get_article` with one of the returned `europepmc_id` values
- `get_article` with `identifier = hello` (should return a readable tool error)
- `search_literature` with `max_results = 50` (should be rejected by the schema)

Tick the Inspector checklist in `VERIFICATION.md`.

## 3. Connect to Claude Code (manual)

Everything after `--` is the launch command, and paths must be **absolute** (Claude Code starts
the server from its own working directory). Using the project environment from `uv sync`, so the
pinned SDK is what runs:

```powershell
claude mcp add europepmc -- uv run --directory C:/path/to/mcp-server mcp run C:/path/to/mcp-server/server.py
```

The project-free form from the SDK's "Connect to a real host" guide also works, with the pin and `httpx` added:

```bash
claude mcp add europepmc -- uv run --with "mcp[cli]==2.2.0" --with httpx mcp run /ABSOLUTE/PATH/TO/server.py
```

This registers the server at the default **local** scope, stored in your own Claude Code settings, not in the repo.
Don't register it at project scope (`.mcp.json`) as well, or Claude Code reports "Conflicting scopes"; remove one with
`claude mcp remove europepmc -s project` (or `-s local`).

Then start `claude` in this folder and run `/mcp`: `europepmc` should show as connected with
`search_literature` and `get_article`. If it doesn't, run the launch command by hand; it should sit
silently waiting on stdin (Ctrl-C to stop). A traceback there is the real error. If Claude Code
can't find `uv`, use its absolute path (`where uv` on Windows).

## 4. The project skill

`.claude/skills/literature-evidence/SKILL.md` is loaded by Claude Code automatically when you work
in this folder. (If you received it as `project-skill/literature-evidence/SKILL.md`, move that folder
into `.claude/skills/` first: `mkdir .claude\skills` then move `project-skill\literature-evidence` there.) It tells Claude to:

1. search, revising the query if needed;
2. inspect each relied-on record with `get_article` instead of trusting titles or truncated abstracts;
3. separate primary studies, reviews and preprints;
4. label findings as association, causal/mechanistic, or not determinable from the abstract;
5. cite only identifiers that appeared in tool output;
6. mark uncertainty, since full text is never retrieved.

To confirm it's picked up, ask Claude Code "which skills are available in this project?". The server and the skill are
separate, demonstrable pieces: the server provides traceable data, the skill sets the working method.

## 5. Demonstration

In Claude Code, ask:

> Find primary studies on TCR clonotype persistence after adoptive T-cell therapy. Separate observed associations from evidence of causation, and give identifiers for the papers used.

Record the result in [`examples/demo-evaluation.md`](examples/demo-evaluation.md):

- **Tool selection:** did Claude call `search_literature`, exclude reviews, and call `get_article` on the papers it relied on?
- **Citation accuracy:** does every cited identifier appear in the tool output, and does the abstract support the claim attached to it?
- **Admitting limits:** does Claude say when an abstract can't support a claim (effect sizes, mechanism, design details)?

Then check the citations in the answer against live Europe PMC abstracts:

```powershell
uv run python scripts/check_citations.py      # reads examples/demo-citations.json
```

Running the question once with the skill and once without it shows what the skill contributes.

More prompts are in [`examples/questions.md`](examples/questions.md).

## Design notes

- **Why `MCPServer` and the 2.2.0 pin:** the current SDK docs (v2.x) use `from mcp.server import MCPServer`; older tutorials use v1's `FastMCP`. `pip install mcp` now installs v2, and this project pins the exact release (`mcp[cli]==2.2.0`) so the code, tests and docs refer to one version.
- **Why search-endpoint lookups for `get_article`:** one well-documented endpoint (`/search` with `resultType=core`) serves both tools, so parsing and error handling are shared.
- **Why truncate abstracts in search:** it keeps a 20-result response small, and it pushes the model to call `get_article` before relying on a paper.
- **Why no full text (yet):** abstract-only records keep version 1 small and honest. Every `get_article` response states that full text was not retrieved. A later version could add open-access full text via `/{PMCID}/fullTextXML`.
- **Europe PMC terms:** it's a free public API with no key. Please keep request volumes modest.
