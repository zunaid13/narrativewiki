# Phase 9 — Per-series data segmentation; Spice and Wolf calibration corpus

**Status:** Calibration run complete · **Started:** 2026-09-03 · **Run finished:** 2026-09-03

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## Why this phase exists

`narrativewiki-pipeline-review.md` (repo root) flagged that *86—EIGHTY-SIX* is a poor corpus to
debug the pipeline against: it stacks a dual timeline, heavy pronoun-only POV, nonstandard
radio-dialogue markup (Para-RAID), and deliberately obscured aliases, all at once. When a
character page comes out thin or wrong, there is no way to tell which of those five things caused
it. The review's recommendation: recalibrate on a structurally simple light novel first, to
separate genuine pipeline bugs from properties specific to 86's text. Spice and Wolf was picked —
two-person core cast (Lawrence, Holo), strictly linear chronology, ordinary prose dialogue, no
radio-comms channel.

## What exists now

```
src/narrativewiki/paths.py
  set_active_series(series_id)   NEW. Repoints DATA_DIR/DIST_DIR/SITE_DIR + every STAGE_DIRS
    entry at data/<id>/ and dist/<id>/site/ for any series other than the default (86, or
    NARRATIVEWIKI_SERIES). The default series' layout is UNCHANGED (data/01_parsed/, not
    data/86/01_parsed/) -- this was deliberate, so the real already-built 86 corpus is never
    silently orphaned. data/cache/llm/ is NEVER segmented (content-addressed, shared by design).
    Must be called once, early, per process (cli.py::_settings does this) -- every other module
    imports PARSED_DIR/PAGES_DIR/etc. as bare module globals, not a function call, so this is a
    call-once-at-startup pattern, not a per-call parameter threaded everywhere.

src/narrativewiki/cli.py
  SeriesOpt = Annotated[Optional[str], typer.Option("--series", "-s", ...)]
  _settings(series, model=None) now calls paths.set_active_series(settings.series_id) right
    after loading Settings, before anything touches a data/ path.
  --series wired on every command (doctor, status, budget, ingest, gazetteer, extract,
    graph build, explain, synthesize, site build, serve, audit, run-all).

src/narrativewiki/audit/reports.py
  _ingest_report's zero-Para-RAID check now reads `speech.require_para_raid` from the series
  config (default False). Only FAILs the build when the series declares it has a radio/
  telepathic-comms channel (series.86.yaml: require_para_raid: true) and a volume shows zero
  such paragraphs. A series with no such channel at all (Spice and Wolf) reports OK instead of a
  false FAIL.

config/series.86.yaml
  + `speech.require_para_raid: true` -- opts 86 INTO the strict check it always effectively had.

config/series.spice-and-wolf.yaml   NEW. Every value checked against the real v01/v02 EPUBs
  before writing (LuCaZ-produced, not Stick like 86) -- see the file's own inline comments for
  what was verified and how. Source EPUBs: "All novels/Spice and Wolf [Yen Press] [LuCaZ]/"
  (NOT raw/ -- that directory is 86-only; series.spice-and-wolf.yaml's `source.dir` points
  directly at the "All novels/" subfolder instead. If a third series is added, decide then
  whether "All novels/" or a per-series raw/<id>/ layout is the long-term convention -- this
  phase did not need to make that call since only one extra series exists so far).

tests/test_paths.py         NEW, 8 tests: set_active_series segmentation/reset behaviour, the
  default-series-stays-unsegmented rule, STAGE_DIRS consistency.
tests/test_audit_reports.py NEW, 6 tests: require_para_raid opt-in behaviour (missing/false/true
  x zero/nonzero Para-RAID paragraphs).
```

## Verify it in one command

```bash
wiki status --series spice-and-wolf     # shows data/spice-and-wolf/ stage state
python -m pytest                        # 226 passed
```

## Current real-data state — the calibration run is finished

| Stage | State | Evidence |
|---|---|---|
| ingest | done | `data/spice-and-wolf/01_parsed/{manifest.json,v01.jsonl,v02.jsonl}` |
| gazetteer | done | `data/spice-and-wolf/02_entities/{candidates,mentions}.jsonl`, `gazetteer.json`, `roster.html` |
| extract | done (v01+v02) | `data/spice-and-wolf/03_claims/{v01,v02}.jsonl` — 255 claims, 33 entities |
| graph build | done | `data/spice-and-wolf/04_graph/graph.db` — 210 intervals, 60 edges, 19 conflicts (17 extraction_error, 2 narrative_change, 0 flagged) |
| synthesize | done (`--upto 2`) | `data/spice-and-wolf/05_pages/` — 17 page files, 14 characters |
| site build | done (`--upto 2`) | `dist/spice-and-wolf/site` — 33 routes |
| audit | all clean | `links`: "OK — every reference resolves"; `claims`: "OK — every cited quote appears verbatim"; `contradictions`/`pages`: no hard failures |

