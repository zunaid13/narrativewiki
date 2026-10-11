"""Tests for synth/assemble.py — Phase 5."""

from __future__ import annotations

import sqlite3

from narrativewiki.graph import store as ST
from narrativewiki.graph import temporal as TE
from narrativewiki.synth import assemble as AS

ATTRIBUTES = {
    "AGE": {"single": True},
    "STATUS": {"single": True},
    "RANK": {"single": True},
    "TITLE": {"single": False},
    "NICKNAME": {"single": False},
}
RELATIONS = {
    "FRIEND_OF": {"symmetric": True, "display": "Friend of"},
    "ENEMY_OF": {"symmetric": True, "display": "Enemy of"},
    "PARENT_OF": {"inverse": "CHILD_OF", "display": "Parent of"},
    "CHILD_OF": {"inverse": "PARENT_OF", "display": "Child of"},
    "AFFILIATED_WITH": {"display": "Affiliation"},
    # Phase 26: directional, no `inverse`, carries passive wording for the object's own page.
    "KILLED": {"display": "Killed", "object_display": "Killed by"},
    "SAVED": {"display": "Saved"},
}
TRAITS = {"PERSONALITY": {}, "BACKGROUND": {}}
PAGE_OUTLINE = [
    {"key": "overview", "kind": "fields", "title": "Overview"},
    {"key": "affiliations", "kind": "affiliations", "title": "Affiliations"},
    {"key": "relationships", "kind": "relationships", "title": "Relationships"},
    {"key": "background", "kind": "prose", "title": "Background", "traits": ["BACKGROUND"]},
    {"key": "personality", "kind": "prose", "title": "Personality", "traits": ["PERSONALITY"]},
    {"key": "appearances", "kind": "derived", "title": "Appearances"},
]


class FakeSettings:
    attributes = ATTRIBUTES
    relations = RELATIONS
    traits = TRAITS
    page_outline = PAGE_OUTLINE
    conflicts_config = {}


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    return conn


def _claim(claim_id, subject, predicate, kind, first_vol, *, object=None, value=None, quote="ev"):
    return {
        "claim_id": claim_id,
        "subject": subject,
        "predicate": predicate,
        "kind": kind,
        "object": object,
        "value": value,
        "qualifier": None,
        "first_vol": first_vol,
        "confidence": 0.9,
        "evidence": [{"para_id": f"v{first_vol:02d}:c00:p0001", "quote": quote}],
        "polarity": "asserted",
        "source": "test",
    }


SHIN = {"entity_id": "shin", "canonical": "Shin", "first_vol": 1}


def test_scalar_field_never_signals_a_future_change():
    conn = _conn()
    entries = [
        {"value": "Second Lieutenant", "qualifier": None, "first_vol": 2, "claim_ids": ["c_a"]},
        {"value": "Captain", "qualifier": None, "first_vol": 6, "claim_ids": ["c_b"]},
    ]
    ST.write_intervals(conn, TE.assign_single_valued("shin", "RANK", entries))

    # At cutoff 3: "Second Lieutenant" is current and its row really has vol_end=5. Neither that
    # number nor the fact that the value closes may reach the field (Phase 32 req. 9).
    page = AS.assemble_page(conn, None, SHIN, 3, FakeSettings(), {})
    rank = page["fields"]["rank"]
    assert rank["value"] == "Second Lieutenant"
    assert "changes_later" not in rank
    assert "5" not in repr(rank)
    assert rank["history"] == []

    # At cutoff 8: the change has happened, so the old value is history with its real volumes
    # (Phase 32 req. 6: earlier information stays on the later page).
    page_8 = AS.assemble_page(conn, None, SHIN, 8, FakeSettings(), {})
    rank_8 = page_8["fields"]["rank"]
    assert rank_8["value"] == "Captain"
    assert rank_8["history"] == [{
        "value": "Second Lieutenant", "vols": [2, 5], "polarity": "asserted", "evidence": [],
    }]


def test_list_field_multi_valued_no_history():
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin",
            "NICKNAME",
            [
                {"value_or_object": "Undertaker", "qualifier": None, "first_vol": 1, "claim_id": "c_a"},
                {"value_or_object": "Baleygr", "qualifier": None, "first_vol": 3, "claim_id": "c_b"},
            ],
            is_relation=False,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page["fields"]["nickname"] == [{
        "value": "Undertaker", "since_vol": 1, "show_vol": False, "evidence": [],
    }]

    page_3 = AS.assemble_page(conn, None, SHIN, 3, FakeSettings(), {})
    values = {e["value"] for e in page_3["fields"]["nickname"]}
    assert values == {"Undertaker", "Baleygr"}


def test_relationship_flips_to_inverse_label_when_entity_is_the_object():
    conn = _conn()
    # Canonical storage direction: (kiriya, PARENT_OF, shin) -- shin is the OBJECT.
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "kiriya", "PARENT_OF", [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
            is_relation=True,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    entries = page["fields"]["relationships"]
    assert len(entries) == 1
    assert entries[0]["entity_id"] == "kiriya"
    assert entries[0]["predicate"] == "CHILD_OF"  # shin is kiriya's child, not the parent
    assert entries[0]["label"] == "Child of"


def test_symmetric_relationship_keeps_same_predicate_from_either_side():
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "raiden", "FRIEND_OF", [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
            is_relation=True,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page["fields"]["relationships"][0]["predicate"] == "FRIEND_OF"


def test_unsupported_verdict_withholds_a_relationship_at_render_time():
    """Phase 23 B2: a fact wiki verify flags as unsupported must not render, even though the
    interval itself is untouched (still in the DB, still readable via wiki explain/trace)."""
    conn = _conn()
    intervals = TE.assign_multi_valued(
        "marheit", "SPOUSE_OF", [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
        is_relation=True,
    )
    ST.write_intervals(conn, intervals)
    ST.write_verdicts(conn, [{
        "target_id": intervals[0]["interval_id"], "verdict": "unsupported",
        "rationale": "cited paragraph never names the object", "model": "test", "run_id": "r1",
    }])
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert "relationships" not in page["fields"]
    # the interval itself is untouched -- still queryable, just not rendered
    assert conn.execute("SELECT COUNT(*) FROM intervals").fetchone()[0] == 1


def test_supported_verdict_does_not_withhold_a_relationship():
    conn = _conn()
    intervals = TE.assign_multi_valued(
        "raiden", "FRIEND_OF", [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
        is_relation=True,
    )
    ST.write_intervals(conn, intervals)
    ST.write_verdicts(conn, [{
        "target_id": intervals[0]["interval_id"], "verdict": "supported", "model": "test", "run_id": "r1",
    }])
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page["fields"]["relationships"][0]["predicate"] == "FRIEND_OF"


def test_unsupported_verdict_withholds_an_attribute_at_render_time():
    conn = _conn()
    intervals = TE.assign_single_valued("shin", "AGE", [{"value": "16", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]}])
    ST.write_intervals(conn, intervals)
    ST.write_verdicts(conn, [{
        "target_id": intervals[0]["interval_id"], "verdict": "unsupported", "model": "test", "run_id": "r1",
    }])
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert "age" not in page["fields"]


def test_affiliation_role_and_current_flag():
    conn = _conn()
    interval = TE.assign_multi_valued(
        "shin", "AFFILIATED_WITH",
        [{"value_or_object": "spearhead-squadron", "qualifier": "leader", "first_vol": 1, "claim_id": "c_a"}],
        is_relation=True,
    )
    ST.write_intervals(conn, interval)
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    aff = page["fields"]["affiliations"][0]
    assert aff == {
        "entity_id": "spearhead-squadron", "role": "leader", "vols": [1, None],
        "current": True, "membership": True, "evidence": [],  # Phase 26
    }
    assert "relationships" not in page["fields"]  # AFFILIATED_WITH never lands in the generic list


def test_claim_set_hash_stable_and_changes_with_visible_set():
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_single_valued("shin", "AGE", [{"value": "16", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]}]),
    )
    page_a = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    page_b = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page_a["claim_set_hash"] == page_b["claim_set_hash"]

    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "NICKNAME", [{"value_or_object": "Undertaker", "qualifier": None, "first_vol": 1, "claim_id": "c_b"}],
            is_relation=False,
        ),
    )
    page_c = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page_c["claim_set_hash"] != page_a["claim_set_hash"]


