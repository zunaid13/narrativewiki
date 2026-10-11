# Reviewer concerns: label finalization and remaining validity repairs

Status: reporting repairs implemented and validated; empirical follow-up remains open.
Follow-up: plan 0022 imports supplied final reviewer CSVs, reproduces agreement, adds pair
placement, corrects reversed reviewer-reference columns and qualifies reference identity.
Human authorship is maintainer-reported; preserved archival metadata conflicts with it.
Raw-label availability is resolved; blinding, provenance verification and adjudication remain open.
Date: 2026-10-10. Run id: `reviewer-concerns-20261010`.

## Scope and evidence

The maintainer requested a GitHub checkpoint before auditing seven supplied reviewer concerns.
The working tree was clean; existing head `e603b6b` was pushed to
`origin/phase-26-citable-pages`. No checkpoint commit was needed.

Read the current setup, results, limitations, annotation, construction-scope, contamination
and reproducibility sections in full; read the archived prompt excerpts relevant to aliases,
title recognition and the schema defect; read the human reports, finalization records and
current handover. The graphify graph predates these edits and was used only to locate code,
not as evidence of current human completion. No new paper was required for these reporting
repairs; research reading in this audit is limited to repository records and their stored
results. Do not infer results of new blinded annotation or experimental runs.

The maintainer clarified that Claude **reviewed and finalized** earlier AI work, then requested
that the manuscript report only Claude as the AI label annotator. This supersedes the old
manuscript attribution of different final annotators. `docs/eval/annotation_provenance_20261010.json`
records the finalization statement and hashes of the current labels; historical drafting
records are preserved. This is a provenance clarification, not a new annotation pass.
The exact unchanged AI first-pass reference used in supplied human-agreement summaries is
not independently matched to the finalized system labels; do not silently equate them.

All new counts and observations are recorded in `docs/MEASUREMENTS.md` before use in the paper.
`docs/eval/disclosure_units_20261010.json` gives deterministic counts and source hashes.

## Concern-by-concern status and best remaining fixes

| Concern | Applied or already present | Remaining best fix |
|---|---|---|
| 1. Label validity / human annotation | Two human reviewers and task-wise human-human, human-AI and joint-alpha tables already exist. Setup now specifies that review-triggered recall corrections are included, while precision/citation disagreements were not propagated. | Obtain the separate raw decisions and reviewer protocol, reproduce agreement, adjudicate disagreements under one rule, and extend corrections across comparable populations before recomputing scores. Repair insufficient gold evidence and repeat reveal-date checks. Agreement summaries alone do not establish blinding, correctness, or corrected population metrics. |
| 2. Different final AI annotators | Manuscript attributes all reported AI labels to Claude Opus 5.5, following the maintainer's finalization clarification. No label value was changed. | Preserve raw source decisions and exact finalization scope. A common finalizer removes the asserted difference in final label ownership; it does not establish independent blinded evaluation or equivalence between original and treated generations. Use shared blinded samples and a fixed decision rubric for stronger comparisons. |
| 3. Single runs / test-series tuning | Setup and limitations already state single runs and Anne's development role. No ranking is presented as established across works. | Freeze code, prompts, rubric and primary outcomes before evaluating an untouched, approved series. Generate repeated independent artifacts for primary systems and report variation across runs/works; bootstrap paired shared fact or character units with clustering. Do not turn cutoff SDs into run uncertainty. |
| 4. Later identities in prompts | Method now distinguishes omitted explicit title/author metadata from title recognition in model outputs. Results acknowledge later aliases in early prompts and that existing index/wiki comparisons do not isolate this channel. | Filter every prompt's aliases, canonical names and other-entity lists by the evidence volume; use prefix-built identity groups when undated merges cannot be undone. Audit serialized prompts, including verifier and long-context inputs. Test on fixtures and stored prompts first, then freeze and run a smallest-slice controlled comparison before any broad confirmation. |
| 5. Underpowered / repeated disclosure units | New script and appendix table count unique subject facts, with a stated unit. Reciprocal facts remain distinct; repeated cutoffs collapse. B5 error-mechanism descriptions distinguish the original inverted relation from the treated prediction-to-marriage mechanism. Named and cross-page-pronoun detection rates already have separate reporting; low counts remain detection-limited. | Independently validate fixtures, manually inspect a stratified sample of retrieval-negative pages, expand the unique future-fact inventory, and annotate event/error clusters explicitly. Report assessments, unique subject facts and independently adjudicated event/error counts together. Avoid universal spoiler-safety or population-rate claims. |
| 6. Framing versus results | Introduction leads with the task and threat model; abstract calls this a pilot and discussion favors prefix retrieval. Follow-up plan 0021 changes the title to “Evaluating Character Wikis at Reader-Selected Narrative Cutoffs” and consistently frames NarrativeWiki as the reference implementation. | Retain factual/citation shortcomings; stronger empirical claims still need held-out data, repeated generations, independent annotation and reader validation. |
| 7. B4 grouping | B4 is included in the B1-B5 pooled generation-input-bounded denominator and system uncertain counts. The generator derives these keys from stored labels, and the derived-value check covers them. | Keep construction scope distinct from generation inputs: B4 and B5 use full-built graphs, while B1-B3 have prefix-only inputs/indexes. No broader safety claim follows from grouping them by generation access. |

