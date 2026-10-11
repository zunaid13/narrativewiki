# Phase 34 — System version 2: the red-flag fix batch and rebuild

## 2026-10-04 — Requirement: fix the version-1 defects before spending further, then rebuild B5 and B4

Maintainer, 2026-10-04: after seeing the "Anne" / "Anne Shirley" split on Gilbert's page ("isn't not
merging anne and anne-shirley a huge negative?"), asked for every other red flag and then: "do it. fix
it", with permission to stop the runners and change the frozen code, and "do not directly delete
cache (instead just rename it ... we dont want to lose ability to backtrack)".

Decisions:
- Version 1 is kept whole for comparison: data and wiki trees untouched, git tag `prefix-v1-20261004`;
  version 2 is built as variant series (`anne@v2`, `oz@v2`) reading the same parsed text.
- Scope of the fix: OPEN_GAPS G1, G2, G5-G12 (docs/eval/CHANGES.md C31). Mary (one bare name, two
  people, no full name mined for either) and epithet-step merges ("Billy Booth" on Billy Andrews) are
  not addressed by this batch and are reported.
- Order: code + tests -> $0 gate (gazetteer rebuild, cached, plus the merge audit) -> billed rebuild of
  B5 and B4 -> re-score -> paper reports version 1 and version 2 side by side.
- Anne is no longer an untouched test work for version 2 (its defects were found by reading its
  results); the paper says so. A truly held-out claim needs a work nobody has read results for.

## 2026-10-07 — Requirement: human review accepted; finish every model call and local job, then the paper

Maintainer, 2026-10-07: "human checked your review and has decided your labels are fine. write the handover
files. the doubts seem ok just pickk the ones best suited by your knowledge and internet search. For now just
complete all the AI calling, local ollama work and once everything is done, start working on the paper".

Decisions (the agent's, under that delegation; reasons in `docs/eval/human_check/HUMAN_REVIEW.md`):
- The accepted label set of the 554-item check is `docs/eval/human_check/final_labels.csv`. It is a human
  review that accepted AI labels, not a blind annotation; the paper says so and reports no human-AI agreement.
- Recall counts full support only (a weaker statement is `no`), applied to every system by one test per fact
  (CHANGES C43). A gold fact dated by an announcing paragraph is `partly` established and keeps its cutoff.
- Order of work: the decontaminated matrix and its local scoring to the end, its labels, then the paper.
  Nothing in the paper is edited before the last billed and local job has finished.
- Not done: Oz and the other series stay out of scope (2026-10-05 entry of the paper-scope decision).

## 2026-10-08 — Construction dependence gets a metric; entity discovery is run per prefix

Maintainer, 2026-10-08: "Construction dependence has no metric. A reviewer will ask why entity discovery is not
run per prefix, as your LightRAG baseline's index is. Start the run" (review 6.3 and DA4 of
`docs/paper/REVIEW_2026-10-08.md`).

Decisions (the agent's):
- Entity discovery is the only stage that reads the whole series, so it is the stage rebuilt: the v2 gazetteer
  from volumes 1..t alone for t=1..4 (`wiki gazetteer --gate build`, runner
  `docs/eval/runners/prefix_gazetteer.sh`), written beside the full build under `data/anne@v2/@t<NN>/`.
  Nothing built is replaced; t=5 is the full build itself.
- The metric is **identity dependence**: the share of the full build's characters visible at t whose set of
  surface forms seen by t is not the set a prefix-built character has (`scripts/eval/identity_dependence.py`,
  $0), split into regrouped, retyped and absent, over all characters and over those with a page at t.
- The original text first (the smallest slice that answers the question); the treated text only if the result
  calls for it. No extraction, graph or page is rebuilt on the prefix indexes: the question asked is how far
  the two indexes differ, and the earlier prefix builds (t=2, 3) already compare pages.

## 2026-10-11 — Requirement: a version-2 paper that frames NarrativeWiki as a probe

Maintainer, 2026-10-11 (reviewer guidance pasted): (1) the framing presents NarrativeWiki as a solution
while the long-context baseline beats it, so rewrite the abstract and introduction around NarrativeWiki as
an analytical probe of what decomposing a novel into a graph costs (modality collapse, identity effects);
(2) expand the renamed-text (decontamination) experiment and move it to the front of Results.

Decisions (the agent's):
- Version 2 is a second entry point, `docs/paper/main_v2.tex`, not a copy of the paper: it shares
  `results.tex`, tables, figures, appendices and sections 3-5 with `main.tex`, so no number can drift between
  the versions. Only `sections_v2/` (abstract, introduction, results, discussion, conclusion) is new; four
  shared files branch on `\ifdefined\nwvtwo`. Version 1 builds byte-for-byte the same text as before.
- No new measurement. Every figure in version 2 is an existing `\res` key; nothing was rerun or relabelled.
- The reviewer's wording was not adopted where the ledger does not support it. "Soundly defeated by B1":
  on the treated text recall is tied (0.843 vs 0.845) and the probe's citation sufficiency is higher than
  B1's (0.625 vs 0.530); what holds in both conditions is lower precision and the only prefix-side
  disclosures. "Definitively separates reading from memorization": the control bounds closed-book recall
  (0.683 to 0.003) but does not apportion any system's original-text score (one build, residual recognition
  0.110 by title, 0.195 by author). "We built it to demonstrate": the system was built as a product; the
  paper says it is *used* as a probe. "Identity contamination" is printed as "identity dependence", since
  "contamination" already names training-data recognition in this paper.
- Main text is held to 8 pages by printing the original-only comparison table and the cutoff illustration
  in the appendix (version 2 only); the paired original/treated table is the single main-text table.
