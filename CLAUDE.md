# CLAUDE.md — Read this first, then jump straight to the file you need

**Project:** `narrativewiki` — turns a novel series (EPUBs) into a hyperlinked, spoiler-scoped
character wiki. The reader picks "I've read up to Volume N"; the site shows only what a Volume-N
reader could know.

**Corpus:** EPUBs live in `corpus/<series-id>/` (gitignored). In scope, v1–2 each (`AGENTS.md`
§3): *Spice and Wolf*, *Overlord* (both Yen On), *Ascendance of a Bookworm* (J-Novel Club,
`--series bookworm`, Part 1 v01–02). *86—EIGHTY-SIX* is retired; *Mushoku Tensei* is not yet in
scope. `probe-gutenberg` is a public-domain ingest probe (no LLM stage run). Series specifics live in
`config/series.*.yaml`. Repo layout and "where does X go": `STRUCTURE.md`.

**Working with Codex:** as of 2026-09-14, Codex and Claude are equivalent agents — either may
decide scope, implement, and commit/push without the other's sign-off. See `AGENTS.md` for the
shared standing rules (volume scope, LLM routing, the files neither agent edits). The old
decider/implementer task-file protocol is retired — commits and PRs are the record.
`docs/vision/plans/NNNN-*.md` holds executable plans (formerly `docs/tasks/`), open to both agents.

---

## 0. How to work in this repo (token discipline — a hard requirement)

The user explicitly asked to minimise re-reading the same files. Obey this order:

1. **This file** tells you where everything is. Use the file map (§5) — do not grep to find a module.
2. **`docs/CONTRACTS.md`** has every data schema. Read it instead of reading code to learn a shape.
3. **`docs/handover/PHASE_<latest>.md`** tells you the current state. Read only the newest one.
4. **Module header docstrings** state inputs/outputs/invariants. The top ~20 lines of a module are
   enough to call it. Read the whole file only when editing it.
5. `LOG.md` is newest-first — read only the top entry unless you need history.

Do **not** read `VISION.md` end to end on every task — it is a one-line-per-entry index now;
read only `docs/vision/PHASE_<n>.md` for the phase you are implementing. Do **not** re-derive
corpus facts — they are in §3.

---

## 1. The one invariant that must never break

> **Spoiler safety.** Every claim carries `first_vol`, the volume whose text supplied its evidence.
> A page rendered at cutoff N is built from claims filtered to `first_vol <= N`, and **the prose is
> generated from that already-filtered set**. Never generate from the full set and redact afterwards
> — implication leaks through redaction.

`tests/test_spoiler_leak.py` enforces this. If it fails, nothing else matters.

## 2. The other rules that shape the code

- **Only characters get unique pages.** Factions/organizations share one codex page; locations &
  battles share another; technology/Legion shares a third. Links go to `/codex/<kind>#<slug>`.
- **Structured fields are never LLM-generated.** Name, age, gender, affiliations, titles, nicknames
  and relationships render deterministically from graph rows. Only `background`/`personality`
  prose (capped 2–4 sentences) and the codex `summary` (capped 1 sentence, `site/bundle.py`)
  cost output tokens — and only when there is evidence to describe; zero evidence means `null`
  with no LLM call, never an invented sentence.
- **Contradictions:** same volume + conflicting value = extraction error, arbitrate and log.
  Different volumes + conflicting value = legitimate narrative change, close the old interval and
  open a new one. Never silently drop either side.
- **Vertex AI first (2026-09-23, standing instruction — supersedes "OpenRouter free tier first",
  which superseded "local first").** Every generative stage defaults to `vertex_flash`
  (`gemini-3.1-flash-lite`, chosen by measurement — `docs/vision/PHASE_28.md`), and each stage's
  `fallback:` is an ordered chain down to the old defaults: **Vertex → OpenRouter free tier →
  local Ollama**. `resolve_role` takes the first rung whose credential exists, so a machine with no
  `GOOGLE_CLOUD_PROJECT` runs on the free tier exactly as before and one with no keys at all still
  runs fully local. Requires `GOOGLE_CLOUD_LOCATION=global` (the gemini-3.x family 404s on regional
  endpoints). Route via `config/models.yaml`; never hard-code a model name in a module.
