# PLAN 0010 — Multi-cutoff evaluation: more volume breaks vs. long series

**Status:** proposed, opened 2026-09-26. Awaiting maintainer decision on interlock + series.

## Problem

The Gutenberg publication track (Plan 0009) produces **one cutoff per novel** (t=1). With two
volumes, t=1 is the only point where "future" facts exist. Leak@t becomes a single point per book,
not a curve. A reviewer can reject this in one sentence: "You claim leakage varies with context
availability but measured it at exactly one split."

| Metric | Current (2-vol novels) | Needed for publication |
|--------|----------------------|----------------------|
| Cutoffs per novel | 1 | ≥4 (ideally 8+) |
| Future facts at worst cutoff | ~25 (Leagues Part 2) | ≥50 per cell |
| Context window stress | ~65k tokens (fits in 1M) | Corpus too long for full prompt |
| Leak@t data points per book | 1 | Curve with CI bands |

## What the data already shows

Evidence `para_id`s encode chapters: `v02:c03:p0036`. The 173 Part Two claims distribute evenly
across 23 chapters (3–13 claims per chapter). This means chapter-level cutoffs within Part Two
would each have a reasonable number of "future" facts — e.g., a cutoff after chapter 10 would
have ~85 claims ahead of it.

Part One has 23 chapters with 182 claims, similarly distributed.

## Options investigated

### ~~Option A: Chapter-level cutoffs (refactor volume axis)~~  **REJECTED**

This was explicitly rejected in PHASE_31.md §2026-09-25:
> "Rejected: chapter-level cutoffs, because they would need the volume axis re-plumbed through
> every stage and the interlock."

Confirmed by the code audit: it requires changes to **7 core subsystems** (database schema,
temporal reasoning, claim extraction, evidence filtering, artifact paths, futureset, all probe
channels). The `claims.first_vol`, `intervals.vol_start/vol_end`, `edges.vol_start/vol_end`,
`state_at()`, `evidence_at()`, and artifact naming all assume integer volume boundaries.

**This is a multi-week refactor, not a config change.**

### Option B: More `volume_breaks` in series config  **CHEAPEST PATH**

The `source.volume_breaks` mechanism already splits a single EPUB into reading volumes by matching
chapter-title regexes. Currently, Leagues uses `["^PART TWO"]` → 2 volumes.

**Change:** Add more break regexes, one every ~5 chapters, producing ~9 reading volumes from the
same EPUB. The entire pipeline handles this natively:
- `select_reading_volume()` slices chapters
- `discover_volumes()` creates Volume objects
- Extraction assigns `first_vol` per the new boundaries
- `futureset.py`, probe channels, `state_at()` all work unchanged
- **Cost: re-run the extraction pipeline once (~$1.65), zero code changes**

**Concrete config** (Leagues has 23 + ~23 = ~46 chapters total):
```yaml
volume_breaks:
  - "^CHAPTER VI AT FULL STEAM"         # v2 starts at Part One ch 6
  - "^CHAPTER XI ALL BY ELECTRICITY"    # v3 starts at Part One ch 11
  - "^CHAPTER XVI A SUBMARINE FOREST"   # v4 starts at Part One ch 16
  - "^CHAPTER XXI CAPTAIN NEMO"         # v5 starts at Part One ch 21
  - "^PART TWO"                         # v6 starts at Part Two
  - "^CHAPTER VI THE MEDITERRANEAN"     # v7 starts at Part Two ch 6
  - "^CHAPTER XI CACHALOTS"             # v8 starts at Part Two ch 11
  - "^CHAPTER XVI WANT OF AIR"          # v9 starts at Part Two ch 16
```

This gives **8 cutoffs** (t=1 through t=8, with future facts visible at each), evenly spacing
~5–6 chapters per volume. The Leak@t curve has 8 points instead of 1.

**Blocker:** `max_volumes: 2` refuses runs with >2 volumes. The interlock must be lifted (or
carved out for the Gutenberg track) to execute this.

### Option C: Long public-domain series (5+ books)  **IDEAL FOR PAPER**

A multi-book series gives both multiple cutoffs AND genuine long-context stress (total text too
large for a single prompt).

**Candidate ranking:**

1. **Anne of Green Gables (Montgomery)** — 8 books, very strong chronological continuity
   (childhood → adulthood), moderate parametric contamination, easy entity remapping. Best
   narrative structure for testing knowledge accumulation over time.
2. **Tarzan (Burroughs)** — 12+ pre-1929 books, strong continuity, already noted in Plan 0009
   E5. Prose style and racial attitudes are concerns.
3. **Oz (Baum)** — 14 books but loose continuity. Character facts from book 3 may not relate
   to book 10; the "future facts" concept works best when later volumes extend earlier knowledge.
