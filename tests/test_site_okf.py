"""Tests for site/okf.py — Phase 6, CONTRACTS §5.2."""

from __future__ import annotations

import yaml

from narrativewiki.site import okf

ATTRIBUTES = {
    "AGE": {"single": True, "display": "Age"},
    "RANK": {"single": True, "display": "Rank"},
    "NICKNAME": {"single": False, "display": "Nickname"},
}


PAGE_OUTLINE = [
    {"key": "overview", "kind": "fields", "title": "Overview"},
    {"key": "affiliations", "kind": "affiliations", "title": "Affiliations"},
    {"key": "relationships", "kind": "relationships", "title": "Relationships"},
    {"key": "background", "kind": "prose", "title": "Background"},
    {"key": "personality", "kind": "prose", "title": "Personality"},
    {"key": "appearances", "kind": "derived", "title": "Appearances"},
]


class FakeSettings:
    attributes = ATTRIBUTES
    page_outline = PAGE_OUTLINE


ENTITY = {
    "entity_id": "shinei-nouzen",
    "canonical": "Shinei Nouzen",
    "type": "CHARACTER",
    "aliases": ["Shin", "Undertaker"],
    "first_vol": 1,
}

PAGE = {
    "entity_id": "shinei-nouzen",
    "canonical": "Shinei Nouzen",
    "upto_vol": 3,
    "claim_set_hash": "abc123",
    "fields": {
        "age": {
            "value": "16", "since_vol": 1, "show_vol": False,
            "polarity": "asserted", "history": [], "inferred": False,
        },
        "rank": {
            "value": "Captain", "since_vol": 3, "show_vol": True,
            "polarity": "asserted", "inferred": False,
            "history": [{"value": "Second Lieutenant", "vols": [2, 2], "polarity": "asserted"}],
        },
        "nickname": [{"value": "Undertaker", "since_vol": 1, "show_vol": False}],
        "affiliations": [
            {"entity_id": "spearhead-squadron", "role": "leader", "vols": [1, 1], "current": False},
            {"entity_id": "nordlicht-squadron", "role": "member", "vols": [2, None], "current": True},
        ],
        "relationships": [
            {
                "entity_id": "kiriya-nouzen", "predicate": "SIBLING_OF", "label": "Sibling of",
                "note": "elder brother", "blurb": "Sibling of — elder brother", "since_vol": 1,
                "show_vol": False, "current": True, "vol_end": None,
            }
        ],
    },
    "prose": {
        "background": {"text": "Shin was orphaned young.", "evidence": ["v01:c00:p0001"]},
        "personality": None,
    },
    "mentions_of": [],
    "generated_by": "test-model",
}

ENTITIES_BY_ID = {
    # `type` matters from Phase 26 on: `_relationship_lines` groups CHARACTER targets under a
    # per-person heading and everything else under "Organisations & places".
    "spearhead-squadron": {"canonical": "Spearhead Squadron", "type": "FACTION"},
    "nordlicht-squadron": {"canonical": "Nordlicht Squadron", "type": "FACTION"},
    "kiriya-nouzen": {"canonical": "Kiriya Nouzen", "type": "CHARACTER"},
}


def test_front_matter_has_required_fields():
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert md.startswith("---\n")
    front, _, body = md[4:].partition("\n---\n")
    doc = yaml.safe_load(front)
    assert doc["entity_id"] == "shinei-nouzen"
    assert doc["canonical"] == "Shinei Nouzen"
    assert doc["type"] == "CHARACTER"
    assert doc["aliases"] == ["Shin", "Undertaker"]
    assert doc["upto_vol"] == 3
    assert doc["categories"] == ["nordlicht-squadron", "spearhead-squadron"]
    assert doc["first_vol"] == 1


def test_body_sections_present_in_contract_order():
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    order = ["## Overview", "## Affiliations", "## Relationships", "## Background", "## Personality", "## Appearances"]
    positions = [md.index(h) for h in order]
    assert positions == sorted(positions)


def test_scalar_field_shows_current_value_and_history_without_leaking_future_vol_end():
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "**Rank:** Captain (since v3)" in md
    assert "previously: Second Lieutenant (v2)" in md


