"""Write figures/f0-teaser-v2.pdf: the teaser with two labels removed from its text layer.

The teaser has no editable source. Version 2 of the paper re-letters the right-hand heading
("Our solution: NarrativeWiki") and the badge ("No spoilers") with a TikZ overlay
(docs/paper/sections_v2/01-introduction.tex); covering them is not enough, because the words
stay in the PDF text layer and come out in any text extraction. This removes the glyphs
themselves and leaves the artwork. Version 1 keeps figures/f0-teaser.pdf untouched.

    .venv/Scripts/python.exe scripts/papers/redact_teaser_v2.py
"""
from pathlib import Path

import fitz

FIG = Path(__file__).resolve().parents[2] / "docs" / "paper" / "figures"
REMOVE = ("Our solution: NarrativeWiki", "No spoilers")

doc = fitz.open(FIG / "f0-teaser.pdf")
page = doc[0]
for phrase in REMOVE:
    hits = page.search_for(phrase)
    assert hits, f"not found in the teaser: {phrase!r}"
    for rect in hits:
        page.add_redact_annot(rect, fill=False)  # no white box: the badge keeps its pill
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
doc.save(FIG / "f0-teaser-v2.pdf", garbage=4, deflate=True)

left = fitz.open(FIG / "f0-teaser-v2.pdf")[0].get_text()
for word in ("solution", "NarrativeWiki", "spoilers"):
    assert word not in left, f"still in the text layer: {word}"
print("wrote", FIG / "f0-teaser-v2.pdf")