- **A paid model is only ever routed behind its interlock.** `vertex_flash` is `tier: frontier`
  with `max_volumes: 2`, so `_enforce_frontier_scope` refuses every call once a run's scope passes
  volume 2 — "Spice and Wolf volumes 1–2 only" made mechanical. `budget.lifetime_cap_usd` ($200 since 2026-09-25)
  survives re-running, `hard_stop_usd` ($10) is per run, a full v1–2 pass measures ~$1.65, and
  `tests/test_config.py` fails if any stage routes to a paid profile without such an interlock.
- **Every LLM call goes through `llm/client.py`** so it is cached, budgeted and provider-swappable.
- **Measurement is free; shipping costs money.** Local models (Ollama, MiniCheck-FT5) are $0 and
  unmetered, so **evaluation and diagnosis may use them freely** (2026-09-21) but must spend
  neither dollars nor OpenRouter quota: `wiki audit eval` still has to complete with every key
  unset. Rationale: `docs/vision/PHASE_27.md`.
- **Spend the API only when nothing else moves the project forward** (2026-09-23, maintainer,
  standing). Deterministic stage, cache hit, fixture or stored-prompt replay first; before any
  command that bills, say in one line why no cheaper path exists. `wiki site build` is the
  canonical cheap path — it re-renders every page for $0, since only `codex_summary`'s *evidence*
  hash gates a call.
- **Tune on the smallest slice that can show the effect.** A prompt or config A/B starts on one
  volume, or on stored prompts (`docs/eval/replay_*`, `docs/probe/gate_comparison_*`) — never on a
  full `--volumes 1-2` pass. That pass is the *confirmation* run, and per
  `docs/handover/PHASE_28.md` §5 it is not optional: a candidate that wins small can lose 7 points
  end to end.
- **Every API output is written down and re-read, never re-asked.** `llm/cache.py` keys on
  `sha256(provider+model+prompt+params)` under `data/cache/llm/`; `_runs/*/calls.jsonl` keeps the
  full record. Never clear the cache for a "clean run", never bypass `llm/client.py`.
- **Every number and observation lands in `docs/MEASUREMENTS.md`** (2026-09-23) — append-only, one
  row per value with its reproducing command and run id. Publication was reinstated 2026-09-25
  (decontaminated Gutenberg novels, `docs/vision/PHASE_31.md`); the paper cites the ledger, so a
  figure must be findable there first. A number in `LOG.md` or a handover without a row there is not recorded.

## 2b. What "done" looks like

Structure and connectedness that stand next to a professional fandom page: every character page
carrying the same sections filled to comparable depth, every named entity reachable by a link in
both directions, no dead-end stubs, and no page asserting what the text or the art does not
support. Balance and connectivity are as much of the deliverable as recall — a page that is right
but isolated has not shipped. The emitter is the last place a claim can be invented and the only
one with no evidence gate behind it. Baseline: `docs/MEASUREMENTS.md` §3.

## 3. Corpus traps already discovered (86 EPUBs; do not rediscover these)

These cost a full inspection pass to find. `ingest/epub.py` absorbs all of them; downstream code can
assume clean text.

1. **No cast lists or glossaries exist as text** in any volume — the character-intro plates are
   JPEGs. Entities must be mined from prose. This is why Phase 2 exists.
2. **Chapters span multiple XHTML files.** The TOC points only at the first; continuation files have
   no `<h1>`. Walk `<spine>` in order; start a new chapter on `h1.chapter-number`; append h1-less
   body docs to the current chapter. Filename sort is wrong (`chapter001_a`, `_aa`, `_bb`).
3. **`nav.xhtml` is broken in v02 and v03.** Use `toc.xhtml`; fall back to `toc.ncx`.
4. **Para-RAID (radio) markup is renamed 7 times** across volumes and moves from block `<p>` to
   inline `<span>`: `san` (v01) → `pararaid` (v02) → `para-raid` (v03) → `para-raid-char` (v04/05) →
   `special` (v06–v10, v12, v13) → `special-1`/`special2-1` (v11). Match
   `^(san|pararaid|para-raid.*|special.*)$`. Densest source of call signs and vocatives in the corpus.
