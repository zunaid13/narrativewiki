# docs/handover/PHASE_25.md — the eight structural-flaws pass

**Written retrospectively on 2026-09-24**, during the repository restructure, because the phase
closed without one. It is an index into the real record: `docs/vision/PHASE_25.md` (eight dated
entries, 2026-09-17 → 2026-09-20) and `VISION.md`'s lines for those dates. Its open threads were
picked up by Phase 26, whose handover (`docs/handover/PHASE_26.md`) supersedes this one for
current state.

## 1. What this phase was

The maintainer named eight problems in one message (2026-09-17): scattered config, a website
bad at showing linked data, no per-volume image gallery, bad quote selection, no illustration
thumbnails, sarcasm and lies extracted as fact, verbose prose, and an unmaintained papers
corpus.

## 2. What exists because of it

| Item | Where it landed |
|---|---|
| 1. Config scattered | Generic `--set` override on every stage command (`cli.py`, `USER_GUIDE.md`) |
| 2. Website | `site/mkdocs_wiki.py`, a MkDocs Markdown wiki. The ES5 SPA (`site/static_site.py`) was deleted |
| 3. Image gallery | Per-volume gallery pages; `ingest/images.py` + `img/manifest.json` (CONTRACTS §1.5) |
| 4. Quotes | Narration no longer quoted as dialogue; notability ranking in `synth/assemble.py` |
| 5. Thumbnails | Volume- and first-appearance-chapter-level art-plate matching (`synth/assemble.py` → `site/mkdocs_wiki.py`) |
| 6. Sarcasm / lies | Insincere statements distinguished at extraction and verify |
| 7. Prose verbosity | The sentence cap is enforced by sentence count, not a character-count proxy |
| 8. Papers | `docs/papers/PAPERS.md` + `scripts/papers/fetch_reference_pdfs.py --check` |

## 3. Traps hit

- The 2026-09-20 real-corpus re-run found a live arbitration schema-key mismatch (`decision` vs
  `resolution`) that had been silently failing `graph build`. A green unit suite had not caught
  it; only the live run did.
- Item 5 at first shipped only at volume granularity. Chapter-level matching needed
  `synth/assemble.py` to thread the first-appearance chapter through. Check reachability, not
  just the presence of a code path.

## 4. Reproduce

`wiki site build --series spice-and-wolf` re-renders the whole wiki for $0 (`CLAUDE.md` §2).
Commands for each item are in its entry in `docs/vision/PHASE_25.md`.
