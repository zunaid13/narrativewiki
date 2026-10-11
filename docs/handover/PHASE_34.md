# docs/handover/PHASE_34.md — version 2, the decontaminated matrix, the human check (IN PROGRESS)

Written 2026-10-07 01:35 local time (19:35 UTC on 2026-10-06). Requirements: `docs/vision/PHASE_34.md` (2026-10-04 and 2026-10-07 entries).
Earlier state: `docs/handover/PHASE_33.md` (top section) and `LOG.md`. Every number below has a row in
`docs/MEASUREMENTS.md` (rows dated 2026-10-04 to 2026-10-07); every label change is in `docs/eval/CHANGES.md`
(C31 to C43).

## 0g. State at 2026-10-08 19:50 UTC (2026-10-09 01:50 local) — newest; every reported cell has its citation labels

Everything in sections 0d and 0f on submission still holds. Added since, at $0 (no model call):

- **What exists:** `cite` verdicts in `docs/eval/precision/<series>_v<t>_all.jsonl` for `anne@b3` t=1..5,
  `anne@b4-v2` t=2..5, `anne@x2` t=1..5 and `anne@p<t>-v2` at t; timeline rows of the prefix builds in
  `precision/timeline_cite_claude.json`. Verdicts as entered: `precision/labels_claude/<series>_v<t>.cite.json`
  and `.tlcite.json`. Rule: the cited paragraphs, read alone and jointly, must establish every element of the
  statement; a trait shown by one loosely related act, or a name the paragraphs do not give, is partial.
- **Result:** original-text citation sufficiency, mean over cutoffs: LightRAG 0.765, graph baseline 0.915,
  full text 0.625 (long context 0.658, prefix retrieval 0.774, reported system 0.512 as before). Prefix builds
  91 of 159 at t=1..4. Ledger section "2026-10-09 — Citation sufficiency for the cells that had none"; C52.
- **How to redo a cell:** `docs/eval/labelling_tools/m8group.py <series> <t> 900` (the view), `para.py` for a
  cut paragraph, write the `.cite.json`, `m8recf.py <series> <t>`; for timeline rows `.tlcite.json` and
  `tlrec.py`. Then `paper_observations.py <series> --system <S> --work anne`, `paper_numbers.py` on the seven
  files with the six pairs (the command is in `docs/eval/paper_numbers.json` under `inputs`), and the fill chain.
- **Trap:** `fill_results.py` rewrites the ledger comment of all 205 keys it computes. Keep a copy of
  `results.tex` first and put the old line back wherever the value did not change (this session did it with a
  30-line script; `git diff` of `results.tex` should show only the keys that moved).
- **Trap:** a Codex session was editing `paper_codex/`, `scripts/papers/` and the end of `docs/MEASUREMENTS.md`
  while this one ran. Its section in the ledger was uncommitted; this session committed only its own rows.
  `paper_codex/` does not have the new values.
- **Still owed:** the Responsible NLP checklist, the exact Codex model name, a human check of the labels made
  since 2026-10-08. The anonymous archive (`dist/narrativewiki-anonymous-release.zip`, 14,220 files) and the
  anonymous clone (12,764 files, commit `ee2ec8b`, one ahead of its origin) were rebuilt after this change and
  both scans are clean; the maintainer has to push the clone for the mirror to show it.

## 0f. State at 2026-10-08 16:20 UTC (22:20 local) — superseded by 0g where they differ; prefix-discovered builds in the paper

Everything in section 0d on submission still holds, except that the anonymous repository now exists (its
address is in `macros.tex`; rebuild it with `scripts/papers/make_submission_repo.py` after any change).

- **What exists:** `data/anne@p<t>-v2/` and `dist/anne@p<t>-v2/wiki/` for t=1..4: the reported system built on
  volumes 1..t with the entity index of that prefix. Labels: `docs/eval/recall_hand/anne@p<t>-v2_v<t>.json`,
  `docs/eval/precision/anne@p<t>-v2_v<t>_all.jsonl` (scene verdicts in `pair_strict_claude.json`),
  `docs/eval/leak_audit/anne@p<t>-v2_tree.jsonl`. Only cutoff t of build t is scored and labelled.