def test_prose_and_generated_by_left_as_placeholders():
    conn = _conn()
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page["prose"] == {"background": None, "personality": None}
    assert page["generated_by"] is None


def test_aliases_carried_onto_page_model():
    """Phase 23 E5: page["aliases"] mirrors entity.get("aliases", []) -- previously dropped from
    the JSON page model entirely even though site/okf.py's Markdown front matter always had it."""
    conn = _conn()
    entity = {**SHIN, "aliases": ["Reaper", "Undertaker"]}
    page = AS.assemble_page(conn, None, entity, 1, FakeSettings(), {})
    assert page["aliases"] == ["Reaper", "Undertaker"]


def test_aliases_default_to_empty_list_when_entity_has_none():
    conn = _conn()
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page["aliases"] == []


class FakeSettingsWithAppearanceProse(FakeSettings):
    attributes = {**ATTRIBUTES, "APPEARANCE": {"single": False}}
    page_outline = [
        *PAGE_OUTLINE,
        {"key": "appearance", "kind": "prose", "title": "Appearance", "traits": ["APPEARANCE"],
         "source": "attributes"},
    ]


def test_appearance_attribute_excluded_from_fields_when_claimed_by_a_prose_section():
    """Phase 23 E2: an attribute predicate named in a `source: "attributes"` prose section's
    `traits` list must not also render as a bullet in `fields.overview` -- it would otherwise
    double-render as both a paragraph and an infobox line."""
    conn = _conn()
    claim = _claim("c1", "shin", "APPEARANCE", "attribute", 1, value="short silver hair")
    ST.write_claims(conn, [claim])
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "APPEARANCE",
            [{"value_or_object": "short silver hair", "qualifier": None, "first_vol": 1, "claim_id": "c1"}],
            is_relation=False,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettingsWithAppearanceProse(), {})
    assert "appearance" not in page["fields"]


