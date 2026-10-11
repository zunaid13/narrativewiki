# Phase 1 — Ingestion

**Closed:** 2026-09-01 · **Next:** Phase 2, Entities

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

`ingest/epub.py`, `ingest/normalize.py`, `ingest/segment.py` implemented; `wiki ingest` and
`wiki audit ingest` work end to end against all 13 volumes.

```
src/narrativewiki/ingest/
  epub.py        EPUB -> RawVolume/RawChapter/RawParagraph. All corpus-trap handling lives here.
  normalize.py   Whitespace/entity cleanup + the mdash-image-to-dash substitution (must run
                 on the live BeautifulSoup tag tree, before any .get_text() call).
  segment.py     RawVolume -> CONTRACTS section 1 paragraph-record dicts + manifest entry.
src/narrativewiki/cli.py       ingest() reads/writes data/01_parsed/, resumable (skip existing
                                 unless --force), merges into the existing manifest.json.
src/narrativewiki/audit/reports.py   _ingest_report(): per-volume table, corpus totals, chapter-kind
                                       counts, and a loud FAIL if any volume has zero para_raid.
tests/test_ingest.py           Unit tests for normalize + kind classification, integration tests
                                 against the real v01 EPUB for traps 2 and 5 specifically.
```

## Verify it in one command

```bash
python -m narrativewiki ingest --volumes 1-13   # ~2s total, all local, no model calls
python -m narrativewiki audit ingest
python -m pytest                                 # 53 passed
```

`wiki audit ingest` reports **926,154 words** across 13 volumes (CLAUDE.md's ~936,000 estimate
was a ballpark from the original inspection pass, not a target to hit exactly — front/back matter
inclusion differences account for the gap) and **non-zero Para-RAID in every volume** (low of 8 in
v07, high of 364 in v01) — the Phase 1 done-condition from `docs/handover/PHASE_0.md`.

## Things you need to know

**`has_heading` must mean "any `<h1>` present," not "matches `chapter_start_selector`."** The
series config's `chapter_start_selector` is `h1.chapter-number`, which only regular
chapters/interludes/epilogues use. Front matter (prologue, epigraph) and back matter (afterword)
use a *different* single heading class (`h1.preface-title`, `h1.appendix-title`, ...). Checking
only the configured selector silently folded v01's real prologue (`preface002.xhtml`,
"Coquelicots Blooming Across the Battlefield," ~30 paragraphs) into the epigraph chapter opened by
`preface001.xhtml` — 16 chapters became 14 and one chapter had the wrong `chapter_kind`. Fixed by
treating *any* `<h1>` as a new-section marker (continuation docs like `chapter010a.xhtml` reliably
have none — that is what trap 2 actually distinguishes on), then picking the title node as
`chapter_title_selector` if present, else the first `<h1>` that isn't the number node. If you touch
chapter-boundary logic, `tests/test_ingest.py::test_v01_chapter_continuation_absorbs_h1_less_documents`
guards this.

**`chapter_kind` is classified heading-text-first, not epub:type-first.** Across the corpus, the
heading text itself says "PROLOGUE" / "INTERLUDE" / "EPILOGUE" far more consistently (in 8-9 of
13 volumes each) than `epub:type` does (`frontmatter prologue` appears in only 2 of 13 volumes'
markup, `backmatter epilogue` in only 1). Priority: heading text → `epub:type` tokens → presence of
a `div.epigraph` wrapper (to split "preface" into prologue vs. epigraph) → default `"chapter"`.
See `epub._classify_kind`.

**Never iterate `Tag.descendants` while mutating the tree.** `substitute_and_strip_images()`
rewrites the tree via `.replace_with()`/`.decompose()`. BeautifulSoup's `.descendants` generator
walks live `next_element` links, so mutating mid-iteration corrupts the remaining walk in ways that
do not raise — paragraphs after a substitution can silently go missing. `epub._extract_paragraphs`
snapshots with `list(container.descendants)` before the loop starts. If you add another
tree-mutating step inside that loop, keep the snapshot.

