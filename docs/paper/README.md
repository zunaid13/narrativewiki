# NarrativeWiki paper

`main.tex` is the entry point. `NarrativeWiki-paper.pdf` is the only PDF kept here: the
anonymous reading copy without line numbers. The line-numbered review PDF is a build output
(`_build/submission.pdf`), not a stored file.
The source includes the complete paper, references, and appendices.

The current title is **Evaluating Character Wikis at Reader-Selected Narrative Cutoffs**.
The task, evaluation protocol and pilot dataset are the contribution; NarrativeWiki is the
reference implementation. The corpus appendix now consolidates source size, primary-matrix
annotation counts, an existing YAML record, easier and harder examples, and an evidence
boundary case. Counts and provenance are in `../eval/dataset_card_20261010.json`.
The annotation examples explain existing labels rather than adding a difficulty-graded split.
This editorial pass runs no tests or new generation, as requested by the maintainer.

## Build

On Overleaf, select `main.tex` and the pdfLaTeX compiler.
Locally, use a LaTeX distribution with pdfLaTeX, BibTeX, and latexmk:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The ACL style and bibliography style are included. Standard LaTeX packages are
required, including TikZ, `tcolorbox` with its breakable/listings/skins libraries,
and `needspace`. Python is not required to compile the paper.

## Files

- `sections/`, `appendix/`, and `tables/`: manuscript sources.
- `figures/`: vector figures, editable TikZ diagrams, and required screenshots.
- `macros.tex` and `results.tex`: shared formatting and reported measurements.
- `refs.bib`, `acl.sty`, and `acl_natbib.bst`: references and ACL styles.
- `REVIEW_NOTES.md`: outstanding empirical and pipeline work for the authors.

The default build includes review line numbers. Its main text ends on page 8,
and Limitations starts on page 9. Build artifacts, previews, older assets, and
local helper scripts are omitted from the Overleaf ZIP.

## Local repository build

The manuscript was refreshed from `narrativewiki-overleaf_updated.zip` on 2026-10-10.
The repository also retains its build helpers, review records, and older assets.
The ZIP's supplied PDF is retained locally as `_build/overleaf-reference.pdf`.

From the repository root, build both PDF variants with:

```sh
sh docs/paper/_build/build.sh              # reading: _build/main.pdf; review: _build/submission.pdf
# On MiKTeX, pass -disable-installer to prevent automatic package installation.
python docs/paper/_build/overfull.py
python docs/paper/_build/emptykeys.py
.venv/Scripts/python.exe docs/eval/labelling_tools/derived_values.py
```

After checking the output, copy `_build/main.pdf` to `NarrativeWiki-paper.pdf` in this folder.
Keep no second copy; take `_build/submission.pdf` only when uploading for review.
`\nwreading` disables line numbers; a direct `main.tex` build retains them.

The 2026-10-10 human-review update adds the supplied two-reviewer agreement table in
`tables/t-human-agreement.tex`, with provenance in
`../eval/agreement/human_review/reported_agreement_2026-10-10.json` and the measurement ledger.
The earlier visible-answer acceptance pass and the later separate human labels are described
separately. Agreement is now recomputed from the supplied final reviewer CSVs, with corrected
reviewer identities and an added pair-placement result. Reviewer-reference comparisons and
joint nominal alpha use the accepted AI-assisted review snapshot, not a verified blind
first-pass baseline. Sources are `../eval/agreement/human_review/recomputed_agreement_20261010.json`
and its provenance manifest. The original screenshot transcriptions are preserved.

Correction 2026-10-11 (maintainer): both reviewer label sets are entirely human-produced, and
each reviewer labelled from scratch without seeing the AI answers. The earlier statements that
accompanying archival metadata described model runs, and that blinding was unconfirmed, were
wrong and are removed from the annotation, corpus and reproducibility appendices and from
Limitations.

The subsequent reviewer-concern audit attributes all reported AI labels to Claude's final
review, distinguishes propagated recall corrections from unresolved precision/citation
review disagreements, and qualifies early-prompt identity exposure. Disclosure aggregates
include B4; `tables/t-disclosure-units.tex` reports unique subject facts separately from
repeated fact-cutoff assessments. Reproduce and validate these counts without model calls:

```sh
python scripts/eval/disclosure_units.py --output docs/eval/disclosure_units_20261010.json --fill-paper
.venv/Scripts/python.exe docs/eval/labelling_tools/derived_values.py
```

Outstanding empirical repairs and their stop criteria are recorded in
`../vision/plans/0020-reviewer-concerns.md`.
The updated Overleaf ZIP includes these repairs and the current review PDF as `main.pdf`.

Reproduce the supplied-data agreement and aligned disagreement audit without model calls:

```sh
.venv/Scripts/python.exe scripts/eval/reproduce_reviewer_agreement.py
```

Plan `0022-human-label-reproduction.md` records the import, reviewer-column correction,
reference identity and remaining adjudication work. No test suite or experiment is rerun.

## Version 2 (probe framing, 2026-10-11)

`main_v2.tex` is a second entry point: **NarrativeWiki: Probing What Decomposition Loses in
Graph-Built Character Wikis at Reader-Selected Narrative Cutoffs** (title set by the maintainer,
2026-10-11). NarrativeWiki is presented as an analytical probe of
graph decomposition, and the renamed-text control (treated text) opens Results. It shares
`results.tex`, `macros.tex`, tables, figures and appendices with `main.tex`; its whole main text
and its Limitations are its own, in `sections_v2/` (since 2026-10-12, after the pre-submission
review: every caveat is stated once, in `sections_v2/limitations.tex`, which carries no numbers).
Shared files that differ between the versions branch on `\ifdefined\nwvtwo`. Version 2 prints
Table `tab:main` and the cutoff illustration in the appendix so that the main text ends on page 8.
Every appendix is two-column (ACL formatting guidelines). It reports no new measurement.

```sh
NW_MAIN=main_v2 sh docs/paper/_build/build.sh   # _build/main_v2.pdf and _build/submission_v2.pdf
```

Copy `_build/submission_v2.pdf` (the build with the review line numbers ARR requires) to
`NarrativeWiki-paper-v2.pdf`. The teaser image has no editable source;
version 2 uses `figures/f0-teaser-v2.pdf`, the teaser with its right-hand heading ("Our solution:
NarrativeWiki") and its badge ("No spoilers") removed from the PDF text layer
(`scripts/papers/redact_teaser_v2.py`), and re-letters both with a TikZ overlay in
`sections_v2/01-introduction.tex`. Version 1 keeps `figures/f0-teaser.pdf`.

After any edit, check the limits on the line-numbered build (abstract at most 200 words, main text
ending on page 8):

```sh
.venv/Scripts/python.exe scripts/papers/check_paper_limits.py docs/paper/_build/submission_v2.pdf
```
