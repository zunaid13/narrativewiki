# Phase 23 — Precision, Grounding, and Fandom-Grade Pages

## 2026-09-10 — Scope and design decisions

**Trigger:** user audit of the live Spice and Wolf v1-2 site. `/#/relationships/marheit/kraft-lawrence`
renders "Kraft Lawrence — Spouse of — Marheit," which is false. Investigation (three parallel
Explore passes over the graph DB, the extraction pipeline, and the rendered bundle/site) found this
is not an isolated bug but the normal output quality of the pipeline as it stands after Phase 22:

- Root cause of the spouse claim: a 5-paragraph evidence window (`context_paragraphs_before/after:
  2`) that excludes the actual referent of "partner" (Holo, named 3 paragraphs past the window
  edge); a prompt that forces an attribution to the one subject in scope even when the passage
  isn't about them; `SPOUSE_OF` carrying no guardrail `note:` (unlike `RELATIVE_OF`/`COMMANDS`,
  which do); and `extract/resolve.py::resolve_surface` binding the relation's object to a string
  the model echoed from the prompt's own `group_known_entities()` label
  (`"Lawrence Kraft (also: Lawrence)"`) rather than a name from the passage — confirmed systemic:
  194 of 621 extraction calls in the live run returned an object of this shape.
- Graph-wide: 29 of 47 relation claims cite evidence that does not name both endpoints; 15 name
  neither. `RELATIVE_OF` (14 intervals, second most common predicate) is essentially all wrong.
  `CHILD_OF` fired in both directions off one sarcastic line. A captive renders as a company
  "member." Four unrelated `FRIEND_OF` edges all cite the same two-word quote, `"Fall back."`
- No layer in the pipeline checks a fact against its own evidence and can act on the result.
  `wiki verify` (Phase 22 C3) is the only evidence-grounded check, has never run on this series
  (`verification.json` absent), is advisory-only by explicit design ("never mutates a claim,
  interval, or page"), and is misrouted to an unreachable local model with no working fallback.
  `intervals`/`edges` carry no confidence column, so no downstream filter is even expressible.
- No precision metric exists anywhere. `eval/gold.py` measures recall and self-consistency only;
  its `_page_text()` flattens predicate names into the keyword bag, so a false relation can only
  *raise* the recall score. Zero of ~615 tests assert an extracted relation is correct.
- Presentation gap vs the Fandom reference (via the repo's own hand-transcribed gold data, since
  live WebFetch of fandom.com returned HTTP 402): target shape is Appearance/Personality/
  History/Relationships/Trivia as narrative prose with volume citations; current pages are
  infobox fragments plus contradictory predicate-badge pills, `aliases` dropped from the page
  model entirely, evidence never rendered, 5 of 13 pages with zero prose sections, mean gold fact
  recall 0.19. Also found: the chapter-span scene pass (documented as "the primary facts source")
  emitted zero `participant_facts` across 25 scenes — likely an output-token cap mismatch between
  `scenes.py`'s request and the `google_fast` model profile — leaving 100% of relations sourced
  from the narrow window pass that produced the spouse bug.

**Decisions** (confirmed with the user):
1. A fact whose own cited evidence does not support it is **withheld entirely** from rendered
   pages, not hedged or merely logged — nothing ships that the pipeline cannot defend.
2. Both correctness AND presentation are in scope for this phase — fixing extraction alone would
   leave true facts in an amateur-looking infobox/badge layout; restyling alone would polish wrong
   facts.
3. V1-V2 will be fully re-extracted after the code lands (cache goes cold — prompts and gates
   change), with before/after precision and recall recorded in the handover as proof.

**Scope, six parts** (full rationale and file-by-file plan in the approved plan file; mirrored here
per the append-only rule so the decision trail survives independent of that file):
- **A — extraction-side precision gates:** fix `resolve_surface` (reject echoed prompt labels,
  require passage-occurrence, return `None` on ambiguity instead of silently picking one); a new
  evidence-adequacy gate (`requires_both_endpoints`, `min_quote_words`, `subject_must_be_named`)
  for family/command predicates; guardrail `note:`s for every relation that lacks one; relation
  `conflicts_with` groups plus rejection of mutual same-predicate edges; wire the already-declared
  but dead `min_for_structured_field: 0.7`.
- **B — make verification binding:** add `confidence`/`evidence_count` to `intervals` and a new
  `verdicts` table; withhold `unsupported`-verdict or sub-threshold facts at assembly (reversible —
  nothing is deleted, `wiki explain`/`trace` still see everything); fix `wiki verify`'s routing/
  fallback and give it full evidence instead of a 2-quote cap; run it inside `graph build` so it
  cannot be skipped, and make `wiki audit verify` FAIL rather than only report.
- **C — measure precision:** a real `score_fact_precision` in `eval/gold.py`; fix `_page_text`'s
  leak; add `negative_facts` to the gold schema (assertions the wiki must NOT make) seeded from
  this audit's findings; gate `wiki audit eval` on negative facts and precision regression; tests
  that assert a relation is wrong — the first such tests in the repo.
- **D — recall defects:** fix the scene pass's zero-output bug (checked first — likely recovers
  most missing recall on its own); widen evidence windows now that A's gates prevent a wider
  window from becoming a wider hallucination surface; diagnose the epithet miner's zero output.
- **E — Fandom-grade pages:** restructure `page_outline` to Appearance/Personality/History/
  Relationships/Trivia; make Appearance prose-generated instead of an infobox fragment list;
  make relationship cards narrative paragraphs per pair instead of badge grids; render evidence as
  visible citations; carry `aliases` onto the page model; fix the dangling `saint-ruvinheigen`
  roster/search/link entries that point at a page file which doesn't exist.
- **F — re-run:** full V1-V2 re-extraction against the new code, numbers recorded before/after.

**Rejected alternative:** patching the single Marheit/Lawrence claim by hand. Explicitly out of
scope per the user — the request was to find the systemic cause and design a fix that prevents the
whole class of error, not to correct one row in one graph.

**Traps hit during diagnosis** (for whoever re-runs this): WebFetch of `spiceandwolf.fandom.com`
returns HTTP 402 in this environment — the Fandom comparison had to run entirely off the repo's
existing `docs/eval/gold/spice-and-wolf/*.yaml` (each file already documents its own
WebSearch-transcription caveat for the same reason). `resolve_surface`'s ambiguity behavior
(`resolve.py:85-97`) is silent today — grep for `best[1] if best else None` if revisiting A1.
