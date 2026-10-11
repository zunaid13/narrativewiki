"""Tests for extract/infobox.py -- the long-context infobox pass."""

from __future__ import annotations

from narrativewiki.extract import infobox as IB


class _Settings:
    attributes = {
        "GENDER": {"single": True, "display": "Gender"},
        "AGE": {"single": True, "display": "Age"},
        "OCCUPATION": {"single": True, "display": "Role"},
    }
    relations: dict = {}
    traits: dict = {}
    extraction_behaviour = {
        "window": {"context_paragraphs_before": 1, "context_paragraphs_after": 1,
                   "never_cross_hard_break": True, "max_tokens_per_request": 6000},
        "confidence": {"min_to_keep": 0.5},
        "max_quote_chars": 240,
        "infobox": {"fields": ["GENDER", "AGE"]},
    }


class _Client:
    def __init__(self, facts):
        self.facts, self.calls = facts, []

    def complete_json(self, stage, prompt, schema, system=None, options=None):
        self.calls.append((stage, prompt, system))
        return schema(facts=self.facts)

    def profile_for(self, stage):
        return "google:test"


def _rec(i, text):
    return {"para_id": f"v01:c00:p{i:04d}", "vol": 1, "chapter_idx": 0, "text": text,
            "print_page": 1, "scene_break_before": "none"}


def test_one_dossier_call_per_character_and_only_infobox_fields_survive():
    """The windowed pass would judge these two far-apart mentions in separate calls, and neither
    alone states Holo's gender outright. The infobox pass packs both into ONE request, and keeps
    only the configured infobox fields even if the model volunteers others."""
    records = [_rec(i, "Filler text about the road.") for i in range(20)]
    records[2] = _rec(2, "Holo pulled her hood lower over her ears.")
    records[17] = _rec(17, "Holo laughed, and she took another apple.")
    mentions = [{"para_id": r["para_id"], "vol": 1, "entity_id": "holo", "surface": "Holo"}
                for r in (records[2], records[17])]
    holo = {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER", "aliases": []}
    gender = {"predicate": "GENDER", "kind": "attribute", "value": "female",
              "para_id": "v01:c00:p0017", "quote": "Holo laughed, and she took another apple.",
              "confidence": 0.95, "polarity": "asserted"}
    role = {**gender, "predicate": "OCCUPATION", "value": "wisewolf"}
    client = _Client([gender, role])

    claims, drops = IB.extract_volume([holo], 1, records, mentions, [holo], _Settings(), client)

    assert len(client.calls) == 1
    stage, prompt, system = client.calls[0]
    assert stage == IB.STAGE
    assert "v01:c00:p0002" in prompt and "v01:c00:p0017" in prompt
    assert "OCCUPATION" not in system          # only the configured fields are asked for
    assert [(c["predicate"], c["value"]) for c in claims] == [("GENDER", "female")]
    assert claims[0]["source"] == "infobox_extract:google:test"
    assert claims[0]["first_vol"] == 1
    assert drops["not_infobox_field"] == 1


def test_recover_verbatim_forgives_dropped_quote_marks_and_nothing_else():
    from narrativewiki.extract.resolve import recover_verbatim

    para = "“We accept your proposal,” said the head of the branch, Richten Marheit, in an even tone."
    got = recover_verbatim("We accept your proposal, said the head of the branch, Richten Marheit", para)
    assert got == "We accept your proposal,” said the head of the branch, Richten Marheit"
    assert got in para                                   # still the source's own bytes
    assert recover_verbatim("We accept your offer, said the head", para) is None   # a changed word
    assert recover_verbatim("in an even tone. It had been two days", para) is None  # stitched text


def test_recover_verbatim_accepts_speech_stitched_across_a_speech_tag():
    """[31] Verne interrupts nearly every line with a tag; the model quotes the spoken words only."""
    from narrativewiki.extract.resolve import recover_verbatim

    para = "“Oh! certainly,” I answered, evasively, “by making a curve.”"
    got = recover_verbatim("Oh! certainly, by making a curve.", para)
    assert got == "Oh! certainly,” I answered, evasively, “by making a curve." and got in para
    assert recover_verbatim("Oh! certainly, by making a circle.", para) is None      # a changed word
    assert recover_verbatim("certainly, evasively", para) is None                   # tag stitched into speech
    assert recover_verbatim("by making a curve. Oh! certainly", para) is None       # order matters
    para2 = "“Himself,” replied I; “Commander Farragut?”"
    assert recover_verbatim("Himself, Commander Farragut?", para2) == "Himself,” replied I; “Commander Farragut?"
    para3 = "“That deceives you, Professor,” replied Ned. “That the vulgar believe.”"
    assert recover_verbatim("That deceives you, Professor. That the vulgar believe.", para3) == \
        "That deceives you, Professor,” replied Ned. “That the vulgar believe."


def test_backstory_pass_keeps_context_so_a_first_person_past_can_be_cited():
    """A past is usually told in dialogue that never names its speaker ("I helped at an
    almshouse..."). The infobox pass sends named paragraphs only; the backstory pass must keep the
    neighbours, where "said Norah" lets the subject-named gate accept the quote."""
    class S(_Settings):
        traits = {"BACKGROUND": {"display": "Background"}}
        extraction_behaviour = {**_Settings.extraction_behaviour, "backstory": {"fields": ["BACKGROUND"]}}

    records = [_rec(0, "Norah looked up."), _rec(1, "I helped at an almshouse attached to an abbey."),
               _rec(2, "Filler."), _rec(3, "Filler.")]
    mentions = [{"para_id": "v01:c00:p0000", "vol": 1, "entity_id": "norah", "surface": "Norah"}]
    norah = {"entity_id": "norah", "canonical": "Norah", "type": "CHARACTER", "aliases": []}
    past = {"predicate": "BACKGROUND", "kind": "trait", "value": "helped at an almshouse",
            "para_id": "v01:c00:p0001", "quote": "I helped at an almshouse attached to an abbey.",
            "confidence": 0.9, "polarity": "asserted"}
    client = _Client([past])

    claims, _ = IB.extract_volume([norah], 1, records, mentions, [norah], S(), client, name="backstory")

    stage, prompt, _system = client.calls[0]
    assert stage == "backstory_extract"
    assert "v01:c00:p0001" in prompt                        # the unnamed neighbour was sent
    assert [c["value"] for c in claims] == ["helped at an almshouse"]
    assert IB._dossier_window_cfg(S(), "infobox")["context_paragraphs_after"] == 0


def test_recover_verbatim_handles_straight_quote_dialogue():
    """[31] Rilla of Ingleside writes dialogue with straight quotes."""
    from narrativewiki.extract.resolve import recover_verbatim, within_dialogue

    para = '"They are calling for volunteers," said Jem. "I\'m going in tonight to enlist."'
    got = recover_verbatim("They are calling for volunteers, I'm going in tonight to enlist.", para)
    assert got and got in para and got.startswith("They are calling")
    assert within_dialogue("going in tonight", para)
