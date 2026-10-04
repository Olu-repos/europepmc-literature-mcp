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
| LAG-3+ TIL and persistence with PFS (42526429) | association | Label right, but the answer left out four things in the same abstract that weaken any causal reading (section 3a) | ◐ |
| Overlap index predicts response, AUC 0.79 (42189877) | association | | ✓ |
| mRNA antigen needed for transferred TCRtg expansion (42570949) | causal | Causal for expansion. Extending it to "persistence" goes beyond the quoted sentence, which says "expanded". **Pending:** check M1 in `examples/manual-checks.json` tests whether the abstract mentions persistence at all | ? (pending M1) |
| PD-1 editing → retained clonotype homology (40753920) | causal | Edited vs non-edited is a controlled comparison, so reasonable. **Pending:** check M2 confirms the abstract describes that direct comparison | ? (pending M2) |
| Overall: "no retrieved study experimentally manipulates clonotype persistence in patients" | synthesis | Correctly scoped to "these records" rather than the literature as a whole | ✓ |

## 3a. What the answer left out: PMID 42526429 (melanoma TIL)

A manual re-read of this abstract (2026-10-02) found four points the answer did not mention. Points 1–3
are in the abstract itself, so the abstract-only limit is not the excuse; point 4 comes from the
record's funding statement (check M4 confirms where it appears). All four bear
directly on the association-vs-causation question the user asked.

| # | Stated in the record | Why it matters for causation | In the answer? |
|---|---|---|---|
| 1 | Patients were treated "with or without additional therapies" | Co-treatment is a confounder: response and persistence may both reflect the add-on therapy, not each other | no |
| 2 | Prior immune checkpoint inhibitor exposure was associated with reduced CD8+ stem-like memory (TSCM) cells and co-stimulatory receptors, "suggesting impaired TIL fitness" | Treatment history affects the product and may affect persistence and response together: a common cause | no |
| 3 | Tertiary lymphoid structures and antigen-presentation / immune programmes in the tumour were "independently associated with clinical benefit" | A rival explanation that sits in the tumour, not the infused clones | no |
| 4 | Funded by Iovance Biotherapeutics (the TIL manufacturer) | Conflict of interest worth reporting next to the finding | no |

The answer also left out the headline outcomes (durable ORR 36%, median PFS 8 months) and that the
data were pooled from several early-phase trials. It did say the abstract gives no cohort size,
which is correct.

**Effect on the score:** the association label for 42526429 stays correct, but the answer presented
"enhanced peripheral TIL persistence" in responders without the confounders and rival explanation
the same abstract offers. That row is now ◐ (partial). Check M4 in `examples/manual-checks.json`
re-confirms each quoted phrase against the live abstract and lists the funder from Europe PMC's
grant metadata.

**Not yet re-read:** PMID 41486415 (acral melanoma, n=4). Its fetch was rate-limited (HTTP 429);
check M5 covers it.

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
- **Missed in an abstract it did read:** for 42526429 the answer left out co-therapies, the effect of prior checkpoint-inhibitor exposure, an independent tumour-side predictor, and industry funding (section 3a). Reading the full abstract is necessary, but the skill didn't ask Claude to report confounders, so it didn't.
- **Open manual checks (pending until `scripts/manual_checks.py` output is recorded):** M1, whether 42570949's abstract supports "persistence" or only "expanded"; M2, whether 40753920 states a direct edited-vs-non-edited comparison (the title, "PD-1 attenuation enhances TIL-based adoptive cellular therapy in humanized-PDX model", suggests so); M5, a re-read of 41486415 for missed points. M3 (NOSIP, PMID 42440569) belongs to the run without the skill and is recorded in `skill-comparison.md`.
- **Change to try next:**
  1. Skill: ask for the label "causal (for X, not for persistence → response)" to be written out every time. The answer did this in prose but not consistently in the table.
  2. Server: add an optional `sort` parameter (e.g. by date or citations), since relevance order biased the sample towards 2025–26 papers.
  3. Skill (added 2026-10-02, not yet re-tested): "For each finding, list the co-treatments, prior treatments, other independent predictors and funding sources that the abstract states."
  4. Export: record the tool calls themselves (expand them before `/export`, or use a verbose transcript) so citations can be checked against the tool output, not just against live records.

## Suggested comparison

Run the same question with the skill moved out of `.claude/skills/`, and fill in a second copy of
this sheet. That shows what the skill adds beyond the server. Record the model used in each run.
