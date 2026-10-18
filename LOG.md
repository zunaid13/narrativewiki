# LOG.md — build log, newest first

What has been built, in reverse chronological order. `VISION.md` records *what we are building
and why*; this file records *what is done*. Append a new entry at the **top**; keep each to about
15 lines. Full context for a completed phase goes in `docs/handover/PHASE_N.md`, not here.

Once this file exceeds ~15 entries, drop everything older than the last 8 — `git log` is the
archive (the old `docs/log/LOG_ARCHIVE_*.md` files were removed 2026-09-14).

## 2026-10-19 — Paper v4: v3 combined with the checked parts of Gemini's rewrite (no model call, no new number)

- **Deliverable:** `docs/paper/v4/`, PDF `docs/paper/NarrativeWiki-paper-v4.pdf` (40 pages, main body 8).
  Build: `sh docs/paper/v4/build.sh`. Check report: `docs/paper/v4/GEMINI_CHECK.md`.
- **Taken from Gemini (each verified against results.tex / v2 appendices / logged prompts):** pipeline figure
  panel (b) with the system-access matrix (separate systems figure removed); codex paragraph-ID defect restored
  (D5); exhibit targets in the stage table; Phil Gordon named; verifier withhold share; other-40 recall; prefix
  builds cost one build per cutoff; two sharper glance caveats.
- **Rejected:** 330-word abstract, "up to 559,824 tokens per call", 2–4 vs 3–4 sentence prompt, swapped X2
  facts-lost, unsupported ethics claims, overclaims ("matching the theoretical ceiling") — full list in the report.
- **Text kept close to v3;** to hold 8 pages: two RQ headings shortened, Statistics paragraph merged, one
  sentence repeating RQ1 removed, figure spacing tightened.

## 2026-10-18 — Paper v3: presentation overhaul from the Gemini blueprint (no model call, no new number)

- **Deliverable:** `docs/paper/v3/` (self-contained; shares only `../results.tex` and `../refs.bib`), PDF
  `docs/paper/NarrativeWiki-paper-v3.pdf` (40 pages, was 62; main body still 8). Build: `sh docs/paper/v3/build.sh`.
- **Applied:** RQ1–RQ5 spine (intro + declarative §6 headings); "paper at a glance" table; image-model teaser
  replaced by a TikZ schematic from stored intervals; four new TikZ data figures (control dashboard, accumulation,
  context collapse + identity, per-cutoff); screenshots → structured diff table; one colour grammar (cyan gain,
  violet headline, magenta failure, lavender confounded); Tables 1+11, 5+6+7, 12+18, 25+26 merged; Appendix O
  30 pp → 3 pp (stage table + 4 defect callouts); formal propositions (App. I) and six reporting recommendations
  (App. J); limitations with declarative openings. Zero raster images remain.
- **Checked against the blueprint, corrected there:** X2 facts lost are 7 orig / 11 treated (blueprint swapped);
  its dashboard mislabelled B2–B5 ("Multi-Agent Debate", "BM25 RAG"); screenshot citations (ch.14 P8, +26, XVII P36).
- **Not done:** Tier A bootstrap CIs (conflicts with the no-intervals rule) and Tier B runs (bill the API); appendix
  section titles left nominal. All numbers come from existing `\res` keys or tables already in the paper.

## 2026-10-12 — Paper v2 checked against the external "v3 ARR review" (no model call)

- **Asked:** judge each point of `NarrativeWiki-v3-ARR-review.md`; fix the paper where it is right; look at
  nothing outside the repo root. Ledger: MEASUREMENTS 2026-10-12 "checked against the external v3 ARR review".
- **Confirmed and fixed (text):** overclaims (I01/S08 "every paragraph", "separates reading from recall"; S01/I02
  "trace each effect", "vary only access"; S14 "stored facts are sound"; I04 "passage is gone"; I03 presumed flag;
  I13/S09 "no later fact"; I19 prefix wikis keep the implied bridesmaid; S03 exploratory split; I07/I08/S19
  mean + textually distinct + condition switch; S18 line-rule and statement-alone precision beside 0.789).
