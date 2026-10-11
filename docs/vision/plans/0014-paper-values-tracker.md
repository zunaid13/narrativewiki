# 0014 — Paper values tracker: every number and fact the paper needs, step by step

**Status:** living tracker, opened 2026-09-28. Update the Status column as work moves; never
delete a step, mark it `dropped` with the reason.
**Serves:** the LaTeX paper in [`docs/paper/`](../../paper/) (placeholders) and
[plan 0013](0013-paper-blueprint.md) (what each section must say).
**Companions:** [plan 0012](0012-research-evaluation-data.md) (deliverables D1–D17 this plan
schedules), [`docs/MEASUREMENTS.md`](../../MEASUREMENTS.md) (where every value lands first).

## How to use this file

1. Pick the first step whose **Blocked by** is done. Read its card below.
2. Produce the value with the listed tool, **append a row to `docs/MEASUREMENTS.md`**, then type
   the value into `docs/paper/results.tex` (the key's third argument) with the ledger section in
   its comment. Text placeholders (`\TBD{ID}`) are replaced in the section file named by the ID.
3. Check progress. This reads the table below, so the progress figures are never hand-kept:

   ```
   .venv/Scripts/python.exe scripts/papers/paper_status.py --steps
   ```

   For each step it prints result keys filled / total and text placeholders left. A key or
   placeholder is counted under the **first** step whose pattern matches it; anything matched by
   no step is listed as unassigned (should be none).
4. Change the step's Status here when it is `done` (all its keys filled and its "Done when" met).

Spending rules for every step: $200 hard cap (`lifetime_cap_usd` $185 + billed offset), five
volumes per work, estimate before any billed run, cheapest path first (CLAUDE.md §2). A cost
column saying "estimate first" means the estimate is itself a sub-task and goes in the ledger.

## Master table

Status legend: `todo` · `in progress` · `blocked` · `done` · `dropped`.
Owner: **A** agent (Claude or Codex), **M** maintainer decision or action, **H** independent human
annotator.

| Step | What | Result keys (regex) | Text placeholders (regex) | Tool | Cost | Owner | Blocked by | Status |
|---|---|---|---|---|---|---|---|---|
| S01 | Rebuild Anne v1–5 on the current pipeline | — | — | exists: `gazetteer --volumes 1-5 --force`, `scripts/run_series.py anne --upto 5` | ≈$5–9 (last Anne build $8.19) | A | Vertex quota | blocked |
| S02 | Freeze the system (0012 D1) | — | `J-freeze\|SETUP-generator\|METHOD-models\|LIM-model\|C-.*\|B-hashes` | exists: git tag, run manifests | $0 | M + A | S01 | todo |
| S03 | Oz: held-out history check, then build v1–5 on the frozen system | — | `SETUP-oz-freeze\|B-history` | exists: `run_series.py oz --upto 5` (+ gazetteer first) | estimate first (≈ Anne) | A | S02 | todo |
| S04 | Gold facts with reveal volumes: expand Anne to ≥20 per cutoff, write Oz | `T1-.*-(gold\|future)-t\d` | `B-refs\|A-examples\|A-adjudication\|SETUP-weights` | exists: `docs/eval/parametric/<s>.yaml`, `recall_review.py` | $0 | H (A may draft, labelled) | — | todo |
| S05 | Corpus counts and frozen cast | `T1-.*-(words\|paras\|chapters\|cast)` | `B-cast\|ETH-license\|ETH-wiki` | build: count script over `01_parsed` | $0 | A + M | S02 | in progress |
| S06 | Assertion inventory over every surface + atomizer (P0a) | `F-atomizer-recall` | — | build: extend `assertion_precision.py` to prose and uncited lines; local atomizer | $0 (local model) | A | — | in progress |
| S07 | Annotation protocol, pilot, annotators | `T1-.*-(overlap\|kappa\|sample-t\d)` | `SETUP-annotators\|SETUP-samplesize\|ETH-annotators\|LIM-annotation\|ABS-annotation\|F-agreement` | exists: `assertion_precision.py`, `recall_review.py` sheets | $0 (people's time) | M decides, H labels | decision D1 | todo |
| S08 | Evaluator validation: screens, known-answer cases, verifier challenge set | `F-screen-.*\|F-judge-bacc\|M12-.*` | `F-cases\|F-screen` | exists: `leak_screen_audit.py`; build: perturbation negatives (local) | $0 | A + H | S06 | in progress |
| S09 | Measure NarrativeWiki (B5) at every cutoff | `(M1\|M2\|M3\|M4\|M6\|M8\|N)-(anne\|oz)-t\d-B5` | — | exists: `pipeline_page_leak.py`, `recall_review.py`, `artifact_exposure.py`; M8 from S07 labels | $0 | A + H | S01, S03, S04, S06, S07 | todo |
| S10 | Implement and tune baselines on development data | — | `SETUP-lightrag\|D-B\d\|D-X\d\|ABS-baselines` | adapt: `probe run parametric` (X1 closed book, B1 prefix in context); build: B2, B3, B4, X2 | estimate first (Middlemarch tuning) | A | S02 | todo |
| S11 | Run baselines and measure them at every cutoff | `(M1\|M3\|M4\|M6\|M8\|N)-(anne\|oz)-t\d-(B1\|B2\|B3\|B4\|X1\|X2)` | — | from S10 + S09's measurement tools | **estimate first; likely the largest spend** | A + H | S10, S09 | todo |
| S12 | Means over cutoffs, intervals, secondary citation metrics | `.*-avg-.*` | `SETUP-stats\|T2-caption\|E-caption\|E-notes` | build: `scripts/eval/paper_numbers.py` (paired, character-clustered bootstrap; prints ledger rows) | $0 | A | S09, S11 | todo |
| S13 | Exposure by surface, and prefix-built vs full-built construction (A1) | `T4-.*` | `T4-caption\|RES-exposure\|RES-dev-leaks\|H\|INTRO-witness` | exists: `artifact_exposure.py` (extend to search index, metadata, slugs); prefix builds via `gazetteer --gate build` | estimate first (5 prefix builds per work) | A + H | S09 | todo |
| S14 | Ablations A2–A7 on the development work (A1 comes from S13) | `A\d-.*` | `G-details\|T3-caption\|RES-ablations\|DISC-verify` | exists: `--set` stage overrides; build: flat evidence store (A5) | estimate first | A | S02, S12 | todo |
| S15 | Stage retention of gold facts (Figure F3, M10) | `M10-.*` | `F3-caption\|RES-retention` | build: route tracer gold → evidence → claim → verdict → interval → page | $0 | A | S09 | todo |
| S16 | Cost of the frozen run (T5) | `T5-.*` | `T5-caption\|RES-cost\|DISC-reuse` | build: sum `calls.jsonl` by stage | $0 | A | S01, S03 | todo |
| S17 | Contamination diagnostics (optional, appendix I) | — | `I-results` | exists: `probe run memorization`, `decontaminate`, `anne-remap`/`anne-decon` configs | small; estimate first | A | S02 | todo (optional) |
| S18 | Figures F1–F3 | — | `F1-caption\|F2-caption` | build: plotting script (F2 from `results.tex`); F1 can be drawn now | $0 | A | F2: S12; F3: S15 | todo |
| S19 | Literature: prior-work table cells, unverified citations | — | `T0.*\|D-prior\|CITE` | exists: `scripts/papers/fetch_reference_pdfs.py` (curl fallback past arXiv's 406, 2026-09-28) | $0 | A | — | in progress |
| S20 | Write the results-dependent text | `HEAD-.*` | `RES-.*\|DISC-.*\|CONC-.*\|INTRO-.*\|ABS-.*\|LIM-works\|SETUP-nworks\|METHOD-example\|T1-caption\|F1-caption` | the paper | $0 | A drafts, M approves | S09–S16 | todo |
| S21 | Statements and release | — | `AUTHORS\|CRediT\|FUNDING\|COI\|DATA\|ETH-ai\|J-.*\|K` | the paper | $0 | M | S02 | todo |

## Decisions the maintainer must take (they block steps)

| ID | Decision | Blocks | Options |
|---|---|---|---|
| D1 | Independent human annotation, or the pilot path (plan 0013 §8.4) | S07, S09, S11 | full path: recruit annotators, double-label a subset · pilot: agent-read labels, labelled as such, narrower claims |
| D2 | Which work carries the ablations | S14 | proposed: Middlemarch (development), keeping Anne and Oz untouched by ablation tuning |
| D3 | A second untouched work | S03-like step | needed for any cross-work claim (plan 0013 §2.6.1); otherwise claims stay per work |
| D4 | Venue and deadline | S20, S21 | sets page limit and checklist |
| D5 | M11 temporal error: report or drop | — | no registry key yet; drop unless a claim needs it |
| D6 | Budget split for S11, S13, S14 | S11, S13, S14 | spent ≈$40 of $185 (2026-09-28); each estimate goes in the ledger first |

## Step cards

Each card: what "done" means, and anything the table cannot say.

**S01 — Anne rebuild.** Done when `run_series.py anne --upto 5` completes, `artifact_exposure.py
anne` shows no future-only name on any cutoff's pages, and the 2026-09-28 findings (later-volume
qualifiers, 25 later-volume canonical names) are re-counted at zero in the ledger. v06 outputs are
parked in `data/anne/_out_of_scope_v06/`. Resume from the gazetteer when Vertex quota returns.

**S02 — Freeze.** Done when a git tag exists, the config and prompt hashes and model revision are
recorded in the ledger, and nothing in `src/` or `config/` changes afterwards without a new tag and a
note on which steps it invalidates.

**S03 — Oz.** First check git history and the ledger that no rule was shaped on Oz (plan 0012 D16).
Then build once on the frozen tag. Done when its audits pass and the build's run ids are in the
ledger. Oz outputs are never read while tuning anything.

**S04 — Gold.** Each fact: atomic, directed, polar, attributed, with a verified evidence paragraph
and its reveal volume. Target ≥20 new facts per cutoff per work (plan 0012 D2) and future facts at
every cutoff below 5. Done when the per-cutoff counts are in the ledger. Anne gold today: 34 facts
(`docs/eval/parametric/anne.yaml`).

**S05 — Corpus counts.** Deterministic counts from `data/<s>/01_parsed/v0{1..5}.jsonl`; the cast
list is frozen before any output is read, and characters without a page stay in the denominator.

**S06 — Assertion inventory.** Today's sampler covers only cited structured lines. Extend it to
prose, uncited lines, codex summaries and relationship blurbs; atomize to name-only, third-person
facts (NarrativeFactScore's decomposition, PAPERS §H). Done when the atomizer's recall on
hand-listed assertions from held-out pages is measured (`F-atomizer-recall`).

**S07 — Annotation.** Write the manual (appendix A of the paper is the skeleton), run a pilot,
fix sample sizes from the pilot, then label. If D1 is the pilot path, every label says who read it
(`reader` field), and the paper says so.

**S08 — Evaluator validation.** Started 2026-09-28 (`docs/eval/leak_audit/`): hand-read screen
negatives for Anne t=1 and Spice and Wolf t=1–3. Spice and Wolf rows are development-only and never
enter the paper; they calibrate the tool. Done when the screen's sensitivity and balanced accuracy
are measured on Anne and Oz, the 14 known-answer cases of plan 0013 §3.3 are run, and the verifier
challenge set (≈100 items, perturbation negatives each confirmed false by hand) is scored.

**S09 — B5 measurement.** Per work and cutoff: M1 by hand review (`recall_review.py`), M3 and M8
from S07's labels on S06's sample, M4 from `pipeline_page_leak.py` with every positive **and a
sample of negatives** read, M6 from `artifact_exposure.py` plus reading, N from S06, M2 from the
graph. Done when all 35 B5 keys per work are in the ledger.

**S10 — Baselines.** Every system gets the same cast, page schema, generator and output budget.
B1: prefix in context; if the prefix exceeds the context window, mark the cell unsupported and
report a separately named chunked variant. B2: BM25 + dense retrieval over a prefix-only index.
B3: LightRAG pinned to a release, built from the prefix. B4: graph from all five volumes, filtered
at retrieval. X1: no novel. X2: the whole text (diagnostic only). Tune on Middlemarch, record the
settings, then freeze. Done when every adaptation is written into appendix D's table.

**S11 — Baseline runs.** Estimate first, from token counts of the prefixes and the cast size;
B1 at t=5 sends five books per character page. Done when every cell of appendix E exists or is
marked unsupported with a reason.

**S12 — Aggregates.** Means are over cutoffs within a work, never pooled across works. Intervals
resample characters within a work, keeping each character's cutoff trajectory together; state
the unit. Zero counts: `0/n` with a design-appropriate bound.

**S13 — Exposure.** Surfaces: page text, titles and slugs, shared navigation, search index, page
metadata, links. A string hit is a screen; only adjudicated disclosures are counted. A1 renders the
same cutoff from a prefix-only build and the full build and labels each difference: harmless
formatting, selection change, premature identity link, or actual revelation.

**S14 — Ablations.** One change at a time; rebuild everything downstream; never reuse a gazetteer
built with a removed component. A7 runs in an isolated copy that is never published.

**S15 — Retention.** For each gold fact, find it (or not) at each stage. A fact can arrive by
several routes; count it at a stage if any route reaches it.

**S16 — Cost.** From the frozen runs' `calls.jsonl`: cold build, warm-cache rebuild (a replay, not a
sample), and the marginal cost of adding one volume.

**S19 — Literature.** NS-ST-GraphRAG, SearchWiki and FABLES stay `\CITE` until the fetch script
or a hand check verifies them; T0 cells are filled only from sections actually read.

**S20 — Writing.** Order (plan 0013 §0.2): results → discussion and limitations → introduction →
abstract and title. Every sentence with a number points at a filled key.

## Log

| Date | Change |
|---|---|
| 2026-09-28 | Opened. 737 result keys declared in `results.tex`, none filled; S08 started; S01 blocked by Vertex 429. |
| 2026-09-28 | S19: fetch script past the 406 (80/80 ids, 15 PDFs); T0 cells for CHIRON, TimeChara, Living the Novel, STORM filled from their text; NS-ST-GraphRAG and SearchWiki cited after reading. Left: `T0-caption`, the \sys scope cell (needs S02). S05: Anne/Oz counts in the ledger (`corpus_counts.py`); cast waits on the maintainer. S01 still blocked (429 at 02–05 UTC too). |
| 2026-09-28 | S06: `assertion_inventory.py` enumerates every surface and atomizes prose/scenes locally; `assertion_precision.py --population all` samples it. Dev pilot on S&W t=1: 871 assertions (cited-only pool was 90), atomizer recall 91/100 agent-read. Done needs held-out Anne/Oz pages (after S01) and a D1-conformant reader. |
| 2026-09-28 | S08: challenge set v1 (`challenge_set.py`, 81 confirmed items, agent-read pilot). MiniCheck bacc 0.718 (TPR 0.457), qwen judge 0.867. Left: production verifier (M12, needs Vertex), the 14 known-answer cases, the hard types (quoted lie, hypothetical, embedded story), screen sensitivity on Anne/Oz after S01. 15/50 gold facts not carried by their evidence paragraph — feed back into S04. |
| 2026-09-28 | S08: the 14 known-answer cases run (`known_answer.py`): 12/14 pass; fails are the local judge on a quoted lie and both leak tiers on implication-only disclosure. Case 9 found the leak scorer dropping page-less gold characters; fixed (control facts count, future facts reported apart; no recorded value changes). |
| 2026-09-28 | S16 built: `scripts/eval/run_cost.py` (cold / warm-rebuild / per-volume cost from `calls.jsonl`, `--sha` for the frozen tag; test). Anne since 09-25: $8.30 cold. S12 built: `paper_numbers.py` (per-cutoff and mean-over-t values within a work, character-clustered paired bootstrap, exact zero-event bound; tests) and `paper_observations.py` (hand verdicts only → observations; screen scores never enter). Both wait on S09/S11 inputs; nothing written to `results.tex`. |
| 2026-09-28 | S15 built: `scripts/eval/retention_trace.py` — per gold fact, stages entity / read / claimed / graph / verified / page / hand, each by any route; claimed/graph/page are a paragraph route (lower bound), hand is the semantic end point. Smoke run on the mid-rebuild Anne data only (not recorded). Waits on S01 + hand recall. |
| 2026-09-28 | S10 built (B3 pending): `scripts/baselines/` — one output contract for every system (B5's sections, sentence caps and citation markup; citations outside a system's own passages dropped and counted), rendered to `dist/<work>@<system>/wiki/`, so every eval tool scores a baseline unchanged (variant series ids, `paths.variant_base`). X1 closed book, B1 prefix in context (unsupported above the context limit), X2 whole text, B2 BM25 + bge-m3 RRF over prefix chunks under an evidence budget, B4 full-built graph read through `graph/temporal.py` at t. `--estimate` prices a cell with no model call; `baseline_page` routes to B5's model. Anne gold-cast estimates (9 characters, Flex): B1 t=5 ≈ $0.70 ceiling, X2 ≈ $0.70, B2/B4 ≈ $0.02, X1 ≈ $0.01 — before the ≈30-character frozen cast and caching credit. Left: tune budget/chunk size on Middlemarch, B3 (LightRAG: install + index cost estimate). |
| 2026-09-28 | Maintainer: observations and claims (not errors) go into the paper. New appendix L (`appendix/l-observations.tex`) + 15 `OBS-*` keys in `results.tex`, 14 filled from existing ledger rows (generator bake-off yield and hand-read support, cost ratio, quota behaviour, Flex latency, one content-refused call); `OBS-alias-calls-lite` waits for the anne-m31 gazetteer. **Drafted, pending maintainer review.** |
| 2026-09-28 | S18: F1 drawn (`docs/paper/figures/f1-overview.tex`, TikZ; synthetic A/B example, six stages with model-calling ones marked, build vs render scope, cutoff-t wiki and shared surfaces). Not compiled here (no TeX) — check on Overleaf. F2/F3 wait on S12/S15 data. |
| 2026-09-28 | S04: Oz gold drafted — `docs/eval/parametric/oz.yaml`, 109 facts / 35 characters, 26/23/20/20/20 by reveal volume, future facts 83/60/40/20 at t=1..4. Agent-drafted (labelled), evidence ids verified present and read; pending maintainer review and key reconciliation after S03. Anne expansion to ≥20 per cutoff still to do. |
| 2026-09-28 | S04: Anne gold expanded 34 → 116 facts (21/24/21/23/22 by reveal volume, future 90/66/45/22 at t=1..4); new rows labelled `reader: agent-2026-09-28`. Both works now meet ≥20 per cutoff; pending maintainer review and key reconciliation after S01/S03. |
| 2026-09-28 | S10 B3 built: `scripts/baselines/b3_lightrag.py` (LightRAG 1.5.7 pinned, isolated `.venv-b3`): prefix-built index per cutoff (t = copy of t-1 + volume t), LightRAG `aquery_data` retrieval only, then the shared generator/contract; its own calls via stage `baseline_lightrag` (cached, budgeted, interlocked), embeddings via local bge-m3. `--dry` smoke run passed ($0). Anne t=1 estimate on current routing: index ≈ $0.14 (+ gleaning), 25 pages ≈ $0.07. |
| 2026-09-28 | Paper: appendix D adaptation cells written from the implemented baselines (tuned chunk size/budget left `\TBD` for Middlemarch tuning); setup-stats paragraph states the implemented method (percentile bootstrap over characters, trajectories kept, unweighted mean over t, exact 1−0.05^(1/k) zero bound over characters). `paper_numbers.py` fixed to bound over characters, not items, as the paper already promised. |
| 2026-09-28 | S02 tooling: `scripts/papers/freeze.py record|check <name> [--tag]` — refuses with uncommitted src/config/scripts; records commit, git tree hashes, config sha256 and every routed stage's provider/model/price/options; `check` lists any drift (exit 1). Freeze itself waits on the generator decision (anne-m31 vs anne-m36) and S01. |
