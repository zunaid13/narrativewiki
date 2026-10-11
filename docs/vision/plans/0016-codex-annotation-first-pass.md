# Codex annotation first pass

Status: complete AI first pass (2026-10-05); human verification pending. Requested by maintainer: "you will annotate everything first. a human will verify later".

## Scope and evidence

Read `docs/eval/human/INSTRUCTIONS.md`. Annotate Part A and Part B from the supplied blinded package without reading `key.json`. Audit the five existing `docs/eval/recall_hand/anne@v2_v<t>.json` files against their rendered cutoff trees. Label every row of the initially available main-system precision samples. The cutoff-5 all-surface sample and `anne@b4-v2_v1_all.jsonl` appeared during the pass and were added before reading; the manifest freezes this collection. Do not resample or rebuild the frozen wiki. Use only Anne volumes 1–5 and deterministic local readers; no model/provider calls.

The package instructions require two independent human readers for the human study. This pass is an explicitly attributed AI pilot authorized by the maintainer, and does not satisfy that requirement. Keep packet answers outside the human scorer's input folder. Preserve source labels and screen verdicts as evidence, never use the screens as annotation decisions.

## Method and files

1. Save input hashes and previous recall labels under `docs/eval/agent_annotation/2026-10-05/`.
2. Read every packet item, following its supplied evidence boundary. Record A support, pair participation, citation-only sufficiency and a reason; record B stated/implied/neither/cannot tell with a reason.
3. Read each precision atom against cited passages and eligible source text. Record factual atom support separately from page placement, and citation sufficiency separately from factual correctness. Inspect unclear speaker/identity context, pair participation, uncited timeline scenes and atomization errors directly. Preserve prior fields and add explicit `reader` / `cite_reader` AI attribution and page hash.
4. Recheck every recall fact against current pages. Apply the uniform core-proposition rule in `docs/eval/recall_hand/anne.provenance.md`; keep per-fact witnesses and changes in the audit artifact. Preserve original recall files and export proposed labels beside them for human comparison.
5. Validate row coverage, allowed verdicts, evidence cutoff, input/page hashes and explicit provenance. Append measured results to `docs/MEASUREMENTS.md` and annotation changes to `docs/eval/CHANGES.md`. Commit only this work.

Commands and progress are recorded in the annotation README and manifest. Source reading helpers live in `docs/eval/agent_annotation/`, keeping the running pipelines' frozen `scripts/`, `src/` and `config/` untouched.

## Validation and stop criteria

Every supplied row receives a reasoned verdict; unresolved evidence produces an explicit uncertain/cannot-tell verdict rather than a guessed binary. Verify no input page changed while annotating. Human labels, human agreement statistics and paper human-study switches remain pending human verification. Do not open the answer key, invoke API calls, or extend to not-yet-ready decontaminated/supplement packets.

## Remaining work

Packet A/B, all collected precision samples, recall audit and coverage/file verification are complete. Results, reproducible commands and limitations are in `docs/eval/agent_annotation/2026-10-05/README.md`, `validation.json`, `manifest.json` and the measurement ledger. Later human verification and not-yet-ready/later-generated inputs require a separate pass.
