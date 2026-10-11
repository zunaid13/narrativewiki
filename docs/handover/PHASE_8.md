# Phase 8 — `--model` CLI override

**Closed:** 2026-09-03 · **Next:** Phase 9, a Spice and Wolf calibration corpus

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

```
src/narrativewiki/config.py
  Settings.model_overrides: dict[str, str]        stage (or "*") -> role name
  Settings.adhoc_profiles:  dict[str, Profile]     stage (or "*") -> a cloned, ad-hoc Profile
  Settings.resolve_role()    now checks adhoc_profiles[stage], then adhoc_profiles["*"], then
                              model_overrides[stage] or ["*"], before the ordinary routing table.
                              An override BYPASSES the key-absent-fallback substitution.
  Profile.use_vertex: bool   new field, default False. Set from a profile's `use_vertex: true`.
  parse_model_override(spec, settings) -> (stage, adhoc_profile | None, role | None)
                              Parses one --model argument. Exactly one of the last two is set.
  _base_profile_for_clone(settings, stage, provider) -> Profile
                              What an ad-hoc override clones options/pricing/api_key/base_url
                              from: (1) the stage's own current profile if same provider,
                              (2) the first models.yaml profile with that provider, (3) default_role.
  apply_model_overrides(settings, specs) -> list[str]
                              Applies zero or more --model specs to `settings` in place. Returns
                              warning strings (one per NEW ad-hoc override) for the CLI to print.

src/narrativewiki/cli.py
  ModelOpt = Annotated[Optional[list[str]], typer.Option("--model", "-m", ...)]
  _settings(series, model=None)   now applies overrides and prints any warnings before returning.
  --model wired on: doctor, gazetteer, extract, graph build, synthesize, site build, run-all.
  run_all forwards model=model to every stage command it chains (they are plain Python calls,
    not subprocess/click dispatch -- see PHASE_3/4's own notes on this).
  doctor's "Stage -> model routing" panel marks an overridden stage inline
    ("(--model override)") and health-checks override roles/ad-hoc profiles the static
    routing-table loop would otherwise never probe.

src/narrativewiki/llm/client.py
  LLMClient.health_profile(profile)   NEW. Same probe as health(role), but takes an already-
    resolved Profile -- what doctor needs for an ad-hoc override, which has no role name to look
    up. health(role) now just calls _build_profile(role) then delegates to this.

src/narrativewiki/llm/providers/google.py
  _client()/health() now branch on profile.use_vertex: True builds
    genai.Client(vertexai=True, project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
    instead of genai.Client(api_key=...). Unexercised against a real Vertex project -- no key
    exists yet (arriving later per the user). The AI Studio path is untouched and still default.

config/models.yaml
  groq_fast / groq_prose   NEW profiles, provider: openai (Groq is OpenAI-compatible, same trick
    as mistral_*), model: qwen/qwen3.8-27b -- see "The Groq model trap" below for why not
    llama-3.3-70b-versatile (obvious first guess, 404s) or any openai/gpt-oss-* model.
  vertex_frontier          NEW, commented out. Uncomment + set GOOGLE_CLOUD_PROJECT/LOCATION once
    the Vertex key exists; no code change needed either way.

tests/test_cli_model_flag.py   NEW, 19 tests: all four --model spec forms, ad-hoc cloning rules,
  every error path, override-priority ordering (stage-specific adhoc > global adhoc > stage
  role-override > global role-override > ordinary routing), the key-absent-fallback bypass, and
  warning dedup across repeated apply_model_overrides calls (what run-all does).
tests/test_config.py           +2 tests: groq_fast/groq_prose are defined and openai-compatible;
  Profile.use_vertex defaults False for every existing profile.
```

## Verify it in one command

```bash
wiki doctor --model claim_extract=groq_fast    # routing panel marks the override, health row
                                                # confirms GROQ_API_KEY works
wiki doctor --model prose=google:gemini-2.5-flash-lite   # ad-hoc clone + cost-estimate warning
wiki doctor --model claim_extract=nonesuch     # ConfigError listing valid roles, exit 1
python -m pytest                               # 212 passed
```

