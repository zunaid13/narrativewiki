# Phase 22 — Output quality: the graph behind the wiki is nearly empty

Append-only. Newest entry at the bottom. See `CLAUDE.md` §4 for the protocol.

---

## 2026-09-09 — Audit of the shipped Spice & Wolf v1-2 bundle, and the plan it produced

**What:** An independent audit measured `dist/spice-and-wolf/site` and `data/spice-and-wolf/`
directly rather than reading the audit reports (which disagree with the data). Verdict: the site
renders, link integrity is perfect (100 links, 0 broken), ingest is clean, the timeline pages are
the best writing on the site, and **the spoiler invariant holds — zero leaks across every V1
cutoff**. Underneath, 127,155 words produced **255 claims**, 5 of 14 character pages have no facts,
24% of the graph is APPEARANCE noise, and 56 scenes produced 0 state changes and 0 locations.

Eight defects were filed (S1-S8), and the user reported seven more from reading the site (U1-U7).
Every one was re-verified against data on disk before planning.

**Why it matters more than the numbers suggest — three findings that reframe the work:**

1. **A crashed run is still feeding the pipeline.** `_runs/20260904T133513-extract-v1-1/manifest.json`
   records `"outcome": "failed"` (`Cannot reach Ollama`), yet its partial `03_claims/v01.jsonl`
   (77 claims, 2 of the volume's 7 mentioned characters) is what every later stage read. Nothing
   checks upstream outcome: `provenance.py` writes `outcome`, and only `wiki runs` / `calls` /
   `rollback` / `audit run` ever read it. Stage gating is file-existence only. Volume 2, extracted
   by a run that finished, handles comparable minor characters fine — so the five empty pages are
   not an extraction-difficulty signal, they are the crash.
2. **The routing on disk pointed at a dead model.** `claim_extract`/`scene_extract` routed to
   `local_fast` -> `ollama qwen2.5:14b`, and `canonicalize` -> `embed` -> `ollama bge-m3`. Ollama is
   not running here. The V2 claims say `google:gemini-flash-lite-latest` — an ad-hoc `-m` override
   never written back, so the config disagreed with what actually ran. Consequence: **Phase 17's
   embedding-based value canonicalization has been silently no-op'ing**, degrading to exact-string
   bucketing (`contradictions.json`: only 10 variants absorbed across the whole graph). That is a
   large part of why the APPEARANCE noise never collapsed.
3. **Most of what the user asked for already exists and is simply not wired up.** `polarity:
   [asserted, denied, presumed]` is extracted (4 claims carry `presumed`) and rendered by nothing.
   `attributes.*.format`, `confidence.min_for_structured_field` and `conflicts.quiet_change` all
   have **no consumer anywhere in `src/`**. `graph/canonicalize.py` exists but skips every
   `single: true` attribute by design.

**The user's seven issues, with their verified causes:**

- **U1 — pronouns lose information.** No coreference anywhere in `src/`. The prompt never tells the
  model that a fact stated about the subject under a pronoun still counts, so it skips those
  sentences. Decision: fix at the **prompt level only** — no coref model, no new pass, no new calls.
  `docs/handover/PHASE_18.md` already argued whole-chapter spans dissolve most of this; the missing
  piece is telling the model so.
- **U2 — "25 years" (v1) vs "twenty-five years" (v2).** Lawrence has *four* AGE claims: `'25'`,
  `'twenty-five'`, `'twenty-five years old'` (v1) and `'twenty-five years'` (v2). `AGE` is
  `single: true`, which `canonicalize` explicitly skips; the only comparison in the graph is
  `temporal.normalize_value` = `.strip().casefold()`. So the v2 rephrasing reads as a genuine
  narrative change — it is the single `narrative_change` in `contradictions.json`.
- **U3 — unwanted "(since v1)".** Emitted unconditionally by `okf.py:72,79,87,96` and
  `app.js:236,239,281,291`. Compounded by `conflicts.quiet_change` having no consumer: Lawrence's
  `age.changes_later` is correctly `false`, yet `previously: 25 (v1-1)` still prints.
  Decision: show a volume marker **only where a value actually changed**; stable facts render bare;
  spans stay inside history/expandables.
- **U4 — cryptic relationship tags.** `synth/assemble.py:173` is `row["qualifier"] or display`,
  letting unvalidated free text *replace* the config display label. Lawrence's page carries 20 rows
  for 9 people, with four Holo badges reading `Comrade of` / `Friend of` /
  `wife (false identity claimed)` / `fake`, and a Jakob pair reading `Child of` +
  `acquaintance / former master`. `okf.py::_relationship_lines` doesn't even group by person.
- **U5 — "also connected to" with no explanation.** `assemble.py:225` `mentions_of` is raw
  `ppr.personalized_pagerank(top_k=8)` with no type filter; 6 of Lawrence's 8 chips are entities
  already rendered above in Relationships/Affiliations. Unexplained *and* duplicative.
- **U6 — status is null.** Zero STATUS claims exist for Lawrence or Holo. The field is **absent
  entirely** from the page dict (`_build_attribute_fields` skips predicates with no rows), so no
  Status row renders at all.
- **U7 — "dead" vs "presumed dead".** `polarity` is extracted, stored, and read into the page model
  by `_scalar_field` — then rendered by nothing. "presumed dead" is currently indistinguishable
  from "dead", exactly the collapse `config/extraction.yaml`'s own `polarity:` block says must
  never happen.

**Implies (the plan, in three call-neutral-or-negative phases):**

- **Phase A — recover what has already been paid for.** Quarantine failed runs and add a claim-file
  completeness assertion; format-aware value normalization + deterministic appearance subsumption
  (works with or without a reachable embed model); membership-predicate filtering for factions;
  wikify every `beat_summary`; and a deterministic page-model/rendering pass covering U3-U7, a lead
  sentence, section reorder, and a page-existence gate. One re-extraction, then zero new calls.
- **Phase B — reallocate the calls already being made.** Split the scene call in two (a 14B model
  handed a six-field schema over a 4k-token span degrades to the easiest field — 56/56 empty
  `state_changes` is what that looks like); prompt-level coreference hardening + the phantom-entity
  fix; replace the flat 40-window cap with a sqrt(mentions) budget; cap codex evidence.
- **Phase C — invert the two passes.** Make the chapter-span pass primary (it already reads 100% of
  paragraphs for a fifth of the cost), demote mention windows to a targeted top-up, add a
  verification pass rather than a bigger extraction pass, and grow the gold set to ten characters
  and gate on it.

**Decisions taken and NOT taken:**

- **Rejected: adding a coreference model.** It would be a new dependency and a new pass for a
  problem the span pass plus two prompt rules should largely absorb. Revisit only if measurement
  after Phase B still shows pronoun-driven loss.
- **Rejected: synthesizing a default STATUS as a graph interval.** That would fabricate a claim with
  no evidence (violating CLAUDE.md §2) and silently change `claim_set_hash`. The default belongs in
  `config/extraction.yaml` as an `attributes.*.default` key, materialized at
  `synth/assemble.py::_build_attribute_fields` and marked `inferred: true` — spoiler-safe by
  construction, since "alive" is the reader's default at any cutoff and a later death is a claim
  that only appears once the reader reaches it.
- **Rejected: special-casing any predicate by name.** Every new behaviour is driven by a new config
  key, preserving the "rendering is generic" invariant `config/extraction.yaml` opens with.
- **Kept: `canonicalize` still routed at the local `embed` profile.** Phase A's subsumption is
  deterministic and degrades gracefully, so there is no reason to spend API budget on embeddings.

---

## 2026-09-09 — Phase 22 part 1: environment and routing corrected

**What:** The two blockers that made every prior measurement untrustworthy.

1. **The installed `wiki` was running a different project.**
   `%APPDATA%\Python\Python314\site-packages\__editable__.narrativewiki-0.1.0.pth` pointed at
   `G:\UIU classes\Gemini AntiGravity RAG+TKG pipeline\src` — a Phase-18-vintage checkout that
   registers the eval report as `evaluate` (not `eval`) and has no `events`/`outline`/
   `relationships` reports at all. That is the real cause of the long-standing "unknown audit stage"
   error flagged since `docs/handover/PHASE_20.md` — and it means every `wiki` command run from this
   repo was executing the sibling project's code and writing into its data directory. Fixed with
   `pip install -e .` from this directory.
2. **`config/models.yaml` routing** for `claim_extract`/`scene_extract` moved from `local_fast`
   (Ollama, not running) to `google_fast` (`gemini-flash-lite-latest` — the profile that actually
   produced the volume-2 claims), with `local_fast` kept as the fallback so flipping back is a
   one-line change once `ollama serve` is up.

Also fixed `cli.py::audit_cmd`'s stale `stage` help string, which listed 8 of the 11 registered
report stages and omitted `events`, `outline`, `eval` and `relationships`.

**Verified:** `python -c "import narrativewiki; print(narrativewiki.__file__)"` now prints this
repo. `reports.available()` returns all 11 stages and matches the help string exactly (asserted).
`python -m narrativewiki.cli audit eval --series spice-and-wolf` runs for the first time from this
checkout. Full suite green, 474 tests.

**Baseline recorded before any behavioural change** (`audit eval`, in-scope facts only):
Holo 50% (5/10), Kraft Lawrence 22% (2/9), Norah Arendt 20% (2/10), Jakob 11% (1/9).
Graph: 255 claims (v01 77 / v02 178), 23 conflicts (22 extraction_error, 1 narrative_change — the
AGE one), canonicalization absorbed 10 variants across 9 groups.

---

## 2026-09-10 — Phase 22 A1: failed-run quarantine + claims-completeness gate

**What:** The guard that would have caught the original crash before it silently fed five later
stages. `provenance.py` gains `COMMAND_STAGE_KEYS` (a static command -> written-stage-keys table
mirroring the literal `stage_keys=[...]` argument at each `start_run` call site in `cli.py`),
`last_run_for_stage(stage_key)` (newest manifest whose command writes that stage), and
`failed_stage_artifacts(stage_keys)` (the subset of those whose `outcome` is `"failed"`, deduped
by run). No new manifest field — both read only `command` and `outcome`, already written by
`finish()`. `cli.py` gains `_guard_upstream_failures(input_stage_keys, allow_partial)`, called as
the very first thing (right after loading settings, before any file-existence check) in `extract`,
`scenes`, `graph build`, `synthesize` and `site build` — each with its own input stages
(`extract`/`scenes` -> `["gazetteer"]`; `graph_build` -> `["gazetteer", "claims"]`; `synthesize`
-> `["gazetteer", "graph"]`; `site_build` -> `["gazetteer", "graph", "pages"]`). It aborts with the
crashed run's id, its error, and the exact `wiki rollback <id> --yes` command, unless the new
`--allow-partial` flag (also added to all five commands) is given.

`graph build` additionally gets `cli.py::_incomplete_claim_volumes` (a pure, file-free helper,
independently unit-tested): for every volume that already has a `03_claims/v{NN}.jsonl` file,
every gazetteer CHARACTER mentioned in that volume must appear as a claim `subject` there, or the
build stops naming exactly which characters are missing — the literal signature the crashed
`20260904T133513-extract-v1-1` run left (2 of 7 mentioned v1 characters got any claims at all).
`--allow-partial` overrides this check too, reusing the same flag since both mean "I know the
input data may be incomplete, proceed anyway."

**Verified:** `tests/test_stage_guard.py` (24 new tests) — the provenance lookups, the shared
guard in isolation, that each of the five commands calls it with its own correct input-stage list
*before* touching any file, that `--allow-partial` short-circuits without even calling
`provenance.failed_stage_artifacts`, the completeness helper's four edge cases (missing/clean/
not-yet-extracted-volume/non-character-mention), and one end-to-end `graph_build` run against
real-shaped fixture files. Full suite green (498 tests). Then run for real against the actual
repo: `wiki graph build --series spice-and-wolf` now refuses immediately, printing
`20260904T133513-extract-v1-1 (writes extract) failed: ... Cannot reach Ollama ...` and the
rollback command — this IS the crash from the 2026-09-09 audit, caught on the first try against
un-doctored data. `docs/CONTRACTS.md` §7.7 documents both checks.

