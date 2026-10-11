# Phase 25 — Eight structural flaws (config, site, images, quotes, sarcasm, prose, papers)

Distinct from Phase 24's leak-channel research programme: this phase is a maintainer-driven pass
fixing eight named problems with the shipped pipeline and its output, not a new measurement.
Scope discipline per the standing rule (see `tests/testing scope` memory): spice-and-wolf only,
volumes 1-2, throughout. **86 is retired from active use entirely as of 2026-09-17** — not
deprioritized, not a fallback. The series after spice-and-wolf is complete is Overlord, never 86.

## 2026-09-17 — Scope and requirements

The user named eight problems in one message:
1. Config is scattered — a "slight change" needs multiple files/lines edited.
2. The generated website is bad at showing multi-linked, hyper-referenced data.
3. Per-volume images need their own browsable gallery page.
4. Quote selection is bad (the feature idea is fine, the execution isn't).
5. Character thumbnails should come from novel illustrations where identifiable.
6. Sarcasm/lies aren't detected — claims get extracted from non-literal statements as fact.
7. Backstory/appearance/personality prose is too verbose, with unrelated detail bleeding in.
8. The research-paper corpus (54 PDFs) needs a maintained doc: applied / failed / reference /
   unread, with a documented naming convention and a working download/verification script.

Full design (data measured against the real spice-and-wolf corpus, literature grounding for #6,
file-level implementation plan) is in the approved plan at conversation time; the durable record
of *why* lives here and in the handover doc once each part lands. Sequencing chosen so the
pipeline is re-run once, not six times: config/papers (no re-run) -> image capture at ingest ->
quotes+sarcasm (shared re-extraction, since both need the `speech` channel already computed at
ingest and discarded everywhere downstream) -> prose -> the MkDocs wiki emitter -> attribution/
gallery/thumbnails (needs both the image manifest and the emitter).

**Mid-flight correction (same day):** the user interrupted implementation to sharpen the series
scope (86 retired entirely, not just deprioritized; Overlord named as the next series after
spice-and-wolf) and to ask for an EPUB-format normalization wrapper for onboarding a second
series' input without hand-adapting `ingest/epub.py` per series. The wrapper is explicitly
deferred by the user's own sequencing ("once [spice and wolf] is successful for entire project,
then use overlord") — a real, named TODO for when Overlord onboarding starts, not something to
build speculatively against a series whose EPUB this project has never seen. See the
`testing-scope-two-volumes` memory for the full record of this correction.

## 2026-09-17 — Part 1 shipped: generic `--set` config override

`src/narrativewiki/config.py::parse_set_override`/`apply_set_overrides` — `--set
<root>.<key>[.<key>...]=<value>` (root: `series`/`models`/`extraction`), mirroring the existing
`--model` override contract exactly (mutate `Settings` in place via the existing `_deep_merge`,
return notes for the CLI to print, same repeat-application no-op check `run-all`/`step` rely on).
Wired into the single `_settings()` funnel in `cli.py` and every command that reads config for its
own behaviour (not just the ones that already took `--model`): `status`, `explain`,
`events-build`, `audit`, plus all ten `--model`-taking commands, `run-all` and `step` propagating
it to every delegated sub-command.

Dead config wired up in the same pass: `--upto`'s hardcoded-`1` default in five commands now falls
through `_resolve_upto()` to `series.<id>.yaml`'s `site.default_upto`; `--min-mentions` no longer
shadows `entities.min_mentions`; the 86-specific "~936,000 words" string in `audit ingest` moved to
a new `series.expected_words` key (only set on `series.86.yaml`, so a series with no known total
gets no false-precision note). `paths.py`'s stage-key -> directory-name mapping, previously written
twice (module scope and `set_active_series`), now builds both from one `_STAGE_SUFFIXES` dict.
`DEFAULT_SERIES` (the env-var-driven fallback, `"86"`) is now defined once in `paths.py`;
`config.py` reads it instead of recomputing the identical thing. `site.title`/`subtitle`/
`volume_labels_from_epub` are deliberately left unwired here — they are site-rendering concerns
that belong with the MkDocs emitter (item 2), not the soon-to-be-deleted `static_site.py`.

Separately: `cli.py::_settings` now defaults an omitted `--series` to `spice-and-wolf`
(`_ACTIVE_SERIES_DEFAULT`) rather than falling through to `config.DEFAULT_SERIES` ("86") — the
mid-flight scope correction above. `config.DEFAULT_SERIES`/`paths.DEFAULT_SERIES` are left at
`"86"` on purpose: that constant names only which series owns the *unsegmented* `data/`/`dist/`
directory the original 86 corpus already lives in, a distinct and narrower fact from "which series
to use," and every CLI command now always passes an explicit series id, so that legacy fact is
unreachable through normal use.

898 tests passing (net +47 across sessions this file's history spans; +18 of those are this part's
own `--set`/`--upto`/`--min-mentions` coverage in `tests/test_config.py`). Six test files' stale
`_settings` monkeypatch lambdas widened to accept the new `set_` kwarg; two `_FakeSettings` test
doubles gained a bare `.series` dict so `_resolve_upto` doesn't crash against them.

## 2026-09-17 — Part 8 shipped: `docs/PAPERS.md` and a fetch script that matches the disk

Commit `497087f` renamed all 54 PDFs from `{arxiv_id}.pdf` to `{Paper Title}.pdf` and flipped
`.gitignore` to track them, but never updated `docs/fetch_reference_pdfs.py`, which still checked
`OUT_DIR / f"{paper_id}.pdf"` for existence — a re-run would have silently re-downloaded all 51
under the old arxiv-id names, doubling the corpus. Fixed: `find_existing(title)` matches by a
normalized (letters+digits, lowercased) key against whatever is actually on disk, so a human's
title-casing touch-up during the original rename doesn't cause a false "not found"; a genuinely
new paper still gets the documented mechanical name (`title_to_filename`) as its target.
`write_manifest`'s PDF column now shows the real filename with a working relative link (fixed a
Windows-backslash-in-markdown-link bug caught in the same pass); the stale "gitignored" sentence
is gone. New `check_consistency()` (wired into `--check`) verifies both directions: every `PAPERS`
entry has a file on disk, and every disk PDF is both claimed by a `PAPERS` entry and documented as
a row in `docs/PAPERS.md` — this is what keeps the two files from drifting apart again.

