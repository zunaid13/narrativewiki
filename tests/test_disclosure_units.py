"""Check that disclosure accounting preserves subject facts and rejects duplicate units."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "disclosure_units", Path(__file__).resolve().parents[1] / "scripts/eval/disclosure_units.py")
units = importlib.util.module_from_spec(spec)
spec.loader.exec_module(units)


def row(t=1, character="A", claim="A marries B", reveal=4, verdict="stated"):
    return dict(t=t, character=character, claim=claim, reveal=reveal, verdict=verdict)


def test_repeated_cutoffs_collapse_but_reciprocal_facts_do_not():
    rows = [row(t=2), row(t=3), row(t=2, character="B", claim="B marries A"),
            row(t=3, character="B", claim="B marries A")]
    result = units.summarize(rows)
    assert result["confirmed_assessments"] == 4
    assert result["unique_subject_facts"] == 2
    assert result["confirmed_unique_subject_facts"] == 2


def test_mixed_verdicts_count_unique_inclusive_facts_without_double_counting():
    result = units.summarize([row(verdict="absent"), row(t=2, verdict="uncertain"), row(t=3)])
    assert result["assessments"] == 3
    assert result["inclusive_assessments"] == 2
    assert result["inclusive_unique_subject_facts"] == 1
    assert result["confirmed_unique_subject_facts"] == 1


@pytest.mark.parametrize("rows", [
    [row(), row()], [row(t=4)], [row(reveal=6)], [row(verdict="supported")],
])
def test_invalid_units_fail_instead_of_inflating_counts(rows):
    with pytest.raises(ValueError):
        units.summarize(rows)
