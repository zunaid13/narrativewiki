# Phase 30 — Structured coverage as the judgement metric

Append-only. A superseded decision gets a new dated entry saying what changed and why.

---

## 2026-09-23 — The metric changes: is the information conveyed, and is it structured?

**Maintainer decision, standing.** The measure of this project is not an internal ratio. It is
whether the information a professional fandom page conveys is present here **and carried in a
structured form**. Internal figures — verified share of the page, prose-versus-fields split,
page-length spread — are means, and when they conflict with that question the question wins.

This supersedes page-length spread as a headline figure entirely. `docs/handover/PHASE_29.md` §7
named the 21.4× ratio "the clearest remaining gap"; it is not a gap, it is a symptom that moves
the wrong way under a correct change. Removing an unevidenced "alive" from eight leads moved it
21.4× → 21.7× (`docs/MEASUREMENTS.md` §12). A metric that worsens when the wiki becomes more
honest cannot be the target.

### What the new metric found immediately

`config/extraction.yaml` splits character facts into `attributes:` and `traits:`. Attributes get
a deterministic structured renderer (`kind: fields`). **Traits had exactly one consumer — the
prose prompt.** So every SKILL, MOTIVATION and FEAR interval reached the reader only as whatever
survived a capped paragraph:

- Holo's page carried **3 of her 14 SKILL rows**, dissolved into half a sentence, under a
  citation reading "+103 more".
- Across the v1–2 roster, **43% of SKILL intervals left no trace in the page prose at all** —
  extracted, evidence-cited, volume-scoped, verified by `wiki verify`, then dropped at the
  emitter, which is the one stage with no evidence gate behind it (`PHASE_29.md` §4).

This is not an extraction problem, a retrieval problem or a model problem. `PHASE_29`'s own
observation applies exactly: the emitter is the last place a fact can be lost as well as invented.

### The decision

