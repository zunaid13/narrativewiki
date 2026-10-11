# Phase 3 — Claims

**Closed:** 2026-09-02 · **Next:** Phase 4, Graph

**Update (2026-09-02, same day):** Everything below this line describes the state at Phase 3's
close, when no real gazetteer/extraction run had happened yet. That is no longer true — a real
`wiki gazetteer` + `wiki extract --volumes 1-2` ran against Mistral (see LOG.md's "Phase 3 (real
run, v01-02)" entry) and Phase 4 has since been built on top of that real data. Left unedited
below as the historical record of what Phase 3 itself verified; do not treat "nothing is real yet"
as still current.

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

```
src/narrativewiki/extract/
  windows.py      Mention para_ids -> deduped, token-bounded evidence windows. No LLM.
  schema.py       Claim / ExtractedFact / ExtractionResult Pydantic models, make_claim_id().
  claims.py       extract_character_volume() / extract_volume(): the claim_extract driver.
src/narrativewiki/cli.py             extract() wired end to end; run_all() now chains
                                       ingest -> gazetteer -> extract, stopping at the Phase 4 stub.
src/narrativewiki/audit/reports.py   _claims_report(): claims-per-character table, predicate
                                       distribution, polarity/confidence spread, and a real
                                       re-verification that every cited quote is verbatim in its
                                       paragraph (FAILs loudly if not).
src/narrativewiki/config.py          Settings.extraction_behaviour — the extraction.yaml
                                       `extraction:` sub-block (window/confidence/quote policy).
tests/test_extract.py                27 tests: window clustering/merging/hard-break/token-budget
                                       behaviour, claim_id determinism, every drop reason in
                                       claims.py, evidence-merge-by-claim_id across two windows,
                                       and extract_volume's cross-character aggregation.
```

## Verify it in one command

```bash
python -m narrativewiki extract --volumes 1-13   # needs `ollama serve` + the model pulled,
                                                    # AND a real gazetteer already built (Phase 2)
python -m narrativewiki audit claims
python -m pytest                                   # 105 passed
```

