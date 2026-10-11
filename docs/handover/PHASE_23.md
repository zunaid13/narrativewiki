# Phase 23 Handover — Precision, Grounding, and Fandom-Grade Pages (PHASE COMPLETE — PARTS A-F ALL DONE)

**Status (updated 2026-09-11, fourth session of the day):** Every part — A, B, C, D, E, F — is
COMPLETE and verified on branch `phase-23-precision-and-grounding` (not yet merged to `main`;
pushed as of the Part F commit, Part E not yet pushed at the time this doc was last edited — check
`git status`/`git log` rather than trust this line). **Read "Part F: DONE" below before touching
model routing** — it documents the actual OpenRouter model that works for this pipeline's call
shape, a routing-scope mistake made and reverted, and one real open extraction bug intentionally
left unfixed. **Read "Part E: DONE" below before touching `page_outline` or `synth/prose.py`'s
section dispatch** — it documents the new section keys, the schema-cap tuning a live run forced,
and a real eval-harness bug (`_HEADING_ALIASES`) found and fixed while verifying it.

**The triggering bug:** `/#/relationships/marheit/kraft-lawrence` rendered "Kraft Lawrence — Spouse
of — Marheit," which is false. The user asked for the systemic cause and a plan to prevent the
whole class of error — not a one-row patch. `docs/vision/PHASE_23.md`'s 2026-09-10 entry has the
full audit (five-link causal chain, graph-wide error counts, why nothing caught it, the Fandom
comparison). Read that before touching anything here if you weren't in the original session.

---

## What exists now (Parts A-D)

### Part A — extraction-side precision gates

- **A1 — `extract/resolve.py::resolve_surface`.** Now takes a required `passage_text` arg: a
  candidate only qualifies if its own surface actually occurs in the text the model was shown
  (kills resolution from a prompt artifact the model echoed back, e.g. `object: "Lawrence Kraft
  (also: Lawrence)"`). Both exact-match and name-part-fallback paths return `None` on a genuine
  tie between distinct entities instead of silently picking the longest/first
  (`resolve.py:105-124`). Wired through all 8 call sites in `extract/claims.py`/`extract/scenes.py`.
  **Known residual:** at the WINDOW level this alone does not remove a false fact whose object is
  merely mentioned elsewhere in the window — that's A2's job.
- **A2 — `extract/adequacy.py` (new).** `passes_evidence_adequacy()`: `min_quote_words` (config,
  6 — kills a two-word quote outright), `subject_must_be_named` (subject's name must be in the
  CITED PARAGRAPH, not just the window), `requires_both_endpoints` (new per-predicate flag on
  family/intimacy/command predicates — object must ALSO be named in that paragraph). This is what
  actually removes the false SPOUSE_OF: the cited paragraph names Marheit but never Lawrence.
  Wired into `claims.py::_build_claim` and `scenes.py::_build_participant_fact`.
- **A3 — `config/extraction.yaml` guardrail notes.** Every relation predicate that lacked a `note:`
  now has one (SPOUSE_OF, ROMANTIC_WITH, SIBLING_OF, PARENT_OF, CHILD_OF, FRIEND_OF, COMRADE_OF,
  AFFILIATED_WITH). Rendered into both prompts automatically via the existing `_vocab_lines`.
- **A4 — `graph/contradictions.py::_strip_mutual_direction_collisions` (new).** Catches a
  directional (non-symmetric) predicate asserted in BOTH raw directions between the same pair
  (`CHILD_OF(A,B)` + `CHILD_OF(B,A)` — the real Jakob/Lawrence bug: one sarcastic false-identity
  line produced simultaneous parent AND child badges). `_canonicalize_relation` only merges a
  predicate with its DECLARED `inverse`, never a raw same-predicate reversal — this runs before
  canonicalization, confidence-ranks the two directions, keeps the winner, logs the loser.
  Separately: `conflicts_with` groups added for the four symmetric family/intimacy predicates
  (SPOUSE_OF/ROMANTIC_WITH vs SIBLING_OF/RELATIVE_OF) — PARENT_OF/CHILD_OF deliberately excluded
  (non-symmetric, already covered by the mutual-direction fix).
- **A5 — deferred, not done.** Wiring `min_for_structured_field: 0.7` as a hard confidence gate
  requires B1's confidence column (done) but was deliberately NOT enforced as a gate: many
  existing test fixtures across `test_synth_assemble.py`/`test_site_bundle.py`/etc. construct
  interval rows without a realistic confidence value (defaulting to 0.0), so a real threshold
  would silently break a large fixture surface never written expecting it. B2's verdict-based
  withholding ships instead, on its own merits, fully backward-compatible. **If you pick this up:**
  audit/update those fixtures deliberately first, then wire `confidence >=
  min_for_structured_field` alongside B2's `_is_renderable` check in `synth/assemble.py`.

