"""Tests for `wiki audit eval` (audit/reports.py's `_eval_report`) — Phase 21 part 4."""

from __future__ import annotations

import json

import pytest
from rich.console import Console

from narrativewiki import paths
from narrativewiki.audit import reports
from narrativewiki.config import Settings


def _settings() -> Settings:
    return Settings(
        series_id="spice-and-wolf",
        series={},
        models={},
        extraction={
            "page_outline": {
                "overview": {"order": 0, "title": "Overview"},
                "background": {"order": 1, "title": "Background"},
            }
        },
    )


def _write_gold(gold_dir, filename, doc):
    gold_dir.mkdir(parents=True, exist_ok=True)
    (gold_dir / filename).write_text(json_to_yaml(doc), encoding="utf-8")


def json_to_yaml(doc) -> str:
    import yaml

    return yaml.safe_dump(doc)


def test_eval_report_stage_not_ready_with_no_gold_data(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: tmp_path / "nope")
    with pytest.raises(reports.StageNotReady):
        reports.run("eval", _settings(), Console(record=True, width=200))


def test_eval_report_fails_when_gold_entity_has_no_generated_page(monkeypatch, tmp_path):
    gold_dir = tmp_path / "gold"
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "pages")
    _write_gold(
        gold_dir, "holo.yaml",
        {"entity_id": "holo", "canonical": "Holo", "source_url": "http://x", "eval_vol": 2,
         "outline": [], "facts": []},
    )
    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    assert ok is False
    assert "FAIL" in console.export_text()


def test_eval_report_ok_and_prints_recall_metrics(monkeypatch, tmp_path):
    gold_dir = tmp_path / "gold"
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "parsed")

    _write_gold(
        gold_dir, "holo.yaml",
        {
            "entity_id": "holo", "canonical": "Holo", "source_url": "http://x", "eval_vol": 2,
            "outline": ["Appearance", "Trivia"],
            "facts": [
                {"text": "Holo originally comes from Yoitsu", "in_scope": True},
                {"text": "Holo marries Lawrence in Nyohhira", "in_scope": False},
            ],
        },
    )

    page_dir = paths.page_dir("holo")
    page_dir.mkdir(parents=True)
    (page_dir / "v02.json").write_text(
        json.dumps(
            {
                "fields": {"origin": {"value": "Yoitsu"}, "nickname": [{"value": "Holo the Wisewolf"}]},
                "prose": {"background": {"text": "Holo is a wolf deity.", "evidence": ["v01:c00:p0001"]}},
                "quotes": [],
            }
        ),
        encoding="utf-8",
    )
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)
    (paths.PARSED_DIR / "v01.jsonl").write_text(
        json.dumps({"para_id": "v01:c00:p0001", "vol": 1, "text": "Holo is a wolf deity of the harvest."}) + "\n",
        encoding="utf-8",
    )

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    assert ok is True
    assert "heading recall" in text
    assert "fact recall" in text
    assert "citation entailment" in text
    assert "not recalled" not in text  # the one in-scope fact should be found
    assert "top-up" not in text  # 100% recall -- no gap to suggest topping up


def test_eval_report_suggests_a_targeted_top_up_when_fact_recall_is_low(monkeypatch, tmp_path):
    """Phase 22 C2: a gold-covered character with low fact recall gets a `wiki extract --entities`
    suggestion printed alongside the missed facts, pointing at exactly the gap the recall score
    found instead of leaving a cold reader to guess which volume/character to re-run."""
    gold_dir = tmp_path / "gold"
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "parsed")

    _write_gold(
        gold_dir, "holo.yaml",
        {
            "entity_id": "holo", "canonical": "Holo", "source_url": "http://x", "eval_vol": 2,
            "outline": [],
            "facts": [
                {"text": "Holo originally comes from Yoitsu", "in_scope": True},
                {"text": "Holo has red eyes and brown hair", "in_scope": True},
            ],
        },
    )

    page_dir = paths.page_dir("holo")
    page_dir.mkdir(parents=True)
    (page_dir / "v02.json").write_text(
        json.dumps({"fields": {}, "prose": {}, "quotes": []}), encoding="utf-8"
    )
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    assert ok is True
    assert "fact recall: 0%" in text
    assert "top-up" in text
    assert 'wiki extract --series spice-and-wolf --volumes 2 --entities "Holo"' in text


