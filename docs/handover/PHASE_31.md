# docs/handover/PHASE_31.md — publication track: decontaminated Gutenberg novels (IN PROGRESS)

Written 2026-09-26 at a pause, not at phase close. A cold contributor should be able to continue
without reading source. Design reasoning: `docs/vision/PHASE_31.md`. Executable plans:
`docs/vision/plans/0009-parametric-leakage-gutenberg.md` (experiments E0–E5) and
`0010-multi-cutoff-evaluation.md` (multi-cutoff corpus, with a correction section). Every number:
`docs/MEASUREMENTS.md` §43–§45. Papers: `docs/papers/PAPERS.md` §G (9 PDFs added).

## 1. Where things stand — read this first

**Update 2026-09-26, later: the Anne run is complete.** Every stage done, all 8 audits OK, leak
curve t=1..5 written and every positive read by hand: 0 leaks (MEASUREMENTS §47). Fixed on the way:
a real spoiler leak (future aliases in page front matter), the verify call cap (the driver sets
`max_calls_per_run=6000` per run), and three dead-link bugs that only a principal-cast build
exposes. §7 step 1 is done except reading the site as a reader. Next: §7 step 2. The rest of this
section is the pause-time state, kept for the record.

**Paused mid-run.** The headline Anne series (six books) stopped at window extraction v5–v6
on a **Vertex 429 RESOURCE_EXHAUSTED** (quota for `gemini-3.1-flash-lite`, global endpoint)
from ~19:55 UTC 2026-09-25. It recovered briefly at 21:34, then failed on every retry until
00:34. That looks like a daily quota, though that is unconfirmed. Done for Anne: ingest,
gazetteer (reviewed), scenes v1–6, window claims v1–v4. Not done: claims v5–6, infobox,
backstory, graph, synthesis, site, audits, leak curve.

**Resume with one command** (429-aware; retries every 15 min; stops on any other failure; ends
with the t=1..5 leak curve written to `docs/eval/pipeline_leak_anne_v{t}.json`):

```
.venv/Scripts/python.exe scripts/probe/anne_driver.py --from extract-v5-6
```

Per-step logs go to `data/anne/_driver/<step>.log`. First check that Vertex answers at all (one tiny call).
The earlier failed `extract-v5-6` runs are recorded as `failed`, so `audit claims` shows FAIL
until a successful run supersedes them. That is expected.

## 2. Things you must know before touching anything

1. **Scope and interlock.** Publication was reinstated 2026-09-25 (supersedes the 2026-09-23
   "not a publication project" ruling). Gutenberg series are in scope. `config/models.yaml` keeps
   `vertex_flash.max_volumes: 2`, so the light-novel corpora stay capped mechanically. Runs past
   volume 2 pass **`--set models.profiles.vertex_flash.max_volumes=6`** per command (the driver
   does this). Do not raise it globally.
2. **Money.** Lifetime cap **$200** (raised from $20). Spent: **$18.92** (Leagues ≈ $1.9 incl.
   decontamination and probes, Anne $4.21). A 429 is not billed; every completed call is cached.
3. **Never switch provider inside a series** to get past a quota error. A mixed-model series
   confounds the per-model comparison, which is now central to the paper (see §4).
4. **Anne is a principal-cast build** (25 characters = 69% of character mentions,
   `docs/eval/parametric/anne_cast.txt`), chosen to cap unattended spend. Whether to build all 313
   characters is the maintainer's decision.
5. How to run things: `.venv/Scripts/python.exe -m narrativewiki.cli <cmd> --series <id>`,
   with `PYTHONIOENCODING=utf-8`. Bash heredocs on this machine mangle backslash escapes
   (`\n`, `\.`): write any file containing them with the Write/Edit tool (it bit three times).

## 3. Corpora (all Project Gutenberg, `corpus/<id>/`, gitignored; download lines in each config)

