"""Tests for site/wikify.py — Phase 7."""

from __future__ import annotations

from narrativewiki.entities.automaton import build_automaton
from narrativewiki.site.wikify import wikify_text

ENTITY_TYPES = {
    "CHARACTER": {"route": "/character/{slug}"},
    "FACTION": {"route": "/codex/factions#{slug}"},
}


class FakeSettings:
    def route_for(self, entity_type, slug):
        return ENTITY_TYPES[entity_type]["route"].format(slug=slug)


def _entity(entity_id, canonical, entity_type, first_vol, surface_forms):
    return {
        "entity_id": entity_id,
        "canonical": canonical,
        "type": entity_type,
        "first_vol": first_vol,
        "surface_forms": surface_forms,
    }


SHIN = _entity(
    "shinei-nouzen", "Shinei Nouzen", "CHARACTER", 1,
    [
        {"text": "Shinei Nouzen", "ambiguous": False, "first_vol": 1},
        {"text": "Shin", "ambiguous": False, "first_vol": 1},
        {"text": "Baleygr", "ambiguous": False, "first_vol": 3},
    ],
)
RAIDEN = _entity(
    "raiden-shuga", "Raiden Shuga", "CHARACTER", 2,
    [{"text": "Raiden", "ambiguous": False, "first_vol": 2}],
)
SPEARHEAD = _entity(
    "spearhead-squadron", "Spearhead Squadron", "FACTION", 1,
    [{"text": "Spearhead", "ambiguous": True, "first_vol": 1}],
)

ENTITIES_BY_ID = {e["entity_id"]: e for e in (SHIN, RAIDEN, SPEARHEAD)}


def _automaton():
    return build_automaton(list(ENTITIES_BY_ID.values()))


def test_links_a_safely_revealed_mention():
    text = "Shin led the squad."
    out = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=1)
    assert out == "[Shin](/character/shinei-nouzen) led the squad."


def test_entity_not_yet_revealed_is_not_linked():
    text = "Raiden watched from the ridge."
    out = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=1)
    assert out == text


def test_entity_revealed_at_exactly_this_cutoff_is_linked():
    text = "Raiden watched from the ridge."
    out = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=2)
    assert "[Raiden](/character/raiden-shuga)" in out


def test_alias_revealed_later_than_the_entity_itself_is_not_linked_early():
    text = "They called him Baleygr."
    out = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=1)
    assert out == text  # Shin exists at v1 but the "Baleygr" alias is a v3 reveal

    out_v3 = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=3)
    assert "[Baleygr](/character/shinei-nouzen)" in out_v3


def test_ambiguous_surface_form_is_never_linked():
    text = "The Spearhead took heavy losses."
    out = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=1)
    assert out == text


def test_self_mentions_are_excluded():
    text = "Shin was born in the Republic."
    out = wikify_text(
        text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=1, exclude_entity_id="shinei-nouzen"
    )
    assert out == text


def test_none_and_empty_text_pass_through():
    automaton = _automaton()
    assert wikify_text(None, automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=1) is None
    assert wikify_text("", automaton, ENTITIES_BY_ID, FakeSettings(), upto_vol=1) == ""


def test_text_with_no_mentions_is_unchanged():
    text = "Nothing named here."
    out = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=5)
    assert out == text


def test_multiple_mentions_all_linked_left_to_right():
    text = "Shin and Raiden fought together."
    out = wikify_text(text, _automaton(), ENTITIES_BY_ID, FakeSettings(), upto_vol=2)
    assert out == "[Shin](/character/shinei-nouzen) and [Raiden](/character/raiden-shuga) fought together."


def test_epithet_mined_surface_form_is_never_linked():
    """Phase 26: `extract/scenes.py::_build_epithet` applies no content filtering beyond a
    confidence floor, so the epithet channel carries generic descriptors (`merchant`,
    `the wolf`, `the spice`, `Shepherd`) alongside real ones. The `ambiguous` flag cannot
    catch those -- it marks a text claimed by MORE THAN ONE entity, and a generic common noun
    is usually claimed by exactly one -- so 21 of them shipped as links in the live v1-2 wiki,
    including "a timid, high-strung [merchant](kraft-lawrence.md)" on Liebert's own page."""
    merchant = _entity(
        "kraft-lawrence", "Kraft Lawrence", "CHARACTER", 1,
        [
            {"text": "Lawrence", "ambiguous": False, "first_vol": 1},
            {"text": "merchant", "ambiguous": False, "first_vol": 1, "source": "epithet_mining"},
        ],
    )
    entities = {"kraft-lawrence": merchant}
    automaton = build_automaton([merchant])
    out = wikify_text("Liebert is a high-strung merchant, unlike Lawrence.",
                      automaton, entities, FakeSettings(), 2)
    assert "[merchant]" not in out
    assert "[Lawrence](/character/kraft-lawrence)" in out


def test_a_non_epithet_surface_form_still_links():
    """The filter is scoped to the mined channel -- corpus/alias-cluster forms are unaffected."""
    entities = {"shinei-nouzen": SHIN}
    automaton = build_automaton([SHIN])
    out = wikify_text("Shin arrived.", automaton, entities, FakeSettings(), 2)
    assert "[Shin](/character/shinei-nouzen)" in out
