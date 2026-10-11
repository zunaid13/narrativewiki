"""Tests for graph/{store,temporal,contradictions}.py — Phase 4.

Follows the pattern in test_extract.py: a scripted fake LLM client (never touches a real
provider) and a hand-built FakeSettings exposing just the extraction.yaml sub-blocks these
modules read.
"""

from __future__ import annotations

import sqlite3

from narrativewiki.graph import canonicalize as CA
from narrativewiki.graph import contradictions as CO
from narrativewiki.graph import store as ST
from narrativewiki.graph import temporal as TE

ATTRIBUTES = {
    "AGE": {"single": True, "format": "number_or_range"},
    "STATUS": {"single": True},
    "RANK": {"single": True},
    "TITLE": {"single": False},
    "APPEARANCE": {"single": False, "subsume": True},
}
RELATIONS = {
    "FRIEND_OF": {"symmetric": True},
    "PARENT_OF": {"inverse": "CHILD_OF"},
    "CHILD_OF": {"inverse": "PARENT_OF"},
    "AFFILIATED_WITH": {},
}
# Phase 17: no conflicts_with here on purpose -- this is the fixture every pre-Phase-17 test in
# this file already uses, and FRIEND_OF must stay ungrouped for those (see
# test_build_graph_dedupes_symmetric_relation_observed_from_both_sides). The relation-conflict
# tests below use RELATIONS_WITH_CONFLICT instead.
RELATIONS_WITH_CONFLICT = {
    **RELATIONS,
    "FRIEND_OF": {"symmetric": True, "conflicts_with": ["ENEMY_OF"]},
    "ENEMY_OF": {"symmetric": True, "conflicts_with": ["FRIEND_OF"]},
}


class FakeSettings:
    attributes = ATTRIBUTES
    relations = RELATIONS
    conflicts_config = {"escalate_when_confidence_within": 0.10}
    # Phase 17: build_graph always reads this for every non-single attribute/trait group. Real
    # `client=None` in every test below means embed_fn is None regardless, so canonicalization
    # degrades to exact-normalize_value bucketing only -- existing tests' expected outputs are
    # unaffected (see graph/canonicalize.py's own no-embed-model fallback contract).
    canonicalize_config = {"enabled": True, "similarity_threshold": 0.86, "min_group_size": 2}


class ConflictFakeSettings(FakeSettings):
    relations = RELATIONS_WITH_CONFLICT


def _claim(claim_id, subject, predicate, kind, first_vol, confidence, *, object=None, value=None, quote="evidence text"):
    return {
        "claim_id": claim_id,
        "subject": subject,
        "predicate": predicate,
        "kind": kind,
        "object": object,
        "value": value,
        "qualifier": None,
        "first_vol": first_vol,
        "confidence": confidence,
        "evidence": [{"para_id": f"v{first_vol:02d}:c00:p0001", "quote": quote}],
        "polarity": "asserted",
        "source": "test",
    }


# ---------------------------------------------------------------------------
# temporal.py
# ---------------------------------------------------------------------------


def test_assign_single_valued_supersedes_sequentially():
    entries = [
        {"value": "Second Lieutenant", "qualifier": None, "first_vol": 2, "claim_ids": ["c_a"]},
        {"value": "Captain", "qualifier": None, "first_vol": 6, "claim_ids": ["c_b"]},
    ]
    intervals = TE.assign_single_valued("shin", "RANK", entries)
    assert len(intervals) == 2
    first, second = intervals
    assert first["value"] == "Second Lieutenant"
    assert first["vol_start"] == 2
    assert first["vol_end"] == 5  # closes the volume before the next value starts
    assert first["superseded_by"] == second["interval_id"]
    assert second["value"] == "Captain"
    assert second["vol_start"] == 6
    assert second["vol_end"] is None  # still true at the last ingested volume
    assert second["superseded_by"] is None


def test_assign_single_valued_merges_repeated_identical_value():
    entries = [
        {"value": "alive", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]},
        {"value": "alive", "qualifier": None, "first_vol": 3, "claim_ids": ["c_b"]},
    ]
    intervals = TE.assign_single_valued("lena", "STATUS", entries)
    assert len(intervals) == 1
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]
    assert intervals[0]["vol_start"] == 1  # earliest evidence wins, not the repeat


def test_assign_single_valued_merges_value_repeated_with_different_casing():
    """Real-data regression (Spice and Wolf, Kraft Lawrence OCCUPATION): the extractor is not
    guaranteed to reproduce identical casing for the same fact across volumes -- "Traveling
    merchant" in v1, "traveling merchant" in v2 -- and that must not render as a supersession
    with a spurious one-volume "previously" entry when nothing actually changed."""
    entries = [
        {"value": "Traveling merchant", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]},
        {"value": "traveling merchant", "qualifier": None, "first_vol": 2, "claim_ids": ["c_b"]},
    ]
    intervals = TE.assign_single_valued("lawrence", "OCCUPATION", entries)
    assert len(intervals) == 1
    assert intervals[0]["value"] == "Traveling merchant"  # first-seen casing wins
    assert intervals[0]["vol_start"] == 1
    assert intervals[0]["vol_end"] is None
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]


def test_assign_multi_valued_keeps_every_distinct_value_open():
    observations = [
        {"value_or_object": "Undertaker", "qualifier": None, "first_vol": 1, "claim_id": "c_a"},
        {"value_or_object": "the Reaper", "qualifier": None, "first_vol": 4, "claim_id": "c_b"},
    ]
    intervals = TE.assign_multi_valued("shin", "NICKNAME", observations, is_relation=False)
    assert len(intervals) == 2
    assert all(iv["vol_end"] is None for iv in intervals)
    assert {iv["value"] for iv in intervals} == {"Undertaker", "the Reaper"}


def test_assign_multi_valued_collapses_duplicate_value_to_earliest_first_vol():
    observations = [
        {"value_or_object": "spearhead-squadron", "qualifier": None, "first_vol": 3, "claim_id": "c_b"},
        {"value_or_object": "spearhead-squadron", "qualifier": None, "first_vol": 1, "claim_id": "c_a"},
    ]
    intervals = TE.assign_multi_valued("shin", "AFFILIATED_WITH", observations, is_relation=True)
    assert len(intervals) == 1
    assert intervals[0]["vol_start"] == 1
    assert intervals[0]["object"] == "spearhead-squadron"
    assert intervals[0]["value"] is None
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]


# ---------------------------------------------------------------------------
# temporal.py — Phase 22 A2: format-aware normalize_value, subsumption
# ---------------------------------------------------------------------------


def test_normalize_value_number_or_range_folds_spelled_out_ages_to_digits():
    """Real-data regression: Lawrence's four AGE phrasings (docs/vision/PHASE_22.md U2)."""
    phrasings = ["25", "twenty-five", "twenty-five years old", "twenty-five years"]
    normalized = {TE.normalize_value(p, "number_or_range") for p in phrasings}
    assert normalized == {"25"}


def test_normalize_value_number_or_range_folds_a_spelled_out_range():
    assert TE.normalize_value("twenty-five to thirty", "number_or_range") == "25-30"
    assert TE.normalize_value("17-19", "number_or_range") == "17-19"


def test_normalize_value_number_or_range_falls_back_when_no_number_present():
    assert TE.normalize_value("Unknown", "number_or_range") == "unknown"


def test_normalize_value_ignores_fmt_it_does_not_recognize():
    assert TE.normalize_value("Traveling merchant", "short_text") == "traveling merchant"


def test_assign_single_valued_merges_across_volumes_using_fmt():
    """The AGE case one layer up from _resolve_single_valued: even after that function's own
    same-volume collapse, the cross-volume defensive merge here needs fmt too, or v1's
    'twenty-five years old' and v2's 'twenty-five years' render as two intervals joined by a
    spurious superseded_by link."""
    entries = [
        {"value": "twenty-five years old", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]},
        {"value": "twenty-five years", "qualifier": None, "first_vol": 2, "claim_ids": ["c_b"]},
    ]
    intervals = TE.assign_single_valued("lawrence", "AGE", entries, fmt="number_or_range")
    assert len(intervals) == 1
    assert intervals[0]["value"] == "twenty-five years old"  # first-seen phrasing wins
    assert intervals[0]["vol_start"] == 1
    assert intervals[0]["vol_end"] is None
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]


