# PLAN 2026-09-14 — Pre-full-scale architecture review and punch-list

**Status:** planning document. Nothing in `src/`, `config/`, or `tests/` was modified to produce it.
No `wiki` command that spends an LLM call was run. `pytest -q` was run (713 passed, exit 0).

**Scope:** (1) should Aho-Corasick be removed; (2) what to adopt from *Living the Novel*
(arXiv 2512.07474); (3) an honest, prioritized audit of what must land before a full-series,
multi-series run.

**Read for this:** `CLAUDE.md`, `docs/CONTRACTS.md` §1/§2/§8, `docs/vision/PHASE_24.md` (all five
entries), `LOG.md` top 8 entries, `docs/handover/PHASE_22.md`/`PHASE_23.md` known-gaps sections,
`docs/archive/GUIDE_TO_PUBLISHING.md` §0/§3.2/§3.3, `entities/{automaton,gazetteer,candidates,alias,classify}.py`,
`probe/{futureset,report}.py` + `probe/channels/index.py`, `cli.py` gate paths, `eval/gold.py`,
`audit/reports.py`, and the full 23 pages of 2512.07474. `2606.31946v2.pdf` was not read past
confirming the prior judgment — it is cs.CV video generation and has nothing to contribute here.

---

# Question 1 — Should Aho-Corasick be removed?

## Recommendation: **KEEP. Augment in three small ways. Do not replace.**

This one is not close, and the deciding factor is nameable.

## 1.1 What it is actually doing

`entities/automaton.py` is multi-pattern exact string matching over an **enumerable, finite pattern
set** — every `surface_forms[].text` in `gazetteer.json` — with two project-specific rules bolted on
(`_is_boundary_match`, so `Shin` never fires inside `Shining`; `_resolve_overlaps`, longest-match-wins).
It has four consumers, not one:

| Consumer | What it needs from the automaton |
|---|---|
| `index_mentions` → `mentions.jsonl` → `extract/windows.py` | exact `(para_id, start, end, surface, entity_id)` offsets |
| `site/wikify.py` (via `site/bundle.py`) | the same, over already-generated prose, to place links |
| `probe/channels/index.py::measure_vocabulary_exposure` | per-surface `first_vol` over an enumerable vocabulary |
| **Planned** `corpus/perturb.py` (Phase 27, `PHASE_24.md` 2026-09-11) | a **reversible** entity remap with an alignment map so every annotation transfers |

It costs $0 and runs one linear pass per gazetteer build. Current scale: 86 has 163 entities /
211 surfaces at 4 volumes; extrapolating linearly, ~500 entities / ~700 surfaces at 13. That is
three orders of magnitude below where any AC implementation starts to care.

## 1.2 The five properties the research programme is resting on it for

1. **Enumerability.** "What does the index know at cutoff *t*" is a finite, printable set of strings.
   This is what makes `probe/channels/index.py` a *diff* rather than an estimate.
2. **Decidability of the counterfactual.** "Could a cutoff-*t* reader have seen this string?" is
   answerable by verbatim search over `01_parsed` — literally what
   `scripts/probe/reanalysis_first_occurrence.py` does, and the only reason the 0.303 → 0.033 correction
   was possible. This works *because* matching is exact-string. Under any approximate matcher the
   question becomes "is cos-sim above τ", which is not a fact about the text.
