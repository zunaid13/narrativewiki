# docs/vision/PHASE_11.md — VISION entries for Phase 11 — Chapter granularity / wiki step

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-04 — Phase 11 built: chapter granularity, `wiki step`, and demoting `run-all`

**What:** The rest of the user's rule 3 (see the 2026-09-03 "Six-phase redesign" entry) — strictly
iterative, one-chapter-at-a-time processing with a mandatory pause for manual audit. `--chapters`
(`'1-4'`, `'2,5'`, `'3'`, parsed by a new `config.py::parse_chapter_range` sharing its body with
`parse_volume_range`) on `ingest` and `extract`, requiring `--volumes` to name exactly one volume.
Both commands now **merge, not overwrite**, when writing chapter-scoped output — a new
`cli.py::_merge_by_chapter` keeps every existing paragraph record / claim whose `chapter_idx` is
outside the requested set and replaces only the rest, so a volume's `v{NN}.jsonl` accumulates one
chapter at a time across repeated calls instead of being clobbered. Skip-if-exists became
per-chapter on both commands. New `wiki step` command: resolves the next unprocessed
`(volume, chapter)` from a new small state file (`data/<series>/_runs/step_progress.json`, via new
`provenance.load_step_progress`/`save_step_progress`), runs
`ingest -> extract --chapters -> graph build -> synthesize -> site build` for that one chapter,
prints the affected character page(s)' real, working local URL
(`http://127.0.0.1:8080/#/character/<id>`, confirmed against `site/templates/app.js`'s hash
router), runs the existing terminal `claims`/`contradictions` audit reports, and only then saves
progress. `wiki step` (bare) does the very first chapter; advancing past an already-completed
increment always requires `--continue` or `--redo` explicitly — a bare repeat is refused
(`StepBlocked`) rather than silently no-oping, which is what makes "pause for manual audit" real
instead of a comment. `run-all` is demoted: it now refuses a `--volumes` scope resolving to more
than one volume unless `--i-accept-unaudited` is passed, pointing at `wiki step` as the default.

**Why:** Confirmed by direct code reading (not assumed from the handover doc) that every on-disk
artifact was volume-granular with no chapter concept anywhere, `graph build`/`synthesize`/
`site build` had no `--volumes` at all, and `run_all` called the other five stage commands
in-process with nothing stopping an unattended 13-volume run. `graph build`'s claim-file glob
(`sorted(paths.CLAIMS_DIR.glob("v*.jsonl"))`) already only reads whatever volume files exist, so
Phase 11's "scope graph build's inputs to whatever claims files exist" needed no code change there
— confirmed, not re-implemented.

**Implies:** `graph build`, `synthesize`, `site build` deliberately get NO chapter selector —
spoiler safety (`CLAUDE.md` §1) is defined at `first_vol`, i.e. volume granularity, by invariant;
synthesizing/building the site "at `--upto <volume>`" while only some of that volume's chapters
are extracted is still spoiler-safe (nothing from unextracted chapters or later volumes can leak,
it's just incomplete until the rest is stepped through). A chapter that legitimately produces zero
claims (a short interlude, no character evidence) is indistinguishable on disk from one never
attempted, so it is silently re-attempted by a later `--chapters`/`wiki step` call touching it —
deliberate, and free, since `llm/cache.py` makes the repeat cost no tokens. `claim_id` has no
chapter component (`make_claim_id(subject, predicate, object, vol)`), so the same claim asserted
in two different chapters of one volume processed by two different `wiki step` calls is not
merged the way a single whole-volume `extract` call already merges it via `_merge_claim` — a known,
accepted gap, not fixed in this phase (see `docs/handover/PHASE_11.md`).

**Status:** Done. 289 tests total (16 new: `test_config.py` gained `parse_chapter_range` cases plus
a byte-exact pin on `parse_volume_range`'s historical error text; new `test_cli_chapters.py`
(`_merge_by_chapter`/`_chapter_of_para_id`), `test_step.py` (`_resolve_step_target`/
`_chapter_count`/`StepBlocked`), `test_run_all_guard.py` (the multi-volume refusal, with the six
delegated stage commands monkeypatched to no-ops)). Full suite green. Verified live against real
Spice-and-Wolf data (volumes 1-2 only, the standing testing cap): `wiki step` correctly identified
v01 chapter 0 (the prologue) as having zero real claims and reported that plainly rather than
erroring; `wiki step` bare a second time was refused with the `--continue`/`--redo` message;
`--continue` advanced to chapter 1 correctly; `--redo` against chapter 1 correctly attempted a
real re-extraction, hit Ollama being down in this environment, failed cleanly through the existing
`LLMError` path, and left `step_progress.json` at chapter 1 unchanged — proving a failed step
never advances progress, using a real failure rather than a simulated one; `run-all --volumes 1-2`
was refused without the flag (exit 1) and proceeded correctly with `--i-accept-unaudited` (exit 0,
all six stages ran, mostly skip-cached since v1-2 were already fully processed). Rollback itself
was not re-exercised live since Phase 11 changed nothing in `provenance.py`'s snapshot/restore
path, already covered by Phase 10's 16 passing tests.

