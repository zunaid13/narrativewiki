"""fill_v2.py: results.tex keys that scripts/papers/fill_results.py cannot derive for the version-2 build. $0.

Run, from the repository root, AFTER fill_results.py and BEFORE summary_stats.py:
  .venv/Scripts/python.exe docs/paper/_build/fill_v2.py

fill_results.py takes N from `docs/eval/inventory/anne_v<t>.jsonl` (the first build) and knows nothing of the
keys below; every value here has its row in docs/MEASUREMENTS.md (2026-10-05), named in NOTE. Existing keys are
overwritten in place, new keys are appended before the summary-statistics block. Inventory sizes are counted
here; everything else is a recorded value.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "docs" / "paper" / "results.tex"
BS = chr(92)
NOTE = "MEASUREMENTS 2026-10-05 and 2026-10-06 version-2 rows (recall keys: 2026-10-07, CHANGES C43; five keys recomputed 2026-10-08, C45)"
NOTE52 = "MEASUREMENTS 2026-10-09 citation sufficiency for the cells that had none (agent reader, CHANGES C52)"


def inv(series):
    return [sum(1 for l in (ROOT / "docs" / "eval" / "inventory" / f"{series}_v{t}.jsonl").open(encoding="utf-8") if l.strip())
            for t in range(1, 6)]


V = {}  # key -> (value, description or None for an existing key)
for system, series in (("B5", "anne@v2"), ("B4", "anne@b4-v2")):
    ns = inv(series)
    for t, n in enumerate(ns, 1):
        V[f"N-anne-t{t}-{system}"] = (f"{n:,}", None)
    V[f"N-anne-avg-{system}"] = (f"{round(sum(ns) / 5):,}", None)

V.update({
    # output amount and citations
    "ND-anne-avg-B5": ("6,970", None), "ND-anne-avg-B4": ("1,701", None), "CITE-anne-B5": ("0.930", None),
    # by page kind (scene rule on relationship pages)
    "M3K-anne-B5-cast": ("0.886 (31/35)", None), "M3K-anne-B5-cast-share": ("21" + BS + "%", None),
    "M3K-anne-B5-rel": ("0.706 (72/102)", None), "M3K-anne-B5-rel-atom": ("0.971 (99/102)", None),
    "M3K-anne-B5-rel-share": ("46" + BS + "%", None), "M8K-anne-B5-cast": ("0.400 (14/35)", None),
    "M8C-anne-B5": ("0.534 (102/191)", None),
    # disclosure
    "M4-anne-total-B5": ("1 of 220", None), "M4-anne-total-B4": ("0 of 220", None),
    "M4-cand-anne-B5": ("5,702", None), "M4-cand-anne-all": ("12,689", None),
    "M5-anne-B5": ("0 of 159", None), "SCREEN-anne-B5": ("1", None), "SCREEN-anne-B4": ("1", None),
    "VERIFY-unsupported": ("21.2" + BS + "% of 2,535", None),
    # cost of one clean build at list price
    "T5-gazetteer-calls": ("2,771", None), "T5-gazetteer-tokens": ("1.53M", None), "T5-gazetteer-usd": ("1.57", None),
    "T5-scenes-calls": ("452", None), "T5-scenes-tokens": ("3.71M", None), "T5-scenes-usd": ("5.69", None),
    "T5-extract-calls": ("2,932", None), "T5-extract-tokens": ("14.47M", None), "T5-extract-usd": ("12.15", None),
    "T5-infobox-calls": ("980", None), "T5-infobox-tokens": ("7.21M", None), "T5-infobox-usd": ("5.73", None),
    "T5-graph-calls": ("64", None), "T5-graph-tokens": ("0.02M", None), "T5-graph-usd": ("0.02", None),
    "T5-verify-calls": ("2,816", None), "T5-verify-tokens": ("6.25M", None), "T5-verify-usd": ("4.81", None),
    "T5-synth-calls": ("953", None), "T5-synth-tokens": ("1.04M", None), "T5-synth-usd": ("1.23", None),
    "T5-site-calls": ("386", None), "T5-site-tokens": ("0.75M", None), "T5-site-usd": ("0.60", None),
    "T5-total-calls": ("11,354", None), "T5-total-usd": ("31.80", None), "T5-warm-usd": ("0.00", None),
    "COST-anne-B5": ("31.80", None), "COST-anne-B5-input": ("33.1M", None),
    # prefix-build comparison: made with the first build; precision under the standing pair rule
    "A1-dM3": ("$+0.038$ (58 vs 55 of 78)", None), "A1-t2-M3-prefix": ("0.769 (30/39)", None),
    "A1-t3-M3-prefix": ("0.718 (28/39)", None),
    "A1-t2-M1-full": ("0.848 (39/46)", "recall of the first full build at t=2 (prefix-build comparison)"),
    "A1-t3-M1-full": ("0.864 (57/66)", "recall of the first full build at t=3 (prefix-build comparison)"),
    "A1-t2-M3-full": ("0.718 (28/39)", "precision of the first full build at t=2, standing pair rule"),
    "A1-t3-M3-full": ("0.692 (27/39)", "precision of the first full build at t=3, standing pair rule"),
    "A1-cost-full": ("31.64", "cost of the first full build, all cutoffs, USD at list price"),
    # pages
    "PAGES-anne-B5-t2": ("117", "character pages of the reported build at t=2"),
    "PAGES-anne-B5-rel-t2": ("71", "pair pages of the reported build at t=2"),
    # later-anchored entities in the reported build
    "LATE-anne-t2": ("6 of 117", "character pages at t=2 whose entity has 80 per cent of its mentions after t=2"),
    "LATE-anne-t3": ("3 of 158", "character pages at t=3 whose entity has 80 per cent of its mentions after t=3"),
    # identity dependence: the reported build's index against indexes built per prefix (MEASUREMENTS 2026-10-08)
    "ID-anne-t1": ("0.390 (23/59)", "identity dependence at t=1: character pages whose set of names seen by t no prefix-built character has"),
    "ID-anne-strict-t1": ("0.220 (13/59)", "the same at t=1, counting only regrouped or absent entities"),
    "ID-anne-mentions-t1": ("0.943", "character mentions in volumes 1..1 under the prefix index, as a share of the full build's"),
    "ID-anne-t2": ("0.256 (30/117)", "identity dependence at t=2: character pages whose set of names seen by t no prefix-built character has"),
    "ID-anne-strict-t2": ("0.145 (17/117)", "the same at t=2, counting only regrouped or absent entities"),
    "ID-anne-mentions-t2": ("0.967", "character mentions in volumes 1..2 under the prefix index, as a share of the full build's"),
    "ID-anne-t3": ("0.133 (21/158)", "identity dependence at t=3: character pages whose set of names seen by t no prefix-built character has"),
    "ID-anne-strict-t3": ("0.076 (12/158)", "the same at t=3, counting only regrouped or absent entities"),
    "ID-anne-mentions-t3": ("0.982", "character mentions in volumes 1..3 under the prefix index, as a share of the full build's"),
    "ID-anne-t4": ("0.089 (17/191)", "identity dependence at t=4: character pages whose set of names seen by t no prefix-built character has"),
    "ID-anne-strict-t4": ("0.052 (10/191)", "the same at t=4, counting only regrouped or absent entities"),
    "ID-anne-mentions-t4": ("0.994", "character mentions in volumes 1..4 under the prefix index, as a share of the full build's"),
    "ID-anne-mean": ("0.217", "identity dependence, mean over t=1..4"),
    "ID-anne-alias-t1": ("10", "character pages at t=1 that differ from the prefix index by a name linked in one build only"),
    "ID-anne-absent-t1": ("9", "character pages at t=1 with no prefix-built counterpart"),
    # the reported system built on prefix-only entity indexes, anne@p<t>-v2 (MEASUREMENTS 2026-10-08)
    "PX-anne-t1-pages": ("48", "character pages of the prefix-discovered build at t=1"),
    "PX-anne-t1-pages-full": ("59", "character pages of the reported build at t=1"),
    "PX-anne-t1-M1": ("0.826 (19/23)", "recall of the prefix-discovered build at t=1"),
    "PX-anne-t1-M3": ("0.950 (38/40)", "page-context precision of the prefix-discovered build at t=1, scene rule"),
    "PX-anne-t1-M4": ("0/88", "later facts stated or implied by the prefix-discovered build at t=1"),
    "PX-anne-t1-N": ("3,977", "assessed atomic assertions of the prefix-discovered build at t=1"),
    "PX-anne-t1-TOK": ("5.68 / 0.31", "one clean prefix-discovered build for t=1: input / output tokens, millions"),
    "PX-anne-t2-pages": ("108", "character pages of the prefix-discovered build at t=2"),
    "PX-anne-t2-pages-full": ("117", "character pages of the reported build at t=2"),
    "PX-anne-t2-M1": ("0.761 (35/46)", "recall of the prefix-discovered build at t=2"),
    "PX-anne-t2-M3": ("0.750 (30/40)", "page-context precision of the prefix-discovered build at t=2, scene rule"),
    "PX-anne-t2-M4": ("0/65", "later facts stated or implied by the prefix-discovered build at t=2"),
    "PX-anne-t2-N": ("8,732", "assessed atomic assertions of the prefix-discovered build at t=2"),
    "PX-anne-t2-TOK": ("11.95 / 0.65", "one clean prefix-discovered build for t=2: input / output tokens, millions"),
    "PX-anne-t3-pages": ("155", "character pages of the prefix-discovered build at t=3"),
    "PX-anne-t3-pages-full": ("158", "character pages of the reported build at t=3"),
    "PX-anne-t3-M1": ("0.818 (54/66)", "recall of the prefix-discovered build at t=3"),
    "PX-anne-t3-M3": ("0.875 (35/40)", "page-context precision of the prefix-discovered build at t=3, scene rule"),
    "PX-anne-t3-M4": ("1/45", "later facts stated or implied by the prefix-discovered build at t=3"),
    "PX-anne-t3-N": ("13,432", "assessed atomic assertions of the prefix-discovered build at t=3"),
    "PX-anne-t3-TOK": ("18.04 / 0.99", "one clean prefix-discovered build for t=3: input / output tokens, millions"),
    "PX-anne-t4-pages": ("185", "character pages of the prefix-discovered build at t=4"),
    "PX-anne-t4-pages-full": ("191", "character pages of the reported build at t=4"),
    "PX-anne-t4-M1": ("0.809 (72/89)", "recall of the prefix-discovered build at t=4"),
    "PX-anne-t4-M3": ("0.795 (31/39)", "page-context precision of the prefix-discovered build at t=4, scene rule"),
    "PX-anne-t4-M4": ("0/22", "later facts stated or implied by the prefix-discovered build at t=4"),
    "PX-anne-t4-N": ("17,723", "assessed atomic assertions of the prefix-discovered build at t=4"),
    "PX-anne-t4-TOK": ("24.04 / 1.37", "one clean prefix-discovered build for t=4: input / output tokens, millions"),
    "PX-anne-M1-pooled": ("180 of 224", "gold-fact reads conveyed by the prefix-discovered builds, t=1..4 pooled"),
    "PX-anne-M1-pooled-full": ("180 of 224", "gold-fact reads conveyed by the reported build, t=1..4 pooled"),
    "PX-anne-M3-pooled": ("134 of 159", "sampled assertions supported on their page, prefix-discovered builds, t=1..4 pooled"),
    "PX-anne-M3-pooled-full": ("130 of 159", "sampled assertions supported on their page, reported build, t=1..4 pooled"),
    # citation sufficiency of the prefix-discovered builds (MEASUREMENTS 2026-10-09, CHANGES C52)
    "PX-anne-t1-M8": ("0.650 (26/40)", "citation sufficiency of the prefix-discovered build at t=1", NOTE52),
    "PX-anne-t2-M8": ("0.425 (17/40)", "citation sufficiency of the prefix-discovered build at t=2", NOTE52),
    "PX-anne-t3-M8": ("0.600 (24/40)", "citation sufficiency of the prefix-discovered build at t=3", NOTE52),
    "PX-anne-t4-M8": ("0.615 (24/39)", "citation sufficiency of the prefix-discovered build at t=4", NOTE52),
    "PX-anne-M8-pooled": ("91 of 159", "sampled assertions whose cited paragraphs suffice, prefix-discovered builds, t=1..4 pooled", NOTE52),
    "M8K-anne-char-B5": ("29 of 64", "sampled assertions on character pages whose cited paragraphs suffice, reported build, t=1..5", NOTE52),
    "M8K-anne-char-B4": ("183 of 200", "sampled assertions (all on character pages) whose cited paragraphs suffice, graph baseline, t=1..5", NOTE52),
    "PX-anne-M8-pooled-full": ("82 of 159", "sampled assertions whose cited paragraphs suffice, reported build, t=1..4 pooled", NOTE52),
    "ID-anne-t1-rate": ("0.390", "identity dependence at t=1, rate only (23/59)"),
    "ID-anne-t4-rate": ("0.089", "identity dependence at t=4, rate only (17/191)"),
    # why a prefix index lacks candidates of the full build (MEASUREMENTS 2026-10-08, OPEN_GAPS G19)
    "G19-anne-lost": ("109, 111, 78 and 44", "full-build candidates first seen by t that are not mined from volumes 1..t, t=1..4"),
    "G19-anne-few": ("91, 87, 60 and 32", "of those, with fewer than three mentions in the prefix, t=1..4"),
    "G19-anne-ratio": ("18, 24, 18 and 12", "of those, dropped by the capitalisation-ratio rule, t=1..4"),
    "G19-anne-off": ("352", "candidates the five-volume build gains with the capitalisation-ratio rule switched off"),
    # sizes in tokens, input / output in millions (MEASUREMENTS 2026-10-08); the paper prints no dollar figure
    "T5-gazetteer-in": ("1.39", "gazetteer stage input tokens (millions), one clean build"),
    "T5-gazetteer-out": ("0.14", "gazetteer stage output tokens (millions), one clean build"),
    "T5-scenes-in": ("2.74", "scenes stage input tokens (millions), one clean build"),
    "T5-scenes-out": ("0.97", "scenes stage output tokens (millions), one clean build"),
    "T5-extract-in": ("14.04", "extract stage input tokens (millions), one clean build"),
    "T5-extract-out": ("0.43", "extract stage output tokens (millions), one clean build"),
    "T5-infobox-in": ("7.10", "infobox stage input tokens (millions), one clean build"),
    "T5-infobox-out": ("0.11", "infobox stage output tokens (millions), one clean build"),
    "T5-graph-in": ("0.02", "graph stage input tokens (millions), one clean build"),
    "T5-graph-out": ("0.00", "graph stage output tokens (millions), one clean build"),
    "T5-verify-in": ("6.21", "verify stage input tokens (millions), one clean build"),
    "T5-verify-out": ("0.04", "verify stage output tokens (millions), one clean build"),
    "T5-synth-in": ("0.89", "synth stage input tokens (millions), one clean build"),
    "T5-synth-out": ("0.15", "synth stage output tokens (millions), one clean build"),
    "T5-site-in": ("0.73", "site stage input tokens (millions), one clean build"),
    "T5-site-out": ("0.02", "site stage output tokens (millions), one clean build"),
    "T5-total-in": ("33.13", "input tokens (millions) of one clean build"),
    "T5-total-out": ("1.86", "output tokens (millions) of one clean build"),
    "TOK-anne-B5": ("33.13 / 1.86", "one clean NarrativeWiki build, all five cutoffs: input / output tokens, millions"),
    "TOK-anne-B1": ("69.23 / 0.37", "prefix long-context, t=1..5: input / output tokens, millions"),
    "TOK-anne-B2": ("3.42 / 0.37", "prefix retrieval, t=1..5: input / output tokens, millions"),
    "TOK-anne-B3": ("5.08 / 1.01", "LightRAG index construction and page calls, t=1..5: input / output tokens, millions"),
    "TOK-anne-X1": ("0.06 / 0.15", "closed book, t=1..5: input / output tokens, millions"),
    "TOK-anne-X2": ("98.67 / 0.37", "instructed full text, t=1..5: input / output tokens, millions"),
    "TOK-anne-B3-index": ("2.36M input and 0.72M output tokens", "LightRAG index construction, five incremental indexes"),
    "TOK-anne-B3-pages": ("2.72M and 0.29M", "LightRAG page calls, t=1..5, input and output tokens"),
    "TOK-anne-first": ("33.14 / 1.81", "one clean first build: input / output tokens, millions"),
    "TOK-anne-first-text": ("33.14M input and 1.81M output tokens", "one clean first build"),
    "TOK-A1-t2-prefix": ("12.03 / 0.68", "one clean first-version prefix build for t=2: input / output tokens, millions"),
    "TOK-A1-t3-prefix": ("17.94 / 1.01", "one clean first-version prefix build for t=3: input / output tokens, millions"),
    "TOK-ID-anne": ("2.61M input and 0.26M output tokens", "the four prefix entity indexes, t=1..4, every call"),
    "TOK-ID-anne-new": ("0.37M and 0.04M", "the four prefix entity indexes: tokens of calls not already made by the full build"),
    # the two builds of the system under one rule and one reader
    "REV-M1-first": ("0.855", "recall of the first build, mean over cutoffs"),
    "REV-M3-first": ("0.751", "page-context precision of the first build, standing pair rule, mean over cutoffs"),
    "REV-M3-first-lenient": ("0.822", "precision of the first build as first labelled, lenient chapter rule"),
    "REV-M3-firstpass": ("0.748", "precision of the reported build by the first annotation pass, before the pair rule was written out"),
    "REV-M3-pair2": ("0.753", "precision of the reported build with the second annotator's own pair verdicts and every other label as reported, mean over cutoffs"),
    "REV-M3L-first": ("0.604", "precision of the first build, line-level pair rule"),
    "REV-M3L": ("0.628", "precision of the reported build, line-level pair rule"),
    "REV-M3A-first": ("0.949", "share of sampled statements true as statements, first build"),
    "REV-M3A": ("0.934", "share of sampled statements true as statements, reported build"),
    "REV-M8-first": ("0.112", "citation sufficiency of the first build, mean over cutoffs"),
    "REV-CITE-first": ("0.198", "share of assertions with a paragraph citation, first build"),
    "REV-N-first": ("20,823", "assertions per cutoff, first build"),
    "REV-ND-first": ("8,808", "distinct assertions per cutoff, first build"),
    "REV-pair-first": ("76 of 116", "sampled pair-page lines whose pair shares an episode, first build"),
    "REV-pair": ("75 of 102", "sampled pair-page lines whose pair shares an episode, reported build"),
    "REV-part-first": ("9.0", "participants listed per scene record, first build, mean"),
    "REV-part": ("5.9", "participants listed per scene record, reported build, mean"),
    "REV-pairs-first": ("10,216", "participant pairs implied by the scene records, first build"),
    "REV-pairs": ("4,604", "participant pairs implied by the scene records, reported build"),
    "REV-cost-first": ("31.64", "one clean first build, USD at list price"),
    "ANN-pair-agree": ("90 of 99", "pair verdicts on which the two LLM annotators agree, reported build"),
    "ANN-pair-kappa": ("0.79", "Cohen kappa of the two LLM annotators on the pair verdict, reported build"),
    "M1-anne-avg-B5-minus-B4": ("0.041", "paired recall difference, main system minus the graph baseline, mean over cutoffs"),
    "REV-M4-first": ("0 of 220", "stated or implied disclosures of the first build, t=1..4"),
    "REV-SCREEN-first": ("4", "lexical screen hits on the first build, t=1..4"),
    "M1-anne-miss-t5": ("22", "gold facts the reported build does not convey at t=5"),
    "M1-anne-miss-t5-prefix": ("18", "of those, conveyed by long-context prompting or prefix retrieval"),
})

sys.path.insert(0, str(ROOT / "scripts" / "eval"))
from disclosure_units import paper_values, report

# Derive system membership and unique subject-fact units from stored labels, so a
# table refresh cannot restore the former four-system denominator.
disclosure_values = paper_values(report())
for key, (value, description) in disclosure_values.items():
    V[key] = (value, description,
              "MEASUREMENTS 2026-10-10 reviewer concerns: disclosure units; reviewer-concerns-20261010")

lines = RES.read_text(encoding="utf-8").split("\n")
head = BS + "declareres{"
seen, out = set(), []
for ln in lines:
    if ln.startswith(head):
        key = ln[len(head):].split("}", 1)[0]
        if key in V:
            m = re.match(r"^(.declareres[{][^}]*[}][{][^}]*[}])[{]", ln)
            assert m, ln
            prefix = f"{head}{key}}}{{{V[key][1]}}}" if key in disclosure_values else m.group(1)
            ln = f"{prefix}{{{V[key][0]}}}% {V[key][2] if len(V[key]) > 2 else NOTE}"
            seen.add(key)
    out.append(ln)
new = [k for k in V if k not in seen]
missing_desc = [k for k in new if V[k][1] is None]
assert not missing_desc, f"keys not declared in results.tex and given no description: {missing_desc}"
block = [f"{head}{k}}}{{{V[k][1]}}}{{{V[k][0]}}}% {V[k][2] if len(V[k]) > 2 else NOTE}" for k in new]
marker = next(i for i, ln in enumerate(out) if ln.startswith("% ==== BEGIN summary_stats.py"))
out[marker:marker] = ["% ==== Version-2 keys added 2026-10-05 (docs/paper/_build/fill_v2.py) ===="] + block + [""]
RES.write_text("\n".join(out), encoding="utf-8")
print(f"{len(seen)} keys overwritten, {len(new)} keys added")
