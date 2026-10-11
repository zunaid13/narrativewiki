"""Tests for extract/{windows,schema,claims}.py — Phase 3.

Follows the pattern in test_entities.py: scripted fake LLM clients (never touches Ollama), and
small hand-built paragraph/mention fixtures rather than real corpus data.
"""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import pytest

from narrativewiki.extract import claims as CL
from narrativewiki.extract import resolve as RS
from narrativewiki.extract import schema as SC
from narrativewiki.extract import windows as W
from narrativewiki.llm.budget import estimate_tokens


def test_system_prompt_warns_against_sarcasm_and_lies_as_fact():
    """Phase 25 item 6: reuses the existing "presumed" polarity for a character's own insincere
    (sarcastic/boastful/joking) statement rather than a new schema field -- see the matching
    scenes.py test."""
    settings = SimpleNamespace(attributes={}, relations={}, traits={})
    system = CL._system_prompt(settings)
    assert "sarcasm" in system.lower()
    assert "presumed" in system.lower()

# ---------------------------------------------------------------------------
# windows.py
# ---------------------------------------------------------------------------


def _para(idx: int, vol: int = 1, text: str = "text", scene_break: str = "none") -> dict:
    return {
        "para_id": f"v{vol:02d}:c00:p{idx:04d}",
        "vol": vol,
        "chapter_idx": 0,
        "seq": idx,
        "text": text,
        "print_page": None,
        "scene_break_before": scene_break,
    }


DEFAULT_WINDOW_CFG = {
    "context_paragraphs_before": 2,
    "context_paragraphs_after": 2,
    "never_cross_hard_break": True,
    "max_windows_per_entity_per_volume": 40,
    "max_tokens_per_request": 6000,
    "merge_overlapping": True,
}


def test_build_windows_expands_context_around_a_single_mention():
    records = [_para(i) for i in range(6)]
    windows = W.build_windows("shin", [records[3]["para_id"]], records, DEFAULT_WINDOW_CFG)
    assert len(windows) == 1
    assert windows[0].para_ids == tuple(r["para_id"] for r in records[1:6])  # 3-2 .. 3+2


def test_build_windows_merges_two_nearby_mentions_into_one_window():
    records = [_para(i) for i in range(10)]
    mentions = [records[2]["para_id"], records[4]["para_id"]]
    windows = W.build_windows("shin", mentions, records, DEFAULT_WINDOW_CFG)
    assert len(windows) == 1
    assert windows[0].mention_count == 2


def test_build_windows_keeps_distant_mentions_as_separate_windows():
    records = [_para(i) for i in range(20)]
    mentions = [records[1]["para_id"], records[18]["para_id"]]
    windows = W.build_windows("shin", mentions, records, DEFAULT_WINDOW_CFG)
    assert len(windows) == 2


def test_build_windows_never_crosses_a_hard_break():
    records = [_para(i) for i in range(6)]
    records[3]["scene_break_before"] = "hard"  # break sits between paragraph 2 and 3
    windows = W.build_windows("shin", [records[2]["para_id"]], records, DEFAULT_WINDOW_CFG)
    assert len(windows) == 1
    # context_paragraphs_after=2 would normally reach index 4, but the break at index 3 stops it
    assert windows[0].para_ids[-1] == records[2]["para_id"]


def test_build_windows_respects_token_budget_by_trimming_context_first():
    long_text = "word " * 2000  # comfortably over any small token budget on its own
    records = [_para(i, text=long_text) for i in range(6)]
    tight_cfg = {**DEFAULT_WINDOW_CFG, "max_tokens_per_request": 400}
    windows = W.build_windows("shin", [records[3]["para_id"]], records, tight_cfg)
    assert len(windows) == 1
    # the core mention paragraph must always survive even if context is fully trimmed away
    assert records[3]["para_id"] in windows[0].para_ids


def test_build_windows_caps_windows_per_entity_keeping_the_densest_clusters():
    records = [_para(i) for i in range(200)]
    # ten well-separated single-mention clusters
    mentions = [records[i]["para_id"] for i in range(0, 200, 20)]
    cfg = {**DEFAULT_WINDOW_CFG, "max_windows_per_entity_per_volume": 3}
    windows = W.build_windows("shin", mentions, records, cfg)
    assert len(windows) == 3


def test_build_windows_max_windows_arg_overrides_config_flat_cap():
    records = [_para(i) for i in range(200)]
    mentions = [records[i]["para_id"] for i in range(0, 200, 20)]
    windows = W.build_windows("shin", mentions, records, DEFAULT_WINDOW_CFG, max_windows=2)
    assert len(windows) == 2


def test_build_windows_reports_capped_count_via_drops():
    records = [_para(i) for i in range(200)]
    mentions = [records[i]["para_id"] for i in range(0, 200, 20)]  # 10 clusters
    drops: Counter[str] = Counter()
    W.build_windows("shin", mentions, records, DEFAULT_WINDOW_CFG, max_windows=3, drops=drops)
    assert drops["window_cap_truncated"] == 7


