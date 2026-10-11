"""Phase 2: candidate mining, classification, alias clustering, and the mention automaton.

Candidate mining and the automaton are pure/deterministic and tested directly. Classification
and alias clustering call an LLM through a duck-typed client, so tests pass a small scripted
fake and assert both the *decisions* it drives and, for the free tiers, that it is never even
called — a real cost invariant, not just a behavioural one.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from narrativewiki.entities import alias as A
from narrativewiki.entities import automaton as AU
from narrativewiki.entities import candidates as C
from narrativewiki.entities import classify as CL
from narrativewiki.entities import gazetteer as G

SERIES_CONFIG = {
    "entities": {
        "honorifics": ["Major", "Captain"],
        "stopword_surfaces": ["Legion"],
        "min_mentions": 3,
        "max_candidates_per_volume": 400,
        "entity_overrides": {"merge": [], "split": [], "force_type": [], "aliases": [], "exclude": []},
    }
}


def _record(para_id: str, text: str, vol: int = 1, speech: str = "narration") -> dict:
    return {"para_id": para_id, "vol": vol, "text": text, "speech": speech}


# ---------------------------------------------------------------------------
# candidates.py
# ---------------------------------------------------------------------------


def test_hyphenated_and_of_titled_names_are_mined_whole():
    """[34] Oz: "Saw-Horse" was mined as "Horse", and "Wicked Witch of the West" / "...of the
    East" only as "Wicked Witch". A title is kept only when its head is a name itself."""
    text = ("Then the Saw-Horse ran. The Wicked Witch of the West laughed. Wicked Witch of the East fell. "
            "Most of the Munchkins hid, and most of them slept.")
    cands = {c["surface"] for c in C.mine_candidates({1: [_record(f"v01:c01:p{i:04d}", text) for i in range(3)]},
                                                    SERIES_CONFIG, min_mentions=3)}
    assert "Saw-Horse" in cands and "Horse" not in cands
    assert {"Wicked Witch", "Wicked Witch of the West", "Wicked Witch of the East"} <= cands
    assert not any("Munchkins" in c and " of " in c for c in cands)


def test_two_titles_with_one_head_are_two_people():
    """[34] A bare "Wicked Witch" is in both titles; it must not fuse the two witches."""
    classified = [_classified("Wicked Witch", "CHARACTER", count=30),
                  _classified("Wicked Witch of the West", "CHARACTER", count=8),
                  _classified("Wicked Witch of the East", "CHARACTER", count=4)]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _ScriptedAliasClient((False, 0.9)))
    assert sorted(e["canonical"] for e in entities) == [
        "Wicked Witch", "Wicked Witch of the East", "Wicked Witch of the West"]


def test_mines_bigram_and_signals():
    records = [_record("v01:c01:p0001", "Vladilena Milizé stood at the window.")] * 4
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    surfaces = {c["surface"]: c for c in cands}
    assert "Vladilena Milizé" in surfaces
    assert "capitalised_bigram" in surfaces["Vladilena Milizé"]["signals"]
    assert surfaces["Vladilena Milizé"]["count"] == 4
    assert surfaces["Vladilena Milizé"]["first_vol"] == 1


def test_possessive_and_contraction_fold_into_base_token():
    """"Shin's" must not become its own candidate distinct from "Shin"."""
    records = [_record("v01:c01:p0001", "Shin's rifle was cold. Shin's hands were steady.")] * 3
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    surfaces = {c["surface"] for c in cands}
    assert "Shin" in surfaces
    assert "Shin's" not in surfaces
    assert "Shin" not in {"Shin's"}  # sanity
    shin = next(c for c in cands if c["surface"] == "Shin")
    assert shin["count"] == 6  # two occurrences per paragraph x 3 paragraphs


def test_sentence_initial_common_word_filtered_by_capitalisation_ratio():
    """"Not" appears at a sentence start a few times but is overwhelmingly used lowercase
    elsewhere in the same text — the frequency-ratio filter must drop it even though it is not
    in the hand-maintained stopword list."""
    records = [
        _record("v01:c01:p0001", "Not today. He was not ready, and he could not stop, not even once."),
        _record("v01:c01:p0002", "Not again. It was not fair, not at all, and not likely to change."),
        _record("v01:c01:p0003", "Not now. She could not wait, would not budge, and did not care."),
    ]
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    assert "Not" not in {c["surface"] for c in cands}


def test_capitalisation_ratio_is_evaluated_per_volume_not_pooled_across_the_whole_call():
    """[24] TASK-0004 Option A: a surface that clears the ratio within one volume's own text must
    survive even though a later volume in the SAME mining call pushes the pooled, corpus-wide
    ratio below threshold — the exact "Wisewolf" shape docs/vision/plans/0004-*.md root-caused (proper
    name in v1, increasingly a common descriptive title once v2 joins the same mining pass).
    Pooled: 4 exact / (4 + 12) any-case = 0.25, below 0.75 — the old, now-fixed behavior would
    have dropped it. Volume 1 alone: 4/4 = 1.0, clears it on its own."""
    v1 = [_record(f"v01:c01:p{i:04d}", "Wisewolf howled at the moon.") for i in range(4)]
    v2 = [_record(f"v02:c01:p{i:04d}", "the wisewolf padded through the snow.", vol=2) for i in range(12)]
    cands = C.mine_candidates({1: v1, 2: v2}, SERIES_CONFIG, min_mentions=3)
    assert "Wisewolf" in {c["surface"] for c in cands}


def test_honorific_signal_detected():
    records = [_record("v01:c01:p0001", "Captain Milizé gave the order.")] * 3
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    surfaces = {c["surface"]: c for c in cands}
    assert "honorific" in surfaces["Captain Milizé"]["signals"]


def test_vocative_signal_only_in_dialogue():
    records = [_record("v01:c01:p0001", "“Kurena, watch out!”", speech="dialogue")] * 3
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    surfaces = {c["surface"]: c for c in cands}
    assert "vocative" in surfaces["Kurena"]["signals"]


def test_para_raid_signal_detected():
    records = [_record("v01:c01:p0001", "Reaper here, reporting in.", speech="para_raid")] * 3
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    surfaces = {c["surface"]: c for c in cands}
    assert "para_raid_callsign" in surfaces["Reaper"]["signals"]


def test_config_stopword_surface_dropped():
    records = [_record("v01:c01:p0001", "The Legion advanced at dawn.")] * 5
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    assert "Legion" not in {c["surface"] for c in cands}


def test_min_mentions_filters_rare_candidates():
    records = [_record("v01:c01:p0001", "Grethe appeared once.")]
    cands = C.mine_candidates({1: records}, SERIES_CONFIG, min_mentions=3)
    assert "Grethe" not in {c["surface"] for c in cands}