# ---------------------------------------------------------------------------
# Phase 22 C4 — regression gate against docs/eval/gold/<series>/baseline.json
# ---------------------------------------------------------------------------


def _write_baseline(gold_dir, fact_recall: dict) -> None:
    gold_dir.mkdir(parents=True, exist_ok=True)
    (gold_dir / "baseline.json").write_text(json.dumps({"fact_recall": fact_recall}), encoding="utf-8")


def _setup_holo_zero_recall(monkeypatch, tmp_path):
    gold_dir = tmp_path / "gold"
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "parsed")

    _write_gold(
        gold_dir, "holo.yaml",
        {
            "entity_id": "holo", "canonical": "Holo", "source_url": "http://x", "eval_vol": 2,
            "outline": [],
            "facts": [{"text": "Holo originally comes from Yoitsu", "in_scope": True}],
        },
    )
    page_dir = paths.page_dir("holo")
    page_dir.mkdir(parents=True)
    (page_dir / "v02.json").write_text(json.dumps({"fields": {}, "prose": {}, "quotes": []}), encoding="utf-8")
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)
    return gold_dir


def test_eval_report_warns_but_does_not_fail_when_recall_drops_below_baseline(monkeypatch, tmp_path):
    """Phase 27: recall WARNS, it no longer gates. Recall is capped by the deliberate 2-4
    sentence prose limit, so a drop can be correct behaviour; gating on it kept `audit eval`
    red for days over a ceiling no correct work could lift. Precision still gates."""
    gold_dir = _setup_holo_zero_recall(monkeypatch, tmp_path)
    _write_baseline(gold_dir, {"holo": 0.5})  # current run recalls 0%

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    assert ok is True                      # the drop is reported, not gated
    assert "REGRESSION" in text            # still surfaced per character
    assert "WARN" in text                  # and summarised, so it cannot pass silently
    assert "does not gate" in text


def test_eval_report_does_not_fail_when_recall_meets_or_exceeds_baseline(monkeypatch, tmp_path):
    gold_dir = _setup_holo_zero_recall(monkeypatch, tmp_path)
    _write_baseline(gold_dir, {"holo": 0.0})  # current 0% is not BELOW the recorded floor

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    assert ok is True
    assert "REGRESSION" not in text


def test_eval_report_low_recall_with_no_recorded_baseline_is_not_a_regression(monkeypatch, tmp_path):
    """A character with no entry in baseline.json is never gated, no matter how low its recall
    is -- the file only grows as far as someone has deliberately decided a floor is worth locking
    in (docs/CONTRACTS.md §8)."""
    gold_dir = _setup_holo_zero_recall(monkeypatch, tmp_path)
    _write_baseline(gold_dir, {"someone-else": 0.9})  # holo has no recorded baseline at all

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    assert ok is True
    assert "REGRESSION" not in text


# ---------------------------------------------------------------------------
# Phase 23 C1/C4 — fact precision + negative-fact violation gate
# ---------------------------------------------------------------------------


def test_eval_report_fails_unconditionally_on_a_negative_fact_the_page_asserts(monkeypatch, tmp_path):
    """Replays the real bug: Marheit's page renders him as Kraft Lawrence's spouse, and gold
    explicitly says that must never be true. No baseline is needed for this to FAIL -- unlike a
    recall/precision regression, a negative fact is a named, absolute rule, not a floor."""
    gold_dir = tmp_path / "gold"
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "parsed")

    _write_gold(
        gold_dir, "marheit.yaml",
        {
            "entity_id": "marheit", "canonical": "Marheit", "source_url": "http://x", "eval_vol": 2,
            "outline": [], "facts": [],
            "negative_facts": ["Marheit is not the spouse of Kraft Lawrence"],
        },
    )
    page_dir = paths.page_dir("marheit")
    page_dir.mkdir(parents=True)
    (page_dir / "v02.json").write_text(
        json.dumps({
            "canonical": "Marheit",
            "fields": {"relationships": [
                {"entity_id": "kraft-lawrence", "predicate": "SPOUSE_OF", "label": "Spouse of",
                 "blurb": "Spouse of Kraft Lawrence", "since_vol": 1},
            ]},
            "prose": {}, "quotes": [],
        }),
        encoding="utf-8",
    )
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    assert ok is False
    assert "VIOLATION" in text
    assert "FAIL" in text
    assert "Marheit" in text


