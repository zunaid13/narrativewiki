"""Audit whether the live v1-2 artifacts justify a larger observation-schema migration.

This is a zero-model replay/audit. It reviews every same-volume contradiction that discarded one
side and traces persisted evidence back to the raw responses that produced it, so polarity and
qualifier disagreements are counted before the legacy claim merge erased those fields.

Run: python scripts/eval/audit_observation_semantics.py
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from narrativewiki import paths
from narrativewiki.extract.schema import Observation, make_claim_id, make_observation_id


SERIES = "spice-and-wolf"
RUN_IDS = (
    "20260922T212119-extract-v1-2",
    "20260922T211717-scenes-v1-2",
)

# Single-review labels grounded in the evidence copied into the report. These are deliberately
# keyed by the two claim IDs rather than conflict-list position so artifact drift fails loudly.
REVIEWS: dict[frozenset[str], tuple[str, str]] = {
    frozenset(("c_207f213a", "c_770f5d00")): (
        "equivalent_wording", "Traveling and wandering merchant describe the same continuing occupation."
    ),
    frozenset(("c_207f213a", "c_db267b98")): (
        "compatible_roles", "Wheat trading is compatible with being a traveling merchant; no transition is stated."
    ),
    frozenset(("c_8936831f", "c_fbe53102")): (
        "equivalent_wording", "Both passages name Marheit as the manager/head of the same Pazzio branch."
    ),
    frozenset(("c_11819ea3", "c_fe31601c")): (
        "compatible_roles", "Public witness is a transaction role and swindler is a characterization, not a temporal replacement."
    ),
    frozenset(("c_11819ea3", "c_14c350e3")): (
        "extraction_error", "The cited sentence describes traveling merchants generally and does not identify Zheren as one."
    ),
    frozenset(("c_11819ea3", "c_5f67be17")): (
        "compatible_roles", "Being a merchant does not conflict with acting as a public witness."
    ),
    frozenset(("c_5a7a734d", "c_84e24253")): (
        "compatible_roles", "Merchant and trading-company employee are compatible descriptions in the cited episode."
    ),
    frozenset(("c_5a7a734d", "c_97d6e91e")): (
        "compatible_roles", "Merchant and Remelio Company employee are compatible descriptions."
    ),
    frozenset(("c_5a7a734d", "c_d4e2f4c7")): (
        "compatible_roles", "Manager describes Liebert's expedition role and does not evidence an occupation change."
    ),
    frozenset(("c_150a9d39", "c_460b1b1c")): (
        "equivalent_wording", "Guild chief and trade guild master describe the same office."
    ),
    frozenset(("c_150a9d39", "c_e659c5d2")): (
        "equivalent_wording", "Running the guild house is the same office described as guild chief here."
    ),
    frozenset(("c_150a9d39", "c_ce5eefe3")): (
        "compatible_roles", "A guild chief can also be a merchant; the evidence gives no transition."
    ),
    frozenset(("c_150a9d39", "c_21dcf772")): (
        "equivalent_wording", "Both values name Jakob as head of the Ruvinheigen Rowen Trade Guild branch."
    ),
    frozenset(("c_be1182e2", "c_5a1c7df9")): (
        "within_volume_change", "The later passage explicitly says the friendship was short, marking friendship-to-enmity in volume 1."
    ),
    frozenset(("c_1bef3c92", "c_171f430d")): (
        "extraction_error", "Contact for business does not support friendship; the presumed hostility is not a state transition from it."
    ),
    frozenset(("c_dbee312f", "c_ea413c48")): (
        "extraction_error", "The same sentence says Yarei is unconscious, so it refutes rather than supports KILLED."
    ),
}

POLARITY_GROUP_REVIEWS: dict[str, tuple[str, str, str]] = {
    "c_921a57fb": (
        "uncertainty_resolved",
        "Yarei's Medio connection is first inferred, then directly evidenced as an association.",
        "Keep the presumed observation as history and publish the later asserted association.",
    ),
    "c_4fea2346": (
        "uncertainty_resolved",
        "A possible fur sample is followed by direct observation of Holo's brown fur.",
        "Keep the possible sample as history and publish the later asserted appearance.",
    ),
    "c_1bef3c92": (
        "uncertainty_resolved",
        "Zheren is first suspected of swindling Lawrence and is later described through the swindle.",
        "Retain the suspicion as presumed history; send the ENEMY_OF typing to review before promotion.",
    ),
    "c_5107a305": (
        "extraction_error",
        "The later passage says other men thought Holo was dead; it does not support presumed alive.",
        "Reject the later observation and retain the directly evidenced alive assertion.",
    ),
    "c_81848e1c": (
        "distinct_relation_contexts",
        "One passage describes Holo's hostility; the other conditionally imagines Norah treating Holo as an enemy.",
        "Do not collapse these into one certainty trajectory; review direction, attribution and qualifier separately.",
    ),
    "c_9f1203ad": (
        "uncertainty_resolved",
        "A risk that Liebert would kill Norah is followed by direct disclosure that he planned to do so.",
        "Keep the earlier risk as presumed history and publish the later asserted hostility.",
    ),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized_qualifier(value: Any) -> str:
    return " ".join(value.split()).casefold() if isinstance(value, str) else ""


def resolve_known_surface(value: Any, surface_to_entity: dict[str, str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().casefold()
    if normalized in surface_to_entity:
        return surface_to_entity[normalized]
    contained = {
        entity_id for surface, entity_id in surface_to_entity.items()
        if re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", normalized)
    }
    return next(iter(contained)) if len(contained) == 1 else None


def evidence_key(predicate: Any, para_id: Any, quote: Any) -> tuple[str, str, str] | None:
    if not all(isinstance(value, str) and value for value in (predicate, para_id, quote)):
        return None
    return predicate.strip().upper(), para_id, quote


def validate_run(run_id: str, command: str) -> tuple[Path, dict[str, Any]]:
    run = paths.run_dir(run_id)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("series_id") != SERIES
        or manifest.get("command") != command
        or manifest.get("outcome") != "ok"
        or not manifest.get("volumes")
        or not set(manifest["volumes"]) <= {1, 2}
    ):
        raise ValueError(f"{run_id} is not a successful {SERIES} {command} run scoped to v1-2")
    return run, manifest


def raw_observations(
    run: Path, stage: str, surface_to_entity: dict[str, str]
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for call_number, call in enumerate(read_jsonl(run / "calls.jsonl")):
        if call.get("stage") != stage:
            continue
        if "Your previous response" in call.get("prompt", ""):
            raise ValueError(f"JSON repair call requires explicit replay handling: {call['cache_key']}")
        response = json.loads(call["response"])
        groups: list[tuple[str | None, list[Any]]]
        if stage == "claim_extract":
            match = re.search(r'^Character: "([^"]+)"', call["prompt"])
            groups = [(match.group(1) if match else None, response.get("facts", []))]
        else:
            groups = [
                (group.get("subject"), group.get("facts", []))
                for group in response.get("participant_facts", [])
                if isinstance(group, dict)
            ]
        for group_number, (surface_subject, facts) in enumerate(groups):
            for fact_number, fact in enumerate(facts if isinstance(facts, list) else []):
                if not isinstance(fact, dict):
                    continue
                key = evidence_key(fact.get("predicate"), fact.get("para_id"), fact.get("quote"))
                if key is None:
                    continue
                raw_object = fact.get("object")
                raw_value = fact.get("value")
                target = None
                if isinstance(raw_object, str) and raw_object.strip():
                    target = resolve_known_surface(raw_object, surface_to_entity)
                elif isinstance(raw_value, str) and raw_value.strip():
                    target = raw_value.strip().casefold()
                observations.append(
                    {
                        "occurrence_key": f"{run.name}:{call['cache_key']}:{group_number}:{fact_number}",
                        "run_id": run.name,
                        "stage": stage,
                        "cache_key": call["cache_key"],
                        "fact_index": f"{group_number}:{fact_number}",
                        "prompt_sha256": hashlib.sha256(call["prompt"].encode("utf-8")).hexdigest(),
                        "extraction_source": f"{call['provider']}:{call['model']}",
                        "surface_subject": surface_subject,
                        "subject": resolve_known_surface(surface_subject, surface_to_entity),
                        "predicate": key[0],
                        "target": target,
                        "para_id": key[1],
                        "quote": key[2],
                        "polarity": fact.get("polarity", "asserted"),
                        "qualifier": fact.get("qualifier"),
                        "confidence": fact.get("confidence", 0.7),
                    }
                )
    return observations


def main() -> None:
    paths.set_active_series(SERIES)
    extract_run, extract_manifest = validate_run(RUN_IDS[0], "extract")
    scenes_run, scenes_manifest = validate_run(RUN_IDS[1], "scenes")
    inputs = [
        paths.contradictions(),
        paths.graph_db(),
        paths.gazetteer(),
        extract_run / "manifest.json",
        extract_run / "calls.jsonl",
        scenes_run / "manifest.json",
        scenes_run / "calls.jsonl",
        Path(__file__).resolve(),
    ]
    claim_paths = sorted((ROOT / "data" / SERIES / "03_claims").glob("*.jsonl"))
    inputs.extend(claim_paths)
    claim_rows = [(path.name, claim) for path in claim_paths for claim in read_jsonl(path)]
    gazetteer = json.loads(paths.gazetteer().read_text(encoding="utf-8"))["entities"]
    surfaces: dict[str, set[str]] = defaultdict(set)
    for entity in gazetteer:
        for surface in (entity["canonical"], *entity.get("aliases", [])):
            surfaces[surface.strip().casefold()].add(entity["entity_id"])
    surface_to_entity = {surface: next(iter(ids)) for surface, ids in surfaces.items() if len(ids) == 1}

    claims_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source_file, claim in claim_rows:
        claims_by_id[claim["claim_id"]].append({**claim, "artifact": source_file})

    contradiction_doc = json.loads(paths.contradictions().read_text(encoding="utf-8"))
    conflicts = [c for c in contradiction_doc["conflicts"] if c["resolution"] in {"keep_a", "keep_b"}]
    actual_keys = {frozenset((c["a"]["claim_id"], c["b"]["claim_id"])) for c in conflicts}
    if actual_keys != set(REVIEWS):
        raise ValueError("Live dropped-side conflicts changed; refresh the hand review before measuring")

    reviewed_conflicts = []
    for conflict in conflicts:
        ids = (conflict["a"]["claim_id"], conflict["b"]["claim_id"])
        label, rationale = REVIEWS[frozenset(ids)]
        sides = {}
        for side, claim_id in zip(("a", "b"), ids):
            sides[side] = [
                {
                    "claim_id": row["claim_id"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row.get("object"),
                    "value": row.get("value"),
                    "qualifier": row.get("qualifier"),
                    "polarity": row["polarity"],
                    "confidence": row["confidence"],
                    "chapter_idx": row["chapter_idx"],
                    "evidence": row["evidence"],
                    "artifact": row["artifact"],
                }
                for row in claims_by_id[claim_id]
            ]
        reviewed_conflicts.append(
            {
                "subject": conflict["subject"],
                "predicate_group": conflict["predicate"],
                "resolution": conflict["resolution"],
                "review_label": label,
                "review_rationale": rationale,
                "a": sides["a"],
                "b": sides["b"],
            }
        )

    observations = raw_observations(extract_run, "claim_extract", surface_to_entity)
    observations.extend(raw_observations(scenes_run, "scene_extract", surface_to_entity))
    raw_by_evidence: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    raw_by_loose_evidence: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        if observation["subject"]:
            raw_by_evidence[
                (
                    observation["subject"], observation["predicate"], observation["target"],
                    observation["para_id"], observation["quote"],
                )
            ].append(observation)
            raw_by_loose_evidence[
                (observation["subject"], observation["predicate"], observation["para_id"], observation["quote"])
            ].append(observation)

    observations_by_claim: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    resolved_observations_by_claim: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    unmatched_evidence = []
    for source_file, claim in claim_rows:
        for evidence in claim["evidence"]:
            key = evidence_key(claim["predicate"], evidence["para_id"], evidence["quote"])
            target = claim.get("object") or (claim.get("value") or "").strip().casefold()
            predicate, para_id, quote = key or ("", "", "")
            lookup = (claim["subject"], predicate, target, para_id, quote)
            matches = raw_by_evidence.get(lookup, [])
            if not matches:
                # A surface such as bare "Remelio" can resolve against the call's local mention
                # set even though it is ambiguous in the global gazetteer. The persisted target
                # records that local resolution; accept only raw candidates whose global target
                # remained unresolved, never a candidate resolved to a different entity.
                loose = raw_by_loose_evidence.get((claim["subject"], predicate, para_id, quote), [])
                matches = [item for item in loose if item["target"] is None]
            if not matches:
                unmatched_evidence.append(
                    {"claim_id": claim["claim_id"], "artifact": source_file, "evidence": evidence}
                )
            for observation in matches:
                occurrence_key = observation["occurrence_key"]
                observations_by_claim[claim["claim_id"]][occurrence_key] = observation
                candidate_assertion_id = make_claim_id(
                    claim["subject"], claim["predicate"], target, claim["first_vol"],
                    polarity=observation["polarity"], qualifier=observation["qualifier"],
                )
                source_observation = Observation(
                    observation_id=make_observation_id(
                        SERIES, observation["run_id"], observation["cache_key"], observation["fact_index"]
                    ),
                    series_id=SERIES,
                    subject=claim["subject"],
                    predicate=claim["predicate"],
                    kind=claim["kind"],
                    object=claim.get("object"),
                    value=claim.get("value"),
                    qualifier=observation["qualifier"],
                    polarity=observation["polarity"],
                    confidence=observation["confidence"],
                    disclosure_vol=claim["first_vol"],
                    chapter_idx=int(re.search(r":c(\d+):", para_id).group(1)),
                    evidence=evidence,
                    source_stage=observation["stage"],
                    source_run_id=observation["run_id"],
                    source_cache_key=observation["cache_key"],
                    source_fact_index=observation["fact_index"],
                    source_prompt_sha256=observation["prompt_sha256"],
                    extraction_source=observation["extraction_source"],
                    candidate_assertion_id=candidate_assertion_id,
                    legacy_claim_id=claim["claim_id"],
                ).model_dump(mode="json")
                existing = resolved_observations_by_claim[claim["claim_id"]].get(occurrence_key)
                if existing is not None and existing != source_observation:
                    raise ValueError(f"One source occurrence mapped to conflicting claims: {occurrence_key}")
                resolved_observations_by_claim[claim["claim_id"]][occurrence_key] = source_observation

    merged = {claim_id: list(items.values()) for claim_id, items in observations_by_claim.items() if len(items) > 1}
    polarity_disagreements = {
        claim_id: items for claim_id, items in merged.items()
        if len({item["polarity"] for item in items}) > 1
    }
    qualifier_disagreements = {
        claim_id: items for claim_id, items in merged.items()
        if len({normalized_qualifier(item["qualifier"]) for item in items}) > 1
    }
    labels: dict[str, int] = defaultdict(int)
    for conflict in reviewed_conflicts:
        labels[conflict["review_label"]] += 1

    if set(polarity_disagreements) != set(POLARITY_GROUP_REVIEWS):
        raise ValueError("Polarity-disagreement groups changed; refresh their reviewed dispositions")
    graph = sqlite3.connect(f"file:{paths.graph_db().as_posix()}?mode=ro", uri=True)
    graph.row_factory = sqlite3.Row
    polarity_group_dispositions = []
    for legacy_claim_id, items in sorted(polarity_disagreements.items()):
        live = graph.execute(
            "SELECT claim_id, subject, predicate, object, value, qualifier, polarity, confidence "
            "FROM claims WHERE claim_id = ?",
            (legacy_claim_id,),
        ).fetchone()
        if live is None:
            raise ValueError(f"Legacy live claim is missing: {legacy_claim_id}")
        disposition, rationale, projection = POLARITY_GROUP_REVIEWS[legacy_claim_id]
        polarity_group_dispositions.append(
            {
                "legacy_claim_id": legacy_claim_id,
                "disposition": disposition,
                "review_rationale": rationale,
                "recommended_shadow_projection": projection,
                "live_merged_claim": dict(live),
                "source_observations": items,
            }
        )
    graph.close()
    disposition_counts: dict[str, int] = defaultdict(int)
    for item in polarity_group_dispositions:
        disposition_counts[item["disposition"]] += 1

    shadow_observations = sorted(
        (
            item
            for claim_id in polarity_disagreements
            for item in resolved_observations_by_claim[claim_id].values()
        ),
        key=lambda item: item["observation_id"],
    )
    shadow_path = ROOT / "docs" / "eval" / "observation_shadow_spice-and-wolf.jsonl"
    shadow_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in shadow_observations),
        encoding="utf-8",
    )

    report = {
        "measurement_id": "20260924-observation-semantics-v1-2",
        "series": SERIES,
        "volumes": sorted(set(extract_manifest["volumes"]) | set(scenes_manifest["volumes"])),
        "model_calls": 0,
        "review_status": "single agent review; quoted source witnesses included for maintainer spot-check",
        "summary": {
            "dropped_side_conflicts_reviewed": len(reviewed_conflicts),
            "conflict_review_labels": dict(sorted(labels.items())),
            "legitimate_within_volume_changes": labels["within_volume_change"],
            "persisted_claim_rows": len(claim_rows),
            "legacy_claim_ids": len(claims_by_id),
            "raw_surviving_observations_traced": sum(len(items) for items in observations_by_claim.values()),
            "raw_fact_observations_scanned": len(observations),
            "raw_fact_observations_with_resolved_subject": sum(bool(item["subject"]) for item in observations),
            "legacy_claim_ids_with_multiple_source_observations": len(merged),
            "merged_claim_ids_with_polarity_disagreement": len(polarity_disagreements),
            "merged_claim_ids_with_qualifier_disagreement": len(qualifier_disagreements),
            "unmatched_persisted_evidence": len(unmatched_evidence),
            "shadow_polarity_groups": len(polarity_disagreements),
            "shadow_observations": len(shadow_observations),
            "shadow_candidate_assertions": len(
                {item["candidate_assertion_id"] for item in shadow_observations}
            ),
            "polarity_group_dispositions": dict(sorted(disposition_counts.items())),
        },
        "decision": (
            "The migration gate is met: source observations differ often enough that the legacy "
            "claim record cannot preserve provenance faithfully. Build the observation/assertion "
            "foundation incrementally, starting with stored-response replay and the six witnessed "
            "polarity-disagreement groups; do not block the already-shipped semantic-key fix."
        ),
        "reviewed_conflicts": reviewed_conflicts,
        "polarity_disagreements": polarity_disagreements,
        "qualifier_disagreements": qualifier_disagreements,
        "polarity_group_dispositions": polarity_group_dispositions,
        "unmatched_persisted_evidence": unmatched_evidence,
        "shadow_observation_artifact": str(shadow_path.relative_to(ROOT)).replace("\\", "/"),
        "input_sha256": {
            paths.relative(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs
        },
    }
    output = ROOT / "docs" / "eval" / "observation_semantics_spice-and-wolf.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
