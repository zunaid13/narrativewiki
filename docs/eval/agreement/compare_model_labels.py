"""Score complete independent model sheets and export agreements/disagreements."""
import argparse
import csv
import html
import json
from pathlib import Path

from build_packet import HERE, TASKS
from run_model_labels import load_questions
from score_agreement import score
from narrativewiki import paths


def compare(a_dir, b_dir, output):
    report = score(a_dir / "answers.csv", b_dir / "answers.csv")
    report["comparison_type"] = "model-model; not human inter-rater reliability or accuracy"
    report["labelers"] = [json.loads((d / "metadata.json").read_text()) for d in (a_dir, b_dir)]
    if report["labelers"][0]["packet_sha256"] != report["labelers"][1]["packet_sha256"]:
        raise ValueError("Labelers used different packets")
    paths.set_active_series("anne")
    for labeler in report["labelers"]:
        ledgers = [json.loads((paths.run_dir(r) / "budget.json").read_text()) for r in labeler["runs"]]
        labeler["recorded_cost_usd"] = round(sum(d["total_cost_usd"] for d in ledgers), 6)
        labeler["usage"] = {k: sum(s[k] for d in ledgers for s in d["stages"].values())
                            for k in ("calls", "cached", "in_tokens", "out_tokens")}
    responses = [{r["item"]: r for r in map(json.loads, (d / "responses.jsonl").read_text(encoding="utf-8").splitlines())}
                 for d in (a_dir, b_dir)]
    rows, sections = [], []
    for question in load_questions():
        item = question["item"]
        a, b = responses[0][item], responses[1][item]
        row = {"item": item, "task": question["task"], "a_label": a["label"], "b_label": b["label"],
               "a_pair": a["pair"], "b_pair": b["pair"], "labels_agree": a["label"] == b["label"],
               "pair_agrees": a["pair"] == b["pair"], "a_reason": a["reason"], "b_reason": b["reason"]}
        row["all_agree"] = row["labels_agree"] and row["pair_agrees"]
        rows.append(row)
        if not row["all_agree"]:
            sections.append(f"<section><h2>{item}: {html.escape(TASKS[question['task']][0])}</h2>"
                            f"<pre>{html.escape(question['question'])}</pre>"
                            f"<p><b>Model A:</b> {html.escape(a['label'])}; pair={a['pair']}. {html.escape(a['reason'])}</p>"
                            f"<p><b>Model B:</b> {html.escape(b['label'])}; pair={b['pair']}. {html.escape(b['reason'])}</p></section>")
    output.mkdir(parents=True, exist_ok=True)
    for filename, subset in (("all_comparisons.csv", rows), ("agreements.csv", [r for r in rows if r["all_agree"]]),
                             ("disagreements.csv", [r for r in rows if not r["all_agree"]])):
        with (output / filename).open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(subset)
    report["items_all_agree"] = sum(r["all_agree"] for r in rows)
    report["items_any_disagreement"] = sum(not r["all_agree"] for r in rows)
    (output / "model_agreement.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "disagreements.html").write_text("<!doctype html><meta charset='utf-8'><title>Model disagreements</title>"
        "<style>body{max-width:1000px;margin:2em auto;font:17px/1.5 sans-serif}pre{white-space:pre-wrap}"
        "section{border-bottom:1px solid #aaa;margin-bottom:2em}</style><h1>Independent model disagreements</h1>"
        + f"<p>A: {html.escape(report['labelers'][0]['model'])}<br>B: {html.escape(report['labelers'][1]['model'])}</p>"
        + "<p>This is model agreement, not human agreement or evidence of accuracy.</p>" + "\n".join(sections), encoding="utf-8")
    for task, result in report["tasks"].items():
        print(f"{task}: n={result['n']} agreement={result['agreement']} kappa={result['kappa']}")
    table = ["| Task | Items | Agreement | Cohen kappa |", "|---|---:|---:|---:|"]
    for task, result in report["tasks"].items():
        value = f"{result['kappa']:.6f}" if result["kappa"] is not None else "undefined"
        table.append(f"| {TASKS[task][0]} | {result['n']} | {result['agreement']:.2%} | {value} |")
    (output / "README.md").write_text("# Independent model agreement\n\n"
        + "Model A: " + report["labelers"][0]["model"] + ". Model B: " + report["labelers"][1]["model"]
        + ". Both read only the blind questions and displayed evidence.\n\n" + "\n".join(table)
        + f"\n\nAll decisions agree on {report['items_all_agree']} items; at least one decision differs on {report['items_any_disagreement']} items. "
        + "Pair placement is reported separately in the JSON. Tasks have different questions and label spaces, so their kappas are not pooled.\n\n"
        + "Recorded model usage costs (configured rates, not a billing-console reconciliation): "
        + "; ".join(f"{m['model']}: ${m['recorded_cost_usd']:.6f}" for m in report["labelers"])
        + ". Hidden thinking is included in provider output-token usage.\n\n"
        + "Use disagreements.html for evidence and both explanations, or the three CSVs for analysis. "
        + "These are model labels; this result does not establish human agreement or annotation accuracy.\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("model_a", type=Path)
    p.add_argument("model_b", type=Path)
    p.add_argument("--output", type=Path, default=HERE / "model_comparison")
    args = p.parse_args()
    compare(args.model_a, args.model_b, args.output)
