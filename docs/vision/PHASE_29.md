# docs/vision/PHASE_29.md — the emitted wiki has to stand next to a fandom page

Append-only. A superseded decision gets a new dated entry saying what changed and why.

---

## 2026-09-23 — Phase 29 opened: four standing rules, and a target that is not recall

The maintainer set the next phase's terms directly. Two parts: rules that bind every agent from
now on, and a goal that is about the *shape* of the output rather than its accuracy.

### The rules (now in `CLAUDE.md` §2 and `AGENTS.md` §3)

1. **Spend the API only when nothing else moves the project forward.** Deterministic stage, cache
   hit, fixture or stored-prompt replay first. Say in one line why no cheaper path exists before
   running anything that bills.
2. **Tune on the smallest slice that can show the effect.** Prompt and config A/Bs start on one
   volume or on stored prompts, never on a full `--volumes 1-2` pass. The full sequence is the
   confirmation run — and per `PHASE_28.md` §5 it is not optional, because a candidate that wins
   on stored prompts can lose 7 points end to end.
3. **Every API output is written down and re-read, never re-asked.** Already true structurally:
   `llm/cache.py` keys on `sha256(provider+model+prompt+params)`, `calls.jsonl` keeps the full
   record. The rule is therefore mostly a prohibition — never clear the cache to "get a clean
   run", never bypass `llm/client.py`.
4. **Every number lands in one ledger.** This project is **not** on a research-publication
   pathway, so there is no paper to be the durable home for a figure. `docs/MEASUREMENTS.md` is,
   as of today: append-only, one row per value, each with the command that reproduces it and the
   run that produced it.

Rule 4 is the one that changes how the project is documented. `LOG.md` and the handovers keep the
narrative; the ledger keeps the numbers, including the ones that turned out to be artefacts.
`ConvinceMe.md` and `Guide to Publishing.md` stay in the repo as design pressure — the standard
they set for an unaudited headline number is exactly the standard the ledger enforces — but they
no longer describe a destination.

### The target

> *"the target is for the final output to have enough structurally well balanced well connected
> information that rivals a professional wiki-fandom page."*

Written into `CLAUDE.md` as a new §2b. What it means concretely, and why each of these is a
separate thing from recall:

- **Balanced.** Every character page carries the same sections filled to a comparable depth. A
  page that is correct but 70 words next to one of 1,497 does not read as the same wiki.
- **Connected.** Every named entity on a page is reachable by a link, in both directions. A
  one-way edge — Holo's page links to Pasloe, Pasloe names Holo in plain text — is the failure
  mode that is easiest to miss, because `wiki audit links` only checks that emitted links
  *resolve*, never that a name that should be a link is one.
- **Honest.** No page asserts something the text or the art does not support. This is where the
  images work landed: a caption naming a character is a claim about the picture, and nothing in
  this pipeline can see a picture.

**Decision: measure the target before improving it.** `docs/MEASUREMENTS.md` §3 is the structural
baseline — page-length spread, per-section fill rate, link count, portrait coverage — taken today,
before any of the changes below. Without it "rivals a fandom page" stays an opinion.

### Rejected, with reasons

- **Giving locations and factions their own pages** (the obvious fandom-wiki move). Rejected:
  `CLAUDE.md` §2 says only characters get unique pages, and that rule exists because a page per
  entity multiplies the spoiler surface and the synthesis cost by the entity count. The codex
  anchor (`/codex/<kind>#<slug>`) is already a real link target; connectivity does not require a
  file per entity.
- **Category pages** (`categories:` is already in every page's front matter and rendered by
  nothing). Deferred, not rejected — it is the cheapest remaining fandom affordance, but it is
  additive and the imbalance in §3 is the larger gap. Note that `categories` is currently `[]`
  for Holo, so the field would need populating first.
- **An infobox table.** Rejected as cosmetics: the `Overview` bullet strip already carries exactly
  the structured fields an infobox would, deterministically from graph rows.
- **Filling the short pages with prose.** Rejected outright — it is the one thing that would break
  `CLAUDE.md` §2's "zero evidence means `null`, never an invented sentence". A 70-word page is
  short because the corpus says little about that character, and that is the correct output. The
  fix for imbalance, if there is one, is more *evidence* reaching synthesis, not more words.

### Shipped today (all of it zero-cost — see `docs/MEASUREMENTS.md` §5)

Four defects, each a case where the emitter said something the data did not support:

1. **`members` and `adversaries` were not mutually exclusive.** Milone Company printed "Members:
   Kraft Lawrence, Marheit" directly above "Adversaries: Kraft Lawrence, Yarei". Both intervals
   are real (an employee who is also betrayed), but the reader sees a contradiction. Membership
   now wins, in `site/bundle.py::_members_and_related` — one place, every caller.
2. **Codex roster names were plain text.** Now links, via a new `_entity_link`. This was the
   one-way edge described above.
3. **The codex `related` bucket was information-free.** Every place and faction alike listed the
   same four globally-central entities, because that is what personalized PageRank returns on a
   2-volume graph. No longer rendered; still computed, still in the bundle, still in CONTRACTS
   §6.1. Re-render it if a bigger graph makes the neighbour sets differ per entry.
4. **An art plate was the "portrait" of up to three different characters at once.** The v01
   frontispiece ran at the top of Holo's, Lawrence's and Yarei's pages, captioned with each of
   their names. `cover_image_for_entity` can only answer "which plate is nearest this character's
   debut" — nothing here can see the image — so the fix is a cap, not a better guess:
   front-matter plates only for the volume's two leads, and any plate on at most two pages.

Plus: an empty codex kind (`tech.md`, a bare `# Technology` heading) is no longer written, linked
from the volume index, or placed in the nav; and `tests/test_audit_html.py`'s fixture now
redirects `paths.SITE_DIR`, which it never did — an unpatched test writing into the repo's real
(gitignored) `dist/wiki` made every other test in that file fail on links it had not written.
