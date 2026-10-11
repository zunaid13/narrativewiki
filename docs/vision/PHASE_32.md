# PHASE_32.md — Five-volume evaluation of a generalised pipeline

Append-only. A superseded decision gets a new dated entry; never rewrite one.

## 2026-09-27 — Maintainer requirements: 5 volumes, recall at fixed precision, one pipeline for all series

**Requirements (maintainer, verbatim intent, numbered as given):**

1. Keep precision at 100% and raise recall as far as possible. Read the papers first.
2. Raise the volume limit from 2 to **5 per series**. Evaluate everything at 5 volumes (prose
   generation, accuracy, recall, precision, spoiler leakage) and record every number.
3. If the 5-volume numbers are worse, research papers and change the pipeline to fix them.
4. **Remove character images.** Portrait identification is outside the study's scope; it is
   recorded as future work.
5. Overlord: Ainz's Rank read "level 100" at v1 and "copper plate" at v2. A field must hold one
   kind of value. Explain the numeric/categorical mix and fix it.
6. At v2, information from v1 must stay visible, marked with the volume in which it was true.
7. Build a second stress-test wiki with about 60 characters.
8. **Every value must come from the general pipeline.** Converting a raw series into the format
   the pipeline reads is allowed, and so is hand-made ground truth for evaluation. Behaviour
   tuned for one series is not allowed. Examples: a per-series prompt, a per-series schema
   overlay, a hand-edited roster, or a manual fix to an output.
9. A page must never say "changes later" or anything else that reveals the future.

**Clarifications obtained (2026-09-27):**
- Point 8, in the maintainer's words: *"converting raw series into a format that the pipeline
  understands is fine. manual editing errors to use as a ground truth for evaluation or comparison
  is also fine. but the final product should be a generalized project which once given the input
  … should output a good wiki fandom."* Under that reading:
  - **Allowed:** EPUB structure selectors, skip files, volume patterns and volume breaks (format
    conversion); `series.author`/`title` metadata; hand-made gold files.
  - **Not allowed:** `entity_overrides` (merge/split/rename/exclude/force_type/aliases/
    remove_aliases), `config/extraction.<series>.yaml` overlays, and per-series
    `prompt_vocabulary`. Each is replaced by a general rule or removed. Hand overrides that record
    true facts move to gold (`docs/eval/gold/<series>/roster.yaml`), where they measure the
    general rule instead of patching its output.
- Point 7: a **new Project Gutenberg novel**, not the Anne rebuild or Overlord. Chosen:
  *Middlemarch* (Gutenberg #145). It is published in 8 Books, which act as natural volumes
  (capped at 5 like every other series), and has a cast of roughly 60 named characters.

**Scope change:** the frontier interlock `vertex_flash.max_volumes` goes 2 → 5 in
`config/models.yaml`. The limit is 5 for every series (`AGENTS.md` §3). 86 stays off-limits and
Mushoku Tensei stays out (the corpus is `.cbz` page images, not text).

**Diagnoses made before any change (2026-09-27):**
- *Point 5.* `RANK` is one `single: true` slot with no definition in `extraction.yaml`. The
  extractor filled it with a game power level at v1 ("level 100") and an adventurer-guild grade
  at v2 ("copper plate"). Cross-volume supersession then treated the second as replacing the
  first. That is two dimensions in one slot, not a narrative change.
- *Point 6.* List fields already carry v1 values into v2. What disappears is the superseded value
  of a single-valued field: `conflicts.quiet_change: [AGE, RANK, TITLE, OCCUPATION]` suppresses
  the "previously: X (v1–v1)" line for exactly those predicates.
- *Point 9.* `site/okf.py` prints `_(changes later)_` on a v1 page when the v1 value's interval is
  closed by a later volume. The later volume's existence is itself a spoiler. `cli.py` does the
  same in the terminal.
- *Precision.* The "100% precision" in earlier reports is **selected-control precision**: no
  hand-listed negative fact appears on a page (MEASUREMENTS §22, row "Legacy precision blind
  spot"). It is not precision over every assertion the wiki makes. Requirement 1 is measured as
  **audited assertion precision**: a random sample of rendered structured assertions, each judged
  against its cited paragraph, reported with its denominator.

**Execution plan:** `docs/vision/plans/0011-five-volume-generalised-evaluation.md`.

## 2026-09-27 (later) — Decisions taken before the five-volume runs

Numbers: `docs/MEASUREMENTS.md` §48. Plan: `docs/vision/plans/0011-five-volume-generalised-evaluation.md`.

- **Precision is measured, not asserted.** Hand-read precision of the shipped v1–2 wikis is 99/120
  (82.5%). "Keep precision at 100%" is therefore a target to reach, not a state to keep.
  Every miss was a relation label ("Friend of" for a business contact), a field holding the wrong
  kind of value (Origin: "traveling merchant"), or a false "(ended v1)". The written standard for
  traits: a trait is supported only when the text presents it as characteristic.
- **The verifier judges by the definitions the extractor was given** (`graph/verify.py` v5). On
  Leagues the same 40 lines went 24/40 → 21/24, at a cost of 3 borderline supported lines.
- **Gleaning (GraphRAG App. A.2) rejected.** +73% claims on Spice and Wolf v01, but the gleaned
  ones were 9/25 supported with 6/25 unsupported (first pass: 14/25 and 1/25), at twice the cost.
  CHIRON's generate-then-validate split is kept as the model for the verifier, not for more
  generation.
- **Recall comes from rendering, not from asking more.** Every verified PERSONALITY/FEAR and
  BACKGROUND row is listed ("Traits", "Background by volume") instead of only what survived a
  capped paragraph.
- **Rejected:** keeping per-series overrides as an "optional expert layer" (it is what req. 8
  forbids), and a numeric LEVEL attribute for Overlord (a genre-specific schema).
- **Series rules found by the stress corpus, all general:** first-volume naming; kinship words
  never name a cluster with a proper name; appositives ("my mom, Effa") propose pairs; a
  confident "different" verdict is a cannot-link; a cluster holds at most one honorific
  (Mr./Miss Brooke); narrator adjectives ("Poor Dorothea") and leading prepositions are not part
  of a name.
- **Future work (req. 4):** character portraits need a model that can see what an illustration
  depicts. The removed heuristic guessed from which plate was nearest a character's debut.