def test_first_vol_is_minimum_across_volumes():
    v1 = [_record("v01:c01:p0001", "Shinei Nouzen walked on.", vol=1)] * 3
    v2 = [_record("v02:c01:p0001", "Shinei Nouzen walked on.", vol=2)] * 3
    cands = C.mine_candidates({2: v2, 1: v1}, SERIES_CONFIG, min_mentions=3)
    entry = next(c for c in cands if c["surface"] == "Shinei Nouzen")
    assert entry["first_vol"] == 1
    assert entry["count"] == 6


# ---------------------------------------------------------------------------
# classify.py
# ---------------------------------------------------------------------------

ENTITY_TYPES = {"CHARACTER": {}, "FACTION": {}, "LOCATION": {}, "EVENT": {}, "TECH": {}}


class _ScriptedClassifyClient:
    def __init__(self, answers: dict[str, tuple[str, float]]):
        self.answers = answers
        self.calls: list[str] = []

    def complete_json(self, stage, prompt, schema, system=None):
        self.calls.append(prompt)
        surface = prompt.split('"')[1]
        entity_type, confidence = self.answers[surface]
        return schema(entity_type=entity_type, confidence=confidence, notes="")


def test_classify_keeps_recognised_type():
    client = _ScriptedClassifyClient({"Shin": ("CHARACTER", 0.9)})
    candidate = {"surface": "Shin", "count": 10, "first_vol": 1, "signals": [], "evidence_para_ids": []}
    result = CL.classify_candidate(candidate, [], ENTITY_TYPES, client)
    assert result is not None
    assert result["type"] == "CHARACTER"
    assert result["type_confidence"] == 0.9


def test_classify_drops_not_entity():
    client = _ScriptedClassifyClient({"Not": ("NOT_ENTITY", 0.95)})
    candidate = {"surface": "Not", "count": 10, "first_vol": 1, "signals": [], "evidence_para_ids": []}
    assert CL.classify_candidate(candidate, [], ENTITY_TYPES, client) is None


def test_classify_drops_type_outside_closed_vocabulary():
    """A model that invents a type must be treated exactly like NOT_ENTITY — never invented
    into the gazetteer's closed taxonomy."""
    client = _ScriptedClassifyClient({"Foo": ("VEHICLE", 0.9)})
    candidate = {"surface": "Foo", "count": 10, "first_vol": 1, "signals": [], "evidence_para_ids": []}
    assert CL.classify_candidate(candidate, [], ENTITY_TYPES, client) is None


def test_classify_candidates_batch_and_progress_callback():
    client = _ScriptedClassifyClient({"Shin": ("CHARACTER", 0.9), "Not": ("NOT_ENTITY", 0.95)})
    candidates = [
        {"surface": "Shin", "count": 10, "first_vol": 1, "signals": [], "evidence_para_ids": []},
        {"surface": "Not", "count": 10, "first_vol": 1, "signals": [], "evidence_para_ids": []},
    ]

    class FakeSettings:
        entity_types = ENTITY_TYPES

    progress_calls = []
    kept = CL.classify_candidates(
        candidates, {}, FakeSettings(), client, on_progress=lambda i, n, c, k: progress_calls.append((i, n, k))
    )
    assert len(kept) == 1 and kept[0]["surface"] == "Shin"
    assert progress_calls == [(1, 2, True), (2, 2, False)]


# ---------------------------------------------------------------------------
# alias.py
# ---------------------------------------------------------------------------


class _RaisingClient:
    """Used to prove the free tiers (a-c) never reach the LLM."""

    def complete_json(self, *args, **kwargs):
        raise AssertionError("LLM should not be called for a free-tier merge")


def _classified(surface: str, entity_type: str, count: int = 10, first_vol: int = 1, evidence=None) -> dict:
    return {
        "surface": surface,
        "type": entity_type,
        "count": count,
        "first_vol": first_vol,
        "type_confidence": 0.9,
        "signals": [],
        "evidence_para_ids": evidence or [],
    }


def test_exact_normalized_match_merges_without_llm_call():
    classified = [_classified("Milizé", "CHARACTER"), _classified("Milize", "CHARACTER")]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert len(entities) == 1
    assert entities[0]["mention_count"] == 20


def test_honorific_stripped_exact_match_merges_without_llm_call():
    classified = [_classified("Captain Milizé", "CHARACTER"), _classified("Milizé", "CHARACTER")]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert len(entities) == 1
    assert entities[0]["canonical"] == "Milizé"


def test_whole_word_subset_merges_without_llm_call():
    classified = [_classified("Vladilena Milizé", "CHARACTER", count=100), _classified("Milizé", "CHARACTER", count=50)]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert len(entities) == 1
    assert entities[0]["canonical"] == "Vladilena Milizé"  # more tokens wins canonical
    assert "Milizé" in entities[0]["aliases"]
    assert entities[0]["mention_count"] == 150


def test_leading_conjunction_does_not_win_canonical_over_the_clean_name():
    """A sentence-initial function word swept into a capitalised run ("As Lena walked...") mines
    as its own candidate alongside the bare name and merges into the same cluster (whole-word
    subset, tier c) -- but must not outrank the clean form for canonical just for having one more
    token. Found via a real v01-04 run: "As Lena", "And Kiriya", "And Anju" all did this."""
    classified = [_classified("As Lena", "CHARACTER", count=3), _classified("Lena", "CHARACTER", count=668)]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert len(entities) == 1
    assert entities[0]["canonical"] == "Lena"
    assert "As Lena" in entities[0]["aliases"]


def test_different_types_never_auto_merge_even_if_identical_text():
    classified = [_classified("Spearhead", "FACTION"), _classified("Spearhead", "TECH")]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert len(entities) == 2


class _ScriptedAliasClient:
    def __init__(self, decision: tuple[bool, float]):
        self.decision = decision
        self.calls = 0

    def complete_json(self, stage, prompt, schema, system=None):
        self.calls += 1
        same, confidence = self.decision
        return schema(same_entity=same, confidence=confidence, notes="")


def test_cooccurrence_pair_reaches_llm_and_merges_on_confident_yes():
    """"Shin" and "Undertaker" share no textual similarity at all — only a shared evidence
    paragraph can nominate them for an LLM call in the first place."""
    classified = [
        _classified("Shin", "CHARACTER", count=400, evidence=["v01:c01:p0003"]),
        _classified("Undertaker", "CHARACTER", count=50, evidence=["v01:c01:p0003", "v01:c02:p0010"]),
    ]
    client = _ScriptedAliasClient((True, 0.9))
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, client)
    assert client.calls == 1
    assert len(entities) == 1
    assert entities[0]["canonical"] == "Shin"  # higher count, same token length
    assert "Undertaker" in entities[0]["aliases"]
    assert entities[0]["confidence"] == 0.9


