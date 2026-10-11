"""List \\res keys used by each .tex file whose value in results.tex is empty or undeclared.

Run: python docs/paper/_build/emptykeys.py [all]
"""
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parent.parent
BS = chr(92)
decl = re.compile(re.escape(BS + "declareres{") + r"([^}]*)\}\{[^}]*\}\{(.*)\}%")
use = re.compile(re.escape(BS) + r"res(?:pt)?\{([^}]*)\}")
vals = {}
for line in (root / "results.tex").read_text(encoding="utf-8").splitlines():
    m = decl.match(line)
    if m:
        vals[m.group(1)] = m.group(2)
print(len(vals), "keys declared,", sum(1 for v in vals.values() if v), "filled")
files = [p for d in ("sections", "appendix", "tables", "figures") for p in sorted((root / d).glob("*.tex"))]
for f in files:
    keys = use.findall(f.read_text(encoding="utf-8"))
    bad = sorted({k for k in keys if not vals.get(k)})
    und = sorted({k for k in keys if k not in vals})
    if bad or len(sys.argv) > 1:
        print(f"{f.relative_to(root)}: {len(keys)} uses, {len(bad)} empty, {len(und)} undeclared")
        for k in bad[:60]:
            print("   ", k)
