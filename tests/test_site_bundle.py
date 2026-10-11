"""Tests for site/bundle.py — Phase 7, CONTRACTS §6."""

from __future__ import annotations

import json
import sqlite3

from narrativewiki import paths
from narrativewiki.entities.automaton import build_automaton
from narrativewiki.graph import events as EV
from narrativewiki.graph import store as ST
from narrativewiki.graph import temporal as TE
from narrativewiki.site import bundle as BU

ENTITY_TYPES = {
    "CHARACTER": {"route": "/character/{slug}"},
    "FACTION": {"route": "/codex/factions#{slug}", "codex": "factions"},
}

WINDOW_CFG = {
    "context_paragraphs_before": 1,
    "context_paragraphs_after": 1,
    "never_cross_hard_break": True,
    "max_windows_per_entity_per_volume": 40,
    "max_tokens_per_request": 6000,
    "merge_overlapping": True,
}


PAGE_OUTLINE = [
    {"key": "overview", "kind": "fields", "title": "Overview"},
    {"key": "affiliations", "kind": "affiliations", "title": "Affiliations"},
    {"key": "relationships", "kind": "relationships", "title": "Relationships"},
    {"key": "background", "kind": "prose", "title": "Background", "traits": ["BACKGROUND"]},
    {"key": "personality", "kind": "prose", "title": "Personality", "traits": ["PERSONALITY"]},
    {"key": "appearances", "kind": "derived", "title": "Appearances"},
]


RELATIONS_CFG = {
    "FRIEND_OF": {"symmetric": True, "display": "Friend of"},
    "ENEMY_OF": {"symmetric": True, "display": "Enemy of", "conflicts_with": ["FRIEND_OF"]},
    "RIVAL_OF": {"symmetric": True, "display": "Rival of"},
    "AFFILIATED_WITH": {"object_types": ["FACTION"], "display": "Affiliation", "membership": True},
}


class FakeSettings:
    series_id = "86"
    series_title = "86 -- EIGHTY-SIX"
    attributes = {"AGE": {"single": True, "display": "Age"}, "STATUS": {"single": True, "display": "Status"}}
    relations = RELATIONS_CFG
    entity_types = ENTITY_TYPES
    extraction = {"codex_pages": {"factions": {"title": "Factions", "types": ["FACTION"]}}, "extraction": {"window": WINDOW_CFG}}
    prose_config = {"codex_summary": {"max_sentences": 1}}
    page_outline = PAGE_OUTLINE

    @property
    def extraction_behaviour(self):
        return self.extraction["extraction"]

    def route_for(self, entity_type, slug):
        return ENTITY_TYPES[entity_type]["route"].format(slug=slug)


def _entity(entity_id, canonical, entity_type, first_vol, importance=0.5, surface_forms=None):
    return {
        "entity_id": entity_id,
        "canonical": canonical,
        "type": entity_type,
        "first_vol": first_vol,
        "importance": importance,
        "aliases": [],
        "surface_forms": surface_forms or [{"text": canonical, "ambiguous": False, "first_vol": first_vol}],
    }


SHIN = _entity("shinei-nouzen", "Shinei Nouzen", "CHARACTER", 1, importance=1.0)
RAIDEN = _entity("raiden-shuga", "Raiden Shuga", "CHARACTER", 2, importance=0.5)
SPEARHEAD = _entity("spearhead-squadron", "Spearhead Squadron", "FACTION", 1, importance=0.3)
GRENADIER = _entity("grenadier-squadron", "Grenadier Squadron", "FACTION", 1, importance=0.3)

GAZ = {"entities": [SHIN, RAIDEN, SPEARHEAD]}
ENTITIES_BY_ID = {e["entity_id"]: e for e in GAZ["entities"]}


# ---------------------------------------------------------------------------
# Phase 23 B2: verdict-based withholding, mirrored from synth/assemble.py
# ---------------------------------------------------------------------------


