# docs/vision/PHASE_2.md — VISION entries for Phase 2 — Entities

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-01 — Interlinked pages; characters unique, everything else shared

**What:** Character pages are unique per character and hyperlinked to each other: if character B is
named on character A's page (e.g. "B is A's father" in Relationships), that mention links to B's
page. Non-character entities do **not** get individual pages — factions and organizations share one
codex page, locations and battles share another, technology/Legion terms share a third. Links to
them resolve to an anchor within the relevant codex page.

**Why:** Characters are the product. Shared codex pages keep every hyperlink resolvable (no dead
ends) and keep the link graph dense, without paying synthesis cost for hundreds of minor entities.

**Implies:** The gazetteer must type entities, not just find them. `site/wikify.py` routes a mention
to `/character/<slug>` or `/codex/<kind>#<slug>` based on entity type. Codex entries are one-line
definitions plus first-appearance volume and linked characters — cheap to generate.

**Status:** Planned — Phases 2 and 7.

---


## 2026-09-01 — Aho-Corasick as the retrieval and cost mechanism

**What:** Build one Aho-Corasick automaton over all canonical names and aliases, and index every
mention in the corpus in a single O(n) pass.

**Why:** It serves three needs at once, and it is deterministic and free. It performs the automated
wikification the reference document calls for; it gives alias-aware mention counts for ranking
characters by importance; and — most importantly — it is the token lever. Knowing exactly which
paragraphs name a character means an extraction prompt never contains text irrelevant to its subject.

**Implies:** `entities/automaton.py` is built before any extraction runs. Extraction reads mention
windows, never whole chapters. Alias resolution quality directly bounds recall, so Phase 2 is the
phase to hand-audit.

**Status:** Planned — Phase 2.

---


## 2026-09-02 — EcphoryRAG evaluated and rejected; token strategy stays extraction-time

**What:** EcphoryRAG (arXiv 2510.08958, Oct 2025) was evaluated as a replacement for the
Aho-Corasick + claim-extraction design and **rejected**. Its headline "94% token reduction" is an
*offline indexing* saving obtained by storing only `(id, name, type, description, source_chunk)`
per entity and **not extracting relations at index time at all** — edges are bare co-occurrence
(undirected, unweighted, untyped), and relations are inferred at query time by embedding-space
multi-hop search feeding raw chunks to a generator LLM. Its own Table 1 shows query-time cost
*higher* than vanilla RAG (1.3M vs 848k QT tokens).

**Why rejected:** Three hard mismatches. (1) It has no typed predicates, so it cannot render
Affiliations/Relationships deterministically from graph rows (rule §2). (2) It has no fact-level
provenance or validity intervals — the paper never addresses temporal change or contradiction —
so it cannot support `first_vol`, interval supersession, or the spoiler invariant (§1). (3) It is
a *query-time* architecture; this project is *build-time*, emitting a static site where every page
at every cutoff must already exist. There is no reader query to spend its "strategic query-time
investment" on. Its savings come precisely from skipping the step that is this project's core
deliverable.

**Implies:** No architecture change. `entities/automaton.py` remains the retrieval mechanism —
for a small, closed, fully-processed corpus, exact Aho-Corasick mention indexing gives 100% recall
at zero token cost, which embedding top-k retrieval cannot beat here.

**Status:** Done (decision only) — 2026-09-02. Superseded only if the product ever grows a live
reader-facing question box.

---


