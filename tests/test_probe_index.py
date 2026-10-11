"""Tests for probe/channels/index.py and probe/report.py — Phase 24 L_build measurement.

`measure_candidate_mining` is the load-bearing probe: it re-runs `entities/candidates.py`
restricted to a cutoff and diffs against a shipped, whole-corpus gazetteer. These tests build a
tiny two-volume fixture with one surface form that only clears `min_mentions` once volume 2's
occurrences are counted in, so mining "at cutoff 1" and mining "the whole corpus" disagree by
construction — the exact shape of the real finding on the 86 series (LOG.md 2026-09-13,
leak_rate=0.303 at t=1).
"""

from __future__ import annotations

import json

import pytest

from narrativewiki import paths
from narrativewiki.probe import report as probe_report
from narrativewiki.probe.channels import index as IX

SERIES_CONFIG = {
    "entities": {
        "honorifics": [],
        "stopword_surfaces": [],
        "max_candidates_per_volume": 400,
    }
}


def _write_parsed_volume(vol: int, paragraphs: list[str]) -> None:
    path = paths.parsed_volume(vol)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for i, text in enumerate(paragraphs):
            fh.write(json.dumps({"para_id": f"v{vol:02d}:c01:p{i:04d}", "vol": vol, "text": text, "speech": "narration"}) + "\n")


@pytest.fixture()
def sandbox(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    paths.set_active_series("probe-fixture")
    paths.ensure_dirs()
    yield
    paths.set_active_series(None)


def test_candidate_mining_leak_when_min_mentions_only_clears_with_future_volumes(sandbox):
    """"Rare Person" appears twice in v1 (below min_mentions=3) and three more times in v2. A
    whole-corpus mine over v1+v2 keeps it (5 >= 3); a cutoff-1-only mine does not (2 < 3)."""
    _write_parsed_volume(1, ["Rare Person walked in.", "Rare Person left.", "The room was quiet."])
    _write_parsed_volume(2, ["Rare Person Rare Person Rare Person spoke three times."])

    from narrativewiki.entities.candidates import mine_candidates

    v1 = {1: [json.loads(l) for l in paths.parsed_volume(1).read_text(encoding="utf-8").splitlines()]}
    v1v2 = {
        1: v1[1],
        2: [json.loads(l) for l in paths.parsed_volume(2).read_text(encoding="utf-8").splitlines()],
    }
    whole_corpus_candidates = mine_candidates(v1v2, SERIES_CONFIG, min_mentions=3)
    cutoff1_candidates = mine_candidates(v1, SERIES_CONFIG, min_mentions=3)

    whole_surfaces = {c["surface"] for c in whole_corpus_candidates}
    cutoff1_surfaces = {c["surface"] for c in cutoff1_candidates}
    assert "Rare Person" in whole_surfaces
    assert "Rare Person" not in cutoff1_surfaces  # <- the leak, demonstrated directly

    # Ship the whole-corpus candidates and a gazetteer entry that is visible at cutoff 1.
    with paths.candidates().open("w", encoding="utf-8") as fh:
        for c in whole_corpus_candidates:
            fh.write(json.dumps(c) + "\n")
    gazetteer = {
        "entities": [
            {
                "entity_id": "rare-person",
                "canonical": "Rare Person",
                "type": "CHARACTER",
                "first_vol": 1,
                "surface_forms": [{"text": "Rare Person", "first_vol": 1}],
            }
        ],
        "volumes_covered": [1, 2],
    }
    paths.gazetteer().write_text(json.dumps(gazetteer), encoding="utf-8")

    result = IX.measure_candidate_mining("probe-fixture", SERIES_CONFIG, upto_vol=1)
    assert result["channel"] == "L_build"
    assert result["surfaces_missing_at_cutoff"] == ["Rare Person"]
    assert result["leak_rate"] == pytest.approx(1.0)  # the fixture's only surface form leaks
    assert result["mining_parameters"]["min_mentions"] == 3
    assert result["mining_parameter_sources"]["min_mentions"] == "legacy_default"


def test_candidate_mining_no_leak_when_threshold_clears_within_cutoff(sandbox):
    """A surface mentioned >= min_mentions times within volume 1 alone leaks nothing."""
    _write_parsed_volume(1, ["Common Name spoke.", "Common Name walked.", "Common Name ran."])

    from narrativewiki.entities.candidates import mine_candidates

    v1 = {1: [json.loads(l) for l in paths.parsed_volume(1).read_text(encoding="utf-8").splitlines()]}
    candidates = mine_candidates(v1, SERIES_CONFIG, min_mentions=3)
    with paths.candidates().open("w", encoding="utf-8") as fh:
        for c in candidates:
            fh.write(json.dumps(c) + "\n")
    gazetteer = {
        "entities": [
            {
                "entity_id": "common-name",
                "canonical": "Common Name",
                "type": "CHARACTER",
                "first_vol": 1,
                "surface_forms": [{"text": "Common Name", "first_vol": 1}],
            }
        ],
        "volumes_covered": [1],
    }
    paths.gazetteer().write_text(json.dumps(gazetteer), encoding="utf-8")

    result = IX.measure_candidate_mining("probe-fixture", SERIES_CONFIG, upto_vol=1)
    assert result["surfaces_missing_at_cutoff"] == []
    assert result["leak_rate"] == 0.0


def test_measure_candidate_mining_requires_a_gazetteer(sandbox):
    with pytest.raises(FileNotFoundError):
        IX.measure_candidate_mining("probe-fixture", SERIES_CONFIG, upto_vol=1)


def test_candidate_mining_ignores_epithet_sourced_surfaces(sandbox):
    """[24] PLAN_2026-09-14 B2's confound: `wiki gazetteer --merge-epithets` adds
    `source: "epithet_mining"` surface_forms to gazetteer.json directly (entities/gazetteer.py),
    without ever writing them to candidates.jsonl. A surface only mine_candidates could have
    produced is a real leak if a cutoff-only mine can't reach it; an epithet the LLM discovered
    from a whole-corpus scene pass never was mine_candidates' job in the first place, so it must
    never count as a `surfaces_missing_at_cutoff` leak even though it IS visible at the cutoff --
    otherwise this channel's clean 0.042 -> 0.000 gate-comparison number (LOG.md 2026-09-13) would
    silently be conflating the epithet channel with build-vs-render mining, exactly the confound
    docs/vision/PHASE_24.md's 2026-09-14 (late pm) entry found in the *entity-set* diff."""
    _write_parsed_volume(1, ["Holo spoke.", "Holo walked.", "Holo ran."])

    with paths.candidates().open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"surface": "Holo"}) + "\n")  # epithet never reaches candidates.jsonl
    gazetteer = {
        "entities": [{
            "entity_id": "holo",
            "canonical": "Holo",
            "type": "CHARACTER",
            "first_vol": 1,
            "surface_forms": [
                {"text": "Holo", "first_vol": 1},
                {"text": "the Wisewolf", "first_vol": 1, "source": "epithet_mining"},
            ],
        }],
        "volumes_covered": [1],
    }
    paths.gazetteer().write_text(json.dumps(gazetteer), encoding="utf-8")

    result = IX.measure_candidate_mining("probe-fixture", SERIES_CONFIG, upto_vol=1)
    assert result["cutoff_visible_surface_forms"] == 2  # "Holo" and "the Wisewolf" both visible
    assert result["surfaces_missing_at_cutoff"] == []  # but only "Holo" was ever mining's to lose
    assert result["leak_rate"] == 0.0


