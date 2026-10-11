"""Phase 11: `wiki step`'s pure "what's next" resolution logic.

`cli._resolve_step_target` is deliberately a standalone function of (settings, progress, flags)
plus whatever's on disk in data/01_parsed/ -- no LLM/network involved, so it's tested directly
here without going through the full step/extract/graph_build/synthesize/site_build chain.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import typer

from narrativewiki import cli, paths, provenance


class _FakeSettings:
    """Just enough of Settings for _resolve_step_target: discover_volumes() -> objects with .vol.
    `series_id`/`extraction`/`schema_*` are only read by Phase 12's step()-owned RunContext
    (provenance.start_run -> provenance._config_hashes)."""

    def __init__(self, vols: list[int]) -> None:
        self._vols = vols
        self.series_id = "test"
        self.extraction: dict = {}
        self.schema_overrides: dict = {}
        self.schema_only: set = set()
        self.schema_skip: set = set()

    def discover_volumes(self):
        return [SimpleNamespace(vol=v) for v in self._vols]


@pytest.fixture()
def parsed_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    return tmp_path


def _write_volume(vol: int, n_chapters: int) -> None:
    with paths.parsed_volume(vol).open("w", encoding="utf-8") as fh:
        for ch in range(n_chapters):
            fh.write(json.dumps({"chapter_idx": ch, "seq": 0}) + "\n")


# --- _chapter_count -----------------------------------------------------------


def test_chapter_count_is_zero_when_volume_not_ingested(parsed_dir):
    assert cli._chapter_count(1) == 0


def test_chapter_count_reads_max_chapter_idx_plus_one(parsed_dir):
    _write_volume(1, 3)
    assert cli._chapter_count(1) == 3


# --- _resolve_step_target -------------------------------------------------------


def test_bootstrap_targets_first_chapter_of_first_volume(parsed_dir):
    settings = _FakeSettings([1, 2])
    target = cli._resolve_step_target(settings, None, do_continue=False, redo=False)
    assert target == (1, 0)


def test_no_volumes_returns_none(parsed_dir):
    settings = _FakeSettings([])
    assert cli._resolve_step_target(settings, None, do_continue=False, redo=False) is None


def test_bare_repeat_with_existing_progress_is_blocked(parsed_dir):
    settings = _FakeSettings([1, 2])
    progress = {"vol": 1, "chapter_idx": 0}
    with pytest.raises(cli.StepBlocked):
        cli._resolve_step_target(settings, progress, do_continue=False, redo=False)


def test_redo_repeats_last_completed_without_continue(parsed_dir):
    settings = _FakeSettings([1, 2])
    progress = {"vol": 1, "chapter_idx": 0}
    target = cli._resolve_step_target(settings, progress, do_continue=False, redo=True)
    assert target == (1, 0)


def test_continue_advances_within_same_volume(parsed_dir):
    _write_volume(1, 3)  # chapters 0, 1, 2
    settings = _FakeSettings([1, 2])
    progress = {"vol": 1, "chapter_idx": 0}
    target = cli._resolve_step_target(settings, progress, do_continue=True, redo=False)
    assert target == (1, 1)


def test_continue_advances_to_next_volume_when_current_finished(parsed_dir):
    _write_volume(1, 2)  # chapters 0, 1 -- chapter 1 is the last one
    settings = _FakeSettings([1, 2])
    progress = {"vol": 1, "chapter_idx": 1}
    target = cli._resolve_step_target(settings, progress, do_continue=True, redo=False)
    assert target == (2, 0)


def test_series_done_at_last_chapter_of_last_volume(parsed_dir):
    _write_volume(2, 1)  # a single chapter, 0 -- the last one
    settings = _FakeSettings([1, 2])
    progress = {"vol": 2, "chapter_idx": 0}
    target = cli._resolve_step_target(settings, progress, do_continue=True, redo=False)
    assert target is None


# --- Phase 12: `wiki step` owns its own run (manifest, HTML audit, touched-page extras) --------


@pytest.fixture()
def stub_stage_commands(monkeypatch):
    """The delegated stage commands, replaced with no-ops that just record the call order --
    the same pattern tests/test_run_all_guard.py uses for `run_all`'s. Phase 18 added `scenes`
    and a `gazetteer(..., merge_epithets=True)` call between `ingest` and `extract`. Phase 19
    adds `events_build` after `graph_build`."""
    calls: list[str] = []
    for name in ("ingest", "scenes", "gazetteer", "extract", "graph_build", "events_build", "synthesize", "site_build"):
        monkeypatch.setattr(cli, name, lambda *a, __n=name, **k: calls.append(__n))
    return calls


@pytest.fixture()
def isolated_step(tmp_path, monkeypatch):
    """Point every path `step()` (and the audit reports it runs) can touch at a scratch
    directory, and give `_settings` a fake with exactly one volume -- `_resolve_step_target`
    then bootstraps to (1, 0) since data/01_parsed/ is empty."""
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "01_parsed")
    monkeypatch.setattr(paths, "CLAIMS_DIR", tmp_path / "03_claims")
    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path / "04_graph")
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeSettings([1]))
    return tmp_path


def test_step_success_creates_and_finishes_its_own_run(stub_stage_commands, isolated_step):
    cli.step(series=None, do_continue=False, redo=False, model=None)

    step_manifests = [m for m in provenance.list_runs() if m["command"] == "step"]
    assert len(step_manifests) == 1
    m = step_manifests[0]
    assert m["outcome"] == "ok"
    assert m["scope"] == "v01c0"
    assert m["vol"] == 1
    assert m["chapter_idx"] == 0
    assert m["touched_pages"] == []  # no claims file on disk -> nothing touched this chapter
    assert stub_stage_commands == [
        "ingest", "scenes", "gazetteer", "extract", "graph_build", "events_build", "synthesize", "site_build",
    ]
    assert provenance.load_step_progress() == {"vol": 1, "chapter_idx": 0}


def test_step_never_snapshots_a_stage_dir_itself(stub_stage_commands, isolated_step):
    """Each delegated stage command already snapshots its own stage dir before writing --
    `step()`'s own wrapping run must not ALSO snapshot (that would be a redundant, pointless
    copy, since `step()` itself never writes to a stage dir directly)."""
    cli.step(series=None, do_continue=False, redo=False, model=None)
    m = next(m for m in provenance.list_runs() if m["command"] == "step")
    assert m.get("snapshotted_stages", []) == []


def test_step_failure_finishes_the_run_as_failed_and_does_not_advance_progress(isolated_step, monkeypatch):
    monkeypatch.setattr(cli, "ingest", lambda *a, **k: None)
    monkeypatch.setattr(cli, "scenes", lambda *a, **k: None)
    monkeypatch.setattr(cli, "gazetteer", lambda *a, **k: None)

    def _boom(*a, **k):
        raise typer.Exit(code=1)

    monkeypatch.setattr(cli, "extract", _boom)

    with pytest.raises(typer.Exit):
        cli.step(series=None, do_continue=False, redo=False, model=None)

    step_manifests = [m for m in provenance.list_runs() if m["command"] == "step"]
    assert len(step_manifests) == 1
    assert step_manifests[0]["outcome"] == "failed"
    assert provenance.load_step_progress() is None