def test_relation_entries_between_withholds_an_unsupported_interval():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    intervals = TE.assign_multi_valued(
        "marheit", "SPOUSE_OF",
        [{"value_or_object": "kraft-lawrence", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
        is_relation=True,
    )
    ST.write_intervals(conn, intervals)
    rows = TE.relations_between(conn, "marheit", "kraft-lawrence", 1)
    assert len(rows) == 1

    # No verdict yet (wiki verify never run) -- renders exactly as before.
    entries = BU._relation_entries_between(conn, rows, {"SPOUSE_OF": {"display": "Spouse of"}}, 1)
    assert len(entries) == 1

    # Flagged unsupported -- withheld.
    verdicts = {intervals[0]["interval_id"]: {"verdict": "unsupported"}}
    entries = BU._relation_entries_between(conn, rows, {"SPOUSE_OF": {"display": "Spouse of"}}, 1, verdicts)
    assert entries == []


def test_members_and_related_withholds_an_unsupported_membership():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    intervals = TE.assign_multi_valued(
        "holo", "AFFILIATED_WITH",
        [{"value_or_object": "medio-company", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
        is_relation=True,
    )
    ST.write_intervals(conn, intervals)
    entities_by_id = {"holo": {"entity_id": "holo", "type": "CHARACTER"}}
    relations_cfg = {"AFFILIATED_WITH": {"membership": True}}

    members, _related, _adversaries = BU._members_and_related(conn, "medio-company", 1, entities_by_id, relations_cfg)
    assert members == ["holo"]

    verdicts = {intervals[0]["interval_id"]: {"verdict": "unsupported"}}
    members, _related, _adversaries = BU._members_and_related(
        conn, "medio-company", 1, entities_by_id, relations_cfg, verdicts
    )
    assert members == []


def test_denied_relation_is_withheld_from_pair_and_codex_projections():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    ST.write_claims(conn, [{
        "claim_id": "c_denied", "subject": "shinei-nouzen", "predicate": "AFFILIATED_WITH",
        "kind": "relation", "object": "spearhead-squadron", "value": None,
        "qualifier": "member", "first_vol": 1, "confidence": 0.9, "polarity": "denied",
        "source": "test", "evidence": [{"para_id": "v01:c00:p0001", "quote": "not a member"}],
    }])
    intervals = TE.assign_multi_valued(
        "shinei-nouzen",
        "AFFILIATED_WITH",
        [{"value_or_object": "spearhead-squadron", "qualifier": "member", "first_vol": 1,
          "claim_id": "c_denied"}],
        is_relation=True,
    )
    ST.write_intervals(conn, intervals)
    rows = TE.relations_between(conn, "shinei-nouzen", "spearhead-squadron", 1)

    assert BU._relation_entries_between(conn, rows, RELATIONS_CFG, 1) == []
    members, _related, adversaries = BU._members_and_related(
        conn, "spearhead-squadron", 1, ENTITIES_BY_ID, RELATIONS_CFG
    )
    assert members == []
    assert adversaries == []


def test_expired_membership_is_not_a_current_codex_member():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    ST.write_intervals(conn, TE.assign_relation_supersession(
        "shinei-nouzen",
        "spearhead-squadron",
        [
            {"predicate": "AFFILIATED_WITH", "qualifier": "member", "first_vol": 1,
             "claim_ids": ["c_member"]},
            {"predicate": "ENEMY_OF", "qualifier": None, "first_vol": 2,
             "claim_ids": ["c_enemy"]},
        ],
    ))

    members, _related, adversaries = BU._members_and_related(
        conn, "spearhead-squadron", 2, ENTITIES_BY_ID, RELATIONS_CFG
    )

    assert members == []
    assert adversaries == ["shinei-nouzen"]


# ---------------------------------------------------------------------------
# index.json / links.json / search.json
# ---------------------------------------------------------------------------


def test_build_index_filters_by_cutoff_and_sorts_by_importance(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)  # no manifest.json here -> generic titles
    idx = BU.build_index(GAZ, FakeSettings(), upto_vol=1)
    assert [c["entity_id"] for c in idx["characters"]] == ["shinei-nouzen"]
    assert idx["upto_vol"] == 1
    assert idx["volumes"] == [{"vol": 1, "title": "Volume 1"}]
    assert idx["field_labels"]["attributes"]["age"] == "Age"
    assert idx["sections"] == [{"key": s["key"], "kind": s["kind"], "title": s["title"]} for s in PAGE_OUTLINE]

    idx2 = BU.build_index(GAZ, FakeSettings(), upto_vol=2)
    assert [c["entity_id"] for c in idx2["characters"]] == ["shinei-nouzen", "raiden-shuga"]


def test_build_links_excludes_entities_not_yet_revealed():
    links = BU.build_links(GAZ, FakeSettings(), upto_vol=1)
    assert set(links) == {"shinei-nouzen", "spearhead-squadron"}
    assert links["shinei-nouzen"] == {"route": "/character/shinei-nouzen", "canonical": "Shinei Nouzen", "type": "CHARACTER"}


def test_build_search_uses_each_surface_forms_own_first_vol():
    gaz = {
        "entities": [
            _entity(
                "shinei-nouzen", "Shinei Nouzen", "CHARACTER", 1,
                surface_forms=[
                    {"text": "Shinei Nouzen", "ambiguous": False, "first_vol": 1},
                    {"text": "Baleygr", "ambiguous": False, "first_vol": 3},
                ],
            )
        ]
    }
    entries_v1 = BU.build_search(gaz, FakeSettings(), upto_vol=1)
    assert [e["name"] for e in entries_v1] == ["Shinei Nouzen"]

    entries_v3 = BU.build_search(gaz, FakeSettings(), upto_vol=3)
    assert {e["name"] for e in entries_v3} == {"Shinei Nouzen", "Baleygr"}


# ---------------------------------------------------------------------------
# pages/<entity_id>.json
# ---------------------------------------------------------------------------


def _write_page(entity_id, vol, *, background=None):
    d = paths.page_dir(entity_id)
    d.mkdir(parents=True, exist_ok=True)
    page = {
        "entity_id": entity_id,
        "canonical": ENTITIES_BY_ID[entity_id]["canonical"],
        "upto_vol": vol,
        "claim_set_hash": f"hash_v{vol}",
        "fields": {},
        "prose": {"background": background, "personality": None},
        "mentions_of": [],
        "generated_by": None,
    }
    (d / f"v{vol:02d}.json").write_text(json.dumps(page), encoding="utf-8")


def test_pages_bundle_is_sparse_and_within_cutoff(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    _write_page("shinei-nouzen", 1)
    _write_page("shinei-nouzen", 3)  # v02 was cache-skipped upstream by synth/cache.py

    automaton = build_automaton(GAZ["entities"])
    result = BU.build_pages_bundle([SHIN], automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=2)

    assert set(result["shinei-nouzen"]["cutoffs"]) == {"1"}  # v03 excluded, upto_vol=2


def test_pages_bundle_wikifies_prose_and_excludes_self_link(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    _write_page(
        "shinei-nouzen", 2,
        background={"text": "Shinei Nouzen led Raiden Shuga into battle.", "evidence": ["v02:c00:p0001"]},
    )
    _write_page("raiden-shuga", 2)  # a link target only resolves when it has a page of its own

    automaton = build_automaton(GAZ["entities"])
    result = BU.build_pages_bundle([SHIN, RAIDEN], automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=2)

    text = result["shinei-nouzen"]["cutoffs"]["2"]["prose"]["background"]["text"]
    assert "[Raiden Shuga](/character/raiden-shuga)" in text
    assert "[Shinei Nouzen]" not in text  # self-link excluded


def test_pages_bundle_never_links_a_character_with_no_page_written(tmp_path, monkeypatch):
    """Phase 26 part B: the live v1-2 wiki shipped `[Jakob](../character/jakob.md)` in Lawrence's
    prose against no such file -- Jakob fell below `page_gate.min_claims`, so the roster, links
    and search bundles all excluded him (Phase 23 E6) but the wikify pass over prose did not, and
    `wiki audit links` failed on the dangling link."""
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    _write_page(
        "shinei-nouzen", 2,
        background={"text": "Shinei Nouzen led Raiden Shuga into battle.", "evidence": ["v02:c00:p0001"]},
    )  # no page written for raiden-shuga

    automaton = build_automaton(GAZ["entities"])
    result = BU.build_pages_bundle([SHIN, RAIDEN], automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=2)

    text = result["shinei-nouzen"]["cutoffs"]["2"]["prose"]["background"]["text"]
    assert text == "Shinei Nouzen led Raiden Shuga into battle."  # named, not linked


def test_character_with_no_page_directory_is_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_pages_bundle([RAIDEN], automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=2)
    assert result == {}


# ---------------------------------------------------------------------------
# Phase 23 E4: visible citations (para_id -> vol/print_page)
# ---------------------------------------------------------------------------


def test_citations_for_attaches_vol_and_print_page():
    print_pages = {"v02:c00:p0001": 47, "v02:c00:p0002": 48}
    citations = BU._citations_for(["v02:c00:p0001", "v02:c00:p0002"], print_pages)
    assert citations == [
        {"para_id": "v02:c00:p0001", "vol": 2, "print_page": 47},
        {"para_id": "v02:c00:p0002", "vol": 2, "print_page": 48},
    ]


def test_citations_for_missing_print_page_is_none_not_an_error():
    citations = BU._citations_for(["v01:c00:p0001"], {})
    assert citations == [{"para_id": "v01:c00:p0001", "vol": 1, "print_page": None}]


def test_pages_bundle_omits_citations_when_print_pages_not_passed(tmp_path, monkeypatch):
    """Backward compatible: no print_pages arg -> no `citations` key at all, byte-identical to
    the pre-E4 shape (an existing caller/test that doesn't know about E4 is unaffected)."""
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    _write_page(
        "shinei-nouzen", 2,
        background={"text": "Shinei Nouzen led Raiden Shuga into battle.", "evidence": ["v02:c00:p0001"]},
    )
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_pages_bundle([SHIN, RAIDEN], automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=2)
    entry = result["shinei-nouzen"]["cutoffs"]["2"]["prose"]["background"]
    assert "citations" not in entry


def test_pages_bundle_attaches_citations_when_print_pages_passed(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PAGES_DIR", tmp_path)
    _write_page(
        "shinei-nouzen", 2,
        background={"text": "Shinei Nouzen led Raiden Shuga into battle.", "evidence": ["v02:c00:p0001"]},
    )
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_pages_bundle(
        [SHIN, RAIDEN], automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=2,
        print_pages={"v02:c00:p0001": 47},
    )
    entry = result["shinei-nouzen"]["cutoffs"]["2"]["prose"]["background"]
    assert entry["citations"] == [{"para_id": "v02:c00:p0001", "vol": 2, "print_page": 47}]
    # evidence itself is untouched -- citations is purely additive (CONTRACTS §5 unchanged).
    assert entry["evidence"] == ["v02:c00:p0001"]


# ---------------------------------------------------------------------------
# Phase 23 E6: restrict roster/links/search to entity_ids with an actual page on disk
# ---------------------------------------------------------------------------


def test_build_index_excludes_character_with_no_written_page():
    written_ids = {"raiden-shuga"}  # shinei-nouzen has no page, despite first_vol <= upto_vol
    idx = BU.build_index(GAZ, FakeSettings(), upto_vol=2, written_ids=written_ids)
    assert [c["entity_id"] for c in idx["characters"]] == ["raiden-shuga"]


def test_build_index_written_ids_none_preserves_old_behaviour():
    idx = BU.build_index(GAZ, FakeSettings(), upto_vol=2, written_ids=None)
    assert {c["entity_id"] for c in idx["characters"]} == {"shinei-nouzen", "raiden-shuga"}


def test_build_links_excludes_character_with_no_written_page_but_keeps_faction():
    written_ids: set[str] = set()  # no character has a page
    links = BU.build_links(GAZ, FakeSettings(), upto_vol=1, written_ids=written_ids)
    assert set(links) == {"spearhead-squadron"}  # the FACTION is untouched by written_ids


def test_build_search_excludes_character_with_no_written_page():
    entries = BU.build_search(GAZ, FakeSettings(), upto_vol=2, written_ids={"raiden-shuga"})
    # shinei-nouzen (CHARACTER, no written page) excluded; spearhead-squadron (FACTION) untouched.
    assert {e["entity_id"] for e in entries} == {"raiden-shuga", "spearhead-squadron"}


# ---------------------------------------------------------------------------
# codex/factions.json
# ---------------------------------------------------------------------------


class FakeClient:
    def __init__(self, text="A First Ward squadron."):
        self.text = text
        self.calls = []

    def complete_json(self, stage, prompt, schema, system=None):
        self.calls.append({"stage": stage, "prompt": prompt})
        assert schema is BU.CodexSummary
        return schema(text=self.text)


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    return conn


def _record(vol, seq, text):
    return {"para_id": f"v{vol:02d}:c00:p{seq:04d}", "vol": vol, "text": text, "scene_break_before": "none"}


def _mention(vol, seq, entity_id):
    return {"para_id": f"v{vol:02d}:c00:p{seq:04d}", "vol": vol, "entity_id": entity_id, "surface": "x", "start": 0, "end": 1}


def _affiliate(conn, character_id, faction_id, vol):
    claim_id = f"c_{character_id}_{vol}"
    ST.write_claims(
        conn,
        [
            {
                "claim_id": claim_id, "subject": character_id, "predicate": "AFFILIATED_WITH", "kind": "relation",
                "object": faction_id, "value": None, "qualifier": "member", "first_vol": vol, "confidence": 0.9,
                "evidence": [{"para_id": f"v{vol:02d}:c00:p0001", "quote": "evidence"}], "polarity": "asserted", "source": "test",
            }
        ],
    )
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            character_id, "AFFILIATED_WITH",
            [{"value_or_object": faction_id, "qualifier": "member", "first_vol": vol, "claim_id": claim_id}],
            is_relation=True,
        ),
    )


# ---------------------------------------------------------------------------
# _cap_codex_evidence (Phase 22 B4)
# ---------------------------------------------------------------------------


def _window(mention_count, para_id, text="text"):
    return BU.Window(entity_id="e", vol=1, para_ids=(para_id,), text=text, mention_count=mention_count)


def test_cap_codex_evidence_respects_window_count_cap():
    windows = [_window(i, f"p{i}") for i in range(10)]
    capped = BU._cap_codex_evidence(windows, max_windows=3, max_tokens=10_000)
    assert len(capped) == 3
    assert {w.mention_count for w in capped} == {7, 8, 9}  # densest three kept


def test_cap_codex_evidence_respects_token_budget_even_under_window_cap():
    long_text = "word " * 2000  # far more than max_tokens on its own
    windows = [_window(5, "p0", long_text), _window(4, "p1", long_text), _window(3, "p2", "short")]
    capped = BU._cap_codex_evidence(windows, max_windows=5, max_tokens=500)
    assert len(capped) == 1  # only the densest window fits before the second would blow the budget


def test_cap_codex_evidence_always_keeps_at_least_the_densest_window():
    long_text = "word " * 5000
    windows = [_window(1, "p0", long_text)]
    capped = BU._cap_codex_evidence(windows, max_windows=5, max_tokens=10)
    assert len(capped) == 1  # a lone over-budget window is kept, not dropped to zero evidence


def test_cap_codex_evidence_sorts_output_by_para_id_not_density():
    windows = [_window(1, "p2"), _window(5, "p0"), _window(3, "p1")]
    capped = BU._cap_codex_evidence(windows, max_windows=5, max_tokens=10_000)
    assert [w.para_ids[0] for w in capped] == ["p0", "p1", "p2"]


def test_codex_bundle_generates_summary_with_evidence_and_members():
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    records_by_vol = {1: [_record(1, 1, "The Spearhead Squadron fought bravely.")]}
    mentions_by_vol = {1: [_mention(1, 1, "spearhead-squadron")]}
    client = FakeClient()
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, client, GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1, mentions_by_vol=mentions_by_vol,
        records_by_vol=records_by_vol,
    )

    entry = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]
    assert entry["summary"] == "A First Ward squadron."
    assert entry["evidence"] == ["v01:c00:p0001"]
    assert entry["members"] == ["shinei-nouzen"]
    assert len(client.calls) == 1
    conn.close()


def test_codex_bundle_skips_unchanged_cutoff_but_writes_on_membership_change():
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    # Same one mention in both volumes -- evidence text never changes.
    records_by_vol = {
        1: [_record(1, 1, "The Spearhead Squadron fought bravely.")],
        2: [_record(2, 1, "Quiet.")],
    }
    mentions_by_vol = {1: [_mention(1, 1, "spearhead-squadron")], 2: []}
    client = FakeClient()
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, client, GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2, mentions_by_vol=mentions_by_vol,
        records_by_vol=records_by_vol,
    )
    # Nothing changed between v1 and v2 (same evidence, same members) -> v2 is skipped.
    assert set(result["factions"]["spearhead-squadron"]["cutoffs"]) == {"1"}
    assert len(client.calls) == 1
    conn.close()

    # Now Raiden joins at v2 -- membership changed even though the summary evidence did not, so
    # v2 must get its own cutoff entry (site/bundle.py module docstring: the whole point of
    # _state_hash covering more than evidence).
    conn2 = _conn()
    _affiliate(conn2, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn2, "raiden-shuga", "spearhead-squadron", 2)
    client2 = FakeClient()
    result2 = BU.build_codex_bundles(
        conn2, client2, GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2, mentions_by_vol=mentions_by_vol,
        records_by_vol=records_by_vol,
    )
    cutoffs = result2["factions"]["spearhead-squadron"]["cutoffs"]
    assert set(cutoffs) == {"1", "2"}
    assert sorted(cutoffs["2"]["members"]) == ["raiden-shuga", "shinei-nouzen"]
    # Evidence (the summary's only real input) never changed between v1 and v2 -- only membership
    # did -- so the LLM must not be re-paid for an identical prompt (Phase 22 B4): one call total,
    # and v2 carries over v1's summary text/evidence verbatim.
    assert len(client2.calls) == 1
    assert cutoffs["2"]["summary"] == cutoffs["1"]["summary"]
    assert cutoffs["2"]["evidence"] == cutoffs["1"]["evidence"]
    conn2.close()


def test_codex_bundle_no_evidence_yields_null_summary_and_no_llm_call():
    conn = _conn()
    client = FakeClient()
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, client, GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1, mentions_by_vol={1: []},
        records_by_vol={1: []},
    )
    entry = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]
    assert entry["summary"] is None
    assert entry["evidence"] == []
    assert client.calls == []
    conn.close()


