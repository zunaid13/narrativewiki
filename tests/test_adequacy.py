"""Phase 23 A2/C5: extract/adequacy.py's evidence-adequacy gate, plus integration-level tests
replaying the real failure shapes found in the Phase 23 audit against extract/claims.py and
extract/scenes.py directly -- these are the first tests in the repo that assert an extracted
relation is WRONG and must be dropped, not merely that plumbing (quotes, cutoffs, dedup) works.
"""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import pytest

import narrativewiki.extract.claims as CL
from narrativewiki.extract.adequacy import passes_evidence_adequacy


@pytest.mark.parametrize("radius", [0, 1, 3])
def test_extraction_prompts_match_configured_subject_neighbourhood(radius):
    from narrativewiki.extract.adequacy import neighbourhood_text
    from narrativewiki.extract.scenes import _detail_system_prompt

    behaviour = {"evidence_adequacy": {
        "subject_must_be_named": True, "subject_named_within_paragraphs": radius,
    }}
    settings = SimpleNamespace(extraction_behaviour=behaviour, attributes={}, relations={}, traits={})
    records = {
        "v01:c01:p0000": {"text": "Lawrence entered the room."},
        "v01:c01:p0001": {"text": "He was a travelling merchant by trade."},
    }
    pid = "v01:c01:p0001"
    accepted = passes_evidence_adequacy(
        subject_entity={"canonical": "Lawrence"}, object_entity=None,
        true_kind="attribute", predicate_spec={}, paragraph_text=records[pid]["text"],
        quote=records[pid]["text"], behaviour=behaviour, drops=Counter(),
        subject_context_text=neighbourhood_text(pid, list(records), records, radius),
    )
    assert accepted is (radius > 0)
    for build in (CL._system_prompt, _detail_system_prompt):
        prompt = build(settings)
        if radius:
            assert f"within {radius} paragraph(s) before or after" in prompt
            assert "Cite and quote the paragraph that actually states the fact" in prompt
            assert "paragraph you cite MUST contain" not in prompt
        else:
            assert "paragraph you cite MUST contain" in prompt
        assert "paragraph you CITE for it must still name them" not in prompt


def test_disabled_subject_gate_does_not_require_names_in_prompt():
    from narrativewiki.extract.adequacy import prompt_rules
    settings = SimpleNamespace(extraction_behaviour={"evidence_adequacy": {
        "subject_must_be_named": False, "subject_named_within_paragraphs": 2,
    }}, relations={})
    assert prompt_rules(settings) == ""

DEFAULT_WINDOW_CFG = {
    "context_paragraphs_before": 2,
    "context_paragraphs_after": 2,
    "never_cross_hard_break": True,
    "max_windows_per_entity_per_volume": 40,
    "max_tokens_per_request": 6000,
    "merge_overlapping": True,
}

MARHEIT = {"entity_id": "marheit", "canonical": "Marheit", "aliases": []}
LAWRENCE = {"entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence", "aliases": ["Lawrence"]}

BEHAVIOUR = {
    "evidence_adequacy": {"min_quote_words": 6, "subject_must_be_named": True},
}


# --- unit tests: passes_evidence_adequacy -----------------------------------------------------


def test_quote_too_short_is_rejected_regardless_of_kind():
    drops = Counter()
    ok = passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=None, true_kind="trait",
        predicate_spec={}, paragraph_text="Kraft Lawrence said, \"Fall back.\"",
        quote="Fall back.", behaviour=BEHAVIOUR, drops=drops,
    )
    assert ok is False
    assert drops["quote_too_short"] == 1


def test_long_enough_quote_with_named_subject_passes_with_no_relation_spec():
    drops = Counter()
    ok = passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=None, true_kind="trait",
        predicate_spec={}, paragraph_text="Kraft Lawrence was tired but kept walking anyway.",
        quote="Kraft Lawrence was tired but kept walking anyway.", behaviour=BEHAVIOUR, drops=drops,
    )
    assert ok is True
    assert sum(drops.values()) == 0


def test_subject_not_named_in_the_cited_paragraph_is_rejected():
    """A general guard: the subject's own name must appear in the specific paragraph cited, not
    merely be inferable from context outside it."""
    drops = Counter()
    ok = passes_evidence_adequacy(
        subject_entity=MARHEIT, object_entity=None, true_kind="trait",
        predicate_spec={}, paragraph_text="He wiped the sweat from his brow and kept walking.",
        quote="He wiped the sweat from his brow and kept walking.", behaviour=BEHAVIOUR, drops=drops,
    )
    assert ok is False
    assert drops["subject_not_named_in_paragraph"] == 1


