# Independent methodology review — 2026-10-09

This review was made independently of `REVIEW_2026-10-08`, from the supplied 47-page `NarrativeWiki-paper.pdf`, the current TeX sources, and limited deterministic inspection of the statistics scripts and stored annotation/run artifacts. PDF pages below are physical pages of that supplied PDF. No model calls, tests, manuscript changes or fresh benchmark runs were made. Values quoted below already appear in the paper/results registry or measurement ledger.

## Assessment

For a regular COLING/NAACL research-paper submission, I would currently recommend **weak reject**. This is a judgement of the present evidence, not a numerical prediction of acceptance. The reader-relative task is useful, the whole-artifact threat model is stronger than page-only evaluation, and the unfavourable results and failures are unusually candid. A negative-results or evaluation paper can be publishable. Here, however, the central disclosure finding is based on a weakly sensitive search and unvalidated LLM verdicts; the quality comparisons are confounded by annotator and output population; and everything comes from one development series and one generation. A long appendix does not replace independent validation.

The convincing contribution is potentially **an evaluation protocol and a taxonomy of cutoff failures**, with a case-study implementation. The present results do not establish an improved wiki-generation method: prefix retrieval has higher selected-gold recall, higher measured precision, higher citation sufficiency and much smaller token use. Nor do they establish spoiler safety. The paper often says this correctly; its framing and a few summaries should be made equally precise.

## Confirmed reporting or analysis problems

### M01 — Critical: the accepted human review found disagreements that remain in the reported quality metrics

**Locations:** `appendix/a-annotation.tex:162–182`, PDF pp.14–15; `sections/05-setup.tex:87–102`, p.6; `sections/limitations.tex:21–31`, p.9. Supporting local record: `docs/eval/human_check/HUMAN_REVIEW.md`.

The accepted answers match only **120 of 148** earlier precision labels and **46 of 60** citation labels. The appendix explicitly says that precision and citation labels were not changed on the sampled items because doing so would correct only a tenth of the population. The local review record reports precision differences mostly in the stricter direction, including 17 `partly` answers against earlier `supported` labels. Thus the human review is not just a limited, nonblind validation: it discovered material inconsistencies with the very labels still used for M3 and M8. Saying values are “after the review” or advertising a human-reviewed sample can make readers infer more validation than actually occurred.

**Fix:** propagate the accepted decision rules through every affected quality-label population before claiming validated quality metrics; then recompute the tables. Alternatively, clearly separate the unchanged LLM estimates from audited-sample results and report the disagreement and its direction prominently. Correcting only sampled rows is insufficient, but leaving the findings without either a full correction or a separate analysis is also insufficient. This is a validation problem, not proof that any particular headline number is wrong by a known amount.

### M02 — High: the paired-difference estimand is described as shared output pages but computed on assessment rows

**Locations:** `sections/05-setup.tex:106–107`, PDF p.6; `appendix/a-annotation.tex:48–51`, p.12; `tables/t-paired.tex:22–25`, p.21. Code: `scripts/papers/summary_stats.py:63–70`; `scripts/eval/paper_numbers.py:116–128`; absence convention: `appendix/b-corpus.tex:20–22`.

The paper defines the matched set as the “page entities both have at t.” `summary_stats.py` instead subtracts the complete per-cutoff metric keys, without examining page entities. `paper_numbers.py` intersects **annotated character/cutoff rows**, which exist even for missing output pages, because the paper explicitly retains missing characters in denominators. These are different estimands. The printed differences can be valid differences on a common assessment inventory, but they are not demonstrated differences restricted to shared output pages.

**Fix:** define the pairing as common assessed character/cutoff rows (and the same eligible/future gold inventory), with absent pages retained as failures; update the equation and caption consistently. If the intended claim is a matched-output-page comparison, recompute it explicitly and label it as a different analysis. Do not drop missing pages from the principal end-to-end recall measure just to make the current caption true.

### M03 — High: an “exact” zero-event confidence bound is claimed without defensible independent units

**Locations:** `appendix/a-annotation.tex:184–187`, PDF p.15; `sections/06-results.tex:35–37`, p.6. Code: `scripts/eval/paper_numbers.py:75–77,93–96`.

The formula `1 - 0.05^(1/k)` is an exact binomial zero-success bound only under an independent Bernoulli model. Replacing fact count by the count of selected characters does not establish independence: spouses share the same marriage, characters share scenes and relation pages, all outcomes come from one generator and one series, and the selected gold characters are not a random sample from a defined population. The event being bounded must also be defined—any detected disclosure for a character is not the same outcome as the fact-level disclosure rate. Search sensitivity is imperfect and varies by wording/page, so this is not an upper bound on true spoilers either.

