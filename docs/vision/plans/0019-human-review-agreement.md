# Human-review agreement in the paper

Status: all supplied human–human, reviewer–AI and joint alpha reports implemented and validated.
Date: 2026-10-10. Scope: original-text Anne v1–5 validation tasks, no inference or relabeling.

## Evidence and provenance

The maintainer supplied a four-task reviewer-pair screenshot, confirmed that both reviewers
were human, and clarified that they recorded separate final labels. The transcript reports
111 gold-evidence, 235 recall, 148 precision and 60 citation judgments; 458 items agree on
every decision and 96 have at least one disagreement. The complete screenshot and its footer
were read. Values are transcribed in `docs/eval/agreement/human_review/` and recorded in
`docs/MEASUREMENTS.md`; the raw final human CSVs have not been supplied to this working tree.
No blinding or weighting protocol is inferred. The existing accepted CSV remains the earlier
AI-assisted reference, not either new human reviewer.

The supplied values coincide with the former model report at displayed precision. The
maintainer explicitly identified the supplied report as human–human and instructed us to
retire the former model outputs. The new report therefore records the maintainer's source
and its verification limit rather than citing, repurposing or recomputing the old model data.
Raw human decisions are needed for an independent reproduction.

## Retired outputs and rollback

Checkpoint `d95d307` was committed and pushed before moving files. Only the 25 files in
`docs/eval/agreement/model_runs/`, `model_comparison/`, `accepted_comparison/` and
`alpha_comparison/` are moved outside the repository to
`G:/UIU classes/narrativewiki-old-ai-evals-2026-10-10-d95d307`, preserving relative paths.
The external `archive-manifest.json` records and verifies their SHA256 hashes. Supporting
scripts, cost metadata, calibration plan, caches and the human packet remain in the repo.
Historical measurement rows stay intact; this retirement does not retract their historical
model-model interpretation. The model-only alpha runner is retained as a historical tool;
its old default input paths are now external, and it is not a human-result source.

## Changes and ordered validation

1. Record source precision and human provenance in `human_review/` and the ledger. Done.
2. Add `HREV-*` declarations to `docs/paper/results.tex` and a four-task table in
   `docs/paper/tables/t-human-agreement.tex`. Publish only supplied values.
3. In `sections/05-setup.tex`, point to the new check; in `appendix/a-annotation.tex`,
   distinguish the earlier visible-answer acceptance pass from the two-reviewer agreement.
   Update `sections/limitations.tex`, `sections/ethics.tex` and `REVIEW_NOTES.md` consistently.
   Separate final labels alone do not establish blinding; agreement is not accuracy.
4. Remove active links to retired model reports from the agreement README; preserve the
   existing human packet, calculators and scientific outcomes. Append CHANGES C53.
5. Run structure, numeric and focused packet/calculator checks:
   `python scripts/papers/paper_status.py`;
   `.venv/Scripts/python.exe docs/eval/labelling_tools/derived_values.py`;
   `.venv/Scripts/python.exe -m pytest tests/test_agreement_packet.py tests/test_agreement_alpha.py -q -p no:cacheprovider -p no:tmpdir`.
6. Build with `bash docs/paper/_build/build.sh -disable-installer`; require no LaTeX errors,
   undefined references or overfull boxes. Inspect extracted pages: main text ends on page 8,
   Limitations starts on page 9. Verify all printed human values against the source report.
   Refresh both named PDFs in `docs/paper/` and their existing `dist/` copies; commit.

## Follow-up and stop criteria

Add reviewer–AI pairwise results and Krippendorff alpha only from the later human reports.
Do not insert model coefficients or empty result placeholders into the paper. Record every
new value in MEASUREMENTS first. Do not infer independent annotation, consent, compensation,
reviewer background, blinding, adjudication or corrected system scores from screenshots.
When raw human labels arrive, compare at source precision using the retained kappa calculator;
adapt the alpha runner to explicit human inputs before running it. Stop and document any
discrepancy rather than silently replacing provenance or changing population scores.

## Completed validation

The two PDFs compile to 64 pages with no LaTeX errors, undefined references/citations or
oversized boxes. Main text ends on page 8; Limitations starts on page 9. The new table on
page 16 was visually inspected and every printed value checked against the human-report
transcription. All 256 existing system cells and the other derived values still match the
stored labels. The six focused packet/kappa/alpha-calculator tests pass. Both named PDFs
and their existing dist copies are refreshed. The external archive was hash-verified after
restoring all supporting files. New observations are recorded in MEASUREMENTS.

The reviewer–AI comparisons have now been supplied. Their screenshot is fully transcribed
in `human_review/reported_ai_comparisons_2026-10-10.json`, including the separate 14-item
pair-placement subset and aggregate counts. The accompanying description identifies the
AI reference as unchanged blind first-pass labels; it does not identify a model/reference
file or establish human blinding. Do not equate it with the earlier accepted-reference CSV.
The new full-width table is `tables/t-human-ai-agreement.tex`, with `HRAI-*` result keys.

Pairwise validation is complete: all 30 `HRAI-*` declarations match the supplied report and
both rendered tables. All previously declared values are unchanged; the existing system-cell
checks pass. Both PDFs remain 64 pages with no LaTeX errors, undefined references/citations
or overfull boxes. Main text still ends on page 8, Limitations starts on page 9, and the
new table on page 17 was visually inspected. Both published copies and their existing dist
aliases are refreshed. Reproduction commands and observations are recorded in MEASUREMENTS.

The alpha screenshot has now been supplied. Its header describes AI-assisted annotations
and models, conflicting with the earlier human-reviewer clarification. Publication was held
until the maintainer explicitly confirmed "AI labels plus two human reviewers", meaning
the same unchanged first-pass AI baseline and the two human final label sets. This resolves
the label-set identity for reporting; it does not supply raw files or prove human blinding.
The complete screenshot, including its nominal-distance method footer, was read.
The primary Krippendorff reference was read through pp. 1–5:
https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf.

Values and method are transcribed in `human_review/reported_alpha_2026-10-10.json` and
appended to MEASUREMENTS before paper changes. `HRAL-*` declarations and
`tables/t-human-alpha.tex` report the five tasks' alpha, mean pairwise agreement and
unanimous counts. The appendix explains joint calculation and includes the method citation;
the limitations distinguish joint AI–human concordance from all-human reliability.
No averaging of kappas, mixed-task pooling, raw-label recomputation or system-score correction
is performed. Pair placement remains a subset; its human–human kappa is not inferred.

Alpha validation is complete: all 21 HRAL declarations and each rendered table row match
the supplied transcription in both PDFs. All previously declared results remain unchanged;
all 256 existing system-cell comparisons pass. Both PDFs compile to 65 pages with no LaTeX
errors, undefined references/citations or overfull boxes. Main text ends on page 8,
Limitations begins on page 9 and the alpha table on page 18 was visually inspected.
The published PDFs and their existing dist copies are refreshed. Commands and observations
are appended to MEASUREMENTS.

Remaining follow-up requires raw human and AI files and reviewer protocol details for
independent reproduction; the human–human pair-placement coefficient remains unsupplied.

The subsequent visual-emphasis update reuses Table 10's cyan/pink fills and boldface.
Sixteen cells mark column maxima/minima in rates and coefficients, with descriptive
caption legends and the pair-placement subset retained. Counts remain plain. All values
and source reports are unchanged. Both PDFs now have 66 pages; main text still ends on
page 8 and Limitations begins on page 9. The three agreement tables on pages 17–19 were
visually inspected, and all rendered rows checked in both variants. MEASUREMENTS records
the highlight policy, corrected preliminary observation and clean-build validation.
