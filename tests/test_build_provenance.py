"""Build-cutoff snapshots, rollback isolation, and failed-stage provenance."""

import json

import pytest
import typer

from narrativewiki import cli, paths, provenance
from narrativewiki.config import Settings


@pytest.fixture()
def isolated_series(tmp_path, monkeypatch):
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(paths, "PROJECT_ROOT", tmp_path)
            paths.set_active_series("spice-and-wolf")
            paths.ensure_dirs()
            yield
    finally:
        paths.set_active_series(None)


def _settings():
    return Settings(series_id="spice-and-wolf", series={}, models={}, extraction={})


@pytest.mark.parametrize("cutoff", [None, 1])
def test_failed_gazetteer_build_snapshots_candidates_before_replacing_them(isolated_series, monkeypatch, cutoff):
    from narrativewiki.entities import classify
    from narrativewiki.llm import client

    paths.set_build_cutoff(cutoff)
    paths.ensure_dirs()
    original = b'{"surface":"Original Person"}\n'
    paths.candidates().write_bytes(original)
    paths.gazetteer().write_text('{"entities":[]}', encoding="utf-8")
    paths.surface_forms().write_text("original vocabulary\n", encoding="utf-8")
    paths.parsed_volume(1).write_text(json.dumps({
        "vol": 1, "para_id": "v01:c00:p0000", "text": "New Person spoke.", "speech": "narration",
    }), encoding="utf-8")
    settings = _settings()
    monkeypatch.setattr(settings, "resolve_role", lambda stage: "fixture")
    monkeypatch.setattr(client, "LLMClient", lambda *args, **kwargs: object())

    def fail(*args, **kwargs):
        raise client.LLMError("classification failed")

    monkeypatch.setattr(classify, "classify_candidates", fail)
    with pytest.raises(typer.Exit):
        cli._build_gazetteer_for_volumes(settings, [1], min_mentions=1, force=True)
    manifest = provenance.last_run_for_stage("gazetteer")
    assert manifest["outcome"] == "failed"
    assert manifest["build_cutoff"] == cutoff
    run = provenance.get_run(manifest["run_id"])
    assert (run.outputs_dir / "gazetteer" / "candidates.jsonl").read_bytes() == original
    assert paths.candidates().read_bytes() != original
    assert run.restore() == ["gazetteer"]
    assert paths.candidates().read_bytes() == original
    assert paths.surface_forms().read_text(encoding="utf-8") == "original vocabulary\n"


@pytest.mark.parametrize("cutoff", [None, 1, 2])
def test_gazetteer_build_exports_vocabulary_in_its_own_scope(isolated_series, monkeypatch, cutoff):
    from narrativewiki.entities import alias, classify
    from narrativewiki.llm import client

    paths.set_build_cutoff(cutoff)
    paths.ensure_dirs()
    paths.parsed_volume(1).write_text(json.dumps({
        "vol": 1, "para_id": "v01:c00:p0000", "text": "Holo spoke.", "speech": "narration",
    }), encoding="utf-8")
    settings = _settings()
    monkeypatch.setattr(settings, "resolve_role", lambda stage: "fixture")
    monkeypatch.setattr(client, "LLMClient", lambda *args, **kwargs: object())
    monkeypatch.setattr(classify, "classify_candidates", lambda *args, **kwargs: [])
    entity = {"entity_id": "holo", "mention_count": 1, "surface_forms": [
        {"text": "Holo", "first_vol": 1, "ambiguous": False, "source": "corpus"}
    ]}
    monkeypatch.setattr(alias, "cluster_candidates", lambda *args, **kwargs: [entity])
    assert cli._build_gazetteer_for_volumes(settings, [1], min_mentions=1, force=True)
    row = json.loads(paths.surface_forms().read_text(encoding="utf-8"))
    assert row["entity_id"] == "holo" and row["indexed"] is True
    assert paths.surface_forms().parent == paths.gazetteer().parent
    assert provenance.last_run_for_stage("gazetteer")["outcome"] == "ok"
    if cutoff is not None:
        exported = paths.surface_forms()
        paths.set_build_cutoff(None)
        assert paths.surface_forms() != exported
        assert not paths.surface_forms().exists()


