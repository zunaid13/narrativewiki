# Phase 33 — Research evaluation (opens when Phase 32's roster and five-volume issues are closed)

## 2026-09-27 — External positioning review adopted; the paper is a measured trade-off, not a "first"

Source: `NarrativeWiki_Research_Positioning_2026-09-27.md` (external review of README, VISION,
the two literature reviews and the 63-paper mapping; it saw no code, gold or ledger). Maintainer:
agree, keep track of the data needed, research starts once Phase 32's issues are fixed.
Executable tracker: `docs/vision/plans/0012-research-evaluation-data.md`.

**Adopted.**
- Research question: *how much source-supported information survives to the page at a reader's
  cutoff without unsupported assertions or disclosure of later text?* Coverage, support and
  boundary adherence are reported jointly, never as one product score.
- Novelty is narrowed. Story-time gating (Living the Novel), verified character sheets (CHIRON),
  temporal literary graphs (NS-ST-GraphRAG) and corpus-to-wiki compilation (SearchWiki) are prior
  art. The claim is the complete cutoff-scoped reference artifact, stage-level loss accounting,
  and construction-time/artifact leakage measurement. Never "first", "hallucination-free",
  "provably spoiler-free" or "decontaminated benchmark".
- Renaming/paraphrase are *contamination-reduction treatments*; a correct future answer is a
  *boundary violation*, with the evidence for a parametric cause stated separately.
- Zero observed leaks is reported with its rough 95% upper bound 3/n (clustered where claims
  share a page), never as "no leaks".
- Empty output: precision undefined, claim count 0, recall 0 where gold exists.
- Baseline matrix (prompt-only full text, prefix long-context, prefix BM25+dense RAG, full-corpus
  graph + retrieval filter, ours, ours + one recovery intervention), same generator and budgets.
- Development works and held-out works are separated before any test number is read.
- Literature: add the review's missing papers once `scripts/papers/fetch_reference_pdfs.py` has
  verified their metadata; apply its four corrections (Living the Novel acronyms DPA/CRE; TimeSPEC
  belongs to *All Leaks Count*, TCFT to *Teaching LLMs When Not to Know*; CHIRON is a character
  sheet with generation/validation; reading order is not chronology).

**Where the review's premise does not match this repo (checked 2026-09-27).**
- Reveal time vs world time is already separated: `first_vol` is disclosure position (CLAUDE.md
  §1), and intervals open at the volume that *tells* the reader. Nothing to build; say so in the
  paper.
- Its central example is live here, not hypothetical. The gazetteer is built at full scope
  (`--volumes 1-5`), and `gazetteer.aliases_at` gates an alias by the volume where the *surface*
  first appears, not the volume where the text *links* it to the page. Two names present from v1
  whose identity is revealed in v3 would both show on a v1 page. Needs a per-alias link volume and
  the prefix-built vs full-built comparison (tracker D5).
- Today's alias fix (Phase 32) closed one parametric channel inside construction: the adjudicator
  was merging from series knowledge ("in the second volume of the Overlord series"). It now
  judges from the quoted passages only.

**Gaps the review could not see.**
- The multi-cutoff gold (`docs/eval/parametric/*.yaml`) has 156 facts over 4 series: 46 / 38 /
  29 / 43. Per-cutoff increments are tiny (Bookworm v3 and v5 add 2 facts each), well under the
  review's 300–600. It was written by the same agent that tuned the pipeline. An independent
  annotator subset with agreement is required before it is test data.
- The precision verdict files (`docs/eval/precision/*_v2.jsonl`, 4 × 40) record "hand-read"
  verdicts. Who read them must be stated; a human second reader is required on a stratified subset.
- Every series used so far has shaped a general rule, so none of them is held out.

**Rejected / deferred.** No fine-tuning, no navigation-agent training (SearchWiki), no
multilingual work. BOOKCOREF-style coreference is added only if stage diagnostics show evidence
discovery is the dominant loss. The narrator-"I" problem in Bookworm/Leagues is the candidate
case. Reader task-utility study is optional, after the core table.

## 2026-09-27 (later) — Every evaluation is per volume cutoff