def test_requires_both_endpoints_rejects_the_real_marheit_lawrence_spouse_paragraph():
    """The exact paragraph (v01:c04:p0382) that produced the false SPOUSE_OF claim: it names
    Marheit (the subject) but never Lawrence (the object) -- Lawrence is the speaker, unnamed in
    his own line."""
    drops = Counter()
    paragraph = (
        "I don't want to think about it, but that same partner may have been captured. "
        "Would it be possible for me to speak with the branch manager, Sir Marheit?"
    )
    ok = passes_evidence_adequacy(
        subject_entity=MARHEIT, object_entity=LAWRENCE, true_kind="relation",
        predicate_spec={"symmetric": True, "requires_both_endpoints": True},
        paragraph_text=paragraph, quote=paragraph, behaviour=BEHAVIOUR, drops=drops,
    )
    assert ok is False
    assert drops["endpoint_not_named_in_paragraph"] == 1


def test_requires_both_endpoints_passes_when_a_paragraph_names_both():
    drops = Counter()
    paragraph = "Marheit smiled warmly at Kraft Lawrence, glad to see an old friend."
    ok = passes_evidence_adequacy(
        subject_entity=MARHEIT, object_entity=LAWRENCE, true_kind="relation",
        predicate_spec={"symmetric": True, "requires_both_endpoints": True},
        paragraph_text=paragraph, quote=paragraph, behaviour=BEHAVIOUR, drops=drops,
    )
    assert ok is True


def test_requires_both_endpoints_is_a_no_op_for_a_predicate_that_does_not_declare_it():
    """FRIEND_OF (no requires_both_endpoints) only needs the subject named -- the object may be
    established by context, not necessarily this exact paragraph."""
    drops = Counter()
    paragraph = "Kraft Lawrence trusted him more than anyone else on the road."
    ok = passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=MARHEIT, true_kind="relation",
        predicate_spec={"symmetric": True}, paragraph_text=paragraph, quote=paragraph,
        behaviour=BEHAVIOUR, drops=drops,
    )
    assert ok is True


def test_object_entity_none_with_requires_both_endpoints_is_rejected():
    drops = Counter()
    ok = passes_evidence_adequacy(
        subject_entity=MARHEIT, object_entity=None, true_kind="relation",
        predicate_spec={"requires_both_endpoints": True},
        paragraph_text="Marheit nodded slowly, considering the offer at length.",
        quote="Marheit nodded slowly, considering the offer at length.",
        behaviour=BEHAVIOUR, drops=drops,
    )
    assert ok is False
    assert drops["endpoint_not_named_in_paragraph"] == 1


# --- integration: extract/claims.py replaying the real spouse-claim shape ---------------------

ENTITIES_BY_ID = {
    "marheit": MARHEIT,
    "kraft-lawrence": LAWRENCE,
}
RELATIONS = {
    "SPOUSE_OF": {"symmetric": True, "display": "Spouse of", "requires_both_endpoints": True},
    "FRIEND_OF": {"symmetric": True, "display": "Friend of"},
}


class _ScriptedExtractClient:
    def __init__(self, facts_by_call):
        self.facts_by_call = facts_by_call
        self.calls = 0

    def complete_json(self, stage, prompt, schema, system=None, options=None):
        facts = self.facts_by_call[self.calls]
        self.calls += 1
        return schema(facts=facts)

    def profile_for(self, stage):
        return "ollama:test-model"


class _FakeSettings:
    attributes = {}
    relations = RELATIONS
    traits = {}
    extraction_behaviour = {
        "window": DEFAULT_WINDOW_CFG,
        "confidence": {"min_to_keep": 0.5},
        "max_quote_chars": 400,
        "drop_unresolved_entities": True,
        "evidence_adequacy": {"min_quote_words": 6, "subject_must_be_named": True},
    }