**This was verified for real, not just against unit tests.** One genuine `arbitrate` call was
made through `--model arbitrate=groq_fast` (resolves to `openai:qwen/qwen3.8-27b` — Groq is
OpenAI-compatible, so its provider is `openai`, not a distinct one): priced at `$8.4e-06` from the
override's own profile pricing; an identical repeat call hit `llm/cache.py`'s disk cache at zero
added cost; reverting the override re-resolved to the original `google:gemini-flash-lite-latest`
role and made its own fresh, uncached call. This confirms `make_key`'s cache key and `Budget`'s
pricing both follow the *resolved profile*, not the stage name — an override cannot pollute or
bypass either.

## Things you need to know

**Override priority, most specific first:** a stage-specific ad-hoc profile beats a global
(`"*"`) ad-hoc profile, which beats a stage-specific role override, which beats a global role
override, which beats the ordinary `routing:` table. `resolve_role`'s own docstring states this;
`test_cli_model_flag.py`'s priority tests are the executable spec if the two ever disagree.

**An override does not fall back on a missing key — this is deliberate, and matches an existing
pattern rather than inventing a new one.** The *ordinary* (non-override) path already returns a
keyless profile as-is when no `fallback` is declared for that stage; it does not raise early. An
override just extends that same behaviour by skipping the fallback substitution too. The actual
failure, if the key really is missing, happens naturally at call time as a `ProviderError` ->
`LLMError`, with the same "run `wiki doctor`" hint every other LLM failure gets. Do not add an
early `ConfigError` for a missing key on an override — it would special-case overrides for no
functional benefit over what already happens at call time.

**The Groq model trap.** `llama-3.3-70b-versatile` — the obvious model id to reach for — 404s on
a real key today; Groq's available model list rotates. Worse, several of what IS available
(`openai/gpt-oss-20b`, `-120b`, `-safeguard-20b`) are reasoning models: they spend `max_tokens` on
a hidden `reasoning` field before ever writing to `content`, and `llm/providers/openai.py` only
ever reads `content` (`data["choices"][0]["message"]["content"] or ""`). This project's per-stage
token budgets are all tight (512-1536), so a reasoning model under this adapter silently returns
an empty string instead of erroring — the same failure *shape* as the `codex_summary`/Gemini
JSON-shape bug from Phase 7 (VISION.md 2026-09-02), just a different mechanism (hidden reasoning
tokens vs. an unconstrained JSON shape). `qwen/qwen3.8-27b` was verified live (plain text and
`response_format: json_object`) to write directly to `content` with no reasoning field, so that is
what `groq_fast`/`groq_prose` use. If another Groq-hosted reasoning model is ever added as a
profile, either raise `max_tokens` enough to cover its reasoning budget, or forward a
`reasoning_effort: "none"`/`"low"` request option once `llm/providers/openai.py` supports passing
it through — it does not today; only `temperature`/`max_tokens`/`response_format` are forwarded.

