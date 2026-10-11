# Implement the structured-wiki quality vision

Created: 2026-09-24. Status: **implementation underway; first reader fixes shipped, WP2 gate met**.
Scope: Spice and Wolf v1–2. Parent: [vision](0007-structured-wiki-quality-vision.md).
Evidence: [MEASUREMENTS §22](../../MEASUREMENTS.md),
[snapshot](../../eval/structured_wiki_snapshot_spice-and-wolf.json),
[paper reading record](../../papers/reviews/0007-structured-wiki-quality.md).

## Resume here

1. Read `CLAUDE.md`, applicable contracts, this plan and the baseline snapshot. Inspect git status.
2. **Continue WP2 incrementally.** The first WP0/WP1 defects and latent witnesses are fixed.
   Reproduce `docs/eval/observation_semantics_spice-and-wolf.json`, then persist source
   observations separately from assertions for its six polarity-disagreement groups first.
3. Do not run extraction or regenerate prose merely to rediscover an existing artifact defect.
4. Compare artifact hashes before reusing this review's conclusions. The code baseline is
   `0a9794e1ea8c4c43b64fd0b801a9281e16106b19`; a later fix can make a witness obsolete.
5. Keep task 0006's held-out facts sealed until a candidate is frozen. This review read its
   development evidence and continuation notes, not the held-out fact entries.

Useful existing commands (PowerShell, repo root; no model calls):

```powershell
git status --short
python scripts/eval/structured_wiki_snapshot.py
python scripts/eval/replay_scene_facts.py --run-id 20260922T211717-scenes-v1-2
python scripts/eval/character_evidence_coverage.py --series spice-and-wolf --cutoff 1
python scripts/eval/character_evidence_coverage.py --series spice-and-wolf --cutoff 2
python -m pytest tests/test_spoiler_leak.py tests/test_eval_gold.py tests/test_site_bundle.py tests/test_graph_verify.py -q -p no:cacheprovider
```

The snapshot command rewrites this review's `snapshot.json`. Preserve the checked-in baseline
before rerunning after implementation; put candidate reports in a separate review/run directory.
The coverage scripts likewise write their reports; preserve baseline copies first. Historical
run logs are gitignored. Missing logs are a provenance limitation, not permission to manufacture
a replacement historical baseline. Windows sandbox temp-directory failure was encountered in
this review; the same focused suite passed outside the sandbox. Do not call that a code failure.

## Work-package dependency map

| Package | Dependency | Deliverable | Inference cost |
|---|---|---|---|
| WP0 measurement contract | None | Source-witness labels, stage funnel, honest metric names | None |
| WP1 publication semantics | WP0 counterexamples | Shared cutoff/polarity/review projection; all consumers covered | None for fixtures/reprojection |
| WP2 observation and time model | WP0; recorded policy decisions | Versioned schemas, migration/replay, shadow state projection | Cached outputs first |
| WP3 classification and identity | WP0; WP2 for persistent schema | Typed candidates, ambiguity handling, safe canonicalization | None initially; bounded local adjudication later |
| WP4 evidence recovery | WP0–3 for trustworthy gain attribution | Controlled B0/B1/top-up result | Only after replay cannot answer and existing approval is resolved |
| WP5 progression and citations | WP1–3 | Structured per-volume developments; validated generated sentences | Deterministic first; generation only if justified |
| WP6 release confirmation | Relevant packages accepted | Matched baseline/candidate report, rollback-ready artifacts | One justified v1–2 confirmation |

WP0 and WP1 are the immediate priority. WP2's semantic policy decisions must be resolved before
changing production behavior. The user requested planning; this document does not claim any of
these packages is already implemented.

## WP0 — measure information, classification and assignment separately

**Files:** extend `scripts/eval/character_evidence_coverage.py`, `eval/gold.py`,
`audit/reports.py`, `tests/test_eval_gold.py`, `tests/test_character_evidence_coverage.py`;
add proposed `docs/eval/fixtures/structured_reference_dev.json` and a separate sealed holdout.

Keep the existing gold dataset as a versioned legacy benchmark. Repair the Yarei conditional
label with a source witness and dated correction; preserve the old result in the ledger.
Do not silently replace historical denominators or copy more fandom facts into gold.

Each new reviewed fact needs: fact ID; subject; acceptable predicate/category; object/value;
polarity/modality; attribution when relevant; source paragraph and exact span; earliest disclosure;
allowed cutoff(s); inclusion rationale; reviewer/status; and split. Include positive, negative,
ambiguous, unexpressible and correctly absent facts. Sample leading and sparse characters,
factions, places, relations, events and uncertainty rather than selecting only known successes.

Track this funnel for every reviewed source fact:

`source witness → request coverage → candidate → subject/object resolution → typing → schema
gate → semantic deduplication → graph assertion → verification → reader snapshot → emitted carrier`.

Store explicit loss/disposition reasons, including not stated at cutoff, unresolvable, vocabulary
gap, rejected support, superseded, duplicate and missing renderer. Paragraph overlap is never
credited as semantic coverage. Keep both inbound and outbound relations.