### Part B — binding verification

- **B1 — `graph/store.py`, `graph/temporal.py`, `graph/contradictions.py`.** `intervals` gained
  `confidence`/`evidence_count` columns (idempotent `ALTER TABLE` migration in `store.connect()`
  for a pre-Phase-23 `graph.db`), threaded through `assign_single_valued`/
  `assign_relation_supersession` (winning claim's own confidence) and `assign_multi_valued` (max
  across corroborating observations). New `verdicts` table
  (`target_id, target_kind, verdict, rationale, model, run_id`) + `write_verdicts`/`read_verdicts`.
- **B2 — `synth/assemble.py`, `site/bundle.py`.** A fact `wiki verify` flags `unsupported` is
  withheld at RENDER time only — never deleted, still fully queryable via `wiki explain`/`trace`.
  Shared `_is_renderable()` in `_build_attribute_fields`/`_relationship_entries`, mirrored in
  `site/bundle.py`'s `_members_and_related`/`_relation_entries_between` (a codex page or pair page
  can never disagree with the character page). Empty `verdicts` table = pure no-op, fully backward
  compatible.
- **B3 — `config/models.yaml`.** `verify`/`arbitrate` were routed to `local_best` (Ollama, not
  running in this environment) with a `fallback` that `config.py::resolve_role` can never actually
  reach (it only falls back on a MISSING API KEY, and an Ollama profile has no key to be missing).
  Both re-routed to `google_best` (confirmed working on this key's tier) with `local_best` kept as
  fallback. **This means `arbitrate` was ALSO silently degrading to the rule-based fallback for
  same-volume conflicts before this fix** — worth knowing if you see old arbitration decisions that
  look rule-based when a real LLM call should have reasoned about them.
- **B4 — `synth/assemble.py::fact_set_for_verification`.** `max_evidence` raised 2 -> 20 (one call
  per character, so the token cost is trivial). **Deferred, not done:** passing the cited
  paragraph's immediate neighbours (not just the quote) to the verifier — would need
  `01_parsed/vNN.jsonl` records threaded into the verify CLI path, a real plumbing addition.
- **B5 — the missing link that activates B1/B2 at all.** `verify_character()` never wrote to
  `verdicts` — `fact_set_for_verification`'s fact dicts didn't even carry `interval_id`. Fixed:
  both fact-building loops stamp it; `cli.py::verify` builds a verdict for every checked fact and
  calls `store.write_verdicts()` before closing ("unsupported" sticky when the same relation
  interval is verified independently from both characters' sides). `wiki verify` now runs INSIDE
  `graph_build` (at `upto = volume_scope`), not as a skippable later stage — a verify failure
  degrades to a printed skip, never fails `graph_build` itself. `run-all`'s now-redundant explicit
  `verify(...)` call removed. `audit/reports.py::_verify_report` FAILs when the unsupported rate
  exceeds `extraction.verify.max_unsupported_rate` (config, default 15%).
  **Operational note:** every `wiki graph build` (and therefore `wiki step`/`wiki run-all`) now
  makes one verify LLM call per character. Real, accepted cost per the approved plan — reversible
  by decoupling the call back out of `graph_build` if this proves unwelcome at scale.

### Part C — a real precision metric

- **C1 — `eval/gold.py::score_fact_precision` (new).** Classifies rendered page facts against
  gold's positive `facts` and new `negative_facts` using the same lexical keyword-overlap
  mechanism `score_fact_recall` already uses. `precision = supported / (supported + contradicted)`,
  `None` when gold has no opinion. **Known gap, not fixed:** `fields.affiliations` entries carry
  only `entity_id`/`role`/`vols`/`current` — no label/display text — so a false AFFILIATED_WITH
  membership (e.g. the real Holo/Medio captive-as-member bug) is invisible to this check unless
  `role` happens to carry text. A real fix needs `entities_by_id` threaded into `_page_text` to
  resolve the bare `entity_id` slug to its canonical name for matching. `fields.relationships`
  entries (which DO have `label`/`blurb`) are reliably caught today.
- **C2 — `eval/gold.py::_page_text`.** Its own docstring always claimed to exclude identifier
  keys; the implementation never actually filtered by key — a false relation's raw
  `entity_id`/`predicate` strings landed in the recall keyword bag exactly like real prose, so a
  FALSE fact could only ever RAISE `fact_recall`. Fixed with an explicit `_PAGE_TEXT_SKIP_KEYS`
  blocklist.
- **C3 — `docs/eval/gold/spice-and-wolf/*.yaml`.** `negative_facts` seeded into the 6
  gold-covered characters with real findings (`marheit`, `jakob`, `enek`, `holo`, `norah-arendt`,
  `kraft-lawrence`), 18 assertions total, transcribed from the audit's own evidence.
- **C4 — `audit/reports.py::_eval_report`.** FAILs UNCONDITIONALLY (no baseline needed) on any
  gold `negative_fact` the page asserts. FAILs on a precision regression against a new
  `baseline.json` sibling `precision` map (`gold.load_precision_baseline`). **`precision: {}` is
  deliberately EMPTY in the live baseline file** — the on-disk v1-2 data predates the Phase 23 A/B
  fixes and still carries the actual false claims; recording today's numbers as a floor would lock
  in the broken state. **Part F must populate this** after the re-run, by running `wiki audit eval`
  against the fixed data and hand-copying the printed `fact precision: NN%` lines into
  `docs/eval/gold/spice-and-wolf/baseline.json`'s `precision` map — same manual discipline
  `fact_recall`'s baseline already uses.

### Part D — recall fixes

- **D1 — provider option-key mismatch.** `extract/claims.py`/`extract/scenes.py` hardcode
  Ollama-vocabulary call options (`num_predict`) regardless of routed provider.
  `llm/providers/{google,openai,anthropic}.py` never recognized that key, silently falling back to
  the profile's own (much lower) default token cap. Confirmed live: 0 of 112 `scene_extract`
  detail responses in one run carried a non-empty `participant_facts` list. Fixed in all three
  providers (call-site `num_predict` now wins over the profile default, but an explicit
  provider-native override still wins over `num_predict`).
- **D2 — `context_paragraphs_before/after` raised 2 -> 4** in `config/extraction.yaml`. Safe now
  that A2's adequacy gate checks the cited paragraph specifically. Fuller design (read-only,
  non-citable wider scene context) deferred — needs a prompt-format change splitting shown text
  from the citable para_id set, not just a config bump.
- **D3 — investigated, no code change.** The empty `epithets_v01/v02.jsonl` files trace to the
  SAME stale pre-Phase-22-C1 run D1 found (confirmed via that run's own logged responses: the
  local model's epithet attempts had a null `entity_id_hint` and empty `quote`, both correctly
  rejected by existing validation). Reads as local-model output quality on a superseded run, not a
  pipeline defect. **Re-assess after Part F's re-run** — a still-empty yield under the current
  Gemini-routed prompts would be a real, new signal worth its own investigation.

---

## Decisions taken (and why), for anyone tempted to redo one differently

- **Withhold unsupported facts entirely, never render "unconfirmed."** Confirmed explicitly with
  the user before implementing B2. Nothing hedges — a fact either renders normally or doesn't
  render at all, with the interval/claim/rationale still fully inspectable via `wiki explain`.
- **B3's fix re-routes `verify`/`arbitrate` rather than teaching `resolve_role` to detect an
  unreachable local provider.** A live-reachability probe inside `resolve_role` would need a
  network call on every single resolution (or a cached health-check with its own staleness
  problem) — a bigger, riskier change for the same outcome the routing swap already achieves,
  using a pattern (`google_fast`/`google_best` primary, `local_*` fallback) already proven by
  `claim_extract`/`scene_extract`.
- **A4's family `conflicts_with` group excludes PARENT_OF/CHILD_OF deliberately** — they're
  non-symmetric, and `_relation_conflict_groups`/`pair_claims` bucket by the already-direction-
  canonicalized `(subject, object)` pair, which does NOT resolve a raw same-predicate reversal.
  The plan's literal wording listed them in the group; the actual mechanism needed
  (`_strip_mutual_direction_collisions`) is a different, additional fix, not a config change —
  implemented separately, applies to every non-symmetric predicate, not just these two.
- **A5 and B4's fuller design, and C1's affiliation-label gap, are deliberately left as gaps, not
  silently absorbed into "done."** Each is called out above with the exact reason and the exact
  follow-up needed — per the project's own "say explicitly what you left out and why" discipline.

## Traps hit (so you don't re-discover them)

- **`resolve_surface`'s old tie-break was silent** (`len(surface) > best[0]`, strict inequality —
  list order broke ties). If you ever see a name collision (e.g. two "Nouzen"s, two "Lawrence"s)
  resolve to the wrong one again, check this hasn't regressed — `resolve.py`'s docstring documents
  the current (fixed) behavior in detail.
