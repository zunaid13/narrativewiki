"""Phase 19: tests for graph/events.py and graph/event_build.py."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from narrativewiki.graph.event_build import _make_claim_id, _scene_to_event, _scene_to_event_claims, build_events
from narrativewiki.graph.events import (
    character_events_at,
    connect,
    event_claims_at,
    events_at,
    events_in_volume,
    group_events_at,
    make_event_id,
    reset,
    shared_events_at,
    write_event_claims,
    write_events,
)


# ---------------------------------------------------------------------------
# make_event_id
# ---------------------------------------------------------------------------


def test_make_event_id_format():
    assert make_event_id(1, 3, 2) == "ev_v01c03s002"
    assert make_event_id(12, 0, 10) == "ev_v12c00s010"


# ---------------------------------------------------------------------------
# connect / schema
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path):
    db = tmp_path / "events.db"
    c = connect(db)
    yield c
    c.close()


def test_connect_creates_both_tables(conn):
    tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "events" in tables
    assert "event_claims" in tables


def test_reset_empties_tables(conn):
    write_events(conn, [
        {
            "event_id": "ev_v01c00s000",
            "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000",
            "participants": ["holo"],
            "location": None,
            "beat_summary": "Holo meets Lawrence.",
            "vol_start": 1,
            "confidence": 0.9,
            "source": "test",
        }
    ])
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    reset(conn)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


# ---------------------------------------------------------------------------
# write_events / events_at
# ---------------------------------------------------------------------------


_SAMPLE_EVENT = {
    "event_id": "ev_v01c02s001",
    "vol": 1,
    "chapter_idx": 2,
    "span_index": 1,
    "scene_id": "sn_v01c02s001",
    "participants": ["holo", "kraft-lawrence"],
    "location": "pasroe",
    "beat_summary": "Holo reveals her true form to Lawrence.",
    "vol_start": 1,
    "confidence": 0.85,
    "source": "test_source",
}

_SAMPLE_EVENT_V2 = {
    "event_id": "ev_v02c00s000",
    "vol": 2,
    "chapter_idx": 0,
    "span_index": 0,
    "scene_id": "sn_v02c00s000",
    "participants": ["holo"],
    "location": None,
    "beat_summary": "Holo is alone.",
    "vol_start": 2,
    "confidence": 0.7,
    "source": "test_source",
}


def test_write_and_read_events(conn):
    write_events(conn, [_SAMPLE_EVENT])
    rows = events_at(conn, vol=1)
    assert len(rows) == 1
    assert rows[0]["event_id"] == "ev_v01c02s001"
    assert rows[0]["beat_summary"] == "Holo reveals her true form to Lawrence."
    participants = json.loads(rows[0]["participants_json"])
    assert "holo" in participants
    assert rows[0]["core_para_ids_json"] == "[]"  # not supplied by _SAMPLE_EVENT -- default


def test_write_and_read_events_core_para_ids_round_trip(conn):
    """core_para_ids -- the paragraphs beat_summary was actually paraphrased from -- survives
    a write/read round trip so generate_chronology can fold it into evidence."""
    event = dict(_SAMPLE_EVENT, core_para_ids=["v01:c02:p0100", "v01:c02:p0101"])
    write_events(conn, [event])
    rows = events_at(conn, vol=1)
    assert json.loads(rows[0]["core_para_ids_json"]) == ["v01:c02:p0100", "v01:c02:p0101"]


def test_events_at_spoiler_filter(conn):
    """events_at must exclude events whose vol_start > cutoff."""
    write_events(conn, [_SAMPLE_EVENT, _SAMPLE_EVENT_V2])
    rows_v1 = events_at(conn, vol=1)
    assert len(rows_v1) == 1
    assert rows_v1[0]["vol"] == 1

    rows_v2 = events_at(conn, vol=2)
    assert len(rows_v2) == 2


def test_events_at_returns_in_reading_order(conn):
    """Events returned in (vol, chapter_idx, span_index) order."""
    e1 = dict(_SAMPLE_EVENT, event_id="ev_v01c02s001", chapter_idx=2, span_index=1)
    e0 = dict(_SAMPLE_EVENT, event_id="ev_v01c00s000", chapter_idx=0, span_index=0)
    write_events(conn, [e1, e0])  # write out of order
    rows = events_at(conn, vol=1)
    assert rows[0]["chapter_idx"] == 0
    assert rows[1]["chapter_idx"] == 2


# ---------------------------------------------------------------------------
# character_events_at
# ---------------------------------------------------------------------------


def test_character_events_at_filters_by_participant(conn):
    """character_events_at should only return events where entity_id is a participant."""
    write_events(conn, [_SAMPLE_EVENT, _SAMPLE_EVENT_V2])
    # holo appears in both; kraft-lawrence only in v1 event
    holo_rows = character_events_at(conn, "holo", vol=2)
    assert len(holo_rows) == 2

    kl_rows = character_events_at(conn, "kraft-lawrence", vol=2)
    assert len(kl_rows) == 1
    assert kl_rows[0]["vol"] == 1


def test_character_events_at_spoiler_filter(conn):
    write_events(conn, [_SAMPLE_EVENT, _SAMPLE_EVENT_V2])
    # At vol=1, only the v1 event should appear for holo
    rows = character_events_at(conn, "holo", vol=1)
    assert len(rows) == 1


def test_character_events_at_no_false_prefix_match(conn):
    """'holo' must not match 'holo-clone' if only 'holo-clone' is in participants."""
    clone_event = dict(
        _SAMPLE_EVENT,
        event_id="ev_v01c03s000",
        chapter_idx=3,
        span_index=0,
        participants=["holo-clone"],
    )
    write_events(conn, [clone_event])
    holo_rows = character_events_at(conn, "holo", vol=1)
    assert len(holo_rows) == 0  # "holo" not present, only "holo-clone"


# ---------------------------------------------------------------------------
# shared_events_at (Phase 21)
# ---------------------------------------------------------------------------


def test_shared_events_at_requires_both_participants(conn):
    """_SAMPLE_EVENT has both holo and kraft-lawrence; _SAMPLE_EVENT_V2 has holo alone."""
    write_events(conn, [_SAMPLE_EVENT, _SAMPLE_EVENT_V2])
    rows = shared_events_at(conn, "holo", "kraft-lawrence", vol=2)
    assert len(rows) == 1
    assert rows[0]["event_id"] == "ev_v01c02s001"


def test_shared_events_at_no_false_prefix_match(conn):
    """'holo' must not match 'holo-clone' as a shared participant."""
    clone_event = dict(
        _SAMPLE_EVENT,
        event_id="ev_v01c03s000",
        chapter_idx=3,
        span_index=0,
        participants=["holo-clone", "kraft-lawrence"],
    )
    write_events(conn, [clone_event])
    rows = shared_events_at(conn, "holo", "kraft-lawrence", vol=1)
    assert rows == []


def test_shared_events_at_spoiler_filter(conn):
    """A shared event only at v2 must not appear when the reader's cutoff is v1."""
    v2_shared = dict(
        _SAMPLE_EVENT_V2,
        event_id="ev_v02c00s001",
        participants=["holo", "kraft-lawrence"],
        vol_start=2,
    )
    write_events(conn, [_SAMPLE_EVENT, v2_shared])
    rows_v1 = shared_events_at(conn, "holo", "kraft-lawrence", vol=1)
    assert [r["event_id"] for r in rows_v1] == ["ev_v01c02s001"]

    rows_v2 = shared_events_at(conn, "holo", "kraft-lawrence", vol=2)
    assert len(rows_v2) == 2


