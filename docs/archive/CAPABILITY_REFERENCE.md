# NarrativeWiki — Capability Reference (ground truth, not a pitch)

**Purpose.** This file is deliberately boring. It says what the pipeline actually does, what is
actually measured, what was **tried and abandoned**, what was planned and not built, and what it
does **not** do. Any research-alignment claim (a cold email, a statement of purpose, a sentence in
the paper) can be checked against it. Give this file, not the pitch, to anyone judging fit.

**Source and date.** Rebuilt **2026-09-28** from `LOG.md`, `docs/MEASUREMENTS.md` §§1–48 plus
its 2026-09-28 rows, `docs/handover/PHASE_{30,31,33}.md`, `docs/vision/PHASE_{31..33}.md`,
`docs/paper/`, and `config/models.yaml`. It replaces the 2026-09-25 version (in `git log`). Four
things changed the frame since then:

1. **Publication is back** (maintainer, 2026-09-25). The paper is a *measured trade-off*, not a
   "first" (`docs/vision/PHASE_33.md`, 2026-09-27). Its question: *how much source-supported
   information survives to the page at a reader's cutoff without unsupported assertions or
   disclosure of later text?* The LaTeX lives in `docs/paper/`. Every number there is a
   `\res{KEY}` in `results.tex`, and no result is filled in before the maintainer has reviewed it.
2. **Published results only on public-domain works with a good reference wiki.** *Anne of Green
   Gables* (v1–5) is the main work, *Oz* (v1–5) is held out, and *Middlemarch* (Books I–V) is the
   stress/tuning corpus. *Spice and Wolf*, *Overlord* and *Bookworm* are development series. Their
   numbers never appear as paper results.
3. **Five volumes, one general pipeline** (Phase 32). The paid interlock is `max_volumes: 5`. Every
   per-series override, overlay and prompt vocabulary was removed. The only series-specific parts
   left are format conversion and gold data.
4. **One generator for every reported number: Gemini 3.6 Flash** on Vertex, Standard capacity
   (maintainer, 2026-09-28). Flash-Lite is retired. A refusal gets the schema's empty answer, never
   another model.

---

## 1. What it is, in one paragraph

A pipeline that reads a novel series and builds a static wiki where every page is scoped to "what
a reader who has read only up to volume *t* would know." Facts are extracted with a verbatim
supporting quote and a paragraph id. They are stored as volume-stamped intervals in a small SQLite
graph and checked one at a time against their own cited evidence. They render as deterministic
structured fields plus short prose that is generated **from the already-filtered set**, never
redacted afterwards. The output is one Markdown/MkDocs tree per cutoff. Every structured row links
to its paragraph. Around it sits an evaluation harness: prefix-only baselines, hand-read recall and
precision per cutoff, leak screens, artifact-exposure scans, judge challenge sets and a contamination
(parametric-memory) probe. "Hybrid temporal GraphRAG" is the project's own label, not a claim that
it uses any published GraphRAG system.

---

## 2. What is actually implemented (built, running, tested)

