# Phase 13 — Config-driven page outline (closed section vocabulary)

**Status:** Complete · **Started:** 2026-09-04 · **Finished:** 2026-09-04

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## Why this phase exists

The six-phase redesign plan (`docs/vision/PHASE_10.md`, 2026-09-03) named Phase 13 next: replace
the two hand-synced hardcoded section templates — `site/okf.py`'s `render_markdown` (fixed Python
calls: Overview, Affiliations, Relationships, Background, Personality, Appearances) and
`site/templates/app.js`'s `renderCharacter` (the same sections as separately hand-written HTML
string literals) — with one declared, closed vocabulary both read. This was worth doing now, not
later, because it turned out the two files had **already** drifted apart: `app.js`'s body order
was Background → Personality → Relationships while `okf.py`'s was Relationships → Background →
Personality, and nothing caught it. It also directly unblocks the depth programme
(`docs/vision/PHASE_17.md`): Phase 20 (outline-driven multi-section pages) and the per-series
schema overlay rule ("no series concept in `src/`") both assume the section list already lives in
config.

## What exists now

```
config/extraction.yaml
  New `page_outline` block, dict-of-dicts keyed by section (same shape as `attributes`/
  `relations`/`traits`, so the existing per-series `_deep_merge` overlay handles it for free --
  add, override, or `null`-delete one section without repeating the rest). Base taxonomy declares
  six: overview (kind: fields), affiliations (kind: affiliations), relationships (kind:
  relationships), background (kind: prose, traits: [BACKGROUND]), personality (kind: prose,
  traits: [PERSONALITY, MOTIVATION, SKILL, FEAR]), appearances (kind: derived). Each entry has
  `order` (explicit sequencing -- not dict-insertion-order, so a series overlay adding one section
  doesn't depend on where the base dict happens to place it) and `title`. `prose:` block trimmed
  to just `codex_summary`/`forbid_uncited_specifics` -- `background`/`personality`'s sentence
  bounds moved into their `page_outline` entries.

src/narrativewiki/config.py
  Settings.page_outline (new property)  -> list[dict], each entry with its own `key`, sorted by
    `order`. Pattern: `prose_config` (same file). No CLI override exists for this yet, unlike
    `--attr`/`--trait`/`--relation` (Phase 17's schema-tuning work) -- out of scope, not asked for.

src/narrativewiki/synth/assemble.py
  assemble_page()'s `"prose": {"background": None, "personality": None}` literal is now
  `{s["key"]: None for s in settings.page_outline if s["kind"] == "prose"}`. Nothing else changed
  -- fields/affiliations/relationships were already generic.

src/narrativewiki/synth/prose.py
  generate_prose() loops `settings.page_outline` filtered to `kind == "prose"` instead of two
  hardcoded calls; `_PERSONALITY_PREDICATES` constant deleted (the predicate list now lives only
  in config, as each section's own `traits` key). `_system_prompt`/`_generate_one` take the
  section dict instead of a `kind: str`, reading `subject`/`source`/`min_sentences`/
  `max_sentences` from it -- falls back to `f"a short {title.lower()} summary"` / `"facts"` if a
  future section omits `subject`/`source`, so a minimal overlay entry still works without a
  prompt-writing exercise.

src/narrativewiki/site/okf.py
  render_markdown()'s five hardcoded `parts.append(...)` calls became one loop over
  `settings.page_outline`, dispatching on `kind` via new `_section_body()` to the same
  `_overview_lines`/`_affiliation_lines`/`_relationship_lines`/prose-lookup/`_appearances` helpers
  (all kept, just called generically). Each section renders as `## {title}` + its content, in
  declared order.

src/narrativewiki/site/bundle.py
  build_pages_bundle()'s `for kind in ("background", "personality")` wikify loop now iterates
  `settings.page_outline` filtered to `kind == "prose"`. build_index()'s `field_labels` dict
  gained a sibling `"sections"` key: `[{"key", "kind", "title"} for s in settings.page_outline]`
  -- CONTRACTS §6 documents it. This is what lets `app.js` stay generic without a build-time
  template step.