def test_build_windows_no_drops_recorded_when_under_the_cap():
    records = [_para(i) for i in range(10)]
    drops: Counter[str] = Counter()
    W.build_windows("shin", [records[3]["para_id"]], records, DEFAULT_WINDOW_CFG, drops=drops)
    assert drops["window_cap_truncated"] == 0


def test_allocate_window_caps_splits_pool_by_sqrt_mentions():
    # protagonist has 100x the mentions of the minor character
    caps = W.allocate_window_caps({"protagonist": 400, "minor": 4}, base_cap=40, floor=3)
    # pool = 40 * 2 = 80; weights sqrt(400)=20, sqrt(4)=2 -> protagonist gets 80*20/22 ~= 73
    assert caps["protagonist"] > 40  # exceeds the old flat cap, which the flat regime never allowed
    assert caps["minor"] >= 3


def test_allocate_window_caps_floor_protects_low_mention_entities():
    caps = W.allocate_window_caps({"protagonist": 10_000, "cameo": 1}, base_cap=40, floor=3)
    assert caps["cameo"] == 3  # sqrt share would round to 0 without the floor


def test_allocate_window_caps_ignores_zero_mention_entities():
    caps = W.allocate_window_caps({"present": 5, "absent": 0}, base_cap=40, floor=3)
    assert "absent" not in caps


def test_allocate_window_caps_empty_input_returns_empty():
    assert W.allocate_window_caps({}, base_cap=40, floor=3) == {}


# ---------------------------------------------------------------------------
# schema.py
# ---------------------------------------------------------------------------


def test_make_claim_id_is_deterministic_and_content_addressed():
    a = SC.make_claim_id("shinei-nouzen", "AFFILIATED_WITH", "spearhead-squadron", 1)
    b = SC.make_claim_id("shinei-nouzen", "AFFILIATED_WITH", "spearhead-squadron", 1)
    c = SC.make_claim_id("shinei-nouzen", "AFFILIATED_WITH", "nordlicht-squadron", 1)
    presumed = SC.make_claim_id(
        "shinei-nouzen", "AFFILIATED_WITH", "spearhead-squadron", 1, polarity="presumed"
    )
    qualified = SC.make_claim_id(
        "shinei-nouzen", "AFFILIATED_WITH", "spearhead-squadron", 1, qualifier="  Captain "
    )
    same_qualified = SC.make_claim_id(
        "shinei-nouzen", "AFFILIATED_WITH", "spearhead-squadron", 1, qualifier="captain"
    )
    assert a == b
    assert a != c
    assert a != presumed
    assert a != qualified
    assert qualified == same_qualified
    assert a.startswith("c_")


def test_observation_id_is_stable_per_recorded_fact_position():
    first = SC.make_observation_id("spice-and-wolf", "run-1", "cache-1", "0:3")
    same = SC.make_observation_id("spice-and-wolf", "run-1", "cache-1", "0:3")
    next_fact = SC.make_observation_id("spice-and-wolf", "run-1", "cache-1", "0:4")
    assert first == same
    assert first != next_fact
    assert first.startswith("o_")


def test_observation_preserves_source_semantics_and_requires_evidence():
    observation = SC.Observation(
        observation_id="o_123",
        series_id="spice-and-wolf",
        subject="yarei",
        predicate="AFFILIATED_WITH",
        kind="relation",
        object="medio-company",
        qualifier="deeply connected",
        polarity="presumed",
        confidence=0.9,
        disclosure_vol=1,
        chapter_idx=5,
        evidence=SC.Evidence(para_id="v01:c05:p0246", quote="He must be deeply connected."),
        source_stage="claim_extract",
        source_run_id="run-1",
        source_cache_key="cache-1",
        source_fact_index="0:0",
        source_prompt_sha256="a" * 64,
        extraction_source="google:model",
        candidate_assertion_id="c_123",
        legacy_claim_id="c_legacy",
    )
    assert observation.schema_version == SC.OBSERVATION_SCHEMA_VERSION
    assert observation.polarity == "presumed"
    with pytest.raises(Exception):
        SC.Observation.model_validate({**observation.model_dump(), "polarity": "confirmed"})


def test_claim_model_rejects_missing_evidence():
    with pytest.raises(Exception):
        SC.Claim(
            claim_id="c_1", subject="s", predicate="AGE", kind="attribute",
            first_vol=1, chapter_idx=0, evidence=[], confidence=0.9, source="test",
        )


def _raw_fact(**overrides) -> dict:
    fact = {
        "predicate": "AGE", "kind": "attribute", "object": None, "value": "16",
        "qualifier": None, "para_id": "v01:c00:p0001", "quote": "He is sixteen.",
        "confidence": 0.9, "polarity": "asserted",
    }
    fact.update(overrides)
    return fact


def test_extraction_result_coerces_non_string_optional_fields_to_none():
    """Observed against real Ollama output: a 14B model sometimes emits `[]` for a field it
    means to leave empty instead of `null` or omitting it. This must not fail validation."""
    result = SC.ExtractionResult.model_validate({"facts": [_raw_fact(qualifier=[], object={})]})
    assert len(result.facts) == 1
    assert result.facts[0].qualifier is None
    assert result.facts[0].object is None


