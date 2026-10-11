# TASK-0003: A deterministic, zero-LLM Leak@t artifact probe (`probe run leak`)

```
Status:   DONE (revised 2026-09-14 night -- see Sec7; Sec1-Sec6 and the Report below are
          untouched, original record of the first attempt)
Author:   claude
Assigned: codex
Created:  2026-09-14
```

**Scope reminder, binding for this task and every acceptance-criteria command in it: Spice and
Wolf, `--volumes 1-2`, only.** The maintainer stopped TASK-0002's 86 run tonight and was explicit:
*"only use 2 volumes... stick with spice and wolf... in the future when full pipeline and
evaluation and benchmark is done, we will work on full series."* Do not run any command in this
task against any other series or a wider volume range, even if it would produce a more interesting
number. `docs/vision/PHASE_24.md`'s 2026-09-14 (night) entry has the full incident.

## 1. Why this task exists

`docs/vision/plans/0008-pre-full-scale-audit.md` §2.1 item A1 names the gap directly: this project's
Leak@t is currently measured **on the artifact** — `tests/test_spoiler_leak.py` and
`scripts/probe/reanalysis_first_occurrence.py` check structural/index properties, not "would a reader
actually encounter this specific withheld fact's value in what gets rendered." The plan's
recommendation is to build this on top of `probe/futureset.py::future_claims_at(conn, t)`
(`src/narrativewiki/probe/futureset.py`), which already returns — with zero annotation, zero LLM
calls — every claim with `first_vol > t`: exactly the set of facts a cutoff-`t` reader must not be
able to find. That function has had zero callers since it was written (`docs/vision/plans/0008-pre-full-scale-audit.md`
§3.3 B5); this task is its first real consumer.

This task builds the **deterministic half only**: for each future fact, does its value/object
appear verbatim in the actual rendered cutoff-`t` artifact (the page files `wiki synthesize`
writes)? This is a real, citable, zero-cost number — not the fuller adversarial "ask an LLM
questions about the cutoff-t artifact and judge the answers" harness the plan also describes
(A1/A2's TT-style eval). That fuller version is explicitly **out of scope** here (see §3) — it
needs a judge-model decision and real LLM spend, which is not this task's call to make.

## 2. Scope — exactly what to build

**A. `src/narrativewiki/probe/channels/leak.py`** (new file, same directory as `channels/index.py`
— read that file first for the docstring/style pattern to match, and `docs/CONTRACTS.md` §5 for
the exact page-JSON shape you're reading)

- `measure_future_fact_leak(series_id: str, upto_vol: int) -> dict[str, Any]`
  - Connect via `graph.store.connect()` (default `graph_db()` path — no `db_path` override needed,
    `paths.set_active_series`/the caller already points `paths.graph_db()` at the right series).
  - `future_claims = probe.futureset.future_claims_at(conn, upto_vol)`. If `graph.db` does not
    exist, let the resulting `sqlite3` error propagate (same "let FileNotFoundError/equivalent
    propagate, the caller decides what to do with it" contract `measure_candidate_mining` already
    follows — see `probe/channels/index.py`).
  - For each future claim, the "leaked value" to search for is:
    - attribute/trait kind (`claim["value"]` is not null): the literal `value` string.
    - relation kind (`claim["object"]` is not null): the OBJECT entity's `canonical` name — look
      it up from the `entities` table (`SELECT canonical FROM entities WHERE entity_id = ?`).
      Skip (do not count in the denominator) a claim whose object entity_id has no `entities` row
      — should not happen in practice, but do not crash if it does.
  - Build one big search corpus: for every `data/<series>/05_pages/*/v*.json` file with a cutoff
    `<= upto_vol` (use `synth.cache.previous_page` semantics — the file exactly AT `upto_vol` if
    `paths.page_json(entity_id, upto_vol)` exists, else the nearest cutoff below it via
    `synth.cache.previous_page(entity_id, upto_vol)` — read that function before reimplementing
    it, it already does the "walk downward to the nearest real file" logic you need for the
    fallback half), concatenate these fields into one search string per character (skip a
    character with no page file at or below this cutoff — nothing to search):
    - `page.get("lead")`
    - every `page["prose"][key]["text"]`
    - every scalar `fields` entry's `["value"]` (the `age`/`status`/`rank`/`origin`/`occupation`/
      `gender`-shaped single-valued ones) — CONTRACTS §5's example
    - every list-valued `fields` entry's items' `["value"]` (`title`/`nickname`/`appearance`-shaped)
    - `fields["relationships"][]["blurb"]`
    - `fields["affiliations"][]["role"]`
  - `leaked_count` = number of future claims whose search string is found as an exact (case-
    sensitive) substring anywhere in the concatenated corpus. Case-sensitive, matching this
    project's existing verbatim-search convention (`scripts/probe/reanalysis_first_occurrence.py`'s
    Tier A) — do not add fuzzy/case-insensitive matching, that is Tier B territory this task does
    not need.
  - Return a dict shaped like `channels/index.py`'s probe rows (read one of those functions'
    return statements for the exact convention) with these keys: `channel: "L_query"`,
    `probe: "future_fact_leak"`, `series`, `upto_vol`, `future_claims_total` (the denominator —
    count of future claims that had a searchable value/object, per the skip rule above),
    `leaked_count`, `future_fact_leak_rate` (`leaked_count / future_claims_total`, or `0.0` when
    the denominator is `0` — do not raise a `ZeroDivisionError`; `upto_vol == max volume` on a
    2-volume corpus has no future claims at all, and that is an expected, valid input, not an
    error).