def test_canonical_is_never_a_name_first_seen_in_a_later_volume():
    """[32] A page is titled by its canonical name at every cutoff. "Vladilena Milizé" has more
    tokens and more mentions, but it first appears in v2; the v1 reader knows "Milizé"."""
    classified = [_classified("Milizé", "CHARACTER", count=50, first_vol=1),
                  _classified("Vladilena Milizé", "CHARACTER", count=100, first_vol=2)]
    # [34] A full name first seen in a later volume is the model's call, not a free merge.
    client = _ScriptedAliasClient((True, 0.9))
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, client)
    assert [e["canonical"] for e in entities] == ["Milizé"]
    assert client.calls == 1


def test_a_full_name_first_seen_later_is_not_merged_for_free():
    """[34] Anne's father "Walter" (v1) joined "Walter Blythe" (v5) by whole-word subset, and the
    v1 page described the son. Kept apart by the model, the v5 bare mentions go to the son."""
    classified = [_classified("Walter", "CHARACTER", count=6, first_vol=1),
                  _classified("Walter Blythe", "CHARACTER", count=4, first_vol=5)]
    paragraphs = {"v01:c01:p0001": "Walter was her father.", "v01:c02:p0001": "Walter died young.",
                  "v05:c01:p0001": "Walter Blythe wrote poems. Walter Blythe dreamed.",
                  "v05:c01:p0002": "Walter laughed. Walter Blythe smiled. Walter ran."}
    client = _ScriptedAliasClient((False, 0.9))
    entities = {e["entity_id"]: e for e in A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, client)}
    assert client.calls == 1
    assert set(entities) == {"walter", "walter-blythe"}
    bare = {eid: sf.get("vols") for eid, e in entities.items() for sf in e["surface_forms"] if sf["text"] == "Walter"}
    assert bare == {"walter": [1], "walter-blythe": [5]}
    assert entities["walter-blythe"]["first_vol"] == 5


def test_a_bare_first_name_two_full_names_contain_joins_the_one_its_volumes_use():
    """[34] "Anne" is in "Anne Shirley" and "Small Anne Cordelia", so clustering kept it apart and
    the protagonist had two pages. Volume 1 uses "Anne Shirley" far more: one page."""
    classified = [_classified("Anne", "CHARACTER", count=300), _classified("Anne Shirley", "CHARACTER", count=5),
                  _classified("Small Anne Cordelia", "CHARACTER", count=1)]
    paragraphs = {f"v01:c01:p{i:04d}": "Anne Shirley said so. Anne agreed. Anne went." for i in range(3)}
    paragraphs["v02:c01:p0001"] = "Anne smiled. Small Anne Cordelia, she whispered."
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _ScriptedAliasClient((False, 0.9)))
    names = {e["canonical"]: sorted(sf["text"] for sf in e["surface_forms"]) for e in entities}
    assert names == {"Anne Shirley": ["Anne", "Anne Shirley"], "Small Anne Cordelia": ["Small Anne Cordelia"]}
    assert not any(sf.get("vols") for e in entities for sf in e["surface_forms"])


def test_a_few_mentions_of_another_full_name_do_not_take_a_bare_name_over():
    """[34] Anne's book 4 says "Small Anne Cordelia" 6 times and "Anne" 702 times; the six took
    every bare "Anne" of books 4-5 off Anne Shirley's page."""
    classified = [_classified("Anne", "CHARACTER", count=300), _classified("Anne Shirley", "CHARACTER", count=5),
                  _classified("Small Anne Cordelia", "CHARACTER", count=3, first_vol=2)]
    paragraphs = {f"v01:c01:p{i:04d}": "Anne Shirley said so. Anne agreed." for i in range(5)}
    paragraphs |= {f"v02:c01:p{i:04d}": "Anne smiled. Anne laughed. Anne ran. Anne sat." * 10 for i in range(5)}
    paragraphs |= {f"v02:c02:p{i:04d}": "Small Anne Cordelia, she said." for i in range(3)}
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _ScriptedAliasClient((False, 0.9)))
    names = {e["canonical"]: sorted(sf["text"] for sf in e["surface_forms"]) for e in entities}
    assert names["Anne Shirley"] == ["Anne", "Anne Shirley"]
    assert not any(sf.get("vols") for e in entities for sf in e["surface_forms"])


def test_a_shared_surname_with_later_full_names_stays_a_bridge():
    """[34] Anne v2: "Blythe" (v4) joined "Gilbert Blythe" (v1) because the bridge check saw only
    the full names not first seen later; "Walter Blythe" and "Di Blythe" (v5) contain it too."""
    classified = [_classified("Blythe", "CHARACTER", count=30, first_vol=4),
                  _classified("Gilbert Blythe", "CHARACTER", count=50, first_vol=1),
                  _classified("Walter Blythe", "CHARACTER", count=10, first_vol=5),
                  _classified("Di Blythe", "CHARACTER", count=5, first_vol=5)]
    client = _ScriptedAliasClient((False, 0.9))
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, client)
    assert sorted(e["canonical"] for e in entities) == ["Blythe", "Di Blythe", "Gilbert Blythe", "Walter Blythe"]


def test_a_bridge_joins_its_longer_forms_once_the_model_makes_them_one():
    """[34] Oz: "Wizard" is in "Wonderful Wizard" and "Wizard of Oz"; held back as a bridge, it
    became a second Wizard page once the model said the two titles are one person."""
    classified = [_classified("Wizard", "CHARACTER", count=200),
                  _classified("Wonderful Wizard", "CHARACTER", count=20, evidence=["v01:c02:p0003"]),
                  _classified("Wizard of Oz", "CHARACTER", count=10, evidence=["v01:c02:p0003"])]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _ScriptedAliasClient((True, 0.9)))
    assert [sorted(sf["text"] for sf in e["surface_forms"]) for e in entities] == [
        ["Wizard", "Wizard of Oz", "Wonderful Wizard"]]


def test_an_article_is_not_a_first_name():
    """[34] Oz v2: "The Princess" had the core ["the"] and went to "The Wonderful Wizard"."""
    classified = [_classified("The Princess", "CHARACTER", count=20), _classified("The Wonderful Wizard", "CHARACTER", count=9)]
    paragraphs = {f"v01:c01:p{i:04d}": "The Wonderful Wizard spoke. The Princess bowed." for i in range(5)}
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _ScriptedAliasClient((False, 0.9)))
    assert sorted(sorted(sf["text"] for sf in e["surface_forms"]) for e in entities) == [
        ["The Princess"], ["The Wonderful Wizard"]]
    assert not any(sf.get("vols") for e in entities for sf in e["surface_forms"])


def test_a_merged_bare_name_never_leaves_a_later_name_on_the_page():
    """[34] anne@v2: "Dick" (v3) merged into "Dick Moore" (v4) kept the v4 name and id for an entity
    that starts in v3 (audit-gazetteer: canonical revealed after the entity appears)."""
    classified = [_classified("Dick", "CHARACTER", count=50, first_vol=3), _classified("Dick Moore", "CHARACTER", count=5, first_vol=4)]
    paragraphs = {f"v04:c01:p{i:04d}": "Dick Moore sat. Dick smiled. Dick ate." for i in range(4)}
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _ScriptedAliasClient((False, 0.9)))
    (e,) = entities
    assert (e["canonical"], e["entity_id"], e["first_vol"]) == ("Dick", "dick", 3)
    assert sorted(sf["text"] for sf in e["surface_forms"]) == ["Dick", "Dick Moore"]