def test_claims_driver_drops_the_real_marheit_lawrence_spouse_claim():
    """End-to-end replay of the actual bug: subject=Marheit, a window that also mentions
    Lawrence two paragraphs away, and a fact whose cited paragraph/quote is Lawrence's own line
    about Holo -- never naming Lawrence himself. Must be dropped, not rendered."""
    quote = (
        "I don't want to think about it, but that same partner may have been captured. "
        "Would it be possible for me to speak with the branch manager, Sir Marheit?"
    )
    records = [
        {"para_id": "v01:c04:p0380", "vol": 1, "chapter_idx": 4,
         "text": "Lawrence wiped the sweat from his forehead and smiled. \"It's my partner that's the reckless one.\"",
         "print_page": 38, "scene_break_before": "none"},
        {"para_id": "v01:c04:p0381", "vol": 1, "chapter_idx": 4, "text": "\"Must be rough.\"",
         "print_page": 38, "scene_break_before": "none"},
        {"para_id": "v01:c04:p0382", "vol": 1, "chapter_idx": 4, "text": quote,
         "print_page": 38, "scene_break_before": "none"},
        {"para_id": "v01:c04:p0383", "vol": 1, "chapter_idx": 4,
         "text": "\"We're a foreign company. Raids and arson are a fact of life for us,\" said the man.",
         "print_page": 38, "scene_break_before": "none"},
        {"para_id": "v01:c04:p0384", "vol": 1, "chapter_idx": 4,
         "text": "It drove home to Lawrence how formidable the man who ran this operation must be.",
         "print_page": 38, "scene_break_before": "none"},
    ]
    mentions = [
        {"para_id": "v01:c04:p0380", "vol": 1, "entity_id": "kraft-lawrence", "surface": "Lawrence"},
        {"para_id": "v01:c04:p0382", "vol": 1, "entity_id": "marheit", "surface": "Marheit"},
        {"para_id": "v01:c04:p0384", "vol": 1, "entity_id": "kraft-lawrence", "surface": "Lawrence"},
    ]
    fact = {
        "predicate": "SPOUSE_OF", "kind": "relation", "object": "Lawrence Kraft (also: Lawrence)",
        "value": None, "qualifier": None, "para_id": "v01:c04:p0382", "quote": quote,
        "confidence": 0.95, "polarity": "asserted",
    }
    client = _ScriptedExtractClient([[fact]])
    claims, drops = CL.extract_character_volume(
        MARHEIT, 1, records, mentions, ENTITIES_BY_ID, _FakeSettings(), client
    )
    assert claims == []
    assert drops["endpoint_not_named_in_paragraph"] == 1


def test_claims_driver_drops_a_two_word_quote_friendship():
    """Replays the corpus's own "Fall back." class: a real (verbatim, in-window, in-volume)
    quote too short to support any relation."""
    records = [
        {"para_id": "v01:c05:p0033", "vol": 1, "chapter_idx": 5,
         "text": "Marheit nodded and stepped back as the fighting began nearby.",
         "print_page": 50, "scene_break_before": "none"},
        {"para_id": "v01:c05:p0034", "vol": 1, "chapter_idx": 5, "text": "Kraft Lawrence: \"Fall back.\"",
         "print_page": 50, "scene_break_before": "none"},
    ]
    mentions = [
        {"para_id": "v01:c05:p0033", "vol": 1, "entity_id": "marheit", "surface": "Marheit"},
        {"para_id": "v01:c05:p0034", "vol": 1, "entity_id": "kraft-lawrence", "surface": "Kraft Lawrence"},
    ]
    fact = {
        "predicate": "FRIEND_OF", "kind": "relation", "object": "Marheit", "value": None,
        "qualifier": None, "para_id": "v01:c05:p0034", "quote": "Fall back.",
        "confidence": 0.9, "polarity": "asserted",
    }
    client = _ScriptedExtractClient([[fact]])
    claims, drops = CL.extract_character_volume(
        LAWRENCE, 1, records, mentions, ENTITIES_BY_ID, _FakeSettings(), client
    )
    assert claims == []
    assert drops["quote_too_short"] == 1


# --- Phase 26 part B: requires_qualifier ------------------------------------------------------


_PARA = "Lawrence and Marheit had known each other for years, and it showed in how they spoke."
_QUOTE = "Lawrence and Marheit had known each other for years"


def _friend_of(qualifier):
    return passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=MARHEIT, true_kind="relation",
        predicate_spec={"requires_qualifier": True}, paragraph_text=_PARA,
        quote=_QUOTE, behaviour=BEHAVIOUR, drops=Counter(), qualifier=qualifier,
    )


def test_relation_requiring_a_qualifier_is_dropped_without_one():
    """Phase 26 part B: 24 of 89 relations in the live v1-2 graph rendered as a bare "Friend of"
    / "Enemy of" -- the maintainer's own words were "'friend of' doesn't make much sense". A
    symmetric social predicate with no phrase saying what the bond consists of is a label, not
    a fact."""
    assert _friend_of(None) is False
    assert _friend_of("") is False
    assert _friend_of("   ") is False


def test_relation_requiring_a_qualifier_passes_with_one():
    assert _friend_of("childhood friends") is True


