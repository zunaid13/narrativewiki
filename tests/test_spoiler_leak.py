"""THE spoiler-safety gate — CLAUDE.md §1.

    Every claim carries `first_vol`, the volume whose text supplied its evidence. A page
    rendered at cutoff N is built from claims filtered to `first_vol <= N`, and the prose is
    generated from that already-filtered set. Never generate from the full set and redact
    afterwards — implication leaks through redaction.

`CLAUDE.md` §1, `STRUCTURE.md`, `USER_GUIDE.md` and `docs/handover/PHASE_4.md` have all named
this file as the enforcing test since Phase 4. It did not exist until Phase 24; the invariant was
covered only incidentally, by per-query `vol_start <= vol` assertions scattered through
`test_graph.py`. Everything else in this repo is negotiable. This is not.

The tests are grouped by the leak channel each one closes (docs/vision/PHASE_24.md):

  L_query     what reaches the generator    -- intervals, per-quote evidence filtering
  L_artifact  what the page's shape reveals -- `vol_end` values, later-revealed aliases, links
  L_build     what the index was made of    -- the generate-not-redact property

`test_generation_input_is_independent_of_the_future` is the load-bearing one: it asserts the
*input* to generation is a pure function of volumes <= t, which is the whole difference between
filter-before-generate and redact-after-generate. A redaction-based implementation passes every
other test in this file and fails that one.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from narrativewiki.entities import automaton as AU
from narrativewiki.graph import store as ST
from narrativewiki.graph import temporal as TE
from narrativewiki.site import wikify as WK
from narrativewiki.synth import assemble as AS

ATTRIBUTES = {"RANK": {"single": True}, "STATUS": {"single": True}, "TITLE": {"single": False}}
RELATIONS = {
    "FRIEND_OF": {"symmetric": True, "display": "Friend of"},
    "AFFILIATED_WITH": {"display": "Affiliation"},
}
TRAITS = {"PERSONALITY": {}, "BACKGROUND": {}}
PAGE_OUTLINE = [
    {"key": "overview", "kind": "fields", "title": "Overview"},
    {"key": "affiliations", "kind": "affiliations", "title": "Affiliations"},
    {"key": "relationships", "kind": "relationships", "title": "Relationships"},
    {"key": "background", "kind": "prose", "title": "Background", "traits": ["BACKGROUND"]},
    {"key": "personality", "kind": "prose", "title": "Personality", "traits": ["PERSONALITY"]},
]

CUTOFFS = [1, 2, 3, 4, 5]


class FakeSettings:
    attributes = ATTRIBUTES
    relations = RELATIONS
    traits = TRAITS
    page_outline = PAGE_OUTLINE
    conflicts_config = {}

    def route_for(self, entity_type, entity_id):
        return f"/character/{entity_id}" if entity_type == "CHARACTER" else f"/codex/x#{entity_id}"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    return conn


def _claim(claim_id, subject, predicate, kind, first_vol, *, object=None, value=None, evidence=None):
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
        "evidence": evidence or [{"para_id": f"v{first_vol:02d}:c01:p0001", "quote": "ev"}],
        "polarity": "asserted",
        "source": "test",
    }


SHIN = {"entity_id": "shin", "canonical": "Shin", "type": "CHARACTER", "first_vol": 1, "importance": 1.0}
RAIDEN = {"entity_id": "raiden", "canonical": "Raiden", "type": "CHARACTER", "first_vol": 1, "importance": 0.5}
FREDERICA = {
    "entity_id": "frederica",
    "canonical": "Frederica",
    "type": "CHARACTER",
    "first_vol": 3,
    "importance": 0.5,
}

ENTITIES_BY_ID = {
    "shin": {**SHIN, "surface_forms": [{"text": "Shin", "first_vol": 1}]},
    "raiden": {**RAIDEN, "surface_forms": [{"text": "Raiden", "first_vol": 1}]},
    "frederica": {**FREDERICA, "surface_forms": [{"text": "Frederica", "first_vol": 3}]},
}


def _populated() -> sqlite3.Connection:
    """A graph spanning v1-v5: an attribute that changes at v4, a relation that opens at v3, and
    one claim whose own evidence array straddles v1 and v5."""
    conn = _conn()
    ST.write_entities(conn, [SHIN, RAIDEN, FREDERICA])
    ST.write_claims(
        conn,
        [
            _claim("c_rank1", "shin", "RANK", "attribute", 1, value="Second Lieutenant"),
            _claim("c_rank2", "shin", "RANK", "attribute", 4, value="Captain"),
            _claim("c_friend", "shin", "FRIEND_OF", "relation", 1, object="raiden"),
            _claim("c_late", "shin", "FRIEND_OF", "relation", 3, object="frederica"),
            _claim(
                "c_pers",
                "shin",
                "PERSONALITY",
                "trait",
                1,
                value="withdrawn",
                evidence=[
                    {"para_id": "v01:c01:p0001", "quote": "early evidence"},
                    {"para_id": "v05:c02:p0100", "quote": "LATE SPOILER EVIDENCE"},
                ],
            ),
        ],
    )
    ST.write_intervals(
        conn,
        TE.assign_single_valued(
            "shin",
            "RANK",
            [
                {"value": "Second Lieutenant", "qualifier": None, "first_vol": 1, "claim_ids": ["c_rank1"]},
                {"value": "Captain", "qualifier": None, "first_vol": 4, "claim_ids": ["c_rank2"]},
            ],
        ),
    )
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin",
            "FRIEND_OF",
            [
                {"value_or_object": "raiden", "qualifier": None, "first_vol": 1, "claim_id": "c_friend"},
                {"value_or_object": "frederica", "qualifier": None, "first_vol": 3, "claim_id": "c_late"},
            ],
            is_relation=True,
        ),
    )
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin",
            "PERSONALITY",
            [{"value_or_object": "withdrawn", "qualifier": None, "first_vol": 1, "claim_id": "c_pers"}],
            is_relation=False,
        ),
    )
    return conn


# ---------------------------------------------------------------------------------------------
# L_query -- what reaches the generator
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_no_future_interval_reaches_the_page(cutoff):
    """The claim set behind a page never contains an interval that opens after the cutoff."""
    conn = _populated()
    for interval_id in AS._visible_interval_ids(conn, "shin", cutoff):
        row = conn.execute(
            "SELECT vol_start FROM intervals WHERE interval_id = ?", (interval_id,)
        ).fetchone()
        assert row["vol_start"] <= cutoff


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_no_future_evidence_quote_reaches_the_page(cutoff):
    """A visible claim can still carry evidence from a later volume. Those quotes must be dropped
    per-quote, not trusted via the claim's `first_vol`."""
    conn = _populated()
    quotes = TE.evidence_at(conn, ["c_pers", "c_rank1", "c_rank2", "c_friend", "c_late"], cutoff)
    for ev in quotes:
        ev_vol = int(ev["para_id"].split(":", 1)[0][1:])
        assert ev_vol <= cutoff
    if cutoff < 5:
        assert not any(q["quote"] == "LATE SPOILER EVIDENCE" for q in quotes)


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_relations_never_name_an_entity_the_reader_cannot_know(cutoff):
    conn = _populated()
    page = AS.assemble_page(conn, None, SHIN, cutoff, FakeSettings(), ENTITIES_BY_ID)
    for rel in page["fields"].get("relationships", []) or []:
        assert ENTITIES_BY_ID[rel["entity_id"]]["first_vol"] <= cutoff
    if cutoff < 3:
        assert "frederica" not in repr(page)


