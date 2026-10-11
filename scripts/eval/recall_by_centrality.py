"""Gold recall split by subject centrality, facts lost between cutoffs, and artifact size.

Reads stored labels and built trees only (no model call):
  docs/eval/recall_hand/<series>@<tag>_v<t>.json   {gold fact: "yes"|"no"}
  dist/anne@<tag>/wiki/v0<t>/**/*.md               pages (source/ and index.md excluded)
Writes docs/eval/recall_by_centrality.json and prints the same table.

"Central" is fixed before looking at any system's labels: the three subjects with the most
gold assessments (Anne Shirley, Gilbert Blythe, Diana Barry; 141 of 335).

Usage: .venv/Scripts/python.exe -X utf8 scripts/eval/recall_by_centrality.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RH = ROOT / "docs/eval/recall_hand"
CENTRAL = ("C Anne Shirley", "C Gilbert Blythe", "C Diana Barry")
SYSTEMS = (("B5", "v2"), ("B1", "b1"), ("B2", "b2"), ("B3", "b3"), ("B4", "b4-v2"), ("X2", "x2"))
CUTOFFS = range(1, 6)


def content_words(md: str) -> int:
    """Words a reader reads: citations, source lists and front matter removed, links kept as text."""
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)
    md = re.sub(r"<sub>.*?</sub>", "", md, flags=re.S)
    md = re.sub(r"(?m)^_Sources:.*$", "", md)
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    return len(md.split())


def main() -> None:
    out = {"central_subjects": CENTRAL, "recall": {}, "per_subject": {}, "versus_b1_and_b2": {},
           "drops": {}, "artifact": {}}
    for series in ("anne", "anne-decon"):
        lab = {s: {t: json.loads((RH / f"{series}@{tag}_v{t}.json").read_text("utf-8"))
                   for t in CUTOFFS} for s, tag in SYSTEMS}
        out["recall"][series] = {}
        for group, keep in (("central", True), ("other", False)):
            out["recall"][series][group] = {}
            for s in lab:
                cells = []
                for t in CUTOFFS:
                    vals = [v for f, v in lab[s][t].items()
                            if (f.split("|")[0].strip() in CENTRAL) == keep]
                    cells.append([sum(v == "yes" for v in vals), len(vals)])
                out["recall"][series][group][s] = {
                    "per_cutoff": cells, "pooled": [sum(c[0] for c in cells), sum(c[1] for c in cells)]}
        out["per_subject"][series] = {
            subj: {s: [sum(v == "yes" for t in CUTOFFS for f, v in lab[s][t].items()
                           if f.split("|")[0].strip() == subj),
                       sum(f.split("|")[0].strip() == subj for t in CUTOFFS for f in lab[s][t])]
                   for s in lab} for subj in CENTRAL}
        # facts B5 conveys that neither B1 nor B2 does, and the reverse, with their cutoffs
        only = {"b5_only": {}, "b1_and_b2_only": {}}
        for t in CUTOFFS:
            for f, v in lab["B5"][t].items():
                others = {lab["B1"][t].get(f), lab["B2"][t].get(f)}
                if v == "yes" and others == {"no"}:
                    only["b5_only"].setdefault(f, []).append(t)
                if v == "no" and others == {"yes"}:
                    only["b1_and_b2_only"].setdefault(f, []).append(t)
        out["versus_b1_and_b2"][series] = only
        # a fact conveyed at t and not conveyed at t+1: the page lost it as the reader advanced
        out["drops"][series] = {
            s: sum(v == "yes" and lab[s][t + 1].get(f) == "no"
                   for t in range(1, 5) for f, v in lab[s][t].items()) for s in lab}
    for s, tag in SYSTEMS[:4]:
        out["artifact"][s] = []
        for t in CUTOFFS:
            pages = [p for p in (ROOT / f"dist/anne@{tag}/wiki/v0{t}").rglob("*.md")
                     if "source" not in p.parts and p.name != "index.md"]
            anne = (ROOT / f"dist/anne@{tag}/wiki/v0{t}/character/anne-shirley.md").read_text(
                "utf-8", errors="replace")
            # "### <character>" blocks under "## Relationships"; the places block is not a character
            rel = anne.split("\n## Relationships", 1)[-1].split("\n## ", 1)[0]
            out["artifact"][s].append({
                "cutoff": t, "pages": len(pages),
                "words": sum(len(p.read_text("utf-8", errors="replace").split()) for p in pages),
                "content_words": sum(content_words(p.read_text("utf-8", errors="replace"))
                                     for p in pages),
                "anne_shirley_page_words": len(anne.split()),
                "anne_shirley_content_words": content_words(anne),
                "anne_shirley_relationship_blocks": sum(
                    ln.startswith("### ") and "Organisations" not in ln for ln in rel.splitlines())})
    (ROOT / "docs/eval/recall_by_centrality.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")

    for series, groups in out["recall"].items():
        for group, systems in groups.items():
            print(f"{series} / {group}")
            for s, r in systems.items():
                y, n = r["pooled"]
                print(f"  {s}: " + "  ".join(f"{a}/{b}" for a, b in r["per_cutoff"])
                      + f"   pooled {y}/{n} = {y / n:.3f}")
        print(f"{series} / drops t->t+1: {out['drops'][series]}")
    for s, rows in out["artifact"].items():
        print(f"{s}: " + "  ".join(
            f"{r['pages']}p/{r['words']}w/anne={r['anne_shirley_page_words']}w"
            f"/{r['anne_shirley_relationship_blocks']}rel" for r in rows))
        print(f"{s} content words (no citations): " + "  ".join(
            f"{r['content_words']}/anne={r['anne_shirley_content_words']}" for r in rows)
            + f"   total {sum(r['content_words'] for r in rows)}")
    for series, only in out["versus_b1_and_b2"].items():
        print(f"{series}: " + ", ".join(
            f"{k} {len(v)} facts / {sum(map(len, v.values()))} assessments" for k, v in only.items()))
        print(f"{series} per subject: {out['per_subject'][series]}")


if __name__ == "__main__":
    main()
