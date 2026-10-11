# PHASE_31.md — Publication track on decontaminated Project Gutenberg novels

Append-only. A superseded decision gets a new dated entry; never rewrite one.

## 2026-09-25 — Publication reinstated; corpus is decontaminated Gutenberg; budget $200

**Decision (maintainer):** the project is back on a publication pathway. This supersedes the
2026-09-23 "not a publication project" ruling (`PHASE_30.md`). `docs/MEASUREMENTS.md` stays the
ledger every figure lands in first; the paper cites it, not the other way round.

- **Corpus:** Project Gutenberg novels, decontaminated by **paraphrasing and entity remapping**
  before the pipeline sees them. The three commercial series stay as development corpora; no
  paper number comes from them.
- **Budget:** `budget.lifetime_cap_usd` $20 → **$200** (`config/models.yaml`). $12.79 already spent.
  `hard_stop_usd` ($10 per run) and the frontier interlock (`max_volumes: 2`) are unchanged. A
  single Gutenberg novel has no volume axis, so the cutoff unit (chapter or part) has to be decided
  before the interlock means anything here.

**Novelty, checked against the literature on 2026-09-25:**
- Renaming entities to defeat memorisation is **established method, not a contribution**
  (WHODUNIT 2502.07747; ∞Bench; name-cloze memorisation, Chang et al. 2023; OWL 2505.22945).
- Rephrased samples evade n-gram contamination checks (2311.04850). Paraphrase is therefore a
  treatment whose effect has to be measured, not assumed.
- *Living the Novel* (2512.07474) reports near-perfect timeline coherence on *Twenty Thousand
  Leagues Under the Sea*: one book, one cutoff, 100 questions, an LLM judge, and **no control for
  the base model having memorised the book**.
- TimeChara (2405.18027) shows LLMs leak future knowledge in point-in-time role-play. That is
  parametric-only: no retrieval gate, no decontamination.

**Candidate central claim (proposed, awaiting maintainer pick):** a filter-before-generate gate
closes retrieval leakage but not parametric leakage. On a memorised classic, the residual leak
is the generator's own memory. Decontamination is the treatment, and it is measured, not assumed.
The design is a 2×2: {original, decontaminated} × {gated pipeline, ungated/long-context}, with
Leak@t across all cutoffs, plus memorisation probes (name-cloze, title identification) run before
and after remapping, which show how much recognition survives. Supporting contributions: a
spoiler-scoped QA set built from the claim graph's `first_vol` labels, and an agent that browses
the cutoff-t site. Full reasoning is in the 2026-09-25 session reply.

## 2026-09-25 (later) — First novel and instruments: decisions taken and rejected

**First novel: *Twenty Thousand Leagues Under the Sea*** (Gutenberg #164). It is the book
*Living the Novel* evaluated on, so the comparison is on the same text. Its two Parts give a
natural v1/v2 split, which keeps the frontier interlock (`max_volumes: 2`) meaningful.

- **Cutoff unit = the book's own Parts**, via `source.volume_breaks` (regexes on chapter
  titles). Rejected: chapter-level cutoffs, because they would need the volume axis re-plumbed
  through every stage and the interlock. Rejected: splitting the EPUB file, which is fiddly and
  loses provenance to the Gutenberg original.
- **Decontamination runs on parsed records, not EPUBs.** A decontaminated series has the same
  `para_id`s as its source, so every measurement is paired paragraph by paragraph (CONTRACTS
  §1.6). `wiki ingest` refuses such a series, because parsing its EPUB would write the original text.
- **Three conditions, not two.** Adding a remap-only series (`paraphrase: false`) tests the
  prior practice directly and costs $0.
- **Remap before paraphrase, and again after.** The paraphraser never sees an original name,
  so it cannot anchor on the book, and a name it restores from memory is caught.
- **The entity map is hand-reviewed config**, seeded from `mine_candidates` (174 surfaces →
  22 entries). Real places and historical people are story facts and stay. Rejected: generating
  the map from the gazetteer, because a wrong automatic entry silently changes a fact.
- **Memorisation probe = Chang et al.'s name cloze plus title identification**, aligned by
  `para_id`. Its key number is *source recall*: the original name given for a decontaminated
  passage. The remap-only cloze is unscored because its masked passage equals the original's.
  Title answers are scored book-level and author-level, because wrong-book Verne answers are common.

## 2026-09-25 (later x2) — Maintainer: one E2 run first; novels; second model

- **E2 runs on one condition first**, the original `leagues`. Audit its output and fix what
  needs fixing; a second condition is considered only after that run is clean.
- **Novels are Claude's choice.** Anything that must be fetched by hand goes to the maintainer.
- **Models:** only Vertex and the OpenRouter free tier (daily request limit) are available. A
  free OpenRouter model may be a second model where the call count fits the limit (E3: about 12
  page calls per condition). Otherwise Gemini only. The memorisation probe (460 calls per
  condition) stays Gemini-only.

## 2026-09-26 — Headline corpus: a long series; decisions taken overnight (maintainer asleep)

**Maintainer, 2026-09-26:** two-volume novels give one cutoff and a context that fits in the
prompt. Keep them as the development and short-text control set, and make a 5+ volume public-domain
series the headline. A parallel session's plan 0010 was checked against the repo and corrected.

Taken under that instruction, each reversible:
- **Anne series (six public-domain books)** is the headline corpus. Tarzan is the fallback.
- **Interlock:** per-run `--set models.profiles.vertex_flash.max_volumes=6` on Anne commands;
  `models.yaml` keeps 2, so the light-novel corpora stay capped mechanically.
- **Principal cast (25 characters, 69% of mentions)** for extraction, infobox and synthesis, to
  stay under a self-imposed ~$15 unattended budget. The full 313-character build is the
  maintainer's call.
- **Wait out a provider quota; do not switch provider inside a series.** A Vertex 429 stopped
  Anne extraction after v04. A mixed-provider series would confound the per-model comparison.
- **Rejected:** carving out a `gutenberg` model profile (routing is global, not per series);
  splitting Leagues into 9 volumes tonight (it does not answer the long-context critique; plan
  0010 option B stays open as a cheap within-book curve).