**Ollama was not reachable in this sandbox either** (`localhost:11434` refused the connection,
same as Phase 2) — so, same as last phase, this was verified two ways instead: unit tests with a
scripted fake client (`tests/test_extract.py`), and one real end-to-end smoke run against v01's
*actual* parsed text with `narrativewiki.llm.providers.ollama.complete` monkeypatched to a
content-derived fake (it echoes a verbatim substring of whatever paragraph the window handed it,
so the quote-verification step is exercised for real, not faked around). That run used a
hand-written 3-entity gazetteer fixture (not a real Phase 2 build — none exists yet), ran real
Aho-Corasick mention indexing over v01's real text (785 genuine mentions), then the real `wiki
extract` CLI command end to end: **80 LLM calls** (2 characters × exactly 40 windows each — proof
`max_windows_per_entity_per_volume` is actually enforced), evidence correctly merged into one
`PERSONALITY` claim per character (40 evidence items each, one per window — proof
`claim_id`-based merging works across many windows, not just two), and `wiki audit claims` came
back clean. All of it — `data/02_entities/`, `data/03_claims/`, and the LLM cache/budget ledger
the run populated — was deleted afterward, same as Phase 2's precedent: fixture output, not a
real build.

**The single most important thing to do before Phase 4 is still what Phase 2 left unfinished: a
real `wiki gazetteer --volumes 1-13` on a machine with Ollama running, a hand-audit of
`roster.html`, and only then a real `wiki extract --volumes 1-13`.** Nothing in this phase's data
directories is real yet.

## Things you need to know

**Windows, not chapters, are the unit of extraction — and `wiki extract` calls the model once per
window, not once per character.** PROMPTS.md says the `claim_extract` prompt "runs once per
character per volume"; read that as naming the prompt template, not the call count. In practice a
protagonist named 785 times in one volume (the real v01 count for Shin's surface forms) still
produces at most `max_windows_per_entity_per_volume` (40, from `extraction.yaml`) calls, because
`extract/windows.py` clusters nearby mentions into merged windows first and then caps the total,
keeping the densest clusters. The smoke test's 80-call total (2 characters × 40) is the cap
working as designed, not a bug.

**A claim's `object` is resolved only against entities already mentioned in the same window's
`mentions.jsonl` records, never against the whole gazetteer.** This is deliberate, not a
shortcut: it means the model cannot produce a relation to a name it did not actually read in the
passage it was given — see PROMPTS.md rule 4 ("evidence is mandatory and verbatim") applied to
entity resolution as well as quotes. `claims.py::_resolve_object` tries an exact surface match
first, then substring containment, both case-insensitive. If a real run shows a lot of
`unresolved_object` drops for an obviously-present name, the likely cause is the window's context
paragraphs not including the sentence that names the object — not a resolver bug — since
`extraction.window.context_paragraphs_before/after` bounds how far a window reaches.

**Repeated observations of the same fact merge by `claim_id`, not by window.** `claim_id` is
`sha1(subject, predicate, object_norm, first_vol)[:8]` (`schema.make_claim_id`), so if two
different windows in the same volume both support `(shinei-nouzen, AFFILIATED_WITH,
spearhead-squadron)`, they land on the identical id and `claims.py::_merge_claim` combines their
evidence lists and keeps the higher confidence — this is what let the smoke test's 40 separate
`PERSONALITY` observations collapse into one claim with 40 evidence items instead of 40
claims. A *different* value for the same `(subject, predicate, first_vol)` — e.g. two different
ages stated in the same volume — deliberately does **not** merge, since `object_norm` differs;
both claims are written, which is exactly the shape `graph/contradictions.py` needs in Phase 4 to
arbitrate a same-volume conflict (CONTRACTS §4.2). Don't "fix" this by merging on
`(subject, predicate, first_vol)` alone — that would silently pick a winner here, a full phase
too early.

**Verbatim-quote checking happens twice, on purpose, and that's not redundant.**
`claims.py::_build_claim` drops a fact immediately if its quote isn't a literal substring of the
cited paragraph — this is the main defense against a confident 14B model inventing a plausible
quote (PROMPTS.md rule 4), so a bad quote never reaches the claims file at all. `wiki audit
claims` re-checks every written claim's quote against the paragraph independently, reading only
`data/03_claims/*.jsonl` and `data/01_parsed/*.jsonl` — it would only fail if `_build_claim`'s
check had a bug, or if a claims file were hand-edited or corrupted. Keep both: the first is a
filter, the second is a trust-but-verify audit of the file that's actually on disk.

**`extraction_behaviour` is a new `Settings` property (`config.py`), not new config.** It just
returns the `extraction:` sub-block of `extraction.yaml` (window sizing, confidence floors,
`drop_unresolved_entities`, `max_quote_chars`) — added because `settings.extraction` was already
taken by the whole parsed file, and repeating `settings.extraction["extraction"]["window"]` at
every call site was worse than one property. Same pattern as the pre-existing `client_config` /
`budget_config` properties on `self.models`.

**A window whose core mention paragraphs alone exceed
`extraction.window.max_tokens_per_request` is left oversized, not truncated.**
`windows.py::_shrink_to_budget` trims outward *context* first and will never cut a paragraph that
actually contains a mention, so the token cap can only be hit exactly when a single paragraph (or
a very dense mention cluster) is already huge on its own — rare in this corpus, since paragraphs
are prose-length, not whole scenes. Documented gap, not a silent one: if a real run logs a huge
oversized window, the fix is either a smaller `context_paragraphs_before/after` for that series or
a follow-up truncation step, not a change to this rule.

**Trait `max_words` (extraction.yaml) is a prompt instruction only, not a code-level filter.**
`claims.py` does not reject a `PERSONALITY`/`SKILL`/etc. value for being a few words over its
configured `max_words` — enforcing that in code risks discarding a genuinely good short phrase
over a soft length heuristic. If real extraction shows traits routinely running long (a sentence
instead of a phrase), tighten the prompt wording first before adding a code-level cutoff.

**Symmetric relations (`SIBLING_OF`, `FRIEND_OF`, ...) are not deduplicated across subjects at
this phase.** Extraction asks "what do we learn about character X" independently for every
character, so a passage naming both A and B as friends can produce both `(A, FRIEND_OF, B)` (while
processing A) and `(B, FRIEND_OF, A)` (while processing B) as two separate claims — this is
expected, matches "extraction = claims table verbatim," and `extraction.yaml`'s own comment
("`symmetric` relations are stored once and rendered from both sides") describes graph-layer
normalization, which is Phase 4's job (`graph/temporal.py`/`edges`), not this phase's.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| One LLM call per evidence window (up to `max_windows_per_entity_per_volume` per character per volume) | Matches the token-budget design in VISION.md/PROMPTS.md exactly — a window is already capped at `max_tokens_per_request`; one call per window keeps each request small and cacheable | One call per character per volume with all windows concatenated — breaks the per-request token cap and produces one giant, harder-to-repair JSON response |
| Resolve relation objects against the window's own `mentions.jsonl` entries only | Guarantees a claim's object was actually named in the cited passage; free (mentions are already computed by Phase 2), no fuzzy matching needed | Fuzzy-matching the model's object text against the whole gazetteer — could resolve to an entity never mentioned in the passage at all, silently inventing evidence |
| Content-addressed `claim_id` (hash of subject/predicate/object_norm/first_vol), with evidence merged across windows on a matching id | Naturally collapses hundreds of repeat observations of the same fact into one claim with rich evidence, and keeps same-volume *conflicting* values as separate claims for Phase 4 to arbitrate | Deduplicating by `(subject, predicate)` alone — would either drop legitimate conflicting values or need a separate "pending arbitration" side table a phase early |
| Drop a claim outright on any verbatim-quote or unresolved-object failure, rather than repairing or flagging it | PROMPTS.md rule 4: evidence is the main defense against hallucination; a claim without real evidence isn't a weaker claim, it's not a claim | Keeping the claim with a `flagged` status for a human to review — adds a review queue this phase's scope (CONTRACTS §3) doesn't call for; `wiki audit claims`' FAIL check exists for exactly this instead |
| `extraction_behaviour` as a new `Settings` property | One property, matching the existing `client_config`/`budget_config` pattern, versus repeating `settings.extraction["extraction"][...]` at every call site | Reading the raw dict directly in `windows.py`/`claims.py` — works, but scatters the same three-level lookup across two modules |

## What Phase 4 must do

Implement `graph/{store,temporal,contradictions}.py` and register `wiki audit contradictions`.
Read `docs/CONTRACTS.md` §4 for the graph schema before writing anything.

Useful things this phase leaves behind: `data/03_claims/v{NN}.jsonl` already has same-volume
conflicting claims as **separate, distinctly-`claim_id`'d records** (see the claim-merge note
above) — `graph/contradictions.py` does not need to detect a conflict by comparing values across
files, it needs to *group* claims sharing `(subject, predicate, first_vol)` and check whether their
`object`/`value` differ. Cross-volume claims for the same `(subject, predicate)` are similarly
already separate records (different `first_vol`, hence different `claim_id`); Phase 4 turns those
into interval supersession per CONTRACTS §4.1. `evidence` on every claim already carries whatever
`print_page`/`quote` the arbitration prompt (`arbitrate_conflict`, PROMPTS.md) will need to show
the model both sides of a same-volume conflict.

## Known gaps, deliberately left

- No real end-to-end run against Ollama happened in this phase either (same sandbox limitation as
  Phase 2) — verified instead via unit tests plus one monkeypatched-provider smoke run against
  real v01 text with a hand-built gazetteer fixture. **Run a real `wiki gazetteer` then a real
  `wiki extract` before Phase 4** — this is now the single most important next action, carried
  forward from Phase 2's own handover.
- A window whose core mention paragraphs alone exceed the token budget is not truncated (see notes
  above) — not exercised against the real corpus yet since no real extraction run has happened.
- Trait `max_words` is prompt guidance only, not code-enforced (see notes above).
- Symmetric relations are not deduplicated across the two subjects that both observe them — by
  design, left for Phase 4's graph normalization (see notes above), not an oversight.
- `extract/claims.py` calls the model once per window with no batching across windows of the same
  character — correct and matches the token-budget design, but means a very talkative protagonist
  still costs up to `max_windows_per_entity_per_volume` calls per volume; this is the intended
  cost/recall tradeoff the config knob exists to control, not something to "optimize" away without
  changing what evidence extraction actually sees.
