"""Phase 9: `wiki audit ingest`'s zero-Para-RAID check is opt-in per series.

`audit/reports.py` has no existing tests (confirmed: no test file imports it) -- this is the
first. Scoped narrowly to the one behaviour Phase 9 changed: a series with no radio/telepathic
comms channel at all (Spice and Wolf) must not FAIL the same check that correctly protects 86
against a regressed CSS-class pattern (CLAUDE.md §3 trap 4 / CONTRACTS §1.1).
"""

from __future__ import annotations

import json

import pytest
from rich.console import Console

from narrativewiki import paths
from narrativewiki.audit import reports
from narrativewiki.config import Settings


@pytest.fixture(autouse=True)
def _isolated_site_dir(tmp_path, monkeypatch):
    """`reports.run("links")` also scans the emitted MkDocs tree at `paths.SITE_DIR` (Phase 25).
    Tests here monkeypatch `BUNDLE_DIR` only, so every links-report test was silently reading the
    REAL `dist/<series>/wiki/` and failing whenever the working copy happened to hold a broken
    link -- which is exactly what a links test must not depend on."""
    monkeypatch.setattr(paths, "SITE_DIR", tmp_path / "_no_emitted_wiki")
    yield


def _write_volume(vol: int, *, n_para_raid: int) -> None:
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "para_id": f"v{vol:02d}:c00:p{i:04d}",
            "vol": vol,
            "chapter_idx": 0,
            "chapter_id": "chapter001",
            "chapter_title": None,
            "chapter_kind": "chapter",
            "seq": i,
            "text": "Some prose.",
            "print_page": None,
            "speech": "para_raid" if i < n_para_raid else "narration",
            "is_monologue": False,
            "scene_break_before": "none",
            "n_words": 2,
        }
        for i in range(max(n_para_raid, 1))
    ]
    paths.parsed_volume(vol).write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    manifest = {
        "series": "test",
        "volumes": [
            {
                "vol": vol,
                "title": f"Vol {vol}",
                "isbn": None,
                "pub_date": None,
                "n_chapters": 1,
                "n_paragraphs": len(records),
                "n_words": len(records) * 2,
                "source_file": f"v{vol:02d}.epub",
            }
        ],
    }
    paths.parsed_manifest().write_text(json.dumps(manifest), encoding="utf-8")


def _settings(require_para_raid: bool | None) -> Settings:
    series: dict = {}
    if require_para_raid is not None:
        series["speech"] = {"require_para_raid": require_para_raid}
    return Settings(series_id="test", series=series, models={}, extraction={})


# ---------------------------------------------------------------------------
# Phase 17: the canonicalization section of `wiki audit contradictions`
# ---------------------------------------------------------------------------


def test_contradictions_report_prints_canonicalization_summary(tmp_path, monkeypatch):
    from narrativewiki.graph import store as ST

    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path)
    doc = {
        "conflicts": [],
        "summary": {"total": 0, "narrative_change": 0, "extraction_error": 0, "flagged": 0},
        "canonicalization": {
            "merges": [
                {
                    "subject": "shin", "predicate": "PERSONALITY", "canonical": "outwardly detached",
                    "variants": [{"value": "detached on the outside", "claim_id": "c_b", "first_vol": 3}],
                }
            ],
            "summary": {"groups_merged": 1, "variants_absorbed": 1},
        },
    }
    paths.contradictions().write_text(json.dumps(doc), encoding="utf-8")

    conn = ST.connect(tmp_path / "graph.db")
    ST.write_intervals(
        conn,
        [
            {
                "interval_id": "i_1", "subject": "shin", "predicate": "PERSONALITY", "object": None,
                "value": "outwardly detached", "qualifier": None, "vol_start": 1, "vol_end": None,
                "claim_ids": ["c_a", "c_b"], "superseded_by": None,
            }
        ],
    )
    conn.close()

    console = Console(record=True, width=120)
    ok = reports.run("contradictions", _settings(None), console)
    output = console.export_text()
    assert ok is True
    assert "near-duplicate value group(s) canonicalized" in output
    assert "outwardly detached" in output
    assert "detached on the outside" in output


def test_contradictions_report_with_no_merges_prints_nothing_new(tmp_path, monkeypatch):
    """A contradictions.json written before Phase 17 (no `canonicalization` key at all) must
    still print cleanly -- absent, not a crash."""
    from narrativewiki.graph import store as ST

    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path)
    doc = {"conflicts": [], "summary": {"total": 0, "narrative_change": 0, "extraction_error": 0, "flagged": 0}}
    paths.contradictions().write_text(json.dumps(doc), encoding="utf-8")

    conn = ST.connect(tmp_path / "graph.db")
    ST.write_intervals(
        conn,
        [
            {
                "interval_id": "i_1", "subject": "shin", "predicate": "AGE", "object": None,
                "value": "16", "qualifier": None, "vol_start": 1, "vol_end": None,
                "claim_ids": ["c_a"], "superseded_by": None,
            }
        ],
    )
    conn.close()

    console = Console(record=True, width=120)
    ok = reports.run("contradictions", _settings(None), console)
    assert ok is True
    assert "canonicalized" not in console.export_text()


# ---------------------------------------------------------------------------
# Phase 22 C3 — wiki audit verify
# ---------------------------------------------------------------------------


