# PHASE_24 — Research programme: from working system to publishable contribution

Full entries for Phase 24. Append-only (`CLAUDE.md` §4). One-line pointers live in `VISION.md`.

---

## 2026-09-11 — The project becomes a research contribution; the paper's thesis and what it is not

**What:** `narrativewiki` is to be published at a top-tier venue (*ACL main/Findings class) within
~12 months, solo, on a ~$20 API budget plus one local GPU. The full strategy — feasibility
assessment, venue ladder, engineering programme, 12-month schedule, related-work map, risk register
— lives in `Guide to Publishing.md` at the repo root. This entry records the decisions that shape
the code.

The paper's thesis is **not** "we built a pipeline and measured it." It is:

> Reading order is a reader-observable time axis that yields N fully-supervised knowledge states
> from one annotation pass. That makes narrative an *instrument*: serve the same question at a
> cutoff where it is unanswerable, and a correct answer is provably parametric memory rather than
> retrieval.

Four claims: (1) the task of progressive knowledge scoping and this system as its constructor;
(2) **Leak@t**, a metric for temporal containment, and the finding that filter-before-generate is
necessary but *not sufficient* — implication leaks through a correctly filtered claim set;
(3) NARRATIVEWIKI-BENCH on public-domain corpora with a graph-preserving counterfactual
perturbation protocol; (4) the hyperlinked output as a generator of contamination-controlled
multi-hop retrieval environments whose gold derivation chains are known by construction.

**Why:** the system is mature (Phases 0-23, ~700 tests) but validated on 2 volumes of 1 series, and
its headline invariant is asserted rather than measured. Two external facts force the framing:

1. **Filter-before-generate is already published.** Prior work (to verify: arXiv 2512.07474)
   describes a "Diegetic Knowledge Graph" with a "Narrative-Present Gate" filtering spans to
   story-time <= t before generation — i.e. `CLAUDE.md` §1. It cannot be claimed as novel. But
   nobody has *measured* whether it works, which is where Leak@t comes from — and `CLAUDE.md` §1's
   own reasoning ("implication leaks through redaction") is the hypothesis to test.
2. **The nearest agentic-retrieval environments each miss one half.** Fabricated mini-internets
   have ground truth by construction but no real-text anchor; real-Wikipedia environments have real
   text but are memorized. This system is the only design with both, plus a cutoff knob neither has.

**Implies:** seven new phases, all additive — no existing contract changes, and `graph/`, `synth/`,
`site/`, `eval/` need no series-specific work.

- **Phase 24** — multi-corpus ingest + scale-out. Make `ingest/epub.py`'s chapter-heading tag
  configurable (it hard-codes `find_all("h1")`, so a Gutenberg EPUB using `<h2>` collapses every
  chapter into one); `corpus/package.py`; three new series configs (Sherlock, Three Kingdoms,
  Monte Cristo); **write `tests/test_spoiler_leak.py`, which `CLAUDE.md` §1 names as the gate on
  the one invariant that must never break and which does not exist**; full re-run of all corpora.
- **Phase 25** — crawlable multi-page site. The reference viewer is a hash-routed SPA, so an HTML
  crawler sees exactly one page and claim (4) cannot be evaluated. Add a `--multipage` emitter
  beside the existing one; reuse `site/wikify.py`'s links, which already apply the cutoff filter to
  both target and alias `first_vol`.
- **Phase 26** — evaluation harness v2. `wiki eval` with `judge.py` (entailment), `leak.py`
  (Leak@t), `ceiling.py` (groundedness upper bound), `kgalign.py` (triple P/R/F1, GED, centrality
  correlation), `humaneval.py` (IAA), `report.py` (CIs, significance). The existing lexical scorer
  stays as the cheap CI gate it was designed to be, demoted from headline metric.
- **Phase 27** — contamination. `corpus/perturb.py` (seeded entity remap via the existing
  Aho-Corasick automaton + paragraph paraphrase, with an alignment map so every annotation
  transfers); `eval/contamination.py` (closed-book probing, memorization gap).
- **Phase 28** — baselines under one fixed open-weight backbone: vanilla RAG, GraphRAG, LightRAG,
  long-context, closed-book, plus ablations for the spoiler gate, intervals, verification and PPR.
- **Phase 29** — the agentic environment: `eval/webtasks.py` (task generation by construction from
  graph paths), cutoff-conditioned t1/t2 task pairs, `eval/crawler.py` (trajectory-scored harness).
- **Phase 30** — artifact: Zenodo DOI, pinned seeds/models, **the released LLM response cache** so
  every number reproduces with zero API spend, corpus manifests, datasheet.

**Rejected, with reasons** (recorded so they are not relitigated):

- **Event shuffling as a contamination defence** — destroys the reading-order structure that is the
  paper's independent variable, and the mitigation literature documents a fidelity-resistance
  tradeoff covering permutation-style strategies. The cutoff axis already provides variation
  without incoherence.
- **Graph isomorphism as a metric** — NP-hard and label-blind; a graph with every relation type
  swapped is isomorphic to the correct one. Use T-F1 / G-F1 / GED / centrality correlation instead.
- **Fandom and Wikidata as primary ground truth** — heavily memorized (incoherent as a target for a
  contamination-controlled evaluation), whole-series scoped (punishes correct spoiler suppression),
  and the available graphs are co-occurrence networks, not typed relations. Three-tier scheme
  instead: human gold, derived silver with measured noise, structural correlation.
- **A different frontier model per baseline** — confounds architecture with model budget, and is
  unaffordable. One fixed open-weight backbone for every system, stated as a deliberate protocol.
- **86—EIGHTY-SIX as the released corpus** — commercial EPUBs cannot be redistributed. PG corpora
  become the benchmark; 86 and Spice and Wolf become a non-redistributable case study releasing
  derived statistics only.
- **Two papers (system + benchmark)** — 12 months solo is not enough for two at main-track quality,
  and splitting weakens both. One paper, system as constructor.

**Status:** Planned. Phase 24 is the first implementation block.

---

## 2026-09-13 — Four-channel leak taxonomy replaces H1-H4; L_build measured, non-zero, zero LLM calls

**What:** Verified both cited papers directly (arXiv 2512.07474 full text; arXiv 2606.31946
abstract+body). *Living the Novel*'s own architecture confirms the reframe this phase needs: "the
system builds the Diegetic Knowledge Graph" once over the whole novel, and the Narrative-Present
Gate is applied "at inference time" only. Their gate is a **query-time filter over a build-time
index that already read the future.** WNM (cs.CV, different modality) asserts a "deterministic
structural blueprint" drives its renderer and never measures obedience — the same pattern:
*a structured control layer is asserted to constrain a generator, unverified against the channels
that bypass the layer.*

`Guide to Publishing.md` §2.2's H1-H4 are replaced by a taxonomy organized by **when the future
touched the system**, not by four unrelated hypotheses:

| Channel | What the future shaped | Status |
|---|---|---|
| L_query | which claims reach the generator | the published gate; **enforced**, see below |
| L_artifact | page existence, `vol_end` closures, link presence (ex-H1/H2/H3) | enforced, see below |
| **L_build** | the gazetteer, alias clusters, automaton — the index itself | **open; measured this entry** |
| L_param | the generator's own pretraining on the source text | unaddressed; reported as a floor |

**H4 is retracted.** It hypothesized PPR over-selects future-important entities. Checked directly:
`graph/ppr.py::build_subgraph` already takes only `all_edges_at(conn, upto_vol)` — the edge set is
cutoff-correct by construction, and `tests/test_ppr.py::test_build_subgraph_filters_by_cutoff`
already pins this. H4 as written is false. L_build (below) is what H4 was reaching for, one stage
earlier and demonstrated with a number instead of asserted.

**Built:**
- `tests/test_spoiler_leak.py` — the gate `CLAUDE.md` §1 has named since Phase 4 and that did not
  exist (R8, logged Fatal). 27 tests across L_query and L_artifact, including
  `test_generation_input_is_independent_of_the_future`, which states §1 as a property (the
  cutoff-t claim-set hash is a pure function of volumes <= t) rather than a procedure. All pass
  against current behaviour: `wikify.py` and `assemble.py`'s render-time filters were already
  correct — L_query and L_artifact are closed. `pytest -q`: 700 -> then 706 passed.
