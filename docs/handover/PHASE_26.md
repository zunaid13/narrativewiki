# Phase 26 Handover — Citable pages (PARTS A, B AND C COMPLETE)

Status as of 2026-09-21, branch `phase-26-citable-pages`, not merged to `main`.
`pytest -q` green (1002). Check `git status`/`git log` rather than trusting this line.

**Where the phase landed:** four of the five defects the opening audit named are closed and
re-measured on the current build (§5). The fifth — `support_score` NULL on every verdict row —
was measured rather than fixed, and the measurement closed one of its two branches: relations
need a *different verifier*, not a calibrated threshold (§5.1). Shipping that is the one open
decision, and it is deliberately left to the maintainer because it changes what readers see.

**Read this before touching** `site/okf.py`'s relationship or affiliation rendering,
`synth/assemble.py`'s quote ranking, `site/wikify.py`'s link filter, or
`config/extraction.yaml`'s `conflicts_with`. Each carries a decision that looks arbitrary
without the measurement behind it, and two of them are reversals of things this same phase
tried first.

---

## 1. What this phase was for

The maintainer asked for an audit of the shipped v1-2 wiki against a real Fandom character page,
then a fix for what it found, plus one new requirement: **every claim should hyperlink to the
exact point in the source it came from**, with an EPUB→PDF wrapper as an acceptable fallback.

The audit's finding in one line: the page *skeleton* already matched Fandom (Overview →
Appearance → Personality → History → Quotes → Affiliations → Relationships → Appearances) and the
History prose was good, but **nothing on any of the 66 pages was verifiable**, several pages
asserted contradictory facts side by side, and the relationship section was unreadable.

Full audit numbers and the requirement are in `docs/vision/PHASE_26.md`'s first entry.

---

## 2. What exists now (Part A — the render layer)

Everything in Part A is rebuildable from the existing `graph.db`. No re-extraction was needed.

### 2.1 The source view — the deliverable the maintainer asked for

`dist/<series>/wiki/vNN/source/` — one Markdown page per (volume, chapter), every paragraph
rendered verbatim followed by `{: #nw-<para_id> }` on its own line. `attr_list` was **already**
an enabled markdown extension, so no config change was needed; the stamp becomes a real HTML id.

- `site/mkdocs_wiki.py::source_route` — `v02:c00:p0044` → `/source/v02-c00#nw-v02-c00-p0044`
- `site/mkdocs_wiki.py::citation_label` — → `v2 ch.1 P44` (chapter rendered 1-based)
- `site/mkdocs_wiki.py::source_anchor` — the `para_id` → HTML id mapping
- `site/okf.py::_source_links` — the only consumer; returns `""` when `link_depth is None` so
  `data/05_pages/**/v{NN}.md` (CONTRACTS §5.2) stays byte-identical as its docstring promises.

Citations render in three places: quote attributions (speaker + link), prose sections
(a `Sources:` footer, capped at 6 links), relation bullets (capped at 3 — a bullet is one line).

**Live result: 595 citation links, 0 broken, 8,703 anchors over 28 source pages, 21/21 character
pages cited (from 0/66).** Verified with a real `mkdocs build --strict`.

### 2.2 Everything else Part A changed

| Area | Before | After |
|---|---|---|
| Live contradictory relation pairs | 5 | 0 |
| False hyperlinks (generic nouns) | 21 | 0 |
| Holo's front-matter aliases | 45 | 9 |
| `"Listen, you"` rank among Holo's quotes | 1 | 725 / 765 |
| Character pages with a portrait | 0/14 | 21/21 |
| `wiki audit links` | FAIL (`may-god`) | OK |
| `wiki audit eval` negative-fact violations | 4 | 3 |

Mechanisms, briefly — each has a `Phase 26` comment at the site of the change:

- **SAVED/KILLED** declared as a *mutual* `conflicts_with`; `object_display` gives the victim's
  page "Killed by" instead of the killer's wording.
- **`_conflict_cliques`** (`graph/contradictions.py`) — new, see §3.1.
- **Quote notability** (`synth/assemble.py::_quote_notability`) replaces confidence ranking.
- **Relationships** group under one `### Name` per person, with a generated paragraph
  (`synth/prose.py::generate_relationship_prose`, one call per page).
