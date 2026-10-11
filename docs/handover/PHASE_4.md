# Phase 4 — Graph

**Closed:** 2026-09-02 · **Next:** Phase 5, Pages (`synth/assemble.py`, `graph/ppr.py`, `explain`)

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

```
src/narrativewiki/graph/
  store.py          SQLite schema (entities/claims/intervals/edges/mention_counts) + write_*
                      functions. connect()/reset() for a full rebuild each run.
  temporal.py        assign_single_valued() / assign_multi_valued(): the interval-building
                      primitives. state_at()/history_at(): the ONLY sanctioned reads of
                      `intervals` (CONTRACTS §4.1).
  contradictions.py  build_graph(): the Phase 4 entry point. Resolves same-volume ties (rule or
                      `arbitrate` LLM role), logs cross-volume supersession, canonicalises
                      symmetric/inverse relation pairs to one storage direction.
src/narrativewiki/cli.py             graph_build() wired end to end; run_all() now chains
                                       ingest -> gazetteer -> extract -> graph build, stopping at
                                       the Phase 6 (synthesize) stub. No --force on graph build —
                                       it is always a full rebuild (see below).
src/narrativewiki/config.py          Settings.conflicts_config — the extraction.yaml `conflicts:`
                                       sub-block, same pattern as attributes/relations/traits.
src/narrativewiki/audit/reports.py   _contradictions_report(): conflicts-by-predicate table,
                                       resolution/arbiter distribution, flagged items printed in
                                       full, plus a graph.db interval/edge sanity count.
tests/test_graph.py                  17 tests: interval supersession/merge/dedup, state_at/
                                       history_at cutoff filtering, both relation-canonicalisation
                                       directions, every _resolve_pair path.
```

Also touched, not new: `config/models.yaml` now routes `prose_polish`/`arbitrate` to
`google_best`/`google_fast` (Gemini) instead of `anthropic_best`/`anthropic_cheap` — see VISION.md
2026-09-02 "Google key for polish + arbitration". Unrelated to the graph schema itself, but
`arbitrate` is this phase's only LLM-calling role, so the two landed in the same session.

## Verify it in one command

```bash
wiki graph build            # needs data/02_entities/ and data/03_claims/*.jsonl already real
wiki audit contradictions
python -m pytest             # 122 passed
```

**This ran for real, not just against unit tests or a monkeypatched client** — against the actual
v01-02 claims from the real Phase 3 run (LOG.md "Phase 3 (real run, v01-02)"): 130 claims -> 122
intervals, 53 edges, 1 same-volume conflict, genuinely arbitrated by `google_fast`
(`gemini-flash-lite-latest`) rather than falling back to the rule. See
`data/04_graph/contradictions.json` for the actual resolved conflict (subject `weisel`, predicate
`ORIGIN` — two extracted origin phrasings in v02, the model correctly preferred the more specific
one and said why). Phase 4 did not have Phase 2/3's sandbox limitation (no reachable model) — a
working Mistral key (bulk stages) and a working Google key (arbitrate) were both present this
session, so nothing here needed a fixture or a fake provider for its real-run verification, only
for the unit tests.

## Things you need to know

**Only `attributes.<PREDICATE>.single: true` (config/extraction.yaml) goes through
tie-resolution and supersession.** Everything else — relations, non-single attributes (TITLE,
NICKNAME, APPEARANCE), traits (PERSONALITY, BACKGROUND, ...) — is multi-valued by design: a
character can have several friends, several nicknames, several personality traits at once, and
none of that is a conflict. `contradictions.py::build_graph` routes single-attribute claims to
`_resolve_single_valued`; everything else goes straight to `temporal.py::assign_multi_valued` with
no arbitration call at all. **Do not add relation-supersession** ("stopped being friends") without
a config flag to opt individual predicates into it — nothing in extraction.yaml currently asks for
it, and inventing it here would be a full phase early, same caution Phase 3's handover gave for
claim merging.

