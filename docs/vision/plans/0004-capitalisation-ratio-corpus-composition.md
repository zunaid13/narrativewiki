# TASK-0004: Per-volume capitalisation ratio — implemented and validated

```
Status:   DONE (Option A; final gate comparison and validation in §7)
Author:   claude
Assigned: either agent, after the maintainer picks an option in §3
Created:  2026-09-15
```

**Scope reminder, binding for this task:** Spice and Wolf, `--volumes 1-2`, only, per the
maintainer's standing instruction (`AGENTS.md` §3, `docs/vision/PHASE_24.md` 2026-09-14 night).

## 1. Why this task exists

`docs/vision/PHASE_24.md`'s 2026-09-14 (late pm) entry root-caused why bare `Wisewolf` (17
occurrences in v1, well clear of `min_mentions=3`) is its own candidate entity at cutoff `@t01` but
**vanishes entirely** — not merged into `holo`, just gone — once volume 2 is added to the same
mining pass (`@t02` and render mode both). The entry explicitly left the fix undecided: "flagged as
a candidate for `docs/vision/plans/`, not fixed impulsively." This task files that.

## 2. The mechanism (verified against `entities/candidates.py::mine_candidates`, not re-derived)

`_passes_capitalisation_ratio` accepts a single-token candidate only if
`(exact-case count) / (any-case count anywhere in the mining scope) >= _ALWAYS_CAPITALISED_RATIO`
(0.75). Both the numerator (`agg[surface]["count"]`) and denominator (`word_freq[surface.lower()]`)
are accumulated in one pass over every volume in the `volumes` dict the caller passes in — there is
no per-volume reset. Measured directly:

| mining scope | exact `Wisewolf` | any-case `wisewolf` | ratio | passes 0.75? |
|---|---|---|---|---|
| volume 1 only | 17 | 20 | **0.850** | yes |
| volumes 1+2 | 34 | 49 | **0.694** | **no** |

Volume 2 adds 12 non-exact-case occurrences (`"wisewolf"`, `"Wise Wolf"`) that don't exist in volume
1 — a real in-narrative shift (v1 uses `Wisewolf` as a proper name the reader doesn't yet understand;
by v2, now that Holo's identity is established, it increasingly reads as a common descriptive title:
`"Holo the Wisewolf"`, `"a canny wisewolf"`). The filter retroactively drops volume 1's own,
independently-qualifying evidence because of how the same string gets used once more text joins the
same mining pass. This is corpus-composition-dependent, not cutoff-dependent — it would reproduce
comparing two render-mode runs at different corpus sizes, no `--gate=build` involved at all.