def test_the_drop_reason_is_counted_under_its_own_key():
    drops = Counter()
    passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=MARHEIT, true_kind="relation",
        predicate_spec={"requires_qualifier": True}, paragraph_text=_PARA,
        quote=_QUOTE, behaviour=BEHAVIOUR, drops=drops, qualifier=None,
    )
    assert drops["relation_without_qualifier"] == 1


def test_a_predicate_not_declaring_the_flag_is_unaffected():
    """The flag is opt-in per predicate -- SAVED, KILLED, AFFILIATED_WITH and the family
    predicates carry their meaning without a qualifier."""
    assert passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=MARHEIT, true_kind="relation",
        predicate_spec={}, paragraph_text=_PARA, quote=_QUOTE,
        behaviour=BEHAVIOUR, drops=Counter(), qualifier=None,
    ) is True


def test_an_attribute_is_never_subject_to_the_relation_qualifier_rule():
    assert passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=None, true_kind="attribute",
        predicate_spec={"requires_qualifier": True}, paragraph_text=_PARA, quote=_QUOTE,
        behaviour=BEHAVIOUR, drops=Counter(), qualifier=None,
    ) is True


# --- Phase 26 part B: qualifier_disqualifiers -------------------------------------------------


def test_qualifier_disqualifiers_drops_the_real_sheepdog_relative_claim():
    """`norah-arendt RELATIVE_OF enek`, qualifier "shepherd's sheepdog" -- one of the three
    `wiki audit eval` negative-fact violations the live v1-2 graph shipped. RELATIVE_OF's prompt
    note already said an animal is never a relative; the model emitted it anyway."""
    drops: Counter[str] = Counter()
    assert not passes_evidence_adequacy(
        subject_entity={"canonical": "Norah Arendt", "aliases": []},
        object_entity={"canonical": "Enek", "aliases": []},
        true_kind="relation",
        predicate_spec={"qualifier_disqualifiers": ["pet", "dog", "pretend"]},
        paragraph_text="Norah let go of Enek, her sheepdog, and stepped back.",
        quote="Norah let go of Enek, her sheepdog, and stepped back.",
        behaviour={},
        drops=drops,
        qualifier="shepherd's sheepdog",
    )
    assert drops["qualifier_disqualifies_predicate"] == 1


def test_qualifier_disqualifiers_drops_a_pretended_family_tie():
    drops: Counter[str] = Counter()
    assert not passes_evidence_adequacy(
        subject_entity={"canonical": "Kraft Lawrence", "aliases": []},
        object_entity={"canonical": "Holo", "aliases": []},
        true_kind="relation",
        predicate_spec={"qualifier_disqualifiers": ["pet", "dog", "pretend"]},
        paragraph_text="Lawrence had thought that the business about debt repayment was just a pretense for Holo.",
        quote="Lawrence had thought that the business about debt repayment was just a pretense for Holo.",
        behaviour={},
        drops=drops,
        qualifier="pretended debt as excuse to remain together",
    )
    assert drops["qualifier_disqualifies_predicate"] == 1


def test_qualifier_disqualifiers_leaves_an_ordinary_qualifier_alone():
    drops: Counter[str] = Counter()
    assert passes_evidence_adequacy(
        subject_entity={"canonical": "Norah Arendt", "aliases": []},
        object_entity={"canonical": "Enek", "aliases": []},
        true_kind="relation",
        predicate_spec={"qualifier_disqualifiers": ["pet", "dog", "pretend"]},
        paragraph_text="Norah let go of Enek, her sheepdog, and stepped back.",
        quote="Norah let go of Enek, her sheepdog, and stepped back.",
        behaviour={},
        drops=drops,
        qualifier="works the flock together",
    )
    assert not drops


# --- Phase 26 part C: irrealis_markers --------------------------------------------------------


def _shipped_config():
    """Read the real config so these tests fail if the shipped marker list or the
    `requires_realis` flags on KILLED/SAVED are weakened, not just the code path."""
    import yaml
    from narrativewiki.paths import PROJECT_ROOT

    return yaml.safe_load((PROJECT_ROOT / "config" / "extraction.yaml").read_text(encoding="utf-8"))


def _killed(quote):
    cfg = _shipped_config()
    behaviour = dict(BEHAVIOUR)
    behaviour["evidence_adequacy"] = dict(
        BEHAVIOUR["evidence_adequacy"],
        irrealis_markers=cfg["extraction"]["evidence_adequacy"]["irrealis_markers"],
    )
    drops: Counter[str] = Counter()
    ok = passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=MARHEIT, true_kind="relation",
        predicate_spec=cfg["relations"]["KILLED"], paragraph_text=quote, quote=quote,
        behaviour=behaviour, drops=drops,
    )
    return ok, drops


