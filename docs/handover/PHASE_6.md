# Phase 6 — Prose (synthesis)

**Closed:** 2026-09-02 · **Next:** Phase 7, Site (`site/wikify.py`, `site/bundle.py`, `wiki site
build`/`serve`, `codex_summary`)

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

```
src/narrativewiki/synth/
  prose.py      NEW. generate_prose(conn, client, entity, upto_vol, settings, *, stage) -> the
                   CONTRACTS §5 `prose` dict. Input is TRAIT claims ONLY -- BACKGROUND for
                   `background`, PERSONALITY/MOTIVATION/SKILL/FEAR for `personality` -- read via
                   synth/assemble.py::trait_values_at() + graph/temporal.py::evidence_at()
                   (cutoff-filtered per quote, the Phase 5 spoiler-leak fix). A field is `None`,
                   with NO LLM call made, when there are zero relevant trait claims at the cutoff.
                   `evidence` in the returned dict is the exact para_id set FED to the prompt, not
                   a model-reported citation.
  cache.py       NEW. previous_page(entity_id, upto_vol) -> nearest existing page file below
                   upto_vol, or None. unchanged(prev, claim_set_hash) -> True if that file's hash
                   already matches. This is CONTRACTS §5.1's cache -- see "Things you need to
                   know" for what it does and does NOT guarantee.
src/narrativewiki/site/
  okf.py         NEW. render_markdown(page, entity, settings, entities_by_id=None) -> the
                   CONTRACTS §5.2 OKF Markdown string (YAML front matter + fixed body section
                   order). Pure function of an already-assembled page dict -- no LLM, no graph.db
                   read, same "assemble from already-filtered data" discipline as
                   synth/assemble.py. Lives under site/ per the CLAUDE.md file map even though it
                   ships in Phase 6, because CONTRACTS §5.2/USER_GUIDE.md both tie `.md` output to
                   `wiki synthesize`'s own deliverable, not to Phase 7's site build.
src/narrativewiki/cli.py
  synthesize()   Wired end to end (was the last `_not_yet` stub besides site build/serve).
                   Iterates CHARACTER entities x cutoffs (entity["first_vol"]..--upto), skips via
                   synth/cache.py, routes `--polish` by an importance-percentile threshold
                   (config/models.yaml budget.polish_importance_percentile, default top 15%),
                   writes both `.json` and `.md`. `run-all` now calls it instead of stubbing.
src/narrativewiki/audit/reports.py
  _pages_report  NEW, registered for `wiki audit pages` (moved out of `_PLANNED`). Field coverage
                   (latest cutoff), prose sentence-length vs configured bounds, and a cache-reuse
                   estimate reconstructed from GAPS in each entity's on-disk volume sequence (no
                   separate manifest exists to record skips directly -- see below).
src/narrativewiki/config.py
  Settings.prose_config   NEW property, mirrors conflicts_config -- extraction.yaml's `prose:`
                   block (sentence bounds, forbid_uncited_specifics).
config/models.yaml
  `prose`/`codex_summary` now declare `fallback: google_fast` -- previously had NO fallback at
                   all, unlike every other API-routed stage. See "Things you need to know".
tests/test_synth_prose.py    NEW. 5 tests, FakeClient pattern (mirrors graph/contradictions.py's
                   JSONClient Protocol test style).
tests/test_synth_cache.py    NEW. 3 tests.
tests/test_site_okf.py       NEW. 7 tests.
```

`docs/CONTRACTS.md` §5/§5.1/§5.2 and `docs/PROMPTS.md`'s catalogue + `background_prose`/
`personality_prose` notes were updated in the same pass to describe what actually shipped, same as
Phase 5 did for §5's field-key note.

## Verify it in one command

```bash
wiki synthesize --upto 2 --entities shin --polish   # needs graph.db + gazetteer.json from Phase 3-5
python -m pytest                                      # 170 passed
wiki audit pages
```

