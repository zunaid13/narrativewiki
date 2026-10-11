# Phase 0 — Foundation

**Closed:** 2026-09-01 · **Next:** Phase 1, Ingestion

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

A working package, all six root docs, three config files, the complete model layer, and
`wiki doctor`. No pipeline stage is implemented — every stage command prints which phase adds it.

```
CLAUDE.md  README.md  VISION.md  LOG.md  USER_GUIDE.md  STRUCTURE.md
config/    series.86.yaml · models.yaml · extraction.yaml
docs/      CONTRACTS.md · PROMPTS.md · handover/
src/narrativewiki/
  paths.py            every data path, so nothing hard-codes data/ anywhere
  config.py           Settings: series + models + extraction, and role resolution
  cli.py              typer app; doctor/status/budget/audit work, stages are stubs
  llm/                client · cache · budget · providers/{ollama,anthropic,google,openai}
  audit/reports.py    report registry; Phase 1 registers the first real one
  ingest/ entities/ extract/ graph/ synth/ site/    package skeletons only
tests/     test_config.py · test_llm.py   (38 tests, all passing)
```

## Verify it in one command

```bash
python -m pytest          # 38 passed
python -m narrativewiki doctor
```

`doctor` currently reports **two failures — `local_fast` and `local_prose` unreachable** — because
Ollama is not running on this machine. That is correct behaviour, not a bug. Start it and pull the
model to clear them:

```bash
ollama serve
ollama pull qwen2.5:14b-instruct-q4_K_M
```

Everything else passes: 13 volumes discovered (1–13), all packages present,
pyahocorasick has a CPython 3.14 wheel, 60 GB free.

## Things you need to know

**The `wiki` console script is not on PATH on this machine.** pip installed `wiki.exe` to
`C:\Users\pc\AppData\Roaming\Python\Python314\Scripts`, which is not in PATH. Use
`python -m narrativewiki <command>` — identical behaviour — or add that directory to PATH. The
docs use `wiki` because that is what a normal install gives you.

**Windows console encoding is handled, do not undo it.** `cli.py` reconfigures stdout/stderr to
UTF-8 at import. Without it, cp1252 raises `UnicodeEncodeError` the moment anything prints the
series title (`86—EIGHTY-SIX` has an em dash) or a name like `Milizé`. This will bite every stage
that prints corpus text, which is all of them.

**YAML flow mappings need a space after the colon.** `KEY:{ ... }` parses as part of the key and
produces a confusing error 14 lines later. Cost a debug cycle already.

**`resolve_role` is the only way to pick a model.** It reads `routing` in `config/models.yaml` and
falls back to a local profile when an API key is missing, which is what makes a zero-key run work.
`tests/test_config.py::test_bulk_stages_route_local` guards against extraction silently drifting
onto a paid provider — do not delete it.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Raw `httpx` for OpenAI-compatible hosts | One adapter serves OpenAI, OpenRouter and any compatible endpoint; keeps the dependency list small | The `openai` SDK — another dependency for no new capability |
| Provider SDKs imported lazily | A fully local run must not require `anthropic` or `google-genai` to be installed | Top-level imports with try/except at module scope — harder to give a good error |
| JSON via prompt + Pydantic validation + repair-retry | Has to work identically across Ollama, Anthropic, Gemini and OpenAI. Ollama's `format: json` is used where available as a bonus | Provider-specific structured-output APIs — four code paths, three of which are untested locally |
| Regex volume discovery, not a file list | Adding volume 14 needs no config edit; a new series needs no filename transcription | An explicit `volumes:` list in the series config |
| `estimate_tokens` = chars/4 | Used only for window sizing and budget display, never for anything exact. Avoids a `tiktoken` dependency that would be wrong for Qwen anyway | Real tokenizer per provider |
| Stubs that name their phase | An unimplemented command should teach, not raise ImportError | Leaving commands unregistered until built |

## What Phase 1 must do

Implement `ingest/` and register the first audit report. Full context is in `CLAUDE.md` §3 — the
nine corpus traps are already written up there and in `config/series.86.yaml`; **do not
rediscover them**, an inspection pass across all 13 volumes already paid for that.

The two that will silently corrupt output if missed:

1. **Chapters span multiple XHTML files.** Walk `<spine>` in order; start a new chapter on
   `h1.chapter-number`; append h1-less body documents to the current chapter. Filename sort is
   wrong (`chapter001_a`, `_aa`, `_bb`).
2. **Replace `img[src*="mdash"]` with `—` before stripping images**, or interrupted speech becomes
   `"thank you for saving m"`.

Output shape is fixed in `docs/CONTRACTS.md` §1 — write to that, not to something new. Use
`paths.parsed_volume(vol)` and `paths.parsed_manifest()`.

**Phase 1 is done when** `wiki ingest --volumes 1-13` produces 13 JSONL files plus a manifest, and
`wiki audit ingest` reports ~936,000 total words with a non-zero Para-RAID count in **every one of
the 13 volumes**. A zero in any volume means the class regex regressed; that check is the point of
the report.

Register the report with `@reports.register("ingest", "wiki ingest")` and remove `"ingest"` from
both `_PENDING` in `cli.py` and `_PLANNED` in `audit/reports.py`.

## Known gaps, deliberately left

- No stage logic anywhere yet — that is the phase plan working as intended.
- `run-all` is a stub; it gets wired up in Phase 7 when there is a full chain to run.
- `web/` is an empty directory until Phase 7.
- Provider adapters are untested against live APIs (no keys on this machine). The Ollama adapter
  is the one that matters and will be exercised properly in Phase 2.
