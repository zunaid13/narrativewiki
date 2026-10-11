"""Count disclosure assessments and unique subject facts from stored Claude verdicts ($0).

Run: python scripts/eval/disclosure_units.py --output docs/eval/disclosure_units_20261010.json
Read the reported original/treated Anne cells only; never call a model or modify labels.
A unique fact is (character, claim, reveal), so reciprocal marriage facts remain distinct.
These counts do not identify independent events or extraction errors. Error mechanisms
require reading the stored witnesses; matching wording is not an event identity rule.
Duplicate fact-cutoff records and ineligible reveal dates fail rather than inflate counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEMS = {"B1": "b1", "B2": "b2", "B3": "b3", "B4": "b4-v2",
           "B5": "v2", "X1": "x1", "X2": "x2"}
INPUT_BOUNDED = ("B1", "B2", "B3", "B4", "B5")
VERDICTS = {"absent", "stated", "implied", "uncertain"}


def summarize(rows: list[dict]) -> dict:
    seen = set()
    facts = set()
    confirmed = set()
    inclusive = set()
    counts = Counter()
    for row in rows:
        t, reveal = row["t"], row["reveal"]
        if type(t) is not int or type(reveal) is not int or not 1 <= t < reveal <= 5:
            raise ValueError("Disclosure requires 1 <= cutoff < reveal <= 5")
        fact = (row["character"], row["claim"], reveal)
        if not fact[0] or not fact[1]:
            raise ValueError("A fact requires a character and claim")
        assessment = (t, *fact)
        if assessment in seen:
            raise ValueError(f"Duplicate fact-cutoff assessment: {assessment}")
        verdict = row["verdict"]
        if verdict not in VERDICTS:
            raise ValueError(f"Unknown verdict: {verdict}")
        seen.add(assessment)
        facts.add(fact)
        counts[verdict] += 1
        if verdict in {"stated", "implied"}:
            confirmed.add(fact)
            inclusive.add(fact)
        elif verdict == "uncertain":
            inclusive.add(fact)
    return {
        "assessments": len(seen), "unique_subject_facts": len(facts),
        "confirmed_assessments": counts["stated"] + counts["implied"],
        "uncertain_assessments": counts["uncertain"],
        "inclusive_assessments": counts["stated"] + counts["implied"] + counts["uncertain"],
        "confirmed_unique_subject_facts": len(confirmed),
        "inclusive_unique_subject_facts": len(inclusive),
    }


def report() -> dict:
    conditions = {}
    for condition, base in (("original", "anne"), ("treated", "anne-decon")):
        cells = {}
        for system, suffix in SYSTEMS.items():
            path = ROOT / "docs" / "eval" / "leak_audit" / f"{base}@{suffix}_tree.jsonl"
            raw = path.read_bytes()
            rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
            cells[system] = {"source": path.relative_to(ROOT).as_posix(),
                             "sha256": hashlib.sha256(raw).hexdigest(), **summarize(rows)}
        conditions[condition] = {
            "systems": cells,
            "input_bounded": {"systems": list(INPUT_BOUNDED), **{
                key: sum(cells[s][key] for s in INPUT_BOUNDED)
                for key in ("assessments", "confirmed_assessments", "uncertain_assessments", "inclusive_assessments")
            }},
        }
    return {"run_id": "reviewer-concerns-20261010", "conditions": conditions,
            "unit": "Unique subject fact = character, claim, reveal; repeated cutoffs collapse, reciprocal facts do not.",
            "limits": "Counts preserve stored judgments. Unique facts are not independent events or unique extraction errors."}


def paper_values(result: dict) -> dict[str, tuple[str, str]]:
    values = {}
    for condition, work in (("original", "anne"), ("treated", "annedecon")):
        cells = result["conditions"][condition]["systems"]
        for system, cell in cells.items():
            values[f"M4U-{work}-{system}"] = (
                f"{cell['confirmed_unique_subject_facts']}/{cell['unique_subject_facts']}",
                f"{condition}, {system}: confirmed unique subject facts over assessed unique subject facts")
    original = result["conditions"]["original"]
    pooled = original["input_bounded"]
    values["M4-anne-total-cut"] = (
        f"{pooled['confirmed_assessments']} of {pooled['assessments']:,}",
        "confirmed disclosure assessments, B1-B5, with later information withheld from page generation")
    values["M4-anne-total-cut-incl"] = (
        f"{pooled['inclusive_assessments']} of {pooled['assessments']:,}",
        "confirmed or uncertain disclosure assessments, B1-B5")
    values["M4-anne-uncertain"] = (
        ", ".join(f"{original['systems'][s]['uncertain_assessments']} ({s})" for s in SYSTEMS),
        "uncertain M4 verdicts by system including B4, t=1..4")
    return values


def fill_paper(result: dict) -> None:
    import re
    paper = ROOT / "docs" / "paper"
    values = paper_values(result)
    note = "MEASUREMENTS 2026-10-10 reviewer concerns: disclosure units; reviewer-concerns-20261010"
    lines = []
    for line in (paper / "results.tex").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\\declareres\{([^}]+)\}", line)
        if match and match[1] in values:
            value, description = values.pop(match[1])
            line = f"\\declareres{{{match[1]}}}{{{description}}}{{{value}}}% {note}"
        lines.append(line)
    for key, (value, description) in values.items():
        lines.append(f"\\declareres{{{key}}}{{{description}}}{{{value}}}% {note}")
    (paper / "results.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fill-paper", action="store_true", help="Update only disclosure-unit result declarations")
    args = parser.parse_args()
    result = report()
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    if args.fill_paper:
        fill_paper(result)
    for name, condition in result["conditions"].items():
        print(name, json.dumps(condition["input_bounded"]))
        for system, cell in condition["systems"].items():
            print(system, json.dumps({k: v for k, v in cell.items() if k not in {"source", "sha256"}}))


if __name__ == "__main__":
    main()
