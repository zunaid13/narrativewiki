# docs/handover/PHASE_29.md — the emitted wiki, and the ledger that now holds every number

Written for a cold contributor. You should be able to continue from here without reading source.

## 1. What this phase was

Two things the maintainer asked for on 2026-09-23, neither of them about extraction quality:

- **Four standing rules** about how the API may be spent and where numbers are recorded, now in
  `CLAUDE.md` §2 and `AGENTS.md` §3 (both files, deliberately — the rules bind Codex and Claude
  equally).
- **A target restated in terms of shape, not accuracy**: the output must have "enough structurally
  well balanced well connected information that rivals a professional wiki-fandom page". Written
  into `CLAUDE.md` as a new §2b.

The design reasoning, including what was rejected, is `docs/vision/PHASE_29.md`. This file is what
exists and how to reproduce it.

## 2. The single most important new fact

**This project is not on a research-publication pathway.** There is therefore no paper to be the
durable home for a measured value. `docs/MEASUREMENTS.md` is, as of this phase.

It is append-only, one row per number, each row carrying the value, the command that reproduces
it, and the run that produced it. Observations — including findings that turned out to be
measurement artefacts — get rows too, because those are exactly what gets rediscovered
expensively. A number quoted in `LOG.md`, a handover, a commit message or a chat reply **does not
count as recorded** until it has a row there.

`ConvinceMe.md` and `Guide to Publishing.md` stay in the repo. They are still useful as design
pressure — the standard they set for an unaudited headline number is the standard the ledger
enforces — but they no longer describe a destination.

## 3. What shipped

Every change is in the emitter or the bundle builder. Nothing touched extraction, synthesis or
the graph, which is why the whole phase cost **$0** (`docs/MEASUREMENTS.md` §5).

| # | Defect | Fix | File |
|---|---|---|---|
| 1 | `members` and `adversaries` were not mutually exclusive — Milone Company printed "Members: Kraft Lawrence, Marheit" directly above "Adversaries: Kraft Lawrence, Yarei"; Remelio listed Norah Arendt in both | `adversaries -= members`. Both intervals are real (an employee who is also betrayed by the company), but a reader sees a contradiction; membership is the narrower claim and the one a roster is for. The betrayal is still in prose and on the relationship page | `site/bundle.py::_members_and_related` |
| 2 | Codex roster names were plain text, so Pasloe *named* Holo while Holo's page *linked to* Pasloe — a one-way edge | New `_entity_link` routes each id through `settings.route_for` | `site/mkdocs_wiki.py` |
| 3 | The `related` bucket printed the same four entities (Medio / Milone / Remelio / Rowen) under every place and faction alike | Not rendered. It is PPR neighbours, and on a 2-volume graph that is global centrality, not a fact about the entry. Still computed, still in the bundle, still in CONTRACTS §6.1 | `site/mkdocs_wiki.py::_render_codex_kind` |
| 4 | One art plate was the captioned "portrait" of up to three characters — the v01 frontispiece topped Holo's, Lawrence's **and** Yarei's pages | Two caps: front-matter plates only for the volume's two highest-importance characters (`allow_front_matter`), and any plate on at most `_MAX_PAGES_PER_PLATE = 2` pages, awarded in descending importance | `ingest/images.py`, `site/mkdocs_wiki.py::_pick_thumbnails` |
| 5 | `tech.md` shipped at both cutoffs as a bare `# Technology` heading, reachable from the volume index and the nav | `_codex_kinds_at` decides once which kinds have anything to say at a cutoff; the writer, the index and the nav all read it | `site/mkdocs_wiki.py` |
| 6 | `tests/test_audit_html.py` never redirected `paths.SITE_DIR` | Fixture now points it at `tmp_path`. Not cosmetic: an unpatched test writing into the repo's real, gitignored `dist/wiki` makes every other test in that file fail afterwards on links it never wrote. This is how it was found | `tests/test_audit_html.py` |

## 4. The trap worth remembering

**Nothing in this pipeline can see what a JPEG depicts.** `cover_image_for_entity` answers only
"which plate is nearest this character's debut", and that collides by construction — the v01
frontispiece is nearest the debut of Holo, Lawrence and Yarei alike. The emitter then captioned
it `![Yarei](...)`, which is a claim about the picture that nothing had evidence for.

The fix is a cap, not a better heuristic. Do not reach for a smarter proximity rule here; every
such rule is still guessing at the frame. A vision model reading the plates is the only thing
that would actually know, and that is a real phase, not a tweak.

The same shape of error is worth watching for elsewhere: **the emitter is the last place a claim
can be invented**, and it is the one place with no evidence gate behind it.

## 5. Reproducing the deliverable

The graph, claims and pages are unchanged from `docs/handover/PHASE_28.md` §6 — do **not** re-run
that sequence, it bills. From the current `data/spice-and-wolf/`:

```
wiki site build -s spice-and-wolf --upto 2 --force
```

This is free. `codex_summary` is the only generative step in it, and it is gated on an
evidence-only hash; the Phase 29 changes touch `members`/`related`, which move the *cache-entry*
hash but never trigger a call. Verified: `wiki budget -s spice-and-wolf` reads $5.49 before and
after.

Then:

```
pytest                                    # 1028 passed
wiki audit links -s spice-and-wolf        # OK, 33 routes / 86 pages
wiki audit eval  -s spice-and-wolf        # OK, with the 3 known recall WARNs
```

All twelve audit stages pass: `ingest gazetteer scenes claims contradictions verify events
outline pages links relationships probe`.

## 6. Numbers

In `docs/MEASUREMENTS.md`, not here — that is the point of the phase. §3 of that file is the
structural baseline (page-length spread, per-section fill rate, link count, portrait coverage),
taken on this build.

The two that matter for judging this phase: **86 pages** (down from 88 — the two lost are the
empty `tech.md` at each cutoff) and **$5.49 total spend, unchanged**.

## 7. What is NOT done

- **Character-page length spread is 21.4×** — 70 words at the shortest, 1,497 at the longest.
  This is the clearest remaining gap against a fandom page and the obvious next target.
  **Do not close it by writing prose.** A 70-word page is short because the corpus says little
  about that character, and `CLAUDE.md` §2's "zero evidence means `null`, never an invented
  sentence" is not negotiable. The fix, if there is one, is more evidence reaching synthesis —
  which means the scene-pass yield gap in `PHASE_28.md` §8, not the emitter.
- **Category pages are unbuilt.** `categories:` is in every page's front matter and rendered by
  nothing; it is also `[]` for Holo, so the field needs populating before the pages would mean
  anything. Cheapest remaining fandom affordance, deliberately deferred below the imbalance above.
- **Three characters now have no portrait at all** (`yarei`, both saints) — correct under the new
  caps, but it means portrait coverage is 11 of 14 rather than 14 of 14. A wrong picture is worse
  than none; a *right* picture needs a vision model.
- **Everything still open from `PHASE_28.md` §8** — `yarei`'s conditional-sentence gold fact,
  `docs/REFERENCES.md` stale at 51 rows against 54 PDFs (arXiv 406s every uncached request;
  `docs/PAPERS.md` is complete at 54/54), low scene-pass yield, serial `synthesize`/`verify`, and
  the unimplemented NLI hybrid from `PHASE_26.md` §5.1, which remains the maintainer's call.
