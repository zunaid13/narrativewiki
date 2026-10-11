"""Reproduce supplied-reviewer agreement from preserved CSVs, without inference.

Reviewer identities follow the maintainer's file assignments, not directory names.
Uses existing nominal coefficient implementations. Never adjudicates source labels
or rewrites the original screenshot transcriptions or primary system scores.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "docs/eval/agreement"
REVIEW = HERE / "human_review"
sys.path.insert(0, str(HERE))
from score_agreement import read_answers, score
from score_alpha import nominal_alpha

RUN_ID = "human-label-reproduction-20261010"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_hashes(path: Path) -> set[str]:
    """Allow Git's LF/CRLF conversion for pre-existing packet/reference text only."""
    data = path.read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    return {hashlib.sha256(value).hexdigest() for value in (data, lf, lf.replace(b"\n", b"\r\n"))}


def reproduce() -> dict:
    provenance = json.loads((REVIEW / "raw_label_provenance_20261010.json").read_text(encoding="utf-8"))
    paths = {name: ROOT / spec["answers_path"] for name, spec in provenance["reviewers"].items()}
    paths["accepted_reference"] = HERE / "accepted_answers.csv"
    template = HERE / "reader_answers_blank.csv"
    with template.open(encoding="utf-8-sig", newline="") as f:
        expected = {r["item"]: {"task": r["task"], "pair_required": r["pair"] != "n-a"}
                    for r in csv.DictReader(f)}
    labels = {name: read_answers(path, expected) for name, path in paths.items()}
    for name, rows in labels.items():
        if set(rows) != set(expected) or any(not r["label"] or not r["pair"] for r in rows.values()):
            raise ValueError(f"Incomplete labels: {name}")
    packet_hash = sha(HERE / "questions_only.html")
    supplied_files = {}
    for name, spec in provenance["reviewers"].items():
        hashes = {}
        for key in ("answers", "responses", "metadata"):
            path = ROOT / spec[f"{key}_path"]
            hashes[key] = sha(path)
            if hashes[key] != spec[f"{key}_sha256"]:
                raise ValueError(f"Preserved input changed: {name}/{key}")
        meta = json.loads((ROOT / spec["metadata_path"]).read_text(encoding="utf-8"))
        if meta["packet_sha256"] not in text_hashes(HERE / "questions_only.html"):
            raise ValueError(f"Question packet differs: {name}")
        responses = [json.loads(s) for s in (ROOT / spec["responses_path"]).read_text(encoding="utf-8").splitlines() if s.strip()]
        response_ids = [r["item"] for r in responses]
        if len(set(response_ids)) != len(response_ids) or set(response_ids) != set(expected):
            raise ValueError(f"Unknown, duplicate or missing response items: {name}")
        mismatch = [r["item"] for r in responses if r["task"] != expected[r["item"]]["task"]
                    or any(r[k].strip().lower() != labels[name][r["item"]][k] for k in ("label", "pair"))]
        if mismatch:
            raise ValueError(f"CSV/response label mismatch: {name}: {mismatch}")
        supplied_files[name] = {"sha256": hashes, "response_items": len(responses),
                                "csv_response_label_mismatches": mismatch,
                                "archived_packet_sha256": meta["packet_sha256"], "current_packet_sha256": packet_hash}
    manifest = json.loads((HERE / "manifest_private.json").read_text(encoding="utf-8"))
    source_path = ROOT / "docs/eval/human_check/final_labels.csv"
    if manifest["source_sha256"]["final_labels.csv"] not in text_hashes(source_path):
        raise ValueError("Accepted-reference source changed after packet construction")
    with source_path.open(encoding="utf-8-sig", newline="") as f:
        source = {r["item"]: r for r in csv.DictReader(f)}
    for item in manifest["items"]:
        original = source[item["source_item"]]
        accepted = labels["accepted_reference"][item["item"]]
        if accepted["label"] != original["accepted label"] or accepted["pair"] != (original["pair"] if item["pair_required"] else "n-a"):
            raise ValueError("Accepted reference differs from its mapped source")
    pairs = {"reviewer_pair": ("reviewer_1", "reviewer_2"),
             "reviewer_1_vs_reference": ("reviewer_1", "accepted_reference"),
             "reviewer_2_vs_reference": ("reviewer_2", "accepted_reference")}
    comparisons = {}
    for key, (a, b) in pairs.items():
        result = score(paths[a], paths[b], template)
        result["readers"] = [paths[n].relative_to(ROOT).as_posix() for n in (a, b)]
        differing = [i for i in expected if labels[a][i] != labels[b][i]]
        result.update({"items_all_agree": len(expected) - len(differing),
                       "items_any_disagreement": len(differing), "disagreement_items": differing})
        comparisons[key] = result
    alpha = {}
    for task in ("G", "R", "P", "C", "PAIR"):
        ids = [i for i, s in expected.items() if (s["pair_required"] if task == "PAIR" else s["task"] == task)]
        field = "pair" if task == "PAIR" else "label"
        value = nominal_alpha([[labels[name][i][field] for name in paths] for i in ids])
        alpha[task] = {**value, "items": ids,
                       "disagreement_items": [ids[j] for j in value["disagreement_unit_indices"]]}
    prior_pair = json.loads((REVIEW / "reported_agreement_2026-10-10.json").read_text(encoding="utf-8"))
    prior_ai = json.loads((REVIEW / "reported_ai_comparisons_2026-10-10.json").read_text(encoding="utf-8"))
    prior_alpha = json.loads((REVIEW / "reported_alpha_2026-10-10.json").read_text(encoding="utf-8"))
    matches = {"reviewer_pair_primary_tasks": {}, "alpha": {}, "reviewer_reference_columns": {}}
    for task in ("G", "R", "P", "C", "PAIR"):
        if task != "PAIR":
            p, r = prior_pair["tasks"][task], comparisons["reviewer_pair"]["tasks"][task]
            matches["reviewer_pair_primary_tasks"][task] = (p["n"] == r["n"] and p["agreement_percent"] == round(100 * r["agreement"], 2) and p["cohen_kappa"] == round(r["kappa"], 6))
        p, r = prior_alpha["tasks"][task], alpha[task]
        matches["alpha"][task] = (p["n"] == r["n_units"] and p["alpha"] == round(r["alpha"], 6) and p["mean_pairwise_agreement_percent"] == round(100 * r["pairwise_agreement"], 2) and p["unanimous_items"] == r["unanimous_units"])
    for name in ("reviewer_1", "reviewer_2"):
        matches["reviewer_reference_columns"][name] = []
        for previous in ("reviewer_1", "reviewer_2"):
            match = True
            for task in ("G", "R", "P", "C", "PAIR"):
                p = prior_ai["tasks"][task][previous]
                r = comparisons[f"{name}_vs_reference"]["tasks"]["P"]["pair_scene"] if task == "PAIR" else comparisons[f"{name}_vs_reference"]["tasks"][task]
                match &= p["agreement_percent"] == round(100 * r["agreement"], 2) and p["cohen_kappa"] == round(r["kappa"], 6)
            if match:
                matches["reviewer_reference_columns"][name].append(previous)
    report = {"run_id": RUN_ID, "date": "2026-10-10", "reviewed_items": len(expected),
              "reviewer_identity_basis": provenance["identity_basis"], "authorship_independently_verified": False,
              "archival_metadata_conflict": provenance["archival_metadata_conflict"],
              "reference": {"path": paths["accepted_reference"].relative_to(ROOT).as_posix(),
                            "sha256": sha(paths["accepted_reference"]), "mapped_source_sha256": sha(source_path),
                            "description": "Accepted AI-assisted review snapshot finalized by Claude; not verified blind unchanged first-pass AI labels"},
              "supplied_files": supplied_files,
              "hash_policy": "Supplied reviewer files use strict byte hashes. Existing packet/reference text allows only LF/CRLF variants for Git checkouts; accepted label mapping is checked separately.",
              "comparisons": comparisons, "joint_nominal_alpha": alpha,
              "comparison_to_prior_summaries": matches, "pooled_coefficient": None,
              "limits": "No authorship/blinding verification, adjudication, primary-score changes, inference or new experiment. Pair placement is a precision subset."}
    aligned = []
    lookup = {r["item"]: r for r in manifest["items"]}
    for i, spec in expected.items():
        a, b, ref = (labels[n][i] for n in ("reviewer_1", "reviewer_2", "accepted_reference"))
        aligned.append({"item": i, "source_item": lookup[i]["source_item"], "task": spec["task"],
                        "pair_required": spec["pair_required"], "reviewer_1_label": a["label"], "reviewer_2_label": b["label"],
                        "reference_label": ref["label"], "reviewer_1_pair": a["pair"], "reviewer_2_pair": b["pair"],
                        "reference_pair": ref["pair"], "reviewers_agree": a == b,
                        "consensus_differs_from_reference": a == b and a != ref,
                        "adjudication_status": "unadjudicated" if a != b or a != ref else "no_difference"})
    with (REVIEW / "aligned_decisions_20261010.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(aligned[0]))
        writer.writeheader()
        writer.writerows(aligned)
    (REVIEW / "recomputed_agreement_20261010.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def paper_values(report: dict) -> dict[str, str]:
    values = {}
    pair = report["comparisons"]["reviewer_pair"]
    for task in ("G", "R", "P", "C", "PAIR"):
        r = pair["tasks"]["P"]["pair_scene"] if task == "PAIR" else pair["tasks"][task]
        values.update({f"HREV-{task}-n": str(r["n"]), f"HREV-{task}-agreement": f"{100*r['agreement']:.2f}\\%", f"HREV-{task}-kappa": f"{r['kappa']:.6f}"})
        values[f"HRAI-{task}-n"] = str(r["n"])
        for number in (1, 2):
            c = report["comparisons"][f"reviewer_{number}_vs_reference"]
            r = c["tasks"]["P"]["pair_scene"] if task == "PAIR" else c["tasks"][task]
            values[f"HRAI-r{number}-{task}-agreement"] = f"{100*r['agreement']:.2f}\\%"
            values[f"HRAI-r{number}-{task}-kappa"] = f"{r['kappa']:.6f}"
        r = report["joint_nominal_alpha"][task]
        values.update({f"HRAL-{task}-n": str(r["n_units"]), f"HRAL-{task}-alpha": f"{r['alpha']:.6f}",
                       f"HRAL-{task}-agreement": f"{100*r['pairwise_agreement']:.2f}\\%", f"HRAL-{task}-unanimous": str(r["unanimous_units"])})
    values.update({"HREV-total": str(report["reviewed_items"]), "HREV-all-agree": str(pair["items_all_agree"]), "HREV-any-disagreement": str(pair["items_any_disagreement"]),
                   "HRAI-total": str(report["reviewed_items"]), "HRAL-total": str(report["reviewed_items"])})
    for number in (1, 2):
        c = report["comparisons"][f"reviewer_{number}_vs_reference"]
        values[f"HRAI-r{number}-all-agree"] = str(c["items_all_agree"])
        values[f"HRAI-r{number}-any-disagreement"] = str(c["items_any_disagreement"])
    return values


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.parse_args()
    report = reproduce()
    for key, c in report["comparisons"].items():
        print(key, {t: (r["n"], round(100*r["agreement"], 2), round(r["kappa"], 6)) for t, r in c["tasks"].items()})
    print("Prior-summary alignment:", report["comparison_to_prior_summaries"])
    print("Report:", (REVIEW / "recomputed_agreement_20261010.json").relative_to(ROOT))


if __name__ == "__main__":
    main()