def test_assign_multi_valued_non_relation_bucket_is_case_and_whitespace_insensitive():
    observations = [
        {"value_or_object": "Traveling merchant", "qualifier": None, "first_vol": 1, "claim_id": "c_a"},
        {"value_or_object": "traveling merchant", "qualifier": None, "first_vol": 2, "claim_id": "c_b"},
    ]
    intervals = TE.assign_multi_valued("lawrence", "TITLE", observations, is_relation=False)
    assert len(intervals) == 1
    assert intervals[0]["value"] == "Traveling merchant"  # earliest first_vol's casing wins
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]


def test_assign_multi_valued_relation_bucket_stays_exact_never_normalized():
    """Relation `value_or_object` is already an entity_id -- normalizing it would be a bug (it
    could collide two differently-cased entity_ids that are not actually the same entity)."""
    observations = [
        {"value_or_object": "Spearhead-Squadron", "qualifier": None, "first_vol": 1, "claim_id": "c_a"},
        {"value_or_object": "spearhead-squadron", "qualifier": None, "first_vol": 2, "claim_id": "c_b"},
    ]
    intervals = TE.assign_multi_valued("shin", "AFFILIATED_WITH", observations, is_relation=True)
    assert len(intervals) == 2  # NOT merged -- exact entity_id match only


def test_assign_relation_supersession_closes_the_old_predicate():
    """Phase 17: mirrors test_assign_single_valued_supersedes_sequentially, but the thing that
    changes across volumes is WHICH predicate holds (FRIEND_OF -> ENEMY_OF), not a value."""
    ordered = [
        {"predicate": "FRIEND_OF", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]},
        {"predicate": "ENEMY_OF", "qualifier": None, "first_vol": 5, "claim_ids": ["c_b"]},
    ]
    intervals = TE.assign_relation_supersession("shin", "raiden", ordered)
    assert len(intervals) == 2
    first, second = intervals
    assert first["predicate"] == "FRIEND_OF"
    assert first["object"] == "raiden"
    assert first["value"] is None
    assert first["vol_start"] == 1
    assert first["vol_end"] == 4
    assert first["superseded_by"] == second["interval_id"]
    assert second["predicate"] == "ENEMY_OF"
    assert second["vol_start"] == 5
    assert second["vol_end"] is None
    assert second["superseded_by"] is None


def test_state_at_and_history_at_filter_by_cutoff():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    entries = [
        {"value": "Second Lieutenant", "qualifier": None, "first_vol": 2, "claim_ids": ["c_a"]},
        {"value": "Captain", "qualifier": None, "first_vol": 6, "claim_ids": ["c_b"]},
    ]
    ST.write_intervals(conn, TE.assign_single_valued("shin", "RANK", entries))

    at_1 = TE.state_at(conn, "shin", 1)
    assert at_1 == []  # before first_vol=2, nothing is known yet

    at_3 = TE.state_at(conn, "shin", 3)
    assert len(at_3) == 1
    assert at_3[0]["value"] == "Second Lieutenant"
    assert TE.history_at(conn, "shin", 3) == []  # not superseded yet at this cutoff

    at_8 = TE.state_at(conn, "shin", 8)
    assert len(at_8) == 1
    assert at_8[0]["value"] == "Captain"
    hist_8 = TE.history_at(conn, "shin", 8)
    assert len(hist_8) == 1
    assert hist_8[0]["value"] == "Second Lieutenant"


def test_relations_at_finds_entity_on_either_side():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    # Canonicalised storage: (raiden, FRIEND_OF, shin) -- shin is the OBJECT here, not the subject.
    observations = [{"value_or_object": "shin", "qualifier": None, "first_vol": 2, "claim_id": "c_a"}]
    ST.write_intervals(conn, TE.assign_multi_valued("raiden", "FRIEND_OF", observations, is_relation=True))

    assert TE.relations_at(conn, "shin", 1) == []  # before first_vol=2, not visible yet
    found = TE.relations_at(conn, "shin", 2)
    assert len(found) == 1
    assert found[0]["subject"] == "raiden"
    assert found[0]["object"] == "shin"
    # Symmetric lookup from the other side too.
    assert len(TE.relations_at(conn, "raiden", 2)) == 1


def test_relations_at_excludes_attribute_intervals():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    ST.write_intervals(conn, TE.assign_single_valued("shin", "AGE", [{"value": "16", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]}]))
    assert TE.relations_at(conn, "shin", 5) == []


def test_relations_at_excludes_closed_relation_and_history_returns_it():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    intervals = TE.assign_relation_supersession(
        "shin",
        "raiden",
        [
            {"predicate": "FRIEND_OF", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]},
            {"predicate": "ENEMY_OF", "qualifier": None, "first_vol": 2, "claim_ids": ["c_b"]},
        ],
    )
    ST.write_intervals(conn, intervals)

    assert [row["predicate"] for row in TE.relations_at(conn, "raiden", 2)] == ["ENEMY_OF"]
    history = TE.relation_history_at(conn, "raiden", 2)
    assert [row["predicate"] for row in history] == ["FRIEND_OF"]
    assert history[0]["vol_end"] == 1


def test_relations_between_finds_pair_either_storage_direction():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    observations = [{"value_or_object": "shin", "qualifier": None, "first_vol": 2, "claim_id": "c_a"}]
    ST.write_intervals(conn, TE.assign_multi_valued("raiden", "FRIEND_OF", observations, is_relation=True))

    assert TE.relations_between(conn, "shin", "raiden", 1) == []  # before first_vol=2
    found = TE.relations_between(conn, "shin", "raiden", 2)
    assert len(found) == 1
    assert found[0]["subject"] == "raiden"
    assert found[0]["object"] == "shin"
    # Same result regardless of argument order.
    assert len(TE.relations_between(conn, "raiden", "shin", 2)) == 1


def test_relations_between_excludes_unrelated_third_party():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    observations = [{"value_or_object": "kurena", "qualifier": None, "first_vol": 1, "claim_id": "c_a"}]
    ST.write_intervals(conn, TE.assign_multi_valued("shin", "COMRADE_OF", observations, is_relation=True))
    # shin-kurena exists, but shin-raiden does not.
    assert TE.relations_between(conn, "shin", "raiden", 5) == []


def test_relation_history_between_closed_conflict_group_only():
    """Phase 17: relations_between still shows a not-yet-closed pair as current; only a
    conflicts_with supersession (FRIEND_OF -> ENEMY_OF) ever populates history_between."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    ordered = [
        {"predicate": "FRIEND_OF", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]},
        {"predicate": "ENEMY_OF", "qualifier": None, "first_vol": 5, "claim_ids": ["c_b"]},
    ]
    ST.write_intervals(conn, TE.assign_relation_supersession("shin", "raiden", ordered))

    # At cutoff 3, the reader knows only FRIEND_OF -- it has not closed yet as far as they know.
    current_at_3 = TE.relations_between(conn, "shin", "raiden", 3)
    assert len(current_at_3) == 1
    assert current_at_3[0]["predicate"] == "FRIEND_OF"
    assert TE.relation_history_between(conn, "shin", "raiden", 3) == []

    # At cutoff 6, FRIEND_OF has closed (revealed) and ENEMY_OF is current.
    current_at_6 = TE.relations_between(conn, "shin", "raiden", 6)
    assert len(current_at_6) == 1
    assert current_at_6[0]["predicate"] == "ENEMY_OF"
    history_at_6 = TE.relation_history_between(conn, "shin", "raiden", 6)
    assert len(history_at_6) == 1
    assert history_at_6[0]["predicate"] == "FRIEND_OF"
    assert history_at_6[0]["vol_end"] == 4


def test_all_edges_at_filters_cutoff():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    ST.write_edges(
        conn,
        [
            {"subject": "shin", "predicate": "FRIEND_OF", "object": "raiden", "vol_start": 1, "vol_end": None},
            {"subject": "shin", "predicate": "FRIEND_OF", "object": "frederica", "vol_start": 3, "vol_end": None},
            {"subject": "shin", "predicate": "FRIEND_OF", "object": "kurena", "vol_start": 1, "vol_end": 1},
        ],
    )
    assert len(TE.all_edges_at(conn, 1)) == 2
    assert len(TE.all_edges_at(conn, 2)) == 1
    assert len(TE.all_edges_at(conn, 3)) == 2


def test_evidence_at_filters_quotes_by_their_own_volume_not_claim_first_vol():
    """Regression: a claim merged across volumes (extract/claims.py collapses repeated
    observations of the same fact into one claim_id) must not leak a later-volume quote just
    because the claim's own first_vol already cleared the cutoff. This is the exact bug found
    real-data-testing `wiki explain` in Phase 5 — evidence_at is the fix."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    claim = _claim("c_a", "shin", "COMRADE_OF", "relation", 1, 0.95, object="raiden", quote="v01 quote")
    claim["evidence"] = [
        {"para_id": "v01:c03:p0001", "quote": "v01 quote"},
        {"para_id": "v02:c05:p0042", "quote": "v02 quote -- must not leak at cutoff 1"},
    ]
    ST.write_claims(conn, [claim])

    at_1 = TE.evidence_at(conn, ["c_a"], 1)
    assert len(at_1) == 1
    assert at_1[0]["para_id"] == "v01:c03:p0001"

    at_2 = TE.evidence_at(conn, ["c_a"], 2)
    assert len(at_2) == 2
    assert {e["para_id"] for e in at_2} == {"v01:c03:p0001", "v02:c05:p0042"}


