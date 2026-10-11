# Phase 26 — Citable pages: evidence anchoring, relation coherence, alias hygiene

Append-only, newest entry at the bottom (CLAUDE.md §4). Phase 25 fixed eight named flaws in what
the pipeline *produces*; this phase fixes what makes the produced pages *trustworthy* — citations,
contradictions, and the alias noise that mislinks them. Scope stays spice-and-wolf v1-2
(`AGENTS.md` §3).

## 2026-09-20 — Audit of the shipped wiki, and the requirement that came out of it

The user asked for an audit of `dist/spice-and-wolf/wiki/` against a real Fandom character page as
the reference. The page *skeleton* already matches (Overview → Appearance → Personality → History →
Quotes → Affiliations → Relationships → Appearances) and the History prose is good. What a Fandom
page has and this does not:

- **Citations.** Zero of 66 emitted pages carry a single source reference, although every claim
  stores verbatim evidence plus `para_id`, and `site/bundle.py::_citations_for` already computes
  `{para_id, vol, print_page}` — `site/mkdocs_wiki.py` simply never reads it.
- **Non-contradictory relations.** 5 entity pairs carry antonym predicates simultaneously.
  `dist/.../v02/character/liebert.md` renders `Status: alive` and `Holo — Killed` on one page; the
  `KILLED` claim (conf 0.96) and a `SAVED` claim (conf 0.95) cite *the same sentence*, "Holo shook
  her head slightly and let the man drop to the ground."
- **Explained relations.** 24 of 89 (27%) render as a bare predicate. Worst where the explanation
  carries the meaning: `FRIEND_OF` 7/12, `ENEMY_OF` 7/16, `RIVAL_OF` 2/3. The user's words:
  "'friend of' doesn't make much sense."
- **Notable quotes.** 765 Holo quotes available; the page ships `"Listen, you"`. Cause:
  `synth/assemble.py` ranks by extraction confidence, which spans only 0.89–0.98 across all 1,968
  quotes, so the top-3 is effectively arbitrary DB order.
- **Trustworthy verdicts.** `verify` returned 747 `supported` / 1 `unsupported`; `support_score` is
  NULL on all 748 rows, because the runs that wrote them did not pass `--nli`.

Requirement added by the user in the same message: **every claim should hyperlink to the exact
point in the source it came from**, with an EPUB→PDF wrapper as an acceptable fallback.

## 2026-09-20 — Decision: synthesize anchors from parsed data, not from the EPUB

Measured, not assumed, before choosing:

| Finding | Number |
|---|---|
| `<p>` elements carrying an `id` in SaW v02 | 0 (3,561 `<p>`, 108 `id=` attrs total) |
| `page-N` anchors in SaW v02 | **54**, for 3,529 paragraphs (~1,338 words apart) |
| `page-N` anchors in 86 v01 | 243 |
| paragraphs whose stored `chapter_id` names the wrong source file | ~60% of v02 |

**New corpus trap (CLAUDE.md §3 trap 8 does not generalise).** Trap 8 says `<a id="page-N">`
markers "give free print page numbers for citations". True for the 86/Stick EPUBs; the LuCaZ Spice
and Wolf EPUBs are 4.5× sparser, at roughly one anchor per 65 paragraphs. Print page is a usable
*label*, not a usable *anchor*, for this series.

**Second trap, new:** `ingest/epub.py` stores only the `<section id>` of a chapter's *first* XHTML
document (`:215`, `:226`), but a chapter absorbs continuation spine docs (`:218`, `:230`). v02
chapter 0 is `chapter002.xhtml` (191 paras) + `chapter004.xhtml` (339 paras), all recorded as
`chapter002`. Any scheme that maps a `para_id` back onto a source file by `chapter_id` is wrong for
the majority of paragraphs. The spine href is computed at `:146` and discarded at `:147`.

**Decision: render a source view from `data/<series>/01_parsed/vNN.jsonl`**, one Markdown page per
chapter per cutoff dir, each paragraph stamped `{: #nw-<para_id> }` via the `attr_list` extension
the emitter already enables. The anchor is correct by construction because it addresses the exact
normalized text the extractor saw — no EPUB re-parsing, no continuation-file ambiguity, no new
dependency, and it composes with the existing cutoff filtering so `vNN/source/` can only hold
volumes ≤ NN.

**Rejected, with reasons:** EPUB mirror with injected ids (needs a full re-parse to resolve the 60%
wrong-file problem, and ships the book as browsable HTML); EPUB CFI + epub.js (no Python CFI
generator exists, so ~80 hand-rolled lines plus a JS dependency, buying portability to external
readers that nothing here needs); EPUB→PDF wrapper, the user's own suggested fallback (external
converter binary, page-level precision only, page numbers drift with converter settings). The
fallback is not needed — the derived view is both cheaper and more precise than it.

