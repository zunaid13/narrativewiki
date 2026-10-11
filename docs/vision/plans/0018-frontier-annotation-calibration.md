# Frontier annotation calibration and cost projection

Status: complete; Nemotron/Gemini outputs and derived reports archived outside the repo on 2026-10-10; retained as historical model calibration, not human evaluation.
Date: 2026-10-10. Scope: the existing original-text Anne v1–5 review packet only.

Archive: `G:/UIU classes/narrativewiki-old-ai-evals-2026-10-10-d95d307`, preserving the
former paths under `docs/eval/agreement/`. Rollback checkpoint: `d95d307` (pushed).
The model tools and supporting metadata remain in the repo. Commands and completion links
below describe the historical run; its outputs are now external. For the new human results,
see [plan 0019](0019-human-review-agreement.md); do not substitute model labels for human labels.

## Evidence and model choices

The consolidated packet has 554 items in four different tasks; 14 precision items also ask
whether both characters participate in a scene. Existing accepted answers originated from AI
and were accepted in a human review, not collected independently. See
`docs/eval/agreement/README.md` and `docs/eval/human_check/HUMAN_REVIEW.md`.
These answers must remain hidden from new labelers. Missing evidence and candidate-only recall
limit what any model can establish; stronger reasoning does not fill those evidence gaps.
No frontier model has been benchmarked on this packet and no perfect-accuracy claim is supported.

Candidate accuracy-first pair: GPT-6 Astra and Claude Fable 5.1, labeling independently.
Candidate lower-cost pair: GPT-6 Astra and Claude Opus 5.5. Cross-provider agreement is a diagnostic,
not proof of truth: audit agreements as well as disagreements with independent humans.
These are proposed adaptations based on documented model roles, not measured rankings for this task.

Official sources checked 2026-10-10; reading depth: model role/capabilities, relevant pricing,
batch-discount and reasoning-billing sections, not complete model-card evaluations:

- [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra): demanding reasoning;
  standard $10 input / $50 output per million tokens; Batch half those rates.
