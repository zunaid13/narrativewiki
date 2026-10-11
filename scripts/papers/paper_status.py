"""What is still missing from the LaTeX paper, and what would break its build. $0, no LaTeX needed.

Run: .venv/Scripts/python.exe scripts/papers/paper_status.py [--list-empty] [--steps]
Checks docs/paper/: every \\input exists; every citation key is in refs.bib; every \\res{KEY} is
declared in results.tex (and every declaration is used); braces and \\begin/\\end balance per file;
results.tex descriptions contain no character that breaks typesetting. Then counts what is left
to fill: empty result values, \\TBD, \\CITE and \\TODO per file. Exit 1 on any structural error.
--steps: progress per step of plan 0014, from the regexes in its master table (first match wins).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "docs" / "paper"
TRACKER = ROOT / "docs" / "vision" / "plans" / "0014-paper-values-tracker.md"


def strip_comments(tex: str) -> str:
    # Literal prompt/output listings can contain elided JSON braces and TeX-like
    # strings. They are printed verbatim, so they are not manuscript structure.
    listing_envs = {"verbatim", "lstlisting", "tcblisting"}
    listing_envs.update(re.findall(r"\\newtcblisting\{([^}]+)\}", tex))
    for env in listing_envs:
        tex = re.sub(r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"\}",
                     "", tex, flags=re.DOTALL)
    return re.sub(r"(?<!\\)%.*", "", tex)


def tracker_steps() -> list[tuple[str, str, str | None, str | None]]:
    """(step, status, result-key regex, placeholder regex) per master-table row of plan 0014."""
    steps = []
    for line in TRACKER.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\|\s*S\d\d\s*\|", line):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        pattern = [m.group(1) if (m := re.search(r"`([^`]+)`", c)) else None for c in cells[2:4]]
        steps.append((cells[0], cells[-1], pattern[0], pattern[1]))
    return steps


def step_report(declared: dict[str, tuple[str, str]], placeholders: list[str]) -> None:
    steps = tracker_steps()
    owner = lambda item, col: next((s for s in steps if s[col] and re.fullmatch(s[col], item)), None)
    keys, left, unassigned = Counter(), Counter(), []
    for k, (_, v) in declared.items():
        s = owner(k, 2)
        if s is None:
            unassigned.append(k)
            continue
        keys[s[0], "total"] += 1
        keys[s[0], "filled"] += bool(v.strip())
    for p in placeholders:
        s = owner(p, 3)
        if s is None:
            unassigned.append(p)
        else:
            left[s[0]] += 1
    print(f"{'step':5} {'status':16} {'result keys filled':>19}  placeholders left")
    for step, status, _, _ in steps:
        total = keys[step, "total"]
        filled = f"{keys[step, 'filled']}/{total}" if total else "-"
        print(f"{step:5} {status:16} {filled:>19}  {left[step] or '-'}")
    if unassigned:
        print("not assigned to any step:", ", ".join(sorted(set(unassigned))))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-empty", action="store_true", help="print every result key still empty")
    ap.add_argument("--steps", action="store_true", help="progress per step of plan 0014")
    args = ap.parse_args()
    files = sorted(PAPER.rglob("*.tex"))
    text = {p: strip_comments(p.read_text(encoding="utf-8")) for p in files}
    errors: list[str] = []

    for p, t in text.items():
        for target in re.findall(r"\\input\{([^}]+)\}", t):
            if not (PAPER / f"{target}.tex").is_file():
                errors.append(f"{p.relative_to(PAPER)}: \\input{{{target}}} does not exist")
        if t.count("{") - t.count("\\{") != t.count("}") - t.count("\\}"):
            errors.append(f"{p.relative_to(PAPER)}: unbalanced braces")
        envs = Counter(re.findall(r"\\begin\{([^}]+)\}", t))
        envs.subtract(Counter(re.findall(r"\\end\{([^}]+)\}", t)))
        errors += [f"{p.relative_to(PAPER)}: \\begin/\\end mismatch for {e}" for e, n in envs.items() if n]

    bib = set(re.findall(r"@\w+\{([^,\s]+),", (PAPER / "refs.bib").read_text(encoding="utf-8")))
    cited = {k.strip() for t in text.values() for group in re.findall(r"\\cite[pt]?\{([^}]+)\}", t)
             for k in group.split(",")}
    errors += [f"citation key not in refs.bib: {k}" for k in sorted(cited - bib)]

    registry = strip_comments((PAPER / "results.tex").read_text(encoding="utf-8"))
    declared = {m[0]: (m[1], m[2]) for m in re.findall(r"\\declareres\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}", registry)}
    used = {k for p, t in text.items() if p.name != "macros.tex" for k in re.findall(r"\\res\{([^}]+)\}", t)}
    errors += [f"\\res key used but not declared: {k}" for k in sorted(used - set(declared))]
    errors += [f"results.tex description of {k} contains a character that breaks typesetting"
               for k, (desc, _) in declared.items() if re.search(r"[_%&#$]", desc)]

    empty = sorted(k for k, (_, v) in declared.items() if not v.strip())
    print(f"results: {len(declared) - len(empty)}/{len(declared)} declared values filled; "
          f"{len(used)} used in the text; {len(set(declared) - used)} declared but unused (fine for later tables)")
    if args.list_empty:
        for k in empty:
            print(f"  empty  {k}: {declared[k][0]}")
    print(f"citations: {len(cited)} keys cited, {len(bib)} in refs.bib, {len(bib - cited)} unused")
    print("left to fill, per file (TBD / CITE / TODO):")
    for p, t in text.items():
        n = (len(re.findall(r"\\TBD\{", t)), len(re.findall(r"\\CITE\{", t)), len(re.findall(r"\\TODO\{", t)))
        if any(n) and p.name != "macros.tex":
            print(f"  {str(p.relative_to(PAPER)):32} {n[0]:3} / {n[1]:2} / {n[2]:2}")
    if args.steps:
        placeholders = [pid for p, t in text.items() if p.name != "macros.tex"
                        for pid in re.findall(r"\\TBD\{([^}]*)\}", t)]
        placeholders += ["CITE" for p, t in text.items() if p.name != "macros.tex" for _ in re.findall(r"\\CITE\{", t)]
        step_report(declared, placeholders)
    for e in errors:
        print("ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
