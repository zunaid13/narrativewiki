# docs/vision/PHASE_8.md — VISION entries for Phase 8 — --model CLI override

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-03 — `--model` CLI override; a stale worktree was the active editable install

**What:** Every command that resolves a stage (`doctor`, `gazetteer`, `extract`, `graph build`,
`synthesize`, `site build`, `run-all`) now accepts a repeatable `--model`/`-m` flag:
`<role>` (every stage), `<stage>=<role>` (one stage), or `<stage>=<provider>:<model>` for a model
id with no `config/models.yaml` profile yet. `config.py::resolve_role` — already documented as
the one chokepoint every model decision funnels through — now consults `Settings.model_overrides`/
`adhoc_profiles` before the ordinary `routing` table, and an explicit override deliberately
bypasses the key-absent-fallback substitution: naming a model and having it silently swapped for
something else would be a worse surprise than the profile simply not working until its key is
set (same failure shape the existing keyless-no-fallback path already has, just without the
substitution). An ad-hoc `provider:model` clones an existing same-provider profile's
options/pricing/api_key/base_url (preferring the stage's own current profile, then the first
matching profile in `models.yaml`, then `default_role` — which this gives a first real use; it
was previously read by nothing) and warns once that its cost estimate is inherited, not measured.

Also added: `groq_fast`/`groq_prose` profiles (`.env` already carried `GROQ_API_KEY` with nothing
routed to it), and a commented-out `vertex_frontier` placeholder plus a `Profile.use_vertex` flag
in `llm/providers/google.py` so the Vertex key arriving later is a `--model` flag and an
uncommented config block, never a code change.

**Why:** The user asked to select models via CLI flags instead of editing `config/models.yaml`
every time, specifically so the promised Vertex frontier key is a flag on arrival. Role-name
overrides were chosen as the primary form (not raw model ids) because pricing, `api_key_env`,
`base_url` and provider-shaped option keys all travel with a profile and a bare id carries none
of them — confirmed by exploration of `llm/cache.py::make_key` (hashes provider+model+options, so
an override correctly misses cache and a revert correctly re-hits) and `llm/budget.py` (prices
from the resolved `Profile`, so an override is costed correctly).

**A real-data trap found choosing the Groq model id:** the obvious pick, `llama-3.3-70b-versatile`,
404s on this key/tier — Groq's available models change often. Of what this key actually serves,
the `openai/gpt-oss-*` models are reasoning models that spend `max_tokens` on a hidden `reasoning`
field before ever writing `content`; `llm/providers/openai.py` only reads `content`, so this
project's tight per-stage token budgets would silently come back empty — the same class of
failure as the `codex_summary`/Gemini shape-guessing bug (2026-09-02 entry above), just a
different mechanism. Verified live against the actual key: `qwen/qwen3.8-27b` returns clean
`content` immediately, plain and with `response_format: json_object`, so `groq_fast`/`groq_prose`
route there instead.

**A real environment bug found along the way, unrelated to this feature:** the editable
`narrativewiki` install (`pip install -e .`) resolved to `.claude/worktrees/wiki-polish-and-guide`
— a stale git worktree on an unrelated, unmerged branch (`worktree-wiki-polish-and-guide` @
`4df352c`, ahead of this repo's `main` @ `0d2303a`) — not this repo. Every `wiki`/
`python -m narrativewiki` invocation was silently running that worktree's code, not what `git
status` on this repo shows. Fixed by `pip install -e .` from this repo's root; the worktree itself
was left untouched (it holds unmerged work from a prior session, not something to discard without
being asked). Anyone hitting an inexplicable "my edit isn't taking effect" on this repo should
check `python -c "import narrativewiki; print(narrativewiki.__file__)"` first.

**Implies:** `resolve_role`'s docstring, `USER_GUIDE.md`, and `CLAUDE.md` §6 all need to describe
the override now. `wiki doctor`'s routing panel marks an overridden stage inline and health-checks
override roles/ad-hoc profiles that the static routing-table loop would otherwise never probe.

**Status:** Done — 21 new tests (`tests/test_cli_model_flag.py`, plus two in `test_config.py` for
the Groq profiles and the `use_vertex` default), 212/212 passing. Real-data verified: `wiki doctor
--model claim_extract=groq_fast` (routing panel shows the override, health row confirms the key),
`--model prose=google:gemini-2.5-flash-lite` (ad-hoc clone + printed cost-estimate warning),
`--model claim_extract=nonesuch` (ConfigError listing valid roles), and `--model google_fast`
(every stage overridden). One real `arbitrate` call through the Groq override, priced at
`$8.4e-06` from the override's own profile; a repeat of the identical call hit the LLM cache at
zero added cost; reverting the override re-resolved to `google:gemini-flash-lite-latest` and made
its own fresh (uncached) call — confirming the cache key and budget pricing both follow the
resolved profile, not the stage name, exactly as designed.

---


