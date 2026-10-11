# Phase 12 — HTML audit reports, `wiki audit run`, `wiki trace`, FAIL exits non-zero

**Status:** Complete · **Started:** 2026-09-04 · **Finished:** 2026-09-04

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## Why this phase exists

Phase 11 built `wiki step`'s one-chapter-at-a-time loop but left its "what's next" list
unaddressed (`docs/handover/PHASE_11.md`'s final section): self-contained HTML audit reports a
non-coder can open from disk, `wiki audit links` exiting non-zero on FAIL, `wiki audit run
<run_id>` as a per-run index, `wiki trace <entity_id>`, and the project's first
`typer.testing.CliRunner` tests. All five are done here.

## What exists now

```
src/narrativewiki/audit/reports.py
  Every registered report function (`_ingest_report`, `_gazetteer_report`, `_claims_report`,
  `_contradictions_report`, `_pages_report`, `_links_report`) now returns `bool` — True at every
  existing "OK" branch, False at every existing "FAIL" branch (module docstring gained a line
  documenting this). `_REGISTRY`'s value type and `run()`'s return type changed to match; `run()`
  now returns whatever the report function returned. No report's PRINTED text changed at all —
  purely a return-value addition, verified by `tests/test_audit_reports.py`'s two pre-existing
  tests still passing unmodified.

src/narrativewiki/provenance.py
  search_calls_all_runs(needle, *, limit_runs=None) -> list[tuple[run_id, record]]   NEW. The
    cross-run form of `read_calls(..., grep=...)`: walks `list_runs()` and calls `read_calls` on
    each, for `wiki trace` ("every call that ever discussed this entity" is one query instead of
    manually checking each run with `wiki calls --run <id> --grep <name>`).

src/narrativewiki/cli.py
  _audit_report(stage, settings, *, html_path=None) -> bool | None   NEW private helper. Runs one
    `audit/reports.py` stage report through exactly ONE `rich.Console(record=True, width=120)` --
    prints live to the terminal AND records for export in the same call, so the report function
    never runs twice regardless of whether HTML is wanted. When `html_path` is given, saves
    `Console.save_html(html_path, inline_styles=True)` after. Returns the report's OK/FAIL
    verdict. Used by both `audit_cmd` and `step()`.
  _write_run_index(run_id, settings) -> None   NEW private helper. `wiki audit run <run_id>`'s
    body: loads the run's manifest via `provenance.get_run`, lists every `audit/*.html` file
    already present in that run's `audit_dir`, and -- if the manifest carries `touched_pages`
    (only a `wiki step` run sets this) -- lists each affected page with its live
    `http://127.0.0.1:8080/#/character/<id>` URL. Writes `audit_dir/index.html`, inline CSS,
    same `esc()`-everything style `_gazetteer_report`'s `roster.html` already established.
  audit_cmd()   REWRITTEN. Gained a second positional `run_id: Optional[str] = None`. If
    `stage.lower() == "run"`: requires `run_id`, calls `_write_run_index`, returns -- this is
    `wiki audit run <run_id>`, NOT a new subcommand (kept `wiki audit <stage>`'s existing shape
    unchanged on purpose, see decisions table). Otherwise: resolves `html_path` from
    `provenance.latest_run_id()` (None, and HTML is silently skipped, if no run has happened yet
    for this series), calls `_audit_report`, and now `raise typer.Exit(code=1)` when the report
    returned `False` -- the actual fix for "`wiki audit links` exits 0 regardless", generalized to
    every report since the mechanism is identical for all six (see decisions table).
  step()   The delegated ingest/extract/graph_build/synthesize/site_build chain is now wrapped in
    its own `command="step"` `RunContext` (`step_run = provenance.start_run(...)`, no
    `stage_keys` -- see decisions table for why it never snapshots). A `typer.Exit` from any
    delegated stage is caught, `step_run.finish("failed", error=...)` is called, then the
    exception is RE-RAISED (same propagation Phase 11 already relied on for `step_progress.json`
    never advancing on failure -- unchanged). On success, the `claims`/`contradictions` audit
    calls now go through `_audit_report(..., html_path=step_run.audit_dir / f"{stage}.html")`
    instead of a bare `reports.run(stage, settings, console)`; `step_run.finish("ok",
    touched_pages=sorted(touched), vol=vol, chapter_idx=chapter_idx)` is called right before
    `provenance.save_step_progress`, and the final message now points at
    `wiki audit run <step_run.run_id>`.
  trace()   NEW command, `@app.command()`. Resolves the entity via the existing `_find_character`
    helper, then prints (all read-only, no LLM calls): every raw claim across every
    `data/03_claims/v*.jsonl` file where the entity is subject OR object, regardless of spoiler
    cutoff (deliberately NOT going through `graph/temporal.py`'s cutoff-filtered `state_at`/
    `history_at` -- see decisions table); which `data/05_pages/<entity_id>/v*.json` files exist;
    the live site URL from `links.json` if built; and, via the new
    `provenance.search_calls_all_runs`, every LLM call in every run that mentions the entity's
    canonical name, grouped by run id.

tests/test_audit_html.py   NEW, 11 tests: `_links_report` returns True/False correctly (2),
  `cli._audit_report` writes a real self-contained HTML file and returns the verdict with/without
  an `html_path` (2), `wiki audit <stage>` raises `typer.Exit(1)` on FAIL / does not raise on OK
  (2), `cli._write_run_index` produces the expected index content (1), `wiki audit run` rejects a
  missing/unknown run id (2), and two `typer.testing.CliRunner` tests against the real `cli.app`
  (`wiki audit run` with no id, `wiki audit <unknown-stage>`) -- the first CliRunner tests in this
  project, per Phase 11's "what Phase 12 needs" #5.
tests/test_step.py         +5 tests (appended to the existing Phase 11 file): `step()`'s own run
  is created and finished "ok" with the right `touched_pages`/`vol`/`chapter_idx` extras and
  `scope` on success; it never sets `snapshotted_stages`; on a delegated stage's `typer.Exit` the
  run finishes "failed" and `step_progress.json` is NOT written. `_FakeSettings` gained
  `series_id`/`extraction`/`schema_overrides`/`schema_only`/`schema_skip` so
  `provenance.start_run`'s config-hash step (which needs a real or fake `Settings`, never a bare
  dict) has what it needs without hitting a real `config/series.<id>.yaml` on disk.
tests/test_trace.py        NEW, 3 tests: a full trace (claim, page file, live URL, cross-run
  call) round-trips through printed output; resolving by alias works (reuses `_find_character`,
  untested for `trace` specifically before this); an entity with nothing recorded yet prints the
  three "not found" messages instead of raising.

docs/CONTRACTS.md   New §7.6: the `bool` return contract on every report function, the
  `audit/<stage>.html` / `audit/index.html` file shapes, `wiki step`'s own run (why it never
  snapshots), and `wiki trace`'s relationship to `wiki explain`.
USER_GUIDE.md        §3's table gained `wiki audit run <run_id>` and `wiki trace`, and now notes
  that `wiki audit <stage>` also saves HTML and exits non-zero on FAIL; §2's `wiki step` section
  now mentions the HTML output.
CLAUDE.md            §6's CLI surface line updated to list every command that exists today
  (`trace`, `audit run`, `runs`, `calls`, `rollback`, `budget` were all missing from that line
  already, predating this phase -- fixed here since it was one line to correct while touching it).
```

## A real environment finding during verification, not a bug

Verified live against Spice-and-Wolf (the standing volumes 1-2 testing cap), non-destructively,
with Ollama down in this session (same as Phase 11's own verification):

- `wiki audit links --series spice-and-wolf` printed `OK` and wrote
  `data/spice-and-wolf/_runs/20260904T124919-site_build-upto2/audit/links.html` (attached to the
  most recent run, `site_build`, since nothing forces `wiki audit <stage>` to a specific run).
- `wiki audit run 20260904T124919-site_build-upto2 --series spice-and-wolf` wrote `audit/
  index.html` linking `links.html` and showing the run's manifest fields correctly.
- `wiki trace Lawrence --series spice-and-wolf` printed 29 raw claims with real evidence quotes,
  both page files, the live URL, and 29 LLM calls across 14 different runs going back to the
  first `wiki extract` this series ever ran — genuinely exercising the cross-run search, not just
  the latest run.
- `wiki step --series spice-and-wolf --redo` hit the same `Cannot reach Ollama` failure Phase 11
  hit, and this time the NEW step-level run is visible in `wiki runs` as
  `step v01c1 failed` (alongside the inner `extract v1-1 failed` run it wraps), with
  `manifest.json`'s `error` field reading `"a delegated stage exited with code 1"` —
  `step_progress.json` stayed at `{"vol": 1, "chapter_idx": 1}`, unchanged, exactly as before.
  Confirms the new run-wrapping does not interfere with Phase 11's "a failed step never advances
  progress" guarantee, and additionally makes the failure itself visible in `wiki runs` where
  before this phase it was not (the only place it showed up was the terminal at the time).

## Verify it in one command

```bash
python -m pytest            # 306 passed (289 before this phase + 17 new)
```

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| `wiki audit run <run_id>` reuses the existing flat `wiki audit <stage>` command (stage="run" plus a second positional `run_id`) rather than a new Typer sub-app | `CLAUDE.md` §6 documents `audit <stage>` as a stable CLI shape; Typer requires every sub-app command to be explicitly named (no positional dispatch with 2+ commands), so a sub-app would have forced `wiki audit report <stage>` or similar, breaking every existing doc/muscle-memory reference to `wiki audit <stage>` | A `graph_app`/`site_app`-style Typer sub-app for `audit` |
| `_audit_report` builds ONE `Console(record=True)` and passes it to `reports.run` instead of calling the report function once for the terminal and once (recording) for HTML | `rich.Console(record=True)` prints live to `sys.stdout` AND records for later export from the SAME call — confirmed empirically before writing any code. Calling twice would double every side effect a report has (`_gazetteer_report` re-writing `roster.html`, wasted LLM-free but real disk I/O) for identical output | Two separate console objects / two calls to `reports.run` |
| `wiki audit <stage>` always targets `provenance.latest_run_id()`, no `--run` option | Keeps the common case (`wiki audit claims` right after `wiki extract`) a single unadorned command; the run that JUST finished is almost always the one you want the HTML attached to. A user who wants a specific older run's HTML can re-run the stage command to make it latest again, or read `wiki runs` and know which run's `audit/` dir corresponds to which invocation | A `--run <id>` option on `wiki audit <stage>` — real but not asked for, and the common path already works without it |
| Every report's FAIL now exits `wiki audit <stage>` non-zero, not just `links` | The handover only named `links` explicitly, but all six reports already had the identical FAIL/OK branch shape, and `_audit_report`'s check is one `if ok is False` regardless of which stage — leaving the other five at "prints FAIL, exits 0" would have been an inconsistent, arbitrary carve-out for no stated reason | Scoping the fix to `links` only, per the letter of the original ask |
| `wiki step`'s own run passes NO `stage_keys` to `provenance.start_run`, so `snapshotted_stages` stays absent and `wiki rollback <step run id>` has nothing to restore | `step()` itself never writes to a stage directory directly — every delegated command (`ingest`/`extract`/`graph_build`/`synthesize`/`site_build`) already snapshots its OWN stage dir before writing. A step-level snapshot would be a redundant second copy of the exact same pre-run state, and `wiki rollback` on the step run would restore nothing new since the delegated runs' own snapshots are the real rollback points | Also snapshotting at the step level "for completeness" — real disk cost, zero behavioral benefit |
| `wiki trace` reads RAW claims directly from `data/03_claims/v*.jsonl` (every claim regardless of `first_vol` cutoff), not through `graph/temporal.py`'s `state_at`/`history_at` | `wiki explain <name> --upto N` already exists and does exactly the assembled, cutoff-filtered view — duplicating that here would make `trace` redundant with it. `trace`'s stated job (`docs/handover/PHASE_11.md`'s Phase 12 item 4, "does not exist yet... traceable end to end by a non-coder") is provenance: the full raw history AND the run/call chain that produced each piece, which is specifically the thing `explain` cannot show (it never touches `_runs/`) | Reimplementing `explain`'s cutoff-filtered view a second time under a new command name |
| `provenance.search_calls_all_runs` is a thin loop over `list_runs()` + the existing `read_calls(..., grep=...)`, not a new index/cache | `calls.jsonl` files are small (this project's testing cap is 1-2 volumes; `CLAUDE.md` §0) and `wiki trace` is an occasional inspection command, not a hot path — a per-run linear scan costs nothing worth optimizing for | A merged/indexed cross-run call log maintained incrementally |

## Known gaps, deliberately left for later phases

- **`wiki audit <stage>`'s HTML always targets the LATEST run for the series, even if that run's
  command has nothing to do with the stage being audited** (e.g. running `wiki audit links` right
  after an unrelated `wiki gazetteer` call attaches `links.html` to the gazetteer run). Harmless
  (the HTML is still correct; it's just filed under a run whose command name doesn't match the
  stage), and the common case (`wiki audit <stage>` right after the command that produces that
  stage's input) always gets the intuitively-right run. Not fixed — would need a `--run` option
  (rejected above) or per-stage "most relevant run" heuristics that are more complexity than the
  problem has warranted so far.
- **No HTML export for `wiki explain`/`wiki trace` themselves** — both remain terminal-only, like
  `wiki calls`. Only `audit/reports.py`'s six registered reports get the HTML treatment, since
  those are the ones the original ask (`docs/handover/PHASE_11.md`) named.
- **`wiki trace`'s cross-run call search is a substring match on the canonical name only** — it
  does not also search for the entity's aliases or `entity_id`. A call that referred to a
  character only by an alias/nickname (not yet resolved to canonical at prompt-construction time)
  would be missed. Not observed in practice against Spice-and-Wolf (prompts consistently use the
  canonical name), and adding multi-term OR search is a small, well-scoped follow-up if it comes
  up on `86`'s larger cast.
- Phase 9's still-open finding (Holo's Appearance field near-duplicates), Phase 10's
  Vertex-frontier-profile-still-commented-out gap, and Phase 11's cross-chapter `claim_id` merge
  gap are all untouched — unrelated to this phase.

## What Phase 13 needs

Start at `VISION.md`'s 2026-09-03 "Six-phase redesign" entry for full scope: Phase 13 is the
planned page outline (closed section vocabulary, replacing the two hand-synced hardcoded
templates in `synth/assemble.py`/`site/okf.py`/`site/templates/app.js`) — a real, large refactor
of everything downstream of `synth/assemble.py`'s hardcoded field table. Nothing built in Phase 12
blocks it; `wiki trace`/`wiki audit run` are inspection tools that will keep working unchanged
once page assembly becomes outline-driven, since neither reads `synth/assemble.py`'s output shape
directly (they read raw claims, page FILES as opaque JSON, and the run ledger).
