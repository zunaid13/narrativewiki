# Phase 10 — Run ledger, per-call prompt/response log, rollback, frontier interlock

**Status:** Complete · **Started:** 2026-09-03 · **Finished:** 2026-09-03

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## Why this phase exists

The user set four new operating rules for this project, none of which had any supporting
infrastructure before this phase:

1. Frontier-model API calls must be strictly limited to 2 volumes.
2. Every LLM response must be saved with its prompt and a timestamp, so nothing gets re-asked.
3. Processing must be strictly iterative (one volume/chapter at a time), pausing for a manual
   audit, with the ability to roll a run back.
4. Every module's inputs/outputs must be traceable end to end by a non-coder, via `USER_GUIDE.md`.

This is the first of six phases planned against those rules plus a literature pass (STORM/
WikiMAG/WikiAutoGen) and `narrativewiki-pipeline-review.md`. The full six-phase plan is recorded
in `VISION.md`'s 2026-09-03 "Six-phase redesign" entry — read that for the other five phases'
scope (11: chapter granularity + `wiki step`; 12: HTML audit reports + `wiki trace`; 13: planned
page outlines; 14: over-association/neutrality/canonicalization fixes; 15: evaluation harness;
16: routing reset [**partially done already, see below**] + non-coder guide rewrite).

Phase 10 specifically builds rules 1 and 2 in full, and the rollback half of rule 3. Chapter-level
iteration (the rest of rule 3) and human-readable HTML reports (rule 4) are Phase 11 and 12.

## What exists now

```
src/narrativewiki/provenance.py   NEW. The whole run-ledger module.
  RunContext           dataclass: run_id, dir, series_id, command, scope, manifest.
    .log_call(record)              append one line to calls.jsonl. Thread-safe.
    .frontier_call_count()         count of tier=="frontier" calls logged so far.
    .attach_budget(budget)         called by LLMClient.__init__ when constructed with run=this.
    .finish(outcome, **extra)      IDEMPOTENT -- only the first call sets finished_ts. Saves
                                    this run's own budget.json AND accumulates into the
                                    series-scoped cumulative data/<series>/budget.json.
    .snapshot_before(stage_keys)   real COPY (not hardlink -- see below) of each named stage
                                    dir into outputs/<key>/, before the caller writes to it.
    .restore()                     copies outputs/<key>/ back over the live stage dir, for
                                    every key this run snapshotted. Used by `wiki rollback`.
  start_run(series_id, command, *, scope, volumes=None, volume_scope=None, argv=None,
            stage_keys=None) -> RunContext
      Creates data/<series>/_runs/<run_id>/, writes the initial manifest, snapshots stage_keys.
      run_id = "<UTC timestamp>-<command>-<scope-slug>", disambiguated on same-second collision.
  list_runs(limit=None), latest_run_id(), get_run(run_id), read_calls(run_id, stage=, grep=)

src/narrativewiki/paths.py
  RUNS_DIR              NEW module global, data/<series>/_runs, reassigned in
                         set_active_series exactly like DATA_DIR/PARSED_DIR/etc.
  run_dir(run_id)        NEW accessor: RUNS_DIR / run_id.

src/narrativewiki/config.py
  Profile gained: tier: str = "standard", max_volumes: int | None = None,
                  max_calls_per_run: int | None = None. Read from raw.get(...) in _build_profile.

src/narrativewiki/llm/cache.py
  CachedResponse gained stage/provider/model/system/prompt/first_seen_ts fields, all optional
  with empty/None defaults -- an entry written before this change reads back fine, just without
  the extra trace. put()/get() read and write them; make_key()/the cache KEY are unchanged.

src/narrativewiki/llm/client.py
  LLMClient.__init__ gained run: RunContext | None = None, volume_scope: int | None = None.
  If run is given, it calls run.attach_budget(self.budget) once.
  _call() now:
    - logs every hit AND every miss to run.log_call(...) via a new _log_call() helper (no-op if
      run is None -- every pre-Phase-10 direct LLMClient(...) construction is unaffected).
    - on a MISS, if profile.tier == "frontier", calls _enforce_frontier_scope(profile) BEFORE
      _PROVIDERS.get(...) is even touched. Raises FrontierScopeExceeded (subclasses LLMError,
      so every existing `except LLMError` in cli.py already handles it with no new code).
    - a cache HIT is never scope-checked -- it costs nothing and reveals no new spend.
  FrontierScopeExceeded(LLMError)  new exception.

src/narrativewiki/llm/budget.py
  Budget.accumulate(other: Budget)  NEW. Merges another run's ledger into this one (used by
  RunContext.finish() to build the series-wide cumulative total).

src/narrativewiki/cli.py
  import provenance. Five commands (gazetteer/extract/graph_build/synthesize/site_build) now:
    run = provenance.start_run(settings.series_id, "<command>", scope=..., volume_scope=...,
                                stage_keys=[...])
    client = LLMClient(settings, run=run, volume_scope=...)
  and call run.finish("failed", error=str(exc)) at each existing `raise typer.Exit` AFTER client
  construction, and run.finish("ok") at the success path. doctor is UNCHANGED -- it only calls
  client.health()/health_profile(), never _call, so it never starts a run.
  graph_build gained a try/except LLMError around contradictions_mod.build_graph it did not have
  before (in passing, for a consistent finish("failed") hook -- a small pre-existing gap fixed,
  not itself a Phase 10 goal).
  NEW commands: `wiki runs [--limit]`, `wiki calls [--run] [--stage] [--grep] [--limit]`,
  `wiki rollback <run_id> [--yes]`.
  `wiki budget` gained `--run <id>` and now reads data/<series>/budget.json by default (the
  series-scoped cumulative total) instead of the never-written llm/budget.py default path.

config/models.yaml
  vertex_frontier (still commented out, no Vertex key exists yet) gained `tier: frontier` and
  `max_volumes: 2` -- ready to uncomment and route to the instant a real key exists; the
  interlock will then be live with zero further code changes.

tests/test_provenance.py   NEW, 16 tests: manifest shape, collision disambiguation, calls.jsonl +
  frontier_call_count, read_calls filtering, finish() idempotency, snapshot/restore round-trip
  (including the hardlink-corruption regression), rollback scoping (only touches what it
  snapshotted), list/get/latest lookups.
tests/test_llm.py          +17 tests: the frontier interlock (in-scope/beyond-max-volumes/
  at-call-count-limit, both directly on _enforce_frontier_scope and through a full _call()),
  cache-hit-bypasses-interlock, miss-beyond-scope-raises-before-any-provider-contact, run
  attachment, call logging on hit, no-run-means-no-logging, Budget.accumulate.
```

