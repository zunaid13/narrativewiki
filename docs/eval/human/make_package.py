"""Plan 0015 step 3 — the package two human readers label, blind to system and to the agent's labels. $0.

Run:  .venv/Scripts/python.exe docs/eval/human/make_package.py
Writes, beside this file:
  A_support.html      120 sampled assertions (20 per system: NarrativeWiki, B1, B2, B3, X1, X2), each with
                      the page it stands on, the page sentence it came from, the paragraphs the page cites
                      for it and the best-matching paragraphs of the books up to the cutoff
  A_answers.csv       one row per item to fill in (copy it once per reader: A_answers_<name>.csv)
  B_disclosure.html   60 (later fact, page sentence) pairs: every pair the agent called stated, implied or
                      uncertain, plus pairs it called absent
  B_answers.csv       to fill in (copy per reader)
  key.json            item -> system, cutoff, source row and the agent's labels. KEEP CLOSED until both
                      readers have finished; score.py reads it.
Sampling is seeded (33) and never looks at which way an agent label would move a result: part A takes,
per system, up to 8 atoms the agent did not call supported and fills to 20 with atoms it did; part B takes
all non-absent verdicts and a random draw of absent ones. Lives in docs/ (not scripts/) so that making or
changing it does not touch the frozen tree; it reads label files and parsed text only.
"""
from __future__ import annotations

import csv
import html
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EV = ROOT / "docs" / "eval"
SYSTEMS = [("B5", "anne"), ("B1", "anne@b1"), ("B2", "anne@b2"), ("B3", "anne@b3"), ("X1", "anne@x1"), ("X2", "anne@x2")]
STOP = set("the a an and of to in on at for with by from is was were are be been his her their its that this as it he she "
           "they who whom which had has have not but or after before into over while when also very more most some such "
           "than then there them what would could should about only just said says".split())
rng = random.Random(33)

paras: dict[str, str] = {}
for v in range(1, 6):
    for line in (ROOT / "data" / "anne" / "01_parsed" / f"v{v:02d}.jsonl").open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            paras[r["para_id"]] = r["text"]
ids = sorted(paras)


def toks(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in STOP]


doc_tok = {i: set(toks(paras[i])) for i in ids}
df = Counter(w for i in ids for w in doc_tok[i])


def best(query: str, t: int, skip: set[str], k: int = 4) -> list[str]:
    q = set(toks(query))
    scored = []
    for i in ids:
        if int(i[1:3]) > t or i in skip:
            continue
        s = sum(math.log(len(ids) / df[w]) for w in q & doc_tok[i])
        if s:
            scored.append((s, i))
    return [i for _, i in sorted(scored, reverse=True)[:k]]


def where(page: str, r: dict) -> str:
    kind = {"character": "Character page", "relationships": "Relationship (pair) page", "codex": "Shared page",
            "timeline": "Timeline", "index.md": "Index"}.get(page.split("/")[0], "Page")
    bits = [f"{kind}: {r.get('entity') or page}"]
    if r.get("section"):
        bits.append(f"section “{r['section']}”")
    if r.get("label") and r["label"] != r.get("section"):
        bits.append(str(r["label"]))
    return " · ".join(bits)


def para_html(i: str) -> str:
    return f"<p class='src'><b>{i}</b> {html.escape(paras[i])}</p>"


CSS = ("<style>body{font:15px/1.45 Georgia,serif;max-width:900px;margin:2em auto;padding:0 1em}"
       ".item{border:1px solid #bbb;border-radius:6px;padding:.8em 1em;margin:1.2em 0}"
       ".atom{font-size:1.15em;background:#eef4fb;padding:.4em .6em;border-left:4px solid #2f6db5}"
       ".src{font-size:.92em;color:#222;margin:.35em 0}.h{color:#555;font:13px sans-serif}"
       "h2{font:bold 17px sans-serif;margin:0 0 .4em}</style>")

# ---------------------------------------------------------------------------------------- part A
key: dict[str, dict] = {}
picked = []
for sysname, series in SYSTEMS:
    rows = []
    for t in range(1, 6):
        f = EV / "precision" / f"{series}_v{t}_all.jsonl"
        if f.exists():
            rows += [(t, n, json.loads(l)) for n, l in enumerate(f.open(encoding="utf-8"))]
    rows = [x for x in rows if (x[2].get("human") or "") in ("supported", "partial", "unsupported", "uncertain")]
    neg = [x for x in rows if x[2]["human"] != "supported"]
    pos = [x for x in rows if x[2]["human"] == "supported"]
    rng.shuffle(neg)
    rng.shuffle(pos)
    take = neg[:8]
    picked += [(sysname, series) + x for x in take + pos[:20 - len(take)]]
rng.shuffle(picked)
a_html = ["<meta charset='utf-8'>", CSS, "<h1>Part A — is the statement supported?</h1>",
          "<p>Read INSTRUCTIONS.md first. For each item fill one row of your copy of A_answers.csv.</p>"]