def test_codex_bundle_wanted_ids_filters_which_entities_regenerate():
    conn = _conn()
    client = FakeClient()
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, client, GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1, mentions_by_vol={1: []},
        records_by_vol={1: []}, wanted_ids={"some-other-entity"},
    )
    assert result["factions"] == {}
    conn.close()


# ---------------------------------------------------------------------------
# codex key_events (Phase 21 part 2)
# ---------------------------------------------------------------------------


class FakeSettingsWithKeyEvents(FakeSettings):
    extraction = {
        "codex_pages": {"factions": {"title": "Factions", "types": ["FACTION"], "max_key_events": 1}},
        "extraction": {"window": WINDOW_CFG},
    }


def test_codex_bundle_omits_key_events_key_when_not_configured(tmp_path):
    """Default FakeSettings has no `max_key_events` -- codex entries stay byte-identical to their
    pre-Phase-21-part-2 shape even when an events_conn with a qualifying group scene is given."""
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": "the trench", "beat_summary": "The squadron holds the line.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        }
    ])
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    assert "key_events" not in result["factions"]["spearhead-squadron"]["cutoffs"]["1"]
    conn.close()
    events_conn.close()


def test_codex_bundle_key_events_requires_two_current_members(tmp_path):
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": "the trench", "beat_summary": "The squadron holds the line.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
        {
            "event_id": "ev_v01c00s001", "vol": 1, "chapter_idx": 0, "span_index": 1,
            "scene_id": "sn_v01c00s001", "participants": ["shinei-nouzen"],
            "location": None, "beat_summary": "Shinei is alone.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    key_events = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"]
    assert [e["event_id"] for e in key_events] == ["ev_v01c00s000"]  # the solo scene is excluded
    assert key_events[0]["participants"] == ["raiden-shuga", "shinei-nouzen"]
    conn.close()
    events_conn.close()