# ---------------------------------------------------------------------------
# group_events_at (Phase 21 part 2)
# ---------------------------------------------------------------------------


def test_group_events_at_requires_min_participants(conn):
    """_SAMPLE_EVENT has both holo and kraft-lawrence; _SAMPLE_EVENT_V2 has holo alone."""
    write_events(conn, [_SAMPLE_EVENT, _SAMPLE_EVENT_V2])
    rows = group_events_at(conn, ["holo", "kraft-lawrence", "someone-else"], vol=2, min_participants=2)
    assert [r["event_id"] for r in rows] == ["ev_v01c02s001"]


def test_group_events_at_short_circuits_below_min_participants():
    """Fewer entity_ids than min_participants can never qualify -- no query needed at all."""
    assert group_events_at(None, ["holo"], vol=1, min_participants=2) == []


def test_group_events_at_no_false_prefix_match(conn):
    clone_event = dict(
        _SAMPLE_EVENT,
        event_id="ev_v01c03s000",
        chapter_idx=3,
        span_index=0,
        participants=["holo-clone", "kraft-lawrence"],
    )
    write_events(conn, [clone_event])
    rows = group_events_at(conn, ["holo", "kraft-lawrence"], vol=1, min_participants=2)
    assert rows == []  # only "holo-clone" + "kraft-lawrence" present, not "holo"