**`MISTRAL_API_KEY` is dead, confirmed live, not just suspected.** A real `claim_extract` call
returned `401 {"detail":"Your API key expired on 2026-09-02."}`. `wiki doctor` will keep reporting
it "present" — doctor only checks presence, never reachability. Every stage still routed to
`mistral_fast`/`mistral_prose` (`entity_classify`, `entity_alias`, `claim_extract`, `codex_summary`,
`prose`) needs either the key renewed or an explicit `--model <stage>=google_fast` override; do not
trust `wiki doctor`'s green check for this key.

**Neither free-tier fallback is generous — pick correctly, then expect to retry:**
- `groq_fast` (`qwen/qwen3.8-27b`) — do NOT use for `claim_extract`. Its 8,000 TPM cap is smaller
  than this stage's own per-character prompt; 20 retries 65s apart all failed identically. Verified
  structurally blocked, not transient.
- `google_fast`/`google_best` (`gemini-flash-lite-latest`/`gemini-flash-latest`) — works, but this
  AI Studio key's free tier caps at **15 requests/minute** for any model. Any stage that loops one
  call per character/entity (`claim_extract`, `prose`, `codex_summary`) will hit `429
  RESOURCE_EXHAUSTED` partway through a >15-item run. Fix: just rerun the same command after the
  error's own `retryDelay` (~50-60s) — `llm/client.py`'s disk cache makes every retry pick up
  exactly where the last one stopped, never restart from zero. A caller-level retry loop (bash
  `for`/`sleep`) is more reliable than relying on `llm/client.py`'s own retry/backoff, which is too
  short (14s total) for either failure mode above.

To rerun from scratch (e.g. after `MISTRAL_API_KEY` is renewed, to compare quality against the
Google-routed run above): `wiki extract --series spice-and-wolf --force`, then the same chain.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Default series (`86`) keeps the original, unsegmented `data/`/`dist/` layout | The real, already-built 86 corpus must never be silently moved or orphaned by adding series support | Segmenting every series including the default under `data/<id>/` — simpler code, but would silently relocate the existing corpus's output on next run |
| `data/cache/llm/` never segmented | Cache keys are content-addressed (provider+model+prompt+options) — a cached answer for a given prompt is valid no matter which series asked it, so segmenting would just duplicate cost for no correctness benefit | Segmenting the cache per series "for consistency" — would double-pay for any prompt structurally shared across series (none currently, but no reason to foreclose it) |
| `set_active_series` mutates module globals, called once at startup | Every module in this codebase already imports `PARSED_DIR`/`PAGES_DIR`/etc. as bare attributes; re-threading a `series_id` parameter through every function that touches a path would touch far more files for the same result | A `series_id` argument threaded through every path-consuming function — more "correct" in isolation, but a much larger, riskier diff for Phase 9's actual goal |
| `require_para_raid` opt-in per series, not inferred | The pipeline cannot distinguish "this series has no radio-comms channel" from "the CSS-class pattern regressed and is silently missing everything" by inspection alone — the review's own listed root cause. An explicit, human-set flag is the only reliable signal | Inferring "expected" from whether the pattern matches anything on a first pass — indistinguishable from the exact silent-failure mode this check exists to catch |
| Spice and Wolf source EPUBs read from `"All novels/<title>/"` rather than moved into `raw/` | `raw/` was implicitly 86-only in every existing series config's mental model; moving files was judged out of scope for a config-only phase | Moving/copying the EPUBs into `raw/spice-and-wolf/` to match 86's layout — arguably cleaner, but a filesystem change beyond what this phase needed, and not yet decided as the long-term multi-series convention |
| Continuing the calibration run on `google_fast` rather than stopping for `MISTRAL_API_KEY` to be renewed | The key's expiry is an external account/billing action outside this session's control; `--model ...=google_fast` is an existing, already-verified (Phase 4) escape hatch, cheap, and reversible (a CLI flag, not a config rewrite) | Blocking and waiting for the user to renew the key — would have stalled a already-scoped, low-cost, resumable run for no correctness benefit |
| `synth/prose.py`'s prompt fixed with a literal JSON example, matching `codex_summary`'s already-applied fix | Same root cause (Gemini `json_mode` enforces valid JSON, never a specific shape, without one), same fix, already precedented — CLAUDE.md/docs/PROMPTS.md rule #3 says every `complete_json` prompt needs this | Leaving it as a documented-but-unfixed "worth watching" gap now that a real repro exists — the fix is a two-line, zero-risk change |
| `claim_extract` given a `fallback: google_fast` even though it won't auto-recover today's specific failure (key present-but-expired, not absent) | Matches the precedent already set for `prose`/`codex_summary` (2026-09-02 entry); helps once the key is fully unset rather than merely expired, and documents the real constraint (15 req/min) for the next person who reads `models.yaml` | Leaving `claim_extract` without a fallback since it wouldn't have prevented today's failure anyway — true, but inconsistent with its siblings and loses the chance to record the rate-limit finding where a future reader will actually see it |