def test_codex_bundle_key_events_admit_a_scene_by_its_location_alone(tmp_path):
    """[30] The >=2-members rule is the right aboutness test for a FACTION, and it silenced every
    place: all 13 place entries shipped with no events, a one-sentence summary and nothing else,
    while 19 of the 53 v1-2 events carried a resolved location nothing read. A scene whose
    `location` IS this entity needs no roster proxy - it is direct evidence the scene happened
    here - so it is admitted whatever the roster size, including a roster of one or none."""
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)  # a ONE-member roster
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_here", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_0", "participants": ["shinei-nouzen"],
            "location": "spearhead-squadron", "beat_summary": "Something happens here.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
        {
            "event_id": "ev_elsewhere", "vol": 1, "chapter_idx": 0, "span_index": 1,
            "scene_id": "sn_1", "participants": ["shinei-nouzen"],
            "location": "somewhere-else", "beat_summary": "Something happens elsewhere.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, build_automaton(GAZ["entities"]),
        FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    key_events = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"]
    assert [e["event_id"] for e in key_events] == ["ev_here"]
    conn.close()
    events_conn.close()


def test_located_events_at_reads_only_this_entity_and_respects_the_cutoff(tmp_path):
    """[30] The scene-level counterpart of `group_events_at`: what happened HERE."""
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {"event_id": "ev_1", "vol": 1, "chapter_idx": 0, "span_index": 0, "scene_id": "s0",
         "participants": [], "location": "pazzio", "beat_summary": "v1 here",
         "vol_start": 1, "confidence": 0.9, "source": "test"},
        {"event_id": "ev_2", "vol": 2, "chapter_idx": 0, "span_index": 0, "scene_id": "s1",
         "participants": [], "location": "pazzio", "beat_summary": "v2 here",
         "vol_start": 2, "confidence": 0.9, "source": "test"},
        {"event_id": "ev_3", "vol": 1, "chapter_idx": 0, "span_index": 1, "scene_id": "s2",
         "participants": [], "location": "poroson", "beat_summary": "v1 elsewhere",
         "vol_start": 1, "confidence": 0.9, "source": "test"},
    ])
    at_v1 = [r["event_id"] for r in EV.located_events_at(events_conn, "pazzio", 1)]
    at_v2 = [r["event_id"] for r in EV.located_events_at(events_conn, "pazzio", 2)]
    assert at_v1 == ["ev_1"]              # v2's scene is not leaked to a v1 reader
    assert at_v2 == ["ev_1", "ev_2"]
    events_conn.close()