@pytest.mark.parametrize("override,cap,missing", [
    (None, 400, []), (3, 400, ["Alpha Person", "Beta Person"]),
    (None, 1, ["Beta Person"]),
])
def test_candidate_mining_replays_recorded_parameters(sandbox, override, cap, missing):
    import copy

    _write_parsed_volume(1, ["Alpha Person spoke.", "Alpha Person ran.",
                             "Beta Person spoke.", "Beta Person ran."])
    surfaces = ["Alpha Person", "Beta Person"]
    gaz = {"entities": [{"entity_id": s, "first_vol": 1, "surface_forms": [{"text": s}]}
                        for s in surfaces],
           "provenance": {"min_mentions": 2, "max_candidates_per_volume": cap}}
    paths.gazetteer().write_text(json.dumps(gaz), encoding="utf-8")
    paths.candidates().write_text("\n".join(json.dumps({"surface": s}) for s in surfaces), encoding="utf-8")
    config = copy.deepcopy(SERIES_CONFIG)
    result = IX.measure_candidate_mining("probe-fixture", config, 1, min_mentions=override)
    assert result["surfaces_missing_at_cutoff"] == missing
    assert result["mining_parameters"] == {
        "min_mentions": 2 if override is None else override, "max_candidates_per_volume": cap,
    }
    assert result["mining_parameter_sources"] == {
        "min_mentions": "gazetteer" if override is None else "explicit",
        "max_candidates_per_volume": "gazetteer",
    }
    assert config == SERIES_CONFIG


@pytest.mark.parametrize("missing", ["candidates", "volume-1", "volume-2"])
def test_candidate_mining_missing_inputs_are_errors(sandbox, missing):
    paths.gazetteer().write_text(json.dumps({"entities": []}), encoding="utf-8")
    if missing != "candidates":
        paths.candidates().write_text("", encoding="utf-8")
    for vol in (1, 2):
        if missing != f"volume-{vol}":
            _write_parsed_volume(vol, ["Some prose."])
    candidate, vocabulary = probe_report.run_index_channel("probe-fixture", SERIES_CONFIG, [2])
    assert "error" in candidate and "leak_rate" not in candidate
    assert vocabulary["probe"] == "vocabulary_exposure"


@pytest.mark.parametrize("threshold", [-1, True, "2", None])
def test_candidate_mining_invalid_provenance_is_error_row(sandbox, threshold):
    paths.gazetteer().write_text(json.dumps({"entities": [], "provenance": {"min_mentions": threshold}}), encoding="utf-8")
    candidate, vocabulary = probe_report.run_index_channel("probe-fixture", SERIES_CONFIG, [1])
    assert "Invalid candidate-mining min_mentions" in candidate["error"]
    assert vocabulary["probe"] == "vocabulary_exposure"


def test_index_runner_preserves_errors_for_corrupt_gazetteer(sandbox):
    paths.gazetteer().write_text("{broken", encoding="utf-8")
    rows = probe_report.run_index_channel("probe-fixture", SERIES_CONFIG, [1, 2])
    assert len(rows) == 4
    assert all("error" in row for row in rows)


def test_measure_vocabulary_exposure_flags_future_entity_mentions_and_claims(sandbox):
    _write_parsed_volume(1, ["Ally spoke to Rival."])
    gazetteer = {
        "entities": [
            {
                "entity_id": "ally",
                "canonical": "Ally",
                "type": "CHARACTER",
                "first_vol": 1,
                "surface_forms": [{"text": "Ally", "first_vol": 1}],
            },
            {
                "entity_id": "rival",
                "canonical": "Rival",
                "type": "CHARACTER",
                "first_vol": 2,  # introduced in v2 -- the vocabulary a cutoff-1 index should not have
                "surface_forms": [{"text": "Rival", "first_vol": 2}],
            },
        ],
        "volumes_covered": [1, 2],
    }
    paths.gazetteer().write_text(json.dumps(gazetteer), encoding="utf-8")
    with paths.mentions().open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"para_id": "v01:c01:p0000", "vol": 1, "entity_id": "ally", "surface": "Ally", "start": 0, "end": 4}) + "\n")
        fh.write(json.dumps({"para_id": "v01:c01:p0000", "vol": 1, "entity_id": "rival", "surface": "Rival", "start": 14, "end": 19}) + "\n")
    claims_path = paths.claims_volume(1)
    claims_path.parent.mkdir(parents=True, exist_ok=True)
    with claims_path.open("w", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "claim_id": "c1",
                    "subject": "ally",
                    "first_vol": 1,
                    "evidence": [{"para_id": "v01:c01:p0000", "quote": "Ally spoke to Rival."}],
                }
            )
            + "\n"
        )

    result = IX.measure_vocabulary_exposure("probe-fixture", upto_vol=1)
    assert result["future_surface_forms"] == 1
    assert result["future_vocabulary_mentions"] == 1  # the "Rival" mention
    assert result["in_scope_mentions"] == 2
    assert result["cutoff_claims"] == 1
    assert result["claims_resting_on_future_vocabulary_paragraph"] == 1  # c1 cites the tainted paragraph
    assert result["tainted_claim_rate"] == pytest.approx(1.0)


