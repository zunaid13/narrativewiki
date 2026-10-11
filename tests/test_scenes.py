"""Tests for extract/{spans,scene_schema,scenes}.py — Phase 18.

Follows the pattern in test_extract.py: scripted fake LLM clients (never touches Ollama), and
small hand-built paragraph/mention fixtures rather than real corpus data.
"""

from __future__ import annotations

from narrativewiki.extract import scene_schema as SS
from narrativewiki.extract import scenes as SC
from narrativewiki.extract import schema as ES
from narrativewiki.extract import spans as SP

# ---------------------------------------------------------------------------
# spans.py
# ---------------------------------------------------------------------------


def _cpara(idx: int, chapter_idx: int = 0, vol: int = 1, text: str = "text", scene_break: str = "none") -> dict:
    return {
        "para_id": f"v{vol:02d}:c{chapter_idx:02d}:p{idx:04d}",
        "vol": vol,
        "chapter_idx": chapter_idx,
        "seq": idx,
        "text": text,
        "print_page": None,
        "scene_break_before": scene_break,
    }


DEFAULT_SCENE_CFG = {"span_target_tokens": 4000, "span_overlap_tokens": 500, "max_tokens_per_request": 6000}


def test_build_chapter_spans_short_chapter_is_one_span():
    records = [_cpara(i) for i in range(5)]
    spans = SP.build_chapter_spans(1, 0, records, DEFAULT_SCENE_CFG)
    assert len(spans) == 1
    assert spans[0].core_para_ids == tuple(r["para_id"] for r in records)
    assert spans[0].para_ids == spans[0].core_para_ids


def test_build_chapter_spans_empty_chapter_returns_no_spans():
    assert SP.build_chapter_spans(1, 0, [], DEFAULT_SCENE_CFG) == []


def test_build_chapter_spans_partitions_a_long_chapter_with_no_gap_or_duplicate():
    """core_para_ids across every span of one chapter must partition it exactly -- the literal
    "100% coverage by construction" guarantee this phase exists to provide."""
    para_text = "word " * 50  # ~62 tokens per paragraph
    records = [_cpara(i, text=para_text) for i in range(20)]
    cfg = {"span_target_tokens": 200, "span_overlap_tokens": 100, "max_tokens_per_request": 6000}
    spans = SP.build_chapter_spans(1, 0, records, cfg)
    assert len(spans) > 1

    core_seen: list[str] = []
    for s in spans:
        core_seen.extend(s.core_para_ids)
    assert core_seen == [r["para_id"] for r in records]  # exact partition, in order, no dupes

    # consecutive spans' para_ids DO overlap by roughly span_overlap_tokens
    for i in range(len(spans) - 1):
        overlap = set(spans[i].core_para_ids) & set(spans[i + 1].para_ids)
        assert overlap, "expected trailing context overlap into the next span"


def test_build_chapter_spans_marks_hard_break_inline_instead_of_splitting():
    """Unlike windows.py, a span may cross a hard scene break -- refusing paragraphs would
    reopen the coverage gap this module exists to close. The break is marked inline instead."""
    records = [_cpara(i) for i in range(6)]
    records[3]["scene_break_before"] = "hard"
    spans = SP.build_chapter_spans(1, 0, records, DEFAULT_SCENE_CFG)
    assert len(spans) == 1
    assert "[SCENE BREAK]" in spans[0].text


def test_build_chapter_spans_emits_oversized_core_rather_than_truncating():
    """A span never drops a CORE paragraph to fit budget -- a paragraph that alone exceeds the
    budget still gets emitted whole, mirroring windows.py's own documented posture."""
    huge_text = "word " * 100  # ~125 tokens, alone bigger than the tiny budget below
    records = [_cpara(0, text=huge_text), _cpara(1, text="short")]
    cfg = {"span_target_tokens": 50, "span_overlap_tokens": 20, "max_tokens_per_request": 50}
    spans = SP.build_chapter_spans(1, 0, records, cfg)
    assert records[0]["para_id"] in spans[0].core_para_ids