Report independently:

- Extraction recall over reviewed source facts, regardless of whether a display section exists.
- Correct subject/object assignment and relation direction; predicate classification confusion.
- Polarity/attribution/time accuracy on the relevant labeled slices.
- Structured coverage: distinct reviewed facts in the safe export / eligible reviewed facts.
- Publication support precision: reviewed supported emitted atoms / all reviewed emitted atoms;
  report ambiguous/unreviewed counts separately rather than excluding them invisibly.
- Grounded coverage retained after review, to expose an overaggressive verifier.
- Citation support and citation completeness, separately from quote substring validity.
- Duplicate fact rate, unsupported additions and missing facts, by entity/category and cutoff.

**First fix:** include actual `traits` content in the legacy carrier adapter, while preserving
identifier exclusions. Label existing precision as selected-gold/control precision. The snapshot's
Alice example must continue to illustrate its limited scope; do not tweak that formula and call
it comprehensive precision. Add a distinct atom-level metric.

**Validation:** exact trait-only fact is found; unsupported extra assertions affect the new
precision denominator; rejected evidence does not count as covered; alias/paraphrase equivalence
cannot credit a wrong entity, direction, modality or time. Have a second independent review of
ambiguous source labels before using them as promotion gates; record single-review limits until
then. Do not invent a corpus-wide confidence interval from a convenience sample.

## WP1 — one safe publication projection

**Files:** proposed `graph/publication.py`; `graph/temporal.py`, `graph/store.py`,
`synth/assemble.py`, `site/bundle.py`, `site/mkdocs_wiki.py`, `graph/ppr.py`, cache/hash builders,
`docs/CONTRACTS.md`; focused tests in the existing bundle/spoiler/graph suites.

1. Specify `reader_snapshot(cutoff, policy_version)` or equivalent typed API. It returns safe
   current/history assertions with visible names, polarity, eligible evidence and review status.
   Keep raw SQL helpers for diagnostics; require publication consumers to use the safe API.
2. Repair `relations_at` current/history semantics without silently deleting history. Audit its
   call sites; callers wanting history must request it explicitly.
3. Project polarity consistently. Denied relations cannot become ordinary membership/enemy
   edges; presumed relations need an explicit structured status and reader label. Preserve
   denials in the evidence/history layer even if omitted from positive relationship lists.
4. Remove all future endpoints, successor IDs and future identity metadata from earlier exports.
   A boundary that ends at N can still reveal a transition after N; make disclosure eligibility,
   not just a numeric comparison, the rule for showing an end or successor.
5. Do not default unknown polarity strings to asserted. Allow only documented semantics-preserving
   normalizations; retain invalid candidates with a reason for replay/review.
6. Centralize review checks. Unknown/skipped/stale is distinct from supported. Keep current default
   behavior behind a named compatibility policy until release-mode behavior is accepted. A
   strict diagnostic comparison can be built without silently changing shipped pages.
7. Audit public sinks: attributes, traits, relationship prose, related entries, codex rosters,
   pair relations/history, event summaries, timeline, navigation, source anchors, metadata,
   search assets and image captions. Make eligibility part of shared selection, not just rendering.
8. Version derived-cache keys with semantic payload, evidence identity, projection policy and
   applicable review decisions. Preserve the raw LLM response cache. A semantic change must not
   reuse stale generated prose merely because interval IDs stayed the same.

**Required counterexamples:** all witnesses in `audit_snapshot.py`; presumed→asserted transition;
no-change re-observation; denied adversary does not suppress a true affiliation; unsupported
history; missing verifier; changed evidence with old verdict; and a future identity reveal.

**Metamorphic gate:** compute cutoff-1 structured export from v1-only inputs, then after appending
v2 evidence/aliases/verdicts. With earlier extraction frozen, earlier reader content must match.
Exercise all public artifacts, not only character Markdown. Any permitted retrospective correction
must carry explicit correction provenance. Separate build-time model knowledge risk from lexical
future-artifact leakage; the existing index/leak probes are diagnostics, not complete proof.

**Exit:** current known witnesses are fixed with regression coverage; identical facts have
identical eligibility across consumers; stale/future verification cannot authorize or suppress
an earlier assertion silently; focused checks pass. No paid generation is necessary for this gate.

## WP2 — preserve evidence observations and model disclosure separately from time

**Decision needed first:** the current standing rule “same volume conflict = extraction error;
different volumes = narrative change” cannot represent legitimate within-volume change, hearsay
or retrospective disclosure. Prepare reviewed fixtures and a shadow projection, then obtain
explicit acceptance of replacement semantics before changing production arbitration.

**Files:** `extract/schema.py`, `extract/scene_schema.py`, `extract/claims.py`, `extract/scenes.py`,
`graph/store.py`, `graph/temporal.py`, `graph/contradictions.py`, `graph/support.py`, `paths.py`,
run snapshot/rollback code, `docs/CONTRACTS.md`.

Proposed minimal records (final names after contract review):

