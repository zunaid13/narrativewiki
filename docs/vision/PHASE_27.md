# Phase 27 — Making the project finishable: rules that cost more than they give

Phase 26 closed the shipped wiki's defects. This phase is about the rules themselves. The
maintainer's instruction on 2026-09-21: the rules and guardrails may be modified, **the free
OpenRouter tier must still carry everything to completion before a paid "hard push"**, and the
project has to become finishable soon.

Everything here is chosen against `docs/PLAN_2026-09-14_pre_full_scale_audit.md` §3.3's blocker
list, not against taste.

---

## 2026-09-21 — Rule change 1: the scarce resource is the OpenRouter quota, not "LLM calls"

**Retired rule:** `eval/gold.py`'s docstring, "this project spends LLM calls only on the stages
CLAUDE.md §2 names (bulk extraction, final prose, arbitration); evaluation is not one of them."

**Why it was wrong.** It conflated two budgets that are nothing alike:

| budget | size | what spends it |
|---|---|---|
| OpenRouter free tier | **1000 requests/day, hard** | `claim_extract`, `scene_extract`, `prose`, `codex_summary`, `verify`, `arbitrate` |
| local compute | unmetered, $0 | Ollama, MiniCheck-FT5 (`llm/providers/minicheck.py`, already wired) |

Evaluation was banned from *both* because the rule said "LLM calls". The saving was ~60 requests
a day against a budget whose heaviest measured day reached 308 of 1000. The cost was that the
project could not detect its own improvements: on 2026-09-21 a real extraction gap was fixed for
`jakob` — three grounded personality traits where the graph had none, warmth visibly in the
rendered prose — and `audit eval` fact recall moved **zero points**, because gold says
"friendly"/"smile" and the page says "warm"/"understanding"/"generous". A yardstick that cannot
see a confirmed improvement is not protecting the budget, it is hiding the work.

**New rule (CLAUDE.md §2).** Measurement, evaluation and diagnosis may use **local** models
freely. They may not spend OpenRouter quota, and `wiki audit eval` must still run to completion
with `OPENROUTER_API_KEY` unset — an eval competing with extraction for the same 1000 requests
would be back to trading the product against its own yardstick.

This also directly serves the maintainer's constraint: local scoring adds **zero** load to the
free tier that has to carry the whole project to the paid run.

---

## 2026-09-21 — Rule change 2: recall WARNS, precision FAILS

**Retired rule:** any drop below `baseline.json` fails `wiki audit eval`, recall and precision
alike.

**Why it was wrong.** The two numbers are not the same kind of thing:

- **Precision / negative-facts** measure the page asserting something *untrue*. Unbounded, always
  actionable, a real defect every time. These still gate, and `tests/test_audit_eval.py` now has
  a test whose only job is to fail if that ever softens.
- **Fact recall** measures how much of a full Fandom page got reproduced — and it is structurally
  capped by the deliberate 2–4 sentence prose limit (CLAUDE.md §2). `norah-arendt` has **68**
  claims in the graph and room for roughly six sentences. Recall against a complete reference
  page can never approach 100%, and the gap is *correct behaviour*.

Gating on a capped number left `audit eval` red for days over a ceiling no correct work could
lift. A permanently-red gate is one nobody reads — the real cost, and nearly realised: on
2026-09-21 the FAIL was very close to being treated as background noise.

Recall now prints a `WARN` block naming every character that dropped, alongside the per-fact
`in graph` / `no lexical match` markers, which is the information a reader actually needs to tell
an extraction gap from a prose-cap omission.

---

## 2026-09-21 — What the two changes did, measured

`wiki audit eval`, v1-2, same graph, before and after:

| character | lexical only | + local entailment |
|---|---|---|
| kraft-lawrence | 44% | **56%** |
| marheit | 17% | **33%** |
| norah-arendt | 30% | **40%** |
| liebert / jakob / holo / enek / hans-remelio / yarei / zheren | — | unchanged |

Three characters gained a fact each, every one a genuine paraphrase the keyword matcher could not
see (`norah-arendt`'s "dreams of becoming a tailor" against a page saying "dressmaker" scores
**0.984**). Recall regressions **3 → 2**, and `norah-arendt`'s cleared on merit rather than by
moving the floor. Overall status: **FAIL → OK**, with two recall drops reported as WARN.

Cost: **zero OpenRouter requests.** Verified by running the whole report with
`OPENROUTER_API_KEY` unset — the entailment pass still ran.

### The one design decision worth not repeating by accident

MiniCheck is a *stricter* judge than keyword overlap, not a better one, so it is unioned in, never
substituted. Scoring by entailment alone measured **worse** than lexical on 3 of 5 characters: it
refuses compound gold sentences that keyword overlap passes, because entailment demands the whole
proposition. And it is acutely chunking-sensitive — the score is a MAX over documents, so
`liebert`'s "tense and nervous during the gold-smuggling job" scored **0.797** as one whole-page
document and **0.059** sentence-chunked, because no single sentence entails both halves. Hence
`gold.page_chunks`' three shapes: structured fields, each prose section (name-prefixed, since
sections are full of pronouns), and a truncated whole-page chunk so cross-section facts still have
one document that spans them.