## A real bug found and fixed during this phase

The first version of `provenance._copy_tree` tried `os.link` (hardlink) before falling back to
`shutil.copy2`. **This silently corrupted every snapshot.** Every stage in this codebase writes
its output via `path.open("w")` / `path.write_text(...)`, which truncates the *existing* file in
place rather than writing a new file and renaming over it. A hardlinked "snapshot" shares the live
file's inode — so the very next time the stage wrote to that path, the snapshot was overwritten
too, with nothing left to roll back to.

Caught by `tests/test_provenance.py::test_snapshot_before_and_restore_round_trip` before this ever
ran against real data. Fixed: `_copy_tree` always does a real copy now, with the reasoning
documented at the point of the fix (`provenance.py`) so it doesn't get "optimized" back to a
hardlink later for the plausible-sounding reason that started this bug.

If you add a new stage-writing command in a later phase, and it uses `path.open("w")` /
`.write_text()` (the existing pattern everywhere in this codebase), you do not need to think about
this again — `_copy_tree` is already correct. Only reconsider this if a future stage starts
writing via write-to-temp-then-rename (an atomic-write pattern), which *would* make a hardlink
safe again — but nothing in this codebase does that today.

## Verify it in one command

```bash
python -m pytest                              # 291 passed
wiki doctor --series spice-and-wolf            # unaffected -- doctor never starts a run
```

## Current real-data state

Nothing in `data/86/` or `data/spice-and-wolf/` was regenerated by this phase except one real,
live, non-destructive verification run:

```
wiki graph build --series spice-and-wolf
```