- **Result:** recall 180 of 224 in both builds over t=1..4; precision 134 of 159 (prefix) and 130 of 159 (full)
  on different samples; no stated later fact in either. Ledger rows of 2026-10-08; CHANGES C50.
- **Paper:** keys `PX-anne-*` are typed in `docs/paper/_build/fill_v2.py`; Table `tab:prefixv2` in Appendix G.
  Fill order is unchanged (`fill_results`, `fill_v2`, `fill_decon`, `summary_stats`, `bold_tables`,
  `derived_values`). Dollar figures are gone from the paper (tokens instead, C47); the cutoff figure is bars.
- **Page limit, the check that works:** after `build.sh`, `pdftotext -layout main.pdf`, split on form feeds,
  and the ninth page must begin with "Limitations". Looking for the heading "8 Conclusion" on page 8 is not
  enough (it was wrong once today). Section 6.3 has about three spare lines.
- **Decided against:** prefix builds on the treated text (maintainer: "forget it"); changing the miner for gap
  G19 (the split is reported instead, C49).
- **Trap:** `docs/eval/` holds untracked extras from the t=4 runner (`pipeline_leak_anne@p4-v2_v{1,2,3}.json`,
  `artifact_exposure_anne@p4-v2.json`, `precision/anne@p4-v2_v{1,2,3,4}.jsonl`): not part of any reported cell.
- **Owed:** the Responsible NLP checklist, the exact Codex model name, a human check of the new labels.

## 0e. State at 2026-10-07 22:30 UTC (2026-10-08 04:30 local) — newest; identity dependence measured and in the paper

Everything in §0d still holds (the three things owed by the maintainer, the deadline, the order of the fill
scripts). Added since:

- **Run:** `sh docs/eval/runners/prefix_gazetteer.sh anne@v2` built the v2 entity index from volumes 1..t alone
  for t=1..4 under `data/anne@v2/@t0N/02_entities/` (0.21 USD; lifetime cap passed as 425 on the command only,
  ledger 415.33 after). It is resumable and skips a finished cutoff.
- **Metric:** `.venv/Scripts/python.exe scripts/eval/identity_dependence.py anne@v2` ($0) writes
  `docs/eval/identity_dependence_anne@v2.json`. Over character pages: 0.390, 0.256, 0.133, 0.089 at t=1..4.
  Classes and the mention-coverage figure are defined in the script header.
- **Paper:** Section 6.3 (last paragraph), Appendix G (`tab:identity`), Limitations. Keys `ID-anne-*` are typed in
  `docs/paper/_build/fill_v2.py` from the JSON; if the JSON is regenerated, retype them there.
- **Decided against, for now:** building extraction, graph and pages on the prefix indexes (a version-2 prefix
  build): about the cost of the first version's prefix builds (11.58 and 17.23 USD at t=2, 3) plus labelling,
  four days before the deadline. The treated text was not run: the question was answered on the original.
- **Trap:** the prefix index is thinner for a reason that is the miner's, not the prefix's (OPEN_GAPS G19); do not
  read 0.390 as pure construction dependence, and do not read it as a defect only: both are in the ledger row.
- **Freeze:** `v2l` replaces `v2k` (one script added). The anonymous archive must be rebuilt before upload:
  `.venv/Scripts/python.exe docs/paper/_build/make_release.py`.

## 0d. State at 2026-10-07 20:35 UTC (2026-10-08 02:35 local) — newest; the paper was audited and is ready but for three things only the maintainer can supply

**What happened.** The paper was read against the label files, its references against the ACL Anthology and
arXiv records, and its format against the ARR call. Everything found was fixed in place (CHANGES C45, five
ledger rows of 2026-10-08, `docs/paper/README.md`). No label was changed, no model was called, no cell moved.

**Deadline.** NAACL 2027 and COLING 2027 share the ARR October 2026 cycle: **submission by 2026-10-12, anywhere
on earth**. Long paper, 8 pages of content; Limitations is required and not counted; the primary venue is
chosen at commitment (NAACL commitment 2026-12-23).

