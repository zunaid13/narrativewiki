"""Cohen's kappa for two independent reader CSVs, grouped by annotation task.

Stdlib only. No prior answer key is opened. Missing labels are errors by default.
The optional partial report explicitly lists excluded items. No pooled task kappa.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from build_packet import ALLOWED, HERE, TASKS


def kappa(a, b):
    if len(a) != len(b):
        raise ValueError("Label arrays must have equal length")
    n = len(a)
    if not n:
        return {"n": 0, "agreement": None, "chance_agreement": None, "kappa": None,
                "undefined_reason": "No paired labels", "confusion": {}}
    ca, cb = Counter(a), Counter(b)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum(ca[x] * cb[x] for x in ca.keys() | cb.keys()) / (n * n)
    undefined = math.isclose(pe, 1.0, rel_tol=0, abs_tol=1e-15)
    confusion = {}
    for x, y in zip(a, b):
        confusion.setdefault(x, Counter())[y] += 1
    return {"n": n, "agreement": po, "chance_agreement": pe,
            "kappa": None if undefined else (po - pe) / (1 - pe),
            "undefined_reason": "Both readers used only the same single category" if undefined else None,
            "reader_a_counts": dict(ca), "reader_b_counts": dict(cb),
            "confusion": {x: dict(c) for x, c in confusion.items()}}


def read_answers(path, expected):
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"item", "task", "label", "pair"} <= set(reader.fieldnames or []):
            raise ValueError(f"Missing CSV columns in {path}")
        for row in reader:
            item = row["item"].strip()
            if item not in expected or item in result:
                raise ValueError(f"Unknown or duplicate item {item!r} in {path}")
            spec = expected[item]
            task = row["task"].strip()
            if task != spec["task"]:
                raise ValueError(f"Wrong task for {item} in {path}")
            label, pair = row["label"].strip().lower(), row["pair"].strip().lower()
            if label and label not in ALLOWED[task]:
                raise ValueError(f"Invalid label {label!r} for {item} in {path}")
            allowed_pair = ("yes", "no") if spec["pair_required"] else ("n-a",)
            if pair and pair not in allowed_pair:
                raise ValueError(f"Invalid pair label {pair!r} for {item} in {path}")
            result[item] = {"label": label, "pair": pair}
    return result


def score(a_path, b_path, template=HERE / "reader_answers_blank.csv", allow_partial=False):
    # The blind template specifies applicability; neither the private manifest nor answers are read.
    with Path(template).open(encoding="utf-8-sig", newline="") as f:
        expected = {r["item"]: {"task": r["task"], "pair_required": r["pair"] != "n-a"}
                    for r in csv.DictReader(f)}
    a, b = read_answers(a_path, expected), read_answers(b_path, expected)
    missing = {"reader_a": [], "reader_b": []}
    for name, rows in (("reader_a", a), ("reader_b", b)):
        for i, spec in expected.items():
            if i not in rows or not rows[i]["label"] or (spec["pair_required"] and not rows[i]["pair"]):
                missing[name].append(i)
    if any(missing.values()) and not allow_partial:
        raise ValueError("Incomplete independent labels; fill both sheets or explicitly use --allow-partial. "
                         + "; ".join(f"{k}: {len(v)} incomplete items" for k, v in missing.items()))
    report = {"formula": "kappa = (observed agreement - chance agreement) / (1 - chance agreement)",
              "readers": [str(a_path), str(b_path)], "missing": missing,
              "status": "partial" if any(missing.values()) else "complete",
              "tasks": {}, "pooled_kappa": "Not computed: different annotation questions and label spaces."}
    for task in TASKS:
        ids = [i for i, spec in expected.items() if spec["task"] == task]
        paired = [i for i in ids if a.get(i, {}).get("label") and b.get(i, {}).get("label")]
        av, bv = [a[i]["label"] for i in paired], [b[i]["label"] for i in paired]
        result = kappa(av, bv)
        result.update({"expected_n": len(ids), "unpaired_items": [i for i in ids if i not in paired],
                       "disagreements": [i for i in paired if a[i]["label"] != b[i]["label"]]})
        # Preserve not-shown as an explicit category above; exclude it from yes-vs-rest agreement.
        substantive = [i for i in paired if "not shown" not in (a[i]["label"], b[i]["label"])]
        result["binary_yes_vs_rest"] = kappa([a[i]["label"] == "yes" for i in substantive],
                                              [b[i]["label"] == "yes" for i in substantive])
        result["binary_excluded_not_shown"] = [i for i in paired if i not in substantive]
        if task == "P":
            pair_ids = [i for i in ids if expected[i]["pair_required"]]
            pair_paired = [i for i in pair_ids if a.get(i, {}).get("pair") in ("yes", "no")
                           and b.get(i, {}).get("pair") in ("yes", "no")]
            result["pair_scene"] = kappa([a[i]["pair"] for i in pair_paired],
                                           [b[i]["pair"] for i in pair_paired])
            result["pair_scene"].update({"expected_n": len(pair_ids),
                "unpaired_items": [i for i in pair_ids if i not in pair_paired],
                "disagreements": [i for i in pair_paired if a[i]["pair"] != b[i]["pair"]]})
            combined = [i for i in substantive if not expected[i]["pair_required"] or i in pair_paired]
            result["supported_on_page"] = kappa(
                [a[i]["label"] == "yes" and (not expected[i]["pair_required"] or a[i]["pair"] == "yes") for i in combined],
                [b[i]["label"] == "yes" and (not expected[i]["pair_required"] or b[i]["pair"] == "yes") for i in combined])
        report["tasks"][task] = result
    return report


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("reader_a", type=Path)
    p.add_argument("reader_b", type=Path)
    p.add_argument("--template", type=Path, default=HERE / "reader_answers_blank.csv")
    p.add_argument("--allow-partial", action="store_true")
    p.add_argument("--output", type=Path, default=HERE / "human_agreement.json")
    args = p.parse_args()
    if args.reader_a.resolve() == args.reader_b.resolve():
        p.error("Provide two separate independently completed reader files")
    try:
        report = score(args.reader_a, args.reader_b, args.template, args.allow_partial)
    except ValueError as e:
        p.error(str(e))
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for task, result in report["tasks"].items():
        print(f"{TASKS[task][0]}: n={result['n']}, agreement={result['agreement']}, kappa={result['kappa']}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
