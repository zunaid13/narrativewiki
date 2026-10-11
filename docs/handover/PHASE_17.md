# Phase 17 — Value canonicalization + relation-conflict arbitration

**Status:** Complete · **Started:** 2026-09-04 · **Finished:** 2026-09-04

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## Why this phase exists

`docs/vision/PHASE_17.md`'s "Fandom-grade depth" entry (2026-09-04) named Phase 17 first among
five depth phases (17-21), specifically **before** any of them add more extraction volume:
"depth multiplies duplicates." Two problems, measured against this project's own real output
(Holo, Spice and Wolf v01-v02): ~40 near-duplicate APPEARANCE fragments for one character, and a
simultaneous `FRIEND_OF`/`ENEMY_OF` pair on the same relationship. Neither is fixed by a bigger
model — the unit of extraction (a ±2-paragraph window) means the same fact gets rephrased across
many windows, and nothing before this phase ever compared two DIFFERENT relation predicates
against each other for the same pair. Two deliverables:

1. **Value canonicalization** — cluster near-duplicate free-text values (multi-valued attributes
   + traits) via local bge-m3 embeddings, elect one canonical form, merge before rendering.
2. **Relation-conflict arbitration** — config-declared mutually-exclusive relation predicates
   (`FRIEND_OF`/`ENEMY_OF`) arbitrate same-volume, supersede cross-volume — closing the
   "relation edges never close" gap for exactly this case.

## What exists now