- **Confirmed and fixed (appendix):** I05 gate (subject in or beside paragraph; object for 12 predicates), I09
  "clean build" → reported runs, I06 t-stats caption, I11 B2/B4 command flags, I12 budget units, I16 reveal
  defined on the prefix, I17 M8 equation now ignores later citations as the rule says (and `\mathbb{1}` glyph
  fixed to `\mathbf{1}`), I21 alive (assumed), I23 LightRAG defaults, I25/I26 exhibit coverage, I27 Codex model
  not recorded, I10 verifier run order explained, I15 Jones et al. in Table 3, I28 Fig. 3 condition, I30
  contents overlap, I32 agreement-table colouring removed, S16/I20 within-volume arbitration in Limitations.
- **New value:** B4 page generation 1.11M / 0.36M tokens (`TOK-anne-B4`, run_cost.py, $0). Bib: NovelQA →
  ICLR 2025 (stored PDF), HyTE pages/DOI; STORYSUMM MiniCheck claim scoped to Flan-T5.
- **Not changed:** I29 (quote marks in Fig. 1 are an intended quote icon); S04–S07, S12–S13 need new annotation
  or runs; human-reviewer wording untouched per maintainer (2026-10-12). Verified: v2 p8 end, abstract 191–199,
  62 pages; v1 61 pages; 0 errors/overfull.

## 2026-10-12 — Phase 34: paper v2 fixed against the pre-submission review (no model call, no new number)

- **Asked:** fix v2 per `NarrativeWiki-presubmission-review.md`; caveats once (not self-deprecating), readable
  8 pages, no experiments, no results removed.
- **Desk-reject fixes:** stored v2 PDF is now the line-numbered `submission_v2.pdf` (README said copy the
  ruler-less build); appendix contents and Appendix O (prompt logs) two-column; figure-PDF metadata
  suppressed (`\pdfsuppressptexinfo=-1`); Limitations rewritten v2-only with no numbers (0.753 pair
  sensitivity and seeded-search recall moved to §5/§6.2).
- **Body (v2 forks `sections_v2/02..05`, `limitations`):** each caveat stated once in Limitations; control
  introduced before the findings; "treated text" / "graph baseline" throughout; annotators named (Codex
  first pass, Claude finalizes); abstract gives unique-fact X2 count (17/88 vs 8/88) and strict identity
  rate (0.220); central-character original-text lead softened; walter example marked first build.
- **Shared fixes (v1 rebuilt too):** I1–I28 wording/cross-refs (B4 name, 341-page denominator, k in zero
  bounds, flagged arbitration, infobox/paraphrase log notes, thinking_budget 0, Qwen2.5-14B named),
  kappa/alpha to 2 dp, Amazon/Krippendorff refs fixed, NovelQA/BooookScore/HyTE/Qwen2.5 added.
- **Verified:** v2 main text ends p8, abstract 189–198 words, 0 errors/overfull, 62 pages; v1 60 pages.
- **Open (maintainer):** checklist + service contributor (D4/D5), repo check (R9), reviewer details (R4),
  Appendix N release claim vs commit a317bc8 quarantine.

## 2026-10-11 — Phase 34: paper v2 reframed as a trade-off; advantages added (no model call)

- **Asked:** check `main_v2` against `docs/eval/narrativewiki_advantages.md`, add what is missing, retitle
  from "what decomposition loses" to trade-offs.
