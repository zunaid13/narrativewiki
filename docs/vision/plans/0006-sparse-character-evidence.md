# Recover supported evidence for sparse character pages

Updated: 2026-09-23. Status: research and implementation plan; production work pending.
Scope: Spice and Wolf, volumes 1–2 only. No package installation or model training proposed.
Maintainer request: research uncertain next steps and leave an implementation plan others can resume.

## Start here

1. Read `CLAUDE.md`, then the relevant contracts. This file supplements the project map.
2. Check `git status` and the ledger's scene-evidence sections before assuming artifacts are unchanged.
3. Implement **Work package A**, the offline evidence coverage report and reviewed fixture.
4. Then separate the existing probe's bundled prompt changes into controlled variants (package B).
5. Do not execute the external comparison until the pending passage-transfer approval is resolved.
   Approval to push to GitHub was received; it is not approval to send passages to Vertex.

Existing reproducible commands (repository root, PowerShell):

```powershell
python scripts/eval/replay_scene_facts.py --run-id 20260922T211717-scenes-v1-2
python scripts/eval/probe_sparse_scene.py
python -m pytest tests/test_sparse_scene_probe.py tests/test_adequacy.py tests/test_extract.py tests/test_scenes.py tests/test_spoiler_leak.py -q -p no:cacheprovider
```

The replay makes no model calls. The probe without `--execute` only prepares inputs. None of these
commands regenerates the live wiki. Stored source logs must exist locally; they are gitignored.
If they are absent, recover the recorded artifacts from the maintainer rather than generating
replacement data and calling it the historical baseline.

## Problem and established evidence

The durable evidence is in [MEASUREMENTS §§3, 7–8](../../MEASUREMENTS.md), with commands and run IDs.
Do not copy new measurements here without adding ledger rows first.

- The last measured character-page spread is **21.4×**, from **70 to 1,497 words**. This is a
  symptom, not a validated target ratio; different characters legitimately have different amounts
  of source information. Reducing the ratio by padding stubs or truncating leads is not success.
- Recorded scene output contains **118** fact observations; current gates accept **86**, merging
  to **40** claim IDs that exactly match persisted scene claims. Repetition accounts for much of
  the low unique yield. Use the ledger's **corrected** first-failure breakdown, not its earlier row.
- Neither saint has proposed scene facts in that recording. However, Ruvinheigen's window-pass
  evidence already reaches his appearance section. Adding the same facts through scenes may add
  provenance but does not establish more page information.
- Subject-name prompt/config alignment was corrected in `970b997`; fresh-output improvement is
  unmeasured. The stored historical response predates that change.
- The scene detail user instruction omits `participant_facts`, while the system prompt requests
  them. This is a plausible omission mechanism, not a demonstrated cause.
- The isolated probe and tests are in `8402e20`. Its candidate changes several instructions at
  once: output families, offstage characters, and epistemic wording. It cannot attribute a gain
  to any one of those changes without ablation.

Artifacts already available:

| Purpose | File |
|---|---|
| Per-fact gate replay, rejected witnesses, input hashes | `scripts/eval/replay_scene_facts.py`, `docs/eval/scene_facts_spice-and-wolf.json` |
| Prepared single-passage comparison | `scripts/eval/probe_sparse_scene.py`, `docs/eval/sparse_scene_prepared.json` |
| Historical source | `data/spice-and-wolf/_runs/20260922T211717-scenes-v1-2/calls.jsonl` |
| Failed live attempt | `data/spice-and-wolf/_runs/20260923T130243-sparse-scene-probe-v2-c0-one-span/` |
| Existing source/graph/page shapes | `docs/CONTRACTS.md` §§1–5 |

The failed attempt produced no response and recorded no spend. The sandbox proxy refused OAuth;
automatic approval review then rejected escalation pending explicit permission for this passage
transfer. There is no measured candidate winner and no justification for a full rerun yet.

## Research consulted and what transfers

Checked on 2026-09-23. These are **references, not applied methods**. Links are primary sources.
Reading depth is explicit; no claimed paper performance is a measurement of this repository.
No PDFs were added, so this does not change the PDF inventory in `PAPERS.md` or `REFERENCES.md`.

