#!/bin/sh
# Compile the v3 paper (pdfLaTeX + BibTeX) into docs/paper/v3/_build, then copy the reading copy to
# docs/paper/NarrativeWiki-paper-v3.pdf. results.tex and refs.bib are shared with v1/v2 (parent dir).
#   main.pdf        reading copy: anonymous, no margin line numbers
#   submission.pdf  the same text with review line numbers
set -eu
cd "$(dirname "$0")"
mkdir -p _build
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) sep=';' ;; *) sep=':' ;; esac
run() { pdflatex "$@" -interaction=nonstopmode -halt-on-error -output-directory=_build > _build/run.out 2>&1 || { tail -30 _build/run.out; exit 1; }; }
run -jobname=main "\def\nwreading{1}\input{main}"
(cd _build && BIBINPUTS="..${sep}../..${sep}" BSTINPUTS="..${sep}" bibtex main > bib.out 2>&1)
run -jobname=main "\def\nwreading{1}\input{main}"
run -jobname=main "\def\nwreading{1}\input{main}"
echo "errors: $(grep -c '^!' _build/main.log)  undefined: $(grep -c 'undefined' _build/main.log)  overfull: $(grep -c 'Overfull' _build/main.log)  $(grep -o 'Output written.*pages' _build/main.log | grep -o '([0-9]* pages')"
if [ "${NW_SUBMISSION:-0}" = 1 ]; then
  cp _build/main.bbl _build/submission.bbl
  for i in 1 2 3; do run -jobname=submission main.tex; done
  echo "submission.pdf: $(grep -o '([0-9]* pages' _build/submission.log | tail -1)"
fi
cp _build/main.pdf ../NarrativeWiki-paper-v3.pdf
