# docs/vision/PHASE_0.md — VISION entries for Phase 0 — Foundation (founding vision)

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-01 — Initial vision: spoiler-scoped character wiki from a novel series

**What:** Given a directory of EPUB volumes for a single series, produce a browsable wiki with one
page per character containing: canonical name, age, gender, affiliations, titles, nicknames,
relationships, background and personality. A tab at the top of the site selects "I have read up to
Volume N" and every page re-renders to that spoiler boundary.

**Why:** Reading a long series (86—EIGHTY-SIX is 13 volumes / ~936k words) means forgetting who
people are, but every existing wiki spoils the ending on page one. The volume boundary is the whole
point of the product; without it this is just another wiki.

**Implies:** Facts cannot be stored as flat strings. Every fact needs the volume that revealed it,
and rendering must filter *before* generation, not after.

**Status:** In progress — Phases 0–8.

---


## 2026-09-01 — Hybrid local + API model routing

**What:** All high-volume work (entity classification, claim extraction) runs on a local
Qwen2.5-14B-Instruct via Ollama on a 16 GB RTX 5070 Ti. A switchable API provider (Anthropic /
Gemini / OpenAI / OpenRouter) is used only for final prose on major characters and for arbitrating
same-volume contradictions. Providers are swappable from `config/models.yaml` with no code change.

**Why:** The corpus is ~1.25M tokens; extraction touches it several times over. Paying an API for
that is wasteful when a 14B model is adequate for structured extraction. Final prose is where model
quality is actually visible to the reader, so that is where API tokens are worth spending.

**Implies:** A single `llm/client.py` abstraction with provider adapters, a disk cache keyed on
prompt hash, per-stage routing config, and budget accounting. The pipeline must run end to end with
no API key at all, just with weaker prose.

**Status:** Planned — Phase 0 (client) onward.

---


## 2026-09-01 — Iterative delivery with per-phase auditable output

**What:** The project is built in 9 phases (0–8). Each phase ends with an inspectable artifact and a
`wiki audit <stage>` report, plus a handover document.

**Why:** The user wants to audit each stage rather than receive one opaque deliverable, and wants a
cold contributor to be able to pick up mid-project.

**Implies:** Every stage writes its intermediate output to `data/NN_<stage>/` in a readable format
(JSONL/JSON), never only to memory or a database blob. `audit/reports.py` grows one report per phase.

**Status:** In progress.

---


