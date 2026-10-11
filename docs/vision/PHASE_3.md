# docs/vision/PHASE_3.md — VISION entries for Phase 3 — Claims

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-02 — Mistral API standing in for local Ollama; testing scope capped at 1-2 volumes

**What:** (1) `config/models.yaml` routing for `entity_classify`, `entity_alias`, `claim_extract`,
`codex_summary`, and `prose` now points at new `mistral_fast` / `mistral_prose` profiles
(provider `openai`, `base_url: https://api.mistral.ai/v1`, model `mistral-small-latest`, a 24B
model) instead of `local_fast` / `local_prose` (Ollama). `prose_polish` / `arbitrate` fall back to
the Mistral profiles instead of the local ones. The `local_*` Ollama profiles are left defined,
unchanged, for whenever a local server is available again. (2) Until this project reaches a phase
where a full-corpus run is actually intended, any test, benchmark, or "real run" performed during
implementation is scoped to volumes 1-2 only, never the full 13-volume series.

**Why:** No Ollama server is reachable in the current working environment (see Phase 3 gaps in
`LOG.md`), but an API key for a 24B Mistral model is available. Since `claim_extract` is the bulk
stage and now costs real money per call, capping implementation-time testing to 1-2 volumes bounds
both spend and turnaround while phases are still being built and re-run.

**Implies:** `claim_extract` no longer satisfies "Local first" (`CLAUDE.md` §2) for the current
environment — this is a deliberate, logged exception, not a silent drift. Anyone running a real
full-series extraction should first re-point `routing.claim_extract` back to `local_fast` once
Ollama is reachable, or accept the Mistral API cost across all 13 volumes with eyes open. No code
changed — this is entirely a `config/models.yaml` edit, per the existing provider-swap design.

**Status:** Done (config only) — 2026-09-02.

---


## 2026-09-02 — Token-efficiency programme (Phase 3.5), quality held constant

**What:** Five cost levers, ordered by expected impact, to be implemented as Phase 3.5 before any
multi-volume extraction run. Quality is a constraint, not a variable: no lever may reduce claim
recall, drop evidence, or weaken the verbatim-quote validation.

1. **Window-major (joint multi-entity) extraction.** `extract/claims.py` currently calls the model
   once per *(character, window)* — `extract_character_volume` builds windows per entity, and
   line ~329 already computes the other characters in the window and then discards them. A scene
   naming five characters is therefore sent five times. Restructure to iterate over deduplicated
   windows and extract claims for every character mentioned in that window in one call. Saving is
   the mean entities-per-window factor — **to be measured on v01-02, not assumed**.
2. **Prompt caching.** The claims system prompt (schema + closed predicate vocabulary + example)
   is byte-identical across every call. Mistral bills cached prefix tokens at 10% of input price
   via a stable `prompt_cache_key`; the `openai.py` adapter must pass it and the prefix must stay
   first and unchanged.
3. **Batch API.** This pipeline is entirely offline — latency is irrelevant. Mistral's batch
   endpoint is a documented 50% discount and composes with caching.
4. **Strict structured outputs.** Replace `response_format: json_object` with a JSON *schema*.
   Every repair retry currently re-sends the whole window (`json_repair_attempts: 2`), and
   `_salvage_truncated_array` exists because truncation is real; schema enforcement plus a correct
   `max_tokens` removes that entire class of wasted call.
5. **Encoder-based window triage (optional, measure first).** GLiNER-Relex-style joint NER+RE runs
   locally in one forward pass at zero API cost. Use it only to *triage* windows unlikely to carry
   any new attribute/relation, at a deliberately permissive threshold, and only if a v01-02
   recall check shows it drops no claims the LLM would have found. The 5070 Ti is idle now that
   generation moved off Ollama.

**Explicitly rejected:** prompt/context compression (LLMLingua-style). `claims.py` drops any claim
whose quote is not verbatim in its cited paragraph; compressing input text destroys exactly the
fidelity that validation depends on.

**Why:** The bulk stage now costs real money per call (2026-09-02 Mistral entry). Lever 1 is also
a *correctness* win — document-level joint extraction avoids the per-entity pipeline's error
propagation, and it directly fixes Phase 3's known gap that symmetric relations are extracted twice
from both sides and never deduplicated.

**Implies:** `extract/claims.py` restructured window-major (prompt rule "one subject per call" in
`PROMPTS.md` is superseded); `llm/client.py` grows a batch submission path and cache-key support;
`llm/providers/openai.py` passes `prompt_cache_key` and a JSON schema. Every lever is measured on
volumes 1-2 only, per the same-dated testing-scope entry above.

**Status:** Planned — Phase 3.5, blocked on a working Mistral key.

---


