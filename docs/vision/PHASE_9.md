# docs/vision/PHASE_9.md — VISION entries for Phase 9 — Spice and Wolf calibration

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-03 — Per-series data segmentation; Spice and Wolf as a calibration corpus

**What:** Every command now takes `--series`/`-s` (default `86`, unchanged). `paths.py::
set_active_series()` repoints `DATA_DIR`/`DIST_DIR`/`SITE_DIR` and every stage directory at
`data/<id>/` and `dist/<id>/site/` for any series other than the default; the default `86` keeps
the original, unsegmented layout exactly as before, so the real already-built corpus is never
silently orphaned under `data/86/`. `data/cache/llm/` is deliberately NOT segmented — it is
content-addressed (`llm/cache.py::make_key`), so a cached answer is valid regardless of which
series asked. `config/series.spice-and-wolf.yaml` was written — inspected against the real v01/v02
EPUBs first, per CLAUDE.md's own rule, not copied blind from `series.86.yaml` — as the calibration
corpus `narrativewiki-pipeline-review.md` §3/§5.1 recommended: a structurally simple control (two-
person core cast, strictly linear chronology, ordinary prose dialogue, no Para-RAID-equivalent
channel) to separate a genuine pipeline bug from a property specific to 86's text (dual timeline,
heavy pronoun-only POV, nonstandard radio-dialogue markup, aliases as a plot device). `audit/
reports.py`'s ingest report gained `speech.require_para_raid` (opt-in per series, set `true` on
`series.86.yaml`) so the zero-Para-RAID-paragraph check — which correctly protects 86 against a
regressed CSS class — does not misfire on a series that legitimately has no such channel at all.

**Why:** The review's own framing: *86* stacks several hard properties at once, so a bad page
can't be attributed to any one of them without a simpler text to compare against. This also
answers "is 86 a poor calibration corpus" without touching the real corpus's data at all — a
second series's config and output live in a fully separate subtree by construction, not by
discipline.

**Implies:** `USER_GUIDE.md` §6 documents the workflow for adding a series. `CLAUDE.md` §6 now
notes `--series` alongside `--model`. A real calibration run was started against Spice and Wolf
v01-v02 to get actual comparison data: `wiki ingest`, `wiki gazetteer`, and `wiki extract` (v01
only) all completed for real against the live EPUBs and a real Groq/`claim_extract` model — this
is not a dry run. It stopped there (v02 claims, `graph build`, `synthesize`, `site build` not yet
run) when the session that started it ended; nothing failed, it simply has not been resumed yet.
See `docs/handover/PHASE_9.md` for exact state and the command to continue.

**Status:** In progress — infrastructure (`set_active_series`, `--series` CLI wiring,
`require_para_raid`) is Done: 226/226 tests passing (14 new — `tests/test_paths.py`, `tests/
test_audit_reports.py`). The calibration run itself, and the quality comparison against 86 it
exists to produce, is NOT done.

---


## 2026-09-03 — Spice and Wolf calibration run finished; a real `synth/prose.py` prompt bug found and fixed; `MISTRAL_API_KEY` confirmed dead

**What:** Resumed and completed the Spice and Wolf v01-v02 calibration run left at v01-claims-only
by the previous session: `extract` (v02), `graph build`, `synthesize --upto 2`, `site build --upto
2`, `audit links` all ran for real against the live EPUBs. 253/253 tests still pass (`prose.py`'s
fix below is covered by the existing prose-generation tests exercising `ProseText`). Two config/
code changes:

1. `synth/prose.py::_system_prompt` now ends with a literal `Respond with JSON only: {"text":
   "..."}` line, exactly like `site/bundle.py`'s `codex_summary` prompt already does. This is the
   exact latent gap the 2026-09-02 "`codex_summary`'s prompt needed a literal JSON example" entry
   above flagged as "worth watching, not yet worth changing without its own repro" — the repro
   showed up here: `wiki synthesize --model prose=google_fast` failed every character with
   `ProseText... text: Field required`, i.e. `gemini-flash-lite-latest` was shape-guessing the
   response body the same way it did for `codex_summary`, just for a different caller. Fixed the
   same way, immediately verified live (all 14 characters' background/personality generated
   cleanly on the next run).
