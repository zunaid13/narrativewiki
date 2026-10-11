# Phase 11 — Chapter granularity, `wiki step`, and demoting `run-all`

**Status:** Complete · **Started:** 2026-09-04 · **Finished:** 2026-09-04

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## Why this phase exists

Phase 10 built the run ledger, per-call log, and rollback. It deliberately did NOT build the rest
of the user's rule 3: "strictly iterative, one-chapter-at-a-time processing with a mandatory pause
for manual audit." That's this phase — the plan for it lives in `VISION.md`'s 2026-09-03
"Six-phase redesign" entry and, in full design detail, in
`C:\Users\pc\.claude\plans\glittery-hugging-duckling.md` §"Phase 11".

## What exists now

```
src/narrativewiki/config.py
  _parse_range(spec, available, *, label, not_found_hint)   NEW private helper. Shared body for
    parse_volume_range/parse_chapter_range -- identical grammar ('1-4','2,5','3', None=all),
    identical "raise ConfigError naming the offending item" behavior. parse_volume_range's exact
    historical error text is preserved byte-for-byte (pinned by a new test).
  parse_chapter_range(spec, available) -> list[int]   NEW. label="chapter",
    not_found_hint="in this volume".

src/narrativewiki/paths.py
  step_progress_path() -> Path   NEW: RUNS_DIR / "step_progress.json". Segmented per series
    automatically (RUNS_DIR already is). NOT touched by snapshot_before/restore -- see below.

src/narrativewiki/provenance.py
  load_step_progress() -> dict[str, int] | None    NEW. {"vol": int, "chapter_idx": int} or None.
  save_step_progress(vol, chapter_idx) -> None      NEW. Called only after a step's full chain
    succeeds.

src/narrativewiki/cli.py
  ChaptersOpt   NEW shared Option, next to VolumesOpt: --chapters/-c.
  ingest()      GAINED chapters: ChaptersOpt = None. If given, requires len(wanted volumes)==1.
    Filters freshly parsed records to the requested chapters, merges with whatever's already on
    disk via _merge_by_chapter (see below), sorts by (chapter_idx, seq), and recomputes the
    manifest entry from the FULL merged record set, not just this call's slice. Skip-if-exists is
    now per-chapter. No --chapters: byte-identical to before.
  extract()     GAINED chapters: ChaptersOpt = None. Same shape: filters records AND
    mentions_by_vol[vol] (via new _chapter_of_para_id helper, since mention records carry no
    chapter_idx of their own) to the requested chapters; merges the resulting claims with whatever
    already exists via _merge_by_chapter. Skip/force is keyed off which chapters already have >=1
    claim on disk. No --chapters: byte-identical to before.
  _chapter_of_para_id(para_id) -> int   NEW private helper: 'v03:c02:p0015' -> 2.
  _merge_by_chapter(existing, fresh, touched_chapters) -> list[dict]   NEW private helper, shared
    by ingest and extract: keep every existing record/claim whose chapter_idx is NOT in
    touched_chapters, append fresh. Pulled out specifically so it's unit-testable without a full
    EPUB/Settings/LLM fixture (tests/test_cli_chapters.py).
  StepBlocked(RuntimeError)   NEW exception: step has existing progress but neither --continue
    nor --redo was given.
  _chapter_count(vol) -> int   NEW private helper: how many chapters data/01_parsed/v{NN}.jsonl
    currently has (0 if not ingested). Relies on chapter_idx being contiguous from 0
    (ingest/epub.py assigns chapter_idx=len(chapters) at append time -- verified, not assumed).
  _resolve_step_target(settings, progress, *, do_continue, redo) -> tuple[int,int] | None   NEW,
    pure function (no LLM/network/console) -- see "Resolution algorithm" below. Raises
    StepBlocked; unit-tested directly in tests/test_step.py.
  step()   NEW command. Body: resolve target via _resolve_step_target -> ingest() the whole target
    volume (always, no --chapters -- cheap, and chapter count/boundaries are needed regardless) ->
    extract(chapters=str(chapter_idx), force=redo) -> graph_build() -> synthesize(upto=vol,
    force=redo) -> site_build(upto=vol, force=redo) -> re-read data/03_claims/v{NN}.jsonl for
    claims with this chapter_idx, print each touched character's real local URL
    (http://127.0.0.1:8080/#/character/<entity_id>, confirmed against
    site/templates/app.js's hash router) -> best-effort terminal audit (claims, contradictions,
    each wrapped in try/except so an audit hiccup never blocks the step) ->
    provenance.save_step_progress(vol, chapter_idx) ONLY on success. Any typer.Exit raised by a
    delegated stage command propagates out of step() uncaught (same propagation run_all already
    relied on before this phase), so a failed increment never advances step_progress.json.
  run_all()   GAINED i_accept_unaudited: bool = False (--i-accept-unaudited). Now calls
    _settings()/parse_volume_range() itself at the top (previously it called neither -- every
    sub-command did that on its own) purely to count the resolved volume scope; if more than one
    volume and the flag isn't set, prints guidance pointing at `wiki step` and exits 1 BEFORE any
    of the six delegated calls run.

tests/test_config.py         +7: parse_chapter_range forms/missing/backwards, a byte-exact pin on
  parse_volume_range's historical error message (guards the _parse_range refactor).
tests/test_cli_chapters.py   NEW, 4 tests: _merge_by_chapter (keeps untouched chapters, replaces
  touched ones, works against an empty existing list, touching every chapter), _chapter_of_para_id.
tests/test_step.py           NEW, 9 tests: _chapter_count (zero when uningested, reads max+1),
  _resolve_step_target (bootstrap, no-volumes, bare-repeat-blocked, redo-without-continue,
  continue-within-volume, continue-across-volumes, series-done).
tests/test_run_all_guard.py  NEW, 3 tests: multi-volume refused without the flag (and nothing
  ran), proceeds with the flag, single-volume needs no flag. The six delegated stage commands are
  monkeypatched to no-ops -- this is the first test file in the project that imports and calls
  into cli.py at all (no CliRunner anywhere in this codebase; that's a deliberate Phase 12 item,
  not started here).

docs/CONTRACTS.md
  New §1.4 (chapter-scoped ingestion), §3.4 (chapter-scoped extraction), §7.5
  (step_progress.json's shape and lifecycle).
```

