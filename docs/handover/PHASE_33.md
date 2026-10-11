# docs/handover/PHASE_33.md — research evaluation: generator choice, baselines, gold (IN PROGRESS)

Written 2026-09-28 ~12:40 UTC at the end of a session, for the next one. Phase 32 (five volumes,
one general pipeline) closed without its own handover; its state is in LOG.md 2026-09-27 and
`docs/vision/PHASE_32.md`. Phase 33 decisions: `docs/vision/PHASE_33.md` (read the four 2026-09-28
entries). Paper work queue: `docs/vision/plans/0014-paper-values-tracker.md` (step table + log).
Every number below has a row in `docs/MEASUREMENTS.md` (2026-09-28 rows).

## 0-------------. 2026-10-02 ~12:30 UTC — Anne is fully labelled and in the paper; two runners still working; read this first

**Is the project done? No.** Done: every Anne cell is built, scored and labelled (agent pilot), and the
paper reports all of it. Open: the held-out matrix (Oz), the decontaminated matrix, human labels, the
anonymous upload, the budget.

**Runners (detached `nohup sh`; check with `tail data/oz_heldout.out data/anne_decon.out`).**
`oz_heldout.sh`: gazetteer, scenes v1-v5, epithets, claims v1-v3 done; v4 running when Vertex began to
answer 429 at 12:15 UTC. `anne_decon.sh`: paraphrase done and checked (8,467 of 8,489 paragraphs, 0
residual names); recognition probes started, same 429. Both wait by design (three attempts, fifteen
minutes apart, then a FAILED line; the probes are non-blocking). To restart a stopped runner remove
its lock (`data/oz_heldout.lock`, `data/anne_decon.lock`) and start the script again: finished calls are
cached. Ledger $265.24, room $67.61 to the 313 gate. The decontaminated run keeps the unspent part of
Oz's $45 estimate in reserve, which leaves it about $26: **it will stop at `budget gate` before its B5
build (needs $25 after the probes and the gazetteer) unless Oz finishes first and cheaper.** That is the
reserve working; restart it after `oz done`, or after the maintainer raises the budget.