## 2026-09-20 — Correction: `--nli` as default is NOT the fix for the verifier

The audit's conclusion "make `--nli` the default" was drafted before reading
`docs/vision/PHASE_24.md`'s entry of the same day, which records that this exact change was already
tried and measured: at the flat 0.5 threshold MiniCheck flags **66 of 123 facts (54%)**, and the
flagged set is almost entirely relations — `ENEMY_OF` 22, `COMRADE_OF` 18, `FRIEND_OF` 16,
`COMMANDS` 15, `SAVED` 9, `RIVAL_OF` 6, against `AGE`/`ORIGIN`/`GENDER` 1 each and `OCCUPATION` 0.
Novels show a relationship through scene and dialogue rather than stating it in the predicate's own
words, so relation evidence is close to definitionally inferential; MiniCheck was built for literal
summary-vs-source checking and reads it as unsupported. A hand spot-check found a
correctly-extracted, well-evidenced `MENTOR_OF` scoring 0.038.

Phase 26 therefore adopts PHASE_24's own named next step rather than re-litigating it: **scope NLI
support scoring to attribute claims, where R21 proved it on the Zheren `OCCUPATION` case, and give
relation predicates a separately calibrated threshold or a different verifier.** Measure with the
existing `docs/eval/nli_controls.py` harness before changing any default. Flipping the flat flag
would reshape what ships to readers by half, which stays the maintainer's call.

## 2026-09-20 — Part A shipped: the render layer

Everything below is rebuildable from the existing `graph.db` — no re-extraction.

**Source view + citations.** `site/mkdocs_wiki.py` emits `vNN/source/`, one page per (volume,
chapter), every paragraph stamped `{: #nw-<para_id> }`. Quote attributions carry the speaker and
a source link; prose sections carry a `Sources:` footer (capped at 6 links, relation bullets at
3). `site/bundle.py::_citations_for` already produced the data — nothing read it. Verified with a
real `mkdocs build --strict`: the stamps materialise as HTML ids, so the links resolve in the
rendered site. **595 citation links, 0 broken; 21/21 character pages cited, from 0/66.**

**SAVED/KILLED arbitration.** Declared mutually in `config/extraction.yaml`, plus `object_display`
so the victim's page reads "Killed by". Found a latent bug doing it: `pair_claims` buckets every
conflict-group predicate for a pair and arbitrates to ONE survivor, but `conflicts_with` is a
graph, not a partition. New `_conflict_cliques` partitions by actual pairwise conflict.
**Genuinely contradictory live pairs 5 → 0.**

*COMRADE_OF/ENEMY_OF was tried and reverted after measuring it.* It is not a true exclusion —
COMRADE_OF's own note scopes it to travelling/working together, and Holo travels with Norah while
hostile to shepherds. Worse, declaring it lost a true fact: a spurious `kraft-lawrence ENEMY_OF
holo` pulled the genuine COMRADE_OF into a three-way clique and arbitration dropped it. Recorded
in the config beside the rule it would have broken.

**Quote notability.** Ranking was by extraction confidence, which spans 0.89–0.98 across 1,968
quotes and so left the top-3 as arbitrary DB order. Replaced with a length/completeness/
first-person/scene heuristic. `"Listen, you"` fell from **rank 1 to 725 of 765**.

**Relationships.** Grouped under one `### Name` heading per related character (was 31 flat
bullets, 9 of them Lawrence, non-adjacent), places and organisations split out, and a generated
2–4 sentence paragraph per pair — one LLM call per page, not per pair, so the model can reconcile
conflicting predicates. It does: on the spurious Weiz romance edge it writes "rather than a
documented close friendship or romance"; on the weak Count Ehrendott edge, "Holo has no direct
interaction with Count Ehrendott."

**Affiliations.** All four of Holo's AFFILIATED_WITH edges were non-membership, and the page led
with "alive · Medio Company" — her captor — because `_build_lead` took the alphabetically first.
Two guards: a qualifier-marker check, and an adversarial-relation check that catches the one no
keyword list can (The Church, qualifier "member", ENEMY_OF at confidence 1.0). Non-membership ties
render under "Other ties".

**Aliases and links.** Nothing from the `epithet_mining` channel is hyperlinked any more
(`extract/scenes.py::_build_epithet` applies no content filtering beyond a confidence floor, and
the `ambiguous` flag cannot catch a generic noun claimed by exactly one entity). **False
hyperlinks 21 → 0.** Front matter keeps a mined form as an alias only when it reads as a name;
Holo's list went from 45 entries to 9.