**B. `src/narrativewiki/probe/report.py`**
- Add `run_leak_channel(series_id: str, cutoffs: list[int]) -> list[dict[str, Any]]`, mirroring
  `run_index_channel`'s shape exactly: one call to `channels.leak.measure_future_fact_leak` per
  cutoff, catching the same class of "input not ready yet" error `measure_candidate_mining` can
  raise (read what `graph.store.connect()`/`future_claims_at` actually raise when `graph.db` is
  missing — probably nothing, since `connect()` CREATES the file if absent per its own docstring;
  in that case check `paths.graph_db().is_file()` yourself BEFORE calling `connect()` and produce
  an error row shaped like `run_index_channel`'s missing-file rows if it's absent, rather than
  silently creating an empty database file as a side effect of measuring).

**C. `src/narrativewiki/cli.py::probe_run`**
- Extend the `channel` argument's accepted values from `{"index"}` to `{"index", "leak"}`. Update
  the command's docstring to describe `leak` (`L_query`): one line, matching `index`'s existing
  style. When `channel == "leak"`, call `probe_report.run_leak_channel(settings.series_id,
  cutoffs)` instead of `run_index_channel`, and adjust the per-row console print block (currently
  branches on `row["probe"] == "candidate_mining"` / `"vocabulary_exposure"`) to also handle
  `row["probe"] == "future_fact_leak"` — print `t=<t>  future_fact_leak  rate=<rate:.3f>
  (<leaked_count>/<future_claims_total> future facts findable in the cutoff artifact)`, same
  register as the other two branches. Everything else in `probe_run` (provenance registration,
  canonical `probe_report_path` write, `--json` optional copy) is channel-agnostic already and
  needs no change — verify this by reading the function's current body (you already have it from
  this session's earlier `wiki audit probe` work) rather than assuming.
- `wiki audit probe` (`audit/reports.py::_probe_report`) needs **no changes** — it already
  discovers every `_rate`-suffixed field per probe type generically. Confirm this by inspection,
  do not add anything there; if you find it does need a change, that means something above doesn't
  match the row shape `_probe_report` expects — fix the row shape, not the report.

## 3. Out of scope — what NOT to touch