4. **Sherlock Holmes (Doyle)** — Very high contamination (good for measuring leakage, but the
   episodic structure means few "future facts" that a reader of early stories shouldn't know).

**Cost per 5-volume series:** ~$4–5 per condition pass. Three conditions × 2 series ≈ $25–40
total. Well within the $200 cap ($12.79 spent).

### Option D: Report current novels as short-text control  **DO REGARDLESS**

Frame Leagues + Little Women as the "full-text-in-context" control condition where the finding is
"context anchors the model (0–4% leak)." The interesting curve lives on the expanded corpus.

## Recommendation

**Do B first, then C, frame with D:**

1. **Immediate (Option B):** Add 8 volume breaks to Leagues config. Requires lifting
   `max_volumes` to ≥9 for the Gutenberg track. One extraction re-run (~$1.65). Produces an
   8-point Leak@t curve on the same text.
2. **Next (Option C):** Add Anne of Green Gables (5–8 books) as the headline long-context
   corpus. Entity-remap + paraphrase. Run the full probe protocol.
3. **Always (Option D):** Current 2-part novels = "short-text control" in the paper.

## Decisions needed from maintainer

1. **Lift `max_volumes`** to 9+ for the Gutenberg/publication track? The light-novel calibration
   corpora stay at 2. Concrete proposal: add a `gutenberg` profile in `models.yaml` with
   `max_volumes: 10`, or raise the global limit and rely on AGENTS.md to keep LN runs at 2.
2. **Which long series?** I recommend Anne of Green Gables (8 books on Gutenberg). Tarzan is
   the backup. Or: is Option B alone sufficient if the curve is convincing?
3. **Does Option B (volume breaks only, no new text) produce a publishable result**, or is
   Option C (new long series) mandatory?

## Data supporting the decision

Claims per chapter in the existing Leagues extraction:

**Part One (v01):** 182 claims across 23 chapters (1–27 per chapter)
**Part Two (v02):** 173 claims across 23 chapters (2–13 per chapter, median ~8)

With 9 volumes (stride ~5 chapters): each cutoff has ~20–40 future claims, which is adequate
for percentage rates but thin for confidence intervals. A second novel (or the Anne series)
would give the needed sample size.

## Files involved

- `config/series.leagues.yaml` — add volume breaks (Option B)
- `config/models.yaml` — lift `max_volumes` (both options)
- `src/narrativewiki/llm/client.py` — `_enforce_frontier_scope()` may need a profile check
- No code changes needed for Option B (the pipeline handles multi-volume natively)
- Option C: new series config, Gutenberg downloads, decontamination pipeline run

## Review and corrections — 2026-09-26 (Claude, checked against the repo)

The direction holds: B for a within-book curve, C as the headline, D for framing. These specifics
were wrong or incomplete:

1. **Two of the eight break regexes match nothing.** Part Two's chapter VI is "THE GRECIAN
   ARCHIPELAGO" and XI is "THE SARGASSO SEA". Use `^CHAPTER VII THE MEDITERRANEAN` and
   `^CHAPTER XII CACHALOTS`. (`select_reading_volume` raises on an unmatched break rather than
   failing silently, so this would have been caught, but the config as written does not run.)
2. **Claim counts:** across all claim files (window, scene, infobox, backstory) Part One has 193
   claims over 23 chapters (1–28 each) and Part Two 182 (2–13 each). 173 is the graph's
   *future-fact* count after merging, a different number.
3. **"Zero code changes" holds for the pipeline, not the evaluation.** A new split renumbers
   every `para_id`. The E3 fact file (`docs/eval/parametric/leagues.yaml`) cites `v02:…` ids, and
   `future`/`control` are hard-wired to Part Two/Part One. Needed: key gold facts by chapter
   title so first_vol is computed per split, and have both page probes take t. Run it as a
   **new series id** (`leagues9`), so the 2-volume E2/E3 results stay reproducible.
4. **Cost is not "one re-run, ~$1.65".** A new split changes every para_id and window, so the
   cache misses almost everywhere. The infobox/backstory passes run per character-volume, and
   synthesis per cutoff, both scaling with the volume count. The measured 2-volume E2 was $1.13;
   expect **$2–4 per condition** at 9 volumes.
5. **Option A's goal is reachable through B.** `volume_breaks` can sit at every chapter, which is
   chapter-granularity cutoffs with no schema refactor; cost scales with the number of cutoffs
   (synthesis). The refactor is only needed for sub-chapter cutoffs.
6. **B does not answer the long-context critique.** At t=8 the context is still ≈90k tokens, so
   the E3 anchoring effect persists. B fixes only the single-point problem. Its 8 points come
   from one book and are correlated, so intervals must be clustered by fact/character. And E2
   measured the gated pipeline at 0/25, so B's curve for the pipeline is likely flat zero. It
   is informative mainly for the ungated baselines.
7. **Anne: six public-domain books on Project Gutenberg, not eight.** *Anne of Windy Poplars*
   (1936) and *Anne of Ingleside* (1939) are neither. Contamination is **high**, not moderate
   (among the most-read novels in English). The six are downloaded (`config/series.anne.yaml`).
   Two of them (#544, #3796) put ~12 chapters in one XHTML file, which needs the new
   `epub.split_within_documents` (same gap as *Pride and Prejudice*).
8. **Interlock carve-out needs no new profile.** Routing is global, not per series, so a
   `gutenberg` profile would need per-series routing that does not exist. Instead,
   `--set models.profiles.vertex_flash.max_volumes=N` raises it for one CLI process;
   `models.yaml` keeps 2, so the light-novel corpora stay capped mechanically. Caveat:
   `load_settings` is cached per process, so in a script the override persists for the rest
   of that process.
9. Spend is stale: lifetime **$14.71**, not $12.79.

**Decisions as taken (maintainer asleep; these follow the maintainer's own 2026-09-26 message
recommending a 5+ volume headline series):** (1) per-run `--set` carve-out, `models.yaml`
untouched; (2) Anne, the six public-domain books; (3) B alone is not publishable for the
long-context claim. C is the headline, and B is a cheap within-book curve and a test of the
machinery.