def test_evidence_at_skips_unknown_claim_id():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    assert TE.evidence_at(conn, ["c_missing"], 5) == []


# ---------------------------------------------------------------------------
# store.py
# ---------------------------------------------------------------------------


def test_store_round_trip_and_reset(tmp_path):
    conn = ST.connect(tmp_path / "graph.db")
    ST.write_entities(conn, [{"entity_id": "shin", "canonical": "Shin", "type": "CHARACTER", "first_vol": 1, "importance": 0.9, "aliases": ["Undertaker"]}])
    ST.write_claims(conn, [_claim("c_a", "shin", "AGE", "attribute", 1, 0.9, value="16")])
    ST.write_intervals(conn, TE.assign_single_valued("shin", "AGE", [{"value": "16", "qualifier": None, "first_vol": 1, "claim_ids": ["c_a"]}]))
    ST.write_edges(conn, [{"subject": "shin", "predicate": "FRIEND_OF", "object": "raiden", "vol_start": 1, "vol_end": None}])
    ST.write_mention_counts(conn, {("shin", 1): 42})

    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM intervals").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 1
    assert conn.execute("SELECT count FROM mention_counts WHERE entity_id='shin'").fetchone()[0] == 42

    ST.reset(conn)
    for table in ("entities", "claims", "intervals", "edges", "mention_counts", "verdicts"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_store_intervals_persist_confidence_and_evidence_count(tmp_path):
    """Phase 23 B1: intervals carry their own confidence/evidence_count now, so a downstream
    renderer can gate on them without re-joining claims."""
    conn = ST.connect(tmp_path / "graph.db")
    interval = TE.assign_multi_valued(
        "holo", "AFFILIATED_WITH",
        [
            {"value_or_object": "medio-company", "qualifier": None, "first_vol": 1, "claim_id": "c_a", "confidence": 0.4},
            {"value_or_object": "medio-company", "qualifier": None, "first_vol": 1, "claim_id": "c_b", "confidence": 0.7},
        ],
        is_relation=True,
    )
    ST.write_intervals(conn, interval)
    row = conn.execute("SELECT confidence, evidence_count FROM intervals").fetchone()
    assert row["confidence"] == 0.7  # max across corroborating observations
    assert row["evidence_count"] == 2


def test_store_migrates_a_pre_phase_23_intervals_table(tmp_path):
    """A graph.db written before Phase 23 has no confidence/evidence_count columns at all --
    connect() must add them rather than erroring on the next write_intervals call."""
    db_path = tmp_path / "old.db"
    old_conn = sqlite3.connect(db_path)
    old_conn.executescript(
        "CREATE TABLE intervals (interval_id TEXT PRIMARY KEY, subject TEXT NOT NULL, "
        "predicate TEXT NOT NULL, object TEXT, value TEXT, qualifier TEXT, vol_start INTEGER "
        "NOT NULL, vol_end INTEGER, claim_ids_json TEXT NOT NULL, superseded_by TEXT);"
    )
    old_conn.commit()
    old_conn.close()

    conn = ST.connect(db_path)  # must migrate, not raise
    ST.write_intervals(conn, [{
        "interval_id": "i_x", "subject": "holo", "predicate": "AGE", "object": None,
        "value": "100", "qualifier": None, "vol_start": 1, "vol_end": None,
        "claim_ids": ["c_a"], "superseded_by": None, "confidence": 0.9, "evidence_count": 1,
    }])
    row = conn.execute("SELECT confidence, evidence_count FROM intervals").fetchone()
    assert row["confidence"] == 0.9
    assert row["evidence_count"] == 1


def test_store_write_and_read_verdicts(tmp_path):
    conn = ST.connect(tmp_path / "graph.db")
    ST.write_verdicts(conn, [
        {"target_id": "i_a", "verdict": "unsupported", "rationale": "no marriage stated",
         "model": "google_fast", "run_id": "run_1"},
        {"target_id": "i_b", "verdict": "supported", "rationale": None, "model": "google_fast", "run_id": "run_1"},
    ])
    verdicts = ST.read_verdicts(conn)
    assert verdicts["i_a"]["verdict"] == "unsupported"
    assert verdicts["i_a"]["rationale"] == "no marriage stated"
    assert verdicts["i_b"]["verdict"] == "supported"

    # [30] `reset()` deliberately spares `verdicts` now: wiping them meant every `graph build`
    # re-verified everything and re-rolled judgements on facts that had not moved (MEASUREMENTS
    # §28). `prune_orphan_verdicts` is what now enforces "no verdict outlives its interval".
    ST.reset(conn)
    assert set(ST.read_verdicts(conn)) == {"i_a", "i_b"}

    ST.write_intervals(conn, [{
        "interval_id": "i_a", "subject": "holo", "predicate": "STATUS", "object": None,
        "value": "alive", "qualifier": None, "vol_start": 1, "vol_end": None,
        "claim_ids": ["c_x"], "superseded_by": None, "confidence": 1.0, "evidence_count": 1,
    }])
    assert ST.prune_orphan_verdicts(conn) == 1          # i_b has no interval any more
    assert set(ST.read_verdicts(conn)) == {"i_a"}       # i_a's fact is still there, so is its verdict
    assert ST.prune_orphan_verdicts(conn) == 0          # idempotent


def test_verdict_context_hash_tracks_the_evidence_a_verdict_was_judged_on():
    """[30] A verdict is only reusable across a rebuild if what it judged has not moved, and
    `interval_id` does not establish that -- it stays stable while a fact's evidence set changes
    underneath it. Without this hash, `graph build` re-rolled 12 reader-visible gates after a
    rebuild that altered one relation (MEASUREMENTS §28)."""
    from narrativewiki.graph import verify as VF

    fact = {
        "kind": "relation", "predicate": "SAVED", "value": "Holo -> Kraft Lawrence",
        "qualifier": "rescued him", "interval_id": "i_a",
        "evidence": [{"para_id": "v01:c07:p0038", "quote": "Holo returned to him."}],
    }
    base = VF.fact_context_sha256(fact)
    assert base == VF.fact_context_sha256(dict(fact))            # stable
    assert base == VF.fact_context_sha256({**fact, "interval_id": "i_zzz"})  # not keyed on identity

    reordered = {**fact, "evidence": [
        {"para_id": "v02:c05:p0037", "quote": "thanks to Holo for saving them"},
        {"para_id": "v01:c07:p0038", "quote": "Holo returned to him."},
    ]}
    grown = {**fact, "evidence": list(reversed(reordered["evidence"]))}
    assert VF.fact_context_sha256(reordered) == VF.fact_context_sha256(grown)  # order-independent
    assert VF.fact_context_sha256(reordered) != base             # a new quote IS a change
    assert VF.fact_context_sha256({**fact, "qualifier": "let him drown"}) != base
    assert VF.fact_context_sha256({**fact, "value": "Kraft Lawrence -> Holo"}) != base
    assert VF.fact_context_sha256({**fact, "evidence": []}) != base


def test_mention_counts_from_records():
    records = [{"entity_id": "shin", "vol": 1}, {"entity_id": "shin", "vol": 1}, {"entity_id": "raiden", "vol": 1}]
    counts = ST.mention_counts_from_records(records)
    assert counts == {("shin", 1): 2, ("raiden", 1): 1}


# ---------------------------------------------------------------------------
# contradictions.py — pairwise resolution
# ---------------------------------------------------------------------------


class _FakeArbitrationClient:
    def __init__(self, decision):
        self.decision = decision
        self.calls = 0

    def complete_json(self, stage, prompt, schema, system=None):
        self.calls += 1
        return schema.model_validate(self.decision)


def test_resolve_pair_rule_based_when_confidence_gap_is_wide():
    a = _claim("c_a", "shin", "RANK", "attribute", 2, 0.95, value="Second Lieutenant")
    b = _claim("c_b", "shin", "RANK", "attribute", 2, 0.5, value="Captain")
    winner, loser, resolution, arbiter, rationale = CO._resolve_pair("shin", "RANK", 2, a, b, 0.10, client=None)
    assert winner is a
    assert loser is b
    assert resolution == "keep_a"
    assert arbiter == "rule:higher_confidence"


def test_resolve_pair_escalates_to_llm_when_confidence_is_close():
    a = _claim("c_a", "shin", "RANK", "attribute", 2, 0.9, value="Second Lieutenant")
    b = _claim("c_b", "shin", "RANK", "attribute", 2, 0.88, value="Captain")
    client = _FakeArbitrationClient({"resolution": "keep_b", "rationale": "Text supports Captain."})
    winner, loser, resolution, arbiter, rationale = CO._resolve_pair("shin", "RANK", 2, a, b, 0.10, client)
    assert client.calls == 1
    assert winner is b
    assert loser is a
    assert resolution == "keep_b"
    assert arbiter == "model:arbitrate"
    assert rationale == "Text supports Captain."


def test_resolve_pair_falls_back_to_rule_when_no_client_and_gap_is_narrow():
    a = _claim("c_a", "shin", "RANK", "attribute", 2, 0.9, value="Second Lieutenant")
    b = _claim("c_b", "shin", "RANK", "attribute", 2, 0.88, value="Captain")
    winner, loser, resolution, arbiter, rationale = CO._resolve_pair("shin", "RANK", 2, a, b, 0.10, client=None)
    assert winner is a  # higher confidence still wins the degrade path
    assert arbiter == "rule:higher_confidence_fallback"


def test_resolve_pair_flag_returns_no_winner():
    a = _claim("c_a", "shin", "RANK", "attribute", 2, 0.9, value="Second Lieutenant")
    b = _claim("c_b", "shin", "RANK", "attribute", 2, 0.88, value="Captain")
    client = _FakeArbitrationClient({"resolution": "flag", "rationale": "Neither passage is conclusive."})
    winner, loser, resolution, arbiter, rationale = CO._resolve_pair("shin", "RANK", 2, a, b, 0.10, client)
    assert winner is None
    assert loser is None
    assert resolution == "flag"


# ---------------------------------------------------------------------------
# contradictions.py — build_graph end to end
# ---------------------------------------------------------------------------


def test_build_graph_same_volume_conflict_is_extraction_error():
    claims = [
        _claim("c_a", "shin", "STATUS", "attribute", 3, 0.95, value="alive"),
        _claim("c_b", "shin", "STATUS", "attribute", 3, 0.4, value="deceased"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert doc["summary"]["extraction_error"] == 1
    assert doc["summary"]["narrative_change"] == 0
    assert doc["conflicts"][0]["resolution"] == "keep_a"
    assert len(intervals) == 1
    assert intervals[0]["value"] == "alive"


def test_build_graph_cross_volume_change_is_narrative_change_and_supersedes():
    claims = [
        _claim("c_a", "shin", "RANK", "attribute", 2, 0.9, value="Second Lieutenant"),
        _claim("c_b", "shin", "RANK", "attribute", 6, 0.9, value="Captain"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert doc["summary"]["narrative_change"] == 1
    assert doc["summary"]["extraction_error"] == 0
    conflict = doc["conflicts"][0]
    assert conflict["kind"] == "narrative_change"
    assert conflict["resolution"] == "supersede"


def test_build_graph_cross_volume_repeat_with_different_casing_is_not_a_conflict():
    """Real-data regression (Spice and Wolf, Kraft Lawrence OCCUPATION -- a single: true
    attribute, like RANK here): the same fact restated with different casing across volumes
    ("Traveling merchant" v1, "traveling merchant" v2) must not be logged as a narrative_change
    and must not split into two intervals."""
    claims = [
        _claim("c_a", "lawrence", "RANK", "attribute", 1, 0.9, value="Traveling merchant"),
        _claim("c_b", "lawrence", "RANK", "attribute", 2, 0.9, value="traveling merchant"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert doc["summary"]["narrative_change"] == 0
    assert len(intervals) == 1
    assert intervals[0]["value"] == "Traveling merchant"
    assert intervals[0]["vol_end"] is None


def test_build_graph_same_volume_spelled_out_age_is_not_a_false_conflict():
    """Phase 22 A2 seam 2: before the same-volume collapse, two same-volume AGE phrasings of the
    identical value would have been ranked as the top two and sent to arbitration -- a genuine
    extraction_error record for a fact that isn't actually in dispute. AGE's format:
    number_or_range (added to the ATTRIBUTES fixture above) must suppress that."""
    claims = [
        _claim("c_a", "lawrence", "AGE", "attribute", 1, 0.9, value="25"),
        _claim("c_b", "lawrence", "AGE", "attribute", 1, 0.6, value="twenty-five"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert doc["summary"]["total"] == 0  # no conflict at all -- same value, not a tie
    assert len(intervals) == 1
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]


def test_build_graph_cross_volume_all_four_age_phrasings_collapse_to_one_interval():
    """The exact real-data bug from docs/vision/PHASE_22.md's audit (U2): Lawrence had four
    distinct AGE values (`'25'`, `'twenty-five'`, `'twenty-five years old'` in v1,
    `'twenty-five years'` in v2) before A2, rendering as the graph's one `narrative_change`
    conflict despite the text never actually stating a different age."""
    claims = [
        _claim("c_a", "lawrence", "AGE", "attribute", 1, 0.9, value="25"),
        _claim("c_b", "lawrence", "AGE", "attribute", 1, 0.6, value="twenty-five"),
        _claim("c_c", "lawrence", "AGE", "attribute", 1, 0.5, value="twenty-five years old"),
        _claim("c_d", "lawrence", "AGE", "attribute", 2, 0.9, value="twenty-five years"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert doc["summary"]["total"] == 0
    assert len(intervals) == 1
    assert intervals[0]["vol_start"] == 1
    assert intervals[0]["vol_end"] is None
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b", "c_c", "c_d"]


def test_build_graph_same_volume_genuinely_different_age_still_arbitrates():
    """format-aware collapse must not swallow a real conflict -- '25' and '30' are actually
    distinct values and still need to go through arbitration like before."""
    claims = [
        _claim("c_a", "lawrence", "AGE", "attribute", 1, 0.9, value="25"),
        _claim("c_b", "lawrence", "AGE", "attribute", 1, 0.5, value="30"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert doc["summary"]["extraction_error"] == 1
    assert doc["conflicts"][0]["resolution"] == "keep_a"
    assert intervals[0]["value"] == "25"


def test_arbitration_decision_accepts_decision_key_as_resolution_alias():
    """openrouter/free's nex-n2.5-pro repeatedly returns {"decision": ...} instead of the
    requested {"resolution": ...} key (observed live on 20260919T190103-graph_build-v1-2,
    jakob/RANK, surviving all 3 repair-retry attempts) -- accept it rather than exhausting
    retries and failing the whole graph build."""
    decision = CO.ArbitrationDecision.model_validate(
        {"decision": "keep_a", "rationale": "Fact A is directly supported by the quoted evidence."}
    )
    assert decision.resolution == "keep_a"


def test_build_graph_non_single_attribute_produces_no_conflict():
    claims = [
        _claim("c_a", "shin", "TITLE", "attribute", 1, 0.9, value="Undertaker"),
        _claim("c_b", "shin", "TITLE", "attribute", 5, 0.9, value="the Reaper"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert doc["summary"]["total"] == 0
    assert len(intervals) == 2
    assert all(iv["vol_end"] is None for iv in intervals)


def test_build_graph_subsumes_redundant_appearance_values():
    """Phase 22 A2 seam 3 end to end: APPEARANCE is marked subsume: true in the ATTRIBUTES
    fixture above. No embed client needed -- subsumption is deterministic, unlike canonicalize's
    clustering, so this runs with client=None exactly like a real build with Ollama down."""
    claims = [
        _claim("c_a", "holo", "APPEARANCE", "attribute", 1, 0.9, value="hair"),
        _claim("c_b", "holo", "APPEARANCE", "attribute", 1, 0.9, value="long brown hair"),
        _claim("c_c", "holo", "APPEARANCE", "attribute", 2, 0.9, value="amber eyes"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert {iv["value"] for iv in intervals} == {"long brown hair", "amber eyes"}


def test_build_graph_dedupes_symmetric_relation_observed_from_both_sides():
    claims = [
        _claim("c_a", "shin", "FRIEND_OF", "relation", 1, 0.9, object="raiden"),
        _claim("c_b", "raiden", "FRIEND_OF", "relation", 1, 0.9, object="shin"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert len(intervals) == 1
    assert len(edges) == 1
    assert {edges[0]["subject"], edges[0]["object"]} == {"shin", "raiden"}


def test_build_graph_dedupes_inverse_relation_pair():
    claims = [
        _claim("c_a", "kiriya", "PARENT_OF", "relation", 1, 0.9, object="shin"),
        _claim("c_b", "shin", "CHILD_OF", "relation", 1, 0.9, object="kiriya"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert len(edges) == 1
    # CHILD_OF < PARENT_OF alphabetically, so the canonical direction is (shin, CHILD_OF, kiriya)
    assert edges[0] == {"subject": "shin", "predicate": "CHILD_OF", "object": "kiriya", "vol_start": 1, "vol_end": None}


def test_build_graph_resolves_same_predicate_asserted_in_both_directions():
    """Phase 23 A4 -- replays the real bug: one sarcastic line ("I'm Kraft Lawrence, then, son of
    the great Jakob Tarantino") produced CHILD_OF in BOTH directions, since both sides used the
    identical predicate name (not PARENT_OF's declared inverse), which _canonicalize_relation's
    symmetric/inverse merge never touches. Only the higher-confidence direction should survive,
    logged as an extraction_error, not both rendered simultaneously."""
    claims = [
        _claim("c_a", "jakob", "CHILD_OF", "relation", 2, 0.6, object="kraft-lawrence"),
        _claim("c_b", "kraft-lawrence", "CHILD_OF", "relation", 2, 0.9, object="jakob"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert len(edges) == 1
    assert edges[0] == {
        "subject": "kraft-lawrence", "predicate": "CHILD_OF", "object": "jakob",
        "vol_start": 2, "vol_end": None,
    }
    mutual = [c for c in doc["conflicts"] if c["arbiter"] == "rule:mutual_direction_collision"]
    assert len(mutual) == 1
    assert mutual[0]["kind"] == "extraction_error"


def test_build_graph_catches_a_reversal_of_a_directional_predicate_that_declares_a_conflict():
    """[30] SAVED and KILLED declare each other in `conflicts_with` AND are both directional --
    the combination `_strip_mutual_direction_collisions` had assumed could not exist, so its
    `pred in conflict_groups` skip exempted them from the only check that catches a same-predicate
    reversal. The live v1-2 graph shipped `holo SAVED kraft-lawrence` and `kraft-lawrence SAVED
    holo` extracted from one sentence, the reversed row reading "Holo stopped the wolves from
    attacking Lawrence" under a heading saying Lawrence saved Holo.

    Both directions came in at confidence 1.0, so this also pins the tiebreak: whichever direction
    the text evidences more often wins, and the outcome does not depend on claim order."""
    class S(FakeSettings):
        relations = {
            **RELATIONS,
            "KILLED": {"conflicts_with": ["SAVED"]},
            "SAVED": {"conflicts_with": ["KILLED"]},
        }

    claims = [
        _claim("c_a", "holo", "SAVED", "relation", 2, 1.0, object="kraft-lawrence",
               quote="Holo, surprised, caught Lawrence as he toppled."),
        _claim("c_b", "holo", "SAVED", "relation", 2, 1.0, object="kraft-lawrence",
               quote="nor give his thanks to Holo for saving them"),
        _claim("c_c", "kraft-lawrence", "SAVED", "relation", 2, 1.0, object="holo",
               quote="nor give his thanks to Holo for saving them"),
    ]
    _, edges, doc = CO.build_graph(claims, S(), client=None)
    saved = [e for e in edges if e["predicate"] == "SAVED"]
    assert len(saved) == 1
    assert (saved[0]["subject"], saved[0]["object"]) == ("holo", "kraft-lawrence")
    mutual = [c for c in doc["conflicts"] if c["arbiter"] == "rule:mutual_direction_collision"]
    assert len(mutual) == 1
    assert mutual[0]["kind"] == "extraction_error"

    _, edges_reversed, _ = CO.build_graph(list(reversed(claims)), S(), client=None)
    assert [(e["subject"], e["object"]) for e in edges_reversed if e["predicate"] == "SAVED"] == [
        ("holo", "kraft-lawrence")
    ]


def test_a_mutual_predicate_keeps_both_directions_when_they_are_separate_incidents():
    """[30] Holo catches Lawrence as he topples; Lawrence pulls Holo back from a window. Both
    rescues are in the text, so `mutual: true` keeps both directions -- and still resolves the one
    sentence read both ways, which is the collision this rule exists for (MEASUREMENTS section 35)."""
    class S(FakeSettings):
        relations = {**RELATIONS, "SAVED": {"mutual": True}}

    def saved(cid, subj, obj, para, conf=1.0):
        c = _claim(cid, subj, "SAVED", "relation", 2, conf, object=obj)
        c["evidence"] = [{"para_id": para, "quote": "q"}]
        return c

    separate = [saved("c_a", "holo", "kraft-lawrence", "v02:c02:p0379"),
                saved("c_b", "kraft-lawrence", "holo", "v02:c03:p0463", conf=1.0)]
    _, edges, doc = CO.build_graph(separate, S(), client=None)
    assert sorted((e["subject"], e["object"]) for e in edges if e["predicate"] == "SAVED") == [
        ("holo", "kraft-lawrence"), ("kraft-lawrence", "holo")]
    assert not [c for c in doc["conflicts"] if c["arbiter"] == "rule:mutual_direction_collision"]

    same_sentence = separate + [saved("c_c", "holo", "kraft-lawrence", "v02:c05:p0037"),
                                saved("c_d", "kraft-lawrence", "holo", "v02:c05:p0037", conf=0.9)]
    _, edges, doc = CO.build_graph(same_sentence, S(), client=None)
    assert len([c for c in doc["conflicts"] if c["arbiter"] == "rule:mutual_direction_collision"]) == 1
    # Only the same-paragraph reading lost; both separate incidents survive.
    assert sorted((e["subject"], e["object"]) for e in edges if e["predicate"] == "SAVED") == [
        ("holo", "kraft-lawrence"), ("kraft-lawrence", "holo")]


def test_build_graph_mutual_direction_collision_is_a_no_op_when_only_one_direction_exists():
    claims = [
        _claim("c_a", "jakob", "CHILD_OF", "relation", 2, 0.9, object="kraft-lawrence"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=None)
    assert len(edges) == 1
    assert edges[0]["subject"] == "jakob"
    assert not [c for c in doc["conflicts"] if c["arbiter"] == "rule:mutual_direction_collision"]


# ---------------------------------------------------------------------------
# canonicalize.py — Phase 17
# ---------------------------------------------------------------------------


def _fake_embed(vectors_by_text):
    """A stand-in `embed_fn`: `cluster_values` calls it with a list of texts and expects vectors
    back in the same order."""
    return lambda texts: [vectors_by_text[t] for t in texts]


def test_cluster_values_merges_near_duplicate_phrasings():
    entries = [
        {"value": "outwardly detached", "confidence": 0.9, "first_vol": 1, "claim_id": "c_a"},
        {"value": "detached on the outside", "confidence": 0.7, "first_vol": 3, "claim_id": "c_b"},
    ]
    embed_fn = _fake_embed(
        {"outwardly detached": [1.0, 0.0], "detached on the outside": [0.95, 0.05]}
    )
    clusters = CA.cluster_values(entries, embed_fn, threshold=0.9, min_group_size=2)
    assert len(clusters) == 1
    assert clusters[0].canonical == "outwardly detached"  # higher confidence wins
    assert {m["claim_id"] for m in clusters[0].members} == {"c_a", "c_b"}


def test_cluster_values_keeps_distinct_phrasings_separate():
    entries = [
        {"value": "fiercely loyal", "confidence": 0.9, "first_vol": 1, "claim_id": "c_a"},
        {"value": "quick to anger", "confidence": 0.9, "first_vol": 2, "claim_id": "c_b"},
    ]
    embed_fn = _fake_embed({"fiercely loyal": [1.0, 0.0], "quick to anger": [0.0, 1.0]})
    clusters = CA.cluster_values(entries, embed_fn, threshold=0.9, min_group_size=2)
    assert len(clusters) == 2
    assert {c.canonical for c in clusters} == {"fiercely loyal", "quick to anger"}


def test_cluster_values_falls_back_to_exact_match_when_embed_unreachable():
    entries = [
        {"value": "Undertaker", "confidence": 0.9, "first_vol": 1, "claim_id": "c_a"},
        {"value": "undertaker", "confidence": 0.8, "first_vol": 2, "claim_id": "c_b"},
        {"value": "the Reaper", "confidence": 0.9, "first_vol": 3, "claim_id": "c_c"},
    ]
    clusters = CA.cluster_values(entries, embed_fn=None, threshold=0.9, min_group_size=2)
    assert len(clusters) == 2  # "Undertaker"/"undertaker" merge by normalize_value alone
    canonicals = {c.canonical for c in clusters}
    assert canonicals == {"Undertaker", "the Reaper"}


def test_cluster_values_skips_embedding_below_min_group_size():
    entries = [{"value": "Undertaker", "confidence": 0.9, "first_vol": 1, "claim_id": "c_a"}]
    calls = []
    embed_fn = lambda texts: calls.append(texts) or [[1.0]]  # noqa: E731
    clusters = CA.cluster_values(entries, embed_fn, threshold=0.9, min_group_size=2)
    assert not calls  # never invoked -- only one distinct value, nothing to cluster
    assert len(clusters) == 1


# ---------------------------------------------------------------------------
# canonicalize.py — Phase 22 A2: subsumption
# ---------------------------------------------------------------------------


def _obs(value, first_vol, claim_id):
    return {"value_or_object": value, "qualifier": None, "first_vol": first_vol, "claim_id": claim_id}


def test_subsume_values_drops_shorter_sibling_whose_words_are_a_subset():
    """Isolates rule 1 (subset-of-a-longer-sibling) from rule 2 (bare single-token noun): "brown
    hair" is 2 tokens, so only rule 1 can be why it is dropped here."""
    observations = [_obs("brown hair", 1, "c_a"), _obs("long brown hair", 2, "c_b")]
    kept = CA.subsume_values(observations)
    assert [o["claim_id"] for o in kept] == ["c_b"]


def test_subsume_values_requires_full_token_containment_not_a_shared_word():
    """The subsumption rule is token-SET containment: "brown hair" and "brown eyes" share the
    word "brown" but neither's token set is a subset of the other's, so neither subsumes the
    other -- unlike a naive raw-substring check, which this deliberately is not."""
    observations = [_obs("brown hair", 1, "c_a"), _obs("brown eyes", 2, "c_b")]
    kept = CA.subsume_values(observations)
    assert {o["claim_id"] for o in kept} == {"c_a", "c_b"}


def test_subsume_values_drops_a_lone_single_word_value():
    observations = [_obs("hair", 1, "c_a")]
    assert CA.subsume_values(observations) == []


def test_subsume_values_keeps_a_two_word_value_with_no_sibling():
    observations = [_obs("brown hair", 1, "c_a")]
    kept = CA.subsume_values(observations)
    assert [o["claim_id"] for o in kept] == ["c_a"]


def test_subsume_values_keeps_distinct_descriptive_phrases():
    observations = [_obs("golden eyes", 1, "c_a"), _obs("silver hair", 2, "c_b")]
    kept = CA.subsume_values(observations)
    assert {o["claim_id"] for o in kept} == {"c_a", "c_b"}


# ---------------------------------------------------------------------------
# contradictions.py — Phase 17: value canonicalization inside build_graph
# ---------------------------------------------------------------------------


class _FakeEmbedClient:
    """Satisfies contradictions.JSONClient's `embed` method; complete_json is unused here."""

    def __init__(self, vectors_by_text):
        self.vectors_by_text = vectors_by_text

    def embed(self, stage, texts):
        assert stage == "canonicalize"
        return [self.vectors_by_text[t] for t in texts]

    def complete_json(self, stage, prompt, schema, system=None):  # pragma: no cover
        raise AssertionError("arbitrate should not be called by a canonicalization-only test")


def test_build_graph_canonicalizes_near_duplicate_trait_values():
    claims = [
        _claim("c_a", "shin", "PERSONALITY", "trait", 1, 0.9, value="outwardly detached"),
        _claim("c_b", "shin", "PERSONALITY", "trait", 3, 0.7, value="detached on the outside"),
    ]
    client = _FakeEmbedClient(
        {"outwardly detached": [1.0, 0.0], "detached on the outside": [0.95, 0.05]}
    )
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=client)
    assert len(intervals) == 1
    assert intervals[0]["value"] == "outwardly detached"
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]
    assert doc["canonicalization"]["summary"]["groups_merged"] == 1
    merge = doc["canonicalization"]["merges"][0]
    assert merge["canonical"] == "outwardly detached"
    assert [v["value"] for v in merge["variants"]] == ["detached on the outside"]


def test_build_graph_degrades_gracefully_when_embed_client_raises():
    """Real-data regression: an unreachable Ollama must not crash `graph build` -- it must fall
    back to exact-match-only canonicalization, and must not re-attempt the dead connection once
    per (subject, predicate) group (a real build can have hundreds)."""

    class _FailingEmbedClient:
        def __init__(self):
            self.calls = 0

        def embed(self, stage, texts):
            self.calls += 1
            raise RuntimeError("Cannot reach Ollama at http://localhost:11434.")

    client = _FailingEmbedClient()
    claims = [
        _claim("c_a", "shin", "PERSONALITY", "trait", 1, 0.9, value="outwardly detached"),
        _claim("c_b", "shin", "PERSONALITY", "trait", 3, 0.7, value="detached on the outside"),
        _claim("c_c", "raiden", "TITLE", "attribute", 1, 0.9, value="Sergeant"),
        _claim("c_d", "raiden", "TITLE", "attribute", 2, 0.9, value="sergeant major"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=client)
    # No embed model reachable -- values stay distinct (normalize_value only), never crashes.
    assert len(intervals) == 4
    assert client.calls == 1  # only the FIRST group ever attempts the dead connection


def test_build_graph_canonicalization_leaves_distinct_values_untouched():
    claims = [
        _claim("c_a", "shin", "TITLE", "attribute", 1, 0.9, value="Undertaker"),
        _claim("c_b", "shin", "TITLE", "attribute", 5, 0.9, value="the Reaper"),
    ]
    client = _FakeEmbedClient({"Undertaker": [1.0, 0.0], "the Reaper": [0.0, 1.0]})
    intervals, edges, doc = CO.build_graph(claims, FakeSettings(), client=client)
    assert len(intervals) == 2
    assert doc["canonicalization"]["summary"]["groups_merged"] == 0


# ---------------------------------------------------------------------------
# contradictions.py — Phase 17: relation-conflict arbitration
# ---------------------------------------------------------------------------


def test_build_graph_same_volume_friend_and_enemy_is_arbitrated():
    claims = [
        _claim("c_a", "shin", "FRIEND_OF", "relation", 3, 0.9, object="raiden"),
        _claim("c_b", "shin", "ENEMY_OF", "relation", 3, 0.5, object="raiden"),
    ]
    intervals, edges, doc = CO.build_graph(claims, ConflictFakeSettings(), client=None)
    assert len(intervals) == 1
    assert intervals[0]["predicate"] == "FRIEND_OF"  # higher confidence, rule-based fallback
    assert doc["summary"]["extraction_error"] == 1
    conflict = doc["conflicts"][0]
    assert conflict["a"]["predicate"] == "FRIEND_OF"
    assert conflict["b"]["predicate"] == "ENEMY_OF"


def test_build_graph_cross_volume_friend_to_enemy_supersedes():
    claims = [
        _claim("c_a", "shin", "FRIEND_OF", "relation", 1, 0.9, object="raiden"),
        _claim("c_b", "shin", "ENEMY_OF", "relation", 5, 0.9, object="raiden"),
    ]
    intervals, edges, doc = CO.build_graph(claims, ConflictFakeSettings(), client=None)
    assert len(intervals) == 2
    by_predicate = {iv["predicate"]: iv for iv in intervals}
    assert by_predicate["FRIEND_OF"]["vol_start"] == 1
    assert by_predicate["FRIEND_OF"]["vol_end"] == 4
    assert by_predicate["ENEMY_OF"]["vol_start"] == 5
    assert by_predicate["ENEMY_OF"]["vol_end"] is None
    assert doc["summary"]["narrative_change"] == 1
    assert len(edges) == 2
    closed_edge = next(e for e in edges if e["predicate"] == "FRIEND_OF")
    assert closed_edge["vol_end"] == 4


def test_build_graph_same_predicate_extracted_from_both_directions_is_not_a_false_conflict():
    """Real-data regression (Spice and Wolf: Holo/Liebert ENEMY_OF was extracted independently
    from both directions, landing as two claim_ids under the SAME canonical predicate in the
    SAME volume, alongside a genuine FRIEND_OF claim). Ranking the top two claims by confidence
    ALONE (without first collapsing same-predicate duplicates) could put both ENEMY_OF claims in
    the top two, producing a nonsensical "ENEMY_OF|ENEMY_OF" conflict and silently dropping the
    real FRIEND_OF claim as a lowest-confidence outlier. Only genuinely different predicates may
    ever be compared."""
    claims = [
        _claim("c_a", "holo", "ENEMY_OF", "relation", 2, 0.9, object="liebert"),
        _claim("c_b", "liebert", "ENEMY_OF", "relation", 2, 0.85, object="holo"),  # other direction
        _claim("c_c", "holo", "FRIEND_OF", "relation", 2, 0.5, object="liebert"),
    ]
    intervals, edges, doc = CO.build_graph(claims, ConflictFakeSettings(), client=None)
    assert len(intervals) == 1
    assert intervals[0]["predicate"] == "ENEMY_OF"
    assert sorted(intervals[0]["claim_ids"]) == ["c_a", "c_b"]  # both directions merged
    assert doc["summary"]["extraction_error"] == 1  # exactly one real conflict, not two
    conflict = doc["conflicts"][0]
    assert {conflict["a"]["predicate"], conflict["b"]["predicate"]} == {"ENEMY_OF", "FRIEND_OF"}


# Phase 26: mirrors the real config/extraction.yaml shape -- ENEMY_OF conflicts with BOTH
# FRIEND_OF and COMRADE_OF, but those two do not conflict with each other; KILLED/SAVED form a
# separate pair that conflicts with neither.
RELATIONS_PARTIAL_CONFLICT = {
    **RELATIONS,
    "FRIEND_OF": {"symmetric": True, "conflicts_with": ["ENEMY_OF"]},
    "COMRADE_OF": {"symmetric": True, "conflicts_with": ["ENEMY_OF"]},
    "ENEMY_OF": {"symmetric": True, "conflicts_with": ["FRIEND_OF", "COMRADE_OF"]},
    "KILLED": {"conflicts_with": ["SAVED"]},
    "SAVED": {"conflicts_with": ["KILLED"]},
}


class PartialConflictFakeSettings(FakeSettings):
    relations = RELATIONS_PARTIAL_CONFLICT


def test_conflict_cliques_separates_predicates_that_do_not_conflict_with_each_other():
    groups = CO._relation_conflict_groups(RELATIONS_PARTIAL_CONFLICT)
    # FRIEND_OF and COMRADE_OF are both in a conflict group (via ENEMY_OF) but not with each
    # other -- they must NOT be arbitrated against one another.
    assert CO._conflict_cliques(["COMRADE_OF", "FRIEND_OF"], groups) == [["COMRADE_OF"], ["FRIEND_OF"]]
    # ENEMY_OF pulls both into one clique: exactly one of the three can hold.
    assert CO._conflict_cliques(["COMRADE_OF", "ENEMY_OF", "FRIEND_OF"], groups) == [
        ["COMRADE_OF", "ENEMY_OF", "FRIEND_OF"]
    ]
    # Being someone's enemy and having saved them are not mutually exclusive; killing and
    # saving them are.
    assert CO._conflict_cliques(["ENEMY_OF", "KILLED", "SAVED"], groups) == [
        ["ENEMY_OF"], ["KILLED", "SAVED"]
    ]


def test_non_conflicting_predicates_on_one_pair_both_survive():
    """Regression for the bug Phase 26's own COMRADE_OF/ENEMY_OF declaration would otherwise
    have introduced: `pair_claims` buckets every conflict-group predicate for a pair together,
    so adding COMRADE_OF to a group made Holo's genuine "comrade AND friend of Lawrence" pair
    arbitrate down to one survivor."""
    claims = [
        _claim("c_a", "holo", "COMRADE_OF", "relation", 1, 0.9, object="lawrence"),
        _claim("c_b", "holo", "FRIEND_OF", "relation", 1, 0.8, object="lawrence"),
    ]
    intervals, _edges, doc = CO.build_graph(claims, PartialConflictFakeSettings(), client=None)
    assert {iv["predicate"] for iv in intervals} == {"COMRADE_OF", "FRIEND_OF"}
    assert doc["summary"]["extraction_error"] == 0


def test_killed_and_saved_on_one_pair_arbitrate_without_disturbing_enemy_of():
    """The live v1-2 defect: `holo KILLED liebert` (0.96) and `holo SAVED liebert` (0.95) cite
    the same sentence, and ENEMY_OF holds alongside both. Exactly one of KILLED/SAVED may
    survive; ENEMY_OF is untouched because it conflicts with neither."""
    claims = [
        _claim("c_a", "holo", "ENEMY_OF", "relation", 2, 0.95, object="liebert"),
        _claim("c_b", "holo", "KILLED", "relation", 2, 0.96, object="liebert"),
        _claim("c_c", "holo", "SAVED", "relation", 2, 0.95, object="liebert"),
    ]
    intervals, _edges, doc = CO.build_graph(claims, PartialConflictFakeSettings(), client=None)
    predicates = sorted(iv["predicate"] for iv in intervals)
    assert "ENEMY_OF" in predicates
    assert len({"KILLED", "SAVED"} & set(predicates)) == 1, predicates
    assert doc["summary"]["extraction_error"] == 1


class FamilyConflictFakeSettings(FakeSettings):
    relations = {
        **RELATIONS,
        "SPOUSE_OF": {"symmetric": True, "conflicts_with": ["RELATIVE_OF", "SIBLING_OF"]},
        "RELATIVE_OF": {"symmetric": True, "conflicts_with": ["SPOUSE_OF", "SIBLING_OF"]},
        "SIBLING_OF": {"symmetric": True, "conflicts_with": ["SPOUSE_OF", "RELATIVE_OF"]},
    }


def test_build_graph_spouse_and_relative_on_the_same_pair_is_arbitrated():
    """Phase 23 A4: SPOUSE_OF/ROMANTIC_WITH now conflict with SIBLING_OF/RELATIVE_OF in the real
    config -- two incompatible family-shaped claims about the same pair must be arbitrated
    exactly like FRIEND_OF/ENEMY_OF, not silently coexist as two rendered relationship badges."""
    claims = [
        _claim("c_a", "marheit", "SPOUSE_OF", "relation", 1, 0.95, object="kraft-lawrence"),
        _claim("c_b", "kraft-lawrence", "RELATIVE_OF", "relation", 1, 0.6, object="marheit"),
    ]
    intervals, edges, doc = CO.build_graph(claims, FamilyConflictFakeSettings(), client=None)
    assert len(intervals) == 1
    assert intervals[0]["predicate"] == "SPOUSE_OF"  # higher confidence, rule-based fallback
    assert doc["summary"]["extraction_error"] == 1


def test_build_graph_relation_conflict_group_with_only_one_predicate_present_is_not_arbitrated():
    """FRIEND_OF/ENEMY_OF are declared conflicting, but if a pair only ever has FRIEND_OF claims,
    there is nothing to arbitrate -- it must behave exactly like an ordinary multi-valued
    relation (permanently open, no conflict logged)."""
    claims = [_claim("c_a", "shin", "FRIEND_OF", "relation", 1, 0.9, object="raiden")]
    intervals, edges, doc = CO.build_graph(claims, ConflictFakeSettings(), client=None)
    assert len(intervals) == 1
    assert intervals[0]["vol_end"] is None
    assert doc["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# Phase 26 part B — a relation contradicted by its object's own STATUS
# ---------------------------------------------------------------------------


class StatusImpliesFakeSettings(FakeSettings):
    attributes = {**ATTRIBUTES, "STATUS": {"single": True, "default": "alive"}}
    relations = {**RELATIONS, "KILLED": {"display": "Killed", "object_status_implies": "dead"}}


def test_killed_is_dropped_when_the_object_is_evidenced_alive():
    """The audit's most visible single error: `holo KILLED liebert` (0.96) and `liebert STATUS
    alive` (0.95) both extracted from Volume 2 off the SAME sentence, rendering "Holo — Killed"
    directly above "Status: alive" on Liebert's page. Neither `conflicts_with` (two relations on
    one pair) nor `single: true` arbitration (two values of one attribute) can see it."""
    claims = [
        _claim("c_k", "holo", "KILLED", "relation", 2, 0.96, object="liebert"),
        _claim("c_s", "liebert", "STATUS", "attribute", 2, 0.95, value="alive"),
    ]
    intervals, edges, doc = CO.build_graph(claims, StatusImpliesFakeSettings(), client=None)
    predicates = {iv["predicate"] for iv in intervals}
    assert "KILLED" not in predicates
    assert "STATUS" in predicates  # the status survives, not the extraordinary claim
    assert not [e for e in edges if e["predicate"] == "KILLED"]  # and the edge goes too
    conflict = next(c for c in doc["conflicts"] if c["arbiter"] == "rule:object_status_contradicts")
    assert conflict["kind"] == "extraction_error"


def test_killed_survives_when_the_object_has_no_evidenced_status():
    """A character with no STATUS claims materialises `attributes.STATUS.default` at RENDER time
    (Phase 22 A5 U6), never as a graph interval -- so a genuine death whose status was never
    restated must not be silently discarded. There is simply no evidence to adjudicate."""
    claims = [_claim("c_k", "holo", "KILLED", "relation", 2, 0.96, object="liebert")]
    intervals, _edges, doc = CO.build_graph(claims, StatusImpliesFakeSettings(), client=None)
    assert {iv["predicate"] for iv in intervals} == {"KILLED"}
    assert not [c for c in doc["conflicts"] if c["arbiter"] == "rule:object_status_contradicts"]


def test_killed_survives_when_the_status_agrees():
    claims = [
        _claim("c_k", "holo", "KILLED", "relation", 2, 0.96, object="liebert"),
        _claim("c_s", "liebert", "STATUS", "attribute", 2, 0.95, value="dead"),
    ]
    intervals, _edges, _doc = CO.build_graph(claims, StatusImpliesFakeSettings(), client=None)
    assert "KILLED" in {iv["predicate"] for iv in intervals}


def test_a_status_that_closes_before_the_relation_does_not_block_it():
    """"Alive in v1" says nothing about a killing in v3 -- only a status still open at the
    relation's own volume is a contradiction."""
    claims = [
        _claim("c_s1", "liebert", "STATUS", "attribute", 1, 0.95, value="alive"),
        _claim("c_s2", "liebert", "STATUS", "attribute", 3, 0.95, value="dead"),
        _claim("c_k", "holo", "KILLED", "relation", 3, 0.96, object="liebert"),
    ]
    intervals, _edges, _doc = CO.build_graph(claims, StatusImpliesFakeSettings(), client=None)
    assert "KILLED" in {iv["predicate"] for iv in intervals}


# ---------------------------------------------------------------------------
# Phase 26 part C — a relation whose object is the wrong KIND of thing
# ---------------------------------------------------------------------------


class ObjectTypesFakeSettings(FakeSettings):
    relations = {**RELATIONS, "KILLED": {"display": "Killed", "object_types": ["CHARACTER"]}}


def test_killed_is_dropped_when_its_object_is_a_location():
    """`holo KILLED pazzio` -- Pazzio is a town -- shipped in the live v1-2 wiki on a graph built
    AFTER KILLED gained `object_types: [CHARACTER]`, because the extractor's gate never revisits
    claims already on disk. The same config has to hold at graph build for it to be a property
    of the graph rather than of one extraction run."""
    claims = [_claim("c_k", "holo", "KILLED", "relation", 2, 0.91, object="pazzio")]
    intervals, edges, doc = CO.build_graph(
        claims, ObjectTypesFakeSettings(), client=None,
        entity_types={"holo": "CHARACTER", "pazzio": "LOCATION"},
    )
    assert intervals == []
    assert edges == []
    conflict = next(c for c in doc["conflicts"] if c["arbiter"] == "rule:object_type_mismatch")
    assert conflict["kind"] == "extraction_error"


def test_killed_survives_when_its_object_is_a_character():
    claims = [_claim("c_k", "holo", "KILLED", "relation", 2, 0.91, object="liebert")]
    intervals, _edges, doc = CO.build_graph(
        claims, ObjectTypesFakeSettings(), client=None,
        entity_types={"holo": "CHARACTER", "liebert": "CHARACTER"},
    )
    assert {iv["predicate"] for iv in intervals} == {"KILLED"}
    assert not [c for c in doc["conflicts"] if c["arbiter"] == "rule:object_type_mismatch"]


def test_an_unknown_object_and_an_absent_gazetteer_both_leave_the_relation_alone():
    """No type to check against is not evidence of a mismatch -- and `entity_types` is optional
    so a caller with no gazetteer (every test below this one) behaves exactly as before."""
    claims = [_claim("c_k", "holo", "KILLED", "relation", 2, 0.91, object="pazzio")]
    for entity_types in (None, {}, {"holo": "CHARACTER"}):
        intervals, _edges, _doc = CO.build_graph(
            claims, ObjectTypesFakeSettings(), client=None, entity_types=entity_types
        )
        assert {iv["predicate"] for iv in intervals} == {"KILLED"}


def test_a_relation_to_oneself_is_dropped():
    """[31] `captain-nemo RELATIVE_OF captain-nemo` reached a graph from a portrait scene."""
    claims = [_claim("c_r", "holo", "KILLED", "relation", 2, 0.9, object="holo")]
    intervals, edges, doc = CO.build_graph(
        claims, ObjectTypesFakeSettings(), client=None, entity_types={"holo": "CHARACTER"},
    )
    assert intervals == [] and edges == []
    assert next(c for c in doc["conflicts"] if c["arbiter"] == "rule:self_relation")["kind"] == "extraction_error"


def test_a_symmetric_relation_checks_its_subject_type_too():
    """[31] The scene pass produced `france FRIEND_OF conseil`: a LOCATION subject."""
    class S(FakeSettings):
        relations = {**RELATIONS, "FRIEND_OF": {"display": "Friend of", "symmetric": True,
                                                "object_types": ["CHARACTER", "FACTION"]}}
    claims = [_claim("c_f", "france", "FRIEND_OF", "relation", 2, 0.9, object="conseil")]
    intervals, _edges, doc = CO.build_graph(
        claims, S(), client=None, entity_types={"france": "LOCATION", "conseil": "CHARACTER"},
    )
    assert intervals == []
    assert "france is a LOCATION" in next(
        c for c in doc["conflicts"] if c["arbiter"] == "rule:object_type_mismatch")["rationale"]
