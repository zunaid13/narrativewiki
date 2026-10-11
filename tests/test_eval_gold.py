"""Tests for eval/gold.py — Phase 21 part 4, the hand-transcribed-gold-data evaluation harness."""

from __future__ import annotations

import json

from narrativewiki import paths
from narrativewiki.eval import gold as G


# ---------------------------------------------------------------------------
# load_gold
# ---------------------------------------------------------------------------


def test_load_gold_returns_empty_list_when_dir_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: tmp_path / "does-not-exist")
    assert G.load_gold("some-series") == []


def test_load_gold_parses_yaml_files_sorted_by_entity_id(monkeypatch, tmp_path):
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    (gold_dir / "zed.yaml").write_text(
        "entity_id: zed\ncanonical: Zed\nsource_url: http://example.com/zed\neval_vol: 2\n"
        "outline: [Appearance]\nfacts:\n  - text: 'Zed exists.'\n    in_scope: true\n",
        encoding="utf-8",
    )
    (gold_dir / "amy.yaml").write_text(
        "entity_id: amy\ncanonical: Amy\nsource_url: http://example.com/amy\neval_vol: 1\n"
        "outline: []\nfacts: []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)

    entries = G.load_gold("some-series")
    assert [e.entity_id for e in entries] == ["amy", "zed"]  # sorted, not file order
    zed = entries[1]
    assert zed.canonical == "Zed"
    assert zed.eval_vol == 2
    assert zed.outline == ["Appearance"]
    assert zed.facts == [G.GoldFact(text="Zed exists.", in_scope=True)]


# ---------------------------------------------------------------------------
# load_baseline (Phase 22 C4)
# ---------------------------------------------------------------------------


def test_load_baseline_returns_empty_dict_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: tmp_path / "does-not-exist")
    assert G.load_baseline("some-series") == {}


def test_load_baseline_reads_fact_recall_map(monkeypatch, tmp_path):
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    (gold_dir / "baseline.json").write_text(
        json.dumps({"_comment": "ignored", "fact_recall": {"holo": 0.4, "jakob": 0.0}}), encoding="utf-8"
    )
    monkeypatch.setattr(paths, "eval_gold_dir", lambda series_id: gold_dir)

    assert G.load_baseline("some-series") == {"holo": 0.4, "jakob": 0.0}


# ---------------------------------------------------------------------------
# nearest_page_at_or_below
# ---------------------------------------------------------------------------