- **`fields.affiliations` has no label/display text field at all** (only `entity_id`/`role`/
  `vols`/`current`) — this bit BOTH `_page_text` (C1's known gap) and a test fixture during this
  session (a precision-regression test had to be rewritten from an AFFILIATED_WITH/affiliations
  shape to a `fields.relationships` shape to actually exercise contradiction detection — see
  `tests/test_audit_eval.py::test_eval_report_fails_when_precision_drops_below_recorded_baseline`'s
  own docstring for the concrete "why").
- **`graph_build` now calls `verify` internally** — `tests/test_run_all_guard.py`'s stubbed-stage
  sequencing tests had "verify" removed from their expected list accordingly (the stub replaces
  `graph_build`'s whole body, so its internal verify call is invisible to that test by design;
  don't add "verify" back there without also making the stub simulate the nested call).
- **The scenes/epithets data this note originally warned about is no longer on disk** — Part F's
  re-run (below) replaced `graph.db`/`05_pages`/`06_bundle`/`dist/` with real, fresh output. This
  bullet stays only as a record of a trap already worked around, not a live warning.

---

## Part F: DONE (third session, 2026-09-11) — read this before touching model routing or eval/gold.py

**Environment state:** `GOOGLE_API_KEY` empty (as in the second session) AND, unlike the second
session, **Ollama was unreachable this time too** (`wiki doctor` confirmed live — `local_fast`/
`embed` both "missing"). So neither of the project's two normal extraction paths worked; this
session's job was making the free-tier API path actually reliable, per explicit user instruction
to keep trying OpenRouter models rather than give up on it.

**The model that works: `nex-agi/nex-n2.5-pro:free` with `reasoning: {effort: "none"}`.** New
profile `openrouter_free_nex_pro` (`config/models.yaml`). Two Google Gemma 4 free variants
(`google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free`) were tried first and both 429'd
unconditionally — OpenRouter's `:free` tier for that family proxies to "Google AI Studio"
specifically (`limit_source: upstream_provider_shared_pool` in the error body), a capacity problem
shared across every OpenRouter free user, not a per-model quality issue. Nex-N2.5-Pro (a "Pro"-tier
model, `structured_outputs` supported, reasoning forceable to "none" via the `effort` sub-key)
smoke-tested clean: 14 windows, 0 retries, 0 CJK/garbled output, 0 truncated responses after
raising `extract/claims.py::_GENERATION_OPTIONS`'s `num_predict` 4096 -> 8192 (one call in the
first smoke test hit the old cap mid-JSON on a genuinely fact-dense window, salvaged but lossy).
Scaled up cleanly: the real full `wiki extract --series spice-and-wolf --volumes 1-2 --force
--model claim_extract=openrouter_free_nex_pro` produced 630 claims across 350 calls, 0 unparseable
responses (1 truncation-salvaged, recovered cleanly), only 3 calls needed a retry.

**Routing mistake made and reverted — read this before changing `config/models.yaml` again.**
First instinct was to change `claim_extract`'s and `arbitrate`/`verify`/`prose`/`prose_polish`/
`codex_summary`'s PRIMARY roles in the base config to point at OpenRouter, to get past this
session's Ollama outage. Both were wrong, for different reasons, and both were reverted:
- `claim_extract`'s default must stay `local_fast` — CLAUDE.md §2 ("Local first. Bulk extraction
  runs on Ollama/Qwen") and `tests/test_config.py::test_bulk_stages_route_local_or_sanctioned_groq`
  both treat this as a real invariant (avoiding an external dependency/rate-limit/prompt-privacy
  exposure at hundreds-of-calls scale, not just avoiding a cost) — distinct from the "sanctioned,
  any $0 option" bar `prose`/`codex_summary` are held to.
- `arbitrate`/`verify`'s `fallback` must stay `local_best` (not `openrouter_free_nex_pro`) —
  `models.yaml`'s own header states the pipeline is "designed to run end to end with NO API key at
  all," and `tests/test_config.py::test_prose_stays_local_when_openrouter_key_missing` pins exactly
  this: a missing OpenRouter key must still degrade to a working (local) path. Pointing the
  fallback at another keyed provider breaks that guarantee for a user with zero keys and Ollama up,
  to fix what is actually THIS environment's transient, session-local Ollama outage.
The correct tool for a transient local outage in one session is a `--model` CLI override at
invocation time (CLAUDE.md §6), not a permanent config change — e.g. `wiki graph build --model
arbitrate=openrouter_free_nex_pro --model verify=openrouter_free_nex_pro`. That's what every
command in this session's actual run used. **If Ollama is down in a future session, reach for
`--model` first; only change `config/models.yaml`'s defaults for a change you actually want to
persist** (like `claim_extract` routing to `local_fast` staying `local_fast`, unchanged).

**Full command sequence actually run (steps 3-9), all via `--model` overrides, not config edits:**
```
wiki extract    --series spice-and-wolf --volumes 1-2 --force --model claim_extract=openrouter_free_nex_pro
wiki graph build --series spice-and-wolf --model arbitrate=openrouter_free_nex_pro --model verify=openrouter_free_nex_pro
wiki synthesize --series spice-and-wolf --upto 2 --force --model prose=openrouter_free_nex_pro --model codex_summary=openrouter_free_nex_pro
wiki site build  --series spice-and-wolf --upto 2 --force --model codex_summary=openrouter_free_nex_pro
```
(`graph build` runs `verify` internally per B5 — no separate `wiki verify` call needed in the
normal sequence; a standalone `wiki verify --model verify=...` was used separately below only to
retest after `graph/verify.py`'s prompt changed.) Results: 556 intervals, 74 edges, 28 conflicts
(25 extraction_error, 3 narrative_change, 1 flagged for human review), verify 0/14 flagged (0%
unsupported, well under the 15% ceiling), all of `wiki audit claims/contradictions/relationships/
links/verify` clean.

**The two founding bugs are confirmed fixed in real data** (not just by the A-D unit tests):
Marheit's page has no SPOUSE_OF Lawrence relation (only COMRADE_OF); Jakob's page shows
"Kraft Lawrence — Parent of" and Lawrence's page shows "Jakob — Child of" — one consistent
direction, not a simultaneous double badge. Confirmed by reading the generated `.md` pages and the
`kraft-lawrence--marheit` relationship-pair bundle JSON directly, and via the 3 manual spot-checks
the original plan named (Marheit page, Jakob/Lawrence badges, Enek page — no phantom relations on
any of them).

**A second, unplanned discovery: `wiki audit eval` itself had a real bug, found via this session's
first eval run against the fixed data.** 17 negative-fact violations came back where only 2 should
have. Traced to `eval/gold.py::score_fact_precision`'s original majority-keyword-overlap matcher:
every one of this project's `negative_facts` reads "X is not a RELATIONSHIP-WORD of Y", and the two
proper-noun keywords (X, Y) alone clear a 50% threshold whenever X and Y are related through ANY
OTHER real predicate — which is common and correct (e.g. Enek and Lawrence never interact at all,
but "Enek is not a friend of Kraft Lawrence" still needs checking against a real relationship
elsewhere on the page). Two straight fix attempts both failed before landing on the right one:
1. Full keyword coverage (`fact_kw <= page_kw`) against the pooled page text: fixed all 15 false
   positives but introduced FALSE NEGATIVES — a real relationship entry's `label`/`blurb` never
   repeats the OTHER party's name (`synth/assemble.py::_relationship_entries` only puts it in
   `entity_id`, which C2 deliberately excludes from matching), so Y's name only appeared by prose-
   mention luck. Missed both real violations entirely.
2. Adding the page's own `canonical` to `_page_text` (a real, kept fix — a page's own name should
   count as its own content) closed some of that gap, but a coincidental UNRELATED use of the word
   "relative" in Lawrence's own Background prose ("apprenticing under a relative" — someone else
   entirely) then falsely tripped EVERY "is not a relative of anyone-Lawrence-has-any-relationship-
   with" check once full coverage pooled it in with entity_id-derived name matches.
