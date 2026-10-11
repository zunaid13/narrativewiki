# Phase 5 — Pages (evidence layer)

**Closed:** 2026-09-02 · **Next:** Phase 6, Prose (`synth/prose.py`, `wiki synthesize`)

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

```
src/narrativewiki/graph/
  temporal.py   +relations_at(entity_id, vol)   -- relation intervals with entity as subject OR
                   object (canonical direction is independent of whose page is being built).
                +all_edges_at(vol)               -- every `edges` row visible at vol; the
                   whole-graph read graph/ppr.py needs (it does not call relations_at per entity).
                +evidence_at(claim_ids, vol)      -- claims.evidence filtered by EACH quote's own
                   para_id volume, not the claim's first_vol. See "Things you need to know" below
                   — this exists because the naive version leaked real evidence in this session.
  ppr.py        NEW. build_subgraph(conn, upto_vol) -> networkx.Graph (undirected, edge weight =
                   count of distinct relations between a pair). personalized_pagerank(conn,
                   entity_id, upto_vol, top_k=8) -> ranked related entities, seed excluded.
                   PageRank itself is a hand-rolled power iteration, NOT nx.pagerank() — see Gaps.
src/narrativewiki/synth/
  assemble.py    NEW. assemble_page(conn, entity, upto_vol, settings) -> CONTRACTS §5 dict, no
                   LLM. trait_values_at(conn, entity_id, upto_vol, traits_cfg) -> Phase 6's prose
                   input, NOT part of the page JSON.
src/narrativewiki/cli.py   explain() wired end to end (was a Phase-5-pending stub). Removed from
                   `_PENDING`. New `_find_character()` helper: exact id/canonical match, else
                   unique alias match, else unique substring match, else lists candidates and
                   exits 1.
tests/test_graph.py          +5 tests (relations_at x2, all_edges_at, evidence_at x2).
tests/test_ppr.py            NEW. 6 tests.
tests/test_synth_assemble.py NEW. 10 tests.
```

`docs/CONTRACTS.md` §5 and §4.1 were rewritten in the same commit — §5's old example showed
`titles`/`nicknames` as if they were special-cased field names; they are not (see below). §4.1 now
lists all five sanctioned graph.db reads, not just `state_at`/`history_at`.

## Verify it in one command

```bash
wiki explain shin --upto 2      # needs data/04_graph/graph.db + data/02_entities/gazetteer.json
python -m pytest                 # 155 passed
```