| Record | Required information |
|---|---|
| Observation | stable occurrence ID; source hash/paragraph/span; candidate/resolved participants; predicate/value; polarity/modality; attribution; source order; extraction run/cache reference |
| Assertion | typed proposition; semantic qualifiers; disclosure position; linked observations; review/conflict state; schema version |
| Development | subject; prior/resulting assertion IDs; source order; optional evidenced valid-time/event link; change kind; supporting observations |
| Review decision | target content hash; evidence/context hash; evidence cutoff; reviewer/model revision; method/policy version; status/score; run ID |

Keep `first_vol` as the disclosure-volume fence. Never backdate it because a later passage
describes an earlier event. Same-volume change can be ordered by evidence position, but reading
order is not automatically world chronology. Unknown valid time stays unknown.

Do not encode all these distinctions into one hash and assume the problem is solved. Separate
observation identity from assertion equivalence. Merge only compatible subject/predicate/value,
polarity, attribution and meaningful qualifiers; preserve all evidence and contradictory reports.
Do not replace the current short hash solely for theoretical collision risk; semantic collision is
the demonstrated problem. Use an explicit schema version and collision-safe new IDs when migrating.

Migration: snapshot source artifacts → replay stored raw responses where available → emit
versioned observations in parallel → build shadow graph → compare assertions/dispositions →
validate rollback and cache invalidation → switch readers only after acceptance. Existing merged
claims may already have lost polarity/qualifier distinctions: raw responses can recover some;
label unrecoverable legacy provenance rather than inventing it. Never edit historical cache entries.

Verification should include visible historical assertions, not only current state. An old positive
verdict does not approve a changed assertion/evidence set; a v2 decision must not silently govern
v1. Calibrate and reuse the existing NLI path rather than treating task 0005's old “pending” header
as evidence it has not been built. Retain its limitations and pending validation explicitly.

**Exit:** order-independent observation replay; incompatible polarities do not merge; within-volume
change, reported belief, false report and later revelation are distinguishable; identical visible
evidence gives stable earlier snapshots; migration and rollback preserve counts and lineage.

## WP3 — classify and assign before increasing extraction volume

**Files:** `config/extraction.yaml`, series overlay, `config.py`, `extract/resolve.py`,
`entities/automaton.py`, `entities/alias.py`, `graph/canonicalize.py`, extraction gates;
new typed-candidate fixtures and contracts if persistent artifacts change.

- Inspect development witnesses for INFLUENCE, REPUTATION, DEPICTION, NAMESAKE and PATRONAGE.
  Define each proposed predicate's meaning, subject/object types, direction, cardinality,
  time behavior, positive/negative examples and public carrier. Do not add all by default.
  A depiction relation describes an artwork/representation, not an unsupported physical trait.
- Distinguish skill from disposition, occupation from honorific/reputation, association from
  membership, and location from origin. Preserve unclassified candidates for diagnosis.
  Count a BACKGROUND fallback as narrative retention, not typed-category success.
- Preserve multiple identity candidates for ambiguous surfaces. Resolve with cutoff-safe local
  evidence and compatible entity types; abstain if unresolved. Measure mention assignment on a
  reviewed sample before proposing a corpus-wide coreference system.
- Scope aliases and identity merges to their disclosure evidence. Opaque internal IDs may remain
  stable while public labels/routes change safely. Test a late reveal joining earlier identities.
- Canonicalize using exact equivalence first. Use embeddings only for candidate generation;
  require bidirectional support or review for merges, preserve polarity/time/qualifier distinctions,
  and record reversible equivalence decisions. The sound/scent skill pair is a nonmerge control.

**Exit:** recovered typed information is genuinely new and correctly attributed; no held-out
taxonomy leakage; no known false merge; rejected/unresolved records remain auditable. Report
classification and identity accuracy independently of extraction recall.

## WP4 — bounded extraction experiments, after diagnosis

Reuse [task 0006](0006-sparse-character-evidence.md). Package A and the B1 harness already exist.
The old instruction in its introduction to “implement A” is superseded by its continuation log.
Do not repeat that work or read its sealed holdout to design this change.

Ordered experiments:

| Experiment | Controlled change | Decision |
|---|---|---|
| E0 | Reproject existing observations through corrected semantics/ontology | Establish gain available without extraction |
| E1 | Current B0 versus B1's single `participant_facts` instruction addition | Reject if no reviewed new supported facts; retain polarity controls |
| E2 | A single character/category question, same evidence budget and gates | CHIRON-inspired test only for residual documented misses |
| E3 | One targeted top-up round planned from remaining source-supported gaps | Promote only if marginal nonduplicate supported coverage justifies cost |

For every candidate record exact prompts, model/config, run/cache IDs, source hashes, schema and
policy versions; match input conditions. Score returned candidates by reading their evidence,
not by `(subject, predicate_family)` matching alone. Preserve original full-roster window budget
allocation even when extracting a subset. Never overwrite an entire volume with a targeted subset.

Existing preparation command:

```powershell
python scripts/eval/probe_sparse_scene.py
```

The existing `--execute --variant B1` command remains subject to task 0006's recorded passage-transfer
approval. Downloading public papers did not grant that approval. Before any billed comparison,
state why cached responses, fixtures or deterministic changes cannot answer the question.