5. **Some em dashes are inline images.** Replace `img[src*="mdash"]` with `—` *before* stripping
   images, or interrupted speech corrupts (`"thank you for saving m"`).
6. **Machine/Legion voice is `&lt;&lt;...&gt;&gt;` entities.** Decode entities only *after* tag
   stripping.
7. **`copyright.xhtml` is mistagged** `epub:type="bodymatter chapter"` in every volume. Filter by
   filename.
8. **`<a id="page-N">` markers** appear mid-paragraph and give free print page numbers for citations.
9. **`img.ornament` = hard scene/POV break**; `p.space-break*` = soft break. Both are chunk
   boundaries. v11 names chapters by in-world date (`9.29: D-Day Minus Two`); v10 is an anthology.

## 4. Documentation protocol (the user's workflow — follow it exactly)

```
new requirement  ->  APPEND a dated section to docs/vision/PHASE_<n>.md (the phase currently
                      open), then APPEND its one-line pointer to VISION.md's index
implementing     ->  read docs/vision/PHASE_<n>.md for this phase, then code
progress made    ->  APPEND to LOG.md      (newest FIRST, <= 15 lines per entry)
any number       ->  APPEND a row to docs/MEASUREMENTS.md, with the command that
                      reproduces it and the run id. Do this BEFORE quoting it anywhere
change that can  ->  APPEND an entry to docs/eval/CHANGES.md: what, why, values before
move a number         -> after, cells invalidated/redone, ablation/appendix it bears on
phase complete   ->  write docs/handover/PHASE_<n>.md, then append the LOG entry
executable plan  ->  docs/vision/plans/NNNN-<slug>.md (next free number; living, not append-only)
new paper        ->  docs/papers/pdf/{Paper Title}.pdf + a row in docs/papers/PAPERS.md
one-off script   ->  scripts/<eval|probe|papers>/; its outputs go to docs/eval/ or docs/probe/
```

- `VISION.md` is an **index only** — one line per entry (date, title, link to the phase file),
  append-only, never rewritten. It stays cheap to read in full; that's what makes "grep VISION for
  the phase I need" a real option again. Full entries live in `docs/vision/PHASE_<n>.md`, one file
  per phase, split out 2026-09-04 when the single file hit 1144 lines. Each phase file is itself
  **append-only** — never rewrite history there either; a superseded decision gets a new dated entry
  saying what changed and why. File a decision under the phase it's *about* when that's clearer than
  the phase currently open (e.g. a Phase 4 design call made while Phase 0 is still being scoped goes
  in `PHASE_4.md`).
- `LOG.md` is **newest-first** and terse: what was built, deliverable path, how verified, known gaps.
  Once it exceeds ~15 entries, delete everything older than the last 8 — `git log` is the archive.
  Keeps "read only the top entry" actually cheap to eyeball.
- A handover doc must let a cold contributor continue without reading any source: what exists, what
  the next phase needs to know, decisions taken *and rejected*, traps hit, and the exact command that
  reproduces the deliverable.
- `docs/MEASUREMENTS.md` is **append-only and never edited** — a superseded value gets a new
  dated row so the trajectory stays readable. Observations (including findings that turned out to
  be measurement artefacts) get rows too; those are what gets rediscovered expensively.
- Keep this file under ~200 lines. New detail goes to `docs/CONTRACTS.md` or a handover, not here.

## 5. File map — go directly to the file you need