def test_invalid_polarity_is_quarantined_instead_of_becoming_asserted():
    """Observed against real Ollama output: a 14B model occasionally writes a polarity synonym
    ("true", "confirmed") instead of one of the three closed values."""
    SC.pop_incomplete_fact_drops()
    with pytest.raises(Exception):
        SC.ExtractedFact.model_validate(_raw_fact(polarity="confirmed"))

    result = SC.ExtractionResult.model_validate(
        {"facts": [_raw_fact(), _raw_fact(polarity="confirmed")]}
    )
    assert len(result.facts) == 1
    assert result.facts[0].polarity == "asserted"
    assert SC.pop_incomplete_fact_drops()["invalid_polarity"] == 1


def test_extracted_fact_defaults_confidence_when_omitted():
    """Observed against real Ollama output: a 14B model occasionally omits "confidence" on some
    facts in a list while including it on others in the same response."""
    raw = _raw_fact()
    del raw["confidence"]
    fact = SC.ExtractedFact.model_validate(raw)
    assert fact.confidence == 0.7


@pytest.mark.parametrize(
    "broken",
    [
        {"quote": None},
        {"para_id": ""},
        {"predicate": None},
        {"kind": "not_a_real_kind"},
    ],
)
def test_extraction_result_drops_facts_missing_any_required_field_not_just_para_id(broken):
    """The 14B model was observed omitting a DIFFERENT required field on different retries of the
    same prompt (para_id, then confidence, then quote) -- the filter must catch all of them, not
    just whichever one was seen first."""
    good = _raw_fact()
    bad = _raw_fact(**broken)
    result = SC.ExtractionResult.model_validate({"facts": [good, bad]})
    assert len(result.facts) == 1
    assert result.facts[0].quote == good["quote"]


def test_extraction_result_normalizes_uppercase_kind_instead_of_dropping_the_fact():
    """Phase 22 B2: `claims.py::_lookup_predicate` re-derives the true kind from
    settings.attributes/relations/traits and ignores this field once a claim is built, so a
    cosmetic case mismatch ("RELATION" instead of "relation") must not silently lose an
    otherwise well-formed fact -- `_is_usable_fact`'s `_VALID_KINDS` check is case-sensitive."""
    result = SC.ExtractionResult.model_validate({"facts": [_raw_fact(kind="RELATION")]})
    assert len(result.facts) == 1
    assert result.facts[0].kind == "relation"


def test_extraction_result_drops_facts_missing_para_id_instead_of_failing_the_batch():
    """One malformed fact (no citable para_id) must not sink the other, well-formed facts in the
    same response -- that would waste a repair-retry over a single field."""
    result = SC.ExtractionResult.model_validate(
        {"facts": [_raw_fact(para_id=None), _raw_fact(), {"predicate": "AGE", "kind": "attribute"}]}
    )
    assert len(result.facts) == 1
    assert result.facts[0].para_id == "v01:c00:p0001"


# ---------------------------------------------------------------------------
# resolve.py (Phase 22 B2)
# ---------------------------------------------------------------------------


def test_resolve_surface_exact_match_wins_over_a_longer_containing_candidate():
    candidates = [
        {"surface": "Kraft Lawrence", "entity_id": "kraft-lawrence"},
        {"surface": "Kraft", "entity_id": "kraft-the-blacksmith"},
    ]
    passage = "Kraft Lawrence walked past. Kraft waved back."
    assert RS.resolve_surface("Kraft", candidates, passage) == "kraft-the-blacksmith"


def test_resolve_surface_name_part_resolves_a_bare_first_name_to_the_full_name_entity():
    """Fixes S3: "Kraft" alone, with no candidate of its own, resolves via the whole-word
    name-part rule to the entity whose only known surface is the full name "Kraft Lawrence"."""
    candidates = [{"surface": "Kraft Lawrence", "entity_id": "kraft-lawrence"}]
    passage = "Kraft Lawrence smiled."
    assert RS.resolve_surface("Kraft", candidates, passage) == "kraft-lawrence"


def test_resolve_surface_longest_name_part_candidate_wins_not_first_in_list_order():
    candidates = [
        {"surface": "Kraft Lawrence", "entity_id": "A"},
        {"surface": "Kraft Lawrence the Merchant", "entity_id": "B"},
    ]
    passage = "Kraft Lawrence the Merchant walked in."
    assert RS.resolve_surface("Kraft", candidates, passage) == "B"


def test_resolve_surface_rejects_a_fragment_that_is_not_a_whole_word_of_any_candidate():
    """The old raw-substring fallback would have matched "man" inside "Norman" -- the name-part
    rule requires a whole-word match, not an arbitrary character-offset substring."""
    candidates = [{"surface": "Norman", "entity_id": "norman-the-guard"}]
    assert RS.resolve_surface("man", candidates, "Norman stood guard.") is None


# --- Phase 23 A1 --------------------------------------------------------------------------


def test_resolve_surface_rejects_a_candidate_not_actually_in_the_passage():
    """A candidate the model was shown in its "known entities" header but that never appears in
    the actual passage text must not resolve -- this is what stops a relation object from being
    bound to a name from the prompt header alone."""
    candidates = [{"surface": "Kraft Lawrence", "entity_id": "kraft-lawrence"}]
    assert RS.resolve_surface("Kraft Lawrence", candidates, "The wolf padded through the wheat.") is None