**Not a leak.** This does not put a future fact in front of a cutoff-`t` reader; if anything it
removes an entity a reader legitimately could infer, so it is a recall/completeness defect, not a
`tests/test_spoiler_leak.py`-class safety defect. It does, however, make the entity set
**non-monotonic across cutoffs** (present at `@t01`, absent at `@t02`), which nothing in the design
predicts and which complicates every future `--gate=build` vs. render comparison — see
`docs/vision/PHASE_24.md` 2026-09-15 for the one channel (`measure_candidate_mining`'s `leak_rate`)
already confirmed structurally immune to this.

## 3. The decision — two options, not resolved here

**Option A — per-volume-OR-across-volumes.** Compute the ratio within each volume separately;
keep the candidate if it clears 0.75 in *any single volume* it appears in, even if the pooled
corpus-wide ratio would fail it. Rationale: once a word has independently earned proper-noun status
from one volume's own text, later volumes using it more loosely shouldn't erase that evidence.
Risk: a word that is a common noun everywhere except one biased paragraph (e.g. three consecutive
sentence-initial "Wolf/Wolf/Wolf" in one action scene) could pass on weak grounds it currently fails
on correctly, pending the sentence-initial safeguards (`agg`'s `signals` set) actually catching it.

**Option B — leave it corpus-wide, treat non-monotonicity as a documented, named property of the
taxonomy** (a reader's own sense of what's a proper noun really is corpus-dependent — that's not
obviously wrong) rather than a bug. Add a `wiki audit gazetteer` warning when a `@tN` cutoff's
candidate set loses a surface a smaller cutoff had, so it's visible instead of silent, and cite the
behavior explicitly in `docs/vision/PHASE_24.md` as an accepted taxonomy dimension for the paper
(a fifth leak-adjacent phenomenon, distinct from L_build/L_extract/etc.) rather than something to
suppress.

**Recommendation (not a decision — the maintainer's, since it changes candidate-mining behavior and
every already-published `docs/probe/*.jsonl` number derived from it): Option A.** A reader who has
finished volume 1 does not un-learn that `Wisewolf` is Holo's name because volume 2 exists; an index
that can is measurably wrong in a way Option A directly fixes, and Option B mostly just accepts a
recall regression instead of fixing it. But Option A is a behavior change to a function three
already-recorded headline numbers (0.303→0.033, 0.982→0.954-class corrections, this task's own
0.042→0.000) were measured against, so re-running the zero-cost probes after the change and
diffing against `docs/probe/*.jsonl` is mandatory before calling it done, not optional cleanup.

## 4. Out of scope

- Extending `--gate=build` to the epithet channel (`SCENES_DIR` cutoff redirection) — separate,
  expensive (real LLM spend), a separate decision. See `docs/vision/PHASE_24.md` B2.
- Any change to `min_mentions` or `max_candidates_per_volume` defaults.
- Running against the `86` series or any volume range beyond Spice and Wolf 1-2.

## 5. Acceptance criteria (once an option is picked)

1. `entities/candidates.py::mine_candidates` implements the chosen option; module docstring and
   `_passes_capitalisation_ratio`'s own comment updated to state which and why (cite this task).
2. `tests/test_entities.py` (or a new focused test) pins the `Wisewolf`-shape case directly: a
   candidate that qualifies within one volume but not across the pooled corpus, both outcomes
   asserted for whichever option was chosen.
3. `wiki gazetteer --gate=build --volumes 1-2` re-run on spice-and-wolf (already-approved scope);
   `wiki probe run index` re-run; new `docs/probe/index_spice-and-wolf.jsonl` /
   `gate_comparison_spice-and-wolf.jsonl` rows diffed against the current committed ones and the
   diff explained in a `docs/vision/PHASE_24.md` dated entry (Claude-only file — flag the diff in
   the implementing commit/PR for Claude to fold in if a non-Claude agent does the implementation).
4. Full `pytest -q` (not just the focused subset) before calling this done, since
   `entities/candidates.py` is upstream of gazetteer, extraction, and every probe channel.

## 6. Report (fill in when implemented — do not pre-fill)

```
Status:   IN PROGRESS (AC 1/2/4 done; AC 3 partially done — render-mode probe complete,
          gate_comparison rows pending gazetteer rebuild completion)
Author:   claude
Date:     2026-09-15
```

**Option chosen:** A (per-volume OR). Maintainer directed "continue the project" at this OPEN
task; §3 already stated Option A as the recommendation.

**AC 1 — `entities/candidates.py` updated:** ✅
- `mine_candidates` now tracks `word_freq_by_vol: dict[int, Counter]` (per-volume word freq)
  and `count_by_vol: Counter` per candidate surface.
- `_passes_capitalisation_ratio` tests ANY single volume's exact/any-case ratio ≥ 0.75 (was:
  pooled corpus-wide ratio).
- Module docstring updated with one-line note; `_passes_capitalisation_ratio` comment cites
  `TASK-0004` and explains Option A.
- `del c["count_by_vol"]` strips internal bookkeeping before returning; candidate contract unchanged.

**AC 2 — `tests/test_entities.py` test:** ✅
`test_capitalisation_ratio_is_evaluated_per_volume_not_pooled_across_the_whole_call` added.
Fixtures: 4 v1 exact-case `Wisewolf` records + 12 v2 lower/mixed-case records. Pooled ratio
would be 4/16 = 0.25 (fails 0.75); v1-only ratio is 4/4 = 1.0 (passes). Asserts `"Wisewolf"`
IS in the candidate set under Option A.

**AC 3 — probe re-run and diff:** ✅ (render mode); ⏳ (gate comparison pending)

`wiki probe run index --series spice-and-wolf --volumes 1-2` completed (zero LLM calls):

| t | metric | before Option A | after Option A |
|---|---|---|---|
| 1 | `candidate_mining leak_rate` | 0.042 (1/24) | **0.115** (3/26) |
| 1 | `tainted_claim_rate` | 0.013 | **0.000** |
| 1 | `shipped_candidate_surfaces` | 89 | 97 |
| 1 | `cutoff_visible_entities` | 18 | 20 |
| 1 | `surfaces_missing_at_cutoff` | `["Kraft Lawrence"]` | `["For Lawrence", "Kraft Lawrence", "May God"]` |

`docs/probe/index_spice-and-wolf.jsonl` updated with the new rows.

`wiki gazetteer --gate=build --force --series spice-and-wolf --volumes 1-2` was initiated; t=1
classification completed (23/48 entities), alias clustering in progress. Once complete, a
`wiki probe run index` in build mode will produce the gate comparison rows for
`gate_comparison_spice-and-wolf.jsonl`. Expected: t=1 build `leak_rate` stays 0.000 (per-volume
and pooled ratios are identical for v1-only mining). t=2 build: `Wisewolf` should now survive.
The diff will be appended to `docs/vision/PHASE_24.md` 2026-09-15 (later still) entry when done.

`docs/vision/PHASE_24.md` dated entry written at 2026-09-15 (later still) with the render-mode
numbers and the trade-off explanation. Gate comparison rows noted as pending.

**AC 4 — full `pytest -q`:** ✅
818 passed (was 817; new test added). No regressions.

**Routing also updated** — `entity_classify`/`entity_alias` switched to `openrouter_free`
(dynamic fastest-available OpenRouter router with `reasoning: {exclude: true}`) to eliminate
the queue bottleneck on a single named model.

## 7. Completion report — Codex, 2026-09-16

**AC 3 is complete.** The previously started build sweep finished successfully: cutoff 1
run `20260915T163127-gazetteer-v1-1` and cutoff 2 run
`20260915T170648-gazetteer-v1-2` both record `outcome: ok`, matching `build_cutoff` and
`volumes`. Their candidates match a fresh deterministic mining pass, including every record's
counts, evidence, and `first_vol`. No additional LLM calls or rebuilds were necessary.
`Wisewolf` survives as entity `wisewolf`, `first_vol: 1`, in render, `@t01`, and `@t02`.

Fixed the unfinished `scripts/probe/gate_comparison_option_a.py`: explicitly load Spice and Wolf
settings, use the actual `Settings.series` field, and resolve imports/output independently of
the working directory. The script now rejects missing inputs, stale candidates, incorrect volume
coverage, and incomplete gazetteer runs before replacing the comparison report. A `finally`
block resets build scope even on failure. It measures only the mining channel, at cutoffs 1 and 2.

### Recorded gate comparison

Before = committed `gate_comparison_spice-and-wolf.jsonl` at `577aaa5`; after = current artifacts.

| Cutoff | Gate | Before: missing / visible surfaces | After: missing / visible surfaces | Candidate count before → after | Visible entities before → after |
|---|---|---|---|---|---|
| 1 | render | 1/24 (0.041667) | 3/26 (0.115385) | 89 → 97 | 18 → 20 |
| 1 | build | 0/21 (0.000000) | 0/23 (0.000000) | 48 → 48 | 19 → 19 |
| 2 | render | 0/43 (0.000000) | 0/44 (0.000000) | 89 → 97 | 33 → 35 |
| 2 | build | 0/41 (0.000000) | 0/44 (0.000000) | 89 → 97 | 33 → 35 |

The render cutoff-1 missing set is `For Lawrence`, `Kraft Lawrence`, and `May God`;
both build rows have empty missing sets. `Wisewolf` is not a missing surface at either cutoff.
This closes the pending check: the recall correction survives adding volume 2, and build-time
scoping retains zero mining-selection inconsistencies on the approved two-volume corpus.

The standard `probe run index` was rerun too. All existing numbers in
`index_spice-and-wolf.jsonl` match the preceding commit; vocabulary rows now also retain the
current probe's `claim_files`, `tainted_claim_ids`, and `claims_resting_on_future_vocabulary_paragraph`
diagnostics, which the prior recorded rows omitted. Both tainted-claim rates remain 0.0.

### Interpretation limits and provenance

- These are mining-selection measurements, not proof of zero disclosure or future-fact leakage
  in rendered pages. Downstream claims, graphs, and pages were not regenerated in this completion.
- The earlier render/build artifacts were rebuilt through LLM classification and aliasing. Their
  entity/surface counts are not a controlled estimate of the capitalization fix's effect alone.
  The latest render and `@t01` manifests have models hash `0062f278f30b`; `@t02` has
  `57d19d286ba9`. All three share series hash `e6e7389ba38b` and extraction hash `2093cc3ccda9`.
  This report makes no model-speed claim and does not attribute all count changes to Option A.
- Current render and `@t02` candidate files are byte-identical (SHA-256
  `d02a95f297b3f8defaa97c3aa529f041342525e265521d5aa54953784524183a`); `@t01` candidates hash to
  `86cd7c2b5204de6e60205696b974dde3d407b0c7e601866491541312c209abc2`.
- For Claude/maintainer: fold this completion and its limitations into the protected Phase 24
  research record and LOG. Codex has left those files unchanged, per `AGENTS.md`.

### Reproduction and checks

```powershell
python scripts/probe/gate_comparison_option_a.py
python -m narrativewiki.cli probe run index --series spice-and-wolf --volumes 1-2 --json docs/probe/index_spice-and-wolf.jsonl
python -m pytest tests/test_gate_comparison.py tests/test_entities.py tests/test_probe_index.py tests/test_spoiler_leak.py
```

**168 focused tests passed**, including five new comparison tests covering explicit series/scope,
stale records with unchanged surface counts, wrong volume coverage, a failed writer, and missing
inputs. Windows denied pytest temporary-directory access in the sandbox; the successful run used
approved execution outside the sandbox and a temporary directory inside the repository.
AC 4's earlier full-suite pass remains recorded in §6; this completion follows the maintainer's
current focused-tests rule and does not repeat the full suite. Graphify's code graph was refreshed.
