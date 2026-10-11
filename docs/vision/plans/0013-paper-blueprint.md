# 0013 — NarrativeWiki paper blueprint and submission roadmap

**Status:** authoring blueprint complete; submission evidence incomplete. No paper has been written and no experiments are authorized by this document alone.
**Reviewed:** 2026-09-27; revised the same day (citation status, ID key, spend cap, 0012 baseline mapping).
**Repository revision inspected:** `ec5519bc2057a0f8e501f74d6bcd2c5bc35bfe77` (working tree also contained unrelated changes; they are not a frozen experimental release).
**Audience:** NLP/IR research, with a conference-length core and supplementary detail suitable for a later journal extension.
**Companion records:** [evaluation tracker 0012](0012-research-evaluation-data.md), [paper values tracker 0014](0014-paper-values-tracker.md), [measurement ledger](../../MEASUREMENTS.md), [five-volume implementation plan 0011](0011-five-volume-generalised-evaluation.md), [data contracts](../../CONTRACTS.md), [paper inventory](../../papers/PAPERS.md), [verified reference inventory](../../papers/REFERENCES.md).

This is an instruction manual for writing the paper, not manuscript prose. Follow its section cards, replace evidence placeholders only after validation, and keep unsupported conclusions out of the abstract. Good organization reduces avoidable review problems; it cannot guarantee acceptance. Assess the submission against [ARR reviewer guidance](https://aclrollingreview.org/reviewerguidelines), then recheck the selected venue's current instructions before submitting.

## 0. How to use this blueprint

### 0.1 Scope and authority

- Evaluate at most **five volumes per series, including Anne and Oz**. The maintainer explicitly selected this cap for this blueprint. It takes precedence over the longer Anne/Oz proposals in [Phase 33](../PHASE_33.md) and plan 0012. Preserve those historical records; do not copy their broader commands into this study. The paid route's interlock enforces the cap mechanically (`max_volumes: 5` in `config/models.yaml`).
- Published experimental results use public-domain works. Spice and Wolf, Overlord, and Bookworm remain development material; their findings can guide internal diagnosis but their numerical results are excluded from the paper under the publication rule. Leagues, Pride and Prejudice, and Little Women (2–3 cutoffs, small casts, Phase 33) are development material too: E05's verifier A/B ran on Leagues.
- Historical builds that processed more than five volumes are not automatically valid five-volume experimental artifacts. Earlier pages may depend on later construction. A compliant experiment needs a scoped provenance record, not merely a truncated output directory.
- **Spend is capped at the maintainer's hard $200 total.** `budget.lifetime_cap_usd` is set to $185 with `billed_offset_usd` covering the measured ledger-vs-bill gap, so an ~8% undercount on remaining spend still lands under $200; `hard_stop_usd` ($10) bounds each run. Every billed step in §4 and §8.1 must fit inside what remains under that cap (`wiki budget`), with a cost estimate recorded first. Re-read the billing console and update the offset before any large run. Raising the cap is a maintainer decision, never a step in this plan.
- Use one general pipeline. Series configuration may normalize input structure; it must not inject roster corrections, facts, special prompts, or output patches.
- Independent human evaluation is required for the strongest quality claims. Section 8.4 defines the resource-constrained pilot alternative.

### 0.2 Evidence labels and placeholder convention

Use these labels in the working draft, result inventory, and display specifications. Remove internal labels from the submitted manuscript only after resolving their meaning in the prose.

| Label | Meaning | Allowed use |
|---|---|---|
| **available evidence** | An implementation artifact or recorded observation exists and has a source pointer | Describe its exact scope; availability alone does not make it a valid comparative result |
| **requires revalidation** | Historical result, limited sampling frame, changed code, uncertain annotation, or incompatible scope | Motivate an experiment; do not use as the final headline result |
| **missing experiment** | Required comparison or measurement has not been completed under the submission protocol | Retain a placeholder and a completion gate |
| **optional extension** | Additional study supports a claim outside the core submission | Omit the claim if the study is not conducted |

**ID key.** E01–E12 evidence items (§0.3) · RQ1–RQ5 research questions (§1.1) · T0–T5 tables, F1–F3 figures (§5) · M1–M13 metrics (§3.1) · B1–B5 baselines, X1–X2 diagnostic controls (§4.1) · A1–A7 ablations (§4.2; not appendices) · R1–R17 citations (§6.2) · P0a–P3b work packages (§8.1) · "appendix A"–"appendix K" always spelled out (§7). "Plan 0012 Dn" means that tracker's deliverable rows, not this file's IDs.

Result placeholder format: `[RESULT-ID: VALUE; NUMERATOR/DENOMINATOR; INTERVAL; WORK; CUTOFF; RUN; LEDGER ENTRY]`. Unmeasured quantities remain placeholders, never plausible-looking example scores. Targets and sample-size proposals must be called design choices, not observations.

Write the paper in this order: task and annotation definitions → methods → experimental protocol → tables → results → discussion/limitations → introduction → abstract/title. This keeps the headline aligned with the evidence.

### 0.3 Current evidence and its limits

| ID | What is known at the reviewed revision | Status | Evidence pointer and implication |
|---|---|---|---|
| E01 | Evidence-bearing claims, temporal queries, deterministic page assembly, and constrained prose are implemented | **available evidence** | [Contracts](../../CONTRACTS.md), [temporal queries](../../../src/narrativewiki/graph/temporal.py), [assembly](../../../src/narrativewiki/synth/assemble.py); supports a method description, not a semantic safety proof |
| E02 | Historical gold precision included selected negative controls rather than all emitted assertions | **requires revalidation** | Ledger §22 and §48; do not reuse the old metric as end-to-end precision |
| E03 | The newer assertion sampler covers cited structured lines; prose and uncited assertions are outside its population | **available evidence** | [Sampler](../../../scripts/eval/assertion_precision.py); a broader assertion inventory is needed for the proposed metric |
| E04 | Cutoff leak probes and artifact exposure tooling exist | **requires revalidation** | [Page probe](../../../scripts/eval/pipeline_page_leak.py), [artifact probe](../../../scripts/eval/artifact_exposure.py), ledger §43–§48; automated matches are screens, and sampled future-fact sets are incomplete |
| E05 | Historical verification and gleaning comparisons reveal precision/coverage trade-offs | **requires revalidation** | Ledger §48; local development comparisons are not frozen end-to-end ablations |
| E06 | Alias eligibility uses surface appearance timing; this does not by itself date an identity link | **available evidence** | [Gazetteer](../../../src/narrativewiki/entities/gazetteer.py), Phase 33; specify the limitation and test it |
| E07 | Shared navigation exposed future vocabulary despite clean cutoff Markdown; a correction is recorded | **requires revalidation** | Ledger §48 artifact-exposure row; recheck final public-domain HTML, search, metadata, and links |
| E08 | Existing gold and some verdicts were created or read by an agent involved in development | **requires revalidation** | Plan 0012 D2/D3/D8/D11 and Phase 33; field names such as `human` do not establish independent human review |
| E09 | A complete matched prefix-baseline comparison is not established | **missing experiment** | Plan 0012 D13; short historical parametric controls are not substitutes |
| E10 | Oz is recorded as ingested and a candidate held-out work | **requires revalidation** | Plan 0012 D16 (all 14 books ingested; only books 1–5 are in scope here); inspect later history before freezing Oz 1–5 as test data |
| E11 | Full-assertion evaluation, stage retention, and semantic construction comparison remain incomplete | **missing experiment** | Plan 0012 D5–D11; core pre-submission work |
| E12 | A second generator family, second untouched work, and reader utility study could widen conclusions | **optional extension** | Require their own completed evidence before making the corresponding claim |

No new benchmark measurement is introduced here. All historical numerical evidence remains in the ledger. Its section numbers are stable references even when newer rows are appended.

## 1. Paper identity, research questions, and claim boundaries

### 1.1 Working title and central question

**Working title:** *NarrativeWiki: Evidence-Grounded Character Wikis at Reader-Selected Narrative Cutoffs*.

Choose a final title that names the task and demonstrated contribution. Avoid “spoiler-proof,” “hallucination-free,” “first,” “decontaminated benchmark,” or superiority language unsupported by matched experiments.

**Central question:** How much source-supported character information can a system preserve in a reference wiki at a reader's chosen cutoff, while limiting unsupported assertions and disclosure of later information?

Coverage, grounding, and boundary adherence are separate outcomes. Do not multiply or average them into a headline score. Always show output amount: silence can look safe.

| Research question | Experiment and evidence | Main display | Current status |
|---|---|---|---|
| RQ1: How does NarrativeWiki compare with strong prefix-only alternatives on coverage, support, and disclosure? | Frozen matched baselines; eligible gold; complete output sampling | T2, F2 | **missing experiment** |
| RQ2: How do construction scope and artifact presentation affect cutoff adherence? | Prefix/full construction pairs; semantic adjudication; complete artifact audit | T4, F1 example, appendix H | **missing experiment** |
| RQ3: Where are useful facts lost, and what do individual safeguards contribute? | Gold route tracing; controlled component removals; verifier challenge set | T3, F3 | **missing experiment** |
| RQ4: How do findings vary by work/cutoff and what does the system cost? | Per-cutoff outcomes and frozen run accounting | F2, T5, appendix E | **missing experiment** |
| RQ5 (optional): Do findings transfer across generator families or improve reader tasks? | Second-family comparison or independent reader study | Appendix E/K; main text only if central | **optional extension** |

### 1.2 Conditional contribution statements

1. **System contribution:** a general, evidence-linked pipeline that produces reader-cutoff reference artifacts. E01 supports the implementation description; deployment-level semantic claims still require evaluation.
2. **Evaluation contribution:** a protocol that jointly evaluates coverage, grounding, construction dependence, and disclosure across the delivered artifact. Claim an implemented reusable protocol only after its tooling and annotations exist.
3. **Empirical contribution:** a controlled account of retention and error trade-offs. Insert the actual result, including null or unfavorable outcomes, after RQ1–RQ4.

Temporal gating, verified character representations, and wiki generation have prior art. The proposed contribution is their particular integration and measured behavior, not ownership of those ideas.

### 1.3 Suggested main-text allocation

Use proportions rather than assuming a venue page limit: introduction 12%, related work 10%, task 10%, method 20%, experimental setup 18%, results/analysis 24%, discussion/conclusion 6%. These are editing targets, not constraints. Put limitations and responsible-research material where the chosen venue requires them. A journal extension should add evidence or deeper analysis, not merely expand prose.

## 2. Section-by-section writing cards

Each card specifies purpose, content, evidence, citations, display, and claims to avoid. Section names below are manuscript headings; this file's numbering is an authoring aid.

### 2.1 Title and abstract

**Purpose:** communicate the problem, approach, test, and bounded finding without requiring the reader to infer the task.

**Write:** fill five slots, in order, rather than drafting an abstract before results:

1. Problem: useful character references while reading an unfinished series.
2. Gap: retrieval filtering can leave construction, generation, or presentation channels unchecked.
3. Approach: evidence-linked extraction, validation, temporal assembly, and cutoff-specific publication.
4. Evaluation: `[PUBLIC-DOMAIN WORKS]`, `[CUTOFFS]`, `[MATCHED BASELINES]`, `[ANNOTATION PROTOCOL]`.
5. Finding: `[HELD-OUT COVERAGE DIFFERENCE WITH INTERVAL]`, `[PRECISION]`, `[DISCLOSURE WITH DENOMINATOR/BOUND]`, and the main limitation.

**Evidence:** T2 and F2 must be final; result slots are **missing experiment**. Cite no development metric as a substitute.
**Citations:** usually none in the abstract; follow the selected venue.
**Display:** abstract claims must be directly recoverable from T2/F2.
**Avoid:** an abstract that promises proof, hides low recall, or calls an agent-reviewed estimate human-validated.

### 2.2 Introduction

**Purpose:** establish a meaningful task and the precise empirical gap.

**Paragraph plan:**

1. Introduce the reader and one public-domain, source-verified example of consulting a character page mid-series.
2. Explain why a fact true in the complete story can be inappropriate at cutoff `t`; distinguish reader knowledge from chronology.
3. Explain why a nearly empty wiki is not a solution. Define usefulness through eligible fact coverage, supported assertions, and citations.
4. Motivate construction and publication failures. Include a delayed-identity example in which both names appear before their equivalence is revealed.
5. Acknowledge closest prior work; identify the complete reference artifact and joint evaluation as the question investigated here.
6. State RQ1–RQ4 and list only contributions supported by the completed study.

**Example rule:** until a suitable public-domain witness is verified, use an explicitly synthetic schematic (“A” and “B” appear in v1; evidence links them in v3). Never present that schematic as a novel finding. Do not import a spoiler example from a commercial development corpus into the published evaluation.

**Evidence:** E01/E06/E07 motivate the problem; exact public-domain examples require source IDs and adjudication. Comparative claims are **missing experiment**.
**Citations:** CHIRON, Living the Novel, TimeChara; recent SearchWiki/NS-ST-GraphRAG only for verified relevant capabilities (reference keys in §6).
**Display:** F1, including a compact before/after cutoff example.
**Avoid:** “no previous work considers time,” a development history narrative, or treating contamination as the central contribution without a validated study.

### 2.3 Related work

**Purpose:** explain what is borrowed, what is different, and why the comparison is fair.

| Subsection | What to explain | Evidence/citations | Display and boundary |
|---|---|---|---|
| Character/narrative representations | Character sheets, graph relations, evolving state; compare output and assessment units | CHIRON; EvolvTrip; inspect methods/evaluation before detailed claims | T0 comparison matrix; do not reduce CHIRON to a graph method |
| Temporally bounded systems | Reader versus character knowledge; story chronology versus disclosure order | Living the Novel; TimeChara; NS-ST-GraphRAG | T0; temporal filtering is prior art |
| Grounded article/wiki generation | Article organization, persistent pages, retrieval, navigability, provenance | STORM; SearchWiki; GraphRAG; LightRAG | T0; distinguish active navigation/QA from static reference generation |
| Factuality and attribution | Atomic assertions, supporting context, narrative ambiguity, judge errors | ALCE; AIS; MiniCheck; STORYSUMM; NarrativeFactScore | Evaluation definitions; literature validation does not establish local judge accuracy |
| Contamination/memorization | Recognition, fact transfer, compliance, fidelity of treatments | Contamination survey and mitigation study; local Phase 31 design | Appendix I; recognition reduction is not proof of no memorization |

**Writing pattern:** summarize a research line; name the closest methods; state a task or evaluation difference supported by the texts; state what this paper measures. Do not write one disconnected paragraph per downloaded PDF.

**T0 columns:** paper/version; task; output artifact; cutoff definition; construction scope; evidence provenance; evaluation unit; evaluated artifact surfaces. Use “not established from the paper” for unknown entries. Keep a compact comparison in the main text, extended details in appendix D or C.

**Citation placement:** introduction for the closest gap; related work for comparison; methods/evaluation at the actual use of a technique or metric; bibliography for full records. Do not confine all related work to the appendix.
**Status:** source records are **available evidence**; unread technical comparisons **require revalidation**.

### 2.4 Task definition and threat model

**Purpose:** make the target behavior and measured failure conditions unambiguous.

**Define:**

- `D_{<=t}`: text through reading volume `t`; `N <= 5` is the evaluated corpus scope.
- `W_t`: everything delivered during normal use at cutoff `t`, including page text, HTML, links, titles, slugs, metadata, shared navigation, search resources, codices, and source views.
- `G_t`: source-validated gold facts with earliest sufficient disclosure `r(g) <= t`; preserve attribution and modality in the fact.
- `F_t`: assessed future facts with `t < r(g) <= N`, a finite probe set rather than an exhaustive inventory of all spoilers.
- `C_t`: distinct atomic assertions in `W_t`. Deduplicate semantically identical claims at a declared unit (within a character page for the primary precision estimate); assess repeated delivery across pages separately with page exposure.
- `E_t(c)`: cited source evidence actually available through `t`; evidence presence, anchor validity, and semantic sufficiency are different properties.

Explain fact truth, source support, and citation support separately. A true assertion can cite the wrong passage. A source-supported future assertion can violate the boundary. Unsupported guesses are not automatically proven disclosures of a true later fact.

Distinguish narrator assertions, character beliefs, lies, hypotheticals, reported speech, and embedded stories. Preserve who believes/says a claim; do not treat every dialogue sentence as world truth. Reading order is not chronology. A surface occurrence is not evidence that two names refer to the same individual.

**Threat categories:** construction dependence; published disclosure; parametric contribution. Label construction differences harmless formatting, selection change, premature identity link, or actual revelation after adjudication. A future answer does not establish which channel caused it.

**Boundary:** test normal cutoff use and all automatically delivered resources. Deliberate navigation to an explicitly later-volume route is a separate access-control scenario, not automatically a failure of this task. Accidentally delivered later information in a sidebar or search response is in scope.

**Evidence:** annotation definitions and artifact inventories; broader semantic evaluation is **missing experiment**.
**Citations:** TimeChara/Living the Novel for positioning; AIS/ALCE for attribution distinctions; state local definitions as adaptations.
**Display:** F1 plus a small notation block.
**Avoid:** universal spoiler safety, exhaustive future gold, or equating full/prefix byte differences with semantic leakage.

### 2.5 Methodology

**Purpose:** allow a reader to reconstruct the approach and understand why each stage is needed.

| Stage | Explain inputs → outputs | Mechanism and failure modes | Source/status |
|---|---|---|---|
| Ingestion/segmentation | EPUB → ordered paragraphs with source IDs and boundaries | Deterministic structure conversion; missing chapters, paratext, ambiguous breaks | Contracts §1; **available evidence** |
| Entity discovery/resolution | Paragraphs → candidates, canonical entities, aliases, mention index | Lexical rules plus model classification/adjudication; overmerge, split, narrator omission, identity-link timing | Entity modules in project map; E06 **available evidence** |
| Evidence/extraction | Mentions and chapter spans → quoted, typed claims and scene records | Model extraction over windows and complementary passes; missed evidence, one-off emotions as traits, directional mistakes | Contracts §3/§3b; **available evidence** |
| Validation/graph | Claims → checked observations, deduplicated values, intervals/relations | Deterministic gates plus model/support checks; false rejection/admission, unresolved conflicts | Contracts §4; **available evidence**, comparative benefit **missing experiment** |
| Cutoff assembly | Graph and eligible evidence → page model | Deterministic sanctioned temporal queries; later evidence attached to an early claim must also be filtered | E01; **available evidence** |
| Publication | Page model → structured lists, constrained prose, citations, linked site | Structured fields deterministic; prose/model summaries conditional on evidence; aliases, links, shared resources may expose future information | Contracts §5; E07 **requires revalidation** on final artifacts |

Give each stage a short paragraph explaining input, operation, output, motivation, and risk. Put implementation knobs and full prompts in appendix C. Report actual generator and verifier routing separately; do not imply every check uses MiniCheck or every stage is deterministic.

**Running example:** trace one public-domain fact through paragraph → claim → verification disposition → temporal row → structured assertion/prose → citation. Show its behavior at adjacent cutoffs and, if applicable, one incorrect candidate rejected by a gate. Store source IDs with the example; no invented manuscript “result.”

**Algorithm 1 writing specification:** pseudocode should take corpus scope/build policy, entity, and cutoff; select eligible observations through sanctioned queries; filter each evidence span; assemble structured fields/history without revealing future interval endings; generate prose only from that input; publish cutoff-eligible links/resources. Annotate where semantic correctness and identity timing remain empirical assumptions. Describe the actual frozen implementation, not an idealized algorithm it does not satisfy.

Explain full-scope versus prefix construction explicitly. Present any new alias-link dating or artifact repair as a change only after implementation and testing. Current temporal intervals are disclosure-position observations, not an unrestricted world-time reasoner.

**Evidence:** code/contracts for behavior; retained/lost facts and performance **require experiments**.
**Citations:** MiniCheck, BGE-M3 for actual components; CHIRON for conceptual comparison; AIS for evidence attribution. Distinguish inspiration, adaptation, and implementation.
**Display:** F1, Algorithm 1, appendix schema/prompt examples.
**Avoid:** claiming correctness from a filter test, importing handwritten facts, or concealing full-corpus construction.

### 2.6 Experimental design

#### 2.6.1 Corpora and splits

**Purpose:** establish the population and independence of evaluation.
**Explain:** Anne 1–5 is already explored; Middlemarch Books I–V is development/stress material; Oz 1–5 is a candidate held-out series subject to a history check. Describe edition, natural versus imposed boundaries, narrative perspective, source length, recurring cast, and gold coverage. Distinguish a book, a volume cutoff, a series, and an independent work.
**Evidence:** source manifests, tuning history, freeze record, and T1; final scoped inventory is **missing experiment**. Historical larger-scope counts **require revalidation**.
**Citations:** primary corpus/edition records and reference-site records, not only dataset papers.
**Display:** T1; appendix B details.
**Avoid:** calling Anne held out, calling five volumes five independent works, or silently evaluating only favorable main characters. Freeze cast selection; missing pages stay visible in completeness/recall.

A second untouched work is an **optional extension** needed before stronger cross-work generalization claims. If only Oz is held out, describe evidence from that series without a population-wide claim. Do not select the second work after looking for favorable system performance.

#### 2.6.2 Gold and annotation

**Purpose:** give the metrics independent, source-grounded meaning.
**Explain:** reference wikis nominate facts; source paragraphs establish truth/attribution and earliest sufficient disclosure. Maintain gold independently of what the system happened to extract. Exhaustive-source recall is not claimed for a selected gold inventory.

The annotation manual must specify atomicity; relation direction; polarity; modality; speaker/belief attribution; characteristic traits versus transient states; sufficient context; earliest support; partial/unsupported/uncertain labels; and adjudication. Assign optional importance weights using only the prefix before outputs are shown.

For the full path, use independent human assessment, blind system IDs, randomized item order, and a double-labeled stratified subset across works/cutoffs/assertion types. Record annotator expertise and independence, overlap, raw agreement and an appropriate chance-corrected statistic, disagreement examples, and adjudication. Never fabricate annotators or infer human participation from a column name. STORYSUMM (R7) found that any single protocol, even with near-perfect agreement, recovered only about two thirds of the errors that a union of fine-grained, adjudicated-expert, and LLM-suggested-then-human-filtered protocols found. So a high κ does not imply complete labels: where the budget allows, merge two protocols on the double-labeled subset, and tag each error easy (every protocol found it) or hard (only one did).

Choose sample sizes before comparative testing using an annotation pilot and desired interval precision. State per-cutoff counts, sampling fractions, clustering, and excluded items. The tracker’s item targets are planning floors, not a power analysis. Preserve uncertain judgments and report a sensitivity analysis rather than silently dropping difficult items.

**Evidence:** annotation records and agreement **missing experiment**; existing agent labels **require revalidation**.
**Citations:** AIS/ALCE; STORYSUMM for narrative assessment; any imported rubric at its point of use.
**Display:** T1, appendix A/F.
**Avoid:** evaluating only cited assertions, positives, or facts the model already found; equating semantic truth with citation entailment.

#### 2.6.3 Baselines and fairness

**Purpose:** test whether the system adds value over simpler and external alternatives.
**Explain:** use B1–B5 in §4.1; use X1/X2 as diagnostics. Match the generator, task, available prefix for fair competitors, output requirements, character population, and declared evidence/output budget. Show native costs separately from a budget-matched comparison. Record preprocessing and index costs.
**Evidence:** implementations, adaptation notes, development settings, and frozen runs **missing experiment**.
**Citations:** LightRAG for B3; GraphRAG as architectural context; do not call a custom graph baseline a reproduction.
**Display:** T2; appendix D protocol matrix.
**Avoid:** weak prompting, silent truncation, hidden full-text access, oracle gold evidence, or different cast lists. If long-context input exceeds a model limit, mark the cell unsupported for that baseline and report a separately named chunked adaptation; never silently drop text.

#### 2.6.4 Reproducibility and statistics

**Purpose:** make results auditable and uncertainty credible.
**Explain:** freeze code, configuration, prompts, source editions/hashes, gold, evaluation scripts, routing, model revisions, and sampling decisions. Report every work/cutoff before macro summaries. Aggregate cutoffs within work before an equal-work summary; do not let a long or large-cast series dominate by accident.

Report paired differences and uncertainty with the unit stated. Account for claims within pages/characters and repeated cutoffs. Preserve an entire work’s cutoff trajectory when resampling works; with too few independent works, emphasize work-specific paired estimates and limited generalizability rather than pretending a work bootstrap provides strong population inference. For within-work uncertainty, respect character/page clusters and the sampling design. State whether intervals reflect annotation sampling, generation variation, or both.

Fresh stochastic outputs may be replicated, using explicit run/sample identifiers through the normal cached client. A cache replay is not an independent sample. Never clear the cache to manufacture independence. Record refusals, fallback providers, missing pages, and failures; a fallback-mixed run is a separate condition from a single-model run.

**Evidence:** freeze/run manifests and analysis scripts **missing experiment**; provenance infrastructure **available evidence**.
**Citations:** cite any borrowed statistical method when adopted; use current venue reproducibility guidance.
**Display:** intervals in T2/F2; appendix E/J.
**Avoid:** unpaired comparisons, treating correlated assertions as independent trials, or selecting thresholds on the held-out series.

### 2.7 Results

**Purpose:** answer RQ1–RQ4 directly, including adverse or null findings.

| Results subsection | Paragraph instructions | Evidence/display | Status |
|---|---|---|---|
| Main comparison | State coverage difference; support/disclosure changes; output amount; whether trade-off is useful | T2 with denominators and intervals | **missing experiment** |
| Cutoff behavior | Explain early/middle/late changes; point to all cutoff rows; distinguish sparse gold from real performance changes | F2; appendix E | **missing experiment** |
| Construction/artifact exposure | Separate byte differences, selection effects, and actual revelations; identify exposed surfaces | T4; appendix H witnesses | **missing experiment** |
| Ablations/stage losses | Attribute effects only to controlled changes; identify dominant omission/error stages | T3/F3; verifier confusion table | **missing experiment** |
| Efficiency | Separate build cost, update cost, page/cutoff reuse, and cold/warm cache behavior | T5; appendix J | **missing experiment** |
| Error analysis | Show overmerge, withheld true fact, unsupported assertion, source/citation error, semantic leak, and baseline wins | Source-backed case table | **requires revalidation** for historical cases |

For each result paragraph use: **observation → effect size/uncertainty → interpretation → alternative explanation/limitation**. Do not fill an interpretation before observing the result. No direct numerical comparison with unrelated scores from prior papers.

**Citations:** local table/figure references first; cite external work when interpreting a mechanism, not as a substitute for data.
**Avoid:** reporting only the final cutoff, hiding missing cells, or claiming victory when prefix long-context generation matches or exceeds the method.

### 2.8 Discussion

**Purpose:** explain what the results mean for building reference systems.
**Explain:** persistent evidence and reuse; the precision/coverage cost of verification; graph-to-publication errors; construction scope; where simpler approaches suffice. Separate experimentally supported causal explanations from hypotheses.
**Evidence:** RQ results **missing experiment**; each discussion claim must name its supporting comparison.
**Citations:** closest methods to explain trade-offs, not to inflate novelty.
**Display:** optional precision–coverage curve if thresholds were predefined on development data; otherwise refer to T2/T3.
**Avoid:** calling historical debugging a controlled ablation or using unmeasured reader utility to explain success.

### 2.9 Limitations, responsible research, and future work

#### Limitations

**Purpose:** state how the study can be misinterpreted.
**Explain:** five-volume cap; few independent works; English/public-domain selection; possible model familiarity; incomplete gold; sampling/annotation uncertainty; model/version dependence; implicit narrative inference; finite artifact threat model. Describe each limitation’s likely effect on conclusions, not just its existence.
**Evidence:** protocol and observed failure cases, available at submission.
**Citations:** [ARR author guidance](https://aclrollingreview.org/authors) and relevant contamination/annotation work.
**Display:** none required; uncertainty belongs in the results too.
**Avoid:** presenting incomplete core validation as a harmless future extension.

#### Responsible research and release

**Purpose:** document provenance, use conditions, and participation accurately.
**Explain:** source editions and redistribution basis; reference-site attribution; annotation conditions and compensation if humans participate; privacy of participant data if collected; marked spoiler-bearing examples; accurate AI-assistance disclosures as required. Open texts and reference-wiki contents have different provenance and licensing: do not infer one from the other.
**Evidence:** actual source and annotation records; do not assert a legal determination without checking the edition and release jurisdiction.
**Citations:** source records and the current [Responsible NLP checklist](https://aclrollingreview.org/responsibleNLPresearch/).
**Display:** release manifest in appendix J.
**Avoid:** invented ethics approval, undisclosed agent-only annotation, or redistributing commercial development material as paper data.

#### Future work

**Purpose:** connect follow-up studies to evidenced limitations.

| Direction | Triggering limitation | Study to propose | Status/priority |
|---|---|---|---|
| Identity-link timing | Surface appearance does not establish equivalence | Evidence-dated alias links plus prefix/full semantic tests | Core gap if safety claim depends on it; otherwise bounded **optional extension** |
| Coreference/narrator resolution | Evidence discovery loses unnamed or first-person mentions | Conditional recovery experiment after stage diagnostics | **optional extension** |
| Beliefs/deception/implicit relations | Attribution and modality errors | Source-grounded challenge set and explicit representation comparison | **optional extension**, with current errors disclosed |
| Chapter/scene cutoffs | Volume granularity hides within-volume revelations | Finer disclosure annotation and cutoff evaluation | **optional extension** |
| Longer series | Current evaluation stops at five volumes | Separately authorized longer-scope study | **optional extension**, no current run permission |
| Cross-language/genre transfer | Narrow corpus selection | Frozen transfer study with independent annotation | **optional extension** |
| Reader utility | Factual metrics do not establish usability | Reader task accuracy/time and unwanted disclosure study | **optional extension** |
| Character images | Text cannot validate portrait identity | Visual grounding and separate identification evaluation | **optional extension**; do not restore nearest-image guesses |

**Citations:** papers tied to the specific proposed technique after methods reading.
**Display:** usually no main-paper table; this planning table becomes a concise ranked paragraph.
**Avoid:** deferring strong baselines, all-assertion precision, or independent quality validation solely to future work.

### 2.10 Conclusion

**Purpose:** close with the actual contribution and its boundary.
**Write:** task → demonstrated method/evaluation contribution → main measured trade-off → scope limitation. Keep it short and consistent with the abstract.
**Evidence:** only finalized T2/T3/F2 results; **missing experiment** until then.
**Citations/display:** no new citations or results.
**Avoid:** new generalization claims, universal safety language, or promises of untested capabilities.

## 3. Metric definitions and evaluation safeguards

### 3.1 Primary estimands

For each work and cutoff, report counts before rates. “Supported” means fully supported at the required attribution/modality; partial is not fully supported. The primary output precision is support from eligible source context; citation sufficiency separately evaluates the evidence actually cited. Judges may need eligible surrounding context, but must not consult future text to approve a prefix assertion.

| Metric ID | Numerator / denominator | Unit, annotation, aggregation | Failure cases/status |
|---|---|---|---|
| M1 End-to-end gold recall | Eligible gold facts correctly conveyed in `W_t` / size of `G_t` | Source-grounded gold, semantic matching with validated assessment; per work/cutoff, then macro | Incomplete gold limits claim to inventory recall; **missing experiment** |
| M2 Graph recall | Eligible gold facts correctly represented in graph at `t` / size of `G_t` | Same gold and cutoff as M1 | Presence must preserve attribution/direction; M2–M1 is not automatically pure rendering loss without route matching; **missing experiment** |
| M3 Assertion precision | Fully source-supported sampled assertions / sampled assertions, design-weighted | All atomic outputs, including prose and uncited content; stratify by surface/type; report supported/partial/unsupported/uncertain | E03 sampling population is narrower; **requires revalidation** |
| M4 Future-fact exposure | Assessed future gold facts disclosed / assessed eligible `F_t` facts | Fact probe; human-calibrated semantic assessment | Selected future inventory, not all possible leaks; zero eligible items → undefined; **requires revalidation** |
| M5 Output disclosure | Confirmed future assertions / assessed output assertions | Distinct atomic output claims; separate from unsupported guesses | Unknown reveal position stays uncertain; **missing experiment** |
| M6 Page disclosure | Assessed pages with any confirmed disclosure / assessed pages | Includes automatically delivered shared surfaces attached to the page visit | Cluster dependence and empty/missing pages reported; **missing experiment** |
| M7 Citation coverage | Assertions carrying a citation / assessed assertions | All assertion types; citation presence only | No citations does not remove an assertion from M3; **missing experiment** |
| M8 Citation sufficiency | Assertions fully supported by their cited eligible evidence / all assessed assertions | Primary end-to-end sufficiency; also report conditional sufficiency among cited assertions | Missing citation is insufficient; jointly sufficient citations allowed; **missing experiment** |
| M9 Citation validity | Resolvable citation references / references checked; cutoff-eligible references / references checked | Reference-level, deterministic validity plus parsed provenance | Resolvable does not imply relevant or sufficient; **requires revalidation** |
| M10 Stage retention | Gold facts available at each stage / size of `G_t`; also conditional transitions | Match gold IDs to evidence/claim/graph/output route | Multiple extraction paths form a DAG; do not force exclusive paths; **missing experiment** |
| M11 Temporal error | Premature and delayed/omitted gold facts with eligible denominators | Compare observed first correct output cutoff to gold reveal cutoff | Never emitted is censored/omitted, not an invented late date; **missing experiment** |
| M12 Verifier errors | Unsupported admitted / labeled unsupported candidates; supported rejected / labeled supported candidates | Independent challenge set; type strata; partial/uncertain separate | Same model’s judgment is not independent gold; **missing experiment** |
| M13 Efficiency | Calls, tokens, money, elapsed time, cache hits, output quantity | Per stage, work, cutoff/update; cost per retained supported fact only with matched quality estimates | Distinguish first build, warm replay, and marginal update; **missing experiment** from frozen logs |

Secondary metrics: prefix-assessed importance-weighted gold recall; relation/event tuple precision/recall/F1 with attribution and direction preserved; dead links, missing pages, page balance and connectivity. These are **optional extensions** unless required for an explicit claim. Do not use fluent text, ROUGE, headings, or graph size as substitutes for factual quality.

### 3.2 Sampling, undefined values, and uncertainty

- Enumerate uncited/prose assertions before sampling; validate the atomizer independently on held-out page samples so omissions in the evaluator are visible. Atomize to name-only, third-person facts (NarrativeFactScore's decomposition prompt, R8) so pronouns and narrator "I" are resolved before judging; run it locally ($0).
- For unequal sampling probabilities, estimate totals/rates with declared design weights. Publish stratum counts and weights; do not average convenience strata as if they were representative.
- Empty output: assertion count zero, precision undefined, recall zero when gold exists. A missing expected character page counts against completeness/recall and is not silently skipped.
- No eligible gold: recall undefined. No future facts within scope at the last cutoff: M4 undefined, not zero. Other cutoff metrics remain defined when their own denominators exist. Future facts beyond the five-volume scope are not silently added to the protocol.
- Report uncertain annotations and bounds/sensitivity to their treatment. Do not improve estimates by dropping difficult cases after seeing outcomes.
- Report zero observed events as `0/n`. For independent Bernoulli trials, an exact one-sided 95% zero-event bound is `1 - 0.05^(1/n)`; `3/n` is a rough approximation. Do not apply claim-level bounds as if correlated claims/pages/cutoffs were independent. Report descriptive counts and a design-appropriate bound or explicitly state that the design cannot support a tight bound.
- Report model-family and prompt variation separately from annotation uncertainty. Do not invent an interval by treating cache hits as repeated samples.

### 3.3 Evaluator validation scenarios

Before the core study, verify the protocol with known examples: a supported uncited assertion; a true claim with a wrong citation; a future quote attached to an early fact; two early names linked only later; a hypothetical relation; a quoted lie; an embedded-story character mistaken for the subject; an incorrect relation direction; a missing page; empty output; no gold; no future probes; a future name in shared HTML; a semantic disclosure with no new vocabulary.

These are specifications for future evaluator validation; none has been run yet. Validate automated judges on positives and negatives, plus difficult types, and report balanced accuracy beside raw agreement: the classes are imbalanced. STORYSUMM (R7) measured MiniCheck-FT5, the local support screen, at 46–47% balanced accuracy on narrative summaries, and ledger §43/§47 record the same direction locally (hand-read control recall 5/8 where the tool found 2/8). So a screen-negative is not evidence of no leak: hand-check a random sample of screen-negatives, not only the flagged positives. Reviewing every flagged leak alone cannot estimate false negatives. Negatives for the verifier challenge set (M12, 0012 D11) can be made by minimal word-swap perturbation of source-verified gold facts (R8's perturbation prompt), generated with a local model and each one hand-confirmed false. Freeze any calibration threshold on development data.

## 4. Controlled experiment specifications

### 4.1 Baseline matrix

| ID | System/condition | Access and comparison purpose | Status |
|---|---|---|---|
| B1 | Prefix long-context generation | Source prefix only; same task/output contract; tests whether direct prompting suffices | **missing experiment** |
| B2 | Prefix hybrid BM25+dense retrieval | Prefix-only index; development-tuned fusion/chunking; same generator and output contract | **missing experiment** |
| B3 | Prefix-built LightRAG adaptation | External graph method built only from prefix; document release/commit and adaptation to character pages | **missing experiment** |
| B4 | Full-built graph with retrieval-time filtering | Full input limited to `N <= 5`; filters at retrieval; diagnostic of construction dependence, not a prefix-only competitor | **missing experiment** |
| B5 | NarrativeWiki, frozen implemented pipeline | Report actual construction access and every cutoff protection; do not assume prefix purity | **missing experiment** |
| X1 | Closed-book generation | Same character task without novel context; diagnose prior knowledge/output tendencies | Historical controls **require revalidation** |
| X2 | Full-text prompt-only generation | Explicitly future-informed diagnostic; keep outside fair prefix-only ranking | **missing experiment** |

**This matrix supersedes plan 0012 D13's B1–B6 numbering.** Mapping (0012 → here): B1 full-text prompt → X2; B2 prefix long-context → B1; B3 prefix BM25+dense → B2; B4 full-corpus graph + filter → B4; B5 ours → B5; B6 ours + one recovery intervention → dropped as a baseline (a recovery intervention is an ablation-style change, added to §4.2 only if implemented). B3 (LightRAG) is new here.

Separate an external-method comparison (B3) from a controlled access-policy intervention (A1 below). Pin releases and tune comparable baseline settings on development data. Keep a settings-selection record and cost estimate before any billed run. If a baseline cannot be executed, mark it absent and narrow the comparative claim; do not relabel a weaker custom method.

### 4.2 Ablations

All final ablation effects are **missing experiment**; historical E05 results are motivation only.

| ID | Intervention and control | Hold fixed / recompute | Question and required outputs |
|---|---|---|---|
| A1 | Same pipeline prefix-built vs full-built, rendered at same `t` | Same model/prompts/source edition; rebuild construction and descendants in isolated artifacts | Semantic differences, alias linkage, selected evidence, page recall/precision/disclosure; classify each relevant difference |
| A2 | Remove factual verifier, retain basic parse/provenance/schema gates | Same extracted candidates; rebuild admission/graph/publication as required | What correct facts are rescued and false facts admitted? M1/M3/M5/M12 plus output quantity |
| A3 | Remove scene extraction contribution | Preserve source/model/other passes; recompute scene-dependent epithets, merges, claims and descendants | Discovery value and downstream changes; do not retain scene-derived aliases accidentally |
| A4 | Remove infobox/backstory passes | Same window/scene artifacts; rebuild descendants; compare each removal separately if affordable | Attribute/backstory contribution and cost, with precision/coverage |
| A5 | Graph-off, same available evidence | Replace graph organization/retrieval with a declared flat evidence store; keep generator, cutoff and budgets | Value of graph organization; log unavoidable selection differences and do not call this an extraction comparison |
| A6 | Prose-only vs structured-plus-prose publication | Same admitted evidence and generator; declare/match output budgets | Rendering retention, support, output length; natural-length secondary comparison |
| A7 | Remove artifact protections in an isolated diagnostic copy | Same content artifacts; never overwrite or publish the ordinary site | Which disclosures originate in metadata/nav/search/links? M6 and surface witnesses |

Reuse upstream artifacts when the intervention permits. Rebuild affected descendants for upstream changes. Do not reuse a gazetteer from a removed extraction component. Pair generations where technically valid and report unavoidable stochastic variation.

Choose settings on development works and freeze before test. Preserve baseline originals and audit provenance. For a resource-limited study prioritize A1, A2, and A6 because they directly support construction, verification, and reference-artifact claims; remaining mechanisms receive weaker causal claims if omitted. Do not select ablations based on favorable final effects.

### 4.3 Contamination diagnostics

**Status:** historical observations **require revalidation**; expanded study is an **optional extension**.

Compare original, name-remapped, and name-remapped-plus-paraphrased inputs on aligned items. Measure recognition separately from future fact transfer and instruction compliance. Validate preservation of facts, attribution, reveal order, and cross-volume coreference; a damaged story is not a successful decontamination treatment. Do not use MiniCheck alone as proof of paraphrase fidelity.

Use identical item intersections, mapped identities, source positions, cutoffs, and model settings. Include closed-book and eligible-prefix controls. Counterfactual variants require independent validation and remain optional. Call these contamination-reduction treatments; residual recognition and memorization are not ruled out. Avoid identifying the cause of a boundary violation without a suitable control.

## 5. Tables and figures: layouts and caption requirements

### 5.1 Main-paper display specifications

| Display | Layout/data contract | Caption must explain | Status |
|---|---|---|---|
| F1 Task and architecture | Left: cutoff/source example; center: six stages and evidence links; right: page plus shared delivery surfaces. Mark model vs deterministic stages and build vs render scope | Example provenance or explicitly synthetic status; reading-order cutoff; no implication of a semantic guarantee | Architecture **available evidence**; final public-domain example **requires revalidation** |
| F2 Cutoff curves | Separate panels for gold recall, assertion precision, and disclosure; x = cutoff; consistent method colors; per-work facets; uncertainty; separate output-amount panel/table | Denominators, undefined last-cutoff future probes, interval unit, evaluated scope; no connection across missing cells | **missing experiment** |
| F3 Stage retention | Aligned bars for discovery/extraction/admission/graph/rendering by work or fact type; common eligible-gold denominator | Multiple paths and non-monotone corrections; stage matching procedure | **missing experiment** |
| T1 Corpus/annotation | Work; split; edition; evaluated volumes; boundaries; source length; eligible cast; gold increments/cumulative count per `t`; output sample count; human overlap | All inventory counts refer to evaluated scope; main vs full cast; reference sources; candidate held-out verification | **missing experiment** for frozen scope |
| T2 Main comparison | Work/cutoff/system; recall; precision; future-probe exposure; page disclosure; assertion/page counts; citation sufficiency; cost or T5 pointer | Raw denominators and intervals, missing cells, matched access/budget, no unfair full-text control ranking | **missing experiment** |
| T3 Ablations | Intervention; paired recall/precision/disclosure difference; retained supported/unsupported counts; output amount; cost | Upstream artifacts held fixed, recomputed dependencies, sampling/variation; trade-offs | **missing experiment** |

Keep T2 legible: use separate coverage/grounding and disclosure panels if necessary. Main text may highlight selected cutoff rows, but every cutoff must appear in F2 and/or appendix E, with aggregates only alongside the underlying granularity.

### 5.2 Supporting displays

- **T0 prior-work matrix:** §2.3 columns; compact main-text version, full evidence/source notes in appendix. **available evidence** only for verified cells.
- **T4 construction/artifact exposure:** work/cutoff/surface; tested pages/items; differences; confirmed disclosures; false positives; source-backed witness. **missing experiment**.
- **T5 efficiency:** stage/build/update; calls/tokens/cost/wall time; warm/cold cache; eligible pages and retained facts; hardware and model revision notes. **missing experiment** for frozen run.
- **Error table:** error type, cutoff, emitted assertion, eligible evidence, adjudication, affected stage; include system and baseline errors. **requires revalidation**.
- **Precision–coverage curve:** optional if development-defined thresholds create meaningful operating points. Show disclosure beside each point. **optional extension**.
- **Contamination plot:** paired recognition and transfer rates with fidelity results and denominators. **optional extension**.

Use standard plotting tools to produce exportable vector figures or publication-resolution raster assets when experiments exist. No invented bars, ornamental graph hairballs, or screenshot-only proof. Prefer aligned bars over a Sankey if fact flows cannot be uniquely traced. Use readable labels, accessible colors, and caption explanations sufficient to interpret each panel without hunting for the denominator.

## 6. Literature and citation placement

### 6.1 Reading and provenance rules

A citation counts as record-verified only when it appears in the machine-verified [REFERENCES](../../papers/REFERENCES.md) (written by `scripts/papers/fetch_reference_pdfs.py`, never by hand); reading depth is documented in [PAPERS](../../papers/PAPERS.md) and [review 0007](../../papers/reviews/0007-structured-wiki-quality.md). As of 2026-09-27, R1, R3, and R7–R10 have no REFERENCES row (R4–R6 are there under their arXiv preprints). R7 and R8 have since been read in full from local PDFs (PAPERS §H). R9–R10 are in neither inventory, and plan 0012 D17 records their IDs as unverified because the fetch script's arXiv requests fail (HTTP 406). Treat those two links as discovery pointers until the script confirms them. A landing-page/abstract check is not a full-paper read. Do not silently upgrade inherited reading status.

For every load-bearing citation record: exact title/authors, venue/year, version or DOI, primary link, sections read, claim supported, local adaptation, and implementation status. Prefer proceedings records when appropriate. Pin arXiv versions before making method-level comparisons; a mutable abstract URL is a discovery pointer, not a version freeze.

### 6.2 Citation map

| Key / primary record | Version/reading depth available | Put it here; specific role | Local implementation boundary |
|---|---|---|---|
| R1 [CHIRON](https://aclanthology.org/2024.findings-emnlp.499/) | Findings EMNLP 2024; selected methods/evaluation/limitations sections documented in review 0007 and PAPERS; no REFERENCES row | Introduction/related work; verified character sheets and generation/validation | Conceptual reference; not a CHIRON replication or trained model |
| R2 [Living the Novel](https://arxiv.org/abs/2512.07474) | Planning consulted [v1 HTML](https://arxiv.org/html/2512.07474v1); repository records a full reading | Introduction/temporal systems; prior temporal gating | Reference, not an implemented reproduction; compare disclosure order carefully |
| R3 [TimeChara](https://aclanthology.org/2024.findings-acl.197/) | Findings ACL 2024; PDF in PAPERS; no REFERENCES row | Task/related work; point-in-time character hallucination | Role-playing task differs from reader reference generation |
| R4 [STORM](https://aclanthology.org/2024.naacl-long.347/) | NAACL 2024; primary record/abstract checked | Related work and any adopted outline metric | Repository implements related heading metric family; not the STORM generation pipeline |
| R5 [ALCE](https://aclanthology.org/2023.emnlp-main.398/) | EMNLP 2023; primary record/abstract checked | Attribution/citation evaluation definitions | Metric adaptation; describe departures rather than claiming official ALCE evaluation |
| R6 [MiniCheck](https://aclanthology.org/2024.emnlp-main.499/) | EMNLP 2024; record checked and selected sections in review 0007 | Method support checking and evaluator limitations | Applied local component; domain-specific accuracy must still be measured |
| R7 [STORYSUMM](https://aclanthology.org/2024.emnlp-main.557/) | EMNLP 2024; arXiv 2407.06501v3 read in full (PAPERS §H); no REFERENCES row | Related work; §2.6.2 annotation design (protocol union, easy/hard); §3.3 judge validation (balanced accuracy; MiniCheck-FT5 at 46–47% on narrative) | Reference; Reddit stories are not a usable corpus (not public domain, no cutoffs) |
| R8 [Agent-as-Judge for Factual Summarization of Long Narratives](https://aclanthology.org/2025.emnlp-main.1204/) | arXiv 2501.09993v3 read in full (PAPERS §H); EMNLP 2025 per the link, not yet in REFERENCES; NarrativeFactScore | Related work: closest use of a character graph, but as an evaluator; §3.2 atomizer; §3.3 perturbation negatives | Candidate evaluator, not implemented; human correlation is moderate (Spearman 0.43/0.47), so it cannot replace human labels; it has no reader cutoff |
| R9 [NS-ST-GraphRAG](https://arxiv.org/abs/2609.05139) | arXiv 2609.05139v1 record verified 2026-09-28 (REFERENCES, PDF local); not yet read | Recent literary graph positioning | Do not assert detailed differences from abstract alone |
| R10 [SearchWiki](https://arxiv.org/abs/2608.29953) | arXiv 2608.29953v1 record verified 2026-09-28 (REFERENCES, PDF local); not yet read | Corpus-to-wiki positioning; active information seeking | Not a local navigation-agent component |
| R11 [GraphRAG](https://arxiv.org/abs/2404.16130) | Repository metadata verified; pin version and read baseline-relevant sections | Graph retrieval related work; any discussed gleaning adaptation | No completed matched comparison established; local gleaning failure is not failure of GraphRAG as a whole |
| R12 [LightRAG](https://arxiv.org/abs/2410.05779) | Repository metadata verified; baseline implementation reading pending | B3 and graph retrieval context | Planned adapted baseline; not yet a measured result |
| R13 [AIS](https://arxiv.org/abs/2112.12870) | Repository metadata verified; methods reading to be recorded | Task/annotation: attributable-to-sources distinction | Conceptual framework; no dedicated AIS scorer claimed |
| R14 [M3-Embedding](https://arxiv.org/abs/2402.03216) | Repository metadata verified; component use recorded | Method canonicalization | BGE-M3 used for value clustering; do not describe it as current retrieval without a new implementation |
| R15 [EvolvTrip](https://arxiv.org/abs/2506.13641) | Repository selected-section review 0007; pin version for final citation | Narrative/temporal graph positioning | Reference/adaptation, not reproduced performance |
| R16 [A Survey on Data Contamination for Large Language Models](https://arxiv.org/abs/2502.14425) | Repository metadata verified; targeted reading pending | Contamination terminology and limitations | Survey framing, not evidence that local data are uncontaminated |
| R17 [The Emperor's New Clothes in Benchmarking?](https://arxiv.org/abs/2503.16402) | Repository metadata verified; targeted reading pending | Treatment fidelity and contamination-reduction caveats | Discuss a validated local adaptation separately from the paper’s findings |

“Unverified” above means no machine-verified record yet; any other status means the stated record or existing reading evidence, not verification of every claim in a paper. For recent work, follow the venue’s policy on contemporaneous submissions; do not misrepresent an unrun recent method as a completed baseline. Exclude irrelevant collected papers rather than padding the bibliography.

### 6.3 Prior-work writing checklist

- Cite borrowed mechanisms and definitions at their point of use, even if already cited in related work.
- Label “implemented,” “adapted,” “inspired by,” and “comparison only” accurately.
- Read methods and evaluation before claiming a paper lacks a capability or uses a weaker protocol.
- Never paste another paper’s score into T2 as a comparable result on this task.
- Ensure bibliography entries match the exact cited versions; the generated reference inventory is not hand-edited by this task.

## 7. Appendix assembly plan

| Appendix | What the author must supply | Why a reviewer needs it | Evidence status |
|---|---|---|---|
| A Task/annotation manual | Label definitions, atomicity, reveal-time procedure, difficult examples, attribution/modality rules, adjudication | Reproduce the meaning of a correct/supporting/safe assertion | **missing experiment** for validated manual/labels |
| B Corpus documentation | Editions, URLs, five-volume scope, split history, boundary rules, exclusions, cast policy, reference sources | Check selection bias and held-out status | Existing configs **available evidence**; frozen inventory **requires revalidation** |
| C Implementation | Ontology, representative schemas, interval semantics, aliases, all prompts/configuration, algorithm details | Reconstruct the method and separate deterministic/model stages | **available evidence**, freeze pending |
| D Baselines/prior comparison | External versions, adaptations, retrieval/fusion, context handling, output contract, budgets, T0 evidence | Assess baseline strength and fair comparison | **missing experiment** |
| E Complete results | Every work/cutoff/system, raw denominators, intervals, independent repetitions, failed/missing conditions | Detect selective reporting and dependence | **missing experiment** |
| F Evaluator validation | Atomizer checks, judge positive/negative confusion matrices, agreement, sampling probabilities, uncertain-label sensitivity | Assess measurement validity | **missing experiment** |
| G Ablations/sensitivity | Complete interventions, recomputation policy, thresholds, length/budget controls, negative outcomes | Assess causal attribution and robustness | **missing experiment** |
| H Leakage casebook | Semantic and surface witnesses with source IDs; content/identity/nav/search/metadata/citation/source-view cases | Show concrete successes and failures rather than only string counts | Historical examples **require revalidation** |
| I Contamination diagnostics | Paired item mappings, remap/paraphrase fidelity, recognition vs transfer, controls, residual uncertainty | Interpret claims about parametric knowledge | **optional extension** |
| J Reproducibility/release | Freeze hash, environment, model versions, configuration/prompt hashes, exact commands, sampling seeds, run/ledger pointers, artifact manifest | Reproduce the tables and understand costs/fallbacks | Infrastructure **available evidence**; frozen package **missing experiment** |
| K Reader study | Actual recruitment, consent/ethics process if applicable, tasks, assignment, measures, outcomes, limitations | Support reader utility claims | **optional extension**; omit if unperformed |

Do not move the task definition, closest-work positioning, primary baseline rationale, or main conclusions into the appendix to hide essential material. Mark spoiler examples clearly in the released package. Release gold/labels under their actual permissions; do not assume reference-site prose is public domain because the novel is.

## 8. Evidence roadmap, reviewer objections, and submission decisions

### 8.1 Ordered work packages

These are future research tasks, not actions performed when saving this file. Update plan 0012 as work actually proceeds; record every measured result in the ledger before quoting it here or in the manuscript.

| Priority | Work package and dependency | Completion/stop criterion | Status |
|---|---|---|---|
| P0a | Fix the measurement basis: output inventory, uncited/prose assertions, semantic leak labels, positive/negative evaluator validation | Known counterexamples in §3.3 behave correctly; measurement scope matches claim | **missing experiment** |
| P0b | Freeze five-volume corpus/cast/split and independent annotation protocol | Oz tuning history checked; no unreported full-scope dependencies; human plan or pilot designation explicit | **missing experiment** |
| P0c | Resolve or explicitly bound alias-link timing and shared-surface risks | No safety claim depends on an untested channel; retained defects disclosed | **missing experiment** |
| P1a | Implement/tune B1–B5 on development data, estimate costs, then freeze | Baseline adaptations and budget/context policies recorded before test | **missing experiment** |
| P1b | Run per-cutoff public-domain comparisons and construction/artifact tests | T2/F2/T4 complete with denominators and failures; held-out outputs not used to tune | **missing experiment** |
| P2a | Run controlled ablations and stage tracing | T3/F3 explain effects without confounded historical comparisons | **missing experiment** |
| P2b | Validate verifier mistakes and extract efficiency accounting | M12/T5 trace to frozen artifacts; rejection rates not mislabeled as output error | **missing experiment** |
| P3a | Second generator family and untouched work | Predeclared transfer protocol; claim limited to actual tested population | **optional extension** |
| P3b | Contamination-treatment and/or reader study | Fidelity or utility independently validated before associated claim | **optional extension** |

Use deterministic analysis, cached artifacts, and stored-prompt replays before billed experiments. Prompt/config changes start on the smallest development slice. Before any future paid step, state why no cheaper path answers its question and provide an estimate; route all calls through the existing client and preserve caches. This plan does not approve a spending amount: each billed package must fit inside the remaining lifetime budget under the $200 hard cap (§0.1), and a package whose estimate does not fit is narrowed or moved to the pilot path (§8.4), never run past the cap.

**Existing evaluation entrypoints for a later authorized run** (these write report/run artifacts):

```powershell
# Explicitly bounded, illustrative development corpus; see metric limitations E03/E04.
.venv/Scripts/python.exe scripts/eval/artifact_exposure.py middlemarch --upto 5
.venv/Scripts/python.exe scripts/eval/assertion_precision.py middlemarch --upto 1 --n 40 --seed 0
.venv/Scripts/python.exe scripts/eval/pipeline_page_leak.py middlemarch --upto 1
```

The assertion sample size above is an existing tool invocation example, not the final precision target. Its local pre-screen is not a human verdict. These tools may write reports/run records; the artifact probe also needs suitable existing builds. Run each intended cutoff explicitly after freezing the protocol. No baseline/ablation CLI is invented here: appendix J must acquire exact commands from their eventual implementations. Never run a command with an implicit default series, default Oz cutoff, or unbounded volume range.

### 8.2 Claim–evidence–reviewer-objection matrix

| Proposed claim | Likely reviewer objection | Evidence required / display | Allowed wording if incomplete |
|---|---|---|---|
| The method is useful at a reader cutoff | Empty pages can avoid leaks | M1/M3/M4–M6 plus output amount; T2/F2 | Implemented system; usefulness unestablished |
| The graph adds value | A simple prefix prompt may suffice | B1/B2/B3 plus A5; matched budgets; T2/T3 | Graph is a design choice, not demonstrated improvement |
| Cutoff filtering prevents disclosure | Future entity merges or shared HTML still leak | A1/A7, semantic identity cases, T4, appendix H | Filtering invariant with residual semantic/artifact risks |
| Factual precision is high | Only easy cited lines or selected negatives were judged | Whole-output sampling, independent labels, weighted M3, appendix F | Narrow sampled estimate or agent-reviewed pilot |
| Verification improves quality | It may simply delete useful claims | A2, supported/unsupported retention, M1/M12, T3 | Observed admission policy; causal benefit not established |
| The method generalizes | All corpora informed development; volumes are correlated | Freeze history, Oz held-out evaluation, optional additional work | Results on named tested series only |
| Zero leaks were found | Sparse future gold and false-negative judges | `0/n`, design-appropriate bounds, negative validation, M4–M6 | No events observed under the stated finite protocol |
| Memory contamination is controlled | Renaming may preserve recognition or damage meaning | Paired recognition/transfer controls and fidelity, appendix I | Contamination-reduction treatment, residual risk remains |
| It is cheaper | Cached repeated pages hide initial cost | T5 cold/warm/build/update accounting at comparable quality | Efficiency description without superiority claim |
| It helps readers | Factual metrics do not measure task utility | Independent reader study, appendix K | Intended use case, not demonstrated reader benefit |
| The paper is novel | Gating, character sheets, and wiki generation already exist | T0 methods-level comparison and specific new evaluation/result | Narrow integrated system/empirical contribution |

### 8.3 Outcome-dependent submission rules

- If prefix long-context generation matches or exceeds NarrativeWiki, report that outcome. A paper may still contribute validated provenance/reuse/diagnostic findings, but must not claim quality superiority without evidence.
- If verification improves precision by suppressing information, report the supported facts lost and coverage change alongside precision.
- If no leaks occur, report the finite tested population, detection validation, and uncertainty. Do not translate the result into a universal safety claim.
- If future construction changes earlier pages, adjudicate semantic effects before claiming cutoff adherence. Do not hide the difference as an implementation detail.
- If a held-out work motivates a rule change, preserve its original result and relabel the revised evaluation as development evidence. Find new untouched data before renewing a held-out claim.
- If the independent annotation or strong baseline requirements remain unmet, use the pilot path rather than implying equivalent evidence.
- If a result cannot be traced to an artifact, revision/configuration, command, run, and ledger entry, leave its manuscript placeholder unfilled.

### 8.4 Resource-constrained pilot path

Keep the same task and writing structure but present an **exploratory system and evaluation pilot**. Identify agent-reviewed and automated labels honestly, restrict statements to the observed samples, and provide reproducible witnesses/protocols where possible. Do not claim human-validated quality, broad generalization, superiority, or comprehensive spoiler prevention.

Prioritize a strong prefix long-context comparator, transparent artifact audits, and source-linked error cases over a large number of poorly validated scores. This is a narrower contribution with weaker evidence, not a shortcut to the same top-tier empirical claim. Venue suitability must be judged from the completed study, not promised here.

### 8.5 Writing and release readiness checklist

- [ ] Title/abstract claims map to completed T2/T3/F2 outcomes and the actual held-out scope.
- [ ] Each paper subsection has purpose, explanation, evidence, citations, display, and claim boundaries.
- [ ] All missing experiments remain marked; planned behavior is not described as implemented.
- [ ] Per-work/per-cutoff counts, undefined values, failures, and intervals accompany aggregate rates.
- [ ] All output types, including prose and uncited assertions, are represented in precision assessment.
- [ ] Independent human participation and agreement are documented, or the paper is explicitly a pilot.
- [ ] Baselines are fairly adapted and strong; diagnostic full-text controls are separated.
- [ ] Alias identity links and all automatically delivered artifact surfaces are evaluated or bounded as limitations.
- [ ] Historical larger-scope and commercial-development results are excluded from the public five-volume result tables.
- [ ] Every number traces to a ledger entry and a frozen artifact/run/configuration.
- [ ] Citation metadata, reading depth, primary links, and implemented/adapted/reference status are checked.
- [ ] Supplement contains prompts, commands, gold/annotation rules, full results, failures, and versioned artifacts as permitted.
- [ ] Target-venue page/template/anonymity/checklist/AI-disclosure requirements are checked at submission time.

### 8.6 Outstanding research decisions

Final venue/deadline; second untouched work if pursued; independent annotator availability; pilot-derived sample sizes; frozen external baseline versions/settings; second generator if pursued; cost-approved experiment schedule. Record these before the experiments they govern. The five-volume cap, the $200 spending cap, the public-domain publication rule, the primary framing, and the pilot fallback are already decided.