- **Changed (v2 only):** title "Probing the Trade-offs of Decomposition ..."; abstract, intro (gain bullets
  beside the cost bullets), new §6.3 "What decomposition gains" + Table `tab:gains` (central-three recall,
  other-40, facts lost across cutoffs), Discussion/Conclusion around one cause for both sides. New
  Appendix H `appendix/n-accumulation.tex` (per-cutoff and per-character recall, artifact size, cost per
  unit, unique facts, LightRAG head-to-head, caveats). Figure `fig:deconrecall` moved to Appendix L for
  space; Limitations gains a v2-only caveat. Shared files changed only inside `\ifdefined\nwvtwo`.
- **Verified:** main text ends p8, abstract 196–202 words (was 199–207), 0 errors/overfull; v1 text
  identical to the stored PDF. New keys CEN-/OTH-/DROP-/UPS-/UNIQ- in `results.tex`; one new ledger row.

## 2026-10-11 — Phase 34: where NarrativeWiki pulls ahead (stored labels, no model call)

- **Asked:** is there any situation where the graph wiki beats long context, prefix retrieval or LightRAG.
- **Found:** on the three most-covered subjects (141 of 335 gold assessments) B5 leads every system,
  0.894 vs 0.837 (B1) on the original and 0.929 vs 0.794 on the treated text, and its lead grows with
  the cutoff; it trails on the other 40 subjects. B5 loses 1 fact between consecutive cutoffs, the
  per-cutoff systems 4–24. B5 ships 345 pages / 219k words at t=4 against 33 / 25k.
- **Caveat:** baseline pages share a sentence budget, so this is a win over budget-capped pages.
- **Deliverable:** `scripts/eval/recall_by_centrality.py` → `docs/eval/recall_by_centrality.json`;
  rows in `docs/MEASUREMENTS.md` (2026-10-11 section). Paper not edited.

## 2026-10-11 — Phase 34: paper v2 framing pass (design under test; each caveat once, in Limitations)

- **Asked:** apply a reviewer memo to `main_v2`: stop arguing against the system in every section, state
  each caveat once in Limitations, and lead with the strengths the tables already support.
- **Changed (v2 only):** `sections_v2/` abstract, introduction, Results, Discussion, Conclusion. Figure 1
  uses `figures/f0-teaser-v2.pdf`: "Our solution: NarrativeWiki" and "No spoilers" are removed from the PDF
  text layer (`scripts/papers/redact_teaser_v2.py`) and re-lettered "The design under test" / "Cutoff-filtered page".
- **Changed (shared with v1):** `sections/02-related`, `04-method` (verifier accuracy replaces the "bug"
  sentence), `05-setup` (two-reviewer kappa range in the main text), `limitations` (zero counts, B4 does not
  isolate effects, repairs untested), appendix A (two-reviewer check first; the column-reversal note stays in
  plan 0022 only), C, I and the prompt appendix ("Note on this log").
- **Verified:** both versions 0 errors, 0 undefined references, 0 overfull boxes; main text ends on page 8 in
  both; v2 abstract 198 words (`scripts/papers/check_paper_limits.py`). Each number in the memo was checked
  against `results.tex` before use; all matched.
- **No new number:** two rounded keys only (`HREV-R-kappa-2dp`, `HREV-P-kappa-2dp`); no model call, $0.
- **Not adopted as worded:** "validated by two reviewers (kappa 0.83)" in the abstract (the best task only;
  reviewer-AI kappa on precision is about 0.5), "cuts title recognition by 87%" (a new derived figure),
  "the gap lies in citation attachment, not the graph's evidence" (B4 also differs in page scope).

## 2026-10-11 — Phase 34: paper version 2 (NarrativeWiki as a probe; renamed-text control first)

- **Asked:** a version-2 paper from reviewer guidance: reframe NarrativeWiki as an analytical probe of
  graph decomposition, and expand the decontamination experiment and move it to the front of Results.
- **Built:** `docs/paper/main_v2.tex` + `sections_v2/` (abstract, introduction, results, discussion,
  conclusion), `figures/f5-decon-recall.tex` (recall, original vs treated, per system). Everything else is
  shared with `main.tex`; four shared files branch on `\ifdefined\nwvtwo`. PDF:
  `docs/paper/NarrativeWiki-paper-v2.pdf`. Build: `NW_MAIN=main_v2 sh docs/paper/_build/build.sh`.
