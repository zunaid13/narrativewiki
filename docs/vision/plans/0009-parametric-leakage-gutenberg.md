# PLAN 0009 — Parametric spoiler leakage on decontaminated Gutenberg novels

**Status:** living plan, opened 2026-09-25 (Phase 31). Decision record: `docs/vision/PHASE_31.md`.
Papers: `docs/papers/PAPERS.md` §G. Every number lands in `docs/MEASUREMENTS.md` first.

## Claim the paper is built around

A filter-before-generate spoiler gate stops future facts the system *retrieves*. It does not stop
future facts the generator *remembers*. On a memorised classic, the leak that remains is
parametric. Renaming the characters, the standard fix (WHODUNIT, InfiniteBench), is a treatment
whose effect has to be measured. We measure it, and paraphrase on top of it, per cutoff.

Closest prior work: *Living the Novel* (2512.07474), 90.8% timeline coherence on *Twenty Thousand
Leagues*, with one cutoff, 100 questions, an LLM judge and no memorisation control. TimeChara
(2405.18027) shows parametric future-knowledge leakage in role-play, with no gate and no
decontamination.

## What the first novel says (2026-09-25, MEASUREMENTS §43)

| gemini-3.1-flash-lite, t = 1 | Original | Names remapped | Names + paraphrase |
|---|---|---|---|
| Book identified from a passage | 99.1% | 55.7% (Qwen 14B: 67.0%) | 33.9% |
| Original name recalled for a masked stand-in | 57.4% (cloze) | n/a (same passage) | **51.3%** |
| Part-Two facts on a name-only page (hand-verified) | **32%** | 0% | 0% |
| Part-Two facts on a Part-One-context page, unguarded / guarded | 4% / 0% | 0% / 0% | 0% / 0% |

**The sharper claim this suggests: recognition is not leakage.** Contamination work measures
recognition (cloze, title identification), and by that measure standard decontamination
fails: the model still recalls "Nemo" for 51% of renamed, paraphrased passages. The harm that
matters for a spoiler-safe system is fact transfer, and on these pages it drops to zero once
names change, even though recognition survives. Full-text context also anchors the model on
the original text (0–4%). What is left untested is the one place memory has room: the gated
pipeline's claim-to-prose prompts, where a sparse character gets a few claims and a name (E2).
That run decides whether the paper says "gates suffice once names are remapped" or "gates leak
through thin prompts, and remapping is what closes it".

### Update 2026-09-26: a second model changes the story (MEASUREMENTS §45)

| Hand-verified, t = 1 | Gemini flash-lite | Nemotron-3-ultra (free) |
|---|---|---|
| Part Two facts on a name-only page, original | 32% | 32% |
| Part Two facts on a context page, original (guarded / unguarded) | 0% / 4% | 4% (implication) / 0% |
| Part Two facts, remap or decon, any mode | 0% | 0% |
| Pages naming the **original book or characters**, remap / decon | 0/12 / 0/12 | **4/12 / 4/12** |
| Gated pipeline v01 pages, original (E2) | 0/25 | not run |