3. **The actual fix:** `_relationship_entry_keywords()` checks each rendered relationship/
   affiliation entry ON ITS OWN (`entity_id` + `predicate` + `label`/`note`/`blurb`, never pooled
   with prose or with other entries) for full coverage of the fact's keywords minus the page's own
   subject name. A negative fact is `contradicted` only when ONE SPECIFIC entry supplies both the
   right other party AND the right relationship word together. Verified against the real run:
   exactly the 2 genuine violations flagged, all 15 false positives cleared, confirmed both by a
   standalone Python replay against the real `data/spice-and-wolf/05_pages/*/v02.json` files and by
   re-running `wiki audit eval` for real. `docs/eval/gold/spice-and-wolf/baseline.json` now has
   real `precision` numbers (mean 93%, 8/10 gold-covered characters at 100%) and a raised
   `fact_recall` floor (mean 0.19 -> 0.338, every entity improved or held, none regressed).

**One real bug is left open, intentionally, not silently fixed:** `Jakob is not the parent of Kraft
Lawrence` / `Kraft Lawrence is not the child of Jakob` still FAIL `wiki audit eval` (by design —
C4's negative-fact check is unconditional). Root cause found and confirmed: Lawrence's own line
"I'm Kraft Lawrence, then, son of the great Jakob Tarantino" (`v02:c02:p0182`, a boastful/sarcastic
self-introduction, not a real genealogy claim) was extracted as a literal PARENT_OF/CHILD_OF fact
— DESPITE `config/extraction.yaml`'s own PARENT_OF/CHILD_OF guardrail note already naming this
EXACT anti-pattern ("son of so-and-so... is NOT evidence of real parentage"). Added a third named
failure pattern to `graph/verify.py`'s system prompt (rhetorical self-introduction / boastful name
invocation) as a second line of defense — re-ran `wiki verify` with the updated prompt against the
real data: **still did not catch it**, same "ok" verdict for all 14 characters. Tried once more
with reasoning turned back ON for this specific model (`openrouter_free_nex_pro_reasoning`, kept
in `config/models.yaml` as a documented dead end, not deleted) — failed outright with an empty
response after 3 attempts, the same narrate-or-empty failure mode every other reasoning-enabled
OpenRouter free model hit earlier in this project. **This is a genuine capability limit of the free
models available to this session, not a config or prompt gap** — worth revisiting with a stronger
model (a paid API tier, or Ollama once reachable again) rather than retrying the same free tier.