def test_no_rendered_page_says_changes_later():
    """Phase 32 req. 9: a marker that a value "changes later" tells the reader a later volume
    changes it. Nothing on a page may point past the cutoff."""
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "changes later" not in md.lower()


def test_affiliation_and_relationship_labels_use_canonical_names():
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "Spearhead Squadron" in md
    assert "Nordlicht Squadron" in md
    # Phase 26: relationships group under a per-person heading, so the other party's name is
    # the heading and the bullet carries the Phase 22 A5 (U4) blurb (label + demoted
    # qualifier). No "(since v1)" -- show_vol is False, v1 being this character's own first
    # appearance.
    assert "### Kiriya Nouzen" in md
    assert "- Sibling of — elder brother" in md
    assert "- Sibling of — elder brother (since v1)" not in md


def test_missing_prose_renders_placeholder_not_crash():
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "_Not yet known._" in md  # personality is None in the fixture


def test_appearances_derived_from_since_vol_and_history_vols():
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    tail = md.split("## Appearances")[1]
    assert "Volumes 1-3" in tail


def test_labels_fall_back_to_entity_id_without_a_lookup_map():
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), entities_by_id=None)
    assert "spearhead-squadron" in md


def test_section_order_follows_page_outline_not_a_hardcoded_list():
    class ReorderedSettings:
        attributes = ATTRIBUTES
        page_outline = [
            {"key": "personality", "kind": "prose", "title": "Personality"},
            {"key": "background", "kind": "prose", "title": "Background"},
            {"key": "overview", "kind": "fields", "title": "Overview"},
        ]

    md = okf.render_markdown(PAGE, ENTITY, ReorderedSettings(), ENTITIES_BY_ID)
    order = ["## Personality", "## Background", "## Overview"]
    positions = [md.index(h) for h in order]
    assert positions == sorted(positions)
    assert "## Affiliations" not in md  # dropped from this outline entirely


