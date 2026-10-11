"""Phase 12: `wiki trace <name>` — end-to-end provenance for one character, cutting across the
raw claim files, page files, the site bundle, AND every run's `calls.jsonl` (not just the latest
one, which is all `wiki calls --grep` can see). See docs/handover/PHASE_11.md's "What Phase 12
needs" #4.
"""

from __future__ import annotations

import json

import pytest
from rich.console import Console

from narrativewiki import cli, paths, provenance


class _FakeSettings:
    series_id = "test"
    extraction: dict = {}
    schema_overrides: dict = {}
    schema_only: set = set()
    schema_skip: set = set()


@pytest.fixture()
def traced_entity(tmp_path, monkeypatch):
    entities_dir = tmp_path / "02_entities"
    claims_dir = tmp_path / "03_claims"
    pages_dir = tmp_path / "05_pages"
    bundle_dir = tmp_path / "06_bundle"
    runs_dir = tmp_path / "_runs"
    for d in (entities_dir, claims_dir, pages_dir, bundle_dir, runs_dir):
        d.mkdir(parents=True)

    monkeypatch.setattr(paths, "ENTITIES_DIR", entities_dir)
    monkeypatch.setattr(paths, "CLAIMS_DIR", claims_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", pages_dir)
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    monkeypatch.setattr(paths, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(paths, "gazetteer", lambda: entities_dir / "gazetteer.json")
    monkeypatch.setattr(paths, "bundle_links", lambda: bundle_dir / "links.json")
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeSettings())

    gaz = {
        "entities": [
            {
                "entity_id": "holo", "canonical": "Holo", "type": "CHARACTER",
                "aliases": ["Wisewolf"], "first_vol": 1, "confidence": 0.9,
                "mention_count": 10, "importance": 0.5,
                "surface_forms": [{"ambiguous": False}], "notes": "",
            }
        ]
    }
    (entities_dir / "gazetteer.json").write_text(json.dumps(gaz), encoding="utf-8")

    claim = {
        "claim_id": "c1", "subject": "holo", "predicate": "AGE", "kind": "attribute",
        "object": None, "value": "600", "qualifier": None, "first_vol": 1, "chapter_idx": 0,
        "evidence": [{"para_id": "v01:c00:p0001", "print_page": 1, "quote": "six hundred years old"}],
        "confidence": 0.9, "polarity": "asserted", "source": "test",
    }
    (claims_dir / "v01.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")

    (pages_dir / "holo").mkdir()
    (pages_dir / "holo" / "v01.json").write_text("{}", encoding="utf-8")

    (bundle_dir / "links.json").write_text(
        json.dumps({"holo": {"route": "/character/holo"}}), encoding="utf-8"
    )

    run = provenance.start_run(
        "test", "extract", scope="v1", volumes=[1], volume_scope=1, settings=_FakeSettings()
    )
    run.log_call({"stage": "claim_extract", "prompt": "Tell me about Holo", "response": "she is 600"})
    run.finish("ok")

    rec_console = Console(record=True, width=200)
    monkeypatch.setattr(cli, "console", rec_console)
    return rec_console, run.run_id


def test_trace_reports_the_raw_claim_page_files_url_and_cross_run_calls(traced_entity):
    rec_console, run_id = traced_entity

    cli.trace(name="Holo", series=None, calls_limit=5)

    out = rec_console.export_text()
    assert "Holo" in out and "holo" in out
    assert "AGE" in out and "600" in out
    assert "v01" in out
    assert "six hundred years old" in out
    assert "Page files" in out
    assert "/character/holo" in out
    assert run_id in out


def test_trace_resolves_by_alias_too(traced_entity):
    rec_console, _ = traced_entity
    cli.trace(name="Wisewolf", series=None, calls_limit=5)
    assert "AGE" in rec_console.export_text()


def test_trace_handles_an_entity_with_no_claims_or_calls_yet(tmp_path, monkeypatch):
    entities_dir = tmp_path / "02_entities"
    entities_dir.mkdir()
    claims_dir = tmp_path / "03_claims"
    claims_dir.mkdir()
    runs_dir = tmp_path / "_runs"
    runs_dir.mkdir()
    monkeypatch.setattr(paths, "ENTITIES_DIR", entities_dir)
    monkeypatch.setattr(paths, "CLAIMS_DIR", claims_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "05_pages")
    monkeypatch.setattr(paths, "BUNDLE_DIR", tmp_path / "06_bundle")
    monkeypatch.setattr(paths, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(paths, "gazetteer", lambda: entities_dir / "gazetteer.json")
    monkeypatch.setattr(paths, "bundle_links", lambda: tmp_path / "06_bundle" / "links.json")
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeSettings())

    gaz = {
        "entities": [
            {
                "entity_id": "lawrence", "canonical": "Lawrence", "type": "CHARACTER",
                "aliases": [], "first_vol": 1, "confidence": 0.9,
                "mention_count": 5, "importance": 0.4,
                "surface_forms": [{"ambiguous": False}], "notes": "",
            }
        ]
    }
    (entities_dir / "gazetteer.json").write_text(json.dumps(gaz), encoding="utf-8")

    rec_console = Console(record=True, width=200)
    monkeypatch.setattr(cli, "console", rec_console)

    cli.trace(name="Lawrence", series=None, calls_limit=5)  # must not raise

    out = rec_console.export_text()
    assert "No raw claims found" in out
    assert "No page files written yet" in out
    assert "No LLM calls found" in out
