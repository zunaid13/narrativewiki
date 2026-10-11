# Phase 18 — Chapter-major scene extraction + epithet alias mining

**Status:** Complete · **Started:** 2026-09-04 · **Finished:** 2026-09-06

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## Why this phase exists

Phase 17 fixed *quality* (near-duplicate values, relation conflicts). Phase 18 fixes *coverage*.

Two measured gaps from this project's own output (Spice and Wolf v01-v02):

1. **The mention-window cap discards exactly the scenes that matter.** At 40 windows/character,
   Holo's v01 pass saw 33.6% of the volume's paragraphs; 62.8% were available. The windows are
   chosen by mention count, so the quiet character-development scenes — which carry status changes,
   relationship transitions, and character-revealing dialogue — are exactly what gets dropped.
   A friend who becomes an enemy mid-volume and is never re-extracted is a fact the graph can never
   see and therefore can never close the interval for.

2. **Pronoun-and-epithet blindness.** Aho-Corasick cannot match “the wisewolf” until that surface
   form is in the gazetteer. Before this phase, epithets were never mined. A chapter where Holo is
   only referred to as “the wisewolf” produced zero extraction windows and zero claims, even though
   the chapter existed and was ingested.

The fix is a second pass that reads **every paragraph in every chapter** — not just paragraphs
that contain a known entity mention — in overlapping ~4k-token spans. Coverage becomes 100% by
construction, and the whole-chapter context carries its own antecedents, so the pronoun problem
largely dissolves without a coreference model.

---

## What exists now

### New files

\src/narrativewiki/extract/spans.py
    build_chapter_spans(vol, chapter_idx, records, span_cfg) -> list[Span]
    A Span carries: vol, chapter_idx, span_index, para_ids (all paras in this window, including
    overlap), core_para_ids (unique slice -- union of all spans' core_para_ids == all chapter
    paras, no gaps, no duplicates), and text (the labeled passage for the LLM prompt, one
    paragraph per line with its para_id in brackets). Span size is controlled by
    extraction.scene.span_target_tokens / span_overlap_tokens in config/extraction.yaml.

src/narrativewiki/extract/scene_schema.py
    Pydantic models. Three groups:
    - ExtractedQuote / ExtractedStateChange / ExtractedEpithet -- what the LLM returns per item
    - SceneExtractionResult -- the whole span response; its @model_validator drops individual items
      missing a structurally required field, same posture as schema.py::ExtractionResult
    - SceneRecord / EpithetRecord -- the validated on-disk shapes (CONTRACTS 3b / 3b.1)
    - make_scene_id(vol, chapter_idx, span_index) -> “sn_v01c03s002”

src/narrativewiki/extract/resolve.py
    Surface-form resolution helpers shared by claims.py and scenes.py:
    - resolve_surface(text, candidates) -> entity_id | None
    - normalize_para_id(raw, span_para_ids) -> canonical_id | None  (validates the LLM's para_id
      against the actual span; accepts bare “p0031” and returns the full “v01:c03:p0031”)
    - unwrap_quote(text) -> stripped text without extra enclosing quotation marks the model added
    - chapter_of_para_id(para_id) -> int

src/narrativewiki/extract/scenes.py
    extract_chapter_scenes(vol, chapter_idx, records, mentions, entities_by_id, settings, client)
        -> (scene_records, epithet_records, drop_reasons)
    extract_volume_scenes(vol, records, mentions, all_entities, settings, client, on_progress)
        -> (scene_records, epithet_records, drop_reasons)
    One call to the model per span; results validated/resolved by _build_scene_record,
    _build_state_change, _build_quote, _build_epithet. Quotes and epithets deduped across
    overlapping spans by (para_id, quote)/(entity_id, para_id, text) keys.
    STAGE = “scene_extract” (routes through config/models.yaml routing.scene_extract).
\
### Modified files

\src/narrativewiki/entities/alias.py
    add_surface_form(entity, text, first_vol, source) -- new helper used by
    gazetteer.merge_epithets; adds a surface form only when it does not already exist for
    this entity.