def test_epithet_merge_refreshes_surface_inventory(isolated_series):
    entity = {"entity_id": "holo", "first_vol": 1, "aliases": [], "surface_forms": [
        {"text": "Holo", "first_vol": 1, "ambiguous": False}
    ]}
    paths.gazetteer().write_text(json.dumps({"entities": [entity]}), encoding="utf-8")
    paths.scene_epithets(1).write_text(json.dumps({
        "entity_id": "holo", "text": "the Wisewolf", "vol": 1, "confidence": 0.9,
    }), encoding="utf-8")
    cli._merge_epithets_into_gazetteer(_settings(), [1])
    rows = [json.loads(line) for line in paths.surface_forms().read_text(encoding="utf-8").splitlines()]
    assert [(r["text"], r["source"]) for r in rows] == [
        ("Holo", "unknown"), ("the Wisewolf", "epithet_mining")
    ]


def test_cutoff_rollback_restores_recorded_scope_without_touching_render_or_other_cutoff(isolated_series):
    render = paths.claims_volume(1)
    render.write_text("render", encoding="utf-8")
    paths.set_build_cutoff(1)
    paths.ensure_dirs()
    cutoff_one = paths.claims_volume(1)
    cutoff_one.write_text("before", encoding="utf-8")
    run = provenance.start_run("spice-and-wolf", "extract", scope="v1", stage_keys=["claims"], settings=_settings())
    cutoff_one.write_text("after", encoding="utf-8")
    paths.set_build_cutoff(2)
    paths.ensure_dirs()
    cutoff_two = paths.claims_volume(1)
    cutoff_two.write_text("other cutoff", encoding="utf-8")
    assert provenance.get_run(run.run_id).restore() == ["claims"]
    assert cutoff_one.read_text() == "before"
    assert cutoff_two.read_text() == "other cutoff"
    assert render.read_text() == "render"
    assert paths.build_cutoff() == 2
    assert paths.STAGE_DIRS["claims"] == cutoff_two.parent


def test_cutoff_restore_resets_active_scope_when_copy_fails(isolated_series, monkeypatch):
    paths.set_build_cutoff(1)
    paths.ensure_dirs()
    paths.claims_volume(1).write_text("before", encoding="utf-8")
    run = provenance.start_run("spice-and-wolf", "extract", scope="v1", stage_keys=["claims"], settings=_settings())
    paths.set_build_cutoff(None)

    def fail(*args):
        raise OSError("cannot copy")

    monkeypatch.setattr(provenance, "_copy_tree", fail)
    with pytest.raises(OSError, match="cannot copy"):
        run.restore()
    assert paths.build_cutoff() is None
    assert paths.STAGE_DIRS["claims"] == paths.DATA_DIR / "03_claims"


def test_failed_writer_lookup_is_isolated_by_build_cutoff(isolated_series):
    render = provenance.start_run("spice-and-wolf", "extract", scope="v1", settings=_settings())
    render.finish("ok")
    paths.set_build_cutoff(1)
    build = provenance.start_run("spice-and-wolf", "extract", scope="v1", settings=_settings())
    build.finish("failed")
    assert provenance.failed_stage_artifacts(["claims"])[0]["run_id"] == build.run_id
    paths.set_build_cutoff(2)
    assert provenance.failed_stage_artifacts(["claims"]) == []
    paths.set_build_cutoff(None)
    assert provenance.last_run_for_stage("claims")["run_id"] == render.run_id
    assert provenance.failed_stage_artifacts(["claims"]) == []


@pytest.mark.parametrize("failed_cutoff", [None, 1])
def test_build_extraction_checks_its_own_gazetteer_failure(isolated_series, monkeypatch, failed_cutoff):
    settings = _settings()
    monkeypatch.setattr(settings, "volume_numbers", lambda: [1])
    monkeypatch.setattr(cli, "_settings", lambda *args, **kwargs: settings)
    paths.parsed_volume(1).write_text("", encoding="utf-8")
    paths.set_build_cutoff(failed_cutoff)
    failed = provenance.start_run("spice-and-wolf", "gazetteer", scope="v1", settings=settings)
    failed.finish("failed")
    paths.set_build_cutoff(1)
    paths.ensure_dirs()
    paths.gazetteer().write_text('{"entities":[]}', encoding="utf-8")
    paths.mentions().write_text("", encoding="utf-8")
    paths.set_build_cutoff(None)
    calls = []
    monkeypatch.setattr(cli, "_extract_claims_for_volumes", lambda *args: calls.append(paths.build_cutoff()))
    if failed_cutoff == 1:
        with pytest.raises(typer.Exit):
            cli.extract(series="spice-and-wolf", gate="build", volumes="1")
        assert calls == []
    else:
        cli.extract(series="spice-and-wolf", gate="build", volumes="1")
        assert calls == [1]
    assert paths.build_cutoff() is None
