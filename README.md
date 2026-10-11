# narrativewiki

**Turn a novel series into a character wiki that doesn't spoil it.**

Point this pipeline at a folder of EPUBs for one series. It reads the books, works out who everyone
is, tracks how their facts change from volume to volume, and builds a hyperlinked static wiki with a
tab at the top that says *"I've read up to Volume N."* Move the tab and every page re-renders to what
a reader at that point in the series could actually know.

The working corpus is *Spice and Wolf* volumes 1–2 (the 13-volume *86—EIGHTY-SIX* was the
original reference and is retired), but nothing in the code is specific to either — a new series
is a new file in `config/`.

---

## Why it exists

Long series are hard to keep straight, and every wiki that could help you spoils the ending in the
first paragraph. Character A dies in Volume 5, so their page says "deceased" while you're still
reading Volume 2. The fix isn't to write less; it's to store *when* each fact became true.

## How it works

Every fact is stored as a temporal quadruple — `(subject, predicate, object, vol_start, vol_end)` —
tagged with the volume that revealed it and the passage that supports it. A page at Volume N is built
from the facts valid at N, and the prose is written from that filtered set rather than written first
and censored after. Censoring after leaks: implication survives redaction.

That same structure solves a second problem. When Volume 7 says something that contradicts Volume 2,
that usually isn't an error — it's a character changing. So a conflict *across* volumes closes the
old interval and opens a new one (the page shows the current value with an expandable history), while
a conflict *within* a single volume is treated as an extraction bug, arbitrated, and logged for audit.

```
EPUB ─► ingest ─► entity discovery ─► claim extraction ─► temporal graph ─► synthesis ─► static site
          │             │                    │                  │              │
      deterministic  Aho-Corasick        local Qwen        SQLite + TKG    short prose,
      parsing        mention index       (free, on GPU)    intervals       heavily cached
```

**Architecture:** hybrid temporal GraphRAG — a temporal knowledge graph for the facts and the spoiler
boundary, Personalized PageRank over the entity graph for multi-hop retrieval (so a claim spread
across separate passages can still be assembled), and an LLM only for the final short prose.

**Cost:** an Aho-Corasick automaton over all names and aliases indexes every mention in the corpus in
one linear pass. Extraction then reads only the passages that actually name its subject, so no prompt
ever contains irrelevant text. Structured fields — name, age, gender, affiliations, titles,
nicknames, relationships — are rendered straight from graph rows and cost nothing to generate. Bulk
work runs locally on a 16 GB GPU; API keys are optional and used only to polish prose for major
characters.

## What you get

- **A page per character** — the structured fields above, plus a short evidence-backed background and
  personality, all scoped to your current volume.
- **Real hyperlinks between them.** If B is named on A's page, that name is a link to B's page.
- **Shared codex pages** for everything else: factions and organizations on one, locations and
  battles on another, technology on a third. Every link resolves; nothing is a dead end.
- **A volume tab** that changes the entire site's spoiler boundary instantly.
- **Auditable intermediates.** Every stage writes readable JSON to `data/` and has a
  `wiki audit` report, so you can check the machine's work instead of trusting it.

## Quick start

```bash
# 1. Put your EPUBs in corpus/<series-id>/ — no renaming.
# 2. Optional: cp .env.example .env, then add an API key (GROQ_API_KEY is free and fastest to get).
pip install -e .
ollama pull qwen2.5:14b-instruct-q4_K_M
wiki doctor                      # tells you exactly what's missing
wiki run-all -s spice-and-wolf --upto 2   # the in-scope slice, end to end
wiki serve -s spice-and-wolf               # then open http://localhost:8080
```

`wiki doctor` runs first for a reason: it checks Python, Ollama, the model, your API keys and the
corpus, and prints a readiness table rather than failing three hours into an extraction run.
Every stage's output — the thing to check if you want to audit the machine's work — lives under
`data/0N_<stage>/`; the full path-by-path breakdown is in `USER_GUIDE.md`'s "Where things live"
table.

Full command reference and the order to run things in: **[USER_GUIDE.md](USER_GUIDE.md)**.
Where everything lives (code, docs, scripts, corpus): **[STRUCTURE.md](STRUCTURE.md)**.
Why it's built this way: **[VISION.md](VISION.md)**. What's been built so far: **[LOG.md](LOG.md)**.

## Status

Built iteratively in phases, each ending in something you can inspect. See the top of
`LOG.md` for the current phase.

## Requirements

Python 3.14 · ~10 GB disk for the local model · an NVIDIA GPU with 12 GB+ VRAM for comfortable local
inference (developed against a 16 GB RTX 5070 Ti).
API keys are optional.

## A note on the source texts

`corpus/` holds copyrighted EPUBs and is never written to, never committed, and never redistributed by
this tool. The generated wiki is a derivative reference work for personal use.