def test_codex_bundle_key_events_beat_summary_wikified_excluding_self(tmp_path):
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)  # needed for the >=2-members check
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": "the trench",
            "beat_summary": "Shinei Nouzen and Spearhead Squadron hold the line.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    key_events = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"]
    assert key_events[0]["beat_summary"] == (
        "[Shinei Nouzen](/character/shinei-nouzen) and Spearhead Squadron hold the line."
    )  # the faction's own name is not self-linked on its own codex entry
    conn.close()
    events_conn.close()


def test_codex_bundle_key_events_drops_quotes_with_unresolved_speaker(tmp_path):
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": "the trench", "beat_summary": "They hold the line.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    EV.write_event_claims(events_conn, [
        {
            "claim_id": "ec_q1", "event_id": "ev_v01c00s000", "kind": "quote",
            "subject": None, "predicate": None, "from_value": None, "to_value": None,
            "object": None, "note": None, "speaker": None,
            "para_id": "v01:c00:p0001", "quote": "Who said that?", "vol": 1,
            "confidence": 0.9, "source": "test",
        },
        {
            "claim_id": "ec_q2", "event_id": "ev_v01c00s000", "kind": "quote",
            "subject": None, "predicate": None, "from_value": None, "to_value": None,
            "object": "raiden-shuga", "note": None, "speaker": "shinei-nouzen",
            "para_id": "v01:c00:p0002", "quote": "Hold the line.", "vol": 1,
            "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    quotes = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"][0]["quotes"]
    assert [q["quote"] for q in quotes] == ["Hold the line."]  # the unresolved-speaker quote is dropped
    conn.close()
    events_conn.close()


def test_codex_bundle_key_events_caps_at_max_key_events(tmp_path):
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": None, "beat_summary": "First group scene.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
        {
            "event_id": "ev_v01c00s001", "vol": 1, "chapter_idx": 0, "span_index": 1,
            "scene_id": "sn_v01c00s001", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": None, "beat_summary": "Second group scene.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(  # FakeSettingsWithKeyEvents caps max_key_events at 1
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    key_events = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"]
    assert len(key_events) == 1
    assert key_events[0]["event_id"] == "ev_v01c00s000"  # earlier in reading order, kept first
    conn.close()
    events_conn.close()


def test_codex_bundle_key_events_none_when_events_conn_missing():
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []},  # events_conn defaults to None
    )
    assert result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"] == []
    conn.close()


def test_codex_bundle_key_events_spoiler_filter(tmp_path):
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v02c00s000", "vol": 2, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v02c00s000", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": None, "beat_summary": "A future scene.",
            "vol_start": 2, "confidence": 0.9, "source": "test",
        }
    ])
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    assert result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"] == []
    conn.close()
    events_conn.close()


def test_codex_bundle_key_events_excludes_scene_the_faction_itself_is_absent_from(tmp_path):
    """Phase 22 A3 (fixing S1): >=2 current members co-occurring is not enough on its own -- the
    faction itself must also be a participant or the scene's location, or a scene that has nothing
    to do with the faction (its members just happen to be talking to each other) would still count."""
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "raiden-shuga"],  # no faction
            "location": "some-other-place", "beat_summary": "The two of them talk privately.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        }
    ])
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettingsWithKeyEvents(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []}, events_conn=events_conn,
    )
    assert result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"] == []
    conn.close()
    events_conn.close()


def test_codex_bundle_key_events_two_factions_sharing_a_roster_do_not_render_identical_lists(tmp_path):
    """The audit's Medio/Milone example: two factions share almost their entire membership, so the
    old "any scene with >=2 members" check made both factions' key_events byte-identical. With the
    faction itself required to be present, a scene about ONE faction no longer counts for the
    other."""
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _affiliate(conn, "raiden-shuga", "spearhead-squadron", 1)
    _affiliate(conn, "shinei-nouzen", "grenadier-squadron", 1)
    _affiliate(conn, "raiden-shuga", "grenadier-squadron", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "raiden-shuga", "spearhead-squadron"],
            "location": None, "beat_summary": "The Spearhead squadron regroups.",
            "vol_start": 1, "confidence": 0.9, "source": "test",
        }
    ])
    automaton = build_automaton(GAZ["entities"] + [GRENADIER])
    entities_by_id = {**ENTITIES_BY_ID, "grenadier-squadron": GRENADIER}

    result = BU.build_codex_bundles(
        conn, FakeClient(), {"entities": GAZ["entities"] + [GRENADIER]}, entities_by_id, automaton,
        FakeSettingsWithKeyEvents(), upto_vol=1, mentions_by_vol={1: []}, records_by_vol={1: []},
        events_conn=events_conn,
    )
    assert [e["event_id"] for e in result["factions"]["spearhead-squadron"]["cutoffs"]["1"]["key_events"]] == [
        "ev_v01c00s000"
    ]
    assert result["factions"]["grenadier-squadron"]["cutoffs"]["1"]["key_events"] == []
    conn.close()
    events_conn.close()


# ---------------------------------------------------------------------------
# members / adversaries (Phase 22 A3, fixing S1)
# ---------------------------------------------------------------------------


def _enemy(conn, character_id, faction_id, vol):
    claim_id = f"c_enemy_{character_id}_{vol}"
    ST.write_claims(
        conn,
        [
            {
                "claim_id": claim_id, "subject": character_id, "predicate": "ENEMY_OF", "kind": "relation",
                "object": faction_id, "value": None, "qualifier": "captured by", "first_vol": vol, "confidence": 0.9,
                "evidence": [{"para_id": f"v{vol:02d}:c00:p0001", "quote": "evidence"}], "polarity": "asserted", "source": "test",
            }
        ],
    )
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            character_id, "ENEMY_OF",
            [{"value_or_object": faction_id, "qualifier": "captured by", "first_vol": vol, "claim_id": claim_id}],
            is_relation=True,
        ),
    )


def test_members_and_related_routes_enemy_of_to_adversaries_not_members():
    conn = _conn()
    _enemy(conn, "shinei-nouzen", "spearhead-squadron", 1)
    members, related, adversaries = BU._members_and_related(
        conn, "spearhead-squadron", 1, ENTITIES_BY_ID, RELATIONS_CFG
    )
    assert members == []
    assert adversaries == ["shinei-nouzen"]
    conn.close()