def test_run_index_channel_reports_missing_files_instead_of_raising(sandbox):
    rows = probe_report.run_index_channel("probe-fixture", SERIES_CONFIG, cutoffs=[1])
    assert len(rows) == 2
    assert all("error" in row for row in rows)


@pytest.mark.parametrize("scene_only", [False, True])
def test_vocabulary_exposure_includes_scene_claims_and_merges_duplicate_evidence(sandbox, scene_only):
    paths.gazetteer().write_text(json.dumps({"entities": [
        {"entity_id": "future", "first_vol": 2, "surface_forms": [{"text": "Future"}]}
    ]}), encoding="utf-8")
    paths.mentions().write_text(json.dumps({"vol": 1, "entity_id": "future", "surface": "Future",
                                         "para_id": "tainted"}), encoding="utf-8")
    legacy = [{"claim_id": "shared", "first_vol": 1, "evidence": [{"para_id": "clean"}]}]
    scenes = [
        {"claim_id": "shared", "first_vol": 1, "evidence": [{"para_id": "tainted"}]},
        {"claim_id": "scene-only", "first_vol": 1, "evidence": [{"para_id": "tainted"}]},
        {"claim_id": "clean", "first_vol": 1, "evidence": [{"para_id": "clean"}]},
        {"claim_id": "after-cutoff", "first_vol": 2, "evidence": [{"para_id": "tainted"}]},
    ]
    if not scene_only:
        paths.claims_volume(1).write_text("\n".join(map(json.dumps, legacy)), encoding="utf-8")
    paths.scene_claims_volume(1).write_text("\n".join(map(json.dumps, scenes)), encoding="utf-8")
    result = IX.measure_vocabulary_exposure("probe-fixture", 1)
    assert result["cutoff_claims"] == 3
    assert result["claims_resting_on_future_vocabulary_paragraph"] == 2
    assert result["tainted_claim_ids"] == ["scene-only", "shared"]
    assert result["tainted_claim_rate"] == pytest.approx(2 / 3)
    assert result["claim_files"] == (
        ([] if scene_only else [paths.relative(paths.claims_volume(1))])
        + [paths.relative(paths.scene_claims_volume(1))]
    )


@pytest.mark.parametrize("missing", ["mentions", "volume-1", "volume-2", None])
def test_vocabulary_exposure_distinguishes_absent_inputs_from_empty_files(sandbox, missing):
    paths.gazetteer().write_text(json.dumps({"entities": []}), encoding="utf-8")
    if missing != "mentions":
        paths.mentions().write_text("", encoding="utf-8")
    for vol in (1, 2):
        if missing != f"volume-{vol}":
            paths.scene_claims_volume(vol).write_text("", encoding="utf-8")
    _, row = probe_report.run_index_channel("probe-fixture", SERIES_CONFIG, [2])
    if missing:
        assert "error" in row and "tainted_claim_rate" not in row
    else:
        assert row["cutoff_claims"] == 0
        assert row["tainted_claim_rate"] == 0.0
        assert row["tainted_claim_ids"] == []


def test_write_jsonl_round_trips(tmp_path):
    rows = [{"a": 1}, {"b": 2}]
    out = tmp_path / "sub" / "out.jsonl"
    probe_report.write_jsonl(rows, out)
    lines = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    assert lines == rows


# ---------------------------------------------------------------------------
# [24] cli.probe_run's provenance wiring + audit/reports.py's probe report
# (docs/vision/plans/0008-pre-full-scale-audit.md S5 -- probe_run previously never touched
# provenance.start_run and there was no `wiki audit probe` report at all)
# ---------------------------------------------------------------------------


class _FakeProbeSettings:
    series_id = "probe-fixture"
    series = SERIES_CONFIG
    # provenance.start_run's _config_hashes reads these directly when given a settings object,
    # instead of falling back to load_settings(series_id) -- which would need a real
    # config/series.probe-fixture.yaml on disk. See config.Settings for the real shape.
    extraction: dict = {}
    schema_overrides: dict = {}
    schema_only: set = set()
    schema_skip: set = set()

    def volume_numbers(self) -> list[int]:
        return [1]


def _report_settings():
    from narrativewiki.config import Settings

    return Settings(series_id="probe-fixture", series={}, models={}, extraction={})


def test_probe_run_registers_provenance_and_writes_canonical_path(sandbox, monkeypatch):
    import typer
    from narrativewiki import cli, provenance

    _write_parsed_volume(1, ["Some prose."])
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeProbeSettings())

    with pytest.raises(typer.Exit) as exc:
        cli.probe_run(channel="index", volumes="1")
    assert exc.value.exit_code == 1

    manifest = provenance.last_run_for_stage("probe")
    assert manifest is not None
    assert manifest["outcome"] == "failed"
    canonical = probe_report.probe_report_path(manifest["run_id"])
    assert canonical.is_file()
    rows = [json.loads(l) for l in canonical.read_text(encoding="utf-8").splitlines()]
    # No gazetteer/claims exist in this sandbox -- both probes report a clean "can't measure this"
    # error row rather than raising, same as test_run_index_channel_reports_missing_files_instead_of_raising.
    assert len(rows) == 2
    assert all("error" in row for row in rows)


def test_probe_report_stage_not_ready_without_any_run(sandbox):
    from rich.console import Console

    from narrativewiki.audit import reports

    with pytest.raises(reports.StageNotReady):
        reports.run("probe", _report_settings(), Console(record=True))


