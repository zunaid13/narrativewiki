"""Offline kappa of current accepted Codex/Claude labels versus each blind model.

No inference, label edits or adjudication. Verify the accepted snapshot still matches
the current source sheet and the new model outputs used the same questions packet.
"""
import csv
import hashlib
import json
from pathlib import Path

from build_packet import HERE, SOURCE, TASKS, read_csv
from score_agreement import score

MODELS = {"nemotron": "openrouter_ultra", "gemini": "gemini_pro"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare():
    baseline = HERE / "accepted_answers.csv"
    manifest = json.loads((HERE / "manifest_private.json").read_text(encoding="utf-8"))
    source = SOURCE / "final_labels.csv"
    if sha(source) != manifest["source_sha256"]["final_labels.csv"]:
        raise ValueError("Current accepted source changed; refresh the accepted packet mapping before comparing")
    accepted, current = read_csv(baseline), read_csv(source)
    for item in manifest["items"]:
        old, new = current[item["source_item"]], accepted[item["item"]]
        pair = old["pair"] if item["pair_required"] else "n-a"
        if new["label"] != old["accepted label"] or new["pair"] != pair:
            raise ValueError("Accepted snapshot differs from current source sheet")
    output = HERE / "accepted_comparison"
    output.mkdir(parents=True, exist_ok=True)
    reports, summary = {}, []
    for name, directory_name in MODELS.items():
        directory = HERE / "model_runs" / directory_name
        metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        if metadata["packet_sha256"] != sha(HERE / "questions_only.html"):
            raise ValueError("Model packet differs from current questions")
        report = score(baseline, directory / "answers.csv")
        report.update({"comparison_type": "accepted AI-assisted annotations versus independently blind model labels",
            "baseline": {"description": "Codex draft checked/corrected by Claude, then accepted in human review",
                         "independent_human_ground_truth": False,
                         "answers_sha256": sha(baseline), "current_source_sha256": sha(source)},
            "model": metadata["model"], "model_runs": metadata["runs"], "new_api_calls": 0})
        judgments = read_csv(directory / "answers.csv")
        comparisons = []
        for item in manifest["items"]:
            item_id = item["item"]
            a, b = accepted[item_id], judgments[item_id]
            comparisons.append({"item": item_id, "task": a["task"], "accepted_label": a["label"],
                "model_label": b["label"], "accepted_pair": a["pair"], "model_pair": b["pair"],
                "label_agrees": a["label"] == b["label"], "pair_agrees": a["pair"] == b["pair"],
                "accepted_label_from": item["label_from"], "model_reason": b["comment"]})
        disagreements = [r for r in comparisons if not r["label_agrees"] or not r["pair_agrees"]]
        report["items_all_agree"] = len(comparisons) - len(disagreements)
        report["items_any_disagreement"] = len(disagreements)
        for suffix, rows in (("comparisons", comparisons), ("disagreements", disagreements)):
            with (output / f"accepted_vs_{name}_{suffix}.csv").open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(comparisons[0]))
                writer.writeheader()
                writer.writerows(rows)
        (output / f"accepted_vs_{name}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        reports[name] = report
        for task, result in report["tasks"].items():
            summary.append({"comparison": f"accepted vs {name}", "task": task, "items": result["n"],
                "agreement": result["agreement"], "kappa": result["kappa"],
                "chance_agreement": result["chance_agreement"], "disagreements": len(result["disagreements"])})
        pair = report["tasks"]["P"]["pair_scene"]
        summary.append({"comparison": f"accepted vs {name}", "task": "P_pair_scene", "items": pair["n"],
            "agreement": pair["agreement"], "kappa": pair["kappa"],
            "chance_agreement": pair["chance_agreement"], "disagreements": len(pair["disagreements"])})
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    lines = ["# Current accepted annotations versus blind model labels", "",
        "Baseline: current Codex draft checked/corrected by Claude, then accepted by a human reviewer. "
        "It is an AI-assisted accepted reference, not independently collected human ground truth. "
        "Each comparison uses all 554 items and the model's unchanged blind first-pass labels. No new API calls.", "",
        "| Task | Items | Nemotron agreement | Nemotron kappa | Gemini agreement | Gemini kappa |",
        "|---|---:|---:|---:|---:|---:|"]
    for task in TASKS:
        a, b = (reports[n]["tasks"][task] for n in MODELS)
        lines.append(f"| {TASKS[task][0]} | {a['n']} | {a['agreement']:.2%} | {a['kappa']:.6f} | {b['agreement']:.2%} | {b['kappa']:.6f} |")
    a, b = (reports[n]["tasks"]["P"]["pair_scene"] for n in MODELS)
    lines.extend([f"| Pair placement | {a['n']} | {a['agreement']:.2%} | {a['kappa']:.6f} | {b['agreement']:.2%} | {b['kappa']:.6f} |", ""])
    for name, report in reports.items():
        lines.append(f"Against {name}: {report['items_all_agree']} items agree on all applicable decisions; {report['items_any_disagreement']} have at least one disagreement.")
    lines.extend(["", "Nominal unweighted kappa is reported separately per task. JSON includes confusion tables, "
        "binary yes-versus-rest results and precision combining factual support with pair placement. "
        "No pooled mixed-task kappa. Disagreement CSVs contain question IDs, both labels, accepted-label provenance and model explanations.", "",
        "Reproduce: `.venv/Scripts/python.exe docs/eval/agreement/compare_accepted_labels.py`", ""])
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    compare()