### Resolution algorithm (`_resolve_step_target`)

1. No volumes discovered at all -> `None` (nothing to do).
2. No progress yet -> `(lowest volume, 0)`. Chapter 0 always exists once a volume's spine has been
   walked at all, by construction (`ingest/epub.py` assigns `chapter_idx=len(chapters)` at append
   time, so indices are always contiguous from 0 with no gaps) -- no need to have ingested the
   volume yet to know this.
3. `--redo` -> repeat exactly `progress`, regardless of `--continue`. Works even if the target
   volume's parsed file is missing (it isn't, in practice -- see point 2's guarantee once a step
   has actually completed).
4. Progress exists, neither flag given -> raise `StepBlocked`. This is what makes "pause for
   manual audit" real: advancing always requires a deliberate flag, every time.
5. `--continue` -> read `_chapter_count(progress["vol"])` (requires that volume's
   `data/01_parsed/v{NN}.jsonl` to exist -- guaranteed, since a completed step for that volume
   means `step()` already called `ingest()` for it). If `progress["chapter_idx"] + 1` is still
   within range, advance within the volume; otherwise advance to chapter 0 of the next volume in
   `settings.discover_volumes()` order, or `None` if there is no next volume.

## A real environment finding during verification, not a bug

Verifying this phase live against Spice-and-Wolf (Ollama down in this session) turned out to be a
genuine test of the "a failed step never advances progress" design rather than a smoke test:
`wiki step --series spice-and-wolf --redo` on v01 chapter 1 (which already had real claims,
so `--redo` forced a real re-extraction) hit `Cannot reach Ollama at http://localhost:11434`,
failed cleanly through the existing `LLMError` -> `typer.Exit(code=1)` path inside `extract()`,
and `step_progress.json` was confirmed unchanged (`{"vol": 1, "chapter_idx": 1}`, exactly as
before the failed call) — not corrupted, not advanced. This is exactly the behavior the design
relies on (§4's point 10 in the original plan), demonstrated with a real failure rather than a
simulated one. No code change resulted; recorded here because it's the kind of thing that's easy
to get wrong silently.

## Verify it in one command

```bash
python -m pytest                              # 289 passed
wiki doctor --series spice-and-wolf            # unaffected -- doctor never starts a run or a step
```

## Current real-data state

Spice-and-Wolf volumes 1-2 (the standing testing cap) were exercised live, non-destructively:

```bash
wiki step --series spice-and-wolf              # v01 chapter 0 (the prologue) -- correctly
                                                # reported zero claims for it, not an error
wiki step --series spice-and-wolf              # refused: "pass --continue ... or --redo ..."
wiki step --series spice-and-wolf --continue   # advanced to v01 chapter 1 (28 real claims)
wiki step --series spice-and-wolf --redo       # hit Ollama down, failed cleanly, progress
                                                # unchanged (see above)
wiki run-all --series spice-and-wolf --volumes 1-2 --upto 2                    # refused, exit 1
wiki run-all --series spice-and-wolf --volumes 1-2 --upto 2 --i-accept-unaudited # ok, exit 0,
                                                # all six stages ran, mostly skip-cached since
                                                # v1-2 were already fully processed before this
                                                # phase (Phase 10's own verification run)
```

`data/spice-and-wolf/_runs/step_progress.json` now holds `{"vol": 1, "chapter_idx": 1}` — real,
current step-loop state, harmless to keep or delete. No claims, graph, pages, or bundle content
was destructively changed: every command above either skipped (already extracted/synthesized) or
rebuilt deterministically from what was already on disk (`graph build`).

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| `--chapters` requires `--volumes` to resolve to exactly one volume | Chapters are numbered per-volume; applying one chapter spec across several differently-sized volumes has no sensible meaning | Applying the same chapter range to every selected volume — silently wrong the moment volumes have different chapter counts |
| Merge-not-overwrite (`_merge_by_chapter`) instead of a hard `--force`-required error when a chapter's already done | This is what makes incremental accumulation across repeated `wiki step`/`extract --chapters` calls actually work — the file grows one chapter at a time instead of needing `--force` (which would also blow away every OTHER already-extracted chapter under the old whole-file overwrite) | A hard error requiring `--force` whenever any requested chapter already exists — safer-looking, but `--force` under the OLD (pre-Phase-11) semantics meant "redo the whole volume," which would silently discard every other already-extracted chapter |
| A chapter with zero claims is always re-attempted on a later call (no "attempted but empty" marker) | Idempotent and free (`llm/cache.py` makes the repeat cost nothing); building a separate "attempted" tracker is real complexity for a purely cosmetic inefficiency | A `chapters_attempted` field alongside claims — correct, but the codebase's existing whole-volume flow never needed this concept either, and it would need its own merge/rollback semantics |
| Step-progress lives in its own small file (`step_progress.json`), not inside the run manifest schema | The manifest's `volumes`/`volume_scope` fields are already meaningfully volume-grained (used by the frontier interlock, `wiki runs`); overloading them with a chapter dimension for one command's internal bookkeeping would complicate every OTHER reader of a manifest for no shared benefit | Adding a `chapter_scope` field to every manifest — touches Phase 10's schema and every existing manifest consumer for a concern only `wiki step` has |
| `step_progress.json` is NOT touched by `snapshot_before`/`restore` | Rolling back one run's output and then continuing the step loop from the same position is the correct combination — `wiki rollback` undoes what a run WROTE, not where the step loop IS | Snapshotting it alongside stage dirs — would silently rewind or fast-forward the step loop as a side effect of an unrelated rollback, surprising and undocumented |
| `wiki step` delegates to the five existing stage commands in-process (same pattern `run_all` already used) rather than building its own extract/synthesize/site-build logic | Reuses every existing skip-if-exists, provenance, and error-handling behavior for free; `run_all`'s own propagation of `typer.Exit` on failure already does exactly what "a failed step must not advance progress" needs | A parallel, step-specific implementation of the four stages — real duplication for no behavioral difference |
| `graph build`/`synthesize`/`site build` get no chapter selector | Spoiler safety (`CLAUDE.md` §1) is defined at `first_vol`, i.e. volume granularity, by invariant — there is no "chapter cutoff" concept to add without touching that invariant | Adding a parallel chapter-level cutoff to synth/site — a materially larger, riskier change touching the one invariant this project cannot regress, for a benefit `wiki step`'s existing `--upto <volume>` calls already get safely (see below) |
| No dedicated automated test for "`graph build` reads only the claim files present" | The behavior needed zero code change (confirmed by reading `cli.py::graph_build`'s existing glob before touching anything) and was exercised for real by every `wiki step`/`run-all` verification run above, which always ran with only 2 of 13 volumes' claims on disk | A heavy CliRunner-style integration test standing up a full Settings/gazetteer/LLMClient fixture just to re-confirm an unchanged `Path.glob` call |

## Known gaps, deliberately left for later phases

- **No cross-chapter `claim_id` merge.** `make_claim_id(subject, predicate, object, vol)` has no
  chapter component. A whole-volume `extract` call already merges duplicate claim_ids across
  chapters within that one call (`extract/claims.py::_merge_claim`, combining evidence). Two
  SEPARATE `wiki step`/`extract --chapters` calls (different chapters, same volume) that both
  produce the same claim_id will NOT be merged — both land in the file. Rare in practice (the same
  exact subject/predicate/object asserted independently in two different chapters of one volume),
  and downstream `graph/contradictions.py` already reconciles same-subject/predicate/object claims
  ACROSS volumes; extending that reconciliation to same-volume-different-chapter duplicates was
  judged out of scope here — not fixed, not silently swept under "merge-not-overwrite."
- **No chapter-level HTML audit report.** `wiki step` runs the existing terminal `claims`/
  `contradictions` reports (Phase 4's `audit/reports.py`, unchanged). Self-contained HTML reports
  a non-coder can open from disk, plus `wiki trace`, are Phase 12.
- **`run-all` still has no `--chapters`.** It was never meant to — it's the "unattended, one
  volume at a time" path now; `wiki step` is the chapter-granular one.
- **No `wiki step --status`/`wiki step --reset`.** Inspecting or clearing
  `step_progress.json` today means reading/deleting the file directly (documented in
  `docs/CONTRACTS.md` §7.5). Not asked for; add if it comes up.
- Phase 9's still-open finding (Holo's Appearance field near-duplicates) and Phase 10's
  Vertex-frontier-profile-still-commented-out gap are both untouched — unrelated to this phase.

## What Phase 12 needs

Start at `VISION.md`'s "Six-phase redesign" entry (2026-09-03) for full scope, then:

1. **Self-contained HTML reports** in `_runs/<run_id>/audit/<stage>.html`, following the pattern
   `roster.html` already establishes — `wiki step` already runs the terminal `claims`/
   `contradictions` reports (this phase, §"What exists now" above); Phase 12 is making those (and
   the rest of `audit/reports.py`'s registry) render to a file too, not re-plumbing when they run.
2. **`wiki audit links` exits non-zero on FAIL.** Currently exits 0 regardless
   (`audit/reports.py`, unrelated to anything touched this phase).
3. **`wiki audit run <run_id>`** — one HTML index per run. Natural to also link `step_progress.json`
   and the touched chapter's affected pages (which `step()` already computes and prints — Phase 12
   just needs to persist that list somewhere an HTML report can read it, e.g. onto the run's own
   manifest via `**extra` on `run.finish(...)`, which Phase 10 already supports).
4. **`wiki trace <entity_id>`** — does not exist yet. `wiki calls --grep <name>` (Phase 10) is the
   closest thing today.
5. The first `typer.testing.CliRunner` tests belong here too, if Phase 12's HTML work wants
   end-to-end coverage beyond the monkeypatched-function-call style this phase and Phase 10 both
   used (`tests/test_run_all_guard.py`, `tests/test_step.py`).