3. **Determinism.** Same gazetteer + same corpus → byte-identical `mentions.jsonl`. No seed, no
   temperature, no model version. This is what makes the Phase 30 artifact claim ("a reviewer
   reproduces every number with zero API spend and no GPU", `docs/archive/GUIDE_TO_PUBLISHING.md` §3.2) true for
   this stage.
4. **Zero marginal cost.** §3.3 already names GPU wall-clock as the binding constraint at
   150k–200k local calls. Anything that adds calls here multiplies by (corpora × variants × cutoffs).
5. **Invertibility.** A match is an exact offset span. Substitution is reversible; an alignment map
   is trivially derivable.

## 1.3 The alternatives, against those constraints

| Alternative | Auditability | Cost | At 13 vols / new series | Verdict |
|---|---|---|---|---|
| **Pure-LLM mention detection per window** | Destroys all five. The index's knowledge becomes model weights — unenumerable, and the detector has read the whole series in pretraining, so L_build becomes L_param by construction | Adds O(windows) calls per cutoff per corpus; under `--gate=build` × 13 cutoffs × 3 corpora × 2 variants this is the single largest line item in the whole programme | worse, superlinearly | **Reject outright.** This would end Claim 2. |
| **Embedding / ANN fuzzy matching** (`ollama.py::embed()` already exists, so it *is* cheap) | Loses 1, 2, 5. The similarity threshold τ is itself a corpus-wide statistic — i.e. it reintroduces the exact `min_mentions` bug the probe just spent two sessions locating, one level up and harder to see | cheap-ish but non-zero; embeddings must be recomputed per cutoff under Mode B | threshold needs recalibration per series → a new unaudited free parameter per corpus | **Reject as a replacement.** Correct as a *separate retriever arm* — see §1.5. |
| **Plain trie, hand-rolled** | identical | identical | identical, slower | No gain. This is roughly what the existing pure-Python fallback branch already is. |
| **`regex` / `re` alternation over ~700 literals** | identical | identical | degrades with pattern count; no native longest-match-wins across alternatives without ordering hacks; escaping is a new failure surface | No gain, strictly more fragile. |
| **FlashText** | identical | identical | AC-equivalent trie, pure Python (slower than the C ext), effectively unmaintained, and it bakes in *its own* word-boundary notion — replacing `_is_boundary_match` is a silent behaviour change for zero benefit | No gain. |
| **spaCy `PhraseMatcher`** | **worse.** Requires tokenization that must agree with this corpus's quirks (para-RAID spans, `<<…>>` machine voice, em-dash-as-image). That inserts a new, corpus-dependent, version-pinned component *into the auditable path* | new ~50MB+ dependency and a model download | a tokenizer trained on newswire on a translated LN corpus is an unmeasured error source per series | **Reject.** Moves backwards on the one axis being published. |

Note the shape of that table: **every option that preserves the property the paper depends on is an
Aho-Corasick reimplementation.** There is nothing to gain by switching, and one option (spaCy)
actively loses ground.

## 1.4 The deciding factor

**Phase 27's counterfactual perturbation protocol needs a reversible, offset-exact, enumerable
surface→entity map, and only exact multi-pattern matching supplies one.**

`PHASE_24.md`'s 2026-09-11 entry specifies `corpus/perturb.py` as "seeded entity remap via the
existing Aho-Corasick automaton + paragraph paraphrase, with an alignment map so every annotation
transfers." Claim 3 (NARRATIVEWIKI-BENCH + contamination protocol) is the leg with no fallback — it
is what makes the benchmark contamination-controlled rather than another memorized-corpus eval. A
fuzzy or learned matcher cannot produce an alignment map, because it cannot tell you which exact
bytes it matched or guarantee it matched them all.

Auditability, cost, determinism and reproducibility all point the same way. This one is load-bearing
because it has no alternative mechanism.

## 1.5 What *to* do instead (augment — all cheap, all improve auditability)

1. **Record the pattern set's provenance in `gazetteer.json`.** `LOG.md` 2026-09-13 already flags
   this: the `min_mentions` a gazetteer was built with is not stored, so
   `probe/channels/index.py::measure_candidate_mining`'s `min_mentions: int = 3` default is an
   **assumption inside the measurement**, not a fact. Add `min_mentions`,
   `max_candidates_per_volume`, and a `source` on every surface form (`corpus` / `alias_cluster` /
   `epithet_mining` / `override` — the last already exists). ~10 lines. This is a prerequisite for
   §3's B2 confound fix below.
2. **Emit the pattern set as a first-class artifact.** A `surface_forms.jsonl` sidecar per
   gate/cutoff (`text, entity_id, first_vol, source, ambiguous`) makes "what the index knew at *t*"
   a citable, shippable file rather than something recomputed from the gazetteer each time. ~15
   lines, and it is exactly the thing to include in the Zenodo release.
3. **Stop silently dropping ambiguous surfaces.** `build_automaton` adds a colliding surface to
   whichever entity comes first under `sorted(entities, key=entity_id)` — an alphabetical,
   silent, unmeasured loss. At 13 volumes and three new series, collisions rise. Minimum fix:
   count the drops and report them in `wiki audit gazetteer`. This is both a correctness-at-scale
   issue and a measurable-leak issue.

Separately, and *not* as a replacement: `PHASE_24.md` 2026-09-13 already decided on
`retrieve/{bm25,dense}.py`, repositioning the automaton as **one of three retriever arms**. That is
the right home for embeddings — as something compared against under one protocol, not as something
the audit trail depends on. `llm/providers/ollama.py::embed()` already exists, so the dense arm is
free.

## 1.6 What *Living the Novel* does instead, and why it doesn't apply

Nothing comparable. Their Stage 0 does LLM entity/relation extraction with a rule-based
alias-normalization convention (`'Nemo'` → `'Captain Nemo'`), then at query time runs *semantic
search over graph nodes and edges* (§3.4.1), splitting the query into low-level keywords (→ nodes)
and high-level keywords (→ edges) with a Qwen3-4B decomposer. There is no lexical index anywhere in
their system.

That is coherent **for their end goal and not for this one**. They ship a conversational agent: they
need the gate to hold at inference, and nobody will ever ask them to prove what their index knew at
*t*. This project ships a static, filtered artifact and is publishing a paper about *whether the gate
holds* — which requires exactly the enumerability their design discards. `PHASE_24.md` 2026-09-13
already makes the sharper version of this point: their Narrative-Present Gate is a query-time filter
over a build-time index that read the whole novel. Adopting their retrieval would import the weakness
this paper exists to measure.

---

# Question 2 — What to adopt from `docs/sample_research_related/`

`2606.31946v2.pdf` (World Narrative Model): confirmed cs.CV, physically-grounded video synthesis.
Nothing transferable. Do not cite it as related work; it is a topical false friend.

`2512.07474v1.pdf` (*Living the Novel*, cs.HC, 8 Dec 2025): highly relevant, and the useful half is
the evaluation design, not the pipeline.

## 2.1 ADOPT — concrete, with a slot in the file map

### A1. Query-shaped Leak@t (their **Timeline-coherence Test**) — *the single most transferable idea*
**Their method (§4.2.2):** 100 questions about future events relative to a fixed early timeline
point; a response scores 1 if the character expresses ignorance, 0 if it leaks. Gemini 2.5 Pro as
judge. Gated systems 87–91; ungated systems and GPT-4o 27–42.

**Why it matters here:** narrativewiki's Leak@t is currently measured **on the artifact** — does a
post-*t* string appear on the page. That is necessary and it is not what a reviewer will accept as
"does the gate work". Their framing is the missing half: *ask* the cutoff-*t* product N questions
whose answers exist only after *t*, and count how many are answerable from it.

**Slot:** new `eval/leak.py` (Phase 26, already named in `PHASE_24.md`), plus a question generator.
**Cost: near zero, because the generator already exists and is dead code.**
`probe/futureset.py::future_claims_at(conn, t)` returns exactly the fact set to turn into questions,
by construction, with no annotation. Today it has zero callers and zero tests (see §3, B5) — wiring
it into a question generator both revives it and gives Claim 2 its query-side evidence.

### A2. Their **Temporal-Adversarial** pair construction as the recipe for the gold
**Their method (§3.3.1):** positive = an in-character refusal; negative = the factually correct
answer that leaks. Mapped here: gold = "not established by volume *t*"; distractor = the true post-*t*
fact from `future_claims_at`. This gives `eval/leak.py` a concrete construction protocol instead of
just a metric name, and it makes the negative class *derived*, not written — which is what keeps it
within the annotation budget.
**Slot:** `eval/leak.py`; gold artifacts under `docs/eval/`.

### A3. Their **four-cell ablation × one fixed external reference**
**Their method (§4.2):** Baseline / DPA-only / CRE-only / Full, all on one backbone, plus GPT-4o as
an outside reference. It isolates *architecture* from *model budget*.

This is precisely `docs/archive/GUIDE_TO_PUBLISHING.md` §3.2's stated protocol, so the value is not the idea — it
is that **a December-2025 paper is a citable precedent for it**, which converts "we could only afford
one backbone" from an apology into a methodology with prior art. The narrativewiki cells map cleanly:
`no-gate` / `render-gate` (the published architecture) / `build-gate` / `full`.
**Slot:** Phase 28 baselines table; cite in the experimental-setup section.

### A4. Report the operational numbers
They report per-turn latency and system-condition variance. The analogue here — per-stage call
counts, cache hit rate, wall-clock per corpus — is already collected by `llm/budget.py` and the run
ledger, and is table-stakes in a resource/D&B submission. Effort: one report function.
**Slot:** `audit/reports.py` (a `wiki audit budget`-shaped report) → the reproducibility section.

### A5. Their **alias-normalization rule** — adopt as a *citation*, not as a design
Their Stage 0 states "normalizing all aliases to a character's canonical name" as an unconditional
preprocessing rule. The 2026-09-14 individuation finding is that **this operation is
cutoff-dependent** — at *t*=1 `Lawrence` and `Kraft Lawrence` are not yet known to be the same string
pair, and merging them retroactively is itself a build-time leak. They assert the rule; this project
can *measure* that it is not cutoff-safe.

That is a genuine, small, defensible contribution sitting directly on top of a published claim, and
it is the strongest argument for resolving Open Question A as **"fragmentation at low cutoffs is
cutoff-correct; retroactive merging is a leak."** (See §3, B2 — a confound has to be cleared before
the number backing this is citable.)
**Slot:** `docs/vision/PHASE_24.md` Open Question A; then `docs/archive/GUIDE_TO_PUBLISHING.md` §2.2.