2. `config/models.yaml routing.claim_extract` gained `fallback: google_fast`, matching
   `codex_summary`/`prose`'s existing fallback — `claim_extract` was the one API-routed stage still
   missing one. See the inline comment for why this does NOT actually auto-recover today's failure
   mode (below) and still needs an explicit `--model` override until `MISTRAL_API_KEY` is either
   unset or renewed.

**Why:** `MISTRAL_API_KEY` — reported "present" by `wiki doctor` (which only checks presence, not
reachability) — is in fact expired: a real `claim_extract` call against it returned a live `401
{"detail":"Your API key expired on 2026-09-02."}`. This confirms 2026-09-02's "prose/codex_summary
had no reachable fallback" entry's own caveat is still true and now bit `claim_extract` too:
`Settings.resolve_role` only substitutes a stage's `fallback` when the primary key is *absent* from
the environment, never when it's present-but-rejected by the provider — so an expired key dead-ends
every routed-to-it stage exactly the way a missing key would NOT. `claim_extract` has no fallback
declared at all (unlike its siblings), so it had no path forward except an explicit `--model`
override; resumed with `wiki extract --series spice-and-wolf --model claim_extract=groq_fast` first.

**Two free-tier rate limits, both hit for real and both structural, not transient:**
- **Groq (`groq_fast`, `qwen/qwen3.8-27b`) has an 8,000 TPM cap on this key's tier.** 20 consecutive
  attempts (65s apart, well past any single retry's backoff) all failed at the same point with the
  same `429 rate_limit_exceeded` — this is not "wait a bit and it clears," the per-character
  extraction prompt is simply too large relative to the cap for more than a couple of characters to
  fit in one rolling minute. Abandoned Groq for this stage; switched to `--model
  claim_extract=google_fast` instead, which completed (partially rate-limited, see below, but not
  structurally blocked).
- **Google AI Studio's free tier (`google_fast`/`google_best`, both models) caps at 15
  requests/minute.** Every stage that fans out one call per character/entity in a tight loop with no
  inter-call pacing (`claim_extract`, `prose`, `codex_summary`) hit this at least once across the
  run (`extract`: 12/14 characters then `429 RESOURCE_EXHAUSTED`; `site build`'s codex-summary step:
  the same, twice). Recovery pattern that worked every time: just retry the same command after the
  API's own `retryDelay` (~50-60s) — `llm/client.py`'s disk cache means a retry only re-attempts the
  items that didn't finish, so each retry is strictly incremental, never a restart from zero.
  `llm/client.py`'s own retry/backoff (`max_retries=3`, `2/4/8s` exponential = 14s total) is too
  short for either failure mode — both need a caller-level retry loop, not a client-level one.

**A real, pipeline-level finding from reading the generated output (the review's actual ask):**
Holo's `v02.md` Appearance field is a wall of ~35 near-duplicate fragments ("wolf ears" / "wolf's
ears" / "wolf ears and a tail" / "lovely ears and tail" / ...) instead of a readable description —
every distinct APPEARANCE claim value is rendered, with no deduplication or canonicalization of
near-identical surface strings. Spice and Wolf has none of 86's five confounding traits (§3 above)
and still produced this, on a character with all of 91 claims (not even the largest volume in the
corpus) — so this is a real pipeline defect, not a property specific to 86's harder text: nothing
downstream of claim extraction canonicalizes or caps near-duplicate values for a single attribute
before rendering. Not fixed here (a dedup/canonicalization pass is real design work — exact-match
dedup would still leave "wolf ears" and "wolf's ears" and "lovely ears and tail" as three separate
bullets — and this session was scoped to finishing the calibration run, not opening a new feature).
Logged as the calibration run's first concrete, actionable finding.

**Implies:** `docs/handover/PHASE_9.md` closes out with the finished run's real numbers and this
finding. Whoever picks up the Appearance-field dedup work should start from `synth/assemble.py`
(where structured fields are assembled from graph rows, CLAUDE.md §2) or `graph/store.py` (where
they're written) — not `synth/prose.py`, which only ever touches `background`/`personality`.

**Status:** Done — calibration run complete end to end (`wiki audit links`: "OK — every reference
resolves"; `wiki audit claims`: "OK — every cited quote appears verbatim"; `wiki audit
contradictions`/`pages`: no hard failures). 253/253 tests passing. The Appearance-field dedup
finding above is open, not yet triaged into a phase.

---