- Every file in `AGENTS.md` §2's boundary list, always.
- The adversarial LLM-judge harness (A1/A2's "ask questions, score answers" version) — this task
  is the static/artifact-side half only. No LLM call anywhere in this task's new code.
- `eval/gold.py`, `eval/leak.py` (a differently-named module the plan document also mentions as a
  *possible* future slot) — this task deliberately uses `probe/channels/leak.py` instead, to reuse
  the provenance/report machinery already built for the `index` channel this session. Do not create
  a second, parallel module under `eval/`.
- Do not run anything against the `86` series, and do not run `--volumes` wider than `1-2` against
  `spice-and-wolf` — see the scope reminder at the top of this file.
- Do not implement fuzzy/normalized matching (Tier B from `reanalysis_first_occurrence.py`) — exact
  substring only, for this first version.

## 4. Acceptance criteria

```bash
pytest -q
# must stay green; report the before/after collected count.

wiki probe run leak --series spice-and-wolf --volumes 1-2
# must complete, print one line per cutoff, and write the canonical
# data/spice-and-wolf/_runs/<run_id>/probe/index.jsonl (same path helper as the index channel --
# probe_report_path is keyed by run_id, not channel name).

wiki audit probe --series spice-and-wolf
# must now show a "probe: future_fact_leak" table alongside candidate_mining/vocabulary_exposure,
# with no code changes to audit/reports.py.
```

- [ ] `pytest -q` green, before/after count reported.
- [ ] At least 3 new tests for `measure_future_fact_leak` in a new or existing
      `tests/test_probe_*.py` (the existing `sandbox` fixture pattern in `tests/test_probe_index.py`
      is the right one to reuse — read it before writing a different fixture from scratch):
      one where a future claim's value IS found in the cutoff artifact (a deliberately-planted
      leak, proving the detector actually detects something), one where it is NOT found (the
      normal, expected case), and one for the zero-future-claims-at-this-cutoff case (rate = 0.0,
      no division error).
- [ ] `wiki probe run leak --series spice-and-wolf --volumes 1-2` run for real; paste its console
      output into the Report.
- [ ] `wiki audit probe --series spice-and-wolf` run for real after that; paste its
      `future_fact_leak` table into the Report. State the actual `future_fact_leak_rate` at t=1
      plainly — **do not editorialize about whether it's a good or bad number; that is Claude's
      call, same rule as every prior task.**
- [ ] Confirm (state explicitly in the Report) that no file under `data/spice-and-wolf/05_pages/`,
      `data/spice-and-wolf/04_graph/`, or `data/spice-and-wolf/03_claims/` changed — this task only
      reads existing pipeline output, it does not regenerate anything.

## 5. Budget and volume scope

- LLM calls: **none.** This task's own code makes zero LLM calls, by design (§1). If anything you
  write ends up calling `llm/client.py`, that's a sign you've misread the scope — stop and ask.
- **Volume scope: Spice and Wolf, `--volumes 1-2`, only** — see the scope reminder at the top of
  this file. `upto_vol=2` (the whole 2-volume corpus) will correctly report `future_claims_total:
  0`, `future_fact_leak_rate: 0.0` — that is an expected, valid, boring result for that cutoff, not
  a bug; the interesting number is at `upto_vol=1`.
- Wall-clock: should be seconds — this reads a handful of already-on-disk JSON files and a SQLite
  database. If it takes more than a minute, something is wrong; do not treat a long runtime here as
  normal the way an LLM-calling task would.

## 6. Report (Codex fills this in — do not pre-fill)

**Status set to:** BLOCKED

**What was built / what blocked it:**

2026-09-14: Stopped before source changes under AGENTS.md §4's conflicting-acceptance-criteria rule. Scope B specifies one `future_fact_leak` measurement row per cutoff from `run_leak_channel`; Scope C routes the leak command to that runner and leaves its canonical output/provenance flow unchanged. However, the acceptance criterion for `wiki audit probe` says its new table must appear "alongside candidate_mining/vocabulary_exposure". Inspection of `audit/reports.py::_probe_report` shows that it reads only `provenance.last_run_for_stage("probe")` and groups only that run's rows. After the specified leak command, that latest run would contain only `future_fact_leak` rows, so the two index tables would not appear alongside it.

