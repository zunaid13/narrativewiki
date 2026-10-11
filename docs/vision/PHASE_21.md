# Phase 21 — cross-entity pages + evaluation

Full requirement originally recorded in `docs/vision/PHASE_17.md`'s 2026-09-04 "Fandom-grade
depth: the ceiling is the ontology, not the model (Phases 17-21)" entry: "cross-entity pages +
evaluation — Relationship pages (pair-scoped subgraph + shared scenes), faction pages,
per-volume timeline pages; `graph/ppr.py` currently feeds only `mentions_of` and gets repointed
at per-section retrieval. Evaluation is not optional — depth and hallucination are
indistinguishable from the inside: hand-transcribe the fact list and outline from three real
Fandom pages, then measure heading recall, fact recall, and citation entailment." This file is
split out now (rather than continuing to file entries under PHASE_17.md) because Phase 21 is
itself multiple independent deliverables large enough to span several sessions.

---

## 2026-09-08 — Relationship pages: scope and design decisions (part 1 of 4)

**What:** Implemented the first of Phase 21's four deliverables: pair-scoped relationship pages
for CHARACTER-CHARACTER pairs. Full implementation details in `LOG.md`'s 2026-09-08 entry and
`docs/CONTRACTS.md` §6.4.

**Why these specific scope cuts (recorded here because they are judgment calls a future session
should not silently re-litigate):**

- **Deterministic v1, no LLM summary.** The vision entry says "relationship pages," not
  "relationship summaries." Phase 20 already established two patterns for a new page surface —
  `build_quotes_section` (deterministic, no LLM) and `_generate_codex_summary` (LLM, gated on
  evidence). Relationship pages follow the first: relation history + shared scenes are exactly
  what `graph.db`/`events.db` already contain, with no need for a model to paraphrase anything.
  An LLM-generated one-sentence relationship summary (mirroring `codex_summary`) is a clean,
  separately-scoped follow-up if a future session wants it — not bundled in here.
- **Population is "pairs with a relation edge," not every possible pair.** A relationship page
  for two characters who are merely co-mentioned but never assigned a relation predicate would be
  indistinguishable from a random pairing. `site/bundle.py::_relationship_pairs` derives the
  population directly from `graph.db`'s `intervals` table (`object IS NOT NULL`), the same
  ground truth `relations_at` already uses for a character's own Relationships field.
- **No per-viewer label flip.** `synth/assemble.py::_relationship_entries` flips a non-symmetric
  predicate to its `inverse` because a character page only knows "the other side," not which
  storage direction was canonicalized. A pair page names both parties explicitly, so
  `graph/contradictions.py::_canonicalize_relation`'s own invariant (subject/object always
  correctly oriented relative to the canonical predicate) means `relations_between`'s rows can
  render as-is — this was verified against the actual canonicalization code, not assumed.
- **`graph/ppr.py` left untouched.** The vision entry's "PPR gets repointed at per-section
  retrieval" is a Phase 21 idea generally, not a relationship-page requirement specifically —
  pair pages use direct `relations_between`/`shared_events_at` queries. Repointing PPR (if it
  turns out to matter for faction pages or timelines) is deferred to whichever later part of
  Phase 21 actually needs it.

**Implies:** Parts 2-4 (faction/codex page enrichment, per-volume timeline pages, the evaluation
harness) remain open — see `LOG.md` for the up-to-date status of which is next.

**Status:** Done (Phase 21, part 1 of 4).

## 2026-09-08 — Faction codex enrichment: scope and design decisions (part 2 of 4)

**What:** Implemented the second of Phase 21's four deliverables: a FACTION codex entry
(`codex/factions.json`) gains `key_events` — scenes where two or more of the entry's current
`members` co-appear. Full implementation details in `LOG.md`'s 2026-09-08 entry and
`docs/CONTRACTS.md` §6.1.

**Why these specific scope cuts:**

