"""fill_decon.py: the results.tex keys of the decontaminated condition, from the observation files. $0.

Run from the repository root, after the observations of every decontaminated system are current:
  for s in v2:B5 b1:B1 b2:B2 b3:B3 b4-v2:B4 x1:X1 x2:X2; do
    .venv/Scripts/python.exe scripts/eval/paper_observations.py "anne-decon@${s%%:*}" --system "${s##*:}" --work annedecon; done
  .venv/Scripts/python.exe docs/eval/labelling_tools/apply_pair_rule.py anne-decon@v2 B5
  .venv/Scripts/python.exe docs/paper/_build/fill_decon.py

Per cutoff a value is the ratio of counts; the mean and the sample SD are over the cutoffs present (as
scripts/papers/summary_stats.py does for the original text). A key already declared in results.tex is overwritten
in place; the others are written between the markers below, which a rerun replaces. All seven systems have five
cutoffs since 2026-10-07 (long context and full text were built last). Every value has its row in docs/MEASUREMENTS.md (2026-10-06 and
2026-10-07 rows on `anne-decon@*`), named in NOTE.
"""
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "docs" / "paper" / "results.tex"
OBS = ROOT / "docs" / "eval" / "observations"
BS = chr(92)
NOTE = "MEASUREMENTS 2026-10-06 and 2026-10-07 rows on anne-decon (fill_decon.py)"
BEGIN, END = "% ==== BEGIN fill_decon.py ====", "% ==== END fill_decon.py ===="
SYSTEMS = [("B5", "anne-decon@v2"), ("B2", "anne-decon@b2"), ("B3", "anne-decon@b3"), ("B4", "anne-decon@b4-v2"),
           ("X1", "anne-decon@x1"), ("B1", "anne-decon@b1"), ("X2", "anne-decon@x2")]
NAME = {"B5": "NarrativeWiki", "B2": "prefix retrieval", "B3": "LightRAG", "B4": "graph baseline", "X1": "closed book",
        "B1": "long context", "X2": "full text"}
METRIC = {"M1": "recall", "M3": "precision", "M8": "citation sufficiency"}


def signed(x):
    return f"${'+' if x >= 0 else '-'}{abs(x):.3f}$"


V = {}  # key -> (value, description)
LOSS = {}  # system -> original minus treated mean recall, for the systems that read
orig ={r["key"]: r["value"] for r in json.loads((ROOT / "docs" / "eval" / "paper_numbers.json").read_text(encoding="utf-8"))["results"]
        if "value" in r}