Maintainer: contamination question probes, recall, precision, spoiler leakage and every other
metric are measured and reported per volume cutoff t, because that granularity is where the
observations and claims come from. Pooled numbers only accompany the per-t rows. Plan 0012 now
states the rule and sizes its data per t (≥20 items per series per t as the working target).

## 2026-09-27 (later x2) — Corpus rule for published results; Anne main, Oz held out

Maintainer: the main goal is Overlord, Spice and Wolf and the Gutenberg novels (Bookworm last).
Anything the paper reports on must be openly published (public domain), and a series needs a
good fandom wiki or reference site (the gold source). Pick for many characters and many cutoffs.

- **Anne of Green Gables, 6 books** is the main published corpus: public domain, a dedicated
  Fandom wiki with per-book appearance pages (per-cutoff gold), a large cast, 6 cutoffs. Re-run
  end to end on the current code with the per-run `max_volumes=6` override (AGENTS.md §3).
- **Oz, 14 books** (Baum) is the candidate held-out work: public domain, oz.fandom.com plus
  Wikipedia's character list, up to 14 cutoffs. Ingested ($0); no LLM stage before the freeze.
- **Middlemarch** stays the Books I–V stress corpus: public domain but only study-guide
  references (SparkNotes, LitCharts), so it is not extended past v5.
- **Overlord and Spice and Wolf** are development series. They are not public domain, so their
  numbers do not appear as paper results. Leagues, Pride and Little Women have 2–3 cutoffs and
  small casts; they stay as they are.

## 2026-09-28 — Model choice: Gemini 3.6 Flash vs 3.1 Flash-Lite, one model for every final reading; ceiling $275

Maintainer: "keep the final readings consistent for same model. if 3.6 is better then use it. if
budget increase is needed, we can issue it but for now try to keep it under 275$."

- **Why the question arose.** `gemini-3.1-flash-lite` on the free-trial billing account returned
  hours of 429 (MEASUREMENTS 2026-09-28); the maintainer proposed 3.8/3.6 Flash for higher
  limits. Stored-prompt bake-off: both valid JSON, fewer claim facts (3.8 19, 3.6 26 vs 50),
  ≈ 2.8× the cost; 3.6 is the faster of the two, so 3.6 is the candidate.
- **Decision rule.** End to end on Anne v1 (the smallest slice that shows the effect, CLAUDE.md
  §2): two series built identically from the same corpus, `anne-m31` (3.1 Flash-Lite) and
  `anne-m36` (3.6 Flash), gazetteer scoped to v1, then scenes → extract → infobox/backstory →
  graph → verify → synthesis → site. Compare hand-read assertion precision (40 per arm,
  `assertion_precision.py`) and control recall against `docs/eval/parametric/anne.yaml`
  (`pipeline_page_leak.py`), plus facts per page and cost. 3.6 wins if it is not worse on
  precision and recall; the loser's numbers are development data only.
- **One model.** Whatever wins runs every paper-facing build (Anne, Oz, Middlemarch, Leagues) and
  every baseline; nothing compared in the paper mixes models. The content-block fallback to a
  second model is an open question for the maintainer (one Overlord call so far).
- **Budget.** Real-bill ceiling $275 (was $200): `lifetime_cap_usd` 255 with the same ≈ 8%
  cushion. Flex is priced at its real 50% rate in `config/models.yaml` so the cap tracks the bill.
  Paper spend covers public-domain corpora only; Overlord stopped after `infobox` (dev only).
  Forecast on 3.6 Flex ≈ $145–180, ≈ $100–135 without the diagnostic X2 baseline.

## 2026-09-28 (later) — Maintainer decisions: refusals stay on one model; ceiling $275 (maybe $400 later); cast = gold characters

