# Gemini rewrite (`docs/paper/GeminiReview.txt`) — what was checked, what v4 takes

v4 = v3 text, plus only the parts of Gemini's rewrite that were verified against the paper's own
sources (`docs/paper/results.tex`, the v2 appendices in `docs/paper/appendix/`, the logged prompts
in `docs/paper/appendix/k-prompts.tex`, `docs/MEASUREMENTS.md`). Gemini's prose was **not** adopted
wholesale: it rewrites almost every sentence, and the request was to keep the text close to v3.

## Adopted (verified)

| Gemini change | Check | Where in v4 |
|---|---|---|
| Pipeline figure gains panel (b): what each system sees at t=2, how the cutoff is enforced, disclosures original/treated | counts = `M4-anne-total-*` / `M4-annedecon-total-*` (0/0, 0/0, 0/0, 0/2, 1/4, 8/23, 4/0) | Fig. 2(b); the original systems figure is kept in App. E |
| Codex-summary defect: response cites `v01:c27:p0000` instead of the requested key `W1` | true — logged in v2 `k-prompts.tex` ("Paragraph-ID normalization"); v3 had dropped it | App. Q, defect D5 |
| Each logged stage names its exhibited target (Anne v1, Charlie vs. Carrie Sloane, Marilla v1, Aid Society t=1, B1 Anne t=4, B2 Marilla t=1, B3 Anne t=5, X1 Matthew t=5, X2 Gilbert t=1, …) | all match the logged prompts | App. Q stage table |
| The t=3 bridesmaid summary is on Phil Gordon's page | casebook row in v2 `h-leak-casebook.tex` | §6.2 |
| Verifier withholds 21.2% of 2,535 checked facts | `VERIFY-unsupported` | §4 |
| Other-40 recall: 0.737 vs 0.845 (B1) and 0.871 (B2) | `OTH-anne-B5/B1/B2` | §6.4 (Table moved to appendix in v3, so the numbers were missing from the body) |
| Prefix-index wikis need one build per cutoff (59.71M vs 33.13M input tokens) | `PX-anne-t1..t4-TOK` sum to 59.71; `TOK-anne-B5` = 33.13 | §6.5 (stated without the new derived number) |
| Glance caveats: search retrieves only 0.309–0.355 of cross-page pronoun disclosures; precision κ = 0.39 | Table `tab:seeds`; `HREV-P-kappa` | Table 2 |

## Correct, but not adopted (space or already present)

- Darker stroke colours (cyan 008B9E, magenta D81B60) — a presentation choice; v3's palette kept.
- Zero-count upper bound 0.072 (t=1) / 0.221 (t=4) (`M4-anne-bound-*`) — already in App. J (R6); no room in §6.2.
- Gate details (quotes under six words, irrealis markers, 4-paragraph windows, ≤40 windows, 150,000-token
  long-context pass, cosine ≥ 0.86, 4,000-token chapter spans) — all true (App. D); kept there.
- Verifier 0.989 vs MiniCheck 0.718 on 81 items, 0.750 on 12 hard items; pair-verdict 90/99, κ = 0.79 — already in v3.
- Gilbert alone in 62 of 113 book-one mentions vs. a three-quarters rule; 6 of 117 pages at t=2 anchored
  (≥ four fifths of mentions later; `susan` 3 of 204) — true (App. G); not added to §6.5.
- 12 of the 23 partly-established gold facts are dated by an announcing paragraph (`HUMR-gold-announce`) — true.
- B2 chunk (150/300) and budget (6k/12k/20k) tuned at t=2 of *Middlemarch* — true (App. E, MEASUREMENTS 2026-09-28).
- Audit counts 108 (96/12), 119 re-read / 34 corrected, citation 0.457 → 0.512 after attaching timeline
  Sources lines; B4 193/200 precision, 183/200 citation, 0/200 unrelated — true.
- Bibliography: Gemini's `custom.bib` has the same metadata as `refs.bib`, only renamed keys
  (e.g. `guo2025lightrag` = `guo2024lightrag`, `gao2023enabling` = `gao2023alce`); `refs.bib` kept.

## Incorrect or unsupported in Gemini's text (not adopted)

| Gemini statement | Problem |
|---|---|
| Abstract (≈330 words) | ARR limit is 200 words; v3 abstract kept |
| "B1 … up to 559,824 tokens per call" | 559,824 is the single exhibited call at t=4; t=5 calls are longer |
| NarrativeWiki prose: "2–4 sentences for appearance" | the archived NarrativeWiki appearance prompt requests 3–4 (App. E) |
| Matplotlib script: X2 facts lost 11 (orig) / 7 (treated) | swapped; ledger: 7 / 11 (`DROP-anne-X2`, `DROP-annedecon-X2`) |
| "re-reading NarrativeWiki's atom-level negatives changed 0" | that re-read was of the *first* build's negatives |
| Timeline (21/22) and codex pages "exceed 0.955" | 21/22 = 0.9545 |
| Mr. Phillips (0/10) "fail to pass extraction or entity-linking gates" | cause not established; the appendix only reports that no fact is conveyed |
| "matching the theoretical ceiling of a fixed sentence budget" | overclaim; the bound is consistent with, not a fit to, B1's decline (App. I) |
| Proposition 1(ii): a rewrite "must omit at least \|G_{t+1}\| − B facts" and loss "> 0" in expectation | assumes one fact per sentence and random re-sampling; v3's bound with k facts per sentence kept |
| "hyperparameters fixed on *Middlemarch*" for all seven systems | only the comparison systems' settings were chosen there |
| "three prompt and parser defects" | five are logged (App. Q, D1–D5) |
| Ethics: the human label sets were "produced by the authors/reviewers"; "SHA-256 provenance manifests" | new claims with no source in the repository; v3 ethics text kept |
| Paraphrase and cloze listed as one run (`decon-v5`) | they are two runs (`…-decontaminate-v5`, `…-probe-memorization-v1-5`) |

## Restored after review (2026-10-19)

Nothing that v2 contained is removed in v4. Restored: the image-model overview illustration as
Figure 1 (the TikZ overview is kept, in the qualitative appendix); the website screenshots and the
cutoff-interval figure (beside the diff table); the complete logged exchanges of every stage (after
the stage table and defects); the original main table with standard deviations; the B4 per-cutoff
table; the three human-agreement tables (beside the merged matrix); the systems figure; the
recall-change figure; and the original per-cutoff plot (beside its colour-harmonized redraw).
