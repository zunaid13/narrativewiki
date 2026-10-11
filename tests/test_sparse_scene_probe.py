"""The isolated probe must preserve production resolution, citation and polarity gates,
and B1's controlled prompt must differ from B0 in exactly one way."""
from collections import Counter
from types import SimpleNamespace

import pytest

from scripts.eval.probe_sparse_scene import (
    B0_INSTRUCTION, B1_INSTRUCTION, B2_INSTRUCTION, VARIANTS,
    score, score_against_fixture,
)
from narrativewiki.extract.scene_schema import SceneDetailResult
from narrativewiki.extract.scenes import _detail_user_prompt, _user_prefix
from narrativewiki.extract.spans import Span


# --- Shared replay helper ---

def replay(quote=None, text=None):
    text = text or "Records describe Saint Ruvinheigen as having red hair."
    pid = "v02:c00:p0148"
    records = {pid: {"para_id": pid, "vol": 2, "chapter_idx": 0, "text": text}}
    span = Span(2, 0, 0, (pid,), (pid,), f"[{pid}] {text}")
    mentions = [{"entity_id": "saint-ruvinheigen", "surface": "Saint Ruvinheigen", "para_id": pid}]
    entities = {"saint-ruvinheigen": {"canonical": "Saint Ruvinheigen", "type": "CHARACTER"}}
    settings = SimpleNamespace(attributes={"APPEARANCE": {}}, relations={}, traits={},
        extraction_behaviour={"evidence_adequacy": {"subject_must_be_named": True}})
    detail = SceneDetailResult.model_validate({"participant_facts": [{
        "subject": "Saint Ruvinheigen", "facts": [{"predicate": "APPEARANCE", "kind": "attribute",
            "value": "red hair", "para_id": pid, "quote": quote or text,
            "polarity": "presumed", "confidence": 0.9}]}]})
    return score(detail, span, mentions, records, entities, settings)


# --- Original gate tests (preserved from the prior version) ---

def test_probe_retains_reported_polarity_and_evidence_volume():
    result = replay()
    assert result["unique_claims"] == 1
    claim = result["accepted"][0]
    assert claim["polarity"] == "presumed"
    assert claim["first_vol"] == 2
    assert claim["evidence"][0]["para_id"] == "v02:c00:p0148"


def test_probe_rejects_subject_known_in_chapter_but_absent_from_passage():
    result = replay(text="Records describe an unnamed man as having red hair.")
    assert result["unique_claims"] == 0
    assert result["drops"] == {"participant_fact_subject_unresolved": 1}


def test_probe_rejects_invented_quote():
    result = replay(quote="Saint Ruvinheigen had blue hair.")
    assert result["unique_claims"] == 0
    assert result["drops"] == {"quote_not_verbatim": 1}


# --- B1 variant isolation tests ---

def test_b1_instruction_differs_only_in_participant_facts():
    """B1 adds exactly ', and participant_facts' relative to B0 — nothing else changes."""
    # B0 ends with "...and epithets for this passage."
    # B1 ends with "...epithets, and participant_facts for this passage."
    assert "participant_facts" not in B0_INSTRUCTION
    assert "participant_facts" in B1_INSTRUCTION
    # The difference should be minimal — B1 is B0 with participant_facts inserted.
    # Verify by checking that removing the insertion restores B0.
    restored = B1_INSTRUCTION.replace(
        "epithets, and participant_facts", "and epithets"
    )
    assert restored == B0_INSTRUCTION, (
        f"B1 differs from B0 beyond the participant_facts insertion:\n"
        f"  B0: {B0_INSTRUCTION!r}\n"
        f"  B1: {B1_INSTRUCTION!r}\n"
        f"  restored: {restored!r}"
    )


def test_variant_prompts_share_prefix_with_production():
    """Every variant builds its prompt as _user_prefix + instruction, so the model always
    sees the same passage, entities, and volume context — only the trailing instruction differs."""
    pid = "v02:c00:p0148"
    text = "Test passage."
    span = Span(2, 0, 0, (pid,), (pid,), f"[{pid}] {text}")
    mentions = [{"entity_id": "test-entity", "surface": "Test", "para_id": pid}]
    entities = {"test-entity": {"canonical": "Test", "type": "CHARACTER"}}

    prefix = _user_prefix(2, 0, span, mentions, entities)
    production = _detail_user_prompt(2, 0, span, mentions, entities)

    # Production prompt must equal prefix + B0 instruction.
    assert production == prefix + B0_INSTRUCTION, (
        "Production _detail_user_prompt has diverged from prefix + B0_INSTRUCTION"
    )

    # Every variant's prompt starts with the same prefix.
    for label, instruction in VARIANTS.items():
        full_prompt = prefix + instruction
        assert full_prompt.startswith(prefix), f"{label} does not share the production prefix"
        assert full_prompt.endswith(instruction), f"{label} does not end with its instruction"


