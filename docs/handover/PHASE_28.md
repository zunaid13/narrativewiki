# Phase 28 Handover — The project runs on paid Vertex AI, and four silent failures are closed

Status 2026-09-23, branch `phase-26-citable-pages`. `pytest -q` green (1022). All eleven audits OK,
`eval` included. `dist/spice-and-wolf/wiki/` rebuilt by the exact sequence in §6: 88 Markdown pages,
two cutoffs, MkDocs-ready. Total spend for the entire phase — model bake-off, four scene re-runs,
three extraction re-runs and the final clean pass — **$5.49**, against a $20 lifetime cap. One
clean pass on its own measures about $1.65.

**Read this before** touching `config/models.yaml`'s `routing:`/`profiles:`,
`config.py::resolve_role`, `extract/adequacy.py`, `graph/verify.py`'s schema, or
`llm/parallel.py`. Each carries a decision from this phase that is easy to undo by accident.

---

## 1. What changed, in one paragraph

Vertex AI became available, so the maintainer authorised paid routing and asked for the project to
be finished, cheaply, without trading accuracy. Every generative stage now defaults to
`vertex_flash` (`gemini-3.1-flash-lite`) with the old defaults kept as an ordered fallback chain.
Switching model then exposed four defects that were never about the model — a routing fallback that
skipped Vertex entirely, three evidence gates the prompts never mentioned, and a verification pass
that had been silently approving everything. Fixing those, plus parallelising the pipeline, took
mean gold fact recall from 39.8% to 45.9% with precision unchanged at 1.0.

## 2. The routing chain (and the trap inside it)

```
vertex_flash (gemini-3.1-flash-lite, Vertex, paid)
  -> openrouter_free / openrouter_free_nex_pro ($0)
     -> local_fast / local_prose / local_best (Ollama, $0)
```

`resolve_role` walks that chain and takes the first rung whose credential exists. Three things
about it:

- **`fallback:` may now be a LIST.** A single value could not preserve both "prefer the free tier
  over local" and "a machine with no keys at all still runs". The last entry is the answer when
  none are callable.
- **`Profile.is_callable`, not `profile.api_key`, decides each hop.** Vertex authenticates with
  Application Default Credentials plus `GOOGLE_CLOUD_PROJECT`; it has no api_key. Before this
  property existed, the "no key → use the fallback" rule silently routed every Vertex stage
  straight back to the free tier and nothing failed or warned. If you add another
  credential-by-environment provider, extend `is_callable` or you will reintroduce this exactly.
- **`GOOGLE_CLOUD_LOCATION` must be `global`.** The gemini-3.x family 404s on `us-central1`. The
  2.5 family works at both, so a location mistake looks like "the new models don't exist".

`wiki doctor` prints the resolved model per stage — that is the fastest way to confirm what a run
will actually call.

## 3. Why `gemini-3.1-flash-lite`, and why not the newer ones

Measured on eight real stored `claim_extract` prompts, eight calls in parallel, same day:

| model | ok | wall | facts/call | thinking | verdict |
|---|---|---|---|---|---|
| `gemini-3.1-flash-lite` | 8/8 | 6.0s | **6.8** | none | chosen |
| `gemini-3.5-flash-lite` | 8/8 | 2.3s | 2.4 | none | terser, measurably worse yield |
| `gemini-3.5-flash` | 7/8 | 31.9s | 6.4 | 2.6k tok/call | one 429; thinking bills as output |
| `gemini-3.8-flash` | 1 then 429 | 48s | — | — | unusable at ~700 calls/run |

On three sentences of wiki prose from fixed facts, all four plus `gemini-3.1-pro-preview` were
indistinguishable. **Do not "upgrade" this profile on model-name recency.** Newer Gemini tiers in
this project are slower, quota-starved, and pay for thinking tokens the work does not need.
`vertex_pro` exists, unrouted, for `--model <stage>=vertex_pro` when an audit shows flash-lite is
actually wrong.

Thinking tokens: billed at the OUTPUT rate and drawn from the same `max_output_tokens` pool as the
answer. `llm/providers/google.py` now adds `thoughts_token_count` into `out_tokens` (the budget was
under-reporting), accepts a `thinking_budget` profile option, and raises a clear ProviderError
instead of returning "" when thinking crowds out the answer.

## 4. The four silent failures — read this section before "simplifying" any gate

### 4.1 A gate the model was never told about deletes good work