This is a full, deterministic rebuild from claims already on disk (its own docstring: "no --force
here because there is nothing to skip"), so rerunning it is safe by design — it reproduced the
exact same 210 intervals / 60 edges / 19 conflicts (17 extraction_error, 2 narrative_change, 0
flagged) as before this phase. What's new is that it happened *through* the run ledger:

```bash
wiki runs --series spice-and-wolf
# one row: graph_build, scope v1-2, outcome ok, snapshotted: graph

wiki calls --run <that-run-id> --series spice-and-wolf
# 10 real qwen2.5:32b arbitration prompts/responses, each with a timestamp

wiki budget --series spice-and-wolf --run <that-run-id>
# arbitrate: 10 calls, 2,857 in / 431 out tokens, $0 (local)
```

`data/spice-and-wolf/_runs/` now has one real run directory from this verification. It is small
(a graph.db + contradictions.json snapshot) and harmless to keep or delete.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Log every call (hit AND miss) to `calls.jsonl` | A cache hit is the proof a question was already answered — exactly what "search before re-asking" (rule 2) needs to be checkable | Logging only real (uncached) calls — cheaper, but would make `wiki calls` blind to the very repeats it exists to catch |
| Frontier interlock checked only on a cache miss | A hit costs no money and reveals no new spend; blocking it would make a previously-legitimate, already-cached answer unreadable later for no safety benefit | Checking on every call regardless of cache state — simpler code, but punishes cheap/free repeats for no reason |
| `RunContext.finish()` is idempotent (first call wins) | Every existing command body has multiple `raise typer.Exit` points; calling `finish()` at each one (rather than reindenting the whole body under one `try/finally`) needed idempotency to be safe from double-counting the budget | A single try/finally wrapping each entire command body — more "correct"-looking, but a much larger, riskier reindentation of five already-working command functions for the same result |
| Snapshot at the whole-stage-directory granularity (`paths.STAGE_DIRS` keys), not per-file | Every command already writes to exactly one (or two, for site build) stage directories; matching that grain needed no new bookkeeping of "which files did this write" | Tracking exact written files — more precise, but needs instrumenting every writer in `ingest/`, `extract/`, `graph/`, `synth/`, `site/`, none of which currently reports what it wrote |
| Cumulative `wiki budget` total moved to `data/<series>/budget.json`, series-scoped | `llm/budget.py`'s own default (`data/cache/llm/budget.json`) is deliberately shared across every series (it backs the content-addressed LLM cache) — reusing it for cost totals would silently mix two series' spend into one number | Leaving the default as `llm/budget.py`'s own path — simpler, but wrong the moment a second series is in active use, which is already true (Spice and Wolf) |
| `doctor` never starts a run | It only calls `client.health()`/`health_profile()`, which hit providers' health/list endpoints directly, never `LLMClient._call` — there is nothing to log | Wrapping doctor in a run "for consistency" — would create an empty run directory on every single `wiki doctor` invocation, which is run constantly, for no benefit |

## Known gaps, deliberately left for later phases

- **No chapter-level granularity.** `--chapters`, `wiki step`, and the mandatory pause-for-audit
  loop are Phase 11. Everything in Phase 10 works at the existing volume grain.
- **`run-all` does not yet refuse an unaudited multi-volume scope.** Phase 11's plan is
  `--i-accept-unaudited` as an explicit opt-out, making the step-by-step loop the default.
- **No HTML audit reports yet** (Phase 12) — `wiki runs`/`wiki calls` are Rich-terminal output
  only, not yet a self-contained HTML file a non-coder can open from disk.
- **`wiki trace <entity_id>`** (Phase 12) does not exist. `wiki calls --grep <name>` is the
  closest thing today — it searches prompts/responses but does not follow one entity through
  every stage.
- **The Vertex frontier profile is still commented out** in `config/models.yaml` — no key exists
  yet. The `tier: frontier`/`max_volumes: 2` annotation is ready; uncommenting it and adding it to
  `routing:` is all a future session needs to do once the key lands. The interlock is already live
  and tested — nothing else to build.
- **`Budget.accumulate` has no CLI command to reset/inspect just the cumulative file directly** —
  `wiki budget` (no `--run`) is that view; there's no `wiki budget --reset`. Not asked for.
- Phase 9's still-open finding (Holo's Appearance field: ~40 undeduplicated near-duplicate
  fragments) is untouched — that's Phase 14 (value canonicalization), not this phase.

## What Phase 11 needs

Start at `VISION.md`'s "Six-phase redesign" entry (2026-09-03) for full scope, then this section:

1. **`--chapters` selector** on `ingest` and `extract`, same shape as `config.parse_volume_range`
   (`'3'`, `'1-4'`, `'2,5'`). Chapter identity already exists in every paragraph record
   (`chapter_idx`/`chapter_id`/`chapter_title`, `ingest/segment.py:27-30`) — nothing surfaces it
   today. `extract/windows.py`'s windows are already paragraph-index ranges, so filtering by
   chapter is a natural extension there, not a new concept.
2. **`wiki step`** — the new primary command: resolves the next unprocessed `(volume, chapter)`,
   runs `extract → graph build → synthesize → site build → audit` for that increment only, using
   `provenance.start_run`/`stage_keys` exactly as the five existing commands already do (Phase 10
   built the primitives `wiki step` needs — it does not need new provenance machinery, just to
   call `start_run` with `stage_keys=["claims", "graph", "pages", "bundle", "site"]` once per
   step, or chain the five existing per-stage calls' own run creation as-is). Prints the affected
   page's URL and stops. `--continue` advances one increment; `--redo` repeats the last one.
3. **`run-all` demoted**: refuse a multi-volume scope unless `--i-accept-unaudited`.
4. **`graph build`** still has no `--volumes` (by design — full rebuild is cheap and correct);
   Phase 11 just needs its *inputs* scoped to whatever claims files exist, so a `wiki step` that
   has only extracted chapter 1 of volume 1 doesn't require all 13 volumes' claims to be present.

The `FrontierScopeExceeded`/`tier: frontier` interlock from this phase will matter more once
Phase 13's outline-planning stage exists and is routed at a frontier profile — nothing to do now,
just be aware `volume_scope` needs to be threaded into whatever `wiki step` passes to
`LLMClient(...)` the same way the five existing commands already do.
