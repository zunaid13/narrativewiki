"""Controlled scene-prompt comparison on one stored Spice and Wolf v2 passage.

Work package B (docs/vision/plans/0006): isolate prompt changes as controlled variants.
B0 = current production user instruction.  B1 = add only participant_facts.
B2 = B1 plus offstage/historical characters (the old bundled CANDIDATE).

Default prepares inputs only; --execute makes cached/budgeted calls through LLMClient.
Does not modify extraction outputs, graph, pages, or production prompts. A passing gate
is not an entailment judgment. Inspect accepted claims before promoting a candidate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from narrativewiki import paths, provenance
from narrativewiki.config import load_settings
from narrativewiki.extract.resolve import resolve_surface
from narrativewiki.extract.scene_schema import SceneDetailResult
from narrativewiki.extract.scenes import (
    STAGE, _DETAIL_GENERATION_OPTIONS, _build_participant_fact,
    _detail_system_prompt, _detail_user_prompt, _user_prefix,
)
from narrativewiki.extract.spans import Span, _format_span
from narrativewiki.llm.client import LLMClient

SOURCE_RUN = "20260922T211717-scenes-v1-2"
ANCHOR = "v02:c00:p0148"

# --- Variant instructions (final line of the user prompt, after the shared prefix) ---

# B0: current production instruction — verbatim from _detail_user_prompt.
B0_INSTRUCTION = "Report state changes, quotes, and epithets for this passage."

# B1: add only participant_facts — isolates the missing-output-family hypothesis.
B1_INSTRUCTION = (
    "Report state changes, quotes, epithets, and participant_facts for this passage."
)

# B2: B1 plus offstage/historical character coverage — isolates the offstage hypothesis.
# This is the old bundled CANDIDATE, now labeled for what it tests.
B2_INSTRUCTION = (
    "Report state_changes, quotes, epithets, and participant_facts for this passage. "
    "For participant_facts, check every named character the passage describes, including "
    "characters discussed in history or recollections who are not physically present. "
    "Extract only supported facts; an empty facts list is correct when nothing is supported. "
    "Keep reported beliefs, legends, speculation, and hypotheticals distinct from asserted facts."
)

VARIANTS = {"B0": B0_INSTRUCTION, "B1": B1_INSTRUCTION, "B2": B2_INSTRUCTION}

FIXTURE_PATH = (ROOT / "docs/eval").joinpath("fixtures") / "sparse_character_evidence.json"

# --- Predicate-family matching ---
# The fixture uses broad predicate_family labels; the extractor uses specific predicate names.
# This maps each extraction predicate to the fixture family it could satisfy.  A claim matches
# a fixture fact when (subject, mapped_family) == (fixture_subject, fixture_predicate_family).
# Families that have no extraction predicate (HISTORY, DEPICTION, NAMESAKE, INFLUENCE,
# REPUTATION, PATRONAGE, GOVERNS) cannot be matched automatically — they appear in the fixture
# as gaps the current vocabulary cannot encode.  This is correct: a B1 win on those requires
# either a new predicate (out of scope) or a BACKGROUND trait covering the narrative content.
_PREDICATE_TO_FAMILY: dict[str, str] = {
    "TITLE": "TITLE", "OCCUPATION": "OCCUPATION", "APPEARANCE": "APPEARANCE",
    "STATUS": "STATUS", "PERSONALITY": "PERSONALITY", "MOTIVATION": "PERSONALITY",
    "SKILL": "PERSONALITY", "BACKGROUND": "HISTORY",  # see _NARRATIVE_FAMILIES below
    "AFFILIATED_WITH": "AFFILIATION", "ORIGIN_FROM": "GOVERNS",
    "ENEMY_OF": "RELATIONSHIP", "RIVAL_OF": "RELATIONSHIP", "FRIEND_OF": "RELATIONSHIP",
    "MENTOR_OF": "RELATIONSHIP", "STUDENT_OF": "RELATIONSHIP", "SPOUSE_OF": "RELATIONSHIP",
    "PARENT_OF": "RELATIONSHIP", "CHILD_OF": "RELATIONSHIP", "SIBLING_OF": "RELATIONSHIP",
    "RELATIVE_OF": "RELATIONSHIP", "ROMANTIC_WITH": "RELATIONSHIP",
    "COMMANDS": "RELATIONSHIP", "SERVES_UNDER": "RELATIONSHIP", "COMRADE_OF": "RELATIONSHIP",
    "PARTICIPATED_IN": "HISTORY", "KILLED": "HISTORY", "SAVED": "HISTORY",
    "AGE": "APPEARANCE", "GENDER": "APPEARANCE", "RANK": "TITLE", "NICKNAME": "TITLE",
    "ORIGIN": "ORIGIN", "FEAR": "PERSONALITY",
}


# Families the fixture uses for narrative content that has no dedicated predicate. BACKGROUND
# ("a biographical fact, not a narrative", max 20 words -- config/extraction.yaml) is the only
# thing in the vocabulary that can carry them, so a genuine recovery of "a pilgrimage road is
# named after him" or "he is pictured on the cathedral mural" can only ever arrive as BACKGROUND.
# Sending BACKGROUND to HISTORY alone made five of the seven dev gaps unreachable by construction
# and capped any B1 result at 2 of 7 before a single call was made. A BACKGROUND claim is a
# candidate for all of them; the reviewer reads its value against the fixture quote and decides.
_NARRATIVE_FAMILIES = frozenset({
    "HISTORY", "DEPICTION", "NAMESAKE", "INFLUENCE", "REPUTATION", "PATRONAGE", "GOVERNS",
})


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(detail, span, mentions, records, entities, settings):
    """Same resolution and fact gates as production; retain every rejected witness."""
    accepted, rejected = [], []
    totals = Counter()
    for group in detail.participant_facts:
        subject = resolve_surface(group.subject, mentions, span.text)
        for fact in group.facts:
            drops = Counter()
            claim = None
            if subject is None:
                drops["participant_fact_subject_unresolved"] += 1
            else:
                claim = _build_participant_fact(subject, fact, span, mentions, records,
                    entities, settings, "stored-prompt-probe", drops)
            if claim:
                accepted.append(claim)
            else:
                rejected.append({"subject": group.subject, "fact": fact.model_dump(), "drops": dict(drops)})
                totals.update(drops)
    return {"accepted": accepted, "rejected": rejected, "drops": dict(totals),
            "unique_claims": len({c["claim_id"] for c in accepted}),
            "subjects": dict(Counter(c["subject"] for c in accepted))}


def score_against_fixture(accepted_claims: list[dict], fixture_path: Path = FIXTURE_PATH):
    """Score a variant's accepted claims against the frozen dev-split fixture facts.

    `candidate_recovered` is NOT a measurement, and is named so no one reads it as one. The
    fixture's families are coarser than the facts they label: R3 (his battles), R4 (the cathedral
    mural) and R5 (the city named for him) would all arrive as BACKGROUND claims citing the same
    paragraph, and no automatic rule separates them. Matching on family alone both credits the
    wrong fact and hides the right one -- a BACKGROUND claim about the mural used to report
    "recovered R3" while R4 stayed unmatched. Each candidate therefore carries the claim's own
    value beside the reviewed quote, and a human decides. docs/vision/plans/0006 says the decision metric
    is "manually supported, semantically new facts ... paraphrases can have new IDs."

    `precision_violated` IS decidable automatically, because each must_not_assert fact names the
    value it forbids. Matching those on family instead scored the fix as the violation: a claim
    correctly recording Saint Ruvinheigen as long dead tripped R8, whose whole point is that the
    page must not call him *alive*.

    Returns a dict with:
      candidate_recovered: [{fact_id, claim_id, predicate, value, fixture_quote}] for human review
      precision_violated: fixture fact IDs (status=must_not_assert) whose forbidden value appeared
      reconfirmed: fixture fact IDs (status=already_covered/covered_with_defect) matched
      unmatched_missing: missing fixture fact IDs with no candidate at all
      claim_families: {subject: {family: count}} for manual inspection
    """
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    dev_facts = [f for f in fixture["facts"] if f["split"] == "dev"]

    # Build claim coverage: (subject, family) -> the claims themselves, not just their ids --
    # the value is what a reviewer needs to judge whether a fact was really recovered.
    claim_coverage: dict[tuple[str, str], list[dict]] = {}
    unmapped: set[str] = set()
    for claim in accepted_claims:
        # `_PREDICATE_TO_FAMILY` is a copy of a vocabulary that lives in config/extraction.yaml,
        # which every series may extend or replace through its own overlay
        # (paths.extraction_overlay_config). A predicate this map has never heard of used to be
        # dropped from scoring silently, so a new predicate would quietly stop counting. Fall
        # back to the predicate's own name as the family -- it still matches a fixture family
        # spelled the same -- and report what was unmapped so the gap is visible, not silent.
        family = _PREDICATE_TO_FAMILY.get(claim["predicate"], claim["predicate"])
        if claim["predicate"] not in _PREDICATE_TO_FAMILY:
            unmapped.add(claim["predicate"])
        if family:
            claim_coverage.setdefault((claim["subject"], family), []).append(claim)
        # Inbound: a relationship claim reaches the OBJECT's page too (Ruvinheigen's "Enemy of
        # Holo" has Holo as subject). Only for relationship predicates -- keying every claim with
        # an object under RELATIONSHIP filed ORIGIN_FROM pasloe as a relationship of Pasloe.
        if claim.get("object") and family == "RELATIONSHIP":
            claim_coverage.setdefault((claim["object"], "RELATIONSHIP"), []).append(claim)
        if claim["predicate"] == "BACKGROUND":
            for narrative in _NARRATIVE_FAMILIES - {family}:  # HISTORY is already filed above
                claim_coverage.setdefault((claim["subject"], narrative), []).append(claim)

    candidate_recovered, precision_violated, reconfirmed, unmatched_missing = [], [], [], []
    for fact in dev_facts:
        hits = claim_coverage.get((fact["subject"], fact["predicate_family"]), [])
        if fact["status"] == "missing":
            # A claim only stands as a candidate for this fact if it cites the paragraph the
            # reviewer read it from. Same family, other paragraph, is a different fact.
            cited = [c for c in hits
                     if fact["para_id"] in {e.get("para_id") for e in c.get("evidence", [])}]
            for claim in cited:
                candidate_recovered.append({
                    "fact_id": fact["id"], "claim_id": claim["claim_id"],
                    "predicate": claim["predicate"], "value": claim.get("value"),
                    "object": claim.get("object"), "fixture_quote": fact["quote"],
                    "adjudicated": None,  # a human fills this in; never scored as a win until then
                })
            if not cited:
                unmatched_missing.append(fact["id"])
        elif fact["status"] == "must_not_assert":
            forbidden = fact.get("forbidden_value")
            if not forbidden:
                raise ValueError(
                    f"{fact['id']}: a must_not_assert fact needs `forbidden_value`; without it "
                    "the control fires on the whole predicate family and scores the fix as the bug."
                )
            if any(forbidden.lower() in str(c.get("value") or c.get("object") or "").lower()
                   for c in hits):
                precision_violated.append(fact["id"])
        elif fact["status"] in ("already_covered", "covered_with_defect"):
            if hits:
                reconfirmed.append(fact["id"])

    # Per-subject family breakdown for manual review
    claim_families: dict[str, dict[str, int]] = {}
    for claim in accepted_claims:
        family = _PREDICATE_TO_FAMILY.get(claim["predicate"], claim["predicate"])
        claim_families.setdefault(claim["subject"], {})
        claim_families[claim["subject"]][family] = claim_families[claim["subject"]].get(family, 0) + 1

    return {
        "unmapped_predicates": sorted(unmapped),
        "candidate_recovered": candidate_recovered,
        "precision_violated": precision_violated,
        "reconfirmed": reconfirmed,
        "unmatched_missing": unmatched_missing,
        "claim_families": claim_families,
        "dev_facts_total": len(dev_facts),
        "dev_missing_total": len([f for f in dev_facts if f["status"] == "missing"]),
        "dev_must_not_assert_total": len([f for f in dev_facts if f["status"] == "must_not_assert"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--variant", choices=["B0", "B1", "B2", "all"], default="all",
                        help="Which variant(s) to prepare/execute (default: all)")
    args = parser.parse_args()
    selected = list(VARIANTS) if args.variant == "all" else [args.variant]

    paths.set_active_series("spice-and-wolf")
    settings = load_settings("spice-and-wolf")
    calls_path = paths.run_dir(SOURCE_RUN) / "calls.jsonl"
    candidates = [c for c in read_jsonl(calls_path) if c.get("stage") == STAGE
                  and f"[{ANCHOR}]" in c["prompt"] and "participant_facts" in c["response"]]
    if len(candidates) != 1:
        raise ValueError("Expected exactly one recorded detail response containing the anchor")
    recorded = candidates[0]
    ids = tuple(re.findall(r"^\[(v\d+:c\d+:p\d+)\]", recorded["prompt"], re.MULTILINE))
    if not ids or any(not pid.startswith("v02:c00:") for pid in ids):
        raise ValueError("Probe must remain scoped to volume 2 chapter 0")
    records = {r["para_id"]: r for r in read_jsonl(paths.parsed_volume(2))}
    passage = _format_span([records[pid] for pid in ids], 0, len(ids) - 1)
    if passage not in recorded["prompt"]:
        raise ValueError("Recorded passage differs from current parsed text")
    span = Span(2, 0, 0, ids, ids, passage)
    mentions = [m for m in read_jsonl(paths.mentions()) if m["para_id"].startswith("v02:c00:")]
    entities = {e["entity_id"]: e for e in json.loads(paths.gazetteer().read_text(encoding="utf-8"))["entities"]}

    prefix = _user_prefix(2, 0, span, mentions, entities)
    prompts = {label: prefix + VARIANTS[label] for label in selected}
    system = _detail_system_prompt(settings)

    inputs = [calls_path, paths.parsed_volume(2), paths.mentions(), paths.gazetteer(),
              paths.extraction_config(), paths.models_config(), Path(__file__).resolve()]
    inputs += [ROOT / "src/narrativewiki/extract" / name for name in
               ("scenes.py", "adequacy.py", "resolve.py", "scene_schema.py", "schema.py", "spans.py")]

    report = {
        "series": "spice-and-wolf", "volumes": [2], "source_run": SOURCE_RUN,
        "source_cache_key": recorded["cache_key"], "anchor": ANCHOR,
        "measurement": "single-passage prompt comparison; gate acceptance is not precision or recall",
        "variants": selected,
        "variant_instructions": {label: VARIANTS[label] for label in selected},
        "variant_instruction_sha256": {
            label: hashlib.sha256(VARIANTS[label].encode()).hexdigest() for label in selected
        },
        "system": system, "prompts": prompts, "options": _DETAIL_GENERATION_OPTIONS,
        "input_sha256": {paths.relative(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        "historical": score(SceneDetailResult.model_validate_json(recorded["response"]),
                            span, mentions, records, entities, settings),
        "results": {},
    }

    suffix = "result" if args.execute else "prepared"
    output = (ROOT / "docs/eval").joinpath(f"sparse_scene_{suffix}.json")
    if args.execute:
        run = provenance.start_run("spice-and-wolf", "sparse-scene-probe", scope="v2-c0-one-span",
                                   volumes=[2], volume_scope=2, settings=settings)
        report["run_id"] = run.run_id
        client = LLMClient(settings, run=run, volume_scope=2)
        try:
            for label, prompt in prompts.items():
                detail = client.complete_json(STAGE, prompt, SceneDetailResult,
                                              system=system, options=_DETAIL_GENERATION_OPTIONS)
                result = score(detail, span, mentions, records, entities, settings)
                result["fixture_eval"] = score_against_fixture(result["accepted"])
                report["results"][label] = result
                # Persist each completed result so interruption cannot discard the comparison.
                output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            report["cost_usd"] = client.budget.total_cost
        except BaseException:
            run.finish("error")
            raise
        else:
            run.finish("ok")

    # Score the historical baseline against the fixture too.
    report["historical"]["fixture_eval"] = score_against_fixture(report["historical"]["accepted"])

    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        "output": str(output), "run_id": report.get("run_id"),
        "cost_usd": report.get("cost_usd", 0),
        "variants": selected,
        "historical_fixture": {
            k: v for k, v in report["historical"]["fixture_eval"].items()
            if k in {"candidate_recovered", "precision_violated", "unmatched_missing", "dev_missing_total"}
        },
    }
    for label, result in report["results"].items():
        summary[label] = {k: v for k, v in result.items()
                          if k in {"unique_claims", "subjects", "drops"}}
        if "fixture_eval" in result:
            summary[f"{label}_fixture"] = {
                k: v for k, v in result["fixture_eval"].items()
                if k in {"candidate_recovered", "precision_violated", "unmatched_missing", "dev_missing_total"}
            }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
