# VISION.md — index of the requirement log

Full entries live in `docs/vision/PHASE_<n>.md` (one file per phase), split out
2026-09-04 because this file had grown to 1144 lines / ~82K chars — too expensive to
read in full just to find "the section for this phase" (`CLAUDE.md` §0/§4).

**This index is append-only and complete** — every entry ever written has one line here,
in the same order it was written, forever. **The per-phase files are also append-only** —
nothing in them is ever rewritten or deleted; a superseded decision gets a new dated entry
in the relevant phase file saying what changed and why. `LOG.md` records *what has been
built so far*; this records *what we are building and why*.

**Where a new entry goes:** append its one-line pointer here, then write the full entry at
the bottom of `docs/vision/PHASE_<n>.md` for whichever phase is currently open (the phase
being planned or implemented right now — not necessarily the phase the decision happens to
be *about*, if that differs, note both in the entry itself).

Entry format (in the phase file):

```
## YYYY-MM-DD — <short title>
**What:**    the requirement, stated concretely
**Why:**     the reason it exists
**Implies:** what has to be built or changed as a result
**Status:**  Planned | In progress | Done (Phase N) | Superseded by <date>
```

---

## Index

- 2026-09-01 — Initial vision: spoiler-scoped character wiki from a novel series — [PHASE_0](docs/vision/PHASE_0.md)
- 2026-09-01 — Temporal knowledge graph as the fact store — [PHASE_4](docs/vision/PHASE_4.md)
- 2026-09-01 — Interlinked pages; characters unique, everything else shared — [PHASE_2](docs/vision/PHASE_2.md)
- 2026-09-01 — Aho-Corasick as the retrieval and cost mechanism — [PHASE_2](docs/vision/PHASE_2.md)
- 2026-09-01 — Hybrid local + API model routing — [PHASE_0](docs/vision/PHASE_0.md)
- 2026-09-01 — Short, non-contradictory prose — [PHASE_6](docs/vision/PHASE_6.md)
- 2026-09-01 — Iterative delivery with per-phase auditable output — [PHASE_0](docs/vision/PHASE_0.md)
- 2026-09-01 — Series-agnostic by construction — [PHASE_1](docs/vision/PHASE_1.md)
- 2026-09-02 — Mistral API standing in for local Ollama; testing scope capped at 1-2 volumes — [PHASE_3](docs/vision/PHASE_3.md)
- 2026-09-02 — EcphoryRAG evaluated and rejected; token strategy stays extraction-time — [PHASE_2](docs/vision/PHASE_2.md)
- 2026-09-02 — Token-efficiency programme (Phase 3.5), quality held constant — [PHASE_3](docs/vision/PHASE_3.md)
- 2026-09-02 — Google key for polish + arbitration — [PHASE_4](docs/vision/PHASE_4.md)
- 2026-09-02 — Page fields are generic per predicate; PPR feeds `mentions_of`; `wiki explain` ships — [PHASE_5](docs/vision/PHASE_5.md)
- 2026-09-02 — Prose is generated from TRAIT claims only, never from structured fields — [PHASE_6](docs/vision/PHASE_6.md)
- 2026-09-02 — `wiki synthesize` caching compares cutoff N to cutoff N-1, not to its own last write — [PHASE_6](docs/vision/PHASE_6.md)
- 2026-09-02 — `config/models.yaml`: `prose`/`codex_summary` had no reachable fallback — [PHASE_6](docs/vision/PHASE_6.md)
- 2026-09-02 — Site bundle: sparse multi-cutoff shape, extended `links.json`, minimal static viewer instead of `web/` — [PHASE_7](docs/vision/PHASE_7.md)
- 2026-09-02 — `codex_summary`'s prompt needed a literal JSON example, not just a field description — [PHASE_7](docs/vision/PHASE_7.md)
- 2026-09-03 — The reference static viewer needs to look professionally made, not like a debug page — [PHASE_7](docs/vision/PHASE_7.md)
- 2026-09-03 — Both configured API fallbacks were simultaneously dead; Groq added as a working one — [PHASE_7](docs/vision/PHASE_7.md)
- 2026-09-03 — `--model` CLI override; a stale worktree was the active editable install — [PHASE_8](docs/vision/PHASE_8.md)
- 2026-09-03 — Per-series data segmentation; Spice and Wolf as a calibration corpus — [PHASE_9](docs/vision/PHASE_9.md)
- 2026-09-03 — Spice and Wolf calibration run finished; a real `synth/prose.py` prompt bug found and fixed — [PHASE_9](docs/vision/PHASE_9.md)
- 2026-09-03 — Six-phase redesign: auditable iteration + STORM/WikiMAG-style outline planning — [PHASE_10](docs/vision/PHASE_10.md)
- 2026-09-03 — Phase 10 built: run ledger, per-call prompt/response log, rollback, frontier interlock — [PHASE_10](docs/vision/PHASE_10.md)
- 2026-09-04 — OpenRouter free-tier routing for prose-quality stages — [PHASE_10](docs/vision/PHASE_10.md)
- 2026-09-04 — Fandom-grade depth: the ceiling is the ontology, not the model (Phases 17-21) — [PHASE_17](docs/vision/PHASE_17.md)
- 2026-09-04 — Per-series extraction schemas and CLI schema tuning; depth must never become series-specific — [PHASE_17](docs/vision/PHASE_17.md)
- 2026-09-04 — Per-series extraction schema overlay + CLI schema tuning built — [PHASE_17](docs/vision/PHASE_17.md)
- 2026-09-04 — Phase 11 built: chapter granularity, `wiki step`, and demoting `run-all` — [PHASE_11](docs/vision/PHASE_11.md)
- 2026-09-04 — Config-driven page outline (closed section vocabulary) built — [PHASE_13](docs/vision/PHASE_13.md)
- 2026-09-04 — Phase 17 built: value canonicalization (bge-m3 embeddings) + relation-conflict arbitration — [PHASE_17](docs/vision/PHASE_17.md)
- 2026-09-04 — Relation staleness when a mid-volume transition is never re-extracted (reinforces Phase 19 event layer) — [PHASE_17](docs/vision/PHASE_17.md)
- 2026-09-08 — Relationship pages: scope and design decisions (Phase 21, part 1 of 4) — [PHASE_21](docs/vision/PHASE_21.md)
- 2026-09-08 — Faction codex enrichment (key events): scope and design decisions (Phase 21, part 2 of 4) — [PHASE_21](docs/vision/PHASE_21.md)
- 2026-09-08 — Per-volume timeline pages: scope and design decisions (Phase 21, part 3 of 4) — [PHASE_21](docs/vision/PHASE_21.md)
- 2026-09-08 — Evaluation harness: scope and design decisions; Phase 21 complete (part 4 of 4) — [PHASE_21](docs/vision/PHASE_21.md)
- 2026-09-08 — Closed the chronology citation-entailment known gap: eval-only fix, not page-widening — [PHASE_21](docs/vision/PHASE_21.md)
- 2026-09-09 — Extended eval gold-data coverage to a 4th character (Jakob / Jacob Tarantino) — [PHASE_21](docs/vision/PHASE_21.md)
- 2026-09-09 — Output audit of the shipped Spice and Wolf v1-2 bundle: a crashed run, dead routing, and 15 defects — [PHASE_22](docs/vision/PHASE_22.md)
- 2026-09-09 — Phase 22 part 1: editable install pointed at a different checkout; bulk routing moved off dead Ollama — [PHASE_22](docs/vision/PHASE_22.md)
- 2026-09-10 — Phase 23: precision/grounding audit found systemic false relations (false SPOUSE_OF among other defects) and no truth-checking layer anywhere in the pipeline; scoped extraction gates, binding verification, a precision metric, recall fixes, and Fandom-shaped pages — [PHASE_23](docs/vision/PHASE_23.md)
- 2026-09-11 — The project becomes a research contribution: Leak@t, a contamination-controlled multi-corpus benchmark, and the hyperlinked output as an agentic-retrieval environment (Phases 24-30; see `Guide to Publishing.md`) — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-13 — Four-channel leak taxonomy replaces H1-H4 (H4 retracted: PPR was already cutoff-correct); `tests/test_spoiler_leak.py` written; L_build measured non-zero via candidate-mining thresholds, zero LLM calls — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-13 — `wiki gazetteer --gate=build`: cutoff-consistent entity discovery closes the measured L_build leak to zero on spice-and-wolf (0.042 -> 0.000 at t=1) — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-13 — Audit of the L_build headline: `leak_rate` 0.303 measures selection consistency, not disclosure; the reportable rate is 0.033 (86, t=1) and 0.000 (spice-and-wolf, t=1); no future entity leaks at any cutoff — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-14 — `--gate=build` reaches claim extraction (TASK-0001); naive diff number is a run-history confound, not a leak; real finding is cutoff-dependent entity individuation (Holo/Wisewolf not yet merged at t=1), a new taxonomy dimension — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-14 (pm) — Correction: the individuation finding is n=2/8 (Lawrence/Kraft Lawrence also splits), not n=1 — found via zero-cost gazetteer diffing — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-14 (late pm) — Correction: individuation finding's stated MECHANISM was wrong (epithet-mining artifact, not alias clustering); root-caused a corpus-composition-dependent candidate filter bug (Wisewolf vanishing at t=2); no gate comparison to date has been a clean A/B — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-14 (night) — Maintainer cancelled the 86 de-risking run: a Claude-authored plan is not authorization for wider scope, reaffirmed Spice-and-Wolf-volumes-1-2-only until pipeline/eval/benchmark complete; B4's "larger registry crowds every prompt" framing corrected (window-scoped, not registry-scoped) — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-15 — B2's remaining half checked: `measure_candidate_mining`'s 0.042→0.000 leak_rate was never epithet-confounded (only the entity-set diff was); now pinned by a regression test — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-15 (later still) — TASK-0004 filed and implemented (Option A, per-volume-OR capitalisation ratio): `Wisewolf` recall fix, render-mode probe diff measured — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-16 — Codex: TASK-0004 AC 3 closed — build-mode gate comparison clean (zero new mining-selection inconsistencies); surface-vocabulary export, alias-merge evidence fix, empty-automaton fix; verify.py cutoff-safe context, dedup'd flagged-interval counts, live verification run closes Phase 23 B4 — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-16 (later) — Output-quality Stage 0: yield.json tracking, relation-polarity fix; the meta-bug confirmed live (an already-fixed scene stage was never re-run — 3→124 v1 claims from a re-run alone, no code change); self-reported confidence found actively misleading arbitration — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-16 (last) — Outward-facing docs (capability reference, ConvinceMe, publishing guide) rebuilt on recomputed numbers; 51/51 arXiv ids verified + PDFs fetched (docs/REFERENCES.md, docs/fetch_reference_pdfs.py); the shipped-then-replaced module record becomes a maintained artifact (capability reference §4); risks R19-R22 filed — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-17 — Eight structural-flaws pass opened: config de-hardcoding, MkDocs wiki replacing the SPA, per-volume image galleries + character thumbnails, quote recall/attribution, sarcasm/veridicality at extraction+verify, prose scope, and a maintained papers doc — [PHASE_25](docs/vision/PHASE_25.md)
- 2026-09-17 (later) — MkDocs Markdown wiki (site/mkdocs_wiki.py) ships, replacing the ES5 SPA; verified end to end on real spice-and-wolf data with a working search, 0 broken links — [PHASE_25](docs/vision/PHASE_25.md)
- 2026-09-19 — Per-volume image gallery + captured EPUB art-plate illustrations ship (item 3); character thumbnails land at volume granularity only, chapter-level matching filed as real next work, not built speculatively (item 5, partial) — [PHASE_25](docs/vision/PHASE_25.md)
- 2026-09-19 (later) — Item 5 finished: `synth/assemble.py` threads each character's first-appearance chapter through the page bundle, making `cover_image_for_entity`'s per-chapter thumbnail tier reachable — [PHASE_25](docs/vision/PHASE_25.md)
- 2026-09-19 (later still) — Items 4/6/7 root-caused against real spice-and-wolf data: narration mis-quoted as dialogue, character insincerity (sarcasm/boasts/lies) never distinguished from sincere statements, and a char-count proxy silently letting prose exceed its configured sentence cap — [PHASE_25](docs/vision/PHASE_25.md)
- 2026-09-19 — R21 addressed: `docs/eval/nli_controls.py` confirms MiniCheck support scoring fixes the Zheren OCCUPATION arbitration bug live, on real corpus data — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-20 — Real-corpus re-run confirms items 4/6/7 live end to end; found + fixed a live arbitration schema-key mismatch (`decision` vs `resolution`) that had been silently failing `graph build` — [PHASE_25](docs/vision/PHASE_25.md)
- 2026-09-20 — `--nli` tried as the default arbitration path: runs cleanly now, but flags 54% of facts, almost entirely RELATION predicates (novels show relationships, don't state them) — a real calibration gap, not made default — [PHASE_24](docs/vision/PHASE_24.md)
- 2026-09-20 (later) — Phase 26 opened: audit of the shipped wiki against a real Fandom page — zero citations on 66 pages, 5 live antonym relation pairs, 27% unexplained relations, arbitrary quote selection; decision to synthesize per-paragraph source anchors from parsed data rather than from the EPUB (two new corpus traps recorded), and a correction that `--nli`-as-default is not the verifier fix — [PHASE_26](docs/vision/PHASE_26.md)
- 2026-09-20 (last) — Phase 26 part A complete: source view + 595 working citation links, contradictory relation pairs 5→0, false hyperlinks 21→0, relationships grouped and narrated, images restored; handover written, part B (extraction layer) not started — [PHASE_26](docs/vision/PHASE_26.md)
- 2026-09-20 — Phase 26 part B measured on a full v1-2 re-run: gates hold, prompt guidance does not ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — Phase 26 part C: KILLED/SAVED now require realis evidence (a deterministic `irrealis_markers` list matched on the cited quote, opt-in per predicate); both false claims were only being caught downstream by unrelated rules, and still reach `explain`/PPR; rejected a corpus-wide hedge filter and an LLM realis check ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — The shipped wiki was serving 12 pages from older builds that the current graph does not support (one asserted a killing that exists nowhere in `graph.db`); `audit links` cannot see them, so `build_wiki` now clears each cutoff dir before rewriting it ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — A gate in the extractor does not fix the graph you already have: `object_types` is now enforced at `build_graph` too, which dropped the live `holo KILLED pazzio` with no re-extraction and no LLM call ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — The daily cap is a CALL budget: a 2-volume run costs ~670 calls and `claim_extract` spends 359 of them on requests with a median 216-token answer; `pack_windows` cuts that to 101 measured offline, shipped OFF pending a smoke test against the routed model ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — Standing rule: quality is never traded for call count — `max_windows_per_request` stays at 1, and no call-saving change ships on cost grounds without an A/B showing equal yield ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — `audit eval` fact recall conflates three failures: extraction coverage (jakob — 14 corpus paragraphs of narrated warmth yield zero trait claims), the deliberate 2-4 sentence prose cap (norah-arendt — 68 claims, most cannot fit), and lexical synonym blindness (tailor/dressmaker); a single float cannot gate all three ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — Measured over all 206 v1-2 claims: MiniCheck relation scores are bimodal (median 0.097, p90 0.928) and a hand-verified correct `MENTOR_OF` sits at its predicate's median, so relations need a different verifier, not a calibrated threshold; attributes (median 0.778) are the usable half ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — Re-extracting Holo on the byte-identical prompt and model yields 235 claims where the stored file has 280: a 16% sampling swing that makes "fresh extract vs stored baseline" an invalid comparison, and which made this phase's own trait A/B read as a regression until a same-day control reversed it ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — CORRECTION to the entry above: the "16% sampling variance" was a bug, not sampling. `extract_volume` sized the window pool over the FILTERED character list, so `--entities "Holo"` gave her a 40-window budget where a full run gives 105-116, discarding 36 evidence windows — and `audit eval` recommends exactly that command as its low-recall remedy. Fixed; allocation-policy papers added but not adopted, since 0 of 359 windows are discarded once the pool is sized correctly ([PHASE_26.md](docs/vision/PHASE_26.md))
- 2026-09-21 — Phase 27 opened on the maintainer's instruction to make the project finishable: the scarce resource is the OpenRouter quota (1000/day), not "LLM calls", so evaluation may now use LOCAL models freely — fact recall gains a MiniCheck entailment pass unioned onto keyword overlap (3 characters +1 fact each, 0 OpenRouter requests), and recall now WARNS while precision still FAILS ([PHASE_27.md](docs/vision/PHASE_27.md))
- 2026-09-23 — Phase 28 opened on the maintainer's instruction to finish the project now that Vertex AI works: `vertex_flash` (`gemini-3.1-flash-lite`, chosen by measured fact-yield against three other Gemini tiers) becomes the routed default for every generative stage, with the OpenRouter free tier and local Ollama as an ordered fallback chain; guardrails relaxed in number, not in kind ($20 lifetime cap, `max_volumes: 2` still fails closed) — [PHASE_28](docs/vision/PHASE_28.md)
- 2026-09-23 (later) — Switching model exposed four defects that were never about the model: `resolve_role` silently fell back past every Vertex profile (ADC has no api_key), three adequacy gates the prompt never mentioned were deleting 611 valid facts (one of them contradicting the prompt outright), and `wiki verify` had been failing OPEN — `{"bad_facts": [...]}` validates against `flags: []`, so 49 flagged facts read as "nothing flagged" — [PHASE_28](docs/vision/PHASE_28.md)
- 2026-09-23 (last) — Optimisation pass: the pipeline was entirely serial (`concurrency:` was read by nothing), the frontier-call interlock was O(n²) over calls.jsonl, and a Gemini client was constructed per call; with those fixed a volume of scene extraction runs in 33s instead of 8.5 min. Mean gold fact recall 39.8% → 43.9%, precision still 1.0, all eleven audits OK, total spend $3.13 — [PHASE_28](docs/vision/PHASE_28.md)
- 2026-09-23 (after the last) — The phase's own A/Bs were sampling noise: a prompt change worth +41% facts in isolation measured 7 points WORSE end to end, and reverting it did not restore the old number because `--merge-epithets` had changed the scene prompts in between; extraction temperature pinned to 0.1, the whole sequence re-run from a fresh gazetteer, mean gold fact recall 45.9% — [PHASE_28](docs/vision/PHASE_28.md)
- 2026-09-23 (Phase 29) — Four standing rules from the maintainer (API only when nothing cheaper moves the project; A/B on the smallest slice; never re-ask a cached prompt; every number into one ledger) and a target that is not recall: structure and connectedness that rival a professional fandom page. The project is explicitly NOT on a publication pathway, so `docs/MEASUREMENTS.md` — not a paper — is where a figure has to be findable — [PHASE_29](docs/vision/PHASE_29.md)
- 2026-09-23 (Phase 29, shipped) — Four emitter defects, each one the wiki asserting what the data did not support: `members`/`adversaries` listing the same character twice, codex rosters naming characters in plain text while their pages linked back, a PPR `related` bucket printing the same four entities under every entry, and one art plate captioned as the portrait of three different characters. Fixed for $0 — emitter-only work, every `codex_summary` a cache hit — [PHASE_29](docs/vision/PHASE_29.md)
- 2026-09-23 (Phase 30) — The judgement metric changes: not an internal ratio but whether the information a professional fandom page conveys is present **and structured**. Page-length spread is retired as a headline figure — it moved the wrong way (21.4× → 21.7×) when eight unevidenced "alive" leads were removed. First finding: `traits:` had exactly one consumer, the prose prompt, so 43% of SKILL intervals never reached the page at all; Holo's page showed 3 of her 14 — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-24 (Phase 30) — Repository restructure: EPUBs to `corpus/<series-id>/`, scripts out of `docs/` into `scripts/`, one papers home (`docs/papers/`), plans into `docs/vision/plans/`, publication-era docs to `docs/archive/`; `STRUCTURE.md` rewritten with an old → new path table — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-24 (Phase 30, later) — Restructure follow-ups decided: `DEFAULT_SERIES` stays "86" on purpose (safer landing for un-scoped code), retrospective handovers for Phases 24/25, commit-by-default and quality-over-calls rules moved from Claude's private memory into `AGENTS.md` — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-25 (Phase 30) — Infobox fields (GENDER/AGE/ORIGIN) come from an additive long-context pass over each character's named paragraphs, not the windowed extractor; editing `claim_extract` would re-roll every claim — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-25 (Phase 30, later) — Backstory pass (`--pass backstory`); prose prompts read only unwithheld intervals, after 17 of 21 withheld facts were found still writing prose — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-25 (Phase 30, later x2) — Verifier sees aliases visible at the cutoff and accepts pronouns for GENDER; ids retired by entity overrides are remapped at load — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-25 (Phase 30, later x3) — A new series needs only id/title/folder: detected heading tags, standalone book = v1, default honorifics and quotes, per-series `prompt_vocabulary`; Gutenberg probe — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-25 (Phase 30, later x4) — Ascendance of a Bookworm v1–2 onboarded; content-filter fallback, NaN-safe embeds, part-ordered volumes, lifetime cap across series — [PHASE_30](docs/vision/PHASE_30.md)
- 2026-09-25 (Phase 31) — Publication reinstated on decontaminated (paraphrased + entity-remapped) Project Gutenberg novels; lifetime cap $20 → $200; candidate claim: the spoiler gate closes retrieval leakage but not parametric leakage — [PHASE_31](docs/vision/PHASE_31.md)
- 2026-09-27 (Phase 32) — Five volumes per series; recall at audited 100% precision; one general pipeline (no per-series overrides/overlays); no character images; history visible, no "changes later"; Middlemarch as the ~60-character stress wiki — [PHASE_32](docs/vision/PHASE_32.md)
- 2026-09-27 (Phase 33) — Research positioning adopted: joint coverage/support/boundary evaluation, narrowed novelty, baseline matrix, data tracker (plan 0012) — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-09-27 (Phase 33, later) — Every evaluation measured and reported per volume cutoff t — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-09-27 (Phase 33, later x2) — Published results only on public-domain works with a reference wiki: Anne main, Oz held out — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-09-28 (Phase 33, later x3) — Model choice 3.6 Flash vs 3.1 Flash-Lite decided end to end on Anne v1; one model for every final reading; ceiling $275 — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-09-28 (Phase 33, later x4) — Refusals stay on one model; ceiling $275 now ($400 possible later); cast = gold characters — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-09-28 (Phase 33, later x5) — Gemini 3.6 Flash everywhere; Anne only to completion, then write; Oz after a budget increase — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-09-30 (Phase 33) — Every number-moving change recorded with reason and before/after values in docs/eval/CHANGES.md — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-09-30 (Phase 33, evening) — Annotation rules R1–R6: placement-aware M3, frame errors out, pilot labels ≠ human, M4 over all F_t — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-10-01 (Phase 33) — Decontaminated arm deferred: full matrix (~$97) later, none now; Anne map review first — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-10-02 (Phase 33) — Overnight mandate: decisions delegated, decontaminated matrix now, $300 real ceiling, paper drafted from the agent pilot; one recall rule; no superiority claim — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-10-04 (Phase 33) — Statistics: no intervals; mean, median, SD and lowest/highest value over cutoffs — [PHASE_33](docs/vision/PHASE_33.md)
- 2026-10-04 (Phase 34) — System v2: fix batch for OPEN_GAPS G1, G2, G5–G12 before further spend; v1 kept for comparison, v2 built as @v2 variants — [PHASE_34](docs/vision/PHASE_34.md)
- 2026-10-07 (Phase 34) — Human review accepted the checked AI labels; recall counts full support only; finish all model and local jobs, then the paper — [PHASE_34](docs/vision/PHASE_34.md)
- 2026-10-08 (Phase 34) — Construction dependence gets a metric (identity dependence); entity discovery rebuilt per prefix t=1..4 as the comparison — [PHASE_34](docs/vision/PHASE_34.md)
- 2026-10-11 (Phase 34) — Paper version 2: NarrativeWiki framed as a probe of graph decomposition; renamed-text control leads Results; shares all numbers with version 1 — [PHASE_34](docs/vision/PHASE_34.md)
