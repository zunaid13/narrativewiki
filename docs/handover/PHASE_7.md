# Phase 7 — Site (bundle, wikify, minimal static viewer)

**Closed:** 2026-09-02 · **Next:** scaffold the real `web/` Vite+React+TS SPA against the
existing `data/06_bundle/` contract (or another generative bundle field, if one comes up first)

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

```
src/narrativewiki/site/
  wikify.py       NEW. wikify_text(text, automaton, entities_by_id, settings, upto_vol, *,
                    exclude_entity_id=None) -> text with safely-revealed entity mentions wrapped
                    as Markdown links `[surface](route)`. Filters on THREE things before linking
                    a match: the target entity's own first_vol, the MATCHED SURFACE FORM's own
                    first_vol (an alias can be revealed later than the entity — CONTRACTS §2.1),
                    and `ambiguous` (never linked). No matching logic of its own — reuses
                    entities/automaton.py::MentionAutomaton.find_all verbatim.
  bundle.py       NEW. The Phase 7 core. Five builder functions (build_index/build_links/
                    build_search/build_pages_bundle/build_codex_bundles) -- see CONTRACTS §6 for
                    every output shape, which this phase wrote from scratch (§6 was previously
                    one paragraph and an illustrative, not-literal, example). build_codex_bundles
                    is also this phase's one new generative step: `codex_summary`, gated by
                    evidence exactly like Phase 6's prose (no evidence -> null, no LLM call).
  static_site.py  NEW. build_site(settings) renders site/templates/ into dist/site/ and copies
                    data/06_bundle/ alongside it. See "The web/ decision" below for why this
                    exists instead of a real SPA build step.
  templates/      NEW. index.html.jinja (one Jinja2 substitution: series title), app.js (~350
                    lines, vanilla JS, no framework, no build step), style.css. The reference
                    client for the bundle contract -- see "Things you need to know".
src/narrativewiki/cli.py
  site_build()    Wired end to end (was the last `_not_yet` stub). `--upto N` (required range,
                    like every other stage), `--force` (regenerate a codex summary even when its
                    evidence/members/related are unchanged from the previous cutoff -- does NOT
                    affect character pages, which are always a fresh copy of whatever `wiki
                    synthesize` already wrote), `--entities` (comma-separated names/ids, limits
                    which CODEX entities get processed -- mirrors `wiki synthesize --entities`
                    for a cheap smoke test; character pages/index/links/search are always built
                    for everyone since those are disk reads with no LLM cost).
  serve()         Wired: stdlib `http.server.ThreadingHTTPServer` over `dist/site/`. Blocks until
                    Ctrl+C, same as any dev server.
  run_all()       Now calls the real site_build() instead of stubbing.
  _PENDING/_not_yet  REMOVED -- every phase is now built, so the "not yet implemented" mechanism
                    had nothing left to guard. Re-add it (it is a ~15-line, self-contained
                    pattern; see git history) if a genuinely new not-yet-built pipeline command
                    shows up later.
src/narrativewiki/audit/reports.py
  _links_report   NEW, registered for `wiki audit links` (moved out of `_PLANNED`, which is now
                    also empty for the same reason as _PENDING above). Reads data/06_bundle/
                    directly (not via site/bundle.py) and checks every entity_id reference
                    (affiliations, relationships, mentions_of, codex members/related, index.json
                    roster) and every wikified Markdown link's route resolves against links.json.
tests/test_site_wikify.py    NEW. 9 tests.
tests/test_site_bundle.py    NEW. 10 tests.
tests/test_site_static.py    NEW. 2 tests.
```

`docs/CONTRACTS.md` §6 was substantially rewritten (not just extended) in the same pass — it
previously described `pages/{id}.json` as "all cutoffs, keyed by volume" without saying whether
that meant dense (all 13) or sparse (only changed ones), and `codex/*.json`'s example had no
cutoff dimension at all. Both ambiguities are resolved now — see "The two real judgment calls"
below. `docs/PROMPTS.md` rule #3 and its `codex_summary` subsection are new/updated for the prompt
bug this phase found (see "Things you need to know").

## Verify it in one command