- **"Faction pages" reads as "richer faction codex entries", not a new unique page type.**
  `config/extraction.yaml` already declares FACTION as `page: codex` (CLAUDE.md §2 — only
  CHARACTER gets a unique page); nothing in the original vision entry asked to change that. The
  gap this part closes is that a codex entry only ever had a one-sentence `summary` +
  `members`/`related` — no sense of what the group actually DID together, which is exactly what
  Phase 20's `quotes` and Phase 21 part 1's `shared_scenes` gave characters and pairs.
- **Co-presence of >= 2 current members, not "any event touching one member."** A well-attested
  faction's roster can rack up dozens of events through a single popular member — that list would
  say nothing about the faction as a group. Requiring 2+ members co-present (mirroring part 1's
  own pair-based `shared_events_at`, generalized) keeps the field meaningfully about the faction
  acting together. `graph/events.py::group_events_at` is the new sanctioned reader for this.
- **Config-gated per codex `kind`, never hard-coded to the string "factions".** `codex_pages.
  <kind>.max_key_events` — present only under `factions` in the shipped config — is what
  `build_codex_bundles` branches on, not the kind name. A LOCATION/EVENT codex entry (`places`)
  already IS the event/place (its own evidence covers "what happened here"); a TECH entry isn't a
  group of co-present people. Neither gains anything from this field, and because `_state_hash`
  only folds `key_events` into its payload when the kind's config declares `max_key_events`, their
  hash values — and therefore their `codex_summary` LLM-call cadence — stay byte-identical to
  before this part existed. A future series or codex kind that DOES want this just adds the config
  key; no code branch needed.
- **No faction-to-faction relations added.** Investigated `config/extraction.yaml`'s `relations`
  block: `AFFILIATED_WITH` is the only relation with `object_types: [FACTION]`, and it is
  CHARACTER-subject only (extraction is a per-character driver, `extract/claims.py`). A "rival
  factions" or "allied factions" enrichment would need a genuinely new relation predicate (and
  probably a new extraction pass, since no existing claim ever has a FACTION subject) — a bigger,
  separately-scoped change than this part's evidence-surfacing goal, not attempted here.
- **No roster history (join/leave over time).** `graph/temporal.py::relations_at`'s own docstring
  already documents the gap this would need closed: relation intervals never close except for a
  `conflicts_with` group (Phase 17), and `AFFILIATED_WITH` isn't one — so there is no way today to
  know a character LEFT a faction, only that they were ever affiliated. The existing sparse-cutoff
  mechanism already reflects membership GROWTH correctly (a new cutoff is written the moment
  `members` changes, per `_state_hash`); modeling departure is a graph-level change, not a codex
  one, and out of scope here.

**Implies:** Parts 3-4 (per-volume timeline pages, the evaluation harness) remain open — see
`LOG.md` for the up-to-date status of which is next.

**Status:** Done (Phase 21, part 2 of 4).

## 2026-09-08 — Per-volume timeline pages: scope and design decisions (part 3 of 4)