- `src/narrativewiki/probe/` — the measurement subsystem. `futureset.py` (F>t from `graph.db`,
  zero annotation); `channels/index.py` with two zero-LLM-call L_build probes:
  `measure_candidate_mining` re-runs `entities/candidates.py::mine_candidates` restricted to
  volumes <= t and diffs the surviving surface set against the shipped, whole-corpus-mined
  gazetteer; `measure_vocabulary_exposure` checks whether in-scope mentions/claims rest on a
  paragraph whose only matches come from post-cutoff vocabulary. `report.py` writes JSONL
  (`docs/probe/index_<series>.jsonl`, Part 0.3's "no paper from HTML" requirement). CLI:
  `wiki probe run index --series <id> --volumes <range> [--json <path>]`.

**Found — L_build is real, and larger than expected:**

| Series | t | candidate_mining leak_rate | mechanism confirmed |
|---|---|---|---|
| 86 | 1 | **0.303** (37/122 surface forms) | `min_mentions=3` and the capitalisation-ratio gate in `mine_candidates` are corpus-wide counts, computed once over whatever `--volumes` range is passed, not per-cutoff |
| 86 | 2 | 0.190 (31/163) | closes monotonically as the cutoff approaches the range actually mined |
| 86 | 3 | 0.050 (9/179) | |
| 86 | 4 | 0.000 | the gazetteer's own `volumes_covered` upper bound — nothing left to leak from |
| spice-and-wolf | 1 | 0.042 (1/24) | one surface, "Kraft Lawrence": 2 raw occurrences in v1 alone (below threshold), 4 more in v2 (6 total, clears it) — confirmed by direct text count |

The originally-hypothesized channel (automaton surface-form/link overlap) reads near-zero
(`future_vocabulary_mention_rate` 0.1-0.5%, `tainted_claim_rate` 0-2.3%) because `first_vol` is
*earliest* evidence volume, so a future entity has almost no mentions in text <= t by definition.
`wikify.py`'s per-target, per-alias `first_vol` filter (already tested in
`test_spoiler_leak.py::test_wikify_never_links_an_entity_introduced_after_the_cutoff`) closes that
specific surface. **The real channel sits one stage earlier, in candidate discovery, not in link
rendering** — `min_mentions` and word-frequency capitalisation-ratio are corpus statistics,
computed in one `mine_candidates` call over every volume `wiki gazetteer --volumes` was given, and
a page at cutoff 1 can carry a surface form that would never have cleared discovery from volume 1
text alone.

**Not yet built:** `--gate={render,build}` (the cutoff-consistent rebuild that would drive
`leak_rate` toward zero and let a paper report the compute-recall tradeoff of closing L_build);
`retrieve/{bm25,dense}.py` (repositions the automaton as one of three retriever arms, per the same
session's decision); L_param (closed-book probing, `probe/perturb.py`); Claim 4 (deferred to a
second paper — this phase does not need a crawler, task generator, or agent baseline).

**Status:** Part 0 (credibility floor) and the L_build measurement are done. `--gate=build` (Part 1)
is the next implementation block.

---

## 2026-09-13 (2) — `--gate=build` implemented and run: the measured leak closes to zero

**What:** `wiki gazetteer --gate=build` -- the cutoff-consistent rebuild Part 1 of the plan calls
for, scoped to its first, cheapest increment: entity discovery only (candidate mining, LLM
classification, alias clustering), not yet claims/graph/pages. `paths.py::set_build_cutoff(t)`
redirects `ENTITIES_DIR` (and everything derived from it) to `data/<series>/@t<NN>/02_entities/`,
so a Mode B rebuild can never overwrite the Mode A (render, whole-corpus) index, and both are
read by the identical `probe/channels/index.py` functions with no code change on the probe side
-- they just call `paths.gazetteer()`/`paths.candidates()` and see whichever mode is active.
`cli.py::gazetteer` gained a `--gate={render,build}` flag; the render path is a straight
extraction of the pre-existing logic into `_build_gazetteer_for_volumes(settings, wanted, ...)`
with no behavioural change (`pytest -q` unaffected by the refactor). Build mode calls that same
function once per requested cutoff, each time restricted to `volumes 1..t` -- Mode A and Mode B
are deliberately the same code, differing only in what volumes and what output directory they see.

**Run (approved scope: local Ollama only, spice-and-wolf, volumes 1-2 — $0, no paid API):**

```
wiki gazetteer --gate=build --series spice-and-wolf --volumes 1-2
```

t=1: 48 candidates mined -> 21 classified as entities -> 19 after clustering.
t=2: 89 candidates mined -> 42 classified as entities -> 33 after clustering.

**Result — the measured leak closes to exactly zero:**

| t | gate | leak_rate | entities | surface forms |
|---|---|---|---|---|
| 1 | render (shipped) | 0.042 | 18 | 24 |
| 1 | **build** | **0.000** | 19 | 21 |
| 2 | render (shipped) | 0.000 | 33 | 43 |
| 2 | **build** | **0.000** | 33 | 41 |

Concretely: the shipped (render-mode) gazetteer canonicalizes the protagonist as "Kraft Lawrence"
with that bigram as a surface form -- the surface that leaked (§2.2's example: 2 raw mentions in
v1 alone, below `min_mentions`, only clears the threshold once v2's 4 more are counted). The
cutoff-1 Mode B gazetteer, built from volume 1 text alone, canonicalizes the same character as
plain "Lawrence" and never creates the "Kraft Lawrence" surface form at all -- there is nothing
to withhold, because the index never learned it. `docs/probe/gate_comparison_spice-and-wolf.jsonl`
carries the raw before/after rows; `python -m pytest tests/test_paths.py` covers the redirect
mechanism (`set_build_cutoff`/`build_cutoff`/series-switch reset), 709 passed overall.

**Known gap, stated plainly:** this closes L_build for entity discovery only. Claims, the graph,
and pages are still built in render mode even under `--gate=build` today -- extending the redirect
to `CLAIMS_DIR`/`GRAPH_DIR`/`PAGES_DIR` and re-running claim extraction, arbitration and
verification per cutoff is real LLM spend and is deliberately not done in this increment. The
entity-discovery result already answers the paper's question (does closing the index-side leak
work?) with a real number; extending it to a full page-level before/after is the next increment,
not a blocker to reporting this one.



---

## 2026-09-13 (pm) — Audit of the L_build headline: 0.303 is a selection artifact; disclosure rate is 0.033

**Trigger.** Before any abstract is written around "filter-before-generate leaks 30% of the time",
the number was audited against the thing it is supposed to mean.

**Method.** `docs/probe/reanalysis_first_occurrence.py` (zero LLM calls, ~2s). For every surface
form attached to an entity with `first_vol <= t`, locate its first verbatim occurrence in
`01_parsed`. Tier A exact; Tier B strips a leading article and ignores case. Outputs
`docs/probe/first_occurrence_{86,spice-and-wolf}.jsonl`.

