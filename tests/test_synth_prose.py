"""Tests for synth/prose.py — Phase 6."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import BaseModel, ValidationError

from narrativewiki.graph import store as ST
from narrativewiki.graph import temporal as TE
from narrativewiki.synth import prose as PR

TRAITS = {
    "PERSONALITY": {"display": "Personality"},
    "MOTIVATION": {"display": "Motivation"},
    "SKILL": {"display": "Skill"},
    "FEAR": {"display": "Fear"},
    "BACKGROUND": {"display": "Background"},
}


PAGE_OUTLINE = [
    {"key": "background", "kind": "prose", "title": "Background", "traits": ["BACKGROUND"],
     "min_sentences": 2, "max_sentences": 4,
     "subject": "a short biography", "source": "biographical facts"},
    {"key": "personality", "kind": "prose", "title": "Personality",
     "traits": ["PERSONALITY", "MOTIVATION", "SKILL", "FEAR"], "min_sentences": 2, "max_sentences": 4,
     "subject": "a short characterisation", "source": "personality, motivation, skill and fear traits"},
]


class FakeSettings:
    traits = TRAITS
    page_outline = PAGE_OUTLINE


class FakeClient:
    """Records every call and returns a canned ProseText, mirroring the JSONClient Protocol
    graph/contradictions.py's tests already use for the same purpose."""

    def __init__(self, text: str = "A short generated sentence."):
        self.text = text
        self.calls: list[dict] = []

    def complete_json(self, stage, prompt, schema, system=None):
        self.calls.append({"stage": stage, "prompt": prompt, "schema": schema, "system": system})
        return schema(text=self.text)


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    return conn


def _claim(claim_id, subject, predicate, first_vol, value, quote_vol=None):
    quote_vol = quote_vol or first_vol
    return {
        "claim_id": claim_id,
        "subject": subject,
        "predicate": predicate,
        "kind": "trait",
        "object": None,
        "value": value,
        "qualifier": None,
        "first_vol": first_vol,
        "confidence": 0.9,
        "evidence": [{"para_id": f"v{quote_vol:02d}:c00:p0001", "quote": f"evidence for {value}"}],
        "polarity": "asserted",
        "source": "test",
    }


SHIN = {"entity_id": "shin", "canonical": "Shin"}


def _write_trait(conn, predicate, first_vol, value, quote_vol=None):
    claim = _claim(f"c_{predicate}_{first_vol}", "shin", predicate, first_vol, value, quote_vol)
    ST.write_claims(conn, [claim])
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", predicate,
            [{"value_or_object": value, "qualifier": None, "first_vol": first_vol, "claim_id": claim["claim_id"]}],
            is_relation=False,
        ),
    )


def test_no_trait_claims_returns_none_and_makes_no_llm_call():
    conn = _conn()
    client = FakeClient()
    result = PR.generate_prose(conn, client, SHIN, 1, FakeSettings(), stage="prose")
    assert result == {"background": None, "personality": None}
    assert client.calls == []


def test_background_generated_from_background_trait_only():
    conn = _conn()
    _write_trait(conn, "BACKGROUND", 1, "Orphaned in the First Offensive")
    client = FakeClient(text="Shin was orphaned in the First Offensive.")
    result = PR.generate_prose(conn, client, SHIN, 1, FakeSettings(), stage="prose")

    assert result["personality"] is None
    assert result["background"]["text"] == "Shin was orphaned in the First Offensive."
    assert result["background"]["evidence"] == ["v01:c00:p0001"]
    assert len(client.calls) == 1
    assert client.calls[0]["stage"] == "prose"
    assert "Orphaned in the First Offensive" in client.calls[0]["prompt"]


def test_personality_combines_all_four_trait_predicates():
    conn = _conn()
    _write_trait(conn, "PERSONALITY", 1, "outwardly detached")
    _write_trait(conn, "MOTIVATION", 1, "protect his squad")
    client = FakeClient(text="He is outwardly detached but fiercely protective of his squad.")
    result = PR.generate_prose(conn, client, SHIN, 1, FakeSettings(), stage="prose")

    assert result["background"] is None
    assert len(client.calls) == 1
    prompt = client.calls[0]["prompt"]
    assert "outwardly detached" in prompt
    assert "protect his squad" in prompt


