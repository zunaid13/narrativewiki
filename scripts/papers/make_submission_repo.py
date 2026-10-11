"""Build the anonymous submission repository: what a new user needs to run the pipeline and to reproduce the
paper's numbers, and nothing that exists only for development. $0.

Run:  .venv/Scripts/python.exe scripts/papers/make_submission_repo.py [OUT_DIR]
      -> "<parent of this repository>/narrativeWiki - for paper submission/"

In:   code and settings (src, scripts, the config of the works the paper uses), the user guide, the data
      contracts and the prompt catalogue; the evaluation files of those works (gold facts, labels, inventories,
      observations, cost, freeze records, the human-check package, the labelling tools); the ledger and the change
      log the paper cites; results.tex and the result tables (what the paper prints, read by derived_values.py
      and summary_stats.py); the generated wikis; the treated text of the decontaminated condition.
Out:  LOG / VISION / phase / handover / plan files, agent instructions, tests, runners, reference PDFs, the paper's
      prose, scripts and files of works the paper does not report, the source texts, the LLM cache.

Text is rewritten with make_release.py's rules, so no local path, account or institution survives; the scan at
the end exits 1 if one does. An OUT_DIR this script built before is rebuilt in place and its .git is kept.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs" / "paper" / "_build"))
from make_release import FORBIDDEN, PATHS  # noqa: E402  one set of anonymisation rules for both releases

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "narrativeWiki - for paper submission"
WORKS = re.compile(r"(anne|leagues)")  # the works the paper reports; Middlemarch (baseline tuning) is added where used
NOT_REPORTED = re.compile(r"spice|overlord|bookworm|mushoku|eighty|littlewomen|pride|probe-gutenberg"
                          r"|(^|[^0-9])86([^0-9]|$)|(^|[/_])oz([@_.-]|$)", re.I)
# scripts/eval: replays and audits on the development series, and operations helpers
EVAL_SCRIPTS_OUT = {"audit_observation_semantics", "character_evidence_coverage", "curve_table", "inventory_equivalence",
                    "make_blind_sheet", "nli_controls", "nli_kind_sweep", "probe_sparse_scene", "replay_context_budget",
                    "replay_scene_facts", "replay_verify_prompt", "structured_wiki_snapshot", "vertex_probe"}
PAPERS_SCRIPTS_IN = {"freeze.py", "summary_stats.py", "fig_cutoff.py"}
# docs/eval: session runners, superseded annotation packages, development-series gold, test fixtures
EVAL_DIRS_OUT = {"runners", "human", "annotation", "gold", "fixtures", "stale", "__pycache__"}
EVAL_NAMES_OUT = re.compile(r"^(OPEN_GAPS\.md|paper_review_.*|sparse_scene_prepared\.json)$|\.zip$")
SINGLES = ("USER_GUIDE.md", "pyproject.toml", ".env.example", "docs/CONTRACTS.md", "docs/PROMPTS.md",
           "docs/MEASUREMENTS.md", "docs/paper/results.tex", "docs/paper/appendix/g-additional-results.tex")

GITIGNORE = """corpus/
.env
.venv*/
__pycache__/
*.py[cod]
*.egg-info/
data/cache/
"""

README = """# NarrativeWiki

Code, evaluation data and generated wikis for the paper *NarrativeWiki: Evidence-Grounded Character Wikis at
Reader-Selected Narrative Cutoffs* (under anonymous review).

NarrativeWiki reads a novel series (EPUB) and builds a hyperlinked character wiki with one tab per volume:
"I have read up to volume N". A page at cutoff N is generated only from facts whose evidence lies in volumes
1..N, and every line cites the paragraphs it rests on.

## What is here

| Path | Holds |
|---|---|
| `src/narrativewiki/` | the pipeline; `wiki` is its command line |
| `config/` | model routing (`models.yaml`), the extraction taxonomy, one `series.<id>.yaml` per work |
| `scripts/run_series.py` | one work, volumes 1..N, every stage and audit in order |
| `scripts/baselines/` | the comparison systems: `X1` closed book, `B1` long context, `B2` prefix retrieval, `B3` LightRAG, `B4` full graph, `X2` full text |
| `scripts/eval/`, `scripts/papers/` | evaluation tools; table values, statistics and the cutoff figure |
| `USER_GUIDE.md` | every command and the order to run them in |
| `docs/CONTRACTS.md`, `docs/PROMPTS.md` | the format of every file the pipeline writes; the prompts |
| `docs/eval/parametric/`, `docs/eval/roster/` | gold facts with evidence paragraphs and reveal volumes; casts |
| `docs/eval/recall_hand/`, `precision/`, `leak_audit/` | label files: recall, precision samples with notes and citation verdicts, disclosure candidates and verdicts |
| `docs/eval/inventory/` | every assertion each wiki makes, per cutoff |
| `docs/eval/observations/`, `paper_numbers.json` | the labels as one row per observation; the values computed from them |
| `docs/eval/human_check/`, `agent_annotation/` | the human-check package and the second annotator's decisions |
| `docs/eval/labelling_tools/` | the helpers the labels were written with, and `derived_values.py` |
| `docs/eval/cost/`, `freeze/`, `a1/`, `m4_seeded/`, `baseline_tuning/` | per-run cost, freeze records, construction-scope comparison, seeded-disclosure test, baseline settings |
| `docs/MEASUREMENTS.md`, `docs/eval/CHANGES.md` | the ledger (one row per measured value, with its command) and the log of changes that moved a number |
| `docs/paper/results.tex`, `tables/`, `appendix/g-additional-results.tex` | every value the paper prints, each with its ledger row; the result tables |
| `dist/<series>/wiki/` | the generated wiki of every system at every cutoff (Markdown) |
| `data/anne-decon/`, `data/leagues-decon/` | the treated (renamed and paraphrased) text of the decontaminated condition |