```
config/models.yaml
  New `canonicalize -> embed` entry under `routing:`. The `embed` profile (bge-m3) already
  existed (added 2026-09-03) but nothing could call it -- this wires it up. No fallback: embed
  calls are always local/free by construction.

config/extraction.yaml
  New `canonicalize:` block: `enabled` (default true), `similarity_threshold` (0.86, bge-m3
  cosine), `min_group_size` (2 -- below this, no embed call is worth making).
  `relations.FRIEND_OF`/`ENEMY_OF` each gained `conflicts_with: [the other]` -- the ONLY declared
  conflict pair. Deliberately not RIVAL_OF: "friendly rivals" and "hated rivals" are both
  unforced readings, so declaring it a hard conflict would invent a bigger taxonomy than the
  corpus evidence justifies. A predicate only joins a conflict group when BOTH sides declare each
  other back (same one-sided-mistake tolerance `symmetric`/`inverse` already have).

src/narrativewiki/llm/providers/base.py
  New `Embedding` dataclass: `vectors: list[list[float]]`, `in_tokens: int`.

src/narrativewiki/llm/providers/ollama.py
  New `embed(profile, texts, timeout) -> Embedding`, POSTing `{"model", "input": texts}` to
  `/api/embed` -- one HTTP call for a whole batch. Same error-handling shape as `complete`
  (ConnectError/ReadTimeout/404/>=400/`"error"` key -> ProviderError with an actionable message).

src/narrativewiki/llm/client.py
  New `LLMClient.embed(stage, texts) -> list[list[float]]`. Per-TEXT disk caching (reuses the
  existing `LLMCache`/`make_key` machinery unchanged -- one input text is the "prompt", the key
  gains `{"_embed": True}` in its options so an embed cache entry can never collide with a real
  completion's cache entry for the same text): every miss is batched into ONE provider call. No
  budget/frontier-scope check (the only role ever routed to `embed` is local/free by
  construction -- unlike `complete`/`complete_json`, which any stage could in principle route to
  a paid tier). If `self.run` is set, ONE compact `calls.jsonl` line per `embed()` call (text
  count + cache-hit count), not one per text -- keeps the run log light for what could be a
  hundred-plus small groups in a real build. A provider with no `embed` attribute (every provider
  except ollama today) raises `LLMError` naming the stage, never a silent empty-vector return.

src/narrativewiki/graph/canonicalize.py  (NEW)
  `cosine(a, b) -> float` (pure Python, no numpy dependency exists in this project and group
  sizes are small enough O(n^2) is fine) and `cluster_values(entries, embed_fn, threshold,
  min_group_size) -> list[Cluster]`. Buckets by `temporal.normalize_value` first (exact
  case/whitespace duplicates merge at zero embed cost, matching the merge rule
  `assign_multi_valued` already documents but does not itself apply). Below `min_group_size`
  distinct values, OR `embed_fn is None` (embed model unreachable): returns one cluster per
  distinct normalized value, no embedding call made -- canonicalization degrades to a no-op, a
  `graph build` never crashes or drops a value for lack of a pulled bge-m3. Otherwise: one greedy
  pass over values sorted (confidence desc, first_vol asc) -- each value joins the first existing
  cluster whose representative cosine similarity crosses `threshold`, else starts a new cluster.
  `Cluster.canonical` = `members[0]["value"]` (the sort makes this the highest-priority member).

src/narrativewiki/graph/temporal.py
  New `assign_relation_supersession(subject, obj, ordered_predicates) -> list[interval]` --
  structurally `assign_single_valued` with `predicate` varying per entry instead of fixed,
  `object` fixed, `value` staying null (the existing relation-interval convention). The one
  exception to "relation intervals never close," scoped to conflict-group members only.

src/narrativewiki/graph/contradictions.py
  `build_graph()` gained two new code paths, both additive to the existing structure --
  single-valued attribute handling is completely untouched.
  (1) Canonicalization: for every non-single-attribute/trait `(subject, predicate)` group
      (`other_claims`, same grouping as before), a new `_run_canonicalization()` clusters the
      group's values via `canonicalize.cluster_values` (embed_fn wraps `client.embed`, or `None`
      if `client` is `None`/lacks `.embed`) and returns a `claim_id -> canonical value` remap,
      applied to each observation's `value_or_object` BEFORE `assign_multi_valued` is called.
      That function's own exact-string dedup then does the actual interval merge, completely
      unchanged. Non-singleton merges are recorded into a new `canonicalization_merges` list,
      which becomes `contradictions_doc["canonicalization"]`.
  (2) Relation arbitration: `_relation_conflict_groups(relations_cfg)` computes predicate ->
      conflict-group-members once (union-find over `conflicts_with`, requiring both sides
      declared). Relation claims are partitioned: a `(subject, object)` pair with claims under
      >=2 of a conflict group's predicates goes to `pair_claims`, routed through the new
      `_resolve_relation_group` (arbitrates same-volume ties by reusing `_resolve_pair` UNCHANGED
      via a pseudo `{"value": predicate, "confidence", "evidence", "claim_id"}` dict -- no new
      arbitrate prompt was written; the existing one already asks "which fact is correct" and a
      relation choice fits the same shape); cross-volume predicate changes supersede via
      `temporal.assign_relation_supersession`. A pair with only ONE conflict-group predicate ever
      present falls through to the ordinary `assign_multi_valued` path unchanged -- nothing to
      arbitrate. Everything else (the overwhelming majority of relation claims) is completely
      unaffected -- `conflict_groups` is empty unless a series' config declares `conflicts_with`.
  New `_relation_conflict_record()` mirrors `_conflict_record()`'s shape but with a joined
  `"predicate": "A|B"` and each side carrying its own `predicate` (plus a `value` alias so the
  audit report's existing `c["a"]["value"]` read still works unchanged for relation conflicts).
  `build_graph()`'s module docstring rewritten to describe both new paths.

docs/CONTRACTS.md
  Section 4.1: new paragraph on the "relation edges never close, except conflict-group members"
  exception. Section 4.2: new "Relation conflicts" paragraph (the `predicate: "A|B"` / per-side
  `predicate` shape) and new "Value canonicalization" paragraph (the `canonicalization` doc key,
  full JSON shape, and "merge already baked into intervals/graph.db, not a pending action").

src/narrativewiki/audit/reports.py
  `_contradictions_report()` gained a canonicalization print block (predicate table + up to 10
  worked examples), reading `doc.get("canonicalization", {})` -- absent entirely for a
  pre-Phase-17 contradictions.json, prints nothing, never crashes. Relation-conflict resolutions
  needed NO new code: they land in the existing `conflicts` list and already show up in the
  existing "Conflicts by predicate"/"Resolutions" tables.

USER_GUIDE.md
  `wiki graph build`'s section gained two sentences describing both automatic behaviors -- no new
  CLI flags exist for this phase.

tests/test_llm.py, tests/test_graph.py, tests/test_config.py, tests/test_audit_reports.py
  29 new tests. See the "Status: Done" paragraph of docs/vision/PHASE_17.md's built entry for the
  full breakdown. Full suite: 336 passed (307 before this phase).
```

## Verify it in one command

```bash
python -m pytest            # 336 passed (307 before this phase + 29 new)
```

Live, actually run in this session against the real Spice and Wolf v1-2 claims (not just
fixtures): `wiki graph build --series spice-and-wolf` → `wiki doctor --series spice-and-wolf` →
`wiki audit contradictions --series spice-and-wolf` → `wiki synthesize --series spice-and-wolf
--upto 2` → `wiki site build --series spice-and-wolf --upto 2` → `wiki audit links`/`wiki audit
pages`. All clean. Real results, not illustrative: canonicalization merged 9 near-duplicate value
groups (10 variants absorbed) — including, confirmed by name, the exact Holo APPEARANCE
near-duplicates Phase 9's handover flagged as an open finding ("wolf's ears" + "wolf ears and a
tail" → "wolf's ears and tail"; "harvest god" → "the god of abundant harvests"; etc.). Relation
arbitration produced real `FRIEND_OF|ENEMY_OF` conflicts for Holo/Liebert, one correctly flagged
for human review ("neither passage clearly establishes a definitive relationship").