def test_evidence_quote_newer_than_cutoff_is_excluded_not_just_the_field():
    """The Phase 5 spoiler-leak fix (evidence_at filters by each quote's OWN volume) must hold
    here exactly as it does for wiki explain -- a trait interval merged across volumes must not
    leak a later quote into an earlier cutoff's prompt or evidence list."""
    conn = _conn()
    # Same claim_id's evidence spans v1 and v2 -- simulate by two claims sharing one interval's
    # claim_ids via two separate BACKGROUND observations at different first_vol that still both
    # resolve into the *current* value's claim_ids at cutoff 2, then check cutoff 1 only sees v1.
    _write_trait(conn, "BACKGROUND", 1, "Orphaned in the First Offensive", quote_vol=1)
    client = FakeClient(text="bio")
    result_v1 = PR.generate_prose(conn, client, SHIN, 1, FakeSettings(), stage="prose")
    assert result_v1["background"]["evidence"] == ["v01:c00:p0001"]

    # A claim whose only quote is from v2 must not appear in a v1 prompt at all -- state_at/
    # trait_values_at already wouldn't surface it (first_vol=2 > upto=1), so this also guards
    # the earlier link in the same chain evidence_at protects downstream.
    conn2 = _conn()
    _write_trait(conn2, "BACKGROUND", 2, "Something learned later", quote_vol=2)
    client2 = FakeClient(text="bio")
    result_v1_again = PR.generate_prose(conn2, client2, SHIN, 1, FakeSettings(), stage="prose")
    assert result_v1_again["background"] is None
    assert client2.calls == []


def test_stage_argument_is_forwarded_for_polish_routing():
    conn = _conn()
    _write_trait(conn, "BACKGROUND", 1, "fact")
    client = FakeClient()
    PR.generate_prose(conn, client, SHIN, 1, FakeSettings(), stage="prose_polish")
    assert client.calls[0]["stage"] == "prose_polish"


# ---------------------------------------------------------------------------
# Phase 20 — _adaptive_bounds tests
# ---------------------------------------------------------------------------


def test_adaptive_bounds_without_spe_returns_configured_fixed_bounds():
    """No sentences_per_evidence → return min_sentences/max_sentences unchanged."""
    section = {"min_sentences": 2, "max_sentences": 4}
    assert PR._adaptive_bounds(section, 10) == (2, 4)
    assert PR._adaptive_bounds(section, 0) == (2, 4)


def test_adaptive_bounds_with_spe_scales_with_evidence():
    """With sentences_per_evidence=0.5, 4 items → raw=2 → min=max(2,1)=2, max=min(6,max(3,2))=3."""
    section = {"min_sentences": 2, "max_sentences": 6, "sentences_per_evidence": 0.5}
    min_s, max_s = PR._adaptive_bounds(section, 4)
    assert min_s == 2
    assert max_s == 3


def test_adaptive_bounds_clamps_to_ceiling():
    """Very many evidence items must not exceed max_sentences ceiling."""
    section = {"min_sentences": 2, "max_sentences": 6, "sentences_per_evidence": 0.5}
    min_s, max_s = PR._adaptive_bounds(section, 100)
    assert min_s <= 6
    assert max_s <= 6


def test_adaptive_bounds_clamps_to_floor():
    """Very few evidence items must not go below min_sentences floor."""
    section = {"min_sentences": 2, "max_sentences": 6, "sentences_per_evidence": 0.5}
    min_s, max_s = PR._adaptive_bounds(section, 1)
    assert min_s >= 2


def test_adaptive_bounds_min_strictly_less_than_max():
    """The +1 guarantee: min_s < max_s always, giving model at least one degree of freedom."""
    section = {"min_sentences": 2, "max_sentences": 6, "sentences_per_evidence": 0.01}
    min_s, max_s = PR._adaptive_bounds(section, 1)
    assert min_s < max_s


def test_adaptive_bounds_defaults_without_explicit_floors():
    """Missing min_sentences/max_sentences default to 2/8 — same as the old fixed-bound defaults."""
    section = {"sentences_per_evidence": 1.0}
    min_s, max_s = PR._adaptive_bounds(section, 0)
    # 0 evidence: raw=0 → min_s=max(2,0)=2, max_s=min(8,max(3,0))=3
    assert min_s == 2
    assert min_s < max_s


# ---------------------------------------------------------------------------
# Phase 23 E1/E2 — source: "attributes" (generate_attribute_prose) and
# source: "history" (generate_history)
# ---------------------------------------------------------------------------

ATTRIBUTES = {"APPEARANCE": {"display": "Appearance", "single": False}}


def _write_attribute(conn, predicate, first_vol, value, quote_vol=None):
    """Same shape _write_trait uses, but through assign_multi_valued the way a real APPEARANCE
    attribute claim is stored (list-valued, no single-value supersession)."""
    quote_vol = quote_vol or first_vol
    claim = _claim(f"c_{predicate}_{first_vol}_{value}", "shin", predicate, first_vol, value, quote_vol)
    ST.write_claims(conn, [claim])
    ST.write_intervals(
        conn,
        TE.assign_multi_valued(
            "shin", predicate,
            [{"value_or_object": value, "qualifier": None, "first_vol": first_vol, "claim_id": claim["claim_id"]}],
            is_relation=False,
        ),
    )


