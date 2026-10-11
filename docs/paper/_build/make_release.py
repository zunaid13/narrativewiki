"""Build the anonymised release archive that accompanies the submission. $0.

Run:  .venv/Scripts/python.exe docs/paper/_build/make_release.py
      -> dist/narrativewiki-anonymous-release.zip, and a scan report on stdout

Contents: code (src, scripts, tests, config, pyproject), the paper's sources and PDF, the evaluation
files of the public-domain works (gold facts, label files, inventories, disclosure candidates and
verdicts, cost summaries, freeze records, runners, the human-annotation package), the measurement
ledger and the change log, and the generated wikis (Markdown) of every system and cutoff.
Left out: the source texts (fetched from Project Gutenberg by id), the LLM cache and raw call logs
(2.4 GB; per-run cost summaries are included instead), evaluation files of the commercial series
used only in development, planning notes, and anything under version control metadata.
Text files are rewritten so that no local path, user name or institution appears; the scan at the
end fails loudly if one survives.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "dist" / "narrativewiki-anonymous-release.zip"
COMMERCIAL = re.compile(r"spice|overlord|bookworm|mushoku|eighty|(^|[^0-9])86([^0-9]|$)", re.I)
TEXT = {".py", ".md", ".sh", ".yaml", ".yml", ".json", ".jsonl", ".tex", ".bib", ".toml", ".txt", ".csv", ".html", ".sty", ".bst", ".example", ".cfg"}
PATHS = [(re.compile(r"[gG]:[/\\]+UIU classes[/\\]+Claude Code RAG\+TKG pipeline[/\\]*"), ""),
         (re.compile(r"/g/UIU classes/Claude Code RAG\+TKG pipeline/?"), ""),
         (re.compile(r"[cC]:[/\\]+Users[/\\]+pc[/\\]*"), "~/"),
         (re.compile(r"/c/Users/pc/"), "~/"),
         (re.compile(r"UIU classes"), "workspace"),
         # 2026-10-08: cloud account names, project ids and a city reached the archive through the ledger, the
         # runner scripts and the human-check notes (18, 16 and 3 occurrences); the scan below did not know them.
         (re.compile(r"adc_[A-Za-z0-9_-]+\.json"), "adc_ACCOUNT.json"),
         (re.compile(r"arnababir1?"), "account-a"),
         (re.compile(r"geminiprof2?"), "account-b"),
         (re.compile(r"min2web-nsyss-4"), "project-a"),
         (re.compile(r"\b309583960553\b"), "PROJECT-NUMBER"),
         (re.compile(r"Asia/Dhaka( \(UTC\+06:00\))?"), "local time"),
         # 2026-10-08: timestamps in the ledger and the human-check notes carried the local UTC offset (572 occurrences)
         (re.compile(r" ?\+06:?00"), "")]
FORBIDDEN = re.compile(r"zunaid|dhaka|uiu\.ac|UIU|Users[/\\]pc\b|arnababir|geminiprof|min2web|nsyss|\+06:?00", re.I)


def wanted() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for top in ("src", "scripts", "tests", "config"):
        files += [(p, p.relative_to(ROOT).as_posix()) for p in (ROOT / top).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    for name in ("pyproject.toml", ".env.example", ".gitattributes", "USER_GUIDE.md", "STRUCTURE.md", "docs/CONTRACTS.md", "docs/PROMPTS.md",
                 "docs/MEASUREMENTS.md"):
        if (ROOT / name).exists():
            files.append((ROOT / name, name))
    for p in (ROOT / "docs" / "eval").rglob("*"):
        if p.is_file() and p.name != "paper_review_2026-10-02.json":
            files.append((p, p.relative_to(ROOT).as_posix()))
    for p in (ROOT / "docs" / "paper").rglob("*"):
        if p.name.startswith("REVIEW_"):  # an internal review of the paper is not part of what reviewers are given
            continue
        if p.is_file() and ("_build" not in p.parts or p.name in ("build.sh", "overfull.py", "emptykeys.py", "sub.py")):
            files.append((p, p.relative_to(ROOT).as_posix()))
    files.append((ROOT / "docs" / "paper" / "_build" / "main.pdf", "NarrativeWiki-paper.pdf"))
    for d in sorted((ROOT / "dist").glob("anne*")) + sorted((ROOT / "dist").glob("oz*")):
        w = d / "wiki"
        if w.is_dir():
            files += [(p, "wikis/" + p.relative_to(ROOT / "dist").as_posix()) for p in w.rglob("*.md")]
    return [(p, a) for p, a in files if not COMMERCIAL.search(a.replace("docs/eval/", ""))
            or a.startswith(("src/", "tests/", "scripts/"))]


README = """# NarrativeWiki: anonymised release

