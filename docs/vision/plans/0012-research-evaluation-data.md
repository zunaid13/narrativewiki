# 0012 — Research evaluation: the data the paper needs, and what exists

**Status:** tracking (opened 2026-09-27). Decision: `docs/vision/PHASE_33.md`. Work starts when
plan 0011's roster fixes and five-volume runs (S7) are done. Living document: update the
Status column as data lands; every number goes to `docs/MEASUREMENTS.md` first.

Notation: t = cutoff volume; W_t = rendered site at t; G_t = gold facts whose earliest support
is ≤ t; C_t = distinct atomic assertions on W_t (structured fields and relation labels included).

## Granularity rule (maintainer, 2026-09-27)

Every measurement is taken **per volume cutoff t = 1..N**, per series: contamination/memorisation
question probes, recall, precision, leak/disclosure, citation support, stage retention, verifier
error rates, baselines and ablations. Pooled or final-volume figures appear only beside the
per-t rows. Consequence for the data: gold, precision samples and probe items need enough items
*at each t* (target ≥20 per series per t), not just in total. The parametric probe asks, at each
t, about facts first revealed at t and after t (the second half is the leak test).

## Data inventory

| # | Data | Exists now | Gap | Status |
|---|---|---|---|---|
| D1 | **Frozen system**: git tag + `config/*.yaml` hashes + LLM cache for the test run | run manifests (`_runs/*/manifest.json`) carry sha and config hashes | a tag and a written freeze date; nothing tuned after it | todo |
| D2 | **Gold inventory per cutoff** (claim, evidence para_id, earliest-support volume) | `docs/eval/parametric/{spice-and-wolf,overlord,bookworm,middlemarch}.yaml`: 46/38/29/43 facts; v1–2 fandom gold `docs/eval/gold/` | aim ≥300 facts; per-cutoff increments ≥20 per series; fields for polarity, speaker/attribution, modality, predicate family; include delayed identity reveals, false beliefs, hypotheticals, implicit relations | todo |
| D3 | **Independent annotation**: second annotator on a stratified subset, blind to condition; agreement (κ) | none | a human annotator, sheet from `scripts/eval/recall_review.py` | todo (needs maintainer; per t) |
| D4 | **Importance weights**, judged from the prefix only | none | 1–3 weight per gold fact, set before any system output is read | todo |
| D5 | **Construction dependence**: prefix-built vs full-built gazetteer, graph and site at the same t | `probe/channels/index.py` (L_build, index only) | full-stage diff (entity merges, aliases, evidence refs, sections); each difference labelled harmless / altered selection / premature identity / actual revelation; **per-alias link volume** (`aliases_at` gates by surface first_vol today) | todo |
| D6 | **Stage-level retention per gold fact**: evidence discovered → extracted → admitted by verify → graph interval → rendered | `audit eval` verdict classes (plan 0011 S4, v1–2 only) | a per-fact route log over all t; graph recall and page recall reported separately | todo |
| D7 | **Artifact exposure**: titles, slugs/URLs, aliases, search index, backlinks, nav, codex, source views at each t | Anne front-matter fix; links audit; `probe/channels/disclosure.py` | crawl of `dist/<s>/wiki/v0t/` for F>t strings; check whether slugs are chosen from full-scope names | todo |
| D8 | **Assertion precision per t** over C_t (sampled, seeded) | `docs/eval/precision/*_v2.jsonl` (4 × 40, t=2 only) | t=1..5 per series after S7; state who read each verdict; human second reader on a subset | todo |
| D9 | **Claim- and page-level disclosure rate per t**, with an exact zero-event bound (`1 - 0.05^(1/n)`; `3/n` only as a rough check; plan 0013 §3.2) | `pipeline_leak_{anne,leagues}_v*.json` | per-series t=1..4 after S7 (driver writes `leak-t*`) | S7 running |
| D10 | **Citation support**: coverage (assertion has sufficient cited evidence) and validity (anchor resolves, evidence ≤ t) | `audit eval` citation entailment (MiniCheck) | per-assertion coverage over C_t; human check of the MiniCheck screen | todo |
| D11 | **Verifier challenge set**: false admission / false rejection by type (attribute, explicit/implicit relation, negation, hypothetical, deception, quoted belief) | Leagues 40-line A/B (MEASUREMENTS §48) | ≈100 labelled candidates, stratified by type (STORYSUMM/FABLES categories) | todo |
| D12 | **Parametric controls, per cutoff t**: original / remapped / remapped+paraphrased / closed-book, plus counterfactual variants; recognise-vs-comply probes (CHARM) | memorisation probe and E3 closed-book (Phase 31, §43/§47) | counterfactual variants; recognise-vs-comply pairs | partial |
| D13 | **Baselines** B1–B6 on the same prefixes, generator, page schema and budgets | none | **Renumbered in plan 0013 §4.1, which is authoritative (mapping there).** Original list: B1 prompt-only full text; B2 prefix long-context; B3 prefix BM25+dense RAG; B4 full-corpus graph + retrieval filter; B5 ours; B6 ours + one recovery intervention. Cost estimate before running | todo |
| D14 | **Ablations**: − scene pass, − verifier v5, − structured rendering, graph-off (same evidence and generator) | partial (gleaning A/B, verify v4/v5 A/B) | run on the frozen system, dev works only | todo |
| D15 | **Efficiency**: tokens, $, wall time per stage and per incremental volume | `calls.jsonl`, manifests, `wiki budget` | one table from the frozen run | todo ($0) |
| D16 | **Held-out works**: ≥2 works never used to shape a rule | Oz (14 books) ingested 2026-09-27, 621k words (MEASUREMENTS) | a second held-out work; gold from oz.fandom.com per book | in progress |
| D17 | **Literature**: missing papers verified and indexed; four corrections applied | `docs/papers/PAPERS.md`, `REFERENCES.md` | Beyond Precision (2604.03141), NarrativeFactScore (EMNLP 2025), BOOKCOREF (ACL 2025), Claimify (2502.10855), EVAR (2608.29835), NS-ST-GraphRAG (2609.05139), CHARM (2609.01352), SearchWiki (2608.29953), Trust-Align (2409.11242), HippoRAG 2 (2502.14802), FABLES (2404.01261), STORYSUMM (EMNLP 2024), WIKIGENBENCH (2402.18264); optional VeriFact, Graph-Guided Evidence Navigation (2609.22939). all 13 in `REFERENCES.md` with PDFs (2026-09-28) | **done** 2026-09-28: the 406 was urllib-specific (curl, same URL and User-Agent, got 200); the fetch script now falls back to curl on 406. 80/80 ids resolve; PAPERS ↔ disk ↔ PAPERS.md consistent. Reading depth is still *not yet read* for the 11 new PDFs |

