# docs/vision/PHASE_10.md — VISION entries for Phase 10 — Provenance/runs

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-03 — Six-phase redesign: auditable iteration + STORM/WikiMAG-style outline planning

**What:** A large follow-on scope, planned against `narrativewiki-pipeline-review.md` plus a
literature pass (STORM/NAACL 2024, WikiMAG/AAAI, WikiAutoGen/ICCV 2025) and four new operating
rules from the user: (1) frontier-model API calls capped at 2 volumes; (2) every LLM response
snapshotted with its prompt and a timestamp, so a repeated question is answered from the log
instead of re-asked; (3) strictly iterative, one-chapter-at-a-time processing with a mandatory
pause for manual audit and the ability to roll a run back; (4) every module's inputs/outputs
traceable end to end by a non-coder, documented in `USER_GUIDE.md`. Full plan:
`docs/handover/` will gain `PHASE_10.md` onward as each lands; the plan file itself lived at
`C:\Users\pc\.claude\plans\glittery-hugging-duckling.md` during planning.

Six phases: **10** provenance/run-ledger/rollback/frontier-interlock, **11** chapter-level `wiki
step` loop, **12** HTML audit reports + `wiki trace`, **13** planned page outline (closed section
vocabulary, replacing the two hand-synced hardcoded templates in `okf.py`/`app.js`), **14**
over-association + cross-volume-arbitration + neutrality + value-canonicalization fixes (the
literal STORM editor-named failure modes, already reproduced on this project's own output — Holo's
page asserts both `Enek — Friend of` and `Enek — Enemy of`; her Appearance field lists ~40
near-duplicate fragments), **15** an evaluation harness using the papers' own metrics (heading
soft/entity recall, citation entailment, neutrality lint, association lint) against a small
hand-written in-domain reference outline (FreshWiki itself is non-fiction Wikipedia, not usable
directly), **16** `config/models.yaml` routing reset + a non-coder-oriented `USER_GUIDE.md` rewrite.

**Why:** The review memo's three symptoms (thin pages, false claims, broken links) map cleanly onto
STORM's own expert-editor findings once you read the two together — this project already exhibits
"source bias transfer" (uncounted evaluative language) and "over-association" (relation pairs
asserted without a stated predicate, worse than plain hallucination per STORM's editors) as
concretely observable defects, not hypothetical risks. Separately, none of the user's four new
operating rules have any supporting infrastructure today: no run/snapshot concept exists in
`paths.py`; `llm/cache.py` stores the response only (`{text, in_tokens, out_tokens}`), never the
prompt, system prompt, or a timestamp, so a cached answer cannot be traced back to what was asked;
`Budget.save()` has no production caller so `wiki budget` always reports nothing recorded; chapter
identity exists inside every paragraph record (`ingest/segment.py:25`'s `para_id`) but no CLI flag
or path function can address one; and `wiki audit links` prints FAIL but exits 0, so a broken build
ships silently.

**Implies:** Everything downstream of `synth/assemble.py`'s hardcoded field table becomes
outline-driven — a real, large refactor of `synth/`, `site/okf.py`, and `site/templates/app.js`
that Phase 13 owns. `graph/contradictions.py`'s cross-volume path (currently auto-accept, no
review — VISION.md history above never revisited this) gets real scrutiny for the first time in
Phase 14. `llm/providers/ollama.py` needs an `/api/embed` path it does not have today, for the
zero-cost local dedup/eval work in Phases 14-15.

**Status:** Planned; implementation starting on branch `phase10-provenance-runs`. The first
concrete action taken (see the entry immediately below) was pulled forward from Phase 16 rather
than done last, because it was blocking every other planned real-data verification run.

---


## 2026-09-03 — Phase 10 built: run ledger, per-call prompt/response log, rollback, frontier interlock

**What:** `provenance.py` (new): every command that writes to a stage directory now starts a
`RunContext` under `data/<series>/_runs/<run_id>/` — a manifest (command, scope, volume_scope,
argv, git sha, config-file hashes, outcome), `calls.jsonl` (one line per LLM call, hit or miss,
with the full system prompt, user prompt, response, and a timestamp), a per-run `budget.json`, and
a pre-run snapshot of whatever stage directories it is about to touch. `llm/client.py::_call` is
the only writer of `calls.jsonl`; `LLMClient` takes optional `run=`/`volume_scope=` constructor
args so no stage module (`extract/claims.py`, `synth/prose.py`, ...) needed to change. `Profile`
gained `tier`/`max_volumes`/`max_calls_per_run`; a `tier: frontier` profile is refused by
`_enforce_frontier_scope` (raising `FrontierScopeExceeded(LLMError)`) once the run's volume scope
or frontier call count exceeds its configured limit — checked only on a cache miss, never a hit.
New commands `wiki runs`, `wiki calls [--run] [--stage] [--grep]`, `wiki rollback <id> --yes`;
`wiki budget` now actually works (`Budget.save()` finally has a caller) and gained `--run <id>`.
`llm/cache.py`'s stored entries also gained `stage`/`provider`/`model`/`system`/`prompt`/
`first_seen_ts`, backwards-compatible with every existing cache entry.

**Why:** The four new operating rules (see the six-phase plan entry above) had zero supporting
infrastructure. Rule 2 (every response snapshotted with prompt and timestamp) needed the call log;
rule 1 (frontier calls capped at 2 volumes) needed the interlock to be enforced in code, not
documentation; rule 3's rollback half needed the pre-run snapshot.

**A real bug found and fixed during implementation, not just planned:** the first version of
`snapshot_before` hardlinked instead of copying (cheaper on the same volume). Every stage in this
codebase writes its output via `path.open("w")`, which truncates the existing file **in place**
rather than writing a new file and renaming over it — so a hardlinked "snapshot" shares the live
file's inode, and the stage's own next write silently corrupts the snapshot too. Caught by
`tests/test_provenance.py::test_snapshot_before_and_restore_round_trip` before this ever ran
against real data; `_copy_tree` now always does a real copy, documented at the point of the fix so
the next person does not reintroduce it for the same "hardlinks are cheaper" reason.

**Implies:** `wiki budget`'s cumulative total now lives at `data/<series>/budget.json` (series-
scoped), not `llm/budget.py`'s own unsegmented default (`data/cache/llm/budget.json`, which stays
shared across series on purpose — it backs the content-addressed LLM cache, not cost accounting).
`graph build` gained a `try/except LLMError` around `contradictions_mod.build_graph` it did not
have before (for a consistent `run.finish("failed", ...)` hook) — a small, in-passing robustness
fix, not itself a Phase 10 goal.