def test_members_and_related_only_counts_membership_flagged_predicates():
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)  # AFFILIATED_WITH -> membership: true
    _enemy(conn, "raiden-shuga", "spearhead-squadron", 1)  # ENEMY_OF -> adversaries, not members
    members, related, adversaries = BU._members_and_related(
        conn, "spearhead-squadron", 1, ENTITIES_BY_ID, RELATIONS_CFG
    )
    assert members == ["shinei-nouzen"]
    assert adversaries == ["raiden-shuga"]
    conn.close()


def test_codex_bundle_omits_adversaries_key_when_none(tmp_path):
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []},
    )
    assert "adversaries" not in result["factions"]["spearhead-squadron"]["cutoffs"]["1"]
    conn.close()


def test_codex_bundle_includes_adversaries_key_when_present(tmp_path):
    conn = _conn()
    _affiliate(conn, "shinei-nouzen", "spearhead-squadron", 1)
    _enemy(conn, "raiden-shuga", "spearhead-squadron", 1)
    automaton = build_automaton(GAZ["entities"])

    result = BU.build_codex_bundles(
        conn, FakeClient(), GAZ, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1,
        mentions_by_vol={1: []}, records_by_vol={1: []},
    )
    entry = result["factions"]["spearhead-squadron"]["cutoffs"]["1"]
    assert entry["members"] == ["shinei-nouzen"]
    assert entry["adversaries"] == ["raiden-shuga"]
    conn.close()


# ---------------------------------------------------------------------------
# timeline/v{NN}.json (Phase 21 part 3)
# ---------------------------------------------------------------------------


def test_timeline_bundle_empty_when_no_events_conn():
    automaton = build_automaton(GAZ["entities"])
    assert BU.build_timeline_bundles(None, 2, automaton, ENTITIES_BY_ID, FakeSettings()) == {}


def test_timeline_bundle_groups_events_by_volume_and_chapter(tmp_path):
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
            "beat_summary": "Holo appears.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
        {
            "event_id": "ev_v01c01s000", "vol": 1, "chapter_idx": 1, "span_index": 0,
            "scene_id": "sn_v01c01s000", "participants": ["kraft-lawrence"], "location": None,
            "beat_summary": "Lawrence travels.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
        {
            "event_id": "ev_v02c00s000", "vol": 2, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v02c00s000", "participants": ["holo"], "location": None,
            "beat_summary": "A new town.", "vol_start": 2, "confidence": 0.9, "source": "test",
        },
    ])

    automaton = build_automaton(GAZ["entities"])
    result = BU.build_timeline_bundles(events_conn, 2, automaton, ENTITIES_BY_ID, FakeSettings())
    assert set(result) == {1, 2}
    v1 = result[1]
    assert v1["vol"] == 1
    # [34] the raw 0-based index, which `mkdocs_wiki.chapter_label` names (OPEN_GAPS G6: +1 was one chapter late)
    assert [c["chapter_idx"] for c in v1["chapters"]] == [0, 1]
    assert v1["chapters"][0]["events"][0]["event_id"] == "ev_v01c00s000"
    assert result[2]["chapters"][0]["events"][0]["beat_summary"] == "A new town."
    events_conn.close()


def test_timeline_bundle_omits_volumes_with_no_events(tmp_path):
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
            "beat_summary": "Holo appears.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_timeline_bundles(events_conn, 3, automaton, ENTITIES_BY_ID, FakeSettings())
    assert set(result) == {1}  # v2 and v3 have no events at all -- omitted, not empty entries
    events_conn.close()


def test_timeline_bundle_wikifies_beat_summary(tmp_path):
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen"], "location": None,
            "beat_summary": "Shinei Nouzen appears.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_timeline_bundles(events_conn, 1, automaton, ENTITIES_BY_ID, FakeSettings())
    beat_summary = result[1]["chapters"][0]["events"][0]["beat_summary"]
    assert beat_summary == "[Shinei Nouzen](/character/shinei-nouzen) appears."
    events_conn.close()


def test_timeline_bundle_includes_state_changes_and_quotes(tmp_path):
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["holo", "kraft-lawrence"], "location": None,
            "beat_summary": "Holo reveals herself.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    EV.write_event_claims(events_conn, [
        {
            "claim_id": "ec_sc1", "event_id": "ev_v01c00s000", "kind": "state_change",
            "subject": "holo", "predicate": None, "from_value": None, "to_value": None,
            "object": None, "note": "Holo's true nature is revealed.", "speaker": None,
            "para_id": "v01:c00:p0001", "quote": "...", "vol": 1, "confidence": 0.9, "source": "test",
        },
        {
            "claim_id": "ec_q1", "event_id": "ev_v01c00s000", "kind": "quote",
            "subject": None, "predicate": None, "from_value": None, "to_value": None,
            "object": "kraft-lawrence", "note": None, "speaker": "holo",
            "para_id": "v01:c00:p0002", "quote": "I am the wisewolf.", "vol": 1,
            "confidence": 0.9, "source": "test",
        },
    ])

    automaton = build_automaton(GAZ["entities"])
    # [31] State changes now drop unresolvable ids like participants do, so the ids must exist.
    entities = {**ENTITIES_BY_ID, **{eid: {"entity_id": eid, "canonical": eid, "type": "CHARACTER", "first_vol": 1}
                                     for eid in ("holo", "kraft-lawrence")}}
    result = BU.build_timeline_bundles(events_conn, 1, automaton, entities, FakeSettings())
    event = result[1]["chapters"][0]["events"][0]
    assert event["state_changes"] == [
        {
            "subject": "holo", "predicate": None, "from_value": None, "to_value": None,
            "object": None, "note": "Holo's true nature is revealed.",
            "para_id": "v01:c00:p0001", "vol": 1,
        }
    ]
    assert event["quotes"] == [
        {
            "speaker": "holo", "addressee": "kraft-lawrence", "quote": "I am the wisewolf.",
            "para_id": "v01:c00:p0002", "vol": 1,
        }
    ]
    events_conn.close()


def test_timeline_bundle_drops_quotes_with_unresolved_speaker(tmp_path):
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["holo", "kraft-lawrence"], "location": None,
            "beat_summary": "They talk.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    EV.write_event_claims(events_conn, [
        {
            "claim_id": "ec_q1", "event_id": "ev_v01c00s000", "kind": "quote",
            "subject": None, "predicate": None, "from_value": None, "to_value": None,
            "object": None, "note": None, "speaker": None,
            "para_id": "v01:c00:p0001", "quote": "Who said that?", "vol": 1, "confidence": 0.9, "source": "test",
        },
        {
            "claim_id": "ec_q2", "event_id": "ev_v01c00s000", "kind": "quote",
            "subject": None, "predicate": None, "from_value": None, "to_value": None,
            "object": "kraft-lawrence", "note": None, "speaker": "holo",
            "para_id": "v01:c00:p0002", "quote": "I am the wisewolf.", "vol": 1,
            "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_timeline_bundles(events_conn, 1, automaton, ENTITIES_BY_ID, FakeSettings())
    quotes = result[1]["chapters"][0]["events"][0]["quotes"]
    assert [q["quote"] for q in quotes] == ["I am the wisewolf."]  # the unresolved-speaker quote is dropped
    events_conn.close()


# ---------------------------------------------------------------------------
# relationships/<a>--<b>.json (Phase 21)
# ---------------------------------------------------------------------------


def _friend(conn, a, b, vol, predicate="FRIEND_OF"):
    claim_id = f"c_{a}_{b}_{vol}"
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            a, predicate,
            [{"value_or_object": b, "qualifier": None, "first_vol": vol, "claim_id": claim_id}],
            is_relation=True,
        ),
    )