`extract/adequacy.py` enforced `min_quote_words: 6`, `requires_qualifier` and
`subject_must_be_named` while the prompts said nothing about them. Measured on one real v1–2 run:
106 facts dropped for a short quote, 163 for a bare `FRIEND_OF`, and 342 for the subject not being
named — the last of which the prompt actively *invited* ("a fact carried by a pronoun still counts
… do not require the character's own name to appear").

`adequacy.py::prompt_rules(settings)` now generates an EVIDENCE REQUIREMENTS block from the same
config the gates read, and both extraction prompts render it. **It is generated, not hand-written,
so a config edit cannot leave the prompt lying.** If you add a gate, add it there too.

### 4.2 `subject_must_be_named` was too strict to be correct

New config: `extraction.evidence_adequacy.subject_named_within_paragraphs: 1`. The name may appear
in the cited paragraph *or its immediate neighbours inside the window the model was shown*; `0`
restores the old single-paragraph behaviour. Prose carries a subject across paragraph breaks with
pronouns constantly, and the strict form dropped more facts than it kept. The misattribution the
gate exists to catch is still caught — a neighbourhood that never names the character is not about
them. Replayed from cache at zero cost: v01 127 → 170 claims, v02 218 → 269.

### 4.3 `wiki verify` had been failing OPEN

The prompt asked in prose to "list the index of every fact…", so models answered in the shape the
prose described: a bare JSON array, or `{"bad_facts": [6, 12, …]}`. That second shape **validates
perfectly** against `flags: []` — unknown key ignored, default empty — so a response flagging 49
facts was read as "nothing wrong" and nothing raised anywhere. How long this had been true is
unknown; the stored response proving it is in
`data/spice-and-wolf/_runs/20260921T064854-verify-upto2/calls.jsonl`.

Fixed at both ends: the prompt states the exact JSON shape, and `VerificationResult` has a
`mode="before"` validator coercing every observed variant (bare list, `bad_facts`/`flagged`/
`indices` aliases, `index`/`i` item keys, bare ints). First run after the fix: 23 flagged facts
across 11 of 15 characters (14 in the final clean run). `tests/test_graph_verify.py` pins it. **A check that fails open is
worse than one that crashes** — keep the validator.

### 4.4 Two prompt/budget interactions in scene extraction

- "QUOTES: notable dialogue" → a literal-minded model returned 6 quotes per span where the passage
  held ~40, and volume 1 kept quotes for 4 of its 11 speaking characters. Now it asks for every
  line; selection is downstream and deterministic (`quotes.max_quotes`). Volume 1 went 133 → 1037
  quotes, 4 → 7 named speakers.
- Once answers got that long, 6 of 42 detail responses were truncated mid-JSON — and the truncated
  tail is always `participant_facts`, the last key in the response, i.e. the cap was silently
  deleting the facts the call exists to produce. `_DETAIL_GENERATION_OPTIONS` num_predict 8192 →
  24576. Output tokens bill only when generated.

## 5. Optimisations (and the one that is a correctness fix in disguise)

- **`llm/parallel.py::map_calls`** — a stage's independent calls, `Profile.concurrency` at a time,
  results in input order. `concurrency:` had been in `config/models.yaml` for months and was read
  by nothing; the whole pipeline was serial. Wired into `entities/classify.py`,
  `extract/claims.py` (per character) and `extract/scenes.py` (per chapter). **Spans inside a
  chapter stay serial on purpose** — quote/epithet dedup and claim merging are order-dependent.
  Thread-safety already existed where the shared state is (Budget's lock, RunContext's lock); the
  disk cache needed a per-thread temp filename. A volume of scene extraction: 8.5 min → 33s.
- **`RunContext.frontier_call_count()` was O(n²)** — re-parsing all of `calls.jsonl`, full prompts
  included, on every frontier call. Seeded once from the file, then counted in memory.
- **One Gemini SDK client per endpoint**, not per call (0.6s to construct, ~1.5s more for the first
  request on a fresh one).
- **Extraction temperature is pinned to 0.1** (`claims.py::_GENERATION_OPTIONS`,
  `scenes.py::_BEAT/_DETAIL_GENERATION_OPTIONS`; prose stages keep the profile's 0.4). This is the
  most important thing in this handover for anyone about to measure a change: at 0.4, **re-running
  only the scene pass moved mean gold fact recall by 7 points in both directions with no code
  change**, which made two of this phase's own A/Bs argue with themselves. A per-character-sweep
  prompt that measured +41% facts in isolation shipped and then measured 7 points WORSE end to end;
  reverting it did not restore the old number either, because `gazetteer --merge-epithets` had run
  in between and legitimately changes the scene prompts. It is not shipped. **A before/after on
  this pipeline is only valid if the whole sequence is re-run from the same starting artifacts.**
- **A 429 is "not yet", not a failure.** It now has its own retry budget (`rate_limit_retries: 8`)
  and its own ladder (20s, 40s, …), separate from `max_retries` (3) for real failures. Vertex's
  shared quota refuses for minutes under a parallel stage; the old shared 3-attempt/14-second
  ladder crashed `wiki scenes` mid-volume twice. `vertex_flash` concurrency settled at 4 — 8
  tripped the quota.

## 6. Reproducing the deliverable

```
gcloud auth application-default login          # once; GOOGLE_CLOUD_PROJECT + LOCATION=global in .env
ollama serve                                   # canonicalize/support only; both are $0
wiki doctor -s spice-and-wolf                  # must print google:gemini-3.1-flash-lite per stage

wiki gazetteer -s spice-and-wolf --volumes 1-2 --force
wiki scenes    -s spice-and-wolf --volumes 1-2 --force
wiki gazetteer -s spice-and-wolf --volumes 1-2 --merge-epithets
wiki extract   -s spice-and-wolf --volumes 1-2 --force
wiki graph build -s spice-and-wolf --allow-partial     # see note below
wiki verify    -s spice-and-wolf --upto 2
wiki events-build -s spice-and-wolf --force
wiki synthesize -s spice-and-wolf --upto 2 --force --polish
wiki site build -s spice-and-wolf --upto 2 --force
```

`--allow-partial` is needed for one legitimate reason: `saint-metrogius` is a patron saint invoked
in three passing lines ("you follow the path of Saint Metrogius in business") and has genuinely
zero extractable facts. The "mentioned, zero claims" guard is doing its job; the page gate skips
him downstream. If a *different* character ever appears in that message, do not reach for the flag
— that is the crashed-run signature it was built for.

Then: `wiki audit eval -s spice-and-wolf`, the other ten audits, and
`wiki probe run index|leak|disclosure`.

## 7. Numbers to compare against

Final state is the clean protocol run of §6, with extraction temperature pinned to 0.1:

| metric | before (2026-09-21) | after |
|---|---|---|
| mean gold fact recall | 39.8% | **45.9%** |
| fact precision, all ten | 1.0 | 1.0 |
| claims, v01 / v02 | 215 / 411 | 166+20 / 270+20 |
| verify flags raised | 0 (failing open) | 14 across 10 of 14 characters |
| v01 scene quotes / speakers | 957 / 11 (with misattributions) | ~1000 / 7 named + unattributed |
| `probe disclosure` t=1 unseeable (exact/normalised) | 0.470 / 0.331 | 0.114 / 0.057 |
| `probe index` t=1 tainted claims | not previously reported | 3 of 172 (one future-vocabulary mention) |
| wall clock, one volume of `scenes` | ~8.5 min | 33s |
| pages in `dist/spice-and-wolf/wiki/` | 86 | 88 |

Per-character recall against the floors recorded earlier the same day: marheit 50→67,
norah-arendt 40→60, zheren 20→40 up; enek 50→25 and kraft-lawrence 56→44 down; hans-remelio (57),
holo (80), liebert (75), jakob (11) at floor; yarei 0. **The floors were deliberately NOT ratcheted
onto this run** — see §5's temperature note and `baseline.json`'s own `_comment`: a single entity's
recall carries about ±1 fact of noise, so raise a floor only from a run you can reproduce twice.

**`probe run leak` at t=1 reads 0.245 against 0.126 before, and that is a denominator artefact, not
new leakage** — the numerator is unchanged (67 vs 69 future facts findable) while the count of
future facts fell with the v2 claim count (273 vs 548). `tests/test_spoiler_leak.py` is the
invariant and is green.

## 8. What is NOT done

- **`yarei` recall is 0.0 against a floor of 0.25, deliberately unfixed.** The fact it used to
  recall is "held in the barn for a week"; the corpus sentence is conditional — "Now Yarei *would
  be* locked in a granary … close to a week". An extractor that declines to assert a hypothetical
  is behaving correctly and gold states it as fact. Fix gold's side, then re-record the floor.
  Do not tune the floor to make the WARN disappear.
- **`docs/REFERENCES.md` is still stale** (51 rows against 54 PDFs). Diagnosis advanced: arXiv
  returns 200 for an API URL it has already served and 406 for every uncached one, so this is
  server-side refusal, not a bad id and not batch size (correcting this file's earlier guess). The
  script writes nothing on a partial fetch, which is right. Re-run
  `python docs/fetch_reference_pdfs.py --check` on a day arXiv is answering.
- **Scene-pass fact yield is low on this model** — roughly 60-80 raw participant_facts per volume
  against a free-tier model's several hundred, of which ~20 per volume survive the gates. The
  window pass (`extract/claims.py`) carries claim recall today. The obvious prompt fix was tried
  and rejected on the end-to-end number (§5); if you try again, measure the whole sequence, twice.
- **`enek`, `kraft-lawrence` and `yarei` WARN** in `wiki audit eval`. `yarei` is the conditional-
  sentence case above; the other two are within the scene-pass sampling band described in §5. Left
  visible on purpose.
- **Gold still covers one series**, and the NLI hybrid from `PHASE_26.md` §5.1 is still
  unimplemented and still the maintainer's call, for the same reason: it changes what readers see.
- **`synthesize` and `verify` are still serial.** Both share one SQLite connection across the loop,
  so parallelising them is not the two-line change the other three stages were. `synthesize` is
  ~2.5 min for two volumes, so this is not urgent.
