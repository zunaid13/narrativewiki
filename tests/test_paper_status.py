"""Paper structure checks distinguish literal model exchanges from manuscript TeX."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "paper_status", Path(__file__).parents[1] / "scripts/papers/paper_status.py"
)
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)


def test_prompt_payload_does_not_become_manuscript_structure():
    tex = r"""\newtcblisting{nwprompt}[3][]{listing only}
\section{Actual section}
\begin{nwprompt}{Color}{Model output}
{"elided_json": {
Literal \input{not-a-file} and \cite{not-a-reference}, 50% of a payload.
\end{nwprompt}
\input{sections/06-results}
"""
    cleaned = ps.strip_comments(tex)
    assert "elided_json" not in cleaned
    assert "not-a-file" not in cleaned
    assert "not-a-reference" not in cleaned
    assert r"\section{Actual section}" in cleaned
    assert r"\input{sections/06-results}" in cleaned


def test_real_tex_errors_and_escaped_percent_remain_visible():
    tex = r"""\begin{lstlisting}
literal } \input{example}
\end{lstlisting}
\section{Unclosed
\cite{real-reference} % ignore \cite{comment}
50\% supported
"""
    cleaned = ps.strip_comments(tex)
    assert r"\section{Unclosed" in cleaned
    assert r"\cite{real-reference}" in cleaned
    assert r"\cite{comment}" not in cleaned
    assert r"50\% supported" in cleaned
    assert r"\input{example}" not in cleaned