src/narrativewiki/site/templates/app.js
  renderCharacter() iterates `state.index.sections` (falls back to a hardcoded `DEFAULT_SECTIONS`
  matching the base six, for a bundle built by an older `wiki site build` with no `sections` key
  yet -- the same forward-compat concern `field_labels` already has). `kind: fields` and
  `kind: affiliations` render into the existing infobox aside (fields bare, affiliations under an
  `infobox-section` title div -- preserved exactly from the old hardcoded version, including
  fields having NO visible "Overview" label, which was already true before this phase);
  `relationships`, `prose`, and `derived` render into the body, each under an `<h2>{title}</h2>`,
  in declared order. New `appearancesOf(page)` helper mirrors `okf.py::_appearances`'s
  since_vol/vols/history walk client-side. This is what fixed the body-order drift noted above,
  and it also adds an Appearances section to the HTML view for the first time -- previously only
  `okf.py`'s Markdown rendered it. Verified live with a real headless-Edge screenshot (see below),
  not just by reading the diff.

src/narrativewiki/cli.py
  synthesize()'s `if prose["background"] or prose["personality"]:` (the "did this cutoff actually
  generate anything" check, used by both `wiki synthesize` and the `wiki step` it's delegated
  from) is now `if any(prose.values()):`.

src/narrativewiki/audit/reports.py
  _pages_report(): the hardcoded `("background", bg_lengths), ("personality", pe_lengths)` loop
  and the two separate printed "Background prose: ..." / "Personality prose: ..." lines are now
  one loop over `{s["key"]: s for s in settings.page_outline if s["kind"] == "prose"}`, printing
  one line per configured section using its own `title`. Sentence-bound checking (`out_of_bounds`)
  now reads `min_sentences`/`max_sentences` from the section itself instead of a separate
  `prose_cfg` lookup (the config values moved, see `extraction.yaml` above).
  _links_report(): the hardcoded `for kind in ("background", "personality"): entry =
  page["prose"].get(kind)` link-check loop is now `for entry in page.get("prose", {}).values()`
  -- simpler, and doesn't need `settings` at all now.

tests/test_synth_assemble.py, tests/test_synth_prose.py, tests/test_site_okf.py,
tests/test_site_bundle.py
  Each file's `FakeSettings` gained a `page_outline` (or `PAGE_OUTLINE` constant) fixture matching
  its existing minimal `attributes`/`traits`. `test_site_okf.py` gained ONE new test,
  `test_section_order_follows_page_outline_not_a_hardcoded_list`, that swaps in a reordered
  3-section outline and asserts the Markdown output follows it -- the only genuinely new behavior
  this phase needed direct test coverage for (everything else is the same rendering logic, just
  reached via a loop instead of five named calls). `test_site_bundle.py`'s
  `test_build_index_filters_by_cutoff_and_sorts_by_importance` gained one assertion that
  `index["sections"]` matches the fixture's `PAGE_OUTLINE`.

docs/CONTRACTS.md   §5: `prose` documented as "one key per `page_outline` kind: prose section";
  new paragraph documenting the `page_outline` shape itself. §5.2: "Body sections follow
  `page_outline`'s declared order" replacing the fixed list. §6: `index.json`'s table row for
  `sections`.
USER_GUIDE.md       §8 gained a "Adding a whole page section" subsection with a worked Overlord
  `page_outline`+`traits` overlay example, right after the existing `--attr`/`--trait`/`--relation`
  documentation it parallels.