Series ids: `anne` is the first build of NarrativeWiki and `anne@v2` the reported one; `anne@x1`, `@b1`, `@b2`,
`@b3`, `@b4` / `@b4-v2`, `@x2` are the comparison systems; `anne-decon@*` are the same systems on the treated text;
`anne@p<t>` / `anne@p<t>-v2` are builds whose entity index saw volumes 1..t only; `anne-m31` / `anne-m36` are the
generator trial; `leagues*` is the first-person sample; Middlemarch is the work the baselines were tuned on.

Not included: the source texts (public domain, fetched below), the model response cache and raw call logs
(2.4 GB; per-run cost summaries are included instead). Labels were produced by LLM annotators and reviewed as
the paper states; the `reader` field of a label file says who wrote each label. Local paths were replaced by
relative ones.

## Setup

Python 3.11 or later.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .[all]   # Linux/macOS: .venv/bin/python
cp .env.example .env                                # then add credentials, all optional
.venv/Scripts/python.exe -m narrativewiki doctor -s anne
```

`wiki doctor` prints what is missing and which model each stage will use. Generative stages follow the
`routing:` block of `config/models.yaml` (Vertex AI first; without credentials they fall back to a free tier
and then to a local Ollama model). The evaluation tools marked `$0` in their docstrings need only the files
here, or a local Ollama model (`ollama pull qwen2.5:14b-instruct-q4_K_M`). `scripts/run_series.py` and
`scripts/baselines/tune.py` start the interpreter at `.venv/Scripts/python.exe` (the `PY` line near the top);
on Linux or macOS change that line to `.venv/bin/python`. `B3` runs in its own environment with
`lightrag-hku==1.5.7`.

## The source texts

```bash
mkdir -p corpus/anne corpus/leagues
n=1; for id in 45 47 51 544 5343 3796; do
  curl -L -o corpus/anne/anne-v0$n.epub https://www.gutenberg.org/ebooks/$id.epub3.images; n=$((n+1)); done