**Stop:** no semantically new supported information; any severe polarity/attribution/spoiler
regression; gain only on development examples; altered baseline inputs; missing provenance or
provider approval. A winning small test still needs WP6 confirmation.

## WP5 — structured progression and generated-assertion provenance

**Files:** `graph/events.py`, `synth/assemble.py`, `synth/prose.py`, `site/bundle.py`,
`site/mkdocs_wiki.py`, page/bundle contracts, evaluation adapters.

Start with deterministic per-character/per-volume records: newly disclosed facts, retained state,
resolved uncertainty and evidenced developments. Distinguish “newly learned by the reader” from
“happened during this volume.” Connect event participation by source evidence and explicit roles;
co-presence alone does not justify a social relation, motivation or causal edge.

Validate existing `beat_summary` text against its source spans before reusing it as event truth.
Attach atom/sentence IDs and supporting observation IDs to generated prose. A pooled source list
is a provenance aid, not evidence that each sentence is supported. Check attribution, negation,
scope and conjunctive claims; preserve enough context to resolve pronouns. Unverifiable sentences
are withheld or sent to the diagnostic queue, not repaired by another unsupported paraphrase.

Use MiniCheck as one locally calibrated signal, not an omniscient judge. Preserve independent
human labels for calibration; report false positives and false negatives by relation/attribute/
trait, modality and evidence distance. Do not reuse a verifier's predictions as its own gold.

Do not add a portrait unless depiction identity is reviewed. A neutral “illustration from volume N”
label may be appropriate for unassigned art; a character name in alt text is itself an assertion.

**Exit:** every displayed progression record is supported at that cutoff; no-change controls stay
stable; sentence citations are complete for the reviewed sample; existing graph facts are not
silently lost during prose compression; redundant facts remain grouped without deleted nuance.

## WP6 — confirmation and release evidence

Before confirmation, freeze dev decisions and open the held-out set once. Record all failures;
do not repeatedly tune on it and continue to call it holdout. Use independently reviewed novel
passages within v1–2 if the old holdout becomes development material.

Preserve baseline data/build configuration and compare on the same source/gazetteer state. For
the one justified full confirmation, follow `docs/handover/PHASE_28.md` §6 stage ordering:
gazetteer → scenes → epithet merge → extract → graph → verify → events → synthesize → site.
Inspect actual CLI help before invoking, constrain every volume-taking stage to `--volumes 1-2`,
every cutoff-taking stage to `--upto 2`, and use `-s spice-and-wolf` throughout. Graph/events stages
consume files rather than a volume flag: assert the staged input manifest contains only v1–2.
Do not copy historical `--allow-partial` or `--polish` automatically; diagnose/justify each.

Run focused tests for changed behavior and affected integrations. Existing relevant suites:
`test_spoiler_leak.py`, `test_eval_gold.py`, `test_site_bundle.py`, `test_provenance.py`,
`test_graph_verify.py`, `test_graph_support.py`, `test_support.py`, and the coverage fixture suite.
Add tests per package; do not run the entire repository suite by default.

Acceptance report must show at both cutoffs: source-supported facts missed/recovered; correct
structured assignments; reviewed publication precision; unsupported additions; duplicates;
unknown/rejected counts; citation support/completeness; state/development consistency; cutoff
invariance; cost/cache hits; and which inputs were independently held out. Break down by entity
and category; a macro average must not hide a sparse-character regression.

Release requires no known high-severity failures in the reviewed set and no unexplained regression
in reviewed supported coverage. Pure safety fixes may reduce apparent coverage by removing false
facts; label that explicitly. Set numerical quality targets only after WP0 establishes denominator
and annotation reliability. No unsupported “professional quality achieved” headline.

Append command, run ID, hashes, result and spend to `docs/MEASUREMENTS.md`. Update this plan's
continuation status. Leave protected planning/log changes to Claude or the maintainer.

## Current status and unresolved decisions

- [x] Architecture, current implementation and artifact review; reproducible synthetic witnesses.
- [x] Public research PDFs downloaded; hashes and selected-section reading records saved.
- [x] Existing focused tests passed; no production pipeline/model calls in this review.
- [x] First WP0/WP1 reader fixes: trait carrier; shared relationship polarity; denied projection;
  explicit current/history relation queries; invalid-polarity quarantine; semantic claim key.
- [x] WP2 measurement gate: 16 conflict reviews and stored-response provenance trace
  (`20260924-observation-semantics-v1-2`).
- [ ] Remaining WP0–WP6 implementation and post-change validation.
- [ ] Accept disclosure/source-order replacement for standing volume-only conflict semantics.
- [x] Reader policy supplied by maintainer: preserve story uncertainty; use model confidence for
  model uncertainty; make missing traceable evidence visible rather than silently asserting it.
- [ ] Implement that reader policy and decide how legacy/stale verdicts migrate.
- [ ] Use agent-drafted labels with quoted witnesses and maintainer spot-checks; freeze a
  defensible acceptance sample before release confirmation.
