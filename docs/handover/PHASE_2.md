# Phase 2 — Entities

**Closed:** 2026-09-02 · **Next:** Phase 3, Claims

You should be able to continue from this document without reading any source. If you find
yourself opening files to answer a question this should have answered, fix this document.

---

## What exists now

```
src/narrativewiki/entities/
  candidates.py   Paragraph records -> name-candidate surfaces. Deterministic, no LLM.
  classify.py     Local-LLM typing: candidate -> CHARACTER/FACTION/LOCATION/EVENT/TECH/dropped.
  alias.py        Tiered alias clustering -> gazetteer entities, plus entity_overrides.
  gazetteer.py    slugify(), compute_importance(), build_gazetteer() assembly, load().
  automaton.py    Aho-Corasick build + corpus mention index. The token lever (VISION.md).
src/narrativewiki/cli.py             gazetteer() wired end to end; run_all() now chains
                                       ingest -> gazetteer before the Phase 3 stub.
src/narrativewiki/audit/reports.py   _gazetteer_report(): by-type table, low-confidence/
                                       ambiguous counts, CHARACTER-count FAIL check, and
                                       roster.html (sortable, click a column header).
tests/test_entities.py               34 tests: every merge tier in isolation, all five
                                       entity_overrides kinds, automaton longest-match/word-
                                       boundary behaviour, gazetteer assembly.
```

## Verify it in one command

```bash
python -m narrativewiki gazetteer --volumes 1-13   # needs `ollama serve` + the model pulled
python -m narrativewiki audit gazetteer
python -m pytest                                     # 87 passed
```

**Ollama was not reachable in the sandbox this phase was built in** (`localhost:11434` refused
the connection) — the full pipeline was verified two other ways instead: unit tests with a
scripted fake client (see `tests/test_entities.py`), and one real run against v01's actual
parsed text with `narrativewiki.llm.providers.ollama.complete` monkeypatched to a scripted fake
(proving the CLI wiring, JSON shapes, and audit report all work against real corpus data end to
end). That output was deleted afterward since it was fake-classifier output, not a real build —
**the first thing to do on a machine with Ollama running is a real `wiki gazetteer --volumes
1-13` and a hand-audit of `roster.html`.**

## Things you need to know

**Candidate mining trades precision for recall, on purpose** (VISION.md/PROMPTS.md design
philosophy: a wrong candidate costs one wasted classify call and is caught by classify.py or the
human roster review; a missed candidate is invisible and never recovered). The miner finds
maximal runs of 1-4 consecutive capitalised tokens, single-space-separated — punctuation, a
second space, or a lowercase token breaks the run. Two things prune the obvious junk before it
even reaches the LLM:
- A small hand-maintained stopword set (`_GENERIC_STOPWORDS` in `candidates.py`) for common
  pronouns/articles/conjunctions.
- A **corpus frequency-ratio filter**: a single-token candidate is kept only if it is
  capitalised at least 75% of the times that exact word (any case) appears anywhere in the
  volumes being mined. Real names are almost always capitalised; ordinary words ("in", "not",
  "don['t]") are capitalised only when they happen to open a sentence, so most of their
  occurrences are lowercase. This is what catches sentence-initial junk a fixed stoplist can't
  enumerate in advance — it caught things the stoplist alone missed ("In", "Not", "To", "All",
  "Having", "Don"). Multi-word candidates skip this filter; a 2+ word capitalised run is
  essentially never a false positive on its own.

**A capitalised run's regex deliberately does not swallow a trailing apostrophe.** An earlier
version matched `Shin's`/`I'm`/`That's` as their own candidates, distinct from `Shin`/`I`/`That`
— splitting a real name's count across two surfaces and flooding the candidate list with
contraction junk. Dropping the apostrophe from the token pattern folds the possessive/
contraction back into the base token for free. If you touch `_TOKEN_RE`, rerun
`test_possessive_and_contraction_fold_into_base_token`.