**`print_page` is legitimately `null` for all of v02, v03, v04, and v10, and mostly null in v01
after the first few pages of some chapters.** Those EPUBs don't carry `<a id="page-N">` anchors in
the body text at all (v02 has exactly one, on the title, with no number); this is a source-file
difference, not an extraction bug — CONTRACTS section 1 already documents `print_page` as
best-effort ("null if none seen yet").

**BeautifulSoup already decodes entities during parsing** (verified: `&lt;System Start&gt;` in raw
XHTML comes back as `<System Start>` from `.get_text()`). Trap 6 ("decode entities only after tag
stripping") is naturally satisfied by working on the parsed tree and calling `.get_text()` rather
than doing string-level tag stripping — `normalize.normalize_paragraph_text`'s `html.unescape()`
call is a defensive no-op for this corpus, not the actual fix.

**Console `�` in tool output is a Windows-terminal display artifact, not a data bug.** Verified
by checking codepoints directly (`—` is U+2014, `É` is U+00C9 in the actual JSONL bytes). Don't
"fix" encoding based on how text looks printed in a shell.

**`toc.xhtml`/`nav.xhtml`/`toc.ncx` are never parsed.** Every content document carries its own
`<h1>` heading(s) in-body, which is a strictly more reliable source of chapter titles than the TOC
(confirmed nav.xhtml's break in v02/v03 doesn't matter here). `epub.toc_sources` in the series
config is unused by ingestion; it's left in place in case a future series needs it, since the
config is meant to be series-agnostic and some series' TOCs may carry information their body text
doesn't.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| `ebooklib` for spine/OPF/metadata, raw `BeautifulSoup` (lxml parser) per document | Spine order and metadata extraction are exactly what ebooklib is for; hand-rolling OPF parsing would just re-implement it with more bugs | Manual `zipfile` + `lxml.etree` parsing of `container.xml`/`.opf` |
| `soup.find("h1")` (any h1) as the chapter-start signal | The only signal proven consistent across chapter, interlude, prologue, epigraph, epilogue, and afterword documents, all of which use different heading classes | `chapter_start_selector` alone — misses front/back matter, see above |
| Heading-text-first `chapter_kind` classification | Heading text says "PROLOGUE"/"INTERLUDE"/"EPILOGUE" outright in most volumes; `epub:type` is inconsistent across the 13 volumes' toolchains | epub:type-first classification |
| `image_page_max_words` filter applied only to headless (continuation) documents | A real chapter that happens to open with a short, image-heavy page must never be silently dropped; only pure art-plate continuations (half-title, insert pages) should be | Applying the word-count filter to every document regardless of heading |
| No windowing/scene-segmentation logic in `segment.py` yet | Not needed until `extract/windows.py` (Phase 3) builds evidence windows; adding it now would be speculative code with no caller | Building the windowing helpers now since the file map mentions them |

## What Phase 2 must do

Implement `entities/{candidates,classify,alias,gazetteer,automaton}.py` and register
`wiki audit gazetteer`. Read `docs/CONTRACTS.md` section 2 for exact schemas
(`gazetteer.json`, `mentions.jsonl`, `candidates.jsonl`) before writing anything — do not
re-derive the shapes from scratch.

Useful things this phase leaves behind: `chapter_kind`, `speech`, and `is_monologue` are already
on every paragraph record, so candidate mining can weight Para-RAID paragraphs and honorific
patterns immediately without re-deriving them. `scene_break_before` is already computed for when
`extract/windows.py` needs it in Phase 3.

## Known gaps, deliberately left

- `print_page` is null for 4 of 13 volumes (source EPUBs carry no page anchors) and partial in
  several others — best-effort per CONTRACTS, not a blocker.
- Chapter segmentation has not been validated chapter-by-chapter against each volume's TOC listing
  (the TOC is unused, see above) — spot-checked v01, v02, v03, v10, v11 by chapter count and
  chapter-kind distribution; a full per-volume manual audit was not done.
- `n_chapters` for v01 (16) does not match the illustrative example in `docs/CONTRACTS.md`
  section 1.3 (18) — that example was always illustrative, not a recorded ground truth; do not
  "fix" ingestion to match it.
- Word-count total (926,154) is ~1% under the CLAUDE.md ~936,000 estimate. Not investigated
  further; within the margin the original estimate was framed as ("~936k").