**Two leak channels, not one.** *Fact transfer* (future plot facts) is what decontamination
removes, and it did for both models. *Identity disclosure* is new: a strong model de-anonymises
renamed and paraphrased text and writes the real identity on the page ("In the original French
text, this character is Ned Land"), even when told to use only the text. For a spoiler-safe
wiki that is a leak in itself, because a reader who learns the source can look up its ending.
It is **model-dependent**, which is the argument for a multi-model protocol. The paper's claim
becomes: *decontamination suppresses fact transfer but not recognition; whether recognition
reaches the page depends on the generator, so it must be measured per model.*

## Conditions (one series each, same `para_id`s — CONTRACTS §1.6)

| Condition | Series | Built by | Cost |
|---|---|---|---|
| Original | `leagues` | `ingest --volumes 1-2` (Part Two = v2 via `volume_breaks`) | $0 |
| Names remapped (prior practice) | `leagues-remap` | `decontaminate` with `paraphrase: false` | $0 |
| Remapped + paraphrased | `leagues-decon` | `decontaminate` (stage `decon_paraphrase`) | ~$0.30 |

## Experiments

- [x] **E0 Corpus construction** — split, remap, paraphrase; `decon_report.json` residual names = 0.
- [ ] **E0b Paraphrase fidelity** (MiniCheck tried and ruled out as the instrument, §43) — MiniCheck (local, $0) both ways between each remapped paragraph
      and its paraphrase: support rate = no invented content, reverse = nothing dropped.
      Report the rate and a hand-read sample of 50 pairs. Needed before any E2 number is believed.
- [x] **E1 Memorisation probe** (`probe run memorization`, CONTRACTS §9.4) on the remap-only
      condition, generator model. Name cloze and title/author identification.
- [x] **E1 local second model** (qwen2.5:14b, $0) on remap-only: title-ID 91.3% → 67.0%.
- [x] **E1 on `leagues-decon`**, Gemini: source recall 51.3%, book identification 33.9%. Qwen run pending.
- [~] **E2 on the original condition done (2026-09-26, §44):** every audit OK after 7 generic fixes;
      v01 pages leak **0/25** future facts (control 87.5%). **Consequence:** the gate plus grounded
      prose did not leak on this book, so decontamination has nothing to remove here. The
      parametric leak shows only when generation is ungrounded (closed book 32%) or unguarded
      with full text (4%). A decontaminated E2 would compare 0 with 0. The informative next run
      is a novel whose Part Two spoilers are relational (*Little Women*), because relationships
      are where the pipeline writes the most prose.
- [ ] **E2 Gated pipeline, all three conditions**, v1–2 (~$2.5 each). Leak@t at t=1 through the
      existing channels (`probe run leak|disclosure`), plus an **entailment tier**: the share of
      F>1 facts (graph claims with `first_vol = 2`) entailed by any v01 page sentence (MiniCheck,
      $0). Gate on original minus gate on decon = what decontamination buys the gated system.
- [~] **E3 Ungated long-context baseline** (`probe run parametric`, CONTRACTS §9.5). Done on
      original and remap-only (§43); decon pending. First reading: with Part One in context the
      generator barely leaks (0% guarded, 4% unguarded, one Atlantis witness), though it knows
      the plot (40% closed-book). **Implication for the claim:** full-text context anchors the
      model, so the parametric leak is likelier where context is thin, meaning the gated
      pipeline's claim-to-prose prompts (E2) and sparse characters. E2 is now the decisive run.
      Decon condition done too: hand-verified 0 leaks in every mode. Give the generator volume 1's text only and ask for
      each character's page. Volume 2 is never in context, so every F>1 fact on the page is
      parametric **by construction**. Run on all three conditions. This is the cleanest
      parametric-leak number and the main table. ~14 characters × 3 × ~65k tokens ≈ $0.70.
- [x] **E3b Closed-book** is the `closed` mode of E3: 40% on original, 0% on remap-only.
- [ ] **E4 Spoiler-scoped QA + browsing agent** (archived design: `docs/archive/GUIDE_TO_PUBLISHING.md`
      §5 F2–F3). Questions labelled by the volume that answers them, generated from the claim
      graph's `first_vol`, then hand-validated. Score answer accuracy at t2, correct abstention
      at t1, path precision. A correct answer at t1 on the decontaminated site is parametric.
- [ ] **E5 More novels.** Candidates with a natural two-part split and well-known part-two
      spoilers: *Little Women* (Part 1 / *Good Wives*), *A Study in Scarlet* → *The Sign of
      Four* (two books), *Tarzan of the Apes* → *The Return of Tarzan*. Maintainer picks.

## Gold

F>t facts come from the pipeline's own graph, so each novel needs a hand-validated sample:
precision of `first_vol = 2` facts, with the evidence paragraph read. A second annotator on
at least one novel gives inter-annotator agreement. Negative facts must not share keywords
with correct pages (PHASE_30 handover §4).

## Open decisions (maintainer)

1. The E5 novels.
2. A second generator for E1/E3 (another family, to show this is not Gemini-specific).
3. Whether the remap-only condition runs the full E2 pipeline (~$2.5) or only E1/E3.

## Known limits of the instruments

- **MiniCheck errs both ways on page-level leak detection** (§43): it credited 5/25 closed-book
  leaks where lexical markers found 10, and scored "granted a degree of freedom" 0.69 for
  "escapes in its small boat". Before any E3 number goes in the paper, hand-verify every
  positive, and add an LLM judge validated on a hand-labelled sample (≥100 page/fact pairs).
- One page per (character, mode) so far: no sampling variance. Add k≥3 samples before reporting.
- **MiniCheck cannot measure paraphrase fidelity** (E0b read 46.5% on faithful pairs, §43). Use a
  hand-read sample of 50 pairs plus an equivalence judge, and validate the judge on that sample.
- **Memorisation item sets differ per condition** (101 of 115 shared). Compare conditions on the
  paired intersection, or change `select_items` to require eligibility in every condition.

- Remap-only cloze passages are the original's by construction (the one name is masked), so its
  cloze rates are not scored (`masked_identical`). Title identification is the remap-only signal.
- Title keywords score "The Mysterious Island, Jules Verne" as author-only, not book.
- A paraphrase can keep distinctive plot facts (the Nautilus's electricity, the octopus). That
  is the point: decontamination removes surface, not story. E1 measures what is left.