def test_relationship_bundle_includes_relation_current_only():
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 1)
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, None, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1)
    assert set(result) == {"raiden-shuga--shinei-nouzen"}
    doc = result["raiden-shuga--shinei-nouzen"]
    assert sorted(doc["pair"]) == ["raiden-shuga", "shinei-nouzen"]
    rel = doc["cutoffs"]["1"]["relations"][0]
    assert rel["predicate"] == "FRIEND_OF"
    assert rel["display"] == "Friend of"
    assert doc["cutoffs"]["1"]["shared_scenes"] == []
    conn.close()


def test_relationship_bundle_marks_presumed_until_confirmation_is_visible():
    conn = _conn()
    ST.write_claims(conn, [
        {
            "claim_id": "c_presumed", "subject": "shinei-nouzen", "predicate": "FRIEND_OF",
            "kind": "relation", "object": "raiden-shuga", "value": None, "qualifier": None,
            "first_vol": 1, "confidence": 0.8, "polarity": "presumed", "source": "test",
            "evidence": [{"para_id": "v01:c00:p0001", "quote": "They may be friends."}],
        },
        {
            "claim_id": "c_asserted", "subject": "shinei-nouzen", "predicate": "FRIEND_OF",
            "kind": "relation", "object": "raiden-shuga", "value": None, "qualifier": None,
            "first_vol": 2, "confidence": 0.9, "polarity": "asserted", "source": "test",
            "evidence": [{"para_id": "v02:c00:p0001", "quote": "They are friends."}],
        },
    ])
    ST.write_intervals(conn, [{
        "interval_id": "i_friend", "subject": "shinei-nouzen", "predicate": "FRIEND_OF",
        "object": "raiden-shuga", "value": None, "qualifier": None, "vol_start": 1,
        "vol_end": None, "claim_ids": ["c_presumed", "c_asserted"], "superseded_by": None,
    }])

    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(
        conn, None, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2
    )
    cutoffs = result["raiden-shuga--shinei-nouzen"]["cutoffs"]

    assert cutoffs["1"]["relations"][0]["display"] == "presumed Friend of"
    assert cutoffs["2"]["relations"][0]["display"] == "Friend of"
    assert cutoffs["1"]["relations"][0]["evidence"] == ["v01:c00:p0001"]
    assert cutoffs["2"]["relations"][0]["evidence"] == [
        "v01:c00:p0001", "v02:c00:p0001",
    ]
    conn.close()


def test_relationship_bundle_no_relation_yields_no_page():
    conn = _conn()
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, None, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2)
    assert result == {}  # SHIN/RAIDEN/SPEARHEAD have no relation edge at all in this graph
    conn.close()


def test_relationship_bundle_spoiler_filter_excludes_future_pair():
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 2)  # relation first attested at v2
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, None, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1)
    assert result == {}  # the pair's own first_vol (2) exceeds this cutoff -- no page yet

    result_v2 = BU.build_relationship_bundles(conn, None, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2)
    assert set(result_v2) == {"raiden-shuga--shinei-nouzen"}
    conn.close()


def test_relationship_bundle_skips_unchanged_cutoff():
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 1)
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, None, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2)
    doc = result["raiden-shuga--shinei-nouzen"]
    assert set(doc["cutoffs"]) == {"1"}  # nothing changed between v1 and v2 -> v2 skipped
    conn.close()


def test_relationship_bundle_includes_shared_scenes_and_new_cutoff_on_change(tmp_path):
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v02c00s000", "vol": 2, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v02c00s000", "participants": ["shinei-nouzen", "raiden-shuga"],
            "location": "the trench", "beat_summary": "They hold the line together.",
            "vol_start": 2, "confidence": 0.9, "source": "test",
        }
    ])

    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, events_conn, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2)
    doc = result["raiden-shuga--shinei-nouzen"]
    assert set(doc["cutoffs"]) == {"1", "2"}  # a new shared scene at v2 changes state
    scenes = doc["cutoffs"]["2"]["shared_scenes"]
    assert len(scenes) == 1
    assert scenes[0]["beat_summary"] == "They hold the line together."
    conn.close()
    events_conn.close()


def test_relationship_bundle_shared_scene_drops_quotes_with_unresolved_speaker(tmp_path):
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v02c00s000", "vol": 2, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v02c00s000", "participants": ["shinei-nouzen", "raiden-shuga"],
            "location": "the trench", "beat_summary": "They talk.",
            "vol_start": 2, "confidence": 0.9, "source": "test",
        }
    ])
    EV.write_event_claims(events_conn, [
        {
            "claim_id": "ec_q1", "event_id": "ev_v02c00s000", "kind": "quote",
            "subject": None, "predicate": None, "from_value": None, "to_value": None,
            "object": None, "note": None, "speaker": None,
            "para_id": "v02:c00:p0001", "quote": "Who goes there?", "vol": 2,
            "confidence": 0.9, "source": "test",
        },
        {
            "claim_id": "ec_q2", "event_id": "ev_v02c00s000", "kind": "quote",
            "subject": None, "predicate": None, "from_value": None, "to_value": None,
            "object": "raiden-shuga", "note": None, "speaker": "shinei-nouzen",
            "para_id": "v02:c00:p0002", "quote": "It's me.", "vol": 2,
            "confidence": 0.9, "source": "test",
        },
    ])

    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, events_conn, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2)
    quotes = result["raiden-shuga--shinei-nouzen"]["cutoffs"]["2"]["shared_scenes"][0]["quotes"]
    assert [q["quote"] for q in quotes] == ["It's me."]  # the unresolved-speaker quote is dropped
    conn.close()
    events_conn.close()