def test_group_events_at_spoiler_filter(conn):
    v2_group = dict(
        _SAMPLE_EVENT_V2,
        event_id="ev_v02c00s001",
        participants=["holo", "kraft-lawrence"],
        vol_start=2,
    )
    write_events(conn, [_SAMPLE_EVENT, v2_group])
    rows_v1 = group_events_at(conn, ["holo", "kraft-lawrence"], vol=1, min_participants=2)
    assert [r["event_id"] for r in rows_v1] == ["ev_v01c02s001"]

    rows_v2 = group_events_at(conn, ["holo", "kraft-lawrence"], vol=2, min_participants=2)
    assert len(rows_v2) == 2


# ---------------------------------------------------------------------------
# events_in_volume (Phase 21 part 3)
# ---------------------------------------------------------------------------


def test_events_in_volume_returns_only_that_volumes_own_events(conn):
    write_events(conn, [_SAMPLE_EVENT, _SAMPLE_EVENT_V2])
    rows_v1 = events_in_volume(conn, 1)
    assert [r["event_id"] for r in rows_v1] == ["ev_v01c02s001"]

    rows_v2 = events_in_volume(conn, 2)
    assert [r["event_id"] for r in rows_v2] == ["ev_v02c00s000"]


def test_events_in_volume_returns_in_reading_order(conn):
    e1 = dict(_SAMPLE_EVENT, event_id="ev_v01c02s001", chapter_idx=2, span_index=1)
    e0 = dict(_SAMPLE_EVENT, event_id="ev_v01c00s000", chapter_idx=0, span_index=0)
    write_events(conn, [e1, e0])
    rows = events_in_volume(conn, 1)
    assert [r["event_id"] for r in rows] == ["ev_v01c00s000", "ev_v01c02s001"]


def test_events_in_volume_empty_for_a_volume_with_no_events(conn):
    write_events(conn, [_SAMPLE_EVENT])
    assert events_in_volume(conn, 3) == []


# ---------------------------------------------------------------------------
# event_claims / event_claims_at
# ---------------------------------------------------------------------------


_SAMPLE_CLAIM = {
    "claim_id": "ec_abc123",
    "event_id": "ev_v01c02s001",
    "kind": "quote",
    "subject": None,
    "predicate": None,
    "from_value": None,
    "to_value": None,
    "object": "kraft-lawrence",
    "note": None,
    "speaker": "holo",
    "para_id": "v01:c02:p0123",
    "quote": "I am Holo the Wise Wolf.",
    "vol": 1,
    "confidence": 0.9,
    "source": "test",
}


def test_write_and_read_event_claims(conn):
    write_event_claims(conn, [_SAMPLE_CLAIM])
    rows = event_claims_at(conn, "ev_v01c02s001", vol=1)
    assert len(rows) == 1
    assert rows[0]["kind"] == "quote"
    assert rows[0]["quote"] == "I am Holo the Wise Wolf."


def test_event_claims_at_vol_filter(conn):
    v2_claim = dict(_SAMPLE_CLAIM, claim_id="ec_xyz999", vol=2, event_id="ev_v01c02s001")
    write_event_claims(conn, [_SAMPLE_CLAIM, v2_claim])
    at_v1 = event_claims_at(conn, "ev_v01c02s001", vol=1)
    assert len(at_v1) == 1  # v2 claim excluded
    at_v2 = event_claims_at(conn, "ev_v01c02s001", vol=2)
    assert len(at_v2) == 2


# ---------------------------------------------------------------------------
# _scene_to_event / _scene_to_event_claims (unit-test the transform)
# ---------------------------------------------------------------------------