### A6. Already adopted — say so, don't rebuild
Their "Event and Background Integration" (events as first-class graph nodes) is
`data/04b_events/events.db` + `graph/events.py` (Phase 19). Their "Diegetic Time Injection" is
`first_vol` + `graph/temporal.py`. Independent convergence is worth one sentence in related work
("our event layer corresponds to X's event nodes; our volume axis to their diegetic time
coordinate"). **No implementation work.**

## 2.2 DO NOT ADOPT — and why, plainly

- **Deep Persona Alignment, GRPO reinforcement fine-tuning, LoRA adapters (their entire Stage 1, and
  the RFT half of Stage 2).** narrativewiki has no conversational agent, no persona, and no model to
  specialize. Its entire generative surface is 2–4 sentences of prose per section plus a one-sentence
  codex summary, produced from an already-filtered claim set. Beyond irrelevance, adopting it would
  be *actively harmful twice over*: it would consume GPU weeks that §3.3 already names as the binding
  constraint, and it would fine-tune a model **on the source corpus** — deliberately manufacturing
  L_param contamination, the one channel the paper currently reports honestly as a floor. There is no
  version of this that helps.
- **CharacterBox and the persona-fidelity metric suite (KA/BA/EE/PT/IM/AD/BC).** Measures role-play
  believability. Nothing here plays a role.
- **The controlled lab study (N=15, per-turn ranking, Friedman + Wilcoxon) and the 5-day ESM diary
  study (N=12).** Correct methodology for an interactive HCI system at CHI/IMWUT; wrong instrument for
  an \*ACL-class resource paper about a static artifact. The human study this project needs is
  inter-annotator agreement on gold facts (`eval/humaneval.py`, already planned in Phase 26), which is
  a different thing entirely. A diary study would cost months and buy nothing at the target venue.
- **Dual-level (low/high keyword) query decomposition via a 4B LLM.** A conversational-retrieval
  trick. Narrativewiki renders pages; it does not serve queries. Only becomes relevant if Claim 4
  (the agentic environment) is revived — and that is explicitly deferred to paper 2.
- **The Narrative-Present Gate itself.** Already implemented, and the entire premise of Phase 24 is
  that copying it is not the contribution.

## 2.3 Citation hygiene — how to characterize this paper in §8.1

It is the closest prior work and should be cited as such, characterized precisely: cs.HC; a single
novel (*Twenty Thousand Leagues*); a 15-participant lab study from one university community; TT and
RT are **100 hand-written questions each with no reported IAA and a single frontier judge with no
judge validation**; and their own Limitations section concedes the evaluation is "centered on a
single novel" and that they "have not yet systematically benchmarked performance on more complex
narrative structures (e.g. non-linear timelines)."

That paragraph writes itself into the gap statement: their gate is asserted and spot-checked on one
book; this work measures it, across corpora, with contamination control. Note also that their TT
scores (87–91, not ~100) are themselves evidence that a correct gate does not fully close leakage —
which is `CLAUDE.md` §1's own hypothesis, observable in their published numbers. **That is worth
quoting in the introduction.**

---

# Question 3 — Audit: what's needed before scaling to full series

Test health as of this document: **`pytest -q` → 713 passed, exit 0.** No failures, no skips
reported. That is a genuinely strong baseline and it is not where the risk is.

## 3.1 Ground truth on current state (checked, not assumed)

| | 86 | spice-and-wolf |
|---|---|---|
| ingested (`01_parsed`) | **13/13 volumes** | 2/2 |
| gazetteer `volumes_covered` | **[1,2,3,4]** — 163 entities, 211 surfaces, 303 candidates | [1,2] — 33 entities, 43 surfaces, 89 candidates |
| claims | v01, v02 only | v01, v02 |
| pages (`05_pages/`) | **1 entity** | 14 entities |
| gold eval data | **none** | 10 characters + `baseline.json` |
| `--gate=build` artifacts | none | `@t01`, `@t02` (entities + claims) |

**The 86 pipeline has never run past volume 4 at any stage after ingest, and has essentially no
rendered output.** "Scaling up to 13 volumes" is not a scale-up of a working run; it is a first run.
Plan accordingly.

## 3.2 Stage-by-stage

| Stage | Tests | `audit` report | In eval | `--gate=build` | 13-vol readiness |
|---|---|---|---|---|---|
| ingest | `test_ingest.py` (4 KB), `test_cli_chapters.py` | `wiki audit ingest` | no | n/a | **done for 86.** Risk is new series only |
| entities | `test_entities.py` (24 KB), `test_probe_index.py` | `wiki audit gazetteer` + roster.html | no | **yes** | **two blockers** (B1, B3) |
| extract (claims) | `test_extract.py`, `test_adequacy.py`, `test_extract_gate.py` | `wiki audit claims` | indirect | **yes** | **unvalidated past a 14-char roster** (B4) |
| extract (scenes) | `test_scenes.py` (29 KB) | `wiki audit scenes` | no | **no `--gate` at all** | blocks gate extension (B2) |
| graph | `test_graph.py` (47 KB), `test_graph_verify.py`, `test_ppr.py`, `test_events.py`, `test_provenance.py` | `contradictions`, `verify`, `events` | no | **not wired** | cross-volume arbitration never seen >2 vols |
| synth | `test_synth_*.py` (~55 KB) | `pages`, `outline` | **yes** | **not wired** | `synth/cache.py` is the designed 13× mitigation and is tested — this is fine |
| site | `test_site_bundle.py` (53 KB), `test_site_wikify.py` (**3.8 KB**), `okf`, `static`, `audit_html` | `links`, `relationships`, `pages` | no | n/a | relationship bundles are edge-driven, not all-pairs — **not** a scale problem |
| audit | `test_audit_reports.py` (43 KB), `test_audit_eval.py`, `test_audit_html.py` | — | — | — | 12 reports registered; **no `probe` report** |
| eval | `test_eval_gold.py`, `test_audit_eval.py` | `wiki audit eval` | — | — | **one series only; stale baseline** (B6) |
| probe | `test_probe_index.py` (8 tests) | **none** | — | — | one channel; `futureset.py` dead (B5) |

## 3.3 BLOCKERS — do not start a full-series run until these are closed

### B1. `MAX_LLM_PAIRS = 300` is already binding and degrades *silently* with corpus size
`entities/alias.py:38` caps alias adjudication at 300 LLM pairs per gazetteer build. Measured
directly against on-disk data:

| corpus | candidates | candidate pairs reaching tier d (single-type upper bound) |
|---|---|---|
| spice-and-wolf v1–2 | 89 | 171 |
| **86 v1–4** | **303** | **1,533** |

Type partitioning reduces the real figure below the upper bound, but 86 at 4 volumes is already in
the same order as the cap, and candidates scale roughly linearly with volumes (→ ~1,000 candidates,
~15k pair upper bound at 13 volumes). Past the cap, pairs are dropped in sorted order — and the sort
puts co-occurrence pairs first, then fuzzy-ratio descending. **The tail that gets cut is precisely the
low-fuzzy nickname/call-sign pairs the comment at `alias.py:130` says are the only ones tier d exists
to catch.** On 86 specifically — a series whose densest naming channel is para-RAID call signs
(`CLAUDE.md` §3 trap 4) — this is the wrong thing to truncate.

Consequence: **entity fragmentation gets worse at full scale, not better, and invisibly.** This is
the same phenomenon as the 2026-09-14 individuation finding, arriving from the other direction.

*Minimum fix (cheap, do it first):* log `len(maybe_pairs)` and the number dropped; surface both in
`wiki audit gazetteer`; move the cap into `config/series.*.yaml`. This converts a silent cliff into a
measured one — which is the standard this repo already holds itself to everywhere else.

### B2. The `--gate=build` A/B is confounded by the epithet channel — the headline result is not yet valid
`cli.py::gazetteer` handles `--merge-epithets` **before** the `--gate` branch (line 870 returns
early), so `--gate=build --merge-epithets` silently ignores `--gate`. More importantly, `SCENES_DIR`
is never cutoff-redirected by `paths.set_build_cutoff`, and `_build_gazetteer_for_volumes` never
merges epithets — so **no build-mode gazetteer has ever had the epithet channel at all.**

Verified on disk:

```
02_entities/gazetteer.json  (render, v1-2)  33 ents  43 surfaces  4 epithet-sourced
@t01/02_entities/gazetteer.json             19 ents  21 surfaces  0 epithet-sourced
@t02/02_entities/gazetteer.json             33 ents  41 surfaces  0 epithet-sourced
```

And the four render-only surfaces are exactly the ones the individuation finding turns on:
`the wisewolf`, `the Wisewolf`, `the Wisewolf of Yoitsu`, `the Nymph`.

Two consequences, both material:

1. **`docs/probe/gate_comparison_spice-and-wolf.jsonl`'s 0.042 → 0.000 is a comparison of
   gate-plus-epithets against gate-without-epithets**, not render-gate against build-gate. It is not
   yet a clean A/B and should not be cited as one.
2. **The 2026-09-14 individuation finding's stated mechanism is probably wrong.** The entry says
   render mode merges Holo/Wisewolf because "alias clustering has seen enough cross-reference."
   Inspection says otherwise: the render `holo` entity carries **no bare `Wisewolf` surface at all** —
   its wisewolf surfaces are *all* `source: epithet_mining`, i.e. they came from `wiki scenes` +
   `--merge-epithets`, a whole-corpus LLM pass build mode never ran. The unification is an
   epithet-channel artifact, not an alias-clustering one.

   Worse, there is a separate real anomaly underneath: `Wisewolf` occurs 17× in v1 and 17× in v2
   (well clear of `min_mentions=3`), yet it is a standalone entity at `@t01` and **absent entirely**
   from `@t02` — neither its own entity nor a surface form of `holo`. The entity set is
   **non-monotonic across cutoffs**, which no part of the design predicts. `@t02`'s `holo` also
   carries `But Holo` / `And Holo` — the sentence-initial mining artifacts `_canonical_rank` is
   documented to discount — which render mode does not have.

*This is the third headline number in four days to move on audit* (0.303 → 0.033; 0.982 →
run-history artifact; and now this). The pattern is consistent: **the gates are byte-identical in
code path but not in inputs.** Fix before any further gate work: either run the epithet pass per
cutoff under build mode (redirect `SCENES_DIR`, add `--gate` to `wiki scenes`), or disable epithet
merging in the render index used for the comparison. Then re-run the free probes and restate the
individuation finding with its mechanism corrected. Zero LLM calls for the restatement; the epithet
re-run is local-only and cheap on spice-and-wolf.

### B3. `gazetteer.json` does not record the `min_mentions` it was built with
Already flagged in `LOG.md` 2026-09-13 and still open. `measure_candidate_mining` takes
`min_mentions: int = 3` as a default, so the load-bearing L_build measurement contains an unverified
assumption about the artifact it is measuring. Ten-line fix; blocks nothing else but should not
survive into a paper. Fold into the §1.5 provenance change.

### B4. Claim extraction has never been validated past a 14-character registry
`extract_volume` passes the visible-entity list into the prompt as "other people/things named in this
passage" context. That list is 14 entities on spice-and-wolf; on 86 at 13 volumes the character
roster will plausibly be 150–300. Nothing in the test suite or any prior run exercises that
prompt shape at that size, and the failure mode is silent degradation (context crowding, dropped
relations, higher NOT_ENTITY noise), not an exception.

There is also a known local-model interaction: `MEMORY.md` records `repeat_penalty` pushing
qwen2.5:14b into CJK garbage on free-text-heavy calls, detectable only in `calls.jsonl`, not in the
exit code. A longer roster is exactly the condition that makes that more likely.

*Fix:* run `wiki extract` on **86 volumes 1–4** (local, $0, gazetteer already exists at that
coverage) before committing to 13. Inspect `calls.jsonl`, not just the claim count. This is the
single highest-value de-risking run available and it costs nothing but wall-clock.

### B5. `probe/futureset.py` is dead code
No callers in `src/`, no callers in `tests/`, no tests of its own. It is listed in `CLAUDE.md` §5 as
the `F>t` mechanism for Leak@t — the metric the paper's Claim 2 is named after. Right now Leak@t has
no implementation that uses it.

This is a blocker in the sense that **the benchmark cannot be called "benchmarked" while its
headline metric's data source has zero consumers.** It is also the cheapest one to close: §2.1's A1
(query-shaped Leak@t) is exactly the consumer it was written for.

### B6. Evaluation covers one series, with a stale regression floor
`docs/eval/gold/` contains `spice-and-wolf/` only — 10 characters and `baseline.json`. There is no
gold for 86, and `docs/handover/PHASE_22.md` "Known gaps" #1/#2 records that `baseline.json` sits on
**pre-C1/C2/C3 numbers**, i.e. the regression gate is calibrated against a superseded pipeline.
Meanwhile everything Phase 26 names — `judge.py`, `leak.py`, `ceiling.py`, `kgalign.py`,
`humaneval.py`, `report.py` — is unbuilt, and the only working metrics are lexical keyword-overlap
heuristics that `eval/gold.py`'s own docstring correctly describes as "a recall SIGNAL for a human
reviewer to skim, not a certified score."

That is fine as a CI gate (it was designed to be exactly that) and insufficient as the evaluation of
a benchmark paper. Gold on a second series is annotation work, not code, and it is on the critical
path.

## 3.4 SHOULD DO before the run (not blockers, but they get expensive later)

- **S1. `--gate=build` stops at claims.** `paths.set_build_cutoff` redirects `ENTITIES_DIR` and
  `CLAIMS_DIR` only. `SCENES_DIR`, `GRAPH_DIR`, `EVENTS_DIR`, `PAGES_DIR`, `BUNDLE_DIR` are all
  render-mode under `--gate=build`. Note the concrete consequence: scene claims land in
  `03_claims/scene_v{NN}.jsonl`, so a `@tNN` claims directory has **no scene channel at all** — a
  build-mode graph would be missing it entirely. Extending the gate is real LLM spend and a human
  decision; the point here is that **B2 must be fixed first**, or each extension inherits the same
  confound one stage deeper.
- **S2. `ingest/epub.py` is still h1-hardcoded for section detection.** `chapter_start_selector` /
  `chapter_title_selector` are configurable (good), but line 129–130 does `all_h1 =
  soup.find_all("h1"); has_heading = bool(all_h1)` — the *presence* test that decides "new section vs.
  continuation document" is still literally `h1`. A Gutenberg EPUB using `<h2>` collapses every
  chapter into one, exactly as `docs/archive/GUIDE_TO_PUBLISHING.md` §0 predicts. The config knob that exists does
  not cover the case the config knob was added for. One-line-ish fix; blocks the three new
  public-domain corpora, not the 86 run.
- **S3. `test_ingest.py` is 4 KB** for the module documented to absorb nine distinct corpus traps
  (`CLAUDE.md` §3). `wiki audit ingest` covers some of it at runtime, but before three new series
  land, the trap-by-trap regression coverage should exist. The 86 corpus already provides 13 volumes
  of fixtures for free.
- **S4. `test_site_wikify.py` is 3.8 KB.** `wikify.py` applies the per-target *and* per-alias
  `first_vol` filter — a spoiler-critical path. `test_spoiler_leak.py` covers the invariant; the unit
  is still thin relative to its risk.
- **S5. No `wiki audit probe` report**, despite `probe/report.py`'s own docstring asserting one
  ("plus the `wiki audit probe` report"). The probe subsystem is the newest, the least tested, and the
  only one producing paper numbers. `CLAUDE.md`'s own rule is "every phase registers exactly one
  report here."
- **S6. `docs/probe/reanalysis_*.py` produce paper numbers from outside `src/` and outside the test
  suite.** They are correct and they are cheap and they are also unversioned analysis scripts in a
  docs folder. For the Phase 30 artifact claim ("every number reproduces"), they need to be either
  promoted into `probe/` with tests, or explicitly declared as one-shot analyses with their outputs
  committed (they are — `docs/probe/*.jsonl`). Pick one deliberately.
- **S7. Estimate the Mode-B cost before authorizing it.** A 13-cutoff `--gate=build` sweep on 86 is
  not 1× the render cost; it is Σ over *t* of the cost at volumes 1..*t*. Rough order: ~1,000
  candidates at full coverage → ~6,500–7,000 classify calls across the sweep, plus up to 300 alias
  calls per cutoff (3,900), plus claim extraction per cutoff. Nothing in the CLI currently prints a
  dry-run estimate. One `--dry-run` that counts candidates and multiplies is worth more than it costs.

## 3.5 ALREADY FINE — do not spend time here

- **The 13× cutoff multiplier.** `synth/cache.py` + `site/bundle.py`'s sparse multi-cutoff maps are a
  correct, tested, documented solution. `test_synth_cache.py` and 53 KB of `test_site_bundle.py`
  cover it.
- **Relationship bundles.** Edge-driven via `_relationship_pairs`, not all-pairs. No O(n²) blowup.
- **PPR.** H4 was retracted correctly; `build_subgraph` filters by cutoff and `test_ppr.py` pins it.
  `_MAX_ITER = 100` is fine at this graph size.
- **The mention index itself.** 211 surfaces at 4 volumes → ~700 at 13. AC does not care.
  `mentions.jsonl` is 814 KB for 86 at 4 volumes; ~2.5 MB at 13. Non-issue.
- **SQLite / `graph/store.py`.** Well within range.
- **Run ledger, rollback, failed-run quarantine, content-addressed cache.** These are the reason a
  multi-week run is feasible at all. `docs/archive/GUIDE_TO_PUBLISHING.md` §3.3 is right that this deserves a
  paragraph in the paper.
- **The test suite's shape.** 713 passing, with the heaviest coverage (`test_graph.py` 47 KB,
  `test_site_bundle.py` 53 KB, `test_audit_reports.py` 43 KB) on the highest-risk modules. This is
  not a repo with a testing problem.