- **Verified:** 0 errors, 0 undefined references, 0 overfull boxes; main text ends on page 8, Limitations on
  page 9; abstract 199 words. Version 1 rebuilt afterwards: its text is identical to the stored PDF.
- **No new number:** every value is an existing `\res` key; no model call, no relabelling, $0.
- **Not adopted from the guidance (ledger does not support it):** "soundly defeated by B1" (treated-text
  recall is tied, citation sufficiency is higher than B1's), "definitively separates" reading from
  memorization, "built to demonstrate". Reasons in `docs/vision/PHASE_34.md`, 2026-10-11.
- **Gaps:** the teaser image still shows a "No spoilers" badge (no editable source; heading re-lettered by
  overlay). The simulated-review pass of the writing skill was not run. Maintainer has not read version 2.

## 2026-10-09 (01:50 local, 2026-10-08 19:50 UTC) — Phase 34: citation sufficiency labelled for every cell that lacked it; in the paper

- **Asked:** "if there is anything else left to run for the paper, run it". Nothing was running and no printed
  value was empty; the one gap was citation sufficiency (M8) on 18 cells. No model was called; $0.
- **Labelled (one agent reader, every cited paragraph read; CHANGES C52):** original text, sufficient of 40 at
  t=1..5: LightRAG 23, 32, 31, 31, 36 (**0.765**); graph baseline 37 (Codex, earlier), 35, 38, 36, 37
  (**0.915**); full text 28, 27, 23, 25, 22 (**0.625**). Prefix-discovered builds at t=1..4: 26/40, 17/40,
  24/40, 24/39. Treated minus original now exists for six systems (LightRAG +0.029, graph baseline -0.020,
  full text -0.150).
- **Paper:** the dashes in Table 1, the per-cutoff table and the treated-text table are values; statistics
  table +3 rows; Appendix G: citation column for the graph baseline, two rows for the prefix builds, a sentence
  each; Limitations. Seven ledger rows (three are observations: where citations fail by system; lists attached
  per section; the reported system's 29 of 64 on character pages against the graph baseline's 183 of 200).
- **Verified:** observations of the three systems regenerated, recall/precision/disclosure unchanged count by
  count; `derived_values.py` exits 0; `build.sh` 0 errors, 0 undefined, 0 overfull, 48 pages (one more than
  before, in the appendix); page 9 begins with "Limitations". PDFs copied to `docs/paper` and `dist/`.
- **Release:** `make_release.py` (14,220 files) and `make_submission_repo.py` (12,764 files, clone commit
  `ee2ec8b`, not pushed: the maintainer pushes) rerun, both scans clean; `derived_values.py` OK in the clone.
- **Not done:** human check of these labels; the citation cells of the first build (`anne@b4`, `anne@p2`,
  `anne@p3`), not in any table; `paper_codex/` (the separate Codex manuscript, being edited by a Codex session
  during this one) still prints the old cells. `freeze.py check v2m` reports the `scripts` tree changed: that
  is the Codex paper's three scripts, not this work.

## 2026-10-08 (22:20 local, 16:20 UTC) — Phase 34: the prefix-discovered builds (t=1..4) are labelled and in the paper

- **Done:** `anne@p4-v2` built (second session, to 13:51 UTC), scored (15:57 UTC) and labelled. All four
  prefix-discovered builds of the reported system now have recall, precision and disclosure labels.
- **Result, prefix against full at the same cutoff:** recall 19/23, 35/46, 54/66, 72/89 against 19/23, 35/46,
  53/66, 73/89 (**180 of 224 each**); precision 38/40, 30/40, 35/40, 31/39 against 33/40, 28/39, 35/40, 34/40;
  no stated later fact in either. Tokens 59.71M in / 3.32M out for the four builds (33.13M / 1.86M for the one
  five-volume build); billed 26.46 USD.
- **Paper (CHANGES C49, C50):** Table `tab:prefixv2` and a paragraph in Appendix G; one sentence in Section
  6.3; Limitations; the split of gap G19 (most lost candidates have too few mentions in the prefix; a sixth
  at t=1 is a mining rule, left unchanged by decision).
- **Verified:** `build.sh` 0 errors, 0 undefined, 0 overfull, 47 pages; page 9 begins with "Limitations";
  `derived_values.py` exits 0. PDFs and the release zip refreshed.
- **Not done:** the treated text (maintainer: not wanted); citation labels and a human check for the new
  cells; the anonymous submission repository was not rebuilt after these changes
  (`scripts/papers/make_submission_repo.py`, the other session's builder).

## 2026-10-08 (19:25 local, 13:25 UTC) — Phase 34: anonymous submission repository

- **Built:** `scripts/papers/make_submission_repo.py` writes `../narrativeWiki - for paper submission/`
  (12,722 files, 437 MB on disk, 35 MB as git objects; one commit, author "Anonymous", UTC). Rerun it after
  any label or code change; it rebuilds the tree in place and keeps its `.git`.
- **In:** `src`, the scripts and config of the works the paper reports (Anne, treated Anne, Leagues, Middlemarch
  for tuning), `USER_GUIDE.md`, CONTRACTS, PROMPTS, the ledger and CHANGES, `docs/eval` of those works,
  `results.tex` + result tables, `dist/<series>/wiki` (Markdown), the treated text (`data/*-decon/01_parsed`).
- **Out:** LOG, VISION, phase/handover/plan files, CLAUDE/AGENTS/STRUCTURE, tests (they load the development
  series' configs), runners, reference PDFs, the paper's prose, Oz and every commercial series, the LLM cache.
- **Verified in the clone:** `derived_values.py` prints OK (every printed value matches the labels);
  `summary_stats.py` leaves `results.tex` unchanged; `paper_numbers.py` runs on the shipped observations;
  `wiki doctor -s anne` runs; every `.py` compiles; no kept script imports one left out.
- **Leak fixed:** timestamps carried the local UTC offset (572 occurrences, ledger and human-check notes).
  `make_release.py`'s rules now strip it and its scan rejects it, so the zip has to be rebuilt as well.
- **Gaps:** `run_series.py` and `tune.py` start `.venv/Scripts/python.exe` (stated in the clone's README, not
  changed: frozen code). No licence file. `\anonrepo` in `macros.tex` is still the placeholder.

## 2026-10-08 (15:30 local, 09:30 UTC) — Phase 34: prefix-discovered builds t=1..3 labelled; paper in tokens, bar figure, page limit restored

- **Built and labelled:** `anne@p<t>-v2`, the reported system on prefix-only entity indexes, t=1..3 (runner
  `docs/eval/runners/prefix_build_v2.sh`; 15.90 USD). Against `anne@v2` at the same cutoff: recall 19/23, 35/46,
  54/66 (full 19, 35, 53); precision 38/40, 30/40, 35/40 (full 33/40, 28/39, 35/40); no stated later fact in
  either. Agent labels, one reader. **Not yet in the paper.** t=4 is building under a second session
  (`prefix_build_v2_t4.sh`); the scorer of this session scores it when it ends.
- **Paper (CHANGES C47):** every dollar figure replaced by input / output tokens; Figure 6 (cutoff plot) is
  grouped bars; **correction:** the entry below was wrong that the conclusion still ended on page 8 (it ran
  nine lines over). Section 6.3's identity paragraph is now one sentence and the conclusion ends on page 8.
- **Tables (CHANGES C48):** the values that carry each table's finding are bold, chosen by rule from
  `results.tex` (`docs/paper/_build/bold_tables.py`, run after `summary_stats.py`); each caption says what
  bold means. Tables without values (metric list, baseline settings, casebook, related work) have none.
- **Verified:** `build.sh` 0 errors, 0 undefined, 0 overfull, 47 pages; page 9 begins with "Limitations";
  `derived_values.py` exits 0; no "dollar", "USD" or price left in the PDF text. Freeze `v2m`.
- **Next:** label t=4 when scored; put the four-cutoff prefix-build comparison in Appendix G with one clause
  in Section 6.3 (there are four spare lines on page 8); update the Limitations sentence that says no page
  was built on the prefix indexes.

## 2026-10-08 (04:30 local, 22:30 UTC on 10-07) — Phase 34: construction dependence has a metric; entity discovery run per prefix

- **Built:** the v2 entity index from volumes 1..t alone, t=1..4, on `anne@v2` (`data/anne@v2/@t0N/02_entities/`;
  runner `docs/eval/runners/prefix_gazetteer.sh`; 0.21 USD, 22 minutes). Nothing existing was rewritten.
- **Metric:** `scripts/eval/identity_dependence.py` ($0) -> `docs/eval/identity_dependence_anne@v2.json`. Share of
  the full build's character pages at t whose set of names seen by t no prefix-built character has:
  **0.390, 0.256, 0.133, 0.089** at t=1..4 (mean 0.217). At t=1: 10 alias, 4 regrouped, 9 absent of 59 pages.
- **Finding:** per-prefix discovery is cheap, so cost is not the reason against it; its index is thinner (0.943 of
  the full build's character mentions at t=1), partly through a mining rule that drops bare "Gilbert" on book
  one alone (OPEN_GAPS G19).
- **Paper:** Section 6.3 paragraph, Appendix G Table `tab:identity`, Limitations sentence; 16 new keys, no
  existing key moved; 47 pages, conclusion still ends on page 8; PDFs refreshed. CHANGES C46; freeze `v2l`.
- **Not done:** extraction, graph and pages on the prefix indexes (no recall, precision or disclosure for such
  a build); the treated text; a repeat run for model variance. The paper says so.

## 2026-10-08 (02:35 local, 20:35 UTC on 10-07) — Phase 34: paper audit before submission (numbers, references, venue rules) and a review

- **Numbers:** all 241 printed cells equal the observation files. Eleven hand-typed values had not followed C43
  (first-build recall 0.866 -> 0.855, prefix-build recall, line-rule precision 0.623 -> 0.628, citations among
  cited atoms, the page-kind table, 43 -> 42 negatives) and nine statistics came from rounded rates. CHANGES C45;
  new checker `docs/eval/labelling_tools/derived_values.py` (exit 1 on the previous `results.tex`, 0 now).
- **Text:** abstract 365 -> 199 words (limit 200) and, with the discussion and conclusion, now states that the
  main system disclosed 4 of 220 on the treated text; treated cells are said to be the first annotator's and
  outside the human check; recognition sentence corrected; Spice-and-Wolf counts removed from the development
  appendix; Figure 1 numbered two steps "3"; the AI-generated figure is disclosed.
- **References:** 25 of 25 exist with matching records; three now cite the published version, one author list
  completed; added Jones et al. 2018 (spoilers in fan wikis, the closest prior work), BookWorm, NoCha, Amazon.
- **Verified:** `build.sh` 0 errors, 0 undefined, 0 overfull; 46 pages, conclusion ends on page 8; freeze `v2k`.
- **Venue:** NAACL 2027 and COLING 2027 share the ARR October cycle; **deadline 2026-10-12** (anywhere on earth).
- **Owed by the maintainer:** the anonymous repository (the paper prints `narrativewiki-0000`), the Responsible
  NLP checklist (reviewer's role, pay, time, consent; AI use), the exact Codex model. Review, expected outcome
  and what would change it: `docs/paper/REVIEW_2026-10-08.md`. State: `docs/handover/PHASE_34.md` §0d.
