"""Verify the table transpose against a Git checkpoint, including rendered size.

Run: .venv/Scripts/python.exe scripts/papers/check_table_layout.py --baseline b646b2b
Uses existing PyMuPDF; does not build, change results, or call a model.
"""
import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import re
import subprocess

import fitz

ROOT = Path(__file__).resolve().parents[2]


def at_commit(commit, path):
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def table_height(document, number):
    for page in document:
        caption = page.search_for(f"Table {number}:")
        if not caption:
            continue
        upper = caption[0].y0
        lower = max((b[3] for b in page.get_text("blocks")
                     if re.search(r"Table \d+:", b[4]) and b[3] < upper), default=0)
        rules = [drawing["rect"] for drawing in page.get_drawings()
                 if drawing["rect"].height < 1 and drawing["rect"].width > 100
                 and lower < drawing["rect"].y0 < upper]
        return max(r.y1 for r in rules) - min(r.y0 for r in rules)
    raise ValueError(f"Table {number} caption missing")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("styling", ROOT / "scripts/transform_tables.py")
    styling = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(styling)
    results = dict(re.findall(r"\\declareres\{([^}]+)\}\{[^}]*\}\{([^}]*)\}",
                              (styling.PAPER / "results.tex").read_text(encoding="utf-8")))
    for name in ["t-stats", "e-decon-cells", "t-paired"]:
        path = f"docs/paper/tables/{name}.tex"
        before = at_commit(args.baseline, path).decode("utf-8")
        after = (ROOT / path).read_text(encoding="utf-8")
        assert Counter(styling.RESULT.findall(before)) == Counter(styling.RESULT.findall(after)), path
        bold = r"\\best\{\\res\{([^}]+)\}\}"
        assert Counter(re.findall(bold, before)) == Counter(re.findall(bold, after)), path
        assert styling.TABLE.sub(lambda m: styling.style_table(m[0], results), after) == after, path
        print(f"PASS {name}: preserved result keys/bold; idempotent styling")
    for name in ["main", "submission"]:
        log = (styling.PAPER / "_build" / f"{name}.log").read_text(encoding="latin1")
        assert not re.search(r"^!", log, re.M) and "undefined" not in log and "Overfull" not in log
        document = fitz.open(styling.PAPER / "_build" / f"{name}.pdf")
        assert "Conclusion" in document[7].get_text() and "Limitations" in document[8].get_text()
        print(f"PASS {name}: {len(document)} pages; clean log; conclusion p8, Limitations p9")
    before = fitz.open(stream=at_commit(args.baseline, "docs/paper/NarrativeWiki-paper.pdf"), filetype="pdf")
    after = fitz.open(styling.PAPER / "_build" / "main.pdf")
    for number in [7, 20]:
        old, new = table_height(before, number), table_height(after, number)
        assert new < old, number
        print(f"Table {number}: {old:.1f} -> {new:.1f} pt, {100 * (1 - new / old):.1f}% shorter")


if __name__ == "__main__":
    main()