def test_traits_are_not_a_page_field_but_available_via_trait_values_at():
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "PERSONALITY", [{"value_or_object": "outwardly detached", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
            is_relation=False,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert "personality" not in page["fields"]

    traits = AS.trait_values_at(conn, "shin", 1, TRAITS)
    assert traits["PERSONALITY"] == [{"value": "outwardly detached", "since_vol": 1, "claim_ids": ["c_a"]}]


def test_mentions_of_populated_from_ppr_excluding_self():
    """Phase 22 A5 (U5): mentions_of is [{entity_id, note}]. `edges` (PPR's graph) is not
    `intervals` -- this pair has no interval, so `relations_between` finds nothing and, with no
    events_conn, `note` stays None."""
    conn = _conn()
    ST.write_edges(conn, [{"subject": "shin", "predicate": "FRIEND_OF", "object": "raiden", "vol_start": 1, "vol_end": None}])
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page["mentions_of"] == [{"entity_id": "raiden", "note": None}]


# ---------------------------------------------------------------------------
# Phase 20 — build_quotes_section tests
# ---------------------------------------------------------------------------

import json


def _make_events_conn_for_quotes(events: list, claims: list):
    """Minimal events.db with the tables build_quotes_section reads."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
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
    for ev in events:
        conn.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                ev["event_id"], ev["vol"], ev.get("chapter_idx", 1), ev.get("span_index", 0),
                ev.get("scene_id", "s0"), json.dumps(ev.get("participants", ["shin"])),
                ev.get("location"), ev.get("beat_summary", "something happened"),
                ev["vol"], ev.get("confidence", 0.8), "",
            ),
        )
    for c in claims:
        conn.execute(
            "INSERT INTO event_claims VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                c["claim_id"], c["event_id"], c.get("kind", "quote"), c.get("subject"),
                c.get("predicate"), c.get("from_value"), c.get("to_value"), c.get("object"),
                c.get("note"), c.get("speaker", "shin"), c.get("para_id", "v01:c01:p0001"),
                c.get("quote", "Hello."), c.get("vol", 1), c.get("confidence", 0.8), "",
            ),
        )
    conn.commit()
    return conn


_QUOTES_SECTION = {"key": "quotes", "kind": "quotes", "max_quotes": 3}


def test_build_quotes_section_returns_none_when_no_events():
    conn = _make_events_conn_for_quotes([], [])
    result = AS.build_quotes_section(conn, "shin", 1, _QUOTES_SECTION)
    assert result is None


def test_build_quotes_section_returns_none_when_no_quote_claims():
    conn = _make_events_conn_for_quotes(
        [{"event_id": "ev1", "vol": 1, "beat_summary": "scene"}],
        [{"claim_id": "c1", "event_id": "ev1", "kind": "state_change", "speaker": "shin"}],
    )
    result = AS.build_quotes_section(conn, "shin", 1, _QUOTES_SECTION)
    assert result is None


def test_build_quotes_section_returns_matching_speaker_quotes():
    conn = _make_events_conn_for_quotes(
        [{"event_id": "ev1", "vol": 1, "beat_summary": "scene"}],
        [{"claim_id": "c1", "event_id": "ev1", "kind": "quote", "speaker": "shin",
          "quote": "I am Shin.", "vol": 1, "confidence": 0.9}],
    )
    result = AS.build_quotes_section(conn, "shin", 1, _QUOTES_SECTION)
    assert result is not None
    assert len(result) == 1
    assert result[0]["quote"] == "I am Shin."
    assert result[0]["vol"] == 1
    assert "confidence" not in result[0]  # confidence stripped from public schema


def test_build_quotes_section_filters_wrong_speaker():
    conn = _make_events_conn_for_quotes(
        [{"event_id": "ev1", "vol": 1, "beat_summary": "scene"}],
        [{"claim_id": "c1", "event_id": "ev1", "kind": "quote", "speaker": "raiden",
          "quote": "I am Raiden.", "vol": 1, "confidence": 0.9}],
    )
    result = AS.build_quotes_section(conn, "shin", 1, _QUOTES_SECTION)
    assert result is None


def test_build_quotes_section_spoiler_fence_excludes_future_vol():
    """A quote from vol=2 must not appear in a vol=1 cutoff build."""
    conn = _make_events_conn_for_quotes(
        [{"event_id": "ev1", "vol": 2, "beat_summary": "future scene"}],
        [{"claim_id": "c1", "event_id": "ev1", "kind": "quote", "speaker": "shin",
          "quote": "Future revelation.", "vol": 2, "confidence": 0.95}],
    )
    result = AS.build_quotes_section(conn, "shin", 1, _QUOTES_SECTION)
    assert result is None  # vol=2 event not visible at upto_vol=1


def test_build_quotes_section_respects_max_quotes():
    events = [{"event_id": f"ev{i}", "vol": 1, "beat_summary": f"scene {i}"} for i in range(5)]
    claims = [
        {"claim_id": f"c{i}", "event_id": f"ev{i}", "kind": "quote", "speaker": "shin",
         "quote": f"Quote number {i}.", "vol": 1, "confidence": 0.9 - i * 0.01}
        for i in range(5)
    ]
    conn = _make_events_conn_for_quotes(events, claims)
    section = {"key": "quotes", "kind": "quotes", "max_quotes": 2}
    result = AS.build_quotes_section(conn, "shin", 1, section)
    assert result is not None
    assert len(result) == 2


def test_build_quotes_section_deduplicates_by_prefix():
    conn = _make_events_conn_for_quotes(
        [{"event_id": "ev1", "vol": 1, "beat_summary": "scene"}],
        [
            {"claim_id": "c1", "event_id": "ev1", "kind": "quote", "speaker": "shin",
             "quote": "A very long quote that starts with these exact words.", "vol": 1, "confidence": 0.9},
            {"claim_id": "c2", "event_id": "ev1", "kind": "quote", "speaker": "shin",
             "quote": "A very long quote that starts with these exact words.", "vol": 1, "confidence": 0.8},
        ],
    )
    result = AS.build_quotes_section(conn, "shin", 1, _QUOTES_SECTION)
    assert result is not None
    assert len(result) == 1  # deduplicated


def test_build_quotes_section_matches_entity_canonical_speaker():
    """Speaker field may hold the canonical name rather than entity_id."""
    conn = _make_events_conn_for_quotes(
        [{"event_id": "ev1", "vol": 1, "beat_summary": "scene"}],
        [{"claim_id": "c1", "event_id": "ev1", "kind": "quote", "speaker": "Shin",
          "quote": "My name is Shin.", "vol": 1, "confidence": 0.9}],
    )
    section = dict(_QUOTES_SECTION, _entity_canonical="Shin")
    result = AS.build_quotes_section(conn, "shin_id", 1, section)
    assert result is not None
    assert result[0]["quote"] == "My name is Shin."


def test_assemble_page_includes_quotes_placeholder_when_outline_has_quotes_section():
    """assemble_page() must include quotes=None if page_outline has kind: quotes."""
    conn = _conn()
    outline_with_quotes = [
        {"key": "quotes", "kind": "quotes", "title": "Quotes", "max_quotes": 3},
    ]

    class SettingsWithQuotes:
        attributes = {}
        relations = {}
        traits = {}
        conflicts_config = {}
        page_outline = outline_with_quotes

    page = AS.assemble_page(conn, None, SHIN, 1, SettingsWithQuotes(), {})
    assert "quotes" in page
    assert page["quotes"] is None


def test_assemble_page_no_quotes_key_without_quotes_section():
    """Without kind: quotes in outline, page dict must not include quotes key."""
    conn = _conn()
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert "quotes" not in page


# ---------------------------------------------------------------------------
# Phase 22 A5 (fixes U3-U7, S5, S6)
# ---------------------------------------------------------------------------


class FakeSettingsWithStatusDefault(FakeSettings):
    attributes = {**ATTRIBUTES, "STATUS": {"single": True, "default": "alive"}}


def test_default_status_materializes_inferred_field_when_no_claims_exist():
    """U6: zero STATUS claims -> a scalar field materialized from attributes.*.default, marked
    inferred: true, never touching claim_set_hash (no claim_ids behind it at all)."""
    conn = _conn()
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettingsWithStatusDefault(), {})
    status = page["fields"]["status"]
    assert status == {
        "value": "alive", "since_vol": None, "show_vol": False,
        "polarity": "asserted", "history": [], "inferred": True,
    }
    # A real claim makes the default disappear entirely -- not merged with it.
    ST.write_intervals(
        conn,
        TE.assign_single_valued("shin", "STATUS", [{"value": "dead", "qualifier": None, "first_vol": 2, "claim_ids": ["c_a"]}]),
    )
    page_2 = AS.assemble_page(conn, None, SHIN, 2, FakeSettingsWithStatusDefault(), {})
    assert page_2["fields"]["status"]["inferred"] is False
    assert page_2["fields"]["status"]["value"] == "dead"


def test_claim_polarity_reflects_most_recent_visible_claim_not_claim_ids_zero():
    """U7: an interval's claim_ids can span multiple original claims (oldest-to-newest). The
    pre-A5 bug read claim_ids[0] unconditionally -- stuck on a stale "presumed" forever, and,
    worse, not even guaranteed spoiler-safe. This must pick the latest claim whose OWN first_vol
    is <= the cutoff, and never read a claim beyond it."""
    conn = _conn()
    ST.write_claims(conn, [
        {
            "claim_id": "c_a", "subject": "shin", "predicate": "STATUS", "kind": "attribute",
            "object": None, "value": "dead", "qualifier": None, "first_vol": 2, "confidence": 0.8,
            "polarity": "presumed", "evidence": [{"para_id": "v02:c00:p0001", "quote": "reported dead"}],
            "source": "test",
        },
        {
            "claim_id": "c_b", "subject": "shin", "predicate": "STATUS", "kind": "attribute",
            "object": None, "value": "dead", "qualifier": None, "first_vol": 5, "confidence": 0.9,
            "polarity": "asserted", "evidence": [{"para_id": "v05:c00:p0001", "quote": "confirmed dead"}],
            "source": "test",
        },
    ])
    ST.write_intervals(conn, [{
        "interval_id": "i_test", "subject": "shin", "predicate": "STATUS", "object": None,
        "value": "dead", "qualifier": None, "vol_start": 2, "vol_end": None,
        "claim_ids": ["c_a", "c_b"], "superseded_by": None,
    }])

    # At cutoff 3, c_b (first_vol=5) is not yet visible -- must read c_a's "presumed", not error
    # or leak c_b's polarity.
    page_3 = AS.assemble_page(conn, None, SHIN, 3, FakeSettings(), {})
    assert page_3["fields"]["status"]["polarity"] == "presumed"

    # At cutoff 6, both are visible -- the MOST RECENT (c_b, "asserted") wins, not claim_ids[0].
    page_6 = AS.assemble_page(conn, None, SHIN, 6, FakeSettings(), {})
    assert page_6["fields"]["status"]["polarity"] == "asserted"


def test_show_vol_false_since_entity_first_appearance_true_for_later_reveal():
    """U3: a value known since the character's own first_vol gets show_vol: False (a "(since
    v1)" marker on day one is noise); a value revealed later gets True."""
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "NICKNAME",
            [
                {"value_or_object": "Undertaker", "qualifier": None, "first_vol": 1, "claim_id": "c_a"},
                {"value_or_object": "Baleygr", "qualifier": None, "first_vol": 3, "claim_id": "c_b"},
            ],
            is_relation=False,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 3, FakeSettings(), {})
    by_value = {e["value"]: e["show_vol"] for e in page["fields"]["nickname"]}
    assert by_value == {"Undertaker": False, "Baleygr": True}