def test_probe_report_ok_when_every_row_measures_cleanly(sandbox):
    from rich.console import Console

    from narrativewiki import provenance
    from narrativewiki.audit import reports

    run = provenance.start_run(
        "probe-fixture", "probe", scope="index:v1-1", volumes=[1], volume_scope=1,
        settings=_report_settings(),
    )
    rows = [
        {"channel": "L_build", "probe": "candidate_mining", "series": "probe-fixture", "upto_vol": 1, "leak_rate": 0.25},
        {"channel": "L_build", "probe": "vocabulary_exposure", "series": "probe-fixture", "upto_vol": 1,
         "tainted_claim_rate": 0.0, "future_surface_form_rate": 0.0},
    ]
    probe_report.write_jsonl(rows, probe_report.probe_report_path(run.run_id))
    run.finish("ok")

    console = Console(record=True, width=200)
    ok = reports.run("probe", _report_settings(), console)
    out = console.export_text()
    assert ok is True
    assert "candidate_mining" in out
    assert "0.250" in out


def test_probe_report_fails_on_an_error_row(sandbox):
    from rich.console import Console

    from narrativewiki import provenance
    from narrativewiki.audit import reports

    run = provenance.start_run(
        "probe-fixture", "probe", scope="index:v1-1", volumes=[1], volume_scope=1,
        settings=_report_settings(),
    )
    rows = [{"channel": "L_build", "probe": "candidate_mining", "series": "probe-fixture",
             "upto_vol": 1, "error": "No gazetteer.json"}]
    probe_report.write_jsonl(rows, probe_report.probe_report_path(run.run_id))
    run.finish("ok")

    console = Console(record=True, width=200)
    ok = reports.run("probe", _report_settings(), console)
    out = console.export_text()
    assert ok is False
    assert "No gazetteer.json" in out


def _leak_graph(claims, entities=()):
    from narrativewiki.graph import store

    conn = store.connect()
    store.write_entities(conn, entities)
    store.write_claims(conn, [
        {"claim_id": f"claim-{i}", "subject": "subject", "predicate": "BACKGROUND",
         "kind": "trait", "first_vol": 2, "confidence": 1.0, "polarity": "asserted",
         "evidence": [], "source": "fixture", **claim}
        for i, claim in enumerate(claims)
    ])
    conn.close()


def _write_page(entity_id, cutoff, page):
    path = paths.page_json(entity_id, cutoff)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(page), encoding="utf-8")


@pytest.mark.parametrize("page", [
    {"lead": "A hidden treasure was found."},
    {"prose": {"background": {"text": "A hidden treasure was found."}, "personality": None}},
    {"fields": {"occupation": {"value": "hidden treasure hunter"}}},
    {"fields": {"title": [{"value": "guardian of the hidden treasure"}]}},
    {"fields": {"relationships": [{"blurb": "Seeks the hidden treasure"}]}},
    {"fields": {"affiliations": [{"role": "hidden treasure keeper"}]}},
])
def test_future_fact_leak_detects_each_visible_text_field(sandbox, page):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": "hidden treasure"}])
    # The match can be on another character's page, not just the future claim's subject.
    _write_page("another-character", 1, page)
    result = measure_future_fact_leak("probe-fixture", 1)
    matches = result.pop("matches")
    assert len(result.pop("artifact_pages")) == 1
    assert result.pop("diagnostic_counts") == {"prior_fact": 0, "within_word": 0, "other_page": 1}
    assert result == {
        "channel": "L_query", "probe": "future_fact_leak", "series": "probe-fixture",
        "upto_vol": 1, "future_claims_total": 1, "leaked_count": 1,
        "future_fact_leak_rate": 1.0,
    }
    assert len(matches) == 1
    match = matches[0]
    assert match["claim_id"] == "claim-0"
    assert match["subject"] == "subject" and match["first_vol"] == 2
    assert match["search_value"] == "hidden treasure"
    location, = match["locations"]
    assert location["page"] == paths.relative(paths.page_json("another-character", 1))
    assert location["entity_id"] == "another-character"
    text = page
    for token in location["field"].split("/")[1:]:
        text = text[int(token)] if isinstance(text, list) else text[token]
    assert location["text"] == text
    assert text[location["start"]:location["end"]] == "hidden treasure"


