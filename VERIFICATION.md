# Verification status

Checks 1–12, 14 and 15 have been run. Check 13 stays **PENDING** until its output is recorded here. Each row gives where and when it ran and the file that holds the evidence; the sections below record the details.

| # | Check | Where it runs | Status | Evidence |
|---|---|---|---|---|
| 1 | Offline tests: `test_europepmc.py` (42), `test_check_citations.py` (5), `test_manual_checks.py` (3) | Cloud workspace, 2026-09-29; re-run 2026-10-02 | **PASS** (42/42 on 09-29; 50/50 on 10-02) | See "Recorded results" below |
| 2 | Environment: pinned `mcp[cli]==2.2.0` installed via `uv sync` | local Windows PC, 2026-09-29 | **PASS** | `verification/results-20260929-171803.md` |
| 3 | In-memory MCP tests (`tests/test_mcp_inmemory.py`) | local Windows PC, 2026-09-29 | **PASS** (9/9) | `verification/results-20260929-171803.md` |
| 4 | Server starts over stdio and lists both tools | local Windows PC, 2026-09-29 | **PASS** | `verification/results-20260929-171803.md` |
| 5 | Live Europe PMC API: search + get_article | local Windows PC, 2026-09-29 | **PASS** | `verification/results-20260929-171803.md` |
| 6 | Live Europe PMC through the MCP server | local Windows PC, 2026-09-29 | **PASS** | `verification/results-20260929-171803.md` |
| 7 | MCP Inspector (`uv run mcp dev server.py`) | local Windows PC, 2026-09-30 | **PASS** (5/5; the limit is enforced by the Inspector from the schema) | `verification/inspector/*.png` |
| 8 | Claude Code: `claude mcp add`, server connected and tools usable | local Windows PC, 2026-09-30 | **PASS** (local scope; `/mcp` shows connected, 2 tools; tools called 11× successfully) | `verification/claude-code-mcp.png`, `examples/transcripts/demo-with-skill.txt` |
| 9 | Project skill picked up by Claude Code | local Windows PC, 2026-09-30 | **PASS** (listed, then loaded automatically) | `examples/transcripts/demo-with-skill.txt` |
| 10 | Demonstration question, scored in `examples/demo-evaluation.md` | local Windows PC, 2026-09-30 | **RUN & SCORED** (answered by Opus 5 after Opus 5.5 safeguard flag) | `examples/transcripts/demo-with-skill.txt` |
| 11 | Demo citations checked against live Europe PMC abstracts (`scripts/check_citations.py`) | local Windows PC, 2026-09-30 | **PASS** (0 problems; 8/8 resolve, 13/13 quotes found) | `verification/citations-20260930-012332.md` |
| 12 | Skill comparison: same question without the skill (`examples/skill-comparison.md`) | local Windows PC, 2026-09-30 | **DONE**; run B citations: 22/22 identifiers correct, 1 misquote | `examples/transcripts/demo-without-skill.txt`, `verification/citations-20260930-123035.md` |
| 13 | All 59 tests on your machine (`uv run pytest`: 50 offline + 9 in-memory MCP) | local Windows PC | **PENDING** | not yet recorded |
| 14 | GitHub Actions CI (`.github/workflows/tests.yml`, Ubuntu + Windows × Python 3.10 + 3.13) | GitHub, 2026-10-04 | **PASS** (4/4 jobs, runs #1 and #2) | [run #2](https://github.com/Olu-repos/europepmc-literature-mcp/actions/runs/37165453508) |
| 15 | Manual checks M1–M5 (`scripts/manual_checks.py`, `examples/manual-checks.json`) | local Windows PC, 2026-10-04 | **DONE** (verdicts below) | `verification/manual-checks-20261004-012123.md` |

Checks 2–6 are automated by `scripts/verify_local.py` (its unit-test step now runs all 50 offline tests); 11 and 12's citations by `scripts/check_citations.py`; 13 by `uv run pytest`; 14 by GitHub Actions; 7–10, 12 and 15's verdicts are manual.

## Recorded results

### 1. Unit tests: cloud workspace, 2026-09-29

- Installed packages: Python 3.11.15, pytest 9.0.3, httpx 0.28.1, pydantic 2.13.3, anyio 4.13.0
- Command: `python -m pytest -p no:cacheprovider`
- Result: `42 passed, 1 skipped`. The skipped item is `tests/test_mcp_inmemory.py`, skipped because the
  workspace had `mcp 1.27.0` installed, not the pinned 2.2.0, and PyPI was not reachable to install it.
- Mutation check: changing the request to `resultType=lite` and disabling the review flag made
  `test_client_search_normal_results` fail, as it should. Both changes were reverted.
- What this covers: input validation, identifier to query mapping, HTML stripping, record parsing,
  and the HTTP client's normal / no-results / failure (503, 429, 400, bad JSON, `errMsg`, timeout,
  connection error) paths, using synthetic Europe PMC JSON and `httpx.MockTransport`.