def test_relationship_label_is_display_qualifier_demoted_to_note_and_blurb():
    """U4: a free-text qualifier no longer overrides the config display label -- it demotes to
    `note`, combined into `blurb` (the generic "{label} — {note}" fallback with no configured
    relations.*.blurb template)."""
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "raiden", "FRIEND_OF",
            [{"value_or_object": "shin", "qualifier": "wife (false identity claimed)", "first_vol": 1, "claim_id": "c_a"}],
            is_relation=True,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    entry = page["fields"]["relationships"][0]
    assert entry["label"] == "Friend of"
    assert entry["note"] == "wife (false identity claimed)"
    assert entry["blurb"] == "Friend of — wife (false identity claimed)"


def test_relationship_with_no_qualifier_has_no_note_and_bare_blurb():
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "raiden", "FRIEND_OF", [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
            is_relation=True,
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    entry = page["fields"]["relationships"][0]
    assert entry["note"] is None
    assert entry["blurb"] == "Friend of"


def test_relationship_closed_by_conflicts_with_shows_current_false():
    """Character pages explicitly combine current relations with relation history, so a
    conflicts_with-superseded relation (FRIEND_OF -> ENEMY_OF) remains visible as ended rather
    than either disappearing or rendering as current."""
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_relation_supersession(
            "raiden", "shin",
            [
                {"predicate": "FRIEND_OF", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]},
                {"predicate": "ENEMY_OF", "qualifier": None, "first_vol": 4, "claim_ids": ["c_b"]},
            ],
        ),
    )
    page = AS.assemble_page(conn, None, SHIN, 6, FakeSettings(), {})
    by_predicate = {e["predicate"]: e for e in page["fields"]["relationships"]}
    assert by_predicate["FRIEND_OF"]["current"] is False
    assert by_predicate["FRIEND_OF"]["vol_end"] == 3
    assert by_predicate["ENEMY_OF"]["current"] is True
    assert by_predicate["ENEMY_OF"]["vol_end"] is None


def test_mentions_of_drops_entities_already_shown_in_fields():
    """U5: a PPR neighbour already surfaced in fields.relationships must not repeat in
    mentions_of."""
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "raiden", "FRIEND_OF", [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}],
            is_relation=True,
        ),
    )
    ST.write_edges(conn, [
        {"subject": "shin", "predicate": "FRIEND_OF", "object": "raiden", "vol_start": 1, "vol_end": None},
        {"subject": "shin", "predicate": "FRIEND_OF", "object": "kurena", "vol_start": 1, "vol_end": None},
    ])
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    mentioned_ids = {m["entity_id"] for m in page["mentions_of"]}
    assert "raiden" not in mentioned_ids  # already in fields.relationships
    assert "kurena" in mentioned_ids


def test_mentions_of_annotated_with_shared_scene_count():
    """U5: with no direct relation but a shared-scene count available (events.db), note reports
    it instead of staying unexplained."""
    conn = _conn()
    ST.write_edges(conn, [{"subject": "shin", "predicate": "FRIEND_OF", "object": "raiden", "vol_start": 1, "vol_end": None}])

    events_conn = sqlite3.connect(":memory:")
    events_conn.row_factory = sqlite3.Row
    events_conn.executescript(
        "CREATE TABLE events (event_id TEXT PRIMARY KEY, vol INTEGER, chapter_idx INTEGER, "
        "span_index INTEGER, scene_id TEXT, participants_json TEXT, location TEXT, "
        "beat_summary TEXT, vol_start INTEGER, confidence REAL, source TEXT);"
    )
    events_conn.execute(
        "INSERT INTO events VALUES ('ev1', 1, 1, 0, 's0', ?, NULL, 'scene', 1, 0.8, '')",
        ('["shin", "raiden"]',),
    )
    events_conn.commit()

    page = AS.assemble_page(conn, events_conn, SHIN, 1, FakeSettings(), {})
    mention = next(m for m in page["mentions_of"] if m["entity_id"] == "raiden")
    assert mention["note"] == "1 shared scene"


def test_build_lead_combines_status_and_primary_affiliation():
    """S6: page["lead"] is a compact "status · affiliation" string, polarity-prefixed, using
    entities_by_id for the affiliation's canonical name."""
    conn = _conn()
    ST.write_intervals(
        conn,
        TE.assign_single_valued("shin", "STATUS", [{"value": "dead", "qualifier": None, "first_vol": 2, "claim_ids": ["c_a"]}]),
    )
    ST.write_claims(conn, [{
        "claim_id": "c_a", "subject": "shin", "predicate": "STATUS", "kind": "attribute",
        "object": None, "value": "dead", "qualifier": None, "first_vol": 2, "confidence": 0.8,
        "polarity": "presumed", "evidence": [{"para_id": "v02:c00:p0001", "quote": "ev"}], "source": "test",
    }])
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "AFFILIATED_WITH",
            [{"value_or_object": "nordlicht-squadron", "qualifier": None, "first_vol": 2, "claim_id": "c_b"}],
            is_relation=True,
        ),
    )
    entities_by_id = {"nordlicht-squadron": {"entity_id": "nordlicht-squadron", "canonical": "Nordlicht Squadron"}}
    page = AS.assemble_page(conn, None, SHIN, 2, FakeSettings(), entities_by_id)
    assert page["lead"] == "presumed dead · Nordlicht Squadron"