| Path (under `src/narrativewiki/`) | Purpose |
|---|---|
| `cli.py` | Typer app. Every CLI command is registered here. |
| `config.py` | Loads `config/*.yaml` + `.env` into typed settings. |
| `paths.py` | Canonical data paths. Never hard-code a `data/` path elsewhere. |
| `llm/client.py` | One LLM interface: routing, retries, JSON-schema validation, repair-retry. |
| `llm/cache.py` | Disk cache keyed `sha256(provider+model+prompt+params)`. |
| `llm/budget.py` | Token/cost accounting per stage; prints the run summary. |
| `llm/parallel.py` | [28] `map_calls` — a stage's independent calls, `concurrency` at a time, in order. |
| `llm/providers/*.py` | `ollama`, `anthropic`, `google`, `openai` adapters. Mistral, Groq and OpenRouter all route through `openai.py` with a `base_url` override (`config/models.yaml`) — no dedicated file each. |
| `ingest/epub.py` | EPUB → chapters. Absorbs every trap in §3. |
| `ingest/decontaminate.py` | [31] Name remap + paraphrase of a parsed novel into a same-`para_id` series (`wiki decontaminate`, CONTRACTS §1.6). |
| `ingest/normalize.py` | Text cleanup, entity-decode ordering, quote/dash normalisation. |
| `ingest/segment.py` | Paragraph records + scene-break/window segmentation. |
| `entities/candidates.py` | Mines name candidates (n-grams, honorifics, vocatives, call signs). |
| `entities/classify.py` | Local-LLM typing: CHARACTER / FACTION / LOCATION / EVENT / TECH. |
| `entities/alias.py` | Alias clustering (RapidFuzz + LLM adjudication) → canonical entities. |
| `entities/gazetteer.py` | Builds and loads `gazetteer.json`. |
| `entities/automaton.py` | Aho-Corasick build + corpus mention index. **The auditable lexical index** — surface forms are enumerable, so what it knows at a cutoff can be proven, not just argued (`probe/channels/index.py`). |
| `extract/windows.py` | Mention offsets → deduped evidence windows under a token budget. |
| `extract/schema.py` | Pydantic models for claims. Mirrors `docs/CONTRACTS.md` §3. |
| `extract/claims.py` | Per-character claim extraction driver. |
| `extract/infobox.py` | [30] Long-context passes (`PASSES`): `infobox` (GENDER/AGE/ORIGIN, named paragraphs) and `backstory` (BACKGROUND, with context). One call per character-volume, own file each; never edits `claim_extract`'s prompt. |
| `extract/spans.py` | Chapter spans: overlapping ~4k-token windows covering 100% of paragraphs. Mirrors CONTRACTS §3b. |
| `extract/scene_schema.py` | Pydantic models for scene/epithet records. Mirrors CONTRACTS §3b/§3b.1. |
| `extract/scenes.py` | Chapter-major scene extraction driver (Phase 18 second pass). |
| `extract/resolve.py` | Surface → entity resolution helpers shared by claims.py and scenes.py. |
| `extract/adequacy.py` | [23] Evidence-adequacy gate: does the quote support the fact, not just exist. |
| `graph/store.py` | SQLite schema + read/write. |
| `graph/temporal.py` | Interval assignment; `state_at(vol)` / `history_at(vol)`. |
| `graph/contradictions.py` | Same-volume arbitration vs cross-volume supersession. |
| `graph/verify.py` | Phase 22 C3: per-character verification call (fact vs. its own cited evidence). |
| `graph/support.py` | MiniCheck support scoring of a claim against its cited paragraphs (`llm/providers/minicheck.py`). |
| `graph/canonicalize.py` | [17] BGE-M3 near-duplicate value clustering before interval assignment. |
| `graph/events.py` / `event_build.py` | [19] Event layer: `events.db` schema/readers / build from scene records. |
| `graph/ppr.py` | Personalized PageRank over the volume-filtered subgraph (multi-hop evidence). |
| `synth/assemble.py` | Builds the page model from graph rows (no LLM). |
| `synth/prose.py` | Short background/personality prose. |
| `synth/cache.py` | Claim-set-hash cache — collapses the 13x volume multiplier. |
| `site/wikify.py` | Aho-Corasick over already-generated prose → Markdown hyperlinks. |
| `site/okf.py` | OKF Markdown + YAML front matter emitter. |
| `site/bundle.py` | Assembles `data/06_bundle/`; also the `codex_summary` generative step. |
| `site/mkdocs_wiki.py` | [25] Renders `dist/<series>/wiki/` — Markdown wiki, one dir per cutoff volume, MkDocs Material-ready. Replaced the ES5 SPA (`site/static_site.py`, deleted). |
| `audit/reports.py` | `wiki audit <stage>` reports. Every phase has one. |
| `eval/gold.py` | Hand-transcribed gold-data recall/entailment metrics for `wiki audit eval`. |
| `probe/futureset.py` | [24] `F>t` — every claim/interval with `first_vol` after a cutoff. Zero annotation: it re-scopes `graph.db`, never re-collects. |
| `probe/channels/index.py` | [24] **L_build** — does the index (gazetteer, candidate mining) know things a cutoff-`t` reader could not? Zero LLM calls; see LOG.md 2026-09-13. |
| `probe/channels/leak.py` / `disclosure.py` | [24] L_query (future values in pages) / surface-vocabulary disclosure. Zero LLM calls. |
| `provenance.py` | Per-run ledger `data/<s>/_runs/<id>/` (manifest, calls.jsonl), snapshot + `wiki rollback`. |
| `probe/memorization.py` | [31] L_param: name-cloze + title-ID probe of the generator, original vs decontaminated (`probe run memorization`, CONTRACTS §9.4). |
| `probe/report.py` | [24] JSONL output for every probe measurement (`wiki probe run`). No paper is written from console/HTML output. |