_FULL_SCENE = {
    "scene_id": "sn_v01c02s001",
    "vol": 1,
    "chapter_idx": 2,
    "span_index": 1,
    "para_ids": ["v01:c02:p0100", "v01:c02:p0101"],
    "core_para_ids": ["v01:c02:p0100"],
    "participants": ["holo", "kraft-lawrence"],
    "location": "pasroe",
    "beat_summary": "Holo reveals herself.",
    "state_changes": [
        {
            "subject": "holo",
            "predicate": "STATUS",
            "from_value": "hidden",
            "to_value": "revealed",
            "object": None,
            "note": "Holo drops her disguise",
            "evidence": [{"para_id": "v01:c02:p0100", "quote": "She let the illusion fall."}],
        }
    ],
    "quotes": [
        {
            "speaker": "holo",
            "addressee": "kraft-lawrence",
            "para_id": "v01:c02:p0101",
            "print_page": 42,
            "quote": "I am Holo the Wise Wolf.",
        }
    ],
    "confidence": 0.88,
    "source": "scenes:v01c02",
}

_EMPTY_SCENE = {
    "scene_id": "sn_v01c03s000",
    "vol": 1,
    "chapter_idx": 3,
    "span_index": 0,
    "para_ids": ["v01:c03:p0200"],
    "core_para_ids": ["v01:c03:p0200"],
    "participants": [],
    "location": None,
    "beat_summary": "",
    "state_changes": [],
    "quotes": [],
    "confidence": 0.5,
    "source": "scenes:v01c03",
}


def test_scene_to_event_full_scene():
    ev = _scene_to_event(_FULL_SCENE)
    assert ev is not None
    assert ev["event_id"] == "ev_v01c02s001"
    assert ev["vol"] == 1
    assert "holo" in ev["participants"]
    assert ev["beat_summary"] == "Holo reveals herself."
    assert ev["core_para_ids"] == ["v01:c02:p0100"]


def test_scene_to_event_empty_scene_returns_none():
    """Empty spans (no participants, no facts) must not become event nodes."""
    assert _scene_to_event(_EMPTY_SCENE) is None


def test_scene_to_event_claims_full_scene():
    event_id = "ev_v01c02s001"
    claims = _scene_to_event_claims(event_id, _FULL_SCENE)
    kinds = {c["kind"] for c in claims}
    assert "state_change" in kinds
    assert "quote" in kinds
    sc_claims = [c for c in claims if c["kind"] == "state_change"]
    assert sc_claims[0]["from_value"] == "hidden"
    assert sc_claims[0]["to_value"] == "revealed"
    q_claims = [c for c in claims if c["kind"] == "quote"]
    assert q_claims[0]["speaker"] == "holo"
    assert q_claims[0]["quote"] == "I am Holo the Wise Wolf."


def test_scene_to_event_claims_empty_scene_returns_empty():
    claims = _scene_to_event_claims("ev_v01c03s000", _EMPTY_SCENE)
    assert claims == []


# ---------------------------------------------------------------------------
# build_events (integration: scene files -> events.db)
# ---------------------------------------------------------------------------


def test_build_events_from_scene_files(tmp_path, conn):
    scene_file = tmp_path / "v01.jsonl"
    scene_file.write_text(json.dumps(_FULL_SCENE) + "\n" + json.dumps(_EMPTY_SCENE) + "\n")

    n_events, n_claims = build_events([scene_file], conn, force=True)
    assert n_events == 1  # empty scene excluded
    assert n_claims == 2  # 1 state_change + 1 quote


def test_build_events_empty_scene_list(conn):
    n_events, n_claims = build_events([], conn, force=True)
    assert n_events == 0
    assert n_claims == 0


def test_build_events_missing_file_is_skipped(tmp_path, conn):
    missing = tmp_path / "v99.jsonl"  # does not exist
    n_events, n_claims = build_events([missing], conn, force=True)
    assert n_events == 0


def test_build_events_force_resets_stale_rows(tmp_path, conn):
    scene_file = tmp_path / "v01.jsonl"
    scene_file.write_text(json.dumps(_FULL_SCENE) + "\n")
    build_events([scene_file], conn, force=True)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1

    # Force again with empty file -> should reset to 0
    scene_file.write_text("")
    build_events([scene_file], conn, force=True)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_make_claim_id_is_stable():
    id1 = _make_claim_id("ev_v01c02s001", "quote", "v01:c02:p0100", "Hello world")
    id2 = _make_claim_id("ev_v01c02s001", "quote", "v01:c02:p0100", "Hello world")
    assert id1 == id2
    assert id1.startswith("ec_")