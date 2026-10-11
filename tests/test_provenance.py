"""Phase 10: the run ledger — manifest, per-call log, and pre-run snapshot/rollback.

These are the tests that matter for the user's operating rules: every model call must be
traceable back to its prompt and a timestamp (`log_call`/`read_calls`), and a run that wrote bad
output must be undoable (`snapshot_before`/`restore`) without touching anything it didn't write.
"""

from __future__ import annotations

import json

import pytest

from narrativewiki import paths, provenance


@pytest.fixture()
def isolated_runs(tmp_path, monkeypatch):
    """Point paths.RUNS_DIR (and, where a test needs it, a stage dir) at a scratch directory --
    the same monkeypatch.setattr(paths, ...) pattern tests/test_audit_reports.py already uses."""
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    return tmp_path


# --- start_run / manifest ---------------------------------------------------


def test_start_run_writes_a_readable_manifest(isolated_runs):
    run = provenance.start_run(
        "86", "extract", scope="v1-2", volumes=[1, 2], volume_scope=2, argv=["wiki", "extract"],
    )
    assert run.manifest_path.is_file()
    on_disk = json.loads(run.manifest_path.read_text(encoding="utf-8"))
    assert on_disk["command"] == "extract"
    assert on_disk["series_id"] == "86"
    assert on_disk["scope"] == "v1-2"
    assert on_disk["volumes"] == [1, 2]
    assert on_disk["volume_scope"] == 2
    assert on_disk["outcome"] == "running"
    assert on_disk["finished_ts"] is None
    assert run.run_id in run.dir.name
    assert "extract" in run.run_id


def test_run_id_disambiguates_on_collision(isolated_runs):
    a = provenance.start_run("86", "extract", scope="v1")
    b = provenance.start_run("86", "extract", scope="v1")
    assert a.run_id != b.run_id
    assert a.dir.is_dir() and b.dir.is_dir()


# --- extraction taxonomy hash reflects the MERGED, effective schema --------


def test_config_hash_changes_when_settings_schema_overrides_differ(isolated_runs):
    """Two runs with the same on-disk config but different `--attr`/`--only` overrides must get
    different manifest `extraction` hashes -- otherwise `wiki runs` can't answer "which schema
    produced this claim set" (VISION.md 2026-09-04)."""
    from narrativewiki.config import Settings, apply_schema_overrides

    plain = Settings(series_id="86", series={}, models={}, extraction={"attributes": {"AGE": {}}})
    widened = Settings(series_id="86", series={}, models={}, extraction={"attributes": {"AGE": {}}})
    apply_schema_overrides(widened, attrs=['KARMA=short_text:"Karma"'])

    a = provenance.start_run("86", "extract", scope="v1", settings=plain)
    b = provenance.start_run("86", "extract", scope="v2", settings=widened)
    assert a.manifest["config_hashes"]["extraction"] != b.manifest["config_hashes"]["extraction"]


def test_config_hash_stable_for_identical_settings(isolated_runs):
    from narrativewiki.config import Settings

    settings = Settings(series_id="86", series={}, models={}, extraction={"attributes": {"AGE": {}}})
    a = provenance.start_run("86", "extract", scope="v1", settings=settings)
    b = provenance.start_run("86", "extract", scope="v2", settings=settings)
    assert a.manifest["config_hashes"]["extraction"] == b.manifest["config_hashes"]["extraction"]


def test_config_hash_falls_back_to_disk_settings_when_none_given(isolated_runs):
    """`settings=` is optional -- a caller with none in hand still gets a real hash, loaded fresh
    from the on-disk config (used implicitly by every pre-Phase-10.5 call site until threaded
    through)."""
    run = provenance.start_run("86", "extract", scope="v1")
    assert run.manifest["config_hashes"]["extraction"]


# --- calls.jsonl -------------------------------------------------------------


def test_log_call_appends_and_frontier_call_count_filters_by_tier(isolated_runs):
    run = provenance.start_run("86", "synthesize", scope="upto2")
    run.log_call({"stage": "prose", "tier": "standard", "prompt": "a", "response": "b"})
    run.log_call({"stage": "outline", "tier": "frontier", "prompt": "c", "response": "d"})
    run.log_call({"stage": "outline", "tier": "frontier", "prompt": "e", "response": "f"})

    assert run.frontier_call_count() == 2
    records = provenance.read_calls(run.run_id)
    assert len(records) == 3