**Navigation and images.** Generated `nav:` (there was none, while the home page told readers to
use it); Source/Timeline/Illustrations linked from each volume index. Images were purely a stale
parse — the manifest is only written for volumes parsed on a run. Verified ingest is idempotent
(both jsonl files hash byte-identical after a forced re-parse, so every `para_id` and therefore
every citation survives), then re-ingested: 42 illustrations, every character page has a
thumbnail.

**`wiki audit links`: FAIL → OK.** The `may-god` mining artifact reached timeline bundles because
Phase 23 E6's `written_ids` filter was applied after they were built; `build_links`'s membership
rule is now factored out as `_resolves` and both use it.

### Papers — added to the script, fetch pending

`docs/fetch_reference_pdfs.py` gained four ids, each verified by hand to resolve to the intended
paper: 2406.06125 (sub-sentence citation granularity — the comparison behind choosing a
per-paragraph anchor), 2508.15396 (evidence-based generation survey), 2502.12124 (RA-MTR, quote
extraction as retrieve-then-rank — the comparison for `_quote_notability`), 2505.24553 (CREFT,
character relation extraction — the comparison for `generate_relationship_prose`).

**The PDFs are NOT downloaded and `docs/REFERENCES.md` is NOT updated**: the arXiv API returns
HTTP 406 from this environment for every User-Agent tried, so the script cannot run. That file is
machine-generated and must not be hand-edited, and `docs/PAPERS.md` rows are keyed by a filename
that does not exist yet, so neither was touched. `python docs/fetch_reference_pdfs.py` from a
network that can reach arXiv completes this; until then `--check` correctly reports the four as
"has no PDF on disk", which is the pending-work marker the script exists to surface.

---

## 2026-09-20 — Part B, measured on a full v1-2 re-run

Part B's three extraction gates (committed 2026-09-20, unverified until now) were run against the
real corpus end to end: `scenes --force` → `gazetteer --merge-epithets` → `extract --force` →
`graph build` → `events-build` → `synthesize` → `site build`. What the re-run settled:

**The gates hold.** Bare social relations (`FRIEND_OF`/`ENEMY_OF`/`RIVAL_OF`/`COMRADE_OF` with no
qualifier) went 31 of 70 → **0 of 54**; `requires_qualifier` fired 22× across the two volumes.
`requires_both_endpoints` on SAVED/KILLED dropped 24 claims including `holo SAVED yarei`, the
claim that motivated it. `object_status_implies` had nothing to arbitrate this run — the re-run
produced no evidenced STATUS for Liebert at all, so `holo KILLED liebert` was instead dropped by
the endpoint gate. That is the right outcome by a different route, and it means the
attribute-vs-relation check is still unexercised on live data.