def test_a_bare_surname_is_never_assigned_to_one_full_name():
    """[34] "Cuthbert" is Matthew's and Marilla's surname; a volume that says "Matthew Cuthbert"
    more often still does not make every bare "Cuthbert" Matthew."""
    classified = [_classified("Cuthbert", "CHARACTER", count=40), _classified("Matthew Cuthbert", "CHARACTER", count=9),
                  _classified("Marilla Cuthbert", "CHARACTER", count=1)]
    paragraphs = {f"v01:c01:p{i:04d}": "Matthew Cuthbert came. Cuthbert went." for i in range(5)}
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _ScriptedAliasClient((False, 0.9)))
    assert sorted(e["canonical"] for e in entities) == ["Cuthbert", "Marilla Cuthbert", "Matthew Cuthbert"]


def test_mention_index_gives_a_split_surface_to_its_owner_of_that_volume():
    """[34] One literal surface, two owners by volume: both are indexed, each only in its volumes."""
    from narrativewiki.entities.automaton import build_automaton

    entities = [
        {"entity_id": "walter", "type": "CHARACTER", "first_vol": 1, "surface_forms": [
            {"text": "Walter", "first_vol": 1, "ambiguous": True, "vols": [1, 2, 3, 4]}]},
        {"entity_id": "walter-blythe", "type": "CHARACTER", "first_vol": 5, "surface_forms": [
            {"text": "Walter Blythe", "first_vol": 5, "ambiguous": False},
            {"text": "Walter", "first_vol": 5, "ambiguous": True, "vols": [5]}]},
    ]
    automaton = build_automaton(entities)
    assert not automaton.dropped_ambiguous_surfaces
    assert [m[3] for m in automaton.find_all("Walter came.", 1)] == ["walter"]
    assert [m[3] for m in automaton.find_all("Walter came.", 5)] == ["walter-blythe"]
    assert [m[3] for m in automaton.find_all("Walter Blythe came.", 5)] == ["walter-blythe"]
    assert automaton.find_all("Walter came.", 6) == []


def test_canonical_is_the_most_used_name_not_a_longer_different_one():
    """[32] Bookworm: the narrator is "Myne"; "Urano Motosu" (her past life) has more tokens but
    does not contain "Myne", so it must not title her page. The fuller form of the most-used name
    still wins ("Lena" -> "Lena Milizé")."""
    classified = [
        _classified("Myne", "CHARACTER", count=900, evidence=["v01:c01:p0003"]),
        _classified("Urano Motosu", "CHARACTER", count=20, evidence=["v01:c01:p0003"]),
        _classified("Lena", "CHARACTER", count=600),
        _classified("Lena Milizé", "CHARACTER", count=5),
    ]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _ScriptedAliasClient((True, 0.9)))
    assert sorted(e["canonical"] for e in entities) == ["Lena Milizé", "Myne"]


def test_different_honorifics_are_different_people():
    """[32] Middlemarch: "Mr. Brooke" (the uncle) and "Miss Brooke" (Dorothea) both strip to
    "Brooke"; tier a fused them, with the bare "Brooke" as a bridge."""
    classified = [_classified("Brooke", "CHARACTER", count=300), _classified("Mr. Brooke", "CHARACTER", count=80),
                  _classified("Miss Brooke", "CHARACTER", count=60)]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _ScriptedAliasClient((True, 0.95)))
    names = {e["canonical"]: sorted(sf["text"] for sf in e["surface_forms"]) for e in entities}
    # The two clusters would both be "Brooke"; each keeps its honorific so each has a page.
    assert names == {"Brooke": ["Brooke", "Mr. Brooke"], "Miss Brooke": ["Miss Brooke"]}


def test_a_bare_name_the_text_gives_two_honorifics_does_not_absorb_either():
    """[32] Middlemarch mines "Brooke" (mostly Mr. Brooke) and "Miss Brooke" (Dorothea); the text
    also says "Mr. Brooke", so the bare form is ambiguous and must not swallow Miss Brooke. A name
    seen with one honorific only ("Miss Holo") still merges."""
    classified = [_classified("Brooke", "CHARACTER", count=282), _classified("Miss Brooke", "CHARACTER", count=65),
                  _classified("Holo", "CHARACTER", count=900), _classified("Miss Holo", "CHARACTER", count=4)]
    paragraphs = {"p1": "Mr. Brooke nodded. Mr. Brooke left.", "p2": "Miss Brooke read. Miss Brooke sighed.",
                  "p3": "Miss Holo laughed."}
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _RaisingClient())
    assert sorted(e["canonical"] for e in entities) == ["Brooke", "Holo", "Miss Brooke"]


def test_alias_quotes_show_the_name_not_the_paragraph_opening():
    """[33] Middlemarch introduces Miss Noble and Miss Winifred ~1,100 characters into a paragraph;
    a 200-character head never showed them, and the model merged them from memory."""
    para = "x" * 1000 + " Miss Noble, her sister, and Miss Winifred Farebrother, the Vicar's elder sister."
    a = {"surface": "Miss Noble", "type": "CHARACTER", "count": 8, "first_vol": 2}
    b = {"surface": "Miss Winifred", "type": "CHARACTER", "count": 6, "first_vol": 2}
    prompt = A._user_prompt(a, b, {"Miss Noble": [para, para], "Miss Winifred": [para]})
    assert "Miss Winifred Farebrother" in prompt
    assert prompt.count("her sister") == 2   # the duplicate paragraph is quoted once per form


def test_a_rename_paragraph_proposes_the_two_names():
    """[33] Overlord: "Ainz" and "Momonga" share no letters and no sampled paragraph; the text's
    "return to being Momonga" does. The pair reaches the model with that paragraph first."""
    classified = [_classified("Ainz", "CHARACTER", count=1429, evidence=["p1"]),
                  _classified("Momonga", "CHARACTER", count=379, evidence=["p2"])]
    paragraphs = {"p1": "Ainz nodded.", "p2": "Momonga sighed.",
                  "p3": "Ainz thought, when that time comes, I'll gladly return to being Momonga."}
    client = _ScriptedAliasClient((True, 0.95))
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, client)
    assert [e["canonical"] for e in entities] == ["Ainz"]


def test_a_single_stray_honorific_does_not_split_a_name():
    """[33] Overlord: "Mistress Albedo" x7, "Miss Albedo" x1. One slip is not a second person."""
    classified = [_classified("Albedo", "CHARACTER", count=421), _classified("Mistress Albedo", "CHARACTER", count=7)]
    paragraphs = {"p1": "Mistress Albedo nodded. Mistress Albedo left.", "p2": "Miss Albedo smiled."}
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _RaisingClient())
    assert [e["canonical"] for e in entities] == ["Albedo"]