A new `kind: traits` page-outline section renders trait intervals the way `kind: fields` already
renders attributes — deterministically, from graph rows, with per-row citations, costing no
output tokens. CLAUDE.md §2 already required this ("structured fields are never LLM-generated …
render deterministically from graph rows"); traits simply had no renderer.

**Only SKILL gets a section (`Abilities`) in the base taxonomy.** PERSONALITY, MOTIVATION and
FEAR stay prose-only, and that is a decision, not an oversight: a professional page characterises
in sentences and bullet-lists capabilities. A list of 152 personality adjectives would be worse
than the paragraph it replaced. The 47% of PERSONALITY rows that do not survive the paragraph are
a compression the carrier is *right* to apply; the 43% of SKILL rows were a carrier mismatch.

Which predicates get a structured home is a `page_outline` decision, so a series overlay settles
it per series. No predicate is named in any module.

### Also decided here

- **`subsume: true` is NOT enabled for SKILL.** The near-duplicates the new list exposes
  ("detecting fraud" / "detecting lies" / "can sense lies") are semantic, and
  `canonicalize.subsume_values` matches token subsets by design — it would catch none of them,
  while dropping the single-token "witty", which is a misclassified personality trait rather than
  a duplicate. Recorded as an observation; a real fix is trait-level canonicalisation, not this.
- **SKILL stays in the `personality` prose traits list**, so a skill may appear in both the list
  and the paragraph. Removing it changes the prose prompt, which invalidates the prose cache and
  bills a regeneration for a cosmetic gain. Carries a `ponytail:` marker in the config; do it in
  the next pass that must regenerate prose anyway.
- **`wiki verify`'s withholding now reaches traits.** It applied to fields and relationships and
  never to traits, so an interval the verifier had rejected could still shape the prose. No live
  leak today (none of the 14 withheld intervals is a trait), but the gate was missing.

### What this implies for the roadmap

Work packages B and C of `docs/tasks/0006` are chasing scene-extraction recall one layer below
the measured bottleneck, and their own ceiling is 7 fixture facts of which 5 cannot be encoded by
the current vocabulary. They are not cancelled, but they rank below:

1. Structured coverage of what is already in the graph — this entry. Emitter-only, $0.
2. A structured-coverage audit: per character, which information categories a professional page
   carries, which this wiki carries, and for each gap the three-way split — absent from the text
   at this cutoff (correct to omit), present but unstructured (the real defect), or missing
   entirely (an extraction gap). The witness-table method of `0006` package A, aimed at the
   target rather than at scene yield.
3. `categories:` is populated on **0 of 14** pages while every page carries the field and nothing
   renders it; bidirectional reachability is still unmeasured as an invariant.
4. Per-volume plot summaries. The wiki emits "Appearances: Volume 1" as a bare strip where a
   professional page carries a paragraph per volume. The largest remaining structural absence.

### The boundary that keeps this safe

Adopting this metric means reading fandom pages as a **specification of what categories of
information a page should carry**. It must never make them an **evidence source**: a fandom page
has no volume scoping, so its content is a spoiler pipeline, and it carries no paragraph
citations, so anything taken from it is unsupported by construction. `docs/tasks/0006`'s "do not
use fandom pages as additional evidence" stands unchanged — schema target, never evidence.

---

## 2026-09-23 (later) — Correction: the fandom page is a quality bar, not an output template

**Maintainer clarification, standing.** The entry above reads in places as though the goal were
to carry what a fandom page carries. It is not. **This product is different from a fandom wiki**,
and the output should not mimic one. The reference supplies a *standard of quality* for
presenting structured information about a novel — completeness, precision, no redundancy, no
dead ends, every claim traceable — and nothing more. Section-for-section parity is not a goal,
and "a fandom page has X" is not by itself an argument for X.

What this changes in practice:

- The planned coverage audit is **not** a checklist of fandom headings. It asks whether the
  structured information this pipeline holds is presented to the standard a good reference work
  would meet. A category we hold nothing for is not a gap.
- Per-volume progression, floated above as "a fandom page carries a paragraph per volume",
  has to be justified on this product's own terms instead. It can be: this wiki is *defined* by
  its volume cutoff, so a reader arriving at cutoff N is asking what changed by volume N. That is
  a native requirement here and a coincidence that fandom pages also do something similar.
- The things this product has that a fandom page does not — per-claim citations, `first_vol`
  scoping, verified-vs-withheld provenance — are where its quality is judged, not deducted.

### Shipped under the corrected reading

`_dedupe_name_fields`. Holo's page carried "**Nicknames:** Holo" — the character's own name,
listed as one of her nicknames directly beneath the `# Holo` heading — and "Wisewolf of Yoitsu"
under both Nicknames and Titles. 5 of 14 pages had one of these. Two rules: the canonical name
never appears in a name-like field, and a value held by a higher-precedence `name_like` attribute
is not repeated by a lower one, precedence being `config/extraction.yaml`'s declaration order.
Overlapping pages 5 → 2.

Deliberately **not** done, and recorded as decisions:

- Values appearing in both the gazetteer's `aliases`/`epithets` front matter and a name-like
  field are left alone. That front matter is YAML metadata, so the Nicknames line is the only
  place a *reader* sees those strings — removing them would delete visible information to tidy
  something invisible.
- The two remaining overlaps are `Role` == `Title` (Holo's "harvest god", Jakob's "master of the
  Ruvinheigen branch of the Rowen Trade Guild"). OCCUPATION is not `name_like` — marking it so
  would let "merchant" compete with titles. The same string arriving under two predicates is an
  extraction artefact, and arbitration, not the emitter, is where it should be settled.

---

## 2026-09-23 (third) - Reverse routes; and a correction to this file

**Correction.** The first entry's roadmap said "`categories:` is populated on 0 of 14 pages".
That is wrong: **8 of 14** carry categories. The measurement read `05_pages/*/v02.json`, where the
field does not exist - `site/okf.py::_front_matter` derives it from affiliations at render time.
The 6 pages without categories are the 6 without affiliations, which is correct.

**Category index pages are decided against.** Categories derive from affiliations, and each
faction's codex page already lists its members. An index would restate that under a second name,
which is exactly what the second entry above rules out: "a fandom page has X" is not an argument
for X.

**Connectivity, measured.** 12 of 40 character-to-character links ran one way, and
`saint-metrogius` was reachable from no page at all. Checked pair by pair, the one-way links were
incidental prose wikification rather than missing graph edges.

`mentions_of` - PPR neighbours minus whoever the page already shows - has been computed since
Phase 22 and rendered nowhere. A `kind: related` section now renders it, showing **only entries
the pipeline can explain**: `note: null` means a multi-hop-only PPR hit, and an unexplained
"related" chip is the noise `PHASE_29` stripped out of the codex pages. 40 -> **58** links,
one-way share 30% -> 24%.

**And a third place the verifier was being overruled.** `_annotated_mentions`'s relation branch,
documented as "defensive; should rarely fire", fires in exactly one case: when a relationship was
withheld by `wiki verify`. A withheld relation is absent from `fields.relationships`, so the other
party is absent from `already_shown`, so the function annotated the pair with the rejected
predicate. Saint Metrogius's page model carried `"note": "Mentor of"` off an interval the verifier
had explicitly rejected. Fixed with the same gate fields and relationships already apply.

That makes three: fields/relationships had the gate from Phase 23 B2; traits did not (second
entry); `mentions_of` did not. **The gate belongs where intervals are read, not re-remembered by
each new reader.** Any future consumer of `temporal.state_at`/`relations_between` inherits this
bug by default, and the next one will not be found by reading a page.

**`saint-metrogius` is still reachable from nothing, and that is honest.** His only real tie is
that Lawrence follows his path in business - `MENTOR_OF` misencodes it, verify correctly withheld
it, and no predicate in `config/extraction.yaml` can express it (fixture fact M3). A vocabulary
limit rendered honestly is not a link defect, and it should not be papered over with a link the
evidence does not support.

---

## 2026-09-23 (fourth) - The codex pages, looked at for the first time

Every entry above is about character pages. The codex - factions, places - is a third of what
this wiki emits and had not been read once under the new metric.

**A faction's vocabulary was being applied to every entity type.** Pasloe, a mountain village,
shipped "**Members:** Count Ehrendott, Holo", because `ORIGIN_FROM` declares `membership: true`
(so being *from* a place files you as one of its members) and the renderer's heading was the
literal string "Members" regardless of type. `entity_types.<TYPE>.roster_labels` now supplies the
word: LOCATION gets "Associated with", EVENT "Participants", TECH "Used by". Omitting the key
keeps the old text, so it is inert for a series that does not set it.

**Recorded, not fixed.** Places carry **no key events at all** (0 across 13 entries) while
factions carry 11 across 6. That is the larger codex gap, and it is a data question - whether a
scene event can attach to a LOCATION in `events.db` - rather than an emitter one, so it does not
belong in the same change. One event summary of ten renders under two faction entries; a scene
genuinely involving two factions is not obviously wrong to show under both.

**The pattern worth carrying forward:** the defects found under this metric are consistently a
default meant for one case being applied to all of them - "alive" for every character, "Members"
for every entity type, a prose paragraph for every trait. None of them is a model failure or an
extraction failure. They are places where one type's convention became the system's default.

## 2026-09-24 — Repository restructure: one obvious home per kind of file

**What:** The repo layout drifted over a month of alternating Claude/Codex work. Scripts ran from
`docs/`, papers sat in two folders under two naming schemes, plans lived in `docs/tasks/` beside
a standalone vision file, the retired 86 EPUBs sat at `raw/` while Spice and Wolf sat in
`All novels/`, and publication-era docs and 80 MB of media sat at the root. It is now: EPUBs in
`corpus/<series-id>/`; code in `src/` or `scripts/{eval,probe,papers}/`; `docs/` holds only text
and data; plans in `docs/vision/plans/NNNN-<slug>.md`; papers in `docs/papers/{pdf,reviews}/`
with `PAPERS.md`/`REFERENCES.md`; frozen publication-era docs in `docs/archive/`.
`STRUCTURE.md` was rewritten to match and carries the old → new path table.
**Why:** Maintainer instruction (2026-09-24): "make sure everything is where it should be and
intuitively we can know where something should be at." Plans belong with the vision record
("tasks should be on the vision folder written as vision").
**Implies:** Append-only records keep their old paths (never rewritten); translate them with
`STRUCTURE.md`. `docs/vision/plans/` stays open to both agents: unlike `PHASE_*.md`, plans are
living documents. `docs/archive/` is read-only. `config.discover_volumes` defaults `source.dir`
to `corpus/<series-id>`. **Not done, needs a decision:** `paths.DEFAULT_SERIES` is still `"86"`,
so the retired series still owns the unsegmented `data/0N_*` layout. Changing it moves where
every default-series path resolves, and it needs an explicit migration.
**Status:** Done (Phase 30). `docs/MEASUREMENTS.md` §23.

## 2026-09-24 (later) — The restructure's open items, decided

**What:** The maintainer delegated the three open items (anything reversible may be decided
without asking):
1. **`paths.DEFAULT_SERIES` stays `"86"`.** Users never hit it: every `wiki` command already
   defaults to spice-and-wolf (`cli.py::_ACTIVE_SERIES_DEFAULT`). What the constant still
   decides is which series owns the unsegmented `data/` root. Code that never calls
   `set_active_series` resolves there, and that includes most of the test suite. Flipping it to
   spice-and-wolf would aim such code at the only live data set, so the retired series' root is
   the safer place for it to land. Revisit only together with making every series segmented and
   a tested `data/` migration.
2. **Retrospective handovers for Phases 24 and 25** were written as indexes into their vision
   files, labelled as retrospective. Phases 14–16 were planned in Phase 10 but never run, so
   there is nothing to hand over.
3. **CLAUDE.md stays at ~263 lines.** The obvious cut, moving §3's 86 corpus traps into
   CONTRACTS §1, would break a dozen "CLAUDE.md §3 trap N" references in code and in
   append-only docs.
Also: two standing rules existed only in Claude's private memory, so Codex never saw them:
commit finished work, and never trade quality for call count. Both are now in `AGENTS.md` §3.
Their absence explains at least in part why the 2026-09-24 review was left uncommitted.
**Why:** Maintainer instruction, 2026-09-24.
**Status:** Done (Phase 30).


## 2026-09-25 — Infobox fields come from a long-context pass, not the windowed one

**What:** A new additive stage, `wiki infobox` (`extract/infobox.py`), fills GENDER, AGE and ORIGIN:
one call per character per volume over every paragraph that names the character, each field bound
to a verbatim quote, through the same gates and verification as every other claim.
**Why:** The done-bar is "every character page carrying the same sections filled to comparable
depth". Before this, GENDER rendered on 2 of 14 pages, ORIGIN on 1 and AGE on 2, the fields every
fandom infobox carries. The windowed pass misses them structurally: no single 4k window *states* a
character's gender. Recent work points the same way. Long-context models locate scattered
literary evidence across a whole novel far better than retrieval over fragments (Literary Evidence
Retrieval via Long-Context LMs, ACL 2025: Gemini 2.5 Pro 62.5% vs embedding retrieval 4.5%), and
evidence-bound extraction (Evidence-Bound Persona Extraction with LLMs, NLPIR 2025) is the
attribution discipline this pipeline already enforces.
**Rejected:** (1) Adding notes for these attributes to `claim_extract`'s prompt: this re-rolls every
claim (about $0.55, gold facts lost, MEASUREMENTS §30). (2) BookNLP-style pronoun counting for
gender: a new heavyweight dependency, and its output would not be a quoted fact a reader can check.
(3) The windowed pass's ±4-paragraph context in the dossier: measured worse, see MEASUREMENTS §34.
**Status:** Built and run on v1–2.


## 2026-09-25 (later) — Backstory gets the same long-context treatment; withheld means withheld in prose too

**What:** `wiki infobox --pass backstory` extracts BACKGROUND facts per character-volume. Separately,
prose prompts now read only intervals verification did not withhold (`assemble.visible_state_at`).
**Why:** The done-bar's History section needs a character's past, and the gold misses were mostly
backstory the text states (Norah's almshouse childhood). The prose fix enforces the rule that a
page never asserts what the evidence does not support: 17 of 21 withheld facts still reached prose.
**Rejected:** Putting BACKGROUND into the infobox pass: it would change that pass's prompt and re-roll
its verified answers. Name-only dossiers for backstory: a past is told in unattributed dialogue.
**Status:** Built and run on v1–2; MEASUREMENTS §37.

## 2026-09-25 (later x2) — The verifier knows a character's other names; overrides may retire ids

**What:** `verify.subject_label` shows the verifier the aliases visible at the cutoff, and its prompt
accepts a gendered pronoun as GENDER evidence (`METHOD_REVISION = per-fact-v3-aliases-gender`).
`alias.id_renames` maps ids that an `entity_overrides` merge or rename retired, wherever claims and
scene records load (`graph build`, `events-build`).
**Why:** Overlord's people carry several names: Ainz's armour was withheld as "about Momon". The
id remap follows from `rename` changing an id after scene records already held the old one.
**Rejected:** A stricter PERSONALITY/relation instruction (replayed on stored prompts: it rejected
23 of 121 true traits). Re-running `wiki scenes` to refresh one id (~$0.80; prompts embed the
gazetteer, so no cache replay).
**Status:** Both series re-verified and rebuilt; MEASUREMENTS §38.

## 2026-09-25 (later x3) — Generic novels: what a new series inherits

**What:** A new series needs only an id, a title and a folder. Chapter heading tags are detected
from the book, a single unnumbered EPUB is volume 1, English honorifics and every common opening
quote are defaults, and `prompt_vocabulary` rewrites the prompts' "translated Japanese light
novel" in `llm/client.py`. A public-domain Gutenberg novel is the committed probe
(`config/series.probe-gutenberg.yaml`).
**Why:** The maintainer's target is "any generic novel". All three corpora so far are Yen On
EPUBs of translated light novels, so every default had been fitted to one house style; the probe
failed silently at the first step (15 chapters read as 2).
**Rejected:** Forking the prompts per genre (fourteen sites, every existing cache invalidated).
Dropping single-letter candidates (a letter can be a name: Kafka's "K."). Running LLM stages on
the probe without the maintainer choosing to widen scope.
**Status:** Ingest and candidate mining verified; MEASUREMENTS §39.

## 2026-09-25 (later x4) — A third corpus: Ascendance of a Bookworm v1–2

**What:** `config/series.bookworm.yaml` (J-Novel Club, Part 1 v01–02) run end to end, with a gold
set of six characters. Fixes it forced, all generic: part-ordered volume numbering, title-based
chapter kinds, a content-filter refusal routed to the next model rung for that one call, an embed
batch that NaNs retried per text, an Abilities `exclude_pattern`, possessive-aware eval keywords,
and the lifetime cap summing every series' ledger.
**Why:** The maintainer supplied it as the non-Yen-On corpus (MEASUREMENTS §39). Each fix would
have hit the next generic novel too; three were silent (canonicalization off, lifetime cap at $0,
eval undercounting).
**Rejected:** Disabling Gemini safety settings (PROHIBITED_CONTENT is not configurable). Skipping
blocked passages (a silent drop). A kinship-aware alias resolver for first-person "Mom"/"Dad"
(a config merge covers ~98%; revisit if a series needs it).
**Status:** Done for v1–2; MEASUREMENTS §40. Mushoku Tensei awaits the maintainer.