def test_nearest_page_at_or_below_walks_downward(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    d = paths.page_dir("holo")
    d.mkdir(parents=True)
    (d / "v01.json").write_text(json.dumps({"upto_vol": 1}), encoding="utf-8")
    # No v02.json/v03.json -- v03 was cache-skipped upstream.

    assert G.nearest_page_at_or_below("holo", 3) == {"upto_vol": 1}


def test_nearest_page_at_or_below_returns_none_when_nothing_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    assert G.nearest_page_at_or_below("nobody", 3) is None


# ---------------------------------------------------------------------------
# score_heading_recall
# ---------------------------------------------------------------------------


def test_score_heading_recall_matches_known_aliases_and_counts_gaps():
    result = G.score_heading_recall(
        ["Appearance", "Personality", "Trivia"],
        ["overview", "personality", "background", "relationships"],
    )
    assert result["recall"] == 2 / 3
    matched = {h["heading"]: h["matched"] for h in result["headings"]}
    assert matched == {"Appearance": True, "Personality": True, "Trivia": False}


def test_score_heading_recall_no_gold_headings_returns_none_recall():
    result = G.score_heading_recall([], ["overview"])
    assert result["recall"] is None
    assert result["headings"] == []


# ---------------------------------------------------------------------------
# score_fact_recall
# ---------------------------------------------------------------------------


def _page(fields=None, prose=None, quotes=None, canonical=None, traits=None):
    return {
        "fields": fields or {},
        "traits": traits or {},
        "prose": prose or {},
        "quotes": quotes or [],
        "canonical": canonical,
    }


def test_score_fact_recall_excludes_out_of_scope_facts():
    facts = [
        G.GoldFact(text="Holo originally comes from Yoitsu", in_scope=True),
        G.GoldFact(text="Holo marries Lawrence in Nyohhira", in_scope=False),
    ]
    page = _page(fields={"nickname": [{"value": "Holo the Wisewolf"}], "origin": {"value": "Yoitsu"}})
    result = G.score_fact_recall(facts, page)
    assert len(result["facts"]) == 1  # the out-of-scope fact never enters the denominator
    assert result["facts"][0]["found"] is True


def test_score_fact_recall_marks_unfound_fact_when_no_keyword_overlap():
    facts = [G.GoldFact(text="Holo despises apples and always has", in_scope=True)]
    page = _page(fields={"origin": {"value": "Yoitsu"}})
    result = G.score_fact_recall(facts, page)
    assert result["facts"][0]["found"] is False
    assert result["recall"] == 0.0


def test_score_fact_recall_none_when_no_in_scope_facts():
    facts = [G.GoldFact(text="Out of scope thing", in_scope=False)]
    result = G.score_fact_recall(facts, _page())
    assert result["recall"] is None
    assert result["facts"] == []


def test_score_fact_recall_reads_prose_and_quotes_text_too():
    facts = [G.GoldFact(text="Lawrence discovers Holo sleeping in his wagon", in_scope=True)]
    page = _page(prose={"chronology": {"text": "Lawrence discovers Holo sleeping in his wagon bed."}})
    result = G.score_fact_recall(facts, page)
    assert result["facts"][0]["found"] is True


def test_score_fact_recall_reads_trait_only_content():
    facts = [G.GoldFact(text="Shin excels at long-range marksmanship", in_scope=True)]
    page = _page(
        canonical="Shin",
        traits={
            "abilities": [
                {
                    "value": "excels at long-range marksmanship",
                    "predicate": "SKILL",
                    "polarity": "asserted",
                    "since_vol": 1,
                    "show_vol": False,
                    "evidence": ["v01:c00:p0001"],
                }
            ]
        },
    )

    result = G.score_fact_recall(facts, page)

    assert result["recall"] == 1.0
    assert result["facts"][0]["found"] is True
    assert "marksmanship" in G.page_chunks(page)[0]  # structured semantic-eval chunk too


# ---------------------------------------------------------------------------
# score_fact_precision (Phase 23 C1) + the _page_text identifier leak fix (Phase 23 C2)
# ---------------------------------------------------------------------------


def test_page_text_excludes_predicate_and_entity_id_from_relationship_fields():
    """Phase 23 C2: the raw predicate constant and entity_id slug inside a rendered relationship
    entry must never land in the keyword bag -- only its human-readable label/note/blurb."""
    page = _page(fields={"relationships": [
        {"entity_id": "kraft-lawrence", "predicate": "SPOUSE_OF", "label": "Spouse of",
         "note": None, "blurb": "Spouse of", "since_vol": 1, "show_vol": True,
         "current": True, "vol_end": None},
    ]})
    text = G._page_text(page)
    assert "kraft-lawrence" not in text
    assert "SPOUSE_OF" not in text
    assert "Spouse" in text  # the human-readable label/blurb still counts


def test_score_fact_precision_flags_a_negative_fact_the_page_asserts():
    """Replays the real bug: Marheit's page renders a Spouse-of-Kraft-Lawrence relationship, and
    the gold file says that must never be true. Negative facts require FULL keyword coverage
    (Phase 23 Part F) -- including the specific relationship word ("spouse"), not just the two
    names, which is why `canonical` matters here too (a real page mentions its own subject by
    name in prose; this minimal fixture has none, so it must be supplied explicitly)."""
    page = _page(canonical="Marheit", fields={"relationships": [
        {"entity_id": "kraft-lawrence", "predicate": "SPOUSE_OF", "label": "Spouse of",
         "blurb": "Spouse of Kraft Lawrence", "since_vol": 1},
    ]})
    result = G.score_fact_precision(
        facts=[], negative_facts=["Marheit is not the spouse of Kraft Lawrence"], page=page
    )
    assert result["contradicted"] == 1
    assert result["negative_facts"][0]["contradicted"] is True
    assert result["precision"] == 0.0


def test_score_fact_precision_requires_the_specific_relationship_word_not_just_the_names():
    """Phase 23 Part F, live finding: two characters legitimately related through some OTHER real
    predicate (here COMRADE_OF) must NOT trip a negative fact about a different, unasserted
    relationship (here "relative") just because their two names co-occur -- 15 of 17 violations
    one real V1-2 re-run produced were exactly this false-positive shape, none of them the genuine
    SPOUSE_OF bug the test above replays."""
    page = _page(canonical="Marheit", fields={"relationships": [
        {"entity_id": "kraft-lawrence", "predicate": "COMRADE_OF", "label": "Comrade of",
         "blurb": "fellow traders", "since_vol": 1},
    ]})
    result = G.score_fact_precision(
        facts=[], negative_facts=["Marheit is not a relative of Kraft Lawrence"], page=page
    )
    assert result["contradicted"] == 0
    assert result["negative_facts"][0]["contradicted"] is False


def test_score_fact_precision_is_1_when_page_only_asserts_confirmed_facts():
    facts = [G.GoldFact(text="Marheit manages the Milone Trading Company branch", in_scope=True)]
    page = _page(fields={"occupation": {"value": "manages the Milone Trading Company branch"}})
    result = G.score_fact_precision(facts=facts, negative_facts=["Marheit is Kraft Lawrence's spouse"], page=page)
    assert result["supported"] == 1
    assert result["contradicted"] == 0
    assert result["precision"] == 1.0


def test_score_fact_precision_none_when_gold_has_no_opinion():
    result = G.score_fact_precision(facts=[], negative_facts=[], page=_page())
    assert result["precision"] is None
    assert result["supported"] == 0
    assert result["contradicted"] == 0


def test_score_fact_precision_a_predicate_string_alone_no_longer_manufactures_a_false_match():
    """Before Phase 23 C2's _page_text fix, the raw string "SPOUSE_OF" or the entity_id
    "kraft-lawrence" landing in the keyword bag could make an unrelated negative fact whose text
    happens to share those tokens look contradicted even when no genuine label ever rendered it
    as a relationship. With the identifier keys excluded, only real label/note/blurb text counts."""
    page = _page(fields={"relationships": [
        {"entity_id": "kraft-lawrence", "predicate": "SPOUSE_OF", "label": "Spouse of",
         "blurb": None, "since_vol": 1},
    ]})
    # A negative fact phrased using words that only appear in the raw identifiers, not the label.
    result = G.score_fact_precision(facts=[], negative_facts=["kraft-lawrence SPOUSE_OF nothing else here"], page=page)
    assert result["contradicted"] == 0


# ---------------------------------------------------------------------------
# score_citation_entailment
# ---------------------------------------------------------------------------


def test_score_citation_entailment_flags_dangling_citation(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    page = _page(prose={"background": {"text": "Holo is a wolf deity.", "evidence": ["v01:c00:p9999"]}})
    result = G.score_citation_entailment(page)
    assert result["sections"][0]["dangling_citations"] == ["v01:c00:p9999"]
    assert result["sections"][0]["grounded"] is False


def test_score_citation_entailment_grounded_when_paragraph_shares_vocabulary(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    (tmp_path / "v01.jsonl").write_text(
        json.dumps({"para_id": "v01:c00:p0001", "vol": 1, "text": "Holo is a wolf deity of the harvest."}) + "\n",
        encoding="utf-8",
    )
    page = _page(prose={"background": {"text": "Holo is a wolf deity.", "evidence": ["v01:c00:p0001"]}})
    result = G.score_citation_entailment(page)
    sec = result["sections"][0]
    assert sec["dangling_citations"] == []
    assert sec["grounded"] is True


def test_score_citation_entailment_skips_sections_with_no_text():
    page = _page(prose={"background": None, "personality": {"text": None}})
    result = G.score_citation_entailment(page)
    assert result["sections"] == []


def test_score_citation_entailment_beat_summary_check_grounds_uncited_chronology(monkeypatch, tmp_path):
    """A chronology section with EMPTY evidence (its events had no state_change/quote -- the
    Norah Arendt case Phase 21 part 4's eval harness found) must still be scored 'grounded' when
    the caller supplies events_conn/entity_id/vol, via the event's own core_para_ids -- never
    written into the page's own evidence field (synth/prose.py::generate_chronology)."""
    from narrativewiki.graph import events as events_db

    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    (tmp_path / "v01.jsonl").write_text(
        json.dumps({"para_id": "v01:c00:p0001", "vol": 1, "text": "Holo boards the merchant's cart at dawn."}) + "\n",
        encoding="utf-8",
    )
    conn = events_db.connect(tmp_path / "events.db")
    events_db.write_events(conn, [{
        "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
        "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
        "beat_summary": "Holo boards the cart.", "core_para_ids": ["v01:c00:p0001"],
        "vol_start": 1, "confidence": 0.8, "source": "test",
    }])

    page = _page(prose={"chronology": {"text": "Holo boards the merchant's cart at dawn.", "evidence": []}})
    result = G.score_citation_entailment(
        page, events_conn=conn, entity_id="holo", vol=1, events_source_keys={"chronology"},
    )
    conn.close()

    sec = result["sections"][0]
    assert sec["dangling_citations"] == []
    assert sec["evidence_count"] == 0
    assert sec["beat_summary_checked"] is True
    assert sec["beat_summary_grounded"] is True
    assert sec["grounded"] is True


def test_score_citation_entailment_beat_summary_check_only_applies_to_events_sourced_sections(monkeypatch, tmp_path):
    """A section NOT in events_source_keys (e.g. background) must not be widened by the
    beat_summary check even when events_conn is supplied -- it stays evidence-only."""
    from narrativewiki.graph import events as events_db

    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    conn = events_db.connect(tmp_path / "events.db")
    events_db.write_events(conn, [{
        "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
        "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
        "beat_summary": "Holo boards the cart.", "core_para_ids": ["v01:c00:p0001"],
        "vol_start": 1, "confidence": 0.8, "source": "test",
    }])

    page = _page(prose={"background": {"text": "Holo is a wolf deity.", "evidence": []}})
    result = G.score_citation_entailment(
        page, events_conn=conn, entity_id="holo", vol=1, events_source_keys={"chronology"},
    )
    conn.close()

    sec = result["sections"][0]
    assert sec["beat_summary_checked"] is False
    assert sec["grounded"] is False


# ---------------------------------------------------------------------------
# claim_keywords / annotate_missed_facts — Phase 26, the in-graph diagnosis bit
# ---------------------------------------------------------------------------


def _claims_conn(rows):
    """In-memory `claims` table with just the columns claim_keywords reads."""
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE claims (subject TEXT, predicate TEXT, object TEXT, "
                 "value TEXT, first_vol INTEGER, evidence_json TEXT)")
    conn.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?)", rows)
    return conn


def test_claim_keywords_excludes_claims_from_later_volumes():
    """CLAUDE.md §1: a diagnosis printed at cutoff N must not draw on volume N+1's text."""
    conn = _claims_conn([
        ("holo", "ORIGIN", None, "Yoitsu", 1, "[]"),
        ("holo", "STATUS", None, "married in Nyohhira", 5, "[]"),
    ])
    kw = G.claim_keywords(conn, "holo", 2)
    assert "yoitsu" in kw
    assert "nyohhira" not in kw  # volume 5 is past the cutoff and must not leak in


def test_claim_keywords_includes_evidence_quotes_and_predicate_words():
    conn = _claims_conn([
        ("jakob", "MENTOR_OF", "kraft-lawrence", None, 1,
         json.dumps([{"quote": "Jakob broke into a grin"}])),
    ])
    kw = G.claim_keywords(conn, "jakob", 2)
    assert {"mentor", "grin", "lawrence"} <= kw


def test_annotate_missed_facts_flags_only_unfound_facts_and_leaves_recall_alone():
    facts = [
        G.GoldFact(text="Holo originally comes from Yoitsu", in_scope=True),
        G.GoldFact(text="Holo despises apples and always has", in_scope=True),
    ]
    page = _page(canonical="Holo", fields={"origin": {"value": "Yoitsu"}})
    result = G.score_fact_recall(facts, page)
    recall_before = result["recall"]
    assert [f["found"] for f in result["facts"]] == [True, False]

    conn = _claims_conn([("holo", "TRAIT", None, "despises apples always", 1, "[]")])
    G.annotate_missed_facts(result, G.claim_keywords(conn, "holo", 2))

    found, missed = result["facts"][0], result["facts"][1]
    assert "in_graph" not in found  # a recalled fact needs no diagnosis
    assert missed["in_graph"] is True  # the graph holds it; the page just did not print it
    assert result["recall"] == recall_before  # annotation must never move the gated number


# ---------------------------------------------------------------------------
# Phase 27 — semantic recall union (local MiniCheck, no OpenRouter quota)
# ---------------------------------------------------------------------------


def test_page_chunks_prefixes_sections_with_the_name_and_keeps_a_whole_page_chunk():
    """Sections use pronouns, so an entailment check needs the name attached; the whole-page
    chunk stays so a fact spanning two sections still has one document covering it."""
    page = _page(canonical="Holo", fields={"origin": {"value": "Yoitsu"}},
                 prose={"personality": {"text": "She is proud and teasing."}})
    chunks = G.page_chunks(page)
    assert any(c.startswith("Holo. She is proud") for c in chunks)
    assert any("Yoitsu" in c and "proud" in c for c in chunks)  # the whole-page chunk


def test_semantic_union_upgrades_a_miss_and_never_drops_a_lexical_hit():
    facts = [
        G.GoldFact(text="Holo originally comes from Yoitsu", in_scope=True),
        G.GoldFact(text="Holo dreams of becoming a tailor", in_scope=True),
    ]
    page = _page(canonical="Holo", fields={"origin": {"value": "Yoitsu"}},
                 prose={"background": {"text": "She wants to be a dressmaker."}})
    result = G.score_fact_recall(facts, page)
    assert [f["found"] for f in result["facts"]] == [True, False]

    # stands in for MiniCheck: the paraphrase entails, nothing else does
    def scorer(_docs, claim):
        return {"score": 0.98 if "tailor" in claim else 0.01}

    G.augment_recall_semantically(result, page, scorer)
    assert result["recall"] == 1.0
    assert result["facts"][1]["semantic"] is True
    assert result["facts"][0].get("semantic") is None  # a lexical hit is never relabelled
    assert result["semantic_upgrades"] == 1


def test_semantic_union_below_threshold_changes_nothing():
    facts = [G.GoldFact(text="Holo despises apples and always has", in_scope=True)]
    page = _page(canonical="Holo", fields={"origin": {"value": "Yoitsu"}})
    result = G.score_fact_recall(facts, page)
    before = result["recall"]
    G.augment_recall_semantically(result, page, lambda _d, _c: {"score": 0.49})
    assert result["recall"] == before == 0.0
    assert result["facts"][0]["found"] is False
    assert result["facts"][0]["semantic_score"] == 0.49  # recorded even when it does not qualify


def test_possessives_and_rendered_relationship_names_count_as_page_text():
    """[30] "Lutz's mother is Karla" missed a page rendering "Karla — Child of — mother": the
    possessive kept "lutz's" unmatched and the counterpart's name lived only in a skipped id."""
    from narrativewiki.eval.gold import GoldFact, score_fact_recall
    page = {"canonical": "Lutz", "fields": {"relationships": [
        {"entity_id": "karla", "predicate": "CHILD_OF", "label": "Child of", "note": "mother"}]}}
    result = score_fact_recall([GoldFact(text="Lutz's mother is Karla.", in_scope=True)], page)
    assert result["recall"] == 1.0