def test_mentions_of_never_annotates_with_a_relationship_verify_withheld():
    """Phase 30: a withheld relationship is absent from `fields.relationships`, so the other
    party is absent from `already_shown`, so `_annotated_mentions` reached its "defensive"
    relation branch and labelled the pair with the rejected predicate. Saint Metrogius's page
    model carried {"entity_id": "kraft-lawrence", "note": "Mentor of"} off an interval the
    verifier had explicitly rejected."""
    conn = _conn()
    claim = _claim("c_r", "shin", "MENTOR_OF", "relation", 1, object="lena")
    ST.write_claims(conn, [claim])
    intervals = TE.assign_multi_valued(
        "shin", "MENTOR_OF",
        [{"value_or_object": "lena", "qualifier": None, "first_vol": 1, "claim_id": "c_r"}],
        is_relation=True)
    ST.write_intervals(conn, intervals)

    related = [{"entity_id": "lena", "score": 1.0}]
    note = AS._annotated_mentions(conn, None, "shin", 1, related, set(), RELATIONS, {})[0]["note"]
    assert note == "MENTOR_OF"  # no verdict recorded: unchanged behaviour

    withheld = {intervals[0]["interval_id"]: {"verdict": "unsupported"}}
    note = AS._annotated_mentions(conn, None, "shin", 1, related, set(), RELATIONS, withheld)[0]["note"]
    assert note is None  # the rejected predicate is not offered as the reason they are related


def test_name_fields_never_repeat_the_subject_or_each_other():
    """Phase 30: Holo's page carried "Nicknames: Holo" -- her own name, under the `# Holo`
    heading -- and "Wisewolf of Yoitsu" under both Nicknames and Titles. Declaration order among
    `name_like` attributes is the precedence, so TITLE keeps what NICKNAME would repeat."""
    class S(FakeSettings):
        attributes = {
            "TITLE": {"single": False, "display": "Titles", "name_like": True},
            "NICKNAME": {"single": False, "display": "Nicknames", "name_like": True},
        }
    conn = _conn()
    values = [("TITLE", "Wisewolf of Yoitsu"), ("NICKNAME", "Wisewolf of Yoitsu"),
              ("NICKNAME", "Shin"), ("NICKNAME", "the Reaper")]
    claims, i = [], 0
    for predicate, value in values:
        i += 1
        claims.append(_claim(f"c_{i}", "shin", predicate, "attribute", 1, value=value))
    ST.write_claims(conn, claims)
    for claim in claims:
        ST.write_intervals(conn, TE.assign_multi_valued(
            "shin", claim["predicate"],
            [{"value_or_object": claim["value"], "qualifier": None, "first_vol": 1,
              "claim_id": claim["claim_id"]}],
            is_relation=False))

    entity = {**SHIN, "canonical": "Shin"}
    fields = AS.assemble_page(conn, None, entity, 1, S(), {})["fields"]

    assert [r["value"] for r in fields["title"]] == ["Wisewolf of Yoitsu"]
    # "Shin" is the page's own heading; "Wisewolf of Yoitsu" is already a Title.
    assert [r["value"] for r in fields["nickname"]] == ["the Reaper"]


def test_name_dedup_is_off_unless_an_attribute_declares_it():
    """No predicate is named in the module -- a series that declares no `name_like` attribute
    keeps every value exactly as before."""
    class S(FakeSettings):
        attributes = {"NICKNAME": {"single": False, "display": "Nicknames"}}
    conn = _conn()
    claim = _claim("c_1", "shin", "NICKNAME", "attribute", 1, value="Shin")
    ST.write_claims(conn, [claim])
    ST.write_intervals(conn, TE.assign_multi_valued(
        "shin", "NICKNAME",
        [{"value_or_object": "Shin", "qualifier": None, "first_vol": 1, "claim_id": "c_1"}],
        is_relation=False))
    fields = AS.assemble_page(conn, None, {**SHIN, "canonical": "Shin"}, 1, S(), {})["fields"]
    assert [r["value"] for r in fields["nickname"]] == ["Shin"]


def _skill_settings():
    """A page_outline with a `kind: traits` section, as config/extraction.yaml's `abilities` is."""
    class S(FakeSettings):
        traits = {**TRAITS, "SKILL": {"display": "Skill"}}
        page_outline = PAGE_OUTLINE + [
            {"key": "abilities", "kind": "traits", "title": "Abilities", "traits": ["SKILL"]}
        ]
    return S()


def test_trait_section_renders_every_row_with_its_own_evidence_and_cutoff():
    """Phase 30: `traits:` had one consumer, the prose prompt, so a SKILL interval reached the
    reader only as whatever survived a capped paragraph -- Holo's page showed 3 of her 14. A
    `kind: traits` section renders them from graph rows, the way `kind: fields` already does."""
    conn = _conn()
    claims = [
        _claim("c_s1", "shin", "SKILL", "trait", 1, value="marksmanship"),
        _claim("c_s2", "shin", "SKILL", "trait", 2, value="piloting"),
    ]
    ST.write_claims(conn, claims)
    for c in claims:
        ST.write_intervals(conn, TE.assign_multi_valued(
            "shin", "SKILL",
            [{"value_or_object": c["value"], "qualifier": None,
              "first_vol": c["first_vol"], "claim_id": c["claim_id"]}],
            is_relation=False))

    at_v1 = AS.assemble_page(conn, None, SHIN, 1, _skill_settings(), {})
    at_v2 = AS.assemble_page(conn, None, SHIN, 2, _skill_settings(), {})

    assert [r["value"] for r in at_v1["traits"]["abilities"]] == ["marksmanship"]  # v2 is not leaked
    assert [r["value"] for r in at_v2["traits"]["abilities"]] == ["marksmanship", "piloting"]
    assert at_v2["traits"]["abilities"][1]["evidence"] == ["v02:c00:p0001"]  # cited per row
    # A section is only built when the outline declares one -- no predicate is named in the module.
    assert AS.assemble_page(conn, None, SHIN, 2, FakeSettings(), {})["traits"] == {}


def test_trait_section_withholds_what_verify_rejected():
    """The verifier's withholding reached fields and relationships and never traits, so an
    interval it had rejected could still shape the page."""
    conn = _conn()
    claim = _claim("c_s1", "shin", "SKILL", "trait", 1, value="marksmanship")
    ST.write_claims(conn, [claim])
    intervals = TE.assign_multi_valued(
        "shin", "SKILL",
        [{"value_or_object": "marksmanship", "qualifier": None, "first_vol": 1, "claim_id": "c_s1"}],
        is_relation=False)
    ST.write_intervals(conn, intervals)
    assert AS.assemble_page(conn, None, SHIN, 1, _skill_settings(), {})["traits"]["abilities"]

    ST.write_verdicts(conn, [{
        "target_id": intervals[0]["interval_id"], "target_kind": "interval",
        "verdict": "unsupported", "rationale": "the evidence does not say this",
        "model": "test", "run_id": "test",
    }])
    assert AS.assemble_page(conn, None, SHIN, 1, _skill_settings(), {})["traits"]["abilities"] == []