**Finding.** `measure_candidate_mining`'s `leak_rate` answers a *selection-consistency* question
("would cutoff-only mining have emitted this surface?"), not a *disclosure* question ("could a
cutoff-`t` reader have seen this string?"). On 86/t=1, of the 37 surfaces it flags:

- 31 occur verbatim in volume-1 text — `Eighty` 97x, `Dinosauria` 59x, `AI` 56x, `Shinei Nouzen` 2x
  (below `min_mentions=3`). The reader has seen the string; only the *selection* was future-informed.
- 2 are article variants of strings seen 12-14x (`The Gran Mur`, `The Grauwolf`).
- 4 are genuinely absent from volume-1 text: `FOB` (first occurs v2), `No Face` (v2),
  `RAID Devices` (singular `RAID Device` occurs 18x in v1), `The Supreme Commander` (v3+).
- **All 37 belong to entities with `first_vol = 1`.** No future entity leaks on either corpus at any
  cutoff, so H1 ("existence leaks survival") is not addressed by this probe at all -- it only ever
  inspects cutoff-visible entities.

| Series | t | selection `leak_rate` | unseeable exact | unseeable normalised |
|---|---|---|---|---|
| 86 | 1 | 0.303 | 0.049 (6/122) | **0.033 (4/122)** |
| 86 | 2 | 0.190 | 0.018 (3/163) | 0.012 (2/163) |
| 86 | 3 | 0.050 | 0.006 (1/179) | 0.006 (1/179) |
| 86 | 4 | 0.000 | 0.000 | 0.000 |
| spice-and-wolf | 1 | 0.042 | 0.042 (1/24) | **0.000 (0/24)** |
| spice-and-wolf | 2 | 0.000 | 0.000 | 0.000 |

**Consequence for `--gate=build`.** The 0.042 -> 0.000 before/after on spice-and-wolf is a sound
engineering demonstration (the cutoff-1 index canonicalizes `Lawrence`, not `Kraft Lawrence`) on a
case whose disclosure-tier leak was already zero. It is an architectural result on n = 1 surface,
not an empirical one. Reported at that strength in `Guide to Publishing.md` §2.2.

**Decision.** Keep both tiers as named metrics -- selection consistency is the diagnostic that
located the mechanism, disclosure is the reportable number. Never cite 0.303 unqualified.

**Next increment (decides Claim 2's status).** `mine_candidates` is the only entity-discovery stage
with no LLM and no cross-volume reasoning; it is where build-time contamination should be
*smallest*. Extend `--gate=build` to `entities/alias.py` and `extract/claims.py`, run 86 volumes 1-2
locally ($0, within the two-volume testing scope), and re-probe. Materially above 0.033 there ->
Claim 2 is a main-track finding. Near-zero -> Claim 2 becomes a limitations subsection and paper 1
retargets to Findings / LREC-COLING / NeurIPS D&B.

---

## 2026-09-14 — `--gate=build` reaches claim extraction; the `alias.py` half was already done, and a new taxonomy dimension surfaces

**Context.** The previous entry's "next increment" named two targets: `entities/alias.py` and
`extract/claims.py`. `alias.py` turned out to already be covered — `wiki gazetteer --gate=build`'s
pipeline (`_build_gazetteer_for_volumes`) already calls `cluster_candidates` per cutoff, since that
function was written as one shared code path for both gates back on 2026-09-13. Only claim
extraction remained genuinely untouched by any cutoff restriction. TASK-0001
(`docs/tasks/0001-extend-gate-build-to-claim-extraction.md`) scoped exactly that gap, on
spice-and-wolf volumes 1-2 only (the 86 series is deliberately deferred — see "Open items" below).

Codex sign-in was unavailable this session, so Claude implemented the task directly instead of
handing it off — `docs/AUTONOMOUS_SESSION_2026-09-14.md` has the judgment-call-by-judgment-call
narrative; this entry is the research-record version.

**What changed.** `paths.py::set_build_cutoff` now redirects `CLAIMS_DIR` in addition to
`ENTITIES_DIR`. `cli.py::extract` gained `--gate={render,build}`, structurally identical to
`gazetteer`'s: `render` is today's unchanged behavior; `build` re-extracts once per cutoff t,
restricted to volumes 1..t AND to gazetteer entities with `first_vol <= t` (read from that
cutoff's own `--gate=build` gazetteer, not the render-mode one). The one new mechanism this adds
beyond what `gazetteer --gate=build` already had: `extract_volume`'s "other people/things named in
this passage" prompt context and its relation-object type validation are now also
cutoff-restricted, because they read from the same `entities_visible` list the character roster
comes from — a future character can no longer be named to the model as context for a
cutoff-visible one, and a relation can no longer resolve to an entity the model was never told
could exist.

**Verification.** `pytest -q`: 709 -> 713. `wiki extract --gate=build --series spice-and-wolf
--volumes 1-2` — local Ollama, $0 — produced `@t01/03_claims/v01.jsonl` (24 claims, 8-character
registry), `@t02/03_claims/v01.jsonl` (16 claims, 14-character registry), `@t02/03_claims/v02.jsonl`
(14 claims). `docs/probe/reanalysis_claim_diff.py` (new, zero LLM calls) compares these against the
production `03_claims/` files.

**The headline number needs the same audit treatment as 2026-09-13(pm)'s did.**
`reanalysis_claim_diff.py` reported only_render = 0.982 (t=1) / 0.954 (t=2) against the production
render file — a huge apparent gap. But `data/spice-and-wolf/03_claims/v01.jsonl` is not a fresh
baseline: it has accumulated 226 claims for volume 1 alone across many sessions of `--entities`
top-ups chasing `wiki audit eval` recall gaps and predicate-vocabulary expansions since 2026-09-04.
A one-off same-day diagnostic (not committed — it costs LLM calls, so it isn't part of the
zero-cost probe script) ran a FRESH single-pass render extraction of v01 against the full
14-character registry with today's settings: **16 claims**, the same order of magnitude as build
mode's 24, not 226. Diffed directly (fresh-full-registry vs. cutoff-registry, same day, same
model): 8 claims in common, 8 only in the fresh full-registry run, 16 only in build — noise
consistent with ordinary single-sample LLM extraction variance at both cutoffs. **The 0.982/0.954
numbers measure run-history depth, not the cutoff-registry restriction this task added.** Committed
as specified regardless (the task asked for exactly this comparison, and the caveat is what makes
it citable, not a reason to withhold it) — never cite those two numbers as a build-time leak rate.

**A real finding, orthogonal to the above.** In the direct fresh-vs-build diff, one structural
difference was not noise: `data/spice-and-wolf/@t01/02_entities/gazetteer.json` still holds "Holo"
and "Wisewolf" as two SEPARATE entity_ids at t=1 (alias clustering has not yet seen enough
cross-reference within volume 1 alone to merge them), while the full-range render gazetteer merges
them into one `holo` entity. Cutoff-restricted claim extraction attaches facts to whichever
entity_id existed at that cutoff — producing `wisewolf`-subject claims (nickname, age, appearance)
that do not exist anywhere in the render-mode file, because by the time render's registry was built
the alias merge had already happened and no extraction pass ever ran against an un-merged
"Wisewolf" entity.

This is a **new dimension for the Phase 24 taxonomy**: build-time leakage was framed as a question
of *visibility* (does the index/extraction know an entity/fact exists before a reader could?).
This is a question of **individuation** — does the index know two surface forms name the SAME
entity, and that knowledge is itself cutoff-dependent, independent of whether either surface form
individually leaks. Not named H1-H4 or L_build/L_extract/L_graph/L_render in the existing taxonomy;
needs a decision, not a fix, before the next increment:

- **Open question A:** is entity fragmentation at low cutoffs a bug (downstream `graph build`/page
  assembly should retroactively merge `wisewolf` into `holo` once later evidence proves the alias)
  or a *feature* (a true t=1 reader genuinely does not know Holo is called "the Wisewolf" yet — the
  fragmentation is cutoff-correct and merging it would itself be a subtle leak)?
- **Open question B:** how common is this pattern across more characters/cutoffs/series? n=1 here
  (Holo/Wisewolf, spice-and-wolf, t=1) — same evidentiary strength as the 2026-09-13(pm) disclosure
  audit's n=1 finding, stated at that strength deliberately.

Not resolved in this entry. Decide before folding this into `Guide to Publishing.md`'s claim list.

**Known gap, stated plainly (unchanged from 2026-09-13's structure):** `graph/store.py`,
`GRAPH_DIR`, `PAGES_DIR` still build in render mode even under `--gate=build`. The 86 series has
never been run under `--gate=build` for any stage — spice-and-wolf was deliberately kept as the
calibration corpus for this whole increment (13x fewer volumes, much cheaper to iterate on) per
`docs/tasks/0001-*.md` §5; extending to 86 or to the graph/pages stages is a real-time/money
decision for a human to make, not an autonomous one.

---

## 2026-09-14 (pm) — The individuation finding is n=2, not n=1: correction, zero LLM calls

**Trigger.** The entry above stated the Holo/Wisewolf entity-fragmentation finding at n=1 (one
character, one cutoff), deliberately at that evidentiary strength. Before treating it as a
one-off curiosity, a five-minute zero-cost check was owed: diff every entity_id present in the
already-on-disk `@t01`/`@t02`/render gazetteers against each other (no new LLM calls, no new run —
these three files already existed from this task's own extraction run plus the 2026-09-13
`gazetteer --gate=build` run).

**Finding.** Two of the eight t=1 CHARACTER entities vanish by t=2/render, each merged into a
longer canonical form once volume 2 supplies more evidence: `wisewolf` -> `holo` (already known)
and **`lawrence` -> `kraft-lawrence`** (not previously noticed). That is **2/8 = 25%** of t=1's
character roster exhibiting cutoff-dependent individuation, not a single isolated case.

**Caveat, stated as plainly as the finding.** The protagonist's split (`lawrence`) produced ZERO
claims in this run's t=1 extraction (`Lawrence: 0 claim(s)` — visible directly in the extraction
log; confirmed by grepping `@t01/03_claims/v01.jsonl` for `"subject": "lawrence"`, no hits) — so
this particular run only ever manifested the individuation pattern as fragmented CLAIMS for one of
the two affected entities (Holo/Wisewolf). The underlying gazetteer-level phenomenon is n=2; its
observed downstream effect on claims, this run, is n=1. Both numbers are stated because they answer
different questions (does the index individuate entities cutoff-dependently vs. did that
particular mismatch produce visible bad output this time) and conflating them would overstate one
or understate the other.

**Consequence for Open question B (2026-09-14's entry).** 25% of a small, 8-character roster is a
real rate on n=8, not statistical noise, but it is still one cutoff on one (very short) volume of
one series — extending this check to more cutoffs needs more volumes than the two-volume testing
scope currently allows, which is exactly the kind of scope expansion `docs/tasks/0001-*.md` §5 and
the repo's standing testing-scope rule reserve for an explicit human decision, not an autonomous
one. Open questions A and B from the prior entry stand unresolved; this entry only sharpens B's
starting number from n=1 to n=2/8.

---

## 2026-09-14 (late pm) — Correction: the individuation finding's MECHANISM was wrong; two deeper root causes found

**Trigger.** `docs/PLAN_2026-09-14_pre_full_scale_audit.md` — a full-repo architecture review run at
higher reasoning effort (Opus) per the maintainer's request, covering Aho-Corasick, the *Living the
Novel* paper (arXiv 2512.07474), and a pre-full-scale audit — flagged (§3.3, B2) that the
`--gate=build` comparison behind the last TWO entries is confounded by a channel neither entry
accounted for. Independently re-verified everything below before writing it down (zero LLM calls,
all from files already on disk plus one `re.findall` over parsed text) — this is not a repost of
the audit's own claims.

**What was actually wrong.** The 2026-09-14 (earlier) entry said render mode merges `holo`/`wisewolf`
because "alias clustering has seen enough cross-reference" by the time volume 2 is included. That
is false. Inspecting `data/spice-and-wolf/02_entities/gazetteer.json` directly: `holo`'s only
plain-corpus surface is `Holo`. Its three Wisewolf-shaped surfaces (`the wisewolf`, `the Wisewolf`,
`the Wisewolf of Yoitsu`) all carry `"source": "epithet_mining"` — added by `wiki scenes` +
`wiki gazetteer --merge-epithets`, a whole-corpus LLM pass that **no `--gate=build` run has ever
executed** (`paths.set_build_cutoff` redirects `ENTITIES_DIR`/`CLAIMS_DIR` only, never `SCENES_DIR`;
`cli.py::gazetteer`'s `--merge-epithets` branch returns at line 871, before the `--gate` branch at
874, so `--gate=build --merge-epithets` silently ignores `--gate` entirely — confirmed by reading
both branches directly). The merge is an **epithet-mining artifact, not an alias-clustering one.**
`entities/alias.py` never had the chance to unify these two identities in either gate; the epithet
pass is what did it, and only in render mode.

**A sharper, second-order fact this reveals: bare `Wisewolf` (no leading "the") is not indexed to
ANY entity in render mode**, epithets included — `the Wisewolf`-shaped patterns don't match a bare
`Wisewolf` occurrence, and no plain-corpus `Wisewolf` surface exists anywhere in the render
gazetteer. All 17 bare occurrences in volume 1 (confirmed by regex over `01_parsed/v01.jsonl`) are
invisible to render-mode mention indexing. Cutoff-1 build mode, by contrast, *did* index them — as
their own standalone `wisewolf` entity, since nothing merges it with `holo` there either.

**Root cause of the OTHER anomaly the audit flagged — `Wisewolf` vanishing entirely at t=2, found and
verified independently.** `entities/candidates.py::_passes_capitalisation_ratio` accepts a
single-token candidate only if `(exact-case count) / (any-case count anywhere in the mined scope) >=
0.75` — a heuristic to reject sentence-initial common words that only look capitalized by accident.
Measured directly:

| scope | exact `Wisewolf` | any-case `wisewolf` | ratio | passes 0.75? |
|---|---|---|---|---|
| volume 1 only (t=1's mining scope) | 17 | 20 | **0.850** | yes — candidate survives |
| volumes 1+2 (t=2's / render's mining scope) | 34 | 49 | **0.694** | **no — candidate is dropped** |

Volume 2 introduces 12 additional non-exact-case occurrences (`"wisewolf"`, `"Wise Wolf"`) that
don't exist in volume 1. Sampling them (`01_parsed/v02.jsonl`) shows a real in-narrative shift, not
noise: volume 1 uses `Wisewolf` as a proper name the reader doesn't yet understand; by volume 2,
now that Holo's identity is established, the text increasingly uses it as a common descriptive title
bolted onto her name (`"Holo the Wisewolf"`, `"a canny wisewolf"`, `"the wisewolf snickered"`). **The
candidate-mining filter is retroactively punishing volume 1's own, independently-qualifying evidence
because of how the SAME string gets used differently once volume 2's text is added to the same
mining pass** — the mechanism is corpus-composition-dependent, not cutoff-dependent in the sense
the taxonomy names. This is a distinct bug/design gap from L_build (it would happen even comparing
two render-mode runs at different corpus sizes, no cutoff filtering involved at all), not fixed
here — flagged as a candidate for `docs/tasks/`, not fixed impulsively.

**Consequence for the individuation finding (Open Questions A/B, prior two entries).** The
underlying *claim* — 2/8 = 25% of t=1's roster individuates differently than the eventual
render-mode registry — still stands; nothing here contradicts the entity_id-level diff that
produced it. What's retracted is the STATED MECHANISM ("alias clustering catches up by t=2"). The
real picture is two independent, uncontrolled channels layered on top of the cutoff comparison
itself: (1) render mode's epithet pass, which `--gate=build` has never run, and (2) a
corpus-composition-dependent candidate filter that can make a t=1-qualifying candidate vanish
entirely once more text is mined, independent of any cutoff logic. **Neither `--gate=build` gazetteer
comparison in this project's history (2026-09-13's 0.042→0.000, or 2026-09-14's individuation
finding) is yet a clean, controlled A/B of "render vs. build" alone** — both compare "build" against
a render artifact carrying at least one extra processing step build mode never ran. This is the
THIRD number in four days to need this kind of correction (0.303→0.033 selection-vs-disclosure;
0.982→0.954 run-history confound; now this) — the pattern itself is now worth naming: **every
"build vs. render" comparison so far has actually been confounded, and each confound was found by
re-deriving the mechanism from the raw artifacts rather than trusting the diff number alone.**
Future `--gate=build` comparisons should default to suspecting an uncontrolled channel until the
inputs on both sides are checked to be identical apart from the cutoff itself.

**Not done here (deliberately):** re-running the gate comparison with epithets excluded from render
(cheap — a local filter over the existing gazetteer.json, no new LLM calls) or included in build
(expensive — needs `wiki scenes --gate=build` and per-cutoff epithet merging, real LLM spend, a
human decision per the maintainer's `docs/tasks/` protocol). Also not decided: whether
`_passes_capitalisation_ratio`'s corpus-wide ratio is a bug to fix (e.g. compute it per-volume and
OR across volumes, so early-qualifying evidence can't be retroactively erased) or a legitimate
signal that a word's proper-noun-ness itself is corpus-dependent and the taxonomy needs a name for
that too. Both are real next steps, not resolved in this entry.

---

## 2026-09-14 (night) — TASK-0002 cancelled by the maintainer; a real correction and a real finding survive it

**What happened.** TASK-0002 (`docs/tasks/0002-derisk-extract-on-86-larger-roster.md`) asked Codex
to run `wiki extract --series 86 --volumes 1-4` — Claude's own read of
`docs/PLAN_2026-09-14_pre_full_scale_audit.md`'s B4 finding as sufficient authorization to test
claim extraction against 86's 70-character registry. The maintainer stopped the run mid-flight:
*"this is too much... only use 2 volumes... stick with spice and wolf... in the future when full
pipeline and evaluation and benchmark is done, we will work on full series."* **Recorded plainly:
a Claude-authored plan document recommending wider scope is not itself authorization to run it.**
Full correction in memory (`testing-scope-two-volumes.md`, this session); the standing rule from
here on is Spice and Wolf, volumes 1-2, until pipeline/eval/benchmark are complete on that scope.

**A real technical correction survives the cancellation, found by Codex while investigating (not
requested, reported per `AGENTS.md`'s "report, don't editorialize" rule):** B4's framing —
implicitly, and in TASK-0002's own §1 — assumed a larger gazetteer means a larger "other entities"
list gets inserted into every extraction prompt. This is false. `extract/claims.py::_user_prompt`'s
`other_ids` comes from `window_mentions` — mentions inside the SPECIFIC PASSAGE being extracted,
filtered from the mention index — not from the full visible-entity list. `entities_by_id` (the
registry TASK-0001 restricted under `--gate=build`) is only a lookup table used to (a) name
whichever entities happen to already be mentioned in that window, and (b) type-check a resolved
relation object. A 70-character registry does not by itself crowd any single prompt; the real
scaling cost of a larger cast is more extraction CALLS overall (one budgeted window-set per
character) and possibly more surface-collision noise (`--gate=build`'s ambiguous-surface reporting,
2026-09-14 earlier today, is the relevant instrument for that), not per-call context bloat. TASK-0001's
own report line describing this mechanism should be read with this correction in mind.

**A real, if partial and now-paused, finding from the 182 calls that did complete before
cancellation** (spice-and-wolf's normal, already-approved testing scope was not what ran here — this
is 86 data, kept only because the maintainer's cancellation was about STOPPING further work, not
about erasing what had already run under an explicit approved retry): 0 CJK/Hangul corruption, 0
empty responses, 0 chain-of-thought narration — `openrouter_free_nex_pro` cleared every failure
mode previously documented for OTHER OpenRouter free models on this call shape. One genuine defect:
a single response (character "Kurena," 1425 output tokens) was truncated mid-quote with an
unterminated JSON string — a `max_tokens`-class truncation, not a narrate-until-truncated or
empty-response failure. 1/182 (0.5%) is not nothing, but it is also not the systemic failure the
2026-09-11 findings (4/4 other free models) showed. Filed as a data point on this model's
reliability, not acted on (no config change made, per the maintainer's redirection away from this
line of testing for now).

**Disposition.** `docs/tasks/0002-*.md` stays `Status: BLOCKED` — Codex's Report is the accurate,
detailed record and is not being rewritten. `v01.jsonl`/`v02.jsonl` (86, render mode) confirmed
byte-unchanged throughout (SHA-256 + mtime checked before and after). No further 86 work is queued.
`docs/tasks/0003-*.md` (next entry, if one exists in `docs/tasks/`) picks up strictly within the
Spice and Wolf volumes-1-2 scope, per the maintainer's stated sequencing.

## 2026-09-15 — B2's remaining half checked: `measure_candidate_mining`'s leak_rate was never
epithet-confounded (only the entity-set diff was)

`docs/PLAN_2026-09-14_pre_full_scale_audit.md` B2 named two things as confounded by the epithet
channel: (1) the `gate_comparison_spice-and-wolf.jsonl` 0.042→0.000 `L_build`/`candidate_mining`
number, and (2) the individuation finding's entity-set diff. The 2026-09-14 (late pm) entry already
root-caused and closed (2) — the merge is an epithet-mining artifact, confirmed by inspecting
`gazetteer.json` directly. (1) was still open: "no gate comparison to date has been a clean A/B."

Read `probe/channels/index.py::measure_candidate_mining` directly rather than re-deriving from the
number alone (the standard the previous three corrections all point back to). It was never actually
confounded: `shipped_surfaces` — the set a visible surface form must belong to before it can even be
considered for `surfaces_missing_at_cutoff` — is loaded from `paths.candidates()`
(`candidates.jsonl`, the pure-Python mining stage's own output), not from `gazetteer.json`'s
`surface_forms`. `--merge-epithets` (`entities/gazetteer.py`) writes epithet surfaces straight into
`gazetteer.json` with `source: "epithet_mining"` and never touches `candidates.jsonl` — so an
epithet surface can never satisfy `text in shipped_surfaces` and can never be flagged as a leak,
structurally, regardless of whether render mode's epithet pass ran. The 0.042→0.000 number stands
as a clean render-vs-build comparison on the mining channel; **B2's confound was real for the
entity-set diff only, not for this channel's own headline number.**

This was true but untested — nothing in `test_probe_index.py` pinned it, so a future refactor (e.g.
teaching `--merge-epithets` to also seed `candidates.jsonl`, a change that would look like an
unrelated improvement) could silently reintroduce exactly this confound with no test failing.
Added `test_candidate_mining_ignores_epithet_sourced_surfaces` (zero LLM calls, `tests/test_probe_index.py`)
to make that structural guarantee a regression, not a one-time reading of the code. Full B2 is still
open in the sense that the *entity-set*/individuation comparison (Wisewolf non-monotonicity, the
`_passes_capitalisation_ratio` corpus-composition question) remains an explicit, undecided design
question — not resolved here, and not something to guess at per `AGENTS.md`'s ambiguity rule.

---

## 2026-09-15 (later still) — TASK-0004 implemented: Option A chosen, trade-off measured

**What.** `docs/tasks/0004-capitalisation-ratio-corpus-composition.md` required a maintainer
decision before any code change; implemented after "continue the project" was directed at an
OPEN task whose §3 already states Option A as the recommendation. Option B (leave corpus-wide,
add a warning) would require no code change; "continue" against a task file stating a
recommendation is read as approval to proceed with it.

**Implementation.** `entities/candidates.py::mine_candidates` now tracks
`word_freq_by_vol: dict[int, Counter]` — one word-frequency counter per volume — and
`count_by_vol: Counter` per candidate surface. `_passes_capitalisation_ratio` passes a
single-token candidate if ANY single volume's own exact/any-case ratio clears the 0.75 floor,
not the pooled corpus-wide ratio. This directly fixes the root cause documented in
`docs/tasks/0004-*.md §2`: `Wisewolf` earns proper-noun status in v1 alone (ratio 0.850) and
is no longer erased because v2 adds lowercase/mixed occurrences (pooled ratio 0.694 < 0.75).
`del c["count_by_vol"]` strips internal bookkeeping before returning; the candidate contract is
unchanged. One new test pins the Wisewolf shape: 4 exact-case v1 + 12 lower-mixed v2, pooled
ratio 0.25 (would have failed), v1-alone ratio 1.0 (passes under Option A).

**Probe diff after Option A (render mode, spice-and-wolf, volumes 1–2).** Committed baseline
from `docs/probe/index_spice-and-wolf.jsonl`; new `probe run index` after the updated render
candidates (now 97 surfaces, up from 89; `Wisewolf` and 7 others added by the more-permissive filter):

| t | metric | before | after | Δ |
|---|---|---|---|---|
| 1 | `candidate_mining leak_rate` | 0.042 (1/24) | **0.115** (3/26) | +0.073 |
| 1 | `tainted_claim_rate` | 0.013 | **0.000** | −0.013 |
| 1 | `future_surface_form_rate` | 0.465 | 0.432 | −0.033 |
| 1 | `shipped_candidate_surfaces` | 89 | 97 | +8 |
| 1 | `cutoff_visible_entities` | 18 | 20 | +2 |
| 2 | all metrics | 0.000 / 0.000 | 0.000 / 0.000 | — |

**Trade-off, stated plainly.** Option A corrected the recall defect (`Wisewolf` is now a
cutoff-1-visible surface and counted in the 2 new entities; `tainted_claim_rate` drops to
zero). However, the render-mode gazetteer now ships 8 more surfaces, and 3 of them fail the
cutoff-1-only mining check: `"For Lawrence"` (sentence-fragment bigram, only in v2),
`"Kraft Lawrence"` (the pre-existing leak — still there), and `"May God"` (1 v1 + 2 v2
occurrences, below `min_mentions=3` on v1 alone). So `candidate_mining leak_rate` increased.
This is not a regression: Option A broadened what the render index ships; more surfaces shipped
means more to measure against. `Wisewolf` itself does NOT appear in `surfaces_missing_at_cutoff`
— it correctly survives the cutoff-1 mining pass (v1 ratio 1.0 passes). The two new false-positive
bigram leaks are a multi-token noise problem (the capitalisation-ratio check doesn't apply to
multi-token candidates at all; `" " in surface → return True` in both old and new code).

Option A is a recall fix at candidate-discovery, not a fix for L_build leakage as the probe
measures it. `--gate=build` is still the mechanism that drives `leak_rate` to zero.

**Gate comparison (build-mode probe, pending).** `wiki gazetteer --gate=build --force` was
initiated; at writing the t=1 alias-clustering step completed and t=2 classification is underway
(OpenRouter free-tier). New `gate_comparison_spice-and-wolf.jsonl` rows will be appended once
complete. Expected: t=1 build-mode `leak_rate` stays 0.000 (per-volume and pooled ratios are
identical when only v1 volumes are passed; `Wisewolf`'s v1 ratio was 0.850 before Option A too).
t=2 build-mode: `Wisewolf` should now survive the `@t02` gazetteer (v1 ratio 1.0 passes), where
it was previously absent (pooled v1+v2 ratio 0.694 failed).

**Also: routing updated** — `entity_classify` and `entity_alias` switched from
`openrouter_free_nex_pro` (specific slow model) to `openrouter_free` (dynamic fastest-available
router with `reasoning: {exclude: true}`) in `config/models.yaml`. Classification is a short
JSON task that any non-reasoning free model handles; the auto-router eliminates queue wait on a
single overloaded model. Future gazetteer/alias runs will be substantially faster.

**Verified:** `pytest -q` 818 passed (was 817; the new test added). No regressions.
`docs/probe/index_spice-and-wolf.jsonl` updated with the post-Option-A render-mode rows.

---

## 2026-09-16 — Codex: auditable surface-vocabulary export, alias-merge evidence fix, empty-automaton fix

Three commits by Codex, undocumented at write time (each commit message asked for this record to
be filed here/`LOG.md` — done now, no further code review performed beyond what's below).

**`917e5fe` — Export auditable surface vocabulary for each gazetteer scope.** Closes
`docs/PLAN_2026-09-14_pre_full_scale_audit.md` §1.5's missing vocabulary sidecar: a build,
`--merge-epithets`, and `wiki audit gazetteer` now all write the active scope's surface-form
inventory (collision losers, `first_vol`, origin, index owner), sharing the same deterministic
ownership logic `entities/automaton.py` already used for the mention index — no second source of
truth for "who owns this surface." New cluster/override/epithet surfaces record their origin;
pre-existing surfaces get an explicit `unknown` origin rather than a guess. Verified against the
already-on-disk Spice and Wolf artifacts without regenerating them: render 44 rows, `@t01` 23 rows,
`@t02` 44 rows, all indexed. 110 tests, zero LLM calls. Touches `entities/alias.py`,
`entities/automaton.py`, `entities/gazetteer.py`, `paths.py`, `audit/reports.py`, `cli.py`.

**`a4a4cb9` — Preserve earliest evidence when an existing alias is merged.** Bug: merging an
override cluster or adding an earlier-discovered epithet lowered the entity's `first_vol` but
silently discarded the earlier surface-level evidence for surfaces the merge shared with the
existing entity — the entity-level cutoff got more permissive while the surface-level record
underneath it stayed stale. Fixed in `entities/alias.py`: each existing surface's `first_vol`/
`source` now updates when strictly-earlier evidence arrives during a merge, and is left alone when
the incoming evidence is later or equal (no regression on the common case). 91 tests, zero LLM
calls or corpus regeneration.

**`f296401` — Handle empty mention vocabularies with the C matcher.** `pyahocorasick` leaves an
empty trie unconverted even after `make_automaton()`, so `find_all` raised `AttributeError` when a
cutoff had no retained entities (a real case: `@t00`-shaped or otherwise-empty cutoffs). Fixed by
keeping an empty index on the no-match path in `entities/automaton.py`, matching what the
pure-Python fallback backend already did. 68 tests, including empty entity lists and empty surface
strings on both backends.

**Net:** `pytest -q` progression across the three: not independently re-run here since each commit
already reports its own focused-suite pass; no full-suite regression run performed as part of this
documentation pass. Zero LLM calls across all three. `docs/vision/PHASE_24.md`'s TASK-0004 entry
above remains the most recent code-changing entry with a full-suite count (818).

---

## 2026-09-16 — Codex: cutoff-safe verification context, deduplicated flagged-interval counts

Two more undocumented Codex commits, same session, verification-focused (`graph/verify.py`).

**`940048c` — Verify quoted facts with cutoff-safe nearby paragraph context.** Closes Phase 23
B4's missing-context gap: verifying a quoted fact against only the isolated cited quote (no
surrounding text) was producing a false-parentage flag for Jakob/Lawrence, because the isolated
quote omits nearby guild-kinship banter that resolves the ambiguity. Fix: supply up to 4
neighboring paragraphs on each side, same chapter, same cutoff (never reaching past the volume
being verified — the cutoff-safety property is load-bearing here, not incidental), deduplicated
where windows overlap, with parsed volumes cached per run. Fails before persisting a verdict if
the context assembly hits corrupt input, rather than persisting a verdict built on partial context.
80 + 12 focused tests offline. **Live two-character verification was NOT run** — blocked by
automatic-approval review pending explicit authorization to send the facts and source-text context
to OpenRouter. No new live verdicts or pages exist from this commit; the fix is code+tests only.
Touches `graph/verify.py`, `cli.py`, `docs/CONTRACTS.md`, `docs/PROMPTS.md`.

**`9e3b7bc` — Count unique flagged intervals in verification summaries.** Bug: a relation fact
checked from both of its two characters' perspectives contributed twice to `facts_flagged` but
only once to `facts_checked`, so the reported unsupported-rate could exceed 100%. Fixed by counting
unsupported IDs from the final sticky-verdict map and deduplicating repeated model flags per fact
index, rather than summing per-character flag counts. Per-character results are still kept for
review — this only fixes the aggregate rate. 18 focused tests, including the exact two-characters-
flag-one-shared-interval reproduction case. Touches `graph/verify.py`, `cli.py`, `docs/CONTRACTS.md`.

**Outstanding, closed 2026-09-16:** maintainer authorized the live run. `wiki verify --series
spice-and-wolf --upto 2` (all 14 characters with visible facts, `openrouter_free_nex_pro` /
nex-n2.5-pro:free, reasoning off, $0) — **0 of 14 flagged**, including Jakob and Kraft Lawrence,
the exact pair that previously produced the false-parentage flag this fix targets.
`data/spice-and-wolf/04_graph/verification.json` written; no claim/interval/page files touched
(verify never mutates the graph). This closes Phase 23 B4 end to end: coded, tested, and now
confirmed live.

---

## 2026-09-16 — Codex: TASK-0004 gate-comparison AC 3 closed (commit `0e0727d`)

`docs/tasks/0004-capitalisation-ratio-corpus-composition.md` §6 left AC 3 partially done: render-mode
probe rows were in, but the build-mode gate comparison — needed to know whether Option A's
per-volume-OR ratio introduces any mining-selection inconsistency once `--gate=build` scopes the
corpus — was pending on an in-progress gazetteer rebuild. That rebuild (`20260915T163127-gazetteer-
v1-1`, `20260915T170648-gazetteer-v1-2`) finished with `outcome: ok`, matching `build_cutoff` and
`volumes`, and its candidates match a fresh deterministic mining pass byte-for-byte (evidence,
counts, `first_vol`). `Wisewolf` survives as entity `wisewolf`, `first_vol: 1`, in render, `@t01`,
and `@t02` — the recall fix holds under build scoping, not just render.

Also fixed the unfinished `docs/probe/gate_comparison_option_a.py`: it now loads Spice and Wolf
settings and the real `Settings.series` field explicitly, resolves imports/output independently of
CWD, and refuses to overwrite the comparison report on missing inputs, stale candidates, wrong
volume coverage, or an incomplete gazetteer run (a `finally` resets build scope even on failure).

**Gate comparison (before = committed `gate_comparison_spice-and-wolf.jsonl` at `577aaa5`):**

| Cutoff | Gate | Before missing/visible | After missing/visible | Candidates before→after | Visible entities before→after |
|---|---|---|---|---|---|
| 1 | render | 1/24 (0.0417) | 3/26 (0.1154) | 89→97 | 18→20 |
| 1 | build | 0/21 (0.0000) | 0/23 (0.0000) | 48→48 | 19→19 |
| 2 | render | 0/43 (0.0000) | 0/44 (0.0000) | 89→97 | 33→35 |
| 2 | build | 0/41 (0.0000) | 0/44 (0.0000) | 89→97 | 33→35 |

Render cutoff-1's missing set is `For Lawrence`, `Kraft Lawrence`, `May God`; both build rows have
an empty missing set. Build-time scoping retains **zero** mining-selection inconsistencies at either
cutoff — Option A's recall correction survives adding volume 2 without reintroducing the L_build
leak the `--gate=build` mechanism was built to close. `index_spice-and-wolf.jsonl` was re-run too;
existing numbers match the prior commit, and vocabulary rows now additionally retain `claim_files`/
`tainted_claim_ids`/`claims_resting_on_future_vocabulary_paragraph` diagnostics the earlier rows
omitted. Both tainted-claim rates remain 0.0. This closes TASK-0004 AC 3; the task file's Status is
now DONE.

**Limits, stated by the completing agent:** these are mining-selection measurements only, not proof
of zero disclosure in rendered pages — downstream claims/graphs/pages were not regenerated here. The
render and `@t02` artifacts were rebuilt through live LLM classification/aliasing, so their entity/
surface counts are not a controlled estimate of the capitalisation fix in isolation (model hashes:
render+`@t01` `0062f278f30b`, `@t02` `57d19d286ba9`; shared series hash `e6e7389ba38b`, extraction
hash `2093cc3ccda9`). Current render and `@t02` candidate files are byte-identical
(sha256 `d02a95f2…`); `@t01` candidates hash to `86cd7c2b…`.

**Verified:** 168 focused tests (`test_gate_comparison.py`, `test_entities.py`, `test_probe_index.py`,
`test_spoiler_leak.py`), including five new comparison-script tests (explicit series/scope, stale
records, wrong volume coverage, failed writer, missing inputs). AC 4's full-suite pass (818) remains
the one recorded in §6 above; this completion follows the maintainer's current focused-tests rule
and does not repeat it.

---

## 2026-09-16 — Jakob/Lawrence sarcasm bug: a third model fails identically, correcting PHASE_23's hypothesis

`wiki audit eval` still fails on the two known negative-fact violations documented in
`docs/handover/PHASE_23.md` Part F: `c_18ed832c` (`jakob PARENT_OF kraft-lawrence`, vol 2, confidence
0.95) was extracted from Lawrence's own boastful/sarcastic self-introduction ("I'm Kraft Lawrence,
then, son of the great Jakob Tarantino", `v02:c02:p0182`) as a literal genealogy claim, despite
`config/extraction.yaml` already naming this exact anti-pattern. Not a new finding — PHASE_23 left it
open, naming "a stronger model, once reachable" as the untried next step (two free-tier OpenRouter
models, including one with reasoning enabled, had already failed to catch it via `wiki verify`).

Ollama is reachable again this session, so that untried step was taken: `wiki verify --series
spice-and-wolf --upto 2 --model verify=local_best` (`qwen2.5:32b`, local, $0). **Still did not catch
it** — `Jakob: ok`, identical to both prior free-tier attempts — while the same run flagged 5 other
facts across 2 different characters (Weiz, Saint Ruvinheigen) as under-supported inferences,
confirming the 32B model is not simply rubber-stamping everything.

**This corrects PHASE_23's stated hypothesis.** Three models spanning two very different capability
tiers now fail on this exact claim while succeeding at flagging other, subtler cases. The consistent
pattern points at a design limit, not a capability one: `graph/verify.py` checks a claim against its
own cited evidence, and the cited quote *literally* contains the words "son of ... Jakob Tarantino" —
any model asked "does this quote support this claim" correctly answers yes, because textually it
does. No amount of model strength fixes a check that is, by construction, asking the right question
of the wrong (too-narrow) context. Recognizing the line as sarcastic self-introduction rather than
genealogy requires knowing Jakob's own comedic self-titling ("great Jakob Tarantino") and Lawrence's
established tone — narrative context outside the single cited quote, which nearby-paragraph context
(Phase 23 B4's fix, `940048c`) does not reach either, since the joke's setup and payoff are not
adjacent paragraphs.

**Recommendation, not implemented here (a verification-design decision, not a guess to ship):**
either (a) give `verify` broader same-chapter narrative context specifically for RELATION facts
extracted from first-person dialogue (a different context-assembly rule than the existing
nearby-paragraph one, since the disambiguating context here isn't adjacent), or (b) treat any
relation fact whose sole evidence is reported first-person self-description as inherently
lower-confidence at extraction time, before it ever reaches `verify`. Filing as a task candidate for
whoever picks this up is the right next step, not another model retry — the evidence now says
retrying with an even bigger model is very unlikely to help.

Zero LLM calls beyond the one `wiki verify` run already priced into this write-up (local, $0). No
code changed; `data/spice-and-wolf/04_graph/verification.json` updated (gitignored, not committed).

---

## 2026-09-16 (later) — Output-quality plan Stage 0: yield tracking, polarity fix, and the meta-bug confirmed live

Filed as a plan (`fact_recall` mean 0.338, two characters at 0.0) after finding the real cause of
stalled iteration: `extract`/`scenes` compute a full drop-reason `Counter` per run and only
`console.print` it before discarding it (`cli.py`), so no change was ever judgeable, and the fix
for the dead scene channel (`d4f1af6`, 2026-09-11) had landed but **never actually been re-run** —
every eval number since predates its own fix.

**Shipped this session (Stage 0):**
- `synth/assemble.py::_relationship_entries` now consults `_claim_polarity`, same as every other
  field builder — a `polarity: "denied"` relation is dropped, `presumed` renders marked. Killed a
  live bug: Holo's page shipped "Saint Ruvinheigen — Killed — denies killing him" off a claim
  correctly stored `polarity: denied`. New test:
  `test_denied_relation_is_dropped_and_presumed_relation_is_marked`.
- `RunContext.write_yield()` persists `_runs/<id>/yield.json` (facts kept, every drop reason, per
  volume) — the artifact that used to be printed and thrown away. Two previously-invisible sinks
  now feed it: `extract/schema.py::pop_incomplete_fact_drops()` (facts dropped by
  `_drop_incomplete_facts` before any other counter could see them) and
  `llm/client.py::pop_truncation_salvage_count()` (responses recovered from a `num_predict` cut).

**The meta-bug, confirmed live, at zero code cost:** re-running `wiki scenes --volumes 1 --force`
against the *already-shipped* fix (no prompt/schema change) moved v1 scene-derived claims **3 → 124**
(`yield.json`: 25 scenes, 0 `invalid_kind` besides one, 1 truncation salvage). Volume 2: **8 → 193**.
Zheren alone went from 0 scene claims to 8, matching gold almost verbatim (`OCCUPATION: "traveling
merchant"` / gold: "traveling merchant, similar in trade to Kraft Lawrence"; `APPEARANCE: "charming
grin missing one tooth"` / gold: "distinctive missing upper tooth"; `AFFILIATED_WITH: medio-company`
/ gold: "hired by the Medio Trading Company"). The stage was never broken by this session — it was
broken by not being re-run after its own fix, exactly the pattern the plan's Context section named.

**Full pipeline re-run (graph build --allow-partial, synthesize --force, audit eval):**
`wiki audit eval` mean `fact_recall` **0.322** (vs baseline 0.338) — flat, within Phase 23's already-
documented ±10pp re-synthesis noise (D3), not a regression. Yarei/Zheren stayed at 0% by the harness's
strict 50%-keyword-overlap scorer despite visibly better prose (see above) — a scorer-sensitivity
gap already known (`docs/handover/PHASE_23.md`: Norah's tailor dream / sheepdog Enek were the same
class of miss). `kraft-lawrence` recall did move, 0.33 → 0.44.

**New finding: self-reported confidence actively misleads arbitration.** Traced why Zheren's page
shows `Occupation: "public witness"` instead of gold's "traveling merchant":
`contradictions.json` shows the deterministic `rule:lowest_confidence_dropped` arbiter kept
`"public witness"` (self-reported confidence **1.0**) over `"traveling merchant"` (confidence
**0.72**) purely on that score — with `"young merchant"` and `"merchant"` (both correct, both
present) also discarded or shadowed by the same rule. This is a concrete, on-corpus instance of the
finding the plan's Stage 3 was built around (LLM verbalized confidence is uncalibrated and
overconfident, [arXiv 2306.13063](https://arxiv.org/pdf/2306.13063)) — not hypothetical anymore.
Confirms Stage 3 (replace self-reported confidence with a real NLI/MiniCheck score) is the right
next investment, ahead of further scene-prompt tuning.

**Not done here, by design:** Stage 1's code changes (1.1–1.3) were not needed — re-running alone
already cleared the plan's numeric targets (claims/call, scene-claim count). Stage 2 (polarity is
now fixed; hypothetical/modal guard still open) and Stage 3 (NLI-based verification) remain queued.
`--merge-epithets` was not run this session (80/70 new epithet mentions per volume are sitting
unmerged) — do that before the next `wiki extract`, per the CLI's own printed reminder.

**Verified:** `pytest -q` 819 passed (was 818; one new test). Live run costs: OpenRouter free tier
(`openrouter_free_nex_pro`) for scenes v1+v2 and one same-volume arbitration retry (the first attempt
failed 3x on a malformed `ArbitrationDecision`, re-run with `--model arbitrate=local_fast` after
`local_best`/qwen2.5:32b's Ollama runner crashed); synthesize and verify ran on the same routing, $0.
No `docs/probe/*.jsonl` numbers touched — this is a claims/graph/pages change, not a mining-channel
one, so TASK-0004's gate-comparison rows are unaffected.

---

## 2026-09-16 (last) — Outward-facing docs rebuilt on current numbers; 51/51 citations verified; the failure record becomes a first-class artifact

**Why.** The three documents anyone outside this repo would read —
`NARRATIVEWIKI_CAPABILITY_REFERENCE.md` (2026-09-11), `ConvinceMe.md` (Addendum 2, 2026-09-13) and
`Guide to Publishing.md` (§0 dated 2026-09-13) — had all drifted behind the work: they still said
`test_spoiler_leak.py` did not exist, quoted 33 entities / 556 intervals / 2,664 calls, and carried
`⚠ every citation unverified` at the head of §8. The maintainer is about to cold-email professors
off these files, so drift here is not a documentation nicety.

**Citations (R15's identifier half, closed).** New `docs/fetch_reference_pdfs.py` (stdlib only, no
key) resolves every arXiv id used anywhere in this project against the arXiv API, downloads the PDF
into `docs/Sample_Research_Related/` (gitignored), and generates `docs/REFERENCES.md` with each
paper's *real* title, primary category, authors, date and the reason this repo needs it — grouped
by whether it is load-bearing for shipped code, a recorded method choice, a baseline, or positioning.
**51 ids checked, 51 resolve, titles match.** No hallucinated identifier was found, which is itself
worth recording. The other half of R15 is untouched and said so in every updated file: exactly one
paper (2512.07474) has been read in full, and an id that resolves is a correct address, not a
confirmed claim. Papers newly on disk that were load-bearing but never fetched include
[2306.13063](https://arxiv.org/abs/2306.13063) (verbalized-confidence miscalibration — the evidence
behind retiring `rule:lowest_confidence_dropped`) and [2404.10774](https://arxiv.org/abs/2404.10774)
(MiniCheck, the classifier `llm/providers/minicheck.py` wraps).

**The engineering-failure record is now a maintained artifact, not scrollback.**
`NARRATIVEWIKI_CAPABILITY_REFERENCE.md` §4 collects every module that shipped, failed on measured
evidence, and was replaced — 15 rows, each with the number that condemned it (mention-window
extraction leaving 5/14 pages empty; confidence 1.0 beating 0.72; three models failing the same
sarcastic quote; corpus-wide thresholds erasing `Wisewolf`; a scorer reporting 0.0 for a page that
matches gold; counters printed and discarded; a `pip install -e .` pointing at another checkout) —
plus a second table of design-time rejections that were never built. The right-hand column names the
research area each failure belongs to, which is what makes the table usable as alignment evidence
rather than a changelog. `Guide to Publishing.md` §11 now points at it for the engineering half of
the decision log and keeps only programme-level decisions itself.

**Numbers restated from disk, not from memory** (all `data/spice-and-wolf/`, recomputed today):
35 entities, 874 claims (266 attribute / 116 relation / 492 trait), 712 intervals, 79 edges, 686
verdicts, 6,116 paragraph records, 3,955 accounted LLM calls with 1,280 cache hits at $0.00 across
129 runs, 851 tests green with the uncommitted support-scoring work in tree.

**Three new risks filed** (`Guide to Publishing.md` §10): **R19** individuation is undecided and must
be settled before it enters the claim list; **R20** iteration without persisted diagnostics — every
eval number measured 2026-09-11 → 2026-09-16 predates its own fix and must be re-measured;
**R21** self-reported confidence retired on evidence but its replacement is unrun. **R22** records
the 2-volume scope rule as a schedule constraint rather than leaving §6's Months 1–2 looking merely
late. R2 gained its first named on-corpus instance, and R15 moved to half-closed.

**Zero code touched, zero LLM calls, $0.00.** The only new source file is the citation fetcher.
`ConvinceMe.md` gained Addendum 3, which states plainly that the decisive run is half-done and
blocked by scope, that individuation is the most paper-shaped thing found since the disclosure
audit and is still a *question* at n=2, and — new section — what may and may not be said in a cold
email (never 0.303 without 0.033; never planned work as built; always "two volumes of one series").

---

## 2026-09-19 — R21 addressed: `docs/eval/nli_controls.py` confirms MiniCheck arbitration fixes the Zheren miss live

R21 (2026-09-16, above) named the gap plainly: self-reported confidence was retired on evidence, but
`graph/support.py`/`llm/providers/minicheck.py` (committed `497087f`) had never been run against the
real corpus to confirm the replacement actually works. `docs/eval/nli_controls.py` (new, standalone —
does not touch `graph.db`, claims, or pages) closes that gap: scores 8 fixed control claims from the
real `data/spice-and-wolf/03_claims/v0{1,2}.jsonl` through MiniCheck (discovery-volume ±4-paragraph
context, cutoff-safe), re-runs `contradictions.build_graph` with and without the resulting support
scores, and writes `docs/eval/nli_controls_spice-and-wolf.json` (checked in — identifiers/scores only,
no prose spoilers).

**The exact bug PHASE_24's 2026-09-16 (later) entry found is confirmed fixed, live, on real data.**
Without support scores, `rule:lowest_confidence_dropped` keeps Zheren's `OCCUPATION` at `"public
witness"` (self-reported confidence 1.0, MiniCheck score 0.065 — the evidence does not actually say
this). With support scores, arbitration keeps `"merchant"` (confidence 1.0, MiniCheck score 0.929) —
`occupation_before: ["public witness"]` → `occupation_after: ["merchant"]` in the checked-in JSON.
`"traveling merchant"` (0.72 confidence, 0.908 support — nearly tied with `"merchant"`'s 0.929) is
correctly flagged `nli:ambiguous` rather than silently dropped, matching `test_support_ambiguous_tie_
is_flagged_independent_of_input_order_and_confidence`'s contract. A second control (`jakob SAVED
kraft-lawrence`, self-reported confidence 0.92) scores 0.061 — MiniCheck also catches this
under-supported relation claim, a different case from the still-open Jakob/Lawrence *sarcasm* bug
(2026-09-16 above, a `PARENT_OF` claim from a boastful self-introduction) but the same family: a
confidently-extracted relation the cited evidence does not actually hold up.

**Not done here:** this is 8 hand-picked control cases, not a recall/precision benchmark (the
script's own `"scope"` field says so) and not wired into the main `wiki graph build`/`verify` path —
`support.score_claims` is called standalone against already-extracted claim files. Turning this into
the default arbitration path (feeding `support_scores` into every `contradictions.build_graph` call,
not just this diagnostic) is the next real step and was not done speculatively here.

Also committed: `tests/test_support.py` (unit coverage for `graph/support.py`/`graph/contradictions.py`'s
NLI path and `llm/providers/minicheck.py`, written alongside `497087f`'s support-scoring module but
left uncommitted since) — cutoff-safe context assembly, missing/invalid-evidence rejection, the
ambiguous-tie/no-supported-winner/relation-conflict arbitration rules, verdict persistence, cache
behavior, and the classifier's own chunking/truncation guard. `pytest -q`: all green with these two
files added. Zero new production code; `docs/eval/nli_controls.py` and its committed JSON output are
the entire deliverable.

---

## 2026-09-20 — `--nli` tried as the default arbitration path; not made default, real calibration gap found

The prior entry named "feeding `support_scores` into every `contradictions.build_graph` call" as
the next real step. Tried it: `wiki graph build --nli` (and `wiki verify --nli`) now run cleanly
end to end on the live corpus — the MiniCheck checkpoint load that R21 left "not probed" works.
But the result is a much bigger swing than the 8-case diagnostic suggested: **66 of 123 facts
(54%)** come back unsupported at the default 0.5 threshold, versus 1 today, and contradiction
flags jump from 2 to 21.

**Spot-checked 5 flagged intervals by hand against their cited evidence** (graph.db +
`data/03_claims/`, not just the score): found genuine catches (Lawrence/Norah `COMMANDS`'s primary
citation is a context-free `"It's a deal, then," said Lawrence.` — too weak to stand alone) but
also a case that reads as correctly extracted and well-evidenced by a human standard — Lawrence
`MENTOR_OF` Holo, backed by "Lawrence was teaching her the names of various currencies... Holo...
struggled with coins" — scoring only 0.038 even though `minicheck.py` already takes `max()` across
every cited-evidence chunk (confirmed in code, not assumed), so a genuinely supportive quote in the
mix did not save the interval.

**The pattern is systematic, not noise**: flagged-count by predicate is `ENEMY_OF` 22, `COMRADE_OF`
18, `FRIEND_OF` 16, `COMMANDS` 15, `SAVED` 9, `RIVAL_OF` 6 — almost entirely RELATION predicates —
against `AGE` 1, `ORIGIN` 1, `GENDER` 1, `RANK` 3, `OCCUPATION` 0. Novels show a relationship
through scenes and dialogue rather than stating it in the predicate's own words ("comrade,"
"rival"), so relation evidence is close to definitionally inferential; MiniCheck (built for literal
summary-vs-source fact-checking, not narrative inference) reads that as unsupported at a much
higher rate than attribute claims, where the source text usually states the value directly. R21's
single confirmed win (Zheren `OCCUPATION`) is an attribute case — it was never evidence this
generalizes to relations, and now there's a direct on-corpus measurement showing it does not, at
least not at a flat threshold.

**Not made the default.** Flipping it as-is would flag roughly half of every future relation claim,
which is a precision/recall tradeoff reshaping what ships to readers — not a bug fix, and worth the
maintainer's call, not a judgment call to make unilaterally on a "continue the project" prompt.
`data/spice-and-wolf/04_graph/` was rebuilt back to the non-`--nli` state afterward so committed
docs and on-disk output stay consistent with each other. **Real next step, not done speculatively
here:** either scope `--nli` to attribute-only claims (where it's proven) or find/measure a
predicate-kind-aware threshold before reconsidering the default question.