**What was labelled this session** (rules and borderline calls: `docs/eval/recall_hand/anne.provenance.md`,
last section): B2 t=1 and B4 t=3, 4, 5: recall, 40 atoms, disclosure; citation sufficiency for B2 t=1.
The tools used are `docs/eval/labelling_tools/` (`m1view`, `q`, `m1rec`, `label`, `m4sent`, `m4rec`, `m8q`,
`m8rec`, `ch`); a per-row view of a precision sample is easy to rewrite (the session's was scratch).
Refresh after any relabel: the four commands of `docs/paper/README.md`, then restore the ledger comment
of keys whose value did not change, then the **hand-typed keys** that `fill_results.py` does not compute:
`M4-anne-total-*`, `SCREEN-anne-*`, `ND-anne-avg-*`, `M3K-anne-*`, `M5-anne-*`, and the B2 row of the
page-kind table in `appendix/g-additional-results.tex` (MEASUREMENTS "Derived counts restated" row has
the method). `results.tex` has CRLF line ends: keep them.

**Found and not fixed (OPEN_GAPS G10).** B4 at t=5 wrote Carl Meredith's page from the series title alone:
`graph_context` found no gazetteer entry named "Carl Meredith" and the empty context fell through to X1's
prompt. One page of 43; stated in Appendix G. Fix after both runners stop (it touches `scripts/`): resolve
through the page map, write no page when no entity is found, record a new freeze, rebuild that page.
**The decontaminated B4 cells will hit the same branch for any remapped name without an exact entry**:
before they are labelled, scan their prompts for one that starts with "The novels:".

**When Oz finishes** (unchanged): `docs/eval/parametric/pages/oz.yaml` if slugs differ, label as for Anne
(109 facts, 40 atoms per cell, disclosure 83/60/40/20), `paper_observations.py oz ... --work oz`, the
held-out block (`*-oz-*` keys are declared and empty). Known before labelling: six gold characters have
no entity under their gold name and `wizard` / `great-oz` / `wonderful-wizard` are one person in three
entities (G9; not fixed on purpose). **When decon finishes:** steps in `docs/paper/README.md`.

**Waiting on the maintainer** (unchanged): two human readers for `dist/narrativewiki-human-annotation.zip`;
upload of `dist/narrativewiki-anonymous-release.zip` (rebuilt 12:27 UTC, scan clean); the budget.

**Traps of this session.** (1) A backslash inside `python -c "..."` under Git Bash is eaten: write the
script to a scratch file. (2) Appending to `MEASUREMENTS.md`, `CHANGES.md` or `OPEN_GAPS.md` with a
quoted heredoc is safe as long as the text has no backslash. (3) The release scan prints
`IDENTIFYING STRINGS LEFT` **after** writing the archive: read its last line every time, a tool copied
from a scratch folder can carry the local path. (4) `paper_numbers.py` prints every row with its full
command; pipe it to a file and diff `paper_numbers.json` against a copy taken before.

## 0------------. 2026-10-02 ~11:00 UTC — END OF SESSION: two runners still working, labels owed; read this first

**What is running when you arrive (detached `nohup sh`, they survive the session; the hourly audit cron does
not).** Check them first: `ps -ef | grep runners`, `tail data/oz_heldout.out data/anne_decon.out`.

| Runner | Log | State at 10:55 UTC | Ends with |
|---|---|---|---|
| `docs/eval/runners/oz_heldout.sh` | `data/oz_heldout.out`, B5 step logs `data/oz/_driver/` | gazetteer, alias clustering (617 calls); then B5 build (`run_series.py oz --upto 5`), X1, B2, B3, B1, X2 at t=1..5 | `oz done` or `budget gate` |
| `docs/eval/runners/anne_decon.sh` | `data/anne_decon.out` | paraphrase: v01, v02 done (1 paragraph still verbatim), v03 running; then treated-text check, memorization probes, gazetteer, B5 build, baselines | `decon done` or `budget gate` |

Both check freeze `oz-v2`, both gate at 313 on the cap check (ledger - 19.85; $300 real with a $5 reserve);
the decon gate also keeps $45 minus what Oz has spent until `oz done`. Lock files `data/oz_heldout.lock`,
`data/anne_decon.lock` stop a second start: remove the lock only to restart a dead runner. Ledger at
10:55 UTC: $261.13 (cap check 241.28). The maintainer will raise the budget later; a `budget gate` line
means "stopped, waiting for that".

**The current paper's data is complete** (`anne_rest.sh` logged `night done` 10:32 UTC): every Anne cell
is built and scored. Four cells have samples but **no hand labels yet**: B2 t=1, B4 t=3, t=4, t=5. Until they
are labelled the paper reports B2 at cutoffs 2-5 and B4 at cutoffs 1-2 (appendix). For each: recall
(`docs/eval/recall_hand/anne@<sys>_v<t>.json`), the 40-atom sample (`docs/eval/precision/anne@<sys>_v<t>_all.jsonl`,
fields `human`, `human_atom`, `note`, `reader`), disclosure (`python scripts/eval/m4_tree.py anne@<sys> --upto <t>`
then verdicts into `docs/eval/leak_audit/anne@<sys>_tree.jsonl`), then the refresh commands in
`docs/paper/README.md`. The session's labelling helpers are kept in `docs/eval/labelling_tools/` (see its README);
`scripts/eval/recall_evidence.py` and the note fields of the existing label files show the conventions
(R1 placement, R2 frame error).
B4 t=5 dropped 59 of 2,516 citations (5 at t=3 and t=4): look at why when labelling it.

**Paper.** `sh docs/paper/_build/build.sh` writes `_build/main.pdf` (reading copy, no margin line numbers)
and `_build/submission.pdf` (with them; the file to submit). 8 content pages, 19 in all, clean. Copies:
`dist/NarrativeWiki-paper.pdf`, `dist/NarrativeWiki-paper-submission.pdf`, `dist/narrativewiki-paper-overleaf.zip`.
Two review rounds (plan `docs/vision/plans/0015-acl-review-revisions.md`, progress table at its end;
the second round's fixes are CHANGES C28, C29) are applied.

**When Oz finishes.** Write `docs/eval/parametric/pages/oz.yaml` if B5's page slugs differ from the gold
names (as for Anne), then label as for Anne (recall 109 facts, 40 atoms per cell, disclosure 83/60/40/20
later facts), run `paper_observations.py oz ... --work oz`, and add a held-out block to the paper (keys
`*-oz-*` are declared and empty in `results.tex`; Table 1 needs a second block; Limitations "A pilot on
one work" and the abstract change). **When decon finishes:** steps in `docs/paper/README.md`.

**Waiting on the maintainer.** Two human readers for `dist/narrativewiki-human-annotation.zip` (answers go
in `docs/eval/human/`, then `python docs/eval/human/score.py`); uploading
`dist/narrativewiki-anonymous-release.zip` (rebuild with `python docs/paper/_build/make_release.py`); the
budget increase.

**Not started.** Review plan step 6's suffix-invariance experiment; an independent read of pages where the
disclosure search found no candidate; M8 for B3 and X2.

**Traps of this session.** (1) A Bash heredoc halves doubled backslashes and Python turns `"\r"`, `"\t"`,
`"\b"` into control characters: a regex word boundary and several table-row ends were lost that way. Write
.tex and regex text with the Write tool or `_build/sub.py`, never with `\\` in a heredoc. (2)
`fill_results.py` rewrites the ledger comment of every key it fills. (3) Any change under `scripts/`, `src/`,
`config/` breaks a runner's freeze check at its start: re-record and rename in both runners first. (4) The
first seeded-disclosure fixtures were invalid (74 of 88 implying sentences did not carry their fact):
validate fixtures before reporting a rate from them. (5) The maintainer does not want a job left waiting
behind another: start independent API work at once and separate priorities with budget reserves.

## 0-----------. 2026-10-02 ~08:25 UTC — review plan 0015 in progress; read this first

**Order of work set by the maintainer:** (1) the current paper must be finishable, so its cells get the
API first; (2) then the decontaminated matrix until the $300 stop; (3) the revision plan
(`docs/vision/plans/0015-acl-review-revisions.md`, progress table and decisions at its end).

**Runners.** `anne_rest.sh` (B4 t=5, B2 t=1 left) then starts `anne_decon.sh` itself. That runner has a
lock (`data/anne_decon.lock`), a gate at 313 (a $5 reserve under the 318 cap check) and checks freeze
`anne-v2e`. **Any change under `scripts/`, `src/` or `config/` before it starts needs a new freeze and
the name in the runner**; tools that only read labels can live in `docs/` (as `docs/eval/human/` does).

**What changed in the evidence.** M4's candidate search retrieves 84% of seeded paraphrases and 27% of
oblique disclosures, so the paper now says "no confirmed disclosure of an assessed later fact" and adds
a search-independent check from the precision samples. The matched population (cast character pages)
shows no precision gap; the gap is misplaced scene lines on relationship pages. LightRAG costs $7.59,
not $3.11. M8 intervals are bootstraps.

**Waiting on people.** Two independent readers for `docs/eval/human/` (about 5 hours each); an anonymous
artifact URL; a decision on a held-out work (needs budget beyond $300).

**Traps.** `fill_results.py` rewrites the ledger comment of every key it fills (restore unchanged ones).
In a Bash heredoc a doubled backslash becomes one: a table row end typed in a `sub.py` block loses a
backslash, and a regex with a word boundary loses it; write such text with the Write tool.

## 0----------. 2026-10-02 ~06:30 UTC — the paper is in ACL format and complete without the decontaminated block; read this first

**What exists.** `docs/paper/` compiles to a submission-shaped PDF in the official ACL two-column
format (`sh docs/paper/_build/build.sh` -> `_build/main.pdf`; copy in `dist/NarrativeWiki-paper.pdf`,
Overleaf zip beside it): 8 content pages, then Limitations, Ethical Considerations, references,
appendices; no placeholder prints. `docs/paper/README.md` is the operating manual (build, switches,
the five steps for adding the decontaminated values, the backslash trap when editing .tex from a shell).

**Decisions taken.** (1) B4 is out of the main table (two cutoffs only) and reported in Appendix G.
(2) The headline is phrased as "only material from volumes <= t reaches the generator", never "input
cut at t", because B5's graph is built from all five volumes. (3) Labels are attributed in Section 5:
Claude Opus 5.5 for everything except B5 precision at t=1..3 (Codex); not blind; two audits; no
agreement statistic. This stays in the paper. (4) No M-code beyond M1/M3/M4/M8/M12/M13 is mentioned,
and unmeasured outcomes (M5, M6, ablations A2-A7, Oz) are not announced as pending inside the paper.
(5) `note` fields are banned in `refs.bib` (they print).

**Rejected.** Hiding the incomplete cells (B2 t=1 is footnoted; B4's scope is stated); `\resizebox`
on tables (widths were fixed by column spacing instead); an image-model figure in place of TikZ (a
prompt for one was given to the maintainer as an option, see the session reply).

**Traps.** In a Bash heredoc a doubled backslash reaches Python as one, and `"\r"` in a non-raw
string is a carriage return: both corrupted .tex this session. Use `_build/sub.py`. A `\res` value
containing `&` cannot be used in a table cell (split it into one key per cell).

**Freeze.** `scripts/papers/fig_cutoff.py` changed (plot style only), so the record is now
`anne-v2c`; `docs/eval/runners/anne_decon.sh` checks that name.

**Next.** Unchanged data work (API still 429 at 05:39 UTC): B4 t=3..5, B2 t=1, decontaminated matrix
(needs the maintainer's call: +$20 or drop X2-decon), A1 precision labels once `anne_a1_m3b.sh`
finishes sampling, M8 for B3/X2, blinded human labels.

## 0---------. 2026-10-02 (21:10 UTC 10-01) — recall audited, paper drafted, decontaminated matrix started; read this first

**Mandate (maintainer, asleep):** take the decisions; finish the data; run the decontaminated matrix;
stop and ask at **$300 real total** (ledger cap check 318 = ledger - 19.85); write the paper with space for
the decontaminated results. Decisions taken: `docs/vision/PHASE_33.md`, entry 2026-10-02.

**State of the Anne (original) matrix** — every label is an agent pilot, files under `docs/eval/`:

| | M1 `recall_hand/` | M3 `precision/*_all.jsonl` | M4 `leak_audit/*_tree.jsonl` |
|---|---|---|---|
| B5 `anne` | t=1..5 | t=1..5 | t=1..4 |
| X1 | t=1..5 | t=1..5 | t=1..4 |
| X2 | t=1..5 | t=1; **t=2..5 sampled by `anne_m3_gap_now.sh`, to label** | t=1..4 |
| B1 | t=1..5 | t=1..4; **t=5 sampled by the gap runner, to label** | t=1..4 |
| B2 | t=2..5 | t=2..5 | t=2..4; **t=1 not built** (night runner, last step) |
| B3 | t=1..5 | t=1..5 | t=1..4 |
| B4 | t=1..2 | t=1..2 | t=1..2; **t=3..5 not built** (night runner; 429) |

**How a cell gets labelled** (session helpers are gone with the session; the repo tools are enough):
M3 — read each of the 40 rows of `<cell>_v<t>_all.jsonl` against the source (`data/anne/01_parsed`) and
write `human`, `human_atom`, `note`, `reader`. M4 — `scripts/eval/m4_tree.py <series> --upto t`, read
every candidate sentence, write `<series>_tree.jsonl` rows (verdict, witness, tree_sha). M1 — for each
gold fact `scripts/eval/recall_evidence.py "<claim>" "<regex>" --diff`, read, then `--set yes|no`.
**Never carry a recall label across cutoffs without re-reading** (C19).

**Then:** `paper_observations.py` for the seven series, `paper_numbers.py ... --pair`, a MEASUREMENTS row,
`scripts/papers/fill_results.py --note "..."` (commands in `docs/paper/README.md`).

**Runners alive** (`ps -ef | grep anne_`): **`anne_rest.sh`** (replaces `anne_night.sh`; log
`data/anne_night.out`): B4 t=3..5, B2 t=1, then it calls `anne_decon.sh` (log `data/anne_decon.out`).
Every billed step waits on `scripts/eval/vertex_probe.py` (one tiny call per 10 min) — **Vertex answers
429 on Standard and Flex since 20:17 UTC**, so the runner is idle, not failing. `anne_rest.sh` checked freeze
`anne-v1x` at its start; `anne_decon.sh` checks **`anne-v2b`** (C22 `ingest/decontaminate.py`, `a1_page_diff.py`,
C23 `m4_tree.py`, C24 `assertion_inventory.py`): if `src/`, `config/` or `scripts/` changes, record a new freeze and change the name in both
runners before relaunching. `anne_m3_gap_now.sh` (`data/anne_m3_gap.out`) samples X2 t=2..5 locally.

**Decontaminated condition (C21, read before touching it):** the first name map was wrong in ways the
residual check could not see — stand-ins that are names in the books, and full names mapped with their
parts left. Map v2 has 239 entries and passes `scripts/eval/decon_map_audit.py anne-decon` (the runner
gates on it). The paraphrased v01 of 2026-10-01 is superseded; the runner redoes v1-5 with `--force`.
After B5-decon builds it needs a gold-to-page map `docs/eval/parametric/pages/anne-decon.yaml` (like
`anne.yaml` in that folder) before scoring, and every label pass above again with the stand-in names
(gold claims remap with the same map: `narrativewiki.ingest.decontaminate.remap`).

**C22 (22:00 UTC):** a paraphrase that keeps half or more of its input's word 4-grams is asked for once
more and, if still a copy, recorded `decon: "verbatim"`; `decon_report.json` has the count and the runner
prints it to `data/anne_decon.out` ("treated text: ...") and stops on a residual name or >1% remap-only.
Read that line and a sample of each volume before trusting the B5-decon build that follows it.

**A1 construction scope (done at $0 for t=2, t=3):** `docs/eval/a1/` (page classes), `leak_audit/anne@p{2,3}_tree.jsonl`,
`recall_hand/anne@p{2,3}_v{2,3}.json`, `cost/anne@p{2,3}_final.json`; ledger rows 2026-10-02 "A1 ...".
Owed: A1 M3 (inventory + `assertion_precision.py anne@p2 --upto 2 --n 40 --population all`, same for p3
t=3, then labels), a second reader for the page classes. A1 t=4 was never built (budget gate, 10-01).

**C23 (read before trusting an "absent" M4 verdict):** absent means the candidate search returned no
sentence. Run `scripts/eval/artifact_exposure.py <series>` beside it: it lists every name on a page that
the text up to t never uses, and it is what found the X2 t=4 miss. For baselines subtract hits in
`_baseline.json` (the run manifest, not a page).

**Paper:** `docs/paper/` — sections written from the pilot; red placeholders are the decontaminated block
(Table 2 lower half, section 6.4, appendix I), Oz, M6/M8, ablations, human annotation.
`scripts/papers/paper_status.py` lists them.

**Read before quoting any number (04:10 UTC):** the pilot now says B5 = B1 on recall, **lower** on
page-level precision (0.822 vs 0.93-0.97 for B1/B2/B3 after the C25 audit), **far lower** on citation
sufficiency (0.112 vs 0.653 B1, 0.748 B2), 5x (not 10x) the distinct assertions, and 0 disclosures like
every prefix-cut system. Two label audits (C19 recall, C25 precision) both found the agent's first pass
biased against the baselines. To label M8: `scratch m8view/m8q` are gone with the session; the rule is in
`docs/paper/appendix/a-annotation.tex` and the fields are `cite`, `cite_note` in `precision/*_all.jsonl`
(read ALL cited paragraphs from `data/anne/01_parsed`; the sample stores only six).

**What the pilot says (do not overclaim):** B5 = B1 on recall, lower page-level precision (G5), 0 disclosures
like every input-cut system; X1 and X2 leak. B2 (prefix RAG) is the cheap strong baseline.

## 0--------. 2026-10-01 ~02:50 UTC+1 — Standard transport, freeze `anne-v1o`, two runners in parallel

Running: `anne_resume.sh` (A1 t=2 → t=3 → t=4; freeze checked at its start only, stages pick up the
Standard config per subprocess) and `anne_after.sh` (X1, X2 t=1, B1 t=1..4, B2/B3/B4 t=1..5, each
scored + M3; started 20:45 UTC). `anne_m3.sh` stopped on purpose. Transport/cap change: CHANGES C14;
cost comparisons by tokens at one rate. Next unchanged: human ★ labels (R4; sheet now from
`scripts/eval/make_blind_sheet.py`), then baselines labelled under R1–R3 when anne_after logs
"after-chain fixes done". M3 B5 t=5 pilot 29/40 (MEASUREMENTS 2026-10-01).

## 0-------. 2026-09-30 ~16:00 UTC — pilot values done for B5 t=1..4; what remains

Done (agent pilot, ledger rows): M1 t=1..5, M3 t=1..4, M4 t=1..4 whole tree. Remaining, in order:
(1) when `docs/eval/precision/anne_v5_all.jsonl` appears (anne_m3.sh): label it as t=4 was
(`human`, `human_atom`, `note`, R1–R3), then `python docs/eval/annotation/make_blind_sheet.py anne 1 2 3 4 5`
(regenerates the blind sheet; do this before any human starts labelling). (2) human ★ labels (R4).
(3) after anne_after "after-chain fixes done": C13 + new freeze, then baselines under R1–R3.

## 0------. 2026-09-30 ~14:25 UTC — rules for a defensible paper; what is left, in order

Rules R1–R6: `docs/vision/PHASE_33.md` 2026-09-30 (evening). M3 pilot (agent, not human) B5 t=1..3 =
37/40, 30/39, 32/39 (MEASUREMENTS). Runners: see §0-----; anne_after checks `anne-v1n` (bdd3259).
**Next, in order:** (1) human labels on `docs/eval/annotation/anne_m3_blind.md` ★ items first (do
not open the `_key.json`); agreement vs `human` in `precision/anne_v<t>_all.jsonl`. (2) When
anne_m3.sh writes `anne_v4_all`/`anne_v5_all`: label them under R1–R3 (agent pilot) and regenerate
the blind sheet with `4 5`. (3) After anne_after logs "after-chain fixes done": C13 in one
scripts/ commit + new freeze (exporter: `lsa.sha(pages)` unconditionally; export `uncertain` and
`frame_error`; move `make_blind_sheet.py` to scripts/eval), then label every baseline cell under
R1–R3 (R5). (4) M4: adjudicate each F_t fact against the whole v<t> tree (R6/G4), t=1..4.
(5) S12 statistics with Wilson/bootstrap intervals; paper text only after the maintainer's review.

## 0-----. 2026-09-30 ~13:20 UTC — freeze is now `anne-v1n` (C12); anne_after.sh must be restarted

External review checked point by point (LOG 2026-09-30 afternoon; MEASUREMENTS rows; CHANGES C12;
OPEN_GAPS G4). The exporter fix moved the scripts tree, so the running `anne_after.sh` (still
checking `anne-v1m`) will log "FREEZE CHECK FAILED - stopping" when the chain ends. Fix: stop the
waiting anne_after.sh, change `anne-v1m` → `anne-v1n` in `anne_after.sh` and `anne_resume.sh`, and
start `sh docs/eval/runners/anne_after.sh` again (it only waits for the chain; nothing is lost).
Before any paper number: re-read the Anne t=1 leak audit on current pages; hand-label `_all`
samples (M3); M4 adjudication over the whole v<t> tree, not only the character's page (G4).

## 0----. 2026-09-30 ~12:00 UTC — HANDOVER: all API work queued and self-running; read this first

**Running (all resumable — rerun the same script; the LLM cache makes finished work ~$0):**
1. `docs/eval/runners/anne_resume.sh` (log `data/anne_resume.out`) — X2 t=3..5 now (t=4, t=5 will each
   hit the $10 per-run hard stop once and finish on the retry), then A1 t=2..4 (budget-gated).
2. `docs/eval/runners/anne_after.sh` (log `data/anne_after.out`) — waits for (1), then: X1 t=1..5,
   X2 t=1, B1 t=1..4, B2/B3/B4 t=1..5 re-rendered under the fair prompts, each scored + M3 ($≈25).
3. `docs/eval/runners/anne_m3.sh` (log `data/anne_m3.out`) — M3 all-assertion inventories + samples,
   local $0, ~35 h; B5 t=1, t=2 done. X1 cells it reaches before (2) re-renders them are redone by (2).

**What changed today and why — `docs/eval/CHANGES.md` C1–C11** (every entry has before/after values):
baseline cast rule (C1), dead links (C2), M3 population (C5), gold→page map for B5 (C6), X1 title
(C7), no page before an entity's name is known (C8), **no title for systems with passages, as B5**
(C9), lifetime cap counts every billed call (C10), **X2 told the reader's cutoff** (C11). Freeze now
`anne-v1m`. Gaps with no fix: `docs/eval/OPEN_GAPS.md` G1 (entity merges — full build 42 flags vs
prefix t=1 build 2; not fixed on Anne on purpose: test-set tuning), G2 (codex summaries unverified),
G3 (screen reads engagement as marriage).

**Numbers so far (screens, not hand-read; all in MEASUREMENTS):** B5 control screen t=1..5 0.652 /
0.630 / 0.621 / 0.551 / 0.568, future positives 1/44, 2/35, 2/19, 0/10, 0/5 (all marriage claims).
X2 (instructed, full text) t=2: 3/26 positives incl. v3 events — instruct-don't-filter leaks.
A1 t=1: prefix and full build equal on the screen (15/23), differ in entity resolution.

**Next for a human (nothing else blocks the paper):** hand-read B5 t=1..5 — precision samples
`docs/eval/precision/anne_v<t>.jsonl` and `anne_v<t>_all.jsonl` (M3), recall via
`python scripts/eval/recall_review.py anne <t>` (now uses the gold→page map), the B5/X2 screen
positives; confirm the G1 merge classification. Baseline cells: only after (2) finishes.
**Spend:** $122.75 billed so far (+ $2.19 billed offset) (calls ledger; the lifetime cap now counts it), projected ≈ $225 of $255.

## 0---. 2026-09-29 ~12:55 UTC — cast leak fixed (freeze `anne-v1f`); resume chain restarted

- §0--'s suspicion was right; fixed in `scripts/baselines/common.py::present` (ledger row). Every
  baseline cell rendered before `anne-v1f` is superseded, including the untracked
  `docs/eval/precision/anne@{b2,b3,x1}_v*` and `docs/eval/pipeline_leak_anne@*` files — the chain
  re-scores each cell as it re-renders it. Middlemarch tuning cells used the old rule (dev only).
- `anne_resume.sh` running since 12:55 UTC (log `data/anne_resume.out`); rerun it after any stop.

- 2026-09-30 00:xx: S01 done (20:34); B3, X1 done t=1..5; B2 t=1..4. **The chain's precision
  samples are cited-only** (X1 pool 0 everywhere) — M3 needs `assertion_inventory.py` +
  `assertion_precision.py --population all` per cell ($0, local; ledger row). Run them while B1/X2
  wait on Vertex, not alongside the chain's own scoring (GPU contention).

## 0--. 2026-09-29 ~00:50 UTC — PC shut down by the maintainer; suspected baseline cast leak

- Vertex still 429 (`gemini-3.6-flash`, generic "try again later", not a quota) at 00:45 UTC; the
  `anne_resume.sh` chain was killed by the shutdown before S01 resumed. **Resume: rerun
  `sh docs/eval/runners/anne_resume.sh`** (log `data/anne_resume.out`; cache makes done steps ~$0).
- **Suspected, not yet verified:** baselines take `gold_cast()` (`run_baseline.py:47`) = all 43
  gold characters regardless of cutoff. `dist/anne@b2/wiki/v01/character/` has pages for Walter
  Blythe, Rilla Blythe, Faith/John Meredith, Susan Baker, Marshall Elliott, Little Jem, Aunt
  Jamesina, Mary Vance — none on B5's t=1 cast. Titles disclose future names, and v1 facts get
  filed under them ("Mr. Marshall" the candidate minister → Marshall Elliott; Jerry Buote →
  Little Jem). Check the filter near `run_baseline.py:113` first; likely fix = cast at t = gold
  characters present by t (new freeze; re-render baseline cells, mostly cache). Do not hand-read
  baseline precision samples (`docs/eval/precision/anne@b2_v1..3`, `anne@b3_v1`) until settled.

## 0-. NIGHT 2026-09-29 ~20:30 UTC — supersedes §0a's runners (session -24)

- **Vertex 429 on every call (Flex too) from ~19:19 UTC** (ledger row). S01 had finished `graph`
  (--allow-partial, 19:51) and died in `verify`; B3 t=2 was losing chapters.
- **B3 fix, freeze `anne-v1e`**: LightRAG's 480 s worker timeout left 5 v2 chapters FAILED, and
  1.5.7 never retries FAILED. `b3_lightrag.py` now uses a 3600 s timeout, re-inserts FAILED chapters,
  and refuses an incomplete index. B3 t=1 index was complete; the t=2 cell is redone.
- **All old runners stopped** (s01d, baselines, a1). One sequential chain replaces them:
  `docs/eval/runners/anne_resume.sh`, log **`data/anne_resume.out`**. Each step is gated by a
  one-call probe every 30 min (gives up after 10 h). Order: S01 from verify → B3 t=2..5 → X1/B2
  t=1..5 re-render → B4 → B1 → X2 → A1 t=2..4 (budget guard). Resume: rerun the script (cache).

## 0a. OVERNIGHT 2026-09-28 ~16:10 UTC — every API step queued (maintainer asleep)

Freeze `anne-v1` (tag `freeze-anne-v1`, commit ab2a2de): 3.6 Flash only. Runners copied to
`docs/eval/runners/` (orchestration only; every command inside is a frozen script):
1. `anne_s01.sh` / `anne_s01b.sh` — S01 Anne v1–5 build (3.6 Standard); log `data/anne/_driver/s01_3.6.out`
   (success line: "all steps done"). Stopped once at scenes-v3 on an unescaped quote → fixed (7bf051f).
2. `anne_baselines.sh` — X1, B2 (150/20k), B3 (mix, 20k), B1 and X2 (Flex, concurrency 2) at t=1..5,
   then B4 after S01; each cell scored locally (leak screen + 40-line precision sample, $0). Log
   `data/anne_baselines.out`; pages in `dist/anne@<system>/wiki/vNN/`.
3. `anne_a1.sh` — A1 prefix-built Anne at t=2,3,4 on Flex (`anne@p2..p4`), after the baselines, each
   skipped unless $255 − spent > estimate + $15. t=1 prefix build = `anne-m36`; t=5 = S01. Log `data/anne_a1.out`.
Also done this evening: B2/B3 tuned on Middlemarch (ledger), M12 production verifier on the
challenge sets (bacc 0.989; hard 0.750). **When back: only hand reading and writing remain** —
B5 at t=1..5 (recall_review, precision samples, leak positives), the same for every baseline cell,
A1 differences (T4), then S12 statistics and S20 writing. If a runner line says FAILED, resume
that cell with the same command (cache makes it cheap).

## 0. UPDATE 2026-09-28 ~14:20 UTC — supersedes §1 and §7 steps 1–3

- **Generator decided by the maintainer: `gemini-3.6-flash` on every stage, no Flash-Lite**
  (PHASE_33 "evening" entry). The Flash-Lite trial arm `anne-m31` was stopped at `graph build`
  (no end-to-end Flash-Lite numbers; the paper says so). `anne-m36` is the only finished trial arm:
  hand-read recall 18/23, 0 disclosures, precision 32/40, cost $2.71 (MEASUREMENTS).
- **Standard capacity**: 3.6 answered 30/30 on Standard at 2.3 s (probe 14:09 UTC), so
  `vertex_flash` = 3.6 **Standard** at $0.75/$3.75 (Flex is the fallback: add
  `shared_request_type: flex` back and set the price to 0.375/1.875 — same cache keys).
- **Scope: Anne only** (v1–5) to completion — build, B5 measurement at t=1..5, baselines on Anne —
  then write the paper. Oz waits for a budget increase the maintainer will ask for.
- **Running: S01** — `sh $TEMP/anne_s01.sh` equivalent: `gazetteer --series anne --volumes 1-5 --force`
  then `scripts/run_series.py anne --upto 5`; progress in `data/anne/_driver/s01_3.6.out` and
  `data/anne/_driver/<step>.log`. Resume after a crash with
  `.venv/Scripts/python.exe scripts/run_series.py anne --upto 5 --from <failed step>` (cache makes
  it cheap). If `graph` stops on the incomplete-claims guard, read the named characters' extract
  calls first; `--allow-partial` only if they returned empty answers (see the Geraldine row).
- **Budget**: ~$44 spent; Anne build ≈ $30–40 (Standard); baselines on Anne estimated X1 $1 ·
  B2 $3 · B1 $57 · X2 $84 at Standard ceilings — run B1/X2 on Flex and measure implicit caching on
  t=1 first; X2 is droppable. Ceiling $275 (cap 255).
- **Next after S01**: `freeze.py record anne-v1 --tag`; hand-read B5 at t=1..5 (precision samples
  the driver writes to `docs/eval/precision/anne_v<t>.jsonl`, recall via `recall_review.py anne <t>`,
  every leak positive); tune B2/B3 settings on Middlemarch (dev) cheaply; run baseline cells; then
  S12 numbers → S20 writing.

## 1. Where things stand — read this first

**The one open decision the next session must close is the generator:** Gemini 3.6 Flash
(`gemini-3.6-flash`) vs 3.1 Flash-Lite (`gemini-3.1-flash-lite`). Maintainer rule: "if 3.6 is
better then use it", and every final (paper) number must come from ONE model. Evidence so far:
stored-prompt bake-off, hand-read — 3.6: 20/26 facts supported, 0 wrong; 3.1: 24/50 supported,
6 wrong; 3.6 costs ≈ 2.8× per prompt. The end-to-end trial on Anne volume 1 is running:

| Job (started 2026-09-28) | State at ~12:40 UTC | Resume if the process died |
|---|---|---|
| `anne-m36` — Anne v1, every stage on 3.6 Flash | inside `graph build --allow-partial` (its verification pass, run `20260928T121341-verify-upto1`), then the driver continues from `verify` | see §7 step 1 |
| `anne-m31` — Anne v1, every stage on 3.1 Flash-Lite | driver at `extract-v1` (run `20260928T122756-extract-v1-1`) | `.venv/Scripts/python.exe scripts/run_series.py anne-m31 --upto 1 --from extract-v1` |
| `anne` gazetteer rebuild v1–5 (3.1) | alias clustering, ~540 calls, since 09:35 | `.venv/Scripts/python.exe -m narrativewiki.cli gazetteer --series anne --volumes 1-5 --force` (cache makes it cheap). Redo on the winner if 3.6 wins. |
| `overlord` (dev only, copyrighted) | stopped after `infobox` on purpose | not needed for the paper; `--from backstory` if wanted |

Check a job: `tail data/<s>/_driver/trial.out` and the newest `data/<s>/_runs/<id>/calls.jsonl`.

**Budget:** real-bill ceiling **$275** now (maintainer; $400 "later down the line but not right
now" — only on their word). `config/models.yaml`: `lifetime_cap_usd: 255`, `billed_offset_usd:
2.19`. Recorded lifetime **$42.14** at 12:20 UTC (+ ≈ $0.40 bake-off outside a ledger). Flex is
priced at its real 50% rate since 2026-09-28. Re-read the console before any large run.

## 2. Things you must know before touching anything

- **Vertex 429s:** the billing account is the **$300 Google Cloud Free Trial** (no usage tier
  likely; `gen-lang-client-0365142802` has no organization). Fix in place: **Flex PayGo**
  (`shared_request_type: flex` on every `vertex_flash*` profile) with `X-Server-Timeout: 1800`
  (`llm/providers/google.py`). `shared_request_type` is kept OUT of the cache key
  (`llm/cache.py::_TRANSPORT_OPTIONS`) — adding it to the key would re-bill every cached call.
  Since the change: 0 errors on Overlord extract v4–v5 and both trial arms. Upgrading to a paid
  account (keeps the credit) is the maintainer's call, still open.
- **Gemini only through Vertex.** AI Studio (`generativelanguage`, `GOOGLE_API_KEY`) is retired:
  profiles removed, the adapter refuses a non-Vertex google profile.
- **Same model, always.** A content-filter refusal is NOT answered by another model any more
  (`client.content_block_fallback: false`; `complete_json` returns the schema's empty answer).
  Jobs started before that commit (`d6af45c`) still had the old fallback: after the trial, check
  `model` in each arm's `calls.jsonl` (one such qwen answer exists in Overlord v4).
- **Swapping the generator for one run:** `--set models.profiles.vertex_flash.model=gemini-3.6-flash
  --set models.profiles.vertex_flash.price_per_mtok.input=0.375 --set
  models.profiles.vertex_flash.price_per_mtok.output=1.875` (that is how `anne-m36` runs). To adopt
  a winner permanently, edit `vertex_flash` in `config/models.yaml` (model + price) — do not route
  stages to `vertex_flash36`, or the cache keys and the audit's model column split.
- **Variant series ids** (`paths.variant_base`): `<work>@<system>` (e.g. `anne@b1`) reads the
  base's config, parsed text and gold and writes its own data/dist/runs — every eval tool scores a
  baseline's pages unchanged. The trial arms instead use real series files
  (`config/series.anne-m31.yaml`, `anne-m36.yaml`, `gold_from: anne`).
- **Gold is agent-drafted where labelled** (`reader: agent-2026-09-28` rows in `anne.yaml`; all of
  `oz.yaml`): accepted by the maintainer ("Fine"), still labelled as pilot data (plan 0014 D1).
  Oz keys must be reconciled with the Oz gazetteer after its frozen build; Anne keys with the
  v1–5 rebuild.

## 3. Findings this session (MEASUREMENTS 2026-09-28)

- Google docs: flash-lite has **no per-project quota** (nothing to raise); usage tiers are
  org-level; Flex queues only as long as `X-Server-Timeout` allows (max 30 min).
- Bake-off (S&W, 12 claim prompts): facts 50 / 19 / 26 (3.1-Lite / 3.8 / 3.6); hand-read support
  24/50 vs 20/26, unsupported 6 vs 0. 3.8 is slower than 3.6 with fewer facts — not a candidate.
- Anne v1 gazetteer by generator: 83 entities (50 characters) on 3.1, 92 (54) on 3.6; alias calls
  325 vs 337 (an earlier "316 vs 26" was a mid-run artefact — compare finished runs only).
- 3.6 arm hit the incomplete-claims guard on "Geraldine" (a name from Anne's story club): 2 calls,
  both `{"facts": []}` — a correct empty answer, built with `--allow-partial` after checking.
- Hard challenge set (12 items): MiniCheck bacc 0.500, local qwen judge 0.667; **neither rejects a
  claim lifted from a story a character tells** (0/2) — the same class as gazetteer "characters"
  Geraldine and Golden Lady. In the paper as an observation (appendix L).
- Spend today $3.88 recorded; the 3.6 arm cost $2.34 for Anne v1 before synthesis — above the
  ≈ $2 per-arm estimate. **Re-estimate the 3.6 plan from `run_cost.py anne-m36` before rebuilding.**

## 4. What exists now (all tested; full suite passes)

| Plan 0014 step | Deliverable |
|---|---|
| S16 cost | `scripts/eval/run_cost.py <s> [--sha] [--since]` — cold $, warm-rebuild tokens, per-volume |
| S12 aggregates | `scripts/eval/paper_numbers.py` (per-cutoff, mean over t within a work, character-clustered paired bootstrap, zero bound 1−0.05^(1/k) over characters) + `paper_observations.py` (hand verdicts only → observations) |
| S15 retention | `scripts/eval/retention_trace.py <s> --upto t` (entity/read/claimed/graph/verified/page/hand) |
| S13 exposure | `artifact_exposure.py` adds a slug/link surface; variants use the base vocabulary |
| S10 baselines | `scripts/baselines/run_baseline.py <work> X1|B1|B2|B4|X2 --upto t [--estimate]`; `b3_lightrag.py` (LightRAG 1.5.7 in isolated `.venv-b3`, `--estimate`, `--dry`); shared contract in `common.py`; stages `baseline_page`, `baseline_embed`, `baseline_lightrag` |
| S02 freeze | `scripts/papers/freeze.py record|check <name> [--tag]` |
| S04 gold | `oz.yaml` 109 facts (26/23/20/20/20), `anne.yaml` 34 → 116 (21/24/21/23/22) |
| S08 | `challenge_hard_v1.jsonl` + `challenge_set.py score --file` |
| S18 | F1 TikZ (`docs/paper/figures/f1-overview.tex`; not compiled here — no TeX) |
| Paper | appendix D adaptations, setup-stats text, appendix L observations (21/758 keys filled, all OBS/ledger-backed) |
| Trial | `scripts/probe/model_bakeoff.py`, `scripts/eval/compare_builds.py <a> <b> --upto t` |

## 5. Traps hit this session

- **Bash heredoc halves backslashes** in inline Python: a `.replace()` silently missed and the
  challenge scorer overwrote `challenge_v1.jsonl` (restored from git; test added). For LaTeX or
  any backslash, use `chr(92)` or the Write tool, and assert the replacement happened.
- `docs/paper/main.tex` has CRLF endings: `sed` line edits miss; edit bytes in Python.
- `data/anne/02_entities/gazetteer.json` is still the 2026-09-26 v1–6 build until the rebuild
  finishes (it titles v1's Jerry Buote "Jerry Meredith") — do not read it as the rebuild.
- The permission classifier sometimes errors on every shell call: Read/Grep still work.
- `graph build` includes verification (long); `trial.out` lines appear only when a step ends.

## 6. Decisions taken and rejected

Taken: Flex PayGo; Vertex only; cap 255 / ceiling $275; refusals → empty answer on the same model;
cast = every gold character (Anne 43, Oz 35); Overlord stopped (dev only); B3 = LightRAG as
retriever with the shared generator; X2 may be dropped if money is short (diagnostic only).
Rejected: Priority PayGo and Provisioned Throughput (premium/subscription), AI Studio key (credit
does not pay for it), weaker or mixed models, 3.8 Flash, routing 429s to another model.

## 7. Next steps, in order

1. **Finish the trial.** If `anne-m36` died: `S="--set models.profiles.vertex_flash.model=gemini-3.6-flash --set models.profiles.vertex_flash.price_per_mtok.input=0.375 --set models.profiles.vertex_flash.price_per_mtok.output=1.875"`;
   `.venv/Scripts/python.exe -m narrativewiki.cli graph build --series anne-m36 --allow-partial $S` (only if graph.db/verification.json are not complete), then
   `.venv/Scripts/python.exe scripts/run_series.py anne-m36 --upto 1 --from verify $S`. `anne-m31` as in §1; if its graph hits the same guard, check the named characters' calls first.
2. **Decide the generator:** `python scripts/eval/compare_builds.py anne-m31 anne-m36 --upto 1`;
   hand-read `docs/eval/precision/anne-m3{1,6}_v1.jsonl` (fill `human`), hand recall with
   `scripts/eval/recall_review.py anne-m3{1,6} 1`; audit `model` in both arms' calls. 3.6 wins if
   not worse on precision and recall (PHASE_33). Record rows + fill appendix L `OBS-trial`.
3. **Adopt the winner** in `vertex_flash` (model + Flex price), re-estimate the plan with
   `run_cost.py`, stay under $275.
4. **S01** Anne v1–5 on the winner: `gazetteer --series anne --volumes 1-5 --force`, then
   `scripts/run_series.py anne --upto 5` (it runs audits, leak curve, precision samples).
5. **S02** `python scripts/papers/freeze.py record v1 --tag`; ledger row it prints.
6. **S03** Oz: history check (plan 0012 D16), `freeze.py check v1`, then gazetteer + `run_series.py oz --upto 5`; reconcile `oz.yaml` keys.
7. **S10 tuning on Middlemarch** (chunk size, evidence budget) with `--estimate` first, then S11
   baseline cells on Anne/Oz; S09/S12/S15 numbers; paper results wait for maintainer review.

## 8. Waiting for the maintainer

- Upgrade the Free Trial billing account to paid? (keeps the credit; likely gives a usage tier).
- Review drafted paper text (appendix L, D, setup-stats) before submission; results stay unfilled
  until their review (memory: manual review before paper).
