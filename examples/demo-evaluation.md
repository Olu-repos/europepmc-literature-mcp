# Demonstration record

Transcript: [`transcripts/demo-with-skill.txt`](transcripts/demo-with-skill.txt), a `/export` from Claude Code. The export collapses tool inputs and outputs ("ctrl+o to expand"), so
the transcript alone can't show exactly what each tool returned. Citation accuracy is therefore
checked separately against live Europe PMC records with `scripts/check_citations.py` (section 2).

**Question**

> Find primary studies on TCR clonotype persistence after adoptive T-cell therapy. Separate observed associations from evidence of causation, and give identifiers for the papers used.

| Field | Value |
|---|---|
| Date run | 2026-09-30, finished 00:49 BST |
| Claude Code version | v2.1.285 (Claude Pro) |
| Model | Opus 5 (switched automatically after a safeguard flag on Opus 5.5) |
| Project skill active? (`literature-evidence`) | **yes**: transcript shows `Skill(literature-evidence) · Successfully loaded skill` |
| MCP server | `europepmc`, local scope (`claude mcp add`), launched with `uv run --directory … mcp run …/server.py` |
| Transcript file | `transcripts/demo-with-skill.txt` |
| Duration | 1 min 58 s |

## 1. Tool selection

| Check | Result | Notes |
|---|---|---|
| Called `search_literature` (not answering from memory) | ☑ yes | 3 searches ("Called europepmc" ×3, logged in the answer's search log) |
| Query wording | see note | Q1: `("TCR clonotype" OR "T cell receptor clonotype" OR "TCR repertoire" OR "clonal tracking") AND ("adoptive cell transfer" OR "adoptive T cell therapy" OR "tumor infiltrating lymphocyte" OR TIL OR "CAR-T") AND persistence NOT PUB_TYPE:review`, 588 hits |
| Tried to exclude reviews | ☑ yes | `NOT PUB_TYPE:review` on all three queries |
| Revised the query when results were thin or off-topic | ☑ yes | Said Q2 "drifted toward checkpoint-blockade and TCR-discovery work", used nothing from it, and revised to Q3 |
| Called `get_article` on each paper it relied on | ☑ all | "Called europepmc 8 times" = 8 cited papers; the answer states full abstracts were retrieved for all eight |
| Stayed within a small `max_results` | ☑ yes | Inspected 10 records from Q1 |

## 2. Citation accuracy

Checked with `uv run python scripts/check_citations.py` on 2026-09-30 01:23 BST against live Europe PMC
(`verification/citations-20260930-012332.md`). **Problems found: 0.**

| Identifier cited | Resolves? | PMCID matches? | Quoted claims in abstract? | Labelled correctly? (metadata types) |
|---|---|---|---|---|
| PMID 41267983 | yes | yes | 1/1 | primary ✓ (brief-report) |
| PMID 42575986 | yes | yes | 1/1 | primary ✓ (Phase II, Randomized Controlled Trial) |
| PMID 41486415 | yes | yes | 2/2 | primary ✓ (research-article) |
| PMID 42618927 | yes | yes | 4/4 | primary ✓ (Phase I) |
| PMID 42526429 | yes | yes | 2/2 | primary ✓ (research-article) |
| PMID 42189877 | yes | yes | 1/1 | primary ✓ (Phase I) |
| PMID 42570949 | yes | yes | 1/1 | primary ✓ (research-article) |
| PMID 40753920 | yes | yes | 1/1 | primary ✓ (research-article) |

- Fabricated or unresolvable identifiers: **0 of 12** (8 cited, plus 4 mentioned but not relied on)
- Quoted claims not found in the cited abstract: **0 of 13**
- Not covered by the check: paraphrased details such as cohort sizes and design summaries. These
  would need reading each abstract by hand.
- Caveat: the export collapses tool outputs, so this checks the citations against the **live**
  records, not against the exact tool responses Claude saw. They should be the same records,
  fetched a few minutes apart.

## 3. Association vs causation

| Claim in answer | Labelled as | Assessment | OK? |
|---|---|---|---|
| Clonotype persistence to 5 years with response (41267983, n=1) | association | Single uncontrolled patient | ✓ |
| Oligoclonal CAR-T persistence at 9.3 years (42575986) | association / descriptive | Also flagged that the metadata "Phase II RCT" tag does not make the persistence analysis randomised: a good catch | ✓ |
| Dominant persisting clone in complete responder (41486415) | association | Explicitly declined the abstract's own "mechanistically linked" wording as causal (n=4) | ✓ |
| Clonal remodelling in responders (42618927a) vs ASS1/CEP20 knockout (42618927b) | association / causal, split | Correctly separated within one paper, and noted the causal part concerns TIL function, not persistence → response | ✓ |
| LAG-3+ TIL and persistence with PFS (42526429) | association | | ✓ |
| Overlap index predicts response, AUC 0.79 (42189877) | association | | ✓ |
| mRNA antigen needed for transferred TCRtg expansion (42570949) | causal | Causal for expansion. Extending it to "persistence" goes slightly beyond the quoted sentence, which says "expanded"; check the abstract | ? |
| PD-1 editing → retained clonotype homology (40753920) | causal | Edited vs non-edited is a controlled comparison, so reasonable; confirm the abstract describes a direct comparison | ? |
| Overall: "no retrieved study experimentally manipulates clonotype persistence in patients" | synthesis | Correctly scoped to "these records" rather than the literature as a whole | ✓ |

## 4. Admitting the limits of an abstract

| Check | Result | Example quote |
|---|---|---|
| Stated that full text was not retrieved | ☑ yes | "Abstract-only basis. Full text was not retrieved for any record." |
| Declined to give numbers/methods not in the abstract | ☑ yes | "Sample sizes, statistics, persistence thresholds, sequencing depth … are not verifiable here" |
| Named at least one point the abstract cannot settle | ☑ yes | "PMID 42526429 does not state its cohort size in the abstract"; whether 42575986's 10-year analysis was pre-specified "would need checking" |
| Separated general background knowledge from retrieved evidence | ☑ yes | Did not cite "landmark" studies from memory; said they "may sit outside that window" and named a search it did not run |
| No-result / absence handled correctly | ☑ yes | "No result here should be read as evidence of absence" |

## 5. Summary

- **What worked:** Claude loaded the project skill by itself and followed its workflow: search, revise, `get_article` on every relied-on paper, classify, cite, state the limits. It kept patient associations apart from experimental causal evidence, even within one paper (42618927), and refused to treat an abstract's causal wording ("mechanistically linked") as causal evidence. Every factual sentence carries a PMID. It said openly where its search was weak (a TIL/2025–26 skew, only one CAR-T paper, 10 of 588 inspected).
- **What failed:** Opus 5.5's safeguards flagged the demonstration question, which is ordinary T-cell literature research ("Details: `[bio]`"). The session switched automatically to Opus 5, which produced the answer, so this run does **not** show Opus 5.5 using the tools.
- **Citations:** 8/8 PMIDs and PMCIDs correct, 13/13 quotes found verbatim in the abstracts, and no invented identifiers.
- **Still worth a manual look:** two causal labels go slightly beyond the quoted text. 42570949's quote says the cells "expanded", but the answer also says "persistence". For 40753920, the title ("PD-1 attenuation enhances TIL-based adoptive cellular therapy in humanized-PDX model") supports a controlled comparison.
- **Change to try next:**
  1. Skill: ask for the label "causal (for X, not for persistence → response)" to be written out every time. The answer did this in prose but not consistently in the table.
  2. Server: add an optional `sort` parameter (e.g. by date or citations), since relevance order biased the sample towards 2025–26 papers.
  3. Export: record the tool calls themselves (expand them before `/export`, or use a verbose transcript) so citations can be checked against the tool output, not just against live records.

## Suggested comparison

Run the same question with the skill moved out of `.claude/skills/`, and fill in a second copy of
this sheet. That shows what the skill adds beyond the server. Record the model used in each run.