| Other | Purpose |
|---|---|
| `docs/MEASUREMENTS.md` | [29] **The numeric ledger** — every measured value, observation and claim, with its reproducing command. The paper (Phase 31) cites it; nothing is quoted before its row exists. |
| `docs/papers/PAPERS.md` / `docs/papers/REFERENCES.md` | Per-paper Applied/Reference status; machine-verified citation metadata (`scripts/papers/fetch_reference_pdfs.py`). PDFs in `docs/papers/pdf/`. |
| `config/series.<id>.yaml` | Volume list, `source.dir` (`corpus/<id>`), EPUB quirks. Add a new series here. |
| `config/models.yaml` | Provider profiles + per-stage model routing. |
| `config/extraction.yaml` | Entity types, relation predicates, attribute keys. |

## 6. CLI surface

`wiki doctor` · `ingest` · `gazetteer` · `gazetteer --merge-epithets` · `scenes` · `extract` · `infobox` ·
`graph build` · `verify` · `explain` · `trace` · `synthesize` · `site build` · `serve` · `step` ·
`audit <stage>` · `audit run <run_id>` · `status` · `runs` · `calls` · `rollback` · `budget` ·
`run-all` · `probe run index` [24, leak-channel measurement, zero LLM calls] · `decontaminate` · `probe run memorization` [31]

Every stage-resolving command also takes a repeatable `--model`/`-m` (`<role>`,
`<stage>=<role>`, or `<stage>=<provider>:<model>`) — the way to try a different model without
editing `config/models.yaml`. See `USER_GUIDE.md` §7.

Every command also takes `--series`/`-s` (default `86`). Output is segmented per series under
`data/<id>/` and `dist/<id>/site/` — except the default `86` series and the LLM cache
(`data/cache/llm/`, content-addressed, shared across series on purpose) — so a second series can
never interleave with or overwrite the first's output. See `USER_GUIDE.md` §6 and
`paths.py::set_active_series`.

Full semantics and the required invocation order: **`USER_GUIDE.md`**.

## 7. Environment

Python **3.14**. Install with `pip install -e .`. Local model: Ollama +
`qwen2.5:14b-instruct-q4_K_M` (~9 GB, fits a 16 GB 5070 Ti with room for long context).
Paid default: Vertex AI via Application Default Credentials — `gcloud auth application-default
login`, then `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION=global` in `.env` (§2). Credentials
are optional at every rung: the pipeline runs on the OpenRouter free tier without a GCP project,
and fully local without any key, just with weaker output. Run `wiki doctor` first; it prints
exactly what is missing and which model each stage will actually use.

## 8. Current phase

See the top entry of `LOG.md`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
