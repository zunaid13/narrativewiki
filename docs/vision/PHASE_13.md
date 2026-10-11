# docs/vision/PHASE_13.md — VISION entries for Phase 13 — Config-driven page outline

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-04 — Config-driven page outline (closed section vocabulary)

**What:** The six-phase redesign plan (`docs/vision/PHASE_10.md`, 2026-09-03) named Phase 13
next: replace the two hand-synced hardcoded section templates — `site/okf.py`'s `render_markdown`
(fixed Python calls: Overview, Affiliations, Relationships, Background, Personality, Appearances,
in that literal order) and `site/templates/app.js`'s `renderCharacter` (the same sections as
separately hand-written HTML string literals) — with one declared, closed vocabulary both read.
A new `page_outline` block in `config/extraction.yaml`, dict-of-dicts shaped like `attributes`/
`relations`/`traits` (so the existing per-series `_deep_merge` overlay already handles it), names
every CHARACTER page section: `order`, `kind` (`fields` | `affiliations` | `relationships` |
`prose` | `derived`), `title`, and — for `kind: prose` — `traits`/`min_sentences`/`max_sentences`/
`subject`/`source`. `Settings.page_outline` (new property) exposes it sorted by `order`.

**Why:** Today a person adding or reordering a page section has to edit both files by hand with
nothing enforcing that they still match — and in fact they already didn't: `app.js`'s body order
(Background, Personality, Relationships) had drifted from `okf.py`'s (Relationships, Background,
Personality) with no test catching it. This also directly unblocks the depth programme recorded
in `docs/vision/PHASE_17.md`: Phase 20 (outline-driven multi-section pages) and the per-series
schema overlay's "no series concept in `src/`" rule both assume the section list already lives in
config, not in either renderer.

**Implies:** `synth/prose.py` is folded into this phase even though the six-phase paragraph names
only `assemble.py`/`okf.py`/`app.js` — `assemble.py`'s prose-dict keys and `prose.py`'s generation
loop are the same contract, and generalizing one without the other would leave any future
config-declared section permanently `null`. `synth/assemble.py`'s `"prose": {"background": None,
"personality": None}` literal becomes one `None` per configured `kind: prose` section key.
`site/bundle.py`'s `index.json` gains a `sections` key (mirroring the existing `field_labels`) so
`app.js` never hard-codes a section title either. `cli.py`'s `step()`/`synthesize()` prose-written
check and `audit/reports.py`'s `_pages_report`/`_links_report` hardcoded `("background",
"personality")` tuples are generalized to the same config-driven list, so a future series-specific
prose section is audited and link-checked automatically. Scope explicitly excludes Phase 20's
per-section graph retrieval and evidence-scaled length budgets — this phase keeps today's
trait-predicate-grouping retrieval and fixed sentence bounds, only declaring the section *list*
itself in config.

**Status:** Done (Phase 13). Full details, decisions taken/rejected, and what Phase 14/20 needs:
`docs/handover/PHASE_13.md`.
