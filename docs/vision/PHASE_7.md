# docs/vision/PHASE_7.md — VISION entries for Phase 7 — Site

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-02 — Site bundle: sparse multi-cutoff shape, extended `links.json`, and a minimal static viewer instead of `web/`

**What:** Three decisions, landed together as Phase 7 (`site/wikify.py`, `site/bundle.py`,
`site/static_site.py`). (1) `data/06_bundle/pages/{id}.json` and `data/06_bundle/codex/*.json`
are both SPARSE multi-cutoff maps — `{"cutoffs": {"<vol>": {...}}}` — carrying only the cutoffs at
which something actually changed; a client resolves a selected volume to the nearest cutoff key
`<=` it, the same walk `synth/cache.py::previous_page` already does on disk. (2) `links.json`'s
value per `entity_id` is `{"route", "canonical", "type"}`, not a bare route string, so a client
can render an affiliation/relationship/PPR-neighbour/codex-member reference's display name without
a second lookup file. (3) `web/` (the planned Vite + React + TS SPA) has no scaffold yet, and
building one is a substantially larger effort than the rest of this phase — asked the user
directly rather than guessing; they chose a dependency-free HTML/CSS/JS viewer
(`site/templates/`) written straight into `dist/site/` by `site/static_site.py`, with no Node/npm
build step, over scaffolding the real SPA this session.

**Why:** (1) mirrors CONTRACTS §5.1's "generated once per cutoff at which the claim set changes"
cache rule at the bundle-file layer, not just at the LLM-call layer — without it, either every
cutoff 1..N would need its own bundle entry (defeating the whole point of the collapse) or the
bundle would silently go stale between characters' actual cutoffs. (2) a compact combined map
costs little and saves the reference viewer (and any future SPA) a second network round trip per
rendered link. (3) `site/bundle.py`'s data contract is independent of what renders it — the bundle
is portable to a real SPA later with zero changes to the Python side, so shipping a working
`wiki site build`/`wiki serve` today was judged more valuable than a half-built React app this
session would not have had time to finish or test properly.

**Implies:** `docs/CONTRACTS.md` §6 now documents the sparse-cutoff shape and the extended
`links.json` shape formally (previously undefined, same as Phase 6's OKF `categories`/
`Appearances` judgment call). `wiki audit links` (moved out of `_PLANNED`) checks every reference
in the bundle resolves against `links.json`. Building the real `web/` SPA later needs no change to
`site/bundle.py` — only to what writes `dist/site/`; see `docs/handover/PHASE_7.md`.

**Status:** Done (Phase 7) — 191 tests pass (21 new); real run against the actual v01-02 data
(`wiki site build --upto 2 --entities "the-spearhead,sixth-sector,juggernaut"`) produced a correct
bundle and a working static site, verified end to end (`wiki audit links`: OK; `wiki serve` +
`curl`: every asset 200; `node --check` on `app.js`).

---


## 2026-09-02 — `codex_summary`'s prompt needed a literal JSON example, not just a field description

**What:** `site/bundle.py::_system_prompt` (the `codex_summary` prompt) now ends with a literal
`Respond with JSON only: {"text": "..."}` line, matching the pattern `entities/classify.py`
already used.