Maintainer, answering the open questions of the entry above:
1. **"Keep same model."** A content-filter refusal is no longer answered by the next routing rung.
   `llm/client.py` raises `ContentRefused`; `complete_json` returns the schema's empty answer
   (no facts) and the refusal stays in `calls.jsonl`; a stage without an empty form fails loudly.
   `client.content_block_fallback: false` in `config/models.yaml` (true restores [30]'s fallback).
2. **"Do what is necessary, for now don't go above $275. We can increase budget to $400 later down
   the line but not right now."** `lifetime_cap_usd` stays 255 (real bill ≤ $275 with the offset);
   a raise to $400 is a future maintainer decision, never assumed. The evaluated cast is every gold
   character of a work (Anne 43, Oz 35 — docs/eval/parametric/*.yaml), frozen with S02.
3. **Drafted gold and appendix L observations: accepted ("Fine").** They keep their reader labels.

## 2026-09-28 (evening) — Maintainer: Gemini 3.6 Flash for everything, one novel to completion, then the paper

"So continue the project using 3.6 without lite, only work on one novel and then once complete
start writing the paper. We can ask for budget increment and do another novel later."

- **Generator: `gemini-3.6-flash` on every generative stage** (`vertex_flash` in
  `config/models.yaml`, Flex price $0.375/$1.875). Evidence behind the choice: stored-prompt
  precision (0 unsupported of 26 vs 6 of 50), the anne-m36 end-to-end read (recall 18/23, 0
  disclosures, precision 32/40), and today's Flash-Lite 429 outages. The Flash-Lite trial arm
  (anne-m31) was stopped at `graph build`, so there is **no end-to-end Flash-Lite comparison**;
  the paper says so rather than filling those keys. Every build made before this entry is
  Flash-Lite and is never compared with 3.6 numbers.
- **One novel: Anne (v1–5)** — the main work — rebuilt on 3.6 (S01), measured at every cutoff
  (S09), with the baselines run on it (S10/S11) inside the $275 ceiling; then the paper is written
  (S20) from Anne alone. Oz (held out) waits for a budget increase and stays untouched.

## 2026-09-30 — Every number-moving change is recorded with its reason and values (maintainer)

"Remember to note the changes made and their reason including values if necessary for the ablation
study." `docs/eval/CHANGES.md` (append-only) is that record: one entry per system, rendering,
baseline-harness or evaluation-protocol change, and per incident that forced a re-run — what, why,
values before → after, invalidated cells and how they were redone, and the appendix (G ablations,
J reproducibility, L observations) it bears on. Backfilled C1–C6 for 2026-09-29/30. Numbers still
need their MEASUREMENTS row first.

## 2026-09-30 (evening) — Annotation rules for a defensible M3/M4 (decided on the maintainer's "decide the best course")

Chosen where a reading was open, always the one a skeptical reviewer would pick; the rest is
reported as a declared sensitivity analysis, never swapped in as the headline.
- **R1 Placement.** An assertion is judged as the page delivers it. A line under "Shared scenes" on
  the a–b page asserts that a and b both take part; supported only if the chapter narrates both as
  present or acting (generous to the system: anywhere in the chapter). True event, false pairing =
  partial. "N shared scenes" = supported only if N such scenes exist; some = partial; none =
  unsupported. An item under a codex entry must concern that entry. Wrong chapter headings are
  citation errors (M8/M9), not M3.
- **R2 Frame errors.** An atom that misstates its page sentence (truncated at "Mrs.", subject
  swapped) is the harness's error: excluded from M3's denominator, counted, and the atomizer fixed
  before the final samples are drawn.
- **R3 Headline and sensitivity.** M3 headline = supported / (sampled − frame errors); partial and
  uncertain are not support. Sensitivity: atom-level (R1 off), partial as supported, uncertain dropped.
- **R4 Readers.** Agent labels (Codex, Claude) are pilot labels. A published M3/M4 needs a human
  double-labelled stratified subset with agreement (plan 0013 §7); until then the paper says pilot.
- **R5 Comparisons.** Every baseline cell is labelled under R1–R3 with the same sample size; no
  baseline number before `anne_after.sh` has re-rendered it.
- **R6 M4.** Denominator is all of F_t (reveal ≤ 5), page or not; the adjudication covers the whole
  v<t> tree, not only the character's page (G4); t=5 is undefined.

## 2026-10-01 — Decontaminated arm: full matrix, deferred (maintainer)

Asked whether the whole evaluation should also run on the decontaminated text. Costs on the original
text: B5 $16.7, X2 $33.7, B1 $31.6, B3 $4.3, B2 $3.6, X1 $1.2, B4 $1.0 → full matrix ≈ $92 + ≈ $5
paraphrase, beyond the $275 ceiling once the queued work lands; every M1/M3/M4 label would be redone
on the new pages. A targeted arm (paraphrase + memorisation probe + B5 and X1 on `anne-decon`, ≈ $30)
was offered and not taken. **Decision: no decontaminated runs now; the full matrix later.** Until
then the original text is the only evaluated condition, and the paper says so. Prerequisites when it
resumes: maintainer review of the unattended 110-entry Anne map (`config/series.anne-decon.yaml`,
shared with `anne-remap`), a budget ceiling that covers it, gold remapped through the same map.

## 2026-10-02 — Overnight mandate: decisions delegated, decontaminated matrix now, paper drafted from the pilot (maintainer + decisions taken under it)

Maintainer, 2026-10-01 night (in substance): keep working through everything and take the decisions;
stop wasteful runs; audit and fix outputs; once the data is in, start the decontamination work; forget
the budget until **$300 total real API cost**, then stop and ask; start writing the paper LaTeX from the
non-decontaminated data, **leave space for the decontaminated results, explain the contributions properly**.
This supersedes "decontaminated arm deferred" (2026-10-01) and, for drafting only, "no results in the paper
before the maintainer reviews": the draft is filled from the agent pilot and says so on every table.

Decisions taken under it (one line of reason each):

- **One written rule for "conveyed" (M1), applied to all seven systems** (`recall_hand/anne.provenance.md`,
  appendix A): core proposition; both halves of a conjunction; incidental qualifiers may be missing. The
  2026-09-30 "all-parts" wording had been applied more strictly to B5 on a few facts and, through carried
  labels, far too strictly to the baselines (CHANGES C19).
- **Page-level M3 stays the pre-registered headline; atom-level is the sensitivity value.** Baselines have no
  pair pages, so R1 only costs B5. That is reported as a fault of B5 (G5), not adjusted away.
- **G5 and G1 are not repaired on Anne.** Fixing the pair-page rule or the merges after reading Anne's labels
  would be tuning on the test work; they go to OPEN_GAPS and to the held-out run.
- **The paper does not claim quality superiority.** After the audit B5 = B1 on recall (-0.002 [-0.100, 0.054])
  and is lower on page-level precision. Per plan 0013 §8.3 the paper says so first and claims the task,
  the protocol, the input-cut finding (0/792 against 4 and 8 of 220) and the properties of the artifact.
- **Decontaminated matrix order:** paraphrase v1–5, gazetteer, B5, then X1, B2, B4, B3, B1, X2, each scored;
  a budget gate before every billed step (`anne_decon.sh`). B1 and X2 are last: they are the expensive cells
  and the first to drop if the ceiling is near.
- **A 429 on both tiers is waited out, never routed around** (same model for every compared number).

## 2026-10-04 — Statistics reporting: no intervals; mean, median, SD and range (maintainer)

- **Instruction (maintainer, 2026-10-04):** "avoid intervals and use mean, median, standard deviances";
  "also keep the lowest and highest value". Every reported value is its mean over cutoffs with the sample
  standard deviation, the median, and the lowest and highest cutoff value. No bootstrap or Wilson
  confidence interval appears in the paper. (The instruction was first given to a parallel session, which
  added Table "stats" but left the bracketed bootstrap intervals in the abstract, text and tables.)
- **Done:** `fill_results.py` writes means only; `summary_stats.py` adds the five statistics for B5's paired
  differences (their mean equals the paired key, checked for all seven pairs); main table cells are
  mean ± SD with the range below, medians in Table stats; the paired table has Mean / SD / Median / Min /
  Max; the per-cutoff figure has no error bars; setup, results, limitations and appendices A, E, G, I, J
  reworded. `paper_numbers.py` still computes the bootstrap into `paper_numbers.json`; nothing prints it.
- **Rejected:** keeping intervals beside the new statistics (the instruction is to avoid them); a median
  column in the main table (the table* has no room; Table stats carries it).
- **Note for readers of the numbers:** SD and range over five cutoffs describe how a value moves with the
  cutoff, not how it would move with other characters or another run.
