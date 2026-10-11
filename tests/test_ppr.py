"""Tests for graph/ppr.py — Phase 5."""

from __future__ import annotations

import sqlite3

from narrativewiki.graph import ppr as PPR
from narrativewiki.graph import store as ST


def _conn(edges):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    ST.write_edges(conn, edges)
    return conn


def _edge(subject, predicate, object, vol_start=1, vol_end=None):
    return {"subject": subject, "predicate": predicate, "object": object, "vol_start": vol_start, "vol_end": vol_end}


def test_build_subgraph_filters_by_cutoff():
    conn = _conn(
        [
            _edge("shin", "FRIEND_OF", "raiden", vol_start=1),
            _edge("shin", "FRIEND_OF", "frederica", vol_start=3),
        ]
    )
    early = PPR.build_subgraph(conn, 2)
    assert set(early.nodes) == {"shin", "raiden"}

    later = PPR.build_subgraph(conn, 3)
    assert set(later.nodes) == {"shin", "raiden", "frederica"}


def test_build_subgraph_collapses_parallel_edges_into_weight():
    conn = _conn(
        [
            _edge("shin", "FRIEND_OF", "raiden"),
            _edge("shin", "COMRADE_OF", "raiden"),
        ]
    )
    graph = PPR.build_subgraph(conn, 1)
    assert graph.number_of_edges() == 1
    assert graph["shin"]["raiden"]["weight"] == 2


def test_personalized_pagerank_excludes_self_and_ranks_neighbours_first():
    # shin -- raiden -- frederica (a chain): raiden is one hop from shin, frederica is two.
    conn = _conn(
        [
            _edge("shin", "FRIEND_OF", "raiden"),
            _edge("raiden", "FRIEND_OF", "frederica"),
        ]
    )
    ranked = PPR.personalized_pagerank(conn, "shin", 1)
    ids = [r["entity_id"] for r in ranked]
    assert "shin" not in ids
    assert ids[0] == "raiden"  # closer to the seed than frederica
    assert set(ids) == {"raiden", "frederica"}
    assert ranked[0]["score"] > ranked[1]["score"]


def test_personalized_pagerank_respects_top_k():
    conn = _conn([_edge("shin", "FRIEND_OF", f"char{i}") for i in range(20)])
    ranked = PPR.personalized_pagerank(conn, "shin", 1, top_k=3)
    assert len(ranked) == 3


def test_personalized_pagerank_empty_for_missing_or_isolated_entity():
    conn = _conn([_edge("raiden", "FRIEND_OF", "frederica")])
    assert PPR.personalized_pagerank(conn, "shin", 1) == []  # not a node at all

    empty_conn = _conn([])
    assert PPR.personalized_pagerank(empty_conn, "shin", 1) == []


def test_personalized_pagerank_deterministic_across_calls():
    conn = _conn(
        [
            _edge("shin", "FRIEND_OF", "raiden"),
            _edge("shin", "FRIEND_OF", "frederica"),
            _edge("raiden", "FRIEND_OF", "frederica"),
        ]
    )
    first = PPR.personalized_pagerank(conn, "shin", 1)
    second = PPR.personalized_pagerank(conn, "shin", 1)
    assert first == second