- [x] Vertex passage transfer is permitted for Spice and Wolf v1–2 under the project's total
  final $200 ceiling; API use remains scarce, with Ollama/free OpenRouter preferred when adequate.

Continuation entries must state package, commit, artifact/run IDs, accepted/rejected hypothesis,
validation result and next exact action. Do not leave a measured result only in chat.

### Continuation — 2026-09-24 implementation start

- **Packages:** WP0 legacy carrier, WP1 publication semantics, WP2 measurement gate.
- **Commits:** `8d886a2` shared presumed relationship label; `05183de` trait evaluation carrier;
  `86a668e` denied-relation projection; `8406691` explicit current/history relation queries;
  `b4b04c6` polarity/qualifier-aware claim identity and invalid-polarity quarantine; `b8e82b1`
  stored-response semantic audit.
- **Artifact/runs:** `docs/eval/observation_semantics_spice-and-wolf.json`, measurement
  `20260924-observation-semantics-v1-2`, source runs `20260922T212119-extract-v1-2` and
  `20260922T211717-scenes-v1-2`. No model calls.
- **Decision:** reject the “near-zero disagreement, no provenance layer needed” hypothesis.
  Six of the 102 multiply-observed legacy claims disagree on polarity, 44 on normalized qualifier,
  and one of 16 dropped-side conflicts is a real within-volume transition. Preserve observations
  separately from assertions, but stage the migration around these witnesses rather than doing a
  big-bang production cutover.
- **Validation:** the report traces every persisted evidence item to a stored response. Focused
  extraction, scene, and CLI suites pass outside the Windows sandbox; see MEASUREMENTS §25.
- **Next exact action:** add a versioned observation contract and deterministic stored-response
  replay that materializes the six polarity-disagreement groups alongside the legacy claims.
  Assert order-independent replay and keep production readers on the legacy graph until a shadow
  comparison accounts for every disposition.

### Continuation — 2026-09-24 observation shadow

- **Package/commit:** WP2, `aa7e5b0`.
- **Artifact/runs:** `docs/eval/observation_shadow_spice-and-wolf.jsonl`; the same two stored
  source runs and measurement ID as the preceding entry. No model calls.
- **Accepted hypothesis:** occurrence identity can be recovered deterministically from the
  recorded run/cache/fact position without changing legacy artifacts. The 13 reconstructed
  observations validate against schema version 1 and replay to a byte-identical SHA-256.
- **Rejected hypothesis:** current qualifier-sensitive claim IDs are already a sufficient
  assertion layer. All 13 observations produce separate candidate IDs; qualifier paraphrase
  equivalence remains unresolved and must not be guessed from spelling.
- **Validation:** `tests/test_extract.py` passes outside the sandbox; report input hashes and the
  shadow artifact hash are recorded in MEASUREMENTS §§25–26.
- **Next exact action:** build a shadow assertion/disposition report for these observations,
  distinguishing uncertainty resolution, later reported belief, extraction error, compatible
  qualifier paraphrase, and true story development before any production graph switch.

### Continuation — 2026-09-24 shadow dispositions and reader-visible citations

- **Packages/commits:** WP2 shadow dispositions; WP1/WP5 per-claim citations on every structured
  row. Continues Codex's uncommitted working tree (`scripts/eval/audit_observation_semantics.py`,
  `synth/assemble.py`, `site/okf.py`, `site/mkdocs_wiki.py`, `graph/publication.py`).
- **Artifact/runs:** `docs/eval/observation_semantics_spice-and-wolf.json` (measurement
  `20260924-observation-semantics-v1-2`, reproduced byte-identically apart from the script's own
  self-hash), `dist/spice-and-wolf/wiki` rebuilt at upto 2, run
  `20260924T161948-site_build-upto2`. **No model calls; $0.** Lifetime spend still $5.4889.
- **Accepted hypothesis:** the 6 polarity-disagreement groups are dispositionable without a graph
  migration — 4 `uncertainty_resolved`, 1 `extraction_error`, 1 `distinct_relation_contexts`. None
  is a true story development, so the legacy graph stays authoritative for now.
- **Rejected hypothesis:** a polarity trajectory is a sufficient merge rule. `c_81848e1c` pairs
  asserted hostility with a *conditionally imagined* enmity; collapsing those into one certainty
  trajectory would manufacture a fact. Direction, attribution and qualifier need separate review.
- **Defect found and fixed (was about to ship):** the "make missing evidence visible" policy read
  a *missing* `evidence` key as "this assertion has no source". `data/05_pages/**/v{NN}.json`
  predated citation-carrying assembly and `claim_set_hash` does not move when the page shape
  changes, so `synthesize` skipped every cutoff and all 21 pages rendered "source evidence
  unavailable" on every attribute row — while `evidence_at` held 590 usable citations. Absent
  (stale artifact, stay silent) is now distinguished from recorded-empty (the real notice).