def test_build_lead_never_states_an_inferred_default_as_fact():
    """U6 defaults have zero evidence behind them. The Overview line may show one because it
    renders "_(assumed)_" beside it; the lead is a bare scan line with nowhere to put that
    marker, so it asserted what nothing in the text supports -- both saints' v1-2 pages led with
    "alive", one of them a man Holo bit centuries before the story starts. Config-driven, so this
    holds for any attribute with a default in any series, not just STATUS."""
    conn = _conn()
    settings = FakeSettings()
    settings.attributes = dict(settings.attributes)
    settings.attributes["STATUS"] = {**settings.attributes.get("STATUS", {}),
                                     "single": True, "default": "alive"}
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "AFFILIATED_WITH",
            [{"value_or_object": "nordlicht-squadron", "qualifier": None, "first_vol": 2, "claim_id": "c_b"}],
            is_relation=True,
        ),
    )
    entities = {"nordlicht-squadron": {"entity_id": "nordlicht-squadron", "canonical": "Nordlicht Squadron"}}
    page = AS.assemble_page(conn, None, SHIN, 2, settings, entities)

    assert page["fields"]["status"]["inferred"] is True   # still materialised for the Overview
    assert page["fields"]["status"]["value"] == "alive"
    assert page["lead"] == "Nordlicht Squadron"           # but it does not headline the page
    assert "alive" not in page["lead"]


def test_build_lead_none_when_nothing_known():
    conn = _conn()
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    assert page["lead"] is None


def test_has_min_evidence():
    """S5: the page gate synth/cli.py::synthesize checks before writing a page at all."""
    conn = _conn()
    assert AS.has_min_evidence(conn, "shin", 1, 1) is False
    ST.write_intervals(
        conn,
        TE.assign_single_valued("shin", "AGE", [{"value": "16", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]}]),
    )
    assert AS.has_min_evidence(conn, "shin", 1, 1) is True
    assert AS.has_min_evidence(conn, "shin", 1, 2) is False  # only 1 interval, floor asks for 2


def test_find_name_collisions_flags_different_types_same_name():
    """S5: Saint Ruvinheigen the character vs. the city he is named for -- distinct entity_ids
    (entities/alias.py's suffix), identical canonical name, different types."""
    entities = [
        {"entity_id": "saint-ruvinheigen", "canonical": "Saint Ruvinheigen", "type": "CHARACTER"},
        {"entity_id": "saint-ruvinheigen-2", "canonical": "Saint Ruvinheigen", "type": "LOCATION"},
        {"entity_id": "shin", "canonical": "Shin", "type": "CHARACTER"},
    ]
    collisions = AS.find_name_collisions(entities)
    assert collisions == [("Saint Ruvinheigen", ["saint-ruvinheigen", "saint-ruvinheigen-2"])]


def test_find_name_collisions_ignores_same_type_duplicates_and_unique_names():
    entities = [
        {"entity_id": "shin", "canonical": "Shin", "type": "CHARACTER"},
        {"entity_id": "shin-2", "canonical": "Shin", "type": "CHARACTER"},  # same type: not a collision
        {"entity_id": "raiden", "canonical": "Raiden", "type": "CHARACTER"},
    ]
    assert AS.find_name_collisions(entities) == []


# ---------------------------------------------------------------------------
# Phase 22 C3 — fact_set_for_verification
# ---------------------------------------------------------------------------


def test_fact_set_for_verification_includes_attribute_with_its_evidence():
    conn = _conn()
    ST.write_claims(conn, [{
        "claim_id": "c_a", "subject": "shin", "predicate": "AGE", "kind": "attribute",
        "object": None, "value": "16", "qualifier": None, "first_vol": 1, "confidence": 0.9,
        "polarity": "asserted", "evidence": [{"para_id": "v01:c00:p0001", "quote": "He was sixteen."}],
        "source": "test",
    }])
    ST.write_intervals(
        conn, TE.assign_single_valued("shin", "AGE", [{"value": "16", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]}])
    )

    facts = AS.fact_set_for_verification(conn, "shin", 1, {})
    assert len(facts) == 1
    assert facts[0]["interval_id"]  # Phase 23 B5 -- verify writes its verdict against this
    fact = {k: v for k, v in facts[0].items() if k != "interval_id"}
    assert fact == {
        "kind": "attribute", "predicate": "AGE", "value": "16", "qualifier": None,
        "evidence": [{"quote": "He was sixteen.", "para_id": "v01:c00:p0001"}],
    }


def test_fact_set_for_verification_relation_keeps_stored_direction_and_resolves_names():
    """The relation entry carries the interval's OWN stored subject/object, not flipped to
    this entity's perspective the way _relationship_entries renders it for display -- the cited
    evidence quote supports exactly that stored direction."""
    conn = _conn()
    ST.write_claims(conn, [{
        "claim_id": "c_a", "subject": "shin", "predicate": "AFFILIATED_WITH", "kind": "relation",
        "object": "nordlicht-squadron", "value": None, "qualifier": "leader", "first_vol": 1,
        "confidence": 0.9, "polarity": "asserted",
        "evidence": [{"para_id": "v01:c00:p0001", "quote": "Shin led Nordlicht Squadron."}],
        "source": "test",
    }])
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "AFFILIATED_WITH",
            [{"value_or_object": "nordlicht-squadron", "qualifier": "leader", "first_vol": 1, "claim_id": "c_a"}],
            is_relation=True,
        ),
    )
    entities_by_id = {
        "shin": {"entity_id": "shin", "canonical": "Shin"},
        "nordlicht-squadron": {"entity_id": "nordlicht-squadron", "canonical": "Nordlicht Squadron"},
    }

    facts = AS.fact_set_for_verification(conn, "shin", 1, entities_by_id)
    assert len(facts) == 1
    assert facts[0]["interval_id"]  # Phase 23 B5
    fact = {k: v for k, v in facts[0].items() if k != "interval_id"}
    assert fact == {
        "kind": "relation", "predicate": "AFFILIATED_WITH", "value": "Shin -> Nordlicht Squadron",
        "qualifier": "leader",
        "evidence": [{"quote": "Shin led Nordlicht Squadron.", "para_id": "v01:c00:p0001"}],
        "pair": ["nordlicht-squadron", "shin"],
    }


