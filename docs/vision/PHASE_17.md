# docs/vision/PHASE_17.md — VISION entries for Phase 17-21 — Fandom-grade depth programme

Split out of the root `VISION.md` (see `CLAUDE.md` §4) so the index stays cheap to read.
Same append-only rule applies: new entries for this phase append at the bottom; nothing here
is ever rewritten. Entry format is defined in `VISION.md`.

---

## 2026-09-04 — Fandom-grade depth: the ceiling is the ontology, not the model (Phases 17-21)

**What:** Raise generated pages from their current ~8-sentences-plus-a-bullet-list shape to the
depth of a mature Fandom wiki (the *Overlord* wiki was named as the target). Five phases, in
dependency order: **17** value canonicalization + relation arbitration, **18** chapter-major
extraction as a second pass + epithet aliases, **19** an event/narrative layer in the graph,
**20** outline-driven multi-section page planning, **21** cross-entity pages + an evaluation
harness. This supersedes nothing; it is the depth axis the six-phase redesign (2026-09-03) did not
cover, and Phases 14/15 of that plan are absorbed into 17 and 21 respectively.

**Why — measured, not assumed.** Four numbers taken from the real Spice and Wolf v01-v02 output
and from running `extract/windows.py` against the live mention index:

1. **Extraction yield:** two entire novels produce 255 claims / 573 evidence quotes across 26
   predicate types. Holo, a co-lead, has 91 claims total. A Fandom character page carries on the
   order of 500-2000 discrete assertions for *one* character.
2. **Coverage:** for Holo in v01, 517 paragraphs contain a mention and cluster into 135 windows;
   `max_windows_per_entity_per_volume: 40` sends 40 of them. The extractor reads **33.6%** of the
   volume's 2,587 paragraphs about its own main character (62.8% if uncapped). Lawrence: 56.6%
   sent, 87.5% available. Discarded windows are chosen by mention count, so the quiet
   character-development scenes are exactly the ones dropped. This is on top of the pronoun- and
   epithet-only scenes Aho-Corasick cannot see at all.
3. **Predicate mass:** 60 of 255 claims are APPEARANCE and 26 are FRIEND_OF. The schema's weight
   sits on timeless entity properties.
4. **Schema shape:** `config/extraction.yaml` is 9 attributes + 5 traits + 22 relations. Every one
   is a property of an *entity*. None is a property of *something that happened*.

