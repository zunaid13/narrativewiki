# docs/vision/PHASE_6.md — VISION entries for Phase 6 — Prose/synthesize

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-01 — Short, non-contradictory prose

**What:** `background` and `personality` are 2–4 sentences each, generated only from the
volume-filtered claim set, with evidence references retained.

**Why:** The user asked for short descriptions for anything not expressible in a word or a sentence.
Long generated prose is also where hallucination and spoiler leakage hide.

**Implies:** Structured fields are rendered from graph rows with no LLM involvement at all. Prose
generation is the only generative step, which makes it cheap to cache on a claim-set hash and cheap
to audit.

**Status:** Planned — Phase 6.

---


## 2026-09-02 — Prose is generated from TRAIT claims only, never from structured fields

**What:** `synth/prose.py` (Phase 6) builds `background` from BACKGROUND trait claims and
`personality` from PERSONALITY/MOTIVATION/SKILL/FEAR trait claims — never from the scalar
attribute/relation fields `synth/assemble.py` renders (age, status, rank, affiliations,
relationships, ...). A field is `null`, with no LLM call made, when the character has zero trait
claims of that kind visible at the cutoff. `evidence` on the returned page is not something the
model reports back; it is the exact `para_id` set the prompt was built from.

**Why:** `docs/PROMPTS.md`'s existing split — `personality_prose` "from trait claims only" — was
already the design; this makes `background_prose` match it exactly rather than inventing a wider
"biography context" pull from structured fields, which CONTRACTS/PROMPTS never specified and would
have needed new evidence-fetching plumbing duplicating `synth/assemble.py`'s. It also keeps
CLAUDE.md §2 ("structured fields are never LLM-generated") unambiguous: the model never sees a
field it might restate as if it were the generated prose. Skipping the LLM call entirely when there
is no trait evidence avoids the exact hallucination risk CLAUDE.md §1 exists to prevent, and costs
zero tokens for the (common, at early cutoffs) case of a minor character with no traits yet.

**Implies:** A character can legitimately reach `--upto N` with populated structured fields
(status, affiliations, relationships from attribute/relation claims) and still have `prose: {
"background": null, "personality": null }` if no trait claims exist yet — this is correct, not a
bug, and `wiki audit pages` reports it as "zero structured fields" only when `fields` itself is
empty, a different condition.

**Status:** Done (Phase 6) — see the Phase 6 LOG.md entry and `docs/handover/PHASE_6.md`.

---


## 2026-09-02 — `wiki synthesize` caching compares cutoff N to cutoff N-1, not to its own last write

**What:** `synth/cache.py::previous_page(entity_id, upto_vol)` walks downward from `upto_vol - 1`
to the nearest cutoff with a file already on disk, and `unchanged(prev, claim_set_hash)` decides
whether the current cutoff needs writing. This correctly collapses a long run of adjacent,
factually-identical cutoffs (CONTRACTS §5.1's "13x multiplier"), including across a resumed
`--upto` invocation with gaps already on disk. It does **not** make a full command re-run a no-op
at the file-write layer: cutoff N is always compared to cutoff N-1's content, not to cutoff N's own
previous run, so re-running `wiki synthesize --upto 2` twice in a row rewrites both files both
times.

**Why:** This is the literal reading of CONTRACTS §5.1 ("If it is unchanged from cutoff N-1...").
A same-cutoff idempotency check (comparing this run's output to the last time *this exact cutoff*
was written) is a different, stronger guarantee nothing in CONTRACTS asks for, and would need a
second comparison path alongside the one §5.1 actually specifies — not worth the complexity when
the expensive resource (LLM spend) is already protected: `llm/cache.py` caches on the exact
request, so a byte-identical prompt on a rewritten cutoff costs nothing.

**Status:** Done (Phase 6) — verified by re-running `wiki synthesize --upto 2 --entities shin
--polish` twice against real data; the second run rewrote both files but made no new network call
(same `generated_by`/prose text both times).

---


## 2026-09-02 — `config/models.yaml`: `prose`/`codex_summary` had no reachable fallback

**What:** `prose` and `codex_summary` routed to `mistral_prose` with no `fallback` entry at all,
unlike every other API-routed stage (`prose_polish`, `arbitrate`). `Settings.resolve_role` only
substitutes the fallback role when the primary profile's API key is *absent* from the environment
— not when the key is present but rejected by the provider (expired, revoked, out of quota). Both
now declare `fallback: google_fast`.

**Why:** Found during Phase 6 real-data testing: `MISTRAL_API_KEY` in this environment expired on
2026-09-02 (the provider returned a 401 saying so), which `resolve_role` cannot detect ahead of a
real call, so `prose` dead-ended with no fallback path even though a working Google key was
present. This does not fully fix the underlying limitation (`resolve_role` still cannot react to a
mid-call auth failure and switch profiles automatically), but at least gives these two stages the
same static-fallback safety net every other API-routed stage already has.

**Implies:** If `MISTRAL_API_KEY` is renewed, `prose`/`codex_summary` still try it first — this is
a fallback, not a repoint. `google_fast` (`gemini-flash-lite-latest`) is a free-tier profile with a
low daily request quota (20/day was hit during Phase 6 testing); a real multi-character run relying
on this fallback should expect to be rate-limited and may need `GOOGLE_API_KEY` upgraded off the
free tier, or `MISTRAL_API_KEY` renewed, before running at scale.

**Status:** Done (config only) — 2026-09-02.

---