def test_fact_set_for_verification_caps_evidence_and_dedupes_across_state_and_relations_at():
    """A relation interval where this entity is the subject shows up in both `state_at` (object
    is not None, skipped there) and `relations_at` -- must appear exactly once. Evidence is capped
    to `max_evidence` even when more quotes exist."""
    conn = _conn()
    ST.write_claims(conn, [
        {
            "claim_id": f"c_{i}", "subject": "shin", "predicate": "FRIEND_OF", "kind": "relation",
            "object": "raiden", "value": None, "qualifier": None, "first_vol": 1, "confidence": 0.9,
            "polarity": "asserted",
            "evidence": [{"para_id": "v01:c00:p0001", "quote": f"quote {i}"}], "source": "test",
        }
        for i in range(3)
    ])
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", "FRIEND_OF",
            [
                {"value_or_object": "raiden", "qualifier": None, "first_vol": 1, "claim_id": "c_0"},
                {"value_or_object": "raiden", "qualifier": None, "first_vol": 1, "claim_id": "c_1"},
                {"value_or_object": "raiden", "qualifier": None, "first_vol": 1, "claim_id": "c_2"},
            ],
            is_relation=True,
        ),
    )
    entities_by_id = {
        "shin": {"entity_id": "shin", "canonical": "Shin"},
        "raiden": {"entity_id": "raiden", "canonical": "Raiden"},
    }

    facts = AS.fact_set_for_verification(conn, "shin", 1, entities_by_id, max_evidence=2)
    assert len(facts) == 1
    assert len(facts[0]["evidence"]) == 2


def test_fact_set_for_verification_empty_when_nothing_visible():
    conn = _conn()
    assert AS.fact_set_for_verification(conn, "shin", 1, {}) == []


def _relation_claim(claim_id, subject, predicate, object, first_vol, polarity):
    return {
        "claim_id": claim_id, "subject": subject, "predicate": predicate, "kind": "relation",
        "object": object, "value": None, "qualifier": None, "first_vol": first_vol,
        "confidence": 0.9, "polarity": polarity, "source": "test",
        "evidence": [{"para_id": f"v{first_vol:02d}:c00:p0001", "quote": "ev"}],
    }


def test_denied_relation_is_dropped_and_presumed_relation_is_marked():
    """`_relationship_entries` was the one field builder that never consulted `_claim_polarity`,
    so a claim stored `polarity: "denied"` rendered identically to an asserted one -- the live
    bug was Holo's page shipping "Saint Ruvinheigen — Killed" off "I did not kill him", and the
    same sink produced Phase 23's false SPOUSE_OF. Denied must vanish (absence is the denial);
    presumed must still render, marked, per config/extraction.yaml's polarity block."""
    conn = _conn()
    ST.write_claims(conn, [
        _relation_claim("c_denied", "shin", "ENEMY_OF", "raiden", 1, "denied"),
        _relation_claim("c_presumed", "shin", "FRIEND_OF", "kurena", 1, "presumed"),
    ])
    ST.write_intervals(conn, [
        *TE.assign_multi_valued("shin", "ENEMY_OF", [
            {"value_or_object": "raiden", "qualifier": None, "first_vol": 1, "claim_id": "c_denied"},
        ], is_relation=True),
        *TE.assign_multi_valued("shin", "FRIEND_OF", [
            {"value_or_object": "kurena", "qualifier": None, "first_vol": 1, "claim_id": "c_presumed"},
        ], is_relation=True),
    ])

    entries = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})["fields"]["relationships"]

    assert [e["entity_id"] for e in entries] == ["kurena"]  # raiden's denied ENEMY_OF is gone
    assert entries[0]["blurb"] == "presumed Friend of"  # not collapsed into a plain assertion
    # the denied interval itself is untouched -- still queryable via wiki explain/trace
    assert conn.execute("SELECT COUNT(*) FROM intervals").fetchone()[0] == 2


