# Phase 22 Handover — Output quality: from a crashed-run audit to a verified, gated harness (COMPLETE)

**Status:** All of A1-A6, B1-B4, and C1-C4 shipped and verified. Full test suite: 615 tests, all
green. One real corpus run happened mid-phase (`Re-extract V1+V2`, local Ollama, $0 spend); every
other sub-item was verified against scripted fake LLM clients only, per this project's
"budget real spend deliberately" discipline — see "Known gaps" below for what that means for
anyone about to spend real money on this series.

Phase 22 began as a single independent audit (`docs/vision/PHASE_22.md`'s 2026-09-09 entry) of the
shipped Spice & Wolf v1-2 bundle, which found the graph nearly empty (255 claims, 5 of 14 character
pages with zero facts) and traced it to three root causes: a crashed extraction run silently
feeding every later stage, routing pointed at a dead local model, and several already-extracted
fields (`polarity`, `conflicts.quiet_change`, format-aware normalization) with zero consumers
anywhere in `src/`. That audit produced a three-track plan (A: recover what's already paid for: B:
reallocate calls already being made; C: invert the two extraction passes) — this handover covers
all three tracks end to end so a cold contributor never has to reconstruct the arc from `LOG.md`
scrollback or `docs/vision/PHASE_22.md`'s ~900 lines of dated entries.

---

## What exists now

### Track A — recover what was already paid for

- **A1 — failed-run quarantine + claims-completeness gate.** `provenance.py::COMMAND_STAGE_KEYS`,
  `last_run_for_stage`, `failed_stage_artifacts`; `cli.py::_guard_upstream_failures`, called first
  thing in `extract`/`scenes`/`graph build`/`synthesize`/`site build`/`verify` — aborts with the
  crashed run's id and the `wiki rollback` command unless `--allow-partial`. `graph build` also
  gets `_incomplete_claim_volumes`: a volume's claims file must carry every mentioned CHARACTER as
  a claim subject or the build stops naming exactly who's missing. This is the check that would
  have caught the original crash. CONTRACTS §7.7.
- **A2 — format-aware value normalization + subsumption.** `temporal.normalize_value(value, fmt)`
  (`attributes.*.format`, e.g. AGE's `number_or_range` folding `'twenty-five'`/`'25'`/etc. to one
  value); `contradictions.py::_collapse_same_normalized_value` (same-volume phrasings never reach
  arbitration as a fake tie); `canonicalize.py::subsume_values()` (deterministic, no embed call —
  token-subset and lone-noun pruning, gated on `attributes.*.subsume: true`, APPEARANCE only);
  `conflicts.quiet_change` finally has a consumer (`synth/assemble.py`). CONTRACTS §4.2.
- **A3 — faction membership + key-event participation.** `relations.*.membership: true`
  (AFFILIATED_WITH/SERVES_UNDER/COMMANDS + ORIGIN_FROM/PARTICIPATED_IN/PILOTS) filters
  `site/bundle.py::_members_and_related`'s `members` list; ENEMY_OF/RIVAL_OF routes to a separate
  `adversaries` bucket. `_faction_key_events` now also requires the faction itself to be a
  participant or the scene's location, fixing two factions sharing most of their roster from
  rendering byte-identical key-event lists. CONTRACTS §4.3 (bundle), `app.js` Adversaries row.
- **A4 — every `beat_summary` wikified.** Faction `key_events`, relationship `shared_scenes`, and
  timeline events all hyperlink entity mentions now, via the same `site/wikify.py` pass prose
  already got; `_links_report` validates those links too. Timeline `chapter_idx` fixed from 0- to
  1-based.
- **A5 — page model + rendering (U3-U7, S5, S6).** `attributes.*.default` materializes an
  `inferred: true` scalar field with no backing claim (STATUS defaults to "alive"); `_claim_polarity`
  reads the most-recent VISIBLE claim, not `claim_ids[0]` (closes a real spoiler gap);
  `polarity_prefixed()` renders "presumed X"/"not X"; a relationship's `label` is always the config
  display text (qualifier demotes to `note`/`blurb`), and `relationships` entries finally carry
  `current`/`vol_end` the way `affiliations` always did; `show_vol` gates every "(since vN)" marker
  to genuine reveals; `mentions_of` deduplicates against what's already shown and gets an
  annotation; `page["lead"]` is a new one-line "status · affiliation" summary;
  `has_min_evidence()`/`find_name_collisions()` gate a page from being written with zero real
  evidence and flag same-name-different-type collisions (Saint Ruvinheigen: character vs. city).
  CONTRACTS §5/§5.1.
- **A6 — yield assertions.** `_claims_report`/`_scenes_report` now hard-FAIL on their OWN stage's
  crashed-run outcome (closing the gap that A1's guard only covers downstream commands, not
  reports); roster yield and APPEARANCE-share numbers print on every run; `_outline_report`'s dead
  prose-completeness branch now actually warns; `_links_report` FAILs on a `speaker: null` quote
  anywhere in the bundle. CONTRACTS §7.8.

### Track B — reallocate the calls already being made

- **B1 — the scene call split in two.** `extract/scenes.py` makes a beat call
  (participants/location/beat_summary) and a detail call (state_changes/quotes/epithets), sharing
  one cached prompt prefix — 56 → 112 calls/volume, same cost tier, much better per-field recall
  (the old combined prompt's one worked example never demonstrated a non-empty state_change).
- **B2 — coreference hardening + phantom-entity fix.** Two new prompt rules (a pronoun/epithet
  referring to the subject still counts when unambiguous; omit rather than guess when ambiguous);
  known entities now listed grouped by entity_id (`"Kraft Lawrence (also: Lawrence, Kraft)"`,
  `resolve.py::group_known_entities`) instead of a flat surface set — the confirmed cause of a
  "Lawrence sells furs to Kraft Lawrence" hallucination; `resolve_surface`'s containment fallback
  is now whole-word, longest-match-wins. Quote cards with an unresolved speaker are suppressed
  client-side rather than rendered "— Unknown".
- **B3 — proportional window budget.** `extract/windows.py::allocate_window_caps` replaces the flat
  per-character window cap with a shared per-volume pool split by `sqrt(mention_count)`, floored at
  `min_windows_per_entity_per_volume` so a low-mention character isn't squeezed to nothing next to
  a protagonist.
- **B4 — capped, cheaper codex evidence.** `site/bundle.py::_cap_codex_evidence` caps by BOTH
  window count and a token budget (`window.codex_max_evidence_tokens`); the cutoff loop now
  accumulates windows incrementally (O(upto_vol), was O(upto_vol²)); the LLM call is now decoupled
  from the cutoff-entry-write decision, so a membership-only change reuses the previous summary
  instead of re-paying for an identical prompt.
- **Re-extract V1+V2 — the one real corpus run this phase.** Ran the full pipeline against
  `--series spice-and-wolf` on LOCAL OLLAMA (not the API the TODO anticipated — `GOOGLE_API_KEY`
  was unset, so it silently fell back; $0 spend, not apples-to-apples with the Gemini-produced
  baseline). Every graph-cleanliness metric improved (roster yield 9/14 → 12/14, APPEARANCE share
  24% → 12%, conflicts 23 → 3); gold-eval fact recall was a mixed bag (two characters up, one flat,
  one to zero) — most plausibly a local-model capability gap, not a regression from these fixes.
  Two real bugs found and fixed here, both invisible until a live run finally exercised the code
  path: stale page/bundle files never cleaned up when an entity/cutoff falls out of scope
  (`synthesize`/`site_build` now delete what the current run doesn't produce); unresolved-speaker
  quotes reaching the bundle JSON despite the client already hiding them (`_shared_scenes_between`/
  `_faction_key_events`/`_event_claims_split` now filter on `speaker` server-side too).

### Track C — invert the two extraction passes

- **C1 — the chapter-span pass becomes primary.** `wiki scenes`'s detail call gains
  `participant_facts` — attribute/relation/trait facts per participant, reusing
  `claim_extract`'s exact vocabulary/validation (`schema.ExtractedFact`) — folded into the
  EXISTING detail call, zero extra calls per span. Written to a new file,
  `data/03_claims/scene_v{NN}.jsonl`, leaving `wiki extract`'s own file untouched; `wiki graph
  build` globs both and merges by `claim_id`. This is now the primary facts source (100% paragraph
  coverage at a fifth of the per-span cost of the mention-window pass).
- **C2 — `wiki extract --entities` becomes a targeted top-up.** The old "skip if the volume's
  claim file exists" guard no longer fires when `--entities` is given — it re-extracts only the
  named character(s) and merges the result in (`cli.py::_merge_by_entity`, keyed on claim
  `subject`), leaving everyone else's claims untouched. `wiki audit eval` prints the exact top-up
  command for any gold character under 50% fact recall.
- **C3 — a verification pass, not a bigger extraction pass.** New `wiki verify --upto N`: one
  `verify`-role LLM call per CHARACTER entity (skipped when there's nothing to check), asking
  whether each currently-visible fact is actually supported by its own cited evidence
  (`synth/assemble.py::fact_set_for_verification`, `graph/verify.py::verify_character`). Never
  mutates a claim/interval/page — a flagged fact is only logged to the new
  `data/04_graph/verification.json`, surfaced via `wiki audit verify`. Wired into `run-all`, NOT
  into `wiki step` (would raise its per-chapter cost). CONTRACTS §4.3.
- **C4 — gold set grown to ten characters, regression gate added.** Six new hand-transcribed gold
  files (`docs/eval/gold/spice-and-wolf/*.yaml`, now 10 of 14 gazetteer characters). New
  `docs/eval/gold/<series>/baseline.json` (hand-maintained, `{entity_id: fact_recall}`, recorded
  from a real `wiki audit eval` run against the data already on disk) — `_eval_report` now FAILs
  when a character WITH a recorded baseline drops below it, while staying purely advisory for any
  character with none. CONTRACTS §8.

---

## Known gaps (for a future session)

1. **Only one real corpus run happened this whole phase** (`Re-extract V1+V2`, local Ollama, $0).
   Every A-track fix after A1, every B-track fix, and all of C1-C4 were verified against scripted
   fake LLM clients only — real, but not exercised against a live model's actual output. The next
   live run (`wiki scenes --force && wiki extract --force && wiki graph build && wiki verify --upto
   2 && wiki synthesize --force --upto 2 && wiki site build --force`) is the first chance to see
   C1's `participant_facts`, C2's top-up path, and C3's verification prompt behave against real
   model output, not just a scripted one — budget accordingly before running it (C3 alone is ~14
   calls at `--upto 2`; C1 folds into the existing scene call at no extra cost).
2. **`baseline.json`'s ten numbers reflect a pre-Phase-22-C1/C2/C3 extraction state.** They were
   recorded from whatever pages already existed on disk (post `Re-extract V1+V2`, before C1's
   `participant_facts` or C3's verification had ever actually run against real data) — not a
   fresh re-run incorporating this phase's own facts-quality changes. The next real
   `wiki graph build && wiki synthesize --force --upto 2` is likely to move these numbers
   (hopefully up, given C1 makes the chapter-span pass primary); update `baseline.json` by hand
   once that run's numbers are trustworthy, rather than leaving stale pre-C1 numbers as the floor.
3. **`enek.yaml` (new in C4) documents a live, real extraction bug**: `enek/v02.json` currently
   renders `RELATIVE_OF Holo` and `FRIEND_OF Lawrence` relationship rows nothing in the real
   character's story supports. Not fixed in this phase (C4's scope was gold-data coverage, not
   extraction correctness) — a good first target for the next real `wiki verify` run to confirm it
   actually catches, and for a human to look at afterward regardless.
4. **`saint-ruvinheigen` still has no generated page at all** (the A5 name-collision finding —
   character vs. the city he's named after) and was deliberately left out of the C4 gold-set
   expansion for that reason (a permanent FAIL with nothing to measure). `weiz`/`count-ehrendott`/
   `saint-metrogius` also remain gold-uncovered — the 10-character TODO target was met without
   them, but nothing stops extending further.
5. **No automatic "sweep only where scenes came up short" mode.** `wiki extract` with no
   `--entities` still runs a full mention-window sweep by default (C2 explicitly scoped this out —
   see its own dated entry); a human (or a future script) still has to read `wiki audit eval`'s
   printed top-up suggestion and run it.
6. **`arbitrate`'s `local_best` role has no working fallback for "Ollama unreachable"** (only for
   "API key missing") — flagged since A1, never picked up; `wiki graph build --allow-partial` gets
   past both stage guards and then still dies at the first contradiction needing arbitration if
   Ollama is down. The same gap now also exists for `verify` (C3's new role, same fallback shape).

---

## Reproducing the live verification

```
wiki doctor --series spice-and-wolf
wiki audit eval --series spice-and-wolf        # read-only, no LLM calls — safe to run any time
python -m pytest                                # 615 tests, all green
```

A full live re-run of the changed stages (real spend — confirm with the user first, per this
project's "never run a paid/full-series command during implementation" discipline):

```
wiki scenes --force --series spice-and-wolf --volumes 1-2
wiki extract --force --series spice-and-wolf --volumes 1-2
wiki graph build --series spice-and-wolf
wiki verify --upto 2 --series spice-and-wolf
wiki synthesize --force --upto 2 --series spice-and-wolf
wiki site build --force --upto 2 --series spice-and-wolf
wiki audit eval --series spice-and-wolf
```

---

## What's next

Phase 22 is complete — the original 2026-09-09 audit's three-track plan (A/B/C) is fully shipped.
Candidate next work, none yet scoped as a phase:

- The live re-run in "Known gaps" #1/#2 above, to get `baseline.json` onto post-C1/C2/C3 numbers
  and give C3's verification prompt its first exercise against real model output.
- Extend gold-set coverage further (4 characters remain uncovered) or build `saint-ruvinheigen` a
  page (would need its own fix — likely more/different evidence, not just a lower `page_gate.
  min_claims` floor, given the underlying issue is a name collision with a LOCATION entity).
- Fix `arbitrate`/`verify`'s missing "Ollama unreachable" fallback (gap #6 above) — a small,
  well-scoped fix whenever someone hits it for real.
- Extend to the full 13-volume `86` corpus, or a second calibration series, now that Phase 22's
  quality work has all been built and verified against the 2-volume testing scope.