- **Affiliations**: `_is_membership_role` + an adversarial-relation check; non-membership ties
  move to `fields["other_ties"]` (see §3.4 for why the flag alone was not enough).
- **Epithet links**: `site/wikify.py` never links a `source: epithet_mining` surface form.
- **Nav**: `_render_nav` generates a curated `mkdocs.yml` `nav:`; there was none.
- **Images**: no code change — a stale parse (see §4.3).

---

## 3. Decisions taken, and three taken then REVERSED

The reversals matter more than the decisions. Each was tried, measured on the real corpus, and
backed out. Do not re-attempt them without reading why.

### 3.1 `conflicts_with` is a graph, not a partition (kept — and it is load-bearing)

`build_graph` buckets a pair's claims under `pair_claims[(subj, obj)][pred]` for every predicate
appearing in *any* conflict group, then `_resolve_relation_group` arbitrates the whole bucket
down to **one** survivor. That is only correct if every predicate in the bucket is mutually
exclusive with every other. It is not: ENEMY_OF conflicts with FRIEND_OF *and* COMRADE_OF, but
those two do not conflict with each other.

`_conflict_cliques` partitions by actual pairwise conflict. A pair carrying ENEMY_OF + KILLED +
SAVED now yields two cliques (`[ENEMY_OF]`, `[KILLED, SAVED]`) — being someone's enemy and having
saved them are not exclusive; killing and saving them are.

This also closes a pre-existing latent hazard: `extraction.yaml`'s own note says SPOUSE_OF and
ROMANTIC_WITH are deliberately *not* conflicts, yet both sat in the family conflict group and
would have been arbitrated against each other. It simply never fired on live data.

### 3.2 REVERSED — COMRADE_OF/ENEMY_OF as a conflict pair

Declared it, rebuilt the graph, measured, reverted. Two reasons:

1. It is not a true exclusion. COMRADE_OF's own config note scopes it to "fellow soldiers/
   workers/travelers" — a role co-membership, not an affective bond. Holo travels with Norah
   while openly hostile to shepherds.
2. It actively **lost a true fact**: a spurious `kraft-lawrence ENEMY_OF holo` (conf 0.9, no
   qualifier) pulled the genuine COMRADE_OF into a three-way clique with FRIEND_OF, and
   arbitration dropped it.

Recorded in `config/extraction.yaml` beside the rule it would have broken, with the same
reasoning the file already uses for RIVAL_OF: do not invent a bigger taxonomy than the corpus
forces.

### 3.3 REVERSED — a `vol_end` filter on `temporal.relations_at`

The plan called for it (`relations_at` is the only `*_at` reader without the "still true" clause,
which looks like an oversight next to `state_at` and `relations_between`). It is not an
oversight. `tests/test_synth_assemble.py::test_relationship_closed_by_conflicts_with_shows_
current_false` asserts the opposite: a closed relation is deliberately returned so it can render
marked `_(ended v1)_` — which is also Fandom's "(formerly)" convention. Reverted immediately; the
`conflicts_with` declaration alone achieved the goal.

### 3.4 Flagging an affiliation was not enough — it had to leave the field

First attempt added `membership: false` to the entry and rendered it under a different heading.
`wiki audit eval` kept reporting "Holo is not affiliated with the Medio Company", and it was
right: `eval/gold.py::_relationship_entry_keywords` adds `{affiliated, affiliation, member,
membership}` to **every** entry in `fields["affiliations"]` unconditionally. The fact was still
filed as an affiliation. Non-membership ties now move to `fields["other_ties"]`, which also fixes
`categories` in the front matter (Holo was categorised under her captor).

### 3.5 Two different bars for "is this a name?"

Deliberate asymmetry, not an inconsistency:

- **Linking** (`site/wikify.py`): nothing from the `epithet_mining` channel is ever linked.
- **Display** (`site/okf.py::_names_a_character`): a mined form may still appear in the infobox
  if it carries a capitalised token that is not merely sentence-initial.