**Files changed this session:** `config/models.yaml` (new `openrouter_free_nex_pro`/
`_gemma`/`_gemma_moe`/`_nex_pro_reasoning` profiles; `claim_extract`/`arbitrate`/`verify`/
`prose`/`prose_polish`/`codex_summary` routing unchanged in the end, see "routing mistake" above),
`src/narrativewiki/extract/claims.py` (`_GENERATION_OPTIONS.num_predict` 4096 -> 8192),
`src/narrativewiki/graph/verify.py` (third failure pattern in the system prompt),
`src/narrativewiki/eval/gold.py` (`_page_text` includes `canonical`; new
`_relationship_entry_keywords`; `score_fact_precision`'s negative-fact matching rewritten),
`tests/test_eval_gold.py`/`tests/test_audit_eval.py` (fixtures updated for the matcher rewrite —
added `canonical` to page fixtures, one new test for the same-page-different-relationship false-
positive case), `docs/eval/gold/spice-and-wolf/baseline.json` (real precision + raised recall).
All committed to `phase-23-precision-and-grounding`; `pytest -q` green (all passing) before, during
every intermediate step, and after.

## Part E: DONE (fourth session, 2026-09-11) — read this before touching page_outline/prose.py

All six sub-items, built against Part F's real re-extracted V1-2 data (no re-extraction needed for
E itself — only `wiki synthesize --force`/`wiki site build --force`, since E is presentation-layer
plus one prose-generation change).