def test_future_fact_leak_does_not_match_case_changes_metadata_or_future_pages(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": "Secret"}])
    _write_page("subject", 1, {"lead": "secret", "canonical": "Secret", "prose": None,
                               "fields": {"age": None}})
    _write_page("future-only", 2, {"lead": "Secret"})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["future_claims_total"] == 1
    assert result["leaked_count"] == 0
    assert result["future_fact_leak_rate"] == 0.0
    assert result["matches"] == []


def test_future_fact_leak_zero_future_claims(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": "Secret"}])
    _write_page("subject", 2, {"lead": "Secret"})
    result = measure_future_fact_leak("probe-fixture", 2)
    assert result["future_claims_total"] == result["leaked_count"] == 0
    assert result["future_fact_leak_rate"] == 0.0
    assert result["matches"] == []


def test_future_fact_leak_uses_nearest_page_and_prefers_exact_cutoff(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": "Secret", "first_vol": 3}])
    _write_page("subject", 1, {"lead": "Secret"})
    result = measure_future_fact_leak("probe-fixture", 2)
    assert result["leaked_count"] == 1
    assert result["matches"][0]["locations"][0]["page"] == paths.relative(
        paths.page_json("subject", 1)
    )
    _write_page("subject", 2, {"lead": "Nothing revealed"})
    assert measure_future_fact_leak("probe-fixture", 2)["leaked_count"] == 0


def test_future_fact_leak_resolves_objects_skips_missing_and_counts_claims(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([
        {"kind": "relation", "object": "target"},
        {"kind": "relation", "object": "missing"},
        {"value": "Canonical Name"},
        {"value": "Absent"},
        {"value": None, "object": None},
    ], entities=[{"entity_id": "target", "canonical": "Canonical Name", "type": "CHARACTER",
                  "first_vol": 2, "importance": 1.0}])
    _write_page("subject", 1, {"lead": "Canonical Name"})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["future_claims_total"] == 3
    assert result["leaked_count"] == 2
    assert result["future_fact_leak_rate"] == pytest.approx(2 / 3)
    assert [m["claim_id"] for m in result["matches"]] == ["claim-0", "claim-2"]
    assert result["matches"][0]["object"] == "target"
    assert result["matches"][0]["search_value"] == "Canonical Name"


def test_run_leak_channel_missing_graph_does_not_create_database(sandbox):
    rows = probe_report.run_leak_channel("probe-fixture", [1, 2])
    assert [row["upto_vol"] for row in rows] == [1, 2]
    assert all(row["probe"] == "future_fact_leak" and "error" in row for row in rows)
    assert not paths.graph_db().exists()


def test_leak_probe_does_not_migrate_an_existing_database(sandbox):
    import sqlite3

    # Enough schema to measure an empty future set, deliberately lacking every other
    # table. A measuring command must not silently upgrade this legacy artifact.
    conn = sqlite3.connect(paths.graph_db())
    conn.execute("CREATE TABLE claims (claim_id TEXT, first_vol INTEGER)")
    conn.commit()
    conn.close()
    _write_page("subject", 1, {})
    before = (paths.graph_db().read_bytes(), paths.graph_db().stat().st_mtime_ns)
    row, = probe_report.run_leak_channel("probe-fixture", [1])
    assert row["future_claims_total"] == 0
    assert before == (paths.graph_db().read_bytes(), paths.graph_db().stat().st_mtime_ns)


def test_graph_read_only_connection_rejects_writes_and_handles_escaped_paths(tmp_path):
    import sqlite3
    from contextlib import closing
    from narrativewiki.graph import store

    target = tmp_path / "graph # one.db"
    with closing(store.connect(target)) as conn:
        assert conn.execute("SELECT count(*) FROM claims").fetchone()[0] == 0
    with closing(store.connect(target, read_only=True)) as conn:
        assert conn.execute("SELECT count(*) AS n FROM claims").fetchone()["n"] == 0
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM claims")


def test_graph_read_only_missing_database_does_not_create_parent(tmp_path):
    import sqlite3
    from narrativewiki.graph import store

    target = tmp_path / "absent" / "graph.db"
    with pytest.raises(sqlite3.OperationalError):
        store.connect(target, read_only=True)
    assert not target.parent.exists()


def test_leak_runner_records_corrupt_page_and_continues_cutoffs(sandbox):
    _leak_graph([{"value": "Secret"}])
    _write_page("subject", 1, {"lead": "Secret"})
    paths.page_json("subject", 1).write_text("{broken", encoding="utf-8")
    _write_page("subject", 2, {"lead": "Secret"})
    rows = probe_report.run_leak_channel("probe-fixture", [1, 2])
    assert "error" in rows[0] and "future_fact_leak_rate" not in rows[0]
    assert rows[1]["future_fact_leak_rate"] == 0.0


@pytest.mark.parametrize("channel", ["index", "leak", "disclosure"])
def test_probe_cli_error_rows_fail_run_but_preserve_json_output(sandbox, monkeypatch, tmp_path, channel):
    from typer.testing import CliRunner
    from narrativewiki import cli, provenance

    _write_parsed_volume(1, ["Some prose."])
    monkeypatch.setattr(cli, "_settings", lambda *args, **kwargs: _FakeProbeSettings())
    copy = tmp_path / "errors.jsonl"
    result = CliRunner().invoke(cli.app, ["probe", "run", channel, "--volumes", "1",
                                         "--series", "probe-fixture", "--json", str(copy)])
    assert result.exit_code == 1, result.output
    manifest = provenance.last_run_for_stage("probe")
    assert manifest["outcome"] == "failed"
    assert "probe measurement(s) failed" in manifest["error"]
    canonical = probe_report.probe_report_path(manifest["run_id"])
    assert canonical.read_bytes() == copy.read_bytes()
    assert all("error" in json.loads(line) for line in copy.read_text().splitlines())


def test_leak_cli_writes_provenance_and_optional_json_copy(sandbox, monkeypatch, tmp_path):
    from narrativewiki import cli, provenance

    _leak_graph([{"value": "Secret"}])
    _write_page("subject", 1, {"lead": "Secret"})
    _write_parsed_volume(1, ["Some prose."])
    monkeypatch.setattr(cli, "_settings", lambda series, model=None, set_=None: _FakeProbeSettings())
    copy = tmp_path / "copy.jsonl"
    cli.probe_run(channel="leak", volumes="1", json_out=str(copy))
    manifest = provenance.last_run_for_stage("probe")
    assert manifest["outcome"] == "ok"
    canonical = probe_report.probe_report_path(manifest["run_id"])
    assert canonical.read_bytes() == copy.read_bytes()
    assert json.loads(copy.read_text())["leaked_count"] == 1
    assert json.loads(copy.read_text())["matches"][0]["claim_id"] == "claim-0"


def test_leak_witness_first_occurrence_counts_claim_once_across_repeated_pages(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": "Secret"}])
    _write_page("a", 1, {"lead": "A Secret, then Secret again."})
    _write_page("b", 1, {"lead": "Secret"})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["leaked_count"] == len(result["matches"]) == 1
    match, = result["matches"]
    location, = match["locations"]
    assert location["entity_id"] == "a"
    assert location["start"] == match["corpus_start"] == 2
    assert location["end"] == match["corpus_end"] == 8


def test_leak_witness_preserves_joined_corpus_and_unicode_offsets(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    # The original measurement can match across synthetic newlines. Keep those hits
    # auditable instead of silently changing the existing denominator or matching rule.
    _leak_graph([{"value": "秘密\nWolf"}, {"value": "Wolf\n\nTail"}])
    _write_page("a", 1, {"lead": "A 秘密", "prose": {"a~/b": {"text": "Wolf"}}})
    _write_page("b", 1, {})
    _write_page("c", 1, {"fields": {"nickname": [{"value": "Tail"}]}})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["leaked_count"] == 2
    corpus = "A 秘密\nWolf\n\nTail"
    for match in result["matches"]:
        assert corpus[match["corpus_start"]:match["corpus_end"]] == match["search_value"]
        assert len(match["locations"]) == 2
        for location in match["locations"]:
            base = location["corpus_start"]
            assert corpus[base:base + len(location["text"])] == location["text"]
    assert result["matches"][0]["locations"][1]["field"] == "/prose/a~0~1b/text"
    assert result["matches"][1]["locations"][1]["entity_id"] == "c"


def test_leak_witness_retains_empty_literal_measurement(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": ""}])
    _write_page("subject", 1, {})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["leaked_count"] == 1
    match, = result["matches"]
    assert match["search_value"] == ""
    assert match["corpus_start"] == match["corpus_end"] == 0
    assert match["locations"] == []


@pytest.mark.parametrize("layout", ["absent", "empty", "future-only"])
@pytest.mark.parametrize("cutoff", [1, 2])
def test_leak_runner_rejects_missing_cutoff_artifacts(sandbox, layout, cutoff):
    _leak_graph([{"value": "Secret"}])
    if layout == "empty":
        paths.PAGES_DIR.mkdir(parents=True, exist_ok=True)
    elif layout == "future-only":
        _write_page("subject", cutoff + 1, {"lead": "Secret"})
    row, = probe_report.run_leak_channel("probe-fixture", [cutoff])
    assert "No cutoff-visible page artifacts" in row["error"]
    assert "future_fact_leak_rate" not in row
    assert "leaked_count" not in row


def test_leak_artifact_inventory_includes_nonmatching_and_empty_pages(sandbox):
    import hashlib
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": "Secret"}])
    _write_page("z", 1, {})
    _write_page("a", 1, {"lead": "Secret"})
    _write_page("a", 2, {"lead": "Nothing revealed"})
    _write_page("future-only", 3, {"lead": "Secret"})
    result = measure_future_fact_leak("probe-fixture", 2)
    selected = [paths.page_json("a", 2), paths.page_json("z", 1)]
    assert result["artifact_pages"] == [
        {"page": paths.relative(p), "entity_id": p.parent.name,
         "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in selected
    ]
    assert result["leaked_count"] == 0
    original_digest = result["artifact_pages"][0]["sha256"]
    _write_page("a", 2, {"lead": "Edited after measurement"})
    updated = measure_future_fact_leak("probe-fixture", 2)
    assert updated["artifact_pages"][0]["sha256"] != original_digest


def test_leak_cli_missing_pages_records_failure_and_continues(sandbox, monkeypatch, tmp_path):
    from typer.testing import CliRunner
    from narrativewiki import cli, provenance

    _leak_graph([{"value": "Secret"}])
    _write_page("subject", 2, {"lead": "Secret"})
    for vol in (1, 2):
        _write_parsed_volume(vol, ["Some prose."])
    settings = _FakeProbeSettings()
    monkeypatch.setattr(settings, "volume_numbers", lambda: [1, 2])
    monkeypatch.setattr(cli, "_settings", lambda *args, **kwargs: settings)
    copy = tmp_path / "incomplete.jsonl"
    result = CliRunner().invoke(cli.app, ["probe", "run", "leak", "--volumes", "1-2",
                                         "--series", "probe-fixture", "--json", str(copy)])
    assert result.exit_code == 1, result.output
    manifest = provenance.last_run_for_stage("probe")
    assert manifest["outcome"] == "failed"
    assert copy.read_bytes() == probe_report.probe_report_path(manifest["run_id"]).read_bytes()
    first, second = [json.loads(line) for line in copy.read_text().splitlines()]
    assert "No cutoff-visible page artifacts" in first["error"]
    assert "future_fact_leak_rate" not in first
    assert second["future_fact_leak_rate"] == 0.0
    assert len(second["artifact_pages"]) == 1
    audit = _audit_probe_cli(monkeypatch)
    assert audit.exit_code == 1, audit.output
    assert "No cutoff-visible page artifacts" in " ".join(audit.output.split())


def _record_probe_rows(scope, rows):
    from narrativewiki import provenance

    run = provenance.start_run("probe-fixture", "probe", scope=scope, volumes=[1, 2],
                               volume_scope=2, settings=_report_settings())
    probe_report.write_jsonl(rows, probe_report.probe_report_path(run.run_id))
    run.finish("ok")
    return run


def _audit_probe_cli(monkeypatch):
    from typer.testing import CliRunner
    from narrativewiki import cli

    monkeypatch.setattr(cli, "_settings", lambda *args, **kwargs: _report_settings())
    return CliRunner().invoke(cli.app, ["audit", "probe", "--series", "probe-fixture"])


def test_probe_audit_aggregates_separate_channel_runs(sandbox, monkeypatch):
    _record_probe_rows("index:v1-2", [
        {"probe": "candidate_mining", "upto_vol": 1, "leak_rate": 0.25},
        {"probe": "vocabulary_exposure", "upto_vol": 1, "tainted_claim_rate": 0.0},
    ])
    _record_probe_rows("leak:v1-2", [
        {"probe": "future_fact_leak", "upto_vol": 1, "future_fact_leak_rate": 0.5},
    ])
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 0, result.output
    for name in ("candidate_mining", "vocabulary_exposure", "future_fact_leak"):
        assert f"probe: {name}" in " ".join(result.output.split())
    assert "Aggregated from 2 probe run(s)" in result.output
    assert "3 row(s) after dedup." in result.output


def test_probe_audit_newer_result_replaces_only_matching_key(sandbox, monkeypatch):
    _record_probe_rows("leak:v1-2", [
        {"probe": "future_fact_leak", "upto_vol": 1, "future_fact_leak_rate": 0.25},
        {"probe": "future_fact_leak", "upto_vol": 2, "future_fact_leak_rate": 0.5},
    ])
    _record_probe_rows("leak:v1-2", [
        {"probe": "future_fact_leak", "upto_vol": 1, "future_fact_leak_rate": 0.75},
    ])
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 0, result.output
    assert "0.750" in result.output and "0.500" in result.output
    assert "0.250" not in result.output
    assert "2 row(s) after dedup." in result.output


def test_probe_audit_skips_missing_run_file_and_keeps_newest_error(sandbox, monkeypatch):
    _record_probe_rows("leak:v1-1", [
        {"probe": "future_fact_leak", "upto_vol": 1, "future_fact_leak_rate": 0.25},
    ])
    _record_probe_rows("leak:v1-1", [
        {"probe": "future_fact_leak", "upto_vol": 1, "error": "Missing graph"},
    ])
    missing = _record_probe_rows("index:v1-1", [])
    probe_report.probe_report_path(missing.run_id).unlink()
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 1
    assert "Missing graph" in result.output and "0.250" not in result.output
    assert "Aggregated from 3 probe run(s)" in result.output


@pytest.mark.parametrize("missing", [False, True])
def test_probe_audit_without_any_measurements_cannot_report_success(sandbox, monkeypatch, missing):
    run = _record_probe_rows("leak:v1-2", [])
    if missing:
        probe_report.probe_report_path(run.run_id).unlink()
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 2, result.output  # existing StageNotReady CLI convention
    assert "No probe measurement rows available" in result.output
    assert "every requested cutoff measured cleanly" not in result.output


@pytest.mark.parametrize("text,value,expected", [
    ("female", "male", True),
    ("malevolent", "male", True),
    ("male", "male", False),
    ("(male).", "male", False),
    ("_male", "male", True),
    ("Émale", "male", True),
    ("Secret", "", False),
])
def test_leak_word_boundary_diagnostic_preserves_literal_score(sandbox, text, value, expected):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": value}])
    _write_page("subject", 1, {"lead": text})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["leaked_count"] == 1
    assert result["matches"][0]["within_word"] is expected
    assert result["diagnostic_counts"]["within_word"] == int(expected)


@pytest.mark.parametrize("changed", [
    {"subject": "someone-else"}, {"predicate": "APPEARANCE"}, {"kind": "attribute"},
    {"object": "another-target"}, {"value": "different"}, {"qualifier": "former"},
    {"polarity": "denied"}, {"polarity": "presumed"},
])
def test_leak_prior_fact_requires_same_complete_identity(sandbox, changed):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([{"value": "Secret", "first_vol": 1, **changed}, {"value": "Secret"}])
    _write_page("subject", 1, {"lead": "Secret"})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["matches"][0]["prior_claim_ids"] == []
    assert result["diagnostic_counts"]["prior_fact"] == 0


def test_leak_diagnostics_overlap_and_prior_evidence_is_cutoff_scoped(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([
        {"value": "male", "first_vol": 1},
        {"value": "male", "first_vol": 1},
        {"value": "male"},
        {"value": "Secret"},
        {"value": "Secret", "first_vol": 3},
    ])
    _write_page("another", 1, {"lead": "female and Secret"})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["leaked_count"] == 3  # repeated later observations still count separately
    assert result["matches"][0]["prior_claim_ids"] == ["claim-0", "claim-1"]
    assert result["matches"][1]["prior_claim_ids"] == []
    assert result["matches"][2]["prior_claim_ids"] == []
    assert result["diagnostic_counts"] == {"prior_fact": 1, "within_word": 1, "other_page": 3}


def test_leak_relation_prior_fact_uses_entity_identity(sandbox):
    from narrativewiki.probe.channels.leak import measure_future_fact_leak

    _leak_graph([
        {"kind": "relation", "object": "target", "first_vol": 1},
        {"kind": "relation", "object": "target"},
    ], entities=[{"entity_id": "target", "canonical": "Secret", "type": "CHARACTER",
                  "first_vol": 1, "importance": 1.0}])
    _write_page("subject", 1, {"lead": "Secret"})
    result = measure_future_fact_leak("probe-fixture", 1)
    assert result["matches"][0]["prior_claim_ids"] == ["claim-0"]
    assert result["matches"][0]["other_page"] is False


def test_probe_audit_displays_diagnostics_alongside_legacy_rows(sandbox, monkeypatch):
    _record_probe_rows("leak:v1-2", [
        {"probe": "future_fact_leak", "upto_vol": 1, "future_fact_leak_rate": 0.5,
         "artifact_pages": [{"page": "example/v01.json", "entity_id": "example",
                             "sha256": "fixture"}],
         "diagnostic_counts": {"prior_fact": 3, "within_word": 2, "other_page": 4}},
        {"probe": "future_fact_leak", "upto_vol": 2, "future_fact_leak_rate": 0.0},
    ])
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 0, result.output
    output = " ".join(result.output.split())
    assert "prior fact=3, within word=2, other page=4" in output
    assert "Diagnostics overlap" in output
    assert "t=2 first-match diagnostics" not in output
    assert "t=1 artifact coverage: 1 page file(s) searched" in output
    assert "t=2 artifact coverage" not in output


def test_probe_audit_exposes_assumed_mining_parameters(sandbox, monkeypatch):
    _record_probe_rows("index:v1-2", [
        {"probe": "candidate_mining", "upto_vol": 1, "leak_rate": 0.0,
         "mining_parameters": {"min_mentions": 3, "max_candidates_per_volume": 400},
         "mining_parameter_sources": {"min_mentions": "legacy_default",
                                      "max_candidates_per_volume": "series_config"}},
        {"probe": "candidate_mining", "upto_vol": 2, "leak_rate": 0.0},
    ])
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 0, result.output
    output = " ".join(result.output.split())
    assert "min_mentions=3 (legacy_default)" in output
    assert "WARNING: min_mentions is assumed" in output
    assert "t=2 mining parameters" not in output


def test_probe_audit_displays_vocabulary_claim_coverage(sandbox, monkeypatch):
    _record_probe_rows("index:v1-2", [
        {"probe": "vocabulary_exposure", "upto_vol": 1, "tainted_claim_rate": 0.5,
         "cutoff_claims": 2, "claims_resting_on_future_vocabulary_paragraph": 1,
         "claim_files": ["v01.jsonl", "scene_v01.jsonl"], "tainted_claim_ids": ["c1"]},
        {"probe": "vocabulary_exposure", "upto_vol": 2, "tainted_claim_rate": 0.0},
    ])
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 0, result.output
    output = " ".join(result.output.split())
    assert "t=1 claim coverage: 2 unique claims from 2 file(s); 1 cite future-vocabulary paragraphs" in output
    assert "t=2 claim coverage" not in output


def test_disclosure_separates_exact_and_normalized_occurrence_and_excludes_future_entities(sandbox):
    from narrativewiki.probe.channels.disclosure import measure_surface_disclosure

    surfaces = ["The Gran Mur", "Gran Mur", "Later", "Never"]
    gaz = {"entities": [
        {"entity_id": "visible", "first_vol": 1,
         "surface_forms": [{"text": s, "first_vol": 2} for s in surfaces]},
        {"entity_id": "duplicate", "first_vol": 1, "surface_forms": [{"text": "Gran Mur"}]},
        {"entity_id": "future", "first_vol": 2, "surface_forms": [{"text": "Future Only"}]},
    ]}
    paths.gazetteer().write_text(json.dumps(gaz), encoding="utf-8")
    _write_parsed_volume(1, ["秘密 the Gran Mur appears.", "Gran Mur again."])
    _write_parsed_volume(2, ["The Gran Mur. Later."])
    first = measure_surface_disclosure("probe-fixture", 1)
    assert first["cutoff_visible_surface_forms"] == 4
    assert first["unseeable_exact"] == ["Later", "Never", "The Gran Mur"]
    assert first["unseeable_normalised"] == ["Later", "Never"]
    assert first["unseeable_exact_rate"] == 0.75
    assert first["unseeable_normalised_rate"] == 0.5
    occurrences = {r["surface"]: r for r in first["occurrences"]}
    assert occurrences["Gran Mur"]["first_exact"] == {"vol": 1, "start": 7, "end": 15}
    assert occurrences["The Gran Mur"]["first_normalised"] == {"vol": 1, "start": 7, "end": 15}
    second = measure_surface_disclosure("probe-fixture", 2)
    occurrences = {r["surface"]: r for r in second["occurrences"]}
    assert occurrences["The Gran Mur"]["first_exact"]["vol"] == 2
    assert occurrences["Gran Mur"]["first_exact"]["vol"] == 1
    assert second["unseeable_exact"] == ["Future Only", "Never"]


def test_disclosure_empty_vocabulary_is_zero_not_division_error(sandbox):
    from narrativewiki.probe.channels.disclosure import measure_surface_disclosure

    paths.gazetteer().write_text(json.dumps({"entities": []}), encoding="utf-8")
    _write_parsed_volume(1, [])
    row = measure_surface_disclosure("probe-fixture", 1)
    assert row["cutoff_visible_surface_forms"] == 0
    assert row["unseeable_exact_rate"] == row["unseeable_normalised_rate"] == 0.0
    assert row["occurrences"] == []


def test_disclosure_requires_entire_reading_prefix_and_keeps_valid_cutoffs(sandbox):
    paths.gazetteer().write_text(json.dumps({"entities": []}), encoding="utf-8")
    _write_parsed_volume(1, ["Some prose."])
    rows = probe_report.run_disclosure_channel("probe-fixture", [1, 2])
    assert rows[0]["unseeable_exact_rate"] == 0.0
    assert "error" in rows[1] and "unseeable_exact_rate" not in rows[1]


def test_disclosure_cli_records_rows_and_aggregates_with_index(sandbox, monkeypatch, tmp_path):
    from typer.testing import CliRunner
    from narrativewiki import cli, provenance

    _record_probe_rows("index:v1-1", [{"probe": "candidate_mining", "upto_vol": 1, "leak_rate": 0.0}])
    paths.gazetteer().write_text(json.dumps({"entities": []}), encoding="utf-8")
    _write_parsed_volume(1, ["Some prose."])
    monkeypatch.setattr(cli, "_settings", lambda *args, **kwargs: _FakeProbeSettings())
    copy = tmp_path / "disclosure.jsonl"
    result = CliRunner().invoke(cli.app, ["probe", "run", "disclosure", "--volumes", "1",
                                         "--series", "probe-fixture", "--json", str(copy)])
    assert result.exit_code == 0, result.output
    run = provenance.last_run_for_stage("probe")
    assert run["outcome"] == "ok" and run["scope"] == "disclosure:v1-1"
    assert copy.read_bytes() == probe_report.probe_report_path(run["run_id"]).read_bytes()
    audit = _audit_probe_cli(monkeypatch)
    assert audit.exit_code == 0, audit.output
    output = " ".join(audit.output.split())
    assert "first_occurrence" in output and "candidate_mining" in output
    assert "unseeable_exact_rate" in output and "unseeable_normalised_rate" in output


def test_probe_audit_same_second_run_replaces_older_result_by_start_time(sandbox, monkeypatch):
    from datetime import datetime, timezone
    from narrativewiki import provenance

    monkeypatch.setattr(provenance, "_now", lambda: datetime(2026, 9, 15, microsecond=100, tzinfo=timezone.utc))
    _record_probe_rows("z-old", [{"probe": "future_fact_leak", "upto_vol": 1, "future_fact_leak_rate": 0.75}])
    monkeypatch.setattr(provenance, "_now", lambda: datetime(2026, 9, 15, microsecond=200, tzinfo=timezone.utc))
    _record_probe_rows("a-new", [{"probe": "future_fact_leak", "upto_vol": 1, "error": "Newest cutoff unavailable"}])
    result = _audit_probe_cli(monkeypatch)
    assert result.exit_code == 1, result.output
    assert "Newest cutoff unavailable" in result.output
    assert "0.750" not in result.output
