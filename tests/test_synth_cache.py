"""Tests for synth/cache.py — Phase 6, CONTRACTS §5.1."""

from __future__ import annotations

import json

from narrativewiki import paths
from narrativewiki.synth import cache as CA


def _write_page(tmp_path, entity_id, vol, claim_set_hash):
    d = tmp_path / entity_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"v{vol:02d}.json").write_text(
        json.dumps({"entity_id": entity_id, "upto_vol": vol, "claim_set_hash": claim_set_hash}),
        encoding="utf-8",
    )


def test_previous_page_none_when_nothing_written(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    assert CA.previous_page("shin", 1) is None


def test_previous_page_finds_nearest_lower_volume_across_a_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    _write_page(tmp_path, "shin", 1, "hash_a")
    # v02 was cache-skipped (unchanged from v01) -- no file for it.
    _write_page(tmp_path, "shin", 3, "hash_b")

    prev = CA.previous_page("shin", 5)
    assert prev["upto_vol"] == 3
    assert prev["claim_set_hash"] == "hash_b"

    prev_at_2 = CA.previous_page("shin", 2)
    assert prev_at_2["upto_vol"] == 1


def test_unchanged_true_only_when_hash_matches_an_existing_previous_page():
    assert CA.unchanged(None, "hash_a") is False
    assert CA.unchanged({"claim_set_hash": "hash_a"}, "hash_a") is True
    assert CA.unchanged({"claim_set_hash": "hash_a"}, "hash_b") is False