def test_resolve_surface_strips_echoed_also_known_as_label_before_matching():
    """The model sometimes echoes group_known_entities()'s own "Canonical (also: alias)" header
    back as an "object" instead of copying a name from the passage -- the shape seen in the false
    "Kraft Lawrence, Spouse of Marheit" relation (Phase 23 A1). Stripping the formatting must
    still resolve the real entity the label names, when that name genuinely appears in the
    passage: it is not resolve_surface's job to blanket-reject anything label-shaped (that would
    also break correct resolution of a real, passage-present name) -- the actual defense against
    an unsupported fact is the evidence-adequacy gate (extract/adequacy.py, Phase 23 A2), which
    checks the *cited paragraph*, not the whole window, for both endpoints."""
    candidates = [{"surface": "Lawrence", "entity_id": "kraft-lawrence"}]
    passage = "Lawrence wiped the sweat from his brow."
    assert RS.resolve_surface("Lawrence Kraft (also: Lawrence)", candidates, passage) == "kraft-lawrence"
    assert RS.resolve_surface("Lawrence (also: Lawrence)", candidates, passage) == "kraft-lawrence"


def test_resolve_surface_returns_none_on_a_genuine_tie_between_distinct_entities():
    """A name collision (two distinct entities with an equally-specific matching surface) must be
    silently-lost, not silently-guessed. Previously `len(surface) > best[0]` (strict) let list
    order break the tie, binding to whichever candidate happened to appear first."""
    candidates = [
        {"surface": "Nouzen", "entity_id": "shinei-nouzen"},
        {"surface": "Nouzen", "entity_id": "rei-nouzen"},
    ]
    assert RS.resolve_surface("Nouzen", candidates, "Nouzen turned to leave.") is None


def test_resolve_surface_same_entity_under_multiple_surfaces_is_not_a_tie():
    candidates = [
        {"surface": "Lawrence", "entity_id": "kraft-lawrence"},
        {"surface": "Kraft Lawrence", "entity_id": "kraft-lawrence"},
    ]
    passage = "Kraft Lawrence walked in. Lawrence smiled."
    assert RS.resolve_surface("Lawrence", candidates, passage) == "kraft-lawrence"


def test_group_known_entities_groups_aliases_under_the_canonical_name():
    entities_by_id = {
        "kraft-lawrence": {
            "entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence",
            "aliases": ["Kraft Lawrence", "Lawrence", "Kraft"],
        },
    }
    assert RS.group_known_entities(["kraft-lawrence"], entities_by_id) == "Kraft Lawrence (also: Kraft, Lawrence)"


def test_group_known_entities_omits_the_also_clause_when_there_are_no_other_aliases():
    entities_by_id = {"holo": {"entity_id": "holo", "canonical": "Holo", "aliases": ["Holo"]}}
    assert RS.group_known_entities(["holo"], entities_by_id) == "Holo"


def test_group_known_entities_empty_input_returns_empty_string():
    assert RS.group_known_entities([], {}) == ""


# ---------------------------------------------------------------------------
# claims.py
# ---------------------------------------------------------------------------

ATTRIBUTES = {"AGE": {"single": True, "format": "number_or_range", "display": "Age"}}
RELATIONS = {
    "AFFILIATED_WITH": {"object_types": ["FACTION"], "display": "Affiliation"},
    "SIBLING_OF": {"symmetric": True, "display": "Sibling of"},
}
TRAITS = {"PERSONALITY": {"display": "Personality", "max_words": 6}}


class FakeSettings:
    attributes = ATTRIBUTES
    relations = RELATIONS
    traits = TRAITS
    extraction_behaviour = {
        "window": DEFAULT_WINDOW_CFG,
        "confidence": {"min_to_keep": 0.5},
        "max_quote_chars": 240,
        "drop_unresolved_entities": True,
    }


ENTITY = {"entity_id": "shinei-nouzen", "canonical": "Shinei Nouzen", "aliases": ["Shin"]}
ENTITIES_BY_ID = {
    "shinei-nouzen": {"entity_id": "shinei-nouzen", "canonical": "Shinei Nouzen", "type": "CHARACTER"},
    "spearhead-squadron": {"entity_id": "spearhead-squadron", "canonical": "Spearhead Squadron", "type": "FACTION"},
    "raiden-shuga": {"entity_id": "raiden-shuga", "canonical": "Raiden Shuga", "type": "CHARACTER"},
}