**This ran for real against the actual v01-02 graph.db** (Phase 3/4's real run, not a fixture):
`wiki explain shin --upto 1`, `--upto 2`, alias resolution (`wiki explain "Undertaker"` resolves to
`shin`), and a low-connectivity character (`wiki explain lena --upto 1`). All produced sane,
cutoff-correct output — see the spoiler-leak note below for what "cutoff-correct" caught.

## Things you need to know

**A claim's evidence can span multiple volumes; `first_vol` alone is not a safe filter for
printing quotes.** `extract/claims.py` merges repeated observations of the same fact (same
subject/predicate/object_norm/first_vol) into one `claim_id`, appending new evidence as later
volumes confirm it again. A claim with `first_vol = 1` can genuinely carry a `v02` quote. This is
correct and fine for the STRUCTURED value (the fact really was known since v01) — but the first
version of `wiki explain` in this session printed every quote attached to a claim regardless of
`--upto`, which leaked v02 dialogue into a `--upto 1` run. Found by running it against real data
and grepping the output for `v02`, not by inspection. Fixed by
`graph/temporal.py::evidence_at(claim_ids, vol)`, which checks each quote's own `para_id` volume.
**Phase 6's `synth/prose.py` must call `evidence_at`, not read `claims.evidence_json` directly**,
or it reproduces the exact same leak when building its prompt — this is the single most important
thing to carry into Phase 6.

**Page-model field keys are `predicate.lower()`, not a hard-coded name table.** CONTRACTS §5's
original example showed `"titles"`/`"nicknames"` as if TITLE/NICKNAME were special-cased; they
render generically like every other attribute (`fields["title"]`, `fields["nickname"]`).
`config/extraction.yaml`'s own header says "Adding a predicate or attribute here is all that is
needed — rendering is generic," which is the literal justification. The ONE exception is relations:
`AFFILIATED_WITH` (identified by predicate name, not a config flag) renders into
`fields["affiliations"]`; every other relation predicate renders into one `fields["relationships"]`
list (each entry carries its own `predicate`, so nothing is lost by not having one list per
predicate). If a future series' config adds a new attribute, it needs zero code changes to appear
on a page; if it adds a new *relation* predicate that deserves its own field the way
`AFFILIATED_WITH` does, that DOES need a code change here — there was no time pressure to
generalize that one exception, and CONTRACTS/CLAUDE.md both call out exactly two relation-driven
field names, so it stayed as the two-bucket split rather than inventing a config flag nothing asks
for yet.

**A currently-open interval's real `vol_end`/`superseded_by` must never reach the page JSON when
it's still in the future relative to the cutoff.** `assemble.py` exposes this as a boolean instead:
a scalar attribute field gets `changes_later: true/false`; an affiliation gets `current: true/false`
plus a `vols` pair whose second element is `null` until the close is actually revealed. This was
Phase 4's handover's explicit instruction (`state_at`'s own docstring: "That scrub is
synth/assemble.py's job") and is covered by
`test_synth_assemble.py::test_scalar_field_scrubs_future_vol_end_and_reports_changes_later`, which
asserts the real number (`"5"`) does not appear anywhere in the field's repr at all, not just that
`changes_later` is set correctly.

**`nx.pagerank()` needs scipy, which is not installed and not a declared dependency.** Discovered
by running `wiki explain` for real, not by reading networkx's docs — the installed networkx (>=3.2)
only ships the scipy-backed implementation of `pagerank()`. Rather than adding a new dependency for
a graph of a few hundred nodes at most, `graph/ppr.py::_personalized_pagerank_scores` is a
hand-rolled pure-Python power iteration (standard formulation: restart to the seed on every jump,
alpha=0.85, L1-convergence at 1e-10 or 100 iterations). If a much larger run ever makes this slow,
either add scipy properly (pyproject.toml + `wiki doctor`) or vectorize with numpy (already an
indirect dependency, per the traceback that surfaced this) — do not silently start calling
`nx.pagerank()` again, it will break the same way.

**`assemble_page()` does not write anything to disk.** It is a pure function returning a dict.
`data/05_pages/` still does not exist — `wiki explain` uses the dict in memory for display only.
Phase 6's `wiki synthesize` is what calls `assemble_page()`, adds prose, checks `claim_set_hash`
against whatever the previous cutoff wrote, and actually writes `data/05_pages/<id>/v<NN>.json`/
`.md`.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Field keys are `predicate.lower()`, generic over `config/extraction.yaml` | That file's own header says rendering is generic; a hard-coded name table breaks the moment a new series' config adds an attribute (series-agnostic requirement) | A fixed name table matching CONTRACTS' old example (`titles`, `nicknames`, ...) — matches the illustrative doc exactly but silently drops any attribute not in the table |
| `AFFILIATED_WITH` is the one relation predicate identified by name, not by a config flag | CONTRACTS/CLAUDE.md both name exactly two relation-driven fields (`affiliations`, `relationships`); no config flag exists to generalize this, and inventing one nothing asks for is exactly the premature-abstraction Phase 3/4's handovers already cautioned against | A generic `relations.<PRED>.field: affiliations` config flag — real complexity for a two-item split |
| `mentions_of` is populated directly from `graph/ppr.py`'s ranked output | PPR existed only as an unused file-map bullet; `mentions_of` was an unfilled CONTRACTS field; pairing them is the only concrete use either one has at this phase | Leaving `mentions_of` empty until Phase 7's wikifier can scan generated prose — defers a decision Phase 5 can make cleanly now, and Phase 7 can still layer wikified-prose mentions on top later without conflict (this list is additive, not exclusive) |
| PageRank hand-rolled as pure-Python power iteration | `nx.pagerank()` requires scipy, not installed/declared; graphs here are a few hundred nodes at most — a new heavy dependency is not worth it for this scale | Adding scipy to pyproject.toml + wiki doctor — legitimate if this ever becomes a bottleneck, not needed now |
| `evidence_at` filters each quote by its own para_id volume, added as a fifth sanctioned `graph/temporal.py` read | Found a real leak this way; centralizing it (rather than fixing it inline in `cli.py::explain`) means Phase 6's prose stage gets the fix for free instead of reintroducing the same bug independently | Fixing the filter only inside `cli.py::explain`'s closure — would have "worked" for this phase and quietly broken again in Phase 6 |

## Known gaps, deliberately left

- Relation intervals still never close (Phase 4's known gap, unchanged) — `relations_at`'s scrub
  logic for a closed-but-not-yet-revealed relation is written and tested
  (`test_synth_assemble.py`), but nothing in real data exercises it yet.
- `assemble_page()`'s `fields` ordering follows `settings.attributes` iteration order (a Python
  dict, so config file order) for attributes, and interval `vol_start` order within a list field —
  not alphabetical. Not a contract violation (CONTRACTS §5 doesn't mandate an order), just worth
  knowing if a future diff looks like fields "moved" for no code reason after an extraction.yaml
  edit.
- `wiki explain`'s "~N evidence tokens" estimate is `len(quote_chars) / 4`, a rough heuristic, not
  a real tokenizer call — good enough for "does this look too big before Phase 6 spends real
  tokens," not for budget accounting (that's `llm/budget.py`'s job once Phase 6 actually calls a
  model).
- No `wiki audit pages` yet — `paths.STAGE_DIRS["pages"]` and `wiki status`'s "pages" row already
  exist from earlier phases, but there is still nothing to audit until Phase 6 writes files there.
- **`quiet_change` (extraction.yaml `conflicts:` block) is still read by nothing.** Phase 4's
  handover flagged this as "Phase 5's rendering layer" work. It is deliberately still not read
  here: CONTRACTS §5 defines no "this field just changed" marker for `assemble_page()` to set —
  the closest thing, `changes_later`, means "will change in the future relative to this cutoff,"
  the opposite direction from `quiet_change` ("a change that already happened, don't badge it").
  Whatever actually renders a "changed!" badge is a Phase 7 SPA concern, and it can read
  `quiet_change` directly against a field's predicate name (trivially: field key `"rank"` ->
  `"RANK"` -> `settings.conflicts_config["quiet_change"]`) without needing it echoed into the page
  JSON at all — so this is deferred to Phase 7, not forgotten. Reconsider only if Phase 6/7 turns
  out to need it earlier than expected.
