"""[33] Fill docs/paper/results.tex from docs/eval/paper_numbers.json and the assertion inventories. $0.

Run:  .venv/Scripts/python.exe scripts/papers/fill_results.py --note "MEASUREMENTS 2026-10-02 paper numbers (agent pilot)" [--dry]

Only keys already declared in results.tex are written, and only when a value was computed; every
other line is left byte-for-byte. Each filled line's trailing comment becomes `--note`, which must
name the ledger row (plan 0013: no number without a MEASUREMENTS row). Formats:
  per-cutoff proportion   0.870 (20/23)        M4 per cutoff   6/65 (counts before rates)
  mean over cutoffs       0.866 [0.793, 0.918] M4 mean, no event   0/220
  N (assertion inventory) 7,316                paired difference  $-0.002$ [$-0.100$, 0.054]
`N-<work>-t<k>-<S>` is the row count of docs/eval/inventory/<series>_v<k>.jsonl.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "docs" / "paper" / "results.tex"
LINE = re.compile(r"^(\\declareres\{([^}]*)\}\{[^}]*\})\{[^}]*\}(%.*)?$")


def _num(x: float) -> str:
    return f"${x:.3f}$" if x < 0 else f"{x:.3f}"


def values(work: str, base: str) -> dict[str, str]:
    rows = json.loads((ROOT / "docs" / "eval" / "paper_numbers.json").read_text(encoding="utf-8"))["results"]
    out, m4 = {}, {}
    for r in rows:
        key, v = r["key"], r["value"]
        if v is None:
            continue
        metric = key.split("-")[0]
        # 2026-10-04, maintainer: no intervals in the paper. Means only here; SD, median, lowest and
        # highest value over the cutoffs come from scripts/papers/summary_stats.py (STAT-* keys).
        if "minus" in key:
            out[key] = _num(v)
        elif "-avg-" in key:
            out[key] = f"{v:.3f}"
        elif metric == "M4":
            out[key] = f"{r['num']:g}/{r['den']:g}"
            n, d = m4.get(key.rsplit("-", 1)[1], (0, 0))
            m4[key.rsplit("-", 1)[1]] = (n + r["num"], d + r["den"])
        else:
            out[key] = f"{v:.3f} ({r['num']:g}/{r['den']:g})"
    for system, (n, d) in m4.items():  # counts before rates; a zero is 0/n, never 0.000 with a degenerate interval
        if n == 0:
            out[f"M4-{work}-avg-{system}"] = f"0/{d:g}"
    counts: dict[str, list[int]] = {}
    for inv in sorted((ROOT / "docs" / "eval" / "inventory").glob(f"{base}*_v*.jsonl")):
        series, t = inv.stem.rsplit("_v", 1)
        system = series.split("@")[1].upper() if "@" in series else "B5"
        if series.split("@")[0] != base or not system[:1] in "BX":
            continue
        n = sum(1 for line in inv.open(encoding="utf-8") if line.strip())
        out[f"N-{work}-t{t}-{system}"] = f"{n:,}"
        counts.setdefault(system, []).append(n)
    for system, ns in counts.items():
        out[f"N-{work}-avg-{system}"] = f"{round(sum(ns) / len(ns)):,}"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="anne")
    ap.add_argument("--series", default="anne", help="base series whose inventories give N")
    ap.add_argument("--note", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    vals, filled, lines = values(a.work, a.series), 0, []
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        m = LINE.match(line)
        if m and m.group(2) in vals:
            line = f"{m.group(1)}{{{vals[m.group(2)]}}}% {a.note}"
            filled += 1
        lines.append(line)
    declared = {m.group(2) for m in map(LINE.match, lines) if m}
    print(f"{filled} keys filled; computed but not declared: {sorted(set(vals) - declared)}")
    if not a.dry:
        RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
