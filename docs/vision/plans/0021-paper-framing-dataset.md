# Paper framing and evaluation dataset documentation

Status: completed editorial pass; PDFs, Overleaf package and local anonymous archive refreshed. Empirical follow-up remains open. No tests or experiments rerun.
Date: 2026-10-10. Run id: `paper-framing-dataset-20261010`.

## Authorization and checkpoint

The maintainer asked to push before any work, make remaining feasible fixes, document dataset
size and explained easier/harder samples, and correct framing/claims without rerunning tests.
The working tree was clean at `08bd2d1`; `git push origin phase-26-citable-pages` reported
everything up to date before any edit. No empty checkpoint commit was created.
The explicit instruction to skip tests supersedes the standing focused-test default for
this editorial pass. No pipeline stage, model call or annotation rerun is authorized by it.

## Evidence and reading

Read the current title, abstract, introduction, task definition, setup, results, discussion,
conclusion, ethics, corpus appendix and release description; inspected the gold YAML,
stored source paragraphs for selected examples, and the existing accepted gold-evidence
check. Existing corpus totals were already in the ledger and paper. The missing material
was a consolidated dataset description, its annotation populations, a serialized sample,
and explanation of direct versus more involved cases.

The selected gold file is `docs/eval/parametric/anne.yaml`, not the older development harness
under `docs/eval/gold/`. Evidence identifiers select volumes 1-5 only. Historical later-volume
entries remain excluded from this paper. All new record counts and example observations
are appended to `docs/MEASUREMENTS.md` before result declarations or prose. No new research
method is introduced; no paper findings or external source verification are inferred.

## Applied changes

1. Title: **Evaluating Character Wikis at Reader-Selected Narrative Cutoffs**. Abstract,
   contribution order and conclusion emphasize the task, evaluation protocol and pilot
   dataset; NarrativeWiki is the reference implementation. The method heading follows this.
2. Replace the closed-book diagnostic's unqualified memory-only cause with its actual
   title/name inputs and observations without source text. Restrict comparative advice
   to this pilot; do not claim causal isolation of construction, retrieval or generation.
   The figure caption marks cutoff safety as the design target rather than an observed guarantee.
   Correct the remaining treated-table caption to report Claude as the final AI annotator
   in both conditions; it still carried the superseded attribution after the prior edit.
3. Corpus appendix: retain per-book size information, add primary-matrix record/judgment
   populations, distinguish repeated cutoff judgments from independent facts, and explain
   that treated text reuses the inventory and does not add an independent corpus.
4. Samples: minimal actual Matthew YAML record and direct supporting text; Owen's
   occupation-plus-grandson conjunction and local pronouns; Anne's wedding-day evidence
   as a paragraph-sufficiency boundary. Reuse the existing accepted labels; no new
   easy/hard split or human decisions are asserted.
   Gold records are described as selected statements rather than all being atomic:
   some contain conjunctions. The sampled precision unit remains an atomic assertion.
5. Separate the earlier human-review subset from the current complete matrix. Clarify
   release contents as AI labels, packets and supplied agreement summaries, with the raw
   two-human decisions unavailable. Describe prompt templates and exchange excerpts rather
   than implying full raw runtime prompts are distributed. Update release README consistently.

Changed files: relevant manuscript sections, main title, appendix contents/corpus/release,
`tables/t-dataset-size.tex`, `figures/f3-systems.tex`, dataset result declarations,
`docs/eval/dataset_card_20261010.json`, ledger, change log, author notes, paper README,
`_build/make_release.py`, this plan and the framing status in plan 0020.

## Reproducing stored-data counts (no model call)

The following counts the primary matrix only, not earlier/prefix-build diagnostics:

```powershell
@'
import json
from pathlib import Path
for base in ['anne', 'anne-decon']:
    cells = recall = disclosure = samples = frame = 0
    for tag in ['b1', 'b2', 'b3', 'b4-v2', 'v2', 'x1', 'x2']:
        for t in range(1, 6):
            p = Path(f'docs/eval/precision/{base}@{tag}_v{t}_all.jsonl')
            rows = [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
            cells += 1
            samples += len(rows)
            frame += sum(r.get('human') == 'frame_error' for r in rows)
            p = Path(f'docs/eval/recall_hand/{base}@{tag}_v{t}.json')
            recall += len(json.loads(p.read_text(encoding='utf-8')))
        p = Path(f'docs/eval/leak_audit/{base}@{tag}_tree.jsonl')
        disclosure += sum(bool(s.strip()) for s in p.read_text(encoding='utf-8').splitlines())
    print(base, cells, recall, disclosure, samples, frame, samples - frame)
'@ | .venv/Scripts/python.exe -
```

Gold selection and its exact count command are in the new ledger row. The card records
the selected gold's SHA256 and example evidence IDs. Corpus totals reuse T1 keys rather
than re-deriving input counts. Reviewer counts reuse the supplied original-text summary.

## Publication refresh and stop criteria

Compile the final paper once to refresh artifacts; no pytest, numerical test suite or new
generation. Keep the abstract within its stated word limit and the main text within eight
pages, with Limitations beginning on page nine. Inspect the new dataset table and sample
layout. If a layout defect requires an edit, fix only that defect and recompile; do not
broaden checks into experiments. Refresh named reading/review PDFs, existing dist copies,
the current Overleaf ZIP and the local anonymous archive. Do not touch an external mirror
working tree or claim that its remote content was updated. Commit this work and push.

Remaining empirical fixes in plan 0020—blinded adjudication, gold-evidence repair, dated
prompt metadata, independent disclosure coverage and frozen held-out/repeated-run
evaluation—remain open. Wording and documentation do not supply their missing evidence.

Final reading and review PDFs compile to 66 pages with no LaTeX errors, unresolved
references/citations or overfull boxes. Main text ends on page eight and Limitations
starts on page nine. The dataset table and examples on page 18 were visually inspected.
Named paper and dist copies and the Overleaf package are refreshed. The ledger records
these typesetting observations; no tests, model calls or empirical reruns occurred.
The local anonymous archive was regenerated with its revised README and current materials;
the existing text scan reports no local path, user name or institution string. Its external
mirror was not updated. The archive's packaging observation is appended to the ledger.