# ---------------------------------------------------------------------------
# scene_schema.py
# ---------------------------------------------------------------------------


def test_scene_beat_result_drops_incomplete_participants():
    result = SS.SceneBeatResult.model_validate({"participants": ["Shin", ""]})
    assert result.participants == ["Shin"]


def test_scene_detail_result_drops_incomplete_state_changes_quotes_epithets():
    result = SS.SceneDetailResult.model_validate(
        {
            "state_changes": [
                {"subject": "Shin", "note": "becomes distrustful", "para_id": "v01:c00:p0001", "quote": "q"},
                {"subject": "Shin"},  # missing note/para_id/quote
            ],
            "quotes": [
                {"para_id": "v01:c00:p0001", "quote": "q"},
                {"quote": "no para id"},
            ],
            "epithets": [
                {"entity_id_hint": "Shin", "text": "the reaper", "para_id": "v01:c00:p0001", "quote": "q"},
                {"entity_id_hint": "Shin"},  # missing text/para_id/quote
            ],
        }
    )
    assert len(result.state_changes) == 1
    assert len(result.quotes) == 1
    assert len(result.epithets) == 1


def test_scene_detail_result_drops_participant_fact_groups_and_facts():
    result = SS.SceneDetailResult.model_validate(
        {
            "participant_facts": [
                {
                    "subject": "Shin",
                    "facts": [
                        {
                            "predicate": "AGE", "kind": "attribute", "value": "18",
                            "para_id": "v01:c00:p0001", "quote": "q",
                        },
                        {"predicate": "AGE", "kind": "attribute"},  # missing para_id/quote
                    ],
                },
                {"subject": "", "facts": []},  # blank subject -- whole group dropped
                {"subject": "Raiden"},  # missing "facts" key entirely -- dropped
            ],
        }
    )
    assert len(result.participant_facts) == 1
    assert result.participant_facts[0].subject == "Shin"
    assert len(result.participant_facts[0].facts) == 1


def test_scene_detail_result_quarantines_invalid_participant_fact_polarity():
    ES.pop_incomplete_fact_drops()
    result = SS.SceneDetailResult.model_validate({
        "participant_facts": [{
            "subject": "Shin",
            "facts": [
                {"predicate": "AGE", "kind": "attribute", "value": "18",
                 "para_id": "v01:c00:p0001", "quote": "q", "polarity": "asserted"},
                {"predicate": "AGE", "kind": "attribute", "value": "19",
                 "para_id": "v01:c00:p0002", "quote": "q", "polarity": "confirmed"},
            ],
        }],
    })

    assert len(result.participant_facts[0].facts) == 1
    assert result.participant_facts[0].facts[0].polarity == "asserted"
    assert ES.pop_incomplete_fact_drops()["invalid_polarity"] == 1


def test_extracted_state_change_coerces_non_string_optional_fields_to_none():
    sc = SS.ExtractedStateChange.model_validate(
        {"subject": "Shin", "predicate": [], "note": "n", "para_id": "p", "quote": "q"}
    )
    assert sc.predicate is None


def test_make_scene_id_is_deterministic():
    a = SS.make_scene_id(1, 2, 3)
    b = SS.make_scene_id(1, 2, 3)
    c = SS.make_scene_id(1, 2, 4)
    assert a == b
    assert a != c
    assert a.startswith("sn_")


# ---------------------------------------------------------------------------
# scenes.py
# ---------------------------------------------------------------------------

ATTRIBUTES = {"AGE": {"single": True, "format": "number_or_range", "display": "Age"}}
RELATIONS = {"ENEMY_OF": {"symmetric": True, "display": "Enemy of"}}


class FakeSettings:
    attributes = ATTRIBUTES
    relations = RELATIONS
    traits = {}
    extraction_behaviour = {
        "scene": DEFAULT_SCENE_CFG,
        "max_quote_chars": 240,
    }