---

## 2026-09-21 — Rule change 3: the regression floor is re-recorded, not frozen

`docs/PLAN_2026-09-14_pre_full_scale_audit.md` **B6** already said the floor was calibrated
against a superseded pipeline. It had drifted further since: the recorded numbers predate Phase
26 parts B/C *and* Phase 27's entailment pass, so `audit eval` was comparing today's output
against a system that no longer exists.

**Re-recorded from one real run against the current graph**, per entity, with the reason written
into the file's own `_comment` so it stays auditable:

| | floor | change |
|---|---|---|
| precision, all 10 | **1.0** | jakob 0.667→1.0, kraft-lawrence 0.75→1.0 — real Phase 26 gains, and raising a floor that still hard-gates is strictly safe |
| recall, risen | enek 0.25→0.50, hans-remelio 0.29→0.43, kraft-lawrence 0.33→0.56, marheit 0.17→0.33 | locked in |
| recall, level | holo 0.70, norah-arendt 0.40 | unchanged |
| recall, newly recorded | yarei 0.25, zheren 0.20 | were ungated |
| recall, lowered | jakob 0.22→0.11, liebert 0.75→0.50 | with a per-entity reason, below |

The two lowered floors are the part that needs justifying, and the justification is not "the
report was red":

- **jakob** — its extraction was *improved* this phase (three grounded PERSONALITY traits where
  the graph had none). The facts still missing are appearance details — hair, mustache, apron —
  for which **no claim exists in the graph at all**, which the report now marks per fact as
  `no lexical match in graph`.
- **liebert** — one missing fact is an appearance detail the novel *contradicts* (gold: "middle-
  aged ~30 with a goatee"; v2 P288: "spirited young employee, smooth blond hair"), and the other
  is a compound sentence whose content is on the page, reworded.

Recall no longer gates, so neither of these blocks anything; they are WARN thresholds now.

**The rule going forward**, written into `baseline.json`: raise a floor whenever a run beats it
and you have read why; lower one only with a per-entity reason recorded in the file, and never to
turn a red report green.

**Result:** `wiki audit eval` reports **OK** for the first time in days, with no regressions and
no metric-gaming — the floors simply describe the pipeline that exists. `audit` is OK on claims,
contradictions, verify, pages, links and relationships. pytest 1011.

---

## 2026-09-21 — Rule change 4: a spend ceiling that does not reset between runs

The maintainer's concern, before handing over a paid key: that the agent would re-run the corpus
repeatedly — wrong format, forgot a fix, needs recalibration, wrong volume — and produce a bill
they cannot pay.

**The concern is supported by this session's own evidence, not refuted by it.** Measured from
`calls.jsonl`: 593 OpenRouter calls today, of which **199 (about a third) were in runs discarded
entirely** — the Holo/Hans trait experiment that was rolled back, and a "control" that turned out
to be measuring the window-budget bug. On a free tier that cost nothing, so nothing disciplined
it. That is exactly the described failure mode at small scale.

### The gap in the existing guardrail

`budget.hard_stop_usd` (25.00) looked like protection. It is not, for a sequence of runs:
`check_before_call` compared against `self.total_cost` — **this run's ledger only** — and the
`Budget` is constructed per `LLMClient`, i.e. per process. `Budget.accumulate`/`save` already
maintained a cumulative total in `data/cache/llm/budget.json`, and **nothing ever checked it**.
24 runs happened on 2026-09-21; that ceiling would have permitted 24 × $25.

### The fix

`budget.lifetime_cap_usd` (unset by default, so nothing pre-existing changes). When set,
`LLMClient` seeds the run's budget with every dollar already recorded in the cumulative ledger,
and `check_before_call` refuses once *this run plus all previous runs* crosses it. It survives
re-running, process restarts, and "just once more"; raising it is an edit to
`config/models.yaml`, not something a run can do to itself.

### The number that reframes the whole worry

Cumulative usage across **every run the project has ever made**, mistakes and discarded
experiments included: **27.0M input / 3.3M output tokens**.

| tier | all history | one cold 2-volume rebuild |
|---|---|---|
| budget (~$0.15/M in, $0.60/M out) | **$6.03** | $1.21 |
| mid (~$1/M, ~$3/M) | $36.88 | $7.38 |
| high (~$3/M, ~$15/M) | $130.39 | $26.10 |
| frontier (~$15/M, ~$75/M) | $651.94 | $130.50 |

**Model choice dominates agent discipline by two orders of magnitude.** Every mistake made in
this project's entire history costs about $6 on a budget-tier paid model. The same mistakes on a
frontier model cost $650. The lever that actually controls the bill is `config/models.yaml`'s
routing, not how careful the agent is — and the honest reading of the table is that the paid run
should be a cheap model everywhere except the few stages measured to need better.