curl -L -o corpus/leagues/twenty-thousand-leagues.epub https://www.gutenberg.org/ebooks/164.epub3.images
```

The paper uses volumes 1-5 of the Anne series. The header of each `config/series.<id>.yaml` names its source.

## Using it

```bash
wiki ingest -s anne --volumes 1-5       # parse the EPUBs ($0)
wiki gazetteer -s anne --volumes 1-5    # discover the cast
python scripts/run_series.py anne --upto 5   # every remaining stage, then the audits
wiki serve -s anne                      # browse the wiki
```

`USER_GUIDE.md` explains each stage, how to check its output, and how to add another series. The wikis the
paper evaluates are already under `dist/`; with the `wiki` extra installed,
`mkdocs serve -f dist/anne@v2/mkdocs.yml` renders one.

## Reproducing the paper's numbers

From the label files, with no model call:

```bash
python docs/eval/labelling_tools/derived_values.py   # recomputes the printed values from the labels; exit 1 on a difference
python scripts/papers/summary_stats.py               # mean, median, SD and range over cutoffs
```

From the source texts (generation is billed by the model provider; responses are not bit-identical to the
ones cached for the paper):

| Step | Command |
|---|---|
| NarrativeWiki, all five cutoffs | `python scripts/run_series.py anne --upto 5` |
| a comparison cell at cutoff t | `python scripts/baselines/run_baseline.py anne {X1,B1,B2,B4,X2} --upto t`, `python scripts/baselines/b3_lightrag.py anne --upto t --mode mix` |
| the treated text | `wiki decontaminate --series anne-decon --volumes 1-5` (or use `data/anne-decon/`) |
| assertion inventory and precision sample of a cell S | `python scripts/eval/assertion_inventory.py S --upto t`, `python scripts/eval/assertion_precision.py S --upto t --n 40 --population all` |
| disclosure candidates | `python scripts/eval/m4_tree.py S --upto t` |
| lexical screen | `python scripts/eval/artifact_exposure.py S` |
| labels to observations | `python scripts/eval/paper_observations.py S --system B5 --work anne`, then `python docs/eval/labelling_tools/apply_pair_rule.py S B5` |
| table values | `python scripts/eval/paper_numbers.py docs/eval/observations/<files>` |
| cost of a cell | `python scripts/eval/run_cost.py S --final` |

Each script's docstring states its inputs, outputs and options.
"""


def tree(top: str, keep=lambda rel: True) -> list[tuple[Path, str]]:
    base = ROOT / top
    return [(p, p.relative_to(ROOT).as_posix()) for p in sorted(base.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and keep(p.relative_to(base).as_posix())]


def keep_script(rel: str) -> bool:
    top, _, name = rel.rpartition("/")
    return (rel == "run_series.py" or top == "baselines" or (top == "papers" and name in PAPERS_SCRIPTS_IN)
            or (top == "eval" and Path(name).stem not in EVAL_SCRIPTS_OUT))


def keep_eval(rel: str) -> bool:
    *dirs, name = rel.split("/")
    if EVAL_DIRS_OUT & set(dirs) or EVAL_NAMES_OUT.search(name):
        return False
    return not NOT_REPORTED.search(rel)


def wanted() -> list[tuple[Path, str]]:
    files = tree("src", lambda r: ".egg-info" not in r) + tree("scripts", keep_script)
    files += tree("config", lambda r: r in ("extraction.yaml", "models.yaml")
                  or bool(re.match(r"series\.(anne|leagues|middlemarch)", r)))
    files += tree("docs/eval", keep_eval) + tree("docs/paper/tables", lambda r: r.endswith(".tex"))
    files += [(ROOT / n, n) for n in SINGLES]
    for d in sorted((ROOT / "dist").iterdir()):
        if d.is_dir() and WORKS.match(d.name):
            files += [(p, p.relative_to(ROOT).as_posix()) for p in sorted((d / "wiki").rglob("*.md"))]
            if (d / "mkdocs.yml").exists():
                files.append((d / "mkdocs.yml", f"dist/{d.name}/mkdocs.yml"))
    for s in ("anne-decon", "leagues-decon"):  # paid to produce and not regenerated identically
        files += tree(f"data/{s}/01_parsed")
    return files


def dangling_imports(files: list[tuple[Path, str]]) -> list[str]:
    """Kept Python files that import a script left out (scripts import each other by bare module name)."""
    kept = {Path(a).stem for _, a in files if a.endswith(".py")}
    gone = {p.stem for p in (ROOT / "scripts").rglob("*.py")} - kept
    rx = re.compile(r"^\s*(?:from|import)\s+(" + "|".join(sorted(gone)) + r")\b", re.M)
    return [f"{a} imports {m.group(1)}" for p, a in files if a.endswith(".py")
            for m in [rx.search(p.read_text(encoding="utf-8", errors="replace"))] if m]


def main() -> int:
    files = wanted()
    if broken := dangling_imports(files):
        print("LEFT-OUT SCRIPT STILL IMPORTED:", broken)
        return 1
    if OUT.exists() and any(OUT.iterdir()):
        readme = OUT / "README.md"  # never empty a directory this script did not build
        if not (readme.exists() and readme.read_text(encoding="utf-8").startswith(README.splitlines()[0])):
            print(f"refusing to overwrite {OUT}: not a tree this script built")
            return 1
        for p in OUT.iterdir():
            if p.name != ".git":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    bad, binary, size = [], [], 0
    texts = [(None, "README.md", README), (None, ".gitignore", GITIGNORE)]
    for src, arc in files:
        raw = src.read_bytes()
        try:
            texts.append((src, arc, raw.decode("utf-8")))
        except UnicodeDecodeError:
            binary.append(arc)
            texts.append((src, arc, raw))
    for _, arc, s in texts:
        dst = OUT / arc
        dst.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(s, str):
            for rx, rep in PATHS:
                s = rx.sub(rep, s)
            if arc == ".env.example":  # the default series (86) is a development series with no config here
                s = s.replace("NARRATIVEWIKI_SERIES=86", "NARRATIVEWIKI_SERIES=anne")
            if m := FORBIDDEN.search(s) or FORBIDDEN.search(arc):
                bad.append((arc, m.group(0)))
            s = s.encode("utf-8")
        dst.write_bytes(s)  # bytes, so line endings stay as they are in the source
        size += len(s)
    print(f"{OUT}: {len(texts)} files, {size / 1e6:.0f} MB")
    if binary:
        print("not text, copied unscanned:", binary)
    if bad:
        print("IDENTIFYING STRINGS LEFT:", bad[:20])
        return 1
    print("scan: no local path, user name, account or institution string in any text file or file name")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