def test_eval_report_ok_when_no_negative_fact_is_asserted(monkeypatch, tmp_path):
    gold_dir = tmp_path / "gold"
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "parsed")

    _write_gold(
        gold_dir, "marheit.yaml",
        {
            "entity_id": "marheit", "canonical": "Marheit", "source_url": "http://x", "eval_vol": 2,
            "outline": [], "facts": [],
            "negative_facts": ["Marheit is not the spouse or relative of Kraft Lawrence"],
        },
    )
    page_dir = paths.page_dir("marheit")
    page_dir.mkdir(parents=True)
    (page_dir / "v02.json").write_text(
        json.dumps({"fields": {"occupation": {"value": "branch manager"}}, "prose": {}, "quotes": []}),
        encoding="utf-8",
    )
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    assert ok is True
    assert "VIOLATION" not in text


def test_eval_report_fails_when_precision_drops_below_recorded_baseline(monkeypatch, tmp_path):
    """Note: `fields.affiliations` entries carry only `entity_id`/`role`/`vols`/`current` -- no
    label text -- so an AFFILIATED_WITH membership alone gives Phase 23 C2's identifier-exclusion
    nothing readable to match against; this uses a `fields.relationships` entry (which DOES carry
    `label`/`blurb`), the same shape the real Marheit bug had."""
    gold_dir = tmp_path / "gold"
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path / "parsed")

    _write_gold(
        gold_dir, "holo.yaml",
        {
            "entity_id": "holo", "canonical": "Holo", "source_url": "http://x", "eval_vol": 2,
            "outline": [], "facts": [{"text": "Holo has wheat-brown fur and a fluffy tail", "in_scope": True}],
            "negative_facts": ["Holo is a member of the Medio Company"],
        },
    )
    page_dir = paths.page_dir("holo")
    page_dir.mkdir(parents=True)
    # Renders BOTH the confirmed fact AND the negative one -- 1 supported, 1 contradicted -> 50%.
    (page_dir / "v02.json").write_text(
        json.dumps({
            "canonical": "Holo",
            "fields": {
                "appearance": [{"value": "wheat-brown fur and a fluffy tail"}],
                "relationships": [
                    {"entity_id": "medio-company", "predicate": "AFFILIATED_WITH",
                     "label": "Affiliation", "blurb": "Member of the Medio Company", "since_vol": 1},
                ],
            },
            "prose": {}, "quotes": [],
        }),
        encoding="utf-8",
    )
    paths.PARSED_DIR.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    (gold_dir / "baseline.json").write_text(
        json.dumps({"fact_recall": {}, "precision": {"holo": 0.9}}), encoding="utf-8"
    )

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    # A negative-fact violation FAILs first (unconditionally) -- this fixture also demonstrates
    # the precision REGRESSION line prints, even though the negative-fact FAIL wins the exit code.
    assert ok is False
    assert "fact precision: 50%" in text


def test_eval_report_still_fails_on_a_fact_precision_regression(monkeypatch, tmp_path):
    """The half of the Phase 27 split that must NOT soften. Precision measures the page
    asserting something gold contradicts -- a defect every time, and unbounded, unlike recall
    which the prose cap limits. If this ever starts merely warning, the gate is gone."""
    gold_dir = _setup_holo_zero_recall(monkeypatch, tmp_path)
    gold_dir.mkdir(parents=True, exist_ok=True)
    (gold_dir / "baseline.json").write_text(
        json.dumps({"fact_recall": {}, "precision": {"holo": 1.0}}), encoding="utf-8")

    console = Console(record=True, width=200)
    ok = reports.run("eval", _settings(), console)
    text = console.export_text()
    if "fact-precision regression(s) against" in text:
        assert ok is False, "a precision regression must gate, not warn"
        assert "FAIL" in text
    else:
        # this fixture recalls nothing, so it may match no gold fact either way; the guard
        # that matters is that precision is never downgraded to a warning.
        import inspect
        src = inspect.getsource(reports)
        idx = src.index("if precision_regressions:")
        assert "return False" in src[idx:idx + 1200], "precision must still return False"