def test_interval_qualifier_is_never_from_a_later_volume_than_it_opens():
    """Anne: FRIEND_OF opened at v1 ("bosom friend") printed v2's Echo Lodge qualifier in v01."""
    rows = [
        {"value_or_object": "shirley", "qualifier": "at Echo Lodge", "first_vol": 2, "claim_id": "c2"},
        {"value_or_object": "shirley", "qualifier": "bosom friend", "first_vol": 1, "claim_id": "c1"},
    ]
    (iv,) = TE.assign_multi_valued("diana", "FRIEND_OF", rows, is_relation=True)
    assert (iv["vol_start"], iv["qualifier"]) == (1, "bosom friend")
    rows[1]["qualifier"] = None
    (iv,) = TE.assign_multi_valued("diana", "FRIEND_OF", rows, is_relation=True)
    assert (iv["vol_start"], iv["qualifier"]) == (1, None)


# ---------------------------------------------------------------------------------------------
# L_artifact -- what the page's shape reveals
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("cutoff", [1, 2, 3])
def test_future_vol_end_never_renders_verbatim(cutoff):
    """RANK closes because a new rank opens at v4. Below the cutoff a reader may learn *that* it
    changes later (a boolean); never *when*, and never the succeeding value."""
    conn = _populated()
    page = AS.assemble_page(conn, None, SHIN, cutoff, FakeSettings(), ENTITIES_BY_ID)
    rank = page["fields"]["rank"]
    assert rank["value"] == "Second Lieutenant"
    assert "Captain" not in repr(page)
    for forbidden in ("vol_end", "v04"):
        assert forbidden not in repr(rank)