**A real, unrelated environment bug was found and fixed while verifying this phase.** The editable
`narrativewiki` install pointed at `.claude/worktrees/wiki-polish-and-guide` — a stale git
worktree sitting on its own unmerged branch (`worktree-wiki-polish-and-guide` @ `4df352c`, ahead
of this repo's `main` @ `0d2303a`), not this repository. Every `wiki`/`python -m narrativewiki`
invocation was silently running that worktree's code. Fixed with `pip install -e .` run from this
repo's root; the worktree itself was deliberately left untouched — it holds unmerged work from a
prior session and discarding it was not this phase's call to make. Anyone whose edit "isn't taking
effect" on this repo should check `python -c "import narrativewiki; print(narrativewiki.__file__)"`
before assuming the change is wrong.

**`default_role` (`config/models.yaml`) now has an actual use.** It was previously read by
nothing in `src/` (confirmed by exploration). `_base_profile_for_clone`'s third and last fallback
reads it, so an ad-hoc override for a provider with no matching profile at all still has somewhere
to clone options from, provided `default_role` names a profile that exists.

**`use_vertex` is unexercised against a real Vertex project.** The branch in
`llm/providers/google.py` is a handful of lines mirroring the existing `api_key` path, reviewed
but not live-tested — there is no Vertex key in this environment yet. Verify it for real the same
way the AI Studio key was verified in Phase 4 (VISION.md 2026-09-02 "Google key for polish +
arbitration"): a real `client.complete()` call through `LLMClient`, not just `wiki doctor`, which
only checks that `GOOGLE_CLOUD_PROJECT` is set, not that it is actually reachable or has the right
IAM role for the Vertex AI API.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Role-name overrides as the primary form; ad-hoc `provider:model` as a secondary, warned form | A role carries pricing/api_key_env/base_url/option-shape with it; a bare model id carries none of that (confirmed via `llm/cache.py`/`llm/providers/*.py` exploration) | Accepting only raw model ids — simpler flag, but every override would need its options/pricing guessed, and budget tracking would misreport cost |
| A per-command `--model` option, no `@app.callback`, threaded explicitly through `run-all` | `cli.py` has no callback today, and `run-all` already calls the other commands as plain Python functions (not subprocess dispatch) — matching that existing pattern needed no new plumbing | A `typer.Context.obj`-based global option — would need a callback added to `app` for the first time, more invasive for the same result |
| Override bypasses key-absent fallback | The caller named a specific model; silently substituting a different one on a missing key is a worse surprise than a clear, familiar `LLMError` at call time | Falling back the same way the ordinary routing table does — would make `--model prose=anthropic_best` with no Anthropic key silently run Mistral instead, defeating the point of asking for it explicitly |
| Ad-hoc profile clone order: stage's own current profile -> first same-provider profile -> `default_role` | Prefers the option/pricing shape most likely to match the model actually being tried, cheapest lookup first | Always cloning the first same-provider profile regardless of stage — simpler, but wrong when the stage's own current role already uses the right provider with different (often cheaper) options |
| `groq_fast`/`groq_prose` point at `qwen/qwen3.8-27b`, verified live | The obvious id (`llama-3.3-70b-versatile`) 404s on this key; reasoning models on this same provider have a silent-empty-output trap under this project's tight token budgets | Picking a model id from Groq's docs without a live round-trip call — exactly what caused the `codex_summary` Gemini bug this project already hit once |
| Reinstall the editable package rather than editing/removing the stale worktree | The install pointing at the wrong path was the actual bug; the worktree's unmerged content is not this phase's to judge or discard | Leaving the broken install in place and just noting it — would leave every future `wiki` invocation in this environment silently wrong |

## Known gaps, deliberately left

- `use_vertex` has no real-project test (see above) — the Vertex key does not exist yet.
- `llm/providers/openai.py` does not forward a `reasoning_effort` request option, so a future
  Groq (or any OpenAI-compatible reasoning-model) profile needs either a large `max_tokens`
  headroom or a small adapter change first — not needed for `qwen/qwen3.8-27b`, which has no
  reasoning field, so not added speculatively here.
- No CLI-level test (`typer.testing.CliRunner`) exercises `--model` through the actual command
  bodies end to end — the 19 new tests cover `parse_model_override`/`apply_model_overrides`/
  `resolve_role` directly, which is where the logic actually lives, and the real `wiki doctor`
  runs quoted above covered the CLI wiring by hand. `cli.py` still has no test harness at all
  (a pre-existing gap Phase 7's exploration already noted).
- `wiki budget`'s on-disk persistence (`Budget.save`) was not touched or re-verified here — Phase
  6's handover already notes nothing calls it yet.

## What Phase 9 needs

A model override never needed a data-layout change, so Phase 8 leaves `paths.py` untouched.
Phase 9 (a Spice and Wolf calibration corpus) is the first time a second series's data would
actually be written, and `paths.py` currently has no series segment in any `data/NN_*/` path —
see the plan's Phase 9 note. Decide and record that explicitly before running `wiki ingest
--series spice-and-wolf`, or it will silently interleave with (or overwrite) the real 86 corpus's
output.