```bash
wiki site build --upto 2 --entities "the-spearhead,sixth-sector,juggernaut"  # needs data/05_pages
                                                                              # from Phase 6
python -m pytest        # 191 passed
wiki audit links
wiki serve               # http://127.0.0.1:8080 — Ctrl+C to stop
```

**This ran for real** against the actual v01-02 data (Phase 3/4/6's real output): the command
above produced `data/06_bundle/{index,links,search}.json`, `pages/shin.json`, and one entry each
in `codex/{factions,places,tech}.json`. `wiki audit links` reported 119 routes, 0 broken
references. `wiki serve` on port 8099 (not the default, to avoid clobbering anything already
running) returned HTTP 200 for `index.html`, `app.js`, `style.css`, and every `bundle/*.json` file
`curl` was pointed at. `node --check app.js` passed, and the four pure JS functions that carry the
real logic (`parseRoute`, `nearestCutoff`, `renderLinkedText`, `escapeHtml`) were hand-verified
against real hash strings and real Markdown-linked prose via `node -e` — see the session transcript
if you need the exact commands again. No headless-browser/DOM test was run (no jsdom/puppeteer
installed in this environment); if one becomes available, that is the next rung of confidence for
`app.js` specifically.

## The `web/` decision

`CLAUDE.md`'s file map has always described `web/` as "Vite + React + TS SPA. The volume tab
drives every view from one state value" — but the directory was completely empty (no
`package.json`, no `src/`) when this phase started, and USER_GUIDE.md's `wiki site build`/`wiki
serve` descriptions ("builds the static site", "serves `dist/site/`... plain static files") are
commands that need SOMETHING to actually build and serve. Scaffolding a real Vite+React+TS project
end-to-end (routing, components, state management, styling) is a substantially larger, separate
effort than the rest of this phase — this was flagged to the user directly (`AskUserQuestion`)
rather than guessed at, with three options: build the minimal static viewer now, scaffold the real
SPA now, or defer the whole frontend (`wiki site build`/`serve` stay stubbed) to a later session.
**The user chose the minimal static viewer.**

What that means concretely: `site/templates/app.js` is vanilla JS with zero dependencies, fetches
`bundle/*.json` at runtime, and does hash-based routing (`#/character/<slug>`,
`#/codex/<kind>#<anchor>` — literally the CONTRACTS route string as the hash value; a URL fragment
can contain a second `#` with no escaping needed, since only the FIRST `#` starts the fragment).
It is a reference client, not a design target — `site/bundle.py`'s output contract does not
change when `web/` eventually gets built for real; only `site/static_site.py` (what writes
`dist/site/`) would need to be replaced with "run `npm run build` in `web/` and copy its output
instead." Do not add features to `app.js` beyond what makes the bundle contract exercisable and
auditable — a nicer UI is exactly the work `web/` exists for.

## Things you need to know

**The sparse multi-cutoff shape is the single most important idea in this phase — get it wrong
and every downstream reader is subtly broken, not obviously broken.** `data/05_pages/<id>/
v{NN}.json` files already only exist at cutoffs where something changed (Phase 6's "13x
collapse"). `build_pages_bundle` does NOT try to fill the gaps — it copies exactly the keys that
exist on disk (`{"cutoffs": {"1": {...}, "3": {...}}}`, no `"2"` key). `build_codex_bundles` does
the analogous thing but has to COMPUTE its own sparseness, since there is no per-cutoff codex file
on disk to mirror — that is what `_state_hash` is for. **Every reader of a multi-cutoff bundle
file — the reference viewer's `nearestCutoff()` in `app.js`, `wiki audit links`, any future
consumer — MUST resolve a selected volume to `max(key for key in cutoffs if key <= selected)`,
never assume the key for the selected volume exists.** Getting this wrong doesn't crash anything;
it just silently shows `undefined`/nothing for a legitimate cutoff, which is a much worse bug to
chase later than a crash would be.

**`_state_hash` covers evidence AND `members`/`related`, not evidence alone — this is a real
divergence from `synth/cache.py`'s single-hash `unchanged()`, made deliberately, not by
oversight.** A codex entry's summary sentence can stay byte-identical across two cutoffs while its
member list changes (a character newly affiliates). If the cache key were evidence-only, that
cutoff would be skipped — no new `cutoffs["<N>"]` key — and a client resolving "nearest cutoff <=
N" would keep showing the STALE member list at N, forever, until the summary text itself happened
to change for unrelated reasons. `test_codex_bundle_skips_unchanged_cutoff_but_writes_on_
membership_change` in `tests/test_site_bundle.py` is the worked example — read it before touching
`_state_hash` or `_members_and_related`.

**`codex_summary`'s prompt needed a literal JSON example, not just a field description — and this
is a real, general lesson, not a one-off.** `_system_prompt` originally read like `synth/prose.py`'s
own system prompts (a paragraph of instructions, no literal JSON shown). Against
`gemini-flash-lite-latest` (`google_fast`, reached via `codex_summary`'s `fallback:` when
`MISTRAL_API_KEY` is absent — it had also independently expired again this session; see `wiki
doctor`'s "key present" check only verifies the key is non-empty, not that the provider still
accepts it, same known gap Phase 6 documented), a prompt whose FIRST LINE was `"Location: Sixth
Sector"` reliably primed the model to invent its own JSON shape — `{"location": "...",
"definition": "..."}` — instead of the `{"text": "..."}` the `CodexSummary` schema actually
requires, and `llm/client.py::complete_json`'s 3-attempt repair-retry loop never recovered it
(reproduced 4/4 times across two entities and two cutoffs before the fix, 0/4 times after adding
one line: `` Respond with JSON only: {"text": "..."} ``, matching the pattern
`entities/classify.py` already used). Google's `json_mode` (`response_mime_type: application/
json`) only enforces *valid JSON*, never a specific *shape* — there is no `response_schema`
constraint wired up in `llm/providers/google.py`. `docs/PROMPTS.md` rule #3 now states this as a
hard rule for every future `complete_json` prompt. `synth/prose.py`'s prompts have the same latent
gap (no literal example) and were NOT observed to fail in Phase 6's real testing, but that may
just mean nobody has hit the right/wrong priming context yet — worth a real repro before "fixing"
something not shown to be broken.

**`members`/`related` on a codex entry come from the graph, not from evidence text.** `members` is
every CHARACTER entity with a visible relation TO this codex entity (`graph/temporal.py::
relations_at` — extraction only ever produces a relation with a character as `subject`, since
`extract/claims.py` is a per-character driver, so the "other side" of any relation touching a
codex entity is always a character; `_members_and_related` filters by type anyway rather than
assuming, matching this codebase's usual "guard, don't trust the shape" style). `related` is this
entity's own `graph/ppr.py::personalized_pagerank` neighbours, restricted to OTHER non-character
entities, capped at 5 — the multi-hop "what else is this connected to" CONTRACTS §6.1's original
(illustrative, not literal) example showed. Both are graph-cutoff-filtered the same way every
other reader of `graph.db` is (`relations_at`/`all_edges_at` both filter `vol_start <= vol` before
anything else) — no new spoiler-filtering discipline was invented here, just applied to entity
types that had not needed it before.

**`links.json`'s value is `{"route", "canonical", "type"}`, not a bare string — CONTRACTS §6 only
ever said "entity_id → route."** This is a deliberate extension (documented in CONTRACTS §6.3),
not an accidental schema drift: without `canonical`, the reference viewer (or any future SPA)
would need a second lookup — realistically `index.json`'s character roster plus three separate
codex files merged client-side — just to print a relationship target's name. `route` alone is
still a strict subset of the object, so nothing that only ever read `.route` breaks.

**`--entities` on `wiki site build` filters CODEX entities only, not characters.** Character
pages/index/links/search are always built for the full roster regardless of the flag — they are
disk reads (Phase 6 already paid the LLM cost) with effectively no marginal cost to include. Only
`build_codex_bundles`'s LLM calls are worth gating for a smoke test, mirroring exactly why `wiki
synthesize --entities` exists (Phase 6's own real-money-real-quota testing lesson).

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Minimal dependency-free static viewer instead of a real `web/` SPA | User's explicit choice (`AskUserQuestion`) after being shown the actual empty-directory state and the scope gap; ships a working `wiki site build`/`serve` today with zero new tooling | Scaffolding the real Vite+React+TS SPA this session — legitimate, but a separate multi-hour effort the user did not choose; deferring the whole frontend — leaves the phase's own stated CLI commands unbuilt |
| `pages/*.json`/`codex/*.json` are sparse multi-cutoff maps, client resolves nearest key `<=` selected | Mirrors CONTRACTS §5.1's own cache rule at the bundle-file layer; a dense (every cutoff) map would defeat the point of Phase 6's collapse and bloat the bundle for no reason | A dense map with every cutoff 1..N explicitly duplicated — simpler client code, much larger files, and re-introduces the "N characters x N volumes" cost this whole project's design exists to avoid |
| Codex cache key (`_state_hash`) covers evidence + members + related | A member-list change with unchanged evidence text still needs a new cutoff entry, or "nearest cutoff <=" resolves to stale membership — see "Things you need to know" | Evidence-only hash (matches `synth/cache.py`'s literal mechanism) — simpler, but demonstrably wrong for this file's extra fields |
| `links.json` extended to `{route, canonical, type}` | Lets a client render any entity reference's name from one file; `route` remains a strict subset | Leaving it a bare route string per CONTRACTS' original wording — forces a second lookup file client-side for no real benefit |
| `codex_summary` evidence comes from `extract/windows.py::build_windows` over mention paragraphs, capped at 5 windows total across ALL volumes | Reuses proven windowing/hard-break logic; a global (not per-volume) cap keeps a corpus-wide entity like "the Legion" from handing the model dozens of windows for one sentence | A fresh, simpler paragraph-grab with no windowing context — cheaper to write, worse evidence quality (no pronoun-resolution context) |
| `wiki site build --entities` filters codex entities only | Character pages are free disk reads; only codex generation has real LLM cost worth gating for a smoke test | Filtering characters too — adds a code path with no cost benefit, since Phase 6 already paid for character prose |
| `_PENDING`/`_not_yet` (cli.py) and `_PLANNED` (audit/reports.py) removed now that both are empty | Every phase is built; an always-empty dict and an unreachable function are dead code, not "useful scaffolding," by this project's own minimalism rule | Leaving them in "for the next phase" — nothing concrete is planned that would need them; trivial to re-add from git history if that changes |

## Known gaps, deliberately left

- `web/` itself remains unscaffolded — see "The `web/` decision" above. This is the explicit
  next step, not an oversight.
- `codex_summary` was real-tested for FACTION (`the-spearhead`), LOCATION (`sixth-sector`), and
  TECH (`juggernaut`), but not EVENT — none of the 3 entities chosen for the (cost-conscious, per
  this session's memory note about staying within volumes 1-2) smoke test happened to be one.
  Covered by `tests/test_site_bundle.py`'s FakeClient tests structurally, just not against a live
  API for that specific type.
- A full `--upto 13` bundle build (the real end-to-end deliverable) was not attempted — this
  session's real-data testing stayed at `--upto 2` per the same testing-scope note, and a 13-volume
  run would multiply the codex LLM-call count across ~150 non-character entities × up to 13
  cutoffs each. `wiki audit links` and the sparse-cutoff logic have no reason to behave
  differently at scale, but this has not been observed, only reasoned about.
- No headless-browser test of `app.js` — verified via `node --check` (syntax) and `node -e`
  (the four pure logic functions, hand-extracted and run against real data shapes), not a real
  DOM. If jsdom or a browser automation tool becomes available in a future session, that closes
  this gap properly.
- `synth/prose.py`'s prompts share `codex_summary`'s pre-fix "no literal JSON example" gap and
  were not changed — no real failure has been observed there, and PROMPTS.md now records this as
  a thing to watch, not to preemptively "fix" without its own repro.
- `wiki doctor`'s model-reachability check still only verifies an API key is non-empty, not that
  the provider currently accepts it (the same gap Phase 6 documented) — this session hit it again
  independently (`MISTRAL_API_KEY` expired) and worked around it by temporarily unsetting the env
  var to force `codex_summary`'s `fallback:` path, exactly as Phase 6's handover predicted a future
  session would need to.
