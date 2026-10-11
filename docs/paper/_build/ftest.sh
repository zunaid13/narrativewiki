#!/bin/sh
# usage: sh _build/ftest.sh [top-fraction-of-page=0.62] [dpi=120]
cd "g:/UIU classes/Claude Code RAG+TKG pipeline/docs/paper" || exit 1
export PATH="/c/Users/pc/AppData/Local/Programs/MiKTeX/miktex/bin/x64:$PATH"
pdflatex -interaction=nonstopmode -output-directory=_build -jobname=figtest zz-figtest.tex > _build/ftest.out 2>&1
grep -n "^!" -A3 _build/figtest.log | head -24 | cut -c1-160; echo "overfull: $(grep -c Overfull _build/figtest.log)"
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" && FRAC="${1:-0.62}" DPI="${2:-120}" .venv/Scripts/python.exe - <<'PY'
import fitz, os
S = "C:/Users/pc/AppData/Local/Temp/claude/g--UIU-classes-Claude-Code-RAG-TKG-pipeline/1bdfefd0-f99c-4b88-8165-374ddf6e3d7a/scratchpad/"
d = fitz.open("docs/paper/_build/figtest.pdf")
p = d[0]; r = p.rect
p.get_pixmap(dpi=int(os.environ["DPI"]), clip=fitz.Rect(0, 0, r.width, r.height * float(os.environ["FRAC"]))).save(S + "figtest.png")
print(len(d), "page(s)")
PY