**Before submitting (maintainer):**
1. Create the anonymous mirror and put its address in `\anonrepo` (`docs/paper/macros.tex`); the PDF prints
   the placeholder `anonymous.4open.science/r/narrativewiki-0000`. Upload the CONTENTS of
   `dist/narrativewiki-anonymous-release.zip` (rebuilt 2026-10-08: 11,615 files, scan clean), never the
   repository: the ledger, the runner scripts and `make_release.py` hold a cloud account name and project ids
   that only the archive builder replaces. After any further change:
   `.venv/Scripts/python.exe docs/paper/_build/make_release.py` (it exits 1 if such a string survives).
2. Fill the Responsible NLP checklist: LLM annotation and its human review (role of the reviewer, paid or not,
   time, whether they knew the books, consent), AI assistance in code, text and Figure 1, compute and cost.
3. Record the exact model the Codex agent ran (the paper says "GPT-6"; OpenAI lists several GPT-6 models).
4. Submit `dist/NarrativeWiki-paper-submission.pdf` (the copy with line numbers).

**After any label change** run, in this order: `scripts/papers/fill_results.py`, `docs/paper/_build/fill_v2.py`,
`docs/paper/_build/fill_decon.py`, `scripts/papers/summary_stats.py`, `docs/paper/_build/bold_tables.py`
(2026-10-08: it puts the bold back on the values that carry each table's finding; `summary_stats.py`
rewrites one table without it), then
`docs/eval/labelling_tools/derived_values.py`, which compares every hand-typed value with the labels.

**Freeze.** `v2k` replaces `v2j` (one script changed: `scripts/papers/summary_stats.py`, formatting only). The
finished runners name `v2j`; change the name in a runner before restarting it.

**What a reviewer will say** and what would change it: `docs/paper/REVIEW_2026-10-08.md`. In one line: one work,
LLM labels without an independent human annotation, and a system that loses to its baselines on recall,
precision and citations; the measurement protocol and the treated-text diagnostic are the contribution.

## 0c. State at 2026-10-07 19:45 UTC (2026-10-08 01:45 local) — superseded by §0d where they differ; the matrix and the paper are done

**Done.** The decontaminated matrix is complete: 7 systems x 5 cutoffs on `anne-decon`, every cell built with
0 failed pages (one page recovered, CHANGES C44) and labelled for recall, precision and citation sufficiency,
with disclosure at t=1..4. No job is running, no lock is left, Ollama is idle. The paper reports all seven
systems on the treated text (`\nwdecontrue`): `docs/paper/NarrativeWiki-paper.pdf`, `dist/NarrativeWiki-paper.pdf`,
`dist/NarrativeWiki-paper-submission.pdf` (45 pages, 0 errors, 0 overfull, conclusion ends on page 8).

**Treated text, means over five cutoffs** (ledger rows of 2026-10-07; keys `*-annedecon-*` in `results.tex`):

| System | Recall (original) | Precision (original) | Citation sufficiency (original) | Disclosed of 220 |
|---|---|---|---|---|
| Main `@v2` | 0.843 (0.802) | 0.770 | 0.625 | 4 |
| Long context `@b1` | 0.845 (0.848) | 0.920 (0.929) | 0.530 (0.658) | 0 |
| Prefix retrieval `@b2` | 0.784 (0.834) | 0.950 | 0.885 (0.774) | 0 |
| LightRAG `@b3` | 0.470 (0.536) | 0.960 (0.950) | 0.794 | 0 |
| Graph baseline `@b4-v2` | 0.704 (0.761) | 0.940 (0.965) | 0.895 | 2 |
| Closed book `@x1` | 0.003 (0.683) | 0.145 | none | 0 |
| Full text `@x2` | 0.744 (0.814) | 0.845 (0.910) | 0.475 | 23 (original 8) |

