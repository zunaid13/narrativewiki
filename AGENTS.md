# AGENTS.md — shared rules for Codex and Claude in this repo

**As of 2026-09-14: Codex and Claude are equivalent agents.** Either may decide what to build next,
implement it directly, and commit/push without waiting on the other's sign-off. The old
decider/implementer split (Claude plans, Codex only executes a pre-written `docs/tasks/*.md` spec)
is retired. Git history (commits, PRs) is now the record of who did what and why; there is no
separate approval gate. Plans live in `docs/vision/plans/NNNN-<slug>.md` (moved from
`docs/tasks/` 2026-09-24); each carries its own status line. Repo layout: `STRUCTURE.md`.

This does not relax the constraints below — those come from the maintainer directly, not from the
old role split, and still bind whichever agent is working.

---

## 1. Read this first, in order

1. **`CLAUDE.md`** — the project map. Use its file map (§5) to find a module instead of grepping for
   it; use its token-discipline order (§0) for everything else.
2. **`docs/CONTRACTS.md`** — data shapes, if the work touches a schema.

## 2. Files that stay off-limits to Codex

This is the one place Codex and Claude are *not* equivalent: Claude still maintains the project's
append-only planning/research record per `CLAUDE.md` §4 (new decisions go in `docs/vision/`, closed
phases in `docs/handover/`, progress in `LOG.md`). Codex does not write to these:

- `CLAUDE.md`, and everything under `docs/archive/` (frozen outward-facing docs)
- `VISION.md`, `docs/vision/PHASE_*.md`, `docs/handover/PHASE_*.md`
- `LOG.md`

If implementation work seems to require changing one of these, it doesn't — flag what you found (a
commit message, a PR description, a code comment) and let Claude or the maintainer fold it into
these docs.

Everything else — `src/`, `tests/`, `config/`, `docs/CONTRACTS.md` (if a schema actually changed),
`docs/vision/plans/*` (plans, unlike `PHASE_*.md`, are living documents) — is open to either agent, and both may commit/push it directly.

## 3. Standing rules (apply no matter who's working, or why)