**Why:** Found real-data-testing Phase 7 against `gemini-flash-lite-latest` (`google_fast`,
`codex_summary`'s fallback role): a prompt that only *described* the wanted field ("write N
sentences...") with no literal example, opened with a priming line like `"Location: Sixth
Sector"`, reliably came back as `{"location": "...", "definition": "..."}` instead of
`{"text": "..."}` — `llm/client.py::complete_json`'s repair-retry loop (3 attempts) never
recovered it, because google's `json_mode` (`response_mime_type: application/json`) only enforces
*valid JSON*, never a specific *shape*. `synth/prose.py`'s own prompts have this same latent gap
(no literal example either) but were not observed to fail in Phase 6's real testing — worth
watching, not yet worth changing without its own repro.

**Implies:** `docs/PROMPTS.md` rule #3 now says explicitly: every new `complete_json` prompt's
system message must end with a one-line literal JSON example naming every field, not just a prose
description of them.

**Status:** Done (Phase 7) — verified: the same real evidence that failed 3/3 times before the fix
(`sixth-sector`, `juggernaut`, both cutoffs) succeeded on the first attempt after it.

---


## 2026-09-03 — The reference static viewer needs to look professionally made, not like a debug page

**What:** The dependency-free HTML/CSS/JS viewer built in Phase 7 (`site/templates/`) needs a real
visual design pass — proper typography hierarchy, a Wikipedia-style infobox card on character
pages, badges/pills for relationships and affiliations, card layouts for codex entries, dark-mode
support — while changing nothing about what data it reads or how interlinking is decided (that was
already correct: `site/wikify.py` and `site/bundle.py::build_codex_bundles`/`build_pages_bundle`
already bake real cross-page hyperlinks — character-to-character relationships, codex member/
related lists, wikified prose — into the bundle at build time, per CONTRACTS §6).

**Why:** The user explicitly asked for a wiki that "looks professionally generated with
interlinked references between pages." The interlinking already existed and was already verified
correct (Phase 7's own real-data test); what was missing was that the reference viewer's HTML/CSS
looked like an unstyled debug page rather than a wiki someone would want to read.

**Implies:** `site/templates/style.css` and `index.html.jinja` get a full rewrite (CSS custom
properties for a light/dark palette via `prefers-color-scheme`, sans-serif UI chrome over a serif
reading typeface, card/pill/badge components); `app.js`'s `renderCharacter`/`renderCodex` get
restructured to emit the new markup (an `<aside class="infobox">` for structured fields/
affiliations, a `.relation-list` for relationships, `.pill-list` for member/related/mentions,
`.codex-entry` cards with a type badge). No change to `site/bundle.py`, `site/wikify.py`, or the
bundle JSON contract — this is a rendering-layer change only. Verified visually via headless
Microsoft Edge screenshots (`--headless=new --virtual-time-budget`) against real v01–v02 bundle
data, in both light and dark color schemes, since `chromium-cli`/Playwright were not available in
this environment.

**Status:** Done (Phase 7 addendum).

---


## 2026-09-03 — Both configured API fallbacks were simultaneously dead; Groq added as a working one

**What:** `MISTRAL_API_KEY` (the primary for `codex_summary`/`prose`) had expired (documented
2026-09-02), and `GOOGLE_API_KEY`'s free tier (the configured `fallback:` for those same roles) hit
its daily quota (`RESOURCE_EXHAUSTED`, 2026-09-03) — reproduced live while rebuilding the site for
the visual redesign above. `resolve_role`'s fallback only triggers when a key is *absent* from the
environment (`config.py`'s own docstring), not when the provider rejects a present-but-broken key,
so both roles dead-ended with no working model at all. The user then supplied a `GROQ_API_KEY`
(console.groq.com/keys).

**Why:** Needed a free, low-latency provider that actually works today to finish testing the site
redesign against live-generated (not just cached) content, and to close a real, currently-broken
gap rather than working around it with more cached fixtures.

**Implies:** `config/models.yaml` gained `groq_fast`/`groq_prose` profiles (`provider: openai`,
`base_url: https://api.groq.com/openai/v1` — Groq's API is OpenAI-compatible, same pattern as the
existing Mistral profiles) using Groq's open-weight `gpt-oss-20b`/`120b` models. `codex_summary`,
`prose`, `prose_polish`, and `arbitrate` were repointed to route through Groq as the primary `role:`
until Mistral/Google are fixed (see routing comments for the exact revert). Two real, non-obvious
findings from getting this working, recorded in the profile comments so they aren't rediscovered:
(1) `gpt-oss` is a reasoning model that spends part of `max_tokens` on a hidden reasoning trace
before the actual JSON `content` — a tight budget against a real (long) evidence prompt returns
*empty* content and a 400 "Failed to validate JSON," not a short-but-valid answer, so `max_tokens`
needed padding well above what the visible output requires; (2) this account's free tier caps at
8000 TPM *shared across models in the org*, tight enough that back-to-back codex_summary calls for
large, evidence-heavy entities (a corpus-wide faction like "Eighty-Six") can 429 even after (1) is
fixed — not investigated further since it did not block the actual task at hand.

**Implies (unresolved, flagged not fixed):** `wiki doctor`/`resolve_role`'s "key present = key
works" assumption (already a documented gap from Phase 6/7) caused real wasted time twice more this
session. Also: a local Ollama server answered `/api/tags` successfully during this session, which
contradicts the 2026-09-02 decision to route bulk stages (`claim_extract`, etc.) to Mistral because
"no local Ollama server is reachable" — worth re-checking (a real, larger inference request, not
just a health check) before deciding whether to revert those roles to `local_fast`; deliberately not
done in this session per the user's own instruction not to run large local inferences just to test.

**Status:** Done (config only) — 2026-09-03.
---