## 3.6 Trivial issues found while reading — noted, not fixed, per instruction

1. **`CLAUDE.md` §5 lists `llm/providers/openrouter.py`. No such file exists.** OpenRouter is routed
   through the `openai` provider with a `base_url` override (`config/models.yaml:128`). Doc drift.
2. **`ahocorapy>=1.6` is declared in `pyproject.toml`** with the comment "pure-Python fallback; used
   automatically if the C ext is absent" — but `automaton.py`'s fallback is a hand-rolled
   `str.find` loop and nothing imports `ahocorapy`. Unused dependency; either wire it or drop it.
   (`wiki doctor` at `cli.py:303` also advertises it as an install option.)
3. **`cli.py:1744`: `list(range(1, 14))`** — a hard-coded 13-volume fallback in a series-agnostic
   codebase. Dead branch in practice (only reached when no scene files exist), but it is an 86-ism.
   `cli.py:438` similarly hard-codes `"wiki synthesize --upto 13"` in a help string.
4. **`graph/verify.py:4` contains a stale `TODO`** in the module docstring.
5. **`cli.py::gazetteer` accepts `--gate=build --merge-epithets` and silently ignores `--gate`.**
   Should error, the way `extract` already errors on incompatible flag combinations
   (`cli.py:1393–1401`). Mechanically trivial; see B2 for why it matters.
