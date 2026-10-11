"""[33] S15: gold facts visible at t, and the page anchor format the tracer matches."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("retention_trace", Path(__file__).parents[1] / "scripts/eval/retention_trace.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)


def test_only_facts_revealed_by_t_are_traced():
    gold = {"characters": {"A": {"facts": [{"claim": "x", "evidence": "v01:c02:p0003"},
                                           {"claim": "y", "evidence": "v03:c00:p0001"}]}}}
    assert [f["claim"] for f in rt.gold_facts(gold, 2)] == ["x"]
    assert [f["first_vol"] for f in rt.gold_facts(gold, 3)] == [1, 3]


def test_anchor_matches_the_wiki_citation_format():
    assert rt.anchor("v01:c06:p0003") == "nw-v01-c06-p0003"