- What this does **not** cover: anything involving the MCP SDK, the stdio transport, or the real Europe PMC API.

**Re-run 2026-10-02 (cloud workspace):** `pytest -q -p no:cacheprovider` → `50 passed, 1 skipped`. The 50 are
`test_europepmc.py` (42), `test_check_citations.py` (5, never run before this date) and the new
`test_manual_checks.py` (3). The skip is again `test_mcp_inmemory.py` (mcp 1.27.0 in the workspace, not 2.2.0).

### 2–6. Automated checks: local Windows PC, 2026-09-29 17:18 BST

Command: `uv run python scripts/verify_local.py` (full mode, including live Europe PMC).
Full output: `verification/results-20260929-171803.md`.

- Environment: Python 3.10.11, Windows (10.0.26200); mcp 2.2.0 (matches pin), httpx 0.28.1,
  pydantic 2.13.5, anyio 4.15.1, pytest 9.1.1, typer 0.27.2
- Unit tests: 42 passed
- In-memory MCP tests: 9 passed (with `REQUIRE_MCP=1`, so a skip would have counted as a failure)
- stdio launch: tools listed `['get_article', 'search_literature']`
- Live API: the demo query returned `total_hits=1456`, 5 records, each with a PMID and DOI;
  `get_article(MED:42189877)` returned `abstract_available=True`, `full_text_retrieved=False`
- Live through MCP: `search_literature` returned 3 records; `get_article` returned `MED:42189877`
  with `full_text_retrieved=False`; `get_article('not an identifier')` returned `is_error=True`

What this does **not** show: how Claude chooses and uses the tools, or how accurately it cites (checks 8–10).

### 7. MCP Inspector: PASS (2026-09-30, Inspector v2.8.0)

Screenshots are in `verification/inspector/`. The Inspector launched the server with `uv run --with mcp==2.2.0 mcp run server.py`
and connected over stdio in 1808 ms. The "Read-only session" banner refers to the Inspector's own
server list, which can't be edited in a `mcp dev` session; it doesn't affect the tools.

- [x] Connected; **Tools** lists "Search Europe PMC" (`search_literature`) and "Get one Europe PMC article"
      (`get_article`). Both are badged **READ-ONLY** and **OPEN-WORLD**, which come from the tool annotations. The query
      description and "Maximum records to return (1-20)" appear as written in `server.py` (`01-search-form.png`).
- [x] `search_literature` with `"TCR clonotype" AND persistence AND "adoptive" AND NOT PUB_TYPE:review`, max 5:
      `total_hits` 147, `returned` 5. The first record, `MED:42189877`, has PMID, PMCID, DOI, article types,
      `review_in_metadata: false`, `abstract_truncated: true`, and Europe PMC / DOI / PubMed links (`02-search-result.png`).
- [x] `get_article` with `MED:42189877` returned the same record with the **full** abstract
      (`abstract_truncated: false`) and links (`03-get-article-result.png`). The end of the result shows
      `"full_text_retrieved": false`, `"full_text_note": "Full text was NOT retrieved. …"`, `"abstract_available": true`
      and `"other_matching_records": []`, with the same data under **Structured Output** (`05-get-article-full-text-note.png`).