| Series | Role | Volumes | Status |
|---|---|---|---|
| `leagues` (#164) | short-text control; E1–E3 done | 2 (split at PART TWO) | full pipeline done, all audits OK |
| `leagues-remap`, `leagues-decon` | names remapped / + paraphrased | 2 | built; E1, E3 done |
| `anne` (#45 #47 #51 #544 #5343 #3796) | **headline long series** (531k words) | 6 | paused at extraction v5 |
| `anne-remap` | names remapped (DRAFT map, 110 entries) | 6 | built, 0 residual names, **needs maintainer review** |
| `anne-decon` | names + paraphrase | 6 | config only; ~$1.7 to build |
| `littlewomen` (#514) | second two-part control | 2 | ingested only |
| `pride` (#42671) | three-volume control | 3 | ingested only |

## 4. Findings so far (hand-verified; MEASUREMENTS §43–45)

- **Renaming does not stop recognition.** A book is identified from name-remapped passages 55.7%
  (Gemini) / 67.0% (Qwen 14B); after remap + paraphrase, 34.7% / 30.7% (paired 101 items). Gemini
  still gives the original character name for 48.5% of paraphrased, renamed cloze passages
  (majority-guess baseline 21.7%).
- **Fact transfer is what decontamination stops.** Part Two facts on a name-only page: 32% on the
  original (Gemini and Nemotron alike), 0% on renamed text. With Part One in context the
  generator barely leaks: 0–4%, one Atlantis witness.
- **The gated pipeline leaks 0/25** Part Two facts on its v01 pages (control recall 87.5%).
- **Identity disclosure is a second channel, and it is model-dependent.** Nemotron writes the real
  identity on 4/12 remap and 4/12 decon pages ("In the original French text, this character is
  **Ned Land**"), even when told to use only the text. Gemini: 0/24.
- **Instrument limits.** MiniCheck errs both ways on page-level leak detection, and it cannot
  judge paraphrase fidelity (E0b read 46.5% on faithful pairs). Every positive above was read
  by hand. Memorisation item sets differ slightly per condition; compare on the paired
  intersection.

## 5. What changed in code this phase (all tested; 1131 passed)

| Area | Change | Where |
|---|---|---|
| Ingest | `source.volume_breaks` (one EPUB → reading volumes); `epub.drop_chapter_titles` (a drop that would delete >50 paragraphs raises); `epub.split_within_documents` (chapters inside one XHTML; number + title heading pairs kept, joined as the title) | `ingest/epub.py` |
| Audit | `audit ingest` FAILs a 0-paragraph volume | `audit/reports.py` |
| Decontamination | `wiki decontaminate` (remap, then paraphrase, same `para_id`s, `decon_report.json`) | `ingest/decontaminate.py`, `cli.py` |
| Probes | `probe run memorization` (name cloze + title ID); `probe run parametric` (context / noguard / closed pages, multi-cutoff gold via evidence ids) | `probe/memorization.py`, `probe/parametric.py` |
| Eval | `pipeline_page_leak.py` (pipeline pages vs gold at t), `decon_fidelity.py` | `scripts/eval/` |
| Candidates | leading conjunction stripped ("But Captain Nemo") | `entities/candidates.py` |
| Aliases | guarded tier-c: a short form joins longer forms only if their name cores are compatible (shared surname no longer fuses two people) | `entities/alias.py` |
| Quotes | stitched dialogue across speech tags; straight-quote dialogue; `quote_too_long` label | `extract/resolve.py`, `extract/*.py` |
| Graph | self-relations dropped; symmetric predicates type-check both endpoints | `graph/contradictions.py`, `config/extraction.yaml` |
| Site | empty image manifest ≠ images; curly marks on stitched quotes | `site/mkdocs_wiki.py`, `site/okf.py` |

Existing corpora re-ingest byte-identical (10/10 files); the alias rule changes 0 clusters on them;
the finished Leagues wiki rebuilds identically from cache (110/113 pages identical; the 3 others
are the designed v02-reuse pages).

## 6. Traps hit

- **Silent data loss** was the pattern again. Two Anne books parsed to 0 paragraphs and the
  ingest audit said OK. A drop rule deleted a whole novel. A series without
  `site.default_upto` silently built volume 1 only.
- **Family sagas break surname-based clustering.** Always review the top ~60 of `roster.html`.
- **First-person narrators** (Aronnax) get few claims. Bare "Walter" in Anne v01 is Anne's
  father, but it is folded into Walter Blythe: check Walter's v01 page once synthesis runs.
- `scenes` must run before `gazetteer --merge-epithets`. Re-running scenes afterwards misses
  the cache (the prompts embed the gazetteer).
- `load_settings` is cached per process, so a `--set` in a script persists for the rest of it.

## 7. Next steps, in order

1. Resume Anne (§1). Then read the site at v01–v06 as a reader, run every audit, and hand-verify
   the leak-curve positives, `docs/eval/pipeline_leak_anne_v{1..5}.json`.
2. E3 baselines on Anne at t ∈ {1, 3, 5}: `probe run parametric --series anne --volumes t --set
   models.profiles.vertex_flash.max_volumes=6`. At t=5 the context is ~700k tokens (~$0.2 per
   page call), so budget it. Add Nemotron as the second model (free tier, ~50 calls a day).
3. Maintainer review of the `anne-remap` map, then build `anne-decon` (~$1.7), then E1/E3 on it.
4. E0b fidelity with a validated judge. Add ≥3 samples per E3 cell before quoting.

## 8. Decisions waiting for the maintainer

- Full 313-character Anne build, or keep the 25-character principal cast.
- Approve or edit the draft Anne name map (`config/series.anne-remap.yaml`).
- Plan 0010 option B (Leagues split into 9 volumes, ~$2–4 per condition) as a within-book curve.
- Carried over from Phase 30: the Family line, Mushoku Tensei, a CREATED_BY predicate, per-cutoff
  search.
