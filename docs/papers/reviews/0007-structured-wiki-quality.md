# Research and evidence record: structured, spoiler-scoped wiki quality

Reviewed 2026-09-24 for [the vision](../../vision/plans/0007-structured-wiki-quality-vision.md)
and [task 0007](../../vision/plans/0007-structured-wiki-quality.md).
Review ID: `20260924-structured-wiki-review`.

## Reproducibility and scope

- [0007-downloads.json](0007-downloads.json) records exact URLs, byte lengths and SHA-256 checksums.
  PDFs were downloaded from ACL Anthology and arXiv, checked for a PDF header and opened locally
  with PyMuPDF. Metadata/title pages were inspected. Public GET requests sent no project text.
- [download_review_papers.py](../../../scripts/papers/download_review_papers.py) reproduces
  missing downloads and preserves existing files; verify checksums against the committed manifest
  when checking a later download.
- [structured_wiki_snapshot.py](../../../scripts/eval/structured_wiki_snapshot.py) reproduces
  implementation counterexamples and reads the production graph with `mode=ro`;
  [its snapshot](../../eval/structured_wiki_snapshot_spice-and-wolf.json) records input hashes.
- These are **selected-section readings**, not full-paper reviews or replications. Page numbers
  below are **1-based PDF pages**; printed proceedings pages are also supplied for ACL papers.
  No paper's performance number is reused as a project result or target.
- The PDFs are version-pinned and live in the shared `docs/papers/pdf/` inventory (moved there
  2026-09-24). `scripts/papers/fetch_reference_pdfs.py` manages the arXiv-verified part of that
  inventory; its `--check` accepts these files because this review's manifest claims them. Its
  stale global bibliography is not silently regenerated as part of this review. The EvolvTrip
  copy was byte-identical to the existing file and was deduplicated; the MiniCheck copy is the
  EMNLP 2024 edition, kept beside the arXiv one with an ` (EMNLP 2024)` suffix.

Search scope: primary work on character representation, narrative state/knowledge graphs,
temporal narrative retrieval and evidence verification. The recent search identified STAGE's
2026 revision; 2025 methods and relevant foundational 2024 work were retained where they map
to a concrete implementation question. This is a targeted review, not a systematic survey.

## R1 — CHIRON