- [x] `get_article` with `hello` returned a **Tool Error**, not a crash: "Could not recognise 'hello' as an article
      identifier. Use a PMID (e.g. 12345678), PMCID (PMC1234567), DOI (10.1000/xyz), or the europepmc_id from
      search_literature (e.g. MED:12345678)." (`04-get-article-invalid-id-error.png`)
- [x] `search_literature` with `max_results` = 50: the Inspector **reset the value to 20** before sending, using the
      schema's `maximum: 20`, and the search ran with 20. So a client that follows the schema can't send an
      out-of-range value, but this didn't exercise the server's own rejection. That rejection is covered by
      `test_search_schema_rejects_out_of_range_limit` (check 3, passed on this machine): a raw call with `max_results: 500`
      returns `is_error: true` and sends no request to Europe PMC.

All tool calls in the Protocol panel (22:14 to 22:52) returned **OK** in 241–883 ms. The `hello` call is also "OK" at the
protocol level, because a tool error is a normal result with `is_error: true`, not a protocol failure.

### 8. Claude Code connection: PASS (2026-09-30)

- Registered with `claude mcp add` at **local scope** (your Claude Code settings, not the repo):
  `claude mcp add europepmc -- uv run --directory C:/path/to/mcp-server mcp run C:/path/to/mcp-server/server.py`
- An earlier duplicate project-scope entry (`.mcp.json`) caused a "Conflicting scopes" warning. It was
  removed with `claude mcp remove europepmc -s project`.
- Evidence: in the demo transcript, Claude Code v2.1.285 called the `europepmc` tools 11 times
  (3 searches, 8 article lookups), and results came back each time.
- `/mcp` screen (Claude Code v2.1.287, captured 2026-10-04, paths replaced with placeholders): `europepmc` **connected**,
  protocol 2026-07-28, capabilities: tools, **2 tools**, config in the user's `.claude.json` under this project (local scope).
  Screenshot: `verification/claude-code-mcp.png`.

### 9. Project skill: PASS (2026-09-30)

- [x] `.claude/skills/literature-evidence/SKILL.md` in place
- [x] Listed by Claude Code when asked "Which skills are available in this project?"
- [x] Loaded automatically for the demo question: `Skill(literature-evidence) · Successfully loaded skill`

### 10. Demonstration: RUN & SCORED (2026-09-30)

- Transcript: `examples/transcripts/demo-with-skill.txt`
- Scoring: `examples/demo-evaluation.md`. Tool selection, association vs causation, and admitting
  the limits of abstracts all scored well; two causal labels are marked for checking.
- Model: **Opus 5.5's safeguards flagged the question (`[bio]`)**, and Opus 5 produced the answer
  after an automatic switch. This run therefore does not show Opus 5.5 using the tools.

### 11. Citation check: PASS (2026-09-30 01:23 BST)

Command: `uv run python scripts/check_citations.py` (reads `examples/demo-citations.json`).
Output: `verification/citations-20260930-012332.md`. **Problems found: 0.**

- All 8 cited PMIDs resolve to Europe PMC records, and all 8 PMCIDs given in the answer match.
- All 8 were labelled "primary"; none is a review or preprint in Europe PMC's metadata.
- All 13 quoted phrases appear in the cited abstracts, including "mechanistically linked"
  (41486415), the wording the answer declined to treat as causal.
- The answer said 42575986 is tagged as a randomised Phase II trial in metadata; the record's types
  include "Clinical Trial, Phase II" and "Randomized Controlled Trial", so that is correct.
- The 4 papers mentioned but not relied on also resolve, and their titles match how the answer described them.

What this does **not** check: claims written in the answer's own words rather than quoted, such as
cohort sizes (n=4, 12, 18, 38) and study-design summaries. Those would need a manual read of each abstract.

### 12. Skill comparison: DONE (2026-09-30)

- Run B (09:56 BST): the skill was moved out of `.claude/skills/`, Claude Code confirmed it was not
  loaded, and the same question was asked. The skill has since been restored.
