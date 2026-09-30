"""Offline tests for the quote matcher used by scripts/check_citations.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_citations import normalise, quote_in_abstract  # noqa: E402


def test_quote_matching_ignores_case_whitespace_and_punctuation():
    abstract = "Results: TIL-derived clonotypes  exhibited\nsustained persistence in blood (n = 1)."
    assert quote_in_abstract("til derived clonotypes exhibited sustained persistence", abstract)
    assert quote_in_abstract("TIL-derived clonotypes exhibited sustained persistence in blood", abstract)


def test_quote_matching_keeps_numbers_and_comparators():
    abstract = "detectable at low frequency (<0.1%) at day 14"
    assert quote_in_abstract("at low frequency (<0.1%) at day 14", abstract)
    assert not quote_in_abstract("at low frequency (<1%) at day 14", abstract)


def test_changed_wording_is_not_found():
    abstract = "Persistence correlated with response."
    assert not quote_in_abstract("persistence caused response", abstract)
    assert not quote_in_abstract("anything", None)


def test_normalise_folds_dashes():
    assert normalise("CRISPR–Cas9") == normalise("CRISPR-Cas9")


def test_first_author_and_year_matching():
    from check_citations import first_author_matches, year_matches

    assert first_author_matches("Muller", "Müller A, Smith B.")
    assert first_author_matches("Paruzzo", "Paruzzo L, Ghilardi G.")
    assert not first_author_matches("Smith", "Müller A, Smith B.")
    assert year_matches(2026, "2025", "2026-01-04")  # print year vs first publication date
    assert not year_matches("2024", "2025", "2025-11-05")