A wrong link sends a reader to the wrong page; a stray infobox entry only looks odd. The display
heuristic knowingly admits two false positives on Holo's page ("a representative of almighty
God", "the god of the Church") in exchange for keeping "the Wisewolf of Yoitsu".

### 3.6 `object_display`, not a `KILLED_BY` predicate

`extract/claims.py::_vocab_lines` enumerates **every** key in the `relations:` block into the
extractor's prompt vocabulary. Adding KILLED_BY would give the model two ways to state one fact.
`object_display` is a display-only key consulted by `synth/assemble.py` when the entity is the
relation's object.

---

## 4. Traps hit (two are new corpus facts)

### 4.1 CLAUDE.md §3 trap 8 does not generalise

Trap 8 says `<a id="page-N">` markers "give free print page numbers for citations". True for the
**86/Stick** EPUBs (243 anchors in v01). The **LuCaZ Spice and Wolf** EPUBs carry **54 anchors
for 3,529 paragraphs** — roughly one per 65 paragraphs. Print page is a usable *label*, not a
usable *anchor*, for this series. `print_page` is still stored per paragraph and non-null on all
3,529 v02 records; the source view renders it as a heading where it changes.

### 4.2 `chapter_id` names the wrong file for ~60% of paragraphs

`ingest/epub.py` stores only the `<section id>` of a chapter's **first** XHTML document (`:215`,
`:226`), but a chapter absorbs continuation spine documents (`:218`, `:230`). v02 chapter 0 is
`chapter002.xhtml` (191 paras) + `chapter004.xhtml` (339 paras), all recorded as `chapter002`.
The spine href is computed at `:146` and discarded at `:147`.

**Consequence for anyone revisiting EPUB deep-linking:** any scheme that maps a `para_id` back to
a source file via `chapter_id` is wrong for the majority of paragraphs, and fixing it requires a
full re-parse. This is the main reason the source view renders our own normalized text instead.

### 4.3 The image manifest is only written for volumes parsed on that run

`cli.py:781-790` writes it under `if parsed_volumes:`. `data/spice-and-wolf/01_parsed/` had no
`img/` dir because the parse predated Phase 25, so 0 of 21 character pages had a portrait —
with no code defect anywhere. A forced re-ingest fixed it.

**Before forcing that re-parse, idempotency was verified**: `v01.jsonl` and `v02.jsonl` hash
byte-identical afterwards, so every `para_id` — and therefore every citation and every claim's
evidence pointer — survived untouched. Do this check before any future `ingest --force`.

### 4.4 arXiv API returns HTTP 406 from this environment

Every User-Agent tried. `docs/fetch_reference_pdfs.py` cannot run here. See §6.

---

## 5. What Parts B and C did — all four closed, re-measured 2026-09-21

Each number below was re-measured against the *current* build, not copied from the commit that
claimed it. Reproduce with the commands in §7.

