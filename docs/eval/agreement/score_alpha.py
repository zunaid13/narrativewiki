"""Nominal Krippendorff alpha for accepted Codex/Claude, Gemini and Nemotron.

Stdlib only; no inference. Input rows in nominal_alpha are units, columns are raters.
Coincidences are weighted by 1/(ratings_in_unit - 1); expected disagreement uses
the finite-sample n*(n-1) denominator, not Fleiss kappa or average pairwise kappa.
Reference: Krippendorff, Computing Krippendorff's Alpha-Reliability, 2011/2013.
"""
import csv
import hashlib
import json
import math
from collections import Counter

from build_packet import HERE, SOURCE, TASKS
from score_agreement import read_answers

METHOD_SOURCE = "https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf"
LABELERS = {
    "accepted_codex_claude": HERE / "accepted_answers.csv",
    "gemini": HERE / "model_runs/gemini_pro/answers.csv",
    "nemotron": HERE / "model_runs/openrouter_ultra/answers.csv",
}


def nominal_alpha(units):
    counts = Counter()
    disagreement = 0.0
    pairable = 0
    excluded = []
    disagreements = []
    unanimous = 0
    for index, values in enumerate(units):
        labels = [v for v in values if v is not None and v != ""]
        m = len(labels)
        if m < 2:
            excluded.append(index)
            continue
        c = Counter(labels)
        counts.update(c)
        disagreement += (m * m - sum(n * n for n in c.values())) / (m - 1)
        pairable += 1
        unanimous += len(c) == 1
        if len(c) > 1:
            disagreements.append(index)
    n = sum(counts.values())
    observed = disagreement / n if n else None
    expected = (n * n - sum(c * c for c in counts.values())) / (n * (n - 1)) if n > 1 else None
    undefined = expected is None or math.isclose(expected, 0, rel_tol=0, abs_tol=1e-15)
    return {"alpha": None if undefined else 1 - observed / expected,
            "n_units": pairable, "pairable_ratings": n, "label_counts": dict(counts),
            "observed_disagreement": observed, "expected_disagreement": expected,
            "pairwise_agreement": None if observed is None else 1 - observed,
            "unanimous_units": unanimous, "excluded_unit_indices": excluded,
            "disagreement_unit_indices": disagreements,
            "undefined_reason": ("No pairable ratings" if not n else "Only one category among pairable ratings") if undefined else None}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_labels():
    manifest = json.loads((HERE / "manifest_private.json").read_text(encoding="utf-8"))
    if sha(SOURCE / "final_labels.csv") != manifest["source_sha256"]["final_labels.csv"]:
        raise ValueError("Current accepted source changed; refresh the reference snapshot first")
    with (HERE / "reader_answers_blank.csv").open(encoding="utf-8-sig", newline="") as f:
        expected = {r["item"]: {"task": r["task"], "pair_required": r["pair"] != "n-a"} for r in csv.DictReader(f)}
    labels = {name: read_answers(path, expected) for name, path in LABELERS.items()}
    for name, sheet in labels.items():
        if set(sheet) != set(expected) or any(not row["label"] or not row["pair"] for row in sheet.values()):
            raise ValueError(f"Incomplete annotations: {name}")
    for name, directory in (("gemini", "gemini_pro"), ("nemotron", "openrouter_ultra")):
        metadata = json.loads((HERE / "model_runs" / directory / "metadata.json").read_text())
        if metadata["packet_sha256"] != sha(HERE / "questions_only.html"):
            raise ValueError(f"Question packet differs for {name}")
    reference = json.loads((HERE / "accepted_comparison/accepted_vs_gemini.json").read_text())
    if reference["baseline"]["answers_sha256"] != sha(LABELERS["accepted_codex_claude"]):
        raise ValueError("Accepted labels changed after source/snapshot verification")
    return expected, labels


