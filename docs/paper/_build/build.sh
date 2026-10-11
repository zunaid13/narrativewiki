#!/bin/sh
# Compile the paper the way Overleaf does (pdfLaTeX + BibTeX), into docs/paper/_build.
#   main.pdf        the reading copy: anonymous, no margin line numbers
#   submission.pdf  the same text with the review line numbers the venue expects in a submitted file
set -eu
# NW_MAIN=main_v2 builds the version-2 paper instead (main_v2.pdf, submission_v2.pdf).
m="${NW_MAIN:-main}"
sub="submission${m#main}"
cd "$(dirname "$0")/.."
mkdir -p _build
# Optional arguments are forwarded to pdfLaTeX (e.g. -disable-installer on MiKTeX).
pdflatex "$@" -interaction=nonstopmode -halt-on-error -output-directory=_build -jobname="$m" "\def\nwreading{1}\input{$m}" > _build/run1.out 2>&1
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) tex_path_sep=';' ;;
  *) tex_path_sep=':' ;;
esac
(cd _build && BIBINPUTS="..${tex_path_sep}" BSTINPUTS="..${tex_path_sep}" bibtex "$m" > bib.out 2>&1)
pdflatex "$@" -interaction=nonstopmode -halt-on-error -output-directory=_build -jobname="$m" "\def\nwreading{1}\input{$m}" > _build/run2.out 2>&1
pdflatex "$@" -interaction=nonstopmode -halt-on-error -output-directory=_build -jobname="$m" "\def\nwreading{1}\input{$m}" > _build/run3.out 2>&1
echo "errors: $(grep -c '^!' "_build/$m.log")  undefined refs/cites: $(grep -c 'undefined' "_build/$m.log")  overfull: $(grep -c 'Overfull' "_build/$m.log")  pages: $(grep -o 'Output written.*' "_build/$m.log" | head -1)"
cp "_build/$m.bbl" "_build/$sub.bbl"
for i in 1 2 3; do pdflatex "$@" -interaction=nonstopmode -halt-on-error -output-directory=_build -jobname="$sub" "$m.tex" > _build/sub$i.out 2>&1; done
echo "$sub.pdf (with line numbers): errors $(grep -c '^!' "_build/$sub.log"), $(grep -o '([0-9]* pages' "_build/$sub.log" | tail -1))"