**Prompt guidance is not a gate.** RELATIVE_OF's note has said "an ANIMAL — a pet, a horse, a
working dog — is never a relative" since the previous commit. The model emitted
`norah-arendt RELATIVE_OF enek` **and** its inverse anyway, qualifiers "pet" and "shepherd's
sheepdog". All three of `wiki audit eval`'s negative-fact violations were RELATIVE_OF claims whose
own qualifier stated why the predicate does not hold (the third: "pretended debt as excuse to
remain together"). New `qualifier_disqualifiers` — a per-predicate, case-insensitive substring
list enforced in `extract/adequacy.py`. Blunt on purpose and scoped to the one predicate where the
failure was measured; a global rule would be guessing. 5 drops per volume on live data.

**A cap that raises is a cap that can kill a stage.** `_prose_schema_for`'s sentence ceiling
raised so the client would repair-retry. `nex-n2.5-pro` then returned 14 sentences against a
12-sentence cap on all three attempts for one character, aborting all of
`wiki synthesize --upto 2`. It now trims to the first `max_s` whole sentences. Considered and
rejected: raising the cap (it is the runaway-verbosity guard Phase 25 item 7 added for a reason),
and a fourth retry (three failures on a deterministic prompt is not bad luck).

**A link filter must be keyed per cutoff, not per build.** `wikify_text` linked any revealed
entity; `okf.py::_label` linked any relationship partner. Both shipped links to pages the
`page_gate` never wrote — `[Jakob](../character/jakob.md)` on v01's Lawrence page, 293 broken
bundle references. The fix is keyed on the cutoff being rendered, because
`mkdocs_wiki.py::resolve_cutoff` emits a character at volume N iff it has a page at some cutoff
≤ N: Jakob is a live target at v02 and a 404 at v01. `mkdocs_wiki.py` passes the exact set of
files it is about to write, which is the only source that cannot drift from disk.

**Known still-open, all extraction-side and all in KILLED.** The re-run produced
`holo KILLED yarei` (from "The image of Yarei's torso in Holo's fangs came unbidden to Lawrence's
mind" — imagined), `kraft-lawrence KILLED liebert` (from "If it had been up to Lawrence, he would
have killed the man" — counterfactual; the previous run marked it `presumed`, this one
`asserted`), and `holo KILLED pazzio` (object is a town). Only the last has a deterministic fix
that needed no judgement, and it is in: `object_types: [CHARACTER]` on KILLED and SAVED, which
routes through the existing `object_type_mismatch` drop. Irrealis — imagined, counterfactual,
intended — is the remaining class, and it is NOT closed: the hedging guidance added for part B
covers "may have"/"seemed to", not "would have"/"the image came to mind".

## 2026-09-21 — Part C: evidence has to describe something that happened

Part B's gates all answer *who is named in the cited paragraph*. None of them asks whether the
sentence describes a real event. That is fine for a bond (FRIEND_OF is about a standing state) and
fatal for an act: with KILLED and SAVED, the event **is** the whole fact, so a counterfactual or
imagined sentence is not weak evidence, it is evidence of the opposite.

The live v1-2 graph proved it twice, both at confidence 0.99:

- `holo KILLED yarei` — "The image of Yarei's torso in Holo's fangs came unbidden to Lawrence's
  mind." An image in a character's head.
- `kraft-lawrence KILLED liebert` — "If it had been up to Lawrence, he would have killed the man."
  An explicit counterfactual, and the qualifier the model itself attached ("expressed an intent to
  kill him") says so.

Both quotes name both endpoints, are verbatim, are in-volume, and are longer than the word floor —
every part-B gate passes them. SAVED's prompt note has warned against hedged narration since part
B and was ignored, which is the same lesson RELATIVE_OF taught: **prompt guidance is not a gate.**

**Neither one currently renders — and that is exactly why the gate is needed.** Checking the
`intervals` table rather than the `claims` table shows both were dropped downstream by mechanisms
that have nothing to do with realis: `holo KILLED yarei` by `rule:object_status_contradicts`
(Yarei's own evidenced STATUS at v1 is "unconscious", and KILLED implies "dead"), the two KILLED
Liebert claims by the SAVED/KILLED `conflicts_with` arbitration added earlier in Phase 26. Remove
either coincidence — a victim with no evidenced STATUS, a killing with no competing SAVED claim —
and the false relation renders. The claims also survive in `claims`, which is what `explain`,
`trace` and PPR read. A fact that is wrong should be dropped for the reason it is wrong.

**Decision:** a deterministic `irrealis_markers` substring list under `evidence_adequacy`, matched
against the *cited quote* (what the model offered as proof, not the surrounding paragraph), and
applied only to predicates that opt in with `requires_realis: true` — KILLED and SAVED today.

**Rejected: applying it to every predicate.** "He may have been her friend for years" is a weak
FRIEND_OF, not a false one. A corpus-wide hedge filter would cost far more history than it buys,
and the two predicates where irrealis is fatal are exactly the two where the event is the fact.

**Rejected: an LLM realis check.** A per-fact "did this happen?" call is one more call per relation
in the stage that already hits the daily cap, to decide something four substrings decide.

Every marker in the shipped list was lifted from a quote that actually put a false relation into
the live graph, including two not previously logged: `holo SAVED norah-arendt` ("he would just
have Holo rescue her if need be") and `norah-arendt SAVED kraft-lawrence` ("if Norah were to take
the gold and disappear").

## 2026-09-21 — The shipped wiki was serving pages its own graph no longer supported

Found while chasing the above: `dist/.../wiki/v02/relationships/holo--saint-ruvinheigen.md`
asserts "Holo — Killed — Saint Ruvinheigen". No such claim, interval or edge exists in `graph.db`,
and no such bundle exists in `06_bundle/` — the file was written by a build on 09-17 and simply
never removed. Twelve pages across the two cutoffs were in this state (98 emitted → 86 after the
fix), each one a page some earlier graph supported.

`wiki audit links` is structurally unable to catch this, and passed OK on every one of those
builds: a stale page's own links resolve fine. What is wrong is the page's *existence*.

This is a spoiler-safety hazard, not just staleness. Every guarantee in CLAUDE.md §1 is about what
gets *written* into a cutoff dir; nothing was ever about what was already sitting there. A page
left behind from a build made at a higher `--upto`, or from a graph since corrected, is served to
the reader with the same authority as a current one.

**Decision:** `build_wiki` clears each cutoff dir before rewriting it. Every file under it is
regenerated from that run's bundles, so anything surviving is by definition unsupported. `img/`
is deliberately outside the cutoff dirs (shared, copied once per build) and is untouched.

**Rejected: a stale-page check in `audit links`.** It would report the problem one command later
than the build that caused it, and the fix for every report would be "delete the file". Not
writing the state is cheaper than auditing for it.

## 2026-09-21 — A gate in the extractor does not fix the graph you already have

`object_types: [CHARACTER]` was added to KILLED/SAVED yesterday and logged as "in but unverified".
Checking it properly showed something worse than unverified: the live wiki was rendering
`holo KILLED pazzio` — Pazzio is a town — on a graph built *after* the gate landed. The gate is in
`extract/claims.py` and `extract/scenes.py`, which only ever see claims being extracted now. The
claim files on disk are never revisited, so every constraint added to the extractor leaves the
existing graph exactly as wrong as it was, and only a full `extract --force` (the thing the daily
cap has blocked for two days) would apply it.

**Decision:** enforce the same `object_types` config in `build_graph` as well
(`_strip_object_type_mismatches`), alongside the existing `object_status_implies` strip. A
predicate's admissible object type is a schema constraint on the graph, not a property of one
extraction run — and enforcing it where the gazetteer's types are known costs one dict lookup per
relation claim and no LLM call. `entity_types` is an optional argument, so callers without a
gazetteer (most tests) are unaffected.

Rebuilt on the existing claims: one drop, `rule:object_type_mismatch`, and no KILLED relation
renders anywhere in the v1-2 wiki now. The general form of the lesson, worth applying to the rest
of part B's gates: **a check that lives only in the extractor is a check on future runs, not on
the artifact.** Anything expressible against the graph should also hold at graph build.

## 2026-09-21 — The daily cap is a CALL budget, and the pipeline spends it on empty requests

The free tier allows 1000 calls/day, not 1000k tokens. A full two-volume run costs about 670:

| stage | calls (v1-2) | shape |
|---|---|---|
| `claim_extract` | 359 | one call per (character, window) |
| `scene_extract` | 113 | two calls per chapter span (beat, then detail) |
| `codex_summary` | 67 | one per codex entry per cutoff |
| `prose` | 57 | one per (character, cutoff), already collapsed by `synth/cache.py` |
| `verify` | 38 | one per character per cutoff |
| `arbitrate` + `canonicalize` | 36 | one per unresolved contradiction |

Two volumes of seventeen, and one run already eats two thirds of a day. At thirteen volumes a
single run is roughly 4400 calls — four and a half days of quota. This is not a "we hit the cap
once" problem; the pipeline as shaped cannot complete a full series inside the free tier.

`claim_extract` is where the waste is, and it is not subtle. Measured over one real run: **median
3.6k tokens in, 216 out**, of which ~2.2k of every single input is the same system prompt
(the full attribute/relation/trait vocabulary) re-sent. The stage sends 359 near-empty requests
against a model whose context is an order of magnitude larger than what each one uses.

**Decision:** pack several windows into one request (`windows.pack_windows`, config
`extraction.window.max_windows_per_request`). Windows are already disjoint passages; packed ones
are joined by an explicit passage-break marker and every paragraph keeps its `[para_id]` label, so
every downstream check is untouched — `normalize_para_id`, the verbatim-quote test and
`passes_evidence_adequacy` all still resolve each fact against the one real paragraph it cites.
Measured offline against the real v1-2 corpus: **359 requests → 101 at 4 per request.**

The batch is bounded by a window COUNT, not only by the input budget, because the binding
constraint is the OUTPUT cap (4096 on the free profile): facts scale with passages, p99 output is
already 2386 tokens for a single window, and a truncated JSON costs a repair retry — spending the
call the packing just saved. The input budget is the profile's own usable context where it
declares one (so a local run never builds a request it cannot send) and `max_request_tokens`
otherwise.

**Shipped at 1 — off.** The only model reachable the day this was written was local qwen2.5:14b,
OpenRouter having been at 0/1000 since the previous evening. Packed at 4 it returned 101 facts
whose quotes were not verbatim in the paragraph they cited (against 3 facts unpacked) — the
cached response shows it appending attributions to quotes, e.g. `"Oh, Mr. Zheren? I know of him."
- The girl at the tavern`. That is plausibly this model's own documented weakness at this stage
rather than the packing, but plausibly is not measured, and this repo's own standing lesson is
that a config flip is not verified until it has been smoke-tested against the model that will
actually run it.

**The flip is one config line after one ~10-call comparison** — same character, same volume, both
settings, comparing claim count and the `quote_not_verbatim` drop counter:

```python
settings.extraction_behaviour["window"]["max_windows_per_request"] = per   # 1, then 4
claims, drops = claims_mod.extract_character_volume(
    entity, vol, records, mentions, entities_by_id, settings, client, max_windows=6)
```

**Rejected: one chapter-major call for all characters at once** (what `scene_extract` already
does). It would cut deeper — ~113 calls instead of 359 — but it discards `claim_extract`'s
"one subject per call" invariant, which is the reason the stage resolves subjects reliably at all;
`subject_must_be_named` exists precisely because chapter-major resolution is where subject
attribution goes wrong. Packing keeps one subject per call and takes most of the win.

**Rejected: shrinking the window pool** (`max_windows_per_entity_per_volume`). Fewer calls by
extracting from less of the book is not an optimisation, it is a quality cut with a cost line.

**Next levers, in order, if 1000/day still binds after packing lands:** merge `scene_extract`'s
beat and detail passes into one call (113 → 56); batch `codex_summary`, which is one *sentence*
per call for 67 calls and is the most obviously batchable stage in the pipeline; then `verify`.
And the standing one that costs nothing: the LLM cache is keyed on the exact prompt, so batch
prompt-affecting config edits together — every edit to a predicate's `note:` invalidates the whole
`claim_extract` cache, because the vocabulary block is in every prompt. Three of the four
extraction re-runs on 2026-09-20 were full-price for exactly that reason.

## 2026-09-21 — Standing rule: quality is never traded for call count

Maintainer instruction, in response to the packing analysis above: *"do not make any modification
that might sacrifice quality of the output. if keeping separate multiple prompts is better then do
that."*

So `max_windows_per_request` stays at **1** — one window per `claim_extract` call — and the packing
mechanism stays as an off-by-default lever rather than something to reach for when the cap bites.
The bar for ever turning it on is a real A/B against the routed model showing equal claim yield and
no rise in `quote_not_verbatim`; absent that measurement, the separate prompts win by default. The
same bar now applies to the other call-saving ideas listed above: merging `scene_extract`'s
beat+detail passes and batching `codex_summary` are both quality-affecting and neither is to be
done on cost grounds alone.

Cost savings that cannot touch quality remain fair game and are the preferred response to the cap:
reusing the prompt-keyed LLM cache, batching prompt-affecting config edits so the cache is
invalidated once rather than four times, running `--volumes N` in daily slices, and simply waiting
for the 00:00 UTC reset. The cap is an operational annoyance; a quality regression is baked into
the artifact and is far more expensive to find and undo.

## 2026-09-21 — `audit eval` fact recall conflates three different failures

Chasing the jakob/norah-arendt drops in the nex-pro prose re-run (LOG 2026-09-21) showed the metric
is measuring three unrelated things at once, which is why it is a poor gate and why chasing a
single number was pointing at the wrong layer each time.

**1. Extraction coverage (jakob — a real gap, worth fixing).** Jakob has **9** trait claims. The
nex-pro prose used essentially all of them (formidable, cunning, crisis-seasoned, consoling,
grand speeches, sharp-eyed, lie-detecting). The gold facts it "missed" — *"very friendly man,
usually with a smile"*, *"treats guild members like his own sons"* — have **no claim at all**, yet
the corpus plainly supports them: `v02:c02:p0191` "Jakob broke into a grin", `p0195` "Jakob's laugh
rang out again", `p0229` "Jakob smiling pleasantly", `p0184` "harsh edge and warmth". 14 paragraphs
pair Jakob with a warmth cue; extraction produced zero traits from any of them. The pattern: these
are **narrated behaviour**, not dispositional statements, and the trait extractor only fires on the
latter. Recall here is bounded by extraction, and no prose model can recover it.

**2. Prose length cap (norah-arendt — working as designed).** The opposite case: **68** claims,
including `MOTIVATION: to become a dressmaker` (x3) and `join a tailors guild`, `formerly lived in
an almshouse`, `watched by The Church`. The gold facts scored "not recalled" are *in the graph*.
They are absent from the page only because `background`/`personality` prose is capped at 2-4
sentences (CLAUDE.md §2) — a deliberate constraint. Fact recall against a full Fandom page is
therefore **structurally bounded well under 100%**, and pushing it up would mean breaking the cap.

**3. Lexical synonym blindness (both).** Gold *"dreams of becoming a tailor"* vs the page's
"dressmaker" is a miss by keyword overlap alone. Same class as the liebert case in LOG.

**Consequence, not yet acted on:** a single `fact_recall` float gating pass/fail cannot separate
"we never extracted it" from "we deliberately did not print it". The gate should be split, or at
minimum the report should mark, per missed fact, whether a supporting claim exists in the graph —
that one bit turns the metric from a score into a diagnosis and is computable with no LLM call.
Left as a named next step rather than built, since it changes what `audit eval` asserts.

## 2026-09-21 — Measured: relations need a different verifier, not a different threshold

PHASE_26's 2026-09-20 entry left a fork — *"give relation predicates a separately calibrated
threshold **or** a different verifier"* — and required measurement before any default changed.
Measured, with `docs/eval/nli_kind_sweep.py` (new, reproducible, checked in alongside its report):
MiniCheck over **all 206** arbitration-scope v1-2 claims with a hypothesis template, not the five
hand-picked cases `nli_controls.py` covers. Local classifier, zero API calls.

```
attribute   n= 97  median 0.778  p90 0.972   flagged@0.5 40%  @0.1 23%  @0.02 7%
relation    n=109  median 0.097  p90 0.928   flagged@0.5 76%  @0.1 52%  @0.02 7%
```

**The fork resolves against the threshold.** A separate relation cutoff would only work if the
score separated good relations from bad ones. It does not:

- The relation distribution is **bimodal, not shifted** — median 0.097 but p90 0.928. Within one
  predicate: `ENEMY_OF` median 0.065 / p90 0.917, `FRIEND_OF` median 0.040 / p90 0.900. No cutoff
  splits that into "correct" and "incorrect"; it only chooses how many to discard.
- PHASE_24's hand-verified, correctly-extracted `MENTOR_OF` scored **0.038**. This sweep puts
  `rel:MENTOR_OF` median at **0.039** — the known-good claim sits *at its predicate's median*, so
  for that predicate the score carries no information about correctness at all.
- Lowering to 0.02 makes relations and attributes flag at an identical 7% — i.e. the only cutoff
  that stops over-flagging relations is one that stops flagging almost anything.
- MiniCheck score vs the extractor's own confidence: Spearman **+0.25** for relations (low-scorers
  and high-scorers share an identical 0.99 median confidence). Weak evidence, since confidence is
  near-constant across this corpus, but it points the same way.

**Attributes are the usable half**, as PHASE_24 predicted: median 0.778, and the deterministic-ish
predicates cluster high (`GENDER` 0.967, `STATUS` 0.879, `OCCUPATION` 0.805). `RANK` is the outlier
at 0.249 — its values are long descriptive phrases ("held an indispensable standing in the city"),
which is a hypothesis-template problem, not a classifier one.

**Not shipped, deliberately.** The 2026-09-20 entry states that reshaping what readers see "stays
the maintainer's call", and scoping `--nli` to attributes means relations lose their only
per-fact check unless a replacement lands in the same change. So this entry ends where the
evidence ends: the threshold branch is closed, and the next step is choosing the relation
verifier (the obvious candidate being the existing chat `verify` stage, which already reads a
fact against its own cited evidence, kept for relations while attributes move to MiniCheck).

## 2026-09-21 — The stored graph is not reproducible to within 16%, and it confounded this phase's own A/B

Found while running a control for the narrated-behaviour trait change. Re-extracting **Holo**
today against the **byte-identical prompt and model** that produced the stored claims yields
**235 claims where the stored file has 280** — a **16% swing from sampling alone**, at the
profile's own temperature, with the same windows, same gazetteer, same mention index.

**This invalidates a comparison this project keeps making**: fresh extract vs stored baseline.
Three-way, same character, same day:

| Holo | claims | PERSONALITY |
|---|---|---|
| old prompt, earlier run (stored) | 280 | 26 |
| old prompt, **today** (control)  | 235 | 20 |
| new prompt, **today** (treatment)| 234 | 28 |

Read against the stored baseline, the new prompt "lost 46 claims" and looked like a regression.
Read against its own same-day control it is **claim-neutral (234 vs 235) and trait-positive
(20 → 28)**. The first reading was an artifact of comparing across runs. Corrections this forces
to numbers reported earlier the same day: `hans-remelio` 8 → 6 is **inside the noise band** and
is not evidence the change did anything to him, and `jakob` 13 → 16 is only trustworthy because
the *kind* of claim added (three grounded PERSONALITY traits where there were zero) is a
categorical change, not a count that noise could produce.

**Consequences, none of them yet acted on:**

1. `docs/handover/PHASE_26.md` §7 tells a cold contributor those commands reproduce the
   deliverable. They reproduce its *shape*, not its contents to better than ~16%.
2. Any future extraction A/B **must re-run both arms in the same session**. A stored baseline is
   not a control. `docs/eval/nli_kind_sweep.py`-style measurement is unaffected (it scores a
   fixed claim set); this hits `extract` comparisons only.
3. A full re-extract is therefore not a free upgrade: it would churn ~16% of the corpus's claims
   for whatever the prompt change is worth, and those are two separate trades. This is the real
   reason the narrated-behaviour change is NOT rolled out beyond Jakob — not that it is unproven
   (it is proven, holding the run fixed), but that the vehicle for shipping it is lossy.
4. Worth measuring next, cheaply: whether the variance is the model's sampling or this pipeline's
   own window/adequacy gates. The control's drop reasons differ sharply from the treatment's
   (`window_cap_truncated` 36 vs 2, `subject_not_named_in_paragraph` 74 vs 181), which suggests
   the gates amplify small generation differences rather than merely passing them through.

## 2026-09-21 — CORRECTION: the "16% sampling variance" was a window-budget bug, not sampling

The entry above ("The stored graph is not reproducible to within 16%") is **wrong in its cause**
and is retracted here rather than edited, per this file's append-only rule. The numbers in it are
real; the explanation is not. Chasing it to the bottom found a live bug.

**What actually happened.** Re-extracting Holo "on the byte-identical prompt" was not
byte-identical at all, and the cache proved it: zero of the 80 new prompts matched any of the 361
stored ones. Two separate causes, found by diffing `calls.jsonl` between runs:

1. **The system prompt is identical (sha `b92cbedd`, 8788 chars), but the USER prompt changed.**
   Commit 46e7029 (packing, shipped OFF) rewrote the per-request header unconditionally —
   "Passage (each paragraph labeled with its id)" became "Passages (… a passage break means …)"
   — so it invalidated the entire `claim_extract` cache for a feature that never activates.
   Verified: 0 actual `PASSAGE_BREAK` separators in any of the 80 prompts.
2. **The real cause of the claim drop: `extract_volume` sized the window pool over the FILTERED
   character list.** `allocate_window_caps` sets `total_pool = base_cap * len(mention_counts)`,
   so passing only the targeted characters collapses the whole pool to fit them. Measured:

   | Holo's window cap | v1 | v2 |
   |---|---|---|
   | full run | 105 | 116 |
   | `--entities "Holo"` | **40** | **40** |

   That is where `window_cap_truncated: 36` came from: 36 evidence windows built and then thrown
   away before the model ever saw them. Not sampling — **a targeted top-up was reading a
   quarter of the evidence a full run reads.**

**Why this one stings.** `wiki audit eval`'s own low-recall hint recommends
`wiki extract --entities "<name>"` as the remedy. The remedy was starving the character it was
meant to help, and it silently invalidated every targeted-vs-stored comparison made this phase —
including the trait A/B, whose "control" was run with `--entities "Holo"` and so was never a
control at all.

**Fixed** (`extract/claims.py`): the pool is sized over every CHARACTER in `all_entities`, which
is already in scope, so a narrowed run gets the same per-entity budget as a full one. Regression
test asserts the targeted cap equals the full-run cap; it fails `40 == 70` without the fix.

**What remains true from the retracted entry:** a stored baseline is still not a control, because
prompt edits invalidate the cache and re-run costs real calls. But the reason is bookkeeping, not
irreducible sampling noise, and the honest position now is that **run-to-run extraction variance
at fixed inputs has not been measured at all** — the one experiment that looked like it measured
variance was measuring this bug.

### Allocation policy: researched, deliberately NOT changed

The cap that truncates is top-k by `mention_count`, a pointwise density score with no
redundancy term. Three papers verified against the arXiv API and added to
`docs/fetch_reference_pdfs.py` (section B):

- **BEAR** (2601.18116) frames exactly this as *budgeted evidence allocation* across items under
  a query-time budget, via coarse-to-fine hierarchical access rather than a per-item quota.
- **Budget-Aware Routing for Long Clinical Text** (2605.00336) compares positional, frequency and
  diversity-aware (MMR) selection under a fixed budget and proposes RCD, a monotone submodular
  relevance/coverage/diversity objective — the direct comparison point for top-k-by-density.
- **EviRerank** (2411.06254) does information-density-aware adaptive budgeting per document.

**Not adopted, for two reasons that are measurements rather than taste.** First, 2605.00336
reports positional heuristics beating diversity-aware selection specifically on *low-budget
extractive* tasks, which is what this stage is; the paper does not endorse MMR here. Second and
decisive: with the allocation bug fixed, **0 of 359 windows are discarded corpus-wide** at two
volumes. The truncation branch never executes, so swapping its policy would be optimising a path
that does not run. Revisit if `window_cap_truncated` becomes non-zero as volumes are added.
