# Should You Keep This Project? — re-evaluated

**Date: 2026-09-28.** Rewritten from scratch. The 2026-09-25 version decided "keep it, as a
product, not as a paper". The maintainer reinstated publication the same day, so that verdict
is checked claim by claim in §2. Earlier versions are in `git log`.

**Verdict: keep it, and finish the paper on Anne. Do not widen scope before that.** The paper is
now a *measured trade-off*: how much source-supported information survives to a cutoff-scoped page
without unsupported assertions or disclosure of later text, against matched prefix-only baselines.
The instrument is built, the generator is fixed, the main build is frozen and running, and the
baselines are queued. What is left is mostly hand reading and writing, plus the one question the
project has never answered: **does the architecture beat a simpler system?** That question is now
funded and scheduled. That is the reason to keep going.

Every number below has a row in `docs/MEASUREMENTS.md`. Facts about the system are in
`CAPABILITY_REFERENCE.md` (same folder). This file only argues.

---

## 1. What changed since the last version

| Then (2026-09-25) | Now (2026-09-28) |
|---|---|
| No publication pathway | **A paper**, positioned as a measured trade-off, not a "first". LaTeX skeleton in `docs/paper/` with every value a `\res{KEY}`; results stay empty until the maintainer reviews them |
| Target: fandom-quality structure | Still the product bar. The **paper** target is per-cutoff coverage, support and disclosure, always reported jointly and never pooled first |
| 3 light-novel corpora at v1–2 | **Anne v1–5 main, Oz v1–5 held out, Middlemarch for tuning.** Light novels are development only (not public domain) |
| Per-series overrides and prompt vocabulary | **One general pipeline**; only format conversion and gold are per series |
| Flash-Lite with a cross-provider fallback chain | **Gemini 3.6 Flash for every stage and every reported number**; a refusal gets an empty answer, never another model |
| $12.79 of a $20 cap | ≈ **$44** recorded of a **$275** ceiling |
| "Precision 100%" | **82.5%** audited assertion precision on the dev wikis. The 100% was a different quantity |
| Gold: 10/6/6 characters, lexical at its core | Anne **116 facts / 43 characters**, Oz **109 / 35**, ≥20 new facts per cutoff; agent-drafted and labelled |
| No baseline | X1, B1, B2, B3 (LightRAG), B4, X2 built; Anne cells running |

---

## 2. The last version's argument, claim by claim

| 2026-09-25 claim | Status today |
|---|---|
| "No publication pathway; dropping it was the honest response" | **Reversed by the maintainer**, and on better grounds than the old paper plan: public-domain corpora, a held-out work, baselines, and a narrowed novelty claim that concedes four pieces of prior art |
| The strongest finding is that a gate is as strong as its least-checked consumer | **Confirmed twice more.** Page front matter listed future aliases (Anne v01: "Anne Blythe"), and an interval took its qualifier from a later volume. Both were found by reading pages; neither was found by a probe |
| Precision 100% on every gold character | **Retracted.** It counted hand-listed negatives on a page, not assertions. Audited over sampled rendered lines: 99/120. The misses were relation labels and mis-filed fields, now defined for the verifier |
| Recall is bounded by the prose cap | Still true, and the bound is now visible: a t=1 reader sees **871** atomic assertions on S&W, while the cited-line pool holds **90** |
| There is no baseline | **Being closed.** This was the weakest point of every earlier version |
| Polish has no natural end | **Solved by a freeze.** `freeze-anne-v1` pins src, config and scripts, and paper numbers come only from it |
| Leak probes on Overlord and Bookworm ($0) | Moot for the paper (dev series). The leak work moved to Anne, hand-read |

---

## 3. What got stronger

- **A held-out design.** Every development series shaped a general rule, so none of them could be
  held out. Oz has had no LLM stage run on it. Its gold was drafted from the text alone.
- **Generator choice made on evidence, then fixed.** In a stored-prompt bake-off, 3.6 Flash had 0
  unsupported facts in 26 against Flash-Lite's 6 in 50. The end-to-end Anne t=1 trial, hand-read:
  recall 18/23, 0/35 future facts disclosed, precision 32/40, $2.71.
- **The verifier is measured, not assumed.** Balanced accuracy is 0.989 on an 81-item challenge
  set and 0.750 on a 12-item hard set. Its blind spot is known and shared by every judge tried:
  claims lifted from a story a character tells.
- **The measuring tools are themselves measured.** MiniCheck is a screen, not an arbiter: tool
  recall was 0.652 against hand recall of 0.783, and it reads "engaged" as "marries". Every positive
  is hand-read, and verdicts are bound to the page's hash.
- **Contamination evidence** (*Leagues*): renaming and paraphrase remove *fact transfer* (name-only
  leak 32% → 0%) but not *recognition* (51.3% name cloze after paraphrase). This is a clean,
  quotable asymmetry.
- **Cost safety.** A 429 outage exposed a request multiplier in `map_calls`, now fixed. Runs stop
  after 3 quota failures, and every stage replays from cache for $0.

---

## 4. The honest case for stopping