A mature Fandom page spends most of its bytes on event-level narrative — Chronology (per-volume
plot from that character's vantage), Abilities with mechanics, a multi-paragraph Relationships
essay per person, Quotes, Trivia, per-chapter Appearances. **The data model has no slot for any of
it.** `EVENT` exists as a gazetteer *entity type* (a battle with a proper name — 86's whole
gazetteer found 2 of them among 163 entities), not as a narrative unit with participants, causality
and time. There are no scene records, no beat summaries, no per-chapter plot, no quote records, no
state-change events.

This is why a stronger model does not fix it, and this is the decision being recorded: **model
capability is ranked fourth of five causes, and finetuning is rejected outright.** Point a frontier
model at this pipeline and it fills the same 26 slots with better sentences. The unit of extraction
(a +/-2-paragraph mention window) is also *smaller than the unit of the fact* — a plot arc, a
motive, a consequence spans a chapter, so no window-scoped call emits one at any model size. Second
confirmation from this project's own output: Holo's ~40 near-duplicate APPEARANCE fragments and her
simultaneous `Enek — Friend of` / `Enek — Enemy of` rows are missing *stages*, not missing
intelligence.

**Finetuning is rejected**, for the record, so it is not re-proposed: (a) it needs thousands of
(passage -> claim) pairs from this corpus that do not exist and would cost more to build than the
project; (b) the failure modes are structural — no slot, no coverage, no dedup — and weights fix
none of them; (c) a finetuned 14B's literary-synthesis ceiling still sits below a frontier model's
zero-shot; (d) decisively, it fights CLAUDE.md §1 — finetuning moves knowledge *into weights*,
where it carries no `first_vol` and cannot be spoiler-scoped. The one defensible future use is
distilling frontier claim-extraction into a local model to cut bulk cost: a cost optimization,
never a quality one.

**Implies:**

- **Phase 17 — canonicalization first, because depth multiplies duplicates.** Embed all values for
  one `(subject, predicate)` with `bge-m3` locally (`llm/providers/ollama.py` still needs the
  `/api/embed` path noted on 2026-09-03), cluster, elect one canonical surface form, keep the rest
  as `variants` carrying their own evidence rather than as sibling bullets. Route contradicting
  relations on the same pair through `arbitrate` as either a temporal transition or an extraction
  error. Zero API cost. Do this before anything else so later changes can be judged.
- **Phase 18 — chapter-major extraction as a SECOND pass, not a replacement.** Read every chapter
  end to end in overlapping ~4k-token spans, emitting scene records: participants, location, beat
  summary, state changes, attributed quotes. Coverage becomes 100% by construction and the pronoun
  problem largely dissolves without a coreference model, because a whole-chapter span carries its
  own antecedents. The existing mention-major pass stays for precise slot-filling. The 40-window
  cap is then replaced by a per-chapter budget, which is naturally bounded. Also: mine epithet
  aliases ("the wisewolf", "the merchant") into the gazetteer so the automaton sees them. Bulk
  cost is ~1.6M input tokens for 13 volumes — free on Ollama, a few GPU-hours.
- **Phase 19 — the event layer.** A narrative node anchored to `(vol, chapter_idx, para span)` with
  participants and roles; new claim kinds `event`, `state_change` (X->Y *at event E*), `quote`
  (speaker, addressee, para_id), `mechanic`. Intervals anchor to `event_id`, not only
  `vol_start`/`vol_end`. Note that claims **already carry `chapter_idx`** (see any row of
  `data/*/03_claims/v01.jsonl`) and `graph/temporal.py` discards it at the interval layer — the key
  chronology needs is being thrown away today.
- **Phase 20 — outline-driven pages, retiring the six hardcoded sections in `site/okf.py`.** Each
  section is a separate generation with its own graph retrieval query, its own evidence set, and
  its own length budget scaled to evidence volume, replacing the global 2-4 sentence cap in
  `extraction.yaml`'s `prose:` block. **CLAUDE.md §1 survives unchanged and is not weakened:** every
  section is still generated from an already-cutoff-filtered set; the invariant simply applies per
  section instead of per page. This is what turns 8 sentences into a full page without raising
  hallucination risk.
- **Phase 21 — cross-entity pages + evaluation.** Relationship pages (pair-scoped subgraph + shared
  scenes), faction pages, per-volume timeline pages; `graph/ppr.py` currently feeds only
  `mentions_of` and gets repointed at per-section retrieval. Evaluation is not optional — depth and
  hallucination are indistinguishable from the inside: hand-transcribe the fact list and outline
  from three real Fandom pages, then measure heading recall, fact recall, and citation entailment.
- **Routing:** chapter-major pass local; section synthesis frontier-tier, cached on a *section*-
  evidence hash (a far better hit rate than the current page-level `claim_set_hash`, where one new
  fact invalidates a whole page). Phase 10's frontier interlock bounds dev spend.

**A limit to state plainly, so it is not rediscovered as a failure:** the Overlord wiki cannot be
equalled from EPUBs alone. A large share of it is out-of-band — author interviews, anime-adaptation
differences, release dates, image galleries, community trivia. The reachable target is *parity with
its novel-derived content*, which is still a 10-20x depth increase over today's output.

**Status:** Planned — Phases 17-21. Nothing implemented.

---


## 2026-09-04 — Per-series extraction schemas and CLI schema tuning; depth must never become series-specific

**What:** The depth programme above must not buy richness by hard-coding one series' concepts.
Two mechanisms, and one standing rule.

1. **Per-series schema overlay.** `config/extraction.yaml` stays the universal base (the concepts
   every narrative has: age, gender, status, kinship, affiliation). A new optional
   `config/extraction.<series>.yaml` is deep-merged over it, holding only what that series needs —
   `KARMA: { single: true, format: short_text, display: "Karma" }` for Overlord, a magic-system
   attribute for another series, `RACE`/`LEVEL`/`JOB_CLASS` and so on.
   `paths.extraction_config()` takes a series id; `load_settings(series_id)` merges base + overlay.
2. **CLI schema tuning**, so a run can be narrowed or widened without editing config at all — the
   same ergonomics as the existing `--model` override (Phase 8): repeatable
   `--attr KARMA=short_text:"Karma"` / `--trait` / `--relation` to add a predicate ad hoc, and
   `--only`/`--skip` (repeatable, accepting predicate names or the kinds `attribute`/`relation`/
   `trait`) to restrict what a given run extracts. Combined with the existing `--volumes` and the
   Phase 11 `--chapters` selector, this is what makes "volume 9 introduces a stat block, extract it
   only there" a command line rather than a code change.
3. **The standing rule:** no Phase 17-21 deliverable may name a series concept in `src/`. Every new
   section, predicate, or page kind is declared in config and rendered generically, exactly as
   attributes already are.

**Why:** The requirement is that the wiki adapt to whatever a series actually tracks — Overlord
characters need a Karma level rendered next to Gender and Affiliations — while the code stays
series-agnostic (2026-09-01 "Series-agnostic by construction"). Verified before writing this that
the attribute axis is **already** generic end to end, so this is a scoping problem, not a rewrite:
`extract/claims.py::_vocab_lines(settings.attributes)` builds the extraction prompt from config;
`_predicate_spec` validates against config; `synth/assemble.py::_build_attribute_fields` keys
fields by `predicate.lower()` for every configured attribute (the 2026-09-02 generic-fields entry);
`site/okf.py::_overview_lines` iterates `attributes_cfg`; and `site/bundle.py` ships a
`field_labels` map so `site/templates/app.js` renders with `for (var k in page.fields)`. Adding
`KARMA` to `extraction.yaml` today would already reach the rendered page with no code change.

The two genuine gaps are exactly what this entry fixes: (a) `paths.py::extraction_config()` takes
no series argument, so the taxonomy is **global** — an Overlord `KARMA` would enter 86's extraction
prompt vocabulary and Spice and Wolf's, spending tokens on a concept those series do not have and
inviting the model to invent one; (b) there is no runtime override, so every experiment costs a
config edit that is easy to forget and impossible to attribute in the Phase 10 run ledger.

**Implies:**

- `paths.extraction_config(series_id)` + a deep merge in `config.py::load_settings`, with the
  overlay able to *remove* a base predicate (an explicit `null` value) as well as add one — a
  series with no military ranks should not carry RANK into its prompts.
- The merged, effective taxonomy is per-run provenance: `provenance.py`'s manifest already hashes
  config files, and must hash the **merged** taxonomy plus any CLI overrides, so `wiki runs` can
  answer "which schema produced this claim set". Without that, ad-hoc `--attr` runs become
  unreproducible, defeating Phase 10's whole purpose.
- Phase 20's section outline is subject to the same rule: sections are a closed vocabulary declared
  in the extraction config (base sections universal; `Abilities`, `Karma`, `Chronology` per series),
  never a hardcoded list in `site/okf.py` or `app.js`.
- `wiki doctor` should print the effective taxonomy for the selected series (base + overlay + CLI),
  the same way it already prints the resolved routing table, and for the same reason: a silently
  wrong schema is otherwise only discovered by reading generated pages.
- `entities/classify.py`'s entity-type vocabulary and `codex_pages` are already config-driven and
  get the same overlay treatment for free once the merge exists (a series needing a `DEITY` or
  `SPELL` codex page declares it in its overlay).

**Status:** Planned — a prerequisite of Phase 17, not a follow-up to Phase 21: the overlay must
exist before any new predicate or section is added, or the first depth phase is what hard-codes a
series into `src/`.

---


## 2026-09-04 — Relation staleness when a mid-volume transition is never re-extracted

**What:** User-raised scenario, recorded as a second confirming data point for Phase 19's design
rather than a new deliverable. Phase 17's relation-conflict arbitration only closes a
`FRIEND_OF`/`ENEMY_OF` interval when BOTH predicates are independently extracted as claims
somewhere in the claim set (same-volume arbitration, or cross-volume supersession once the second
claim appears). If a friend turns enemy mid-volume and the passage that shows it is never sampled
into an extraction window at all — the mention-window cap already measured to discard exactly the
"quiet" low-mention-count scenes, per the coverage numbers in the entry above — no conflicting
`ENEMY_OF` claim ever enters the graph. Nothing to arbitrate against means the `FRIEND_OF` interval
stays open forever, and every later cutoff (volume N+1, N+2, ... even if the enmity is never
restated on-page again) renders the stale, backdated relation.

**Why:** This is a coverage/recall gap, not an arbitration gap. Phase 17 already handles "both
sides got extracted, which one wins." This is "only one side was ever extracted" — structurally
the same "missing stages, not missing intelligence" diagnosis made above for the near-duplicate
APPEARANCE/simultaneous-FRIEND_OF-ENEMY_OF findings, just for the opposite failure direction (an
edge that should have closed and didn't, instead of two edges open at once).

**Implies:** No new phase opened — this reinforces the two mitigations already planned, so it's
recorded here rather than as a new item:
- **Phase 18** (chapter-major extraction) directly raises the odds the transition passage is
  sampled at all: 100% coverage by construction vs. today's measured ~34% (Holo, v01) mention-window
  coverage under the 40-window cap.
- **Phase 19** (event layer) is the structural fix, already named as the target home for "a general
  relation-edge-closing redesign" in `docs/handover/PHASE_17.md`'s Known Gaps. A `state_change`
  claim (`FRIEND_OF -> ENEMY_OF` *at event E*) is a single explicit assertion of the transition
  itself — it closes the old interval unconditionally at extraction time and does not depend on a
  second, independently-extracted conflicting relation claim ever showing up later.
- **Residual ceiling Phase 19 cannot remove:** a transition that is genuinely never stated in the
  text (it happens off-page, between volumes) cannot be recovered by any extraction design. This is
  a corpus-coverage limit, not a pipeline bug — Phase 21's evaluation harness should name it as such
  rather than treat every stale relation it finds as a defect to chase.

**Status:** Noted. No code changes from this entry — folded into Phase 18/19 scope, which already
plan to address it.

---


## 2026-09-04 — Phase 17 built: value canonicalization + relation-conflict arbitration

**What:** Both deliverables from the "Fandom-grade depth" entry above, implemented, scoped
entirely inside `graph build` (`graph/contradictions.py::build_graph`) — no change needed to
`graph/store.py`'s schema, `synth/`, or `site/`, since canonicalization reduces the *input* to the
existing `assign_multi_valued` merge rather than adding a new output shape.

1. **Embedding infra**, the prerequisite the `embed` profile's own comment named as missing:
   `llm/providers/base.py::Embedding`, `llm/providers/ollama.py::embed()` (`/api/embed`, one
   batched HTTP call per group), `LLMClient.embed(stage, texts)` — per-text disk-cached via the
   existing `LLMCache`/`make_key` (an embedding's vector is just `json.dumps`'d into the same
   `CachedResponse.text` field a completion's answer would use), no budget/frontier-scope check
   (the only role ever routed to `embed` is local/free by construction), one compact run-log line
   per batch call rather than one per text. `config/models.yaml` gained a `canonicalize -> embed`
   routing entry — `wiki doctor` health-checks it for free via its existing generic `for stage in
   routing` loop, no doctor code change needed.
2. **`graph/canonicalize.py`** (new module): pure-Python cosine similarity + greedy single-pass
   clustering (no numpy/sklearn dependency exists in this project, and group sizes are small
   enough that O(n²) is fine). Buckets by `temporal.normalize_value` first — exact case/whitespace
   duplicates merge at zero embed cost — then embeds one representative per bucket only when
   `min_group_size` is met and an embed model is reachable; degrades to normalize-value-only
   bucketing otherwise (never crashes a `graph build`, never drops a value). Canonical form =
   highest-confidence, earliest-`first_vol` member of each cluster.
3. **Canonicalization wired into `build_graph`**: every multi-valued attribute/trait `(subject,
   predicate)` group is clustered and remapped to its cluster's canonical value *before*
   `assign_multi_valued` is called — that function's own exact-string dedup then does the actual
   merge, unchanged. Merge decisions are recorded in a new `contradictions.json["canonicalization"]`
   key (CONTRACTS §4.2) for provenance/audit, printed by an extended `wiki audit contradictions`.
4. **Relation-conflict arbitration**: `config/extraction.yaml` `relations.*.conflicts_with`
   (declared symmetrically, `FRIEND_OF`↔`ENEMY_OF` only — deliberately not `RIVAL_OF`, see the
   config comment on why a bigger fictional taxonomy than the corpus evidence justifies was
   rejected). A `(subject, object)` pair with claims under ≥2 of a conflict group's predicates
   routes through the new `_resolve_relation_group` — same-volume ties reuse `_resolve_pair`
   unchanged via a pseudo `{"value": predicate, ...}` dict (no new arbitrate prompt needed);
   cross-volume predicate changes supersede via the new `temporal.py::assign_relation_supersession`
   (structurally `assign_single_valued` with `predicate` varying per entry instead of fixed) —
   this is the one exception to "relation edges never close" (CONTRACTS §4.1), scoped to
   conflict-group members only.

**Why this order:** exactly the vision entry's own framing — "depth multiplies duplicates... do
this before anything else so later changes can be judged." Phases 18-21 add extraction volume;
this phase makes sure more volume produces more distinct *facts*, not more distinct *phrasings of
the same fact* or silently-coexisting contradictory edges.

**Deliberately out of scope** (named so it is not rediscovered as a gap):
- Surfacing merge/variant provenance on the rendered page itself — the core ask ("stop sibling
  bullets") is fully satisfied upstream at the graph-merge step; an expandable "also phrased
  as..." UI is presentation work that fits Phase 20's per-section richness work, not this one.
- Canonicalizing `single: true` attribute values — those already go through
  `_resolve_single_valued`'s same-volume arbitration and cross-volume supersession; near-duplicate
  *wording* of a single-valued attribute across volumes is a real but separate gap, untouched here.
- A general "relation edges can close" redesign — only `conflicts_with` group members supersede;
  every other relation predicate keeps the original permanently-open-interval behaviour.

**Status:** Done, and real-data verified — not just fixtures. Live against Spice and Wolf v1-2:
`graph build` → `doctor` → `audit contradictions` → `synthesize` → `site build` → `audit links`/
`pages`, all clean. Canonicalization merged 9 real near-duplicate value groups (10 variants),
including Phase 9's specifically-flagged Holo APPEARANCE near-duplicates by name — that finding is
now closed. Relation arbitration produced real `FRIEND_OF|ENEMY_OF` conflicts for Holo/Liebert,
one correctly flagged for human review rather than guessed. This live run caught two real bugs no
fixture reproduced: `LLMClient.embed()` wasn't translating `ProviderError` into `LLMError` (an
unreachable Ollama crashed `graph build` instead of degrading — fixed, plus a sticky per-run flag
so a dead connection isn't retried once per `(subject, predicate)` group); and
`_resolve_relation_group` compared claims by confidence alone without first collapsing
same-predicate duplicates, so a relation extracted independently from both directions in one
volume (real: Holo/Liebert's ENEMY_OF) could rank two same-predicate claims into the "top two,"
producing a nonsense `"ENEMY_OF|ENEMY_OF"` conflict and silently dropping the real conflicting
claim as an outlier — fixed, confirmed by rerun (conflict count corrected 29 → 23, intervals/edges
unchanged). New tests (29 total): `tests/test_llm.py` (ollama `embed()` request shape + error
path, `LLMClient.embed()` per-text caching/batching, no-embed-support provider raises `LLMError`);
`tests/test_graph.py` (`canonicalize.cluster_values` near-duplicate merge/distinct-stay-separate/
no-embed-fallback, `temporal.assign_relation_supersession`, `build_graph` integration tests for
trait-value canonicalization, FRIEND_OF/ENEMY_OF same-volume arbitration + cross-volume
supersession, the "only one conflict-group predicate present" non-arbitrated case, the
both-directions-same-predicate regression, and the embed-failure graceful-degradation regression);
`tests/test_config.py` (`canonicalize_config` property + per-series overlay override);
`tests/test_audit_reports.py` (canonicalization section prints, and is absent-not-crashing for a
pre-Phase-17 `contradictions.json`). Full suite green (336 tests). See
`docs/handover/PHASE_17.md` for the file-by-file summary and what Phase 18+ needs to know.

---


## 2026-09-04 — Per-series extraction schema overlay + CLI schema tuning built

**What:** Both mechanisms from the entry above, implemented as planned:

1. `paths.extraction_overlay_config(series_id)` (`config/extraction.<series>.yaml`) +
   `config.py::_deep_merge`, called from `load_settings`. Deep-merges the overlay over the base
   `extraction.yaml` dict-by-dict; an overlay value of exactly `null` deletes that key from the
   merged result (removes a base predicate); any other overlay value replaces the base value,
   recursing one level deeper only when both sides are dicts at that key. Lists (e.g.
   `codex_pages.*.types`) are replaced wholesale, never concatenated. Verified live against the
   real repo (not just tests): a scratch `config/extraction.spice-and-wolf.yaml` adding `KARMA`
   and nulling `RANK` showed up correctly in `wiki doctor --series spice-and-wolf`'s new taxonomy
   panel, while `wiki doctor --series 86` was completely unaffected — then deleted, since it was
   only a smoke test, not a real predicate this series needs yet.
2. `Settings` gained `schema_overrides`/`schema_only`/`schema_skip`; `attributes`/`relations`/
   `traits` are now computed properties (`_effective_predicates`) that apply them on top of the
   already-merged base+overlay dict. New CLI options on `wiki extract` and `wiki doctor`:
   `--attr NAME=format:"Display"[:multi]`, `--trait NAME="Display"[:max_words]`, `--relation
   NAME="Display"[:symmetric|:inverse=OTHER]` (all additive, parsed by `config.py::
   parse_attr_override`/`parse_trait_override`/`parse_relation_override`), and `--only`/`--skip`
   (repeatable, each token a predicate name or a kind word — `attribute`/`relation`/`trait` —
   normalized by `_normalize_only_skip_token`). `apply_schema_overrides` mirrors
   `apply_model_overrides`'s shape exactly (same "mutate the loaded Settings in place, return
   human-readable notes for the CLI to print" contract), same ergonomics as `--model`.
3. `wiki doctor` prints a new "Effective extraction taxonomy" panel: which overlay file (if any)
   is in effect, and the resulting entity-type/attribute/relation/trait lists — "a silently wrong
   schema is otherwise only discovered by reading generated pages" is now a five-second check.
4. `provenance.py::_config_hashes` now takes an optional `settings` argument and, when given,
   hashes the MERGED effective taxonomy (`settings.extraction` + `schema_overrides`/`schema_only`/
   `schema_skip`) instead of just `extraction.yaml`'s raw bytes — a per-series overlay or an
   ad-hoc `--attr` run is now visible in a run's manifest even though the base file never changed.
   `start_run` threads `settings=` through; all five existing call sites in `cli.py`
   (gazetteer/extract/graph_build/synthesize/site_build) now pass their already-loaded `Settings`.

**Why:** Exactly the two gaps named in the entry above: the taxonomy was global (no series
argument anywhere in the load path) and there was no per-run override, so every experiment cost a
config edit that was easy to forget and impossible to attribute in `wiki runs`.

**Implies:** Nothing downstream had to change — `extract/claims.py`, `synth/assemble.py`,
`graph/contradictions.py`, `site/okf.py`, `site/bundle.py`, `synth/prose.py` all already read
`settings.attributes`/`.relations`/`.traits`/`.entity_types` as properties (verified by grep
before writing this), so the override plumbing is invisible to every consumer except `config.py`
and `cli.py` themselves — confirming the 2026-09-04 "Per-series extraction schemas" entry's own
claim that this was "a scoping problem, not a rewrite." One deliberate scope limit: `--attr`/
`--trait`/`--relation`/`--only`/`--skip` were added only to `extract` and `doctor` (where the
extraction *prompt* vocabulary matters), not to `graph build`/`synthesize`/`site build`/`run-all`
— an ad-hoc predicate's claims land in `data/03_claims/` from `extract` alone, but rendering it as
a page field still needs the SAME predicate in the base taxonomy or a per-series overlay, since
`synth`/`site` re-derive `settings.attributes` fresh from config, not from a prior run's flags.
This is documented in `USER_GUIDE.md` §8 rather than treated as a gap to close, since it is what
"ad hoc" is supposed to mean here — see that section for when to promote a predicate to a real
overlay entry instead.

**Status:** Done. 27 new tests (`test_config.py`: deep-merge, overlay isolation between series,
all three parse functions, `apply_schema_overrides` add/only/skip/self-skip interactions;
`test_provenance.py`: config hash differs for different `Settings.schema_*` state, stable for
identical state, still works when no `settings` is given). Full suite green. Verified against
real, live config on disk (not just tests): `wiki doctor --series spice-and-wolf --attr
'KARMA=short_text:"Karma"' --only trait --only KARMA` printed exactly `attributes (1): KARMA` +
every trait, nothing else; a real (then-deleted) `extraction.spice-and-wolf.yaml` overlay file
round-tripped through `wiki doctor` correctly scoped to that series only; `wiki extract --series
spice-and-wolf --attr ... --only AGE --skip relation` ran cleanly end to end (skipped existing
volumes, as expected with no `--force`).

---


