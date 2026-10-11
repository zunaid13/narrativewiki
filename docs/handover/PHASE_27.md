# Phase 27 Handover — The rules, changed so the project can finish

Status 2026-09-21, branch `phase-26-citable-pages`. `pytest -q` green (1011). All eight audits
OK, `eval` included — the first time it has passed in days.

**Read this before** touching `eval/gold.py`'s recall path, `audit/reports.py`'s eval gate, or
`docs/eval/gold/spice-and-wolf/baseline.json`. Each carries a rule that was deliberately changed
this phase, and reverting one by accident is easy.

---

## 1. Why this phase exists

The maintainer's instruction: the rules and guardrails may be modified, **the free OpenRouter
tier must still carry everything to completion before a paid "hard push"**, and the project has
to become finishable soon.

So this phase changed rules, not features. Three of them, each chosen because it was measurably
costing more than it gave.

## 2. The three rule changes

### 2.1 The scarce resource is the OpenRouter quota, not "LLM calls"

**Was:** `eval/gold.py` — "this project spends LLM calls only on bulk extraction, final prose,
arbitration; evaluation is not one of them."

**Now (CLAUDE.md §2):** the protected budget is the **OpenRouter free tier, 1000 requests/day**.
Local models (Ollama, MiniCheck-FT5) are unmetered and $0. Measurement, evaluation and diagnosis
may use local models freely; they may **not** spend OpenRouter quota, and `wiki audit eval` must
still complete with `OPENROUTER_API_KEY` unset.

The old rule saved ~60 requests/day against a budget whose heaviest measured day reached 308 of
1000, and in exchange the project could not see its own improvements — a confirmed extraction fix
for `jakob` landed with **zero** movement in the metric meant to detect it.

`audit/reports.py` hard-refuses a non-local profile via `profile.is_local`, and degrades to
lexical-only with a printed reason if the classifier is unavailable. **Verified with the key
unset**: the entailment pass still ran.

### 2.2 Recall WARNs, precision FAILs

Precision and negative-facts measure the page asserting something **untrue** — unbounded, always
a defect. They still hard-gate. `tests/test_audit_eval.py::test_eval_report_still_fails_on_a_
fact_precision_regression` exists solely to fail if that softens.

Fact recall measures how much of a full Fandom page got reproduced, and is **capped by the
deliberate 2–4 sentence prose limit** (CLAUDE.md §2): `norah-arendt` has 68 claims and room for
about six. Gating on a capped number kept the report red for days over a ceiling no correct work
could lift, and a permanently-red gate is one nobody reads.

### 2.3 The regression floor is re-recorded, not frozen

`PLAN_2026-09-14` B6 already said the floor was calibrated against a superseded pipeline, and it
had drifted further. Re-recorded from one real run, per entity, with reasons in the file's own
`_comment`. Precision floors rise to **1.0 across all ten**; four recall floors rise; two
(`jakob`, `liebert`) fall with a written per-entity reason and no longer gate anything.

**The rule, now written into `baseline.json`:** raise a floor whenever a run beats it and you have
read why; lower one only with a per-entity reason recorded in the file, and never to turn a red
report green.

## 3. The trap in the semantic recall pass — do not "simplify" this

MiniCheck is a **stricter** judge than keyword overlap, not a better one. Two measurements that
will look like over-engineering until you re-derive them the hard way:

1. **It is unioned in, never substituted.** Scoring by entailment *alone* measured WORSE than
   lexical on 3 of 5 gold characters: it refuses compound gold sentences that keyword overlap
   passes, because entailment demands the whole proposition.
2. **`page_chunks` has three shapes on purpose.** The score is a MAX over documents. One
   whole-page document truncates at MiniCheck's 512-token window and loses the tail; fine chunks
   break any fact needing two sections. `liebert`'s "tense and nervous during the gold-smuggling
   job" scores **0.797** whole-page and **0.059** sentence-chunked. Hence: structured fields,
   each prose section (name-prefixed, because sections are full of pronouns an entailment check
   cannot resolve), and a truncated whole-page chunk.

Gain: `kraft-lawrence` 44→56%, `marheit` 17→33%, `norah-arendt` 30→40%, every one a genuine
paraphrase. Cost: **0 OpenRouter requests.**

## 4. State of the deliverable

`dist/spice-and-wolf/wiki/` — 86 Markdown pages, v01 and v02, MkDocs-ready. Every stage
populated. All audits OK: ingest, gazetteer, scenes, claims, contradictions, verify, events,
outline, pages, eval, links, relationships.

All three leak channels run and produce numbers (zero LLM calls):

| channel | t=1 | t=2 |
|---|---|---|
| `index` (L_build, candidate mining) | leak 0.017 (3/181 surfaces) | 0.000 (0/213) |
| `leak` (L_query, future facts) | 0.126 (69/548) | 0.000 (0/0) |
| `disclosure` (first occurrence) | unseeable exact 0.470 / normalised 0.331 | 0.131 / 0.005 |

**`PLAN_2026-09-14` §3.3 is itself stale** — B5 ("`probe/futureset.py` is dead code, the
benchmark cannot be called benchmarked") is closed: `probe/channels/leak.py` consumes it and all
three channels are wired into `wiki probe run`. Re-measure that plan before working from it; it
was written seven phases ago.

## 5. What is NOT done

- **`docs/REFERENCES.md` is stale** — 51 entries against 54 PDFs on disk. Machine-generated,
  "do not hand-edit". Needs `python docs/fetch_reference_pdfs.py --check` to complete a full
  pass; arXiv was 406-flapping all day and 38 of 58 ids went unreachable. `docs/PAPERS.md` is
  the hand-maintained index and IS current.
- **Gold covers one series.** B6's "gold on a second series is annotation work, and it is on the
  critical path" still stands. That is annotation, not code.
- **The NLI hybrid** (attributes to MiniCheck, relations stay on chat) is specified in
  `PHASE_26.md` §5.1 and deliberately left to the maintainer, because it changes what readers see.
- **Documentation overhead was NOT reduced.** One finding costs edits to `LOG.md`, `VISION.md`,
  a phase file, and sometimes a handover. Making `VISION.md` generated was considered and
  rejected this phase: regenerating it from phase-file headings would destroy index lines that
  are richer than the headings they would be rebuilt from. Worth revisiting deliberately, not as
  a side effect.

## 6. Reproducing

```
pytest -q                                          # 1011
wiki audit eval  -s spice-and-wolf                 # OK; recall drops appear as WARN
OPENROUTER_API_KEY= wiki audit eval -s spice-and-wolf   # must still run the entailment pass
wiki probe run index ; wiki probe run leak ; wiki probe run disclosure
```