_QUOTE = "Shin is the captain of the Spearhead Squadron."
RECORDS = [
    {"para_id": "v01:c00:p0000", "vol": 1, "chapter_idx": 0, "text": "Context before.",
     "print_page": 1, "scene_break_before": "none"},
    {"para_id": "v01:c00:p0001", "vol": 1, "chapter_idx": 0, "text": _QUOTE,
     "print_page": 1, "scene_break_before": "none"},
    {"para_id": "v01:c00:p0002", "vol": 1, "chapter_idx": 0, "text": "Context after. Raiden waited outside.",
     "print_page": 1, "scene_break_before": "none"},
]
MENTIONS = [
    {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin", "start": 0, "end": 4},
    {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "spearhead-squadron", "surface": "Spearhead Squadron",
     "start": 24, "end": 43},
    # Phase 23 A1: "Raiden" must actually appear somewhere in the window text (resolve_surface now
    # requires a candidate's surface to occur in the passage it was shown, not just be named as a
    # mention record) -- placed in the neighbouring paragraph, inside the same 5-para window.
    {"para_id": "v01:c00:p0002", "vol": 1, "entity_id": "raiden-shuga", "surface": "Raiden", "start": 15, "end": 21},
]


class _ScriptedExtractClient:
    """Returns the next scripted fact list on each call, in order. `profile_for` is duck-typed
    to what claims.py needs to stamp `source` — never a real LLMClient."""

    def __init__(self, facts_by_call: list[list[dict]]):
        self.facts_by_call = facts_by_call
        self.calls = 0

    def complete_json(self, stage, prompt, schema, system=None, options=None):
        facts = self.facts_by_call[self.calls]
        self.calls += 1
        return schema(facts=facts)

    def profile_for(self, stage):
        return "ollama:test-model"


def _relation_fact(**overrides) -> dict:
    fact = {
        "predicate": "AFFILIATED_WITH", "kind": "relation", "object": "Spearhead Squadron",
        "value": None, "qualifier": "captain", "para_id": "v01:c00:p0001",
        "quote": _QUOTE, "confidence": 0.9, "polarity": "asserted",
    }
    fact.update(overrides)
    return fact


def test_relation_claim_resolves_object_from_window_mentions_only():
    client = _ScriptedExtractClient([[_relation_fact()]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert len(claims) == 1
    claim = claims[0]
    assert claim["subject"] == "shinei-nouzen"
    assert claim["predicate"] == "AFFILIATED_WITH"
    assert claim["kind"] == "relation"
    assert claim["object"] == "spearhead-squadron"
    assert claim["qualifier"] == "captain"
    assert claim["first_vol"] == 1
    assert claim["evidence"][0]["quote"] == _QUOTE
    assert not drops


def test_relation_object_not_mentioned_in_window_is_dropped():
    client = _ScriptedExtractClient([[_relation_fact(object="Someone Never Named")]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert claims == []
    assert drops["unresolved_object"] == 1


def test_relation_object_type_mismatch_is_dropped():
    """AFFILIATED_WITH requires object_types=[FACTION]; "Raiden" resolves to a CHARACTER."""
    client = _ScriptedExtractClient([[_relation_fact(object="Raiden")]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert claims == []
    assert drops["object_type_mismatch"] == 1


def test_nonverbatim_quote_is_dropped():
    client = _ScriptedExtractClient([[_relation_fact(quote="This sentence is not in the paragraph.")]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert claims == []
    assert drops["quote_not_verbatim"] == 1


def test_quote_wrapped_in_extra_straight_quotes_is_recovered():
    """Observed against real Ollama output: the model sometimes wraps an otherwise-verbatim
    excerpt in its own straight '"' pair on top of the corpus's curly dialogue quotes, which
    would otherwise make a genuine quote fail the verbatim check."""
    client = _ScriptedExtractClient([[_relation_fact(quote=f'"{_QUOTE}"')]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert len(claims) == 1
    assert claims[0]["evidence"][0]["quote"] == _QUOTE
    assert not drops


def test_para_id_missing_zero_padding_is_repaired_against_the_window():
    """Observed against real Ollama output: the model often retypes "v01:c00:p0001" as
    "v01:c00:p1", dropping the zero-padding. Since the repaired id must already be one of the
    window's own real paragraphs, this is a safe repair, not a guess."""
    client = _ScriptedExtractClient([[_relation_fact(para_id="v01:c00:p1")]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert len(claims) == 1
    assert claims[0]["evidence"][0]["para_id"] == "v01:c00:p0001"
    assert not drops


def test_low_confidence_fact_is_dropped():
    client = _ScriptedExtractClient([[_relation_fact(confidence=0.2)]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert claims == []
    assert drops["low_confidence"] == 1


def test_unknown_predicate_is_dropped_not_invented():
    client = _ScriptedExtractClient([[_relation_fact(predicate="MADE_UP_PREDICATE")]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert claims == []
    assert drops["unknown_predicate"] == 1


def test_attribute_fact_uses_value_not_object():
    fact = {
        "predicate": "AGE", "kind": "attribute", "object": None, "value": "16",
        "qualifier": None, "para_id": "v01:c00:p0001", "quote": _QUOTE,
        "confidence": 0.95, "polarity": "asserted",
    }
    client = _ScriptedExtractClient([[fact]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert len(claims) == 1
    claim = claims[0]
    assert claim["kind"] == "attribute"
    assert claim["value"] == "16"
    assert claim["object"] is None
    assert not drops


def test_citation_outside_window_is_dropped():
    """A model that cites a para_id never included in the window it was given is hallucinating
    its own evidence, not the passage's."""
    fact = _relation_fact(para_id="v01:c00:p9999")
    client = _ScriptedExtractClient([[fact]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, RECORDS, MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert claims == []
    assert drops["citation_outside_window"] == 1


def test_repeated_fact_across_two_windows_merges_evidence_not_duplicates():
    """Two mention clusters far enough apart to form separate windows, each independently
    reporting the same AGE fact -- the driver must merge them into one claim by claim_id."""
    records = [_para(i) for i in range(30)]
    records[0]["text"] = "Shin is sixteen."
    records[25]["text"] = "Shin was born sixteen years ago."
    mentions = [
        {"para_id": records[0]["para_id"], "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin", "start": 0, "end": 4},
        {"para_id": records[25]["para_id"], "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin", "start": 0, "end": 4},
    ]
    fact_1 = {
        "predicate": "AGE", "kind": "attribute", "object": None, "value": "16",
        "qualifier": None, "para_id": records[0]["para_id"], "quote": "Shin is sixteen.",
        "confidence": 0.7, "polarity": "asserted",
    }
    fact_2 = {**fact_1, "para_id": records[25]["para_id"], "quote": "Shin was born sixteen years ago.", "confidence": 0.9}
    client = _ScriptedExtractClient([[fact_1], [fact_2]])
    claims, drops = CL.extract_character_volume(ENTITY, 1, records, mentions, ENTITIES_BY_ID, FakeSettings(), client)
    assert client.calls == 2
    assert len(claims) == 1
    claim = claims[0]
    assert len(claim["evidence"]) == 2
    assert claim["confidence"] == 0.9  # max of the two
    assert not drops


def test_combined_claim_merge_keeps_opposite_polarity_and_qualifier_separate():
    from narrativewiki.cli import _merge_claims_by_id

    base = {
        "claim_id": "c_legacy_collision", "subject": "shinei-nouzen", "predicate": "AGE",
        "kind": "attribute", "object": None, "value": "16", "first_vol": 1,
        "chapter_idx": 0, "confidence": 0.9, "source": "test",
    }
    merged = _merge_claims_by_id([
        {**base, "qualifier": "report A", "polarity": "asserted",
         "evidence": [{"para_id": "v01:c00:p0001", "quote": "asserted report"}]},
        {**base, "qualifier": "report B", "polarity": "presumed",
         "evidence": [{"para_id": "v01:c00:p0002", "quote": "uncertain report"}]},
    ])

    assert len(merged) == 2
    assert len({claim["claim_id"] for claim in merged}) == 2
    assert {(claim["polarity"], claim["qualifier"]) for claim in merged} == {
        ("asserted", "report A"), ("presumed", "report B"),
    }


def test_user_prompt_groups_two_alias_mentions_of_one_entity_into_one_name():
    """Phase 22 B2 (fixes S3): `window_mentions` can carry two separate rows for the SAME other
    entity, one per alias surface the automaton matched ("Lawrence" and "Kraft" both indexing to
    entity_id "kraft-lawrence"). The old flat `{surface for m in window_mentions}` set rendered
    these as two apparently-different people -- exactly what let a beat_summary hallucinate a
    transaction between "Lawrence" and "Kraft Lawrence"."""
    window = W.Window(entity_id="shinei-nouzen", vol=1, para_ids=("v01:c00:p0001",), text=_QUOTE, mention_count=1)
    window_mentions = [
        {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "kraft-lawrence", "surface": "Lawrence"},
        {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "kraft-lawrence", "surface": "Kraft"},
    ]
    entities_by_id = {
        **ENTITIES_BY_ID,
        "kraft-lawrence": {
            "entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence",
            "aliases": ["Kraft Lawrence", "Lawrence", "Kraft"], "type": "CHARACTER",
        },
    }
    prompt = CL._user_prompt(ENTITY, 1, window, window_mentions, entities_by_id)
    assert "Kraft Lawrence (also: Kraft, Lawrence)" in prompt
    assert prompt.count("Kraft") == 2  # once in the canonical name, once in the "also" clause -- never as a lone entry


def test_extract_volume_gives_denser_entity_a_larger_window_cap(monkeypatch):
    captured: dict[str, int | None] = {}

    def fake_build_windows(entity_id, para_ids, records, window_cfg, max_windows=None, drops=None):
        captured[entity_id] = max_windows
        return []

    monkeypatch.setattr(CL, "build_windows", fake_build_windows)
    entity_b = {"entity_id": "raiden-shuga", "canonical": "Raiden Shuga", "aliases": []}
    dense_mentions = MENTIONS + [
        {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin", "start": 0, "end": 4}
        for _ in range(50)
    ]
    client = _ScriptedExtractClient([[], []])
    CL.extract_volume(
        [ENTITY, entity_b], 1, RECORDS, dense_mentions, list(ENTITIES_BY_ID.values()), FakeSettings(), client
    )
    assert captured["shinei-nouzen"] > captured["raiden-shuga"]
    assert captured["raiden-shuga"] >= 3  # floor


def test_extract_volume_aggregates_claims_and_drops_across_characters():
    entity_b = {"entity_id": "raiden-shuga", "canonical": "Raiden Shuga", "aliases": []}
    client = _ScriptedExtractClient([[_relation_fact()], [_relation_fact(predicate="MADE_UP")]])
    progress_calls = []
    claims, drops = CL.extract_volume(
        [ENTITY, entity_b], 1, RECORDS, MENTIONS, list(ENTITIES_BY_ID.values()), FakeSettings(), client,
        on_progress=lambda i, total, entity, n: progress_calls.append((i, total, entity["entity_id"], n)),
    )
    assert len(claims) == 1
    assert drops["unknown_predicate"] == 1
    assert progress_calls == [(1, 2, "shinei-nouzen", 1), (2, 2, "raiden-shuga", 0)]


class _ContextCheckedClient:
    def __init__(self, context_limit=None):
        self.options = {} if context_limit is None else {"num_ctx": context_limit}
        self.requests = []

    def profile_for(self, stage):
        return SimpleNamespace(options=self.options)

    def complete_json(self, stage, prompt, schema, system=None, options=None):
        if "num_ctx" in self.options:
            assert estimate_tokens(system + "\n" + prompt) + options["num_predict"] + 256 <= self.options["num_ctx"]
        self.requests.append(prompt)
        # Return one supported fact for each paragraph actually sent to this call.
        facts = []
        for line in prompt.splitlines():
            if line.startswith("[v01:"):
                facts.append({
                    "predicate": "AGE", "kind": "attribute", "value": "16",
                    "object": None, "qualifier": None, "para_id": line[1:line.index("]")],
                    "quote": "Shin is sixteen years old.", "confidence": 0.9,
                    "polarity": "asserted",
                })
        return schema(facts=facts)


def _context_records(count=4, repetitions=300):
    records = [_para(i, text="Shin is sixteen years old. " + "word " * repetitions) for i in range(count)]
    mentions = [{"para_id": r["para_id"], "entity_id": ENTITY["entity_id"]} for r in records]
    return records, mentions


def test_claim_context_splits_preserve_paragraphs_and_evidence():
    records, mentions = _context_records()
    client = _ContextCheckedClient(9100)
    claims, drops = CL.extract_character_volume(
        ENTITY, 1, records, mentions, ENTITIES_BY_ID, FakeSettings(), client, system="Extract facts."
    )
    assert len(client.requests) == 4
    assert drops == {"context_window_split": 3}
    assert len(claims) == 1
    assert {ev["para_id"] for ev in claims[0]["evidence"]} == {r["para_id"] for r in records}
    for record in records:
        assert sum(f'[{record["para_id"]}] {record["text"]}' in request for request in client.requests) == 1


def test_claim_context_unsendable_paragraph_is_counted_without_call():
    records, mentions = _context_records(count=1, repetitions=3000)
    client = _ContextCheckedClient(9100)
    claims, drops = CL.extract_character_volume(
        ENTITY, 1, records, mentions, ENTITIES_BY_ID, FakeSettings(), client, system="Extract facts."
    )
    assert not client.requests
    assert not claims
    assert drops == {"context_window_overflow": 1}


def test_claim_context_accounts_for_system_and_entity_metadata():
    records, mentions = _context_records(count=1, repetitions=0)
    client = _ContextCheckedClient(9100)
    entity = {**ENTITY, "aliases": ["an extremely long alias " * 120]}
    claims, drops = CL.extract_character_volume(
        entity, 1, records, mentions, ENTITIES_BY_ID, FakeSettings(), client, system="Extract facts."
    )
    assert not client.requests
    assert drops == {"context_window_overflow": 1}
    client = _ContextCheckedClient(9100)
    CL.extract_character_volume(
        ENTITY, 1, records, mentions, ENTITIES_BY_ID, FakeSettings(), client, system="instructions " * 300
    )
    assert not client.requests


def test_claim_context_without_declared_limit_preserves_existing_requests():
    records, mentions = _context_records()
    client = _ContextCheckedClient()
    claims, drops = CL.extract_character_volume(
        ENTITY, 1, records, mentions, ENTITIES_BY_ID, FakeSettings(), client, system="Extract facts."
    )
    assert len(client.requests) == 1
    assert len(claims[0]["evidence"]) == 4
    assert not drops


def test_claim_context_overflow_does_not_discard_a_fitting_sibling():
    records, mentions = _context_records(count=2, repetitions=0)
    records[0]["text"] += "word " * 3000
    client = _ContextCheckedClient(9100)
    claims, drops = CL.extract_character_volume(
        ENTITY, 1, records, mentions, ENTITIES_BY_ID, FakeSettings(), client, system="Extract facts."
    )
    assert len(client.requests) == 1
    assert drops == {"context_window_split": 1, "context_window_overflow": 1}
    assert [ev["para_id"] for ev in claims[0]["evidence"]] == [records[1]["para_id"]]


# ---------------------------------------------------------------------------
# Phase 26 part C — packing several windows into one request
# ---------------------------------------------------------------------------


def _win(*para_ids, text="word " * 100):
    from narrativewiki.extract.windows import Window

    return Window(entity_id="holo", vol=1, para_ids=tuple(para_ids), text=text, mention_count=1)


def test_pack_windows_is_the_identity_when_packing_is_off():
    """`max_windows_per_request: 1` is the pre-Phase-26C behaviour and must stay byte-identical:
    one call per window, no separator inserted into any prompt."""
    from narrativewiki.extract.windows import pack_windows

    windows = [_win("p1"), _win("p2"), _win("p3")]
    assert pack_windows(windows, 100_000, 0, 1) == windows


def test_pack_windows_groups_up_to_the_per_request_cap():
    from narrativewiki.extract.windows import PASSAGE_BREAK, pack_windows

    packed = pack_windows([_win(f"p{i}") for i in range(9)], 100_000, 0, 4)
    assert [len(w.para_ids) for w in packed] == [4, 4, 1]
    assert packed[0].para_ids == ("p0", "p1", "p2", "p3")
    assert packed[0].text.count(PASSAGE_BREAK) == 3
    assert packed[0].mention_count == 4


def test_pack_windows_respects_the_token_budget_before_the_count_cap():
    """The count cap is about the OUTPUT limit; the token budget is the input side, and whichever
    binds first wins."""
    from narrativewiki.extract.windows import pack_windows
    from narrativewiki.llm.budget import estimate_tokens

    one = _win("p0")
    budget = estimate_tokens(one.text) * 2 + 5  # room for two, never four
    packed = pack_windows([_win(f"p{i}") for i in range(4)], budget, 0, 4)
    assert [len(w.para_ids) for w in packed] == [2, 2]


def test_pack_windows_counts_the_prompt_overhead_against_every_request():
    """The system prompt is ~2.2k tokens and is re-sent with each request, so it has to come out
    of each batch's budget, not just the first."""
    from narrativewiki.extract.windows import pack_windows
    from narrativewiki.llm.budget import estimate_tokens

    one = _win("p0")
    per_window = estimate_tokens(one.text)
    packed = pack_windows([_win(f"p{i}") for i in range(4)], per_window * 3, per_window, 4)
    assert [len(w.para_ids) for w in packed] == [2, 2]


def test_a_window_bigger_than_the_whole_budget_is_passed_through_untouched():
    """`claims.py`'s context-overflow splitter owns that case -- packing must not silently drop
    an evidence window it cannot fit."""
    from narrativewiki.extract.windows import pack_windows

    big = _win("p0", text="word " * 10_000)
    packed = pack_windows([big, _win("p1")], 100, 0, 4)
    assert [w.para_ids for w in packed] == [("p0",), ("p1",)]


def test_window_pool_is_sized_over_all_characters_not_the_targeted_subset(monkeypatch):
    """`extract --entities "Holo"` narrows `characters`, and the pool used to be sized over that
    filtered list -- `allocate_window_caps` sets `total_pool = base_cap * len(mention_counts)`,
    so targeting one character collapsed the pool to fit it. Measured on the real corpus
    2026-09-21: Holo's cap was 105 (v1) / 116 (v2) in a full run and 40 under
    `--entities "Holo"`, discarding 36 evidence windows before the model saw them, which
    inverted the very remedy `wiki audit eval` recommends for low recall."""
    captured: dict[str, int | None] = {}

    def fake_build_windows(entity_id, para_ids, records, window_cfg, max_windows=None, drops=None):
        captured[entity_id] = max_windows
        return []

    monkeypatch.setattr(CL, "build_windows", fake_build_windows)
    entity_b = {"entity_id": "raiden-shuga", "canonical": "Raiden Shuga", "aliases": []}
    dense_mentions = MENTIONS + [
        {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin", "start": 0, "end": 4}
        for _ in range(50)
    ]
    all_entities = list(ENTITIES_BY_ID.values())

    CL.extract_volume([ENTITY, entity_b], 1, RECORDS, dense_mentions, all_entities,
                      FakeSettings(), _ScriptedExtractClient([[], []]))
    full_run_cap = captured["shinei-nouzen"]

    captured.clear()
    # the targeted top-up: ONE character in `characters`, the whole cast still in `all_entities`
    CL.extract_volume([ENTITY], 1, RECORDS, dense_mentions, all_entities,
                      FakeSettings(), _ScriptedExtractClient([[]]))
    assert captured["shinei-nouzen"] == full_run_cap, (
        "a targeted re-extract must give the character the same evidence budget as a full run"
    )


def test_a_dense_cluster_is_tiled_into_windows_that_fit_the_budget():
    """[34] C35: a protagonist named in every paragraph made one cluster per chapter, kept as ONE
    window however long its core (Anne's reached 77,699 tokens). Tiled, every window fits the budget
    and every mention paragraph is still inside one."""
    from narrativewiki.llm.budget import estimate_tokens

    records = [_para(i, text="Anne walked on and thought about many things. " * 40) for i in range(60)]
    mentions = [r["para_id"] for r in records]
    cfg = dict(DEFAULT_WINDOW_CFG, max_tokens_per_request=3000)
    windows = W.build_windows("anne", mentions, records, cfg, max_windows=10**6)
    assert len(windows) > 1
    assert all(estimate_tokens(w.text) <= 3000 for w in windows)
    assert {p for w in windows for p in w.para_ids} >= set(mentions)
