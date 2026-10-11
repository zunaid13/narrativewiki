"""Phase 22 A1: refuse to build on a stage whose most recent run crashed, until the user
acknowledges it (`--allow-partial`) or rolls it back. A crashed `wiki extract` run left a partial
`03_claims/v01.jsonl` on disk that every later stage happily consumed (docs/vision/PHASE_22.md,
2026-09-09 audit, defect item 1) -- this is the guard meant to catch that before it happens again.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import typer

from narrativewiki import cli, paths, provenance


@pytest.fixture()
def isolated_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    return tmp_path


# --- provenance.last_run_for_stage / failed_stage_artifacts -----------------


def test_last_run_for_stage_finds_the_newest_writer(isolated_runs, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from itertools import count

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    counter = count()
    monkeypatch.setattr(provenance, "_now", lambda: base + timedelta(seconds=next(counter)))

    a = provenance.start_run("86", "extract", scope="v1")
    a.finish("ok")
    b = provenance.start_run("86", "extract", scope="v2")
    b.finish("failed", error="Cannot reach Ollama")
    provenance.start_run("86", "gazetteer", scope="v1-2").finish("ok")

    found = provenance.last_run_for_stage("claims")
    assert found["run_id"] == b.run_id


def test_last_run_for_stage_returns_none_when_never_run(isolated_runs):
    assert provenance.last_run_for_stage("claims") is None


def test_failed_stage_artifacts_reports_only_failed_writers(isolated_runs):
    provenance.start_run("86", "gazetteer", scope="v1").finish("ok")
    provenance.start_run("86", "extract", scope="v1").finish("failed", error="Cannot reach Ollama")

    failed = provenance.failed_stage_artifacts(["gazetteer", "claims"])
    assert [m["command"] for m in failed] == ["extract"]


def test_failed_stage_artifacts_empty_when_all_clean(isolated_runs):
    provenance.start_run("86", "gazetteer", scope="v1").finish("ok")
    provenance.start_run("86", "extract", scope="v1").finish("ok")
    assert provenance.failed_stage_artifacts(["gazetteer", "claims"]) == []


def test_failed_stage_artifacts_empty_when_stage_never_run(isolated_runs):
    assert provenance.failed_stage_artifacts(["gazetteer", "claims"]) == []


def test_failed_stage_artifacts_dedupes_one_run_writing_two_stages(isolated_runs):
    provenance.start_run("86", "site_build", scope="upto1").finish("failed", error="boom")
    failed = provenance.failed_stage_artifacts(["bundle", "site"])
    assert len(failed) == 1


# --- cli._guard_upstream_failures --------------------------------------------


def test_guard_upstream_failures_passes_when_clean(monkeypatch):
    monkeypatch.setattr(provenance, "failed_stage_artifacts", lambda keys: [])
    cli._guard_upstream_failures(["claims"], allow_partial=False)  # must not raise


def test_guard_upstream_failures_aborts_on_a_failed_writer(monkeypatch):
    manifest = {"run_id": "20260101T000000-extract-v1", "command": "extract", "error": "Cannot reach Ollama"}
    monkeypatch.setattr(provenance, "failed_stage_artifacts", lambda keys: [manifest])
    with pytest.raises(typer.Exit):
        cli._guard_upstream_failures(["claims"], allow_partial=False)


def test_guard_upstream_failures_allow_partial_short_circuits(monkeypatch):
    def _boom(keys):
        raise AssertionError("failed_stage_artifacts should not be called when allow_partial=True")

    monkeypatch.setattr(provenance, "failed_stage_artifacts", _boom)
    cli._guard_upstream_failures(["claims"], allow_partial=True)


# --- wiring: each guarded command checks its own input stages, first ---------


class _FakeSettings:
    series_id = "test-series"
    series: dict = {}


@pytest.fixture()
def fake_settings(monkeypatch):
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeSettings())


@pytest.mark.parametrize(
    "command, input_stages",
    [
        (cli.extract, ["gazetteer"]),
        (cli.scenes, ["gazetteer"]),
        (cli.graph_build, ["gazetteer", "claims"]),
        (cli.synthesize, ["gazetteer", "graph"]),
        (cli.site_build, ["gazetteer", "graph", "pages"]),
    ],
)
def test_each_guarded_command_checks_its_input_stages_before_touching_files(
    command, input_stages, fake_settings, monkeypatch
):
    seen: dict[str, list[str]] = {}

    def fake_failed(stage_keys):
        seen["stage_keys"] = stage_keys
        return [{"run_id": "r1", "command": "whatever", "error": "boom"}]

    monkeypatch.setattr(provenance, "failed_stage_artifacts", fake_failed)
    with pytest.raises(typer.Exit):
        command()
    assert seen["stage_keys"] == input_stages


@pytest.mark.parametrize(
    "command",
    [cli.extract, cli.scenes, cli.graph_build, cli.synthesize, cli.site_build],
)
def test_allow_partial_lets_a_guarded_command_reach_its_next_check(command, fake_settings, monkeypatch):
    """With --allow-partial, the guard must not even consult provenance -- confirmed by making
    every command's next real precondition check (all missing) the thing that raises typer.Exit
    instead. All five checked paths are stubbed so the test is deterministic regardless of what
    this repo checkout's own data/ directory happens to contain."""
    _missing_file = SimpleNamespace(is_file=lambda: False)
    _missing_dir = SimpleNamespace(is_dir=lambda: False)

    def _boom(keys):
        raise AssertionError("failed_stage_artifacts should not be called when allow_partial=True")

    monkeypatch.setattr(provenance, "failed_stage_artifacts", _boom)
    monkeypatch.setattr(paths, "gazetteer", lambda: _missing_file)
    monkeypatch.setattr(paths, "mentions", lambda: _missing_file)
    monkeypatch.setattr(paths, "graph_db", lambda: _missing_file)
    monkeypatch.setattr(paths, "CLAIMS_DIR", _missing_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", _missing_dir)
    with pytest.raises(typer.Exit):
        command(allow_partial=True)


# --- cli._incomplete_claim_volumes -------------------------------------------


def test_incomplete_claim_volumes_flags_a_mentioned_character_with_zero_claims():
    characters_by_id = {
        "holo": {"entity_id": "holo", "canonical": "Holo"},
        "lawrence": {"entity_id": "lawrence", "canonical": "Kraft Lawrence"},
        "norah": {"entity_id": "norah", "canonical": "Norah Arendt"},
    }
    mentions = [
        {"vol": 1, "entity_id": "holo"},
        {"vol": 1, "entity_id": "lawrence"},
        {"vol": 1, "entity_id": "norah"},
    ]
    claims = [
        {"first_vol": 1, "subject": "holo"},
        {"first_vol": 1, "subject": "lawrence"},
        # norah mentioned in v1 but never got a claim -- the crash signature.
    ]

    incomplete = cli._incomplete_claim_volumes(claims, mentions, characters_by_id, {1})
    assert incomplete == {1: ["Norah Arendt"]}


def test_incomplete_claim_volumes_clean_when_every_mentioned_character_has_a_claim():
    characters_by_id = {"holo": {"entity_id": "holo", "canonical": "Holo"}}
    mentions = [{"vol": 1, "entity_id": "holo"}]
    claims = [{"first_vol": 1, "subject": "holo"}]

    assert cli._incomplete_claim_volumes(claims, mentions, characters_by_id, {1}) == {}


def test_incomplete_claim_volumes_ignores_a_volume_not_yet_extracted():
    """A character mentioned in v2, which has no claims file at all yet, is not "incomplete" --
    it just hasn't been extracted. Only volumes in `claimed_vols` (ones with a claims file) are
    checked."""
    characters_by_id = {"holo": {"entity_id": "holo", "canonical": "Holo"}}
    mentions = [{"vol": 1, "entity_id": "holo"}, {"vol": 2, "entity_id": "holo"}]
    claims = [{"first_vol": 1, "subject": "holo"}]

    assert cli._incomplete_claim_volumes(claims, mentions, characters_by_id, {1}) == {}


def test_incomplete_claim_volumes_ignores_a_non_character_mention():
    """Only gazetteer CHARACTERs are checked -- `characters_by_id` is pre-filtered by the caller,
    so a FACTION/LOCATION mention with zero claims (expected -- codex entries have no per-volume
    claim requirement) must never be flagged."""
    characters_by_id = {"holo": {"entity_id": "holo", "canonical": "Holo"}}
    mentions = [{"vol": 1, "entity_id": "holo"}, {"vol": 1, "entity_id": "milone-company"}]
    claims = [{"first_vol": 1, "subject": "holo"}]

    assert cli._incomplete_claim_volumes(claims, mentions, characters_by_id, {1}) == {}


# --- graph_build wires the completeness assertion in ------------------------


def test_graph_build_stops_on_incomplete_claims(monkeypatch, tmp_path):
    """End-to-end through cli.graph_build with real files on disk (via monkeypatched paths), no
    LLM involved -- confirms the completeness gate actually fires before contradictions_mod.build_graph
    would spend a single call."""
    import json

    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeSettings())
    monkeypatch.setattr(cli, "_guard_upstream_failures", lambda *a, **k: None)

    gaz_path = tmp_path / "gazetteer.json"
    gaz = {
        "entities": [
            {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER"},
            {"entity_id": "lawrence", "canonical": "Kraft Lawrence", "type": "CHARACTER"},
        ]
    }
    gaz_path.write_text(json.dumps(gaz), encoding="utf-8")
    monkeypatch.setattr(paths, "gazetteer", lambda: gaz_path)

    claims_dir = tmp_path / "03_claims"
    claims_dir.mkdir()
    (claims_dir / "v01.jsonl").write_text(
        json.dumps({"claim_id": "c_test0001", "first_vol": 1, "subject": "holo", "evidence": [], "confidence": 0.9})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "CLAIMS_DIR", claims_dir)

    mentions_path = tmp_path / "mentions.jsonl"
    mentions_path.write_text(
        "\n".join(
            json.dumps(m)
            for m in [{"vol": 1, "entity_id": "holo"}, {"vol": 1, "entity_id": "lawrence"}] * 10
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "mentions", lambda: mentions_path)

    with pytest.raises(typer.Exit):
        cli.graph_build(allow_partial=False)


def test_incomplete_claim_volumes_ignores_a_passing_mention_below_the_floor():
    """[33] Overlord v2 names Brain Unglaus once in a list; he has no claim there, correctly."""
    characters_by_id = {"brain": {"entity_id": "brain", "canonical": "Brain Unglaus"}}
    mentions = [{"vol": 2, "entity_id": "brain"}]
    assert cli._incomplete_claim_volumes([], mentions, characters_by_id, {2}, min_mentions=10) == {}
    assert cli._incomplete_claim_volumes([], mentions * 10, characters_by_id, {2}, min_mentions=10) == {2: ["Brain Unglaus"]}


def test_extract_finished_ok_trusts_a_clean_run_but_not_a_killed_one(monkeypatch):
    """[33] A1 t=2: a clean extract with zero claims about "God" is not a crash; a killed run
    (no outcome recorded) still is."""
    from narrativewiki import paths, provenance
    monkeypatch.setattr(paths, "build_cutoff", lambda: None)
    runs = [{"command": "extract", "volumes": [2], "build_cutoff": None},              # killed, newest
            {"command": "extract", "volumes": [1], "build_cutoff": None, "outcome": "ok"},
            {"command": "extract", "volumes": [2], "build_cutoff": None, "outcome": "ok"}]
    monkeypatch.setattr(provenance, "list_runs", lambda limit=None: runs)
    assert cli._extract_finished_ok(1) and not cli._extract_finished_ok(2) and not cli._extract_finished_ok(3)
