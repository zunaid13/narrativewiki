"""Primary-source alpha examples verify finite-sample and missing-data weights."""
import sys
from pathlib import Path

import pytest

DIR = Path(__file__).resolve().parents[1] / "docs/eval/agreement"
sys.path.insert(0, str(DIR))
from score_alpha import nominal_alpha


def test_krippendorff_published_two_rater_nominal_example():
    # Krippendorff (2011/2013), example B, pp. 3-4; displayed alpha rounds to .692.
    rows = list(zip("aabbdcccedda", "babbbccceddd"))
    value = nominal_alpha(rows)
    assert value["alpha"] == pytest.approx(1 - 138 / 448)
    assert value["pairable_ratings"] == 24
    assert value["observed_disagreement"] == pytest.approx(0.25)


def test_krippendorff_published_missing_data_example():
    # Example C, pp. 4-5: four raters, 12 units; one singleton contributes no coincidence.
    raters = [[1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
              [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
              [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
              [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None]]
    value = nominal_alpha(list(zip(*raters)))
    assert value["alpha"] == pytest.approx(1 - 312 / 1216)
    assert value["label_counts"] == {1: 9, 2: 13, 3: 10, 4: 5, 5: 3}
    assert value["pairable_ratings"] == 40
    assert value["excluded_unit_indices"] == [11]


def test_three_raters_negative_perfect_and_undefined_cases():
    assert nominal_alpha([["yes", "yes", "no"], ["no", "no", "yes"]])["alpha"] == pytest.approx(-1 / 9)
    assert nominal_alpha([["yes"] * 3, ["no"] * 3])["alpha"] == 1
    assert nominal_alpha([["yes"] * 3])["alpha"] is None
    assert nominal_alpha([["yes", None]])["alpha"] is None
