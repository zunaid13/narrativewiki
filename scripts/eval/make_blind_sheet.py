"""[33] R4 — blind M3 sheet for a human annotator. $0, no model. (Moved from docs/eval/annotation/, C13.)

Run: .venv/Scripts/python.exe scripts/eval/make_blind_sheet.py anne 1 2 3 4 5
Writes docs/eval/annotation/<series>_m3_blind.md (what the annotator reads: page, placement, the
delivered line, the page sentence it came from, the page's own citations with their text <= t;
no agent verdict, note or reader) and <series>_m3_blind_key.json (item -> (t, row); keep closed).
Order is shuffled across cutoffs (seed 33). Items marked ★ are the double-label subset: a
surface-stratified random draw, 15 per cutoff, chosen without looking at any verdict (so ★ says
nothing about what an agent thought).
"""
import json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from narrativewiki import paths  # noqa: E402

series, cutoffs = sys.argv[1], [int(x) for x in sys.argv[2:]]
paths.set_active_series(series)
paras = {}
for v in range(1, max(cutoffs) + 1):
    for line in paths.parsed_volume(v).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            paras[r["para_id"]] = r["text"]
rng = random.Random(33)
items = []
for t in cutoffs:
    rows = [json.loads(l) for l in (ROOT / "docs/eval/precision" / f"{series}_v{t}_all.jsonl").open(encoding="utf-8")]
    by_surface = {}
    for n in range(len(rows)):
        by_surface.setdefault(rows[n]["surface"], []).append(n)
    star = set()
    while len(star) < 15 and any(by_surface.values()):  # round-robin over surfaces
        for s in sorted(by_surface):
            if by_surface[s] and len(star) < 15:
                star.add(by_surface[s].pop(rng.randrange(len(by_surface[s]))))
    items += [(t, n, rows[n], n in star) for n in range(len(rows))]
rng.shuffle(items)
out, key = [f"# {series} M3 blind sheet — cutoffs {cutoffs}\n\nFor each item write one label: "
            "supported / partial / unsupported / uncertain (appendix A, rules R1–R2 in "
            "docs/vision/PHASE_33.md 2026-09-30 evening). Use only text from volumes ≤ the item's cutoff. "
            "★ = double-label subset (do these first).\n"], {}
for i, (t, n, r, star) in enumerate(items, 1):
    iid = f"M3-{i:03d}"
    key[iid] = [t, n]
    out.append(f"\n## {iid}{' ★' if star else ''} — cutoff t={t}\n\n- page: `{r['page']}` · section: {r.get('section') or '—'} · "
               f"about: {r['entity']} · surface: {r['surface']}\n- **line:** {r['value']}\n")
    if r.get("unit"):
        out.append(f"- page sentence(s): {r['unit']}\n")
    ev = [e for e in (r.get("evidence") or []) if isinstance(e, str)]
    for e in ev[:4]:
        if e in paras and int(e[1:3]) <= t:
            out.append(f"  - `{e}` {paras[e][:600]}\n")
    out.append(f"- chapter on page: {r.get('chapter') or '—'}\n- LABEL: \n")
d = ROOT / "docs/eval/annotation"
(d / f"{series}_m3_blind.md").write_text("".join(out), encoding="utf-8")
(d / f"{series}_m3_blind_key.json").write_text(json.dumps(key, indent=0), encoding="utf-8")
print(f"{len(items)} items, {sum(s for *_, s in items)} starred -> {d / (series + '_m3_blind.md')}")
