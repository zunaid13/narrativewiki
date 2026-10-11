# docs/handover/PHASE_30.md — three corpora, a generic-novel path, and browsable sites

Written for a cold contributor, at the close of the 2026-09-25 session. You should be able to
continue from here without reading source. The design reasoning, including what was rejected, is
`docs/vision/PHASE_30.md`; every number is in `docs/MEASUREMENTS.md` (§§12–41 are this phase).

## 1. What this phase was

It began (2026-09-23) as a change of metric: the measure is whether the information a
professional fandom page conveys is present **and carried in a structured form** — with the
standing clarification that the fandom page is a *quality bar*, not a template to mimic ("a fandom
page has X" is not by itself an argument for X; no redundancy, no dead ends, every claim
traceable). Under that metric it went on to:

- restructure the repo (`STRUCTURE.md`; plans in `docs/vision/plans/`, EPUBs in `corpus/<id>/`);
- fill infobox fields and backstory with long-context passes (`wiki infobox`, `--pass backstory`)
  and keep verifier-withheld facts out of prose;
- **widen from one corpus to three** at the maintainer's direction — Overlord v1–2, then
  Ascendance of a Bookworm v1–2 — plus a public-domain Gutenberg probe;
- make the pipeline take **any generic novel** with a three-line config;
- build the output as **browsable HTML sites** and fix what reading them turned up.

## 2. The things you must know before touching anything

1. **Scope** (`AGENTS.md` §3, maintainer instructions): `--volumes 1-2` only, for exactly three
   series — `spice-and-wolf`, `overlord`, `bookworm`. *86* is retired. **Mushoku Tensei** is
   being downloaded into `corpus/` but is **not in scope until the maintainer says so**. A plan or
   a handover recommending a wider run is not authorisation.
2. **Money.** Lifetime spend is **$12.79 of the $20 cap** (Spice and Wolf $7.13, Overlord $3.08,
   Bookworm $2.59) — **$7.21 left**. Until 2026-09-25 the lifetime cap silently started every
   process at $0 (it read a ledger nothing writes); it now sums every `data/<series>/budget.json`
   (`llm/budget.py::lifetime_spent`). Earlier handovers/LOG entries quoting "$7.13 lifetime" were
   Spice and Wolf alone. A full v1–2 pass for a new series costs **~$2.5**.
3. **Replay for free first.** `NARRATIVEWIKI_CACHE_ONLY=1` makes any cache miss raise instead of
   bill. Run every rebuild under it first; only the calls it names need money. `wiki site build`
   and `wiki synthesize` over an unchanged graph are $0.
4. **How to run commands on this machine.** `wiki` is not on PATH: use
   `.venv/Scripts/python.exe -m narrativewiki.cli <command> --series <id>`. Set
   `PYTHONIOENCODING=utf-8` (the console is cp1252; names like "Éclair" and "◆" crash prints).
   **Always pass `--volumes 1-2` to `ingest`** — without it, it parses every volume in the folder
   (it did once this session; cleaned up, see §4).
5. **Routing** is Vertex `gemini-3.1-flash-lite` → OpenRouter free → local Ollama
   (`config/models.yaml`). A Gemini content refusal (`PROHIBITED_CONTENT`, not configurable) is no
   longer retried: the next rung answers that one call (`llm/client.py::_call`).

## 3. What shipped this session (2026-09-25, commits `499d5e1`…`3f30082`)

