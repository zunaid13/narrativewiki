"""Phase 11: the chapter-scoping helpers `ingest --chapters`/`extract --chapters` share.

`_merge_by_chapter` is what makes chaptered ingest/extract accumulate a volume's file one
chapter at a time instead of clobbering chapters an earlier, narrower call already wrote --
pulled out of both command bodies into one small pure function specifically so it's testable
without a full EPUB/Settings/LLM fixture. `_chapter_of_para_id` is the one place a mention
record's chapter is recovered, since mention records carry no chapter_idx field of their own.
"""

from __future__ import annotations

import pytest
import typer

from narrativewiki import cli, paths


def _rec(chapter_idx: int, seq: int, tag: str) -> dict:
    return {"chapter_idx": chapter_idx, "seq": seq, "tag": tag}


def _vrec(vol: int, tag: str) -> dict:
    return {"vol": vol, "tag": tag}


def test_merge_keeps_untouched_chapters_and_replaces_touched_ones():
    existing = [_rec(0, 0, "old-c0"), _rec(1, 0, "old-c1"), _rec(2, 0, "old-c2")]
    fresh = [_rec(1, 0, "new-c1")]
    merged = cli._merge_by_chapter(existing, fresh, {1})
    assert {r["tag"] for r in merged} == {"old-c0", "old-c2", "new-c1"}


def test_merge_against_empty_existing_is_just_the_fresh_records():
    merged = cli._merge_by_chapter([], [_rec(0, 0, "new-c0")], {0})
    assert [r["tag"] for r in merged] == ["new-c0"]


def test_merge_touching_every_chapter_drops_nothing_old():
    existing = [_rec(0, 0, "old-c0"), _rec(1, 0, "old-c1")]
    fresh = [_rec(0, 0, "new-c0"), _rec(1, 0, "new-c1")]
    merged = cli._merge_by_chapter(existing, fresh, {0, 1})
    assert {r["tag"] for r in merged} == {"new-c0", "new-c1"}


def _crec(subject: str, tag: str) -> dict:
    return {"subject": subject, "tag": tag}


def test_merge_by_entity_keeps_untouched_entities_and_replaces_touched_ones():
    existing = [_crec("holo", "old-holo"), _crec("lawrence", "old-lawrence")]
    fresh = [_crec("holo", "new-holo")]
    merged = cli._merge_by_entity(existing, fresh, {"holo"})
    assert {r["tag"] for r in merged} == {"old-lawrence", "new-holo"}


def test_merge_by_entity_against_empty_existing_is_just_the_fresh_records():
    merged = cli._merge_by_entity([], [_crec("holo", "new-holo")], {"holo"})
    assert [r["tag"] for r in merged] == ["new-holo"]


def test_chapter_of_para_id_parses_the_c_segment():
    assert cli._chapter_of_para_id("v03:c02:p0015") == 2
    assert cli._chapter_of_para_id("v01:c00:p0000") == 0
    assert cli._chapter_of_para_id("v11:c12:p0001") == 12


# ---------------------------------------------------------------------------
# Phase 18: `_merge_by_volume` (`wiki gazetteer --merge-epithets`'s mentions.jsonl re-index)
# ---------------------------------------------------------------------------


def test_merge_by_volume_keeps_untouched_volumes_and_replaces_touched_ones():
    existing = [_vrec(1, "old-v1"), _vrec(2, "old-v2"), _vrec(3, "old-v3")]
    fresh = [_vrec(2, "new-v2")]
    merged = cli._merge_by_volume(existing, fresh, {2})
    assert {r["tag"] for r in merged} == {"old-v1", "old-v3", "new-v2"}


def test_merge_by_volume_against_empty_existing_is_just_the_fresh_records():
    merged = cli._merge_by_volume([], [_vrec(1, "new-v1")], {1})
    assert [r["tag"] for r in merged] == ["new-v1"]


# ---------------------------------------------------------------------------
# Phase 18: `wiki gazetteer --merge-epithets` prerequisite guards
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_entities_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    paths.ENTITIES_DIR.mkdir(parents=True)
    paths.SCENES_DIR.mkdir(parents=True)
    return tmp_path


def test_merge_epithets_errors_cleanly_without_a_gazetteer(isolated_entities_dir):
    with pytest.raises(typer.Exit):
        cli._merge_epithets_into_gazetteer(object(), [1])


def test_merge_epithets_errors_cleanly_without_scenes_output(isolated_entities_dir):
    paths.gazetteer().write_text('{"entities": []}', encoding="utf-8")
    with pytest.raises(typer.Exit):
        cli._merge_epithets_into_gazetteer(object(), [1])


def test_gazetteer_gate_build_rejects_merge_epithets():
    """[24] `--gate=build --merge-epithets` used to silently ignore `--gate` (the merge-epithets
    branch returns before the gate branch is ever reached) -- one of the confounds behind the
    2026-09-14 (late pm) individuation-mechanism correction (docs/vision/PHASE_24.md). Must now
    error instead, before touching settings/paths -- mirrors `extract`'s own incompatible-option
    guard (tests/test_extract_gate.py)."""
    with pytest.raises(typer.Exit):
        cli.gazetteer(gate="build", merge_epithets=True)