def test_a_leading_verb_never_names_the_page():
    """[33] "Is Albedo" (a question's first words, 3 mentions) titled Albedo's page (421)."""
    classified = [_classified("Albedo", "CHARACTER", count=421), _classified("Is Albedo", "CHARACTER", count=3)]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert [e["canonical"] for e in entities] == ["Albedo"]


def test_honorifics_of_one_person_class_are_one_person():
    """[32] Overlord says "Sir Momon" and "Lord Momon" for one man; counting them as two
    honorifics split the protagonist across five pages. Mr./Miss still split (above)."""
    classified = [_classified("Momon", "CHARACTER", count=147), _classified("Sir Momon", "CHARACTER", count=13),
                  _classified("Lord Momon", "CHARACTER", count=3)]
    paragraphs = {"p1": "Sir Momon nodded.", "p2": "Lord Momon left."}
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, _RaisingClient())
    assert [e["canonical"] for e in entities] == ["Momon"]


def test_an_honorific_alias_that_is_another_pages_name_keeps_its_honorific():
    """[32] Dorothea's "Miss Brooke" joins Dorothea; stripped, it would be the alias "Brooke",
    which is her uncle's page."""
    classified = [_classified("Dorothea", "CHARACTER", count=600, evidence=["p2"]),
                  _classified("Miss Brooke", "CHARACTER", count=65, evidence=["p2"]),
                  _classified("Brooke", "CHARACTER", count=282)]
    paragraphs = {"p1": "Mr. Brooke nodded. Mr. Brooke left.", "p2": "Miss Brooke, Dorothea, read. Miss Brooke sighed."}
    client = _ScriptedAliasClient((True, 0.95))
    entities = {e["canonical"]: e for e in A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, client)}
    assert entities["Dorothea"]["aliases"] == ["Miss Brooke"]


def test_a_narrators_adjective_does_not_become_part_of_the_name():
    """[32] Middlemarch: "Poor Dorothea" is Dorothea."""
    classified = [_classified("Dorothea", "CHARACTER", count=500), _classified("Poor Dorothea", "CHARACTER", count=40)]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert [e["canonical"] for e in entities] == ["Dorothea"]


def test_a_kinship_word_does_not_name_a_cluster_that_has_a_proper_name():
    """[32] Bookworm's narrator says "Dad" 592 times and "Gunther" far less; the page is Gunther's."""
    classified = [
        _classified("Dad", "CHARACTER", count=592, evidence=["v01:c01:p0003"]),
        _classified("Gunther", "CHARACTER", count=40, evidence=["v01:c01:p0003"]),
    ]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _ScriptedAliasClient((True, 0.9)))
    assert [e["canonical"] for e in entities] == ["Gunther"]


def test_an_appositive_proposes_a_kinship_word_and_a_name_for_adjudication():
    """[32] "my mom, Effa" is the only place Bookworm ties "Mom" (564 mentions) to Effa; the two
    share no letters and no sampled evidence paragraph, so only the appositive can propose them."""
    classified = [
        _classified("Mom", "CHARACTER", count=564, evidence=["v01:c02:p0001"]),
        _classified("Effa", "CHARACTER", count=53, evidence=["v01:c05:p0009"]),
        _classified("Tuuli", "CHARACTER", count=900, evidence=["v01:c07:p0002"]),
    ]
    paragraphs = {"v01:c01:p0010": "My family was four people: my mom, Effa; my older sister, Tuuli."}
    client = _ScriptedAliasClient((True, 0.9))
    entities = A.cluster_candidates(classified, paragraphs, SERIES_CONFIG, client)
    assert client.calls == 1  # Mom/Effa only; "sister, Tuuli" is not a Mom appositive
    assert sorted(e["canonical"] for e in entities) == ["Effa", "Tuuli"]


def test_a_confident_different_verdict_blocks_a_transitive_merge():
    """[32] Spice and Wolf: Elsa != Melta (1.0), but Melta == "Miss Elsa" (0.9) and "Miss Elsa"
    is Elsa by honorific stripping. Union-find used to fuse all three."""
    classified = [
        _classified("Elsa", "CHARACTER", count=340, first_vol=4, evidence=["v04:c00:p0001"]),
        _classified("Miss Elsa", "CHARACTER", count=14, first_vol=4, evidence=["v05:c02:p0721"]),
        _classified("Melta", "CHARACTER", count=43, first_vol=5, evidence=["v05:c02:p0721"]),
    ]

    class Client:
        def complete_json(self, stage, prompt, schema, system=None):
            a = prompt.split('"')[1]
            b = prompt.split('Form B: "')[1].split('"')[0]
            same = {a, b} == {"Melta", "Miss Elsa"}
            return schema(same_entity=same, confidence=0.9 if same else 1.0, notes="")

    # Tier a merges "Miss Elsa" into "Elsa" (honorific stripped) before any call; the model is
    # then asked Elsa/Melta only if co-occurrence proposes it, so give both pairs shared evidence.
    classified[0]["evidence_para_ids"].append("v05:c02:p0721")
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, Client())
    assert sorted(e["canonical"] for e in entities) == ["Elsa", "Melta"]


def test_the_author_named_in_an_afterword_is_not_an_entity():
    """[32] Read from series metadata, replacing each series' hand-written exclusion."""
    classified = [_classified("Isuna Hasekura", "CHARACTER"), _classified("Holo", "CHARACTER")]
    cfg = {**SERIES_CONFIG, "series": {"author": "Isuna Hasekura"}}
    entities = A.cluster_candidates(classified, {}, cfg, _RaisingClient())
    assert [e["canonical"] for e in entities] == ["Holo"]


def test_cooccurrence_pair_stays_separate_on_low_confidence_yes():
    classified = [
        _classified("Shin", "CHARACTER", count=400, evidence=["v01:c01:p0003"]),
        _classified("Undertaker", "CHARACTER", count=50, evidence=["v01:c01:p0003"]),
    ]
    client = _ScriptedAliasClient((True, 0.5))  # below LLM_MERGE_CONFIDENCE
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, client)
    assert len(entities) == 2


def test_unrelated_pairs_with_no_signal_never_reach_llm():
    classified = [
        _classified("Shin", "CHARACTER", evidence=["v01:c01:p0001"]),
        _classified("Annette", "CHARACTER", evidence=["v01:c09:p0050"]),
    ]
    entities = A.cluster_candidates(classified, {}, SERIES_CONFIG, _RaisingClient())
    assert len(entities) == 2