with (HERE / "A_answers.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["item", "supported (yes / partly / no / cannot tell)", "pair page only: did both take part? (yes / no / n-a)",
                "cited paragraphs alone enough? (yes / partly / no / none cited)", "comment"])
    for k, (sysname, series, t, n, r) in enumerate(picked, 1):
        item = f"A{k:03d}"
        cited = [e if isinstance(e, str) else e.get("para_id", "") for e in (r.get("evidence") or [])]
        cited = [c for c in cited if c in paras and int(c[1:3]) <= t][:6]
        extra = best(r["value"] + " " + (r.get("unit") or "") + " " + (r.get("entity") or ""), t, set(cited))
        key[item] = {"system": sysname, "series": series, "t": t, "row": n, "agent_page": r["human"],
                     "agent_atom": r.get("human_atom") or r["human"], "agent_cite": r.get("cite"), "surface": r["surface"]}
        a_html.append(
            f"<div class='item'><h2>{item} — the reader has finished volume {t}</h2>"
            f"<p class='h'>{html.escape(where(r['page'], r))}</p>"
            f"<p class='atom'>{html.escape(r['value'])}</p>"
            + (f"<p class='h'>The page text it comes from:</p><p>{html.escape(r['unit'])}</p>" if r.get("unit") else "")
            + "<p class='h'>Paragraphs the page cites for it:</p>"
            + ("".join(para_html(c) for c in cited) or "<p class='src'><i>none cited</i></p>")
            + f"<p class='h'>Other paragraphs of volumes 1–{t} that may bear on it (found by word overlap; the answer may be elsewhere):</p>"
            + "".join(para_html(c) for c in extra) + "</div>")
        w.writerow([item, "", "", "", ""])
(HERE / "A_support.html").write_text("\n".join(a_html), encoding="utf-8")

# ---------------------------------------------------------------------------------------- part B
def clean(witness: str) -> str:
    """The stored witness of a non-absent verdict carries the agent's reading of it; keep the page text only."""
    for cut in (" — romance-label class", "; implies the later", " -- the book-five", " —  romance-label"):
        witness = witness.split(cut)[0]
    witness = re.sub(r"\s*\((cites|the decision|engagement|also|marriage)[^)]*\)\.?", "", witness)
    return witness.strip()


pairs = []
for sysname, series in SYSTEMS:
    rows = [json.loads(l) for l in (EV / "leak_audit" / f"{series}_tree.jsonl").open(encoding="utf-8")]
    verdict = {(r["t"], r["claim"]): r for r in rows}
    for r in rows:
        if r["verdict"] != "absent" and r.get("witness"):
            pairs.append((sysname, series, r["t"], r["claim"], r["reveal"], clean(str(r["witness"])), r["verdict"]))
    absent = []
    for t in range(1, 5):
        f = EV / "leak_audit" / f"{series}_tree_candidates_v{t}.jsonl"
        if not f.exists():
            continue
        for l in f.open(encoding="utf-8"):
            c = json.loads(l)
            v = verdict.get((t, c["claim"]))
            if c["hits"] and v and v["verdict"] == "absent":
                h = rng.choice(c["hits"])
                absent.append((sysname, series, t, c["claim"], c["reveal"], f"{h['page']}: {h['sentence']}", "absent"))
    rng.shuffle(absent)
    pairs += absent[:6]
rng.shuffle(pairs)
pairs = pairs[:60] if len(pairs) > 60 else pairs
b_html = ["<meta charset='utf-8'>", CSS, "<h1>Part B — does the page sentence give away the later fact?</h1>",
          "<p>Read INSTRUCTIONS.md first. For each item fill one row of your copy of B_answers.csv.</p>"]
with (HERE / "B_answers.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["item", "verdict (stated / implied / neither / cannot tell)", "comment"])
    for k, (sysname, series, t, claim, reveal, witness, verdict_) in enumerate(pairs, 1):
        item = f"B{k:03d}"
        key[item] = {"system": sysname, "series": series, "t": t, "claim": claim, "reveal": reveal, "agent": verdict_}
        b_html.append(
            f"<div class='item'><h2>{item} — the reader has finished volume {t}</h2>"
            f"<p class='h'>A fact first revealed in volume {reveal}:</p><p class='atom'>{html.escape(claim)}</p>"
            f"<p class='h'>Text on a page of the volume-{t} wiki:</p><p>{html.escape(witness)}</p></div>")
        w.writerow([item, "", ""])
(HERE / "B_disclosure.html").write_text("\n".join(b_html), encoding="utf-8")
(HERE / "key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"part A: {len(picked)} items ({Counter(k_['system'] for i, k_ in key.items() if i[0] == 'A')}); agent page labels "
      f"{Counter(k_['agent_page'] for i, k_ in key.items() if i[0] == 'A')}")
print(f"part B: {len(pairs)} items; agent verdicts {Counter(k_['agent'] for i, k_ in key.items() if i[0] == 'B')}")
