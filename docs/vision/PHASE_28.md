# Phase 28 — The paid push: Vertex AI becomes the default, and three gates stop eating good work

Append-only. Newest entry at the bottom. One line per entry goes in `VISION.md`'s index.

---

## 2026-09-23 — Requirement: Vertex works, so finish the project on it

The maintainer's instruction, in full: *"Google vertex api is now working. I want you to complete
this project. if you believe guard rail for api calls need to be relaxed for project improvement
and testing, you are allowed to relax them but be careful that it doesn't get too expensive. try to
keep it manageable cost. try to do optimizations wherever possible (without sacrificing accuracy)."*

This supersedes the 2026-09-14 standing instruction ("OpenRouter free tier first, local only when
the key is absent") for as long as a Google Cloud project with credit is configured. The free tier
stays wired in as `fallback:` — it is not deleted, it is demoted, and a machine with no
`GOOGLE_CLOUD_PROJECT` behaves exactly as it did on 2026-09-22.

### The model was chosen by measurement, not by tier name

Eight parallel calls, the same eight real stored `claim_extract` prompts out of
`data/spice-and-wolf/_runs`, same day:

| model | ok | wall | facts/call | thinking tokens | note |
|---|---|---|---|---|---|
| `gemini-3.1-flash-lite` | 8/8 | 6.0s | **6.8** | 0 | chosen |
| `gemini-3.5-flash-lite` | 8/8 | 2.3s | 2.4 | 0 | measurably terser |
| `gemini-3.5-flash` | 7/8 | 31.9s | 6.4 | **2.6k per call** | one 429 |
| `gemini-3.8-flash` | 1 call then 429 | 48s | — | — | unusable at ~700 calls |

On prose (three sentences of wiki background from fixed facts) all four were indistinguishable,
and so was `gemini-3.1-pro-preview`, which spent 1,124 thinking tokens to say the same thing. So
the cheap fast one wins outright, and `vertex_pro` is defined but unrouted.

Two facts worth writing down because they are not obvious:

1. **The gemini-3.x family is not served from `us-central1`** — it 404s. `GOOGLE_CLOUD_LOCATION`
   must be `global`.
2. **Thinking tokens bill at the OUTPUT rate and are drawn from `max_output_tokens`.** A 3.x flash
   model asked for JSON under a small cap can spend the whole cap thinking and return an empty
   string. `llm/providers/google.py` now counts them into `out_tokens` (the budget was
   under-reporting) and accepts a `thinking_budget` profile option.

### Guardrails: relaxed in number, unchanged in kind

- `tier: frontier` + `max_volumes: 2` still refuses any call once a run's volume scope passes 2,
  before the provider is contacted. This is what keeps "Spice and Wolf volumes 1–2 only"
  mechanical.
- `max_calls_per_run` raised 20 → 2000. At 20, no real run could start; the dollar ceilings are
  what bound spend.
- `budget.lifetime_cap_usd` 5 → 20, `hard_stop_usd` 25 → 10 (per run), `warn_usd` 5 → 2.
- `tests/test_config.py` kept its cost-strategy guard but changed its shape: a routed profile must
  be either $0 **or** `tier: frontier` with a `max_volumes` cap. "Paid model, no interlock" still
  fails the suite.

**Actual spend for everything in this entry, including four scene re-runs and three extraction
re-runs: $3.13.** A single clean v1–2 pass measures ~$1.65.

## 2026-09-23 (later) — Three gates were deleting good extraction, and one check had failed open

Switching model exposed four defects that had nothing to do with which model was routed. Each was
found by comparing `yield.json` drop counters between runs, not by reading output.

1. **`Profile.is_callable`.** Vertex authenticates with ADC and a project, never an `api_key`, so
   `resolve_role`'s "no key → use the fallback" rule silently routed every Vertex stage back to the
   free tier. Nothing failed; it just quietly did not happen. `fallback:` may now be a list
   (Vertex → OpenRouter free → local), because one entry could not preserve both "prefer the free
   tier over local" and "a machine with no keys at all still runs".

2. **A gate the model was never told about.** `min_quote_words: 6` and `requires_qualifier` were
   enforced silently: 106 facts dropped for a short quote, 163 for a bare `FRIEND_OF`. Worse,
   `subject_must_be_named` contradicted the prompt outright — the prompt said a fact carried by a
   pronoun "still counts … do not require the character's own name to appear", and the gate threw
   exactly those away (342 of them). `extract/adequacy.py::prompt_rules` now generates an EVIDENCE
   REQUIREMENTS block from the same config the gates read, so a config edit cannot leave the prompt
   lying, and both extraction prompts include it.

3. **`subject_must_be_named` was too strict to be right.** Prose carries a subject across
   paragraph breaks with pronouns constantly. New config `subject_named_within_paragraphs: 1`
   widens the check to the cited paragraph's immediate neighbours *within the window the model was
   shown* (0 restores the old behaviour). The misattribution it exists to catch is still caught: a
   neighbourhood that never names the character is not about them. Effect, replayed from cache at
   zero cost: v01 127 → 170 claims, v02 218 → 269.

4. **`wiki verify` had been failing open.** The prompt asked in prose to "list the index of every
   fact…", so models answered with the shape the prose described — a bare array, or
   `{"bad_facts": [6, 12, …]}`. That last one validates perfectly against `flags: []`: unknown key
   ignored, default empty. **49 flagged facts read as "nothing flagged" and nothing raised.** The
   prompt now states the exact JSON shape and `VerificationResult` coerces every observed variant.
   First real run after the fix: 23 flagged facts across 11 of 15 characters.

Also: the scene detail prompt asked for "notable dialogue" and a literal-minded model returned 6
quotes per span where the passage held ~40 — volume 1 kept quotes for 4 of its 11 speaking
characters. It now asks for every line, selection being a downstream deterministic job
(`quotes.max_quotes`). And `_DETAIL_GENERATION_OPTIONS` num_predict 8192 → 24576, because once the
answer got long, 6 of 42 detail responses were truncated mid-JSON — and the truncated tail is
always `participant_facts`, the last key in the response.

## 2026-09-23 (later still) — Optimisations, all measured, none trading accuracy

- **The pipeline was entirely serial**; `concurrency:` in `config/models.yaml` was read by nothing.
  `llm/parallel.py::map_calls` runs a stage's independent calls a few at a time, in input order.
  Wired into candidate classification, per-character claim extraction and per-chapter scene
  extraction. Spans inside a chapter stay serial — their quote dedup and claim merge are
  order-dependent. Measured: a volume of scene extraction 8.5 min → 33s; `wiki extract` on two
  volumes ~9 min.
- **`RunContext.frontier_call_count()` was O(n²)** — it re-parsed the whole of `calls.jsonl`, full
  prompts included, on every frontier call. Now seeded once, counted in memory.
- **One Gemini SDK client per endpoint**, not per call: construction measured 0.6s and the first
  request on a fresh client another ~1.5s.
- **A 429 is "not yet", not a failure.** Vertex's shared quota answers one for minutes under a
  parallel stage, and three attempts on a 2s ladder crashed `wiki scenes` mid-volume twice.
  Rate-limited attempts now have their own budget (`rate_limit_retries: 8`) and their own ladder
  (20s, 40s, …). Concurrency on `vertex_flash` settled at 4; 8 tripped the quota.

**Result, `wiki audit eval`, mean fact recall over the ten gold characters: 39.8% → 43.9%**, with
precision still 1.0 everywhere and all eleven audits OK. Four floors raised in
`baseline.json`; `yarei` left at 0.25 although it now scores 0.0, because the one fact it used to
recall is conditional in the corpus ("Now Yarei *would be* locked in a granary … close to a week")
and gold states it as fact — the extractor declining to assert a hypothetical is correct, so the
WARN stays visible instead of being tuned away.

## 2026-09-23 (last) — Sampling variance made this phase's own comparisons argue with themselves

Two prompt experiments ran after the numbers above were recorded, and together they produced the
most useful finding of the phase — about the measurement, not the prompt.

**Experiment: does telling the model to work through every named character raise fact yield?**
A/B on eight real stored detail prompts, same model, same temperature: participant_facts 17 → 24
(subject groups 14 → 17) with quote output unchanged (469 vs 462). A clean win on its own terms.

**Then the full pipeline measured WORSE with it: mean gold fact recall 43.9% → 36.7%**, five
characters regressing against the floors recorded an hour earlier.

**Reverting the prompt did not restore 43.9%.** The reverted run scored the same 36.7%, and its
own cache told us why: 53 of 112 scene calls were fresh, not replays. `wiki gazetteer
--merge-epithets` had run in between, which is the documented order (scenes → merge → extract), and
it grows the "Known entities in this chapter" list that both scene prompts are built from. So the
comparison was never model-vs-model at all — and at temperature 0.4 the scene pass was free to
answer differently anyway.

**Conclusion, and the change that follows from it:** in structured extraction, sampling variance is
not creativity, it is an unreproducible deliverable and a measurement that cannot be trusted to
±7 points. `temperature: 0.1` is now pinned in the extraction call options
(`claims.py::_GENERATION_OPTIONS`, `scenes.py::_BEAT/_DETAIL_GENERATION_OPTIONS`); the prose stages
keep the profile's 0.4, where a little variation genuinely reads better. The per-character-sweep
prompt is NOT shipped: it measured better in isolation and worse end to end, and this phase has
already learned what happens when you ship on the isolated number.

This is the same lesson as the 2026-09-21 "16% variance" entry in `PHASE_26.md`, one layer along:
that one turned out to be a window-budget bug, this one is real sampling plus a prompt input that
legitimately changes between stages. Both say the same thing — **a before/after on this pipeline is
only valid if the whole sequence is re-run from the same starting artifacts.**