**What the paper says that is new** (Section 6.4, Limitations, appendix "Contamination Diagnostics and the
Decontaminated Condition"): full text discloses 23 of 220 later facts on the treated text against 8, eight of
them at t=1 where the original build disclosed none; long-context citation sufficiency falls from 0.875 to
0.375 with citations that keep a paragraph number and lose its volume; six treated pages print the island's
real name, which the treated text does not contain; two namesakes made by the name map cost pages.

**Not claimed, and still open:** why citations degrade faster on the treated text; why full text keeps the
cutoff worse at t=1; the prefix-retrieval citation gap (0.885 treated against 0.774 original). Each condition is
one build. The citation labels of LightRAG are by two agent readers (a 15-row calibration is in the ledger);
long context t=1 is by another reader than t=2..5.

**For the human check, listed in the ledger:** graph baseline t=3 row 17 and t=5 row 33 (one citation line read
two ways); the rows where the page label and the atom label differ (full text t=2 rows 2, 3, 38; t=3 rows 3,
37; t=4 row 33; t=5 rows 0, 1; long context t=2 rows 34, 39).

**Owed by the maintainer** (the paper does not invent them): the human reviewer's role, whether paid, time
taken, whether they knew the books, consent to release the labels.

**If anything is rebuilt:** spending rules are in the ledger row "the lifetime cap of 390 was reached" (cap 400
was passed per command for the last 16 pages; `config/models.yaml` is still 318 under freeze v2j). Runners:
`docs/eval/runners/fix_v2_decon_rest3.sh` (billed, resumable), `score_decon_worker2.sh <sys>:<t>` (local),
`recover_page.py` (a page lost to a mismatched bracket). To refresh the paper: `docs/paper/README.md`.

## 0b. State at 2026-10-07 11:05 UTC (17:05 local) — superseded by §0c; kept for the procedures

**Who does what.** One session owns the phase (it took over at 08:53 UTC from the maintainer's handover prompt).
The earlier paper session stood down but still owns the runner processes as its background tasks: if it is
closed they die (`ps -ef | grep "docs/eval/runners"`, then restart as below). The second labelling session
finished the graph baseline (t=1..5) and LightRAG t=1, 2 and holds nothing.

**Matrix (7 systems x 5 cutoffs on `anne-decon`).** Labelled in full: `@v2`, `@x1`, `@b2`, `@b4-v2`, `@b3`.
- `@b1` long context: recall and disclosure t=1..4; precision and citation t=1..4 (0.975 · 0.950 · 0.900 · 0.825
  and 0.875 · 0.675 · 0.425 · 0.300). **t=5 is not built** (30 of 43 pages, stopped at the $10 per-run stop; the
  second-pass runner resumes it after the first pass ends).
- `@x2` full text: t=1 built (14 pages; the main character's page recovered from its recorded response,
  CHANGES C44) with recall 19/23 and disclosure 8 of 88; precision sample being scored. t=2 building; t=3..5 not
  built. About 3.5 minutes a page, 20 to 43 pages a cell.

**Jobs.** `fix_v2_decon_rest.sh` (paid first pass, on X2 t=2..5, lock `data/fix_v2_decon.lock`);
`fix_v2_decon_rest2.sh` (waits for that lock; then B1 t=5 and whatever is not logged ok; then scores b1 and x2
cells); `log_keeper.sh`. Scorer 1 has finished its queue. Score a built cell at once with
`sh docs/eval/runners/score_decon_worker2.sh x2:<t>` (one worker at a time on a cell).
**If a full-text or long-context cell is logged with "N pages, 1 failures" on every attempt:** the response is
cached and malformed (a list closed with `}`); retries cost $0 and never succeed. After the runner's last
attempt (`<SYS> t=<t>: FAILED` in the log): `python docs/eval/runners/recover_page.py anne-decon <SYS> <t>
"<Character>"`, then append `HH:MM <SYS> t=<t>: ok` to `data/fix_v2_decon.out` so the second pass does not
rebuild the cell (a rebuild deletes the recovered page), and add a ledger row.

**To label next, in this order as cells land:** `@x2` t=1 precision + citation; `@x2` t=2..5 (recall via
`recall_patterns.py --view anne-decon@x2 --upto <t>`, disclosure via `scripts/eval/m4_tree.py` for t<=4, then
extend the `anne-decon@x2` entry of `labelling_tools/decon_labels.py` and its `"cutoffs"`, run it, and
`strict_reread.py` must print nothing; then precision + citation); `@b1` t=5 the same way (add 5 to its
`"cutoffs"`). Label files as `docs/eval/precision/labels_claude/anne-decon@b1_v4.json` / `.cite.json`.
Scratch viewers of this session (copy if useful): `lv.py` (atom beside its page sentence), `dq.py` (treated-text
lookups), `pg.py` (sentences of a cell's pages matching a regex), in
`%TEMP%/claude/g--UIU-classes-Claude-Code-RAG-TKG-pipeline/5ec2bcff-f3cf-4448-b15e-e6378d91b384/scratchpad/`.

**Paper, done ahead of the numbers (still behind `\nwdeconfalse`):** `_build/fill_decon.py` knows seven
systems; `tables/t2b-decon.tex` and `tables/e-decon-cells.tex` have B1 and X2 rows. Still to do once every cell
is labelled: observations, `fill_decon.py`, the seven-system rewrite of `sections/06b-decon.tex`, the
`\ifnwdecon` branch of Limitations, appendix I, the `tab:decon` caption, `\nwdecontrue`, build, PDFs, README.
**Findings to carry into that text (each has its ledger row of 2026-10-07):** full text discloses later facts
on the treated text at t=1 (8 of 88) where it disclosed none on the original; long context loses precision and,
much faster, citation sufficiency as volumes are added, with citations that keep chapter and paragraph number
and miss the volume; LightRAG citation sufficiency 0.794 with two readers and a 15-row calibration; one page
recovered (C44); "Gardner" and "Jamesina" reach pages. Not to claim: any cause for these, or for the prefix
retrieval citation gap.

## 0a. State at 2026-10-07 04:55 UTC (10:55 local) — read this before §0 and §1, which it supersedes where they differ

**Maintainer today:** "Raise to $390 and build" (the nine missing decontaminated cells); "you can parallelize
local gpu if needed"; start the paper. So the treated text is to be reported with all seven systems.

**Three jobs are running; all write to `data/fix_v2_decon.out`. They die with the agent session** (check
`ps -ef | grep "fix_v2_decon\|score_decon"` first; restart = remove the dead lock, start the same command).

| Job | Command | Lock | Does |
|---|---|---|---|
| paid runner | `sh docs/eval/runners/fix_v2_decon_rest.sh` | `data/fix_v2_decon.lock` | builds B1 t=2..5, X2 t=1..5 (cap 390 by `--set`, config stays 318 under freeze v2j), then scores what is left |
| scorer 1 | `SCORE_ONLY=1 sh docs/eval/runners/fix_v2_decon.sh` (since 10-06 17:20 UTC) | `data/fix_v2_decon_score.lock` | b4-v2 t=1..5, b3 t=1..5, b1, x2 in that order; skips a cell logged `m3 ... ok` |
| scorer 2 | `sh docs/eval/runners/score_decon_worker2.sh b1:1 b3:5 b3:4 b3:3` | `data/score_decon_worker2.lock` | those four cells, from the end of scorer 1's queue |

Progress: `grep -a "B1 t=\|X2 t=\|m3 \|worker 2\|FAILED\|budget" data/fix_v2_decon.out | tail -30`. Three FAILED
lines in a row for one reason: stop that job and report. Scorer 2 was given few cells on purpose: scorer 1
cannot see a cell in progress there. If both run slower than one alone (Ollama reloads the model when the
judge and the atomizer ask for different context sizes), let scorer 2 finish its list and do not restart it.

**Labels on the treated text** (precision + citation; recall and disclosure are done for v2, x1, b2, b3,
b4-v2, and for b1 t=1):

| System | Precision / citation | Who |
|---|---|---|
| main `@v2`, closed book `@x1`, prefix retrieval `@b2` | done, t=1..5 | committed |
| graph baseline `@b4-v2` t=1..5 | as the scorer lands them | the other Claude session (`claude-code-rag-tkg-pipeline-8c`); it writes only the `_all.jsonl` and `labels_claude/` files of those cells and messages the counts; this session writes the ledger rows |
| LightRAG `@b3`, long context `@b1`, full text `@x2` | not yet | this session |
| long context t=2..5, full text t=1..5 | also owe recall (`recall_patterns.py --view`, `decon_labels.py`, `strict_reread.py`) and disclosure (`m4_tree.py`) once built | this session |

Citation standard used since today (calibrated on the notes of the original `anne@b2` cells): a trait inferred
from one remark or act = partial; a relation not stated in the cited paragraphs = partial; an atom with one
wrong component = page partial and citation partial; a stale value printed as present = page partial, citation
sufficient; a wrong-referent fact = unsupported.

**Paper** (`docs/paper`, builds clean, 41 pages, content ends on page 8):
- Done: recall after C43 everywhere; `\nwhumantrue` (the review stated as a review of AI labels, no agreement
  figure); treatment keys `DECON-*`; `sections/06b-decon.tex`, `tables/t2b-decon.tex`, `tables/e-decon-cells.tex`,
  appendix I, the Limitations / abstract / conclusion clauses, all behind `\nwdeconfalse`.
- To finish, in order: (1) label the remaining cells; (2) regenerate observations and run
  `docs/paper/_build/fill_decon.py` (its docstring has the commands; add `b1:B1` and `x2:X2` to the loop and to
  `SYSTEMS`' five-cutoff handling once they have five cutoffs); (3) rewrite the sentences that say five systems
  were rebuilt "for cost" (06b-decon, Limitations, appendix I, caption of `tab:decon`) and add B1 and X2 rows
  to both tables; the X2 disclosure count on the treated text is the one result the section cannot yet state
  (does an instruction keep the cutoff when the model does not recognise the work?); (4) set `\nwdecontrue`,
  build, check `sec:limitations` starts page 9 with the conclusion ending on page 8 (it fit with the
  five-system text; every added line needs a line cut); (5) copy the PDFs (`docs/paper`, `dist/`), update
  `docs/paper/README.md`, ledger row for anything new, LOG, commit.
- Owed by the maintainer for the Ethics and Appendix A text: the reviewer's role, whether paid, time taken,
  whether they knew the books, consent to release the labels.

**Found today, recorded in the ledger:** 27 source names left in inflected forms in 26 treated paragraphs
(`labelling_tools/decon_residual_forms.py`); a paraphrase error a page repeats ("Six minutes after"); one
contradicted citation label in an original cell (`anne@b2` t=3 row 32), reported and not changed; the prefix
retrieval citation figure is 0.11 higher on the treated text and that is not yet explained.

## 0. Read this first

**Standing order (maintainer, 2026-10-07):** finish every model call and every local (Ollama, GPU) job first;
start on the paper only when all of it is done.

**Is the project done? No.** Done: version 2 of the main system and all six comparison systems on the original
Anne text, built, scored and labelled; the paper reports it (with recall figures that C43 has since moved, see
§4); the human check of 554 items; four of seven systems on the decontaminated text built and labelled for
recall and disclosure. Open, in order:

1. The decontaminated matrix: LightRAG t=5, long context t=1..5, full text t=1..5 (billed); then the local
   scoring of every built cell.
2. Labels for the decontaminated cells: recall and disclosure for LightRAG, long context, full text; the
   40-row precision sample **and citation sufficiency** for all seven (maintainer, 2026-10-07: "dont skip
   citation sufficiency. if the section has slot missing, we can add it later"; the paper's decontamination
   section has no M8 slot yet). Done so far: `anne-decon@v2` t=1.
3. The paper: refill M1 after C43, the decontamination section (`\nwdecontrue` in `docs/paper/main.tex`), the
   human-check paragraph and appendix, then the PDFs.

## 1. The runner (check before anything else)

**2026-10-06 23:24 UTC: the billed instance is STOPPED at the lifetime cap; nothing billed can run until the
maintainer raises it.** `config/models.yaml` `budget.lifetime_cap_usd` is 318 and the cap check read 318.19
(ledger 338.03 minus the 19.85 offset; `room.py --show`: spent_old 294.44, spent_new 43.59). Long context t=2
and t=3 each failed six times on `BudgetExceeded`, not on the API; the agent stopped the loop (lock renamed
`data/fix_v2_decon.lock.stopped-cap-20261006T2324`) and left the scoring instance running. Built: long context
t=1 only. `dist/anne-decon@b1/wiki/v02` holds 15 pages of 21, written before the cap was reached, and `v03`,
`v04` are empty: none of the three is a finished cell, none is logged `ok`, and none may be scored or labelled. Not built: long
context t=2..5, full text t=1..5. Cost left, from the runner's own estimates (about $0.06 per page and volume
read, no caching credit): long context about $27, full text about $39, **about $66**. The maintainer gave the
second project a $200 budget on 2026-10-04 (`room.py`: $99 of room for this runner), but the lifetime cap was
never raised to match. **Do not raise the cap without the maintainer's word.** After it is raised: start
`sh docs/eval/runners/fix_v2_decon.sh` again; steps logged `ok` are skipped, the FAILED cells are retried.

The paragraphs below describe the runner as it was started.

`docs/eval/runners/fix_v2_decon.sh`, log `data/fix_v2_decon.out`. Two instances were started 2026-10-06 17:20
UTC: the billed one (lock `data/fix_v2_decon.lock`) and a scoring-only one (`SCORE_ONLY=1`, lock
`data/fix_v2_decon_score.lock`). At 19:27 UTC on 2026-10-06 the log read `B3 t=4: ok`.

- Progress: `grep -a "t=[1-5]: \(ok\|FAILED\)\|m3 .* ok\|budget gate\|billed steps done\|decon v2 done" data/fix_v2_decon.out`.
- It is restartable: a step the log records as `ok` is skipped. After a dead run (power cut, closed session)
  remove the lock of the dead instance and start the same script. Runners have died with the session before:
  check `ps -ef | grep fix_v2_decon` first.
- A half-built LightRAG index for a cutoff must be removed before a restart
  (`data/anne-decon@b3/lightrag/v0<t>`): a kept one is read as "this volume is indexed".
- Budget: `python docs/eval/runners/room.py decon` printed 104 and `room.py old` 38 (dollars of room) at 19:21
  UTC. The script stops by itself at `budget gate`. Long context and full text are the expensive cells
  (the script asks for $12 of room for each).
- On a 429 it switches project and goes on; a cell is tried six times. Three FAILED lines in a row for the same
  reason: stop the runner and report, do not let it retry for hours.

## 2. What exists

| Thing | Where |
|---|---|
| Version-2 code, frozen | `python scripts/papers/freeze.py check v2j`; version 1 is tag `prefix-v1-20261004` |
| Original text, seven systems, t=1..5 | `dist/anne@{v2,b1,b2,b3,b4-v2,x1,x2}/wiki/v0<t>` |
| Decontaminated text | `dist/anne-decon@{v2,x1,b2,b4-v2}` t=1..5; `@b3` t=1..4; `@b1`, `@x2` not built |
| Recall labels | `docs/eval/recall_hand/<series>_v<t>.json`; rules `anne.provenance.md`, `anne@v2.provenance.md` |
| Disclosure labels | `docs/eval/leak_audit/<series>_tree.jsonl` |
| Precision and citation samples | `docs/eval/precision/<series>_v<t>_all.jsonl` (40 rows a cell; `human`, `human_atom`, `cite`) |
| Human check | `docs/eval/human_check/`: `HUMAN_REVIEW.md`, `final_labels.csv`, `CLAUDE_CHECK.md`, `CODEX_REVIEW.md` |
| First-person sample | `dist/leagues@v2`, `dist/leagues-decon` (state not re-checked for this handover) |

## 3. The human check, as it ended

Codex drafted the 554 answers; Claude checked 200 of them against the text and corrected the package (CHANGES
C42: parts C and P had shown six of up to 22 cited paragraphs, part R had cut sentences after "Mr."); a human
reviewed the checked sheet and accepted it. **The paper may say a human reviewed and accepted AI labels. It may
not report human-AI agreement:** the reviewer saw the AI answers. Agreement of the accepted labels with the
labels the paper used: R 204/235, P 120/148, C 46/60; gold facts yes 85, partly 23, no 3 of 111.

Not recorded and needed for the paper: the reviewer's role, whether paid, time taken, whether they knew the
books, consent to release. Ask the maintainer.

## 4. Decisions of 2026-10-07 (delegated by the maintainer) and what they changed

- **Recall counts full support only.** A weaker statement of the fact is `no` (strict nugget support, the
  primary score of the TREC 2024 RAG track). Six facts were re-read in every cell with one test each:
  `docs/eval/labelling_tools/strict_reread.py`, log `docs/eval/recall_hand/anne.strict_20261007.log`.
  **M1 moved for every system** (C43): main 0.787 -> 0.802, long context 0.868 -> 0.848, prefix retrieval 0.834,
  LightRAG 0.552 -> 0.536, graph baseline 0.767 -> 0.761, closed book 0.696 -> 0.683, full text 0.835 -> 0.814;
  decontaminated main 0.838 -> 0.843, prefix retrieval 0.779 -> 0.784, graph baseline 0.697 -> 0.704.
  **The paper still prints the old values.**
- **New decontaminated cells are labelled under the same six tests.** After writing recall labels for LightRAG,
  long context and full text, run `strict_reread.py` (it prints the cells it would change) and `--write`.
- A gold fact dated by a paragraph that announces the event is `partly` established; 12 of 111; no cutoff
  moves. To state in the paper.
- "alive (assumed)" is supported when the character acts within the cutoff and no death is told.

**Rejected:** relabelling only the sampled items (it would correct 10% of the labels under a rule the other 90%
did not get); replacing the precision and citation labels by the check's labels on the sampled rows (same
reason: the check sample is a reliability estimate for those parts, not a relabel); a lenient second recall
figure in the main text (the old values stay in the ledger and can go to an appendix as the lenient reading).

## 5. How to label a new decontaminated cell (as done for the four finished systems)

1. Before reading: `python docs/eval/labelling_tools/emptyctx.py --all` (a page written with no passage is the
   closed-book branch, OPEN_GAPS G10) and look at `calls.jsonl` of the run for failed calls.
2. Recall: `python docs/eval/recall_hand/recall_patterns.py --view anne-decon@<sys>` (names are mapped back to
   the original ones), read every candidate, enter the verdicts in `docs/eval/labelling_tools/decon_labels.py`
   and run it; then `strict_reread.py`.
3. Disclosure: `python scripts/eval/m4_tree.py anne-decon@<sys> --upto <t>`, read every candidate sentence.
4. Precision and citation: the runner's scoring step writes `docs/eval/precision/<series>_v<t>_all.jsonl`;
   view with `labelling_tools/pview.py` (precision) and `m8view_any.py <series> <t>` (the cited paragraphs in
   the cell's own text, timeline rows included); record with `label.py <file> <labels.json>` and `m8rec.py
   <series> <t> '<json>'`; the labels entered are kept in `docs/eval/precision/labels_claude/`. A timeline row's
   verdict goes into `timeline_cite_claude.json` under the series. Timeline lines: read their
   citations from the page (`timeline_sources.py`, OPEN_GAPS G16). Pair pages: the standing pair rule (C38).
5. One ledger row per cell group, one LOG entry, commit.

## 6. Traps met in this phase

- A reader package can hide what its question needs. Before a reader starts, join a first pass to the existing
  labels and read the disagreements for a common cause (C42).
- A script that rewrites label files only when the count of `yes` changes skips cells whose changes cancel
  (met in `strict_reread.py`; it now compares the labels).
- Shell heredocs here turn `\b` into a backspace character and drop backslashes: write regexes with the
  editor, never through a heredoc.
- Known and deliberately not fixed while the matrix runs on the frozen code: OPEN_GAPS G13 (Prissy Andrews
  merged into Priscilla Grant), G15 (`shirley` as its own character), G17 (line keys printed in prose), G18 (a
  neighbour's guess printed as a marriage; it reaches the graph baseline too).

## 7. Reproduce

```
.venv/Scripts/python.exe docs/eval/human_check/make_check.py              # the 554-item package
.venv/Scripts/python.exe docs/eval/labelling_tools/strict_reread.py       # prints nothing when labels are current
.venv/Scripts/python.exe docs/eval/recall_hand/recall_patterns.py --validate
sh docs/eval/runners/fix_v2_decon.sh                                      # the decontaminated matrix (billed)
sh docs/paper/_build/build.sh                                             # the paper
```