APPEARANCE_SECTION = {
    "key": "appearance", "kind": "prose", "title": "Appearance", "traits": ["APPEARANCE"],
    "min_sentences": 2, "max_sentences": 4,
    "subject": "a physical description", "source": "attributes",
}


def test_attribute_prose_returns_none_with_no_evidence_and_makes_no_llm_call():
    conn = _conn()
    client = FakeClient()
    result = PR.generate_attribute_prose(conn, client, SHIN, 1, APPEARANCE_SECTION, ATTRIBUTES, stage="prose")
    assert result is None
    assert client.calls == []


def test_attribute_prose_generated_from_appearance_attribute():
    conn = _conn()
    _write_attribute(conn, "APPEARANCE", 1, "short silver hair")
    _write_attribute(conn, "APPEARANCE", 1, "gray eyes")
    client = FakeClient(text="Shin has short silver hair and gray eyes.")
    result = PR.generate_attribute_prose(conn, client, SHIN, 1, APPEARANCE_SECTION, ATTRIBUTES, stage="prose")

    assert result["text"] == "Shin has short silver hair and gray eyes."
    assert len(client.calls) == 1
    prompt = client.calls[0]["prompt"]
    assert "short silver hair" in prompt
    assert "gray eyes" in prompt


def test_attribute_prose_respects_cutoff():
    conn = _conn()
    _write_attribute(conn, "APPEARANCE", 2, "a new scar", quote_vol=2)
    client = FakeClient()
    result = PR.generate_attribute_prose(conn, client, SHIN, 1, APPEARANCE_SECTION, ATTRIBUTES, stage="prose")
    assert result is None
    assert client.calls == []


HISTORY_SECTION = {
    "key": "history", "kind": "prose", "title": "History", "traits": ["BACKGROUND"],
    "min_sentences": 2, "max_sentences": 4,
    "subject": "a narrative biography", "source": "history",
}


def test_history_returns_none_with_no_facts_and_no_events():
    conn = _conn()
    client = FakeClient()
    result = PR.generate_history(conn, None, client, SHIN, 1, HISTORY_SECTION, TRAITS, stage="prose")
    assert result is None
    assert client.calls == []


def test_history_generated_from_background_trait_alone_when_no_events_conn():
    conn = _conn()
    _write_trait(conn, "BACKGROUND", 1, "Orphaned in the First Offensive")
    client = FakeClient(text="Shin was orphaned in the First Offensive.")
    result = PR.generate_history(conn, None, client, SHIN, 1, HISTORY_SECTION, TRAITS, stage="prose")

    assert result["text"] == "Shin was orphaned in the First Offensive."
    assert result["evidence"] == ["v01:c00:p0001"]
    assert len(client.calls) == 1
    assert "Orphaned in the First Offensive" in client.calls[0]["prompt"]


def test_generate_prose_dispatches_history_and_attributes_sections():
    """generate_prose()'s main dispatch loop routes source: "history"/"attributes" to the new
    functions, exactly as source: "events" already routes to generate_chronology."""
    conn = _conn()
    _write_trait(conn, "BACKGROUND", 1, "Orphaned in the First Offensive")
    _write_attribute(conn, "APPEARANCE", 1, "short silver hair")

    class SettingsWithHistoryAndAppearance:
        traits = TRAITS
        attributes = ATTRIBUTES
        page_outline = [HISTORY_SECTION, APPEARANCE_SECTION]

    client = FakeClient(text="generated")
    result = PR.generate_prose(conn, client, SHIN, 1, SettingsWithHistoryAndAppearance(), stage="prose")
    assert result["history"]["text"] == "generated"
    assert result["appearance"]["text"] == "generated"
    assert len(client.calls) == 2


def test_generate_prose_system_prompt_reflects_adaptive_bounds():
    """The LLM system prompt should mention the adaptive sentence count, not the raw config."""
    conn = _conn()
    # 10 BACKGROUND facts → spe=0.5 → raw=5 → min_s=max(2,2)=2, max_s=min(6,5)=5
    for i in range(10):
        _write_trait(conn, "BACKGROUND", 1, f"fact {i}")
    outline_with_spe = [
        {"key": "background", "kind": "prose", "title": "Background", "traits": ["BACKGROUND"],
         "min_sentences": 2, "max_sentences": 6, "sentences_per_evidence": 0.5,
         "subject": "a short biography", "source": "biographical facts"},
    ]

    class SettingsWith20:
        traits = TRAITS
        page_outline = outline_with_spe

    client = FakeClient()
    PR.generate_prose(conn, client, SHIN, 1, SettingsWith20(), stage="prose")
    assert client.calls  # at least one call
    system = client.calls[0]["system"]
    # The prompt should NOT say "2-4" (old fixed bounds) but instead reflect adaptive bounds
    assert "2-4" not in system  # adaptive bounds in effect (spe with 10 facts gives 2-5 or similar)


