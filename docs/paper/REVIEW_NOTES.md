# Author follow-up after the editorial pass

The revision improves presentation, preserves existing measurements, and makes the
evaluation scope explicit. It does not resolve the following issues without raw data
or new annotations. This file is an author note, not an appendix for submission.

The 2026-10-10 reviewer-concern audit is in
`../vision/plans/0020-reviewer-concerns.md`. Human agreement tables are already included.
The maintainer confirms that Claude reviewed and finalized all reported AI labels; the
manuscript attributes those labels to Claude. A common finalizer does not establish
blinding or repair all review disagreements. Setup now specifies the propagated recall
recheck and distinguishes unresolved precision/citation disagreements. B4 is included in
the generation-input-bounded aggregate and uncertain counts; unique subject-fact counts
are reported separately. The method qualifies explicit title metadata versus recognized
model output and later aliases in actual prompts. No system was regenerated or relabeled.

The follow-up in plan `0021-paper-framing-dataset.md` reframes the title, abstract,
contributions and conclusion around the task/protocol and pilot dataset. Dataset size,
stored-record samples, direct versus conjunction/coreference reasoning, and a partial
gold-evidence example are added to the corpus appendix. Closed-book outputs no longer
receive an unqualified memory-only causal label. The illustrated cutoff target is not
presented as an observed safety guarantee. Release wording distinguishes AI labels and
agreement summaries from unavailable raw human decisions and complete runtime call logs.
No experiment or test suite is rerun, and the empirical concerns below remain open.

The subsequent raw-label import in plan `0022-human-label-reproduction.md` supplies the
two reviewer CSVs and accompanying records, reproduces agreement, adds human pair-placement
agreement and corrects reversed reviewer-reference columns. The reference is verified as
an accepted AI-assisted snapshot, not a blind first pass. Human authorship is maintainer-
reported and conflicts with preserved archival metadata. This supersedes the earlier
missing-raw-data limitation, but leaves blinding, provenance verification and adjudication open.
The aligned audit identifies disagreements and shared changes without substituting them
into the primary population metrics.

1. **Repair and audit gold evidence.** The recorded source paragraphs fully establish
   85 facts, partially establish 23 and fail to establish three. Retrieve sufficient
   eligible evidence, confirm earliest reveal volumes, and recompute affected values.
   Report a sensitivity analysis on a fully supported gold subset if feasible.
2. **Obtain independent, blinded judgments.** Prioritize disclosure candidates and
   the search's missed cases, plus a common precision/citation sample across systems.
   Have reviewers label before viewing LLM answers, record disagreements and propagate
   adjudicated corrections. The subsequent two-reviewer check reports task-wise agreement
   on reviewed AI annotations; blinding and annotation accuracy remain separate questions.
3. **Validate generalization and uncertainty.** A held-out series and repeated runs
   would materially strengthen the main-conference case. With raw labels, use paired
   comparisons on shared characters or facts and resampling that respects clustering;
   cutoff standard deviations describe these artifacts, not confidence intervals.
   Character-level zero-event bounds are illustrative and assume independent,
   representative character units, which the purposive cast does not establish.
4. **Strengthen controlled comparisons.** B4 is now visible in the main table. It
   shares B5's graph but changes retrieval, prose generation and publication scope.
   Its total build cost is unreported. Match output populations and budgets before
   treating this comparison as an isolated ablation. Validate the renamed/paraphrased
   text independently and repeat paragraph-sufficiency checks before interpreting
   original-versus-treated differences as memory effects.
5. **Check the release and reader-facing failures.** Verify the anonymous repository,
   actual accompanying archive, licenses and frozen-run records. The paper currently
   asserts that these materials are released; this folder cannot verify that claim.
   The teaser's "No spoilers" badge is an intended behavior, not a demonstrated safety
   guarantee. The observed prediction-to-spouse error, undated identities, stale ages,
   misplaced relationship lines and leaked source keys remain valuable repair targets.
   A reader study would test whether the extra linked content improves reference use.
6. **Repair prompt definitions in the executed pipeline.** The archived extraction
   prompt exposes internal revision labels and code paths in the STATUS and APPEARANCE
   descriptions. The verifier receives the APPEARANCE canonicalization note as its
   semantic definition while being instructed to judge by that definition. This is
   a pipeline defect, and changing this paper's wording cannot repair it. Retrieve
   the actual schema and prompt-builder source, then keep semantic label descriptions
   separate from implementation metadata. Proposed clean definitions are: STATUS is
   the character's stated or presumed state (alive, deceased, missing, or captured);
   APPEARANCE is the character's physical features described in eligible evidence.
   Keep deduplication rules and the inferred-status default in implementation code,
   with their provenance explicit. Check generated prompts for accidental inclusion
   of internal revision labels or code-path metadata. Evaluate the corrected verifier
   and regenerate affected artifacts and labels before reporting corrected results.
7. **Audit citation keys and sentence limits against real calls.** The archived codex
   response returns a paragraph ID in `cited` where the prompt requests an input-line
   key such as `W1`. The author confirmed that the parser normalizes returned paragraph
   IDs; the paper now describes that behavior. The middle-elided input still cannot
   establish whether this paragraph was supplied. Obtain the complete call,
   citation-resolution code, and delivered codex page to audit evidence eligibility.
   Validate both line keys and normalized paragraph IDs against supplied evidence,
   record any rejection or repair, and measure effects on citation sufficiency after
   rerunning if validation changes. Likewise,
   the shared appearance template says 2--4 sentences while the archived NarrativeWiki
   appearance prompt requests 3--4. Decide on the intended requirement, align the
   actual prompt builder and any enforcement, and audit outputs before claiming
   matched output limits. All 53 displayed prompt/output payloads remain unchanged.

Presentation changes include the vector teaser, a complete seven-system main comparison,
a recognition-control table, updated vector cutoff plots, consistent colors and full-width
prompt boxes. None adds a new experimental condition or fabricated result.