- [Claude Fable 5.1](https://platform.claude.com/docs/en/models/fable-5-1/overview): demanding
  reasoning; $10 / $50, Batch half. Anthropic recommends starting with Opus for most work and
  escalating to Fable when evaluation shows a need.
- [Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview): $4 / $20,
  Batch half; adaptive thinking always on.
- [OpenAI pricing](https://developers.openai.com/api/docs/pricing): GPT-6.1 Sol $2 / $10,
  Batch half, short-context Standard.
- [Google Cloud pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing):
  Gemini 3.1 Pro Preview $2 / $12, global, at most 200K input tokens per request;
  Batch $1 / $6. This is the repo's Google Cloud route, not an AI Studio switch.
- [OpenAI reasoning billing](https://developers.openai.com/api/docs/guides/reasoning): hidden
  reasoning is billed as output and usage varies. Exact future invoices cannot be known.

## Offline projection

Reproduce with `python docs/eval/agreement/estimate_api_cost.py`.
Files: `docs/eval/agreement/pricing_20261010.json` (historical rate snapshot),
`estimate_api_cost.py` (offline only), and `api_cost_projection.json` (all scenarios and input hash).
These are reporting artifacts, not provider routing profiles or a live API runner.

Each hypothetical request contains one whole item's question and evidence as plain text plus the
full reader rules and a short JSON-response instruction. There are 554 requests per model.
The combined prompt text contains 3,858,174 characters. The project's rough English sizing
rule (floor of characters / 4 per request) gives 964,334 input tokens; maximum request 7,111
estimated tokens. These are **estimates**, not model-specific token counts. No paid tokenizer
or inference endpoint was used.

Assuming 1,000 total billed output tokens per item (thinking plus visible JSON/reason):

| Model | Standard full pass, USD | Batch full pass, USD |
|---|---:|---:|
| GPT-6 Astra | 37.34 | 18.67 |
| Claude Fable 5.1 | 37.34 | 18.67 |
| Claude Opus 5.5 | 14.94 | 7.47 |
| GPT-6.1 Sol | 7.47 | 3.73 |
| Gemini 3.1 Pro Preview | 8.58 | 4.29 |

Astra plus Fable: $74.69 Standard or $37.34 Batch. Astra plus Opus: $52.28 Standard or $26.14
Batch. At 500–2,000 billed output tokens per item, each Astra/Fable pass ranges from $23.49
to $65.04 Standard ($11.75–$32.52 Batch). This range is illustrative, not a confidence interval
or hard cap; higher reasoning usage can exceed it. No retries, extra evidence retrieval,
adjudication, cache writes/reads, tools, tax, regional uplift or message/schema overhead is included.
Round only displayed totals; the JSON retains arithmetic before currency-display rounding.

## Ordered experiments if labeling is subsequently authorized

1. Implement blind request preparation without reading accepted answers or prior rationales.
   Preserve cutoff, evidence IDs and all displayed evidence; add task-specific response schemas.
   Use `config/models.yaml` profiles and `llm/client.py` for every model call, cache and budget.
   Inspect provider support before implementing: reasoning and Responses/Batch options may need
   work in `src/narrativewiki/llm/providers/openai.py` and `anthropic.py`; do not bypass the client.
2. First use deterministic prompt inspection and fixture validation. Then select a small
   task-stratified pilot that includes pair placement, partly, not-shown and uncited cases.
   Before billing, explicitly explain why stored answers/fixtures cannot measure the new model's
   independent accuracy. No pilot inference is authorized by this cost discussion alone.
3. Have independent humans label the pilot. Run the two candidate models independently,
   without exchanging labels. Compare each with the human judgments by task and evidence sufficiency.
   Measure total billed input/output including reasoning from provider usage, token-limit failures,
   invalid schemas, and cached/retried calls. Record every result and exact command/run id in
   `docs/MEASUREMENTS.md`. Existing AI-accepted answers are a secondary comparator, not ground truth.
4. Stop and repair the protocol if evidence needed for the task is absent, labels are malformed,
   cutoff rules are violated or token limits truncate verdicts. Do not force missing evidence to no.
   Select model and effort from human-validated errors rather than generic leaderboard rank.
   Establish the acceptable error threshold with the maintainer before claiming a validated winner.
5. Once the pilot establishes usable quality and a spend bound, label the full existing packet
   once per chosen model. Batch may reduce rates while keeping one question per inference;
   compare pilot quality before adopting a changed configuration. Preserve untouched model outputs.
6. Compute per-task Cohen kappa on first-pass labels, audit disagreements and a random subset
   of agreements with humans. Keep adjudication separate. Name the result model–model or
   model–human agreement as appropriate. Human–human agreement needs two independent humans.

## Authorized model agreement execution, 2026-10-10

The maintainer requested the strongest free OpenRouter candidate and strongest Gemini candidate
to independently label this packet, followed by Cohen kappa. Selected a fixed Nemotron 3 Ultra
550B/A55B free endpoint for its documented complex reasoning capabilities, and Gemini 3.1 Pro
Preview through the configured Vertex credentials. This is a reasoned selection, not an empirical
claim of best accuracy. OpenRouter's free collection ranks usage, not annotation accuracy.
Live catalogue saved in `docs/eval/agreement/openrouter_free_catalog_20261010.json`.
Official sources inspected for availability, capabilities and limits:
[Nemotron Ultra](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free),
[free models](https://openrouter.ai/collections/free-models),
[limits](https://openrouter.ai/docs/api/reference/limits),
[Gemini Pro](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview).

The paid pipeline's lifetime guard is already exhausted. The maintainer separately approved
up to $20 additional Gemini spend for this evaluation; the pipeline cap remains unchanged.
The runner persists the allowance across resumed runs and reserves a conservative per-request
maximum including hidden thinking. The pinned zero-price OpenRouter endpoint cannot add paid
spend and has its own zero-cost budget ledger. Both use LLMClient/cache/provenance, with no SDK
calls outside the adapters and no model fallback. One full question per request, original rubrics,
strict item/label/pair validation, independent outputs and durable checkpoints.
OpenRouter lacks native response_format support on this endpoint; text JSON is validated locally
and malformed results are repaired through the same model/client. Gemini uses native JSON mode.

Commands (rerun to resume without relabeling completed items):

```powershell
.venv/Scripts/python.exe docs/eval/agreement/run_model_labels.py --role agreement_openrouter_ultra --output docs/eval/agreement/model_runs/openrouter_ultra --jobs 4 --interval 3.2
.venv/Scripts/python.exe docs/eval/agreement/run_model_labels.py --role agreement_vertex_pro --output docs/eval/agreement/model_runs/gemini_pro --jobs 4 --additional-budget-usd 20
.venv/Scripts/python.exe docs/eval/agreement/compare_model_labels.py docs/eval/agreement/model_runs/openrouter_ultra docs/eval/agreement/model_runs/gemini_pro
```

Stop on exhausted quota/budget, invalid output after repairs, provider refusal or inaccessible
credentials; preserve completed outputs and report missing items rather than inventing labels.
The comparator requires complete labels and produces per-task kappa, full comparison CSV,
agreement/disagreement CSVs and an evidence-rich disagreement HTML for human review.
Record completed runs and per-task numbers in MEASUREMENTS before treating them as results.

Unresolved: empirically best labeler, correlated model errors, human recruitment and acceptable
error thresholds. Agreement is model-model, not independent human reliability or accuracy.

Completion: `docs/eval/agreement/model_comparison/README.md` summarizes the full comparison;
`model_agreement.json` preserves counts, confusion tables and separate pair-placement agreement.
CSV and HTML exports retain both independent judgments and explanations. Results, recorded usage,
exact command and run IDs are in `docs/MEASUREMENTS.md`. The hourly supervisor has stopped.