- **Volume scope: Spice and Wolf, `--volumes 1-2`, only.** Never run a narrativewiki command across
  the full corpus, the `86` series, or an unbounded volume range — this is a direct, repeatedly
  reaffirmed maintainer instruction, not a task-protocol artifact, and picking your own scope does
  **not** extend to picking a wider volume range. *"only use 2 volumes... stick with spice and
  wolf... in the future when full pipeline and evaluation and benchmark is done, we will work on
  full series."* **Widened 2026-09-25:** Overlord `--volumes 1-2` is now in scope too
  (*"we are getting biased towards spice and wolf. consider overlord v1-2"*), as a second
  calibration corpus. Still two volumes per series, still never 86 or a full series.
  **Widened again 2026-09-25:** Ascendance of a Bookworm `--volumes 1-2` (Part 1 v01-v02), the
  first non-Yen-On corpus, placed in `corpus/` by the maintainer in answer to "which third
  corpus?" (*"ascendance of bookworm is now there"*). Mushoku Tensei is being downloaded; it is
  not in scope until the maintainer says so.
  **Widened 2026-09-25/26 (publication track, `docs/vision/PHASE_31.md`):** public-domain
  Gutenberg series are in scope: `leagues`, `littlewomen` (2 volumes), `pride` (3), and the
  headline long series **`anne`, volumes 1–6** (*"make at least one long public-domain series
  (5+ volumes) the headline corpus"*), plus their `-remap`/`-decon` twins. Runs past volume 2
  pass `--set models.profiles.vertex_flash.max_volumes=N` per command; `models.yaml` stays at 2,
  so the light-novel corpora above keep their two-volume cap. Resume state:
  `docs/handover/PHASE_31.md`.
  **Widened 2026-09-27 (`docs/vision/PHASE_32.md`):** the limit is now **5 volumes per series**
  (*"expand from 2 volume limit to a 5 volume limit for each series"*), and
  `vertex_flash.max_volumes` is 5. It covers Spice and Wolf, Overlord and Bookworm v1–5, plus
  *Middlemarch* Books 1–5, the ~60-character stress wiki. Still never 86, never Mushoku Tensei,
  never past volume 5.
- **One pipeline for every series** (maintainer, 2026-09-27). A series config may only convert the
  raw input into what the pipeline reads (EPUB selectors, skip files, volume patterns and breaks,
  title/author metadata). No per-series prompt, schema overlay, roster override or output patch.
  Hand-made facts belong in gold (`docs/eval/gold/`), where they measure the pipeline instead
  of correcting it.
- **Every LLM call goes through `llm/client.py`.** Never call a provider SDK directly, never
  hard-code a model name — route through `config/models.yaml` (`CLAUDE.md` §2). This is also what
  makes the cache real: `data/cache/llm/` is keyed on
  `sha256(provider+model+prompt+params)`, so an identical prompt is never billed twice. Never
  clear it to "get a clean run" — a cached answer is the same answer.
- **Spend the API only when nothing else moves the project forward** (maintainer, 2026-09-23).
  Prefer a deterministic stage, a cache hit, a fixture, or a stored-prompt replay. Before running
  anything that bills, state in one line why no cheaper path exists. Note that `wiki site build`
  re-renders the entire wiki for $0 — only `codex_summary`'s *evidence* hash gates a call — so
  emitter work needs no budget at all.
- **Tune on the smallest slice that can show the effect** (maintainer, 2026-09-23). Prompt and
  config A/Bs run on one volume or on stored prompts (`scripts/eval/replay_context_budget.py`,
  `scripts/eval/nli_kind_sweep.py`), never on a full `--volumes 1-2` pass. Confirm the winner with
  the full documented sequence once — `docs/handover/PHASE_28.md` §5 is the case where a
  candidate that won on stored prompts lost 7 points end to end.
- **Record every number in `docs/MEASUREMENTS.md`** (maintainer, 2026-09-23). Publication was
  reinstated 2026-09-25 (`docs/vision/PHASE_31.md`), and the ledger stays the durable home for
  any measured value, observation or claim; the paper cites it. Append a row with the value, the exact command, and the
  run id. Codex may write to this file; it is not in §2's off-limits list.
- **Structured fields are never LLM-generated** (`CLAUDE.md` §2) — they come from graph rows, not a
  prompt.
- **Use focused tests for each change** (maintainer instruction, 2026-09-15). Do not run the full
  suite on every iteration or completed change. Run tests covering the behavior and affected
  integrations; broaden only when a concrete regression risk or the maintainer calls for it.
  A regression anywhere is still your problem to fix or flag.
- **Never install packages, edit `.gitignore`, or touch anything outside the repo working tree**
  without it being clearly necessary for the change at hand.
- **When something is ambiguous or two requirements conflict, stop and write the conflict down**
  (commit message, PR description, code comment) rather than guessing and shipping something
  plausible — see `docs/archive/CONVINCE_ME.md` §2 (the 0.303 → 0.033 retraction) for what an unaudited headline number costs.
- **Commits and pushes are real, visible actions** — write a commit message that says what changed
  and why, the same way you'd want to read one six months from now.
- **Commit finished work by default** (maintainer, 2026-09-04; written here 2026-09-24 because
  it had lived only in Claude's private memory). Once a change is complete and verified, commit
  it without waiting to be asked. That includes research and plans. A plan left uncommitted in
  the working tree can be lost, or folded into someone else's commit. Stage only the files that
  belong to the work. If your sandbox cannot write `.git`, say so in your final message so the
  maintainer knows the work is uncommitted. Destructive git operations still need explicit
  authorization.
- **Quality is never traded for call count** (maintainer, 2026-09-21, `docs/vision/PHASE_26.md`).
  No call-saving change ships on cost grounds without an A/B showing equal yield;
  `extraction.window.max_windows_per_request` stays at 1.

## 4. Research uncertainty, then leave an executable plan

Maintainer instruction, 2026-09-23: when continuing the project and unsure what to do next,
investigate the issue and research potential solutions, including recent research papers when
relevant. Prefer primary sources and distinguish a paper's findings from an untested adaptation
to this project. Save the resulting implementation plan as `docs/vision/plans/NNNN-<slug>.md` (next free
number) so another contributor
can continue without the conversation. Include the evidence for the problem, source links and
reading depth, proposed changes and files, ordered experiments, validation/stop criteria, commands,
current status, and unresolved decisions. Record measured findings in `docs/MEASUREMENTS.md`.
Update the plan as work proceeds; do not leave the next step only in chat. This does not authorize
extra API spend, broader corpus scope, or changes to the protected planning files in §2.
