# Supplied reviewer labels: reproduce agreement and correct identities

Status: completed import, calculation and reporting pass; PDFs, Overleaf and local anonymous archive refreshed. Empirical follow-up remains open. No tests or experiments rerun.
Date: 2026-10-10. Run id: `human-label-reproduction-20261010`.

## Authorization and evidence

The maintainer supplied answers.csv and responses.jsonl from the archived `gemini_pro`
directory as reviewer 1 and `openrouter_ultra` as reviewer 2, asking to resolve remaining
issues. Read the files, accompanying metadata, packet/mapping, reported summaries and
the existing nominal coefficient implementations. The graph predates these records and
does not establish provenance. The clean checkpoint was pushed before importing or editing.
The earlier instruction to skip tests and experimental reruns remains in effect.

When asked about the metadata, the maintainer first confirmed humans reviewed and finalized
these exact decisions, then stated "none of the files were anything AI. humans did both".
The original metadata describes Gemini/Nemotron model-model runs. **This is a recorded
conflict:** reviewer identities and human authorship are maintainer-reported; neither
authorship, assistance nor blinding is independently established by the files. Preserve
the CSVs, JSONL and metadata byte-for-byte and document the conflict rather than rewriting
archival metadata or inventing an independent human protocol. No external archive is edited.

## Implemented repairs

1. Copy supplied records and original metadata into `docs/eval/agreement/human_review/`
   under reviewer_1/reviewer_2. A provenance manifest preserves source-relative locations,
   file hashes, identity assignments, both clarifications and the archival conflict.
2. `scripts/eval/reproduce_reviewer_agreement.py` uses the existing stdlib Cohen-kappa and
   nominal-alpha implementations. It checks complete valid packet coverage, duplicate IDs,
   CSV/response correspondence, input hashes and the accepted-reference source mapping.
   No model runs, package installation or inference are needed.
   Preserve supplied evidence bytes with narrow .gitattributes rules and an archive-builder
   exception. Existing packet/source hash checks accept only Git LF/CRLF variants; label
   mapping is still verified. This prevents platform newline conversion from breaking replay.
3. Reproduce all prior primary reviewer-pair and joint-alpha coefficients at displayed
   precision. Add the previously pending human pair-placement agreement: 14 items,
   92.86% agreement and kappa 0.857143. Pair placement remains a precision subset.
4. Correct the reviewer-reference columns and totals: the newly assigned reviewer 1 is
   the prior summary's second column and reviewer 2 is its first. The scores are not
   newly estimated population outcomes; their association with reviewer identities changes.
5. Identify the reproduced reference as `accepted_answers.csv`, verified against its
   mapped accepted source, not independently verified unchanged blind first-pass AI labels.
   Update captions, appendix, limitations and release descriptions accordingly. Primary
   AI evaluation ownership remains Claude's finalization, as previously instructed.
6. Release an aligned decision audit with original source item IDs, both reviewers' labels,
   pair decisions and the accepted reference. Mark all disagreements/common departures as
   unadjudicated; do not substitute consensus into only reviewed population rows.
7. Update dataset raw-label availability, result declarations and README. Keep all original
   summary JSONs unchanged as historical transcriptions. Record findings in MEASUREMENTS
   before changing the manuscript; C59 explains changed values and unchanged primary scores.

## Commands and publication refresh

```powershell
.venv/Scripts/python.exe scripts/eval/reproduce_reviewer_agreement.py
& 'C:/Program Files/Git/bin/bash.exe' docs/paper/_build/build.sh -disable-installer
.venv/Scripts/python.exe docs/paper/_build/make_release.py
```

No pytest, prior numerical test suite or new annotation/generation run. Only calculate
coefficients from the supplied rows and compile/package the manuscript. Keep main text
on eight pages and Limitations starting on nine; inspect all changed tables. Refresh
named paper/dist PDFs and the Overleaf ZIP before rebuilding the local anonymous archive.
Do not claim the external anonymous mirror was updated. Commit and push the completed work.

## Remaining decisions and executable follow-up

1. Resolve the preserved metadata/authorship conflict with a documented export/protocol
   account; establish whether answers were visible and record reviewer familiarity,
   times and consent/compensation. Coefficients alone cannot supply those facts.
2. Use aligned_decisions_20261010.csv plus questions_only.html to adjudicate conflicts.
   Record the final decision, eligible evidence and rule for each case. Shared departures
   from the reference are candidates for review, not automatically correct ground truth.
3. Map any adjudicated rule change across the comparable population in both conditions
   before recomputing primary precision/citation or recall. Repair gold evidence with
   sufficient eligible paragraphs and an earliest-reveal audit; version changed gold.
4. Independently review disclosure and treated-text samples; they are not in these CSVs.
5. Continue dated prompt-metadata controls and frozen held-out/repeated-run evaluation
   under plan 0020. These require implementation and/or new evidence beyond this import.

Stop criteria: a hash, packet, row-identity, count or reference-mapping mismatch must fail
the reproduction; write the conflict instead of silently relabeling or swapping inputs.
The discovered reviewer-column reversal is explicitly corrected and preserved in the
report's comparison_to_prior_summaries field. No primary system score or gold is changed.

## Publication observations

Both final PDF variants compile to 66 pages with no errors, undefined references/citations
or overfull boxes. Main text ends on page eight and Limitations begins on page nine.
Agreement tables on pages 16-18 were visually inspected. Named paper/dist PDFs and the
Overleaf ZIP are refreshed. The measurement ledger records these observations.
The local anonymous archive is rebuilt with the supplied raw labels and updated source
records. Its existing text scan passes; all six evidence files match the recorded input
hashes both in staged Git blobs and the ZIP. The external mirror is not updated.
All six imported evidence files also match existing remote-branch ancestor d95d307 apart
from LF/CRLF conversion. This import adds explicit reviewer assignments and provenance
records for raw decisions already in the remote history; it does not independently
resolve the accompanying metadata conflict. The ledger records the exact read-only check.
