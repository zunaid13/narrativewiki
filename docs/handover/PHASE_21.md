# Phase 21 Handover — Cross-entity pages + evaluation (COMPLETE, all 4 parts)

**Status:** All four deliverables shipped and verified against a live corpus run (Spice and Wolf
v1-2). Full test suite: 470 tests, all green.

Phase 21 was originally scoped in `docs/vision/PHASE_17.md`'s 2026-09-04 entry as "cross-entity
pages + evaluation," split into its own file (`docs/vision/PHASE_21.md`) because it was itself
four independent deliverables large enough to span several sessions. Part 1 shipped in an earlier
session; parts 2-4 shipped in this one. This handover covers all four so a cold contributor never
has to reconstruct the whole arc from `LOG.md` scrollback.

---

## What exists now

### Part 1 — Relationship pages (`data/06_bundle/relationships/<a>--<b>.json`)

Pair-scoped CHARACTER-CHARACTER pages: relation history (`graph/temporal.py::relations_between`/
`relation_history_between`) + shared scenes (`graph/events.py::shared_events_at`). Deterministic,
no LLM. `/relationships/<a>/<b>` route in `app.js`, linked from every character page's
Relationships card. `wiki audit relationships` is its dedicated spoiler-safety report.
CONTRACTS §6.4. See `LOG.md`'s 2026-09-08 "part 1 of 4" entry and `docs/vision/PHASE_21.md`'s
first entry for the full scope-cut rationale (population = pairs with a relation edge only, no
LLM summary, `graph/ppr.py` untouched).

### Part 2 — Faction codex enrichment (`codex/factions.json`'s new `key_events` field)

A FACTION codex entry gains `key_events`: scenes where >= 2 of its current `members` co-appear
(`graph/events.py::group_events_at`, generalizing part 1's pair-based reader to an arbitrary
member set). Config-gated per codex `kind` (`codex_pages.factions.max_key_events: 5` in
`config/extraction.yaml`) rather than hard-coded — `places`/`tech` entries stay byte-identical to
their pre-Phase-21-part-2 shape, including their `_state_hash` cache key, so no LLM regeneration
was wasted on kinds that gain nothing from this field. CONTRACTS §6.1. Rationale for NOT adding
faction-to-faction relations or roster-departure history: see `docs/vision/PHASE_21.md`'s part 2
entry — both are real, bigger, separately-scoped changes (a new relation predicate + extraction
pass for the first; closing `AFFILIATED_WITH` intervals, which `graph/temporal.py::relations_at`'s
own docstring already flags as an unclosed gap, for the second).

### Part 3 — Per-volume timeline pages (`data/06_bundle/timeline/v{NN}.json`)

A chapter-by-chapter recap of one volume's own events (`graph/events.py::events_in_volume` — new:
`WHERE vol = ?`, distinct from `events_at`'s cumulative `WHERE vol_start <= ?`). Unlike every
other `data/06_bundle/` file, this needs **no sparse-cutoff/state-hash machinery at all**: an
event's `vol_start` always equals `vol` (CONTRACTS §4b.1), so a volume's timeline is permanently
fixed the moment `wiki events-build` runs. `/timeline` (volume picker, gated by the READER's own
slider position, not the bundle's `--upto`) and `/timeline/<vol>` routes in `app.js`. Each event
card now also renders `state_changes` — the first surface anywhere in the viewer to show raw
`event_claims` `kind="state_change"` rows directly (previously only consumed, paraphrased, by
Chronology prose). `wiki audit links` extended with link + same-volume + `index.json` agreement
checks for this file (no dedicated report — folded into the existing "links" report, matching how
part 2's `key_events` checks were added, since there's no per-codex-file report the way
relationships gets one). CONTRACTS §6.5.

**A real, pre-existing bug was found and fixed while building this part's live-UI check** (not
introduced by it): `app.js::nameFor(null)` rendered the literal text "null" for a quote whose
speaker scene extraction never resolved a speaker for. This was already reachable through every
earlier caller of the shared `renderSceneCard` (relationship shared_scenes, faction key_events) —
the timeline page's DOM-stub check just happened to be the first live verification to hit a real
unresolved-speaker quote. One-line fix: `nameFor` now falls back to `"Unknown"`.

### Part 4 — Evaluation harness (`wiki audit eval`)

Heading recall, fact recall, and citation entailment against hand-transcribed gold data
(`docs/eval/gold/<series_id>/*.yaml`) from three real reference-wiki pages. New `eval/gold.py`
module (pure functions: `load_gold`, `score_heading_recall`, `score_fact_recall`,
`score_citation_entailment`) called by a new `audit/reports.py::_eval_report`
(`@register("eval", "wiki synthesize")` — no new CLI command). CONTRACTS §8.