**This ran for real against the actual v01-02 graph.db** (Phase 3/4's real data): `wiki synthesize
--upto 2 --entities shin --polish` produced `data/05_pages/shin/v01.{json,md}` and
`v02.{json,md}`. v01 correctly has `prose: {"background": null, "personality": null}` (no
BACKGROUND trait claim exists that early) and made no LLM call. v02's background prose cites only
`v02:...` evidence and reads as a plausible, cutoff-safe biography. Re-running the identical
command rewrote both files (see "Things you need to know" on why) but made no new network call —
`generated_by` and the prose text were byte-identical both times, confirming `llm/cache.py`
absorbed it for free.

## Things you need to know

**`synth/prose.py` reads TRAIT claims only — never a structured `fields` value.** This was a
deliberate narrowing of "background... from the volume-filtered claim set" (docs/PROMPTS.md's
original planning-stage wording): BACKGROUND trait claims already ARE members of that set, and
pulling in status/rank/affiliation history as extra "biography context" would need new
evidence-fetching plumbing nothing in CONTRACTS specifies, while blurring CLAUDE.md §2's
"structured fields are never LLM-generated" (the model would see content it could restate as if it
were the generated prose). If a future request wants background prose to also draw on structured
fields, that is a real CONTRACTS §5 change, not a bug fix — flag it explicitly rather than quietly
widening the prompt's input.

**A `null` prose field with no LLM call is intentional, not a gap.** `_generate_one` in
`synth/prose.py` returns `None` immediately, before touching the client, when there are no fact
lines to hand it. This is why v01's page above has both fields `null`: Shin has no BACKGROUND
trait claim by volume 1 in the real corpus. Do not "fix" this by asking the model to write
something from nothing — that is the exact hallucination risk CLAUDE.md §1 exists to prevent.

**`evidence` in the prose dict is not a citation the model produces — it is what we fed it.**
`_gather_facts` collects every `para_id` from `evidence_at(claim_ids, upto_vol)` calls made while
building the prompt, and that list (deduped, sorted) becomes `evidence` regardless of what the
model's response text actually says. This makes the field impossible for the model to falsify by
paraphrasing a quote instead of citing it, at the cost of it being "everything shown", not
"everything used" — a model that ignores one of five facts still gets all five listed as evidence.
This was a deliberate simplicity-over-precision call; revisit only if `wiki audit pages` ever needs
finer-grained citation accuracy than it currently checks (it currently only checks sentence-count
bounds, not grounding).

**`synth/cache.py`'s skip is about ADJACENT cutoffs within one logical build, not about rerun
idempotency.** `previous_page(id, N)` finds the nearest EXISTING file below N and compares hashes.
On a totally fresh multi-volume run (`--upto 13` from nothing) this is exactly CONTRACTS §5.1's
"13x collapse": a character whose facts do not change between v5 and v6 gets no v06 file at all,
and Phase 7's bundle step is expected to resolve cutoff 6 to the v05 file it finds on disk. But
re-running `wiki synthesize --upto 2` a SECOND time over the SAME already-populated data rewrites
both v01 and v02 again, every time — because v02's hash is being compared to v01's hash (which is
almost always different; that is real narrative content, not staleness), never to v02's own
previously-written copy. This is deliberate (see VISION.md 2026-09-02 entry) and safe: the
expensive resource, LLM spend, is still protected by `llm/cache.py`'s exact-request cache, which
returns free and instant on a byte-identical prompt. If a future need genuinely requires
same-cutoff rerun idempotency at the file layer too, that's a second comparison
(`prev_at_this_exact_vol.claim_set_hash == claim_set_hash`) layered on top of what exists — not
a replacement for the N-vs-N-1 check CONTRACTS §5.1 actually specifies.

**`wiki audit pages`'s cache-reuse number is reconstructed, not recorded.** There is no manifest
file listing which cutoffs were attempted vs skipped — the report infers skips from GAPS in each
entity's on-disk `v{NN}.json` sequence (e.g. v01 and v03 exist, v02 doesn't -> assume v02 was
skipped). This is a heuristic that assumes every cutoff in an entity's written range was actually
attempted in some run; it will misreport if pages were manually deleted or `--entities` filtered
runs left irregular gaps for reasons other than caching. Good enough for an audit sanity check,
not a source of truth — if this ever matters more precisely, the real fix is a manifest written by
`synth/cache.py` itself, not smarter gap inference.

**`config/models.yaml`: `prose`/`codex_summary` had no reachable fallback, discovered by a real
401.** `Settings.resolve_role` only substitutes `fallback` when the primary profile's API key is
*absent* from the environment (`profile.api_key` is falsy) — it has no way to react to a key that
is *present but rejected* by the provider (expired, revoked, quota-exhausted) without actually
attempting the call. `MISTRAL_API_KEY` in this environment expired on 2026-09-02 itself (the
provider's own error said so), and `prose`/`codex_summary` were the only two API-routed stages
with no `fallback:` entry at all — every other stage (`entity_classify`, `entity_alias`,
`claim_extract`, `arbitrate`, `prose_polish`) already had one. Both now fall back to `google_fast`.
This does not fix `resolve_role`'s inability to detect a bad-but-present key ahead of time — that
would need either a health-check call before every stage (real cost) or a runtime provider-swap on
auth failure inside `llm/client.py::_call` (a real architecture change, out of scope for a
one-stage prose bug) — it just gives these two stages the same static safety net the others have.

**`GOOGLE_API_KEY`'s free tier has a 20-request/day quota per model, hit mid-session.** Real
verification beyond Shin's `--polish` run was blocked by this, not by any code defect — see LOG.md
Gaps. A future session picking this phase back up (or starting Phase 7's real-data checks) should
either wait for the daily reset, use a non-free-tier key, or wait for `MISTRAL_API_KEY` to be
renewed so the un-polished `prose` role (higher volume, cheaper per call) is reachable again.

**`--polish` routing is importance-percentile, computed over the FULL character roster, not the
`--entities`-filtered subset.** `_polish_threshold` in cli.py is called with
`[e for e in gaz["entities"] if e["type"] == "CHARACTER"]` freshly, independent of any
`--entities` filter applied to the actual run — so `wiki synthesize --entities lena --polish`
still asks "is Lena above the 85th importance percentile of the WHOLE cast", not "of just Lena",
which is the only sensible reading (a filter for testing convenience should not change who counts
as "major"). Verified in the real run: Shin (importance 1.0, clearly major) got `prose_polish` and
`generated_by: "google:gemini-flash-latest"`.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Prose input is TRAIT claims only, never structured `fields` | Matches docs/PROMPTS.md's existing `personality_prose` design exactly; avoids new evidence plumbing and keeps CLAUDE.md §2's "never LLM-generated" boundary unambiguous | Also feeding scalar attribute history ("biography context") for `background` — broader reading of "volume-filtered claim set" nothing in CONTRACTS actually requires |
| `evidence` = para_ids fed to the prompt, not model-cited | Deterministic, cannot be falsified by paraphrase; simpler than parsing/validating a model citation list | Asking the model to return which facts it used — adds a schema field and a validation failure mode for marginal precision gain |
| No LLM call when zero trait evidence exists | Zero-evidence generation is exactly CLAUDE.md §1's hallucination risk; also free | Always calling the model with an empty fact list and hoping `forbid_uncited_specifics` holds — real risk, no upside |
| Cache compares cutoff N to cutoff N-1's file, not to N's own last run | The literal CONTRACTS §5.1 mechanism; the expensive resource (LLM spend) is already protected by llm/cache.py regardless | A second same-cutoff idempotency layer — real complexity for a guarantee nothing currently asks for |
| `categories` = affiliation entity_ids; `Appearances` = every vol named in `fields` | Both undefined by CONTRACTS §5.2; this derives them from the page dict alone with no new evidence read, keeping site/okf.py a pure function like synth/assemble.py | Reading mention_counts from graph.db for `Appearances` — a new read path this module didn't otherwise need |
| `prose`/`codex_summary` get `fallback: google_fast` | Every other API-routed stage already has a fallback; found the gap via a real 401, not inspection | Rewriting `Settings.resolve_role` to retry-and-swap on a runtime auth failure — real architecture change, out of scope here |
| `wiki audit pages` reuse count is inferred from on-disk gaps | No manifest exists and adding one only to serve an audit report is premature | A dedicated cache-skip manifest written by synth/cache.py — legitimate if precision ever actually matters |

## Known gaps, deliberately left

- Non-major (`prose`, not `prose_polish`) generation was not real-run-verified this session —
  blocked by `MISTRAL_API_KEY` expiring today and `google_fast`'s free-tier quota being exhausted
  by the `prose_polish` testing that came first. Covered by `test_synth_prose.py`'s FakeClient
  tests (stage-forwarding is asserted directly), just not against a live API.
- Cache-skip (`synth/cache.py::unchanged` returning `True` in a real run) was not observed on real
  data — Shin's facts genuinely changed between v01 and v02, so nothing exercised the skip path
  outside `test_synth_cache.py`'s isolated tests. Worth watching the first time a real `--upto 13`
  run is attempted.
- `codex_summary` (facts about factions/locations/events/tech, for Phase 7's shared codex pages)
  is still unbuilt — it was never Phase 6's job (CONTRACTS/PROMPTS both scope it to codex pages,
  which are a Phase 7 concern), but its `models.yaml` routing gap got the same fallback fix as
  `prose` while touching that file, since it was the identical bug.
- `wiki audit pages`'s reuse-percentage is a heuristic (see "Things you need to know" above), not
  an exact count.
- No `wiki budget` persistence — `client.budget` accumulates in memory during `synthesize` but
  nothing calls `.save()`, matching every existing LLM-calling CLI command (`extract`,
  `graph build`) — this is a pre-existing gap across the whole CLI, not something Phase 6
  introduced or was asked to fix.