**Fix:** remove the unconditional “exact” inferential claim; report descriptive zeros and denominators. If retaining a model-based bound, explicitly define a character-level event, state the independent-unit and detection assumptions, and present it only as conditional sensitivity analysis, not a calibrated safety bound.

### M04 — High: closed-book subtraction is not a reading contribution or a memory floor

**Locations:** `sections/06-results.tex:49–63`, PDF p.7; `appendix/a-annotation.tex:51–52`, p.12; `tables/t-paired.tex:25`, p.21; `sections/limitations.tex:52–55`, p.9.

`recall(system) - recall(X1)` is called the margin gained “by reading” over memory, and all recall comparisons are said to live above a memory “floor.” The two systems can convey different sets of facts, and X1's correct output neither proves a reading system used memory nor bounds how much it gained from evidence. A text-reading system can score lower than X1. The paper itself later admits that remembered facts can also have been read, which is correct but conflicts with the stronger wording.

**Fix:** call this a descriptive **difference from the closed-book diagnostic**. Analyse per-fact overlap/discordance if helpful, but do not treat subtraction as identified memory attribution. The treatment establishes strong recognition-linked closed-book ability; it does not identify the memory share of each reading system.

### M05 — Medium: gold evidence pointers do not satisfy the stated sufficient-evidence definition

**Locations:** `sections/03-task.tex:15–17`, PDF p.3; `sections/05-setup.tex:12–20`, p.5; `appendix/a-annotation.tex:82–86,164–170`, pp.13–15.

The setup says each gold fact names the paragraph whose text first establishes it, but the accepted check finds **85 full, 23 partial, and 3 not established by the recorded paragraph alone**. The main text mentions 85 and 23 while omitting the three failures. The appendix says the fact holds in the assigned volume, including twelve planned/announced events completed later in that same volume, but that does not repair the claimed gold evidence record. This does not prove the volume labels are wrong; it does prove the pointer-level description is wrong and weakens gold grounding and fidelity checks.

**Fix:** repair evidence IDs or permit explicit multi-paragraph support sets, prove sufficiency for every gold proposition, and independently recheck earliest sufficient reveal volume. Report all three categories until repaired.

### M06 — Medium: universal name-replacement claims exceed the actual treatment

**Locations:** `sections/06b-decon.tex:7–9`, PDF p.8; `appendix/i-contamination.tex:21–31,64–80`, pp.28–29; `sections/limitations.tex:61–65`, p.9. Local evidence: `config/series.anne-decon.yaml:107` maps “Mary Vance” to “Mary Stubbs”; `docs/MEASUREMENTS.md`, 2026-10-05 upstream audit, explicitly records unmapped minor names such as Mary, Aunt Martha and Mary Joe, in addition to bare West.

The paper says **every character, family and place name** is replaced. The map is selective and even retains some first-name surfaces in replacement full names. The residual-name discussion focuses on inflected/derived forms in 26 paragraphs, but does not disclose the by-design unmapped minor-name coverage recorded in the ledger. The effect of the treatment can remain useful, but its advertised scope is inaccurate.

**Fix:** describe replacement of a reviewed set of mapped names, publish coverage and ambiguous-name handling, distinguish retained source names from morphological leftovers and restored names, and avoid universal wording. Do not silently fix the treatment now and retain results from the earlier text.

### M07 — Low, definite: the conclusion incorrectly says treated recall is zero

**Locations:** `sections/08-conclusion.tex:9`, PDF p.8; contrast `sections/06b-decon.tex:13–15`, p.8, and `appendix/i-contamination.tex:118–121`, p.31. Registry: `results.tex:926` = **0.003**; `results.tex:1070` = **1 of 335**.

The conclusion says closed-book recall “fell to zero,” although the body and supplied-PDF abstract correctly report 0.003. The appendix explains the residual as a death shared accidentally by an invented story.

**Fix:** “fell to near zero (0.003; 1 of 335 assessments).” This is not a rounding dispute: the conclusion asserts zero events while the recorded count is nonzero.

### M08 — Medium: enumeration/search is at times described as exhaustive reading

**Locations:** `sections/01-introduction.tex:66–70`, PDF p.2; `sections/06-results.tex:29–34`, p.6; methodological clarification `sections/05-setup.tex:67–69`, p.5, and `appendix/a-annotation.tex:104–110`, p.14.

The contribution says every later fact “is read against every page,” and the result says the search “reads” 9,695 assertions at cutoff 2. In fact lexical searches scan outputs and the annotator reads **only candidate sentences**. A sentence that fails retrieval is labelled absent without being read. The detailed methods disclose this, but the contribution summary can create a stronger impression of exhaustiveness.

**Fix:** consistently say “searched across every page; retrieved candidates were read.” Separate inventory size, search-scanned size, and annotator-read candidate counts.