**Symmetric and inverse relation pairs are canonicalised to ONE storage direction, deterministically,
by predicate name.** `_canonicalize_relation` picks whichever of `{predicate, inverse(predicate)}`
sorts first alphabetically as the canonical predicate; for a symmetric relation it instead sorts
`(subject, object)` lexicographically. This closes the exact gap Phase 3's handover flagged
("Symmetric relations are extracted independently from both sides and not deduplicated... Phase
4's job") — verified for real: v01-02 actually contained a `(shin, FRIEND_OF, raiden)` /
`(raiden, FRIEND_OF, shin)` pair from independent per-character extraction, and it collapsed to one
edge. **The canonical direction is an implementation detail, not a contract** — CONTRACTS §4 does
not name a direction — so a query for "X's relations" must check `subject = X OR object = X` for
predicates with an `inverse`/`symmetric` flag; `graph/ppr.py` (Phase 5) needs to know this or it
will silently miss half the edges touching a given entity.

**A same-volume group with more than 2 conflicting values only arbitrates the top 2 by
confidence.** `claim_id` merging in `extract/claims.py` already guarantees every claim in a
`(subject, predicate, first_vol)` group has a genuinely distinct value (identical values already
share a `claim_id`), so ">2" means 3+ actually different extracted values for one attribute in one
volume — rare, and never occurred in the real v01-02 run. The 3rd+ entries are logged as a
`rule:lowest_confidence_dropped` conflict without an LLM call, to avoid chaining N-1 arbitration
calls for what is very likely one clearly-wrong outlier among the low-confidence entries. If a
future real run on more volumes shows this happening often with a non-obvious outlier, revisit —
right now it is an unexercised, deliberately cheap default, not a validated design.

**`state_at`/`history_at` return rows whose `vol_end` can be in the future relative to the query's
`vol`.** This is correct for *which rows are true* (an interval closing at volume 8 is still true
at a cutoff-3 read), but a row's raw `vol_end` field must never be printed verbatim by a renderer
at a cutoff earlier than that `vol_end` — doing so tells a Volume-3 reader that this fact changes
at Volume 8, before they have read Volume 8. **This is Phase 5's responsibility, not something
`temporal.py` enforces** — `state_at` is documented (see its docstring) as answering "is this row
true", not "which of this row's fields are safe to show". `synth/assemble.py` must scrub
`vol_end`/`superseded_by` down to "changes later" (no number) rather than pass the real value
through, or `tests/test_spoiler_leak.py`-style leakage happens one field at a time instead of one
whole claim at a time.

**`quiet_change` (extraction.yaml `conflicts:` block: AGE/RANK/TITLE/OCCUPATION) is read by
NOTHING in this phase.** Every cross-volume value change is logged as a `narrative_change`
conflict identically regardless of predicate — the "don't show this as a flashy UI change badge"
behavior `quiet_change` names is a rendering decision, deferred to whatever Phase 5 module builds
the "this changed" marker; it should read `settings.conflicts_config["quiet_change"]` directly
against an interval's `predicate` rather than expecting `contradictions.json` to carry a flag for
it (it does not, and should not — the conflict itself is not "quiet", only its rendering is).

**`graph build` has no `--force` and always fully rebuilds.** Unlike `ingest`/`gazetteer`/`extract`
(which skip a volume whose output file already exists), the graph has one combined output computed
fresh from `data/03_claims/*.jsonl` every time — cheap (all-local except the rare `arbitrate` call,
which is itself LLM-cached) and, critically, *must not* be incremental: a claim removed or changed
upstream has to actually disappear from `intervals`/`edges`, which `INSERT OR REPLACE`-by-key alone
cannot guarantee. `cli.py::graph_build` calls `store.reset(conn)` unconditionally before writing.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Only `single: true` attributes get conflict/supersession handling | Matches extraction.yaml's own documented semantics exactly ("single: true... makes rank promotions render as history rather than a contradiction"); relations/traits/non-single attributes are legitimately multi-valued | Detecting a "conflict" whenever any two claims share `(subject, predicate, first_vol)` with different values — would misfire on every character with two friends, two nicknames, or two personality traits |
| Canonical relation direction chosen deterministically by predicate/subject-object sort order | Fully general — one rule handles every symmetric and inverse pair in extraction.yaml with no per-predicate special-casing, and is a pure function of the config, not of extraction order | Picking canonical direction by whichever claim was extracted/written first — nondeterministic across reruns, and wrong to depend on iteration order for something that must be stable in the DB |
| Top-2-by-confidence arbitration for a >2-way same-volume conflict, rest rule-dropped | Keeps `_resolve_pair`'s schema and prompt binary (matches PROMPTS.md's own framing: "two same-volume claims disagree"); >2 genuinely distinct values for one attribute in one volume is rare and unexercised | An N-way arbitration prompt/schema — real complexity for a case that did not occur in the actual v01-02 run; add it if a larger run shows it matters |
| `flag`/`keep_both` on a single-valued attribute still picks a provisional value (highest confidence) for interval-building, while the conflict itself is still logged with `resolution: "flag"`/`"keep_both"` | CONTRACTS §4.2's "never silently pick a winner" is about not hiding the conflict, not about halting the whole graph build over one ambiguous attribute; the audit report surfaces every flagged item for a human | Leaving a gap in the interval sequence, or refusing to build the graph — either breaks every other subject/predicate in the same run over one ambiguous case |
| `graph build` unconditionally resets and rebuilds; no `--force` flag | The output is one combined artifact computed fresh from claims every time, not per-volume files that are expensive to redo; `INSERT OR REPLACE` alone cannot delete a stale row for a claim that no longer exists | A `--force` flag mirroring `ingest`/`gazetteer`/`extract` — would invite a "skip if `graph.db` exists" default that goes stale the moment claims change |

## What Phase 5 must do

Build `synth/assemble.py` (the page model, CONTRACTS §5) and `graph/ppr.py` (multi-hop evidence via
Personalized PageRank over the volume-filtered subgraph — CLAUDE.md file map). Read
`docs/CONTRACTS.md` §5 before writing anything.

Useful things this phase leaves behind: `graph/temporal.py::state_at(conn, entity_id, vol)` /
`history_at(conn, entity_id, vol)` are exactly the two queries CONTRACTS §5's page model needs —
call them, do not re-query `intervals` by hand. Remember the future-`vol_end` scrub noted above.
For relations, remember a symmetric/inverse predicate's edge may be stored with this entity as
`object`, not `subject` — `state_at`/`history_at` already filter on `subject = entity_id` only, so
a page renderer building "this character's relations" from `edges` (for PPR or a relations list)
must query both directions itself.

## Known gaps, deliberately left

- Relation intervals never close — no "the friendship/command relationship ended" modelling.
  Matches CONTRACTS §4's `edges` being described as static PPR input, but is not yet written down
  as a limitation anywhere else; noting it here is that.
- A same-volume group with more than 2 distinct values only arbitrates the top 2 by confidence
  (see notes above) — unexercised against real data, since it never occurred in the real v01-02
  run.
- `graph/ppr.py` is not built in this phase — it is filed under Phase 5 in CLAUDE.md's own file
  map (multi-hop evidence for `explain`), and the Phase 3 handover's "what Phase 4 must do" section
  only asked for `graph/{store,temporal,contradictions}.py` + `wiki audit contradictions`, both of
  which now exist.
- `quiet_change` is read by nothing yet (see notes above) — Phase 5's rendering layer needs to read
  it directly from `extraction.yaml`, not expect it echoed into `contradictions.json`.