def test_killed_and_saved_require_realis_evidence_in_the_shipped_config():
    cfg = _shipped_config()
    assert cfg["relations"]["KILLED"]["requires_realis"] is True
    assert cfg["relations"]["SAVED"]["requires_realis"] is True


def test_counterfactual_quote_drops_the_real_lawrence_killed_liebert_claim():
    """`kraft-lawrence KILLED liebert`, conf 0.99, shipped in the live v1-2 graph on nothing but
    this sentence. Marheit stands in for Liebert here; the object only has to be named."""
    ok, drops = _killed(
        "Lawrence himself had felt a certain homicidal urge. If it had been up to Lawrence, "
        "he would have killed Marheit."
    )
    assert ok is False
    assert drops["irrealis_evidence"] == 1


def test_imagined_quote_drops_the_real_holo_killed_yarei_claim():
    ok, _ = _killed(
        "The image of Marheit's torso in Kraft Lawrence's fangs came unbidden to his mind."
    )
    assert ok is False


def test_a_real_killing_still_passes():
    ok, drops = _killed(
        "Kraft Lawrence drove the dagger home, and Marheit fell dead on the frozen road."
    )
    assert ok is True
    assert drops["irrealis_evidence"] == 0


def test_a_predicate_without_requires_realis_keeps_its_hedged_evidence():
    """Opt-in per predicate: "he may have been her friend" is a weak FRIEND_OF, not a false one."""
    cfg = _shipped_config()
    behaviour = dict(BEHAVIOUR)
    behaviour["evidence_adequacy"] = dict(
        BEHAVIOUR["evidence_adequacy"],
        irrealis_markers=cfg["extraction"]["evidence_adequacy"]["irrealis_markers"],
    )
    assert passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=MARHEIT, true_kind="relation",
        predicate_spec={"requires_qualifier": True},
        paragraph_text="Kraft Lawrence may have been Marheit's friend for years.",
        quote="Kraft Lawrence may have been Marheit's friend for years.",
        behaviour=behaviour, drops=Counter(), qualifier="old business friends",
    ) is True


# --- 2026-09-21: atypical_markers -------------------------------------------------------------


def _personality(quote):
    cfg = _shipped_config()
    behaviour = dict(BEHAVIOUR)
    behaviour["evidence_adequacy"] = dict(
        BEHAVIOUR["evidence_adequacy"],
        atypical_markers=cfg["extraction"]["evidence_adequacy"]["atypical_markers"],
    )
    drops: Counter[str] = Counter()
    ok = passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=None, true_kind="trait",
        predicate_spec=cfg["traits"]["PERSONALITY"], paragraph_text=quote, quote=quote,
        behaviour=behaviour, drops=drops,
    )
    return ok, drops


def test_personality_requires_typicality_in_the_shipped_config():
    assert _shipped_config()["traits"]["PERSONALITY"]["requires_typicality"] is True


def test_first_time_quote_drops_the_real_jakob_capable_of_empathy_claim():
    """The claim this gate was built for: conf 0.95, extracted from a sentence whose whole point
    is that the behaviour was a departure from how he usually is."""
    ok, drops = _personality(
        "For the first time, a flicker of empathy appeared in Kraft Lawrence's eyes."
    )
    assert ok is False
    assert drops["atypical_evidence"] == 1


def test_characteristic_behaviour_still_passes():
    """`overbearing yet warm` — the trait the same re-extraction got RIGHT, and the reason this
    gate is a marker list rather than a ban on narrated behaviour."""
    ok, drops = _personality(
        "Kraft Lawrence's manner was as overbearing as always, and it hit him with all the "
        "harsh edge and warmth of liquor."
    )
    assert ok is True
    assert drops["atypical_evidence"] == 0


def test_atypical_marker_does_not_affect_a_predicate_that_did_not_opt_in():
    cfg = _shipped_config()
    behaviour = dict(BEHAVIOUR)
    behaviour["evidence_adequacy"] = dict(
        BEHAVIOUR["evidence_adequacy"],
        atypical_markers=cfg["extraction"]["evidence_adequacy"]["atypical_markers"],
    )
    drops: Counter[str] = Counter()
    ok = passes_evidence_adequacy(
        subject_entity=LAWRENCE, object_entity=None, true_kind="trait",
        predicate_spec=cfg["traits"]["SKILL"],
        paragraph_text="For the first time, Kraft Lawrence haggled well.",
        quote="For the first time, Kraft Lawrence haggled well.",
        behaviour=behaviour, drops=drops,
    )
    assert ok is True  # SKILL never declared requires_typicality
    assert drops["atypical_evidence"] == 0
