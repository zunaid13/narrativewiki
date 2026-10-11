"""Phase 19: tests for synth/prose.py::generate_chronology and the events sentinel dispatch."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from narrativewiki.synth.prose import ProseText, generate_chronology, generate_prose


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_events_conn(events: list[dict]) -> sqlite3.Connection:
    """Build an in-memory events.db with just the tables generate_chronology reads."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY, vol INTEGER, chapter_idx INTEGER, span_index INTEGER,
            scene_id TEXT, participants_json TEXT, location TEXT, beat_summary TEXT,
            core_para_ids_json TEXT, vol_start INTEGER, confidence REAL, source TEXT
        );
        CREATE TABLE event_claims (
            claim_id TEXT PRIMARY KEY, event_id TEXT, kind TEXT, subject TEXT,
            predicate TEXT, from_value TEXT, to_value TEXT, object TEXT, note TEXT,
            speaker TEXT, para_id TEXT, quote TEXT, vol INTEGER, confidence REAL, source TEXT
        );
    """)
    for ev in events:
        conn.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                ev["event_id"], ev["vol"], ev["chapter_idx"], ev["span_index"],
                ev["scene_id"], json.dumps(ev.get("participants", [])), ev.get("location"),
                ev["beat_summary"], json.dumps(ev.get("core_para_ids", [])),
                ev["vol_start"], ev.get("confidence", 0.8), ev.get("source", ""),
            ),
        )
    conn.commit()
    return conn


def _make_client(text: str = "A story was told.") -> MagicMock:
    client = MagicMock()
    client.complete_json.return_value = ProseText(text=text)
    return client


_ENTITY = {"entity_id": "holo", "canonical": "Holo"}

_SECTION = {
    "key": "chronology",
    "kind": "prose",
    "title": "Chronology",
    "traits": [],
    "min_sentences": 3,
    "max_sentences": 8,
    "subject": "a narrative arc",
    "source": "events",
}


# ---------------------------------------------------------------------------
# generate_chronology
# ---------------------------------------------------------------------------


def test_chronology_returns_none_when_no_events():
    conn = _make_events_conn([])
    client = _make_client()
    result = generate_chronology(conn, client, _ENTITY, upto_vol=1, section=_SECTION, stage="prose")
    assert result is None
    client.complete_json.assert_not_called()
    conn.close()


def test_chronology_calls_llm_with_beat_summaries():
    events = [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
            "beat_summary": "Holo boards the cart.", "vol_start": 1,
        },
        {
            "event_id": "ev_v01c01s000", "vol": 1, "chapter_idx": 1, "span_index": 0,
            "scene_id": "sn_v01c01s000", "participants": ["holo", "kraft-lawrence"],
            "location": None, "beat_summary": "Lawrence makes a deal.", "vol_start": 1,
        },
    ]
    conn = _make_events_conn(events)
    client = _make_client("Holo boards a cart. Lawrence makes a deal.")
    result = generate_chronology(conn, client, _ENTITY, upto_vol=1, section=_SECTION, stage="prose")
    assert result is not None
    assert result["text"] == "Holo boards a cart. Lawrence makes a deal."
    # Check prompt content
    call_args = client.complete_json.call_args
    prompt: str = call_args[0][1]
    assert "Holo boards the cart." in prompt
    assert "Lawrence makes a deal." in prompt
    conn.close()


def test_chronology_spoiler_filter():
    """Events with vol_start > upto_vol must not reach the prompt."""
    events = [
        {
            "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
            "beat_summary": "Early event.", "vol_start": 1,
        },
        {
            "event_id": "ev_v03c00s000", "vol": 3, "chapter_idx": 0, "span_index": 0,
            "scene_id": "sn_v03c00s000", "participants": ["holo"], "location": None,
            "beat_summary": "SPOILER: future event.", "vol_start": 3,
        },
    ]
    conn = _make_events_conn(events)
    client = _make_client("Only early things.")
    generate_chronology(conn, client, _ENTITY, upto_vol=1, section=_SECTION, stage="prose")
    prompt: str = client.complete_json.call_args[0][1]
    assert "SPOILER" not in prompt
    conn.close()


def test_chronology_evidence_is_para_ids_from_event_claims():
    """evidence list is derived from event_claims.para_id, not model output."""
    conn = _make_events_conn([{
        "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
        "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
        "beat_summary": "Holo boards.", "vol_start": 1,
    }])
    # Insert an event_claim for this event
    conn.execute(
        "INSERT INTO event_claims VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("ec_abc", "ev_v01c00s000", "quote", None, None, None, None, None,
         None, "holo", "v01:c00:p0010", "Hello.", 1, 0.9, "test"),
    )
    conn.commit()
    client = _make_client("Text.")
    result = generate_chronology(conn, client, _ENTITY, upto_vol=1, section=_SECTION, stage="prose")
    assert result is not None
    assert "v01:c00:p0010" in result["evidence"]
    conn.close()


def test_chronology_evidence_does_not_include_core_para_ids():
    """generate_chronology's stored `evidence` deliberately stays event_claims-only -- a span's
    `core_para_ids` (a chapter-scale slice, sometimes 100+ paragraphs) is real grounding for
    `beat_summary` but too coarse for the page's own citation list. `wiki audit eval` checks that
    broader grounding separately, straight from events.db (eval/gold.py)."""
    conn = _make_events_conn([{
        "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
        "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
        "beat_summary": "Holo boards.", "vol_start": 1,
        "core_para_ids": ["v01:c00:p0005", "v01:c00:p0006"],
    }])
    client = _make_client("Text.")
    result = generate_chronology(conn, client, _ENTITY, upto_vol=1, section=_SECTION, stage="prose")
    assert result is not None
    assert result["evidence"] == []
    conn.close()


# ---------------------------------------------------------------------------
# generate_prose — dispatch of "events" sentinel
# ---------------------------------------------------------------------------


class _FakeSettings:
    def __init__(self, page_outline: list[dict], traits: dict | None = None):
        self.page_outline = page_outline
        self.traits = traits or {}


def _make_graph_conn() -> sqlite3.Connection:
    """An empty graph.db with the real schema (trait_values_at also reads `verdicts` now)."""
    from narrativewiki.graph import store

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(store.SCHEMA)
    return conn


def test_generate_prose_events_sentinel_calls_generate_chronology():
    """When source == 'events' and events_conn is provided, the LLM is called once for
    the chronology section."""
    events_conn = _make_events_conn([{
        "event_id": "ev_v01c00s000", "vol": 1, "chapter_idx": 0, "span_index": 0,
        "scene_id": "sn_v01c00s000", "participants": ["holo"], "location": None,
        "beat_summary": "Something happened.", "vol_start": 1,
    }])
    graph_conn = _make_graph_conn()
    client = _make_client("Chronology text.")
    settings = _FakeSettings(page_outline=[_SECTION])

    result = generate_prose(
        graph_conn, client, _ENTITY, upto_vol=1, settings=settings,
        stage="prose", events_conn=events_conn,
    )
    assert "chronology" in result
    assert result["chronology"] is not None
    assert result["chronology"]["text"] == "Chronology text."
    client.complete_json.assert_called_once()
    events_conn.close()
    graph_conn.close()


def test_generate_prose_events_sentinel_without_events_conn_returns_none():
    """When events_conn is None, the chronology section is None (no LLM call)."""
    graph_conn = _make_graph_conn()
    client = _make_client()
    settings = _FakeSettings(page_outline=[_SECTION])

    result = generate_prose(
        graph_conn, client, _ENTITY, upto_vol=1, settings=settings,
        stage="prose", events_conn=None,
    )
    assert result["chronology"] is None
    client.complete_json.assert_not_called()
    graph_conn.close()


def test_generate_prose_events_sentinel_no_events_returns_none():
    """When events_conn is provided but no events for this character, returns None."""
    events_conn = _make_events_conn([])  # empty
    graph_conn = _make_graph_conn()
    client = _make_client()
    settings = _FakeSettings(page_outline=[_SECTION])

    result = generate_prose(
        graph_conn, client, _ENTITY, upto_vol=1, settings=settings,
        stage="prose", events_conn=events_conn,
    )
    assert result["chronology"] is None
    client.complete_json.assert_not_called()
    events_conn.close()
    graph_conn.close()