## Known gaps, deliberately left

- No decision recorded yet on the long-term raw-EPUB-storage convention for a third series
  (`"All novels/<title>/"` vs. a per-series `raw/<id>/`) — only needed once a third series exists.
- None of `narrativewiki-pipeline-review.md`'s other "do now" / "short-term engineering" items
  were touched in this phase: cross-volume contradiction arbitration (still auto-promoted to
  canon, `graph/contradictions.py` unchanged), relationship/faction/event synthesis pages (PPR
  exists but is not wired into any output stage), explicit snapshot carry-forward in
  `synth/cache.py`, or mention-window/coreference widening for pronoun-only passages. Citation
  verification (quote-must-be-verbatim, `extract/claims.py`) and the post-build link checker
  (`wiki audit links`) were already in place before this review — not new to this phase.
- The frontier-model pilot (review §4/§5.2) needs a budget decision from the user before any code
  work; not started.
- **The Appearance-field dedup finding below is not fixed** — it needed a design decision (exact
  match? fuzzy cluster? cap displayed count? keep-longest?) this session didn't have the scope to
  make unilaterally.
- Only one page pair (Holo, Kraft Lawrence) was read closely for the review's requested quality
  comparison — not a full pass over all 14 characters, and not yet compared side by side against
  the equivalent 86 pages (that would need re-reading 86's existing `data/05_pages/` output, not
  done this session).

## What Phase 9 (continued) or Phase 10 needs

The calibration run is done and clean (audits pass, quotes verify verbatim). One concrete,
actionable finding came out of actually reading the generated output, the review's real ask:

**Appearance fields render as a wall of undeduplicated near-duplicate fragments.** Holo's `v02.md`
lists ~35 separate Appearance bullets — "wolf ears" / "wolf's ears" / "wolf ears and a tail" /
"lovely ears and tail" / ... — because every distinct APPEARANCE claim value gets rendered with no
canonicalization step anywhere downstream of extraction. This happened on Spice and Wolf, which has
none of 86's five confounding traits (CLAUDE.md §3) — so it is a genuine pipeline defect, not
something specific to 86's harder text. It answers the review's core question for at least this one
issue: fix it regardless of the 86-vs-simple-corpus question, and expect the same shape of bug
wherever a claim type accumulates many near-synonymous values (nicknames, titles — both visible in
the same page's Overview section, not yet checked closely for the same problem). Start at
`synth/assemble.py` (CLAUDE.md §2: structured fields render deterministically from graph rows) or
`graph/store.py` (where trait values are written) — not `synth/prose.py`, which never touches
Overview fields.

Beyond that: finish the page-by-page comparison this session only started (read the rest of the 14
Spice and Wolf pages, and the equivalent 86 pages, side by side), then classify each remaining
thinness/fabrication/breakage as either (a) present on the simple corpus too — a real pipeline bug,
fix it — or (b) absent on Spice and Wolf — a property of 86's specific text, informing whether the
review's harder architectural asks (coreference, cross-volume arbitration) are worth doing before
or after a frontier-model pilot decision. Separately, `MISTRAL_API_KEY`'s actual status (expired,
confirmed live this session) needs a decision from the user: renew it, or accept `google_fast` — at
its real 15 req/min free-tier ceiling — as the default for `claim_extract`/`prose`/`codex_summary`
going forward.