1. **`holo KILLED liebert` is gone** (0 intervals). Two independent mechanisms, because the
   original arbitration bug had two causes: `conflicts_with` on the SAVED/KILLED pair, and a
   **realis gate** (`extract/adequacy.py`: `requires_realis` + `irrealis_markers`) so an event
   that is imagined, feared or hypothetical cannot found a claim at all. Part B's gates asked
   *who* is named and never *whether it happened*, which is why `holo KILLED yarei` ("The image
   of Yarei's torso in Holo's fangs came unbidden to Lawrence's mind") cleared every one of them.
   `object_types` is now also enforced at `build_graph`, not only at extraction — a gate in the
   extractor does not repair the graph you already have.
2. **Bare relations 24/89 (27%) → 13/127 (10%)**, and every remaining one is `SAVED` (10) or
   `ORIGIN_FROM` (3), both self-explanatory. `FRIEND_OF`/`ENEMY_OF`/`RIVAL_OF` — the three the
   maintainer actually complained about ("'friend of' doesn't make much sense") — are all
   explained now.
3. **Hedging recall 4.6% → 8.8%** (81 of 917 claims carry `presumed`/`denied`).
4. **`audit eval` negative-fact violations 3 → 0.** `Jakob PARENT_OF Kraft Lawrence` and
   `enek RELATIVE_OF norah-arendt` are both gone from the graph (0 intervals each).

`wiki audit` is OK on all eleven other stages (`ingest` … `relationships`). **`audit eval` still
FAILs**, on fact recall for `jakob`/`norah-arendt` only — see §5.2, which is a metric story, not
a pipeline defect, and the baseline was deliberately not lowered to silence it.

### 5.1 The verifier — the threshold branch is now CLOSED by measurement

`support_score` is still NULL on all 256 verdict rows, because the runs that wrote them did not
pass `--nli`. **Do not just flip it.** `docs/vision/PHASE_24.md` measured why at a flat 0.5
threshold, and Phase 26 has now measured the follow-up question over **all 206** arbitration-scope
v1-2 claims (`docs/eval/nli_kind_sweep.py`, local MiniCheck, zero API calls, report checked in
beside it):

```
attribute   n= 97  median 0.778  p90 0.972   flagged@0.5 40%
relation    n=109  median 0.097  p90 0.928   flagged@0.5 76%
```

The old plan was "give relations a separately calibrated threshold **or** a different verifier."
**The threshold branch is dead**, and the reason is not the low median:

- Relations are **bimodal, not shifted** — median 0.097 against p90 0.928. `FRIEND_OF` is median
  0.040 / p90 0.900. A cutoff cannot split that into right and wrong; it only picks how many to
  throw away.
- PHASE_24's hand-verified, correctly-extracted `MENTOR_OF` scored **0.038**. This sweep puts
  `rel:MENTOR_OF`'s median at **0.039** — the known-good claim sits *at its predicate's median*,
  so for that predicate the score is uninformative about correctness by construction.
- At 0.02 relations and attributes flag identically (7%): the only cutoff that stops
  over-flagging relations is one that flags almost nothing.

**Attributes are the usable half**: median 0.778, with `GENDER` 0.967, `STATUS` 0.879,
`OCCUPATION` 0.805. `RANK` is the one attribute outlier (0.249) and it is a *template* problem,
not a classifier one — its values are long descriptive phrases ("held an indispensable standing
in the city") that no short hypothesis sentence states literally.

**The remaining decision, left to the maintainer:** scoping `--nli` to attributes means relations
lose their only per-fact check unless a replacement lands in the same change. The obvious
replacement is the existing chat `verify` stage, which already reads a fact against its own cited
evidence — i.e. a hybrid where attributes go to MiniCheck and relations stay on chat. That is
additive rather than reshaping (relations would behave exactly as they do today), but it is still
a change to what ships, which PHASE_26 records as the maintainer's call. Spec:
`docs/tasks/0005-nli-verification-and-arbitration.md`.

### 5.2 Why `audit eval` still FAILs, and why the baseline was not lowered

Fact recall conflates **three unrelated failures**, which is why chasing the single number kept
pointing at the wrong layer. Diagnosed 2026-09-21 (`docs/vision/PHASE_26.md`):

- **Extraction coverage** — real, and the only one worth fixing. Jakob has 9 trait claims; the
  prose used essentially all of them. The gold facts it misses ("very friendly", "treats guild
  members like his own sons") have **no claim at all**, though the corpus plainly supports them:
  14 paragraphs pair Jakob with a warmth cue (`v02:c02:p0191` "broke into a grin", `p0229`
  "smiling pleasantly"). The extractor fires on *dispositional statements* and not on *narrated
  behaviour*. No prose model can recover this.
- **The prose cap** — working as designed. Norah has **68** claims; the "missed" gold facts are
  in the graph and off the page only because prose is capped at 2-4 sentences (CLAUDE.md §2).
  Recall against a full Fandom page is therefore structurally bounded well under 100%.
- **Lexical synonym blindness** — gold "tailor" vs the graph's "tailors"/"dressmaker".

`wiki audit eval` now prints, per missed fact, **`in graph`** vs **`no lexical match in graph`**,
by running the *same* matcher against the volume-filtered `claims` table instead of the page — so
the one varying thing is page-vs-graph. The two directions are **not** equally trustworthy and the
report says so: `in graph` is reliable; its negation over-reports (a 14-keyword gold sentence
scores 5 against a threshold of 6 while three matching almshouse claims exist). It is deliberately
not "fixed" by lowering that threshold, because the same rule computes the gated recall number —
that would be tuning the metric to the desired answer. The top-up hint now fires only when some
miss has no graph match, so it no longer recommends a full re-extract for a page bounded by the
prose cap.

---

## 6. Research papers — added, not yet fetched

`docs/fetch_reference_pdfs.py` gained four ids, each hand-verified (via the arXiv abs page, not
the API) to resolve to the intended paper:

| id | paper | justifies |
|---|---|---|
| 2406.06125 | Verifiable Generation with Subsentence-Level Fine-Grained Citations | the per-paragraph vs sub-sentence granularity choice |
| 2508.15396 | Attribution, Citation, and Quotation: A Survey | positioning for the citation layer |
| 2502.12124 | RA-MTR: Inspirational Quote Extraction from Long Documents | the comparison for `_quote_notability` |
| 2505.24553 | CREFT: Sequential Multi-Agent LLM for Character Relation Extraction | the comparison for `generate_relationship_prose` |

**The PDFs are NOT downloaded and `docs/REFERENCES.md` is NOT updated.** That file is
generated-only and must not be hand-edited; `docs/PAPERS.md` rows are keyed by a filename that
does not exist yet, so neither was touched. Until the fetch runs,
`python docs/fetch_reference_pdfs.py --check` correctly reports the four as "has no PDF on disk"
— that is the pending-work signal the check exists for, not a regression.

To finish, from a network that can reach arXiv:

```
python docs/fetch_reference_pdfs.py          # downloads PDFs, regenerates docs/REFERENCES.md
python docs/fetch_reference_pdfs.py --check  # then must report no problems
```
…then hand-add one row per paper to `docs/PAPERS.md` §A/§B with its Applied/Reference status.

---

## 7. Reproducing the deliverable

From a clean checkout of `phase-26-citable-pages`, with `OPENROUTER_API_KEY` set:

```
pip install -e ".[dev,wiki]"
wiki doctor

# Part A, in order. The ingest is idempotent (§4.3) but --force is what writes the image manifest.
wiki ingest     -s spice-and-wolf --volumes 1,2 --force
wiki graph build -s spice-and-wolf --allow-partial      # deliberately NOT --nli, see §5.1
wiki synthesize -s spice-and-wolf --upto 2 --force
wiki site build -s spice-and-wolf --upto 2 --force

# verification
pytest -q
wiki audit links -s spice-and-wolf                      # must print OK
wiki audit eval  -s spice-and-wolf                      # FAILs on jakob/norah fact recall only (§5.2)
python -m mkdocs build -f dist/spice-and-wolf/mkdocs.yml --strict

# the NLI measurement behind §5.1 -- local MiniCheck, no API key needed, no API calls
python docs/eval/nli_kind_sweep.py
```

**`wiki extract` is not reproducible to better than ~16%** (measured 2026-09-21): re-running it
against the byte-identical prompt and model gives Holo 235 claims where the stored file has 280.
The commands above reproduce the deliverable's *shape*, not its exact contents, and **a stored
baseline is not a valid control for an extraction A/B** — re-run both arms in the same session.
See `docs/vision/PHASE_26.md`, 2026-09-21.

`audit eval`'s FAIL is expected and is **not** a pipeline defect: it is fact recall for `jakob`
(a real extraction gap) and `norah-arendt` (the prose cap), both explained in §5.2. The baseline
in `docs/eval/gold/spice-and-wolf/baseline.json` was deliberately NOT lowered to make it pass —
that file is hand-maintained, and the report's own error message warns against re-running until
it goes green.

`--allow-partial` is required: `may-god` and `Liebert` (v1) trip the "mentioned/zero-claims"
crash-signature guard. Both are confirmed non-crashes.

The deliverable is `dist/spice-and-wolf/wiki/`. Read
`dist/spice-and-wolf/wiki/v02/character/holo.md` against
<https://spiceandwolf.fandom.com/wiki/Holo> — that page is the reference the whole phase was
scored against, and the same one `docs/eval/gold/spice-and-wolf/` was transcribed from.

To confirm the headline feature specifically, follow any `[v1 ch.2 P270]` link on a character
page: it must land on that exact paragraph in `vNN/source/`.