**Two real bugs were caught and fixed by this live run, not by the unit tests** (both fixtures
were too clean to reproduce them):
1. `LLMClient.embed()` did not translate a provider's `ProviderError` into `LLMError` the way
   `_call` does — an unreachable Ollama crashed `graph build` outright instead of degrading.
   Fixed: `embed()` now does the same `ProviderError -> LLMError` translation, and
   `graph/contradictions.py::_run_canonicalization` catches it, falling back to exact-match-only
   canonicalization for the REST of the run too (a sticky `embed_state["unavailable"]` flag,
   shared across every `(subject, predicate)` group in one `build_graph()` call) — so one dead
   connection doesn't retry hundreds of times across a real build.
2. `_resolve_relation_group`'s per-volume logic compared the top-two claims BY CONFIDENCE ALONE
   without first collapsing same-predicate claims — real data had Holo/Liebert's ENEMY_OF
   extracted independently from both directions (two claim_ids, same canonical predicate, same
   volume) alongside a genuine FRIEND_OF claim, and confidence ranking could put two ENEMY_OF
   claims in the top two, producing a nonsensical `"ENEMY_OF|ENEMY_OF"` "conflict" and silently
   dropping the real FRIEND_OF claim as a lowest-confidence outlier. Fixed: claims are now
   collapsed to one representative PER PREDICATE per volume first (merging claim_ids, exactly
   mirroring how `assign_multi_valued` already merges same-predicate relation claims on the
   ordinary path) — only genuinely different predicates are ever compared. Confirmed by rerunning
   against real data: the spurious `ENEMY_OF|ENEMY_OF` row disappeared, conflict count dropped
   from 29 to 23 (the correct count), interval/edge counts unchanged.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Canonicalization remaps values UPSTREAM of `assign_multi_valued`, storing nothing new on intervals/`graph.db` | The core ask ("stop sibling bullets") is fully satisfied by fewer, cleaner values reaching the existing merge — no schema change, no `synth`/`site` change, smallest possible blast radius | Adding a `variants_json` column to `intervals` and threading it through `synth/assemble.py`/`site/okf.py`/`app.js` to render an expandable "also phrased as..." UI |
| `conflicts_with` requires BOTH predicates to declare each other | Matches the existing `symmetric`/`inverse` tolerance for a one-sided config mistake — silently not grouped, never a crash | A `ConfigError` on a one-sided declaration |
| Only `FRIEND_OF`/`ENEMY_OF` declared conflicting | The one pair the corpus (and the vision entry) actually evidenced; RIVAL_OF is a genuinely ambiguous word ("friendly rivals" is real) | Also declaring RIVAL_OF, SPOUSE_OF, etc. as conflicts of ENEMY_OF |
| Relation same-volume arbitration reuses `_resolve_pair` via a pseudo `{"value": predicate, ...}` dict | No new arbitrate prompt needed — the existing "which fact is correct" framing already fits "which relation is correct" | Writing a second, relation-specific arbitrate prompt |
| Embeddings cached per-TEXT (not per-group) via the existing `LLMCache` | A surface form re-embedded across many different `(subject, predicate)` groups (or reruns) is a cache hit, not a re-embed — same infra, zero new cache code | A dedicated embedding cache file/format |
| `embed()` has no budget/frontier-scope check | Every role ever routed to `embed` is local/free by construction (only the `embed` profile exists for it); adding the check would be dead code | Reusing `_call`'s full machinery unchanged, including budget/frontier checks |

## Known gaps, deliberately left for later phases

- **No UI surfacing of merged variants** — see the decision above. A future phase (naturally
  Phase 20's per-section richness work) could add an expandable "also phrased as..." to a
  nickname/title/appearance bullet, reading `contradictions.json["canonicalization"]["merges"]`.
- **`single: true` attributes are not canonicalized** — AGE/STATUS/RANK/etc. already go through
  `_resolve_single_valued`'s same-volume arbitration and cross-volume supersession. Near-duplicate
  *wording* of a single-valued value across volumes (not the same as `normalize_value`'s
  case/whitespace fold) is a real but separate, untouched gap.
- **No general "relation edges can close" redesign** — only `conflicts_with` group members
  supersede. A character's `COMMANDS`/`AFFILIATED_WITH`/etc. edges still never close, exactly as
  before this phase (Phase 19's event layer is the more likely place a general fix belongs, if it
  ever gets built — anchoring interval closure to a narrative event rather than inferring it from
  predicate conflict).
- Phase 9's Holo Appearance near-duplicate finding is now **confirmed fixed** — see the live-run
  paragraph above. Nothing left to re-verify there.

## What Phase 18 needs

`docs/vision/PHASE_17.md`'s depth programme continues with **Phase 18** — chapter-major
extraction as a second pass (coverage becomes 100% by construction) + epithet alias mining. Phase
17 was named as a prerequisite specifically so Phase 18's extra volume doesn't just produce more
duplicate phrasings unchecked — nothing built here blocks it or needs revisiting for it. One thing
Phase 18 SHOULD reuse rather than reinvent: `LLMClient.embed()` and `graph/canonicalize.py` are
already general over "a group of free-text values for one subject" — a chapter-major pass emitting
scene beat summaries or quote records could route duplicate-detection through the same mechanism
if that need arises, rather than writing a second clustering implementation.