## Changed files and reproducible checks

- `scripts/eval/disclosure_units.py`: source-preserving assessment and unique subject-fact counts,
  fail on duplicate/ineligible units; optional narrow paper-key update.
- `tests/test_disclosure_units.py`: reciprocal/repeated facts, inclusive counts and invalid units.
- `docs/paper/_build/fill_v2.py`: derive revised grouping during normal refresh, rather than restoring
  the former hard-coded denominator.
- `docs/eval/labelling_tools/derived_values.py`: compare the new declarations with live label counts.
- Manuscript setup, results, limitations, method and relevant appendices; new unique-fact table.
- `docs/eval/annotation_provenance_20261010.json`, `docs/eval/disclosure_units_20261010.json`,
  `docs/MEASUREMENTS.md`, `docs/eval/CHANGES.md`, paper README and author review notes.

Ordered checks (no model call):

```powershell
python scripts/eval/disclosure_units.py --output docs/eval/disclosure_units_20261010.json --fill-paper
.venv/Scripts/python.exe -m pytest tests/test_disclosure_units.py -q -p no:cacheprovider -p no:tmpdir
python scripts/papers/paper_status.py
.venv/Scripts/python.exe docs/eval/labelling_tools/derived_values.py
& 'C:/Program Files/Git/bin/bash.exe' docs/paper/_build/build.sh -disable-installer
python docs/paper/_build/overfull.py
python docs/paper/_build/emptykeys.py
```

Validate both PDF variants: no errors, undefined references/citations or overfull boxes;
main text must end on page eight with Limitations beginning on page nine. Visually inspect
the new table and affected text. Refresh the existing named PDF copies after checks pass.
Commit only this work and push the branch. Do not edit protected planning/history files.

## Ordered future experiments and stop criteria

1. **Raw-label audit, free.** Import separately identified human CSVs and the unchanged AI reference;
   reproduce the supplied task-wise summaries before adjudicating. Stop if identity, counts or
   coefficients disagree; record the discrepancy rather than rewriting source provenance.
2. **Blinded common-sample adjudication.** Use the existing questions-only packet as a starting point,
   supplying eligible context needed to distinguish support from missing evidence. Freeze rules;
   preserve first passes and record protocol/background/consent. Disclosure and treated text need
   their own samples. Do not apply sampled corrections to unreviewed populations selectively.
3. **Temporal prompt fixtures, free.** Identify every builder in `extract/infobox.py`,
   `extract/claims.py`, `graph/verify.py`, `synth/prose.py` and entity classification/resolution.
   Add evidence-volume assertions at the serialized call boundary. Check adversarial future aliases,
   canonical surnames and full-series entity lists across stages before asking a model to generate.
4. **Frozen held-out / repeated-run evaluation.** Choose an actually unused approved series and
   document that no tuning used it. This decision remains unresolved: do not assume an existing
   development/stress corpus is held out or expand corpus scope. Determine call budget only after
   fixture/cache paths cannot answer the experimental question; state the reason before billing.
   Independent repeats must retain genuine sampling variation; cache hits are not new runs.
5. **Disclosure coverage.** Expand independently validated unique facts and pronoun fixtures, read
   retrieval negatives, and record event identifiers separately from reciprocal facts/cutoff rows.
   Stop any safety headline if candidate coverage or sampling assumptions do not support it.

No new inference, billable generation, corpus expansion or system relabeling is part of this audit.
Remaining empirical concerns are explicitly open; reporting repairs do not certify their resolution.

## Completed validation

The focused disclosure-accounting tests pass. All existing per-system values and supplied
human-agreement results are unchanged; the derived-value checker validates both existing
cells and the new declarations. A read-only intercepted run of the normal `fill_v2.py`
refresh verifies that it preserves the revised values and descriptions. Source-label hashes
still match the finalization manifest. Both PDFs compile without errors, undefined
references/citations or overfull boxes; the main text ends on page eight and Limitations
starts on page nine. The unique-fact table was visually inspected in the reading copy and
its extracted rows checked in both variants. Named paper/dist copies and the existing
Overleaf ZIP are refreshed. Reproduction commands and validation observations are in the ledger.