src/narrativewiki/entities/gazetteer.py
    merge_epithets(gaz, epithet_records, min_confidence) -- folds high-confidence mined
    epithet mentions into gazetteer surface_forms; called by cli.py::_merge_epithets_into_gazetteer.

src/narrativewiki/paths.py
    SCENES_DIR = data/02b_scenes/  (already declared in the prior phase's paths setup)
    scenes_volume(vol) -> data/02b_scenes/v{NN}.jsonl
    scene_epithets(vol) -> data/02b_scenes/epithets_v{NN}.jsonl

src/narrativewiki/cli.py
    wiki scenes (L882) -- new command; chapter-scoped (--chapters) and volume-scoped (--volumes);
    merge-not-overwrite for chapter-scoped runs via _merge_by_chapter.
    wiki gazetteer --merge-epithets (L673) -- new flag; calls _merge_epithets_into_gazetteer
    (L808), which is a local-only, no-LLM operation.
    wiki step (L1912-1913) -- now calls scenes + gazetteer --merge-epithets between ingest and
    extract. Order: ingest -> scenes -> gazetteer --merge-epithets -> extract -> graph build ->
    synthesize -> site build.
    wiki run-all (L1999-2002) -- same order for the full-volume unattended path.

src/narrativewiki/audit/reports.py
    register(“scenes”, “wiki scenes”) -- paragraph-coverage check (core_para_ids must partition
    the chapter) + verbatim-quote check (same discipline as the claims report) + mined-epithet
    table (top 30, for review before --merge-epithets).

config/extraction.yaml
    New extraction.scene: block:
      span_target_tokens: 4000
      span_overlap_tokens: 500
      max_tokens_per_request: 6000
      min_epithet_confidence: 0.6

config/models.yaml
    New routing entry: scene_extract -> local_fast, fallback: groq_fast
    (same escape-hatch pattern as claim_extract)
\
---

## The invocation order (and why it changed)

**Before Phase 18:**
ingest -> gazetteer -> extract -> graph build -> synthesize -> site build

**After Phase 18:**
ingest -> gazetteer -> scenes -> gazetteer --merge-epithets -> extract -> graph build -> synthesize -> site build

The scenes pass comes BEFORE extract because its primary value for the claim-extraction pass
is the epithet merge: once “the wisewolf” is a gazetteer surface form, the automaton finds it,
mentions.jsonl indexes it, and wiki extract receives extraction windows for chapters that
previously had zero. The scene records themselves (beat summaries, state changes, quotes) are
data-layer only at this phase -- they are written to data/02b_scenes/ and auditable, but no
downstream stage reads them yet. That consumption is Phase 19's job.

wiki gazetteer --merge-epithets is deliberately separate from wiki gazetteer (the full
mining+classification+clustering pipeline). It is: (1) local and free -- no LLM call, just a
surface-form write and automaton rebuild; (2) idempotent -- re-running it over the same epithet
file produces the same gazetteer; (3) narrowly scoped -- it only touches the surface_forms for
entities the epithet records mention, not the full entity list.

---

## Data contracts

See docs/CONTRACTS.md section 3b (scene records) and section 3b.1 (epithet records). Key points:

- core_para_ids across all a chapter's SceneRecords partitions every paragraph in that chapter
  exactly once. wiki audit scenes verifies this. A violation means spans.py regressed.
- beat_summary is the ONE field not verbatim-quote-gated. Everything else -- participants,
  location, quotes, state_changes, epithets -- requires a real para_id and verbatim quote.
- state_changes always carry a note (free text) even when predicate is null. The note is
  the raw material Phase 19's event layer will consume.
- Epithet records below min_epithet_confidence stay on disk for audit but are excluded by
  --merge-epithets.

---

## What the tests cover

New test files / suites (full suite was 336 tests before Phase 18; new total ~388):

\tests/test_scenes.py
    build_chapter_spans: basic span construction, single-para chapter, overlap capping, hard-break
    spanning; extract_chapter_scenes: entity resolution, quote/epithet validation, drop counting,
    cross-span dedup; extract_volume_scenes: progress callback, chapter aggregation.

tests/test_entities.py (additions)
    alias.add_surface_form: new form added, duplicate not added, first_vol respected.
    gazetteer.merge_epithets: below-threshold excluded, already-present not duplicated,
    unknown entity_id skipped.

tests/test_cli_chapters.py (additions)
    wiki scenes basic invocation; --chapters flag; merge-not-overwrite behavior;
    --force re-runs only the requested chapter.
    wiki gazetteer --merge-epithets: succeeds with existing scenes output; errors cleanly when
    no gazetteer or no epithets file.

tests/test_paths.py (additions)
    scenes_volume / scene_epithets: correct paths; set_active_series re-segments them.

tests/test_audit_reports.py (additions)
    _scenes_report: OK path (coverage complete + quotes verbatim); FAIL on coverage gap; FAIL on
    bad quote; epithet table printed; StageNotReady when no scene files.

tests/test_step.py (additions)
    wiki step now calls scenes + merge-epithets before extract; verified by checking call order
    via mock.

tests/test_run_all_guard.py (additions)
    wiki run-all includes scenes and merge-epithets in the correct positions.
\
---

## Known gaps (deliberately left)

1. **No live run yet.** Phase 18 is code-complete and unit-tested but has NOT been run against
   real corpus data. wiki scenes --volumes 1-2 --series spice-and-wolf is the next verification
   step. The _GENERATION_OPTIONS (num_predict: 6144, repeat_penalty: 1.3) are starting values
   that will almost certainly need tuning after seeing real Ollama output -- see PHASE_3.md's
   section on tuning methodology.

2. **Token cost unvalidated.** docs/vision/PHASE_17.md's Phase 18 bullet estimated ~1.6M input
   tokens for 13 volumes. This is unverified; run wiki budget after a real scenes pass to measure it.

3. **Scene records are not yet consumed downstream.** data/02b_scenes/ is written and
   auditable but graph build / synthesize / site build do not read it. That is Phase 19's
   scope (the event layer). This is not a gap in Phase 18's own contract -- the phase goal was
   100% paragraph coverage and epithet mining, both delivered.

4. **wiki step's audit loop does not include scenes.** The end-of-step audit currently runs
   claims and contradictions only. Adding scenes to that loop is trivial but deferred until
   after a live run confirms the scenes output is stable enough to always-audit.

5. **_GENERATION_OPTIONS is untuned against real data.** See gap 1. Specifically: num_predict:
   6144 may be too tight for a dense chapter with many state changes and quotes, or too generous
   for a short interlude. repeat_penalty: 1.3 is inherited from claim_extract's tuned value;
   the scene schema's wider response shape may need a different setting.

---

## What Phase 19 needs to know

Phase 19 adds the event layer: a narrative node anchored to (vol, chapter_idx, para span) with
participants and roles; new claim kinds event, state_change (X->Y at event E), quote
(speaker, addressee, para_id). The Phase 18 scene records are the direct input:

- beat_summary -> event node summary
- state_changes (with note + optional predicate) -> state_change claims
- quotes -> quote claims
- participants -> event participant roles

The key design constraint Phase 19 must respect: claims.py's mention-major pass remains
unchanged, and the event layer is a THIRD tier (scene records -> event nodes -> graph), not a
replacement for either of the first two. docs/vision/PHASE_17.md's Phase 19 bullet is the
source of truth for what that layer looks like.

To reproduce this phase's deliverable (after a live corpus run):

\wiki scenes --volumes 1-2 --series spice-and-wolf
wiki audit scenes --series spice-and-wolf
wiki gazetteer --volumes 1-2 --series spice-and-wolf --merge-epithets
wiki extract --volumes 1-2 --series spice-and-wolf --force
wiki graph build --series spice-and-wolf
wiki audit contradictions --series spice-and-wolf
wiki synthesize --upto 2 --series spice-and-wolf --polish --force
wiki site build --series spice-and-wolf --upto 2 --force
wiki audit links --series spice-and-wolf
\