Three byte-identical duplicate PDFs deleted (`Living the Novel ... (v1).pdf` and `(v1_1).pdf`,
`World Narrative Model ... (v2).pdf` — confirmed via `sha256sum` before removal), leaving 51 files
for 51 `PAPERS` entries, 1:1.

`docs/PAPERS.md` (new, hand-maintained, filename-keyed) carries the axis the fetch script never
tracked: **Applied** (implemented in a named module — 4 papers: MiniCheck, BGE-M3, STORM's heading
recall, ALCE's citation entailment), **Reference** (cited for a decision/comparison/positioning,
not implemented — the remaining 47), and **Failed** (implemented, then measured worse and
removed — none currently; the several internal mechanisms that *did* fail and get replaced,
recorded in `NARRATIVEWIKI_CAPABILITY_REFERENCE.md` §4.1, are each attributed to this project's
own design decisions, not to a cited paper's method itself failing — the doc says so explicitly
rather than force a label that doesn't fit). Naming convention (title, `:` -> ` - `, version
suffix only when two versions are both kept) written down for the first time; established by
`497087f` but never documented until now.

`check_consistency()` verified clean (0 problems) against the real 51-paper corpus, run offline
against arXiv-API metadata fetched via `curl` (this sandbox's `urllib` gets HTTP 406 from
`export.arxiv.org` where `curl` with the identical User-Agent gets 200 — an environment TLS/HTTP
fingerprinting quirk unrelated to the script's own logic, not chased further here).

## 2026-09-17 — Part 2 shipped: MkDocs Markdown wiki replaces the ES5 SPA

`site/static_site.py` (58 lines) and `site/templates/{app.js,style.css,index.html.jinja}` (808 +
449 + 39 lines) deleted. New `site/mkdocs_wiki.py` consumes the SAME in-memory bundle dicts
`cli.py::site_build` already builds this run (`pages_bundle`, `codex_bundles`,
`relationship_bundles`, `timeline_bundles`, `index_doc`) — `site/bundle.py` and `data/06_bundle/`
are completely unchanged; the JSON bundle stays the `codex_summary` cache and `wiki audit links`'s
target, not an intermediate this module re-parses. Writes `dist/<series>/wiki/v{NN}/` per cutoff
volume 1..upto (character pages via `site/okf.py::render_markdown`, now `link_depth`/`thumbnail`-
aware; codex/relationship/timeline pages new in `mkdocs_wiki.py`), plus a generated
`dist/<series>/mkdocs.yml` (docs/CONTRACTS.md §6b, new).

The sparse-multi-cutoff resolution rule (§6.2's client-side "nearest key `<=` volume") that used
to live in `app.js` now lives once, centrally, in `resolve_cutoff` — flagged in the plan as the
single highest-risk line in the whole emitter (get the `<=` wrong and a future cutoff's snapshot
silently reaches an earlier cutoff dir with nothing else positioned to notice) and guarded by a
new `tests/test_spoiler_leak.py` test. `href(route, depth)`/`_relativize(md, depth)` are the pure
functions that turn already-wikified absolute routes (`[text](/route)`, baked in by
`site/wikify.py` before this module ever sees a page dict) into paths relative to the emitting
page — both covered directly in `test_spoiler_leak.py` and `tests/test_wiki_emit.py` (new,
replacing the deleted `tests/test_site_static.py`).

`wiki audit links` extended to walk the emitted `.md` tree: every link must resolve to a real file
and stay inside its own cutoff directory (or the shared `img/` dir the images work will add) —
verified against the real spice-and-wolf output (60 emitted pages, 0 broken links).

Real corpus verification (`-s spice-and-wolf --upto 2`, no `--force`, reused the already-cached
codex summaries — zero new LLM calls): 14 character pages, 3 codex pages (factions/places/tech),
19 relationship pages, 2 timeline pages, all cross-linked with real working relative Markdown
links (spot-checked: Holo's Affiliations/Relationships sections, a faction codex entry's wikified
summary and `key_events`, a relationship pair's `shared_scenes`). `pip install -e ".[wiki]"` +
`wiki site build --html` + `wiki serve` verified end to end: a real Material site with working
search, one nav section per cutoff volume.

One real design correction made live: the first `mkdocs.yml` (`docs_dir: .`, config file inside
its own docs tree) was rejected by mkdocs 1.6/Material 9 ("`docs_dir` should not be the parent
directory of the config file") — moved `mkdocs.yml` to `dist/<series>/`, a sibling of
`dist/<series>/wiki/` (`docs_dir: wiki`), rather than inside it. `paths.py` gained
`wiki_cutoff_dir`/`wiki_html_dir`/`wiki_mkdocs_yml` accessors (not module globals, so each follows
`set_active_series()`); `SITE_DIR` repointed `dist/<series>/site/` -> `dist/<series>/wiki/` in
both copies. Dead `WEB_DIR` constant (the never-scaffolded Vite SPA `web/`) removed along with the
`web/` row in CLAUDE.md's file map — MkDocs supersedes that plan.

915 tests passing (+17 from this part). `pyproject.toml` gained an optional `wiki` extra
(`mkdocs`, `mkdocs-material`) — `site_build` never imports mkdocs itself; `.md` is always written,
`--html` shells `mkdocs build` only when the extra is present.

## 2026-09-19 — Item 3 shipped: per-volume image gallery; item 5 partially shipped (vol-level thumbnails)

`ingest/epub.py::parse_epub` now captures art-plate illustration bytes it used to discard: the same
no-heading/has-image/low-word-count test that already classifies a spine document as an art plate
(§3 trap 9) now also pulls its `<img>` bytes into a new `RawImage`/`RawVolume.images`, filtering out
anything under 5,000 bytes (`_MIN_ART_BYTES`) so ornament/mdash-replacement images (already handled
upstream, §3 trap 5) don't get captured as illustrations. New `ingest/images.py::write_image_manifest`
(called once at the end of `wiki ingest`, over every volume actually parsed this run) writes bytes to
`data/01_parsed/img/v{NN}/` and a combined `manifest.json` (CONTRACTS §1.5, new). `site/mkdocs_wiki.py`
copies these into the shared `dist/<series>/wiki/img/` once per `site build` and writes a per-cutoff
`vNN/images.md` gallery page (`_render_gallery`, grouped by volume, only rows with `first_vol <= vol`
— no new spoiler channel since the two things that link into the un-cutoff-scoped `img/` dir are
themselves cutoff-filtered before they look).

**Item 5 (character thumbnails) landed at volume granularity, not chapter granularity, and the gap
is real, not a typo.** `ingest/images.py::cover_image_for_entity` was written to prefer an image
whose `chapter_idx` matches a character's first-appearance chapter, but nothing threads a real
`first_chapter_idx` into `site/mkdocs_wiki.py` — that module's own docstring says it consumes only
the bundle dicts `site/bundle.py` already assembled this run, and none of those carry a per-character
first-appearance chapter (`fields` entries have `since_vol`, not `para_id`; the page's own
`mentions_of` has neither). Caught mid-review: the call site was passing a nonexistent
`doc.get("_first_chapter_idx")` (always `None`, dead code — nothing anywhere ever set that key) and
separately calling `render_markdown` twice per character, once with no thumbnail and once with one,
wasting the first render. Both fixed: `mkdocs_wiki.py` now calls `cover_image_for_entity` once, with
`first_chapter_idx=None` explicit and documented, falling through to the volume-level front-matter
tier — every character debuting in the same volume currently shares one thumbnail (or none, for a
volume with no art). Real per-character differentiation needs `synth/assemble.py` (which holds the
`graph.db` connection and each character's cited `para_id`s) to compute and thread a first-appearance
`chapter_idx` through the page bundle — filed as the concrete next step, not built speculatively here.

New coverage: `tests/test_ingest.py` (art-plate capture, tiny-image filtering, chapter_idx
attribution — landed alongside the extraction code, already green before this entry), `tests/
test_images.py` (new — manifest write/rewrite-not-merge/dedup, `cover_image_for_entity`'s three
tiers), `tests/test_wiki_emit.py` (+5 — gallery presence/absence, real file copy into `wiki/img/`,
thumbnail present/absent on a character page). `docs/CONTRACTS.md` §1.5 (new) and §6b amended;
CLAUDE.md file map gained `ingest/images.py`. Zero LLM calls; deterministic throughout.

## 2026-09-19 — Item 5 finished: `synth/assemble.py` threads the first-appearance chapter

Closes the gap the previous entry filed as the concrete next step. `assemble_page` gained
`_first_appearance_chapter_idx(events_conn, entity_id, first_vol)`: reads
`graph/events.py::character_events_at(events_conn, entity_id, first_vol)` (already spoiler-fenced,
already ordered `(vol, chapter_idx, span_index)`) and takes the first row's `chapter_idx` — no new
query, no new evidence, the exact connection `_build_lead`/`_annotated_mentions` were already
holding. Stored on the page dict as `first_chapter_idx` (`docs/CONTRACTS.md` §5). `site/bundle.py`
needed no change — it already spreads the whole page JSON into `cutoffs[str(vol)]`. `site/
mkdocs_wiki.py` now passes `snapshot.get("first_chapter_idx")` into `cover_image_for_entity`
instead of the hard-coded `None`, so its chapter-matching tier is live: a character now gets the
art plate immediately preceding their debut chapter when one exists, falling back to volume
front-matter/first-image only otherwise. A re-run of `wiki synthesize` + `wiki site build` is
needed for existing `data/05_pages/` output to pick up the new field — nothing in the pipeline
does this automatically since unchanged claim sets skip writing a fresh page file
(`synth/cache.py`). New coverage: 3 cases in `tests/test_synth_assemble.py`, 1 end-to-end case in
`tests/test_wiki_emit.py`. Item 5 is now fully shipped. `pytest -q`: 900+ green.

## 2026-09-19 — Items 4 (quotes), 6 (sarcasm/lies), 7 (prose verbosity)

All three root-caused against the real spice-and-wolf v1-2 corpus, not designed blind, following
the same "confirm on real data" discipline as PHASE_24's NLI diagnostic.

**Item 4 (quote quality).** Pulled every quote already extracted for v1-2 from `events.db` and
read them: alongside real dialogue, several were narrator prose the model mistook for a spoken
line ("It was a common technique for buying up a commodity in advance of a higher price." —
Marheit's business exposition, not anyone's quoted speech), and one had a narrator attribution tag
leak into the quote text itself (`"Why do you want me to?" she shot back` extracted verbatim,
tag included). Root cause: `ingest/epub.py`'s per-paragraph `speech` classification
(dialogue/narration/para_raid/machine, CLAUDE.md §3 trap 4) is computed at ingest and read by
nothing downstream (`audit/reports.py`'s stats aside) — exactly the gap this phase's own scope
note named. Fix: `extract/scenes.py::_build_quote` now drops a quote cited from a `speech ==
"narration"` paragraph (a hallucinated attribution, not a verbatim-check failure — the substring
genuinely is in the paragraph, it's just not something anyone said); the extraction prompt now
explicitly says the quote text excludes narrator attribution. Deliberately NOT applied to
epithets/state_changes, which are legitimately narration-sourced by design (the worked example
itself, "the wisewolf smiled," is narration).

**Item 6 (sarcasm/lies).** Spice and Wolf's Holo is built around teasing, boasting, and
suspected lying, so the real corpus is a strong stress test. Checked the polarity distribution
across all 947 v1-2 claims: `presumed`/`denied` are already used (43 of 947) and handle narrator
hedging well ("Lawrence guessed," "was said to," explicit negation) — the existing machinery
(`polarity_prefixed` rendering, arbitration handling) is mature. The actual gap: nothing in either
extraction prompt (`claims.py`, `scenes.py`) ever told the model that a CHARACTER'S OWN sincere-
sounding statement could itself be insincere (a boast, a joke, a lie) — the polarity guidance only
covered secondhand/uncertain narration, never in-character insincerity. Fix: extended both
prompts' polarity instruction to mark such a line `presumed` too (narration cues like "she
teased," "he lied," "in jest" as the signal) — deliberately reuses the existing `Polarity` literal
and downstream handling rather than adding a new schema field or a fourth polarity value, since
the semantics ("not confirmed, take with a grain of salt") already match exactly.

**Item 7 (prose verbosity).** Read Holo's actual generated v2 prose: `appearance` (config cap: 4
sentences) had 5 real sentences; `history` (cap: 12) had 15 — both comfortably under their
`max_sentences * 280`-char validation budget, so both passed silently. The character-count check
was a proxy for a sentence cap, not a real one. User's explicit call on the fix (asked, not
assumed, given real design trade-offs): (1) keep `history` as a narrative chronology, tightened to
major turning points rather than scene-by-scene transaction detail, over reverting to a
background-only bio; (2) replace the char-count proxy with a real sentence-boundary count as the
actual enforced ceiling, over just lowering the chars-per-sentence budget. Implemented both:
`synth/prose.py::_count_sentences` (regex sentence-boundary count) backs `_prose_schema_for`'s
Pydantic validator, which now rejects a response over `max_sentences` directly; only the ceiling
is a hard gate (`min_sentences` stays a prompt instruction — undershooting is a quality nit, not
the runaway-verbosity bug this closes). `_chronology_system_prompt` (shared by `generate_history`
and the older `source: "events"`-dispatched `generate_chronology` path) now explicitly asks for
major turning points and says to omit a scene's incidental logistics (exact sums, side-character
errands, transaction place names) unless the detail IS the turning point.

11 new tests across `tests/test_scenes.py`, `tests/test_extract.py`, `tests/test_synth_prose.py`.
`pytest -q`: 900+ green. A real-corpus re-run (scenes → events-build → graph build → synthesize →
site build, v1-2, $0 OpenRouter free tier) is in progress to confirm the fixes change real output,
not just pass unit tests — a first attempt hit a transient OpenRouter non-JSON response and was
retried; result recorded in the next LOG.md/PHASE_25.md entry once it completes.

## 2026-09-20 — Re-run landed; items 4/6/7 confirmed live; arbitration key-alias fix

Full pipeline finished for v1-2 (scenes, claims, graph, events, pages, site). Along the way,
`graph build` hit a real (not transient) failure: `openai:nex-agi/nex-n2.5-pro:free` returns
`{"decision": ...}` instead of the schema's `{"resolution": ...}` key on some arbitration calls,
and its own repair-retry doesn't reliably self-correct — one case (jakob/RANK,
`20260919T190103-graph_build-v1-2`) returned `decision` on all 3 attempts and exhausted retries,
failing the whole build. Fixed with a `model_validator(mode="before")` key alias on
`ArbitrationDecision` (`graph/contradictions.py`) — accepts `decision` as `resolution` before
Pydantic validation runs, rather than touching the generic `llm/client.py` repair loop that every
other schema also relies on. New test:
`test_arbitration_decision_accepts_decision_key_as_resolution_alias` (`tests/test_graph.py`).
Full writeup and final counts: `LOG.md` 2026-09-20. **Known gap, not fixed this pass:**
`wiki audit links` flags a `may-god` gazetteer noise entity (0 claims either volume, predates this
session) as an unresolved `entity_id` — filed for later, orthogonal to items 4/6/7.