- **No result yet says the system is better.** If B1 (prefix long-context) or B2 (chunk RAG)
  matches it on coverage at similar precision, the architecture's complexity is unearned. The paper
  must report that too.
- **Annotation is not independent.** Gold, precision verdicts and challenge items were read by the
  same agent that tuned the pipeline. Without a human second reader on a subset, the numbers are
  pilot data, and a reviewer will say so.
- **The rates are small-*n*.** 0/35 disclosures bounds the rate only at ≤ 0.086. Per-cutoff future
  denominators shrink toward t=5 (Anne: 90 → 22 future facts at t=1..4).
- **Budget and capacity.** B1 and X2 are estimated at $57 and $84 at Standard ceilings. The account
  is a free trial with no usage tier, and a day of 429s is normal. Oz needs a budget increase that
  has not been asked for.
- **The full-scope gazetteer is a known leak surface** until A1 (prefix-built t=2–4) measures it,
  and A1 runs only if money is left after the baselines.

**Stop if** the Anne matrix shows the system losing to B1/B2 on coverage *and* not winning on
precision or disclosure, **and** the maintainer does not want to publish a negative result. Short
of that, finishing is cheaper than it looks: most of the remaining work costs $0.

---

## 5. When is the paper done? (plan 0014)

| Step | State (2026-09-28 evening) |
|---|---|
| S02 freeze `anne-v1` | **Done** (tag `freeze-anne-v1`) |
| S01 Anne v1–5 build on the freeze | **Running** (extract-v4 finished 15:58 UTC) |
| S04 gold, Anne + Oz | **Done** (agent-drafted, labelled) |
| S08 judge challenge sets, M12 verifier | **Done** (pilot items) |
| S10 baselines built; B2/B3 tuned on Middlemarch | **Done** |
| S11 baseline cells on Anne, t=1..5 | **Running** (X1 t=1–2 done) |
| A1 prefix builds t=2–4 | Queued; budget-gated ($255 − spent > estimate + $15) |
| B5 hand reading at t=1..5 (recall, precision, every leak positive) | Waiting on S01 |
| Human second reader on a stratified subset | **Not started.** Required before anything is called test data |
| S03 Oz held-out run | Waiting on a budget increase |
| S12 statistics → S20 writing → maintainer review | After the above |

---

## 6. What to do next, cheapest first

1. **Let S01 and the baseline runner finish.** Resume a FAILED cell with its own command; the cache
   makes it cheap.
2. **Hand-read B5 and each baseline cell at t=1..5** ($0). This is the paper's core table.
3. **Recruit a human second reader** for a stratified subset of gold and precision verdicts ($0,
   but it takes someone's time). It is the cheapest way to turn pilot numbers into results.
4. **Re-measure artifact exposure** (pages, shared nav, slugs) on the frozen build ($0).
5. **A1 prefix builds** if the budget allows. They answer whether the full-scope gazetteer leaks in
   practice.
6. **Ask for the Oz budget** only once Anne's table exists, so the request comes with numbers.

---

## 7. If you are putting this in a cold email to a professor

Lead with a failure you measured, not with the system. `CAPABILITY_REFERENCE.md` §4.1 has the
full table; the best five now:

- **Evaluation validity:** a "100% precision" turned out to count missing negatives, not correct
  assertions. Audited over rendered lines it was 82.5%, and the errors clustered in relation labels.
- **Contamination:** renaming and paraphrasing a novel stopped closed-book fact transfer (32% →
  0%), but the model still recovered the original names from 51% of paraphrased passages.
- **LLM-as-judge:** every judge tried (a production verifier at 0.989 balanced accuracy, an NLI
  model, a local LLM) accepted a claim lifted from a story a character tells.
- **Temporal leakage:** each reader-facing spoiler with a concrete witness (a shared search index,
  page front matter, an interval qualifier) was found by reading pages, and none by the probes
  built to find them.
- **Calibration:** verbalized confidence picked a wrong occupation over the right one, 1.0 against
  0.72.

Rules for those emails:

- **Say "paper in preparation, results under review".** Do not quote a result the maintainer has
  not reviewed.
- **Never "no leaks"; say "0 of *n*" with its bound.** Never "first", "hallucination-free",
  "provably spoiler-free" or "decontaminated benchmark".
- **Never cite 100% precision, and never cite 0.303 without 0.033.**
- **Say the scope:** Anne v1–5 main, Oz held out, development work on three light-novel series
  that is never reported as results.

---

**Sources**
- [Living the Novel (arXiv 2512.07474)](https://arxiv.org/abs/2512.07474)
- [Can LLMs Express Their Uncertainty? (arXiv 2306.13063)](https://arxiv.org/abs/2306.13063)
- [MiniCheck (arXiv 2404.10774)](https://arxiv.org/abs/2404.10774)
- Project record: `docs/MEASUREMENTS.md`, `docs/handover/PHASE_33.md`,
  `docs/vision/PHASE_33.md`, `docs/vision/plans/0014-paper-values-tracker.md`,
  `docs/archive/CAPABILITY_REFERENCE.md`