```

## A real environment finding during verification, not a bug

No JS test harness exists in this project — `app.js` is exercised only by `wiki site build` +
manual/browser verification, same as every prior phase. This phase's body-order/Appearances-
section changes were significant enough (not a pure refactor of the JS — the render order visibly
changed) that reading the diff was not enough. No headless browser tool was pre-installed, but
Windows ships Edge; `msedge.exe --headless --disable-gpu --virtual-time-budget=4000 --screenshot=...`
against the running `wiki serve` instance produced a real screenshot of `kraft-lawrence`'s page.
It confirmed: infobox shows Age/Nicknames/Role (fields, no visible label) then an "AFFILIATIONS"
label + pills, exactly as before; body now reads Relationships → Background → Personality →
**Appearances** (new) → "Also connected to", in `page_outline`'s declared order — the drift-fix
and the incidental Appearances addition both visibly correct, not just passing tests.

## Verify it in one command

```bash
python -m pytest            # 307 passed (306 before this phase + 1 new)
```

Live: `wiki synthesize --series spice-and-wolf --upto 2 --force` then `wiki site build --series
spice-and-wolf --upto 2 --force` then `wiki audit pages`/`wiki audit links --series
spice-and-wolf` (both OK) then open `wiki serve --series spice-and-wolf` in a browser.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| `page_outline` is a dict-of-dicts keyed by section (like `attributes`/`relations`/`traits`), not a list | A list is replaced wholesale by `_deep_merge`'s existing rule (`docs/vision/PHASE_17.md`), so a per-series overlay adding ONE section would have to repeat the entire base list. A dict merges key-by-key for free with the exact same mechanism already proven for `attributes` | A `page_outline:` list, matching the order visually |
| `synth/prose.py` was folded into this phase even though the six-phase paragraph names only `assemble.py`/`okf.py`/`app.js` | `assemble.py`'s prose-dict keys and `prose.py`'s generation loop are the same contract -- leaving `prose.py` hardcoded to two calls would mean any future config-declared prose section stayed permanently `null`, a silent bug waiting for Phase 17-21 | Scoping strictly to the three named files and leaving `prose.py`'s hardcode for a later phase |
| Infobox-vs-body placement (`fields`/`affiliations` -> aside; everything else -> body) stays a fixed rule in `app.js`, not a new config field | The six-phase ask was a closed **section** vocabulary, not a full layout DSL; the aside/body split is a page-chrome decision, not part of "what sections exist and what feeds them" | A `placement: infobox\|body` key on every `page_outline` entry |
| No `--attr`-style CLI override for `page_outline` | Not asked for by the six-phase entry; the per-series overlay (already built, Phase 17) covers the actual use case ("Overlord needs an Abilities section") without extra CLI surface | `--section`/`--only-section` flags mirroring `--attr`/`--only` |
| `_generate_one`'s `subject`/`source` fall back to text derived from `title` when a section omits them | A minimal overlay entry (just `traits`+bounds) still produces a working prompt instead of a blank/broken one -- lowers the bar for adding a new prose section later | Requiring `subject`/`source` on every `kind: prose` entry |

## Known gaps, deliberately left for later phases

- **No `--attr`-style CLI override for `page_outline`** (see decision above) — overlay-only for
  now. A future ad-hoc `--section` flag would mirror `apply_schema_overrides`'s shape exactly if
  ever needed.
- **Infobox-vs-body placement is not itself config** (see decision above) — every section beyond
  `fields`/`affiliations` lands in the body. A series wanting a section to render into the aside
  instead would need this extended.
- **Retrieval and length budgets are still per-page-outline-entry, fixed sentence counts** — Phase
  20's "each section gets its own graph retrieval query and an evidence-scaled length budget" is
  explicitly NOT this phase. `page_outline` only declares which trait predicates feed a prose
  section; it does not (yet) let a section query the graph directly or read structured fields.
- Phase 9's still-open finding (Holo's Appearance field near-duplicates), Phase 10's
  Vertex-frontier-profile-still-commented-out gap, and Phase 11's cross-chapter `claim_id` merge
  gap are all untouched — unrelated to this phase.
- **Not a code gap, but worth flagging:** `narrativewiki-pipeline-review.md` (root of the repo) is
  missing from the working tree as of this phase, though nothing in this phase touched it and it
  is still present in `git log` history — likely cleanup from a concurrent session (its content is
  already fully absorbed into `docs/vision/PHASE_10.md`'s six-phase entry). Left alone, not
  restored, per the same "don't touch someone else's in-progress work" precedent
  `docs/handover/PHASE_12.md` already established for a similar concurrent-edit situation.

## What Phase 14/17 needs

`docs/vision/PHASE_17.md`'s depth programme is next in dependency order: **17** value
canonicalization + relation arbitration (the literal STORM editor-named failure modes already
reproduced on this project's own output). Nothing built in Phase 13 blocks it or needs revisiting
for it — `page_outline` is additive infrastructure that Phase 20 (outline-driven multi-section
pages, later in the same programme) will extend with per-section retrieval, not Phase 17. If
Phase 17's canonicalization work ever wants its own page section (unlikely — canonicalization
operates on existing `fields`/`prose` values, not a new one), the mechanism documented here and in
`USER_GUIDE.md` §8 is ready to use without touching `assemble.py`/`prose.py`/`okf.py`/`app.js`
again.
