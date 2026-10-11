"""Phase 12: audit reports return an OK/FAIL verdict, `wiki audit <stage>` saves a self-contained
HTML copy into the current run's `_runs/<run_id>/audit/`, `wiki audit run <run_id>` builds an
index of one run, and a real FAIL now exits non-zero (was always exit 0 before this phase).
"""

from __future__ import annotations

import json

import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from narrativewiki import cli, paths, provenance
from narrativewiki.audit import reports
from narrativewiki.config import Settings


def _settings() -> Settings:
    return Settings(series_id="test", series={}, models={}, extraction={})


# --- reports.py now returns True (OK) / False (FAIL) ---------------------------------------


@pytest.fixture()
def bundle_dir(tmp_path, monkeypatch):
    d = tmp_path / "06_bundle"
    (d / "pages").mkdir(parents=True)
    (d / "codex").mkdir(parents=True)
    (d / "timeline").mkdir(parents=True)
    monkeypatch.setattr(paths, "BUNDLE_DIR", d)
    monkeypatch.setattr(paths, "bundle_links", lambda: d / "links.json")
    monkeypatch.setattr(paths, "bundle_index", lambda: d / "index.json")
    monkeypatch.setattr(paths, "bundle_codex", lambda kind: d / "codex" / f"{kind}.json")
    # [29] `reports.run("links")` also walks the emitted Markdown tree at `paths.SITE_DIR`.
    # Unpatched, that is the repo's real `dist/wiki` -- which is gitignored, so any test that
    # forgets to redirect SITE_DIR leaves a half-built tree there and every test in this file
    # fails afterwards on links it never wrote. Point it somewhere empty and per-test.
    monkeypatch.setattr(paths, "SITE_DIR", tmp_path / "wiki")
    return d


def test_links_report_returns_false_and_prints_fail_on_a_broken_reference(bundle_dir):
    (bundle_dir / "links.json").write_text(
        json.dumps({"holo": {"route": "/codex/character#holo"}}), encoding="utf-8"
    )
    (bundle_dir / "pages" / "holo.json").write_text(
        json.dumps(
            {"cutoffs": {"1": {"fields": {"affiliations": [{"entity_id": "no-such-entity"}]}, "prose": {}}}}
        ),
        encoding="utf-8",
    )
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is False
    assert "FAIL" in console.export_text()


def test_links_report_returns_true_when_every_reference_resolves(bundle_dir):
    (bundle_dir / "links.json").write_text(
        json.dumps({"holo": {"route": "/codex/character#holo"}}), encoding="utf-8"
    )
    (bundle_dir / "pages" / "holo.json").write_text(json.dumps({"cutoffs": {}}), encoding="utf-8")
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is True