| Layer | What's really there | What it is *not* |
|---|---|---|
| **Ingest** | Deterministic EPUB → paragraph parser, no LLM. Handles Yen On, J-Novel Club and Project Gutenberg markup: chapters split across files, heading-tag detection, `source.volume_breaks` (one file split into books), `epub.split_within_documents` (several chapters in one XHTML), straight-quote dialogue. | Not a general document parser. |
| **Decontamination** | `wiki decontaminate` builds same-`para_id` variants of a parsed novel: `-remap` (seeded name remapping, $0) and `-decon` (remap + LLM paraphrase, stage `decon_paraphrase`). Built for *Twenty Thousand Leagues*: 99.6% of paragraphs paraphrased, 0 residual original names. | A *contamination-reduction treatment*, not a "decontaminated benchmark" (§4.1 #25). |
| **Entity discovery** | Regex + frequency-ratio mining → LLM typing → alias clustering (fuzzy + co-occurrence triggers, LLM adjudication **from the quoted passages only**) → gazetteer → **Aho-Corasick automaton**. General alias rules: first-volume naming, kinship, appositive, cannot-link, honorific, narrator adjective, preposition. `gazetteer.aliases_at` hides an alias before the volume its surface first appears. | Not embedding-based ER; not benchmarked. **The gazetteer is still built at full scope** (`--volumes 1-5`); a prefix-built comparison (A1) is queued, not measured. |
| **Fact extraction** | Four passes, each with its own output file: chapter-span **scenes** (100% paragraph coverage), mention-window **`claim_extract`** (one window per call), long-context **infobox** (GENDER/AGE/ORIGIN over paragraphs that name the character) and **backstory**. Every fact needs a verbatim quote that passes deterministic gates: subject named, verbatim, realis, per-predicate object types and qualifier disqualifiers. RANK/OCCUPATION/ORIGIN/TITLE/SKILL/MOTIVATION/FEAR now carry written definitions. | No fine-tuning. No vision: illustrations are never read, and character images were **removed** from pages in Phase 32. |
| **Temporal KG** | SQLite intervals `(s, p, o, vol_start, vol_end)` with `first_vol` = **disclosure position** (reveal time, not world time) and polarity. Same-volume conflict → arbitrate; cross-volume → close and open. A superseded value is shown with its volumes ("previously: … (v1)"); the "changes later" marker is gone. A qualifier first seen after `vol_start` is dropped. bge-m3 is used for value canonicalisation only. | Granularity is one relationship per pair per volume. |
| **Verification** | `wiki verify`: one call per fact against its cited evidence plus cutoff-safe neighbours, pair-sibling context for relations, the predicate definitions above. Verdicts reused by context hash, so a rebuild reproduces the wiki byte for byte. Withheld facts reach no consumer (fields, relations, traits, prose). On the challenge set: **bacc 0.989** (v1, 81 items); **0.750** on the 12-item hard set. | Single-pass judge. **Admits claims lifted from a story a character tells** (0/2 rejected on the hard set, like both local judges). |
| **NLI (MiniCheck-FT5)** | Local, $0. Used in `wiki audit eval`'s recall union and as the **first-pass leak screen**. Every screen positive is hand-read before it counts. | Not in the shipped verdict path (0 of 1,524 verdicts NLI-scored at the §42 count; not re-counted since). As a screen it misses: 2 of 7 on-page controls caught at Anne t=1, and it reads "engaged" as "marries". |
| **Retrieval for generation** | Personalized PageRank over the cutoff-filtered entity graph plus direct interval queries. Cutoff restriction is pinned by a test. | Not dense retrieval. |
| **Synthesis + site** | Closed section vocabulary; structured fields at zero LLM cost; 2–4-sentence prose and one-sentence codex summaries only from verifier-approved, cutoff-filtered claims; `null` on zero evidence. One MkDocs tree per cutoff; character pages, shared codex pages, relationship pages, timeline, source view. `audit links` fails on orphans and dead links. | **Search disabled** (one index leaked across cutoffs). |
| **Baselines** (`scripts/baselines/`) | Same generator, same cast (all gold characters), same page contract, variant series `<work>@<system>`: **X1** prompt-only, **B1** prefix long-context, **B2** prefix chunk RAG (tuned on Middlemarch: 150-token chunks / 20k budget), **B3** LightRAG 1.5.7 as retriever (isolated `.venv-b3`, `mix` mode, 20k), **B4** full-corpus graph + retrieval filter, **X2** diagnostic (droppable). Every eval tool scores a baseline's pages unchanged. | Anne cells were **running** on 2026-09-28 (X1 t=1–2 done at the time of writing); no baseline number exists yet. |
| **Evaluation harness** | Per-cutoff hand recall (`recall_review.py`), audited **assertion precision** over a seeded sample of rendered lines (`assertion_precision.py`, Wilson CI), `assertion_inventory.py` (every surface a reader sees, atomised), leak screen + hand audit bound to page sha (`pipeline_page_leak.py`, `leak_screen_audit.py`), `artifact_exposure.py` (future-only vocabulary in pages, shared nav, HTML, slugs), judge challenge sets, `known_answer.py` (14 protocol cases), `retention_trace.py` (entity → read → claimed → graph → verified → page), `run_cost.py`, `paper_numbers.py` (character-clustered paired bootstrap; zero-count bound), `freeze.py`. | No human second reader yet. Gold and most hand verdicts were read by an agent and are labelled as pilot (plan 0014 D1). |
| **Contamination probes** | `probe run memorization` (name cloze + title ID) and `probe run parametric` (closed-book / in-context page facts against hand-verified future facts). Plus the three zero-LLM leak channels from Phase 24 (index, query, disclosure). | Run on *Leagues* only; the paper-scale contamination step (S17) is pending. |
| **Routing, cost, reproducibility** | Every call goes through `llm/client.py`: cached (`sha256(provider+model+prompt+params)`, never cleared), budgeted, per-run ledger. **Vertex only** (AI Studio retired). Flex PayGo with `X-Server-Timeout: 1800` is the 429 fallback, kept out of the cache key. Lifetime cap `255` + `billed_offset_usd 2.19` against a **$275** real-bill ceiling. `NARRATIVEWIKI_CACHE_ONLY=1` replays for $0. Freeze `anne-v1` = tag `freeze-anne-v1`. Full test suite passes (LOG 2026-09-28). | No training anywhere. |

---

## 3. Real, measured numbers (each has a row in `docs/MEASUREMENTS.md`)

**Status labels matter.** *Pilot* = agent-read, no human second reader. *Dev* = a development
series; never a paper result. Nothing in this section is a paper headline yet.

### 3.1 Paper works (Anne main, Oz held out, Middlemarch tuning)

| Fact | Value | Status |
|---|---|---|
| Anne corpus v1–5 | 8,489 paragraphs · 428,122 words · 184 chapters | measured |
| Gold | Anne **116 facts / 43 characters** (21/24/21/23/22 by reveal volume; 90/66/45/22 future facts at t=1..4). Oz **109 / 35** (26/23/20/20/20) | agent-drafted, labelled |
| Gold errors found | 2 of 90 Anne t=1 "future" facts were first stated in v1 (Bolingbroke, White Sands), found by the leak screen; 15/50 challenge gold facts are not carried by their cited paragraph ±1 | measured |
| Model trial, `anne-m36` (all stages 3.6 Flash), t=1, hand-read | recall **18/23** (tool screen 15/23) · disclosure **0/35** future facts · precision **32/40** (Wilson 0.65–0.90) · $2.71, 1,911 calls, 664 claims, 80/428 intervals flagged | pilot |
| Anne Phase 31 build (3.1 Flash-Lite, v1–6), leak curve | tool rates t1–t5 0 / .125 / .154 / 0 / 0; **every positive hand-read: 0 leaks** (MiniCheck read "engaged" as "marries") | superseded build |
| Stored-prompt bake-off (12 prompts, hand-read) | 3.6 Flash **20/26 supported, 0 unsupported**; 3.1 Flash-Lite 24/50, 6 unsupported; 3.6 ≈ 2.8× the cost per prompt | pilot |
| Production verifier on challenge sets | v1: TPR 1.000, TNR 0.978, **bacc 0.989**; hard: **0.750** (story-within-story 0/2) | pilot items |
| Local judges on challenge v1 | MiniCheck bacc **0.718** (TPR 0.457); qwen2.5:14b 0.867 | pilot items |
| Known-answer protocol cases | **12/14 pass** (fails: a quoted lie, an implication-only spoiler) | measured |
| Artifact exposure, Anne Phase 31 site | future-only strings on t=1..5 cutoff pages 8/10/8/9/6; in **shared nav** 139/96/76/51/22 | measured, pre-fix build |
| B2/B3 tuning, Middlemarch t=2 (screen recall n=19) | B2 chunk 150 / 20k **0.526**; B3 `mix` = `hybrid` 0.316 | dev, tool-read |
| Spend | recorded ≈ **$44** lifetime at 2026-09-28 14:20 UTC; console read $40.00 against ledger $37.81 earlier that day | measured |

### 3.2 Development history (not paper results)

| Fact | Value |
|---|---|
| **Audited assertion precision**, shipped v1–2 wikis | **99/120 = 82.5%** (S&W 33/40, Overlord 36/40, Bookworm 30/40). *Replaces the old "100% precision"*, which was selected-control precision (§4.1 #21) |
| Assertion inventory, S&W t=1 | **871** atomic assertions a v1 reader sees, vs **90** in the cited-line pool; atomiser recall 91/100 |
| *Leagues* contamination (§43–44) | book identified from 99.1% of passages → 55.7% after renaming; name-only closed-book fact leak 32% → 0% remapped → 0% paraphrased; cloze still recalls the original name on 51.3% of paraphrased passages. **Recognition survives decontamination; fact transfer does not.** Pipeline v01 pages leak 0/25 Part Two facts |
| Historical, 86 t=1 (retired) | selection-tier 0.303 vs disclosure-tier **0.033**. The two travel together |
| Rebuild determinism | full round trip: 0 files differ (§29–30) |

---

## 4. Modules tried, failed, and swapped out

**Shipped-then-replaced** (it ran, produced bad output, and the output is on disk) is kept apart
from **rejected at design time**. Only the first kind is evidence about the system. The right-hand
column is the honest hook for a research email.

### 4.1 Shipped, then replaced on measured evidence

| # | What was in place | How it failed | What replaced it | Research area |
|---|---|---|---|---|
| 1 | Mention windows as the only fact source | 5/14 pages had zero facts; ~40 near-duplicate fragments per character | Chapter spans + long-context infobox/backstory; GENDER 2/14 → 12/14 | Long-document IE |
| 2 | Verbalized confidence as the arbitration signal | "public witness" at 1.0 beat the correct "traveling merchant" at 0.72 | Model arbitration + per-fact verification; NLI bimodal on relations (median 0.097, p90 0.928) | Calibration ([2306.13063](https://arxiv.org/abs/2306.13063)); NLI ([2404.10774](https://arxiv.org/abs/2404.10774)) |
| 3 | "A stronger model fixes the sarcasm bug" | 3 models, 2 tiers read "son of the great Jakob Tarantino" as `PARENT_OF` | Insincerity marked at extraction + realis gate; violations 3 → 0 | Pragmatics in IE |
| 4 | Batched per-character verification | One changed fact re-rolled 12 verdicts; rows 34 → 23 | Context-hash reuse, then per-fact calls; per-fact released 16/16 relations (a false marriage) → pair-sibling context | LLM-as-judge granularity |
| 5 | Fuzzy similarity alone for aliases | Cannot merge nickname and name | Co-occurrence trigger + adjudication | Coreference |
| 6 | Exact-string dedup | Paraphrased duplicates never collapsed | bge-m3 at 0.86 + subsumption; negative result on file (duplicate 0.756 < distinct 0.770) | Canonicalisation |
| 7 | Corpus-wide mining thresholds | Erased "Wisewolf" at t=2 | Per-volume-OR thresholds | Temporal index construction |
| 8 | Render-time-only gating | 37/122 of 86's t=1 surfaces not discoverable from v1 alone | `--gate=build`; paper version is A1 prefix builds (queued) | Temporal leakage |
| 9 | Lexical overlap as the judging metric | Near-verbatim page scored 0.0; direction-blind negative fired | Lexical ∪ entailment; recall WARN, precision gates | Metric validity |
| 10 | Drop counters printed and discarded | A shipped fix never re-ran (3 → 124 claims) | `yield.json` per run | Observability |
| 11 | H4 "PPR concentrates on future importance" | Falsified by reading the code | Four-channel leak taxonomy | Falsifiability |
| 12 | `leak_rate = 0.303` headline | Artefact of the predicate | Two tiers reported together (0.033) | Measurement validity |
| 13 | Verifier honoured only on fields | 17/21 withheld facts reached prose | One `visible_state_at` for every consumer | Gate enforcement |
| 14 | ±4-paragraph infobox dossier | Gender read from "said the girl" before naming, 3/3 | Only paragraphs naming the character | Entity grounding |
| 15 | One search index for all cutoffs | v1 search quoted v2 text | Search disabled | Artifact leakage |
| 16 | Config edit as a "surgical" change | Gate config is in the prompt; re-rolled claims, lost 2 facts | Cache-only replay first | LLM reproducibility |
| 17 | Local → free tiers → paid routing | 404s, shared-pool 429s, bad JSON, empty key, refusals | Vertex default, ordered fallback, then (#24) one model | API reproducibility |
| 18 | One-publisher assumptions | Gutenberg 15 chapters read as 2; narrator's "Mom" became a character | Generic ingest defaults | IE robustness |
| 19 | Silent failures | Cap read an unwritten ledger; one NaN disabled canonicalisation; 0/30 relationship pages reachable while `audit links` said OK | Summed ledger, per-text retry, reachability audit | "Passes its check" ≠ "does its job" |
| 20 | Global `wiki` command | Ran a different checkout for ~3 phases | Module invocation from the repo venv | Provenance |
| 21 | **"Precision 100%"** | It was selected-control precision: no hand-listed negative fact on a page | **Audited assertion precision** over sampled rendered lines: 82.5% on the dev wikis; misses were relation labels and mis-filed fields → predicate definitions in the verifier (Leagues 24/40 → 21/24) | Evaluation validity; what a precision number counts |
| 22 | Per-series overrides, overlays, prompt vocabulary | Each series quietly tuned the pipeline, so nothing was held out | **One general pipeline**; overrides kept only as roster gold | Generalisation; held-out discipline |
| 23 | Alias adjudicator free to use world knowledge | Merged from series knowledge ("in the second volume of the Overlord series"); a false merge in Middlemarch | Judges from quoted passages only | Parametric leakage inside construction |
| 24 | Flash-Lite with refusals answered by another model | Bake-off 6/50 unsupported vs 0/26; mixed-model runs cannot be compared | **3.6 Flash on every stage**; refusal → empty answer, same model | Controlled comparison |
| 25 | Treating renamed/paraphrased text as "decontaminated" | Renaming left the book identifiable in 55.7% of passages; name cloze 51.3% after paraphrase | Reported as a contamination-*reduction* treatment, with parametric cause stated separately | Contamination and memorisation |
| 26 | Aliases gated only in body text | Page front matter listed future aliases ("Anne Blythe" on v01) | `gazetteer.aliases_at` on every surface | Metadata as a leak channel |
| 27 | Interval qualifier taken from the first claim in input order | A v2 qualifier ("at Echo Lodge") printed on a v1 page; 4/498 Anne intervals | Earliest-only; dropped if later than `vol_start`; test in `test_spoiler_leak.py` | Temporal provenance at field level |
| 28 | `map_calls` submitting every item up front | During a 429 outage every queued call still ran its retry ladder, multiplying requests | Stop submitting after failure; driver stops after 3 quota failures | Cost safety under outages |
| 29 | MiniCheck as the leak and recall arbiter | Tool recall 0.652 vs hand 0.783; engagement read as marriage | Screen only; every positive and a sample of negatives hand-read, bound to page sha | Automatic judges as measurement |

**Kept deliberately:** confidence fallback behind model arbitration; `ENEMY_OF`'s object-type rule;
the full-scope gazetteer until A1 measures its cost.

### 4.2 Rejected at design time (never built)

| Rejected | Why | Instead |
|---|---|---|
| spaCy / off-the-shelf NER | Invented names still need review | Mining + LLM typing |
| Provider structured-output APIs | Four code paths, three untestable | JSON-by-prompt + Pydantic + repair |
| `tiktoken` | Wrong tokenizer for routed models | `chars/4`, labelled estimate |
| Graph isomorphism as KG metric | NP-hard and label-blind | Triple-level P/R/F1 |
| Event shuffling vs contamination | Destroys reading order | The cutoff axis |
| Fandom/Wikidata as gold | In pretraining; whole-series spoilers | Text-grounded gold, earliest-statement checked |
| Stricter trait instruction for the verifier | Replay: fixed 7, rejected 23/121 true traits | Kept v3 prompt |
| Gleaning (a second extraction pass) | Measured worse on precision | Not shipped |
| Priority PayGo, Provisioned Throughput, AI Studio key, weaker or mixed models, 3.8 Flash | Premium/subscription, credit doesn't pay, breaks one-model rule, 3.8 slower with fewer facts | Flex PayGo on the free-trial account |
| Fine-tuning, navigation-agent training, multilingual | Out of scope (PHASE_33) | — |

---

## 5. Known, currently open gaps

- **No baseline number yet.** The Anne matrix is running; B1/X2 are the expensive cells (estimates
  $57 / $84 at Standard ceilings), and X2 may be dropped.
- **S01, the frozen Anne v1–5 build, was mid-run** on 2026-09-28 (extract-v4 done at 15:58 UTC).
  B5 (the system itself) has no t=1..5 numbers until it finishes.
- **Held-out Oz has not been run.** It waits for a budget increase.
- **No independent annotation.** Gold, precision verdicts and challenge items are agent-read
  (labelled). A human second reader on a stratified subset is required before test data.
- **Full-scope gazetteer.** Names from later volumes can title early pages (Anne: 25/483 entities
  titled by a later surface in the pre-rebuild gazetteer). A1 prefix builds at t=2–4 are queued
  behind the baselines, budget permitting.
- **Story-within-story claims pass every judge** (verifier, MiniCheck, qwen: 0/2).
- **Shared navigation carries future-only vocabulary** (measured on the Phase 31 site). Nav/slug
  exposure has to be re-measured on the frozen build.
- **Within-volume relationship changes** get one provisional pick per pair per volume.
- **Taxonomy gaps** (`CREATED_BY`, `GOVERNS`) remain on the dev series.
- **Illustrations are invisible.** Fandom descriptions of art (eye colour, clothing) are not
  recallable from text; text-grounded gold excludes them.
- **The billing account is a $300 free trial.** No usage tier and 429 outages; Flex is the fix in
  place. Upgrading is the maintainer's decision.

---

## 6. Planned, NOT built (never describe as a capability)

- Per-cutoff search.
- Per-alias *link volume* (when the text reveals two names are one person, not when a surface first
  appears).
- Ablations S14 and the paper-scale contamination step S17.
- A reader task-utility study (optional, after the core table).
- Public release of the response cache, gold and tooling (the paper's "reusable protocol" claim
  waits on it).

*Moved out of this list since 2026-09-25:* baselines (built, running), the contamination protocol
(built and run on *Leagues*), the memorisation probe (built).

---

## 7. What this project explicitly does NOT use

- **No training of any kind.** Every generative call is a plain prompt to Gemini 3.6 Flash on
  Vertex. MiniCheck-FT5, bge-m3 and local qwen2.5:14b (eval judging and atomising only, $0) are
  used as-is.
- **No dense retrieval in the system.** Aho-Corasick + PPR. (Baselines B2/B3 use dense and graph
  retrieval, because they are the comparison.)
- **No vision model, no interpretability, no learned ranker, no test-time adaptation.**
- **No iterative verification.** One call per fact, bounded context.
- **No knowledge-editing method or benchmark.** Interval supersession is bespoke.
- **No human-rater validation yet.**

---

## 8. Literature status (2026-09-28)

- **84 PDFs** in `docs/papers/pdf/`, each with Applied/Reference status in `PAPERS.md`.
  `REFERENCES.md` metadata: **80/80 ids verified** (curl fallback past arXiv's 406, 2026-09-28).
- **Read in full: *Living the Novel*** (2512.07474, story-time gate, published first), and
  **STORYSUMM** and **NarrativeFactScore** (PAPERS §H). The rest are read to abstract level or only
  title-verified.
- **Prior art the paper concedes:** story-time gating (Living the Novel), verified character
  sheets (CHIRON), temporal literary graphs (NS-ST-GraphRAG), corpus-to-wiki compilation
  (SearchWiki). The claim is narrower: the complete cutoff-scoped artifact, stage-level loss
  accounting, and construction-time/artifact leakage measurement.

---

## 9. How to use this file

1. **Match a professor's methods against §2 and §7 first.** If the overlap needs §6, say "a
   problem I expect to hit," not "a thing I built."
2. **§4.1 is the strongest material. Quote the failure, not the fix.** Rows 21–29 are the newest
   and the most paper-relevant.
3. **Say the scope and the status:** Anne v1–5 main, Oz held out and not yet run, results pending
   the maintainer's review. Development-series numbers are never results.
4. **Never write "no leaks".** Write "0 of *n*" with the rough 95% bound 3/*n* (0/35 → ≤ 0.086).
   Never write "first", "hallucination-free", "provably spoiler-free" or "decontaminated benchmark".
5. **Never quote "100% precision".** It was a different quantity (#21). And 0.303 never travels
   without 0.033.
6. Regenerate this file when a phase closes, from `docs/MEASUREMENTS.md` and the newest handover.