- **Also fixed:** `cli.py::_merge_claims_by_id` raised `KeyError: 'predicate'` on a malformed
  claim row, crashing the completeness gate meant to report it (regression from `b4b04c6`;
  `tests/test_stage_guard.py` had been red). `site.default_upto` for this series was still 1 from
  when only v1 existed, so a bare `site build` rendered half the site and failed `audit links`.
  `mkdocs_wiki._source_links` duplicated `okf._source_links` and rendered a literal `_(None)_`;
  both renderers now share `okf._evidence_suffix`, the one choke point onto `evidence_notice`.
- **Validation:** full suite 1073 passed, exit 0 (was 1 failed). `audit links` OK across 33
  routes. 0 v2 citations on any cutoff-1 page. Re-synthesis changed only `fields` — no prose
  churn, $0. See MEASUREMENTS §27.
- **Next exact action:** decide qualifier-paraphrase equivalence, which the 44 qualifier
  disagreements still block and which must not be guessed from spelling. Until then the
  `uncertainty_resolved` projection (keep the presumption as history, publish the later
  assertion) is reviewed but not implemented in `graph/temporal.py`; implement it for the 4
  witnessed groups first and leave `c_81848e1c` and `c_1bef3c92` to explicit review.

### Continuation — 2026-09-24 directional reversal fixed; verdict instability found

- **Package/commit:** WP1 publication semantics (a directional relation rendered backwards) plus a
  WP2 finding that changes what the remaining WP2 work has to cover.
- **Artifact/runs:** `graph.db` rebuilt (`20260924T162...-graph_build`), wiki rebuilt at upto 2,
  `docs/eval/fixtures/sparse_character_evidence.json` pointers migrated. **$0.0600 total**
  (lifetime $5.4889 → $5.5489). MEASUREMENTS §28.
- **Accepted hypothesis:** `_strip_mutual_direction_collisions`'s `pred in conflict_groups` skip
  was unsound. SAVED and KILLED declare each other **and** are directional — the combination the
  code's own note assumed impossible — so they were exempt from the only reversal check, and
  `kraft-lawrence SAVED holo` shipped alongside the correct direction from one sentence. Fixed;
  only symmetry exempts a predicate now. The tiebreak had to change with it: both directions came
  in at confidence 1.0, and `_rank_key` fell back to dict order, so the check alone would have
  picked the wrong direction about half the time.
- **Rejected hypothesis:** that the qualifier-paraphrase question (44 disagreement groups) was the
  most valuable next step. Inspected, and the groups are overwhelmingly the same relation at
  different specificity ("traveling companions" 16 times out of 18, plus "trusted companions" and
  one longer restatement) — a presentation nicety. Two live correctness defects outranked it.
- **Finding that should reshape the rest of WP2 — verification verdicts do not hold still.**
  The rebuild changed exactly one relation and re-rolled 12 reader-visible gates (unsupported
  14 → 25 of ~350). 4 of 5 sampled flips had an identical `interval_id` and identical evidence
  count: same fact, same quotes, opposite verdict. Cause is structural, in `graph/verify.py`: one
  LLM call per character, facts as a numbered list, flags returned as `fact_index`. So (1) changing
  any one fact re-prompts and re-rolls all of that character's verdicts, and (2) judgements bleed
  between facts in a call — `norah-arendt COMMANDS enek` was withheld on the rationale "describes
  Enek following orders, not Norah commanding **Liebert**", a blend of two adjacent COMMANDS
  facts. An in-range but wrong `fact_index` withholds the wrong fact undetectably.
