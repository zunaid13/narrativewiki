"""Plan 0015 step 3 — agreement of the human readers with each other and with the agent labels. $0.

Run:  .venv/Scripts/python.exe docs/eval/human/score.py
Reads every A_answers_<name>.csv / B_answers_<name>.csv beside this file (and A_adjudicated.csv /
B_adjudicated.csv when present) and key.json, and prints:
  - raw agreement and Cohen's kappa between each pair of readers;
  - each reader (and the adjudicated labels) against the agent's labels: overall, per system, and
    what the humans said for each agent label;
  - the items on which the readers disagree (to adjudicate).
Part A is scored as supported = "yes" against everything else (the paper counts only full support),
its citation column as "yes" against everything else, part B as disclosed = stated or implied
against everything else. Writes human_agreement.json.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
key = json.loads((HERE / "key.json").read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return (s or "").strip().lower().replace("can't", "cannot")


def load(prefix: str) -> dict[str, dict[str, list[str]]]:
    out = {}
    for f in sorted(HERE.glob(f"{prefix}_answers_*.csv")) + sorted(HERE.glob(f"{prefix}_adjudicated.csv")):
        name = f.stem.split("_", 2)[-1] if "answers" in f.stem else "ADJUDICATED"
        with f.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))[1:]
        got = {r[0].strip(): [norm(c) for c in r[1:]] for r in rows if r and r[0].strip() in key and any(c.strip() for c in r[1:4])}
        if got:
            out[name] = got
    return out


def kappa(a: list[int], b: list[int]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def report(title: str, readers: dict, human_pos, agent_pos, col: int, agent_field: str) -> dict:
    res = {}
    print(f"\n=== {title} ===")
    for (n1, r1), (n2, r2) in combinations([x for x in readers.items() if x[0] != "ADJUDICATED"], 2):
        items = sorted(set(r1) & set(r2))
        a = [int(human_pos(r1[i][col])) for i in items]
        b = [int(human_pos(r2[i][col])) for i in items]
        k = kappa(a, b)
        agree = sum(x == y for x, y in zip(a, b))
        print(f"{n1} vs {n2}: {agree}/{len(items)} agree, Cohen's kappa {k if k is None else round(k, 3)}")
        dis = [i for i, x, y in zip(items, a, b) if x != y]
        print("  to adjudicate:", ", ".join(dis) or "none")
        res[f"{n1}|{n2}"] = {"n": len(items), "agree": agree, "kappa": k, "disagree": dis}
    for name, r in readers.items():
        items = [i for i in sorted(r) if key[i].get(agent_field) not in (None, "")]
        h = [int(human_pos(r[i][col])) for i in items]
        g = [int(agent_pos(key[i][agent_field])) for i in items]
        k = kappa(h, g)
        print(f"{name} vs agent: {sum(x == y for x, y in zip(h, g))}/{len(items)} agree, kappa {k if k is None else round(k, 3)}; "
              f"human positive {sum(h)}, agent positive {sum(g)}")
        by_sys = defaultdict(lambda: [0, 0, 0])
        table = defaultdict(Counter)
        for i, x, y in zip(items, h, g):
            s = by_sys[key[i]["system"]]
            s[0] += 1
            s[1] += x
            s[2] += y
            table[key[i][agent_field]][r[i][col] or "(blank)"] += 1
        print("  per system (n, human positive, agent positive):", {k_: tuple(v) for k_, v in sorted(by_sys.items())})
        print("  agent label -> human answers:", {k_: dict(v) for k_, v in table.items()})
        res[f"{name}|agent"] = {"n": len(items), "kappa": k, "per_system": {k_: v for k_, v in by_sys.items()},
                                "confusion": {k_: dict(v) for k_, v in table.items()}}
    return res


def main() -> int:
    a, b = load("A"), load("B")
    if not a and not b:
        print("no A_answers_<name>.csv or B_answers_<name>.csv found beside this script")
        return 1
    out = {}
    if a:
        out["A_support"] = report("Part A: supported on the page (yes vs the rest)", a, lambda x: x == "yes",
                                  lambda x: x == "supported", 0, "agent_page")
        out["A_citation"] = report("Part A: cited paragraphs alone (yes vs the rest)", a, lambda x: x == "yes",
                                   lambda x: x == "sufficient", 2, "agent_cite")
    if b:
        out["B_disclosure"] = report("Part B: disclosed (stated or implied vs the rest)", b,
                                     lambda x: x in ("stated", "implied"), lambda x: x in ("stated", "implied"), 0, "agent")
    (HERE / "human_agreement.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\n-> docs/eval/human/human_agreement.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
