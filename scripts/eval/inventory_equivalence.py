"""[34] Does the parallel atomizer (`local_eval`, 4 in flight) split pages as the serial one did? $0.

Run:  .venv/Scripts/python.exe scripts/eval/inventory_equivalence.py <old.jsonl> <new.jsonl>

Both files are `assertion_inventory.py` outputs for the same series and cutoff. Structured rows are
not atomized and must match exactly. For each prose/scene unit (same page, surface and unit text)
it reports how often the two runs gave the same number of atoms and the same atom texts. The serial
run sampled at temperature 0.1 once, so some difference is sampling, not parallelism; the numbers
go to MEASUREMENTS (CHANGES C32) either way.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict


def load(path: str) -> tuple[list[tuple], dict[tuple, list[str]]]:
    structured, units = [], defaultdict(list)
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("atom_of") is None:
            structured.append((r["page"], r["surface"], r.get("label"), r["value"], tuple(r.get("evidence") or [])))
        else:
            units[(r["page"], r["surface"], r["unit"])].append(r["value"])
    return sorted(structured), units


def main() -> None:
    old_s, old_u = load(sys.argv[1])
    new_s, new_u = load(sys.argv[2])
    shared = [k for k in old_u if k in new_u]
    same_n = sum(len(old_u[k]) == len(new_u[k]) for k in shared)
    same_text = sum(old_u[k] == new_u[k] for k in shared)
    atoms_old, atoms_new = sum(len(v) for v in old_u.values()), sum(len(v) for v in new_u.values())
    print(json.dumps({
        "structured_rows_identical": old_s == new_s, "structured_rows": [len(old_s), len(new_s)],
        "units": [len(old_u), len(new_u)], "units_shared": len(shared),
        "units_same_atom_count": round(same_n / len(shared), 3) if shared else None,
        "units_identical_atoms": round(same_text / len(shared), 3) if shared else None,
        "atoms_total": [atoms_old, atoms_new],
        "atoms_ratio_new_over_old": round(atoms_new / atoms_old, 3) if atoms_old else None,
    }, indent=1))


if __name__ == "__main__":
    main()