for system, series in SYSTEMS:
    f = OBS / f"{series}_{system}.jsonl"
    if not f.exists():
        continue
    rows = [json.loads(l) for l in f.open(encoding="utf-8")]
    assert {r["work"] for r in rows} == {"annedecon"}, f"{f.name}: regenerate with --work annedecon"
    cell = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("den"):
            cell[(r["metric"], r["cutoff"])][0] += r["num"]
            cell[(r["metric"], r["cutoff"])][1] += r["den"]
    for m, word in METRIC.items():
        if m == "M8" and system == "X1":
            continue  # it cites nothing: printed as a dash
        ratios = []
        for t in range(1, 6):
            n, d = cell.get((m, t), (0, 0))
            if d:
                V[f"{m}-annedecon-t{t}-{system}"] = (f"{n / d:.3f} ({n:g}/{d:g})", f"treated text, {word}, t={t}, {NAME[system]}")
                ratios.append(n / d)
        if len(ratios) == 5:
            V[f"{m}-annedecon-avg-{system}"] = (f"{st.mean(ratios):.3f}", f"treated text, {word}, mean over t, {NAME[system]}")
            V[f"{m}-annedecon-sd-{system}"] = (f"{st.stdev(ratios):.3f}", f"treated text, {word}, sample SD over t, {NAME[system]}")
            o = orig.get(f"{m}-anne-avg-{system}")
            if o is not None:
                # Taken before rounding, like every difference in the paper (Section 5, Statistics): LightRAG's
                # recall difference is -0.067, where the two printed means (0.470, 0.536) differ by 0.066.
                V[f"{m}-annedecon-diff-{system}"] = (signed(st.mean(ratios) - o),
                                                    f"{word}, treated minus original mean, {NAME[system]}")
                if m == "M1" and system != "X1":  # the systems that are given text
                    LOSS[system] = o - st.mean(ratios)
    m4 = [cell.get(("M4", t), (0, 0)) for t in range(1, 5)]
    for t, (n, d) in enumerate(m4, 1):
        if d:
            V[f"M4-annedecon-t{t}-{system}"] = (f"{n:g}/{d:g}", f"treated text, stated or implied disclosures, t={t}, {NAME[system]}")
    if all(d for _, d in m4):
        total = f"{sum(n for n, _ in m4):g} of {sum(d for _, d in m4):g}"
        V[f"M4-annedecon-total-{system}"] = (total, f"treated text, stated or implied disclosures, t=1..4, {NAME[system]}")
        V[f"M4-annedecon-avg-{system}"] = (total, None)
        unc = sum(1 for r in rows if r["metric"] == "M4" and r.get("label") == "uncertain")
        V[f"M4-annedecon-uncertain-{system}"] = (str(unc), f"treated text, uncertain disclosure verdicts, {NAME[system]}")
    m3 = [r for r in rows if r["metric"] == "M3"]
    if system == "X1" and m3:
        V["M3-annedecon-unsup-X1"] = (str(sum(1 for r in m3 if r.get("label") == "unsupported")),
                                      "treated text, closed book, sampled statements labelled unsupported, of 200")
        n1 = sum(cell.get(("M1", t), (0, 0))[0] for t in range(1, 6))
        d1 = sum(cell.get(("M1", t), (0, 0))[1] for t in range(1, 6))
        V["M1-annedecon-count-X1"] = (f"{n1:g} of {d1:g}", "treated text, closed book, gold facts conveyed over all fact-by-cutoff reads")
    if system == "B5" and len(m3) == 200:
        V["M3A-annedecon-avg-B5"] = (f"{sum(1 for r in m3 if r.get('label_atom') == 'supported') / 200:.3f}",
                                     "treated text, share of sampled statements true as statements, NarrativeWiki")

if len(LOSS) == 6:  # abstract, Section 6.4, conclusion: "the systems that read lose at most ..."
    worst = max(LOSS, key=LOSS.get)
    V["M1-annedecon-maxloss"] = (f"{LOSS[worst]:.3f}", f"largest loss of mean recall on the treated text among the six systems given text ({NAME[worst]})")

# a cell that is not labelled yet is declared empty, so that its table cell prints a dash and not an error
for system in ("B5", "B1", "B2", "B3", "B4", "X1", "X2"):
    for m, word in METRIC.items():
        for suffix, what in [(f"t{t}", f"t={t}") for t in range(1, 6)] + [("avg", "mean over t"), ("sd", "sample SD over t")]:
            V.setdefault(f"{m}-annedecon-{suffix}-{system}", ("", f"treated text, {word}, {what}, {NAME[system]} (not labelled)"))

head = BS + "declareres{"
lines = RES.read_text(encoding="utf-8").split("\n")
if BEGIN in lines:  # a rerun replaces its own block
    a, b = lines.index(BEGIN), lines.index(END)
    del lines[a:b + 1]
    if a < len(lines) and not lines[a].strip():  # the blank line this script writes after END; summary_stats.py strips it
        del lines[a]
seen, out = set(), []
for ln in lines:
    if ln.startswith(head):
        key = ln[len(head):].split("}", 1)[0]
        if key in V:
            m = re.match(r"^(.declareres[{][^}]*[}][{][^}]*[}])[{]", ln)
            assert m, ln
            ln = f"{m.group(1)}{{{V[key][0]}}}% {NOTE}"
            seen.add(key)
    out.append(ln)
new = sorted(k for k in V if k not in seen and V[k][1])
block = [BEGIN] + [f"{head}{k}}}{{{V[k][1]}}}{{{V[k][0]}}}% {NOTE}" for k in new] + [END, ""]
marker = next(i for i, ln in enumerate(out) if ln.startswith("% ==== BEGIN summary_stats.py"))
out[marker:marker] = block
RES.write_text("\n".join(out), encoding="utf-8", newline="\n")
print(f"{len(seen)} keys overwritten, {len(new)} keys in the fill_decon block")
for s, _ in SYSTEMS:
    print(s, " ".join(f"{m} {V.get(f'{m}-annedecon-avg-{s}', ('-',))[0]}" for m in METRIC), "M4", V.get(f"M4-annedecon-total-{s}", ("-",))[0])