def test_cluster_candidates_reports_pairs_capped_via_callback():
    """[24] `on_pairs_capped(total, dropped)` fires once, before any LLM call, even when the cap
    isn't binding -- docs/vision/plans/0008-pre-full-scale-audit.md B1."""
    classified = [
        _classified("Shin", "CHARACTER", count=400, evidence=["v01:c01:p0003"]),
        _classified("Undertaker", "CHARACTER", count=50, evidence=["v01:c01:p0003"]),
    ]
    client = _ScriptedAliasClient((True, 0.9))
    seen: list[tuple[int, int]] = []
    A.cluster_candidates(classified, {}, SERIES_CONFIG, client, on_pairs_capped=lambda t, d: seen.append((t, d)))
    assert seen == [(1, 0)]  # one pair considered, none dropped -- cap is 300 by default


def test_mark_ambiguous_flags_a_surface_shared_by_two_entities():
    """A literal surface text claimed by more than one entity is a real collision — both
    entities' copies of it must be flagged, per CONTRACTS section 2.1."""
    entities = [
        {"entity_id": "a", "surface_forms": [{"text": "Reaper", "ambiguous": False, "first_vol": 1}]},
        {"entity_id": "b", "surface_forms": [{"text": "Reaper", "ambiguous": False, "first_vol": 4}]},
        {"entity_id": "c", "surface_forms": [{"text": "Kurena", "ambiguous": False, "first_vol": 1}]},
    ]
    A._mark_ambiguous(entities)
    assert entities[0]["surface_forms"][0]["ambiguous"] is True
    assert entities[1]["surface_forms"][0]["ambiguous"] is True
    assert entities[2]["surface_forms"][0]["ambiguous"] is False


# ---------------------------------------------------------------------------
# gazetteer.py
# ---------------------------------------------------------------------------


def test_slugify_ascii_folds_accents_and_lowercases():
    assert G.slugify("Vladilena Milizé") == "vladilena-milize"
    assert G.slugify("  Weird---Spacing  ") == "weird-spacing"
    assert G.slugify("") == "entity"


def test_compute_importance_normalises_to_max():
    entities = [{"mention_count": 100}, {"mention_count": 25}, {"mention_count": 50}]
    G.compute_importance(entities)
    assert entities[0]["importance"] == 1.0
    assert entities[1]["importance"] == 0.25
    assert entities[2]["importance"] == 0.5


def test_build_gazetteer_shape():
    entities = [{"mention_count": 10, "entity_id": "a"}, {"mention_count": 20, "entity_id": "b"}]
    gaz = G.build_gazetteer(entities, [3, 1, 2])
    assert gaz["volumes_covered"] == [1, 2, 3]
    assert [e["entity_id"] for e in gaz["entities"]] == ["b", "a"]  # sorted by mention_count desc
    assert gaz["built_at"].endswith("Z")


def test_build_gazetteer_omits_provenance_when_nothing_given():
    """[24] No behaviour change for a caller that doesn't pass any provenance kwarg."""
    gaz = G.build_gazetteer([{"mention_count": 1, "entity_id": "a"}], [1])
    assert "provenance" not in gaz


def test_build_gazetteer_provenance_includes_only_given_fields():
    """docs/vision/plans/0008-pre-full-scale-audit.md B1/B3: min_mentions and the alias-pair cap's
    effect are now recorded on the artifact they describe, not left as an outside assumption."""
    gaz = G.build_gazetteer(
        [{"mention_count": 1, "entity_id": "a"}], [1],
        min_mentions=3, alias_pairs_total=12, alias_pairs_dropped=0,
    )
    assert gaz["provenance"] == {"min_mentions": 3, "alias_pairs_total": 12, "alias_pairs_dropped": 0}


# ---------------------------------------------------------------------------
# automaton.py
# ---------------------------------------------------------------------------


def _make_automaton(pairs: list[tuple[str, str]]) -> AU.MentionAutomaton:
    auto = AU.MentionAutomaton()
    for surface, entity_id in pairs:
        auto.add(surface, entity_id)
    return auto.build()


def test_longest_match_wins():
    auto = _make_automaton([("Nouzen", "shinei-nouzen"), ("Shinei Nouzen", "shinei-nouzen")])
    matches = auto.find_all("Shinei Nouzen walked in.")
    assert len(matches) == 1
    start, end, surface, entity_id = matches[0]
    assert surface == "Shinei Nouzen"


def test_word_boundary_respected():
    """"Shin" must not match inside "Shining"."""
    auto = _make_automaton([("Shin", "shin")])
    assert auto.find_all("The sun was shining brightly.") == []
    assert auto.find_all("Shin walked in.")[0][2] == "Shin"


def test_non_overlapping_matches_for_two_different_entities():
    auto = _make_automaton([("Shin", "shin"), ("Lena", "lena")])
    matches = auto.find_all("Shin and Lena talked.")
    entity_ids = {m[3] for m in matches}
    assert entity_ids == {"shin", "lena"}


def test_build_automaton_records_dropped_ambiguous_surfaces():
    """[24] A literal surface claimed by two entities is now recorded, not just silently kept for
    whichever entity_id sorts first (docs/vision/plans/0008-pre-full-scale-audit.md Sec1.5 item 3)."""
    entities = [
        {"entity_id": "b-entity", "surface_forms": [{"text": "Shared", "ambiguous": True, "first_vol": 1}]},
        {"entity_id": "a-entity", "surface_forms": [{"text": "Shared", "ambiguous": True, "first_vol": 1}]},
    ]
    auto = AU.build_automaton(entities)
    assert auto.dropped_ambiguous_surfaces == [
        {"surface": "Shared", "kept_entity_id": "a-entity", "dropped_entity_id": "b-entity"}
    ]
    # "Shared" still resolves to whichever entity kept it -- unaffected by the new bookkeeping.
    assert auto.find_all("Shared walked in.")[0][3] == "a-entity"


def test_build_automaton_indexes_every_surface_form():
    entities = [
        {
            "entity_id": "shinei-nouzen",
            "surface_forms": [
                {"text": "Shinei Nouzen", "ambiguous": False, "first_vol": 1},
                {"text": "Shin", "ambiguous": False, "first_vol": 1},
                {"text": "Undertaker", "ambiguous": False, "first_vol": 1},
            ],
        }
    ]
    auto = AU.build_automaton(entities)
    matches = auto.find_all("Shin, also known as Undertaker, walked in.")
    entity_ids = {m[3] for m in matches}
    assert entity_ids == {"shinei-nouzen"}
    assert len(matches) == 2  # Shin + Undertaker, distinct spans


def test_index_mentions_reads_parsed_volumes(tmp_path, monkeypatch):
    from narrativewiki import paths

    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    record = {
        "para_id": "v01:c01:p0001",
        "vol": 1,
        "chapter_idx": 1,
        "chapter_id": "c01",
        "chapter_title": "t",
        "chapter_kind": "chapter",
        "seq": 1,
        "text": "Shin walked in.",
        "print_page": None,
        "speech": "narration",
        "is_monologue": False,
        "scene_break_before": "none",
        "n_words": 3,
    }
    (tmp_path / "v01.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")

    auto = _make_automaton([("Shin", "shin")])
    mentions = list(AU.index_mentions(auto, [1, 2]))  # v02 does not exist; must be skipped silently
    assert len(mentions) == 1
    m = mentions[0]
    assert m == {"para_id": "v01:c01:p0001", "vol": 1, "entity_id": "shin", "surface": "Shin", "start": 0, "end": 4}