**Known gaps / not done here:** No re-extraction was run — the plan (see "Implies" above)
explicitly defers "Re-extract V1+V2" until after A2-A5 and B1/B2 land, since prompt edits there
would invalidate the same cache a now-spend would have paid into. So volume 1's 5 missing
characters are still missing; `wiki graph build` (without `--allow-partial`) will keep refusing
until either a rollback+re-extract happens or Phase A/B lands and the planned re-extraction pays
for the fix once. Separately noticed but out of scope for A1: `arbitrate`'s `role: local_best` has
no working fallback for "Ollama not running" (only for "API key missing" — `config/models.yaml`
line 241's own comment), so `wiki graph build --allow-partial` gets past both new guards and then
still dies at the contradiction-arbitration call. Not fixed here; flagging for whoever picks up
routing next.

---

## 2026-09-10 — Phase 22 A2: format-aware value normalization + deterministic subsumption

**What:** The four seams the TODO named, plus the two claim-collapse plumbing changes they
required. `graph/temporal.py::normalize_value(value, fmt=None)` gains `fmt`, driven by
`attributes.*.format` (previously unread by anything); `fmt="number_or_range"` folds spelled-out
numbers to digits and strips trailing unit words (`_normalize_number_or_range`), so AGE's `'25'`,
`'twenty-five'`, `'twenty-five years old'`, `'twenty-five years'` all become `'25'`.
`assign_single_valued` and `assign_multi_valued` both take `fmt` now and normalize through it —
`assign_multi_valued` also switched from exact-string bucketing to `normalize_value` bucketing for
attributes/traits (never for a relation's object, which stays an exact `entity_id`).
`contradictions.py::_resolve_single_valued` gained `_collapse_same_normalized_value`, run on each
same-volume group **before** ranking for arbitration — two phrasings of the identical value now
collapse (highest-confidence claim wins the display value; the rest ride along as
`claim_ids_extra` and still end up in the interval's `claim_ids`) instead of reaching `arbitrate`
as a fake tie; the existing cross-volume comparison a few lines down was already normalize_value-
based and just needed `fmt` threaded in to stop treating a re-phrasing as a `narrative_change`.
`graph/canonicalize.py::subsume_values(observations)` is new: two deterministic (no embed call)
rules over one `(subject, predicate)` group's distinct values — token-SET containment drops a
value fully covered by a longer sibling ("hair" next to "long brown hair"; token sets, not a raw
substring check, so "man" is never swallowed by "woman"), and a lone single-token value is dropped
even with no sibling. Gated on a new `attributes.*.subsume: true` key, added to APPEARANCE only
(the "24% of the graph is APPEARANCE noise" finding) — applied in `build_graph` right before
`assign_multi_valued`. `conflicts.quiet_change` finally has a consumer: `synth/assemble.py::
_scalar_field` now carries a `quiet_change` bool (from `Settings.conflicts_config`), and
`site/okf.py`/`app.js` skip the "previously: ..." line when it's set — `history` itself is
untouched, this is a rendering decision only.

**Verified:** New tests in `tests/test_graph.py` (`normalize_value` on all four AGE phrasings and
a spelled-out range; `assign_single_valued`/`assign_multi_valued` fmt-aware merging;
`subsume_values`'s two rules including the "man"/"woman" false-positive check; three `build_graph`
tests reproducing the exact U2 bug end to end — same-volume AGE phrasings no longer arbitrate as a
false conflict, all four Lawrence phrasings across v1-2 collapse into ONE interval with zero
conflicts, a genuinely different AGE value still arbitrates correctly; one `build_graph` test for
APPEARANCE subsumption with `client=None`, confirming it needs no embed model). `tests/
test_synth_assemble.py` and `tests/test_site_okf.py` get `quiet_change` coverage (flag only set
for configured predicates; "previously:" line actually disappears from rendered Markdown). Full
suite green: 516 tests (was 498).

**Known gaps / not done here:** The planned "Re-extract V1+V2" step is still deferred (per the
"Implies" plan above, until after A3-A5/B1-B2 land) — today's graph.db was built before this
change, so it still reflects the old four-value AGE split until a `wiki graph build --force`
re-run (no LLM cost — arbitration/canonicalization is unaffected for existing single-valued
claims; only the interval-assignment layer changed, which `build_graph` recomputes from
`data/03_claims/` claims already on disk). `PHASE_22.md`'s "Known traps" section already flags
this: normalizing values changes `interval_id`s (hashed from the raw value string) and therefore
`claim_set_hash`, so `wiki synthesize` will regenerate prose for every character touched once a
`graph build` is re-run — budgeted alongside the deferred re-extraction, not spent here.

---

## 2026-09-10 — Phase 22 A3: faction membership filtering + key-event participation requirement

**What:** `site/bundle.py::_members_and_related` no longer treats every relation touching a codex
entity as membership. `config/extraction.yaml` relations gained a `membership: true` flag —
AFFILIATED_WITH/SERVES_UNDER/COMMANDS (the audit's list) plus ORIGIN_FROM/PARTICIPATED_IN/PILOTS
(added so `places`/`tech` codex entries keep their pre-existing "who's associated with this"
behaviour instead of losing their `members` field outright, since none of THEIR real predicates
were in the audit's trio). `_members_and_related` now returns a third value, `adversaries` —
CHARACTER entities related via ENEMY_OF/RIVAL_OF, kept in their own bucket rather than dropped or
folded into `members`. Any relation touching a codex entity that is neither membership-flagged nor
ENEMY_OF/RIVAL_OF (an extraction error under the closed vocabulary) lands in neither list.
`_state_hash` takes `adversaries` as a new optional arg, sparse the same way `key_event_ids`
already was — omitted from the hash payload, not just `[]`, when there are none, so an entry that
never had an adversary edge keeps a cache key byte-identical to before this change.
`_faction_key_events` gained a second filter beyond ">=2 current members co-present": the faction
itself (`entity_id`, now threaded through as a new parameter) must also be a participant of the
scene, or the scene's `location` must be the faction — fixing the Medio/Milone byte-identical-lists
bug, where two factions sharing most of their roster satisfied the old member-co-presence check for
either one regardless of which faction the scene was actually about. `site/templates/app.js`
renders a new "Adversaries" row next to "Members"/"Related" on codex entries (reuses the existing
`.codex-meta-row`/`.pill-list` CSS, no new class). `audit/reports.py`'s links report now resolves
`adversaries[]` entity_ids the same way it already does for `members[]`/`related[]`.

**Verified:** `tests/test_site_bundle.py` — `RELATIONS_CFG` fixture gained `membership: true` on
AFFILIATED_WITH (every existing `_affiliate`-based test depends on this to keep populating
`members`) and a bare `RIVAL_OF` entry; four existing `key_events` tests updated to include the
faction itself in the fixture event's `participants` (the new requirement they now exercise, not
just tolerate); two new regression tests reproduce S1 directly — a co-occurring-members scene the
faction itself is absent from is excluded, and two factions sharing an identical two-member roster
no longer produce identical `key_events` lists (only the faction actually present in the scene gets
it). Four new tests cover `_members_and_related`'s ENEMY_OF-to-adversaries routing, the
membership-flag filter isolating AFFILIATED_WITH from ENEMY_OF on the same entity, and
`adversaries`'s sparse presence/absence in a built codex bundle. Full suite green: 522 tests (was
516).

**Known gaps / not done here:** No re-run of `wiki graph build`/`site build` against real corpus
data — `graph.db`/the bundle on disk still reflect the pre-A3 membership rule until the deferred
"Re-extract V1+V2" step (still waiting on A4-A5/B1-B2, per the plan). `_faction_key_events`'s new
"faction itself must be a participant" check is exercised here only for the `factions` codex kind
(the only kind `max_key_events` is configured for today); if a future phase enables `key_events` for
`places`/`tech`, the `location == entity_id` branch (rather than the participant branch) is the one
that will actually fire for a LOCATION entity, and has no dedicated test yet since no such config
exists.

---

## 2026-09-10 — Phase 22 A4: wikify every `beat_summary`

**What:** The three scene-recap surfaces that render a paraphrase sentence but never hyperlinked
it — a faction codex entry's `key_events`, a relationship pair's `shared_scenes`, and a volume's
`timeline` events — now get the same `site/wikify.py` pass `background`/`personality`/codex
`summary` text already got. `site/bundle.py::_faction_key_events` and `_shared_scenes_between`
each gain `automaton`/`entities_by_id`/`settings` params (all three already in scope at every
caller — `build_codex_bundles` already had them; `build_relationship_bundles` gained a new
`automaton` param to pass through) and wikify `beat_summary` at their own `vol` argument, which is
already the correct per-cutoff value. `_faction_key_events` excludes the faction's own `entity_id`
from linking (matching `_generate_codex_summary`'s self-exclusion); `_shared_scenes_between` has no
single "self" entity, so it excludes nothing. `build_timeline_bundles` gained the same three params
as new *required* positional args (no defaults — every caller, including every test, was updated
directly rather than adding a backwards-compat shim) and wikifies each event's `beat_summary` at
that event's OWN `vol` — the outer per-volume loop variable, never the function's `upto_vol`
parameter, since a volume's timeline is permanently fixed regardless of what cutoff a later rebuild
runs at (its own docstring's "no state-hash question" guarantee would break otherwise). Also fixed
while here: `build_timeline_bundles`'s outer `chapters[].chapter_idx` is now 1-based (was the raw
0-based `graph/events.py` value, which `app.js` rendered directly as "Chapter 0" for a volume's
first chapter) — the per-event `chapter_idx` `_faction_key_events`/`_shared_scenes_between` carry
is untouched, since no renderer displays it.

Client-side, `app.js::renderSceneCard` (shared by all three surfaces) now calls `renderLinkedText`
on `beat_summary` instead of `escapeHtml` — without this, the Markdown links baked into the bundle
would have rendered as literal `[text](route)` strings. Also per the TODO's "timeline cosmetics":
the per-card "Volume N" badge is dropped (each surface already scopes/labels its own volumes — a
relationship/codex page via its cutoff picker, a timeline page via its own page heading — so
repeating it on every card added nothing), and the participant pill row is now sorted by display
name (`nameFor(...).localeCompare(...)`) instead of raw insertion order.

`audit/reports.py::_links_report` (`check_links_in_text`) now also validates the Markdown links
inside `key_events[].beat_summary`, `shared_scenes[].beat_summary`, and every timeline event's
`beat_summary` — previously only `prose.*`/codex `summary` were checked, so a broken link in a
scene recap would have shipped silently.

**Verified:** 3 new tests in `tests/test_site_bundle.py` — `_faction_key_events`'s self-exclusion
(`test_codex_bundle_key_events_beat_summary_wikified_excluding_self`), `_shared_scenes_between`'s
two-sided linking with no exclusion (`test_relationship_bundle_shared_scene_beat_summary_is_wikified`),
and `build_timeline_bundles`'s per-event wikify plus the new 1-based `chapter_idx`
(`test_timeline_bundle_wikifies_beat_summary`, and `test_timeline_bundle_groups_events_by_volume_
and_chapter`'s existing assertion updated from `[0, 1]` to `[1, 2]`). Every pre-existing
`build_relationship_bundles`/`build_timeline_bundles` call site in the test file (11 call sites)
was updated for the new required params — no defaults were added, per this project's
no-backwards-compat-shim rule. Full suite green: 525 tests (was 522). `docs/CONTRACTS.md` §6.1,
§6.4, §6.5 updated with the wikify/exclusion/chapter_idx details.

**Known gaps / not done here:** No live re-run against corpus data — `graph.db`/the bundle on disk
still reflect pre-A4 unlinked `beat_summary` text and 0-based timeline chapter numbers until the
deferred "Re-extract V1+V2" step (still waiting on A5/B1-B2, per the plan). A5 (page model +
rendering: U3-U7, S5, S6) is next.

---

## 2026-09-10 — Phase 22 A5: page model + rendering (fixes U3-U7, S5, S6)

**What:** All deterministic, no new LLM calls, no cache invalidation. `synth/assemble.py`:
(U6) `attributes.*.default` (STATUS -> `"alive"`) materializes a scalar field with no backing
rows at all, marked `inferred: true`, never touching `claim_set_hash`. (U7) `_claim_polarity`
now takes `upto_vol` and picks the polarity of the MOST-RECENT claim among an interval's
`claim_ids` whose own `first_vol <= upto_vol` — not `claim_ids[0]`, which could freeze a stale
"presumed" forever or, worse, read a not-yet-visible claim's polarity outright (a real spoiler
gap, since a defensively-merged interval's `claim_ids` are not all guaranteed <= the cutoff);
`polarity_prefixed()` renders "presumed X"/"not X" instead of collapsing to plain "X". (U3)
every scalar/list attribute value and every `relationships` entry gains `show_vol` — true only
when `since_vol` is later than the entity's own `first_vol`, so a "(since v1)" marker only
appears for a genuine reveal. (U4) a relationship's `label` is always the config `display` text
now (never overridden by free-text `qualifier`, the audit's "wife (false identity claimed)" /
"fake" badges); `qualifier` demotes to `note`, combined into `blurb` via the predicate's optional
`relations.*.blurb` template or the generic `"{label} — {note}"` fallback — plus the sibling fix:
`relationships` entries now carry `current`/`vol_end` (the same closed/live scrub `affiliations`
already had), since the old code computed `closed` for affiliations but silently discarded it
for relationships, rendering a `conflicts_with`-superseded relation as if still live. (U5)
`mentions_of` is now `[{entity_id, note}]` — filtered to drop anyone already in
`fields.affiliations`/`relationships` (was 75% duplicative on the audited page), annotated via
`relations_between` or `shared_events_at`; needs a new `events_conn` param. (S6) `page["lead"]`
(`_build_lead`) is a "status · primary affiliation" one-liner, needs a new `entities_by_id`
param; paired with `config/extraction.yaml` `page_outline`'s new `lead` section (`kind: lead`,
`order: -1`) — `site/okf.py::render_markdown` special-cases it (no `## ` heading);
`app.js::renderCharacter` renders it above the infobox/body layout and now assembles
`infobox + body` (was `body + infobox`) so identity/status reads first. (S5)
`has_min_evidence()` (config `page_gate.min_claims`, default 1) gates `wiki synthesize` from
writing a page with zero real evidence at all — reuses `_claim_set_hash`'s own interval-id query,
factored out as `_visible_interval_ids`; `find_name_collisions()` is a separate, non-cutoff-scoped
gazetteer scan that prints a build-time warning when two different-typed entities share one
canonical name (Saint Ruvinheigen: character vs. the city he is named for — `entities/alias.py`
already guarantees distinct `entity_id`s via a numeric suffix, so this is a name collision, not
an id collision; detection only). `build_relationship_bundles`/`build_timeline_bundles` were
already Phase 22 A4's `automaton`/`entities_by_id`/`settings` threading — untouched here;
`site/bundle.py::build_pages_bundle` additionally wikifies `page["lead"]` the same way it already
wikifies prose text. `audit/reports.py::_links_report` also validates `lead`'s links and reads
`mentions_of`'s new shape; `_pages_report`'s sparse-page detector now excludes `inferred` fields
from its coverage count (STATUS always existing now would otherwise make it blind to the exact
S1-type "zero real evidence" symptom it exists to catch).

**Verified:** 21 new tests (`test_synth_assemble.py`, `test_site_okf.py`, `test_audit_reports.py`
— the last file's first-ever coverage of `_pages_report`). Every existing `assemble_page` call
site (17 in tests, 2 in `cli.py`) updated for the new required `events_conn`/`entities_by_id`
params — no defaults added, per this project's no-backwards-compat-shim rule. Full suite green:
546 tests (was 525). `docs/CONTRACTS.md` §5/§5.1 updated with every new field
(`show_vol`/`inferred`/`note`/`blurb`/`current`/`vol_end`/`lead`) and the page-gate/name-collision
checks.

**Known gaps / not done here:** No live re-run against corpus data — still waiting on the
deferred "Re-extract V1+V2" step (A6/B1-B2 not done yet, per the plan). `_build_lead`'s "primary
affiliation" clause names only one affiliation (the first `current` one, or the first ever) —
multiple simultaneous current affiliations are not all listed. The name-collision check is
detection-only; no display site actually disambiguates two same-named, different-typed entities
yet (roster, search, pills all still show the bare canonical name). A6 (yield assertions, S7) is
next.

---

## 2026-09-10 — Phase 22 A6: yield assertions (fixes S7)

**What:** Four numbers `audit/reports.py` now prints (or hard-fails) instead of requiring a
one-off hand-audit to notice, plus two previously-silent holes closed. `_claims_report` and
`_scenes_report` each call `provenance.failed_stage_artifacts(["claims"])` / `(["scenes"])`
directly and FAIL (crashed run id, error, `wiki rollback ... --yes`) if their OWN stage's last
writer recorded `outcome: failed` — closing the gap that §7.7's `_guard_upstream_failures` (A1)
only covers downstream CLI commands, not the diagnostic report itself, which is exactly how the
2026-09-09 audit's crash shipped unnoticed by anything in this repo. `_claims_report` also prints
**roster yield** (share of gazetteer CHARACTER entities with `>= page_gate.min_claims` claims —
reusing A5's existing threshold rather than adding a second one) and **APPEARANCE share of all
claims** (the "24% of the graph is APPEARANCE noise" number). `_scenes_report` prints the share of
scene records with at least one of `location`/`state_changes`/`quotes` (the "56 scenes produced 0
state changes and 0 locations" number). None of these gate anything new — they are numbers on
every run, not a new config key or a new gate.

The two "known holes" the TODO named: `_outline_report`'s prose-completeness branch computed a
condition and then did nothing with it regardless of the result (dead code) — it now warns when
one prose section is `None` while a sibling section on the same page has content (a real
generation gap), while an all-`None` page (a legitimate zero-evidence character) still prints
nothing. `_links_report` gained `check_quote_speakers()`, called at all four quote-bearing sites
in `data/06_bundle/` (a page's own `quotes`, a codex `key_events[].quotes[]`, a relationship pair's
`shared_scenes[].quotes[]`, a timeline event's `quotes[]`) — a `speaker: null` quote now FAILs the
report instead of shipping silently, which is exactly what happened with the 9 such quotes the
2026-09-09 audit found already on the live Spice & Wolf bundle. This does not fix extraction (that
remains Phase B2's job — suppress an unresolved-speaker quote at the source); it only stops the
report from vouching for a bundle that already has one.

**Verified:** 11 new tests in `tests/test_audit_reports.py` (this file's first-ever coverage of
`_claims_report` and `_links_report`) — roster-yield/APPEARANCE-ratio printing, the upstream-
failure hard-fail for both `_claims_report` and `_scenes_report` (monkeypatching
`provenance.failed_stage_artifacts` directly, matching `test_stage_guard.py`'s own pattern rather
than writing real run manifests), the structured-field yield line, the outline dead-loop fix's two
branches (warns on asymmetric `None`, silent on all-`None`), and one null-speaker FAIL test per
quote-bearing site plus one all-resolved OK sanity test. The four pre-existing `_scenes_report`
tests that now also exercise the new upstream-failure check were given their own
`monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")` for hermeticity — without it they
would read this repo's real (currently empty) `data/_runs/` directory, which is exactly the kind
of hidden coupling to real disk state this phase's own A1 work exists to catch. Full suite green:
557 tests (was 546). `docs/CONTRACTS.md` §6.4 and new §7.8 document all of the above.

**Known gaps / not done here:** No live re-run against corpus data — still waiting on B1/B2 before
the deferred "Re-extract V1+V2" step (per the plan, prompt edits there would invalidate the same
extraction cache a now-spend would pay into). B1 (split the scene call) and B2 (coreference
prompt hardening + phantom-entity fix) are next.

---

## 2026-09-10 — Phase 22 B1+B2: split the scene call, coreference hardening, phantom-entity fix

**What:** Batched together per the plan (both edit prompts, so both would invalidate the same
extraction cache — landing them together means only one re-extraction spend is needed later, not
two). No live extraction run against corpus data happened in this work; everything below is
prompt/code/test changes verified against scripted fake LLM clients only.

**B1 — `extract/scenes.py` now makes two calls per span, not one.** `scene_schema.py`'s single
`SceneExtractionResult` split into `SceneBeatResult` (participants/location/beat_summary) and
`SceneDetailResult` (state_changes/quotes/epithets); `_SYSTEM_TEMPLATE` split into
`_BEAT_SYSTEM_TEMPLATE` (no predicate vocabulary needed at all now) and `_DETAIL_SYSTEM_TEMPLATE`
(full predicate vocabulary, now with **three** worked examples — one per field — where the old
combined prompt's single example never actually demonstrated a non-empty state_change or
epithet). Both calls share an identical passage-text/known-entities prefix
(`_user_prefix`), diverging only in the final "Report ..." line, so a caching provider reuses that
prefix instead of paying for it twice. `_GENERATION_OPTIONS` split into
`_BEAT_GENERATION_OPTIONS` (`num_predict: 2048`) and `_DETAIL_GENERATION_OPTIONS` (`num_predict:
6144`, unchanged) — the beat call's response is much shorter. A scene's `confidence` is now
`min()` of the two calls' self-reported confidences (56 → 112 calls per volume, same conservative
posture as everywhere else in this pipeline: discount on the lower half rather than average it
away). `data/02b_scenes/v{NN}.jsonl`'s on-disk shape is unchanged (CONTRACTS §3b) — this is
purely an internal call-count/prompt-budget decision.

**B2 — coreference hardening (U1) + the phantom-entity fix (S3).** Three independent fixes:
(1) `claims.py::_SYSTEM_TEMPLATE` gained two rules: a fact about the subject stated through a
pronoun or epithet still counts when the passage makes the antecedent unambiguous (the recall
half), paired with an explicit "omit rather than guess" rule for the genuinely ambiguous case —
so recall doesn't just trade for a new hallucination mode. (2) Both drivers' user prompts now
list other named entities grouped by entity_id (`resolve.py::group_known_entities`, new) as
`"Kraft Lawrence (also: Lawrence, Kraft)"` instead of a flat set of raw surfaces
(`{m["surface"] for m in mentions}`) — this is the actual, confirmed cause of a beat_summary
hallucinating "Lawrence sells furs to Kraft Lawrence": two aliases of one person read to the
model as two different people with nothing tying them together, and `beat_summary` is never
resolved against entities, so no resolution rule downstream could have fixed it. (3)
`resolve.py::resolve_surface`'s fallback replaced raw bidirectional substring containment (which
could misresolve a fragment sharing no whole word with a candidate, e.g. "man" inside "Norman")
with a whole-word name-part rule — a bare "Kraft" now resolves to a "Kraft Lawrence" candidate via
token-set containment, and when more than one candidate qualifies the longest (most specific)
surface wins, not the first one in list order. While in `schema.py`: `_is_usable_fact` compared
`kind` against `_VALID_KINDS` case-sensitively, so a model emitting `"kind": "RELATION"` (rather
than lowercase) silently lost the fact before `claims.py::_lookup_predicate` ever got a chance to
re-derive the true kind from config — fixed by lowercasing `kind` before that check
(`_normalize_kind`). Client-side, `app.js::renderSceneCard` now filters out any quote whose
speaker didn't resolve instead of rendering it with a "— Unknown" byline (a placeholder that reads
as a real, if anonymous, attribution to a reader).

**Verified:** 570 tests total (was 557), all against scripted fake clients — no Ollama/API calls.
New: 4 `resolve_surface` tests (exact-match-still-wins, name-part resolves a bare first name,
longest-match-wins over list order, a bare substring that isn't a whole word is rejected), 3
`group_known_entities` tests, 1 `schema.py` uppercase-`kind` test, 1 `claims.py` test proving two
alias mention rows for one entity render as one grouped name in the prompt, and in
`test_scenes.py`: the old single `SceneExtractionResult` test split into a beat-result test and a
detail-result test, plus three new tests (exactly two calls per span in beat-then-detail schema
order, both calls share the same known-entities/passage prefix, and the known-entities line groups
aliases the same way claims.py's does). `_ScriptedSceneClient` needed only one change to support
two calls per span: index scripted payloads by `calls // 2` rather than `calls`, relying on
pydantic's default `extra="ignore"` so one combined payload dict still serves both the beat and
detail schema (every existing test already supplied one payload per span, so none needed editing).

**Known gaps / not done here:** Still no live re-extraction run — that is the deferred "Re-extract
V1+V2" TODO item, now unblocked (A2-A5 and B1/B2 have all landed) but deliberately not started in
this session: it is a real, single spend against final prompts, not something to trigger without
asking. `app.js`'s speaker-name link (`nameFor`) is still plain text, not a link to the speaker's
page — out of scope for B2, which only asked to suppress the unresolved case. B3 (proportional
window budget) and B4 (cap codex evidence) are next, followed by the re-extraction step.

---

## 2026-09-10 — Phase 22 B3+B4: proportional window budget, capped codex evidence

**What:** Both local/deterministic, no LLM prompt changes, so unlike B1/B2 neither invalidates the
extraction cache — landed independently of the still-pending "Re-extract V1+V2" spend. All changes
verified against unit tests and scripted fake clients only, no live extraction run.

**B3 — `extract/windows.py` gained `allocate_window_caps(mention_counts, base_cap, floor)`**: turns
the old flat `max_windows_per_entity_per_volume` (40) cap into a shared per-volume pool sized
`base_cap * num_characters`, split across entities proportional to `sqrt(mention_count)`, floored
at `min_windows_per_entity_per_volume` (new config key, default 3) so a low-mention character isn't
squeezed below a flat share just because a protagonist dominates the sqrt sum. `build_windows` gained
an optional `max_windows` arg (overrides the config flat cap — this is what the per-entity share
gets passed through as) and an optional `drops: Counter[str]` that records `window_cap_truncated`
for every window the cap drops — previously invisible, since the truncation happened inside
`windows.py` before `claims.py` ever saw it. `extract/claims.py::extract_volume` now computes
per-character mention counts once and calls `allocate_window_caps` before its character loop,
threading each entity's share through `extract_character_volume` into `build_windows`; the existing
per-character `drops` Counter (already returned to the CLI and printed) now also carries
`window_cap_truncated`, so `wiki extract`'s dropped-reasons line reports it with no CLI change
needed.

**B4 — `site/bundle.py`'s codex evidence pipeline fixed on all three multiplying causes the audit
named.** (1) `_gather_codex_evidence` split into `_codex_windows_for_volume` (one volume's raw,
uncapped windows) and `_cap_codex_evidence` (caps a windows pool by BOTH `max_windows` (5) AND a new
total-token budget, `window.codex_max_evidence_tokens`, default 2000 — a window-count cap alone let
merged windows for a corpus-wide entity like "the Legion" total ~30k tokens for a one-sentence
summary; the densest single window is kept even alone-over-budget, same rule
`windows.py::_shrink_to_budget` already documents). (2) `build_codex_bundles`'s cutoff loop now
accumulates one volume's windows per iteration (`raw_windows = raw_windows + _codex_windows_for_volume(...)`)
instead of re-scanning volume 1..vol from scratch on every cutoff — O(upto_vol) window builds
instead of O(upto_vol^2). (3) The LLM-call decision is now decoupled from the cutoff-entry-write
decision: `_state_hash` (evidence + members + related + adversaries + key_events) still decides
whether a NEW CUTOFF ENTRY is written, per CONTRACTS §6.1's rule that a stale member list must
never be served at a later cutoff — but `_generate_codex_summary` is now only called again when the
evidence-only hash changed; a membership-only change (e.g. a character newly joining a faction with
no new evidence) reuses the previous cutoff's summary text/evidence instead of re-paying for an
identical prompt.

**Config:** `config/extraction.yaml`'s `extraction.window` gained `min_windows_per_entity_per_volume:
3` (B3) and `codex_max_evidence_tokens: 2000` (B4); both read with safe defaults so old config
files without these keys still work.

**Verified:** 582 tests total (was 570) — 8 new in `test_extract.py`
(`allocate_window_caps` proportional/floor/zero-mention/empty-input, `build_windows`'s new
`max_windows` override and `drops` reporting, `extract_volume` wiring a denser entity to a larger
cap than a sparser one via a monkeypatched `build_windows` spy), 4 new in `test_site_bundle.py`
(`_cap_codex_evidence`'s window-count cap, token-budget cap, always-keep-the-densest-window-even-
over-budget, and stable para_id sort), plus a strengthened assertion on the existing
membership-change test proving exactly one LLM call total across two cutoffs and that the reused
cutoff's `summary`/`evidence` match the original verbatim. All against scripted fake clients — no
Ollama/API calls.

**Known gaps / not done here:** The re-extraction cache is untouched by this session (no prompt
changed) — "Re-extract V1+V2" is still the next real-spend step, now with the B3 window-allocation
change and B4 cheaper codex pass both live for whenever that run happens. Phase C (invert the two
extraction passes, C1-C4) not started.

---

## 2026-09-10 — Re-extract V1+V2 (spice-and-wolf) on every A/B-track fix, plus two bugs the live run found

**What:** User go-ahead given for the deferred "Re-extract V1+V2" item. Ran the full pipeline —
`scenes --force` (picks up B1's beat/detail split) → `extract --force` (A2/A3/B2/B3) → `graph
build` → `events-build --force` → `synthesize --force` → `site build --force` — against
`--series spice-and-wolf`, the series the original Phase 22 audit measured. `wiki gazetteer
--merge-epithets` was skipped: 0 epithet mentions were mined this run, so it would have been a
no-op (and the auto-mode permission classifier blocked the call anyway).

**Routing note — this ran on local Ollama, not the API the TODO item anticipated.**
`config/models.yaml` routes `claim_extract`/`scene_extract` to `google_fast` with `local_fast`
fallback; `GOOGLE_API_KEY` in `.env` is present but empty, so every stage silently fell back to
`ollama:qwen2.5:14b`/`qwen2.5:32b` — confirmed via `wiki budget`: 3,248,563 input / 336,050 output
tokens across 1,650 calls, **all free**. This means the before/after comparison below is NOT
apples-to-apples on raw recall — the baseline's claims were produced by `gemini-flash-lite-latest`,
this run's by a much smaller local model — so a recall drop here is a model-capability signal, not
necessarily evidence against the A/B-track fixes. The graph-cleanliness metrics (claims-per-
character coverage, APPEARANCE noise share, conflict count, canonicalization) are a fairer read on
those fixes since they measure extraction-pipeline behavior, not raw model recall.

**Results vs the 2026-09-09 baseline (same audits, `--series spice-and-wolf`):**

| Metric | Baseline (Gemini) | This run (local qwen2.5:14b) |
|---|---|---|
| Total claims | 255 (v01 77 / v02 178) | 158 (v01 78 / v02 80) |
| Roster yield (>=1 claim) | 9/14 (5 empty pages) | 12/14 (86%) |
| APPEARANCE share of claims | 24% | 12% |
| Graph conflicts | 23 (22 extraction_error, 1 narrative_change) | 3 (2 extraction_error, 1 narrative_change) |
| Canonicalization | 10 variants / 9 groups | 18 variants / 1 group (one PERSONALITY cluster) |
| Scenes with a structured field | 0/56 (0%) | 21/56 (38%) |
| Event-layer claims | ~0 (0 state changes) | 29 |
| `wiki audit links` | (not run clean before) | OK — 0 broken references |
| Gold-eval fact recall — Holo | 50% (5/10) | 40% (4/10) |
| Gold-eval fact recall — Kraft Lawrence | 22% (2/9) | 22% (2/9) |
| Gold-eval fact recall — Norah Arendt | 20% (2/10) | 30% (3/10) |
| Gold-eval fact recall — Jakob | 11% (1/9) | 0% (0/9) |

Reading this: every graph-cleanliness metric improved, several sharply (roster yield, APPEARANCE
noise, conflict count all moved in the direction Phase 22's A-track fixes targeted; the 18-variant
PERSONALITY canonicalization is A2's subsumption logic visibly working on real data for the first
time). Gold-eval fact recall is a mixed bag (two up, one flat, one down to zero) and net lower
claim volume than the Gemini baseline — most plausibly the local-model capability gap described
above, not a regression these fixes caused; B3/B4 touch window allocation and codex-evidence
caching, neither of which reduces what a well-functioning extraction call would find. Re-running
this same comparison once `GOOGLE_API_KEY` is populated (or another capable API key) would isolate
model quality from pipeline quality — not done here.

**Two real bugs found and fixed, both invisible until this was the first live run to exercise
these code paths against real data (every earlier Phase 22 fix was verified only against scripted
fake clients):**

1. **Stale bundle/page files never cleaned up when an entity/cutoff falls out of scope.**
   `cli.py`'s `synthesize` command's A5 minimum-evidence gate (`has_min_evidence`) skips writing a
   page for a gated cutoff but never touched a page file already on disk from before — so a
   character whose re-extracted claims now correctly fall below the evidence floor (Saint
   Ruvinheigen's v02, Weiz's v01) kept serving a page file from a 2026-09-08 run, in the PRE-A5
   `mentions_of` shape (`["holo", ...]`, bare entity_id strings, not A5's `[{"entity_id",
   "note"}]` dicts) — crashing `_links_report`'s `TypeError: string indices must be integers, not
   'str'`. Same bug, same fix, in `cli.py`'s `site_build`: the character-page-bundle,
   codex-bundle, and relationship-bundle writers each only ever WRITE what the current run
   produces, never delete a file for an entity/pair that dropped out — `saint-ruvinheigen.json`
   survived a full `site build --force` with its stale v02 cutoff still in the bundle. Fixed by
   deleting `pages_dir`/`codex_dir`/`rel_dir` files not present in the current run's output before
   writing — gated behind `wanted_ids is None` for codex/relationships specifically, since
   `--entities` deliberately narrows those two to a subset for a cheap smoke test and must not
   wipe out every entity/pair it didn't touch.
2. **Unresolved-speaker quotes reached the bundle JSON despite the client already hiding them.**
   B2 (2026-09-10, earlier today) taught `app.js::renderSceneCard` to suppress a quote whose
   speaker never resolved rather than render `"— Unknown"`. `renderSceneCard` is the SAME function
   for character-page scene cards AND `relationships/<a>--<b>.json`'s `shared_scenes` — so the
   client-side fix already covered both, but `_links_report`'s `check_quote_speakers` (Phase 22
   A6) treats a null-speaker quote anywhere in `codex/*.json` key_events, `relationships/*.json`
   shared_scenes, or `timeline/*.json` events as a hard FAIL, and none of the three server-side
   quote-building functions (`site/bundle.py::_shared_scenes_between`, `_faction_key_events`,
   `_event_claims_split`) filtered on `speaker` — a documented, deliberate choice in
   `_shared_scenes_between`'s old docstring ("every quote in the scene is included regardless of
   speaker"), never reconciled with A6's audit check because the check was never run against data
   containing an actual null-speaker quote until now (30 of them, in `holo--kraft-lawrence.json`
   and `holo--norah-arendt.json`). Fixed by adding `claim["speaker"]` to the filter in all three
   functions — the quote was already dead weight (nothing renders it), so dropping it server-side
   both fixes the audit and shrinks the bundle.

**Verified:** 585 tests (was 582) — 3 new regression tests, one per fixed function, each asserting
a null-speaker quote is dropped while a resolved one survives. `wiki audit links` clean (0 broken
references) after the fix; before it, the same command crashed with a Python traceback rather than
reporting FAIL, which is itself worth noting as a robustness gap in `_links_report` (an audit
report should never crash on malformed-but-parseable input — it should FAIL with a message) though
not fixed here since the root cause (stale files existing at all) is fixed instead.

**Known gaps / not done here:** No comparison run exists yet with a real API key, so model-quality
vs pipeline-quality is not cleanly isolated in the table above. Phase C (invert extraction passes,
C1-C4) not started. `wiki gazetteer --merge-epithets` was never actually exercised this session
(0 epithets mined, and the call was blocked by the permission classifier) — worth a deliberate
re-check next time a volume mines a nonzero epithet count.

---

## 2026-09-10 — Phase 22 C1: chapter-span pass becomes the primary facts source

**What changed.** `wiki scenes`'s detail call (Phase 22 B1) gained a `participant_facts` field:
for every participant a span says something new about, `{"subject": <name>, "facts": [...]}`
groups, each `fact` shaped identically to a `claim_extract` fact (predicate/kind/object/value/
qualifier/para_id/quote/confidence/polarity), reusing the SAME three-way attribute/relation/trait
vocabulary `claim_extract`'s system prompt uses (`schema.ExtractedFact`, imported unchanged into
`scene_schema.py`). `extract/scenes.py::_build_participant_fact` resolves and validates each fact
with the identical discipline `claims.py::_build_claim` already applies — verbatim quote, real
para_id, known predicate, resolved relation object — just scoped to the chapter's known entities
instead of one mention window's. `_build_scene_record` now returns a third list (claims) per span;
`extract_chapter_scenes`/`extract_volume_scenes` merge them by `claim_id` across spans/chapters
(same `_merge_claim` logic `claims.py` already used, duplicated locally so `scenes.py` never
imports from `claims.py` — deliberate: `claims.py` is the dependent/secondary pass now, not the
other way round).

**Folded into the existing call, not a third one.** `participant_facts` was added to the detail
call's response instead of a new call, so this costs **zero extra calls per span** — chapter-span
coverage already reaches every paragraph and every participant by construction, which is what
lets this replace `claim_extract`'s mention-window pass as primary rather than merely
supplementing it. `_DETAIL_GENERATION_OPTIONS.num_predict` raised 6144 -> 8192 (participant_facts
is usually the largest sub-list per span).

**Two claim files, unioned at graph build, not merged at write time.** Rather than redesign
`wiki extract`'s write semantics this session (real scope creep into C2's job — see "what's still
open" below), `wiki scenes` writes claims to a NEW file, `data/03_claims/scene_v{NN}.jsonl`
(`paths.py::scene_claims_volume`), leaving `wiki extract`'s own `v{NN}.jsonl` completely
untouched. `wiki graph build` now globs both `v*.jsonl` and `scene_v*.jsonl`
(`cli.py::graph_build`), and merges the combined list by `claim_id`
(`cli.py::_merge_claims_by_id`) — a fact independently derived by both passes lands on the
identical content-addressed id, so this combines evidence instead of one file's copy silently
winning (`graph/store.py::write_claims` is `INSERT OR REPLACE` regardless, so a raw duplicate
would not have crashed, just silently dropped one side's evidence — worth merging explicitly
rather than relying on that). `_incomplete_claim_volumes` (A1's completeness gate) is unaffected
in behavior — it already worked off a plain claims list, now just a fuller one — but now credits
a character found by EITHER pass, which is strictly more correct than only ever crediting
`claims.py`. `provenance.start_run` for the `scenes` command's `stage_keys` grew
`["scenes", "claims"]` (from `["scenes"]`) so `_guard_upstream_failures` correctly blocks
`graph build` if a `wiki scenes` run left claims mid-write.

**A design fork resolved before writing code.** The two ways to wire this in were (a) fold into
`wiki scenes` (chosen — no duplicate span/LLM work, matches the "net fewer calls" goal since
nothing runs twice) or (b) keep `wiki extract` as the facts command and have it build its own
chapter-span pass internally, independent of whatever `wiki scenes` already did (duplicates span
construction and, unless scenes had already run, duplicates the LLM calls over the same text).
Confirmed with the user via AskUserQuestion before implementing — (a) was explicitly picked,
recommended for the reason above.

**Verification.** 36 tests in `test_scenes.py` (10 new: attribute/relation fact -> claim dict,
subject-unresolved / unknown-predicate / nonverbatim-quote drops, cross-chapter claim_id merge,
prompt vocabulary presence, plus a `scene_schema.py` test for group-level dropping — blank
subject, a group whose facts all fail validation, and a group missing the `facts` key entirely
are all dropped rather than surfacing as empty noise). One existing test
(`test_stage_guard.py::test_graph_build_stops_on_incomplete_claims`) needed a `claim_id` added to
its synthetic fixture claim, since `_merge_claims_by_id` now keys on it — a pre-existing test
gap, not new behavior it was testing. Full suite green (593 tests). No real corpus run yet — this
is code-level only; the next `wiki scenes` run against spice-and-wolf or 86 will be the first live
exercise of `participant_facts` against real model output, the same way B1/B2/B3/B4 all needed a
live run before their prompt/schema assumptions were trustworthy (see the two bugs the last live
run found, dated entry above). Budget accordingly before running it for real.

**What's still open (C2-C4, unstarted).** `wiki extract` still runs its full, unmodified
mention-window sweep every time — C2 (demote it to a sparse top-up driven by `audit eval` gaps,
plus the "top up an existing volume" path `extract --chapters` doesn't have today) is real,
separate work, not done here. C3 (a verification pass over assembled fact sets) and C4 (grow the
gold set to ten characters) also untouched. `docs/CONTRACTS.md` §3/§3b and `docs/PROMPTS.md`
`scene_extract` and `USER_GUIDE.md`'s `wiki scenes`/`wiki extract` sections were updated to match
the new architecture.

## 2026-09-10 — Phase 22 C2: `wiki extract --entities` becomes a targeted top-up

**What changed.** `wiki extract`'s "skip if the volume's claim file already exists" guard
(`cli.py::extract`) previously fired regardless of `--entities`, so `--entities "Holo"` against an
already-extracted volume just printed "already extracted, use --force" and did nothing — the
gap C1's writeup flagged. Now: passing `--entities` on an existing volume no longer skips it.
Instead it re-extracts only the named character(s) and merges the fresh claims into the existing
file, replacing that/those character(s)' prior claims while leaving every other character's claims
on disk untouched (`cli.py::_merge_by_entity`, same shape as the pre-existing `_merge_by_chapter`/
`_merge_by_volume` helpers, keyed on `claim["subject"]` — a claim's subject is always the resolved
`entity_id`, per `claims.py::_build_claim`). `--force` still means whole-volume and is unaffected;
you do not need it alongside `--entities` to top up, and `--entities --force` still only touches
the named entities (force never widens an entities-scoped run back out to the whole volume).

**Driven by `audit eval` gaps.** `_eval_report` (`audit/reports.py`) now prints a top-up suggestion
under any gold-covered character whose fact recall falls below `_TOP_UP_RECALL_THRESHOLD` (0.5):
`wiki extract --series <id> --volumes <eval_vol> --entities "<canonical>"`. This is the "driven by
where audit eval shows a gap" half of C2's spec — a cold contributor reading the eval report gets
the exact command to run, not just a number, closing the loop C1 left open (eval was already
computing per-character fact recall; nothing pointed back at the fix).

**What C2 deliberately did NOT do.** No new flag (`--top-up` etc.) — `--entities` already existed
and its combination with an existing volume file was simply undefined/buggy before, so fixing that
combination was the whole surface area. No change to `--chapters`' own merge behavior or to
`wiki graph build`'s claim-file discovery (still globs `v*.jsonl` + `scene_v*.jsonl`, C1). No
automatic "sweep only where scenes came up short" mode — that would mean `wiki extract` itself
reading `audit eval` output and picking entities/volumes on its own; today a human (or a future
script) still reads the printed suggestion and runs it. Demoting `wiki extract`'s DEFAULT (no
`--entities`) behavior away from a full mention-window sweep was not in scope either — that default
still exists for whole-corpus/whole-volume runs; C2 only fixed the narrower, already-requested path.

**Verification.** Two new pure-function tests in `test_cli_chapters.py`
(`test_merge_by_entity_keeps_untouched_entities_and_replaces_touched_ones`,
`test_merge_by_entity_against_empty_existing_is_just_the_fresh_records`), same style as the
existing `_merge_by_chapter`/`_merge_by_volume` tests. One new test in `test_audit_eval.py`
(`test_eval_report_suggests_a_targeted_top_up_when_fact_recall_is_low`) asserting the exact printed
command for a synthetic 0%-recall gold character; the existing 100%-recall test now also asserts
`"top-up" not in text` so the two cases stay distinguishable. Full suite green, 597 tests (+3). No
live corpus run — this only touches CLI control flow, not extraction quality, so a live run would
not exercise anything a unit test can't already cover; the next live `wiki extract --entities`
top-up against a real `audit eval` gap is still a good idea before trusting it under real load
(untested: a volume with a large existing claims file, to confirm merge cost stays cheap).
`USER_GUIDE.md`'s `wiki extract` section updated with the top-up flag description and example.

---

## 2026-09-10 — Phase 22 C3: a verification pass, not a bigger extraction pass

**What changed.** A new `wiki verify --upto N` command: one `verify`-role LLM call per CHARACTER
entity (skipped entirely, no call, when the character has zero currently-visible facts), asking
whether each fact already on the graph is actually supported by its own cited evidence — the
backstop the TODO named for two failure patterns extraction-level fixes (B2's alias grouping, A3's
membership-predicate filter) reduce but cannot guarantee eliminated: a fact hallucinated about the
wrong entity ("phantom Kraft" — two aliases of one person read as two people) and a relationship
claim the evidence doesn't actually support ("Medio membership" — a captured-by/enemy passage
misread as membership). `synth/assemble.py::fact_set_for_verification()` is the new input builder
— current state only (`state_at`/`relations_at`, not `history_at`, since a superseded value isn't
what the live page asserts today), each fact paired with up to 2 evidence quotes via
`graph/temporal.py::evidence_at()`, the same path `wiki explain`/`wiki trace` already use; NOT
`assemble_page()`'s rendered dict, which deliberately drops `claim_ids`/evidence entirely.
`graph/verify.py::verify_character()` makes the one call per character (`VerificationResult` ->
`flags: [{fact_index, rationale}]`, resolved back against the numbered fact list the prompt showed
it) and, mirroring `graph/contradictions.py`'s own `client=None`/empty-input handling, degrades to
"skipped, zero flags" rather than a fabricated verdict whenever there is nothing to check or no
model reachable.

**Never mutates anything.** A flagged fact stays exactly where it was — in `claims`, in
`intervals`, on the rendered page — logged only to the new `data/04_graph/verification.json`
(CONTRACTS §4.3) for a human to read via the new `wiki audit verify` report. Same "never silently
pick a winner" discipline `contradictions.json`'s `flag` resolution already established
(CLAUDE.md §2); `_verify_report` never FAILs on a flagged fact for the same reason
`_contradictions_report` never fails on a flagged conflict — a flag is a pointer, not a build
defect.

**Wired into `run-all`, not into `step`.** `wiki run_all` now runs `verify` right after
`graph_build` (before `events_build`) — a legitimate, LLM-calling pipeline stage, same tier as
`graph_build`/`synthesize`, so "run every stage in order" should include it. Deliberately NOT
added to `wiki step`'s fixed `extract -> graph build -> synthesize -> site build` per-chapter
sequence — its own docstring names exactly those four stages, and adding a fifth LLM call per
chapter to the fast audited-loop path would raise its per-chapter cost for a check that makes more
sense run once over the whole assembled graph than once per chapter.

**Config.** New `verify:` role in `config/models.yaml`'s `routing:` block — `local_best` with
`openrouter_free` fallback, same tier as `arbitrate` (infrequent, needs real reasoning, not a bulk
stage). `provenance.py::COMMAND_STAGE_KEYS` gained `"verify": ["verify"]` so a crashed `wiki
verify` run is caught by `_guard_upstream_failures` exactly like every other stage. New
`docs/PROMPTS.md` catalogue row (`verify_facts`).

**Verification.** New tests: `tests/test_synth_assemble.py` (4 — attribute fact with evidence,
relation fact keeping the interval's own stored subject/object direction with names resolved via
`entities_by_id`, evidence capped at `max_evidence` while deduping an interval that appears in
both `state_at` and `relations_at`, empty when nothing is visible), `tests/test_graph_verify.py`
(new file, 7 — prompt formatting with/without evidence, no-call when facts are empty or client is
`None`, a flagged fact carries its rationale, an out-of-range `fact_index` is dropped rather than
crashing, an empty `flags` list means nothing was flagged), `tests/test_audit_reports.py` (3 —
`StageNotReady` with no `verification.json` yet, flagged facts print and the report still returns
`True`, a clean run with nothing flagged prints a clean summary). `tests/test_run_all_guard.py`
updated for the new stage in `run-all`'s fixed sequence. Full suite green, 610 tests (was 597,
+13). No live corpus run — everything here is unit-tested against a fake `complete_json` client,
same discipline every other Phase 22 sub-item used before its own first live run; the next `wiki
verify --upto 2` against the real spice-and-wolf graph is still a good idea before trusting its
prompt/flagging behavior at real scale (budget accordingly: ~14 calls for two volumes, per the
TODO's own estimate, now confirmed by the live gazetteer's 14 CHARACTER entities).

**What's still open.** C4 (grow the gold set to ten characters, gate on it) is the only remaining
Phase 22 TODO item, untouched here.

---

## 2026-09-10 — Phase 22 C4: gold set grown to ten characters, regression gate added

**What changed.** Six new hand-transcribed gold files in `docs/eval/gold/spice-and-wolf/`
(`marheit.yaml`, `liebert.yaml`, `hans-remelio.yaml`, `enek.yaml`, `yarei.yaml`, `zheren.yaml`),
bringing gold-data coverage from 4 to all 10 characters this project has ever extracted claims for
(the remaining 4 gazetteer CHARACTER entities — `weiz`, `count-ehrendott`, `saint-metrogius`, and
`saint-ruvinheigen`, which has no generated page at all and would only produce a permanent,
uninformative FAIL — were deliberately left out; the TODO's "ten characters" target is met without
them). Same WebSearch-transcription methodology `holo.yaml`'s header documents (WebFetch of
`fandom.com` still returns HTTP 402 in this sandbox). `enek.yaml`'s header flags something found
while inspecting its live page before writing the file: `enek/v02.json` currently renders
`RELATIVE_OF Holo`/`FRIEND_OF Lawrence` relationship rows nothing in the real character's story
supports — exactly the kind of phantom-relationship noise C3's `wiki verify` exists to catch, left
as-is (not fixed here — C4 is gold-data scope, not extraction fixing) and useful as a live case for
whoever runs `wiki verify` against this data next.

**The regression gate.** `docs/eval/gold/<series>/baseline.json` — a second hand-maintained file,
sibling to the gold YAMLs, `{"fact_recall": {entity_id: value, ...}}` — recorded from a REAL `wiki
audit eval --series spice-and-wolf` run against the data already on disk (no extraction re-run
performed; these are whatever the existing post-C1/C2/C3 pages already scored). `eval/gold.py::
load_baseline()` reads it (`{}` when absent, same convention `load_gold` already has).
`_eval_report` now FAILs when a gold-covered character WITH a recorded baseline scores below it
this run — a genuine regression check — while staying purely advisory (as before) for any
character with no baseline on record, regardless of how low its score is. This is deliberately
narrower than "gate on absolute quality," which the report's own docstring has argued against
since Phase 21 part 4: nothing here invents a quality bar for a character nobody has measured
before, it only stops an already-measured one from silently getting worse. Nothing auto-updates
`baseline.json` — raising a value after a genuine improvement is a hand edit, the same discipline
gold facts themselves already follow.

**Verified.** `wiki audit eval --series spice-and-wolf` run for real (read-only, no LLM calls —
`eval/gold.py`'s scoring is pure lexical-overlap Python) against the live 2-volume corpus data
already on disk, twice: once to produce the 10-character recall table `baseline.json` now records,
once more after writing `baseline.json` to confirm a clean `OK` with no false regression. Recorded
fact recall: Holo 40%, Kraft Lawrence 22%, Norah Arendt 30%, Jakob 0% (all four match the
`Re-extract V1+V2` entry's own table exactly, confirming these numbers are stable/reproducible);
Liebert 50%, Hans Remelio 29%, Marheit 17%, Enek 0%, Yarei 0%, Zheren 0%. New tests: `tests/
test_eval_gold.py` (2 — `load_baseline` empty-on-missing-file, reads the `fact_recall` map), `tests/
test_audit_eval.py` (3 — a real regression FAILs and prints `REGRESSION`/`baseline.json`, a score
at-or-above the recorded floor does not FAIL, a character with no baseline entry is never gated no
matter how low its score is). Also fixed while here: `USER_GUIDE.md`'s `wiki audit <stage>` table
had listed only 7 of the by-then 11 registered report stages (the exact staleness bug Phase 22
part 1 already fixed once in `cli.py`'s own help string — this was the same bug in a second,
un-synced location) — corrected to all 12 (now including `verify`), matched directly against
`reports.available()`. Full suite green, 615 tests (was 610, +5).

**What's still open.** Nothing — this was Phase 22's last TODO item. See `docs/handover/PHASE_22.md`
for the full-phase handover.

---

## TODO — the remaining Phase 22 work, in order

All of A1-A6, B1-B4, and C1-C4 are done (2026-09-10, see the dated entries above) — every checkbox
below is checked. Phase 22 is complete; see `docs/handover/PHASE_22.md`. Each item below still
names its own original fix seam so a cold session can see exactly what was asked for versus what
shipped, without re-deriving anything. Full line-level detail, including verbatim quotes of every
function named here, is in the audit findings above plus the defect list.

### A. Recover what has already been paid for

- [x] **A1. Quarantine failed runs.** Done 2026-09-10 — see the dated entry below. Original spec:
      Add `last_run_for_stage(stage_key)` / `failed_stage_artifacts()`
      to `provenance.py` (reading the `outcome` / `snapshotted_stages` fields `finish()` and
      `snapshot_before()` already write — no new manifest fields). Add one shared guard at the top
      of `extract`, `scenes`, `graph build`, `synthesize`, `site build` in `cli.py`: abort if the
      most recent run that wrote an input stage recorded `outcome: failed`, printing the exact
      `wiki rollback <run_id> --yes` command. Add `--allow-partial` to override. Plus a
      completeness assertion: a volume's claim file must contain every gazetteer character with
      mentions in that volume, or the build stops. This is the check that would have caught the
      original crash.
- [x] **A2. Value normalization + subsumption (fixes U2, S2).** Done 2026-09-10 — see the dated
      entry below. Original spec, four seams:
      (1) `temporal.normalize_value` gains an optional `fmt` argument driven by
      `attributes.*.format` — which today has no consumer at all. `number_or_range` folds
      spelled-out numbers to digits and strips trailing unit words, so all four Lawrence AGE
      phrasings become `25`.
      (2) `contradictions.py::_resolve_single_valued` currently does **no value comparison** on the
      same-volume path (L182-185 assumes the extractor deduped); collapse by normalized value first
      so only genuinely distinct values reach arbitration.
      (3) `temporal.assign_multi_valued` L167 buckets by the **exact** value string — switch to
      `normalize_value`, then add `canonicalize.py::subsume_values()`, gated on a new per-predicate
      `subsume: true` key: drop any value that is a case-folded substring of a longer sibling, and
      any bare noun under three tokens with no modifier. Deterministic, so it works with Ollama down.
      (4) Give `conflicts.quiet_change` its first consumer — a quiet-change predicate must not emit
      a `previously:` line.
- [x] **A3. Faction membership + key events (fixes S1).** Done 2026-09-10 — see the dated entry
      below. Original spec: `bundle.py::_members_and_related` treats
      *any* relation as membership, which is how Holo became a member of the company that kidnapped
      her (an `ENEMY_OF` edge qualified `captured by`) and Lawrence a member of Medio. Add
      `membership: true` to `AFFILIATED_WITH`/`SERVES_UNDER`/`COMMANDS` and filter on it; route
      `ENEMY_OF`/`RIVAL_OF` to a separate `adversaries` bucket. `_faction_key_events` counts any
      scene where >=2 "members" co-occur, which is why Medio and Milone render byte-identical lists
      (Holo and Lawrence share 43 of 54 scenes) — require the faction itself to be a participant or
      the scene's location.
- [x] **A4. Wikify every `beat_summary` (fixes S4).** Done 2026-09-10 — see the dated entry above.
      Original spec: `wikify_text` already does this for prose and
      codex summaries. Thread `automaton`/`entities_by_id`/`settings` into
      `bundle.py::_faction_key_events`, `_shared_scenes_between` and `build_timeline_bundles` (all
      three are already in scope at the `cli.py` call site; the cutoff for a timeline event is
      `row["vol"]`, not `upto_vol`). Client-side, `app.js::renderSceneCard` needs `renderLinkedText`
      instead of `escapeHtml`, or links render as literal Markdown. Extend `_links_report`'s
      `check_links_in_text` to `beat_summary` or the new links go unvalidated. Timeline cosmetics:
      `chapter_idx` is 0-based *and* the bundle carries no chapter title at all, so fixing
      `CHAPTER 0` is a bundle change; drop the per-card volume badge; sort participant chips.
- [x] **A5. Page model + rendering (fixes U3-U7, S5, S6).** Done 2026-09-10 — see the dated
      entry above. Original spec: All deterministic, in
      `synth/assemble.py` + `site/okf.py` + `site/templates/app.js`:
      `attributes.*.default` materialized as an `inferred: true` field (U6); polarity rendered as a
      "Presumed …" prefix, and `_claim_polarity` fixed to stop reading only `claim_ids[0]` (U7);
      `label` becomes display-first with the qualifier demoted to a note, plus a per-relation
      `blurb` template (U4) — and fix the related bug that `relations_at` never filters `vol_end`
      while `assemble.py:155` computes `closed` and discards it, so superseded relationships render
      as live; `mentions_of` filtered against what is already on the page and annotated with the
      connecting relation or shared-scene count via the existing `shared_events_at` /
      `relations_between` (U5); a `show_vol` flag gating every `(since vN)` (U3); a `lead` section
      kind plus reordered `page_outline` **and** a swapped DOM assembly in `app.js` (S6); a minimum
      evidence gate before a page is generated, plus a roster/places name-collision check —
      Saint Ruvinheigen is currently both a character and the city it is the eponym of (S5).
- [x] **A6. Yield assertions (fixes S7).** Done 2026-09-10 — see the dated entry above. Original
      spec: Reports are `(Settings, Console) -> bool` registered with
      `@register`. Add: share of the roster with >=N claims, share of scenes returning any
      structured field, appearance-to-total ratio, and hard failure on an upstream
      `outcome: failed`. Also close two known holes: `_outline_report`'s prose branch is a dead loop
      that does nothing, and `_links_report` explicitly opts out of validating quote speakers —
      which is why 9 `speaker: null` quotes shipped unnoticed.

### B. Reallocate the calls already being made

- [x] **B1. Split the scene call in two.** Done 2026-09-10 — see the dated entry above. Original
      spec: Call one returns participants/location/beat; call two
      returns quotes/state_changes/epithets with worked examples. Same text, cached prefix,
      56 -> 112 calls. Split `SceneExtractionResult` to match.
- [x] **B2. Coreference prompt hardening (U1) + the phantom-entity fix (S3).** Done 2026-09-10 —
      see the dated entry above. Original spec: Batched with B1
      because both edit prompts and therefore invalidate the same cache. Add two rules to
      `claims.py::_SYSTEM_TEMPLATE`: a fact stated about the subject under a pronoun or epithet
      still counts when the antecedent is unambiguous (this is the recall half — the information
      loss the user reported); omit rather than guess when it is ambiguous. In both drivers' user
      prompts, pass **canonical names with aliases grouped by entity_id**
      (`Kraft Lawrence (also: Lawrence, Kraft)`) instead of a flat set of raw surfaces — this is the
      actual cause of "Lawrence sells furs to Kraft Lawrence", a hallucination inside `beat_summary`
      that no resolution rule can fix. Make `resolve_surface`'s containment fallback
      longest-match-wins rather than first-match-in-list-order, and add the name-part rule. Suppress
      quote cards with an unresolved speaker instead of printing `Unknown`.
      While here: `schema.py::_is_usable_fact` rejects a fact whose `kind` isn't lowercase *before*
      `_lookup_predicate` can derive the true kind from config, so `"kind": "RELATION"` silently
      loses the fact.
- [x] **Re-extract V1+V2.** Done 2026-09-10 — see the dated entry below. Ran on local Ollama, not
      the API, since GOOGLE_API_KEY is unset — $0 spend, not the real spend this item's spec
      anticipated.
- [x] **B3. Proportional window budget.** Done 2026-09-10 — see the dated entry below.
- [x] **B4. Cap codex evidence.** Done 2026-09-10 — see the dated entry below.

### C. Invert the two passes

- [x] **C1.** Make the chapter-span pass primary. Done 2026-09-10 — see the dated entry below.
- [x] **C2.** Done 2026-09-10 — see the dated entry above. `wiki extract --entities` now tops up an
      existing volume (merges by `subject`, doesn't touch other characters' claims); `wiki audit
      eval` prints the exact top-up command for any gold character under 50% fact recall. Original
      spec: Demote mention windows to a targeted top-up driven by where `audit eval` shows a gap.
      Note this also needs a "top up an existing volume" path: `extract` currently skips a volume
      whose file exists unless `--force`, and `--force` is whole-volume.
- [x] **C3.** Done 2026-09-10 — see the dated entry above. `wiki verify --upto N` makes one
      `verify`-role call per CHARACTER entity, flagging any fact whose own cited evidence doesn't
      support it (`data/04_graph/verification.json`, `wiki audit verify`); never mutates a claim,
      interval, or page. Original spec: Add a verification pass, not a bigger extraction pass —
      one cheap call per character over the assembled fact set plus its top evidence. ~14 calls
      for two volumes, and the thing that catches both the phantom Kraft and the Medio membership
      error.
- [x] **C4.** Done 2026-09-10 — see the dated entry above. Six new gold files (10 total);
      `docs/eval/gold/<series>/baseline.json` (hand-maintained) records each character's last
      measured fact recall, and `_eval_report` FAILs on a drop below it. Original spec: Grow the
      gold set to ten characters and gate on it so recall cannot regress.

### Known traps for whoever resumes

- **A2 forces a full prose regeneration.** `make_interval_id` hashes the raw value string and
  `_claim_set_hash` hashes the visible interval-id set, so normalizing values changes those ids and
  every character's prose cache misses. Correct, but real spend — budget it alongside the
  re-extraction rather than discovering it.
- **The converse:** `_claim_set_hash` hashes interval **ids only** — not `qualifier`, `vol_end`,
  `superseded_by` or `claim_ids`. A5's qualifier and relationship-closure fixes invalidate nothing
  on their own; a `synthesize` re-run will not reflect them without `--force`.
- **`PYTHONPATH=src` is no longer needed** now that the editable install is correct, but older docs
  (`docs/handover/PHASE_21.md` §"Reproducing") still say it is. Harmless, but ignore that note.