def test_read_calls_filters_by_stage_and_grep(isolated_runs):
    run = provenance.start_run("86", "synthesize", scope="upto2")
    run.log_call({"stage": "prose", "prompt": "tell me about Holo", "response": "she is a wolf"})
    run.log_call({"stage": "codex_summary", "prompt": "define Yoitsu", "response": "a forest"})

    prose_only = provenance.read_calls(run.run_id, stage="prose")
    assert len(prose_only) == 1
    assert prose_only[0]["stage"] == "prose"

    holo_only = provenance.read_calls(run.run_id, grep="wolf")
    assert len(holo_only) == 1
    assert "wolf" in holo_only[0]["response"]

    assert provenance.read_calls(run.run_id, grep="nonexistent-text") == []


def test_read_calls_on_a_run_with_no_calls_returns_empty(isolated_runs):
    run = provenance.start_run("86", "graph_build", scope="v1-2")
    assert provenance.read_calls(run.run_id) == []


# --- finish() ----------------------------------------------------------------


def test_finish_is_idempotent(isolated_runs):
    run = provenance.start_run("86", "extract", scope="v1")
    run.finish("ok")
    first_ts = run.manifest["finished_ts"]
    assert run.manifest["outcome"] == "ok"

    run.finish("failed", error="should not overwrite")
    assert run.manifest["outcome"] == "ok"
    assert run.manifest["finished_ts"] == first_ts
    assert "error" not in run.manifest


def test_finish_persists_the_outcome_to_disk(isolated_runs):
    run = provenance.start_run("86", "extract", scope="v1")
    run.finish("failed", error="LLMError: boom")
    on_disk = json.loads(run.manifest_path.read_text(encoding="utf-8"))
    assert on_disk["outcome"] == "failed"
    assert on_disk["error"] == "LLMError: boom"
    assert on_disk["finished_ts"] is not None


# --- snapshot / rollback -------------------------------------------------------


def test_snapshot_before_and_restore_round_trip(isolated_runs, monkeypatch):
    claims_dir = isolated_runs / "data" / "03_claims"
    claims_dir.mkdir(parents=True)
    (claims_dir / "v01.jsonl").write_text("original content\n", encoding="utf-8")
    monkeypatch.setattr(paths, "STAGE_DIRS", {"claims": claims_dir})

    run = provenance.start_run("86", "extract", scope="v1", stage_keys=["claims"])
    assert run.manifest["snapshotted_stages"] == ["claims"]

    # Simulate the stage doing its (bad) work: overwrite the live file.
    (claims_dir / "v01.jsonl").write_text("bad new content\n", encoding="utf-8")
    assert (claims_dir / "v01.jsonl").read_text(encoding="utf-8") == "bad new content\n"

    restored = run.restore()
    assert restored == ["claims"]
    assert (claims_dir / "v01.jsonl").read_text(encoding="utf-8") == "original content\n"


def test_snapshot_before_skips_a_missing_or_empty_stage_dir(isolated_runs, monkeypatch):
    """A first-ever run has nothing to protect yet -- this must not raise or fabricate a
    snapshot of a directory that does not exist."""
    empty_dir = isolated_runs / "data" / "03_claims"
    monkeypatch.setattr(paths, "STAGE_DIRS", {"claims": empty_dir})

    run = provenance.start_run("86", "extract", scope="v1", stage_keys=["claims"])
    assert run.manifest["snapshotted_stages"] == []
    assert run.restore() == []


def test_rollback_only_touches_snapshotted_stages(isolated_runs, monkeypatch):
    """A run that only wrote to `claims` must never touch `pages` on rollback, even if `pages`
    also exists on disk -- rollback must be scoped to exactly what this run snapshotted."""
    claims_dir = isolated_runs / "data" / "03_claims"
    pages_dir = isolated_runs / "data" / "05_pages"
    claims_dir.mkdir(parents=True)
    pages_dir.mkdir(parents=True)
    (claims_dir / "v01.jsonl").write_text("claims v1\n", encoding="utf-8")
    (pages_dir / "holo.json").write_text("page v1\n", encoding="utf-8")
    monkeypatch.setattr(paths, "STAGE_DIRS", {"claims": claims_dir, "pages": pages_dir})

    run = provenance.start_run("86", "extract", scope="v1", stage_keys=["claims"])
    (pages_dir / "holo.json").write_text("page v2 -- unrelated later change\n", encoding="utf-8")

    run.restore()
    assert (pages_dir / "holo.json").read_text(encoding="utf-8") == "page v2 -- unrelated later change\n"