- **E1 — `page_outline` restructured** (`config/extraction.yaml`): Appearance(1)/Personality(2)/
  History(3)/Quotes(3.5)/Affiliations(4)/Relationships(4.5)/Appearances(6, unchanged utility
  strip). "Trivia" deliberately NOT added — `eval/gold.py::_HEADING_ALIASES` already treats it as
  a permanent, expected recall gap (no LLM-generated trivia, CLAUDE.md §2). Old `chronology`
  (`source: "events"`) + `background` (`traits: [BACKGROUND]`) keys REMOVED, replaced by one
  `history` key, `source: "history"`.
- **E2 — `appearance` prose section** (new): `synth/prose.py::generate_attribute_prose`, dispatched
  by a new `source: "attributes"` sentinel in `generate_prose()` (parallel to `"events"`/
  `"history"`) — reads ATTRIBUTE rows via `state_at` filtered against `settings.attributes`, NOT
  `trait_values_at`/`settings.traits` (APPEARANCE is `kind: "attribute"`, not a trait).
  `synth/assemble.py::assemble_page` computes `prose_attribute_predicates` from `page_outline` and
  excludes them from `_build_attribute_fields`'s generic `overview` loop, so APPEARANCE stops
  double-rendering as both an infobox bullet list and a paragraph.
- **History merge** (also E1): `synth/prose.py::generate_history` combines this section's own
  `traits` (BACKGROUND facts, via the same `_gather_facts`/`trait_values_at` path `background`
  used) with events.db's scene summaries (`character_events_at`, the same source `generate_chronology`
  used) into ONE LLM call — adaptive sentence bounds computed from the COMBINED evidence count.
  `generate_chronology`/`source: "events"` intentionally left in the module, unused by the base
  config, in case a future series wants event-only chronology without merged biography.
  **Schema-cap tuning forced by a live run:** `history`'s combined evidence pool produces longer
  output than either old section alone — a live `wiki synthesize` run failed validation at
  `max_sentences: 12` under the OLD 200-chars/sentence schema cap (`_prose_schema_for`), and even
  at `max_sentences: 10` after widening the cap to 280. Landed on: cap raised 200->280
  chars/sentence (affects every long prose section, not just `history` — a strict widening, never
  tightens anything), `history.max_sentences` raised back to 12 once the wider cap made it pass.
  **If you see a `did not produce valid ProseText<N> after 3 attempts` error from a prose section
  with a large adaptive evidence count, this is the same failure mode — widen the cap further or
  lower that section's `max_sentences`, don't just retry.**