# --- Fixture scoring tests ---

def test_fixture_scoring_counts_recovery_and_precision(tmp_path):
    """A synthetic fixture and synthetic claims produce correct recovery/precision counts."""
    fixture = {
        "fixture": "test",
        "facts": [
            {"id": "F1", "subject": "saint-ruvinheigen", "predicate_family": "APPEARANCE",
             "status": "missing", "split": "dev", "para_id": "v02:c00:p0148",
             "quote": "red hair", "cutoff": 2, "polarity": "asserted"},
            {"id": "F2", "subject": "saint-ruvinheigen", "predicate_family": "STATUS",
             "status": "must_not_assert", "split": "dev", "para_id": "v02:c00:p0148",
             "quote": "alive", "cutoff": 2, "polarity": "denied",
             "forbidden_value": "alive"},
            {"id": "F3", "subject": "saint-ruvinheigen", "predicate_family": "TITLE",
             "status": "already_covered", "split": "dev", "para_id": "v02:c00:p0148",
             "quote": "Saint", "cutoff": 2, "polarity": "asserted",
             "covered_by_claim_id": "c_existing"},
            {"id": "F4", "subject": "saint-ruvinheigen", "predicate_family": "HISTORY",
             "status": "missing", "split": "holdout", "para_id": "v02:c00:p0148",
             "quote": "battle", "cutoff": 2, "polarity": "asserted"},
        ],
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    # Claims that match F1 (APPEARANCE=missing) and F2 (STATUS=must_not_assert)
    ev = [{"para_id": "v02:c00:p0148"}]
    claims = [
        {"subject": "saint-ruvinheigen", "predicate": "APPEARANCE", "claim_id": "c_new1",
         "value": "red hair", "evidence": ev},
        {"subject": "saint-ruvinheigen", "predicate": "STATUS", "claim_id": "c_new2",
         "value": "alive", "evidence": ev},
    ]

    result = score_against_fixture(claims, fixture_path)
    assert [c["fact_id"] for c in result["candidate_recovered"]] == ["F1"]
    assert result["precision_violated"] == ["F2"]
    assert result["reconfirmed"] == []  # TITLE not claimed
    assert result["unmatched_missing"] == []  # F1 was recovered; F4 is holdout, invisible
    assert result["dev_facts_total"] == 3  # F4 is holdout
    assert result["dev_missing_total"] == 1  # only F1 in dev
    assert result["dev_must_not_assert_total"] == 1


def test_holdout_facts_never_scored(tmp_path):
    """Holdout facts must be invisible to fixture scoring — even if a claim matches them."""
    fixture = {
        "fixture": "test",
        "facts": [
            {"id": "H1", "subject": "saint-ruvinheigen", "predicate_family": "HISTORY",
             "status": "missing", "split": "holdout", "para_id": "v02:c00:p0148",
             "quote": "battle", "cutoff": 2, "polarity": "asserted"},
        ],
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    # A claim that would match H1 if it were dev
    claims = [
        {"subject": "saint-ruvinheigen", "predicate": "BACKGROUND", "claim_id": "c_hist",
         "value": "fought the pagan gods", "evidence": [{"para_id": "v02:c00:p0148"}]},
    ]

    result = score_against_fixture(claims, fixture_path)
    assert result["candidate_recovered"] == []
    assert result["precision_violated"] == []
    assert result["dev_facts_total"] == 0
    assert result["dev_missing_total"] == 0


# Need json for fixture scoring tests
import json


# ---------------------------------------------------------------------------
# The scorer has to survive its own use: these three ways of being wrong would each
# have turned the one approval-gated call into an unusable answer.
# ---------------------------------------------------------------------------


def _one_fact_fixture(tmp_path, **overrides):
    fact = {"id": "F1", "subject": "saint-ruvinheigen", "predicate_family": "STATUS",
            "status": "must_not_assert", "split": "dev", "para_id": "v02:c00:p0145",
            "quote": "hundreds of years ago", "cutoff": 2, "polarity": "denied",
            "forbidden_value": "alive"}
    fact.update(overrides)
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps({"fixture": "test", "facts": [fact]}), encoding="utf-8")
    return path


def _status_claim(value):
    return [{"subject": "saint-ruvinheigen", "predicate": "STATUS", "claim_id": "c_1",
             "value": value, "evidence": [{"para_id": "v02:c00:p0145"}]}]


def test_precision_control_fires_on_the_forbidden_value_not_the_family(tmp_path):
    """R8 says the page must not call a centuries-dead saint `alive`. Matching on the STATUS
    family instead scored the FIX as the violation: a claim correctly recording him as long
    dead was reported as a precision regression, which would have rejected a winning candidate."""
    fixture_path = _one_fact_fixture(tmp_path)
    assert score_against_fixture(_status_claim("alive"), fixture_path)["precision_violated"] == ["F1"]
    assert score_against_fixture(_status_claim("long dead"), fixture_path)["precision_violated"] == []


def test_must_not_assert_without_a_forbidden_value_is_refused(tmp_path):
    """Silently falling back to family matching is how the inverted control got shipped."""
    fixture_path = _one_fact_fixture(tmp_path, forbidden_value=None)
    with pytest.raises(ValueError, match="forbidden_value"):
        score_against_fixture(_status_claim("alive"), fixture_path)


def test_a_candidate_must_cite_the_paragraph_the_fact_was_read_from(tmp_path):
    """Same subject and same family in a different paragraph is a different fact."""
    fixture_path = _one_fact_fixture(
        tmp_path, status="missing", predicate_family="HISTORY", para_id="v02:c00:p0149",
        forbidden_value=None, quote="in his battles against the heathen deities")
    claim = {"subject": "saint-ruvinheigen", "predicate": "BACKGROUND", "claim_id": "c_1",
             "value": "fought the pagan gods", "evidence": [{"para_id": "v02:c00:p0149"}]}
    hit = score_against_fixture([claim], fixture_path)
    assert [c["fact_id"] for c in hit["candidate_recovered"]] == ["F1"]
    # The reviewer, not the scorer, decides whether this really is the fact.
    assert hit["candidate_recovered"][0]["adjudicated"] is None
    assert hit["candidate_recovered"][0]["fixture_quote"].startswith("in his battles")
    elsewhere = dict(claim, evidence=[{"para_id": "v02:c03:p0025"}])
    assert score_against_fixture([elsewhere], fixture_path)["unmatched_missing"] == ["F1"]


def test_inbound_credit_is_only_for_relationship_predicates(tmp_path):
    """`ORIGIN_FROM pasloe` (family GOVERNS) used to register as a RELATIONSHIP of Pasloe,
    because every claim carrying an object was filed under the object's RELATIONSHIP key."""
    fixture_path = _one_fact_fixture(
        tmp_path, subject="pasloe", predicate_family="RELATIONSHIP", status="missing",
        para_id="v01:c02:p0069", forbidden_value=None, quote="managed the region")
    claim = {"subject": "count-ehrendott", "predicate": "ORIGIN_FROM", "claim_id": "c_1",
             "object": "pasloe", "value": None, "evidence": [{"para_id": "v01:c02:p0069"}]}
    assert score_against_fixture([claim], fixture_path)["unmatched_missing"] == ["F1"]
    rel = dict(claim, predicate="ENEMY_OF")
    assert [c["fact_id"] for c in
            score_against_fixture([rel], fixture_path)["candidate_recovered"]] == ["F1"]


def test_a_predicate_the_map_has_never_seen_is_reported_not_dropped(tmp_path):
    """The family map copies a vocabulary that lives in config/extraction.yaml, which any series
    may extend through its own overlay. An unknown predicate used to vanish from scoring."""
    fixture_path = _one_fact_fixture(
        tmp_path, status="missing", predicate_family="DIVINE_ROLE", para_id="v02:c00:p0149",
        forbidden_value=None, quote="god of the harvest")
    claim = {"subject": "saint-ruvinheigen", "predicate": "DIVINE_ROLE", "claim_id": "c_1",
             "value": "god of the harvest", "evidence": [{"para_id": "v02:c00:p0149"}]}
    result = score_against_fixture([claim], fixture_path)
    assert [c["fact_id"] for c in result["candidate_recovered"]] == ["F1"]
    assert result["unmapped_predicates"] == ["DIVINE_ROLE"]