Gold data for `spice-and-wolf`: `holo.yaml`, `kraft-lawrence.yaml`, `norah-arendt.yaml`,
transcribed from `spiceandwolf.fandom.com`. **Every gold fact carries `in_scope: true/false`** —
this is the single most important design decision in this part: a real reference wiki describes
the WHOLE series, but this project's wiki at a given cutoff is CORRECTLY supposed to omit anything
revealed later (CLAUDE.md #1). Scoring recall against an out-of-scope fact (e.g. Holo and
Lawrence's eventual marriage, which belongs to the sequel series) would penalize correct spoiler
suppression — exactly backwards. `docs/vision/PHASE_21.md`'s part 4 entry has the full list of
scope cuts and the reasoning behind each.

Both recall metrics are **lexical keyword-overlap heuristics, not an LLM judge** — deliberate,
extending CLAUDE.md §2's "local first, no wasted call" discipline to evaluation itself. The report
always prints the per-fact/per-heading verdict, not just a percentage, so a human catches false
negatives by eye (a real one was found and documented: several "not recalled" facts about Norah
Arendt — her tailor dream, her sheepdog Enek, her Church background — are genuinely present in
`data/05_pages/norah-arendt/v02.json`, just phrased differently than the gold fact's wording).

---

## Known gaps (for a future session)

1. **`chronology`'s citation entailment doesn't examine `beat_summary` provenance.** The prose is
   actually grounded in each event's `beat_summary` (Phase 19's un-gated paraphrase field,
   CONTRACTS §4b.2), but `score_citation_entailment` only looks at `prose.chronology.evidence`
   (event_claims para_ids, a bonus collection, not the real source) — Norah Arendt's chronology
   scored "0 cited paragraphs" / "weak overlap" despite being well-grounded. Fixing this properly
   means either changing what `generate_chronology` records as `evidence`, or teaching
   `score_citation_entailment` to also fetch `events_in_volume`'s `beat_summary` fields for
   `source: "events"` sections — a real design question, not a quick patch, deliberately left open.
2. **Only 3 characters have gold data**, all from `spice-and-wolf`. Extending coverage (more
   characters, or a second series once one exists) or tuning the lexical-overlap thresholds
   (`eval/gold.py`'s `_keywords`/found-threshold constants) is real future work but not required
   for Phase 21's own completion — the harness itself is the deliverable, not a specific score.
3. **No faction-to-faction relations, no roster-departure history** (part 2's scope cuts) —
   `AFFILIATED_WITH` intervals never close (a `graph/temporal.py`-level gap predating this phase,
   documented in `relations_at`'s own docstring), and no relation predicate has FACTION as its
   subject type at all. Both are real, bigger changes than "faction page enrichment" implied.
4. **`graph/ppr.py` untouched across all four parts.** The original vision entry's "PPR gets
   repointed at per-section retrieval" turned out not to be needed by any of relationship pages,
   faction key events, timelines, or the eval harness — all four used direct, cutoff-filtered
   queries instead. Revisit only if a future feature actually needs multi-hop retrieval.
5. **WebFetch of `fandom.com` returned HTTP 402 in this sandbox** (a bot/paywall gate) — gold data
   was transcribed from WebSearch results against the same pages instead of one full-page fetch.
   Noted in each gold YAML's own header comment; re-verify against a full page fetch if that
   restriction ever lifts, in case anything was missed.

---

## Reproducing the live verification

```
PYTHONPATH=src python -m narrativewiki.cli site build --series spice-and-wolf --upto 2
PYTHONPATH=src python -m narrativewiki.cli audit links --series spice-and-wolf
PYTHONPATH=src python -m narrativewiki.cli audit eval --series spice-and-wolf
PYTHONPATH=src python -m narrativewiki.cli serve --series spice-and-wolf --port 8099
```

(`PYTHONPATH=src` is still required on this machine — its global `pip install -e .` points at a
different checkout, `Gemini AntiGravity RAG+TKG pipeline`, an unresolved cross-session issue
flagged since `docs/handover/PHASE_20.md`, not a Phase 21 regression.)

`python -m pytest` — 470 tests, all green.

---

## What's next

Phase 21 is complete. `docs/vision/PHASE_17.md`'s original Phases 17-21 roadmap ("fandom-grade
depth: the ceiling is the ontology, not the model") is now fully delivered. Candidate next work,
none yet scoped as a phase:

- Extend the evaluation harness's gold-data coverage (more characters, tune the lexical
  thresholds, or fix the `chronology` entailment gap above).
- A `web/` SPA to replace `site/templates/`'s dependency-free viewer (CLAUDE.md's file map already
  flags this as "not scaffolded yet").
- Resolve the OpenRouter free-tier routing situation (flagged since Phase 20) if API-quality prose
  without local Ollama ever becomes a priority.
- Extend to the full 13-volume `86` corpus, or a second calibration series, now that Phases 17-21
  have all been built and verified against the 2-volume testing scope.