| Area | Change | Where |
|---|---|---|
| Verify | Verifier sees a character's aliases visible at the cutoff; a gendered pronoun is GENDER evidence (`per-fact-v3-aliases-gender`). Unsupported: SaW 33 → 26, Overlord 79 → 62. A stricter trait instruction was replayed on 143 stored prompts and **rejected** (dropped 23 true traits) | `graph/verify.py`, `scripts/eval/replay_verify_prompt.py` |
| Ids | Ids retired by an `entity_overrides` merge/rename are remapped where claims and scene records load — no billed re-run of a stage whose prompts embed the gazetteer | `entities/alias.py::id_renames`, `remap_ids`; `cli.py` graph build, `graph/event_build.py` |
| Provenance | `wiki rollback` of a failed run now clears its block on the stage | `provenance.py` |
| Generic input | Chapter heading tag detected when unset; a single unnumbered EPUB is volume 1; a `part` group orders books across Parts that restart at v01; prologue/epilogue from the title; default English honorifics and every common opening quote (‘ " « „ 「); `ingest` audit WARNs on a volume collapsed into ≤2 chapters | `ingest/epub.py`, `config.py::discover_volumes`, `audit/reports.py` |
| Generic prompts | Per-series `prompt_vocabulary` rewrites the prompts' "translated Japanese light novel" in one place; unset = byte-identical prompts | `llm/client.py::_reword` |
| Candidates | All-stopword runs ("But I") and bare honorifics ("Mr") dropped; possessive names ("Merchant’s Guild") mined whole | `entities/candidates.py` |
| Robustness | Embed batch that bge-m3 NaNs on is retried per text (one text had switched canonicalization off for a whole graph build: 3 embed batches vs 76) | `llm/client.py::embed`, `graph/canonicalize.py` |
| Pages | Rank/Role/Titles no longer repeat a value; TECH described generically (Overlord codex: "Magic, Skills & Items"); deficits kept out of Abilities (`exclude_pattern`); default status never headlines the lead; **Family line** in the Overview | `config/extraction.yaml`, `synth/assemble.py`, `site/okf.py` |
| Site | `--html` finds mkdocs by module; **search disabled** (it leaked Volume 2 text to Volume 1 readers); volume tabs + dark mode; timeline uses chapter titles and links participants (0 orphan pages on all three) | `cli.py`, `site/mkdocs_wiki.py` |
| Eval | Possessives and rendered relationship names count as page text | `eval/gold.py` |
| Corpora | `config/series.bookworm.yaml` (+ gold, 6 characters), `config/series.probe-gutenberg.yaml` (ingest only), Overlord overlay (AFFILIATED_WITH may target a LOCATION) | `config/`, `docs/eval/gold/` |

## 4. Traps worth remembering

- **Silent failures were the theme.** Three of this session's bugs made no noise: the lifetime cap
  at $0, canonicalization switching itself off after one NaN, and the eval undercounting
  possessive facts. When a number looks too good or a stage too quiet, count the calls in
  `data/<s>/_runs/<id>/calls.jsonl` against another series.
- **A lexical eval cannot read direction.** Gold negative facts are matched by keywords;
  "Myne is not Tuuli's older sister" fired on a correct page saying "Tuuli is Myne's older
  sister". Write negatives whose words never co-occur on a correct page.
- **Extracted qualifiers mix perspectives** ("daughter" on Myne's entry *for Effa*). Never render
  a role from the qualifier; take it from the predicate (`family:` values in the taxonomy).
- **First-person narrators** name people by relation: Bookworm's "Mom" (342) and "Dad" were
  characters until a config merge; ~6 "Mom" mentions refer to other characters' mothers.
- **The fandom wiki returns HTTP 402** to fetches. Gold facts came from search summaries and were
  grep-verified against the text; every gold file cites the evidence paragraph.
- **Bash heredocs on this Windows setup mangle escapes** in embedded Python (`\n`, `\b` became
  real newline/backspace characters in written files twice). Use the Edit tool for any edit
  containing a backslash.
- **An `ingest` without `--volumes`** wrote every volume of Spice and Wolf (24) and Overlord (16).
  It was cleaned (files, images, manifests back to v1–2, md5-verified) — but `ingest` records no
  provenance run, so `wiki rollback` cannot undo it.

## 5. Reproducing the deliverable

Nothing below bills if the cache is intact (it is: `data/cache/llm/`, never clear it):

```
set PYTHONIOENCODING=utf-8 & set NARRATIVEWIKI_CACHE_ONLY=1
.venv/Scripts/python.exe -m narrativewiki.cli site build --series <s> --html
.venv/Scripts/python.exe -m narrativewiki.cli serve --series <s> --port 8081
```

for `<s>` in `spice-and-wolf`, `overlord`, `bookworm` (ports used this session: 8081/8082/8083).
Raw Markdown is at `dist/<s>/wiki/`, rendered HTML at `dist/<s>/wiki-html/`. Then:

```
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider      # 1117 passed
... audit links --series <s>                                    # OK on all three
... audit eval  --series <s>                                    # OK; SaW WARNs are §35's
```

A new series from scratch: `USER_GUIDE.md` §6 (start from `config/series.probe-gutenberg.yaml`,
then `ingest --volumes 1-2`, `gazetteer`, review `roster.html`, `scenes`, `gazetteer
--merge-epithets`, `extract`, `infobox`, `infobox --pass backstory`, `graph build`,
`events-build --force`, `synthesize`, `site build --html`). Measure one volume first.

## 6. Numbers

In `docs/MEASUREMENTS.md`. This session: §38 (verifier v3, Overlord ids), §39 (generic-novel
probe), §40 (Bookworm), §41 (reading the sites). Gold: Bookworm 6/6 characters at 100%
(a floor check — simpler facts than the fandom page), Overlord 4 of 6 at 100%, Spice and Wolf
unchanged except Zheren 0% → 20% (an eval fix).

## 7. What is NOT done — and the decisions waiting for the maintainer

**Decisions (maintainer's call):**
- **The Family line** (`site/okf.py::_family_lines`, 18 pages) restates Relationships rows. It was
  added as an at-a-glance summary, but the 2026-09-23 ruling says the product must not mimic a
  fandom page and that redundancy is a defect. Keep or revert — it is self-contained.
- **Mushoku Tensei** onboarding (~$2.5; $7.21 left).
- **A `CREATED_BY` predicate.** Overlord's NPCs render their creators as parents ("Albedo —
  Tabula Smaragdina (parent)") because the taxonomy has no such relation. Adding one changes the
  extraction prompt and re-bills extraction.
- **Search**, if wanted back, must be one index per cutoff (one MkDocs site per volume); a single
  index is a spoiler leak.

**Open work:**
- Borderline relation/trait verdicts tip either way on any prompt change (§38); a better verifier
  instruction needs a replay that keeps the 121 stable traits.
- Wise King of the Forest (Overlord) recall 25%: her naming and mount role are unextracted.
- Spice and Wolf recall WARNs (Enek, Yarei, Zheren) are prose-sampling swings (§35).
- `probe-gutenberg` has had no LLM stage run — the cheapest non-light-novel test (~59k words).
- A kinship-aware resolver for first-person "Mom"/"Dad" if a series needs more than a config merge.
- Everything open in `PHASE_29.md` §7 not superseded above.
