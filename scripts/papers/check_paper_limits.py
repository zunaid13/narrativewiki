"""Page-limit and abstract-length check for a built paper PDF. No model calls.

    .venv/Scripts/python.exe scripts/papers/check_paper_limits.py docs/paper/_build/submission_v2.pdf

Prints the abstract word count (limit 200), the page on which Limitations starts (the main
text must end by page 8) and the text that spills onto page 9 before it, if any.
"""
import re
import sys

import fitz

doc = fitz.open(sys.argv[1])
first = doc[0].get_text()
abstract = first.split("Abstract", 1)[1].split("1\nIntroduction", 1)[0]
abstract = re.sub(r"^\d{3}\n", "", abstract, flags=re.M)  # review line numbers
# A line-end hyphen is either a break inside a word or a real compound ("closed-\nbook"), and
# the PDF does not say which: the true count lies between the two figures.
low = len(abstract.replace("-\n", "").split())
print(f"abstract words: {low} to {len(abstract.split())} (limit 200)")

for number, page in enumerate(doc, start=1):
    text = page.get_text()
    if re.search(r"^Limitations$", text, flags=re.M):
        before = re.sub(r"^\d{3}$\n?", "", text.split("Limitations", 1)[0], flags=re.M).strip()
        print("Limitations starts on page", number)
        break
    if number == 9:
        spill = re.sub(r"^\d{3}$\n?", "", text, flags=re.M).strip()
        print(f"page 9 holds main text ({len(spill.splitlines())} lines):")
        print(spill[:1500])
