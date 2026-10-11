# docs/handover/PHASE_24.md — leak measurement and cutoff-consistent entity discovery

**Written retrospectively on 2026-09-24**, during the repository restructure, because the phase
closed without one. It is an index into the real record, not a re-telling:
`docs/vision/PHASE_24.md` (every decision, correction and number, dated) and `VISION.md`'s
2026-09-11 → 2026-09-20 lines. Paths below are post-restructure (`STRUCTURE.md` translates the
old ones used inside those records).

## 1. What this phase was

It opened on 2026-09-11 as a research programme (Leak@t, a contamination-controlled benchmark,
see `docs/archive/GUIDE_TO_PUBLISHING.md`). **That framing is retired**: as of Phase 29 the
project is not on a publication pathway. What survives is engineering, not a paper.

## 2. What exists because of it

- `src/narrativewiki/probe/` — leak-channel measurement with zero LLM calls: `futureset.py`
  (`F>t`), `channels/index.py` (L_build), `channels/leak.py` (L_query), `channels/disclosure.py`,
  `report.py` (JSONL). CLI: `wiki probe run`. Outputs: `docs/probe/*.jsonl`.
- `wiki gazetteer --gate=build` — cutoff-consistent entity discovery, carried through to claim
  extraction (former TASK-0001).
- `tests/test_spoiler_leak.py` — the invariant test in `CLAUDE.md` §1.
- The per-volume-OR capitalisation ratio in `entities/candidates.py` (plan
  `docs/vision/plans/0004-*`), the fix for "Wisewolf" vanishing as the corpus grows.
- MiniCheck support scoring (`llm/providers/minicheck.py`, `graph/support.py`), validated by
  `scripts/eval/nli_controls.py`. It is **not** the default arbitration path (2026-09-20 entry).
- The papers inventory, now `docs/papers/`.

## 3. Decisions and corrections a successor must not relearn

Each has a dated entry in `docs/vision/PHASE_24.md`:
- The H1–H4 hypotheses were replaced by a four-channel leak taxonomy; H4 was retracted (PPR was
  already cutoff-correct).
- The first L_build headline measured selection consistency, not disclosure. Read the
  2026-09-13 (pm) audit before quoting any leak rate.
- The "individuation" finding went through two corrections: first its count, then its mechanism
  (an epithet-mining artifact plus a corpus-composition-dependent filter, not alias clustering).
- The maintainer cancelled the 86 de-risking run (TASK-0002). **A plan written by an agent is not
  authorization for wider scope**, and scope stays Spice and Wolf v1–2 (`AGENTS.md` §3).
- `--nli` as the default arbitration flagged about half of all facts, almost all RELATIONs. That
  is a calibration gap, not a verifier fix.

## 4. Reproduce

`wiki probe run index --series spice-and-wolf` (zero LLM calls), and the scripts under
`scripts/probe/`. Each script's header gives its exact command. Measured values live in the
vision entries; rows added from Phase 29 onward live in `docs/MEASUREMENTS.md`.
