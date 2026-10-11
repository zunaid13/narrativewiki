# Phase 19 Handover — The Event Layer

**Status:** Code-complete, unit-tested (397 tests, up from 367).
**Branch/commit:** All changes on the main working tree.

---

## What Phase 19 added

Phase 18 wrote scene records to `data/02b_scenes/` but nothing downstream consumed them.
Phase 19 adds the **event layer**: a third tier that promotes Phase 18 raw scene records into
first-class graph citizens — event nodes with participant roles, `state_change` claims (X→Y at
event E), and `quote` claims (speaker, addressee, para_id) — and wires them into synthesis so
character pages gain a **Chronology** prose section.

**The three-tier constraint is preserved:** `claims.py`'s mention-major pass is completely
untouched. The event layer is additive only — new tables in a separate database, no modifications
to `graph.db` or any existing pipeline step.

---

## New files

### `src/narrativewiki/graph/events.py`
SQLite schema + read/write helpers for `data/04b_events/events.db`. Two tables: `events`
(one row per non-empty scene span) and `event_claims` (state_change and quote records).
Sanctioned reads: `events_at`, `character_events_at`, `event_claims_at` — all spoiler-fenced
with `vol_start <= vol` / `vol <= vol`.

### `src/narrativewiki/graph/event_build.py`
Pure deterministic transform: scene records → event rows. No LLM call. `build_events(scene_files,
conn, *, force)` reads every `.jsonl` in `data/02b_scenes/`, filters out empty spans (no
participants, no state_changes, no quotes), and populates `events.db`. Returns
`(n_events, n_event_claims)`.

### `tests/test_events.py`
21 tests covering `make_event_id`, `connect`/`reset`, `write_events`/`events_at` (including
spoiler filter and reading-order invariant), `character_events_at` (spoiler filter, no
false-prefix match), `event_claims_at` (vol filter), `_scene_to_event` (empty → None),
`_scene_to_event_claims`, `build_events` (force reset, missing file skip, empty input).

### `tests/test_synth_events.py`
9 tests covering `generate_chronology` (None when no events, LLM called with beat summaries,
spoiler filter excludes future events, evidence is para_ids not model output) and
`generate_prose` dispatch (events sentinel calls generate_chronology, None without events_conn,
None when no events for character).

---

## Modified files

### `src/narrativewiki/paths.py`
- Added `EVENTS_DIR = DATA_DIR / "04b_events"` (global, reassigned in `set_active_series`,
  added to `STAGE_DIRS`, added to `ensure_dirs()`).
- Added `events_db() -> Path` accessor (`data/04b_events/events.db`).

### `src/narrativewiki/synth/prose.py`
- Added `_chronology_system_prompt()` and `generate_chronology()` — the event-driven prose path.
- Updated `generate_prose()` to accept optional `events_conn` parameter. When a `page_outline`
  section has `source: "events"`, routes to `generate_chronology` instead of the trait path.
  When `events_conn is None`, the section is returned as `None` (no LLM call).

### `config/extraction.yaml`
- Added `chronology` section to `page_outline` (order: 3, between relationships and background):
  ```yaml
  chronology: { order: 3, kind: prose, title: "Chronology",
                traits: [], min_sentences: 3, max_sentences: 8,
                subject: "a narrative arc ...", source: "events" }
  ```
  The `source: "events"` sentinel is the hook `prose.py` checks. Old sections (background,
  personality, appearances) are renumbered by order only — no functional change.

### `src/narrativewiki/audit/reports.py`
- Added `@register("events", "wiki events-build")` → `_events_report()`: counts events and
  event_claims, prints kind distribution table, schema-guards `kind` values, prints top-20
  characters by event count. FAIL if any unknown `kind`; StageNotReady if `events.db` absent.

### `src/narrativewiki/cli.py`
- Added `@app.command("events-build")` → `events_build()` (after `graph_build`, before
  `explain`): reads scene files, calls `event_build.build_events()`, writes `events.db`,
  starts a provenance run with `stage_keys=["events"]`.
- Updated `step()`: calls `events_build(series=series, force=redo)` between `graph_build` and
  `synthesize`.
- Updated `run_all()`: calls `events_build(series=series, force=False)` between `graph_build`
  and `synthesize`.
- Updated `synthesize()`: opens `events.db` if it exists (graceful if absent), passes
  `events_conn` to `generate_prose()`, closes on exit/error.

### `docs/CONTRACTS.md`
- Added §4b (event layer) between §4 and §5: schema, sanctioned reads, relationship to graph.db,
  pipeline order, and the beat_summary exception.

### Updated tests
- `tests/test_paths.py`: added `EVENTS_DIR` assertion and `"events"` key to `STAGE_DIRS` check.
- `tests/test_step.py`: added `"events_build"` to `stub_stage_commands` fixture and expected
  call order.
- `tests/test_run_all_guard.py`: added `"events_build"` to `stub_stages` fixture and both
  expected call order assertions.
- `tests/test_audit_reports.py`: added 3 events report tests.

---

## Invocation order (updated)

```
wiki ingest --volumes N
wiki gazetteer --volumes N
wiki scenes --volumes N
wiki gazetteer --volumes N --merge-epithets
wiki extract --volumes N
wiki graph build
wiki events-build               ← NEW (Phase 19)
wiki synthesize --upto N
wiki site build --upto N
```

`wiki step --continue` and `wiki run-all` already call every step in this order.

---

## Data contracts (quick ref)

- `data/04b_events/events.db` — see CONTRACTS.md §4b.
- `events.event_id`: `"ev_v01c03s002"` (matches `make_event_id(vol, chapter_idx, span_index)`).
- `event_claims.kind`: closed vocabulary — only `"state_change"` and `"quote"`.
- Empty spans (all-empty scene records) → no event row (sparse by design).
- `events_at`/`character_events_at`/`event_claims_at` are the only sanctioned reads.

---

## Known gaps (for Phase 20+)

1. **No live run yet** — `wiki events-build --volumes 1-2 --series spice-and-wolf` is the
   next verification step once scene records have been generated.
2. **Token cost unvalidated** — the Chronology prose prompt is based on beat_summary strings
   (cheap, already paraphrases) but real-data volume is unknown.
3. **`intervals` still do not anchor to `event_id`** — the vision doc (PHASE_17.md §19)
   mentions this as a goal. Currently `event_claims` carry their own `para_id` and `vol`, but
   the main `intervals` table (built from claims.py) has no FK to `events`. A future phase
   could add `event_id` as a nullable column to `intervals` for richer provenance linking.
4. **`wiki step`'s audit loop does not include events** — `wiki step` runs `claims` and
   `contradictions` audit HTML at end-of-chapter. Events audit is not currently included
   (events-build is a full-corpus rebuild, not per-chapter).
5. **Chronology section in `page_outline` uses `order: 3`** — if a per-series overlay needs
   a different position, it can override this key in `config/extraction.<series>.yaml`.

---

## Test count

| Phase | Tests |
|---|---|
| Before Phase 19 | 367 |
| After Phase 19  | 397 (+30) |