def test_object_display_renders_passive_wording_on_the_objects_page():
    """Phase 26: a directional predicate with no declared `inverse` used to fall back to itself
    on the OBJECT's page, so the victim's page rendered the killer's wording -- the live v1-2
    build shipped "Holo — Killed" on Liebert's page, directly above "Status: alive".
    `object_display` supplies "Killed by" without adding a KILLED_BY predicate to the
    extractor's prompt vocabulary."""
    conn = _conn()
    ST.write_intervals(conn, TE.assign_multi_valued(
        "holo", "KILLED",
        [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_k"}],
        is_relation=True,
    ))
    page = AS.assemble_page(conn, None, SHIN, 2, FakeSettings(), {})
    entry = next(e for e in page["fields"]["relationships"] if e["entity_id"] == "holo")
    assert entry["label"] == "Killed by"

    # The subject's own page keeps the active wording.
    page_holo = AS.assemble_page(
        conn, None, {"entity_id": "holo", "canonical": "Holo", "first_vol": 1}, 2, FakeSettings(), {},
    )
    assert next(e for e in page_holo["fields"]["relationships"] if e["entity_id"] == "shin")["label"] == "Killed"


def test_predicate_without_object_display_still_falls_back_to_its_own_display():
    """The fallback path is unchanged for a directional predicate that declares no
    `object_display` -- this is the pre-Phase-26 behaviour, kept deliberately rather than
    invented for every predicate at once."""
    conn = _conn()
    ST.write_intervals(conn, TE.assign_multi_valued(
        "holo", "SAVED",
        [{"value_or_object": "shin", "qualifier": None, "first_vol": 1, "claim_id": "c_s"}],
        is_relation=True,
    ))
    page = AS.assemble_page(conn, None, SHIN, 2, FakeSettings(), {})
    assert next(e for e in page["fields"]["relationships"] if e["entity_id"] == "holo")["label"] == "Saved"


def test_quote_notability_prefers_a_substantive_line_over_conversational_filler():
    """Phase 26: the live v1-2 wiki shipped `"Listen, you"` as Holo's top quote, ahead of 765
    alternatives, because ranking was by extraction confidence -- which measures "is this
    really a quote by this speaker", spans only 0.89-0.98 across the corpus, and therefore
    left the top-3 as arbitrary DB order."""
    filler = {"quote": "Listen, you", "participants": 2}
    substantive = {
        "quote": "I am Holo the Wisewolf, and I have kept this village's harvest for centuries.",
        "participants": 2,
    }
    assert AS._quote_notability(substantive) > AS._quote_notability(filler)


def test_quote_notability_rewards_completeness_independently_of_length():
    """Two short lines, one a finished thought."""
    incomplete = {"quote": "Listen, you", "participants": 1}
    complete = {"quote": "Am I wrong, then?", "participants": 1}
    assert AS._quote_notability(complete) > AS._quote_notability(incomplete)


def test_quote_notability_is_zero_for_empty_text():
    assert AS._quote_notability({"quote": "  ", "participants": 3}) == 0.0


def test_affiliation_to_an_entity_the_character_opposes_is_not_membership():
    """Phase 26: Holo's strongest Church claim is ENEMY_OF at confidence 1.0 ("the Church
    sought to end her life"), yet a separate AFFILIATED_WITH carried the qualifier "member"
    off a co-location reading, and that one word headlined her page. An organisation a
    character is in open conflict with is not one they belong to."""
    conn = _conn()
    ST.write_intervals(conn, TE.assign_multi_valued(
        "shin", "AFFILIATED_WITH",
        [{"value_or_object": "the-church", "qualifier": "member", "first_vol": 1, "claim_id": "c_a"}],
        is_relation=True,
    ))
    ST.write_intervals(conn, TE.assign_multi_valued(
        "shin", "ENEMY_OF",
        [{"value_or_object": "the-church", "qualifier": None, "first_vol": 1, "claim_id": "c_b"}],
        is_relation=True,
    ))
    page = AS.assemble_page(conn, None, SHIN, 1, FakeSettings(), {})
    # Filed under `other_ties`, not `affiliations` -- `eval/gold.py` treats anything in the
    # affiliations list as an affiliation claim regardless of any flag on it.
    assert "affiliations" not in page["fields"]
    tie = next(a for a in page["fields"]["other_ties"] if a["entity_id"] == "the-church")
    assert tie["membership"] is False
    # ... and it must not headline the page.
    assert "The Church" not in (page["lead"] or "")


def test_non_membership_qualifiers_are_flagged():
    """The config's AFFILIATED_WITH note already says captivity/debt/opposition is not
    affiliation; nothing enforced it after extraction."""
    for qualifier in ("held captive", "seeking sanctuary", "visitor", "indebted to them"):
        assert AS._is_membership_role(qualifier) is False, qualifier
    for qualifier in ("leader", "employee", "member", None, ""):
        assert AS._is_membership_role(qualifier) is True, qualifier


def test_nothing_verify_withheld_reaches_the_page_model_by_any_route():
    """Phase 30 invariant. The verdict gate has now been forgotten three times: fields and
    relationships got it in Phase 23 B2, `_build_trait_sections` did not, `_annotated_mentions`
    did not. Each was found by reading a rendered page, which does not scale and did not catch
    the other two. This asserts the property itself over the whole page model, so the NEXT
    consumer of `temporal.state_at`/`relations_between` fails here instead of shipping."""
    class S(FakeSettings):
        attributes = {"OCCUPATION": {"single": True, "display": "Role"}}
        traits = {"SKILL": {"display": "Skill"}}
        page_outline = PAGE_OUTLINE + [
            {"key": "abilities", "kind": "traits", "title": "Abilities", "traits": ["SKILL"]}
        ]

    conn = _conn()
    marker = "zzmarkerzz"
    claims = [
        _claim("c_a", "shin", "OCCUPATION", "attribute", 1, value=f"{marker}-role"),
        _claim("c_t", "shin", "SKILL", "trait", 1, value=f"{marker}-skill"),
        _claim("c_r", "shin", "MENTOR_OF", "relation", 1, object="lena"),
    ]
    ST.write_claims(conn, claims)
    withheld = {}
    for claim in claims:
        intervals = TE.assign_multi_valued(
            "shin", claim["predicate"],
            [{"value_or_object": claim["object"] or claim["value"], "qualifier": None,
              "first_vol": 1, "claim_id": claim["claim_id"]}],
            is_relation=claim["kind"] == "relation")
        ST.write_intervals(conn, intervals)
        withheld[intervals[0]["interval_id"]] = True

    # Every one of them present first, so the test cannot pass by assembling nothing at all.
    before = json.dumps(AS.assemble_page(conn, None, SHIN, 1, S(), {}))
    assert before.count(marker) == 2 and "lena" in before

    ST.write_verdicts(conn, [
        {"target_id": tid, "target_kind": "interval", "verdict": "unsupported",
         "rationale": "the evidence does not say this", "model": "test", "run_id": "test"}
        for tid in withheld
    ])
    after = json.dumps(AS.assemble_page(conn, None, SHIN, 1, S(), {}))
    assert marker not in after, "a withheld interval's value reached the page model"
    assert "lena" not in after, "a withheld relation reached the page model"


def test_a_trait_row_contained_in_a_longer_sibling_folds_into_it_with_its_citations():
    """[30] Lawrence's page would list "own a shop" and "to open his own shop" as two goals.
    Function words are ignored, a single word is not dropped merely for being short, and along a
    chain the citations land on the row that survives."""
    def row(value, *ev):
        return {"value": value, "evidence": list(ev)}

    rows = [row("own a shop", "p1"), row("to open his own shop", "p2"), row("revenge", "p3"),
            row("shop", "p4")]
    out = AS._fold_contained_rows(rows)
    assert [r["value"] for r in out] == ["to open his own shop", "revenge"]
    assert out[0]["evidence"] == ["p1", "p2", "p4"]


def test_a_withheld_trait_never_reaches_a_prose_prompt():
    """[30] Norah's History called her "an orphan" from a BACKGROUND interval verification had
    withheld: fields and trait lists applied the verdict, the prose input did not."""
    conn = _conn()
    intervals = TE.assign_multi_valued(
        "shin", "BACKGROUND",
        [{"value_or_object": "orphaned young", "qualifier": None, "first_vol": 1, "claim_id": "c_a"},
         {"value_or_object": "raised in a camp", "qualifier": None, "first_vol": 1, "claim_id": "c_b"}],
        is_relation=False,
    )
    ST.write_intervals(conn, intervals)
    withheld = next(i["interval_id"] for i in intervals if i["value"] == "orphaned young")
    ST.write_verdicts(conn, [{"target_id": withheld, "target_kind": "interval",
                              "verdict": "unsupported", "rationale": "inference", "model": "m", "run_id": "r"}])

    values = [t["value"] for t in AS.trait_values_at(conn, "shin", 1, {"BACKGROUND": {}})["BACKGROUND"]]
    assert values == ["raised in a camp"]


def test_a_trait_section_leaves_out_rows_matching_its_exclude_pattern():
    """[30] Bookworm listed Lutz "illiterate" under Abilities: a true SKILL row, not an ability."""
    class S(FakeSettings):
        traits = {**TRAITS, "SKILL": {"display": "Skill"}}
        page_outline = PAGE_OUTLINE + [{"key": "abilities", "kind": "traits", "title": "Abilities",
                                        "traits": ["SKILL"], "exclude_pattern": r"^(illiterate)\b"}]
    conn = _conn()
    claims = [_claim("c_s1", "shin", "SKILL", "trait", 1, value="illiterate"),
              _claim("c_s2", "shin", "SKILL", "trait", 1, value="woodworking")]
    ST.write_claims(conn, claims)
    for c in claims:
        ST.write_intervals(conn, TE.assign_multi_valued("shin", "SKILL", [
            {"value_or_object": c["value"], "qualifier": None, "first_vol": 1,
             "claim_id": c["claim_id"]}], is_relation=False))
    page = AS.assemble_page(conn, None, SHIN, 1, S(), {})
    assert [r["value"] for r in page["traits"]["abilities"]] == ["woodworking"]


def test_a_claimed_default_status_does_not_headline_the_page():
    """[30] Lutz's index entry read "— alive" because his STATUS was claimed; Myne's, inferred,
    read nothing. The default is not news either way; a non-default status still leads."""
    alive = {"status": {"value": "alive", "polarity": "asserted"}}
    dead = {"status": {"value": "deceased", "polarity": "asserted"}}
    assert AS._build_lead(alive, {}, "alive") is None
    assert AS._build_lead(dead, {}, "alive") == "deceased"
