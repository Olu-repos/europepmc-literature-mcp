"""Offline tests for scripts/manual_checks.py helpers and its input file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from manual_checks import funders, term_lines  # noqa: E402


def test_term_lines_report_found_and_missing_terms():
    lines = term_lines(["stem-like", "tumour control"], "Responders had Stem-like CD8+ cells.")
    assert lines == ['- FOUND: "stem-like"', '- not found: "tumour control"']
    assert term_lines(["x"], None) == ['- not found: "x"']


def test_funders_are_deduplicated_and_missing_grants_tolerated():
    raw = {"grantsList": {"grant": [{"agency": "Iovance"}, {"agency": "NCI"}, {"agency": "Iovance"}, {}]}}
    assert funders(raw) == ["Iovance", "NCI"]
    assert funders({}) == []


def test_manual_checks_file_is_complete():
    spec = json.loads((ROOT / "examples" / "manual-checks.json").read_text(encoding="utf-8"))
    ids = [c["id"] for c in spec["checks"]]
    assert len(ids) == len(set(ids))
    for c in spec["checks"]:
        assert c["identifier"].isdigit() and c["claim"] and c["question"] and c["terms"]