| Source | What was checked | Relevant idea and implementation limit |
|---|---|---|
| Gurung & Lapata, **CHIRON: Rich Character Representations in Long-Form Narratives**, Findings EMNLP 2024 ([paper](https://aclanthology.org/2024.findings-emnlp.499/), [PDF](https://aclanthology.org/2024.findings-emnlp.499.pdf)) | Abstract, architecture, generation/validation sections and atomic-claim discussion | Character-focused questions generate candidates, followed by validation of individual statements. Adapt category-specific extraction questions to existing predicates and gates. Their trained narrative entailment model is not equivalent to our current verifier; do not claim reproduction or install/train it by default. |
| Papoudakis, Lapata & Keller, **Think Before you Write: QA-Guided Reasoning for Character Descriptions in Books**, April 2026 preprint ([versioned paper](https://arxiv.org/html/2604.11435v1), [metadata](https://arxiv.org/abs/2604.11435)) | Abstract, introduction, QA formulation and reported limitations | Separates structured QA from final description generation. Use short evidence-bearing answers as candidate facts, not free-form prose passed straight to pages. Its training setup and results do not establish that a prompt-only adaptation will work here. Avoid treating generic reasoning mode as an automatic improvement. |
| Wang et al., **FACT: Examining the Effectiveness of Iterative Context Rewriting for Multi-fact Retrieval**, Findings NAACL 2025 ([paper](https://aclanthology.org/2025.findings-naacl.188/), [PDF](https://aclanthology.org/2025.findings-naacl.188.pdf)) | Abstract and method/results discussion | Multi-fact retrieval may miss items in one pass; iterative attention to remaining evidence is worth a bounded experiment. Do not rewrite source paragraphs or cite a generated rewrite. Here, any iteration must revisit immutable original paragraphs with a narrow unanswered question and preserve their IDs. |
| Singhania, Razniewski & Weikum, **Recall Them All: Retrieval-Augmented Language Models for Long Object List Extraction from Long Documents**, 2024 ([primary preprint](https://arxiv.org/abs/2405.02732)) | Abstract only | Separates recall-oriented candidate generation from precision-oriented scrutiny. This supports testing a targeted proposal stage, not weakening acceptance. Long object-list extraction differs from narrative traits and reported legends; read the full method before adopting retrieval details. |

**Working hypothesis, not an established finding:** a bounded character-and-category extraction
request may recover useful evidence that an all-character scene request overlooks. The first
experiment should test this with existing source passages and validators, not change the model,
increase every context window, or rewrite every page.

## Work package A — offline diagnosis and a reviewed source fixture

Proposed files: `scripts/eval/character_evidence_coverage.py`,
`docs/eval/fixtures/sparse_character_evidence.json`, `tests/test_character_evidence_coverage.py`.
These files do not exist yet. Keep the initial report offline and separate from production CLI.

Read through `paths.py` accessors: parsed records, gazetteer, mentions, both claim producers,
read-only graph, page JSON and emitted Markdown. Restrict every input to the selected cutoff.
For each visible character report:

- Source mention paragraphs and selected/sent paragraph IDs, with request provenance when present.
- Raw scene proposals, first rejection reason, accepted observations and unique claim IDs.
- Existing window claims, scene claims, their union, graph retention and page-section evidence.
- Explicit missing/stale input indicators. Never turn an unavailable recording into a zero count.
- Page length and section presence, with one documented counting method and hashed artifacts.
  Reproduce the old ledger's count if possible; otherwise label the new definition separately.

Produce a witness table that locates loss: source absent; retrieval missed; no proposal; rejected;
merged with existing fact; lost at graph arbitration; available but unused by synthesis. The last
two require inspecting actual IDs/evidence, not inferring loss from a short page.

Source review must label atomic facts with subject, predicate family, polarity, exact paragraph
and quote, cutoff, and `already_covered` versus `missing`. Include supported and unsupported cases:
reported history, ambiguous pronouns, unmentioned subjects, hypothetical events and legitimately
empty categories. Start with the saints and a sparse speaking character selected by the report;
use an adequately covered character as a control. Ruvinheigen's already-rendered red hair is a
deduplication control, not a novel-fact success. Do not use fandom pages as additional evidence.

Keep this fixture separate from the existing gold benchmark and its floors. Freeze it before
new outputs are inspected, and retain a held-out passage so prompt edits are not evaluated only
on the example used to design them. Tests should demonstrate cutoff filtering, missing-input
errors, repeated observations versus unique facts, and passage-only name resolution.

**Exit:** each targeted deficit has a reproducible witness and a source-review label. If there
are no missing supported facts in a character's available text, record that and preserve the stub.

## Work package B — controlled prompt comparisons

Extend `scripts/eval/probe_sparse_scene.py` and `tests/test_sparse_scene_probe.py`.
Keep prepared and completed reports separate; checkpoint results and hash code, effective
configuration (including any series overlay), source bytes, prompts and generation options.

Freeze passage IDs, entity index, effective configuration, model route and generation settings.
Compare sequentially, stopping when no meaningful gain justifies another experiment:

| Variant | Change | Purpose |
|---|---|---|
| B0 | Current production system and user prompts | Actual baseline; historical output is context only |
| B1 | Add only `participant_facts` to the final user instruction | Isolate the missing-output-family hypothesis |
| B2 | B1 plus explicit coverage of characters discussed offstage/in history | Isolate the offstage-character hypothesis |
| B3 | Character/category question with existing fact schema and gates | Test QA-style decomposition only if simpler variants miss reviewed facts |

Reuse the cached B0 response across comparisons. Do not mix the older historical system prompt
with current candidates and label it a controlled A/B. B3 should invoke the existing character
extraction machinery, not invent another unvalidated claim builder. No fact or section quotas.

After external-transfer approval, use the prepared executable command only for the variant set
actually implemented and reviewed:

```powershell
python scripts/eval/probe_sparse_scene.py --execute
```

Explain why cached outputs/fixtures no longer answer the question before making paid calls.
All inference stays behind `LLMClient`, configured roles, existing budget caps, and run provenance.
No local/backend substitutions to bypass an approval rejection.

**Decision metric:** manually supported, semantically new facts reaching the relevant character,
not raw accepted count. Claim-ID novelty alone is insufficient: paraphrases can have new IDs.
Compare against both existing extraction sources and the current graph. Report facts per
character/category, unsupported additions, preserved polarity/cutoff, deduplicated gain and cost.
Local support scores may assist review but are not gold labels or proof of entailment.

**Stop/reject:** no new supported information; gains only on the development passage; harmful
misattribution/polarity change; loss of a reviewed existing fact; unavailable validation evidence;
or an unapproved/failed provider request. Write the result, including a rejected hypothesis, to
the ledger. Do not tune benchmark floors to disguise regression.

## Work package C — bounded targeted top-up, only after evidence of benefit

This is a candidate design, not an instruction to implement it ahead of A/B.

- Reuse `extract/claims.py::extract_character_volume` and `_build_claim`; scene-only changes belong
  in `extract/scenes.py::_detail_user_prompt`. Keep evidence/polarity gates unchanged.
- Add a planner (proposed `extract/topup.py`) that accepts a cutoff, target character/category,
  reviewed candidate paragraph IDs, and already accepted claims. Use paragraph windows already
  available from `extract/windows.py`; preserve scene boundaries and context-fit behavior.
- Preserve `extract_volume`'s full-roster cap allocation when calling a subset. A target-only
  roster must not change its evidence budget. Do not increase caps without observing truncation.
- The first prototype performs one targeted round on one category and stored passage set.
  This is a proposed limit, not a measured optimum. Stop if it finds no new supported fact.
  Consider another bounded round only after recording marginal gain and checking remaining source.
- Candidates retain standard claim shape, verbatim evidence, `first_vol`, polarity and source.
  Questions/answers are diagnostic artifacts; they never populate page fields directly.
- Store top-up outputs separately first. If integration is justified, add a canonical path in
  `paths.py`, document that artifact in `CONTRACTS.md`, then extend graph input collection and
  claim-ID evidence merging explicitly. Update snapshot/rollback inputs at the same time.
  Never replace an entire volume's claims with a targeted subset.
- Check exact duplicates before calls and exact/semantic equivalence afterward. Do not collapse
  distinct polarities, temporal changes, or qualifiers merely because wording is similar.

No corpus-wide coreference system, fine-tuning, embedding replacement or extra verifier is needed
to test this hypothesis. Research those only if labeled failure cases show the current mechanism
is the bottleneck. The separate NLI task `0005` is not silently completed by this plan.

## Work package D — confirmation and downstream evaluation

A small-slice winner is provisional. Preserve immutable starting snapshots and run IDs before
production changes. Compare baseline/candidate from matching source, gazetteer and cache state;
do not compare a candidate after epithet merging against a baseline before it. Keep the response
cache intact. Check that no artifacts beyond allowed volumes are in the active series inputs.

Follow `docs/handover/PHASE_28.md` §6 for the confirmation stage order: gazetteer → scenes →
epithet merge → extract → graph → verify → events → synthesis → site. Then run focused audits,
gold evaluation and cutoff probes. That sequence can bill; state why a full confirmation is now
necessary and preserve its provenance. Read the actual CLI help before execution if flags changed.
Do not copy `--allow-partial` blindly: the handover's historical explanation differs from today's
Metrogius page, so diagnose the actual missing character/claims guard before using it.

Use focused tests for modified modules plus spoiler invariants. Add integration tests for top-up
merge preservation, duplicate evidence union, cutoff filtering and rollback if C is implemented.
Do not run the full suite by default. Record all observations, costs and commands in the ledger.

Publish a per-character before/after: supported unique facts, missed reviewed facts, section fill,
new unsupported facts, and the page-length distribution. Explicitly permit a short page when its
source supports little. Page-length ratio alone cannot establish fandom-quality improvement.

**Promotion requires:** supported novel evidence survives into the correct cutoff page; no reviewed
precision, polarity or spoiler regression; focused checks pass; the full confirmation supports
the small experiment; commands/artifacts/limitations are recorded. Otherwise retain the current
pipeline and record the rejected candidate, without repeatedly billing to chase a favorable run.

## Unresolved decisions and continuation log

- **STATUS default conflict:** configuration and CONTRACTS U6 authorize inferred `alive`; the
  current zero-evidence rule conflicts with rendering that as fact. The ledger records the
  saints' witnesses. Obtain an explicit decision before changing this behavior. A proposed
  resolution is to omit unsupported status, not infer death for historical figures. This can be
  handled independently and must not be presented as an evidence-recall gain.
- **Passage transfer:** the Vertex comparison still awaits the requested explicit approval. The
  maintainer's research-workflow instruction does not answer that earlier question. Offline A/B
  preparation and package A remain available without it.
- **2026-09-23:** researched the sources above, saved this plan, and added the standing workflow
  to `AGENTS.md`. No new provider call or production change in this planning step.

When resuming, append date, completed package, commit, source/run IDs, acceptance result, and the
next exact action here. Keep active work in `docs/vision/plans/`; Codex must not update protected
`CLAUDE.md`, `LOG.md`, `VISION.md`, or phase vision/handover records.

- **2026-09-23 (later), package A complete, $0.** `scripts/eval/character_evidence_coverage.py` now
  runs at both cutoffs; fixture frozen at `docs/eval/fixtures/sparse_character_evidence.json`;
  `tests/test_character_evidence_coverage.py` binds it to the corpus and graph. Numbers in
  [MEASUREMENTS §10](../../MEASUREMENTS.md). Source runs unchanged (`20260922T211717-scenes-v1-2`,
  `20260922T212119-extract-v1-2`); no artifact regenerated; budget still $5.49.
  **The witness table closes three of its own hypotheses.** No mention paragraph of any character
  failed to reach a recorded request at either cutoff, so "source absent" and "retrieval missed"
  are out. Claim→active-interval retention is high, so arbitration is out. And the report was
  keyed on `subject` alone, which called inbound relationship facts missing when they already
  render — `inbound_claims` fixes that, and it changes how any B/C gain must be counted.
  **Two findings outrank the remaining plan.** `wiki verify` had already caught 3 of 3 precision
  errors the hand review found, withholding 14/349 intervals and a larger share of sparse
  characters' claims than of leads'. And page length tracks total evidence monotonically while
  claims-per-mention runs the *other* way, so there is no sign the stubs are under-extracted
  relative to their source. B's ceiling is therefore the 11 `missing` facts in the fixture, not
  the length ratio.
  **Next exact action:** implement B1 (add only `participant_facts` to the final scene user
  instruction) and score it against the fixture's 19 `dev` facts — supported-and-new only, both
  claim directions, with the 3 `must_not_assert` controls as the precision floor. The 4 `holdout`
  facts stay unread until a candidate is frozen. The passage-transfer approval for `--execute`
  is still outstanding; B1 can be prepared and unit-tested without it.
  Not done, recorded instead of fixed: the `ORIGIN_FROM`/"From" display defect on Ehrendott's
  page, and the `wisewolf` phantom entity (now reported by `wiki audit gazetteer`, never
  auto-deleted). The STATUS default conflict is unchanged and still needs a decision.

- **2026-09-23 (later), package B1 prepared, $0.** `scripts/eval/probe_sparse_scene.py` extended
  with B0/B1/B2 variant framework and fixture-based scoring against the 19 dev facts (7 missing,
  3 must_not_assert, 9 covered). B0 = current production instruction (state changes, quotes,
  epithets only). B1 = adds only `participant_facts`. B2 = the old bundled candidate. Each
  variant's prompt shares the identical `_user_prefix` and differs only in its trailing
  instruction line. `score_against_fixture` matches accepted claims against fixture facts by
  `(subject, predicate_family)` with inbound-claim awareness. Historical baseline scores 0/7
  recovered, 0 precision violations — confirming the stored response contains no saint facts.
  `tests/test_sparse_scene_probe.py` has 7 tests (3 original gate tests + 4 new: instruction
  isolation, prefix sharing, fixture scoring, holdout sealing). Focused suite: 177 passed.
  Source runs unchanged. No production prompt modified; no artifact regenerated.
  **Next exact action:** obtain passage-transfer approval and `--execute` B0+B1 on the stored
  passage. If B1 recovers any of the 7 missing dev facts without violating the 3
  `must_not_assert` controls, proceed to B2 comparison. If not, the hypothesis is rejected.

- **2026-09-23 (later still), package B harness corrected before spending the approval, $0.**
  Reviewed `99cc99b`'s scorer against the fixture it scores and found three defects that would
  each have made the one gated call unusable — numbers and reproductions in
  [MEASUREMENTS §11](../../MEASUREMENTS.md). The serious one inverted the precision controls: a
  claim correctly recording Saint Ruvinheigen as long dead was scored as violating R8, whose
  point is that the page must not call him *alive*. A candidate that fixed the STATUS defect
  would have been rejected for it. Fixture facts now carry `forbidden_value`; the scorer refuses
  a `must_not_assert` fact without one.
  **B1's scoreable ceiling was 2 of 7 dev facts before a single call was made** — five gaps
  (INFLUENCE, REPUTATION, DEPICTION, NAMESAKE, PATRONAGE) had no predicate that could produce
  them. `BACKGROUND` is the only thing in the vocabulary that can carry narrative content, so it
  now stands as a candidate for every narrative family; the ceiling is 7 of 7 and every candidate
  is human-adjudicated (`adjudicated: null`), never auto-credited. B0/B1/B2 prompts, the
  historical baseline (0/7, 0 violations) and the holdout seal are all unchanged.
  **Next exact action is unchanged and now worth its call:** with the passage-transfer approval,
  `python scripts/eval/probe_sparse_scene.py --execute --variant B1`, then adjudicate each
  `candidate_recovered` entry by reading its value against the fixture quote. Promotion still
  needs the §28 confirmation pass, not the probe alone.