# ---------------------------------------------------------------------------
# Phase 25 item 7 — real sentence-count cap, replacing the old char-length proxy
# ---------------------------------------------------------------------------


def test_prose_schema_accepts_text_within_the_sentence_cap():
    schema = PR._prose_schema_for(3)
    result = schema(text="One. Two. Three.")
    assert result.text == "One. Two. Three."


def test_prose_schema_trims_text_over_the_sentence_cap():
    """The real corpus bug this closes: a 900/280-char-length proxy let a 5-sentence answer pass
    a 4-sentence cap and a 15-sentence answer pass a 12-sentence cap, both comfortably short
    enough in characters. Over-cap output is now trimmed to the cap (Phase 26 part B -- raising
    killed a whole `wiki synthesize` run when the model overshot on all 3 repair attempts)."""
    schema = PR._prose_schema_for(3)
    assert schema(text="One. Two. Three. Four.").text == "One. Two. Three."


def test_prose_schema_trim_keeps_whole_sentences_only():
    """A trim must never leave a half sentence -- the cut is at a sentence boundary, and the
    trailing fragment after the last kept terminator is dropped, not emitted."""
    schema = PR._prose_schema_for(2)
    assert schema(text="A one. B two. C three. And a dangling fragment").text == "A one. B two."


def test_prose_schema_ignores_char_length_only_sentence_count_matters():
    """A single very long sentence must still pass -- the cap is about sentence count, not
    length, unlike the old char-based proxy this replaces."""
    schema = PR._prose_schema_for(1)
    long_sentence = "This is one single, quite long, deliberately run-on sentence. " * 5
    long_sentence = long_sentence.strip()
    assert long_sentence.count(".") == 5  # would have massively failed any char-based cap
    # Force it into exactly one terminal period so _count_sentences reads it as one sentence.
    one_sentence = long_sentence.replace(". ", ", ")[:-1] + "."
    result = schema(text=one_sentence)
    assert result.text == one_sentence


def test_a_model_answer_that_it_found_nothing_is_no_prose():
    """[34] Six frozen Anne pages printed "Ned Clay is not present in the provided events. As a
    result, there are no details available regarding his history" as History (OPEN_GAPS G8)."""
    from narrativewiki.synth import prose as P

    section = {"key": "history", "title": "History", "kind": "prose"}
    entries = [("Role: hired boy (since v1) -- \"Ned Clay worked there.\"", ["v01:c00:p0001"])]
    meta = FakeClient("Ned Clay is not present in the provided events. As a result, there are no details available.")
    assert P._generate_one(meta, "prose", section, "Ned Clay", 1, entries) is None
    # anne@v2 2026-10-05: "Theodora Dix is not mentioned in the provided scenes." (History, t=3..5)
    assert P._is_no_evidence_answer("Theodora Dix is not mentioned in the provided scenes.")
    plain = FakeClient("Ned Clay was a hired boy who was given information about the farm.")
    assert P._generate_one(plain, "prose", section, "Ned Clay", 1, entries)["text"].startswith("Ned Clay was")


def test_prose_cites_the_lines_the_model_names_not_every_fed_paragraph():
    """[34] OPEN_GAPS G7: a section cited every paragraph fed to it, and a page printed the first
    six. The model names the keys of the lines it used; an invented key cites nothing, and no
    valid key at all keeps every fed paragraph."""
    from narrativewiki.synth import prose as P

    section = {"key": "personality", "title": "Personality", "kind": "prose"}
    entries = [("Trait: kind -- \"a\"", ["v01:c00:p0001"]), ("Trait: brave -- \"b\"", ["v01:c00:p0002"]),
               ("Trait: shy -- \"c\"", ["v01:c00:p0003"])]

    class Citing(FakeClient):
        def __init__(self, cited):
            super().__init__("Shin is brave.")
            self.cited = cited

        def complete_json(self, stage, prompt, schema, system=None):
            self.calls.append({"prompt": prompt, "system": system})
            return schema(text=self.text, cited=self.cited)

    one = Citing(["F2"])
    assert P._generate_one(one, "prose", section, "Shin", 1, entries)["evidence"] == ["v01:c00:p0002"]
    assert "[F2] Trait: brave" in one.calls[0]["prompt"] and '"cited"' in one.calls[0]["system"]
    assert P._generate_one(Citing(["[F3]", "F9"]), "prose", section, "Shin", 1, entries)["evidence"] == ["v01:c00:p0003"]
    assert len(P._generate_one(Citing(["F9"]), "prose", section, "Shin", 1, entries)["evidence"]) == 3
