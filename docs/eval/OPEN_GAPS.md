# OPEN_GAPS.md — major gaps found with no fix available now

Kept separate from `CHANGES.md` (fixes) on the maintainer's instruction (2026-09-30). An entry here
has no change that closes it within the current budget, freeze or scope; it needs money, a rebuild,
a design decision, or it is a result to report. Each says what it costs the paper and what would
close it. Append-only; a closed gap gets a dated "closed by" line, never deleted.

## G1 — B5 entity-resolution merges (system error; needs a rebuild to fix)

`di` (Diana Barry + Di Blythe), `walter` (Walter Shirley + Walter Blythe), `marshall` (Mr. Marshall +
Marshall Elliott), `mary` (Mary Keith + Mary Vance), `west` (Rosemary West given Leslie's
grandmother's kinship), `leslie-moore` (absorbed v3 "Will Leslie"); split identities `anne` +
`anne-shirley`, `matthew` + `matthew-cuthbert`. **Cost:** precision errors on merged pages; later-
volume facts on an early entity's page are leak candidates; "fandom quality" claim weakened.
**Scoring:** handled honestly by the gold-page map (merges counted, not filtered; CHANGES C6).
**Would close it:** an alias-clustering fix + rebuild from `gazetteer` (≈ the full S01 cost) — only
with a budget decision. **Paper:** report as B5 errors (appendix L), and as evidence for A3.

## G2 — Codex summaries have no evidence gate

The one-sentence codex summary is generated from evidence but never verified. Found: t=3 Patterson
Street — "the Reverend Jo Blake takes a position ... settles down with his wife, Phil" while v3 has
them only engaged, and "Reverend Jo" is a v4 surface form (inferred by the generator, not leaked
through the prompt: the prompt held only v3 passages). **Cost:** a small class of overstatement /
implication disclosures on a shared surface. **Would close it:** a local MiniCheck support check of
each summary against its cited paragraphs (≈ $0) with regeneration or suppression on failure — a
system change after the freeze, so it needs the maintainer's go-ahead and a rescore of M3/M5 on
codex surfaces. **Paper:** limitation + appendix H casebook entry either way.

## G3 — Leak screen confuses engagement/romance with marriage

B5 screen positives t=1..3 are all "X marries Y" gold facts against pages that state a courtship or
engagement (Anne–Gilbert, Diana–Fred Wright). **Cost:** screen precision; M4/M5 must be hand-
adjudicated. **Would close it:** only hand adjudication (in progress for B5). **Paper:** appendix F
(screen audit) already covers implication-level failures.

### 2026-09-30 decision on G1 (maintainer offered a full re-run; not taken)

Rebuilding B5 on Anne to fix G1 would tune the system on its own test work (the merges were found by
reading Anne's results) and taint every B5 number. Instead: report G1 as system errors, measured
honestly (CHANGES C6); fix the alias clustering / volume-gated mention index on the development work
(Middlemarch) and evaluate the fixed system on the untouched held-out work (Oz) when budget allows.
Every EVALUATION fix (C1, C5, C6, C7, C9) is re-run in full, because those are flaws of the harness,
not of the system under test. A1 already shows the build-channel effect G1 is part of: the
prefix-built t=1 wiki resolves Diana Barry and Anne Shirley cleanly; the full build does not.

### 2026-09-30 G1, complete list (`scripts/eval/entity_merge_audit.py`, deterministic, $0)

The earlier G1 list came from reading gold characters' pages; the maintainer noted merges "should've
been caught" — the gazetteer carried every signal. Audit of all CHARACTER entities: full v1–5 build
`anne` **42 flags** (span 19, surname 13, split 10); prefix t=1 build `anne-m36` **2 flags**, both
false alarms. Draft reading (agent, 2026-09-30; to confirm):
- **different people merged (≈12):** `walter` (Walter Shirley + Walter Blythe), `di` (Diana Barry +
  Di Blythe), `marshall` (Mr. Marshall + Marshall Elliott), `james-a` (James A. Harrison + James
  Matthew "Jem"), `martin` (hired man + Martin Crawford), `mary` (Mary Keith + Mary Vance); likely
  `faith`, `susan`, `billy-andrews` (+ "Billy Booth"), `davis`, `baxter`, `emily` — each a v1–3 first
  name joined to a v4–5 full name.
- **one person split (4):** `anne` + `anne-shirley`, `matthew` + `matthew-cuthbert`, `jane` +
  `jane-andrews`, `diana` + `diana-wright` (Diana's married name).
- **same person, benign:** married names (Phil Gordon/Blake, Cornelia Bryant/Mrs. Marshall Elliott),
  Anne's "Mrs. Doctor" forms, Bertie Shakespeare Drew, nicknames.
Every A1 prefix build gets the same audit after its gazetteer; the difference is an A1 result.

## G4 — 2026-09-30 — The leak screen is not the paper's M4 (screen only; needs adjudication design)

`pipeline_page_leak.py` summary: (a) `future_leak_rate` drops future facts whose character has no
page (`n_future_no_page`: 49/93 at t=1, 35/70, 31/50, 17/27, 0/5) — paper M4 is over all of |F_t|;
(b) it reads character pages only — paper W_t is every delivered surface (codex, shared menus,
other characters' pages); (c) it includes the 5 reveal-6 gold facts, so t=5 reads "0/5" where the
paper says M4 is undefined. The per-row output keeps `first_vol` and `page_empty`, so (a) and (c)
are recomputable at $0; the exporter (C12) already applies (c). **Cost:** every screen rate quoted so
far ("1/44 … 0/5") has the wrong denominator and scope; screens were never paper values. **Would
close it:** the M4 adjudication sheet covers each F_t fact against the whole v<t> tree (grep of the
fact's key terms over all pages, then a reader), not only the character's page; not changed now
because the runners score every re-rendered cell with this script (changing it mid-chain would mix
two definitions across cells).

## G5 — 2026-09-30 — Relationship pages list scenes one of the pair is not in (system error)

`relationships/<a>--<b>.md` "Shared scenes" carries whole-chapter scene summaries whose participant
list includes a character only mentioned in the chapter: `anne--moody-spurgeon-macpherson` (v01)
lists five scenes (summer outdoors, pass list, leaving for Queen's, Avery, Matthew's death), and
Moody is in none of their summaries. In the 68 shared-scene rows of the t=1..3 M3 samples, a reader
(agent, Claude Opus 5.5, from the scene summaries) finds **24 with one of the pair absent**, 5
ambiguous, 39 fine. The Codex labels judged each atom alone ("supported") and so did not count the
page's implicit claim "a and b share this scene". **Cost:** M3 read in page context falls from
39/35/36 to about 31/29/26 of 40 at t=1/2/3 (agent estimate; presence was read from the summary,
not the chapter text). **Would close it:** a participant = present-in-scene rule in scene extraction
(system change: rebuild), or scoring rule in the annotation guide: a shared-scene line is supported
only if both characters take part. **Paper:** needs the annotation rule decided before M3 is final.

## G6 — 2026-09-30 — Timeline sections labelled one chapter late (system error, deterministic)

`site/bundle.py:1111` emits `chapter_idx: idx + 1` (Phase 22 "fix 0-based timeline chapters"), and
`mkdocs_wiki.chapter_label` (Phase 30) expects the raw index, so every `timeline/vNN.md` section is
headed with the NEXT chapter's title (v01: Matthew's death, c37, under "XXXVIII. The Bend in the
Road"; last section "Chapter 40" in a 38-chapter book). Relationship and character pages label the
same scenes correctly. **Cost:** a wrong chapter on a shared surface (M8-type citation error), no
factual error. **Would close it:** drop the `+ 1` ($0 re-render), after the freeze and after every
job reading `dist/anne` stops; not done now (M3 runner reads that tree).
- **2026-09-30 correction to G5:** read against the chapter text (rule R1, generous: anywhere in
  the chapter), 11 of 68 shared-scene lines pair a non-participant, not 24; page-context M3 is
  37/40, 30/39, 32/39 at t=1/2/3 (MEASUREMENTS 2026-09-30 rows). The summary-based estimate
  over-counted. The count rows ("N shared scenes") are overstated in 4/4 sampled.
- **2026-09-30 G4 progress:** B5 M4 adjudicated over the whole v<t> tree at t=1..4 as an agent
  pilot (`leak_audit/anne_tree.jsonl`, MEASUREMENTS row): 0 confirmed, 4 uncertain. The screen
  script is unchanged; the exporter must read `anne_tree.jsonl` (bound by `tree_sha`) instead of
  the per-page file for M4 — add to C13.

## G7 — 2026-10-02 — Most of what B5 publishes has no paragraph citation (system gap; unfavourable M8)

Counts over the frozen inventories: 63% of B5's assertions are scene-summary atoms that link to a
chapter, about half of its prose atoms (relationship blurbs, codex summaries) have no source list,
and a prose section's source list is the first six paragraphs of its evidence, not the ones a
sentence rests on. Only structured lines and quotations (7% + 1%) carry a checked paragraph.
**Cost:** M8 end to end 22/197 = 0.112 against 130/199 = 0.653 for B1 (agent pilot, MEASUREMENTS
2026-10-02); equal among cited atoms (0.667 vs 0.663). **Would close it:** (a) keep the paragraph
ids a scene summary was written from and print them; (b) choose a prose section's sources by the
claims the prose was generated from, not by position; (c) cite relationship and codex prose.
All three are rendering/bundle changes plus stored provenance; none needs new extraction. Not done
on the frozen build. **Paper:** reported as measured (section 6.1 "Citations"); the verifiability
claim is restricted to structured lines.

## G8 — 2026-10-02 — B5's size is inflated by repeated scene summaries; later-anchored pages; meta-prose

- A scene summary is printed on the timeline and on every pair page it concerns: mean 20,823
  assertions per cutoff are 8,806 distinct (42%). The paper now reports distinct counts (5x B1,
  not 10x). The repetition is also the source of the placement errors of G5.
- Building from all volumes creates early pages whose entity is a later-volume character (7 at
  t=2, 9 at t=3: `walter`, `di`, `mary`, `jerry`, `marshall`...; MEASUREMENTS A1 rows). **Would
  close it:** resolve a surface form to an entity only among entities first seen at or before the
  form's volume, or split an entity whose early mentions are another person.
- Six frozen pages print the model's "X is not present in the provided text" as History.
  **Would close it:** treat that answer as no evidence (null prose).
None is repaired on the frozen build; each is a candidate change for the next build, with a
CHANGES entry.

## G9 — 2026-10-02 — hyphenated and titled names are split or dropped by entity discovery (seen on the held-out work)

- **Seen:** Oz gazetteer under freeze `oz-v2`: the Saw-Horse became the entity `Horse` (aliases "Sawhorse",
  "The Saw"), the Woggle-Bug became `Bug` (aliases "H", "The Woggle"); "Wizard of Oz", "Wicked Witch of the
  West", "Button-Bright" and "King Dox" have no entity under those names; one entity merges a princess, a
  prince and "Evring". MEASUREMENTS 2026-10-02 (Oz gazetteer row).
- **Likely cause (not verified in code):** candidate mining tokenises on the hyphen and treats "X of Y"
  titles as two names; alias clustering then joins the fragments by whole-word subset.
- **Why it is open:** Oz is the held-out work. Nothing in `src/` or `config/` changes while its matrix runs;
  the effect on recall and precision is a held-out result to report, not a bug to fix first.
- **For the next build (after the held-out numbers are recorded):** keep hyphenated tokens whole in
  candidate mining; treat "<Title> of <Place>" as one surface form; test on Oz fixtures and on Anne
  ("Rev. Jo", "Miss Lavendar") before any billed rerun.

## G10 — 2026-10-02 — a B4 page with no graph entity is written from the model's memory (harness fault)

- **Seen:** B4 at cutoff 5, Carl Meredith. The prompt held the series title and the instruction only
  (172 characters): no graph fact, no passage. The model wrote a full page and 55 paragraph ids, none of
  which it had been shown; the citation check removed all of them. MEASUREMENTS 2026-10-02 (observation row).
- **Cause (read in code):** `scripts/baselines/run_baseline.py::graph_context` returns two empty strings when
  the gold name is neither a canonical name nor an alias in the full gazetteer, and `common.prompt` then
  takes its title-only branch, the one written for X1. "Carl Meredith" is the only gold name of 43 without
  an exact entry (the entity is "Carl", no alias). B5 itself is scored through the page map
  (`docs/eval/parametric/pages/anne.yaml`), which B4's lookup does not use.
- **Cost:** one of 43 pages in one appendix cell. For that character B4 is the closed-book baseline: one
  recall fact conveyed from memory, one sampled atom unsupported. It also means a decontaminated B4 cell
  can hit the same branch for any remapped name that has no exact entry.
- **Why it is open:** `scripts/` is frozen while the held-out and decontaminated runners read it (freeze
  `oz-v2`); a change now would put a different file under cells still to run.
- **Would close it (after both runners stop):** resolve the gold name through the page map, and when no
  entity is found write no page and count the character in `no_page`, never the title-only prompt; add a
  check to the runner's cell audit that no B1/B2/B4/X2 prompt starts with "The novels:"; record a new
  freeze; rebuild B4 t=5 for that one character and re-draw its sample (about $0.01).

## G11 — 2026-10-03 — the assertion inventory keeps sentences whole when the local model is unreachable (harness fault)

- **Seen:** Oz B5, `assertion_inventory.py oz --upto 1`, 21:23-22:24 UTC: Ollama was not running (it had
  died with the session at ~02:10 UTC; connection refused on :11434), and **113 sentences** were logged
  "atomizer gave no valid answer; sentence kept whole" before the agent started `ollama serve` at 22:24.
  The script exited 0 for nothing; the runner would have logged "m3 oz t=1: ok". MEASUREMENTS 2026-10-03.
- **Cause (read in code):** `scripts/eval/assertion_inventory.py::atomize` catches every exception per
  sentence and keeps the sentence whole (line ~174); `eval_atomize` is local-only with no fallback
  (`config/models.yaml`), so an unreachable server turns the whole inventory into unsplit sentences.
- **Cost:** the t=1 Oz B5 inventory and its precision sample are not comparable with Anne's; rerun both
  after the runner's m3 loop (local, $0). Any earlier inventory with the same warning count would be suspect.
  Anne's inventories were checked at the time (the atomizer recall check, `F-atomizer-recall`).
- **Why it is open:** `scripts/` is frozen while the held-out runner reads it (freeze `oz-v2`).
- **Would close it (after the runners stop):** probe the eval role once at start and exit non-zero when it
  does not answer; fail the run when more than a few sentences fall back; record a new freeze. Runners
  should start `ollama serve` (or check `api/version`) before an m3 step, as they probe Vertex.

## G12 — 2026-10-04 — Oz volume 3's text ends with a publisher's catalogue of later books (corpus trap; future content inside a cutoff)

- **Seen:** reading a B2 t=3 leak flag ("Jim is a cab-horse"). `data/oz/01_parsed/v03.jsonl` chapter 26,
  "Books by L. Frank Baum" (17 paragraphs, 410 words), is the back-matter catalogue of the Gutenberg
  edition: blurbs of books 4 (Dorothy, Zeb and Jim the Cab Horse, the vegetable land, Eureka), 5 (the road
  to the Magic City), 6 (the Nome King threatens the Emerald City) and 7 (the Patchwork Girl, Ojo), then
  the transcriber's note. Ingest kept it as a story chapter. MEASUREMENTS 2026-10-04.
- **Reach:** B5's v03 claims cite c26 **13** times (Jim, Zeb, Eureka, Ozma); **27** B5 page files at
  t=3..5 cite `v03-c26` (character pages for Jim, Zeb, Eureka exist at t=3); B2 4 files; X1 none (reads
  no text). By the pipeline's own rule these are not leaks (the evidence is in volume 3's file); for a
  reader of book 3's story they are. Every text-reading system at t>=3 sees the same paragraphs, so the
  comparison between systems is unaffected; absolute M4 and the leak screen at Oz t=3, 4 are. The other
  Oz volumes have no such chapter (front-matter author's notes in v02/v03 hold no later plot); Anne v01-v05
  are story chapters only.
- **Why it is open:** the fix is in `src/narrativewiki/ingest/` (and `data/oz/01_parsed`), which the
  held-out runner is reading now (B2 t=4 building); changing it mid-matrix would put two texts under one
  column.
- **Would close it (after the runner stops):** drop back-matter chapters by title ("Books by", "Transcriber's
  note") in ingest, as `copyright.xhtml` is dropped for EPUBs; re-ingest Oz v03; rerun B5 from claims-v3
  (cache serves every window not touching c26; synthesis at t=3..5 re-bills the changed pages) and the
  t=3..5 cells of every text-reading baseline already built; record a new freeze. Until then, report Oz
  t=3, 4 with c26-derived statements counted as later-volume content, and say so in the appendix.

### G12 addendum — 2026-10-04 16:20 UTC: the catalogue's names pull memory into B3's pages

- **Seen:** Oz B3 (LightRAG) at t=3 writes a Jim page (127 words) with book-4 content no t=3 input holds:
  "once a fast racehorse in his youth", "taken to Hugson's Ranch, where he worked pulling a buggy".
  "Hugson" occurs 13 times in v04 and 0 times in v01-v03 and in `data/oz@b3/lightrag/v03`; the only Jim in
  t=3's text is the catalogue's "Jim, the Cab Horse" (v03:c26:p0006). The page cites nothing. Pages also
  exist at t=3 for Zeb, Eureka and the Mangaboo Sorcerer (16 words, empty). Same mechanism as G10: a name
  with no retrieved facts, a page written from memory.
- **Counted how:** not in M4 (the Hugson fact is not a gold fact); it is a later-volume statement on a t=3 page
  and is reported with G12. The G12 fix (drop the catalogue) removes the trigger for every system.

## 2026-10-04 — fix batch (CHANGES C31, Phase 34): status of G1-G12

Fixed in code and tested; the version-1 trees keep the defects and stay the reported v1 values.
Version 2 is built as `anne@v2` / `oz@v2`; each fix is confirmed on those builds before it is called closed.
- **G1 / G9 (entity resolution):** later-volume full names go to the model; bare first names are owned
  per volume or merged (`alias._assign_bare_forms`); pair cap 1000 -> 5000; hyphenated and "of" names
  mined whole; whole-word swaps never fuzzy-merge. Not addressed: one bare name for two people with no
  mined full name for either ("Mary" Keith/Vance when "Mary Vance" is not mined), and wrong names
  attached by the epithet step ("Billy Booth" on Billy Andrews).
- **G2:** codex summaries checked by local MiniCheck against their windows; one regeneration, else none.
- **G3 / G4:** evaluation design, unchanged (the M4 whole-tree read already replaced the screen).
- **G5:** participants are those who take part, not those mentioned (scene prompt).
- **G6:** timeline sections carry the raw chapter index.
- **G7:** keyed citations for every generated text; scene summaries name 1-4 paragraphs; blurbs and
  codex summaries print `_Sources:`.
- **G8:** "not present in the provided ..." answers are null prose. Later-anchored pages: G1's fix.
- **G10:** B4 page-map lookup; no passage-less prompt for a text-reading system.
- **G11:** atomizer probed before work; more than 1% sentences kept whole fails the run.
- **G12:** back matter dropped at ingest; Oz re-ingested (only v03 changed, 1,259 -> 1,242 paragraphs,
  the 17 of `v03:c26`); the old parsed text kept as `data/oz/01_parsed.v1-20261004`.

## G13 — 2026-10-05 — v2 merges Prissy Andrews into Priscilla Grant (entity residual, introduced by the larger pair budget)

`anne@v2`'s `priscilla-grant` carries `Prissy Andrews` (a different girl, Mr. Phillips's pupil in book 1).
The model judged the bare forms `Priscilla` and `Prissy` one person (`entity_alias`, run
`20261004T193719-gazetteer-v1-5`): right for Prissy Andrews, whom Mr. Phillips's verses call "Priscilla",
but the cluster around `Priscilla` already held `Priscilla Grant`, so the closure joined two people. v1 never
asked that pair (cap 1000; v2 5000). Effect: Priscilla Grant's v1-2 pages carry Prissy Andrews's facts (sixteen,
Latin with Mr. Phillips), and the gold fact "Mr. Phillips makes eyes at Prissy Andrews" is lost at every cutoff.
**No name-shape rule separates it**: "Prissy Andrews"/"Priscilla Grant" (two people) has the same shape as
"Phil Blake"/"Philippa Gordon" (one person, married name), so a cannot-link on full names that differ in
first and last token would break legitimate merges. v1 has the mirror error (`di` holds `Di Blythe` and
`Diana Barry`), which v2 fixes. Count of character entities holding two full names that differ in both
tokens: anne 5 -> anne@v2 4, oz 8 -> oz@v2 3 (each listed in MEASUREMENTS 2026-10-05). Not fixed: needs
evidence-level disambiguation of a shared bare name (per-volume ownership of nickname forms), the same
class as "Mary" Keith/Vance. Reported as a residual; no rerun.

Related, not new in v2: an affiliation interval keeps one qualifier per (subject, predicate, object), so
`diana-barry AFFILIATED_WITH improvers` shows "member of the Improvement Society" and the claim's
"treasurer" qualifier is not rendered (`graph/temporal.py` interval merge). v1 conveyed it through a
second claim on the split `diana` entity.

## G14 — 2026-10-05 — a first-person narrator is under-collected (seen on the first-person sample)

In `leagues@v2` the narrator, Aronnax, is named 120 times against Nemo's 613: his own narration is "I", and
the mention index (`entities/automaton.py`) counts names only, so his claim windows cover only the passages
where someone addresses or names him (30 claims vs 73-83 for the other leads). The scene pass resolves
participants by name too: 5 distinct scene summaries at t=2 say "the narrator", and those scenes are not on his
page. Recall on the sample is unaffected at t=1 (8/8) and the two narrator facts at t=2 that failed are not
narrator-specific, but the narrator's page is thinner than its role. **General fix, not built:** one call per
series deciding whether the narration is first person and naming the narrator, then counting first-person
pronouns outside quotation marks as that entity's mentions and passing the name to the scene prompt. No
per-series setting (one general pipeline); a third-person work must come out unchanged.

## G15 — 2026-10-05 — a bare surname or an ordinal stands as its own character (`shirley`, `fourth`, `west`; v1 and v2)

- **Seen (audit, MEASUREMENTS 2026-10-05):** `data/anne@v2/02_entities/gazetteer.json` has three single-token
  CHARACTER entities with their own pages: `shirley` (76 mentions), `fourth` (76), `west` (33). `shirley` takes
  Anne's "Miss Shirley" mentions and, in volume 5, her son Shirley Blythe, so the t=5 page is two people (female,
  schoolteacher, "the little brown boy"). `fourth` is the ordinal of Charlotta the Fourth. `west` is a stub for
  the bare surname of the West sisters. All three are in the v1 gazetteer with the same counts: not a v2 regression.
- **Cost:** one false page, two near-empty ones; Anne's page loses 76 of 4,083 mentions. None is a gold cast name,
  so they enter M1 only if facts moved off `charlotta` (1 gold fact at t=5) or off Rosemary/Ellen West (4): not
  checked. They count in N and can be drawn into the all-surface precision sample. Conditions differ: the
  decontaminated gazetteer has `harcourt` (same split) but no `fourth` or `west`.
- **Why it is open:** closing it rebuilds the anne@v2 gazetteer and pages, which makes every anne@v2 label stale
  (recall t=1..5, the disclosure read, nine precision samples, the inventories) and breaks freeze `v2j`.
- **Would close it (general, not built):** a single-token form that occurs only after a title or a given name of
  one existing entity ("Miss Shirley", "Charlotta the Fourth") is a form of that entity; when two entities claim
  it (Anne Shirley, Shirley Blythe) it stays ambiguous and resolves per mention by volume and context. No
  per-series list (one general pipeline).
- **G15 addendum, 2026-10-05 (double check of C37):** the scene pass resolves Anne to `shirley` in 21 of the
  226 anne@v2 scenes, and in 20 of them `anne-shirley` is not a participant (v1: 6 scenes, always beside
  `anne`). Those scenes are missing from Anne's character and pair pages and make up the five `shirley`
  pair pages at t=5. Six sampled precision rows were rejected for this alone (DOUBLE_CHECK.md finding 1-2).
- **G5 update, 2026-10-05 (CHANGES C39):** read row by row under one written rule by one AI reader, the share of
  sampled shared-scene lines whose pair never shares an episode of the scene is 40/116 in version 1 and 27/102 in
  version 2; by the stricter reading (the pair takes part in the statement's own episode) 69/116 and 62/102. Scene
  records are chapter digests (median 38 paragraphs) with 9.0 (v1) and 5.9 (v2) participants on average, and every
  pair of them gets the digest as a shared scene. **Would close it:** participants recorded per episode inside a
  scene, and a pair page listing only episodes that name both.

## G16 — 2026-10-06 — the assertion inventory drops the paragraph citations of timeline lines (harness fault)

- **Seen (MEASUREMENTS 2026-10-06):** every timeline row of the `anne@v2` inventory has `evidence: []` (0 of
  444 · 868 · 1,260 · 1,596 · 2,004 at t=1..5) although the delivered timeline pages print a `_Sources:` line
  under nearly all of them. `scripts/eval/assertion_inventory.py::units` fills `pending` units from the next
  `_Sources:` line, and the timeline branch (`**A, B** -- summary`) never appends its unit to `pending`.
- **Cost:** the 22 sampled timeline atoms were labelled `cite: none`, which put M8 at 0.457 and the cited share
  at 0.840; read from the page they are 0.512 and 0.930 (CHANGES C40). The human check showed "none cited" for
  its timeline items until the package was rebuilt.
- **Why it is open:** the tool is under `scripts/`, frozen while the decontaminated runner reads it, and a fixed
  inventory would change the stored `anne@v2_v<t>.jsonl` files that the precision samples were drawn from. The
  reported values are corrected beside the files (`timeline_cite_claude.json`, `timeline_sources.py`).
- **Would close it:** `pending.append(u)` for the timeline unit (one line), then the same reading for any build
  inventoried before the fix. **Owed for the decontaminated build:** its inventory will have the same gap; read
  its sampled timeline atoms from the page before quoting an M8.

## G17 — 2026-10-06 — the generator's line keys are printed in prose on a few pages (v2)

- **Seen (MEASUREMENTS 2026-10-06):** bracketed key groups such as "[R3, R4, S1, S4]" inside relationship prose
  on 5 of 341 pages at t=4 (156 groups) and 3 of 435 at t=5 (51); none at t=1..3. Gilbert Blythe's page at t=4
  is one of them and is the page shown in the paper's qualitative appendix.
- **Cost:** cosmetic for a reader, and a sign that the model sometimes writes the keys into the text instead of
  only into the `cited` field (C31 item 6). No label depends on it; none of the sampled atoms was rejected for it.
- **Why it is open:** stripping them re-renders `anne@v2` pages and makes the recall and disclosure labels
  stale by the tools' own check, for a cosmetic defect on eight page-cutoffs.
- **Would close it:** remove key groups from generated text after the keys are resolved (`synth/prose.py`), and a
  test that no page matches the pattern.

## G18 — 2026-10-06 — a character's guess about the future is rendered as a fact (`presumed` spouse printed as spouse; decontaminated build)

- **Seen (MEASUREMENTS 2026-10-06, M4 of `anne-decon@v2`):** at t=2 and t=3 the pages of the two leads print
  each other as "(spouse)" in the Family field, with "presumed Spouse of (since v2)", "Spouse of (since v2)" and
  the prose "the two eventually married". The marriage is a book-four fact. The evidence is book two: a
  neighbour's remark that she "is likely to wed" him (v02:c28:p0005), plus two paragraphs that say nothing of
  marriage (v02:c26:p0037, v02:c24:p0049).
- **Cost:** 4 stated disclosures of 220 for the decontaminated main system (the original build: 0 stated, from
  the same paragraph it stored a presumed ROMANTIC_WITH). This is the invariant of CLAUDE.md §1 failing in
  substance while holding in form: every cited paragraph is eligible.
- **Three causes, each general:** (1) extraction turns a prediction ("will probably marry") into a relation dated
  to the volume of the remark, with polarity `presumed`; (2) `synth/assemble.py` drops only `denied` relations, so a `presumed` SPOUSE_OF reaches the Family field,
  where the marker is lost exactly where the page is most authoritative; (3) two more SPOUSE_OF claims for the
  pair are `asserted` on quotes that do not mention marriage (`c_847a65b3`, `c_bb36cdcf`) and passed the quote
  gate and the verifier; the graph also has an asserted SPOUSE_OF between Mrs. Allan's stand-in and the heroine
  (`c_74410239`). The original graph has 2 presumed SPOUSE_OF claims of 114, this one 8 of 135.
- **Why it is open:** `src/` is frozen (v2j) while the decontaminated matrix runs, the graph baseline reads this
  graph, and re-rendering would make the labels just written stale. The build is reported as built.
- **Would close it:** Family (and every structured field) takes only `asserted` rows; a `presumed` kinship or
  spouse relation is shown, if at all, only under Relationships with its marker; the adequacy gate rejects a
  future-tense or conditional quote for a state predicate ("likely to", "will probably", "is going to" are not
  in `irrealis` today); a test with this paragraph. Then check every build for `presumed` rows that reach a
  structured field.

## G19 — 2026-10-08 — the candidate miner needs more text than a short prefix has (prefix entity discovery loses names)

- **Seen (MEASUREMENTS 2026-10-08, `docs/eval/identity_dependence_anne@v2.json`):** of the full build's
  candidates first seen by t, 109 (t=1), 111, 78 and 44 (t=4) are not mined from volumes 1..t alone. Bare
  "Gilbert" (113 occurrences in book one) is one: the capitalisation rule of `entities/candidates.py` asks that
  a single token stand alone in 0.75 of its occurrences in some volume, and 51 of the 113 are inside
  "Gilbert Blythe". "Jane" (96) is also lost; cause not traced.
- **Cost:** the prefix index holds 0.943 of the full build's character mentions at t=1 (0.994 at t=4), and
  9 character pages of the full build at t=1 have no prefix-built counterpart. It also means the full build's
  cast at an early cutoff is partly made by later text: identity dependence 0.390 at t=1.
- **Why it is open:** the miner is frozen and a change moves every cell; the deadline is 2026-10-12.
- **Would close it:** count a token inside a longer admitted name as a capitalised use, not as a use that
  fails to stand alone; evaluate `min_mentions` and the ratio on the prefix; then build extraction, graph and
  pages on prefix indexes (incrementally: only entities whose index entry changed) and score that build.
- **2026-10-08, later: decomposed, and left open by decision (maintainer: "apply recommended fix", the
  recommendation being to report the split).** Of the lost candidates, 18 / 24 / 18 / 12 (t=1..4) are dropped
  by the ratio rule ("Jane" is one) and 91 / 87 / 60 / 32 have fewer than three mentions in the prefix, which
  no rule removes. Switching the rule off admits 352 junk candidates on the five-volume build, and the
  targeted rule above would also change the five-volume index, so the reported build would have to be
  rebuilt and relabelled. The paper states the split (Appendix G, Limitations; CHANGES C49). The
  pages-on-prefix-indexes part is done for t=1..4 (`anne@p<t>-v2`, CHANGES C50): recall 180 of 224
  in both builds, no stated later fact in either.