def test_relationship_bundle_shared_scene_beat_summary_is_wikified(tmp_path):
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 2)  # raiden-shuga's own first_vol is 2
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v02c00s000", "vol": 2, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v02c00s000", "participants": ["shinei-nouzen", "raiden-shuga"],
            "location": None, "beat_summary": "Shinei Nouzen and Raiden Shuga hold the line.",
            "vol_start": 2, "confidence": 0.9, "source": "test",
        }
    ])
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, events_conn, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=2)
    doc = result["raiden-shuga--shinei-nouzen"]
    beat_summary = doc["cutoffs"]["2"]["shared_scenes"][0]["beat_summary"]
    assert beat_summary == (
        "[Shinei Nouzen](/character/shinei-nouzen) and [Raiden Shuga](/character/raiden-shuga) hold the line."
    )
    conn.close()
    events_conn.close()


def test_relationship_bundle_shared_scene_spoiler_filter(tmp_path):
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 1)
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v02c00s000", "vol": 2, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v02c00s000", "participants": ["shinei-nouzen", "raiden-shuga"],
            "location": None, "beat_summary": "A future scene.",
            "vol_start": 2, "confidence": 0.9, "source": "test",
        }
    ])
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(conn, events_conn, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1)
    doc = result["raiden-shuga--shinei-nouzen"]
    assert doc["cutoffs"]["1"]["shared_scenes"] == []  # v2 scene must not leak at cutoff 1
    conn.close()
    events_conn.close()


def test_relationship_bundle_wanted_ids_filters_pairs():
    conn = _conn()
    _friend(conn, "shinei-nouzen", "raiden-shuga", 1)
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_relationship_bundles(
        conn, None, ENTITIES_BY_ID, automaton, FakeSettings(), upto_vol=1, wanted_ids={"some-other-entity"},
    )
    assert result == {}
    conn.close()


def test_timeline_participants_drop_characters_with_no_page(tmp_path):
    """Phase 26: `wiki audit links` FAILed on the `may-god` mining artifact in v01.json and
    v02.json -- Phase 23 E6's `written_ids` filter reached the roster, links and search, but
    timeline bundles were built before it and kept every raw participant. A participant that
    resolves to nothing is a 404 waiting to be clicked."""
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "may-god"], "location": None,
            "beat_summary": "Shin appears.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    # [31] State changes follow the same rule (Anne's principal-cast build FAILed the links audit on them).
    EV.write_event_claims(events_conn, [
        {
            "claim_id": f"ec_s{i}", "event_id": "ev_v01c00s000", "kind": "state_change",
            "subject": subject, "predicate": None, "from_value": None, "to_value": None,
            "object": None, "note": "changes", "speaker": None,
            "para_id": "v01:c00:p0001", "quote": "Shin changes.", "vol": 1, "confidence": 0.9, "source": "test",
        }
        for i, subject in enumerate(["shinei-nouzen", "may-god"])
    ])
    automaton = build_automaton(GAZ["entities"])
    entities = {**ENTITIES_BY_ID, "may-god": {"entity_id": "may-god", "canonical": "May God", "type": "CHARACTER", "first_vol": 1}}

    unfiltered = BU.build_timeline_bundles(events_conn, 1, automaton, entities, FakeSettings())
    assert "may-god" in unfiltered[1]["chapters"][0]["events"][0]["participants"]

    filtered = BU.build_timeline_bundles(
        events_conn, 1, automaton, entities, FakeSettings(), written_ids_at={1: {"shinei-nouzen"}}
    )
    assert filtered[1]["chapters"][0]["events"][0]["participants"] == ["shinei-nouzen"]
    assert [sc["subject"] for sc in filtered[1]["chapters"][0]["events"][0]["state_changes"]] == ["shinei-nouzen"]
    events_conn.close()


def test_timeline_participants_keep_codex_entities_without_a_page(tmp_path):
    """A FACTION/LOCATION never gets its own page by design (CLAUDE.md §2) but always has a
    codex anchor, so `written_ids` must not filter it out."""
    events_conn = EV.connect(tmp_path / "events.db")
    EV.write_events(events_conn, [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["shinei-nouzen", "spearhead-squadron"], "location": None,
            "beat_summary": "A meeting.", "vol_start": 1, "confidence": 0.9, "source": "test",
        },
    ])
    automaton = build_automaton(GAZ["entities"])
    result = BU.build_timeline_bundles(
        events_conn, 1, automaton, ENTITIES_BY_ID, FakeSettings(), written_ids_at={1: {"shinei-nouzen"}}
    )
    assert result[1]["chapters"][0]["events"][0]["participants"] == ["shinei-nouzen", "spearhead-squadron"]
    events_conn.close()


class _GatedClient(FakeClient):
    """FakeClient that also answers `codex_check`: supported iff the definition is in `supported`."""

    def __init__(self, texts, supported):
        super().__init__(texts[0])
        self.texts, self.supported, self.summaries, self.checks = list(texts), set(supported), [], []

    def complete_json(self, stage, prompt, schema, system=None):
        self.calls.append({"stage": stage, "prompt": prompt})
        if stage == "codex_check":
            text = prompt.rsplit("Definition: ", 1)[1]
            self.checks.append(text)
            return schema(supported=text in self.supported, unsupported="" if text in self.supported else "married")
        self.summaries.append(prompt)
        return schema(text=self.texts[min(len(self.summaries) - 1, len(self.texts) - 1)])


class _CheckingSettings(FakeSettings):
    models = {"routing": {"codex_check": {"role": "vertex_flash"}}}


def test_codex_summary_must_be_supported_by_its_passages():
    """[34] OPEN_GAPS G2 (C33: a model check, not MiniCheck): an unsupported summary is regenerated
    once with what failed, then dropped; settings that route no `codex_check` skip the check."""
    entity = {"entity_id": "e", "canonical": "Patterson Street", "type": "LOCATION"}
    windows = [_window(1, "v03:c01:p0001", "Jo and Phil are engaged.")]
    ok = _GatedClient(["Jo and Phil are engaged here."], {"Jo and Phil are engaged here."})
    assert BU._generate_codex_summary(ok, entity, 3, windows, _CheckingSettings())["text"] == "Jo and Phil are engaged here."
    assert "Jo and Phil are engaged." in ok.calls[1]["prompt"]   # the check sees the passages
    fixed = _GatedClient(["Jo and Phil are married here.", "Jo and Phil are engaged here."], {"Jo and Phil are engaged here."})
    assert BU._generate_codex_summary(fixed, entity, 3, windows, _CheckingSettings())["text"] == "Jo and Phil are engaged here."
    assert "not supported" in fixed.summaries[1] and "(married)" in fixed.summaries[1]
    never = _GatedClient(["Jo and Phil are married here."], set())
    assert BU._generate_codex_summary(never, entity, 3, windows, _CheckingSettings()) is None
    unchecked = _GatedClient(["Jo and Phil are married here."], set())
    assert BU._generate_codex_summary(unchecked, entity, 3, windows, FakeSettings())["text"] == "Jo and Phil are married here."
    assert not unchecked.checks