def test_verify_report_not_ready_with_no_verification_file(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path)
    with pytest.raises(reports.StageNotReady):
        reports.run("verify", _settings(None), Console(record=True, width=200))


def test_verify_report_prints_flagged_facts_without_facts_checked_never_fails(tmp_path, monkeypatch):
    """A `verification.json` written before Phase 23 B5 (no `facts_checked` in its summary) has
    no denominator for the unsupported-rate gate -- the gate is skipped entirely, not crashed."""
    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path)
    doc = {
        "upto_vol": 2,
        "results": [
            {
                "entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence", "upto_vol": 2,
                "flagged": [
                    {
                        "kind": "relation", "predicate": "AFFILIATED_WITH",
                        "value": "Kraft Lawrence -> Medio", "qualifier": None,
                        "evidence": [{"quote": "Medio's men seized him.", "para_id": "v02:c04:p0031"}],
                        "rationale": "The evidence describes capture, not membership.",
                    }
                ],
            }
        ],
        "summary": {"characters_checked": 14, "characters_flagged": 1, "facts_flagged": 1},
    }
    paths.verification().write_text(json.dumps(doc), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("verify", _settings(None), console)
    text = console.export_text()
    assert ok is True  # a flag is a pointer for a human, never a build defect on its own
    assert "14 character(s) checked" in text
    assert "Kraft Lawrence" in text
    assert "capture, not membership" in text


def test_verify_report_fails_when_unsupported_rate_exceeds_the_ceiling(tmp_path, monkeypatch):
    """Phase 23 B5: the config default ceiling is 15%. 3 flagged out of 10 checked = 30% -- FAIL,
    not just a printed pointer for a human."""
    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path)
    doc = {
        "upto_vol": 2,
        "results": [{
            "entity_id": "marheit", "canonical": "Marheit", "upto_vol": 2,
            "flagged": [
                {"kind": "relation", "predicate": "SPOUSE_OF", "value": "Marheit -> Kraft Lawrence",
                 "qualifier": None, "evidence": [], "rationale": "No marriage stated."},
            ],
        }],
        "summary": {
            "characters_checked": 5, "characters_flagged": 1, "facts_flagged": 3, "facts_checked": 10,
        },
    }
    paths.verification().write_text(json.dumps(doc), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("verify", _settings(None), console)
    text = console.export_text()
    assert ok is False
    assert "FAIL" in text
    assert "30.0%" in text


def test_verify_report_passes_when_unsupported_rate_is_under_the_ceiling(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path)
    doc = {
        "upto_vol": 2, "results": [],
        "summary": {
            "characters_checked": 5, "characters_flagged": 0, "facts_flagged": 1, "facts_checked": 20,
        },
    }
    paths.verification().write_text(json.dumps(doc), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("verify", _settings(None), console)
    text = console.export_text()
    assert ok is True
    assert "5.0%" in text


def test_verify_report_with_nothing_flagged_prints_clean_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "GRAPH_DIR", tmp_path)
    doc = {
        "upto_vol": 2, "results": [],
        "summary": {"characters_checked": 14, "characters_flagged": 0, "facts_flagged": 0},
    }
    paths.verification().write_text(json.dumps(doc), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("verify", _settings(None), console)
    text = console.export_text()
    assert ok is True
    assert "0 with a flagged fact" in text


def test_zero_para_raid_fails_when_series_requires_it(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    _write_volume(1, n_para_raid=0)
    console = Console(record=True, width=200)
    reports.run("ingest", _settings(require_para_raid=True), console)
    out = console.export_text()
    assert "FAIL" in out
    assert "zero Para-RAID paragraphs" in out


def test_zero_para_raid_is_ok_when_series_does_not_require_it(tmp_path, monkeypatch):
    """Spice and Wolf's exact situation: no radio/telepathic channel exists in this genre at
    all, so a zero count is expected, not a regression."""
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    _write_volume(1, n_para_raid=0)
    console = Console(record=True, width=200)
    reports.run("ingest", _settings(require_para_raid=False), console)
    out = console.export_text()
    assert "FAIL" not in out
    assert "OK" in out


def test_zero_para_raid_is_ok_when_flag_is_entirely_absent(tmp_path, monkeypatch):
    """The flag defaults to false/absent -- a series config that predates this feature (or never
    mentions the flag) must not suddenly start failing."""
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    _write_volume(1, n_para_raid=0)
    console = Console(record=True, width=200)
    reports.run("ingest", _settings(require_para_raid=None), console)
    out = console.export_text()
    assert "FAIL" not in out


@pytest.mark.parametrize("require_para_raid", [True, False, None])
def test_nonzero_para_raid_is_ok_regardless_of_the_flag(require_para_raid, tmp_path, monkeypatch):
    """A series that DOES have Para-RAID paragraphs never fails this check, whether or not it
    declares require_para_raid -- the flag only changes what a ZERO count means."""
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    _write_volume(1, n_para_raid=5)
    console = Console(record=True, width=200)
    reports.run("ingest", _settings(require_para_raid), console)
    out = console.export_text()
    assert "FAIL" not in out


# ---------------------------------------------------------------------------
# Phase 18 — `wiki audit scenes`
# ---------------------------------------------------------------------------


def _write_parsed_chapter(vol: int, para_ids: list[str], texts: dict[str, str] | None = None) -> None:
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)
    texts = texts or {}
    records = [
        {
            "para_id": pid, "vol": vol, "chapter_idx": 0, "chapter_id": "chapter001",
            "chapter_title": None, "chapter_kind": "chapter", "seq": i,
            "text": texts.get(pid, "Some prose."), "print_page": 1, "speech": "narration",
            "is_monologue": False, "scene_break_before": "none", "n_words": 2,
        }
        for i, pid in enumerate(para_ids)
    ]
    paths.parsed_volume(vol).write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )


def _write_scenes(vol: int, scenes: list[dict]) -> None:
    paths.SCENES_DIR.mkdir(parents=True, exist_ok=True)
    paths.scenes_volume(vol).write_text(
        "\n".join(json.dumps(s) for s in scenes) + "\n", encoding="utf-8"
    )


def _scene(scene_id: str, core_para_ids: list[str], **overrides) -> dict:
    scene = {
        "scene_id": scene_id, "vol": 1, "chapter_idx": 0, "span_index": 0,
        "para_ids": core_para_ids, "core_para_ids": core_para_ids,
        "participants": [], "location": None, "beat_summary": "Something happens.",
        "state_changes": [], "quotes": [], "confidence": 0.7, "source": "test",
    }
    scene.update(overrides)
    return scene


def test_scenes_report_raises_stage_not_ready_with_no_output(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    console = Console(record=True, width=120)
    with pytest.raises(reports.StageNotReady):
        reports.run("scenes", _settings(None), console)


def test_scenes_report_ok_with_full_coverage_and_verbatim_quotes(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "01_parsed")
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    para_ids = ["v01:c00:p0000", "v01:c00:p0001"]
    _write_parsed_chapter(1, para_ids, texts={para_ids[1]: "Shin said the plan."})
    _write_scenes(
        1,
        [
            _scene(
                "sn_v01c00s000", para_ids,
                quotes=[{"speaker": None, "addressee": None, "para_id": para_ids[1],
                         "print_page": 1, "quote": "the plan"}],
            )
        ],
    )
    console = Console(record=True, width=200)
    ok = reports.run("scenes", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "FAIL" not in out
    assert "OK" in out


def test_scenes_report_fails_on_a_paragraph_coverage_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "01_parsed")
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    para_ids = ["v01:c00:p0000", "v01:c00:p0001"]
    _write_parsed_chapter(1, para_ids)
    # only reports coverage of the first paragraph -- the second is silently missing
    _write_scenes(1, [_scene("sn_v01c00s000", para_ids[:1])])
    console = Console(record=True, width=200)
    ok = reports.run("scenes", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "FAIL" in out
    assert "coverage" in out


def test_scenes_report_fails_on_a_nonverbatim_quote(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "01_parsed")
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    para_ids = ["v01:c00:p0000"]
    _write_parsed_chapter(1, para_ids)
    _write_scenes(
        1,
        [
            _scene(
                "sn_v01c00s000", para_ids,
                quotes=[{"speaker": None, "addressee": None, "para_id": para_ids[0],
                         "print_page": 1, "quote": "not actually in the paragraph"}],
            )
        ],
    )
    console = Console(record=True, width=200)
    ok = reports.run("scenes", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "FAIL" in out
    assert "verbatim" in out


def test_scenes_report_renders_mined_epithets_for_review(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "01_parsed")
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    para_ids = ["v01:c00:p0000"]
    _write_parsed_chapter(1, para_ids)
    _write_scenes(1, [_scene("sn_v01c00s000", para_ids)])
    paths.ENTITIES_DIR.mkdir(parents=True, exist_ok=True)
    paths.gazetteer().write_text(
        json.dumps({"entities": [{"entity_id": "holo", "canonical": "Holo"}]}), encoding="utf-8"
    )
    paths.scene_epithets(1).write_text(
        json.dumps(
            {
                "entity_id": "holo", "text": "the wisewolf", "vol": 1, "chapter_idx": 0,
                "para_id": para_ids[0], "print_page": 1, "quote": "they called her the wisewolf",
                "confidence": 0.82, "source": "test",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    console = Console(record=True, width=200)
    reports.run("scenes", _settings(None), console)
    out = console.export_text()
    assert "Holo" in out
    assert "the wisewolf" in out
    assert "0.82" in out


# ---------------------------------------------------------------------------
# Phase 19 — events report
# ---------------------------------------------------------------------------


def _make_events_db(tmp_path, *, events=None, claims=None):
    """Write a minimal events.db to tmp_path/04b_events/events.db."""
    import sqlite3
    db_dir = tmp_path / "04b_events"
    db_dir.mkdir(parents=True, exist_ok=True)
    db = db_dir / "events.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY, vol INTEGER, chapter_idx INTEGER, span_index INTEGER,
            scene_id TEXT, participants_json TEXT, location TEXT, beat_summary TEXT,
            vol_start INTEGER, confidence REAL, source TEXT
        );
        CREATE TABLE event_claims (
            claim_id TEXT PRIMARY KEY, event_id TEXT, kind TEXT, subject TEXT,
            predicate TEXT, from_value TEXT, to_value TEXT, object TEXT, note TEXT,
            speaker TEXT, para_id TEXT, quote TEXT, vol INTEGER, confidence REAL, source TEXT
        );
    """)
    for ev in (events or []):
        conn.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (ev["event_id"], ev["vol"], ev["chapter_idx"], ev["span_index"],
             ev["scene_id"], json.dumps(ev.get("participants", [])), ev.get("location"),
             ev["beat_summary"], ev["vol_start"], ev.get("confidence", 0.8), ev.get("source", "")),
        )
    for cl in (claims or []):
        conn.execute(
            "INSERT INTO event_claims VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cl["claim_id"], cl["event_id"], cl["kind"],
             cl.get("subject"), cl.get("predicate"), cl.get("from_value"), cl.get("to_value"),
             cl.get("object"), cl.get("note"), cl.get("speaker"),
             cl["para_id"], cl["quote"], cl["vol"], cl.get("confidence", 0.8), cl.get("source", "")),
        )
    conn.commit()
    conn.close()
    return db_dir


def test_events_report_stage_not_ready_when_db_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "EVENTS_DIR", tmp_path / "04b_events")
    console = Console(record=True, width=200)
    with pytest.raises(reports.StageNotReady):
        reports.run("events", _settings(None), console)


def test_events_report_ok_with_valid_events(tmp_path, monkeypatch):
    events_dir = _make_events_db(
        tmp_path,
        events=[{
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["holo"],
            "beat_summary": "Something.", "vol_start": 1,
        }],
        claims=[{
            "claim_id": "ec_aaa", "event_id": "ev_v01c00s000", "kind": "quote",
            "para_id": "v01:c00:p0000", "quote": "Hi.", "vol": 1,
        }],
    )
    monkeypatch.setattr(paths, "EVENTS_DIR", events_dir)
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")

    console = Console(record=True, width=200)
    ok = reports.run("events", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "OK" in out
    assert "1" in out  # 1 event


def test_events_report_fail_on_unknown_kind(tmp_path, monkeypatch):
    events_dir = _make_events_db(
        tmp_path,
        events=[{
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": [],
            "beat_summary": "X", "vol_start": 1,
        }],
        claims=[{
            "claim_id": "ec_bad", "event_id": "ev_v01c00s000", "kind": "BAD_KIND",
            "para_id": "v01:c00:p0000", "quote": "Hi.", "vol": 1,
        }],
    )
    monkeypatch.setattr(paths, "EVENTS_DIR", events_dir)
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")

    console = Console(record=True, width=200)
    ok = reports.run("events", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "FAIL" in out
    assert "BAD_KIND" in out


# ---------------------------------------------------------------------------
# Phase 22 A5 — pages report's field-coverage / sparse-page detector
# ---------------------------------------------------------------------------


def _write_page(pages_dir, entity_id, vol, fields):
    page_dir = pages_dir / entity_id
    page_dir.mkdir(parents=True, exist_ok=True)
    page = {
        "entity_id": entity_id, "canonical": entity_id, "upto_vol": vol, "claim_set_hash": "h",
        "fields": fields, "prose": {}, "mentions_of": [], "generated_by": None,
    }
    (page_dir / f"v{vol:02d}.json").write_text(json.dumps(page), encoding="utf-8")


def test_pages_report_excludes_inferred_default_from_field_coverage(tmp_path, monkeypatch):
    """Phase 22 A5 (U6): a `default:`-materialized field (`inferred: true`) must not count as
    real field coverage -- STATUS now always exists on every page, so counting it here would
    make this detector blind to the exact "5 of 14 pages have no facts" (S1) symptom it exists
    to catch (coverage == 0 -> "sparse")."""
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "05_pages")
    _write_page(
        paths.PAGES_DIR, "shin", 1,
        {"status": {"value": "alive", "since_vol": None, "inferred": True}},
    )
    settings = Settings(series_id="test", series={}, models={}, extraction={"attributes": {"STATUS": {"single": True}}})
    console = Console(record=True, width=160)
    ok = reports.run("pages", settings, console)
    out = console.export_text()
    assert ok is True
    assert "Average field coverage (latest cutoff): 0%" in out


def test_pages_report_counts_real_evidence_as_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "05_pages")
    _write_page(
        paths.PAGES_DIR, "shin", 1,
        {"age": {"value": "16", "since_vol": 1, "inferred": False}},
    )
    settings = Settings(
        series_id="test", series={}, models={},
        extraction={"attributes": {"AGE": {"single": True}, "STATUS": {"single": True}}},
    )
    console = Console(record=True, width=160)
    ok = reports.run("pages", settings, console)
    out = console.export_text()
    assert ok is True
    assert "Average field coverage (latest cutoff): 50%" in out


# ---------------------------------------------------------------------------
# Phase 21 — relationships report
# ---------------------------------------------------------------------------


def _write_gazetteer(tmp_path, entities):
    entities_dir = tmp_path / "02_entities"
    entities_dir.mkdir(parents=True, exist_ok=True)
    (entities_dir / "gazetteer.json").write_text(json.dumps({"entities": entities}), encoding="utf-8")
    return entities_dir


def _write_relationship_bundle(bundle_dir, filename, doc):
    rel_dir = bundle_dir / "relationships"
    rel_dir.mkdir(parents=True, exist_ok=True)
    (rel_dir / filename).write_text(json.dumps(doc), encoding="utf-8")


_SHIN = {"entity_id": "shinei-nouzen", "canonical": "Shinei Nouzen", "type": "CHARACTER"}
_RAIDEN = {"entity_id": "raiden-shuga", "canonical": "Raiden Shuga", "type": "CHARACTER"}
_SPEARHEAD = {"entity_id": "spearhead-squadron", "canonical": "Spearhead Squadron", "type": "FACTION"}


def test_relationships_report_stage_not_ready_when_bundle_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "BUNDLE_DIR", tmp_path / "06_bundle")
    console = Console(record=True, width=200)
    with pytest.raises(reports.StageNotReady):
        reports.run("relationships", _settings(None), console)


def test_relationships_report_ok_when_evidence_within_cutoff(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    monkeypatch.setattr(paths, "ENTITIES_DIR", _write_gazetteer(tmp_path, [_SHIN, _RAIDEN]))
    doc = {
        "pair": ["raiden-shuga", "shinei-nouzen"],
        "first_vol": 1,
        "cutoffs": {
            "1": {
                "relations": [{"subject": "shinei-nouzen", "predicate": "FRIEND_OF", "display": "Friend of",
                                "object": "raiden-shuga", "qualifier": None, "since_vol": 1}],
                "history": [],
                "shared_scenes": [{"event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0,
                                    "location": None, "beat_summary": "x", "quotes": []}],
            }
        },
    }
    _write_relationship_bundle(bundle_dir, "raiden-shuga--shinei-nouzen.json", doc)
    (bundle_dir / "index.json").write_text(
        json.dumps({"relationship_pairs": [["raiden-shuga", "shinei-nouzen"]]}), encoding="utf-8"
    )

    console = Console(record=True, width=200)
    ok = reports.run("relationships", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "OK" in out


def test_relationships_report_fails_when_relation_evidence_exceeds_cutoff(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    monkeypatch.setattr(paths, "ENTITIES_DIR", _write_gazetteer(tmp_path, [_SHIN, _RAIDEN]))
    doc = {
        "pair": ["raiden-shuga", "shinei-nouzen"],
        "first_vol": 1,
        "cutoffs": {
            # A relation whose OWN since_vol (2) is past this cutoff key (1) -- a leak.
            "1": {
                "relations": [{"subject": "shinei-nouzen", "predicate": "FRIEND_OF", "display": "Friend of",
                                "object": "raiden-shuga", "qualifier": None, "since_vol": 2}],
                "history": [], "shared_scenes": [],
            }
        },
    }
    _write_relationship_bundle(bundle_dir, "raiden-shuga--shinei-nouzen.json", doc)

    console = Console(record=True, width=200)
    ok = reports.run("relationships", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "FAIL" in out


def test_relationships_report_fails_on_non_character_pair(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    monkeypatch.setattr(paths, "ENTITIES_DIR", _write_gazetteer(tmp_path, [_SHIN, _SPEARHEAD]))
    doc = {
        "pair": ["shinei-nouzen", "spearhead-squadron"],
        "first_vol": 1,
        "cutoffs": {"1": {"relations": [], "history": [], "shared_scenes": []}},
    }
    _write_relationship_bundle(bundle_dir, "shinei-nouzen--spearhead-squadron.json", doc)

    console = Console(record=True, width=200)
    ok = reports.run("relationships", _settings(None), console)
    assert ok is False


def test_relationships_report_fails_when_index_disagrees_with_disk(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    monkeypatch.setattr(paths, "ENTITIES_DIR", _write_gazetteer(tmp_path, [_SHIN, _RAIDEN]))
    doc = {
        "pair": ["raiden-shuga", "shinei-nouzen"],
        "first_vol": 1,
        "cutoffs": {"1": {"relations": [], "history": [], "shared_scenes": []}},
    }
    _write_relationship_bundle(bundle_dir, "raiden-shuga--shinei-nouzen.json", doc)
    # index.json claims a DIFFERENT pair list than what is actually on disk.
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "index.json").write_text(json.dumps({"relationship_pairs": []}), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("relationships", _settings(None), console)
    assert ok is False


# ---------------------------------------------------------------------------
# Phase 22 A6 — yield assertions + closing two known audit-report holes (S7)
# ---------------------------------------------------------------------------


def _write_claim(claims_dir, vol, claim):
    claims_dir.mkdir(parents=True, exist_ok=True)
    path = claims_dir / f"v{vol:02d}.jsonl"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    path.write_text(existing + json.dumps(claim) + "\n", encoding="utf-8")


def test_claims_report_prints_roster_yield_and_appearance_ratio(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CLAIMS_DIR", tmp_path / "03_claims")
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    monkeypatch.setattr(
        paths, "ENTITIES_DIR",
        _write_gazetteer(
            tmp_path,
            [
                {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER"},
                {"entity_id": "lawrence", "canonical": "Lawrence", "type": "CHARACTER"},
            ],
        ),
    )
    _write_claim(paths.CLAIMS_DIR, 1, {
        "claim_id": "c1", "subject": "holo", "predicate": "AGE", "object": None,
        "polarity": "asserted", "confidence": 0.9, "first_vol": 1, "evidence": [],
    })
    _write_claim(paths.CLAIMS_DIR, 1, {
        "claim_id": "c2", "subject": "holo", "predicate": "APPEARANCE", "object": None,
        "polarity": "asserted", "confidence": 0.9, "first_vol": 1, "evidence": [],
    })
    console = Console(record=True, width=200)
    ok = reports.run("claims", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "Roster yield: 1/2" in out
    assert "APPEARANCE share of all claims: 1/2 (50%)" in out


def test_claims_report_fails_when_upstream_extract_run_failed(tmp_path, monkeypatch):
    """Phase 22 A6: this report must not vouch for a crashed `wiki extract` run's partial claims
    -- the exact blind spot the 2026-09-09 audit found (docs/vision/PHASE_22.md)."""
    from narrativewiki import provenance

    monkeypatch.setattr(paths, "CLAIMS_DIR", tmp_path / "03_claims")
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    _write_claim(paths.CLAIMS_DIR, 1, {
        "claim_id": "c1", "subject": "holo", "predicate": "AGE", "object": None,
        "polarity": "asserted", "confidence": 0.9, "first_vol": 1, "evidence": [],
    })
    manifest = {"run_id": "20260904T133513-extract-v1-1", "command": "extract", "error": "Cannot reach Ollama"}
    monkeypatch.setattr(provenance, "failed_stage_artifacts", lambda keys: [manifest])

    console = Console(record=True, width=200)
    ok = reports.run("claims", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "FAIL" in out
    assert "20260904T133513-extract-v1-1" in out
    assert "rollback" in out


def test_scenes_report_prints_structured_field_yield(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "01_parsed")
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    para_ids = ["v01:c00:p0000", "v01:c00:p0001"]
    _write_parsed_chapter(1, para_ids)
    _write_scenes(
        1,
        [
            _scene("sn_v01c00s000", para_ids[:1], location="Pasloe"),
            _scene("sn_v01c00s001", para_ids[1:]),
        ],
    )
    console = Console(record=True, width=200)
    ok = reports.run("scenes", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "Scenes with >=1 structured field" in out
    assert "1/2 (50%)" in out


def test_scenes_report_fails_when_upstream_scenes_run_failed(tmp_path, monkeypatch):
    from narrativewiki import provenance

    monkeypatch.setattr(paths, "SCENES_DIR", tmp_path / "02b_scenes")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "01_parsed")
    monkeypatch.setattr(paths, "ENTITIES_DIR", tmp_path / "02_entities")
    para_ids = ["v01:c00:p0000"]
    _write_parsed_chapter(1, para_ids)
    _write_scenes(1, [_scene("sn_v01c00s000", para_ids)])
    manifest = {"run_id": "20260101T000000-scenes-v1", "command": "scenes", "error": "boom"}
    monkeypatch.setattr(provenance, "failed_stage_artifacts", lambda keys: [manifest])

    console = Console(record=True, width=200)
    ok = reports.run("scenes", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "FAIL" in out
    assert "20260101T000000-scenes-v1" in out


def _write_outline_page(pages_dir, entity_id, vol, prose, quotes=None):
    page_dir = pages_dir / entity_id
    page_dir.mkdir(parents=True, exist_ok=True)
    page: dict = {"entity_id": entity_id, "prose": prose}
    if quotes is not None:
        page["quotes"] = quotes
    (page_dir / f"v{vol:02d}.json").write_text(json.dumps(page), encoding="utf-8")


def _outline_settings() -> Settings:
    return Settings(
        series_id="test", series={}, models={},
        extraction={
            "page_outline": {
                "background": {"kind": "prose", "order": 0},
                "personality": {"kind": "prose", "order": 1},
            }
        },
    )


def test_outline_report_warns_on_asymmetric_none_prose(tmp_path, monkeypatch):
    """Phase 22 A6: the old version of this check computed a condition and did nothing with it,
    regardless of the outcome -- a dead branch. One section None while a sibling has content is a
    real generation gap, not a zero-evidence character."""
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "05_pages")
    _write_outline_page(
        paths.PAGES_DIR, "holo", 1,
        {"background": None, "personality": {"text": "Curious and playful."}},
    )
    console = Console(record=True, width=200)
    ok = reports.run("outline", _outline_settings(), console)
    out = console.export_text()
    assert ok is True
    assert "background prose is None but" in out
    assert "possible generation gap" in out


def test_outline_report_does_not_warn_when_all_prose_is_none(tmp_path, monkeypatch):
    """A character with zero evidence legitimately gets None everywhere -- not a generation gap."""
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "05_pages")
    _write_outline_page(
        paths.PAGES_DIR, "lawrence", 1,
        {"background": None, "personality": None},
    )
    console = Console(record=True, width=200)
    ok = reports.run("outline", _outline_settings(), console)
    out = console.export_text()
    assert ok is True
    assert "possible generation gap" not in out


def _write_bundle_links(bundle_dir, entries: dict[str, str]) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    links = {eid: {"route": route} for eid, route in entries.items()}
    (bundle_dir / "links.json").write_text(json.dumps(links), encoding="utf-8")


def test_links_report_ok_when_all_quote_speakers_resolved(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    _write_bundle_links(bundle_dir, {"holo": "/character/holo"})
    pages_dir = bundle_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "entity_id": "holo",
        "cutoffs": {
            "1": {
                "fields": {}, "mentions_of": [], "prose": {}, "lead": None,
                "quotes": [{"quote": "Hello.", "speaker": "holo", "para_id": "p1", "vol": 1}],
            }
        },
    }
    (pages_dir / "holo.json").write_text(json.dumps(doc), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "OK" in out


def test_links_report_fails_when_roster_id_has_no_page_file_on_disk(tmp_path, monkeypatch):
    """Phase 23 E6: index.json's roster must not list a character with no pages/<id>.json on
    disk -- the saint-ruvinheigen dangling-roster-entry bug (site/bundle.py::build_index's own
    written_ids fix addresses the write side; this is the independent read-side check)."""
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    _write_bundle_links(bundle_dir, {"holo": "/character/holo", "ghost": "/character/ghost"})
    pages_dir = bundle_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "entity_id": "holo",
        "cutoffs": {"1": {"fields": {}, "mentions_of": [], "prose": {}, "lead": None}},
    }
    (pages_dir / "holo.json").write_text(json.dumps(doc), encoding="utf-8")
    # "ghost" is in links.json and would-be roster, but has no pages/ghost.json.
    (bundle_dir / "index.json").write_text(
        json.dumps({"characters": [{"entity_id": "holo"}, {"entity_id": "ghost"}]}), encoding="utf-8"
    )

    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "ghost" in out
    assert "no pages/<id>.json" in out or "no page file exists" in out


def test_links_report_ok_when_every_roster_id_has_a_page_file(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    _write_bundle_links(bundle_dir, {"holo": "/character/holo"})
    pages_dir = bundle_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "entity_id": "holo",
        "cutoffs": {"1": {"fields": {}, "mentions_of": [], "prose": {}, "lead": None}},
    }
    (pages_dir / "holo.json").write_text(json.dumps(doc), encoding="utf-8")
    (bundle_dir / "index.json").write_text(
        json.dumps({"characters": [{"entity_id": "holo"}]}), encoding="utf-8"
    )

    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(None), console)
    assert ok is True


def test_links_report_fails_on_null_speaker_in_page_quotes(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    _write_bundle_links(bundle_dir, {"holo": "/character/holo"})
    pages_dir = bundle_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "entity_id": "holo",
        "cutoffs": {
            "1": {
                "fields": {}, "mentions_of": [], "prose": {}, "lead": None,
                "quotes": [{"quote": "Hello.", "speaker": None, "para_id": "p1", "vol": 1}],
            }
        },
    }
    (pages_dir / "holo.json").write_text(json.dumps(doc), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "no resolved speaker" in out


def test_links_report_fails_on_null_speaker_in_codex_key_events(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    _write_bundle_links(bundle_dir, {"spearhead-squadron": "/codex/factions#spearhead-squadron"})
    codex_dir = bundle_dir / "codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "spearhead-squadron": {
            "cutoffs": {
                "1": {
                    "members": [], "adversaries": [], "related": [], "summary": None,
                    "key_events": [{
                        "event_id": "ev1", "vol": 1, "participants": [], "beat_summary": None,
                        "quotes": [{"quote": "Hi.", "speaker": None, "vol": 1}],
                    }],
                }
            }
        }
    }
    (codex_dir / "factions.json").write_text(json.dumps(doc), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "no resolved speaker" in out


def test_links_report_fails_on_null_speaker_in_shared_scenes(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    _write_bundle_links(bundle_dir, {"holo": "/character/holo", "lawrence": "/character/lawrence"})
    doc = {
        "pair": ["holo", "lawrence"],
        "cutoffs": {
            "1": {
                "relations": [], "history": [],
                "shared_scenes": [{
                    "event_id": "ev1", "vol": 1, "chapter_idx": 0, "location": None,
                    "beat_summary": "x", "quotes": [{"quote": "Hi.", "speaker": None, "vol": 1}],
                }],
            }
        },
    }
    _write_relationship_bundle(bundle_dir, "holo--lawrence.json", doc)

    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "no resolved speaker" in out


def test_links_report_fails_on_null_speaker_in_timeline_event(tmp_path, monkeypatch):
    bundle_dir = tmp_path / "06_bundle"
    monkeypatch.setattr(paths, "BUNDLE_DIR", bundle_dir)
    _write_bundle_links(bundle_dir, {"holo": "/character/holo"})
    timeline_dir = bundle_dir / "timeline"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "vol": 1,
        "chapters": [{
            "events": [{
                "event_id": "ev1", "vol": 1, "participants": [], "location": None,
                "beat_summary": None, "state_changes": [],
                "quotes": [{"quote": "Hi.", "speaker": None, "vol": 1}],
            }]
        }],
    }
    (timeline_dir / "v01.json").write_text(json.dumps(doc), encoding="utf-8")
    (bundle_dir / "index.json").write_text(json.dumps({"timeline_volumes": [1]}), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("links", _settings(None), console)
    out = console.export_text()
    assert ok is False
    assert "no resolved speaker" in out


# ---------------------------------------------------------------------------
# [24] gazetteer report: build provenance + ambiguous-surface collisions
# ---------------------------------------------------------------------------


def test_gazetteer_report_shows_provenance_and_dropped_ambiguous_surfaces(tmp_path, monkeypatch):
    """docs/vision/plans/0008-pre-full-scale-audit.md B1/B3: min_mentions and the alias-pair cap's
    effect are now visible on the artifact, and an ambiguous surface collision is now reported
    (surface, kept entity, dropped entity) instead of silently favoring whichever entity_id sorts
    first."""
    entities_dir = tmp_path / "02_entities"
    entities_dir.mkdir(parents=True)
    entities = [
        {
            "entity_id": "a-entity", "canonical": "Alpha", "type": "CHARACTER",
            "aliases": [], "first_vol": 1, "mention_count": 10, "importance": 1.0,
            "confidence": 0.9, "notes": "",
            "surface_forms": [
                {"text": "Alpha", "ambiguous": False, "first_vol": 1},
                {"text": "Shared", "ambiguous": True, "first_vol": 1},
            ],
        },
        {
            "entity_id": "b-entity", "canonical": "Beta", "type": "CHARACTER",
            "aliases": [], "first_vol": 1, "mention_count": 5, "importance": 0.5,
            "confidence": 0.9, "notes": "",
            "surface_forms": [
                {"text": "Beta", "ambiguous": False, "first_vol": 1},
                {"text": "Shared", "ambiguous": True, "first_vol": 1},
            ],
        },
    ]
    gaz = {
        "entities": entities,
        "volumes_covered": [1],
        "built_at": "2026-09-14T00:00:00Z",
        "provenance": {
            "min_mentions": 3, "max_candidates_per_volume": 400,
            "max_llm_alias_pairs": 300, "alias_pairs_total": 5, "alias_pairs_dropped": 2,
        },
    }
    (entities_dir / "gazetteer.json").write_text(json.dumps(gaz), encoding="utf-8")
    monkeypatch.setattr(paths, "ENTITIES_DIR", entities_dir)

    console = Console(record=True, width=200)
    ok = reports.run("gazetteer", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "min_mentions=3" in out
    assert "2/5 alias candidate pair(s)" in out
    assert "1 ambiguous surface(s) dropped" in out
    inventory = [json.loads(line) for line in paths.surface_forms().read_text(encoding="utf-8").splitlines()]
    assert len([r for r in inventory if not r["indexed"]]) == 1
    assert all(r["source"] == "unknown" for r in inventory)
    assert "Shared" in out and "a-entity" in out
    assert "index no surface form" not in out  # b-entity still indexes "Beta"


def test_gazetteer_report_flags_an_entity_that_indexes_nothing(tmp_path, monkeypatch):
    """Phase 30: `wisewolf` is Holo, mined as its own candidate and then subsumed when epithet
    merging gave Holo the same literal. It keeps a stale mention_count of 33 while indexing
    nothing, so it can never gain a mention, a claim or a page. Reporting the dropped surface is
    not enough -- only the alphabetical tie-break decides whether the phantom or the real
    character is the one left starved."""
    entities_dir = tmp_path / "02_entities"
    entities_dir.mkdir(parents=True)
    common = {"type": "CHARACTER", "aliases": [], "first_vol": 1, "importance": 1.0,
              "confidence": 0.9, "notes": ""}
    entities = [
        {"entity_id": "holo", "canonical": "Holo", "mention_count": 500, **common,
         "surface_forms": [{"text": "Holo", "ambiguous": False, "first_vol": 1},
                           {"text": "Wisewolf", "ambiguous": True, "first_vol": 1}]},
        {"entity_id": "wisewolf", "canonical": "Wisewolf", "mention_count": 33, **common,
         "surface_forms": [{"text": "Wisewolf", "ambiguous": True, "first_vol": 1}]},
    ]
    (entities_dir / "gazetteer.json").write_text(
        json.dumps({"entities": entities, "volumes_covered": [1], "built_at": "2026-09-23T00:00:00Z"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "ENTITIES_DIR", entities_dir)

    console = Console(record=True, width=200)
    assert reports.run("gazetteer", _settings(None), console) is True
    out = console.export_text()
    assert "1 entit(y/ies) index no surface form at all" in out
    assert "'wisewolf'" in out


def test_gazetteer_report_notes_absent_provenance_without_failing(tmp_path, monkeypatch):
    """A gazetteer built before the provenance field existed must still report cleanly, not KeyError."""
    entities_dir = tmp_path / "02_entities"
    entities_dir.mkdir(parents=True)
    entities = [{
        "entity_id": "a-entity", "canonical": "Alpha", "type": "CHARACTER",
        "aliases": [], "first_vol": 1, "mention_count": 10, "importance": 1.0,
        "confidence": 0.9, "notes": "", "surface_forms": [{"text": "Alpha", "ambiguous": False, "first_vol": 1}],
    }]
    gaz = {"entities": entities, "volumes_covered": [1], "built_at": "2026-09-14T00:00:00Z"}
    (entities_dir / "gazetteer.json").write_text(json.dumps(gaz), encoding="utf-8")
    monkeypatch.setattr(paths, "ENTITIES_DIR", entities_dir)

    console = Console(record=True, width=200)
    ok = reports.run("gazetteer", _settings(None), console)
    out = console.export_text()
    assert ok is True
    assert "No build provenance recorded" in out
