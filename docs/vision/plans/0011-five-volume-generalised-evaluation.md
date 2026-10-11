# 0011 — Five-volume evaluation of a generalised pipeline

**Status:** in progress (opened 2026-09-27). Requirements and diagnoses: `docs/vision/PHASE_32.md`.
Living document: update the status column as work lands. Numbers go to `docs/MEASUREMENTS.md` §48+
first.

## Corpora and scope

| Series | Volumes | Cast | Note |
|---|---|---|---|
| `spice-and-wolf` | 1–5 | small (≈15 chars at v2) | Yen On |
| `overlord` | 1–5 | large, aliases as plot | Yen On |
| `bookworm` | 1–5 (Part 1 v1–3, Part 2 v1–2) | first-person narrator | J-Novel Club |
| `middlemarch` (new, Gutenberg #145) | Books 1–5 | ≈60 named characters | stress test (req. 7) |

The interlock `vertex_flash.max_volumes` becomes 5. Anne, Leagues and the other Phase 31 series
keep their per-run `--set` and are not re-run by this plan.

## Stages (in order; cheap before billed)

| # | Stage | Cost | Status |
|---|---|---|---|
| S1 | **$0 emitter fixes.** Delete `changes_later` (req. 9; `site/okf.py`, `cli.py`, `synth/assemble.py`). Delete `conflicts.quiet_change` so superseded values render as "previously: X (vA–vB)" (req. 6). Remove character images: `ingest/images.py`, image rendering in `site/mkdocs_wiki.py`, `images.md`, CONTRACTS §1.5 (req. 4). A test asserts that no rendered page contains "changes later". Rebuild with `wiki site build` | $0 | done (977ea02) |
| S2 | **Generalise (req. 8).** Move every `entity_overrides` block into `docs/eval/gold/<series>/roster.yaml` as ground truth. Delete `config/extraction.overlord.yaml`: `AFFILIATED_WITH` accepts `[FACTION, LOCATION]` for every series, and the tech codex gets one generic title. Delete `prompt_vocabulary`: prompts say "novel", not "translated Japanese light novel". Replace the two few-shot examples naming S&W characters (`extract/scenes.py`, `graph/verify.py`) with invented names. Titles a page at cutoff N by the most-mentioned alias with `first_vol ≤ N` (replaces the Hamsuke/Myne renames). Excludes paratext names equal to `series.author`/`illustrator`. Then score the override-free roster against `roster.yaml` | $0 for rules; the gazetteer's LLM steps may miss cache | done: overrides -> gold, general alias rules (first-volume naming, kinship, appositive, cannot-link, honorific, adjective, preposition) |
| S3 | **RANK semantics (req. 5).** Define `RANK` in `extraction.yaml` as a formal grade inside a named organisation or hierarchy (military rank, guild/adventurer grade, noble rank). It is never a power level or a game statistic. Batched with S4's prompt changes, because every prompt change misses the cache | batched | done: RANK/OCCUPATION/ORIGIN/TITLE defined |
| S4 | **Recall at fixed precision (req. 1).** First classify every gold miss at v2 as never extracted / withheld by a gate / in graph but not on the page, using `audit eval`'s own verdicts, which cost $0. Then read the papers (FACT NAACL-F 2025, Recall Them All 2024, and §G of PAPERS.md) and change only the dominant miss class. A/B on one volume or on stored prompts | small | done: gleaning measured and rejected; verifier judges by definitions (Leagues 24/40 -> 21/24); Traits + Background-by-volume sections |
| S5 | **Real precision metric.** `scripts/eval/assertion_precision.py`: a seeded random sample of rendered structured assertions (attributes + relations) at each cutoff, each with its cited paragraph. The judge reads them and writes a verdict file. The metric is hand-verified precision with its denominator, and MiniCheck runs alongside as a free screen | $0 | done: baseline 99/120 (82.5%) hand-read |
| S6 | **Gold for v3–5.** Extend each gold YAML with per-fact `first_vol`, transcribed from the reference wiki via search and grep-vetted against the text. Multi-cutoff recall scores facts with `first_vol ≤ t`; leak scores `first_vol > t` facts that appear on a t page. The Middlemarch gold is written the same way | $0 | done: text-grounded gold for 4 series |
| S7 | **Five-volume runs.** For each series: ingest v1–5 (inspect the new EPUBs for traps first), gazetteer, scenes, extract, infobox, backstory, graph, verify, synthesize, site, then every `audit`. Measure recall, audited precision, leak curve t=1..4, prose citation entailment, page balance and link connectivity | ≈$25–40 total | in progress (scripts/run_series.py) |
| S8 | **Fix what got worse (req. 3).** Compare against the v1–2 numbers. For each regression, research, change the general pipeline, and re-run only the smallest slice that shows the effect | TBD | todo |

## Validation / stop criteria

- `tests/test_spoiler_leak.py` passes at every step. A leak stops the run.
- Audited precision below 100% blocks every recall change until each false assertion is explained
  and its general cause is fixed.
- Three consecutive Vertex quota failures stop the run, which is then reported (standing rule).
- `hard_stop_usd` stays $10 per run. A 5-volume series runs stage by stage, so no one process
  exceeds it.

## Commands (fill in as they are run)

```
.venv/Scripts/python.exe -m narrativewiki.cli site build --series <s>
.venv/Scripts/python.exe -m narrativewiki.cli audit eval --series <s>
```

## Open decisions

- None yet. Anything ambiguous found during S2 is written here before it is resolved.

## Log

- 2026-09-27: S1-S6 landed (MEASUREMENTS §48). Real precision of the shipped v1-2 wikis is
  82.5% hand-read; every miss is a relation label or a mis-filed field. The verifier now judges
  by the predicate definitions. Gleaning was rejected on precision. Next: final gazetteers, then
  `scripts/run_series.py <s>` for spice-and-wolf, overlord, bookworm, middlemarch.
