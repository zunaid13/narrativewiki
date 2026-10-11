"""[32] One table of the multi-cutoff recall/leak curves across series (tool readings).

Run:  .venv/Scripts/python.exe scripts/eval/curve_table.py spice-and-wolf overlord bookworm middlemarch

Reads docs/eval/pipeline_leak_<series>_v<t>.json (scripts/eval/pipeline_page_leak.py). These are
MiniCheck/lexical readings, not verdicts: every leak positive, and the recall rows reported as
headline numbers, are read by hand before they go in MEASUREMENTS.md.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
print("| series | t | control facts | recall (tool) | future facts | leak (tool, either) | page words |")
print("|---|---|---|---|---|---|---|")
for series in sys.argv[1:]:
    for t in range(1, 9):
        f = ROOT / "docs" / "eval" / f"pipeline_leak_{series}_v{t}.json"
        if not f.is_file():
            continue
        s = json.loads(f.read_text(encoding="utf-8"))["summary"][0]
        print(f"| {series} | {t} | {s['n_control']} | {s['control_recall']} | {s['n_future']} | "
              f"{s['future_leak_rate_either']} | {s['page_words']} |")
