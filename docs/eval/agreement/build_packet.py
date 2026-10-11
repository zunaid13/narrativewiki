"""Consolidate the existing paper review sample; deterministic, stdlib, no model calls.

Preserves every displayed evidence paragraph and accepted answer. Randomizes order only;
does not redraw the sample, regenerate evidence, or change any evaluation label.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "docs/eval/human_check"
SEED = 20261010
FILES = {"G": "G_gold.html", "R": "R_recall.html",
         "P": "P_precision.html", "C": "C_citation.html"}
TASKS = {
    "G": ("Gold evidence", "Do the displayed source paragraphs establish this fact as worded?"),
    "R": ("M1 recall", "Do the displayed wiki sentences convey the core of this gold fact?"),
    "P": ("M3 precision", "Do the eligible source paragraphs support this statement in full?"),
    "C": ("M8 citation sufficiency", "Do the cited paragraphs alone establish this statement in full?"),
}
ALLOWED = {"G": ("yes", "partly", "no", "not shown"),
           "R": ("yes", "partly", "no"),
           "P": ("yes", "partly", "no", "not shown"),
           "C": ("yes", "partly", "no", "none cited")}
FIELDS = ["item", "task", "label", "pair", "comment"]
RULES = """
<h2>Reader instructions</h2>
<p>Work alone. Judge only the displayed text, with the item's volume cutoff. Do not use
novel memory. Do not discuss answers or open the answer key until both readers have
submitted their first-pass labels. Record labels in your own CSV, matching each Q identifier.
Keep notes on unclear items. Record your role, book familiarity, start/end times,
compensation if applicable and consent to release labels separately.</p>
<p><b>Gold evidence (G):</b> yes = the source establishes the fact as worded;
partly = its core is present but a stated detail is missing; no = relevant text does
not establish it or establishes something different. not shown = none of the text bears on it.
This checks the evidence paragraph, not the earliest reveal volume across the whole novel.</p>
<p><b>M1 recall (R):</b> yes = the wiki conveys the same person, event/relation/attribute
and object, even in different words. Incidental dates or colours may be omitted.
A missing core element is no; partly = only one part of a conjunction is conveyed.
A plan is not completion; an engagement is not a marriage. Judge the displayed candidate
sentences. A no here does not independently prove absence from the entire wiki.</p>
<p><b>M3 precision (P):</b> yes = all elements are supported of the right person with
the right force (a rumour remains a rumour); partly = a core is supported but a detail
is missing or a passing state is promoted to a lasting trait; no = relevant text does
not support it. not shown = nothing displayed bears on it. Consider all eligible source
paragraphs shown, not just citations.</p>
<p><b>Pair pages:</b> additionally answer pair = yes or no: do both named people take
part in at least one episode of the scene summary containing this line, present and acting
or speaking? Merely being mentioned, remembered, written to, dead or watching from a
distance does not count. Sharing a chapter alone does not count. For all other items
the pair field is n-a. Keep factual support and pair placement as separate decisions.</p>
<p><b>M8 citation sufficiency (C):</b> yes = the cited eligible paragraphs alone, jointly
if needed, establish every element; partly = a core but not all details; no = they do
not establish it; none cited = there are no paragraph citations. No outside context is
allowed for this task. A chapter link is not a paragraph citation.</p>
<p>not shown is an evidence-coverage flag, not a negative factual verdict. Record it
and retain the first pass if more context is later supplied.</p>
"""
CSS = """<meta charset="utf-8"><style>
body{font:16px/1.5 Georgia,serif;max-width:960px;margin:2em auto;padding:0 1em;color:#18212b}
.item{border:1px solid #ccd2da;padding:1.1em;margin:1.6em 0;break-before:auto}
.atom{background:#edf4ff;border-left:4px solid #3974ac;padding:.8em;font-weight:bold}
.h{font:14px/1.5 system-ui,sans-serif;color:#465365}.src{font-size:.94em}
.answer{background:#fff4df;border:1px solid #d4aa60;padding:1em}.question{font-weight:bold}
@media print{body{max-width:none;margin:0}.item{break-inside:auto}h2{break-after:avoid}}
</style>"""


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    keyed = {r["item"]: r for r in rows}
    if len(keyed) != len(rows):
        raise ValueError(f"Duplicate identifiers in {path}")
    return keyed


def load_items(source=SOURCE):
    final = read_csv(source / "final_labels.csv")
    drafts = read_csv(source / "ai_draft_checked.csv")
    private_key = json.loads((source / "key.json").read_text(encoding="utf-8"))
    items = []
    for part, name in FILES.items():
        text = (source / name).read_text(encoding="utf-8")
        for block in re.findall(r"<div class='item'>(.*?)</div>", text, re.S):
            match = re.match(r"<h2>([GRPC]\d{3})(.*?)</h2>(.*)", block, re.S)
            if not match or not match[1].startswith(part):
                raise ValueError(f"Unrecognized item in {name}")
            old_id, heading, body = match.groups()
            accepted = final[old_id]
            if accepted["accepted label"] not in ALLOWED[part]:
                raise ValueError(f"Invalid accepted label for {old_id}")
            pair_required = part == "P" and "Relationship (pair) page:" in body
            pair = accepted["pair"] if part == "P" else "n-a"
            if pair not in (("yes", "no") if pair_required else ("n-a",)):
                raise ValueError(f"Inconsistent pair applicability for {old_id}")
            draft = drafts[old_id]
            reason = draft["claude note"] if accepted["label from"] == "claude" else draft["codex comment"]
            items.append({"source_item": old_id, "task": part, "heading": heading,
                          "body": body, "pair_required": pair_required,
                          "label": accepted["accepted label"], "pair": pair,
                          "reason": reason, "label_from": accepted["label from"],
                          "prior_evaluation_label": accepted["earlier AI label"],
                          "source_key": private_key[old_id]})
    identifiers = [r["source_item"] for r in items]
    if len(set(identifiers)) != len(identifiers) or set(identifiers) != set(final):
        raise ValueError("HTML and accepted answers do not cover exactly the same items")
    if set(identifiers) != set(drafts) or set(identifiers) != set(private_key):
        raise ValueError("Checked draft and key coverage differ from the packet")
    return items


def document(items, with_answers=False):
    title = "All evaluation questions and accepted answers" if with_answers else "Evaluation questions only"
    preface = ("<p><b>Moderator copy: contains existing answers. Do not give this file to readers.</b> "
               "These are AI labels accepted in the previous human review, not independently "
               "collected human labels or a new gold standard.</p>" if with_answers else
               "<p>Reader copy: prior labels and system identifiers are withheld. Some wording "
               "and page layouts may still reveal a system; complete system blinding is not guaranteed.</p>")
    out = ["<!doctype html><html lang='en'><head>", CSS,
           f"<title>{title}</title></head><body><h1>{title}</h1>", preface,
           "<p>This packet combines the paper's existing random review sample: all gold facts "
           "plus its per-system random recall, precision and citation subsets. Every item and "
           "displayed passage is retained; only presentation order is shuffled. Original Anne "
           "text, volumes 1–5. Disclosure, treated-text labels and labels added after that "
           "review are outside this sample. No new annotation is claimed.</p>", RULES]
    for r in items:
        part = r["task"]
        task, question = TASKS[part]
        pair_prompt = ("<p>Also answer pair: did both named people take part in the scene? yes / no.</p>"
                       if r["pair_required"] else "<p>Pair field: n-a.</p>")
        out.append(f"<div class='item' id='{r['item']}'><h2>{r['item']} — {task}{r['heading']}</h2>"
                   f"<p class='question'>{question}</p><p>Allowed labels: {' / '.join(ALLOWED[part])}</p>"
                   + r["body"] + pair_prompt)
        if with_answers:
            out.append("<div class='answer'><b>Previously accepted answer:</b> "
                       + html.escape(r["label"]) + "<br><b>Pair answer:</b> " + html.escape(r["pair"])
                       + "<br><b>AI label author:</b> " + html.escape(r["label_from"])
                       + "<br><b>Recorded AI rationale:</b> " + html.escape(r["reason"] or "No reason recorded.")
                       + "<br><b>Original review item:</b> " + r["source_item"] + "</div>")
        out.append("</div>")
    return "\n".join(out) + "\n</body></html>\n"


def build(output=HERE, seed=SEED, source=SOURCE):
    items = load_items(source)
    random.Random(seed).shuffle(items)
    for n, r in enumerate(items, 1):
        r["item"] = f"Q{n:04d}"
    output.mkdir(parents=True, exist_ok=True)
    questions = output / "questions_only.html"
    answers = output / "questions_and_answers.html"
    questions.write_text(document(items), encoding="utf-8")
    answers.write_text(document(items, True), encoding="utf-8")
    template = output / "reader_answers_blank.csv"
    with template.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in items:
            writer.writerow({"item": r["item"], "task": r["task"], "label": "",
                             "pair": "" if r["pair_required"] else "n-a", "comment": ""})
    # Machine-readable moderator key, never included in the reader archive.
    with (output / "accepted_answers.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({k: r.get(k, "") for k in FIELDS} for r in items)
    source_names = list(FILES.values()) + ["final_labels.csv", "ai_draft_checked.csv", "key.json"]
    manifest = {"schema_version": 1, "run_id": "agreement-packet-20261010",
                "presentation_seed": seed, "original_sampling_seed": 554,
                "sampling": "Existing paper sample: gold census and per-system random subsets; no redraw.",
                "counts": dict(sorted(Counter(r["task"] for r in items).items())),
                "total": len(items), "pair_items": sum(r["pair_required"] for r in items),
                "source_sha256": {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in source_names},
                "items": [{k: v for k, v in r.items() if k not in ("body", "heading", "reason")}
                          | {"evidence_html_sha256": hashlib.sha256(r["body"].encode()).hexdigest()}
                          for r in items]}
    (output / "manifest_private.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)
                                                  + "\n", encoding="utf-8")
    # Explicit allowlist prevents the answer key and prior rationales leaking to readers.
    with zipfile.ZipFile(output / "reader_packet.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for path in [questions, template]:
            info = zipfile.ZipInfo(path.name, date_time=(2026, 10, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
    print(json.dumps({k: manifest[k] for k in ("run_id", "counts", "total", "pair_items")}, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    build(args.output, args.seed)
