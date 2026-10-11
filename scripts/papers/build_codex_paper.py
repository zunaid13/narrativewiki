"""Build the self-contained Codex manuscript and check its submission mechanics.

Requires existing pdfLaTeX/BibTeX and PyMuPDF; installs nothing, calls no model.
Run from any working directory with the repository's existing Python environment.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper_codex"
BUILD = PAPER / "_build"
REPORT = PAPER / "analysis" / "build-validation.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def uncomment(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def braced(text: str, at: int) -> tuple[str, int]:
    assert text[at] == "{"
    depth, start, at = 1, at + 1, at + 1
    while at < len(text):
        if text[at] == "\\":
            at += 2
            continue
        if text[at] == "{":
            depth += 1
        elif text[at] == "}":
            depth -= 1
            if not depth:
                return text[start:at], at + 1
        at += 1
    raise ValueError("Unclosed result-registry field")


def source_checks() -> dict:
    sources: dict[Path, str] = {}

    def visit(path: Path):
        path = path.resolve()
        if path in sources:
            return
        if not path.is_relative_to(PAPER.resolve()):
            raise ValueError(f"Source outside standalone paper: {path}")
        text = uncomment(path.read_text(encoding="utf-8"))
        sources[path] = text
        for name in re.findall(r"\\input\{([^}]+)\}", text):
            visit(PAPER / (name if Path(name).suffix else name + ".tex"))

    visit(PAPER / "main.tex")
    registry = {}
    text = sources[PAPER / "results.tex"]
    for match in re.finditer(r"\\declareres(?=\{)", text):
        at, fields = match.end(), []
        for _ in range(3):
            value, at = braced(text, at)
            fields.append(value)
        key, description, value = fields
        if key in registry:
            raise ValueError(f"Duplicate result key: {key}")
        registry[key] = value
    prose = "\n".join(t for p, t in sources.items() if p.name not in {"macros.tex", "results.tex"})
    used = set(re.findall(r"\\res(?:pt)?\{([^}]+)\}", prose))
    missing = sorted(used - registry.keys())
    empty = sorted(k for k in used if k in registry and not registry[k])
    if missing or empty:
        raise ValueError(f"Missing result keys {missing}; unmeasured printed keys {empty}")
    bib = (PAPER / "refs.bib").read_text(encoding="utf-8")
    keys = re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib)
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate bibliography keys")
    cites = {k.strip() for block in re.findall(r"\\cite\w*(?:\[[^]]*\])*\{([^}]+)\}", prose)
             for k in block.split(",")}
    if cites - set(keys):
        raise ValueError(f"Missing citations: {sorted(cites - set(keys))}")
    if re.search(r"\\(?:TBD|TODO|CITE)\{", prose):
        raise ValueError("Unfinished authoring placeholders in printed sources")
    abstract = sources[PAPER / "sections" / "00-abstract.tex"]
    abstract = abstract.replace(r"\sys", "NarrativeWiki").replace(r"\%", "%")
    abstract = re.sub(r"\\(?:begin|end)\{abstract\}", "", abstract)
    words = len(abstract.split())
    if words > 200:
        raise ValueError(f"Abstract has {words} whitespace words; maximum 200")
    return {"abstract_words": words, "included_tex_files": len(sources),
            "used_result_keys": len(used), "bibliography_entries": len(keys),
            "cited_entries": len(cites), "unmeasured_used_keys": empty,
            "source_sha256": {p.relative_to(PAPER).as_posix(): sha(p) for p in sorted(sources)}}


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"{command[0]} failed\n{result.stdout[-6000:]}\n{result.stderr[-2000:]}")


def arrange_supplement_tables() -> None:
    """Place unchanged generated tables side by side, retaining their captions/labels."""
    for target, names in (("t-review-panels", ("t-audit", "t-audit-draft")),
                          ("t-diagnostic-panels", ("t-paired", "t-b4"))):
        panels = []
        for name in names:
            text = (PAPER / "tables" / (name + ".tex")).read_text(encoding="utf-8")
            body = re.sub(r"\\begin\{table\*?\}\[t\]", "", text, count=1)
            body = re.sub(r"\\end\{table\*?\}", "", body, count=1).strip()
            panels.append("\\begin{minipage}[t]{0.48\\textwidth}\n" + body + "\n\\end{minipage}")
        merged = ("% Generated layout wrapper by build_codex_paper.py; counts remain unchanged.\n"
                  "\\begin{table*}[t]\n" + "\n\\hfill\n".join(panels) + "\n\\end{table*}\n")
        (PAPER / "tables" / (target + ".tex")).write_text(merged, encoding="utf-8")


def compile_copy(job: str, submission: bool) -> dict:
    env = os.environ.copy()
    for variable in ("BIBINPUTS", "BSTINPUTS"):
        env[variable] = str(PAPER) + os.pathsep + env.get(variable, "") + os.pathsep
    expression = "submission.tex" if submission else "main.tex"
    command = ["pdflatex", "-halt-on-error", "-interaction=nonstopmode",
               "-output-directory=" + str(BUILD), "-jobname=" + job, expression]
    run(command, PAPER, env)
    run(["bibtex", job], BUILD, env)
    run(command, PAPER, env)
    run(command, PAPER, env)
    log = (BUILD / (job + ".log")).read_text(encoding="utf-8", errors="replace")
    aux = (BUILD / (job + ".aux")).read_text(encoding="utf-8", errors="replace")
    bad = re.findall(r"(?:LaTeX|Package natbib) Warning: [^\n]*(?:undefined|multiply defined)[^\n]*", log)
    overfull = re.findall(r"Overfull \\[hv]box \(([^)]+)\)[^\n]*", log)
    label_pages = {name: int(page) for name, page in re.findall(
        r"\\newlabel\{([^}]+)\}\{\{[^}]*\}\{(\d+)\}", aux)}
    main_labels = ["sec:intro", "sec:task", "sec:method", "sec:setup", "sec:results",
                   "sec:discussion", "sec:conclusion", "fig:boundary", "tab:main",
                   "tab:gold-sensitivity", "tab:surface-samples"]
    omitted = sorted(set(main_labels) - label_pages.keys())
    if omitted:
        raise ValueError(f"Main labels missing from compiled file: {omitted}")
    final_main_page = max(label_pages[k] for k in main_labels)
    pdf = BUILD / (job + ".pdf")
    with fitz.open(pdf) as document:
        texts = [page.get_text() for page in document]
        pages = len(document)
        metadata = document.metadata
    data = {"pdf_pages": pages, "last_main_content_page": final_main_page,
            "limitations_page": label_pages["sec:limitations"],
            "ethics_page": label_pages["sec:ethics"], "review_line_numbers": submission,
            "unresolved_warnings": bad, "overfull_boxes": overfull,
            "pdf_sha256": sha(pdf), "metadata": metadata,
            "main_label_pages": {k: label_pages[k] for k in main_labels}}
    if final_main_page > 8 or bad or overfull:
        raise ValueError(f"Submission mechanics failed for {job}: {json.dumps(data, ensure_ascii=False)}")
    if data["limitations_page"] <= final_main_page:
        raise ValueError("Limitations must follow the main paper on a new page")
    if re.search(r"\?\?", "\n".join(texts)):
        raise ValueError("Unresolved reference markers in PDF")
    target = PAPER / ("Reader-Cutoff-Wikis-submission.pdf" if submission else "Reader-Cutoff-Wikis.pdf")
    shutil.copyfile(pdf, target)
    return data


def archive() -> dict:
    target = PAPER / "Reader-Cutoff-Wikis-source.zip"
    # Deliberately explicit: no local review metadata, measured label records or scratch builds.
    candidates = [PAPER / x for x in ("main.tex", "submission.tex", "macros.tex", "results.tex", "refs.bib",
                                     "acl.sty", "acl_natbib.bst", "README.md")]
    for folder in ("sections", "figures", "tables", "appendix"):
        candidates.extend(sorted((PAPER / folder).glob("*.tex")))
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in candidates:
            bundle.write(path, path.relative_to(PAPER).as_posix())
    return {"source_archive_files": len(candidates), "source_archive_sha256": sha(target)}


def main() -> None:
    for executable in ("pdflatex", "bibtex"):
        if shutil.which(executable) is None:
            raise SystemExit(f"Existing {executable} is required; no automatic installation")
    BUILD.mkdir(exist_ok=True)
    arrange_supplement_tables()
    result = {"run_id": "codex-paper-build-2026-10-09", "source": source_checks()}
    result["reading"] = compile_copy("reading", False)
    result["submission"] = compile_copy("submission", True)
    result.update(archive())
    result["validation_passed"] = True
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation_passed": True, "abstract_words": result["source"]["abstract_words"],
                      "main_pages": result["reading"]["last_main_content_page"],
                      "total_pages": result["reading"]["pdf_pages"],
                      "source_archive_files": result["source_archive_files"]}))


if __name__ == "__main__":
    main()
