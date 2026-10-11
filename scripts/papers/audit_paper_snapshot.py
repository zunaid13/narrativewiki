"""Read-only PDF/source checks for the 2026-10-09 manuscript review.

Run from the repo root: python scripts/papers/audit_paper_snapshot.py
No generation, provider calls, or manuscript writes. Uses installed PyMuPDF.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "docs" / "paper"


def inspect_pdf(path: Path) -> dict:
    doc = fitz.open(path)
    return {
        "file": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "pages": len(doc),
        "page_8_has_conclusion": "Conclusion" in doc[7].get_text(),
        # PDF reading order keeps the heading before margin rulers in review mode.
        "page_9_starts_limitations": doc[8].get_text().lstrip().startswith("Limitations"),
        "creation_date": doc.metadata.get("creationDate"),
    }


def main() -> None:
    pdf = PAPER / "NarrativeWiki-paper.pdf"
    doc = fitz.open(pdf)
    # The supplied paper's abstract is in two blocks of the left column.
    # This is snapshot-specific; do not reuse its coordinates for another layout.
    blocks = [b[4] for b in doc[0].get_text("blocks") if b[0] < 100 and 240 < b[1] < 590]
    abstract = re.sub(r"-\s*\n\s*", "", "".join(blocks))
    abstract = re.sub(r"\s+", " ", abstract).strip()
    bib = (PAPER / "refs.bib").read_text(encoding="utf-8")
    result = {
        "run_id": "paper-review-20261009",
        "reviewed_pdf": inspect_pdf(pdf),
        "abstract_whitespace_tokens_after_dehyphenation": len(abstract.split()),
        "abstract": abstract,
        "bibliography_entries": len(re.findall(r"(?m)^@\w+\{", bib)),
        "bibliography_keys": re.findall(r"(?m)^@\w+\{([^,]+)", bib),
    }
    submission = ROOT / "dist" / "NarrativeWiki-paper-submission.pdf"
    if submission.exists():
        result["submission_pdf"] = inspect_pdf(submission)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