**What:** Implemented the third of Phase 21's four deliverables: `data/06_bundle/timeline/
v{NN}.json`, a chapter-by-chapter recap of one volume's own events, plus `/timeline` and
`/timeline/<vol>` routes in the viewer. Full implementation details in `LOG.md`'s 2026-09-08 entry
and `docs/CONTRACTS.md` §6.5.

**Why these specific scope cuts:**

- **One volume's own events, not a cumulative "story so far."** `graph/events.py::events_at`
  already gives "everything visible through cutoff V" (used by `character_events_at`/Chronology
  prose); a timeline page's job is different — "what happened IN volume V specifically," so a
  reader can walk the story chapter by chapter one volume at a time. This needed a new reader
  (`events_in_volume`, `WHERE vol = ?` rather than `WHERE vol_start <= ?`) rather than reusing or
  generalizing an existing one — the semantics genuinely differ, generalizing them into one
  function would have made both call sites pass a flag to pick a filter mode for no real gain.
- **No sparse-multi-cutoff shape, unlike every other §6 file.** `events.vol_start` always equals
  `vol` (CONTRACTS §4b.1 — an event is anchored to its own volume, never forward-dated), so a
  timeline file's content is permanently fixed the moment `wiki events-build` runs; there is
  nothing for a later `--upto` rebuild to change. Giving it the same cutoffs/state-hash machinery
  `build_codex_bundles`/`build_relationship_bundles` need would have been complexity with no
  payoff — the simplest correct shape here really is "one stable file per volume, present or not."
- **Deterministic v1, no LLM narrative.** Consistent with every other Phase 20/21 evidence surface
  (`quotes`, `shared_scenes`, `key_events`) before it — the underlying `beat_summary`/`note` text
  already reads as prose (LLM-paraphrased at scene-extraction time), so a second LLM pass to
  narrate "volume 1's story" would be re-paraphrasing an already-paraphrased summary for
  questionable gain. An LLM-narrated volume recap is a clean, separately-scoped follow-up.
- **The volume picker gates on the READER's own slider position, not the build's `--upto`.**
  `renderTimelineIndex` loops `1..state.vol`, not `1..state.index.upto_vol` — a bundle built at
  `--upto 5` still must not let a reader who has only moved their slider to volume 2 see a
  "Volume 3 Timeline" link. This mirrors every other per-volume-gated UI element in the viewer
  (the character roster, codex entries); verified live in the DOM-stub check (see LOG.md).
- **`state_changes` gets its first-ever renderer here**, not in Phase 19/20. Chronology prose
  already consumes `event_claims` state_change rows (folded into paraphrased prose), but nothing
  before this rendered one directly. A timeline page is exactly the surface where showing the raw
  `note` text (rather than an LLM's re-paraphrase of it) earns its place — it is already a
  paraphrase once, at scene-extraction time, and showing it verbatim here costs no LLM call.
- **A real, pre-existing bug found (not introduced) by this part's own live-UI check, fixed in
  passing:** `app.js::nameFor(null)` rendered the literal text "null" for a quote whose speaker
  scene extraction never resolved. This was already reachable through `renderSceneCard`'s two
  earlier callers (relationship shared_scenes, faction key_events) before this part existed;
  the timeline page's DOM-stub check just happened to be the first time this session's live
  verification hit a real unresolved-speaker quote. Fixed by making `nameFor` fall back to
  "Unknown" — a one-line, self-contained fix, not a scope expansion of this part's actual work.

**Implies:** Part 4 (the evaluation harness) remains open — see `LOG.md` for status.

**Status:** Done (Phase 21, part 3 of 4).

## 2026-09-08 — Evaluation harness: scope and design decisions (part 4 of 4, Phase 21 complete)

**What:** Implemented the fourth and final deliverable of Phase 21: `wiki audit eval`, computing
heading recall, fact recall, and citation entailment against hand-transcribed gold data from three
real Spice & Wolf Fandom wiki pages (Holo, Kraft Lawrence, Norah Arendt — the three well-attested
characters within the project's own volumes 1-2 testing scope). Full implementation details in
`LOG.md`'s 2026-09-08 entry and `docs/CONTRACTS.md` §8.

**Why these specific scope cuts:**

- **`in_scope: true/false` per gold fact, not a flat fact list.** The vision entry's own framing —
  "depth and hallucination are indistinguishable from the inside" — assumes the comparison is
  fair. A real Fandom page describes the character across the WHOLE series; this wiki at
  `eval_vol` 2 is CORRECTLY supposed to omit anything revealed later (CLAUDE.md #1). Scoring recall
  against those facts would have measured spoiler-safety compliance as a defect. Concretely: Holo
  and Lawrence's eventual marriage and bathhouse in Nyohhira (the sequel series' setting) is
  excluded; Lawrence being "respected by Eve and Eringin" is excluded because neither appears in
  the extracted v1-2 roster at all — cross-checking a candidate gold fact's named entities against
  the project's OWN roster turned out to be a genuinely useful, cheap sanity signal for "is this
  even in scope," used throughout the transcription.
- **Uncertain-provenance facts excluded conservatively, not guessed.** A few real facts (e.g.
  "Holo is willing to reveal her true wolf form to protect Lawrence") are plausible by volume 2 but
  not something transcription could confidently place to a specific volume from memory alone —
  marked `in_scope: false` with a note, rather than asserted. Wrong gold data would be worse than
  incomplete gold data: it would blame the pipeline for not recalling something never actually
  guaranteed to be there yet.
- **WebFetch of fandom.com returned HTTP 402 in this sandbox** (a bot/paywall gate, not a project
  decision) — transcription used several targeted WebSearch queries against the same
  `spiceandwolf.fandom.com` pages instead of one full-page fetch. Documented in each gold file's
  header comment as a real, non-hidden constraint on completeness, not silently worked around.
- **Both recall metrics are lexical keyword-overlap heuristics, not an LLM judge.** Consistent
  with CLAUDE.md §2's "local first," no-wasted-call discipline extended to evaluation itself — an
  LLM-as-judge pass over 3 characters' worth of facts was a real option, deliberately not taken, in
  favor of a deterministic, free, immediately-rerunnable check. The tradeoff surfaced live: real
  facts already present in the generated pages (Norah's tailor dream, her sheepdog Enek, her Church
  background — all confirmed present by directly reading `data/05_pages/norah-arendt/v02.json`)
  scored as "not recalled" because the exact wording differed enough that keyword overlap fell
  under the found-threshold. This is a real, known limitation of a lexical heuristic, not a defect
  in the actual generated wiki content — `_eval_report`'s own docstring and CONTRACTS §8 call this
  out explicitly, and the report always prints the per-fact miss list specifically so a human
  reviewer catches false negatives like this one by eye rather than trusting the number alone.
- **Citation entailment needs no gold data — it self-checks the page's own citations** (does the
  cited paragraph exist, does the prose share vocabulary with it), rather than trying to verify
  facts against an external source, which a lexical heuristic cannot do reliably. Live run finding:
  `chronology` sections scored "weak overlap" for all three characters (Norah's had zero cited
  paragraphs at all) — traced to `generate_chronology`'s `evidence` list only collecting
  `event_claims` para_ids as a bonus, not the underlying `beat_summary` paraphrases the prose is
  actually built from (Phase 19 design, CONTRACTS §4b.2's "the one un-gated field"); the citation
  entailment check does not currently look at `beat_summary` provenance at all. Left as a
  documented known gap rather than fixed here — fixing it is a Phase 19/`eval/gold.py` design
  question of its own, out of this part's scope.
- **No new top-level CLI command.** `wiki audit eval` reuses the existing `audit/reports.py`
  registry (`@register("eval", "wiki synthesize")`) exactly like every other phase's report,
  inheriting `wiki audit run`'s HTML export for free — consistent with "every phase has one"
  (CLAUDE.md file map) rather than inventing a parallel `wiki eval` surface.
- **Descriptive, not a spoiler-safety gate.** `_eval_report` FAILs only on a structural problem (a
  gold `entity_id` with no generated page at all) — never on a low recall/entailment score. Depth
  and hallucination-avoidance quality are a continuum for a human to read and judge from the
  report's printed detail; CLAUDE.md #1's one hard boolean invariant stays `test_spoiler_leak.py`'s
  job, not this one's.

**Status:** Done (Phase 21, part 4 of 4). **Phase 21 is now complete** — all four deliverables
(relationship pages, faction codex enrichment, per-volume timelines, evaluation harness) shipped.

## 2026-09-08 — Closing the "chronology citation entailment" known gap: eval-only, not page-widening

**What:** Fixed the first known gap listed above and in `docs/handover/PHASE_21.md`: a chronology
section with no `event_claims` (state_change/quote) scored "0 cited paragraphs" / "weak overlap"
even when well-grounded, because `synth/prose.py::generate_chronology`'s stored `evidence` never
included each event's own `core_para_ids` (`graph/events.py`) — the paragraphs `beat_summary` was
actually paraphrased from.

**Why this specific fix, over the alternative already named in the known-gap text:** The known gap
named two options — widen what `generate_chronology` records as `evidence`, or teach
`score_citation_entailment` to check `core_para_ids` separately. The first was tried and reverted
in this same session: `core_para_ids` is chapter-span-scale (12-158 paragraphs per scene in the
live spice-and-wolf v1-2 corpus, not a handful), so folding it into a character's stored page
evidence made Holo's `evidence` list balloon to **5103** entries and her `v02.json` grow from
10KB to 142KB — for a character present in most scenes, "evidence" degenerated into "somewhere in
most of the corpus," which is technically defensible (beat_summary genuinely was paraphrased from
that whole span) but useless as a citation and a real regression against CLAUDE.md §2's token/data
discipline once run across a full 13-volume corpus. **Chose the second option instead**: `graph/
events.py`'s `events` table gained a `core_para_ids_json` column (additive, harmless — exposes an
event's true grounding to anyone who queries it, e.g. a future `wiki explain`-style tool), but
`generate_chronology`'s own `evidence` stays event_claims-only, exactly as before. `eval/gold.py::
score_citation_entailment` gained optional `events_conn`/`entity_id`/`vol`/`events_source_keys`
kwargs: for a `source: "events"`-configured section only (chronology, identified generically via
`page_outline`, never hard-coded by key name), it ALSO checks vocabulary overlap against the union
of that character's events' `core_para_ids` — on demand, printed only in the eval report, never
written to `data/05_pages/`. Live re-run confirmed the fix: Norah Arendt's chronology now reports
`grounded (0 cited paragraph(s); beat_summary check: grounded (966 paragraph(s)))` instead of the
previous `weak overlap` — while her page's own stored `evidence` count stays 0, unchanged.

**Implies:** The other three known gaps from part 4 (gold-data coverage beyond 3 characters, no
faction-to-faction relations / roster-departure history, `graph/ppr.py` still untouched) remain
open — see `docs/handover/PHASE_21.md`.

**Status:** Done.

## 2026-09-09 — Extending eval gold-data coverage: Jakob (Jacob Tarantino)

**What:** Closed known-gap #2 partially: added `docs/eval/gold/spice-and-wolf/jakob.yaml`, a 4th
gold-data character (entity_id `jakob`, real name Jacob Tarantino — master of the Ruvinheigen
branch of the Rowen Trading Guild), picked as the next best-attested character in the extracted
v1-2 roster after the original three (Holo, Lawrence, Norah Arendt) — richer than the other 10
generated pages (5 structured fields + 2 prose sections vs. 0-2 fields for most of the rest).

**Why this character, and why the outline omits "History":** His Fandom page is tagged
`Category:Article stubs` and has a `/Gallery` subpage but no WebSearch evidence of a distinct
History heading — rather than guess one exists (the same conservative posture part 4's own gold
files already use for uncertain facts), the transcribed `outline` only lists headings with real
evidence (Appearance, Personality, Relationships, Trivia, Gallery). Confirmed via WebSearch that
every fact found belongs entirely to Volume 2's Ruvinheigen arc — no later-series spoiler risk for
this minor character, so every fact is `in_scope: true`.

**Live result, cross-checked against the generated page (not just the recall number):** 1/9 facts
recalled (11%) — genuinely low, not a lexical false negative like Norah's chronology case. Read
`data/05_pages/jakob/v02.json` directly: `appearance` extracted only `"giant"` (no hair/mustache/
build/clothing — the Fandom summary's appearance detail was never captured at all), and the
extracted `personality` prose describes different traits (understanding, cunning, detects lies,
overbearing) than the gold facts (friendly, treats members like his own children) — plausibly a
different source passage, not a paraphrase of the same one. This is a real, useful signal about
extraction depth for a minor character, exactly what the eval harness exists to surface.

**Implies:** Gold coverage is now 4/14 generated characters. Extending further (the next
candidates by content richness: Liebert, Hans Remelio) or tuning lexical thresholds remains open.

**Status:** Done.
