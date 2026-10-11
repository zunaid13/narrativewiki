"""TASK-0004's reproducible comparison must never publish mixed or failed inputs."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from narrativewiki import paths
from narrativewiki.entities.candidates import mine_candidates

_spec = importlib.util.spec_from_file_location(
    "gate_comparison_option_a",
    Path(__file__).resolve().parents[1] / "scripts/probe/gate_comparison_option_a.py",
)
comparison = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comparison)


@pytest.fixture()
def comparison_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(paths, "DOCS_DIR", tmp_path / "docs")
    paths.set_active_series(comparison.SERIES)
    series_config = {"entities": {"max_candidates_per_volume": 400}}
    loaded_series = []

    def load_settings(series_id):
        loaded_series.append(series_id)
        return SimpleNamespace(series=series_config)

    monkeypatch.setattr(comparison.config, "load_settings", load_settings)
    volumes = {}
    for vol, count in ((1, 2), (2, 3)):
        volumes[vol] = [
            {"para_id": f"v{vol:02d}:c01:p{i:04d}", "vol": vol,
             "text": "Rare Person walked in.", "speech": "narration"}
            for i in range(count)
        ]
        parsed = paths.parsed_volume(vol)
        parsed.parent.mkdir(parents=True, exist_ok=True)
        parsed.write_text("".join(json.dumps(r) + "\n" for r in volumes[vol]), encoding="utf-8")
    for cutoff in (None, 1, 2):
        paths.set_build_cutoff(cutoff)
        paths.ENTITIES_DIR.mkdir(parents=True, exist_ok=True)
        scope = {v: rs for v, rs in volumes.items() if v <= (cutoff or 2)}
        candidates = mine_candidates(scope, series_config)
        gazetteer = {
            "volumes_covered": list(scope),
            "entities": [
                {"entity_id": "rare-person", "first_vol": 1,
                 "surface_forms": [{"text": "Rare Person", "first_vol": 1}]}
            ] if candidates else [],
        }
        paths.gazetteer().write_text(json.dumps(gazetteer), encoding="utf-8")
        paths.candidates().write_text(
            "".join(json.dumps(c) + "\n" for c in candidates), encoding="utf-8"
        )
        manifest = paths.run_dir(f"gazetteer-{cutoff}") / "manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({
            "run_id": manifest.parent.name, "command": "gazetteer",
            "outcome": "ok", "build_cutoff": cutoff,
            "volumes": list(scope), "snapshotted_stages": ["gazetteer"],
            "started_ts": "2026-09-16T00:00:00+00:00",
        }), encoding="utf-8")
    paths.set_build_cutoff(None)
    output = paths.DOCS_DIR / "probe/gate_comparison_spice-and-wolf.jsonl"
    output.parent.mkdir(parents=True)
    output.write_text("previous result\n", encoding="utf-8")
    yield output, loaded_series
    paths.set_active_series(None)


def test_comparison_uses_explicit_series_and_each_cutoff(comparison_inputs):
    output, loaded_series = comparison_inputs
    comparison.main()
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert loaded_series == ["spice-and-wolf"]
    assert [(r["upto_vol"], r["gate"]) for r in rows] == [
        (1, "render"), (1, "build"), (2, "render"), (2, "build")
    ]
    assert rows[0]["surfaces_missing_at_cutoff"] == ["Rare Person"]
    assert all(r["leak_rate"] == 0 for r in rows[1:])
    assert all(r["series"] == "spice-and-wolf" for r in rows)
    assert paths.build_cutoff() is None


@pytest.mark.parametrize("defect", ["stale", "wrong_scope", "failed_run", "missing"])
def test_comparison_preserves_previous_report_on_invalid_inputs(comparison_inputs, defect):
    output, _ = comparison_inputs
    paths.set_build_cutoff(2)
    if defect == "stale":
        candidates = [json.loads(l) for l in paths.candidates().read_text(encoding="utf-8").splitlines()]
        candidates[0]["first_vol"] = 2  # Same surfaces/count; provenance is still stale.
        paths.candidates().write_text(
            "".join(json.dumps(c) + "\n" for c in candidates), encoding="utf-8"
        )
    elif defect == "wrong_scope":
        gazetteer = json.loads(paths.gazetteer().read_text(encoding="utf-8"))
        gazetteer["volumes_covered"] = [1]
        paths.gazetteer().write_text(json.dumps(gazetteer), encoding="utf-8")
    elif defect == "failed_run":
        manifest = paths.run_dir("gazetteer-2") / "manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["outcome"] = "failed"
        manifest.write_text(json.dumps(data), encoding="utf-8")
    else:
        paths.candidates().unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        comparison.main()
    assert output.read_text(encoding="utf-8") == "previous result\n"
    assert paths.build_cutoff() is None