Code, evaluation data and generated artifacts for "Evaluating Character Wikis at
Reader-Selected Narrative Cutoffs" (under review). NarrativeWiki is the reference implementation.

| Path | Holds |
|---|---|
| `NarrativeWiki-paper.pdf`, `docs/paper/` | the paper and its LaTeX sources; `docs/paper/results.tex` names the ledger row of every number |
| `src/`, `scripts/`, `config/`, `tests/`, `pyproject.toml` | the pipeline, the comparison systems, the evaluation tools and their settings; `USER_GUIDE.md` gives the commands |
| `docs/PROMPTS.md`, `src/narrativewiki/**` | prompt templates; logged exchange excerpts are in the paper appendix |
| `docs/eval/parametric/`, `docs/eval/dataset_card_20261010.json` | gold facts with evidence identifiers; dataset sizes, units and illustrative records (evaluation selects evidence volumes 1-5) |
| `docs/eval/precision/`, `recall_hand/`, `leak_audit/`, `inventory/` | label files (precision samples with notes and citation verdicts, recall, disclosure verdicts and the candidate sentences read) and the assertion inventories |
| `docs/eval/human/`, `human_check/`, `agreement/` | annotation packets and keys, the accepted AI-assisted reference, supplied reviewer CSVs and accompanying records, provenance hashes, aligned decisions and recomputed agreement; original summary transcriptions are retained |
| `docs/eval/m4_seeded/`, `a1/`, `cost/`, `freeze/`, `runners/` | seeded-disclosure test, construction-scope comparison, per-run cost summaries, freeze records, the runner scripts |
| `docs/MEASUREMENTS.md`, `docs/eval/CHANGES.md` | the measurement ledger (one row per reported value, with its command) and the log of changes that moved a number |
| `wikis/` | the generated wiki of every system at every cutoff (Markdown) |

Not included: the source texts (Project Gutenberg eBooks 45, 47, 51, 544, 5343; fetch by id), the model
response cache and raw call logs (2.4 GB), and files of series used only in development. Primary AI evaluation labels were
finalized by Claude Opus 5.5 after evidence review, as the paper states; historical `reader`
fields preserve drafting provenance. Human authorship of the supplied final reviewer labels
is maintainer-reported; conflicting archival metadata is retained in the provenance record.
Agreement is reproduced against an accepted review snapshot, not a verified blind first pass.
Current primary-matrix sizes and easier/harder examples are documented
in the corpus appendix; the difficulty descriptions are illustrative, not measured strata.
Local paths were replaced by relative ones.
"""


def main() -> int:
    files = wanted()
    bad = []
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("README.md", README)
        for p, arc in files:
            if arc.startswith("docs/eval/agreement/human_review/reviewer_") and p.name in {
                "answers.csv", "responses.jsonl", "supplied_original_metadata.json"
            }:
                # These are immutable evidence: text newline rewriting invalidates their hashes.
                data = p.read_bytes()
                match = FORBIDDEN.search(data.decode("utf-8", errors="replace"))
                if match:
                    bad.append((arc, match.group(0)))
                z.writestr(arc, data)
                continue
            if p.suffix.lower() in TEXT:
                s = p.read_text(encoding="utf-8", errors="replace")
                for rx, rep in PATHS:
                    s = rx.sub(rep, s)
                if FORBIDDEN.search(s):
                    bad.append((arc, FORBIDDEN.search(s).group(0)))
                z.writestr(arc, s)
            else:
                z.write(p, arc)
    print(f"{OUT.relative_to(ROOT)}: {len(files) + 1} files, {OUT.stat().st_size / 1e6:.1f} MB")
    if bad:
        print("IDENTIFYING STRINGS LEFT:", bad[:20])
        return 1
    print("scan: no local path, user name or institution string in any text file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