- Opus 5.5's safeguard flagged the question again (`[bio]`), so Opus 5 answered both runs.
- With the skill, Claude looked up the full record of all 8 papers it relied on (11 tool calls).
  Without it, Claude made 6 tool calls and cited about 22 papers, mostly from truncated search abstracts.
  The run without the skill reasoned better about reverse causation.
- Citation check for run B (12:30 BST, `examples/demo-citations-noskill.json`, output `verification/citations-20260930-123035.md`): **1 problem.**
  All 22 PMIDs resolve; every PMCID, DOI, first author and year matches. There is one misquote: "suggested",
  attributed to PMID 31845905, is not in the abstract. The NOSIP claim (PMID 42440569)
  that I flagged from its title turned out to be supported by the abstract (check 15, M3).
- Full comparison: `examples/skill-comparison.md`.

### 13. Full test suite on your machine: PENDING

```powershell
uv sync
$env:REQUIRE_MCP="1"; uv run pytest; Remove-Item Env:REQUIRE_MCP
```

Expected: `59 passed` (50 offline + 9 in-memory MCP). Record the date and the summary line here.

### 14. GitHub Actions CI: PASS (2026-10-04)

Runs on every push to `main` and on pull requests: `uv sync --locked`, a check that `mcp` is 2.2.0, then
`uv run pytest` with `REQUIRE_MCP=1`, so the MCP tests fail rather than skip if the SDK is missing. No step calls
Europe PMC.

- Run #1 (commit `639912e`, 36 s) and run #2 (commit `fc3263d`, after the screenshot redaction, 31 s): **success**,
  all 4 jobs green: Python 3.10 and 3.13 on `ubuntu-latest` and `windows-latest`. Because `REQUIRE_MCP=1` is set, the
  in-memory MCP tests ran rather than skipped on every job. The per-job test count is in the job logs, which need a
  GitHub login to read, so it isn't copied here.
- GitHub warned that Node.js 20-based actions are being deprecated. The warning doesn't affect results; bumping
  `actions/checkout` and `astral-sh/setup-uv` to their next major versions will clear it.
- Links: [run #2](https://github.com/Olu-repos/europepmc-literature-mcp/actions/runs/37165453508),
  [run #1](https://github.com/Olu-repos/europepmc-literature-mcp/actions/runs/37165034062).

### 15. Manual checks M1–M5: DONE (2026-10-04)

```powershell
uv run python scripts/manual_checks.py
```

The script prints each full abstract, which listed terms it contains and the funders in Europe PMC's grant
metadata, and writes `verification/manual-checks-latest.md`. It gives no verdicts. A reader decides each one
and records it in `examples/demo-evaluation.md` (M1, M2, M4, M5) or `examples/skill-comparison.md` (M3).

Run on 2026-10-04 01:21 BST; output `verification/manual-checks-20261004-012123.md`. Verdicts:

| Check | PMID | Question | Verdict |
|---|---|---|---|
| M1 | 42570949 | Does the abstract support "persistence", or only "expanded"? | **Expansion only.** Persistence is not a reported measured outcome; it appears in the background and the authors' closing claim. The answer's "and persistence" overreaches slightly (◐) |
| M2 | 40753920 | Does it state a direct edited vs non-edited comparison? | **Yes**, for both TCR homology and PDX tumour growth. Causal label correct (✓) |
| M3 | 42440569 | Does it report tumour control, or only persistence in chronic infection? | **Tumour control is reported** ("In a tumor model … improved tumor control"). Run B was right; the flag raised from the title was wrong |
| M4 | 42526429 | Confirm the four missed points (co-therapies, prior ICI, TLS, funding) | **All four confirmed** in the abstract text, including "funded by Iovance Biotherapeutics" in its Funding paragraph. Europe PMC's grant metadata does not list Iovance |
| M5 | 41486415 | Re-read for missed confounders | **No material omission.** Minor: the responder vs non-responder contrast is 3 patients vs 1 |
