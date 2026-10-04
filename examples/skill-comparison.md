# Skill comparison: same question, with and without the project skill

| | Run A: with skill | Run B: without skill |
|---|---|---|
| Transcript | `transcripts/demo-with-skill.txt` | `transcripts/demo-without-skill.txt` |
| Date / time | 2026-09-30, 00:49 | 2026-09-30, 09:56 |
| Claude Code | v2.1.285 | v2.1.285 |
| Model that answered | Opus 5 (Opus 5.5 safeguard flag `[bio]`) | Opus 5 (Opus 5.5 safeguard flag `[bio]` again) |
| Skill present | yes, loaded: `Skill(literature-evidence)` | no; Claude confirmed it wasn't loaded |
| MCP server | same (`europepmc`, local scope) | same |
| Question | identical | identical |

Both answers came from Opus 5, so the model is the same in both runs. The safeguard flag on
Opus 5.5 **reproduced** on the second run: it happened twice in two attempts.

## Results

| Measure | With skill | Without skill |
|---|---|---|
| Tool calls | 11 | 6 |
| Searches | 3, each listed with exact query and hit count | 4, described in a sentence; no exact queries or hit counts |
| Query revised when off-topic | yes, stated and explained | not stated |
| Reviews excluded | yes (`NOT PUB_TYPE:review`) | yes ("excluding reviews") |
| `get_article` on papers relied on | **8 of 8** | **at most 2 of ~22** (6 calls, 4 of them searches) |
| Papers cited | 8 | ~22, plus 4 conference abstract books it excluded |
| Evidence table (identifier, type, design, finding, association/causal) | yes | no: prose sections grouped by evidence type |
| Direct quotes from abstracts | 13 phrases | a few short words ("suggesting", "may contribute", …) |
| Identifiers on each claim | PMID on every sentence | PMID, PMCID, DOI, first author and year per paper |
| Citations verified against live Europe PMC | **0 problems**: 8/8 resolve, 8/8 PMCIDs, 13/13 quotes | **1 problem**: 22/22 resolve; all PMCIDs, DOIs, first authors and years correct; 4/5 quoted words found |
| Association vs causation kept apart | yes, even within one paper | yes, grouped by design strength (removal > necessity > gain/loss of function > inferred) |
| Called out an abstract's causal wording | yes ("mechanistically linked") | yes, same phrase, "the wording overreaches" |
| Reverse causation / confounding discussed | no | **yes**: antigen load drives persistence; persistence not intrinsically good (TET2/BATF3) |
| Stated abstract-only limits | yes, with specific gaps (cohort size missing, pre-specification) | yes, general ("could not check sample sizes, statistics …") |
| Search gaps / absence of evidence | yes, named a search it didn't run | partly: "not a systematic search"; suggested pulling full text |
| Labelled background knowledge | yes | no: "often cited in this area" hints at prior knowledge without saying so |
| Excluded non-primary records explicitly | 4 off-topic papers listed | 4 conference abstract books, 2 manufacturing studies, non-ACT studies marked "adjacent" |
| Time | 1 min 58 s | 2 min 2 s |

## What the skill added (from this pair of runs)

1. **Inspecting source records.** (Run B's one misquote is what happens without this.) With the skill, Claude fetched the full record of every paper it
   relied on. Without it, it made 6 calls in total and cited about 22 papers, so most claims rest
   on search results, whose abstracts are cut off after 1,500 characters. That's the step the skill
   exists to enforce.
2. **An auditable trail.** The skill's output format (search log, evidence table, quotes) made the
   first answer checkable line by line; its citations were verified with 0 problems. The second
   answer is harder to audit: no exact queries, fewer quotes, and many more papers.
3. **Scope discipline.** The skilled run stayed with 8 papers it had inspected. The unskilled run
   cast a wider net, including famous papers and adjacent fields. That broadens the discussion, but
   more of it goes beyond what was actually read.

## Citation check for the run without the skill (2026-09-30 12:30 BST)

`uv run python scripts/check_citations.py examples/demo-citations-noskill.json`: **1 problem.**

- **Bibliography: all correct.** All 22 PMIDs resolve, and every PMCID, DOI, first author and year
  given matches the Europe PMC record. The 4 conference abstract books it excluded are indeed
  abstract books ("Plenary Abstracts…", "Abstract Book…", "ASGCT … Abstracts", "Special Issue: EACR 2026 Congress").
  No invented or mismatched identifiers.
- **One misquote:** for PMID 31845905 (Nobles et al., JCI 2020) the answer puts "suggested" in quotation marks as the
  authors' own word; that word is not in the abstract. The point it makes may still be fair,
  but the quotation marks claim wording the source doesn't use. The skilled run had no misquotes.
- **NOSIP claim checked and supported (M3, 2026-10-04,
  `verification/manual-checks-20261004-012123.md`):** the answer says NOSIP overexpression "increases persistence
  and tumour control" (PMID 42440569). The title mentions only chronic infection, which is why I flagged it, but the abstract says:
  "In a tumor model, NOSIP-overexpressing CD8+ T cells exhibited improved tumor control". **My suspicion was wrong; run B
  was right.** This shows the reverse lesson too: a title alone is not enough to judge a claim, whether
  you are the model or the evaluator.
- **Checkable surface:** only 5 quoted words could be checked in run B, against 13 phrases in run A.
  Most of run B's claims are paraphrases, which this check doesn't cover.

## What the run without the skill did better

- **Deeper causal reasoning:** reverse causation (tumour control changes antigen, which changes
  persistence), and the point that persistence can reflect an unhealthy clonal state. The skilled
  answer did not raise either.
- **Grading causal evidence by design strength**, not just "association vs causal".
- **Fuller bibliographic identifiers** (DOI, first author, year) on each paper.

## Caveats

- One run of each. Some differences may be run-to-run variation, not the skill.
- Tool outputs are collapsed in both exports, so tool-call counts come from the transcript
  summaries ("Called europepmc 6 times"). Which of the 6 calls were searches is inferred from
  the answer's own statement ("four queries").
- The citation checker checks identifiers, bibliographic details and quoted words. It does not check
  claims written in the answer's own words, and run B's claims are almost all in its own words.

## Change suggested for the skill

Keep the inspection and table rules, and add one instruction: *"Before concluding, consider reverse
causation and confounding for every association, and grade causal evidence by design (removal /
necessity / gain-loss of function / inferred)."* That would carry the best part of the unskilled
answer into the skilled workflow.