def test_show_vol_false_renders_bare_no_since_marker():
    """Phase 22 A5 (U3): age's show_vol is False in the fixture (known since this character's
    first appearance) -- no "(since v1)" noise."""
    md = okf.render_markdown(PAGE, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "**Age:** 16" in md
    assert "**Age:** 16 (since v1)" not in md


def test_presumed_polarity_prefixes_the_value():
    """Phase 22 A5 (U7): "presumed dead" must not render indistinguishable from "dead"."""
    page = {
        **PAGE,
        "fields": {**PAGE["fields"], "age": {**PAGE["fields"]["age"], "value": "dead", "polarity": "presumed"}},
    }
    md = okf.render_markdown(page, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "**Age:** presumed dead" in md


def test_inferred_field_gets_assumed_note():
    """Phase 22 A5 (U6): a default-materialized field (inferred: true) is marked as such."""
    page = {
        **PAGE,
        "fields": {**PAGE["fields"], "age": {**PAGE["fields"]["age"], "inferred": True}},
    }
    md = okf.render_markdown(page, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "(assumed)" in md


def test_untraceable_attribute_is_marked_but_assumed_default_is_not_double_marked():
    field = {**PAGE["fields"]["age"], "evidence": []}
    line = okf._overview_lines({"fields": {"age": field}}, ATTRIBUTES)[0]
    assert "source evidence unavailable" in line

    # A page assembled before citations existed has no `evidence` key; that is a stale artifact,
    # not a statement about the source, so it stays silent instead of marking every row.
    stale = {k: v for k, v in field.items() if k != "evidence"}
    stale_line = okf._overview_lines({"fields": {"age": stale}}, ATTRIBUTES)[0]
    assert "source evidence unavailable" not in stale_line

    assumed = {**field, "inferred": True}
    assumed_line = okf._overview_lines({"fields": {"age": assumed}}, ATTRIBUTES)[0]
    assert "(assumed)" in assumed_line
    assert "source evidence unavailable" not in assumed_line


def test_traceable_attribute_links_to_its_exact_source_paragraph():
    field = {**PAGE["fields"]["age"], "evidence": ["v01:c00:p0001"]}
    line = okf._overview_lines({"fields": {"age": field}}, ATTRIBUTES, link_depth=2)[0]
    assert "../source/v01-c00.md#nw-v01-c00-p0001" in line
    assert "source evidence unavailable" not in line


def test_closed_relationship_shows_ended_marker():
    """Phase 22 A5 (U4): a superseded relation renders with an ended marker instead of looking
    indistinguishable from a still-live one."""
    page = {
        **PAGE,
        "fields": {
            **PAGE["fields"],
            "relationships": [
                {
                    "entity_id": "kiriya-nouzen", "predicate": "FRIEND_OF", "label": "Friend of",
                    "note": None, "blurb": "Friend of", "since_vol": 1, "show_vol": False,
                    "current": False, "vol_end": 3,
                }
            ],
        },
    }
    md = okf.render_markdown(page, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "(ended v3)" in md


def test_lead_section_renders_as_bare_paragraph_no_heading():
    """Phase 22 A5 (S6): kind: lead has no "## " heading -- render_markdown special-cases it."""
    class SettingsWithLead:
        attributes = ATTRIBUTES
        page_outline = [{"key": "lead", "kind": "lead", "title": ""}, *PAGE_OUTLINE]

    page = {**PAGE, "lead": "presumed dead · Nordlicht Squadron"}
    md = okf.render_markdown(page, ENTITY, SettingsWithLead(), ENTITIES_BY_ID)
    assert "\n\npresumed dead · Nordlicht Squadron" in md  # bare paragraph, no "## " heading
    assert "## \n" not in md  # the lead section's empty title never becomes a heading


def test_lead_section_omitted_entirely_when_none():
    class SettingsWithLead:
        attributes = ATTRIBUTES
        page_outline = [{"key": "lead", "kind": "lead", "title": ""}, *PAGE_OUTLINE]

    page = {**PAGE, "lead": None}
    md = okf.render_markdown(page, ENTITY, SettingsWithLead(), ENTITIES_BY_ID)
    assert "## Overview" in md  # rest of the page still renders fine


# ---------------------------------------------------------------------------
# Phase 26 — alias vs epithet in the front matter
# ---------------------------------------------------------------------------


def test_names_a_character_accepts_titles_and_rejects_descriptions():
    from narrativewiki.site.okf import _names_a_character

    for name in ("Holo the Wisewolf", "the Wisewolf of Yoitsu", "Wisewolf", "the Wisewolf Holo"):
        assert _names_a_character(name), name
    for description in ("her prey", "a mere dog", "the companions' anxiety", "The wisewolf", "merchant"):
        assert not _names_a_character(description), description


def test_split_aliases_moves_mined_descriptions_out_of_the_alias_list():
    """Phase 26: the live v1-2 wiki put all 45 of Holo's surface forms in her front matter, so
    `the companions' anxiety`, `the merchant` (Lawrence's) and `the shepherd girl` (Norah's)
    rendered as names she goes by."""
    from narrativewiki.site.okf import _split_aliases

    entity = {
        "aliases": ["Holo the Wisewolf", "her prey", "the Wisewolf of Yoitsu", "Wisewolf of Yoitsu"],
        "surface_forms": [
            {"text": "Holo the Wisewolf", "source": "epithet_mining"},
            {"text": "her prey", "source": "epithet_mining"},
            {"text": "the Wisewolf of Yoitsu", "source": "epithet_mining"},
            {"text": "Wisewolf of Yoitsu", "source": "alias_cluster"},
        ],
    }
    aliases, epithets = _split_aliases(entity, 99)
    assert aliases == ["Holo the Wisewolf", "Wisewolf of Yoitsu", "the Wisewolf of Yoitsu"]
    assert epithets == ["her prey"]


def test_split_aliases_keeps_every_non_mined_alias():
    from narrativewiki.site.okf import _split_aliases

    entity = {
        "aliases": ["Shin", "the reaper"],
        "surface_forms": [
            {"text": "Shin", "source": "corpus"},
            {"text": "the reaper", "source": "override"},
        ],
    }
    assert _split_aliases(entity, 99) == (["Shin", "the reaper"], [])


def test_relationships_group_by_person_with_narration_above_the_bullets():
    """Phase 26: the shipped v1-2 wiki rendered one flat list sorted by (since_vol, entity_id),
    so Holo's page carried 31 bullets of which 9 were Kraft Lawrence -- and not adjacent,
    because everything first seen in v1 sorted ahead of everything first seen in v2."""
    page = {
        **PAGE,
        "relationship_prose": {"kiriya-nouzen": {"text": "They were raised together.", "evidence": []}},
        "fields": {
            **PAGE["fields"],
            "relationships": [
                {"entity_id": "kiriya-nouzen", "predicate": "SIBLING_OF", "label": "Sibling of",
                 "note": "elder brother", "blurb": "Sibling of — elder brother", "since_vol": 1,
                 "show_vol": False, "current": True, "vol_end": None, "evidence": []},
                {"entity_id": "kiriya-nouzen", "predicate": "SAVED", "label": "Saved",
                 "note": None, "blurb": "Saved", "since_vol": 2,
                 "show_vol": True, "current": True, "vol_end": None, "evidence": []},
            ],
        },
    }
    md = okf.render_markdown(page, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert md.count("### Kiriya Nouzen") == 1  # one heading, not one per predicate
    assert "They were raised together." in md
    assert md.index("They were raised together.") < md.index("- Sibling of")
    assert "- Saved (since v2)" in md


def test_non_character_relations_render_under_their_own_heading():
    """Places and organisations were interleaved with people in the flat list."""
    page = {
        **PAGE,
        "fields": {
            **PAGE["fields"],
            "relationships": [
                {"entity_id": "spearhead-squadron", "predicate": "ORIGIN_FROM", "label": "From",
                 "note": None, "blurb": "From", "since_vol": 1, "show_vol": False,
                 "current": True, "vol_end": None, "evidence": []},
            ],
        },
    }
    md = okf.render_markdown(page, ENTITY, FakeSettings(), ENTITIES_BY_ID)
    assert "### Organisations & places" in md


def test_related_section_shows_only_connections_the_pipeline_can_explain():
    """Phase 30: `mentions_of` was computed since Phase 22 and rendered nowhere, so a connection
    reached the reader only if prose happened to name it. An entry with `note: None` is a
    multi-hop-only PPR hit -- an unexplained "related" chip is the noise Phase 29 stripped out of
    the codex pages, not connectivity, so it stays hidden."""
    page = {"mentions_of": [
        {"entity_id": "zheren", "note": "9 shared scenes"},
        {"entity_id": "holo", "note": None},
    ]}
    section = {"key": "related", "kind": "related", "title": "Related"}
    entities = {"zheren": {"entity_id": "zheren", "canonical": "Zheren", "type": "CHARACTER"}}
    body = okf._section_body(section, page, FakeSettings(), entities, None, None)
    assert body == "- Zheren — 9 shared scenes"

    empty = okf._section_body(section, {"mentions_of": []}, FakeSettings(), {}, None, None)
    assert empty == "_None known yet._"


def test_family_line_takes_roles_from_the_predicate_not_the_mixed_perspective_note():
    """[30] Myne's page read "Effa (daughter)": the qualifier described Myne, not Effa."""
    class S(FakeSettings):
        relations = {"CHILD_OF": {"family": "parent"}, "RELATIVE_OF": {"family": "relative"},
                     "FRIEND_OF": {}}
    page = {"entity_id": "myne", "fields": {"relationships": [
        {"entity_id": "effa", "predicate": "RELATIVE_OF", "note": "mother", "label": "Relative of"},
        {"entity_id": "effa", "predicate": "CHILD_OF", "note": "daughter", "label": "Child of"},
        {"entity_id": "tuuli", "predicate": "RELATIVE_OF", "note": "older sister", "label": "Relative of"},
        {"entity_id": "lutz", "predicate": "FRIEND_OF", "note": "friend", "label": "Friend of"}]}}
    names = {"effa": {"canonical": "Effa"}, "tuuli": {"canonical": "Tuuli"}, "lutz": {"canonical": "Lutz"}}
    [line] = okf._family_lines(page, names, S())
    assert "Effa" in line and "(parent)" in line and "(sibling)" in line and "Lutz" not in line