def test_links_report_fails_on_a_broken_key_event_participant(bundle_dir):
    (bundle_dir / "links.json").write_text(
        json.dumps({"spearhead-squadron": {"route": "/codex/factions#spearhead-squadron"}}), encoding="utf-8"
    )
    (bundle_dir / "codex" / "factions.json").write_text(
        json.dumps(
            {
                "spearhead-squadron": {
                    "first_vol": 1,
                    "kind": "factions",
                    "cutoffs": {
                        "1": {
                            "canonical": "Spearhead Squadron",
                            "summary": None,
                            "evidence": [],
                            "members": [],
                            "related": [],
                            "key_events": [
                                {
                                    "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0,
                                    "location": None, "beat_summary": "...", "quotes": [],
                                    "participants": ["no-such-entity"],
                                }
                            ],
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is False
    assert "FAIL" in console.export_text()


def test_links_report_fails_on_a_key_event_that_exceeds_its_cutoff(bundle_dir):
    (bundle_dir / "links.json").write_text(
        json.dumps({"spearhead-squadron": {"route": "/codex/factions#spearhead-squadron"}}), encoding="utf-8"
    )
    (bundle_dir / "codex" / "factions.json").write_text(
        json.dumps(
            {
                "spearhead-squadron": {
                    "first_vol": 1,
                    "kind": "factions",
                    "cutoffs": {
                        "1": {
                            "canonical": "Spearhead Squadron",
                            "summary": None,
                            "evidence": [],
                            "members": [],
                            "related": [],
                            "key_events": [
                                {
                                    "event_id": "ev_v02c00s000", "vol": 2, "chapter_idx": 0,
                                    "location": None, "beat_summary": "...", "quotes": [],
                                    "participants": [],
                                }
                            ],
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is False
    assert "spoiler-safety violation" in console.export_text()


def _timeline_doc(vol, event_id, event_vol, participants, location=None):
    return {
        "vol": vol,
        "chapters": [
            {
                "chapter_idx": 0,
                "events": [
                    {
                        "event_id": event_id, "vol": event_vol, "location": location,
                        "beat_summary": "...", "participants": participants,
                        "state_changes": [], "quotes": [],
                    }
                ],
            }
        ],
    }


def test_links_report_fails_on_a_broken_timeline_participant(bundle_dir):
    (bundle_dir / "links.json").write_text(json.dumps({}), encoding="utf-8")
    (bundle_dir / "index.json").write_text(json.dumps({"timeline_volumes": [1]}), encoding="utf-8")
    (bundle_dir / "timeline" / "v01.json").write_text(
        json.dumps(_timeline_doc(1, "ev_v01c00s000", 1, ["no-such-entity"])), encoding="utf-8"
    )
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is False
    assert "FAIL" in console.export_text()


def test_links_report_fails_when_an_event_vol_does_not_match_its_timeline_file(bundle_dir):
    (bundle_dir / "links.json").write_text(json.dumps({}), encoding="utf-8")
    (bundle_dir / "index.json").write_text(json.dumps({"timeline_volumes": [1]}), encoding="utf-8")
    (bundle_dir / "timeline" / "v01.json").write_text(
        json.dumps(_timeline_doc(1, "ev_v02c00s000", 2, [])), encoding="utf-8"
    )
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is False
    assert "spoiler-safety violation" in console.export_text()


def test_links_report_fails_when_index_timeline_volumes_disagrees_with_disk(bundle_dir):
    (bundle_dir / "links.json").write_text(json.dumps({}), encoding="utf-8")
    (bundle_dir / "index.json").write_text(json.dumps({"timeline_volumes": [1, 2]}), encoding="utf-8")
    (bundle_dir / "timeline" / "v01.json").write_text(
        json.dumps(_timeline_doc(1, "ev_v01c00s000", 1, [])), encoding="utf-8"
    )
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is False
    assert "timeline_volumes disagrees with disk" in console.export_text()


def test_links_report_ok_with_a_valid_timeline_file(bundle_dir):
    (bundle_dir / "links.json").write_text(
        json.dumps({"holo": {"route": "/character/holo"}}), encoding="utf-8"
    )
    (bundle_dir / "index.json").write_text(json.dumps({"timeline_volumes": [1]}), encoding="utf-8")
    (bundle_dir / "timeline" / "v01.json").write_text(
        json.dumps(_timeline_doc(1, "ev_v01c00s000", 1, ["holo"])), encoding="utf-8"
    )
    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(), console)
    assert ok is True


# --- cli._audit_report: one execution, live print + HTML export -----------------------------


def test_audit_report_writes_a_self_contained_html_copy(bundle_dir, tmp_path):
    (bundle_dir / "links.json").write_text(
        json.dumps({"holo": {"route": "/codex/character#holo"}}), encoding="utf-8"
    )
    (bundle_dir / "pages" / "holo.json").write_text(json.dumps({"cutoffs": {}}), encoding="utf-8")

    html_path = tmp_path / "audit" / "links.html"
    ok = cli._audit_report("links", _settings(), html_path=html_path)
    assert ok is True
    assert html_path.is_file()
    body = html_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in body
    assert "OK" in body


def test_audit_report_with_no_html_path_just_returns_the_verdict(bundle_dir):
    (bundle_dir / "links.json").write_text(json.dumps({}), encoding="utf-8")
    ok = cli._audit_report("links", _settings(), html_path=None)
    assert ok is True


# --- wiki audit <stage> exits non-zero on FAIL ------------------------------------------------


def test_audit_cmd_exits_nonzero_when_report_fails(bundle_dir, monkeypatch):
    monkeypatch.setattr(paths, "RUNS_DIR", bundle_dir.parent / "_runs")
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _settings())
    (bundle_dir / "links.json").write_text(
        json.dumps({"holo": {"route": "/codex/character#holo"}}), encoding="utf-8"
    )
    (bundle_dir / "pages" / "holo.json").write_text(
        json.dumps(
            {"cutoffs": {"1": {"fields": {"affiliations": [{"entity_id": "no-such-entity"}]}, "prose": {}}}}
        ),
        encoding="utf-8",
    )
    with pytest.raises(typer.Exit) as excinfo:
        cli.audit_cmd(stage="links", run_id=None, series=None)
    assert excinfo.value.exit_code == 1


def test_audit_cmd_exits_zero_when_report_passes(bundle_dir, monkeypatch):
    monkeypatch.setattr(paths, "RUNS_DIR", bundle_dir.parent / "_runs")
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _settings())
    (bundle_dir / "links.json").write_text(json.dumps({}), encoding="utf-8")
    cli.audit_cmd(stage="links", run_id=None, series=None)  # must not raise


# --- wiki audit run <run_id> ------------------------------------------------------------------


def test_audit_run_writes_an_index_linking_saved_reports_and_touched_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    run = provenance.start_run(
        "test", "step", scope="v01c00", volumes=[1], volume_scope=1, settings=_settings()
    )
    run.finish("ok", touched_pages=["holo", "lawrence"], vol=1, chapter_idx=0)
    (run.audit_dir / "claims.html").parent.mkdir(parents=True, exist_ok=True)
    (run.audit_dir / "claims.html").write_text("<html>claims report</html>", encoding="utf-8")

    cli._write_run_index(run.run_id, _settings())

    index_path = run.audit_dir / "index.html"
    assert index_path.is_file()
    body = index_path.read_text(encoding="utf-8")
    assert "claims.html" in body
    assert "holo" in body and "lawrence" in body
    assert "127.0.0.1:8080/#/character/holo" in body


def test_audit_run_requires_a_run_id(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _settings())
    with pytest.raises(typer.Exit) as excinfo:
        cli.audit_cmd(stage="run", run_id=None, series=None)
    assert excinfo.value.exit_code == 1


def test_audit_run_rejects_an_unknown_run_id(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _settings())
    with pytest.raises(typer.Exit) as excinfo:
        cli.audit_cmd(stage="run", run_id="no-such-run", series=None)
    assert excinfo.value.exit_code == 1


# --- the first CliRunner tests in this project (Phase 12, per PHASE_11.md's "what's next") ---


def test_cli_runner_audit_run_without_id_fails_cleanly():
    result = CliRunner().invoke(cli.app, ["audit", "run"])
    assert result.exit_code == 1
    assert "requires a run id" in result.output


def test_cli_runner_audit_unknown_stage_fails_cleanly():
    result = CliRunner().invoke(cli.app, ["audit", "not-a-real-stage"])
    assert result.exit_code == 1
    assert "Unknown audit stage" in result.output


def test_links_report_fails_on_a_pair_page_nothing_links_to(bundle_dir):
    """2026-09-25: every link resolving is not the same as every page being reachable. All 30 pair
    pages shipped with no inbound link and this report said OK."""
    (bundle_dir / "links.json").write_text(json.dumps({}), encoding="utf-8")
    site = paths.SITE_DIR
    (site / "v01" / "relationships").mkdir(parents=True)
    (site / "v01" / "character").mkdir(parents=True)
    (site / "v01" / "relationships" / "a--b.md").write_text("# A & B\n", encoding="utf-8")
    (site / "v01" / "character" / "a.md").write_text("# A\n", encoding="utf-8")
    console = Console(record=True, width=200)
    assert reports.run("links", _settings(), console) is False
    assert "orphan" in console.export_text()

    (site / "v01" / "character" / "a.md").write_text("# A\n[B](../relationships/a--b.md)\n", encoding="utf-8")
    console = Console(record=True, width=200)
    assert reports.run("links", _settings(), console) is True
