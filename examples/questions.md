# Example questions

Ask these in Claude Code with the `europepmc` server connected. The first one is the main demonstration.

## 1. Main demonstration (tool use, citation and uncertainty)

> Find primary studies on TCR clonotype persistence after adoptive T-cell therapy. Separate observed associations from evidence of causation, and give identifiers for the papers used.

What a good answer does: runs `search_literature` (ideally excluding reviews), calls `get_article` on the papers it relies on, cites PMIDs/DOIs from the tool output, keeps "persistence correlated with response" apart from any causal claim, and says where the abstract is not enough.

## 2. Primary vs review

> Search for work on stem-like (TCF1+/TCF7+) CD8 T cells and response to adoptive cell therapy. Which of the results are reviews and which are primary studies? How can you tell from the records?

Tests: uses `article_types` / `review_in_metadata` and the abstract, and admits that `review_in_metadata: false` alone isn't proof of primary research.

## 3. Single-record inspection

> Get the article `<PMID or europepmc_id from question 1's results>` and tell me what its abstract does and does not let us conclude about T-cell persistence.

Tests: direct `get_article` use; the answer should repeat the full-text-not-retrieved caveat. Also try a made-up identifier: the answer should report "no record matched", not invent a paper.

## 4. Claim checking

> Is there published evidence that lymphodepletion with fludarabine improves CAR-T persistence? Cite only papers you retrieved and say whether each shows association or causation.

Tests: refusing to go beyond retrieved abstracts; distinguishing randomised or controlled comparisons from cohort correlations.

## 5. Preprints

> Find recent preprints on TCR repertoire tracking in TIL therapy and flag which findings have not been peer reviewed.

Tests: `preprint: true` handling and `PPR:` identifiers.

## 6. No-result behaviour

> Find randomised controlled trials of TCR-T therapy in glioblastoma that report clonotype persistence beyond five years.

Tests: when the search returns little or nothing, the answer should say so and not treat it as proof no such trial exists.