**Honorific detection has to look in two places, not one.** A single-token honorific check
("does the text right before this candidate say 'Major '?") fails for the common case, because
`Major Milizé` is itself ONE capitalised run — `Major` is inside the matched surface, not before
it. `_preceded_by_honorific` in `candidates.py` checks both: does the surface's own first word
match an honorific, and (for an honorific the run-regex didn't capture, e.g. `Dr. Milizé` where
the period breaks the run) does the text immediately preceding the run match one. This was
caught by `test_honorific_signal_detected` failing during this phase — if you touch honorific
detection, keep that test.

**`entity_id` collisions are a real, not hypothetical, case.** Two different-typed clusters can
land on the same canonical text (e.g. a faction and a piece of tech both plausibly named
"Spearhead" in a different series) and `slugify()` would give them the same `entity_id`. Nothing
downstream (`_apply_overrides`'s `by_id` dict, `automaton.build_automaton`'s per-entity mention
tagging) can tolerate that silently — it was caught by
`test_different_types_never_auto_merge_even_if_identical_text` (the *type* stayed unmerged in
the union-find, but the two same-slug entities silently collapsed into one dict entry one step
later). `_build_clusters` now disambiguates with a `-2`, `-3`, ... suffix. If you add another
place that builds a lookup dict keyed by `entity_id`, assume collisions are possible, not rare.

**True nickname/call-sign aliases ("Shin" -> "Undertaker") are never textually similar**, so a
fuzzy-string-only approach to picking which pairs are worth an LLM call would never even propose
them. `alias.py`'s tier-d pair discovery adds a second, independent trigger: two candidates that
share at least one evidence `para_id` (both were seen in at least one of the same sampled
paragraphs) are also LLM-eligible, regardless of string similarity. This is why
`candidates.py::_MAX_EVIDENCE_PER_CANDIDATE` was raised from 8 to 40 — co-occurrence detection
only has as much recall as the evidence sample it's checking against. It is still best-effort,
not exhaustive (a candidate seen hundreds of times only keeps 40 sampled paragraphs); a genuine
miss is exactly what `entity_overrides.aliases` in the series config exists to patch by hand —
see the worked `Baleygr` example already in `config/series.86.yaml`'s comments. When ranking
which of the (capped at `MAX_LLM_PAIRS = 300`) eligible pairs actually get an LLM call,
co-occurrence pairs are prioritised ahead of fuzzy-band pairs, since a fuzzy-ratio sort alone
would push the (textually dissimilar, by definition) nickname pairs to the back of the list.

**`entity_overrides.split` cannot automatically decide which mention belongs to which target.**
Given `{entity: "nouzen", into: ["shinei-nouzen", "kiriya-nouzen"]}`, there is no way for
corpus-wide mention counts alone to know which specific occurrences of "Nouzen" refer to which
person — that's a real coreference problem outside what this phase's evidence gives it. The
implemented behaviour: the original merged cluster is deleted and replaced with the listed
target ids as new, empty entities (0 mentions, no surface forms, confidence 0.5, a note pointing
at this fact). A human then populates each target via a follow-up `entity_overrides.aliases`
entry per target and reruns `wiki gazetteer --force`. This is a deliberate, documented gap, not
an oversight — see `test_entity_overrides_split_creates_empty_targets`.

**The Aho-Corasick automaton enforces word boundaries itself.** Neither pyahocorasick nor the
pure-Python fallback has a boundary concept, so without this "Shin" would fire inside "Shining".
`automaton._is_boundary_match` checks the character immediately before/after each raw match
isn't alphanumeric/apostrophe, applied identically to both backends before the longest-match-
wins overlap resolution (`start` ascending, then longest first, greedy non-overlapping sweep).

**`wiki doctor` already reports which automaton backend is active** ("pyahocorasick (C
extension)" vs "ahocorapy (pure Python, slower but correct)" per the Phase 0 handover) — this
phase's own `pyproject.toml` fallback dependency is `ahocorapy`, but `automaton.py` does NOT
call into it. Its API wasn't worth depending on sight-unseen; instead there's a small internal
pure-Python fallback (linear multi-substring scan per surface, O(entities x text) instead of
O(text) — correct, just not the fast path) that activates automatically whenever
`import ahocorasick` fails. `MentionAutomaton.backend` reports which one is live. This machine's
pyahocorasick import succeeded (confirmed via the smoke tests), so the fallback path is
untested against ahocorapy specifically — only exercised by unit tests that force
`_HAS_PYAHOCORASICK = False`... actually it isn't forced anywhere; **if you need to verify the
fallback path, monkeypatch `automaton._HAS_PYAHOCORASICK = False` and `automaton.ahocorasick =
None`** before building an automaton in a test. Not done in this phase — a known gap, not a
claim of coverage that doesn't exist.