Claude clarification needed: if the intended acceptance is that the latest leak run displays only the `future_fact_leak` table, please amend the "alongside" criterion and reopen this task. If all three tables must appear together, specify the intended data/run aggregation and allowed edits. Changing the leak row shape cannot supply the two missing probe types while retaining the specified one-measurement-per-cutoff runner and existing command write flow. No alternate design was implemented.

**Acceptance criteria results:** (paste actual output/numbers, not just pass/fail)

- Baseline full suite: `pytest -q` with process-local Scripts PATH and `PYTEST_ADDOPTS='--basetemp=data/_task0003_pytest_baseline -o addopts='`: **727 passed in 6.07s**, exit 0. An initial sandbox attempt produced setup errors and was interrupted; the approved retry passed. No packages installed.
- No implementation or new tests; the post-change count and new CLI/audit acceptance commands are not applicable yet. No pipeline or LLM command was run.
- Confirmed `_probe_report` already discovers `_rate` fields generically; that part requires no audit edit. The conflict is which runs/rows it reads, not its rate-column formatting.
- Existing Spice and Wolf `05_pages/`, `04_graph/`, and `03_claims/` files were snapshotted by SHA-256 and nanosecond mtime before inspection; the final comparison found no additions, removals, content changes, or mtime changes.

**Anything noticed but out of scope:**

- `graph.store.connect()` applies schema/migrations and creates a missing database. The task's Scope B precheck is necessary to prevent creating a missing database during measurement; no connection was opened in this preflight.
- `graphify-out/graph.json` is absent. Read only the task's named modules/functions and CONTRACTS §5; no graph generation performed.

**Files actually touched:**

- This task file's Status and Report only (tracked).
- Test artifacts in `data/_task0003_pytest_before/`, `data/_task0003_pytest_baseline/`, and pytest cache. No source, contracts, routing, existing pipeline artifacts, or protected planning documents edited. No commit or push.

---

## 7. Revision (2026-09-14, night) — resolving the audit-probe aggregation conflict

Good catch, and the right call to stop rather than guess — the conflict is real and it's a spec bug
in Sec2/Sec4 of the original task, not something ambiguous about `_probe_report`'s existing
behavior. Everything in Sec1-Sec6 above (including the Report) is left exactly as written; this
section is the resolution and, where it conflicts with something above, THIS section wins.

**The actual bug:** `audit/reports.py::_probe_report` (built this session, for the `index` channel
only) reads `provenance.last_run_for_stage("probe")` — the single most recent `probe`-command run
— and shows only that run's rows. `wiki probe run index` and `wiki probe run leak` are two
SEPARATE invocations, each creating its own run with its own `run_id`. After running `leak`, the
"most recent run" is the leak run, which contains only `future_fact_leak` rows. Sec4's "must show a
`future_fact_leak` table alongside candidate_mining/vocabulary_exposure, with no code changes to
audit/reports.py" cannot both be true — Sec2.C's "no changes needed" instruction was written before
a second probe channel existed and didn't anticipate this. **Resolution: `_probe_report` DOES need
a change.** This supersedes Sec2.C's "wiki audit probe (audit/reports.py::_probe_report) needs no
changes" bullet specifically — nothing else in Sec2.C changes.