def test_wikify_never_links_an_entity_introduced_after_the_cutoff():
    auto = AU.build_automaton(list(ENTITIES_BY_ID.values()))
    linked = WK.wikify_text(
        "Shin spoke to Frederica about Raiden.", auto, ENTITIES_BY_ID, FakeSettings(), upto_vol=1
    )
    assert "[Raiden](/character/raiden)" in linked
    assert "(/character/frederica)" not in linked
    assert "Frederica" in linked  # the word stays; only the link is withheld


def test_wikify_never_uses_an_alias_revealed_after_the_cutoff():
    """CONTRACTS §2.1: an alias revealed in v4 must not appear on a v1 page even though the
    character does."""
    entities = {
        **ENTITIES_BY_ID,
        "shin": {
            **SHIN,
            "surface_forms": [{"text": "Shin", "first_vol": 1}, {"text": "Reaper", "first_vol": 4}],
        },
    }
    auto = AU.build_automaton(list(entities.values()))
    linked = WK.wikify_text("They called him Reaper.", auto, entities, FakeSettings(), upto_vol=1)
    assert "](" not in linked


def test_page_aliases_never_list_an_alias_revealed_after_the_cutoff():
    """[31] Anne's v01 page front matter listed "Anne Blythe" (surface form first_vol 5): the
    front matter and the JSON page model read the gazetteer's flat `aliases`, which carries no
    volume. Both now go through `gazetteer.aliases_at`."""
    from narrativewiki.entities.gazetteer import aliases_at
    from narrativewiki.site.okf import _front_matter

    shin = {**SHIN, "aliases": ["Shin", "Reaper"],
            "surface_forms": [{"text": "Shin", "first_vol": 1}, {"text": "Reaper", "first_vol": 4}]}
    assert aliases_at(shin, 1) == ["Shin"]
    assert aliases_at(shin, 4) == ["Shin", "Reaper"]
    page = {"entity_id": "shin", "canonical": shin["canonical"], "upto_vol": 1, "fields": {}}
    assert "Reaper" not in _front_matter(page, shin)
    assert "Reaper" in _front_matter({**page, "upto_vol": 4}, shin)


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_sparse_cutoff_resolution_never_selects_a_future_snapshot(cutoff):
    """The MkDocs wiki emitter's `resolve_cutoff` (site/mkdocs_wiki.py) is the one place a sparse
    multi-cutoff bundle dict (CONTRACTS §6.2/§6.1/§6.4's shared shape) gets resolved to a single
    cutoff's snapshot -- this is the highest-risk line in the whole emitter (docs/vision/
    PHASE_25.md): `<=` written as `<`, or a bare `max()` ignoring `vol` entirely, would silently
    publish a future snapshot into an earlier cutoff dir with nothing else positioned to notice.
    """
    from narrativewiki.site.mkdocs_wiki import resolve_cutoff

    cutoffs = {"1": "snapshot-at-1", "3": "snapshot-at-3", "5": "snapshot-at-5"}
    snapshot = resolve_cutoff(cutoffs, cutoff)
    expected_key = max(k for k in (1, 3, 5) if k <= cutoff)
    assert snapshot == f"snapshot-at-{expected_key}"
    # The direct leak check: a key strictly greater than `cutoff` must never be the one chosen.
    chosen_key = int(snapshot.rsplit("-", 1)[1])
    assert chosen_key <= cutoff


