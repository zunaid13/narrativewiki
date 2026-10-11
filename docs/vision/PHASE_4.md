# docs/vision/PHASE_4.md — VISION entries for Phase 4 — Graph

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-01 — Temporal knowledge graph as the fact store

**What:** Facts are stored as TKG quadruples `(subject, predicate, object, vol_start, vol_end)`
rather than as a per-character document.

**Why:** Two requirements force it. (1) Spoiler scoping needs a per-fact validity interval.
(2) The user requires that contradictory information is avoided *unless* the contradiction comes
from a change over time ("a person who was kind became evil") — which is exactly a closed interval
followed by a new one.

**Implies:** `graph/temporal.py` and `graph/contradictions.py` are the correctness core. Same-volume
conflicts are extraction errors and get arbitrated + logged; cross-volume conflicts are narrative
change and get interval supersession. Character pages show the current value at the cutoff plus an
expandable history of prior values, itself filtered to the cutoff.

**Status:** Planned — Phase 4.

---


## 2026-09-02 — Google key for polish + arbitration

**What:** `config/models.yaml` routes `prose_polish` and `arbitrate` — CLAUDE.md §2's "API keys are
spent only on final prose for major characters and on contradiction arbitration" — to new `google_best`
(`gemini-flash-latest`) and `google_fast` (`gemini-flash-lite-latest`) profiles instead of
`anthropic_best`/`anthropic_cheap`, with `mistral_prose`/`mistral_fast` kept as the `fallback` role
unchanged. `entity_classify`/`entity_alias`/`claim_extract`/`codex_summary`/`prose` are untouched —
still Mistral, per the 2026-09-02 entry above.

**Why:** The user provided a `GOOGLE_API_KEY` (from aistudio.google.com); no `ANTHROPIC_API_KEY` has
ever been set in this environment, so `prose_polish`/`arbitrate` were silently falling all the way
back to Mistral with no distinct "best-effort" tier above the bulk stage. Two model names needed
correcting against what this key's tier actually serves, discovered by a live call, not by
assumption: `gemini-2.5-pro` and `gemini-2.5-flash` both returned errors (`2.5-flash` is deprecated
for new keys; `gemini-pro-latest`, the intended `google_best` target, returned
`429 RESOURCE_EXHAUSTED` — this AI Studio key's tier has no Pro quota without billing enabled).
`gemini-flash-latest` and `gemini-flash-lite-latest` both round-tripped successfully through the
real `LLMClient` (not just the SDK directly) and are what `google_best`/`google_fast` now point at.

**Implies:** If billing is ever enabled on this Google key, `google_best.model` should be revisited
(`gemini-pro-latest`) for a real quality step up over Mistral on prose polish — flash-latest is a
reachability fix, not necessarily the best available tier. `docs/PROMPTS.md`'s `arbitrate_conflict`
note ("routes to `anthropic_cheap`") is now stale prose describing the *pattern* (rare, cheap,
local-model-can't-referee-itself), not the literal current profile name — the routing table in
`config/models.yaml` is the source of truth, per CLAUDE.md §2 ("route via config/models.yaml; never
hard-code a model name in a module... elsewhere").

**Status:** Done (Phase 4) — verified against a real `wiki graph build` run on the existing v01-02
claims: one same-volume conflict was arbitrated for real by `google_fast`
(`data/04_graph/contradictions.json`, subject `weisel`, predicate `ORIGIN`), not just a smoke test.

---