## Metrics (defined once; computed from the data above)

End-to-end fact recall at t (D2), importance-weighted recall (D4), grounded precision (D8),
claim and page disclosure rate (D9), citation coverage and validity (D10), stage retention (D6),
relation/event tuple F1 by predicate family (D2 fields), temporal early/late error (D2, D9),
artifact exposure (D7), verifier false admission/rejection (D11), efficiency (D15). Report
per work and per cutoff, then macro; paired, work-level resampling; operating point chosen on
dev works and frozen before the test works are run.

## Order (cheap before billed)

1. $0: D17, D15, D7 crawl, D5 alias link volume, D6 route log, D2/D4 gold extension on dev works.
2. Maintainer: D3 and the human half of D8 and D11.
3. Billed, after D1 freeze: D13 baselines and D14 ablations on dev works, then everything on D16.

## Log

- 2026-09-27: opened from the positioning review; inventory checked against the repo.
- 2026-09-27: per-volume-cutoff granularity rule added (maintainer).
- 2026-09-27: D17 blocked (arXiv API 406). D8/D9 now produced per t by `scripts/run_series.py` (precision-t1..t5, leak-t1..t5); the sampler writes a dated file instead of overwriting read verdicts.
- 2026-09-27: corpus rule — published results only on public-domain works with a good reference wiki. Anne (6) main, Oz (14) held out, Middlemarch v1–5 stress; Overlord/S&W development only (PHASE_33).