6. **`docs/papers/pdf/2512.07474v1 (1).pdf`** is a duplicate of `2512.07474v1.pdf`.
   Gitignored, so cosmetic only.

---

# Recommended sequencing

Ordered by dependency and by cost-of-discovering-it-later. Everything in Wave 0 and Wave 1 is $0.

## Wave 0 — free, same-day, and each one unblocks something (do all of these first)

1. **Fix B2's confound.** Decide epithets in/out for the gate comparison, make `--gate=build
   --merge-epithets` an error, and re-run the zero-cost probes. Then **restate the 2026-09-14
   individuation finding with its corrected mechanism** (epithet channel, not alias clustering) and
   investigate the non-monotonic `Wisewolf` disappearance at `@t02`.
   *Why first:* every downstream gate extension, and the Open Question A decision in §2.1/A5, inherits
   this. It is also the third correction in four days — closing it protects the credibility discipline
   `docs/archive/GUIDE_TO_PUBLISHING.md` §0 is explicitly built on.
2. **Instrument B1.** Log and audit-report `len(maybe_pairs)` vs `MAX_LLM_PAIRS`; move the cap to
   config. Do not change the cap's *value* yet — measure first.
   *Why now:* it tells you, before you spend a week of GPU, how badly alias quality will degrade at 13
   volumes. It may also partly explain B2's anomaly.
3. **Record gazetteer build provenance (B3 + §1.5 items 1–2).** `min_mentions`,
   `max_candidates_per_volume`, per-surface `source`, and the `surface_forms.jsonl` sidecar.
   *Why now:* it removes an assumption from inside the load-bearing measurement, and the sidecar is
   what Wave 2's Leak@t and Wave 3's Zenodo artifact both want.
4. **Count and report ambiguous-surface drops in `build_automaton` (§1.5 item 3).**
5. **Fix S2 (h1-hardcoding) and the §3.6 trivia.** Small, and S2 gates the three new corpora.

## Wave 1 — the decisive free run (do not skip; it is the cheapest information available)

6. **`wiki extract` on 86 volumes 1–4, local, $0** (B4). Gazetteer already covers exactly that range.
   Inspect `calls.jsonl` for the `repeat_penalty`-class corruption, not just the claim count.
   *Why here:* it is the only evidence that will exist about whether the extraction prompt survives a
   roster 4–5× larger than anything it has seen, and discovering it doesn't during a 13-volume run is
   the expensive version of this experiment. It also stress-tests B1 at 303 candidates for real.
7. **Add the `wiki audit probe` report (S5).** Required by `CLAUDE.md`'s own "every phase registers one
   report" rule and by the fact that the probe subsystem is where the paper's numbers come from.

## Wave 2 — make the benchmark a benchmark (this is what "evaluated" actually means)

8. **Build `eval/leak.py` on top of `probe/futureset.py` (A1 + A2 + B5).** Generate questions from
   `future_claims_at(conn, t)`, score whether the cutoff-*t* artifact answers them, report per-corpus
   Leak@t. Local judge; frontier judge only on the validation sample.
   *Depends on:* Wave 0 item 1 (a clean gate), Wave 1 item 6 (claims on more than 2 volumes).
   *Why this is the pivot:* it converts Leak@t from an artifact-inspection metric into the
   query-shaped metric a reviewer will recognize, and it revives the one dead module in the tree. It
   is also the item most likely to decide the §0 "one run that decides Claim 2" question.
9. **Refresh `baseline.json` and transcribe gold for 86** (B6). Annotation, not code; start it early
   and in parallel, because it is the only item on this list that cannot be compressed by working
   harder on the day.
10. **Fill in `test_ingest.py` and `test_site_wikify.py` (S3, S4)** using the 13 volumes of 86 already
    on disk as fixtures.

## Wave 3 — only after Waves 0–2 are green

11. **Cost-estimate the Mode-B sweep (S7)**, then make the human decision about extending
    `--gate=build` to `scenes` → `graph` → `pages` (S1). Do it one stage at a time, re-probing after
    each, exactly as the last two increments did — that discipline is working.
12. **Then, and only then, the full-series runs.** 86 to 13 volumes first (it is ingested, and its
    traps are documented), then the new corpora once S2 is fixed and their configs exist.

## The single most important next action

**Wave 0 item 1: clear the epithet confound in the `--gate=build` comparison and restate the
individuation finding.** It is free, it takes an afternoon, it corrects a claim that is currently
written down as fact in `PHASE_24.md` and `LOG.md`, and every subsequent gate extension and every
paper sentence about build-time leakage is built directly on top of it.
