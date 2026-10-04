---
name: literature-evidence
description: Answer biomedical literature questions (especially T-cell / cell-therapy research) using the Europe PMC MCP tools. Use when asked to find, compare or cite papers, or to judge what published evidence supports a claim.
---

# Literature evidence from Europe PMC

Use the `europepmc` MCP server tools: `search_literature` and `get_article`.
The tools return source records only. You do the interpretation, and every
claim you make must be traceable to a record you actually retrieved.

## Workflow

1. **Plan the search.** Turn the question into 1–3 Europe PMC queries. Include
   synonyms (e.g. `"adoptive cell transfer" OR "adoptive T-cell therapy" OR TIL OR "CAR-T"`,
   `clonotype OR "TCR repertoire" OR "clonal tracking"`). When the user wants primary
   studies, add `NOT PUB_TYPE:review`. Keep `max_results` small (5–10).
2. **Search.** Call `search_literature`. If `total_hits` is 0 or results are off-topic,
   revise the query once or twice and say that you did. No results is not evidence of absence.
3. **Inspect the source records.** For every paper you intend to rely on, call
   `get_article` with its `europepmc_id` and read the full abstract. Do not rely on a
   truncated search abstract (`abstract_truncated: true`) or on the title alone.
4. **Classify each paper** from what the record shows:
   - *Review / meta-analysis*: `review_in_metadata: true`, or the abstract describes
     summarising other work. Use for background only, never as primary evidence.
   - *Preprint*: `preprint: true`. Say it is not peer reviewed.
   - *Primary study*: reports its own data. Note the design the abstract states
     (trial phase, cohort size, mouse model, in vitro, case report). If the abstract does not
     state it, write "design not stated in abstract".
   - `review_in_metadata: false` does not prove a paper is primary research; check the abstract.
5. **Separate association from causation.** Label each finding:
   - *Observed association*: correlation in patients or cohorts (e.g. persistence correlated with response).
   - *Causal / mechanistic evidence*: an intervention or controlled experiment that manipulates the
     variable (e.g. knockout, randomised comparison, controlled transfer experiment).
   - *Not determinable from abstract*: say so rather than guessing.

   For every finding, also report what the abstract or record states about **co-treatments,
   prior treatments, other independent predictors, and funding sources**. These are the confounders
   and rival explanations a reader needs before treating an association as causal.
6. **Cite with identifiers.** Every factual sentence about a paper ends with its identifier,
   e.g. `(PMID 12345678)`, or `(PMC1234567)`, `(DOI 10.xxxx/yyy)`, or `(PPR:PPR123456)` for preprints.
   Only cite identifiers that appear in tool output from this conversation. Never invent or
   "recall" an identifier, author list or number.
7. **Mark uncertainty explicitly.** Every `get_article` result says full text was not retrieved.
   Therefore:
   - Do not state effect sizes, p-values, sample sizes or methods unless they appear in the abstract.
   - When the user's question needs detail the abstract lacks, write:
     "The abstract does not report X; the full text would need to be checked."
   - If a tool returns an error, report it; do not fill the gap from memory.

## Output format

1. **Search log**: queries run, hits, anything revised.
2. **Evidence table**: identifier | year | type (primary / review / preprint) | design as stated | key finding (quoted or closely paraphrased) | association vs causal.
3. **Synthesis**: short, with each claim cited, and associations kept apart from causal evidence.
4. **Limits**: abstract-only basis, papers that looked relevant but could not be assessed, and search gaps.

## Don'ts

- Don't present background knowledge as if it came from the retrieved papers. If you add context
  from general knowledge, label it "(general background, not from retrieved records)".
- Don't upgrade an association to a cause because the abstract's discussion speculates about mechanism.
- Don't count a review as independent confirmation of the primary studies it summarises.