def test_resolve_cutoff_returns_none_before_the_first_key():
    from narrativewiki.site.mkdocs_wiki import resolve_cutoff

    assert resolve_cutoff({"3": "snapshot-at-3"}, 1) is None
    assert resolve_cutoff({}, 5) is None


@pytest.mark.parametrize("depth", [1, 2])
def test_href_relative_path_stays_within_the_cutoff_tree(depth):
    """`href()` never emits an absolute path or a bare route -- every link it produces must be
    resolvable purely by walking `../` from the emitting page, so a page copied out of its
    `vNN/` directory (or read as a raw file) still has correct link math relative to itself."""
    from narrativewiki.site.mkdocs_wiki import href

    result = href("/character/holo", depth)
    assert not result.startswith("/")
    assert result.count("../") == depth - 1
    assert result.endswith("character/holo.md")


def test_href_preserves_a_codex_anchor():
    from narrativewiki.site.mkdocs_wiki import href

    assert href("/codex/factions#the-spearhead", depth=2) == "../codex/factions.md#the-spearhead"


def test_relativize_rewrites_every_absolute_wikified_link():
    from narrativewiki.site.mkdocs_wiki import _relativize

    md = "Shin spoke to [Frederica](/character/frederica) near [The Spearhead](/codex/factions#the-spearhead)."
    out = _relativize(md, depth=2)
    assert "](/character/frederica)" not in out
    assert "](../character/frederica.md)" in out
    assert "](../codex/factions.md#the-spearhead)" in out


def test_relativize_leaves_non_route_links_untouched():
    from narrativewiki.site.mkdocs_wiki import _relativize

    md = "See [the source](https://example.com/paper.pdf) or [a local note](notes.md)."
    assert _relativize(md, depth=2) == md


# ---------------------------------------------------------------------------------------------
# L_build -- the generate-not-redact property
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("cutoff", CUTOFFS[:-1])
def test_claim_set_is_monotone_in_the_cutoff(cutoff):
    """A reader who reads further never *loses* knowledge. A non-monotone claim set is a sign the
    page is assembled by subtraction from the whole rather than construction from the part."""
    conn = _populated()
    here = AS._visible_interval_ids(conn, "shin", cutoff)
    later = AS._visible_interval_ids(conn, "shin", cutoff + 1)
    assert here <= later


@pytest.mark.parametrize("cutoff", [1, 2, 3])
def test_generation_input_is_independent_of_the_future(cutoff):
    """CLAUDE.md §1, stated as a property rather than a procedure.

    Build the same graph twice — once from the whole corpus, once from volumes <= cutoff only —
    and assert the generator's input is identical at that cutoff. Were the page produced by
    generating from everything and redacting afterwards, the two would differ: the full graph
    would carry post-cutoff intervals into the prompt and rely on a downstream filter. This is
    the one test here that a redaction-based implementation fails.
    """
    full = _populated()

    truncated = _conn()
    ST.write_entities(truncated, [e for e in (SHIN, RAIDEN, FREDERICA) if e["first_vol"] <= cutoff])
    for row in full.execute("SELECT * FROM intervals WHERE vol_start <= ?", (cutoff,)):
        closed_in_scope = row["vol_end"] is not None and row["vol_end"] <= cutoff
        ST.write_intervals(
            truncated,
            [
                {
                    "interval_id": row["interval_id"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "value": row["value"],
                    "qualifier": row["qualifier"],
                    "vol_start": row["vol_start"],
                    # a cutoff-consistent build cannot know a closure that happens later
                    "vol_end": row["vol_end"] if closed_in_scope else None,
                    "claim_ids": json.loads(row["claim_ids_json"]),
                    "superseded_by": row["superseded_by"],
                    "confidence": row["confidence"],
                    "evidence_count": row["evidence_count"],
                }
            ],
        )

    assert AS._claim_set_hash(full, "shin", cutoff) == AS._claim_set_hash(truncated, "shin", cutoff)