### M09 — Low: the gold-fact unit is not consistently atomic

**Locations:** `sections/03-task.tex:15`, PDF p.3; `appendix/a-annotation.tex:88–96`, p.13; human-check rules in `docs/eval/human_check/INSTRUCTIONS.md`.

Gold facts are defined as atomic but recall explicitly scores conjunctions (e.g. newspaper man **and** grandson of the schoolmaster) as one unit and requires both. Such units receive the same weight as single propositions. The inventory can use compound nuggets, but it should not simultaneously be described as atomic.

**Fix:** either split compound gold facts before freezing a revised benchmark, or define gold nuggets/core propositions explicitly and acknowledge their unequal granularity. Preserve old results if changing units invalidates them.

## Major reviewer concerns supported by the paper, rather than undisclosed errors

### M10 — Critical: disclosure search sensitivity is insufficient for the central safety comparison

**Locations:** `appendix/g-additional-results.tex:30–72`, PDF pp.18,21 (Table 10); `sections/limitations.tex:33–39`, p.9; main finding `sections/06-results.tex:10–21`, p.6.

The search retrieves **0.845** of named paraphrases and **0.714** of named implications, but only **0.309** and **0.355** when a pronoun occurs on another character's page. This latter case is especially relevant to relationship pages, codex pages and timelines, which NarrativeWiki uniquely publishes in volume. The main abstract/limitations foreground the named cases. Seeds were written and checked by the same LLM annotator, without independent validation. No human checks disclosure verdicts. Thus observed zeros and one observed implication are detection counts, not a reliable estimate of actual spoiler prevalence, and detector sensitivity is not established as equal across output types.

**Required work:** independently validate a diverse disclosure challenge set, including pronouns, aliases, cross-page attribution, predictions, beliefs, titles and inferred identity; read a blinded sample of pages not retrieved by the search to estimate missed disclosures; measure detector sensitivity by surface and system. Human review of positive and negative disclosure outcomes is more urgent than adding another easy seed category. Present 0.309/0.355 prominently until repaired. Do not mechanically divide observed zeros by a single sensitivity rate.

### M11 — Critical: annotator identity is confounded with system and condition

**Locations:** `sections/05-setup.tex:74–86`, PDF p.6; `sections/limitations.tex:10–31`, p.9; `appendix/i-contamination.tex:112–118`, p.31; `appendix/a-annotation.tex:129–137`, p.14.

On the original text, one agent labels comparison-system precision/citations and another labels NarrativeWiki. The first agent also helped build the system and supplies pair verdicts. On treated text it labels everything. Annotators are not blind. Prior audits found first-pass treatment harder on baselines, and only negative quality labels were audited. These admissions make the evaluation transparent but do not remove the confounds; cross-system and cross-condition quality differences cannot be uniquely assigned to system performance.

**Required work:** relabel a common blinded, randomised sample of every system/condition with the same independent humans, use overlapping assignments and adjudication, and audit positive as well as negative labels. Give human-review role, compensation, book familiarity, time and consent details, which the local `HUMAN_REVIEW.md` explicitly says are still owed. Keep LLM labels useful as a scalable secondary analysis, not the only grounding of central claims.

### M12 — High: the treatment does not causally separate reading from memory

**Locations:** `sections/06b-decon.tex:7–11`, PDF p.8; `appendix/i-contamination.tex:51–59,82–103,181–192`, pp.28–29,31–32; `sections/limitations.tex:59–76`, p.9.

The body says the condition “separates” reading from memory. In reality 0.110 of treated paragraphs are still recognised, paraphrasing is unproofread, a children's-age answer is changed into an interval of minutes, and the name map introduces collisions that specifically damage the long-context/full-text systems. Gold fidelity was checked against selected evidence paragraphs rather than the entire story or strict support test. Precision intentionally treats a fact introduced by corrupt paraphrasing as supported when it matches the altered text. Name-only system-generation results are not reported, so effects of renaming and rewriting are not separated. The very large X1 recall collapse is compelling evidence of recognition-dependent closed-book performance; smaller changes in readers, or differences in X2 disclosure, are not identified memory effects.

**Required work:** validate/refine treatment without retaining incompatible old result cells, quantify mutation categories, report the names-only ablation for the systems if making causal claims, use several independently drawn name maps/treatments or a demonstrably unseen natural text, and freeze/evaluate after validation. Otherwise call this a stress test reducing recognisability, with exploratory interpretation.

### M13 — High: no independent generalisation test and tuning on the evaluation series

**Locations:** `sections/05-setup.tex:10–11`, PDF p.5; `sections/06-results.tex:94–97`, p.7; `sections/limitations.tex:4–8,41–50,84–93`, pp.9–10; `appendix/c-implementation.tex:76–94`, p.17.