- **Regression shipped knowingly, and recorded:** relation rows 34 → 23, heading-only stub pages
  6 → 11. Not from the SAVED fix (one row) but from re-verification. Some newly withheld facts are
  correctly withheld; at least two are false negatives. Against §2b's "no dead-end stubs" the
  artifact is worse than the one it replaced. Reverting is not the answer — carrying stale verdicts
  onto a changed graph is the thing WP2 explicitly forbids ("an old positive verdict does not
  approve a changed assertion/evidence set").
- **Validation:** full suite 1074 passed, exit 0; the new reversal test fails on pre-fix code.
  `audit links` OK across 33 routes. `SPOUSE_OF` ("false identity for travel") re-verified
  `unsupported`, so the marriage is still withheld — that defect stays latent, as §24 graded it.
- **Next exact action:** make a verdict survive a rebuild when its own fact and evidence are
  unchanged. `verdicts.context_sha256` / `evidence_cutoff` / `model_revision` already exist and
  are NULL on all 348 rows, while `store.py::reset()` deletes the table on every `graph build`.
  Populate `context_sha256` from the fact's identity plus its cited evidence, carry matching
  verdicts forward, and re-verify only facts whose own context moved. That is WP2's unmet exit
  criterion "identical visible evidence gives stable earlier snapshots", and it should land before
  any further verdict-sensitive measurement — the stub-page regression above is what its absence
  costs. Per-fact call granularity (which would also fix the cross-fact bleed) is the larger
  follow-on; decide it after stability, since stability is free and measurable.

### Continuation — 2026-09-24 verdict stability (WP2 exit criterion met)

- **Package:** WP2. Implements the preceding entry's "next exact action".
- **Artifact/runs:** `graph.db` verdicts now carry `context_sha256` + `evidence_cutoff` on all 348
  rows; wiki rebuilt and proven byte-identical across a round-trip. **$0.00** across three full
  `graph build` runs; lifetime unchanged at $5.5489. MEASUREMENTS §29.
- **Accepted hypothesis:** verdict instability was entirely mechanical, not model variance.
  `store.reset()` deleted `verdicts` on every `graph build`, so nothing could be carried forward
  even for a fact whose own evidence was untouched. `reset()` now spares the table,
  `prune_orphan_verdicts` keeps the "no verdict outlives its interval" invariant, and
  `verify.fact_context_sha256` fingerprints exactly what a verdict was judged on (kind, predicate,
  value, qualifier, sorted evidence). A character whose facts all still match is not re-asked.
- **Result:** rebuild 1 re-verified (stored verdicts predated the hash); rebuilds 2 and 3 checked
  0 characters, reused all 14, kept 348 verdicts, and produced a byte-identical `dist/` tree.
  Unsupported held at 25 (7.2%) instead of moving 14 → 25. **WP2's exit criterion "identical
  visible evidence gives stable earlier snapshots" is met for this pipeline.**
- **Rejected hypothesis:** that per-fact verdict granularity was needed to get stability. It is
  not — per-character reuse is sufficient and free. It IS still needed for the other half of §28,
  the cross-fact bleed, and that remains open.
- **Known limit, stated not papered over:** the reuse unit is the character, because the call is.
  One changed fact still re-rolls all of that character's verdicts. The regression §28 records
  (relation rows 34 → 23, stub pages 6 → 11) is therefore contained, not undone — it stays until
  the false negatives inside it are re-judged.
- **Side effect, intended:** `characters_flagged` 11 → 12. Weiz read "ok" while its page withheld
  `kraft-lawrence FRIEND_OF weiz`, flagged from Lawrence's side; the report now lists every
  character carrying an unsupported verdict. `facts_flagged` (the audit gate's numerator) unchanged.
- **Validation:** 1077 passed, exit 0; `audit verify` OK at 7.2%; `audit links` OK across 33 routes;
  round-trip diff clean.
- **Next exact action:** re-judge the 12 intervals §28 lists as newly withheld, because at least two
  are false negatives (`norah-arendt COMMANDS enek` — a shepherdess commanding her sheepdog,
  withheld on a rationale arguing about Liebert; `kraft-lawrence ENEMY_OF remelio-company` —
  Remelio threatens to kill him in v2). Do it by making verification flag a fact by an identifying
  echo rather than by bare list index, so a judgement cannot be attached to the wrong fact, and
  decide per-fact call granularity at the same time — the two share the same root cause. Stability
  is in place now, so that change's effect can finally be measured against a fixed baseline.

### Continuation — 2026-09-24 per-fact verification (accepted with a recorded cost)

- **Package:** WP1/WP2. Implements the preceding entry's next action (flag a fact by something
  other than a bare list index) and decides the per-fact granularity question with it.
- **Artifact/runs:** per-fact `verify` over 348 facts, then re-extraction of both volumes, graph
  rebuild, wiki rebuild. **$0.7992** (lifetime $5.5489 → $6.3481). MEASUREMENTS §30.
- **Accepted hypothesis:** one call per fact removes the mis-attribution defect outright — there is
  no index left to get wrong — and it is cheap ($0.1252 for 348 calls, because a per-fact prompt is
  far smaller than one carrying a character's whole fact list). It also makes the reuse unit match
  the call unit: a changed fact now costs one call, not a whole character's re-roll. `METHOD_REVISION`
  gates verdict reuse, so replacing the method re-verified once rather than silently carrying the
  replaced method's judgements forward.
- **Rejected hypothesis — and this is the finding:** that the per-character batching was purely
  harmful. It was not. The flips split cleanly by fact kind: **16 of 16 releases are relations,
  25 of 26 new withholdings are attributes.** Per-fact is sharper on a trait (it caught
  `NICKNAME 'Holo'`, `PERSONALITY 'drunk'`, `'always-quick'`, `'jealous'` where the quote says the
  opposite, `'softhearted'` which is Holo describing Lawrence, and two unconfirmed SKILL claims) and
  more permissive on a relation, because it no longer sees the character's other facts. The batching
  was incidentally supplying cross-fact context that relation judgements were using.
- **What that cost, before it was caught:** `holo SPOUSE_OF kraft-lawrence` ("false identity for
  travel") flipped to supported and **shipped on 6 pages** — a §2b hard violation. Also wrongly
  released: `marheit AFFILIATED_WITH medio-company` (evidence is about Milone), `norah-arendt
  ENEMY_OF ruvinheigen` (a city), `enek ENEMY_OF holo` (a sheepdog).
- **Fixed deterministically:** `SPOUSE_OF.qualifier_disqualifiers` now carries RELATIVE_OF's
  pretence list plus `false identity` / `false name` / `cover story`. Its own config note already
  demanded this and `RELATIVE_OF` already had the list. A fixed phrase belongs in a rule, not in a
  judgement that held under one verification method and not the other. 0 occurrences of "Spouse of"
  in the emitted tree; the gate fired 16 times in v02.
- **Trap found, worth more than the fix:** `extract/adequacy.py::prompt_rules()` injects the gate
  config INTO the extraction prompt, so editing `qualifier_disqualifiers` made every
  `claim_extract` call a cache miss and **re-rolled the claim set** instead of re-filtering it
  (v01 166 → 183 claims, $0.5545). Collateral: two hand-reviewed `already_covered` facts
  unrelated to SPOUSE_OF disappeared from the graph (`saint-metrogius OCCUPATION 'saint of
  business'`, `saint-ruvinheigen APPEARANCE 'missing left arm'`). They are recorded as `lost` in
  the fixture rather than re-pointed at a different claim, and their `status` moved to `missing`.
  **No extraction-config edit in this repo is surgical. Budget a re-extraction for every one.**
- **Validation:** 1085 passed, exit 0; `audit links` OK across 33 routes; unsupported 9.0% of 323;
  rebuild round-trip byte-identical at $0. Net artifact: relation rows 34 → 38, relationship pages
  25 → 30, heading-only stubs 6 → 9.
- **Open, and not papered over:** 9 relationship pages still have every relation withheld, so §2b's
  "no dead-end stubs" is unmet; and ~4 attribute withholdings are wrong, including two `STATUS
  'alive'` for characters who are alive.
- **Next exact action:** give a relation fact the other facts about the **same pair** in its prompt,
  and nothing more — that is the context the batched call supplied by accident, scoped to where the
  evidence says it is used, without returning to per-character batching. Measure against this run
  as the fixed baseline (stability from §29 makes that possible): the target is to recover the four
  wrongly-released relations without giving back the attribute precision. Bump `METHOD_REVISION`,
  which will re-verify once.

## Audit by Claude — 2026-09-24

Every code-level claim in §3 of the vision checks out. Checked in source: `_page_text` omits
traits; invalid polarity defaults to asserted; `make_claim_id` excludes polarity/qualifier and
`_merge_claim` keeps the first semantic fields; `relations_at` has no end filter; bundle
`until_vol` copying; permissive `_is_renderable`; alphabetical automaton claimant; ungated
`beat_summary`. The direction is right: one shared publication projection instead of per-consumer
checks. The following changes are proposed. Each is reversible, and none needs a model call.
Numbers: `docs/MEASUREMENTS.md` §24.

1. **Re-grade by what is live.** 0 closed relation intervals and 0 denied claims exist, so the
   temporal-read and denied-projection items are *latent*. They should get regression tests, but
   they are not P0 fires. The live, reader-visible defects are (a) presumed polarity dropped on pair
   pages (Zheren/Lawrence) and (b) the eval carrier missing traits. Fix those two first. They are
   small and ship value immediately.
2. **Measure before migrating (WP2).** The four-record observation/assertion/development/review
   schema, shadow graph and migration is the plan's largest cost. Its justification is
   hypothetical at this scope. Two free checks come first: review the **16** same-volume
   arbitrations that dropped a side (§24) for legitimate within-volume change, and count claims
   whose merged observations disagreed on polarity or qualifier (from stored `calls.jsonl`
   responses). If both are near zero, the fix is small: add polarity (and a normalized
   qualifier) to the merge key, quarantine invalid polarity, and keep the standing
   contradiction rule. Otherwise, run WP2 scoped to the witnessed cases.
3. **Keep the target in view.** `CLAUDE.md` §2b and Phase 30 judge the wiki on structure and
   connectedness as well as faithfulness. This plan is almost entirely about precision, so every
   WP exit should also report page balance/dead ends (`wiki audit links`), so that safety fixes do
   not silently hollow out pages.
4. **Make review requirements achievable.** There is one maintainer. "Second independent review"
   and "reviewer agreement" gates will stall WP0. Use agent-drafted labels, each with a quoted
   source witness, plus maintainer spot-checks of ambiguous items. Record single-review status
   as the plan already allows.
5. **Strict release mode is cheap: adopt it.** 349 of 351 intervals already carry verdicts, so
   withholding unreviewed assertions costs almost nothing. It stays a maintainer decision because
   it changes shipped behaviour.
6. **The "passage-transfer approval" blocker needs a ruling, not waiting.** It came from Codex's
   sandbox auto-review. It is not a project rule: `CLAUDE.md` §2 already routes every generative
   stage for Spice and Wolf v1–2 to Vertex, and every extraction run sends these same passages.
   The maintainer should confirm that it is covered, so task 0006's B0/B1 run is judged only by
   the cheapest-path rule.
7. **Portraits (WP5):** keep reviewed-or-neutral captions, but do not strip every heuristic
   thumbnail. Phase 29 already removed the one known mis-caption.

**Proposed first commits, in order:** pair-page presumed label via a shared polarity helper,
with a test; traits in `_page_text`, with the trait-only recall test; the snapshot's synthetic
witnesses as focused tests (latent paths); `relations_at` end filter with an explicit history
variant; polarity-aware merge key plus invalid-polarity quarantine; then the two WP2 measurements
above, before any schema work.