# ---------------------------------------------------------------------------
# Phase 18 — alias.add_surface_form / gazetteer.merge_epithets
# ---------------------------------------------------------------------------


def _entity(entity_id: str, surfaces: list[tuple[str, int]]) -> dict:
    return {
        "entity_id": entity_id,
        "canonical": entity_id.title(),
        "type": "CHARACTER",
        "aliases": [],
        "surface_forms": [{"text": t, "ambiguous": False, "first_vol": fv} for t, fv in surfaces],
        "first_vol": min((fv for _t, fv in surfaces), default=1),
        "mention_count": 1,
        "confidence": 0.9,
        "notes": "",
    }


def test_add_surface_form_appends_a_new_alias():
    entity = _entity("shin", [("Shin", 1)])
    added = A.add_surface_form(entity, "the reaper", 3)
    assert added is True
    assert {"text": "the reaper", "ambiguous": False, "first_vol": 3,
            "source": "override"} in entity["surface_forms"]
    assert "the reaper" in entity["aliases"]
    assert entity["first_vol"] == 1  # unaffected -- 3 is not earlier than the existing 1


def test_add_surface_form_is_idempotent():
    entity = _entity("shin", [("Shin", 1)])
    A.add_surface_form(entity, "the reaper", 3)
    added_again = A.add_surface_form(entity, "the reaper", 3)
    assert added_again is False
    assert len(entity["surface_forms"]) == 2  # no duplicate row


def _epithet(entity_id: str, text: str, vol: int = 3, confidence: float = 0.8) -> dict:
    return {
        "entity_id": entity_id, "text": text, "vol": vol, "chapter_idx": 0,
        "para_id": f"v{vol:02d}:c00:p0001", "print_page": 1, "quote": f"they called her {text}",
        "confidence": confidence, "source": "test",
    }


def test_merge_epithets_adds_a_new_surface_form_tagged_by_source():
    gaz = {"entities": [_entity("holo", [("Holo", 1)])]}
    G.merge_epithets(gaz, [_epithet("holo", "the Wisewolf")], min_confidence=0.6)
    sf = next(sf for sf in gaz["entities"][0]["surface_forms"] if sf["text"] == "the Wisewolf")
    assert sf["source"] == "epithet_mining"
    assert "the Wisewolf" in gaz["entities"][0]["aliases"]


def test_merge_epithets_skips_below_floor_confidence():
    gaz = {"entities": [_entity("holo", [("Holo", 1)])]}
    G.merge_epithets(gaz, [_epithet("holo", "the Wisewolf", confidence=0.3)], min_confidence=0.6)
    assert "the Wisewolf" not in gaz["entities"][0]["aliases"]


def test_merge_epithets_skips_descriptions():
    """[33] "that girl" / "a great bird" (Diana, v3) matched every v2 "that girl"; only a
    name-like epithet becomes a surface form."""
    gaz = {"entities": [_entity("diana", [("Diana", 3)])]}
    recs = [_epithet("diana", t) for t in ("that girl", "a great bird", "cheeky wolf girl", "the Chronicler")]
    G.merge_epithets(gaz, recs, min_confidence=0.6)
    assert gaz["entities"][0]["aliases"] == ["the Chronicler"]


def test_merge_epithets_skips_an_epithet_the_records_disagree_on():
    """[33] "the Wise King of the Forest": one record says Hamusuke, one says Ainz. Neither gets it;
    a clear majority (3 vs 1) does."""
    gaz = {"entities": [_entity("ainz", [("Ainz", 1)]), _entity("hamusuke", [("Hamusuke", 2)])]}
    G.merge_epithets(gaz, [_epithet("hamusuke", "the Wise King of the Forest"),
                           _epithet("ainz", "The Wise King of the Forest")], min_confidence=0.6)
    assert all("Wise King" not in " ".join(e["aliases"]) for e in gaz["entities"])
    G.merge_epithets(gaz, [_epithet("ainz", "King of Death")] * 3 + [_epithet("hamusuke", "King of Death")], 0.6)
    assert gaz["entities"][0]["aliases"] == ["King of Death"] and gaz["entities"][1]["aliases"] == []


def test_merge_epithets_is_idempotent():
    gaz = {"entities": [_entity("holo", [("Holo", 1)])]}
    G.merge_epithets(gaz, [_epithet("holo", "the Wisewolf")], min_confidence=0.6)
    n_after_first = len(gaz["entities"][0]["surface_forms"])
    G.merge_epithets(gaz, [_epithet("holo", "the Wisewolf")], min_confidence=0.6)
    assert len(gaz["entities"][0]["surface_forms"]) == n_after_first


def test_merge_epithets_marks_a_new_collision_ambiguous():
    """A mined epithet can collide with another entity's EXISTING surface form -- mark_ambiguous
    must rerun over the whole entity list, not just the newly-touched entity."""
    gaz = {
        "entities": [
            _entity("holo", [("Holo", 1)]),
            _entity("lawrence", [("the Merchant", 1)]),
        ]
    }
    G.merge_epithets(gaz, [_epithet("holo", "the Merchant")], min_confidence=0.6)
    holo_sf = next(sf for sf in gaz["entities"][0]["surface_forms"] if sf["text"] == "the Merchant")
    lawrence_sf = next(sf for sf in gaz["entities"][1]["surface_forms"] if sf["text"] == "the Merchant")
    assert holo_sf["ambiguous"] is True
    assert lawrence_sf["ambiguous"] is True


def test_merge_epithets_ignores_a_record_for_an_unknown_entity():
    gaz = {"entities": [_entity("holo", [("Holo", 1)])]}
    G.merge_epithets(gaz, [_epithet("nobody", "the ghost")], min_confidence=0.6)
    assert gaz["entities"][0]["surface_forms"] == [{"text": "Holo", "ambiguous": False, "first_vol": 1}]


def test_surface_inventory_matches_index_ownership_and_preserves_unknown_provenance():
    import copy

    entities = [_entity("b", [("Shared", 2)]), _entity("a", [("Shared", 1), ("", 1)])]
    entities[0]["surface_forms"][0]["source"] = "epithet_mining"
    before = copy.deepcopy(entities)
    rows = AU.surface_inventory(entities)
    assert rows == AU.surface_inventory(list(reversed(entities)))
    assert entities == before
    shared = [r for r in rows if r["text"] == "Shared"]
    assert [(r["entity_id"], r["indexed"], r["index_entity_id"], r["ambiguous"])
            for r in shared] == [("a", True, "a", True), ("b", False, "a", True)]
    assert [r["source"] for r in shared] == ["unknown", "epithet_mining"]
    assert [r["first_vol"] for r in shared] == [1, 2]
    assert rows[0]["indexed"] is False
    assert rows[0]["index_entity_id"] is None
    assert AU.build_automaton(entities).find_all("Shared") == [(0, 6, "Shared", "a")]