**The design decision, made here rather than left to guesswork:** `wiki audit probe` should show
the CURRENT state of every probe measurement this series has ever produced, not just whatever the
single most recent invocation happened to touch — the same principle every other `wiki audit
<stage>` report already follows (`wiki audit gazetteer` shows the current `gazetteer.json`
regardless of which run last wrote it; `wiki audit claims` does not care which of several `wiki
extract` invocations produced today's `03_claims/`). A probe report that only ever reflects "the
last command someone happened to type" is a worse design than one that aggregates, now that a
second channel exists — this was always going to need fixing once `leak` (or any second channel)
showed up; TASK-0003 just surfaced it first.

**Exact spec for the fix, replacing Sec2.C's "wiki audit probe needs no changes" bullet:**

In `audit/reports.py::_probe_report`, replace the current `manifest = provenance.last_run_for_stage("probe")`
/ single-run-read logic with an aggregation over every probe run for this series:

1. `runs = [m for m in provenance.list_runs() if m.get("command") == "probe"]` — `list_runs()`
   (`provenance.py`) already returns every run for the CURRENT active series, newest-first; no
   further sorting needed.
2. If `runs` is empty, raise `StageNotReady` exactly as today (same message).
3. Build the aggregated row set by iterating `runs` in the order `list_runs()` already returned
   (newest first) and, for each run, reading its `probe_report_path(run["run_id"])` jsonl (skip a
   run whose file is missing — same tolerance the single-run path already has, don't raise). For
   each row, key it by `(row["probe"], row["upto_vol"])`; keep the FIRST row seen for a given key
   (i.e. from the newest run that produced it) and ignore the same key from any older run — a
   Python `dict` with `setdefault` on that tuple key, populated in newest-to-oldest run order, does
   exactly this with no extra bookkeeping.
4. Everything downstream of "the list of rows" (the `errored`/`by_probe` split, the per-probe
   table rendering with dynamic `_rate` column discovery) is UNCHANGED — it already operates on a
   flat `rows` list; feed it the aggregated list instead of one run's rows.
5. The "Latest probe run: ..." header line changes meaning slightly (it was "the one run this
   report reflects"; now the report can reflect several runs). Print instead: `f"Aggregated from
   {len(runs)} probe run(s), most recent {runs[0]['run_id']!r}, {len(rows)} row(s) after
   dedup."` — state the actual count, don't hand-wave it.

This is a small, mechanical change (no new file, no new CLI surface) — the rest of TASK-0003
(Sec2.A `probe/channels/leak.py`, Sec2.B `run_leak_channel`, Sec2.C's `probe_run` wiring other than
the struck bullet) is unchanged from the original spec above.

**Updated acceptance criteria (replaces Sec4's third command block and its "no code changes to
audit/reports.py" claim only — the rest of Sec4 stands):**

```bash
wiki probe run index --series spice-and-wolf --volumes 1-2
wiki probe run leak --series spice-and-wolf --volumes 1-2
wiki audit probe --series spice-and-wolf
# must now show all three tables together -- candidate_mining, vocabulary_exposure, AND
# future_fact_leak -- aggregated across the two separate runs above, per this section's spec.
```

- [ ] `_probe_report` aggregation implemented exactly as specified above; add at least 2 new tests
      in `tests/test_probe_index.py` (reusing its `sandbox` fixture): one proving two SEPARATE
      probe runs' rows both appear in one `wiki audit probe` invocation (the case that was broken),
      one proving a re-run of the SAME probe/cutoff from a newer run overrides the older run's row
      for that exact key rather than duplicating it.
- [ ] All of Sec4's original checklist items still apply, adjusted only for the three-command
      sequence above in place of the single `wiki probe run leak` + `wiki audit probe` pair.

## 8. Report — revision (Codex fills this in)

**Status set to:** DONE

**What was built:**

Implemented the deterministic `L_query` / `future_fact_leak` measurement in `probe/channels/leak.py`. It uses `future_claims_at`, resolves relation objects to canonical names, skips unresolved objects, selects each character's exact cutoff page or `previous_page` fallback, and searches only the specified text fields with case-sensitive substrings. Missing databases yield error rows without creating a database; the denominator-zero result is 0.0. No LLM calls.

Added `run_leak_channel` and `wiki probe run leak`, retaining canonical JSONL/provenance and optional `--json` output. Updated `_probe_report` according to Sec7: iterate probe runs in `list_runs()` order, skip absent output files, and keep the first row per `(probe, upto_vol)`. Existing rate-column discovery and error handling operate on the aggregated rows.

**Acceptance criteria results:**

- Before: **727 passed in 6.07s** (baseline recorded in Sec6). After: **742 passed in 6.95s**, `pytest -q`, exit 0. Fifteen new collected test cases cover all six specified text-field categories, absent/case-sensitive matches and exclusion of future-only pages/metadata, zero future claims, fallback/exact-page preference, relation resolution and denominator rules, missing-database behavior, CLI provenance/JSON copy, separate-run aggregation, newest-result replacement, and newest-error/missing-file handling. Used process-local PATH and `PYTEST_ADDOPTS='--basetemp=data/_task0003_pytest_final -o addopts='` with approved test execution; no installation. The first implementation test run had one assertion failure from Rich wrapping a table title; the assertion now normalizes whitespace, and the full suite passed afterward.
- `wiki probe run index --series spice-and-wolf --volumes 1-2`, exit 0:

```text
4 row(s) ->
data/spice-and-wolf/_runs/20260914T142100-probe-index-v1-2/probe/index.jsonl
(see wiki audit probe)

t=1  candidate_mining  leak_rate=0.042  (1/24 surface forms would not survive a
cutoff-only mining run)
t=1  vocabulary_exposure  tainted_claim_rate=0.013
future_surface_form_rate=0.465
t=2  candidate_mining  leak_rate=0.000  (0/43 surface forms would not survive a
cutoff-only mining run)
t=2  vocabulary_exposure  tainted_claim_rate=0.000
future_surface_form_rate=0.000
```

- `wiki probe run leak --series spice-and-wolf --volumes 1-2`, exit 0:

```text
2 row(s) ->
data/spice-and-wolf/_runs/20260914T142101-probe-leak-v1-2/probe/index.jsonl
(see wiki audit probe)

t=1  future_fact_leak  rate=0.150 (61/408 future facts findable in the cutoff
artifact)
t=2  future_fact_leak  rate=0.000 (0/0 future facts findable in the cutoff
artifact)
```

- `wiki audit probe --series spice-and-wolf`, exit 0. All three tables appeared together (`candidate_mining`, `future_fact_leak`, `vocabulary_exposure`). Header: `Aggregated from 3 probe run(s), most recent '20260914T142101-probe-leak-v1-2', 6 row(s) after dedup.` This includes an existing earlier probe run as well as the two new runs. The requested table:

```text
   probe: future_fact_leak
┌───┬───────────────────────┐
│ t │ future_fact_leak_rate │
├───┼───────────────────────┤
│ 1 │                 0.150 │
│ 2 │                 0.000 │
└───┴───────────────────────┘
```

The audit ended `OK — every requested cutoff measured cleanly.` HTML copy: `data/spice-and-wolf/_runs/20260914T142101-probe-leak-v1-2/audit/probe.html`.

- Actual JSONL result at t=1: `future_claims_total=408`, `leaked_count=61`, **`future_fact_leak_rate=0.14950980392156862`**. At t=2: total 0, leaked 0, rate 0.0. These are literal value-occurrence measurements; no semantic entailment judgment was performed.
- Confirmed **all 49 files** under `data/spice-and-wolf/05_pages/`, `data/spice-and-wolf/04_graph/`, and `data/spice-and-wolf/03_claims/` retain exactly the baseline SHA-256 and nanosecond mtime. No additions or removals in those trees. No regeneration and no LLM calls.
- `git diff --check` passed. Ran the standing `graphify update .` command: exit 0, AST-only, 3071 nodes / 5832 edges / 183 communities. Parallel extraction was unavailable under sandbox permissions; its automatic sequential fallback completed successfully.

**Anything noticed but out of scope:**

- Aggregation intentionally relies on `provenance.list_runs()` ordering exactly as Sec7 specifies. That existing helper sorts run-directory names descending; it does not independently sort manifest timestamps. No provenance changes made.
- No new task is selected or inferred from these measurement results. Claude decides the next implementation/evaluation task within Spice and Wolf volumes 1–2.

**Files actually touched:**

- `src/narrativewiki/probe/channels/leak.py` (new).
- `src/narrativewiki/probe/report.py`.
- `src/narrativewiki/cli.py` (`probe_run` only).
- `src/narrativewiki/audit/reports.py` (`_probe_report` only).
- `tests/test_probe_index.py`.
- This task file's Status and Sec8 Report only; prior report and Sec7 preserved.
- Generated probe provenance/JSONL and audit HTML under the two run directories above; test temporary artifacts/cache; AST graph artifacts under `graphify-out/` from the standing update command. No protected planning files changed; no commit or push.