def test_a_rolled_back_failed_run_no_longer_blocks_its_stage(isolated_runs, monkeypatch):
    """[30] Rolling back a failed run restores the stage, so the failure no longer speaks for it."""
    claims_dir = isolated_runs / "data" / "03_claims"
    claims_dir.mkdir(parents=True)
    (claims_dir / "v01.jsonl").write_text("claims v1", encoding="utf-8")
    monkeypatch.setattr(paths, "STAGE_DIRS", {"claims": claims_dir})

    run = provenance.start_run("86", "extract", scope="v1", stage_keys=["claims"])
    run.finish("failed", error="cache miss")
    assert [m["run_id"] for m in provenance.failed_stage_artifacts(["claims"])] == [run.run_id]

    run.restore()
    assert provenance.failed_stage_artifacts(["claims"]) == []

# --- listing / lookup ----------------------------------------------------------


def test_list_runs_is_newest_first(isolated_runs, monkeypatch):
    """Two runs a few seconds apart, with controlled clock -- real wall-clock speed could put
    both start_run calls in the same second, which would make this test's outcome depend on
    string-comparing the scope slug rather than on chronological order."""
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    times = iter([base, base + timedelta(seconds=5)])
    monkeypatch.setattr(provenance, "_now", lambda: next(times))

    a = provenance.start_run("86", "extract", scope="v1")
    b = provenance.start_run("86", "extract", scope="v2")
    manifests = provenance.list_runs()
    ids = [m["run_id"] for m in manifests]
    assert ids.index(b.run_id) < ids.index(a.run_id)
    assert provenance.latest_run_id() == b.run_id


def test_get_run_roundtrips_the_manifest(isolated_runs):
    run = provenance.start_run("86", "extract", scope="v1", volumes=[1])
    fetched = provenance.get_run(run.run_id)
    assert fetched.manifest["scope"] == "v1"
    assert fetched.manifest["volumes"] == [1]


def test_get_run_rejects_an_unknown_id(isolated_runs):
    with pytest.raises(provenance.ProvenanceError):
        provenance.get_run("no-such-run")


def test_list_runs_with_no_runs_dir_returns_empty(isolated_runs):
    assert provenance.list_runs() == []
    assert provenance.latest_run_id() is None


def test_list_runs_orders_same_second_scopes_by_precise_start(isolated_runs, monkeypatch):
    from datetime import datetime, timezone

    ticks = iter([datetime(2026, 9, 15, 12, 0, 0, 100, tzinfo=timezone.utc),
                  datetime(2026, 9, 15, 12, 0, 0, 200, tzinfo=timezone.utc)])
    monkeypatch.setattr(provenance, "_now", lambda: next(ticks))
    first = provenance.start_run("spice-and-wolf", "probe", scope="z-first")
    second = provenance.start_run("spice-and-wolf", "probe", scope="a-second")
    assert first.manifest["started_ts"].endswith(".000100+00:00")
    assert [m["run_id"] for m in provenance.list_runs()] == [second.run_id, first.run_id]
    assert provenance.list_runs(limit=1)[0]["run_id"] == second.run_id
    assert provenance.last_run_for_stage("probe")["run_id"] == second.run_id


def test_list_runs_numeric_collision_suffixes_sort_naturally(isolated_runs, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(provenance, "_now", lambda: datetime(2026, 9, 15, tzinfo=timezone.utc))
    runs = [provenance.start_run("spice-and-wolf", "probe", scope="v1-2") for _ in range(11)]
    assert [m["run_id"] for m in provenance.list_runs()] == [r.run_id for r in reversed(runs)]


def test_list_runs_handles_legacy_and_missing_start_timestamps(isolated_runs):
    paths.RUNS_DIR.mkdir()
    records = [
        ("20260915T010000-probe-a", "2026-09-15T07:00:00+06:00"),
        ("20260915T003000-probe-b", "2026-09-15T01:30:00Z"),
        ("20260915T020000-probe-c", None),
        ("20260915T030000-probe-d", "broken"),
    ]
    for run_id, started in records:
        folder = paths.run_dir(run_id)
        folder.mkdir()
        (folder / "manifest.json").write_text(json.dumps({"run_id": run_id, "started_ts": started}), encoding="utf-8")
    assert [m["run_id"] for m in provenance.list_runs()] == [r[0] for r in reversed(records)]