The only natural-text series is Anne, used in development and revisited after its first labels. The reported system receives a batch of changes after evaluation while comparison systems do not receive an equivalent round. There is one generator and one run; five cutoffs are dependent versions of one work. The decontaminated version is a treatment of that same story, not a second held-out series. The candid disclosures prevent accidental misrepresentation, but empirical scope remains too thin for general claims about narrative reference generation or the comparative merits of retrieval designs.

**Required work:** freeze the final system/protocol and evaluate truly held-out series with varied length, identities and narrative structure; use repeated generation where differences are small and evaluate another generator. Keep authorised corpus scope and budget limits. As a lower-cost writing route, explicitly position this as a pilot/evaluation case study and strengthen independent human/detector validation first.

### M14 — High: output populations confound the headline comparison

**Locations:** `sections/05-setup.tex:33–46`, PDF p.5; `sections/06-results.tex:70–92`, p.7; `appendix/g-additional-results.tex:74–108,129–141`, pp.18–19,21 (Table 11).

Baselines receive a gold-derived cast and write only those character pages. NarrativeWiki discovers its own cast and additionally publishes relationship, codex, timeline and index surfaces. M1 rewards a gold fact conveyed anywhere, giving extra surfaces extra recall opportunities, while whole-artifact precision samples NarrativeWiki's additional surfaces (especially relationship lines) and penalises it for their errors. This is a valid product-level description, but it does not isolate whether graph extraction is better or worse at comparable page-generation work. The cast-page precision comparison has just **35** sampled NarrativeWiki atoms, and the pooled cited-cast sufficiency is **14 of 35**. The paper correctly disaggregates some outcomes; it needs enough matched sampling to support the recommendations made from them.

**Required work:** separate end-to-end artifact evaluation from common-cast, common-surface page-generation evaluation; increase and stratify matched samples; report entity discovery independently. Give each baseline an equivalent artifact expansion if claiming whole-artifact architectural superiority. Do not infer statistical equivalence from a nonsignificant/underpowered 35-atom comparison.

### M15 — Medium: identity disagreement is not purely a causal measure of future-text dependence

**Locations:** `sections/06-results.tex:116–121`, PDF p.8; `appendix/g-additional-results.tex:184–218`, pp.19–20,23 (Table 14).

The deterministic candidate miner provides convincing examples of dependence on future counts. But one full index and one index per prefix also contain model/run variability, which the caption acknowledges. Alias-set differences need not mean a reader sees a different person, and regrouping/absence are more consequential than an extra already-eligible alias. Calling the entire 0.390 mismatch rate “identity dependence” is therefore a descriptive operational definition, not an isolated estimate of causal identity leakage.

**Required work:** keep the stricter regrouped/absent rate beside the all-mismatch rate, distinguish alias-set mismatch from wrong-person output, and compare same-scope rebuild variability or otherwise control generation when making causal statements. Human-label the later-anchored identity cases and add them to an artifact-level disclosure benchmark.

## Submission priorities

1. Fix the definite prose/statistical-estimand errors now: M02–M09. These require no provider spend.
2. Resolve human-review contradictions, blind the evaluation and validate disclosure negatives: M01, M10, M11. These are the strongest acceptance blockers.
3. Freeze the dataset/evidence and treatment after validation; stop describing treatment as identified reading-versus-memory separation: M05, M06, M12.
4. Add held-out evidence and matched-page comparisons, or explicitly submit a narrowly scoped pilot/evaluation paper: M13–M15.
5. Put the most consequential detector/annotation caveats in the main methods/results rather than relying on the appendix. Keep the useful negative findings and concrete pipeline failure cases.

## Claims that survive this review

The observed artifacts demonstrate that instructions with future text present can fail to keep a cutoff; construction over later volumes can alter early identity/cast surfaces; source eligibility alone cannot preserve attribution/modality; correct citations are distinct from merely printing a citation; and model familiarity materially affects closed-book outputs. The paper's inventory-specific observed counts and descriptive metric means can be reported as pilot measurements with their full annotation/search limitations. They do not establish that every unobserved spoiler is absent, that memory has been isolated from reading, or that the final system improves over a strong prefix-retrieval reference.

The checked source/run registry consistently identifies the system generator as Gemini 3.6 Flash. `results.tex:888`, the supplied PDF p.5 and stored `docs/eval/cost/anne@v2_final.json` agree. The comparative Flash-Lite sentence in `appendix/l-observations.tex` adopts 3.6 Flash after finding fewer unsupported outputs; it is not a proven run-model inconsistency. This review does not externally validate the provider model identifier; the bibliography/model-source audit is separate.
