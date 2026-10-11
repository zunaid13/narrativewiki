# docs/vision/PHASE_5.md — VISION entries for Phase 5 — Assemble/PPR/explain

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-02 — Page fields are generic per predicate; PPR feeds `mentions_of`; `wiki explain` ships

**What:** Three decisions, landed together as Phase 5: (1) `synth/assemble.py`'s page-model
`fields` are keyed by `predicate.lower()` for every `config/extraction.yaml` attribute, not a
hard-coded name list — CONTRACTS §5's example previously showed `titles`/`nicknames` as if those
were special-cased. (2) `graph/ppr.py`'s Personalized PageRank output populates `mentions_of`
directly — the multi-hop related-entity list this project's own file map already promised, now
wired to something concrete. (3) `wiki explain "<name>" --upto N` is real, not a stub, and prints
the assembled fields, the evidence quotes behind each one, and the PPR-ranked related entities.

**Why:** `config/extraction.yaml`'s own header says "Adding a predicate or attribute here is all
that is needed — rendering is generic." Hard-coding `titles`/`nicknames` as named fields (as
CONTRACTS' original example did) would silently drop any new attribute a future series' config
adds — a direct violation of "series-agnostic by construction" (2026-09-01 entry above). PPR
existed only as a file-map bullet with no consumer; `mentions_of` was an unfilled CONTRACTS field
with no producer. Pairing them was the obvious, and only, use for either one at this phase.

**Implies:** A real-data run of `wiki explain shin --upto 1` surfaced a genuine spoiler leak before
this shipped: `extract/claims.py` merges repeated observations of the same fact into one
`claim_id`, so a claim with `first_vol = 1` can carry a `v02` quote confirming it again later.
`first_vol <= upto_vol` clears the claim for structured rendering, but says nothing about which of
its *individual quotes* are safe to print — the original `explain` printed all of them. Fixed by
adding `graph/temporal.py::evidence_at(claim_ids, vol)`, which filters each quote by its own
para_id volume; `docs/CONTRACTS.md` §4.1 and the module's own docstring now document this as a
fifth sanctioned read, alongside `state_at`/`history_at`/`relations_at`/`all_edges_at`. Phase 6's
`synth/prose.py`, when it cites evidence for the LLM prompt, must call `evidence_at` too — reading
`claims.evidence_json` any other way reproduces the same bug.

`nx.pagerank()` needs scipy, which is not a declared dependency and was not installed; rather than
adding a new heavy dependency for a graph of a few hundred nodes, `graph/ppr.py` hand-rolls
personalized PageRank as a pure-Python power iteration. Revisit only if a much larger graph (a
full 13-volume run across all characters) makes convergence speed an actual problem.

**Status:** Done (Phase 5) — 33 new tests (`test_ppr.py`, `test_synth_assemble.py`, five more in
`test_graph.py` for `relations_at`/`all_edges_at`/`evidence_at`), 155/155 passing. Real run:
`wiki explain shin --upto 1` and `--upto 2` against the actual v01-02 graph, including the
alias-resolution path (`wiki explain "Undertaker"` resolves to `shin`) and the spoiler-leak fix
verified by grepping the `--upto 1` output for `v02` (zero matches, post-fix).

---