**Status:** Done — 291/291 tests pass (38 new: `test_provenance.py` plus Phase 10 additions to
`test_llm.py`). Verified against real, live data, not just tests: `wiki graph build --series
spice-and-wolf` (a genuinely non-destructive full rebuild from existing claims) produced the same
210 intervals / 60 edges / 19 conflicts as before, `wiki runs --series spice-and-wolf` showed the
run, and `wiki calls --run <id>` printed real `qwen2.5:32b` arbitration prompts and responses with
timestamps. Full state and what Phase 11 needs: `docs/handover/PHASE_10.md`.


## 2026-09-04 — OpenRouter free-tier routing for prose-quality stages

**What:** Route `prose`/`prose_polish`/`codex_summary`/`arbitrate` to a free OpenRouter model
(MiniMax M3, `minimax/minimax-m3:free`) instead of Groq's `openai/gpt-oss-20b`, with `groq_prose`/
`local_best` kept as the one-hop fallback in each case (config.py's `resolve_role` only honours a
single fallback level, not a chain).

**Why:** User request: "use a stronger but free model like minimax or nemotron" now that an
OpenRouter key is available, wanting a visibly better final prose/codex output for the Spice and
Wolf v1 site without spending money. Checked live against `https://openrouter.ai/api/v1/models`
(not guessed) before picking a model id: of OpenRouter's free-tier listings, `minimax/minimax-m3:
free` (1M context) and `nvidia/nemotron-3-super-120b-a12b:free` both declare `response_format` in
`supported_parameters` (required for `llm/providers/openai.py`'s `json_mode` path, used by
`arbitrate`); `nvidia/nemotron-3-ultra-550b-a55b:free`, despite being the largest, does not list
`response_format` and was passed over for that reason. MiniMax M3 was chosen over the Nemotron
Super option as the larger context window at the same $0 price.

**Implies:** New `openrouter_free` profile in `config/models.yaml`; `routing:` entries for the
four prose-quality stages repointed at it. `entity_classify`/`entity_alias`/`claim_extract` are
UNCHANGED — bulk extraction still routes `local_fast` (Ollama) per CLAUDE.md §2's "local first"
rule; this is a fallback/prose-quality change only, not a bulk-cost-strategy change. Separately
(unrelated bug, found while wiring this up): the user's pasted key landed in `.env` under
`OPEN_ROUTER_API`, not the `OPENROUTER_API_KEY` name `api_key_env` actually reads — silently
ignored rather than erroring, since a missing key just falls back. Renamed in place. Three tests
pinned the old routing decision (`test_config.py::test_bulk_stages_route_local_or_sanctioned_groq`,
a new pair replacing `test_prose_falls_back_to_local_when_groq_key_missing`, and
`test_cli_model_flag.py::test_adhoc_prefers_the_stages_own_current_provider_when_it_matches`) and
were updated to match, same as every prior routing change in this file's history.

**Status:** Done. 291/291 tests pass. Verified against real, live data: `wiki synthesize --series
spice-and-wolf --upto 2 --polish --force` (9 fresh prose generations, 21 pages written) and `wiki
site build --series spice-and-wolf --upto 2 --force` both ran clean against `openai:minimax/
minimax-m3:free`; `wiki audit links --series spice-and-wolf` reports every one of 33 routes
resolving with zero broken references.

---


