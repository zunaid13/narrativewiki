# Output quality: NLI verification and arbitration

Status: pending implementation. Scope: Spice and Wolf volumes 1-2 only.

The maintainer's 2026-09-16 continuation prioritizes replacing self-reported confidence after
Zheren's occupation arbitration chose `public witness` over `traveling merchant`.
The detailed earlier plan was found in Claude's saved
`need-you-to-search-structured-pillow.md`; its Stage 3 names local MiniCheck-FT5.

## Reconcile these implementation gaps before claiming Stage 3 complete

- The earlier plan starts with relations only. That cannot fix the newly demonstrated
  **attribute** arbitration bug. Scoring must reach single-valued attribute candidates before
  `graph/contradictions.py::_resolve_single_valued` drops all but its top two candidates.
  Replacing only `_resolve_pair` or post-build verification leaves that loss intact.
- `graph/store.py`'s verdicts table has no numeric score column. Preserve model identity,
  score, evidence/context identity, and threshold explicitly; do not silently overwrite the
  extractor's `confidence` field or describe a generated number as a classifier probability.
- All inference must go through `llm/client.py`, with model selection in `config/models.yaml`.
  MiniCheck's upstream Python API exposes `raw_prob`; use the actual support score.
  See https://github.com/Liyan06/MiniCheck for the backend API.
- PyTorch and MiniCheck were absent from the active Python 3.14 environment on this pass.
  Backend installation/compatibility and a live scored run remain outstanding.
- Preserve cutoff-safe evidence context. Missing backend/context must not become a successful
  verdict, an invented score, or a silent fallback to extractor confidence.
- Test against fixed claim inputs before resynthesis: include Zheren's competing occupations,
  the known false relations, and clean supported controls. A nonzero flag count alone is not
  evidence of better accuracy. Do not change gold/baseline numbers to manufacture a pass.

## Work completed in the continuation

`gazetteer --series spice-and-wolf --volumes 1-2 --merge-epithets` processed 150 mentions,
adding 59 surface forms and rebuilding 4,689 mentions. No extraction was rerun.

Stage 0.3's initial-request context sizing is implemented. Offline reproduction:
`python scripts/eval/replay_context_budget.py`. Its checked-in JSON records input hashes and compares
the old request sizing with the new splitter using empty model responses, not inferred facts.
Under `local_fast`'s 16,384-token context, estimated over-budget requests fall from 8 to 0 in v1
and 7 to 0 in v2; requests increase 117 to 131 and 245 to 254. No selected paragraphs are lost.
This does not measure model-tokenizer accuracy, repair retries, fact yield, or recall improvement.

Stage 2.2's premise is stale: `eval/gold.py::_relationship_entry_keywords` already checks
affiliations by entity ID and membership synonyms independently of their missing display label.
No label/schema change was made merely to satisfy that obsolete premise.

Validation: 110 focused tests across extraction, adequacy, spoiler safety and provenance pass.
The sandboxed test run hit Windows temporary-directory permissions; the identical focused run
passed outside the sandbox. No live LLM calls, graph rebuild, synthesis, or new recall score.

Maintainer/Claude follow-up: fold this progress into the protected planning/log documents.