def test_cluster_surface_sources_distinguish_original_and_stripped_names():
    classified = [_classified("Captain Holo", "CHARACTER"), _classified("Lawrence", "CHARACTER")]
    entities = A._build_clusters(classified, A._UnionFind(2), ["Captain"], [])
    sources = {sf["text"]: sf["source"] for e in entities for sf in e["surface_forms"]}
    assert sources == {"Holo": "alias_cluster", "Lawrence": "corpus"}


def test_cluster_surface_source_follows_earliest_evidence_and_prefers_raw_on_tie():
    classified = [_classified("Captain Holo", "CHARACTER"), _classified("Holo", "CHARACTER")]
    classified[1]["first_vol"] = 2
    uf = A._UnionFind(2)
    uf.union(0, 1)
    sf = A._build_clusters(classified, uf, ["Captain"], [])[0]["surface_forms"][0]
    assert (sf["first_vol"], sf["source"]) == (1, "alias_cluster")
    classified[1]["first_vol"] = 1
    sf = A._build_clusters(classified, uf, ["Captain"], [])[0]["surface_forms"][0]
    assert sf["source"] == "corpus"


def test_epithet_repeat_does_not_relabel_an_existing_override():
    entity = _entity("holo", [("Holo", 1)])
    A.add_surface_form(entity, "the wisewolf", 1)
    G.merge_epithets({"entities": [entity]}, [_epithet("holo", "the wisewolf", vol=2)], 0.6)
    sf = next(sf for sf in entity["surface_forms"] if sf["text"] == "the wisewolf")
    assert sf["source"] == "override"


def test_existing_surface_moves_to_earlier_evidence_without_duplicating():
    entity = _entity("holo", [("Holo", 1), ("the wisewolf", 2)])
    added = A.add_surface_form(entity, "the wisewolf", 1, source="epithet_mining")
    assert added is False
    assert len(entity["surface_forms"]) == 2
    sf = next(sf for sf in entity["surface_forms"] if sf["text"] == "the wisewolf")
    assert (sf["first_vol"], sf["source"]) == (1, "epithet_mining")
    A.add_surface_form(entity, "the wisewolf", 2, source="override")
    assert (sf["first_vol"], sf["source"]) == (1, "epithet_mining")


def test_out_of_order_epithet_merge_uses_earliest_surface_cutoff():
    gaz = {"entities": [_entity("holo", [("Holo", 1)])]}
    G.merge_epithets(gaz, [_epithet("holo", "the Wisewolf", vol=2)], 0.6)
    G.merge_epithets(gaz, [_epithet("holo", "the Wisewolf", vol=1)], 0.6)
    sf = next(sf for sf in gaz["entities"][0]["surface_forms"] if sf["text"] == "the Wisewolf")
    assert sf["first_vol"] == 1
    assert sf["source"] == "epithet_mining"


@pytest.mark.parametrize("use_c_extension", [False, True])
@pytest.mark.parametrize("entities", [[], [{"entity_id": "empty", "surface_forms": [{"text": ""}]}]])
def test_empty_mention_automaton_matches_nothing_on_both_backends(monkeypatch, use_c_extension, entities):
    if use_c_extension and AU.ahocorasick is None:
        pytest.skip("optional C extension not installed")
    monkeypatch.setattr(AU, "_HAS_PYAHOCORASICK", use_c_extension)
    automaton = AU.build_automaton(entities)
    assert automaton.find_all("A cutoff with no known names.") == []
    assert automaton.find_all("") == []


def test_pronoun_runs_and_bare_honorifics_are_not_candidates():
    """[30] A first-person novel mined "But I"/"If I", and "Mr." tokenised to a bare "Mr"."""
    records = [_record("v01:c01:p0001", "But I said so. If I go, Mr. Holmes and Mr. Watson follow.")] * 3
    surfaces = {c["surface"] for c in C.mine_candidates({1: records}, {"entities": {}}, min_mentions=3)}
    assert {"Holmes", "Watson"} <= surfaces
    assert not surfaces & {"But I", "If I", "Mr"}


def test_a_sentence_initial_conjunction_is_not_part_of_a_name():
    """[31] "But Captain Nemo" became the canonical id `but-captain-nemo`; "The" is an epithet."""
    records = [_record("v01:c01:p0001", "But Captain Nemo spoke. If Ned Land came. The Canadian left.")] * 3
    counts = {c["surface"]: c["count"] for c in C.mine_candidates({1: records}, {"entities": {}}, min_mentions=3)}
    assert {"Captain Nemo", "Ned Land", "The Canadian"} <= set(counts)
    assert not set(counts) & {"But Captain Nemo", "If Ned Land"}
    assert counts["Captain Nemo"] == 3


def test_a_possessive_inside_a_name_is_mined_whole():
    """[30] "Merchant’s Guild" split at the possessive and was only ever mined as "Guild"."""
    records = [_record("v01:c01:p0001", "We went to the Merchant’s Guild today.")] * 3
    surfaces = {c["surface"] for c in C.mine_candidates({1: records}, {"entities": {}}, min_mentions=3)}
    assert "Merchant’s Guild" in surfaces


def test_a_shared_surname_or_given_name_does_not_fuse_two_people():
    """[31] A bare "Cuthbert" is a subset of "Matthew Cuthbert" and "Marilla Cuthbert"; tier-c
    merging it into both fused Matthew and Marilla through union-find. Titles and epithets are
    not evidence of two people: "Aunt Marilla", "Norah the Nymph", "M. Aronnax" still merge."""
    from narrativewiki.entities.alias import _auto_cluster
    from narrativewiki.entities.candidates import DEFAULT_HONORIFICS

    def groups(surfaces):
        cl = [{"surface": s, "type": "CHARACTER", "evidence_para_ids": []} for s in surfaces]
        uf, _n, _p = _auto_cluster(cl, DEFAULT_HONORIFICS)
        out = {}
        for i, c in enumerate(cl):
            out.setdefault(uf.find(i), set()).add(c["surface"])
        return sorted(sorted(g) for g in out.values())

    assert groups(["Matthew Cuthbert", "Marilla Cuthbert", "Cuthbert"]) == [
        ["Cuthbert"], ["Marilla Cuthbert"], ["Matthew Cuthbert"]]
    assert groups(["Marilla", "Aunt Marilla", "Marilla Cuthbert"]) == [["Aunt Marilla", "Marilla", "Marilla Cuthbert"]]
    assert groups(["Norah", "Norah Arendt", "Norah the Nymph"]) == [["Norah", "Norah Arendt", "Norah the Nymph"]]
    assert groups(["Aronnax", "M. Aronnax", "Pierre Aronnax"]) == [["Aronnax", "M. Aronnax", "Pierre Aronnax"]]