def calculate():
    expected, labels = load_labels()
    names = list(LABELERS)

    def result(ids, field="label", binary=False, combine=False):
        matrix = []
        for item in ids:
            values = []
            for name in names:
                row = labels[name][item]
                value = row[field]
                if binary:
                    value = value == "yes"
                if combine:
                    value = value and (not expected[item]["pair_required"] or row["pair"] == "yes")
                values.append(value)
            matrix.append(values)
        value = nominal_alpha(matrix)
        return {**value, "items": ids, "n_raters": len(names),
                "disagreement_items": [ids[i] for i in value["disagreement_unit_indices"]]}

    report = {"metric": "Krippendorff's alpha", "level_of_measurement": "nominal",
              "formula": "alpha = 1 - Do/De; Do=sum_unit ordered_mismatches/(m_unit-1)/n; De=(n*n-sum_category count*count)/(n*(n-1))",
              "method_source": METHOD_SOURCE, "raters": names,
              "baseline": "One combined accepted Codex draft checked/corrected by Claude, then human-reviewed; not separate Codex and Claude raters or independent human ground truth",
              "inputs": {n: {"path": str(p.relative_to(HERE)), "sha256": sha(p)} for n, p in LABELERS.items()},
              "status": "complete", "new_api_calls": 0, "tasks": {},
              "pooled_alpha": "Not computed: tasks ask different questions and use different label spaces."}
    for task in TASKS:
        ids = [item for item, spec in expected.items() if spec["task"] == task]
        task_result = result(ids)
        substantive = [item for item in ids if all(labels[name][item]["label"] != "not shown" for name in names)]
        task_result["binary_yes_vs_rest"] = result(substantive, binary=True)
        task_result["binary_excluded_not_shown"] = [item for item in ids if item not in substantive]
        if task == "P":
            task_result["pair_scene"] = result([i for i in ids if expected[i]["pair_required"]], field="pair")
            task_result["supported_on_page"] = result(substantive, binary=True, combine=True)
        report["tasks"][task] = task_result
    output = HERE / "alpha_comparison"
    output.mkdir(parents=True, exist_ok=True)
    (output / "three_rater_alpha.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = []
    for task, item in report["tasks"].items():
        for variant, value in (("nominal", item), ("binary_yes_vs_rest", item["binary_yes_vs_rest"])):
            summary.append({"task": task, "variant": variant, **{k: value[k] for k in
                ("n_units", "pairable_ratings", "alpha", "observed_disagreement", "expected_disagreement", "pairwise_agreement", "unanimous_units")}})
    for variant in ("pair_scene", "supported_on_page"):
        value = report["tasks"]["P"][variant]
        summary.append({"task": "P", "variant": variant, **{k: value[k] for k in
            ("n_units", "pairable_ratings", "alpha", "observed_disagreement", "expected_disagreement", "pairwise_agreement", "unanimous_units")}})
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    with (output / "ratings.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "task", *names, *(n + "_pair" for n in names)])
        writer.writeheader()
        for item, spec in expected.items():
            writer.writerow({"item": item, "task": spec["task"], **{n: labels[n][item]["label"] for n in names},
                             **{n + "_pair": labels[n][item]["pair"] for n in names}})
    lines = ["# Three-rater nominal Krippendorff alpha", "",
        "Label sets: accepted Codex/Claude annotations, Gemini and Nemotron. The accepted reference is "
        "one combined label set, not two raters. All 554 items have complete labels from all three. "
        "This measures agreement among AI-assisted annotations and models, not independent human reliability or accuracy.", "",
        "| Task | Items | Alpha | Mean pairwise agreement | Unanimous items |", "|---|---:|---:|---:|---:|"]
    for task, value in report["tasks"].items():
        lines.append(f"| {TASKS[task][0]} | {value['n_units']} | {value['alpha']:.6f} | {value['pairwise_agreement']:.2%} | {value['unanimous_units']} |")
    pair = report["tasks"]["P"]["pair_scene"]
    lines.extend([f"| Pair placement | {pair['n_units']} | {pair['alpha']:.6f} | {pair['pairwise_agreement']:.2%} | {pair['unanimous_units']} |", "",
        "Method: nominal distance (same label = 0, different = 1), observed within-item coincidences "
        "and expected disagreement from pooled category counts with the n*(n-1) finite-sample correction. "
        "Alpha is calculated jointly, rather than averaging pairwise kappas. "
        f"Reference: [Krippendorff, Computing Krippendorff's Alpha-Reliability, pp. 1-5]({METHOD_SOURCE}).", "",
        "not shown remains a nominal category; the optional binary results exclude any item marked not shown by any rater. "
        "none cited remains a citation category. Pair placement is calculated separately. No mixed-task pooled alpha or confidence intervals.", "",
        "JSON includes all results, counts, disagreements, input hashes and item IDs. summary.csv includes primary and secondary results; ratings.csv aligns all three annotation sets.", "",
        "Reproduce: `.venv/Scripts/python.exe docs/eval/agreement/score_alpha.py`. No new API calls.", ""])
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    return report


if __name__ == "__main__":
    calculate()