ENTITIES_BY_ID = {
    "shinei-nouzen": {"entity_id": "shinei-nouzen", "canonical": "Shinei Nouzen", "type": "CHARACTER"},
    "raiden-shuga": {"entity_id": "raiden-shuga", "canonical": "Raiden Shuga", "type": "CHARACTER"},
    "district-one": {"entity_id": "district-one", "canonical": "District One", "type": "LOCATION"},
}

_QUOTE = "Shin glared at Raiden, and something between them had changed for good."
CHAPTER_RECORDS = [
    # Phase 23 A1: "District One" must actually appear in the chapter/span text
    # (resolve_surface now requires a candidate's surface to occur in the passage it was shown).
    {"para_id": "v01:c00:p0000", "vol": 1, "chapter_idx": 0, "text": "Context before, in District One.",
     "print_page": 1, "scene_break_before": "none"},
    {"para_id": "v01:c00:p0001", "vol": 1, "chapter_idx": 0, "text": _QUOTE,
     "print_page": 1, "scene_break_before": "none"},
    {"para_id": "v01:c00:p0002", "vol": 1, "chapter_idx": 0, "text": "Context after.",
     "print_page": 1, "scene_break_before": "none"},
]
CHAPTER_MENTIONS = [
    {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin"},
    {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "raiden-shuga", "surface": "Raiden"},
    {"para_id": "v01:c00:p0000", "vol": 1, "entity_id": "district-one", "surface": "District One"},
]


class _ScriptedSceneClient:
    """Returns the next scripted payload for each SPAN, in order -- Phase 22 B1 makes two calls
    per span (beat, then detail) instead of one, but pydantic's default `extra="ignore"` means a
    single combined payload dict can serve both `SceneBeatResult` and `SceneDetailResult` calls,
    since each model only reads the fields it declares and drops the rest. `profile_for` is
    duck-typed to what scenes.py needs to stamp `source` — never a real LLMClient."""

    def __init__(self, payloads_by_call: list[dict]):
        self.payloads_by_call = payloads_by_call
        self.calls = 0

    def complete_json(self, stage, prompt, schema, system=None, options=None):
        payload = self.payloads_by_call[self.calls // 2]
        self.calls += 1
        return schema(**payload)

    def profile_for(self, stage):
        return "ollama:test-model"


def _empty_payload(**overrides) -> dict:
    payload = {
        "participants": [], "location": None, "beat_summary": "",
        "state_changes": [], "quotes": [], "epithets": [], "participant_facts": [], "confidence": 0.7,
    }
    payload.update(overrides)
    return payload


def test_participant_not_mentioned_in_chapter_is_dropped():
    client = _ScriptedSceneClient([_empty_payload(participants=["Shin", "Someone Never Named"])])
    scenes, epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert len(scenes) == 1
    assert scenes[0]["participants"] == ["shinei-nouzen"]
    assert drops["participant_unresolved"] == 1


def test_location_resolved_but_wrong_type_is_dropped():
    """"Shin" resolves fine but is a CHARACTER, not a LOCATION."""
    client = _ScriptedSceneClient([_empty_payload(location="Shin")])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert scenes[0]["location"] is None
    assert drops["location_type_mismatch"] == 1


def test_location_resolves_to_the_right_type():
    client = _ScriptedSceneClient([_empty_payload(location="District One")])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert scenes[0]["location"] == "district-one"
    assert not drops


def test_empty_structured_payload_with_beat_summary_still_produces_a_scene_record():
    """The direct test for the motivating scenario: a quiet passage a mention-window extractor
    would never sample (no relation/attribute fact, zero mentions worth clustering into a
    window) still gets a scene record with a beat summary, because chapter-major coverage does
    not depend on entity mention density at all."""
    client = _ScriptedSceneClient(
        [_empty_payload(beat_summary="Shin and Raiden say nothing, but something has shifted.")]
    )
    scenes, epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert len(scenes) == 1
    assert scenes[0]["beat_summary"] == "Shin and Raiden say nothing, but something has shifted."
    assert scenes[0]["participants"] == []
    assert scenes[0]["state_changes"] == []
    assert scenes[0]["quotes"] == []
    assert epithets == []


def test_state_change_resolves_subject_and_known_predicate():
    payload = _empty_payload(
        state_changes=[
            {
                "subject": "Shin", "predicate": "ENEMY_OF", "from_value": None, "to_value": None,
                "object": "Raiden", "note": "Their friendship breaks down here.",
                "para_id": "v01:c00:p0001", "quote": _QUOTE,
            }
        ]
    )
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert not drops
    sc = scenes[0]["state_changes"][0]
    assert sc["subject"] == "shinei-nouzen"
    assert sc["predicate"] == "ENEMY_OF"
    assert sc["object"] == "raiden-shuga"
    assert sc["note"] == "Their friendship breaks down here."
    assert sc["evidence"] == [{"para_id": "v01:c00:p0001", "print_page": 1, "quote": _QUOTE}]


def test_state_change_with_unrecognized_predicate_keeps_the_note_predicate_null():
    payload = _empty_payload(
        state_changes=[
            {
                "subject": "Shin", "predicate": "MADE_UP_PREDICATE", "note": "Something changed.",
                "para_id": "v01:c00:p0001", "quote": _QUOTE,
            }
        ]
    )
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert not drops
    sc = scenes[0]["state_changes"][0]
    assert sc["predicate"] is None
    assert sc["note"] == "Something changed."


def test_state_change_subject_not_mentioned_is_dropped():
    payload = _empty_payload(
        state_changes=[
            {"subject": "Someone Never Named", "note": "n", "para_id": "v01:c00:p0001", "quote": _QUOTE}
        ]
    )
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert scenes[0]["state_changes"] == []
    assert drops["state_change_subject_unresolved"] == 1


def test_state_change_nonverbatim_quote_is_dropped():
    payload = _empty_payload(
        state_changes=[
            {"subject": "Shin", "note": "n", "para_id": "v01:c00:p0001", "quote": "not in the paragraph at all"}
        ]
    )
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert scenes[0]["state_changes"] == []
    assert drops["quote_not_verbatim"] == 1


def test_quote_speaker_and_addressee_resolve_to_entity_ids():
    payload = _empty_payload(
        quotes=[{"speaker": "Shin", "addressee": "Raiden", "para_id": "v01:c00:p0001", "quote": _QUOTE}]
    )
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert not drops
    q = scenes[0]["quotes"][0]
    assert q["speaker"] == "shinei-nouzen"
    assert q["addressee"] == "raiden-shuga"
    assert q["quote"] == _QUOTE


def test_quote_citation_outside_span_is_dropped():
    payload = _empty_payload(quotes=[{"para_id": "v01:c00:p9999", "quote": _QUOTE}])
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert scenes[0]["quotes"] == []
    assert drops["citation_outside_span"] == 1


def test_quote_cited_from_a_narration_paragraph_is_dropped():
    """Phase 25 item 4: a real corpus bug where the model quoted narrator prose, not dialogue,
    as if it were a spoken line. `ingest/epub.py`'s `speech` classification (CLAUDE.md §3 trap 4)
    is the deterministic signal to catch it -- a "quote" cited from a "narration" paragraph is
    dropped even though the text is genuinely verbatim."""
    records = [dict(r) for r in CHAPTER_RECORDS]
    records[1]["speech"] = "narration"
    payload = _empty_payload(quotes=[{"para_id": "v01:c00:p0001", "quote": _QUOTE}])
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, records, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert scenes[0]["quotes"] == []
    assert drops["quote_not_spoken"] == 1


def test_quote_cited_from_a_dialogue_paragraph_is_kept():
    records = [dict(r) for r in CHAPTER_RECORDS]
    records[1]["speech"] = "dialogue"
    payload = _empty_payload(quotes=[{"speaker": "Shin", "para_id": "v01:c00:p0001", "quote": _QUOTE}])
    client = _ScriptedSceneClient([payload])
    scenes, _epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, records, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert not drops
    assert scenes[0]["quotes"][0]["quote"] == _QUOTE


def test_epithet_resolves_and_is_kept_even_below_confidence_floor():
    """Confidence gating happens later, at gazetteer-merge time (`min_epithet_confidence`) --
    not here. The extraction driver's job is only evidence/resolution validity."""
    payload = _empty_payload(
        epithets=[
            {"entity_id_hint": "Shin", "text": "the reaper", "para_id": "v01:c00:p0001", "quote": _QUOTE, "confidence": 0.1}
        ]
    )
    client = _ScriptedSceneClient([payload])
    _scenes, epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert not drops
    assert len(epithets) == 1
    assert epithets[0] == {
        "entity_id": "shinei-nouzen", "text": "the reaper", "vol": 1, "chapter_idx": 0,
        "para_id": "v01:c00:p0001", "print_page": 1, "quote": _QUOTE,
        "confidence": 0.1, "source": "ollama:test-model",
    }


def test_epithet_referent_not_mentioned_is_dropped():
    payload = _empty_payload(
        epithets=[
            {"entity_id_hint": "Someone Never Named", "text": "the ghost", "para_id": "v01:c00:p0001", "quote": _QUOTE}
        ]
    )
    client = _ScriptedSceneClient([payload])
    _scenes, epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert epithets == []
    assert drops["epithet_referent_unresolved"] == 1


def test_overlapping_spans_dedup_quotes_and_epithets_but_keep_separate_scene_records():
    """Two overlapping spans, both able to see paragraph p0001 -- the second span must not
    re-report the same (para_id, quote)/(entity_id, para_id, text) pair, but each span still
    gets its own scene record."""
    para_text = "word " * 50
    records = [
        {"para_id": f"v01:c00:p{i:04d}", "vol": 1, "chapter_idx": 0, "text": para_text,
         "print_page": None, "scene_break_before": "none"}
        for i in range(6)
    ]
    records[1]["text"] = _QUOTE  # the paragraph both spans will see (core of span0, overlap of span1)
    mentions = [
        {"para_id": records[1]["para_id"], "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin"},
        {"para_id": records[1]["para_id"], "vol": 1, "entity_id": "raiden-shuga", "surface": "Raiden"},
    ]

    class TightSceneSettings(FakeSettings):
        # Tuned so paragraph 0's core group also swallows paragraph 1 (the quote paragraph),
        # and the NEXT span's overlap pulls paragraph 1 back in as trailing context -- i.e. both
        # spans can see it, exactly the situation that needs deduping.
        extraction_behaviour = {
            "scene": {"span_target_tokens": 90, "span_overlap_tokens": 30, "max_tokens_per_request": 6000},
            "max_quote_chars": 240,
        }

    quote_fact = {"para_id": records[1]["para_id"], "quote": _QUOTE}
    epithet_fact = {"entity_id_hint": "Shin", "text": "the reaper", "para_id": records[1]["para_id"], "quote": _QUOTE}
    n_spans = len(SP.build_chapter_spans(1, 0, records, TightSceneSettings.extraction_behaviour["scene"]))
    payloads = [_empty_payload(quotes=[quote_fact], epithets=[epithet_fact]) for _ in range(2)]
    payloads += [_empty_payload() for _ in range(n_spans - 2)]
    client = _ScriptedSceneClient(payloads)
    scenes, epithets, _claims, drops = SC.extract_chapter_scenes(
        1, 0, records, mentions, ENTITIES_BY_ID, TightSceneSettings(), client
    )
    assert len(scenes) >= 2
    assert len({s["scene_id"] for s in scenes}) == len(scenes)  # every span kept its own scene_id
    total_quotes = sum(len(s["quotes"]) for s in scenes)
    assert total_quotes == 1
    assert len(epithets) == 1
    assert drops["duplicate_quote_across_spans"] >= 1
    assert drops["duplicate_epithet_across_spans"] >= 1


class _RecordingSceneClient(_ScriptedSceneClient):
    """Same scripting as `_ScriptedSceneClient`, but also records each call's `schema` and
    `prompt` so a test can verify the two-call split (Phase 22 B1) without re-deriving it from
    the returned scene records alone."""

    def __init__(self, payloads_by_call: list[dict]):
        super().__init__(payloads_by_call)
        self.seen_schemas: list[type] = []
        self.seen_prompts: list[str] = []

    def complete_json(self, stage, prompt, schema, system=None, options=None):
        self.seen_schemas.append(schema)
        self.seen_prompts.append(prompt)
        return super().complete_json(stage, prompt, schema, system=system, options=options)


def test_each_span_makes_exactly_two_calls_beat_then_detail():
    """Phase 22 B1: 56 -> 112 calls -- one span is now a beat call plus a detail call, not one
    combined call."""
    client = _RecordingSceneClient([_empty_payload()])
    SC.extract_chapter_scenes(1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    assert client.calls == 2
    assert client.seen_schemas == [SS.SceneBeatResult, SS.SceneDetailResult]


def test_beat_and_detail_calls_share_the_same_known_entities_and_passage_text():
    """"Same text, cached prefix" (Phase 22 B1) -- both calls for one span must be built from the
    identical passage/known-entities prefix so a caching provider reuses it, diverging only in
    the final "Report ..." instruction line."""
    client = _RecordingSceneClient([_empty_payload()])
    SC.extract_chapter_scenes(1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    beat_prompt, detail_prompt = client.seen_prompts
    known_line = "Known entities in this chapter: District One, Raiden Shuga, Shinei Nouzen"
    assert known_line in beat_prompt
    assert known_line in detail_prompt
    assert beat_prompt != detail_prompt


def test_known_entities_line_groups_two_alias_mentions_of_one_entity_into_one_name():
    """Phase 22 B2 (fixes S3): the same grouping fix applied to claims.py's user prompt."""
    mentions = CHAPTER_MENTIONS + [
        {"para_id": "v01:c00:p0001", "vol": 1, "entity_id": "raiden-shuga", "surface": "Shuga"},
    ]
    entities_by_id = {
        **ENTITIES_BY_ID,
        "raiden-shuga": {**ENTITIES_BY_ID["raiden-shuga"], "aliases": ["Raiden Shuga", "Raiden", "Shuga"]},
    }
    client = _RecordingSceneClient([_empty_payload()])
    SC.extract_chapter_scenes(1, 0, CHAPTER_RECORDS, mentions, entities_by_id, FakeSettings(), client)
    beat_prompt = client.seen_prompts[0]
    assert "Raiden Shuga (also: Raiden, Shuga)" in beat_prompt


def test_extract_volume_scenes_aggregates_across_chapters():
    records = CHAPTER_RECORDS + [
        {"para_id": "v01:c01:p0000", "vol": 1, "chapter_idx": 1, "text": "Another chapter entirely.",
         "print_page": 2, "scene_break_before": "none"},
    ]
    mentions = CHAPTER_MENTIONS
    client = _ScriptedSceneClient([_empty_payload(), _empty_payload()])
    progress_calls = []
    scenes, epithets, _claims, drops = SC.extract_volume_scenes(
        1, records, mentions, list(ENTITIES_BY_ID.values()), FakeSettings(), client,
        on_progress=lambda i, total, chapter_idx, n: progress_calls.append((i, total, chapter_idx, n)),
    )
    assert len(scenes) == 2  # one span per chapter, one chapter has zero mentions but still runs
    assert epithets == []
    assert not drops
    assert progress_calls == [(1, 2, 0, 1), (2, 2, 1, 1)]


# ---------------------------------------------------------------------------
# scenes.py -- Phase 22 C1: participant_facts -> claims
# ---------------------------------------------------------------------------


def test_participant_fact_attribute_builds_a_claim_dict():
    payload = _empty_payload(
        participant_facts=[
            {
                "subject": "Shin",
                "facts": [
                    {
                        "predicate": "AGE", "kind": "attribute", "value": "18", "para_id": "v01:c00:p0001",
                        "quote": _QUOTE, "confidence": 0.9, "polarity": "asserted",
                    }
                ],
            }
        ]
    )
    client = _ScriptedSceneClient([payload])
    _scenes, _epithets, claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert not drops
    assert len(claims) == 1
    claim = claims[0]
    assert claim["subject"] == "shinei-nouzen"
    assert claim["predicate"] == "AGE"
    assert claim["kind"] == "attribute"
    assert claim["value"] == "18"
    assert claim["first_vol"] == 1
    assert claim["evidence"] == [{"para_id": "v01:c00:p0001", "print_page": 1, "quote": _QUOTE}]


def test_participant_fact_relation_resolves_object_against_chapter_mentions():
    payload = _empty_payload(
        participant_facts=[
            {
                "subject": "Shin",
                "facts": [
                    {
                        "predicate": "ENEMY_OF", "kind": "relation", "object": "Raiden",
                        "para_id": "v01:c00:p0001", "quote": _QUOTE, "confidence": 0.9,
                    }
                ],
            }
        ]
    )
    client = _ScriptedSceneClient([payload])
    _scenes, _epithets, claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert not drops
    assert claims[0]["object"] == "raiden-shuga"


def test_participant_fact_subject_not_mentioned_in_chapter_is_dropped():
    payload = _empty_payload(
        participant_facts=[
            {
                "subject": "Someone Never Named",
                "facts": [
                    {
                        "predicate": "AGE", "kind": "attribute", "value": "18", "para_id": "v01:c00:p0001",
                        "quote": _QUOTE, "confidence": 0.9,
                    }
                ],
            }
        ]
    )
    client = _ScriptedSceneClient([payload])
    _scenes, _epithets, claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert claims == []
    assert drops["participant_fact_subject_unresolved"] == 1


def test_participant_fact_unknown_predicate_is_dropped():
    payload = _empty_payload(
        participant_facts=[
            {
                "subject": "Shin",
                "facts": [
                    {
                        "predicate": "MADE_UP", "kind": "attribute", "value": "x", "para_id": "v01:c00:p0001",
                        "quote": _QUOTE, "confidence": 0.9,
                    }
                ],
            }
        ]
    )
    client = _ScriptedSceneClient([payload])
    _scenes, _epithets, claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert claims == []
    assert drops["unknown_predicate"] == 1


def test_participant_fact_nonverbatim_quote_is_dropped():
    payload = _empty_payload(
        participant_facts=[
            {
                "subject": "Shin",
                "facts": [
                    {
                        "predicate": "AGE", "kind": "attribute", "value": "18", "para_id": "v01:c00:p0001",
                        "quote": "not in the paragraph at all", "confidence": 0.9,
                    }
                ],
            }
        ]
    )
    client = _ScriptedSceneClient([payload])
    _scenes, _epithets, claims, drops = SC.extract_chapter_scenes(
        1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client
    )
    assert claims == []
    assert drops["quote_not_verbatim"] == 1


def test_extract_volume_scenes_merges_the_same_claim_across_chapters():
    """Same fact independently (re)stated in two different chapters of the same volume merges
    into one claim by claim_id, combining evidence -- mirrors claims.py's cross-window merge."""
    records = CHAPTER_RECORDS + [
        {"para_id": "v01:c01:p0000", "vol": 1, "chapter_idx": 1, "text": _QUOTE,
         "print_page": 2, "scene_break_before": "none"},
    ]
    mentions = CHAPTER_MENTIONS + [
        {"para_id": "v01:c01:p0000", "vol": 1, "entity_id": "shinei-nouzen", "surface": "Shin"},
    ]
    fact = {
        "predicate": "AGE", "kind": "attribute", "value": "18", "confidence": 0.9,
    }
    payload_c0 = _empty_payload(
        participant_facts=[{"subject": "Shin", "facts": [{**fact, "para_id": "v01:c00:p0001", "quote": _QUOTE}]}]
    )
    payload_c1 = _empty_payload(
        participant_facts=[{"subject": "Shin", "facts": [{**fact, "para_id": "v01:c01:p0000", "quote": _QUOTE}]}]
    )
    client = _ScriptedSceneClient([payload_c0, payload_c1])
    _scenes, _epithets, claims, drops = SC.extract_volume_scenes(
        1, records, mentions, list(ENTITIES_BY_ID.values()), FakeSettings(), client
    )
    assert not drops
    assert len(claims) == 1
    assert len(claims[0]["evidence"]) == 2


def test_detail_system_prompt_includes_attribute_relation_trait_vocab():
    client = _RecordingSceneClient([_empty_payload()])
    SC.extract_chapter_scenes(1, 0, CHAPTER_RECORDS, CHAPTER_MENTIONS, ENTITIES_BY_ID, FakeSettings(), client)
    _beat_prompt, detail_prompt = client.seen_prompts
    detail_system = SC._detail_system_prompt(FakeSettings())
    assert "AGE" in detail_system
    assert "ENEMY_OF" in detail_system
    assert "PARTICIPANT_FACTS" in detail_system


def test_detail_system_prompt_warns_against_sarcasm_and_lies_as_fact():
    """Phase 25 item 6: a character's own sarcastic/boastful/joking line must not become an
    "asserted" fact just because it is phrased as a direct statement -- the fix reuses the
    existing "presumed" polarity rather than inventing new schema, so the guidance lives in the
    prompt, not in scene_schema.py."""
    detail_system = SC._detail_system_prompt(FakeSettings())
    assert "sarcasm" in detail_system.lower()
    assert "presumed" in detail_system.lower()


def test_detail_system_prompt_warns_narration_not_quotable():
    """Phase 25 item 4: the prompt must tell the model a quote's text excludes the narrator's
    attribution tag ("she shot back") -- the deterministic `speech`-classification filter in
    `_build_quote` is the backstop, not the only line of defense."""
    detail_system = SC._detail_system_prompt(FakeSettings())
    assert "narration" in detail_system.lower()


def test_a_span_crossing_a_scene_break_may_answer_with_one_beat_per_scene():
    """[30] Overlord's spans cross hard POV breaks; the model answers with a list of beats, and
    every such span used to fail validation three times. The beats fold into the span's record."""
    from narrativewiki.extract.scene_schema import SceneBeatResult

    beat = SceneBeatResult.model_validate([
        {"participants": ["Ainz", "Albedo"], "location": "Throne Room",
         "beat_summary": "Momonga waits for the servers to close.", "confidence": 1.0},
        {"participants": ["Enri", "Ainz"], "location": None,
         "beat_summary": "Enri tends her family's field.", "confidence": 0.8},
    ])
    assert beat.participants == ["Ainz", "Albedo", "Enri"]
    assert beat.location == "Throne Room"
    assert beat.beat_summary == "Momonga waits for the servers to close. Enri tends her family's field."
    assert beat.confidence == 0.8


def test_a_quote_inside_a_narration_led_paragraphs_dialogue_is_spoken():
    """[30] Speech is classified per paragraph by how it opens, so a line of dialogue after a
    speech tag was dropped as narration: 234 quotes in Overlord v1, 99 in Spice and Wolf v1."""
    from narrativewiki.extract.resolve import within_dialogue

    para = "Momonga took it as a bow and said, “Don’t worry about it, HeroHero.”"
    assert within_dialogue("Don’t worry about it, HeroHero.", para)
    assert not within_dialogue("Momonga took it as a bow", para)
    assert within_dialogue("the speech runs on", "He began, “and the speech runs on")  # unclosed
