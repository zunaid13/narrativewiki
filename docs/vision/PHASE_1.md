# docs/vision/PHASE_1.md — VISION entries for Phase 1 — Ingestion

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-01 — Series-agnostic by construction

**What:** The pipeline must run on another series (Game of Thrones was named) with only a new
`config/series.<name>.yaml`.

**Why:** Stated as a requirement, and it is also a design discipline: it forces series specifics out
of the code and into config, which keeps the modules honest.

**Implies:** No hard-coded character names, factions, volume counts, or EPUB quirks in `src/`. The
86-specific CSS-class drift lives in `config/series.86.yaml` as a pattern list, defaulted sensibly so
a new series usually needs no quirk entries at all.

**Status:** Planned — Phase 1 onward.

---


