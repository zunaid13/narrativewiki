# Guide to Publishing — turning `narrativewiki` into a research contribution

**Written:** 2026-09-11
**Status:** Living document. §8 (related work) and §10 (risk register) are meant to be updated
continuously; everything else is a decision record.
**Scope:** the strategy, the honest feasibility assessment, and the engineering programme required
to take this repo from "a working system" to "a paper a top-tier venue accepts."

> **Read this first.** Every arXiv ID and venue claim in §8 was gathered from web search on
> 2026-09-11. **Status as of 2026-09-16: all 51 identifiers used anywhere in this project resolve
> against the arXiv API, with matching titles, and every PDF is on disk** — `docs/REFERENCES.md` is
> the generated, verified table, `python docs/fetch_reference_pdfs.py` regenerates it, and the PDFs
> live in `docs/Sample_Research_Related/` (gitignored). That closes the *hallucinated identifier*
> half of the problem, and only that half. **One paper has been read in full** (2512.07474; one
> more at abstract+body level). An id resolving to the right title is a correct address, not a
> confirmed claim — before a citation goes into a submission, open the PDF and confirm it says what
> this file says it says. "An assistant found it for me" is not a defence.

---

## Table of contents

0. [State of play — read this before writing anything](#0-state-of-play--read-this-before-writing-anything)
1. [Honest verdict on the idea as proposed](#1-honest-verdict-on-the-idea-as-proposed)
2. [The paper to write instead](#2-the-paper-to-write-instead)
3. [Feasibility: venues, odds, risks, budget](#3-feasibility-venues-odds-risks-budget)
4. [Corpus plan](#4-corpus-plan)
5. [Engineering programme](#5-engineering-programme)
6. [Twelve-month timeline](#6-twelve-month-timeline)
7. [What the repo is today (baseline facts)](#7-what-the-repo-is-today-baseline-facts)
8. [Related work map](#8-related-work-map)
9. [Target paper skeleton](#9-target-paper-skeleton)
10. [Rejection-risk register](#10-rejection-risk-register)
11. [Decision log — what was rejected and why](#11-decision-log--what-was-rejected-and-why)

---

## 0. State of play — read this before writing anything

**Updated 2026-09-16.** This section is the current answer to "what do I actually have?" Everything
below it (§1 onward) is the plan as written on 2026-09-11 plus dated corrections. When they
disagree, this section wins.

### 0.0 What changed since 2026-09-13 (read this first)

| | Status |
|---|---|
| **The decisive run (§0.3) is half done.** `--gate=build` now covers alias clustering **and** claim extraction, with per-cutoff provenance/rollback isolation. Build-mode gate comparison on spice-and-wolf: **0 mining-selection inconsistencies introduced** (t=1 0/21→0/23, t=2 0/41→0/44) | The gating architecture works and is measured |
| **The other half will not run soon.** Standing maintainer scope rule: 2 volumes, 1 series, until pipeline + eval + benchmark are complete. The 86 volumes-1–4 run was stopped mid-flight | **Plan paper 1 on the limitation branch.** Treat a main-track finding as upside, not schedule |
| **Do not cite the claim-diff numbers.** `reanalysis_claim_diff.py`'s only_render = 0.982/0.954 measures accumulated run-history depth (226 claims for v1 across many top-up sessions) against a fresh 16-claim single-pass baseline — not the cutoff restriction | Committed with the caveat; never a leak rate |
| **A new taxonomy dimension: individuation.** At t=1 the index holds `holo` and `wisewolf` as two entities; the render index merges them. Whether cutoff-dependent fragmentation is a bug or *correct* is undecided (n=2) | Open question — see §2.2's channel table |
| **Self-reported confidence retired on evidence.** `rule:lowest_confidence_dropped` kept `"public witness"` (confidence 1.0) over gold-correct `"traveling merchant"` (0.72). MiniCheck-FT5 NLI support scoring is written, uncommitted, unrun | §5.3 `judge.py` is now partly built ahead of schedule |
| **The lexical scorer failed to register a real improvement.** Zheren's page went 0 → 8 scene claims matching gold almost verbatim; `fact_recall` stayed 0.0 | R2 is no longer theoretical — it has a named on-corpus instance |
| **A meta-bug invalidated iteration between 2026-09-11 and 2026-09-16.** Drop-reason counters were printed and discarded, and the scene-channel fix was never re-run; re-running it alone moved scene claims 3→124 (v1) and 8→193 (v2) | Every eval number in that window predated its own fix. Fixed: `_runs/<id>/yield.json` |
| **Citations: 51/51 arXiv ids resolve**, PDFs on disk, `docs/REFERENCES.md` generated | R15's identifier half closed; the read-the-paper half is open |
| **851 tests green** (was 706 on 2026-09-13), with the in-flight support-scoring work in tree | — |

The engineering-iteration record — every module that shipped, failed on measured evidence, and was
replaced — is maintained in `NARRATIVEWIKI_CAPABILITY_REFERENCE.md` §4, with the research area each
failure belongs to. That table is the source for §7's "named failure modes" and for anything that
needs to describe this project to an outside reader.

### 0.1 What is proven (as of 2026-09-13; §0.0 above is newer)

| | Evidence |
|---|---|
| `tests/test_spoiler_leak.py` exists and passes — the CLAUDE.md §1 gate that was missing since Phase 4 | 27 tests; full suite 709 passed, exit 0 (2026-09-13) |
| **L_query** (the published gate) is correct on this system | `graph/temporal.py`, pinned by the above |
| **L_artifact**, link case, is correct | no link on a cutoff-*t* page resolves to an entity with `first_vol > t`; pinned by the above |
| **H4 is false** — PPR does not leak | `build_subgraph` already restricts to `all_edges_at(conn, upto_vol)`; `tests/test_ppr.py` |
| **L_build is non-zero**, and it sits in `entities/candidates.py`, not in retrieval | `docs/probe/index_{86,spice-and-wolf}.jsonl` |
| A per-cutoff index rebuild (`wiki gazetteer --gate=build`) closes the measured selection inconsistency to zero | `docs/probe/gate_comparison_spice-and-wolf.jsonl` |

### 0.2 What is *not* proven, and the correction that matters most

**The 0.303 headline is a selection-threshold artifact, not a measured spoiler.** Audited
2026-09-13 (`docs/probe/reanalysis_first_occurrence.py`, `ConvinceMe.md` Addendum 2):

- All 37 "leaking" surfaces at 86/t=1 belong to entities with `first_vol = 1`. **No future entity
  leaks on either corpus at any cutoff.**
- 31 of 37 appear verbatim in volume-1 text (up to 97 times); 2 more are article variants of
  strings the reader saw 12–14 times. Only **4 of 122** are strings a volume-1 reader could never
  have seen.
- The disclosure-relevant rate is **0.033 (86, t=1)** and **0.000 (spice-and-wolf, t=1)** — not
  0.303 and 0.042.
- Consequently the `--gate=build` before/after pair closes a leak that was, on the disclosure
  predicate, already zero. It is a sound engineering result on an empirically thin case (n = 1
  surface, on the smaller corpus).

Nothing else in the taxonomy has been measured. `entities/alias.py`, `extract/claims.py`,
`graph/contradictions.py` and `synth/prose.py` all consume cross-volume context and all still build
in render mode — and every one of them has more opportunity to leak than a pair of integer
thresholds does.

### 0.3 The one run that decides Claim 2's status — now half-run, see §0.0

Extend `--gate=build` past entity discovery to alias clustering and claim extraction, run on 86
volumes 1–2 (local, $0), and re-probe.

- **Build-time leakage materially above 0.033 at those stages** → Claim 2 is a main-track finding;
  write the abstract around build-time vs. query-time gating.
- **Near-zero there as well** → Claim 2 becomes a limitations subsection and an honest-negative
  validation result; paper 1 retargets to Findings / LREC-COLING / NeurIPS D&B (§3.1's lower rows),
  and weight moves to paper 2. That is the §6 Month-4 gate firing early, for $0.

**Do not write the abstract before that run.** Today's audit moved this project's headline number by
9× on a change of predicate; a first paper cannot survive learning that from a reviewer.

### 0.4 Venue expectation, adjusted

§3.1's "~10–15% main track" was priced on Claim 2 being a correction of a published claim. On the
audited numbers it is currently a *validation* of one, with one narrow exception. Until the decisive
run says otherwise, treat **Findings / LREC-COLING resource / NeurIPS D&B as the primary target**
and main track as the upside case, not the plan.

---

## 1. Honest verdict on the idea as proposed

The original plan was: propose the pipeline as a solution to a real-world problem, benchmark on
Project Gutenberg (Sherlock Holmes, Three Kingdoms), tackle contamination via entity mapping +
paraphrasing + shuffling time-independent event sequences, and evaluate on (a) claim
recall/accuracy, (b) isomorphism of the built graph to an online ground truth, (c) a web crawler's
ability to answer multi-hop questions across hyperlinked pages.

**The project is publishable. That framing is not.** It is a system with three evaluations bolted
on. The first question every *ACL reviewer asks is *what is the research question* — and "we built
a pipeline and measured it" answers a different one. What follows is a component-by-component
verdict, then the reframing in §2.

### 1.1 Claim recall / accuracy — keep, but it is not a contribution and it is currently mis-measured

Necessary, insufficient, and broken in three specific ways:

**(a) Lexical keyword overlap cannot be the primary metric.** `eval/gold.py` scores a gold fact as
recalled when a majority of its content keywords (length ≥ 4, stopworded, threshold
`max(2, 0.5·|kw|)`) appear anywhere in the page's pooled text. That is a deliberate, well-reasoned
choice for a **zero-cost CI regression gate** and it should stay in that role. As a headline number
in a paper it will be attacked immediately: it cannot distinguish "Holo is from Yoitsu" from "Holo
has never been to Yoitsu", and it has no notion of entailment. Move the headline to entailment-based
scoring, validate the judge against humans, report the correlation, and keep the lexical scorer as
the cheap gate it was designed to be.

**(b) There is no groundedness ceiling, so 0.32 is uninterpretable.** The current mean
`fact_recall` of ≈0.32 is measured against facts transcribed from a Fandom page that describes the
**whole series**. The gold format already handles the obvious half of this with `in_scope: false`
— excluding future-volume facts from the denominator so correct spoiler suppression is not punished.
But `in_scope: true` only means *a human believed this was true by volume N*; it does not mean *the
text of volumes 1–N actually states it*. Fan wikis routinely synthesize across sources, import
material from adaptations, and encode community inference. Until you measure, for each gold fact,
whether **any** source paragraph at that cutoff entails it, you do not know whether 0.32 is a
failure or near-ceiling.

This is the single highest-value experiment in the whole programme, it is cheap, and it should run
in Month 3. If the ceiling is 0.45, then 0.32 is 71% of achievable and the story changes completely.

**(c) No baselines.** A recall number with nothing beside it is not evidence. See §5.5.

### 1.2 Graph isomorphism against an online ground truth — reframe; this is the weakest leg

Three independent problems, any one of which is disqualifying:

**Wrong formalism.** Graph isomorphism is NP-hard *and* semantically wrong for this task: you do not
want a structure-preserving bijection that ignores labels — a graph where every `SIBLING_OF` became
`ENEMY_OF` is isomorphic to the correct one and completely wrong. The literature's actual metrics
are triple-level precision/recall/F1 (T-F1), graph-level exact match (G-F1), Graph Edit Distance,
and G-BERTScore for soft edge alignment. Use those words; using "isomorphism" signals to a reviewer
that you have not read the KG-construction evaluation literature.

**No ground truth exists to be isomorphic to.** Searched on 2026-09-11: there is **no**
machine-readable reference KG for either target corpus. What exists is Fandom prose (Baker Street
Wiki), thin Wikidata entries, and hobbyist co-occurrence networks built by counting characters
appearing in the same chapter. None of these is a labelled, typed, temporally-scoped relation graph.
You would be **constructing** the reference, not finding it — which is legitimate and valuable, but
it is weeks of annotation work that must be in the schedule, not a footnote.

**It contradicts the contamination story.** Fandom and Wikipedia pages about Sherlock Holmes are
heavily represented in pretraining corpora. Scoring a contamination-controlled system against a
memorized reference is incoherent unless you measure and report the overlap. Worse, a co-occurrence
network is not a relation graph at all — matching it well would mean your system learned *who
appears near whom*, which is not the claim.

**Replacement.** Three tiers, reported separately and never conflated:
- **Gold (human-adjudicated):** a typed, temporally-scoped subgraph you build and double-annotate.
  Scored with alias-aware, embedding-soft triple P/R/F1, plus hallucination and omission rates.
- **Silver (derived):** extracted from Fandom/Wikidata/Wikipedia, with its noise rate against gold
  measured and published. Useful for scale, never for a headline claim.
- **Structural:** Spearman correlation of character-network centrality ranks against the reference
  network. This is what the co-occurrence graphs are *actually* evidence for, and it is a fair,
  honest use of them.

### 1.3 Multi-hop crawler evaluation — this is the strongest idea; make it the headline

This is the one component that is genuinely novel and that no existing work can produce. It gets its
own claim in §2.4 and its own engineering phase in §5.6. Everything else in the paper should be
arranged to set it up.

### 1.4 Shuffling time-independent event sequences — drop it

Two reasons, either sufficient:

**It fights the thesis.** Reading order *is* the signal this entire system is built around. The
cutoff axis is the independent variable. Shuffling event sequences destroys the exact structure
being measured, and a reviewer will notice the contradiction between "reading order carries
knowledge state" and "we shuffled the reading order."

**The literature has already been here.** The contamination-mitigation survey work evaluates ~11
strategies — irrelevant context, relevant context, syntactic modification, synonym replacement,
typographical perturbation, translation, back-translation, choice paraphrasing, added distractors,
choice permutation — and reports a **fidelity–resistance tradeoff**: no strategy both eliminates
memorization and stays faithful to the original evaluation goal. Proposing permutation without
engaging that result is a rejection. Proposing it *while engaging* that result requires showing why
yours escapes the tradeoff, and shuffling does not.

**You already have a better variation axis, for free: the cutoff.** One corpus yields N distinct,
internally coherent knowledge states. That is variation *without* incoherence — precisely what
shuffling tries and fails to buy. Use it, and say in the paper that you considered permutation and
rejected it for these reasons. A well-argued rejected alternative strengthens a methods section.

---

## 2. The paper to write instead

> **Working title.** *Reading-order-conditioned knowledge: constructing and evaluating
> temporally-scoped encyclopedic hypertext from narrative — and using it to separate parametric
> memory from retrieval.*

Four claims in dependency order. Claims 2 and 4 are what get this into a good venue; claims 1 and 3
are the scaffolding that makes them possible.

### 2.1 Claim 1 — Task and system *(table stakes)*

Formalize **progressive knowledge scoping**: given a narrative corpus *C* and a reader position *t*,
produce an encyclopedic artifact containing exactly the knowledge derivable from *C*≤*t*. This
generalizes temporal KG construction with **reading order as the time axis**, and it has a property
no wall-clock temporal KG has: *N* fully-supervised knowledge states fall out of a single annotation
pass, because the same annotation is re-scoped per cutoff rather than re-collected.

That cheap-supervision argument is the reason this task is interesting beyond fiction, and it should
be stated in the introduction, not buried.

**The novelty caveat you must handle head-on, in the introduction, not the related work.** Prior
work has already published a diegetic knowledge graph with a "narrative-present gate" that filters
spans to story-time ≤ *t* before generation — which is exactly the invariant in `CLAUDE.md` §1
("the prose is generated from that already-filtered set... never generate from the full set and
redact afterwards"). **Do not claim filter-before-generate as novel.** Cite it as the closest prior
work and differentiate on five concrete axes:

| Axis | Prior work | This work |
|---|---|---|
| Artifact | conversational agent | hyperlinked encyclopedic site, N cutoffs |
| Provenance | span-level | claim-level, with verbatim quote + `para_id` + print page |
| Temporal model | timestamp tag | intervals with `vol_start`/`vol_end`, supersession, contradiction arbitration |
| Corpora | one novel | three public-domain + two commercial case studies |
| Safety | asserted by construction | **measured** (Claim 2) |

Being visibly aware of the closest competing paper and beating it on specifics is far stronger than
hoping a reviewer has not read it. They will have.

### 2.2 Claim 2 — Leak@t: the metric, and the finding that it is not enough

**Every "spoiler-free by construction" claim in the literature is asserted and never measured.**
That is the gap.

**Definition.** Given a page *P* rendered at cutoff *t*, and *F*>*t* = the set of facts first
established in (*t*, *T*], **Leak@t** is the fraction of *F*>*t* that a competent reader could infer
from *P*. Measured at three tiers:

| Tier | Method | Cost |
|---|---|---|
| Lexical | future entity names / strings present in *P* | free |
| Entailment | NLI model over (*P*, *f*) for each *f* ∈ *F*>*t* | local, free |
| Inferential | LLM judge: "could a reader who has read only up to *t* conclude *f* from this page?" | local, validated against humans |

The future-fact set requires **no new annotation** — it is `claims` with `first_vol > t`, already in
`graph.db`.

**The finding that makes this a paper.** Filter-before-generate is *necessary but not sufficient*.
Correct filtering of the claim set does not prevent leakage through **structure, implication, and
the index the filter is applied to**. The four hypotheses below (H1-H4, as originally drafted
2026-09-11) are superseded by a taxonomy organized by **when the future touched the system**,
which is a stronger and more falsifiable framing than a list of unrelated hypotheses — one axis,
not four coincidences:

| Channel | What the future shaped | Mechanism | Status (2026-09-13) |
|---|---|---|---|
| L_query | which claims reach the generator | the published gate (`graph/temporal.py`) | **closed**, `tests/test_spoiler_leak.py` |
| L_artifact | page existence, pair pages, `vol_end` closures, link presence (absorbs H1/H2/H3) | `site/bundle.py`, `site/wikify.py` | **closed** for the link case, `tests/test_spoiler_leak.py` |
| **L_build** | the gazetteer, alias clusters, automaton — the index itself | `entities/candidates.py::mine_candidates` | **open, measured non-zero** |
| L_param | the generator's own pretraining on the source text | none — the corpus predates every model | unaddressed; reported as a floor |

**A fifth dimension, found 2026-09-14, not yet placed in the taxonomy: individuation.** The four
channels above all ask a *visibility* question — does the system know an entity or fact exists
before a reader could? Cutoff-restricted index building surfaced a different one: at t=1
`entities/alias.py`, having read only volume 1, keeps `holo` and `wisewolf` as two entities, while
the whole-corpus render index merges them; cutoff-restricted extraction then attaches nickname/age/
appearance facts to a `wisewolf` entity that exists nowhere in render mode. **Whether two surface
forms denote one character is itself cutoff-dependent knowledge**, and it is genuinely undecided
whether fragmentation at low cutoffs is a bug (later evidence should merge retroactively) or the
correct behaviour (a volume-1 reader does not yet know the epithet, so merging is the leak). n = 2
cases. Decide this before it enters the claim list — as a *finding* it is the most paper-shaped
thing here since the disclosure audit; as an unexamined artifact it is a reviewer's first question.

**H4 is retracted, on evidence, not by re-framing.** It hypothesized that `graph/ppr.py` weights
entities by centrality partly determined by their later role. Checked directly:
`build_subgraph(conn, upto_vol)` already restricts to `all_edges_at(conn, upto_vol)` — the edge
set is cutoff-correct by construction, and `tests/test_ppr.py::test_build_subgraph_filters_by_cutoff`
already pins this. **H4 as written is false.** Retracting it yourself, with the mechanism that
disproves it, is stronger than letting a reviewer find it — and L_build is what H4 was reaching
for, one pipeline stage earlier, demonstrated with a number instead of asserted.

**L_build, measured (2026-09-13, `docs/vision/PHASE_24.md`).** Two zero-LLM-call, zero-annotation
probes in `src/narrativewiki/probe/channels/index.py`. The obvious channel — automaton surface
forms / hyperlink targets belonging to a future entity — reads near-zero
(0.1-2.3% of in-scope mentions/claims), because `first_vol` is defined as *earliest* evidence
volume, so a future entity has almost no occurrences in text at or before the cutoff by
construction. The real channel sits one stage earlier: `mine_candidates`'s `min_mentions` and
capitalisation-ratio thresholds are corpus-wide counts, computed once over whatever `--volumes`
range is passed to `wiki gazetteer` — not per-cutoff. Re-running candidate mining restricted to
volumes `<= t` and diffing against the shipped gazetteer:

| Series | t | leak_rate | Confirmation |
|---|---|---|---|
| 86 | 1 | **0.303** (37/122 surface forms) | falls to 0.190/0.050/0.000 at t=2/3/4 as the cutoff approaches the mined range |
| spice-and-wolf | 1 | 0.042 (1/24) | "Kraft Lawrence": 2 raw mentions in v1 alone (below `min_mentions`), 4 more in v2 (clears it) — confirmed by direct text count |

This is the paper's first real number: **30.3% of the surface-form vocabulary behind a cutoff-1
page in this system's own reference series would not have been discovered from cutoff-1 text
alone.** It corrects the implicit assumption in `CLAUDE.md` §1 as much as it corrects prior work —
"the prose is generated from that already-filtered set" was true of *claims*, not of the *index*
that surfaced them. `wiki probe run index --series <id> --volumes <range>` reproduces both
numbers; `docs/probe/index_{86,spice-and-wolf}.jsonl` are the raw rows.

Demonstrating this is a mechanistic result that **corrects a published claim**, including this
project's own prior draft of it. That is main-track material, and it is the kind of finding that
gets cited.

**The architectural fix, built and run (2026-09-13).** `wiki gazetteer --gate=build` rebuilds the
entity-discovery index once per cutoff, each time restricted to volumes `1..t`
(`paths.py::set_build_cutoff` redirects the output so Mode A and Mode B never collide). Run on
spice-and-wolf, volumes 1-2, local Ollama, $0:

| t | gate | leak_rate |
|---|---|---|
| 1 | render (published architecture) | 0.042 |
| 1 | **build (cutoff-consistent)** | **0.000** |
| 2 | render | 0.000 |
| 2 | build | 0.000 |

Concretely: the shipped index canonicalizes the protagonist as "Kraft Lawrence"; the cutoff-1
`--gate=build` index, having never read volume 2, canonicalizes the same character as plain
"Lawrence" and never creates the leaking surface form at all. This is the paper's clean before/
after pair — the leak measured, then closed, with the compute cost of closing it now known
(2 extra classify+cluster passes for a 2-cutoff sweep). **Scoped to entity discovery only**:
claims, the graph and pages still build in render mode under `--gate=build` today; extending the
redirect to those stages is real LLM spend across every cutoff and is the next increment, not
done here. `docs/probe/gate_comparison_spice-and-wolf.jsonl` carries the raw rows.

**Correction (2026-09-13, same day): the 0.303 above is a selection artifact, and the paper must
say so itself.** `measure_candidate_mining` answers "would cutoff-only mining have *selected* this
surface?", not "could a cutoff-*t* reader have *seen* it?". Re-measured with the disclosure
predicate — first verbatim occurrence of the surface in parsed text, Tier B additionally stripping
a leading article and ignoring case (`docs/probe/reanalysis_first_occurrence.py`,
`docs/probe/first_occurrence_*.jsonl`):

| Series | t | selection `leak_rate` | unseeable (exact) | unseeable (normalised) |
|---|---|---|---|---|
| 86 | 1 | 0.303 | 0.049 (6/122) | **0.033 (4/122)** |
| 86 | 2 | 0.190 | 0.018 (3/163) | 0.012 (2/163) |
| 86 | 3 | 0.050 | 0.006 (1/179) | 0.006 (1/179) |
| 86 | 4 | 0.000 | 0.000 | 0.000 |
| spice-and-wolf | 1 | 0.042 | 0.042 (1/24) | **0.000 (0/24)** |
| spice-and-wolf | 2 | 0.000 | 0.000 | 0.000 |

Of the 37 surfaces behind 86/t=1: 31 occur verbatim in volume-1 text (`Eighty` 97×, `Dinosauria`
59×, `AI` 56×, `Shinei Nouzen` 2× — below `min_mentions=3`), 2 are article variants of strings seen
12–14× (`The Gran Mur`, `The Grauwolf`), and 4 are genuinely absent (`FOB`, `No Face`,
`RAID Devices`, `The Supreme Commander`). **All 37 belong to entities with `first_vol = 1`** — no
future entity's existence leaks on either corpus at any cutoff, so H1 is neither confirmed nor even
addressed by this probe.

Two things follow for the write-up. **Report both tiers, lead with the disclosure tier.** The
selection metric is the diagnostic that located the mechanism and belongs in the analysis section;
the disclosure metric is the one that can appear in an abstract. And **state the `--gate=build`
result at its true strength**: it closes the selection inconsistency to zero, on a corpus whose
disclosure-tier leak was already zero — an architectural result demonstrated on n = 1 surface, not
an empirical result. The honest framing is "we built the first cutoff-consistent index and verified
it changes the index (`Kraft Lawrence` → `Lawrence`); the leak it removes is small at this stage,
and the stages where it should be larger are not yet gated."

**The stages that are not yet measured are the ones that should leak most.** `mine_candidates` is
the only entity-discovery stage with no LLM and no cross-volume reasoning — two integer thresholds.
`entities/alias.py` (LLM clustering over the whole corpus), `extract/claims.py` (cross-volume
extraction windows), `graph/contradictions.py` (supersession is cross-volume by definition) and
`synth/prose.py` (generated once, cached by claim-set hash, reused across cutoffs) all still build
in render mode. Measuring those is §0's decisive run, and Claim 2's status as finding-vs-limitation
turns on it.

> **Update 2026-09-16.** Two of those four are no longer unmeasured. `entities/alias.py` was
> already covered by `gazetteer --gate=build` (one shared code path per cutoff), and
> `extract/claims.py` was brought under the gate on 2026-09-14. On the mining channel the result is
> clean — 0 selection inconsistencies introduced at either cutoff (§0.0) — and the claim-level diff
> that looked dramatic (0.982/0.954) turned out to measure accumulated run-history depth, not the
> cutoff restriction; never cite it. `graph/contradictions.py` and `synth/prose.py` remain
> ungated and unmeasured, and the 13-volume corpus remains unrun under any gate by standing scope
> decision (R22). What the extension *did* surface is the individuation dimension above.

### 2.3 Claim 3 — Benchmark and contamination protocol

Release **NARRATIVEWIKI-BENCH**: public-domain corpora, the gold subgraph, the Leak@t future-fact
sets, the multi-hop task set, and a **counterfactual perturbation** protocol.

**The perturbation.** Deterministic seeded entity remapping plus paragraph-level paraphrase, such
that the gold graph is **preserved exactly** — the remap is a bijection on entity identifiers, so
every annotation transfers automatically through the alignment map. No re-annotation.

**The validation.** A closed-book probe: prompt a frontier model with no tools, *k* independent
trials, flag any item answered correctly in ≥ *k*/2. Report the **memorization gap**
(original − perturbed) as a first-class number for every system evaluated, baselines included.

**The answer to the obvious objection.** The survey's fidelity–resistance tradeoff says no
perturbation both defeats memorization and stays faithful. Your reply is structural, not rhetorical:
this perturbation is **semantics-altering by construction and graph-preserving by construction**.
Fidelity is not being *hoped for*, it is guaranteed by the bijection — the evaluation target (the
graph, the claims, the derivation chains) is provably unchanged while the surface form that a model
could have memorized is provably different. Measure and report residual fidelity loss anyway (§5.4,
D3); a small, honestly-reported divergence is far stronger than a claim of perfection.

### 2.4 Claim 4 — The agentic environment *(deferred to paper 2, 2026-09-13)*

**Decision (2026-09-13):** defer this claim to a second paper. Paper 1 (Claims 1-3, reframed
around the four-channel taxonomy in §2.2) is self-contained and submittable with no crawler, no
task generation, no agent baselines, and no API budget — it is fully local and fully measured
already for L_query/L_artifact, with L_build's first number in hand. Claim 4 needs the
`--multipage` emitter, task generation, and agent baselines (Phase 25/29) before any number
exists, pushing the first result to ~month 8 on the original schedule. Splitting does not waste
the agentic work: it reuses the identical graph/provenance machinery afterwards as a follow-up,
not a dependency, and the leakage paper's release (NARRATIVEWIKI-BENCH, §2.3) is exactly the
artifact the follow-up needs. Kept below as the eventual paper-2 thesis.

Because the output is hyperlinked hypertext generated from a provenance-carrying graph, the system
is a **generator of contamination-controlled, provenance-grounded multi-hop retrieval environments
whose gold derivation chains are known by construction, not by annotation.**

Positioning, which is the single most important table in the paper:

| Work | Content | Ground truth | Counterfactual control | Cutoff axis |
|---|---|---|---|---|
| Synthetic-web-style benchmarks | fabricated | by construction | none — no real-text anchor | no |
| BrowseComp-Plus-style | real Wikipedia | human-verified | none — real ⇒ memorized | no |
| SimpleWikiSearch-style | real Wikipedia | derived | none | no |
| **This work** | **real narrative prose** | **by construction, traced to source spans** | **yes — matched original/perturbed pairs** | **yes** |

Only one row has both a real-text anchor and a counterfactual control. And only one has the cutoff
knob, which buys the experiment nobody else can run:

> **Serve the site at a cutoff where the question is unanswerable.** A correct answer is
> *provably* parametric memory, not retrieval — because the information is not in the environment.

State that in the abstract. It is a clean, general-interest probe for a problem the whole agentic-
retrieval field has (distinguishing "the agent found it" from "the agent already knew it"), and it
generalizes far beyond fiction. Fiction is the *instrument*, not the subject.

### 2.5 Why this framing survives "it's just a fan wiki"

Because it reframes the domain as an apparatus. Narrative is the only large corpus where ground
truth is naturally indexed by a **reader-observable** time axis, letting you construct arbitrarily
many coherent knowledge states from one annotation pass. That is a property of the *instrument*, and
the results it produces — about leakage, about memory vs. retrieval — are about language models, not
about light novels.

If the paper reads as "we made a wiki for a book series," it gets rejected as narrow. If it reads as
"narrative reading order gives us a controllable knowledge-state axis, and here is what that reveals
about retrieval systems," it does not.

---

## 3. Feasibility: venues, odds, risks, budget

### 3.1 Venue realism

Constraints: solo author, no advisor, first paper, ~$20 of API budget, one consumer GPU.

| Venue | Fit | Realistic odds | Notes |
|---|---|---|---|
| ACL / EMNLP **main** | Good if Claims 2 + 4 land | **~10–15%** | Bar is novelty *and* polish. Unaffiliated solo authors are not excluded but are disadvantaged on writing quality and related-work depth — both of which are fixable with time |
| ACL / EMNLP **Findings** | Very good | **~25–35%** | The realistic primary target. Same submission, no extra work |
| **NeurIPS Datasets & Benchmarks** | Very good — this is benchmark-shaped | **~25%** | Deadline typically ~June. Values artifact quality highly, which plays to your strengths |
| **LREC-COLING** resource track | Excellent | **~50%+** | Explicitly wants corpora, benchmarks, evaluation methodology |
| **CIKM** resource track | Good | ~30% | Requires a Zenodo/Dataverse deposit — plan for it |
| **WNU / NLP4DH / CHR** workshops | Excellent, ACL Anthology-indexed | **~60%+** | The de-risking backstop. A real publication, not a consolation prize |

**Strategy: write one paper at main-track quality and let the review process sort the venue.**
Submit through ACL Rolling Review. ARR moved to 10-week cycles in 2025; the 2026 pattern was
Jan 5 / Mar 16 / May 25 / Aug 3 / Oct 12, and 2027 should follow the same cadence — **verify the
actual 2027 dates before committing.** Target the **August or October 2027 cycle**, which fits the
12-month schedule with slack.

Reviews are portable. Strong scores → commit to EMNLP 2027 / ACL 2028 main. Middling → Findings.
Weak → revise once against the reviews and take LREC-COLING or a workshop, rather than burning
another year chasing main track.

**Post the arXiv preprint the day you submit** to timestamp Leak@t. It is the idea most likely to be
independently rediscovered, and it costs nothing to protect.

### 3.2 Budget: $20 is workable, and it can be turned into a methodological strength

**The protocol that makes it work:** fix one open-weight backbone and run **every** system through
it — yours, GraphRAG, LightRAG, vanilla RAG, long-context stuffing. You are then comparing
**architectures** rather than model budgets. This is a *cleaner* experiment than most published
baseline tables, where a system's advantage is often just a bigger model. State it as a deliberate
controlled-comparison protocol in the experimental setup, not as an apology in the limitations.

**Spend the $20 on exactly three things:**

| Priority | Purpose | Why it must be paid | Est. |
|---|---|---|---|
| 1 | Closed-book contamination probes | Needs a genuinely frontier model; free tiers are the wrong instrument for measuring memorization | ~$8 |
| 2 | Judge validation | Frontier judge on the same sample humans annotate → three-way human/frontier/local agreement | ~$7 |
| 3 | One frontier agent run on the multi-hop task | Gives the headline table a strong upper reference point | ~$5 |

Free-tier OpenRouter covers everything else. Phase 23 Part F already established that
`nex-agi/nex-n2.5-pro:free` with `reasoning: {effort: "none"}` handles this call shape at **0
unparseable responses across 350 calls** — that is a validated, documented free route, and the
reliability figure belongs in the paper's reproducibility section.

**Release the LLM response cache.** There are ~4,700 content-addressed cached responses already, and
the count will grow by orders of magnitude. Shipping the cache means **a reviewer reproduces every
number in the paper with zero API spend and no GPU**. Almost nobody does this. It is a strong,
cheap, differentiating artifact claim — say it explicitly in the reproducibility statement.

### 3.3 Compute reality check — the binding constraint

The current 2-volume run has cost 3,955 accounted LLM calls (2026-09-16; it was 2,664 when this section was written, and the growth is re-runs, not new corpus). The full programme is roughly:

> 3 public-domain corpora × 2 variants (original + perturbed) × ~10× the current per-corpus volume,
> plus the baseline sweep ⇒ **on the order of 150k–200k local calls.**

On one 5070 Ti with a 14B-q4 model that is **weeks of wall-clock**, not days. Design for it now:

- **Start the longest runs in Month 1–2 and let them run in the background.** GPU time, not ideas,
  is what will make or break the schedule.
- **Consider a 7–8B backbone for the baseline sweep**, documented, with a 14B-vs-8B calibration on
  one corpus showing the *ranking* is stable even if absolute numbers shift. Reviewers accept this
  when it is measured rather than assumed.
- **Lean on the existing infrastructure.** The run ledger, per-call logging, rollback, failed-run
  quarantine, and content-addressed cache make these runs resumable and auditable. This is the
  reason the programme is feasible at all on this hardware, and it is worth a paragraph in the
  paper.

### 3.4 The single biggest non-technical risk: writing quality

Solo, no advisor, first paper. The technical work in this repo is already stronger than a lot of
what gets published. The gap will be in **the writing** — specifically the introduction, the
related-work section, and the framing of contributions.

Mitigations, in order of value:
1. **Budget three full weeks for writing** (Month 11). Not "write it up at the end" — three weeks.
2. **Get an external read.** A faculty member who did not supervise you, a senior student, or a
   mailing-list peer. One honest read before submission is worth more than another experiment.
3. **Related work is the section that kills unsupervised first papers.** Start §8 of this file in
   Month 1 and add to it every single week. Twenty verified, correctly-characterized citations
   accumulated over a year beats forty found in a panic in Month 11.
4. **Consider recruiting a co-author** at Month 6, when you have the Leak@t and ceiling numbers.
   That is the moment you have something concrete to show, and a co-author who joins for the writing
   and framing is a large, cheap improvement in acceptance odds. This is not a concession — it is
   how most accepted papers are made.

---

## 4. Corpus plan

Keep everything; add three public-domain corpora.

| Corpus | Source | "Volume" mapping | Why this one |
|---|---|---|---|
| **Sherlock Holmes canon** | Project Gutenberg | 9 books in publication order: *A Study in Scarlet*, *The Sign of Four*, *Adventures*, *Memoirs*, *Hound*, *Return*, *His Last Bow*, *Case-Book* (+ split as needed) | Episodic with genuinely spoiler-bearing arcs — Moriarty's existence, Reichenbach, Holmes's apparent death and return, Watson's marriage and widowhood. Small clean cast. **Heavily memorized ⇒ a strong contamination signal**, which is a feature: it makes the memorization gap large and measurable |
| **Romance of the Three Kingdoms** (Brewitt-Taylor tr.) | Project Gutenberg | 120 chapters → 12 volumes of 10 | Hundreds of characters, courtesy names and titles as aliases, shifting allegiances, mass character death. **The hardest possible stress test** for `intervals.vol_end`, `superseded_by`, and contradiction arbitration. Non-Western, translated — supports the generality claim |
| **The Count of Monte Cristo** | Project Gutenberg | 117 chapters → ~10 volumes | **Add this one.** Edmond Dantès *is* the Count — a sustained identity concealment that is the single best natural test case for interval supersession *and* for Leak@t. If the volume-3 page leaks the identity, the metric catches it. A clean, human-legible demonstration for a figure |
| 86—EIGHTY-SIX (13 vols) | commercial | as-is | Non-redistributable qualitative case study. Hard modern prose, 13-volume continuity, the Para-RAID channel. Release **derived statistics only**, never text |
| Spice and Wolf (2 vols) | commercial | as-is | Same. The existing calibration corpus and gold set |

Three public-domain corpora give era, language-of-origin, structure, and cast-size variation —
enough to claim generality without overclaiming universality.

**Decide packaging early.** Gutenberg ships `.epub` for all three, which is much cheaper than a new
ingest path — but PG EPUBs commonly use `<h2>` chapter headings or put the whole book in a single
spine document, either of which breaks the current parser (§5.1, A1). **Inspect the actual files
before choosing**; this is the same discipline `USER_GUIDE.md` §6 already mandates for new series.

**Licensing hygiene.** Record exact PG ebook IDs and retrieval dates in a committed manifest. PG
texts are public domain in the US but PG's own boilerplate carries trademark terms — strip the
header/footer and cite the ebook ID rather than redistributing PG's packaging verbatim. For the
commercial corpora, release statistics and derived graph structure only, and state the position
plainly in the paper's ethics/licensing section rather than leaving a reviewer to wonder.

---

## 5. Engineering programme

Everything below is **additive**. No existing contract changes. `graph/`, `synth/`, `site/` and
`eval/` contain zero series-specific strings, which is why this is tractable.

Follow the repo's own `CLAUDE.md` §4 protocol for each block: a dated entry in
`docs/vision/PHASE_<n>.md`, a one-line pointer in `VISION.md`, a handover in `docs/handover/`, and a
`LOG.md` entry at the top.

### 5.1 Phase 24 — Multi-corpus ingest and scale-out *(Months 1–2)*

**A1. Generalize chapter detection.** `ingest/epub.py` keys chapter boundaries on a literal
`soup.find_all("h1")`; the configurable `chapter_start_selector` is consulted only *afterwards*, to
extract the number text. Consequence: a PG EPUB using `<h2>` collapses every chapter into one.

Make the heading tag set configurable — `epub.chapter_heading_tags: [h1, h2]`, defaulting to `[h1]`
so 86 and Spice and Wolf parse byte-identically. Small patch, required, and covered by the existing
`tests/test_ingest.py`.

**A2. `ingest/plaintext.py` — only if PG EPUBs prove unusable after A1.** Check first. If needed:
emit the same `RawVolume` / `RawChapter` / `RawParagraph` shapes `ingest/segment.py` already
consumes, with a configurable chapter regex (`CHAPTER I.`, `ADVENTURE I.`, `第N回`), PG
header/footer stripping, and blank-line paragraph segmentation. Dispatch on file extension in
`cli.py::ingest`. Add a `docs/CONTRACTS.md` §1.5.

**A3. `corpus/package.py`.** Splits a PG download into `vNN` files per the volume map in §4,
deterministically, emitting a committed manifest with PG ebook IDs, retrieval dates, and checksums.
Note that `source.volume_pattern` requires a named `(?P<vol>\d+)` group **in the filename**, so
packaging must produce `sherlock-v01.epub`-style names.

**A4. Three series configs** — `config/series.{sherlock,three-kingdoms,monte-cristo}.yaml`, modelled
on `config/series.spice-and-wolf.yaml`, which is the proof that the quirk sections mostly take
defaults. Per `USER_GUIDE.md` §6: **inspect the real files before touching quirk sections**, and
record what was checked in the config's own comments — that annotation discipline is itself a
methodological artifact worth citing in the paper.

Three Kingdoms will need an `config/extraction.three-kingdoms.yaml` overlay for courtesy names,
titles, and transliteration variants. Budget real time for the post-`gazetteer` roster review: 86
needed heavy `entity_overrides` tuning, Spice and Wolf needed one exclusion, and RoTK with hundreds
of named characters will be the expensive one.

**A5. Write `tests/test_spoiler_leak.py`.** `CLAUDE.md` §1 says: *"`tests/test_spoiler_leak.py`
enforces this. If it fails, nothing else matters."* **The file did not exist when this was written
(2026-09-11); it was written on 2026-09-13 and now has 27 cases — see R8.** At the time the
invariant was enforced only indirectly, through `wiki audit pages` / `links` / `relationships` and
assertions scattered across other suites. The list of assertions below is what that file now pins.

For a paper whose central claim is temporal scoping, and whose artifact reviewers will open, this is
a credibility problem independent of whether the invariant actually holds. Write it in Month 1.
Assert, on a fixture graph:
- no claim with `first_vol > N` reaches a page rendered at cutoff N;
- no wikified link at cutoff N resolves to an entity with `first_vol > N`, and no alias with
  `first_vol > N` is matched (both conditions are already implemented in `site/wikify.py` — this
  pins them);
- no relationship pair page exists before both endpoints do;
- no codex entry surfaces an entity before its `first_vol`.

**A6. Full pipeline run, all corpora, all cutoffs.** The long pole. Start it the moment A1–A4 allow
and let it run in the background while §5.3 is built.

### 5.2 Phase 25 — Crawlable multi-page site *(Month 2)*

**The problem.** `site/static_site.py` emits one `index.html` plus `app.js`, and the viewer is a
**hash-routed SPA** (`#/character/<slug>`, `#/codex/<kind>`, `#/relationships/<a>/<b>`,
`#/timeline/<n>`). A naive HTML crawler sees exactly one page. **The headline evaluation cannot run
against this.**

**The fix.** Add a `--multipage` mode emitting real files:

```
dist/<series>/site/v<NN>/index.html
dist/<series>/site/v<NN>/character/<slug>/index.html
dist/<series>/site/v<NN>/codex/<kind>/index.html
dist/<series>/site/v<NN>/relationships/<a>--<b>/index.html
dist/<series>/site/v<NN>/timeline/v<MM>/index.html
dist/<series>/site/v<NN>/sitemap.xml
dist/<series>/site/v<NN>/robots.txt
```

Server-render from the same page model `site/bundle.py` already produces. **Reuse
`site/wikify.py`'s existing output** — it already emits `[surface](/character/<slug>)` links and
already applies the cutoff filter to both the target's and the matched alias's `first_vol`. That is
precisely the hyperlink-level spoiler guarantee the crawler evaluation depends on, and it is already
built and tested (`tests/test_site_wikify.py`).

The JSON bundle contract does not change; the existing SPA keeps working; this is a new emitter
alongside the old one.

### 5.3 Phase 26 — Evaluation harness v2 *(Months 2–4)*

Promote `wiki audit eval` to a top-level `wiki eval` with subcommands. **Keep the existing lexical
scorer** as the cheap CI regression gate it was designed to be — including the `negative_facts`
unconditional-FAIL behaviour, which is genuinely good design and worth describing in the paper as
"precision expressed as must-not-assert constraints rather than a score."

New modules under `src/narrativewiki/eval/`:

| Module | Purpose |
|---|---|
| `judge.py` | Entailment scoring. Local NLI **and** local-LLM judge behind one interface, routed through `llm/client.py` so it is cached, budgeted, and logged like everything else. **Started early, 2026-09-16:** `llm/providers/minicheck.py` (MiniCheck-FT5, pinned checkpoint) + `LLMClient.score_support` + `graph/support.py` already implement the classifier half, because arbitration needed it before evaluation did. Reuse that provider here rather than adding a second NLI path |
| `leak.py` | **Leak@t** (§2.2). Three tiers. Future-fact set = `claims` with `first_vol > t`, already in `graph.db` — no new annotation |
| `ceiling.py` | **Groundedness ceiling.** For each gold fact, is it entailed by *any* source paragraph at cutoff *t*? **Build this first** — it is cheap and it reinterprets every recall number in the paper |
| `kgalign.py` | Alias-aware, embedding-soft triple P/R/F1; GED on the aligned subgraph; hallucination and omission rates; centrality-rank Spearman vs. reference network |
| `humaneval.py` | Stratified annotation-task export (CSV/HTML), agreement computation (Cohen's κ / Krippendorff's α), judge-vs-human correlation |
| `contamination.py` | Closed-book probing (§5.4, D2) |
| `webtasks.py`, `crawler.py` | §5.6 |
| `baselines/*.py` | §5.5 |
| `report.py` | Per-corpus / per-cutoff tables, bootstrap CIs, paired significance tests, LaTeX export |

**Gold data expansion.** The existing format is good and should be kept verbatim — `entity_id`,
`canonical`, `source_url`, `transcribed`, `eval_vol`, `outline`, `facts: [{text, in_scope}]`,
`negative_facts`. It already encodes the key insight that whole-series references would punish
correct spoiler suppression, and the per-fact `in_scope` comments explaining *why* each exclusion
was made are exactly the provenance an annotation appendix needs.

Extend to:
- **Gold (human):** ~25 characters × 3 corpora, with `in_scope` resolved per cutoff. **This is the
  largest single time cost in the programme — plan 6–8 weeks part-time.** Start in Month 3, not
  Month 8.
- **Silver (derived):** Fandom / Wikidata / Wikipedia, extracted at scale, with its noise rate
  against gold measured and published.
- **Inter-annotator agreement:** you are solo, so **recruit two peers to double-annotate ~200
  items** for Cohen's κ. Without a κ number, "hand-transcribed gold" is not a citable resource. If
  recruiting truly fails, the fallback is author annotation plus frontier-model adjudication with
  disagreement rates reported — meaningfully weaker, and it must be stated in Limitations.

**On the metric hierarchy.** Say plainly in the paper which metric is the claim and which is the
gate. Three tiers reported side by side (lexical / entailment / human-validated) with their
correlations is far more convincing than one number, and it inoculates against the "your judge is
the same family as your generator" objection — which a reviewer *will* raise, and which you answer
with the human-agreement numbers.

### 5.4 Phase 27 — Contamination protocol *(Months 4–6)*

**D1. `corpus/perturb.py`** — produces a parallel corpus variant under `data/<series>-cf/`:

- **Entity remap.** Seeded and deterministic. Surrogate names preserve gender, era, culture, and
  morphology (so "Sherlock Holmes" → a plausible Victorian English name, not a random string, and
  the possessive/vocative forms still work). Apply across all surface forms using the **existing**
  gazetteer and Aho-Corasick automaton (`entities/automaton.py`) — do not write a second matcher.
  Emit an alignment map so every gold annotation, every Leak@t future-fact set, and every multi-hop
  task transfers automatically.
- **Paraphrase.** Paragraph-level, local model, with an entailment self-check that meaning is
  preserved and that original named entities are not reintroduced. Cache aggressively — this is one
  of the larger call volumes in the programme.
- **Explicit non-goal: event shuffling.** Document the rejection here and in §11 with the
  fidelity–resistance citation, so it is a reasoned methodological choice in the paper rather than
  an omission a reviewer notices.

**D2. `eval/contamination.py`** — closed-book probe. No tools, *k* independent trials, flag items
answered correctly in ≥ *k*/2. Run on original and perturbed variants, for every system including
baselines. Report the **memorization gap** per corpus.

**Prediction worth testing explicitly:** Sherlock Holmes should show a large gap (canonical,
endlessly discussed in English) and Three Kingdoms a smaller one in English translation. If that
differential shows up, it is a clean secondary result that validates the probe itself — the
instrument is measuring the thing it claims to measure.

**D3. Perturbation-validity check.** Run the *entire* pipeline on both variants and compare the
resulting graphs. If structure diverges beyond a stated tolerance, the perturbation damaged
something. **Report the divergence as a fidelity measure**; a small, honestly-quantified divergence
is far more credible than a claim of perfect preservation.

### 5.5 Phase 28 — Baselines *(Months 6–8)*

All under one fixed open-weight backbone, all reading the same chunked corpus, all answering the
same questions. Wrap each behind one interface in `eval/baselines/<name>.py`.

| Baseline | What it establishes |
|---|---|
| Vanilla RAG (BM25 + dense) | The floor |
| **GraphRAG** (Microsoft) | The reference graph-RAG system. Expensive — document its cost honestly; your cost advantage is a legitimate result |
| **LightRAG** | The cheaper graph-RAG; your closest architectural competitor |
| Long-context stuffing | Whole volume(s) in context where the window allows |
| Direct LLM, closed-book | Pure parametric memory — the contamination reference line |
| **Ablation: no spoiler gate** | Your system generating from *unfiltered* claims. Isolates the gate's contribution — **likely the single most informative row in the paper** |
| **Ablation: no temporal intervals** | Flat graph, no supersession. Isolates the interval model |
| **Ablation: no verification pass** | Isolates Phase 23's binding-verification contribution |
| **Ablation: no PPR** | Uniform evidence selection. Tests H4 from §2.2 directly |

The three system ablations are what turn "we built a thing" into "here is which part does the work,"
and they are the cheapest experiments in the programme because the infrastructure already exists —
`--model` overrides, run rollback, and per-stage caching make each one a configuration change rather
than a code change.

### 5.6 Phase 29 — Agentic multi-hop environment *(Months 7–9)* — the headline

**F1. `eval/webtasks.py` — task generation by construction.** Sample a path of length *k* through
the cutoff-filtered graph; emit a question whose answer requires traversing it; record the gold
hyperlink path. Because the path comes from the graph and the pages are rendered from that same
graph, **the gold derivation chain is known without annotation** — which is the property no existing
benchmark has.

Stratify by:
- **hop count** (2 / 3 / 4),
- **entity importance** (reuse `graph/ppr.py` — do not write a new centrality routine),
- **answer type** (entity / attribute / temporal / count),
- **cutoff**.

Hand-validate a random sample and **report the validity rate**. Auto-generated questions are only
credible with a measured validity number.

**F2. Cutoff-conditioned task pairs — the key experiment.** For each question, identify *t*₁ where
it is unanswerable from the site and *t*₂ where it is answerable. Serve the site at *t*₁.

> **A correct answer at *t*₁ is parametric-memory leakage, by construction** — the information is
> not in the environment.

Cross this with the original/perturbed axis and you get a 2×2 that separates four distinct failure
modes: genuine retrieval, memorization of the source text, memorization of secondary discussion
(Fandom/criticism), and hallucination that happens to be right. **No existing benchmark can produce
that decomposition.** This is the figure the paper is built around.

**F3. `eval/crawler.py` — the harness.** An agent loop with `search()` / `open_page()` /
`follow_link()` over the §5.2 multipage site, logging the full trajectory. Metrics:

- answer EM / F1;
- **path precision and recall against the gold hyperlink chain**;
- pages opened (efficiency);
- **abstention rate on unanswerable items** — the *t*₁ condition makes correct abstention a
  measurable virtue, which most QA benchmarks cannot reward.

Trajectory-level scoring is what distinguishes this from yet another multi-hop QA set. Say so
explicitly.

**F4. Agent sweep.** Local backbone + one free-tier frontier + one paid frontier run, crossed with
original/perturbed and *t*₁/*t*₂.

### 5.7 Phase 30 — Artifact and release *(Months 10–12)*

- Zenodo DOI (also satisfies CIKM's deposit requirement if that becomes the venue).
- Pinned model versions, quantizations, seeds, and sampling parameters.
- **The released LLM response cache** — reproduction with zero API spend and no GPU.
- Corpus manifests with PG ebook IDs, retrieval dates, and checksums.
- A one-command reproduction script regenerating every table and figure from the cache.
- A datasheet for the dataset and a model card for the pipeline.
- Derived-statistics-only release for the commercial corpora, with the licensing position stated
  plainly in the paper rather than buried in a README.

---

## 6. Twelve-month timeline

| Month | Work | Milestone / gate |
|---|---|---|
| 1 | §5.1 A1–A5 (ingest generalization, three series configs, **`test_spoiler_leak.py`**), corpus packaging | Three corpora ingest cleanly; `pytest -q` green |
| 2 | §5.1 A6 full runs start (background); §5.2 multipage site | Crawlable sites at every cutoff |
| 3 | §5.3 `judge.py`, `ceiling.py`; **gold annotation begins** | **Groundedness ceiling number** — reinterprets the 0.32 |
| 4 | §5.3 `leak.py`; Leak@t pilot on one corpus | First Leak@t numbers. **Gate: go/no-go on Claim 2** |
| 5 | Gold annotation continues; recruit annotators; run IAA | κ reported |
| 6 | §5.4 perturbation + contamination probes | Memorization gap measured. **Consider recruiting a co-author now** |
| 7 | §5.5 baselines (GraphRAG, LightRAG, RAG, long-context) | Comparison table v1 |
| 8 | §5.5 ablations; §5.6 F1–F2 task generation | Task set built and hand-validated. **Gate: is *t*₁/*t*₂ separating?** |
| 9 | §5.6 F3–F4 agent sweep | Headline table complete |
| 10 | Full experiment matrix; statistics; human eval of prose quality | All numbers frozen |
| 11 | **Write the paper.** Three weeks, not three days. Related work is the hard part | Full draft + external read |
| 12 | §5.7 artifact; revision; arXiv + ARR submission | Submitted |

> **Schedule correction, 2026-09-16.** Months 1–2 (multi-corpus scale-out) are **paused by standing
> instruction**: two volumes of one series until the pipeline, the evaluation and the benchmark are
> complete on that scope. The work that moved instead is output quality and measurement — which is
> the right order, since Month 3's groundedness ceiling and Month 4's Leak@t tiers are both
> uninterpretable while the extraction yield and the scorer are still moving. Re-plan from the month
> the scope rule lifts, not from 2026-09.

### Checkpoint discipline

Two explicit off-ramps. Take them without sentiment.

**Month 4 gate.** If Leak@t shows no measurable leakage under the gate, Claim 2 collapses. That is
still a *result* (it validates the filter-before-generate approach empirically for the first time)
but it is a weaker one. Pivot weight onto Claims 3 + 4 and retarget LREC-COLING or NeurIPS D&B.

> **Fired early, 2026-09-13 (§0).** Three of four channels measure at or near zero; the fourth
> measures 0.033 on the disclosure predicate. The gate has not fully closed — the stages most likely
> to leak (alias clustering, claim extraction) are unmeasured — but the *direction* is already the
> weaker branch. Treat Findings / LREC-COLING / NeurIPS D&B as the plan and main track as upside
> until §0's decisive run says otherwise.

**Month 8 gate.** If the agent evaluation is not producing a clean *t*₁/*t*₂ separation — because
tasks are too easy, too noisy, or the crawler harness is unreliable — cut to a benchmark-and-metric
paper and target a workshop or resource track, rather than pushing a weak main-track submission and
losing a review cycle.

**A rejected main-track submission costs ~4 months. A workshop acceptance costs nothing and is a
real publication.** Do not let sunk cost drive the venue decision.

---

## 7. What the repo is today (baseline facts)

**Recomputed 2026-09-16 from `data/spice-and-wolf/` and the test suite.** These numbers are the
paper's starting point and several belong in it. The 2026-09-11 column is kept where it moved, so
the direction of travel is visible.

| Fact | Source |
|---|---|
| Phases 0–23 complete, Phase 24 in progress; **851 tests green** (was ~700 on 2026-09-11) | `LOG.md`, `tests/` (36 files) |
| Validated on **2 volumes of 1 series**: 6,116 paragraph records, **35 entities, 874 claims, 712 intervals, 79 edges**, 56 scenes, 150 merged epithet mentions (was 33/556/74 on 2026-09-11) | `data/spice-and-wolf/04_graph/graph.db` |
| **3,955 accounted LLM calls, 1,280 cache hits, $0.00**, across 129 rollback-able runs (was 2,664/94) | `data/spice-and-wolf/budget.json`, `_runs/` |
| `tests/test_spoiler_leak.py` **exists**, 27 cases | `tests/` |
| A measurement subsystem exists: `probe/futureset.py`, `probe/channels/index.py`, `probe/report.py`, `wiki probe run index` — zero LLM calls | `src/narrativewiki/probe/` |
| A per-cutoff index build exists: `wiki gazetteer --gate=build`, `wiki extract --gate=build` | `paths.py::set_build_cutoff` |
| Support scoring (MiniCheck-FT5 NLI) is **written, uncommitted, never run live** | `graph/support.py`, `llm/providers/minicheck.py`, `docs/tasks/0005-*.md` |
| 86's 13 volumes are *parsed* (14.5 MB) but nothing past `03_claims` was re-run post-segmentation | `data/01_parsed/` (legacy unsegmented root) |
| Gold data: 10 hand-transcribed characters, one series, from Fandom | `docs/eval/gold/spice-and-wolf/` |
| Metrics are lexical keyword overlap, deliberately not semantic | `src/narrativewiki/eval/gold.py` |
| Mean `fact_recall` baseline **0.338**, latest full re-run **0.322** (within documented re-synthesis noise); mean `fact_precision` **0.93** over 8 scored characters | `docs/eval/gold/spice-and-wolf/baseline.json`, `LOG.md` 2026-09-16 |
| The lexical scorer has a named insensitivity case: Zheren 0 → 8 scene claims matching gold almost verbatim, `fact_recall` unchanged at 0.0 | `LOG.md` 2026-09-16 (later) |
| Ingest is EPUB-only; chapter detection hard-codes `find_all("h1")` | `ingest/epub.py` |
| Reference viewer is a hash-routed SPA — a crawler sees one page | `site/static_site.py`, `app.js` |
| `graph/`, `synth/`, `site/`, `eval/` contain **zero** series-specific strings | verified by inspection |
| Two open, documented defects: sarcasm-induced `PARENT_OF`; a character/location name collision | `docs/handover/PHASE_23.md` |
| The sarcasm defect survived **three** models across two capability tiers (two free-tier OpenRouter, local qwen2.5:32b) — a verification-design limit, not a capability one | `docs/vision/PHASE_24.md` 2026-09-16 |
| Full engineering-iteration record (shipped → failed on evidence → replaced), with the research area each failure belongs to | `NARRATIVEWIKI_CAPABILITY_REFERENCE.md` §4 |

**Three of these are paper-worthy as they stand:**

1. **$0.00 across 3,955 calls** with routing invariants pinned by tests (`test_config.py` asserts
   bulk stages stay local and that the pipeline runs with *no API key at all*). A zero-cost
   construction claim that is enforced by CI is unusual and worth a subsection.
2. **`negative_facts` as unconditional-FAIL constraints** rather than a precision score. Expressing
   precision as "must-not-assert" assertions is a genuinely nice evaluation-design idea.
3. **Two known defects documented rather than hidden**, with the failing evidence span recorded
   (`v02:c02:p0182` — a sarcastic "son of the great Jakob Tarantino" read as a parentage claim).
   That is exactly the kind of concrete error analysis reviewers reward, and it should go in the
   paper as a named failure mode, not be quietly fixed and forgotten.

---

## 8. Related work map

**⚠ Identifier-verified 2026-09-16; claim-unverified.** Gathered via web search on 2026-09-11.
All 51 ids used in this project were resolved against the arXiv API on 2026-09-16 — **51/51 exist
and their titles match the descriptions below** — and the PDFs are on disk. `docs/REFERENCES.md`
holds the generated table (real title, primary category, authors, date, why this repo needs it);
`python docs/fetch_reference_pdfs.py` regenerates both the table and the PDFs. What is still
**not** verified is whether each paper *says what this section claims it says*: only 2512.07474
has been read in full. Open the PDF before citing, and add to this file weekly.

### 8.1 Narrative KG, spoiler-aware and character-centric systems *(closest prior work)*

| Work | Claimed content | How we differ |
|---|---|---|
| **"Living the Novel"** (arXiv 2512.07474) | Diegetic Knowledge Graph + "Narrative-Present Gate": filters spans to story-time ≤ *t* before generation. Conversational agents from novels. One corpus (*20,000 Leagues*). CharacterBox metrics + user studies | **THE critical citation.** Same filter-before-generate invariant, already published. We differ on: hypertext vs. chatbot; claim-level provenance; intervals + supersession + contradiction arbitration; multi-corpus; **measured** rather than asserted safety |
| **EvolvTrip** (arXiv 2506.13641) | Temporal theory-of-mind graphs over literary characters; triples tagged with plot numbers | Psychological state vs. our encyclopedic facts; no hypertext artifact; no leakage measurement |
| **Narrative Knowledge Weaver** (arXiv 2606.05724) | Stable graph backbone over narrative entities; events, atomic facts, entity profiles, provenance | Retrieval-focused; no reading-order conditioning; no generated artifact |
| **Character network survey** (arXiv 1907.02704) | Survey of fictional character network extraction | Establishes the co-occurrence-network tradition we use only for *structural* comparison |
| **DiscoGraMS** (arXiv 2410.14666) | Character-aware discourse graph for screenplay summarization | Summarization, not KB construction |
| **Narrative World Model** (arXiv 2607.05577) | Narratology-grounded writer memory for long-form fiction | Generation-side; complementary |
| **Taggus** (arXiv 2508.03358) | Character social networks from Portuguese fiction | Pipeline comparison point for entity extraction |
| **Narrative understanding overview** (arXiv 2310.18783) | Survey | Framing/positioning source |
| **Narrative theory-driven LLM methods survey** (arXiv 2602.15851) | Survey | Framing/positioning source |

#### 8.1a — **VERIFIED 2026-09-12: "Living the Novel" (arXiv 2512.07474)**

Read in full (abstract + HTML body). First entry in §8 that is no longer unverified.

- **Venue/status:** arXiv preprint, **cs.HC**, 8 Dec 2025. Shanda AI Research (Tokyo),
  The University of Tokyo, Dalian University of Technology. No code/data release stated.
- **Task:** multi-character *conversational* agents from a novel. Two-stage training: Deep Persona
  Alignment (data-free RFT) + Coherence and Robustness Enhancing (story-time KG + retrieval-grounded
  training). The KG is a *training and retrieval substrate for dialogue*, not a published artifact.
- **Gate (the overlap):** "Diegetic Time Injection" links every entity/relation/event node to a
  temporal node; the **Narrative-Present Gate** "discards any entities or relations with timestamps
  exceeding the user-selected story time (>t*), guaranteeing spoiler safety"; "the final context
  provided to the generator consists exclusively of the values in the retained nodes and edges."
  This is `CLAUDE.md` §1, published. Confirmed: **do not claim filter-before-generate as novel.**
- **How story time is assigned: not specified.** The paper says nodes are linked to "a temporal node
  corresponding to its diegetic time coordinate (t)" and gives no procedure (no chapter index, event
  ordering, or interval semantics). No intervals, no supersession, no contradiction arbitration.
- **Scale:** one novel (*Twenty Thousand Leagues Under the Sea*), four characters
  (Nemo, Aronnax, Conseil, Ned Land). In-the-wild study: 12 participants, 5 days.
- **Safety measurement — the opening.** Their only leakage number is the **Timeline-coherence
  Test**: **100 hand-crafted direct questions about future events at one fixed early cutoff**;
  correct iff the character expresses ignorance. Full system **90.8%**; ablations without the
  story-time memory 26.8–42.2%.
  Two consequences, both usable:
  1. **The architectural "guarantee" is empirically ~9% wrong by their own measurement.** A gate
     described as guaranteeing safety fails roughly one probe in eleven.
  2. **Direct questioning is the only channel tested.** Verified: the paper does **not** measure
     implicit or inferential leakage — nothing on what a reader could *infer* from what is said, and
     nothing on structural channels (existence of a page, a link, a closed interval). Leak@t's
     entailment and inferential tiers (§2.2) therefore measure something no published work measures,
     and H1–H4 describe channels that cannot exist in a chat transcript at all.
- **Their stated limitations** (verbatim gist): teacher-LLM dependent; "our formal evaluation scope
  ... was centered on a single novel"; not benchmarked on non-linear timelines; small homogeneous
  user population. All three are axes this repo already exceeds or can exceed cheaply.

**Net effect on the programme:** kills nothing except the unstated hope that the gate itself was the
contribution (already handled in §2.1/R9). Strengthens Claim 2 — the citation now reads "prior work
asserts a guarantee and measures it with 100 direct questions on one novel at one cutoff; we measure
it across tiers, corpora and every cutoff, and it does not hold."

### 8.2 Automatic encyclopedic article generation

| Work | Claimed content | How we differ |
|---|---|---|
| **STORM** (arXiv 2402.14207) | Wikipedia-like article generation via multi-perspective question asking. **FreshWiki** dataset curated post-Feb-2022 to avoid leakage. **Heading Soft Recall / Heading Entity Recall** | Our `eval/gold.py` heading recall is in this metric family — cite it as the source. Their leakage mitigation is *recency*; ours is *counterfactual perturbation*, which does not expire |
| **WikiMAG** (AAAI) | Multi-agent guided structured Wikipedia-like generation; progressive planner, reflective inspector, versatile writer | Our `page_outline` config is a closed-vocabulary version of their planner. No temporal scoping |
| **RAPID** (arXiv 2503.00751) | Retrieval-augmented long-text generation with writing planning | Efficiency comparison point |
| **Hierarchical Memory Organization for Wikipedia Generation** (arXiv 2506.23393) | Memory structuring for article generation | — |
| **DeFine** (arXiv 2503.07170) | Decomposed fine-grained annotated dataset for long-form article generation | Annotation-protocol reference |

### 8.3 Data contamination *(essential — Claim 3 lives or dies here)*

| Work | Claimed content | How we use it |
|---|---|---|
| **"The Emperor's New Clothes in Benchmarking?"** (arXiv 2503.16402) | Rigorous examination of BDC mitigation. 11 strategies incl. permutation, paraphrase, synonym replacement, back-translation. **Finds a fidelity–resistance tradeoff: none is both effective and faithful** | **The citation that kills event shuffling.** Must be engaged directly in §2.3 |
| **Survey on Data Contamination for LLMs** (arXiv 2502.14425) | Taxonomy, detection, mitigation | Framing |
| **Unveiling the Spectrum of Data Contamination** (arXiv 2406.14644) | Detection → remediation survey | Framing |
| **Clean-Eval** | LLM paraphrase + back-translation, semantic filtering | Method comparison for `corpus/perturb.py` |
| **DE-COP** | Verbatim vs. paraphrase multiple-choice probing for copyright/contamination detection | Probe-design reference |
| **"Speak, Memory" / novel memorization cloze work** | Cloze task + data archaeology over 571 novels | **Directly on point** — evidence that novels specifically are memorized. Use to motivate the perturbation |
| **Contamination-resistant benchmarks** (arXiv 2605.19999) | Position paper | Positioning |
| **awesome-data-contamination** (GitHub, lyy1994) | Curated paper list | Use for §8.3 completeness sweep in Month 10 |

### 8.4 Agentic retrieval and web environments *(Claim 4's neighbourhood)*

| Work | Claimed content | How we differ |
|---|---|---|
| **The Synthetic Web** (arXiv 2603.00801) | Procedurally **fabricated** mini-internets: 15,476 articles / 77 sites / 64.3M chars; credibility + factuality ground truth; **contamination filtering via closed-book probe (drop if correct in ≥2 of 4 trials)**; corpus withheld for dual-use reasons | **Closest environment-design neighbour.** Borrow the probe protocol; differ on real-text anchor, provenance to source spans, counterfactual pairs, cutoff axis, and full release |
| **BrowseComp-Plus** (ACL 2026) | ~100k human-verified fixed corpus; disentangles retrieval failure from reasoning failure | Real ⇒ memorized; no counterfactual control; no cutoff knob |
| **SimpleWikiSearch** (arXiv 2607.26070) | Clean offline Wikipedia environment for agentic search | Same limitation |
| **AgentWebBench** (arXiv 2604.10938) | Multi-agent coordination over a public web corpus | Coordination-focused |
| **BrowseComp** (OpenAI, 2025) | 1,266 multi-hop browsing questions | The task-design reference point |
| **WebArena / VisualWebArena** | Synthetic web environments with execution-based verification | Execution-verified but not knowledge-scoped |
| **GTA** (arXiv 2605.29218) | Long-horizon web-agent task generation at scale | Task-generation comparison |
| **Odysseys** (arXiv 2604.24964), **BrowserArena** (arXiv 2510.02418), **WebChoreArena** (arXiv 2506.01952), **DR-Arena** (arXiv 2601.10504), **SGR-Bench** (arXiv 2605.22219) | Web-agent benchmarks | Breadth citations for the related-work paragraph |

### 8.5 KG construction and its evaluation metrics

| Work | Claimed content | How we use it |
|---|---|---|
| **"Enhancing KG Construction: Hallucination, Omission, and Graph Similarity Metrics"** (arXiv 2502.05239) | Evaluation with explicit hallucination/omission analysis | **Primary metric source for §5.3 `kgalign.py`** |
| **Grapher / "KG Generation From Text"** (arXiv 2211.10511) | **T-F1, G-F1, G-BERTScore**; permutation-invariant alignment | The metric definitions to adopt — *not* isomorphism |
| **LLM-empowered KG construction: a survey** (arXiv 2510.20345) | Survey | Positioning |
| **PiVe** (arXiv 2305.12392) | Prompting with iterative verification | Comparison for our `graph/verify.py` |
| **Can LLMs be Good Graph Judge?** (arXiv 2411.17388) | LLM-as-judge for KG construction | Judge-design reference and a caution |
| **KGGen** (2025) | LLM triplet extraction + entity/relation resolution | Pipeline comparison |
| **Extracting Summary KGs from Long Documents** (arXiv 2009.09162) | Long-document KG extraction | Pre-LLM baseline |
| **Fine-tuning or prompting on LLMs: evaluating KGC** (Frontiers in Big Data, 2025) | Empirical comparison | — |

### 8.6 Graph RAG *(baselines)*

**GraphRAG** (Microsoft) — community detection + traversal; strong global understanding, very high
token cost, expensive to update. **LightRAG** — vector-first entity/relation retrieval with the
graph for structural context; incremental updates. Also **ReMindRAG** (arXiv 2510.13193),
**XGRAG** (arXiv 2604.24623), **Query-Aware Flow Diffusion** (arXiv 2605.18775). LightRAG is the
closest architectural competitor and the most important baseline to run well.

### 8.7 Temporal leakage metrics from adjacent fields *(the Leak@t analogy)*

The finance/backtesting literature has developed exactly the metric family Leak@t needs, under the
name temporal leakage:

- **"All Leaks Count, Some Count More"** (arXiv 2602.17234) — **Shapley-weighted Decision-Critical
  Leakage Rate (Shapley-DCLR)**: decompose rationales into atomic claims, use Shapley values to
  quantify each claim's decision impact. **The closest methodological template for Leak@t** —
  claim-level decomposition plus impact weighting.
- **Temporal Leakage in Financial News NLP** (arXiv 2608.17223) — multi-architecture leakage audit.
- **TimeSPEC / Teaching LLMs When Not to Know** (arXiv 2605.14636) — temporally-filtered retrieval
  with claim-level supervision; "ex-ante reasoning" and the definition of temporal leakage as *use
  of post-cutoff knowledge under an explicit pre-cutoff restriction*.

**Citing across fields here is a strength.** It shows Leak@t is an instance of a recognized problem
rather than a bespoke metric invented to make one system look good — which is the standard objection
to any new metric proposed alongside the system it evaluates.

### 8.8 Attribution and grounding

**AIS (Attributable to Identified Sources)** and **ALCE** for citation-quality evaluation — the
framework for `eval/gold.py::score_citation_entailment` and the visible "Sources: v1 p.9" citations
added in Phase 23 E4. Verify exact references before citing.

---

## 9. Target paper skeleton

Eight pages + unlimited references, ACL format. Know from Month 1 what every experiment is *for*.

| § | Content | Figures / tables |
|---|---|---|
| **1. Introduction** | Progressive knowledge scoping. The cheap-supervision argument. The memory-vs-retrieval probe. Explicit, early acknowledgement of filter-before-generate prior work. Four contributions | **Fig. 1**: one corpus → N knowledge states → N sites; same question answerable at *t*₂, not *t*₁ |
| **2. Related work** | The six groups from §8, each ending in one sentence of differentiation. **Budget 3 weeks; this section decides unsupervised first papers** | **Table 1**: the positioning matrix from §2.4 |
| **3. Task formulation** | Formal definition of progressive knowledge scoping. Leak@t definition. Why reading order ≠ wall-clock time | — |
| **4. System** | Pipeline in ~1.5 pages. Emphasize claim-level provenance, intervals + supersession, contradiction arbitration, and the $0.00 zero-API-key construction | **Fig. 2**: architecture, EPUB → pages, with the cutoff filter marked |
| **5. NARRATIVEWIKI-BENCH** | Corpora, volume mapping, gold protocol + **κ**, silver tier + noise rate, perturbation protocol, closed-book validation | **Table 2**: corpus statistics. **Table 3**: annotation agreement |
| **6. Experiments** | 6.1 Construction quality + **groundedness ceiling**. 6.2 **Leak@t** across the four channels (L_query/L_artifact/L_build/L_param), both tiers, render vs. `--gate=build`. 6.3 Contamination / memorization gap. 6.4 **Multi-hop agents, *t*₁ vs *t*₂**. 6.5 Ablations | **Table 4**: quality vs. baselines. **Fig. 3**: Leak@t by cutoff and page type. **Table 5**: memorization gap. **Fig. 4**: the 2×2 memory-vs-retrieval decomposition. **Table 6**: ablations |
| **7. Analysis** | Why filtering leaks (per channel, with mechanisms; H1–H4 retracted 2026-09-13, see §11). The selection-vs-disclosure predicate gap as a methodological finding in its own right. Named failure modes — sarcasm-induced `PARENT_OF`, character/location collisions. Cost analysis vs. GraphRAG | **Fig. 5**: leak channel diagram |
| **8. Limitations** | Judge/generator family overlap. Single annotator + 2-peer subset. Corpus scale. Local backbone. What the perturbation does not defend against | — |
| **9. Ethics & licensing** | PG provenance. Commercial corpora excluded from release. Dual-use of a memorization probe | — |

**Figure 4 is the paper.** If it is clean and legible, the paper is strong. Design the experiment
backwards from that figure.

---

## 10. Rejection-risk register

| # | Risk | Severity | Owner phase | Status |
|---|---|---|---|---|
| R1 | **No baselines** — uninterpretable numbers | Fatal | §5.5 / M7 | Open |
| R2 | **Lexical metrics as primary** | Fatal | §5.3 / M3 | Open — **now with a named on-corpus instance**: a page rebuilt to match gold almost verbatim scored 0.0 recall (2026-09-16). Stop reporting recall movement until the entailment tier exists |
| R3 | **Scale: 2 volumes, 1 series** | Fatal | §5.1 / M1–2 | Open |
| R4 | **LLM judge with no human validation** | Fatal | §5.3 / M5 | Open |
| R5 | **Contamination asserted, not measured** | Fatal | §5.4 / M6 | Open |
| R6 | **No statistical treatment** (seeds, CIs, significance) | Major | §5.3 `report.py` / M10 | Open |
| R7 | **Copyrighted corpus in the artifact** | Fatal (legal) | §4 / M12 | **Resolved by decision** — PG-only release |
| R8 | **`test_spoiler_leak.py` does not exist** while CLAUDE.md §1 says it enforces the core invariant | Fatal (credibility) | §5.1 A5 / M1 | **Resolved 2026-09-13** — 27 tests, `pytest -q` 706 passed |
| R9 | **Filter-before-generate already published** | Major (novelty) | §2.1 framing | **Open again 2026-09-13 (pm)** — the differentiator is now *build-time* gating (`--gate=build`), which is architecturally novel but currently closes a leak measured at 0.033/0.000 on the disclosure predicate. Novelty rests on the decisive run in §0, not on 0.303 |
| R17 | **Headline leak number is predicate-dependent** — 0.303 (selection) vs 0.033 (disclosure) on the same data | Fatal (integrity) | §2.2 / immediate | **Resolved 2026-09-13** — both tiers defined, both reported, disclosure tier leads. Never cite 0.303 unqualified |
| R18 | **`--gate=build` demonstrated on n = 1 leaking surface**, on the corpus with the smallest leak | Major | §0 decisive run | Open, and **now partly blocked by decision** — the gate reaches alias + claims and is clean there (0 inconsistencies introduced), but the 86 run that would give it a bigger n is out of scope under the standing 2-volume rule |
| R19 | **Individuation is undecided** — cutoff-dependent `holo`/`wisewolf` fragmentation is either a bug or the correct behaviour, and the paper cannot say which | Major (framing) | §2.2 / before any write-up | Open — n=2; sweep more characters/cutoffs/corpora and decide before it enters the claim list |
| R20 | **Iteration without persisted diagnostics** — for five days, drop-reason counters were printed and discarded and a shipped fix was never re-run, so every eval number in that window predated its own fix | Major (integrity) | §5.3 / immediate | **Resolved 2026-09-16** — `_runs/<id>/yield.json` persists kept/dropped counts per run. Any number measured 2026-09-11 → 2026-09-16 must be re-measured before use |
| R21 | **Self-reported model confidence used as a decision signal** in arbitration | Major | §5.3 / M3 | **Retired on evidence 2026-09-16** (confidence 1.0 beat the correct 0.72 value). Replacement (MiniCheck-FT5 NLI) written, uncommitted, **unrun** — the risk stays open until a live scored run exists |
| R22 | **Scope is fixed at 2 volumes / 1 series by standing instruction** until pipeline + eval + benchmark are complete | Major (schedule) | §5.1 | Open by decision, not by oversight. §6's Month 1–2 scale-out is paused; plan around it rather than assuming it will lift |
| R10 | **Judge and generator from the same model family** | Major | §5.3 / M5 | Open — answered with human agreement numbers |
| R11 | **Auto-generated tasks may be invalid or trivial** | Major | §5.6 F1 / M8 | Open — hand-validate and report validity rate |
| R12 | **Perturbation may damage the corpus** | Major | §5.4 D3 / M6 | Open — measure and report divergence |
| R13 | **GPU wall-clock overruns the schedule** | Major (logistics) | §5.1 A6 / M2 | Open — start runs early, consider 8B for the sweep |
| R14 | **Writing quality (solo, no advisor)** | Major | M11 | Open — 3-week budget, external read, consider co-author at M6 |
| R15 | **Unverified citations in §8** | Fatal (integrity) | M10 | **Half-closed 2026-09-16** — 51/51 ids resolve, titles match, PDFs on disk (`docs/REFERENCES.md`). Still open: only 1 paper read in full; an id is an address, not a confirmed claim |
| R16 | **Fandom used as gold while claiming contamination control** | Major (coherence) | §5.3 / M5 | Open — gold/silver separation, measure silver noise |

Review this table monthly. A risk that is still "Open" at its owner month is a schedule problem, not
a detail.

---

## 11. Decision log — what was rejected and why

Recorded so these are not relitigated at Month 7. **The engineering half of this log — modules that
shipped, failed on measured evidence, and were replaced — lives in
`NARRATIVEWIKI_CAPABILITY_REFERENCE.md` §4**, which keeps the failure, the number that condemned it,
the replacement, and the research area it belongs to in one table. This section keeps the
*programme-level* decisions.

**Retired on evidence (2026-09-16): self-reported model confidence as a decision signal.**
*Why:* `rule:lowest_confidence_dropped` kept Zheren's occupation as `"public witness"` (verbalized
confidence 1.0) over the gold-correct `"traveling merchant"` (0.72), with two other correct values
discarded by the same rule — a textbook instance of verbalized-confidence miscalibration
([2306.13063](https://arxiv.org/abs/2306.13063)) reproducing inside this pipeline. *Instead:* a real
NLI support score (local MiniCheck-FT5) against each claim's own cited evidence, at its first
evidence volume so later corroboration cannot retroactively change an earlier page. Written, not yet
run — the decision is made, the evidence for it is not in yet.

**Rejected (2026-09-16): fixing the sarcasm-induced `PARENT_OF` bug with a stronger model.**
*Why:* three models across two capability tiers (two free-tier OpenRouter models, one with reasoning
enabled, plus local qwen2.5:32b) all answered "supported", while the same 32B run flagged five
genuinely unsupported facts elsewhere. Verification asks whether a claim is supported by *its own
cited quote*, and the quote literally contains "son of ... Jakob Tarantino". *Instead:* a
verification-design change — broader same-chapter context for relation facts drawn from first-person
dialogue, or discounting self-description at extraction time. A fourth model retry is explicitly
ruled out.

**Chosen (2026-09-15, TASK-0004 Option A): per-volume-OR capitalisation ratio, not corpus-wide.**
*Why:* the corpus-wide ratio erased `Wisewolf` at t=2 (pooled 0.694 vs. volume-1's own 0.850) — the
threshold was measuring corpus composition, not the term. *Instead:* evaluate the ratio per volume
and accept a surface that passes in any single volume. The trade-off was measured before the call,
not asserted: render-mode `leak_rate` 0.042 → 0.115 (more surfaces shipped, 3 new multi-token false
positives), `tainted_claim_rate` 0.013 → 0.000. Three already-published headline numbers were
measured against the old behaviour, so the probe re-run was an acceptance criterion.


**Corrected (2026-09-13, pm): the L_build headline restated from 0.303 to 0.033.** *Why:* an audit
of all 37 "leaking" surfaces at 86/t=1 found 31 occur verbatim in volume-1 text (up to 97×), 2 are
article variants of strings seen 12–14×, and all 37 belong to entities with `first_vol = 1` — the
probe measures whether cutoff-only mining would have *selected* a surface, not whether a cutoff-*t*
reader could have *seen* it. *Instead:* two named tiers — selection consistency (the diagnostic,
0.303) and disclosure (the reportable number, 0.033 exact-normalised at 86/t=1, 0.000 at
spice-and-wolf/t=1) — both reported, disclosure leading. Recorded rather than quietly rewritten
because the 9× swing on a change of predicate is itself the methodological lesson. See §0, §2.2,
`ConvinceMe.md` Addendum 2, `docs/probe/reanalysis_first_occurrence.py`.

**Retracted (2026-09-13): H4 ("PPR concentrates on future importance").** *Why:* checked directly
against `graph/ppr.py::build_subgraph`, which already restricts to `all_edges_at(conn, upto_vol)`
— cutoff-correct by construction, pinned by `tests/test_ppr.py::test_build_subgraph_filters_by_cutoff`.
H4 as originally drafted (§2.2, 2026-09-11) is false. *Instead:* H1-H4 replaced by a four-channel
taxonomy (L_query/L_artifact/L_build/L_param) organized by when the future touched the system,
which subsumes H1-H3 under L_artifact and replaces H4 with L_build — a real, measured, non-zero
channel one pipeline stage earlier (candidate discovery, not retrieval). See §2.2 and
`docs/vision/PHASE_24.md` 2026-09-13.

**Deferred (2026-09-13): Claim 4, the agentic environment, to a second paper.** *Why:* it needs a
crawlable multi-page emitter, task generation, and agent baselines before any number exists
(originally scheduled M8); Claims 1-3 are fully self-contained, need no API budget, and already
have a first real result (L_build). *Instead:* paper 1 ships the leakage taxonomy + benchmark;
paper 2 reuses the identical graph/provenance machinery for the agentic environment as a
follow-up, not a dependency. See §2.4.

**Rejected: event shuffling as a contamination defence.** *Why:* it destroys the reading-order
structure that is the paper's independent variable, and the mitigation literature already documents
a fidelity–resistance tradeoff covering permutation-style strategies. *Instead:* the cutoff axis
provides variation without incoherence, and entity remap + paraphrase provides surface-form
variation with a bijection-guaranteed fidelity argument.

**Rejected: graph isomorphism as an evaluation metric.** *Why:* NP-hard, label-blind, and
semantically wrong — a graph with every relation type swapped is isomorphic to the correct one.
*Instead:* alias-aware embedding-soft triple P/R/F1 (T-F1), G-F1, GED on the aligned subgraph,
hallucination/omission rates, and centrality-rank Spearman for structural comparison.

**Rejected: Fandom/Wikidata as the primary ground truth.** *Why:* those pages are heavily
represented in pretraining data, making them incoherent as a target for a
contamination-controlled evaluation; they also describe whole series, which punishes correct spoiler
suppression; and co-occurrence networks measure proximity, not typed relations. *Instead:* a three-
tier scheme — human-adjudicated gold for claims, derived silver with measured noise for scale, and
structural correlation as the honest use of the co-occurrence graphs.

**Rejected: a different frontier model per system in the baseline table.** *Why:* it confounds
architecture with model budget, and it is unaffordable. *Instead:* a single fixed open-weight
backbone for every system, stated as a deliberate controlled-comparison protocol.

**Rejected: keeping 86—EIGHTY-SIX as the primary corpus.** *Why:* commercial EPUBs cannot be
redistributed; a benchmark whose data cannot be released scores badly on reproducibility and may
violate venue artifact policy. *Instead:* PG corpora are the released benchmark; 86 and Spice and
Wolf become a non-redistributable qualitative case study releasing derived statistics only.

**Rejected: two separate papers (system paper + benchmark paper).** *Why:* 12 months solo is not
enough for two submissions at main-track quality, and splitting weakens both — the system's
justification is the benchmark, and the benchmark's credibility is the system. *Instead:* one paper
where the system is the *constructor* of the benchmark. Revisit only if the Month 4 and Month 8
gates both pass with room to spare.

**Rejected: replacing the lexical `eval/gold.py` scorer.** *Why:* it is a well-designed, zero-cost
CI regression gate, and its `negative_facts` unconditional-FAIL behaviour is genuinely novel
evaluation design worth describing in the paper. *Instead:* keep it in that role and add entailment-
based scoring above it, reporting all tiers with their correlations.

---

## Appendix — verification checklist per phase

- `pytest -q` green after every phase; `tests/test_spoiler_leak.py` present and passing.
- `wiki doctor --series {sherlock,three-kingdoms,monte-cristo}` clean.
- The full audit suite passes on every new corpus:
  `wiki audit ingest | gazetteer | scenes | claims | contradictions | verify | outline | pages | eval | links | relationships`.
  This existing suite is the regression net for the entire scale-out — it is the reason adding
  corpora is safe.
- §5.2: a recursive crawl over `wiki serve` reaches every character page; no link at cutoff *N*
  resolves to an entity with `first_vol > N`.
- §5.3: judge-vs-human correlation is reported *before* any judge-derived number is used in the
  paper.
- §5.4: the pipeline runs on both original and perturbed variants; graph divergence is within the
  stated tolerance and is reported either way.
- §5.6: 50 randomly sampled generated tasks are hand-validated; the validity rate appears in the
  paper.
- §5.7: one command reproduces every table and figure from the released cache, with no API key and
  no GPU.