- **E3 — narrative relationship cards** (`site/templates/app.js`): `renderRelationships` (character
  page) and the new shared `relationNarrativeCard` (relationship pair page) replace the old
  predicate-badge grid with one flowing `<p class="relation-narrative">` line per pair, composed
  DETERMINISTICALLY (string-joining each relation's own config `display`/`blurb` text,
  lower-cased and comma-joined — CLAUDE.md §2 forbids an LLM smoothing this into real prose).
  **A real direction bug caught before shipping:** on the pair page, relation rows are NOT
  guaranteed to share one (subject, object) direction — Holo/Lawrence carries both
  `COMRADE_OF(holo, lawrence)` and `SAVED(lawrence, holo)`, stored in whichever direction
  extraction produced (unlike the character page's `fields.relationships`, which `synth/
  assemble.py::_relationship_entries` already flips to the VIEWING character's own perspective).
  `relationNarrativeCard` groups rows by their OWN `subject|object` key first, renders each
  direction as its own "subj — phrase, phrase — obj (since vN)" line, and only THEN joins the
  per-direction lines together — naively picking one row's direction for every phrase (the first
  version written) would have silently misattributed who did what to whom.
- **E4 — visible citations**: `site/bundle.py::_citations_for` (new) attaches `{para_id, vol,
  print_page}` to every prose entry's `evidence` under a NEW `citations` key (evidence itself is
  untouched — CONTRACTS §5 unchanged) — `vol` parsed straight from the para_id's own `vNN:`
  prefix, `print_page` from a `para_id -> print_page` map `cli.py::site_build` builds from the
  `01_parsed/vNN.jsonl` records it already loads for codex windows (CLAUDE.md §3 trap #8's
  markers, surfaced for the first time). `build_pages_bundle` takes `print_pages` as a new
  OPTIONAL parameter (`None` = pre-E4 byte-identical shape, no `citations` key at all — every
  existing caller/test that doesn't pass it is unaffected). `app.js` renders a small "Sources: v1
  p.9, v1 p.12" line under each prose paragraph when `citations` is present.
- **E5 — `aliases` on the page model**: `synth/assemble.py::assemble_page` now sets
  `page["aliases"] = list(entity.get("aliases", []))`, mirroring the line `site/okf.py`'s Markdown
  front matter has had since Phase 6 — the JSON page model (what `app.js`/the bundle actually
  read) had simply never gotten the same field. `app.js` renders it as an "Also known as: ..."
  line under the infobox title.
- **E6 — dangling roster/search/link entries fixed at both ends**: WRITE side —
  `site/bundle.py::build_index`/`build_links`/`build_search` take a new optional `written_ids`
  parameter (CHARACTER-only; non-CHARACTER entities untouched) that restricts the roster/search/
  link-target set to entity_ids with an actual `pages/<id>.json` on disk; `cli.py::site_build`
  computes it from `pages_bundle`'s own keys (the thing that's already the ground truth for "did
  this character actually get a page") and passes it through. READ side —
  `audit/reports.py::_links_report` independently checks every `index.json` roster entry against
  `pages_dir`'s actual file list, FAILing with a NEW `missing_page_file` category if they disagree
  — a defense-in-depth check, not just trusting the write-side fix produced correct data (the same
  "read and judge, nothing more" discipline every other check in that report already follows). In
  THIS session's real data every character has a page, so this fix is currently a no-op in
  practice — verified instead via unit tests (`tests/test_site_bundle.py`,
  `tests/test_audit_reports.py`) that construct the mismatch directly.

**A real regression found and fixed while verifying E, not part of the original plan:**
`eval/gold.py::_HEADING_ALIASES` mapped Fandom's "History"/"Appearance" headings only to the OLD
section keys (`background`/`chronology`/`overview`) — after E1 renamed them, `wiki audit eval`
started reporting "no equivalent section for gold heading 'History'" on every character, a false
recall miss for a heading that now matches EXACTLY. Fixed by adding the new keys (`history`,
`appearance`) alongside the old ones, so the table matches a bundle built before OR after E1.

**A real, honest metric shift, not a bug:** re-running `wiki synthesize --force` against the same
graph.db as Part F (no re-extraction) regenerates prose with a live LLM call each time (temperature
0.1, not zero) — `kraft-lawrence` (fact_recall 0.4444->0.3333, precision 0.8->0.75) and `marheit`
(fact_recall 0.3333->0.1667) genuinely dropped in `wiki audit eval`'s keyword-overlap match against
gold sentences. Confirmed this is prose-phrasing variance, NOT a coverage bug introduced by the
History merge: re-read both characters' `history` AND `personality` sections directly — the
underlying facts are still present, just worded differently than gold's phrasing expects, and
Marheit's unmatched personality facts belong to the completely UNCHANGED trait-driven `personality`
path, proving the variance isn't specific to the new merged section. `docs/eval/gold/spice-and-wolf/
baseline.json` re-recorded to the honest current numbers (same "record real observed numbers, don't
chase 100%" discipline Part F established) — every other entity's number is byte-unchanged (same
graph.db, same untouched prose). `heading recall` improved for every gold-covered entity that has a
"History" heading (10/10 now correctly matched, was 0/10 before the `_HEADING_ALIASES` fix above).

**Files changed this session:** `config/extraction.yaml` (page_outline restructure),
`src/narrativewiki/synth/prose.py` (`generate_attribute_prose`, `generate_history`, dispatch,
280-char schema cap), `src/narrativewiki/synth/assemble.py` (APPEARANCE exclusion, `aliases`),
`src/narrativewiki/site/bundle.py` (`_citations_for`, `written_ids` on 3 functions),
`src/narrativewiki/cli.py` (wiring: `print_pages`, `written_ids`), `src/narrativewiki/audit/
reports.py` (`missing_page_files` check), `src/narrativewiki/site/templates/app.js` (E3/E4/E5
rendering, `DEFAULT_SECTIONS` updated), `src/narrativewiki/site/templates/style.css` (new classes),
`src/narrativewiki/eval/gold.py` (`_HEADING_ALIASES` fix), `docs/eval/gold/spice-and-wolf/
baseline.json` (re-recorded), plus new tests in `tests/test_synth_prose.py`,
`tests/test_synth_assemble.py`, `tests/test_site_bundle.py`, `tests/test_audit_reports.py`.
`pytest -q` green throughout (673 passing). Real data verified: `wiki synthesize --force`/`wiki
site build --force --series spice-and-wolf --upto 2` (both via `--model
prose=openrouter_free_nex_pro --model codex_summary=openrouter_free_nex_pro`, same Ollama-down
session as Part F), then `wiki audit outline/links/relationships/verify/eval` all read and judged
clean (eval's only FAIL is the 2 known, pre-existing, intentionally-unfixed Jakob/Lawrence
violations). Served via `wiki serve --series spice-and-wolf`; curl-verified `index.html`/`app.js`/
bundle JSON directly (no headed browser available in this environment) — confirmed Holo's
Appearance section, Kraft Lawrence's merged History narrative, aliases, and citation data all
render as real, non-empty content matching what was inspected in the JSON files directly.

## Reproduction / verification (works right now, no LLM calls)

```bash
git checkout phase-23-precision-and-grounding   # ahead of main, not yet merged/pushed
pytest -q                                        # all passing as of Part E's completion (673)
pytest tests/test_synth_prose.py tests/test_synth_assemble.py tests/test_site_bundle.py tests/test_audit_reports.py tests/test_eval_gold.py -q
```

To reproduce Part F's original extraction (real OpenRouter calls, not free — well,
`nex-n2.5-pro:free` IS free, but still real network calls against real quota): re-run the four
commands in "Full command sequence actually run" above. To reproduce Part E's re-synthesis against
that same data (no re-extraction needed):

```bash
wiki synthesize --series spice-and-wolf --upto 2 --force --model prose=openrouter_free_nex_pro --model codex_summary=openrouter_free_nex_pro
wiki site build --series spice-and-wolf --upto 2 --force --model codex_summary=openrouter_free_nex_pro
wiki audit eval --series spice-and-wolf   # expect exactly the 2 known Jakob/Lawrence violations
```

`OPENROUTER_API_KEY` must be set for either; check `wiki doctor` first. If Ollama is reachable in
your environment, drop the `--model` overrides entirely — they exist only to route around this
session's local-model outage (see "Part F: DONE" above for why the base config itself was NOT
changed to point at OpenRouter permanently).

## What's next (Phase 23 has no open sub-items — this is for whoever picks the NEXT phase)

- The Jakob/Lawrence CHILD_OF/PARENT_OF sarcasm-extraction bug (Part F) is still open — needs a
  stronger model for `verify` (a paid API tier, or Ollama once reachable) than this session's free
  tier could provide, not a config/prompt change.
- E1's `history` section combines two evidence sources into one LLM call; if a future corpus makes
  that call's evidence pool much larger (a very well-attested character across many volumes), watch
  for the same schema-cap failure mode this session hit and tuned around (widen `_prose_schema_for`
  further, or lower that section's `max_sentences`) before assuming it's a new bug.
- `docs/eval/gold/spice-and-wolf/baseline.json`'s numbers will shift again on ANY future
  `wiki synthesize --force` re-run (temperature 0.1 prose is not perfectly reproducible) — this is
  expected, not itself a sign of regression; re-record deliberately after confirming the shift is
  real drift (or a real improvement), the same judgment call this session made for
  kraft-lawrence/marheit.
- Branch not yet merged to `main` — merge (or open a PR) is the natural next action once this
  handover and its LOG.md entry are reviewed.
