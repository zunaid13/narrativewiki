"""Phase 24 / TASK-0001: `wiki extract --gate=build` -- the cutoff-consistent extraction sweep.

`_extract_claims_for_volumes` must use exactly the `entities_visible` list its caller passes,
never a freshly (re)loaded, unfiltered gazetteer -- that is what makes `--gate=build`'s per-cutoff
entity restriction actually take effect instead of being silently bypassed.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest
import typer

from narrativewiki import cli, paths
from narrativewiki.config import load_settings
from narrativewiki.extract import claims as claims_mod


@pytest.fixture()
def isolated_claims_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CLAIMS_DIR", tmp_path / "03_claims")
    paths.CLAIMS_DIR.mkdir()
    mentions_path = tmp_path / "mentions.jsonl"
    mentions_path.write_text(
        json.dumps({"para_id": "v01:c00:p0000", "vol": 1, "entity_id": "holo", "surface": "Holo", "start": 0, "end": 4})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "mentions", lambda: mentions_path)
    (tmp_path / "v01.jsonl").write_text(
        json.dumps({"para_id": "v01:c00:p0000", "vol": 1, "chapter_idx": 0, "text": "Holo spoke."}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "parsed_volume", lambda vol: tmp_path / f"v{vol:02d}.jsonl")
    # `_extract_claims_for_volumes` opens a real run; unpatched, every pytest invocation left a
    # fake "ok" extract run in the repo's ledger, where `last_run_for_stage("claims")` finds it.
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    return tmp_path


def test_extract_claims_for_volumes_only_sees_passed_entities_visible(isolated_claims_dir, monkeypatch):
    """A fixture entity with `first_vol` above the cutoff -- excluded from `entities_visible` by
    the caller (this is `extract()`'s job in --gate=build, not this helper's) -- must not reach
    `extract_volume`'s character list or its "other entities" registry."""
    captured: dict = {}

    def fake_extract_volume(characters, vol, records, mentions, all_entities, settings, client, on_progress=None):
        captured["characters"] = characters
        captured["all_entities"] = all_entities
        return [], Counter()

    monkeypatch.setattr(claims_mod, "extract_volume", fake_extract_volume)

    holo = {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER", "first_vol": 1, "aliases": []}
    # A future character (first_vol=3) that a cutoff-1 caller would already have excluded from
    # entities_visible -- never even offered to this helper.
    entities_visible = [holo]

    settings = load_settings("spice-and-wolf")
    cli._extract_claims_for_volumes(settings, [1], entities_visible, None, False, None, None)

    assert [e["entity_id"] for e in captured["characters"]] == ["holo"]
    assert captured["all_entities"] == entities_visible
    assert not any(e["entity_id"] == "future-girl" for e in captured["all_entities"])


def test_extract_gate_build_rejects_entities_filter():
    """--gate=build is a cutoff sweep over volumes/characters; --entities targets one character
    for iterative development. The two don't compose (task 0001 §2.B) -- must error, not silently
    ignore --entities and run the full sweep."""
    with pytest.raises(typer.Exit):
        cli.extract(gate="build", entities="Kraft Lawrence")


def test_extract_gate_build_rejects_chapters_and_limit_too():
    with pytest.raises(typer.Exit):
        cli.extract(gate="build", chapters="1-2")
    with pytest.raises(typer.Exit):
        cli.extract(gate="build", limit=2)


def test_extract_gate_render_with_entities_is_unaffected(monkeypatch, capsys):
    """Regression check (task 0001 acceptance criteria): render + --entities must not be treated
    as an invalid combination -- only build + narrowing is. Proven by reaching a LATER failure
    (no gazetteer on disk) rather than the --gate/--entities compatibility message."""
    monkeypatch.setattr(cli, "_guard_upstream_failures", lambda *a, **k: None)
    monkeypatch.setattr(paths, "gazetteer", lambda: paths.PROJECT_ROOT / "does-not-exist.json")
    with pytest.raises(typer.Exit):
        cli.extract(series="spice-and-wolf", volumes="1", gate="render", entities="Kraft Lawrence")
    out = capsys.readouterr().out
    assert "No gazetteer/mention index found" in out
    assert "incompatible" not in out