Alexander Gurung and Mirella Lapata. **CHIRON: Rich Character Representations in Long-Form
Narratives.** Findings of EMNLP 2024, pp. 8523–8547.
[Primary record](https://aclanthology.org/2024.findings-emnlp.499/),
[archived PDF](<../pdf/CHIRON - Rich Character Representations in Long-Form Narratives.pdf>), DOI `10.18653/v1/2024.findings-emnlp.499`.

**Read/used:** PDF pp. 3–4 (printed 8525–8526), §4 “CHIRON: Character Sheets”, Table 1,
and §5/§5.1 opening; PDF p. 9 (8531), Limitations. Also inspected title/abstract.

**Specific use:** §4's character-and-snippet questions motivate WP4's single category top-up.
The sentence validation and individual-claim simplification discussion on p. 4 motivates
separating candidate discovery from publication. Table 1 is a question-design reference only.

**Boundary:** this project's closed typed assertions are our adaptation. No CHIRON model is
trained/imported and its similarity threshold is not adopted. Its limitations identify missing
prior-story context and uncertain salience; give our validator only eligible earlier context.
Status: **Reference / proposed adaptation**, not Applied.

## R2 — STAGE, specifically revision v9

Qiuyu Tian et al. **STAGE: A Full-Screenplay Benchmark for Reasoning over Evolving Stories.**
arXiv `2601.08510v9`, revised 2026-08-04.
[Primary version](https://arxiv.org/abs/2601.08510v9),
[archived PDF](<../pdf/STAGE - A Full-Screenplay Benchmark for Reasoning over Evolving Stories.pdf>).

**Read/used:** PDF pp. 3–4, §3.1.2 and Figure 2; p. 5, §3.2.1 and §3.3;
p. 9, Limitations. Title/abstract and revision history checked.

**Specific use:** evidence-linked state/development records inform WP2/WP5. The reference-state
versus autoregressive update distinction and no-change controls inform WP6 stability tests.
Separate state/development coverage and contradiction measures inform WP0.

**Boundary:** character access differs from reader access. Screenplay results do not validate
novel extraction, and no role-playing or movie-data expansion is proposed. Its review and
context-condition caveats remain applicable. Search results exposed an older title/task set:
this plan uses **v9**, not those earlier descriptions. Status: **Reference / proposed adaptation**.

## R3 — EvolvTrip

Bohao Yang, Hainiu Xu, Jinhua Du, Ze Li, Yulan He and Chenghua Lin.
**EvolvTrip: Enhancing Literary Character Understanding with Temporal Theory-of-Mind Graphs.**
arXiv `2506.13641v1`, 2025-06-16.
[Primary version](https://arxiv.org/abs/2506.13641v1),
[archived PDF](<../pdf/EvolvTrip - Enhancing Literary Character Understanding with Temporal Theory-of-Mind Graphs.pdf>).

**Read/used:** PDF p. 4, §3.3 “Mental State Triple Extraction”; p. 5, §3.4 “Temporal Knowledge
Graph Construction”; p. 9, Limitations. Also read the adjacent dataset description on p. 4.

**Specific use:** perspective-qualified mental-state predicates and plot-local temporal links
inform WP2's attribution and explicit belief-change representation.

**Boundary:** our proposed uncertainty and hypothetical handling is an extension, not an
implemented EvolvTrip mechanism. The paper explicitly limits its treatment of uncertainty,
counterfactuals and complex psychology; its multiple-choice evaluation does not certify wiki
generation. Do not infer hidden motives merely to fill fields. Status: **Reference / proposed
adaptation**; no claim to implement its system.

## R4 — E²RAG

Ze Yu Zhang, Zitao Li, Yaliang Li, Bolin Ding and Bryan Kian Hsiang Low.
**Respecting Temporal-Causal Consistency: Entity–Event Knowledge Graphs for
Retrieval-Augmented Generation.** arXiv `2506.05939v1`, 2025-06-06.
[Primary version](https://arxiv.org/abs/2506.05939v1),
[archived PDF](<../pdf/Respecting Temporal-Causal Consistency - Entity-Event Knowledge Graphs for Retrieval-Augmented Generation.pdf>).

**Read/used:** PDF p. 4, §4 opening; p. 5, formal definition/Eq. (1), preprocessing and
query-time retrieval steps; p. 9, Limitations. Title/abstract checked.

**Specific use:** keeping context-specific entity mentions linked to events motivates WP2/WP5
occurrence provenance instead of collapsing all descriptions into a timeless entity profile.

**Boundary:** retain canonical identity and separate observations locally. Do not adopt the
paper's name-in-generated-description link rule as evidence of participation, nor its full
embedding/retrieval architecture. Temporal relevance does not establish reader-disclosure
safety. Status: **Reference / proposed adaptation**.

## R5 — MiniCheck

Liyan Tang, Philippe Laban and Greg Durrett. **MiniCheck: Efficient Fact-Checking of LLMs on
Grounding Documents.** EMNLP 2024, pp. 8818–8847.
[Primary record](https://aclanthology.org/2024.emnlp-main.499/),
[archived PDF](<../pdf/MiniCheck - Efficient Fact-Checking of LLMs on Grounding Documents (EMNLP 2024).pdf>), DOI `10.18653/v1/2024.emnlp-main.499`.

**Read/used:** PDF p. 2 (printed 8819), §2 claim-verification setup and footnote 2;
pp. 9–10 (8826–8827), Limitations: interpretation and multi-document reasoning.
Title/abstract checked.

**Specific use:** calibrate the existing `graph/support.py`/MiniCheck path on our reviewed
narrative statements (WP0/WP2/WP5). Distinguish evidence support from absolute truth.

**Boundary:** binary unsupported is not a contradiction classification; the paper's setup
does not establish reliability on widely separated novel evidence. Scores cannot replace
independent gold or justify dropping ambiguous claims without a disposition record.
Status: **Applied in the existing backend; proposed calibration/extensions unimplemented**.

## Interpretation rules for later contributors

Each adoption must identify its source ID, local hypothesis, changed files, controlled experiment,
observed result and whether the mechanism is now Applied, rejected, or still Reference. Do not
upgrade a citation's status because the project uses similar words. For unread sections or new
revisions, download/pin and record the additional reading before citing them as evidence.

No paper fully supplies the proposed publication boundary or dual disclosure/time model. Those
are project design proposals motivated by observed defects; they must pass local fixtures and
held-out evaluation. The diagrams and proposed schemas in the vision are our design, not copied
architectures or claims of published guarantees.