## Decisions taken, and what was rejected

| Decision | Why | Rejected alternative |
|---|---|---|
| Regex + frequency-ratio candidate mining, no NLP library | Zero dependencies, deterministic, fast enough to mine all 13 volumes in well under a second; the LLM classify stage and human roster review are the accuracy backstop by design | spaCy NER — heavier dependency, and still needs the same human-review safety net for a translated light novel's invented names |
| Tiered clustering (free tiers a-c, LLM only for tier d) with a hard `MAX_LLM_PAIRS` cap | Bounds cost on a corpus with hundreds of candidates per volume; PROMPTS.md's own design rule is "one decision per call" plus conservative defaults | Asking the LLM about every candidate pair (O(n^2), unbounded cost) |
| Co-occurrence as a second, independent tier-d trigger alongside fuzzy similarity | Fuzzy similarity alone structurally cannot find true nicknames/call-signs; this was found and fixed mid-phase, see notes above | Fuzzy-similarity-only pair discovery (the first draft; would have silently never merged "Shin"/"Undertaker") |
| `entity_overrides.split` creates empty stub targets for a human to populate | Automatic per-mention disambiguation is a real coreference problem this phase's evidence can't solve; matches the project's own stated design (roster.html + config overrides as the human-in-the-loop safety net) | Attempting an automatic split heuristic (e.g. by evidence volume) — would silently misattribute facts with no way for a reviewer to notice |
| Internal pure-Python Aho-Corasick fallback instead of depending on `ahocorapy`'s exact API | Avoids guessing at an unverified third-party API; correctness is what matters for the fallback path (rarely hit — this machine has the C extension), not speed | Wiring the declared `ahocorapy` dependency directly |

## What Phase 3 must do

Implement `extract/{windows,schema,claims}.py` and register `wiki audit claims`. Read
`docs/CONTRACTS.md` section 3 for the claim schema before writing anything.

Useful things this phase leaves behind: `data/02_entities/mentions.jsonl` is exactly the
Aho-Corasick mention index `extract/windows.py` needs to build evidence windows without ever
scanning a whole chapter — every mention already carries `para_id`, `vol`, `entity_id`,
`surface`, `start`, `end` in corpus order. `gazetteer.json`'s `importance` field is what
`config/models.yaml`'s `budget.polish_importance_percentile` will use in Phase 6, already
computed. `first_vol` on every `surface_forms` entry is what makes spoiler-safe alias display
possible later — never re-derive it from `aliases` alone, the two lists carry different
information (`aliases` has no per-alias volume).

**Run a real `wiki gazetteer --volumes 1-13` and hand-audit `roster.html` before starting
Phase 3.** Extraction is the expensive stage (hours of local GPU time per USER_GUIDE.md); a bad
merge or split in the gazetteer means redoing that work.

## Known gaps, deliberately left

- No real end-to-end run against Ollama happened in this phase (sandbox had no reachable Ollama
  server) — verified instead via unit tests plus one monkeypatched-provider smoke run. This is
  the single most important thing to do before Phase 3.
- The pure-Python Aho-Corasick fallback path (`automaton.py`, used only when `pyahocorasick`
  fails to import) has no dedicated test forcing that branch — see the automaton note above.
- `entity_overrides.split` requires a human follow-up (`aliases` entries per target) to actually
  populate the split entities — by design, not an oversight; see notes above.
- Candidate mining is regex-based and English-prose-shaped; a series with very different prose
  conventions (script formatting, non-Latin scripts) would need `series.<id>.yaml` tuning or,
  in the worst case, a different mining strategy — not exercised, since this project has one
  reference corpus.
