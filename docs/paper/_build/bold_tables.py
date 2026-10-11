"""bold_tables.py: put the values that carry each table's finding in bold, from the values in results.tex. $0.

Run (from the repository root, after the fill scripts and scripts/papers/summary_stats.py, which
rewrites tables/t-stats.tex without bold):
  .venv/Scripts/python.exe docs/paper/_build/bold_tables.py

Maintainer 2026-10-08: "for every single table, bold out the important values (like minimum or
maximum) ... depending on the context". A rule names a table by its label, the keys of a group by
a regular expression, and what to mark in the group:
  max / min   the highest / lowest leading number of the group (every tie is marked)
  max1        the highest, only when the group is not all equal (a pair of builds that tie has no mark)
  nonzero     every value whose leading number is above zero (disclosure counts: a zero is the
              common case and the found disclosures are the reading)
  all         every key of the group (a row or cell chosen by hand, with the reason beside it)
Only \\res / \\respt cells inside that table's tabular are touched, wrapped in \\best{...}
(macros.tex). The step is idempotent: it removes its own marks first, so a value that moves takes
the bold with it. Tables of typed numerals (tab:seeds, tab:kinds) carry \\best{} by hand, and
tables without values (metric list, baseline settings, casebook, related work) have none.
"""
from __future__ import annotations

import re
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
B = "B1|B2|B3|B5"
BD = "B1|B2|B3|B4|B5"
STAGES = "gazetteer|scenes|extract|infobox|graph|verify|synth|site"
RULES: list[tuple[str, str, str, str]] = [  # file, table label, key regex (full match), mark
    ("tables/t1-corpus.tex", "tab:corpus", r"T1-anne-(paras|words|chapters)", "all"),  # the totals row
    ("tables/t2-main.tex", "tab:main", rf"M1-anne-avg-({B})", "max"),
    ("tables/t2-main.tex", "tab:main", rf"M3-anne-avg-({B})", "max"),
    ("tables/t2-main.tex", "tab:main", rf"M8-anne-avg-({B})", "max"),
    ("tables/t2-main.tex", "tab:main", r"M4-anne-total-.*", "nonzero"),
    ("tables/t2-main.tex", "tab:main", rf"ND-anne-avg-({B})", "max"),
    ("tables/t2-main.tex", "tab:main", rf"TOK-anne-({B})", "min"),  # by input tokens, the leading number
    ("tables/t2b-decon.tex", "tab:decon", rf"M1-annedecon-avg-({BD})", "max"),
    ("tables/t2b-decon.tex", "tab:decon", r"M1-annedecon-diff-.*", "min"),  # the largest loss
    ("tables/t2b-decon.tex", "tab:decon", rf"M3-annedecon-avg-({BD})", "max"),
    ("tables/t2b-decon.tex", "tab:decon", rf"M8-annedecon-avg-({BD})", "max"),
    ("tables/t2b-decon.tex", "tab:decon", r"M4-annedecon-total-.*", "nonzero"),
    ("tables/t-paired.tex", "tab:paired", r"STAT-M1-B5-minus-.*-mean", "max"),
    ("tables/t-paired.tex", "tab:paired", r"STAT-M1-B5-minus-.*-mean", "min"),
    ("tables/t-paired.tex", "tab:paired", r"STAT-M4-B5-minus-.*-mean", "min"),
    ("tables/t-stats.tex", "tab:stats", r"STAT-M1-B\d-mean", "max"),
    ("tables/t-stats.tex", "tab:stats", r"STAT-M3-B\d-mean", "max"),
    ("tables/t-stats.tex", "tab:stats", r"STAT-M8-B\d-mean", "max"),
    ("tables/t-stats.tex", "tab:stats", r"STAT-M4-..-mean", "nonzero"),
    ("tables/t-stats.tex", "tab:stats", r"STAT-N-B\d-mean", "max"),
    ("appendix/g-additional-results.tex", "tab:b4", r"M1-anne-t\d-B4", "max"),
    ("appendix/g-additional-results.tex", "tab:b4", r"M1-anne-t\d-B4", "min"),
    ("appendix/g-additional-results.tex", "tab:scope", r"A1-t\d-classes-anchored", "all"),  # the finding of 6.3
    ("appendix/g-additional-results.tex", "tab:identity", r"ID-anne-t\d", "max"),
    ("appendix/g-additional-results.tex", "tab:identity", r"ID-anne-strict-t\d", "max"),
    ("appendix/g-additional-results.tex", "tab:identity", r"ID-anne-mentions-t\d", "min"),
    ("appendix/g-additional-results.tex", "tab:efficiency", rf"T5-({STAGES})-calls", "max"),
    ("appendix/g-additional-results.tex", "tab:efficiency", rf"T5-({STAGES})-in", "max"),
    ("appendix/g-additional-results.tex", "tab:efficiency", rf"T5-({STAGES})-out", "max"),
    # tab:builds: the better of the two builds, where a direction exists
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-M1-first|M1-anne-avg-B5", "max"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-M3-first|M3-anne-avg-B5", "max"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-M3L-first|REV-M3L", "max"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-M3A-first|REV-M3A", "max"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-M8-first|M8-anne-avg-B5", "max"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-CITE-first|CITE-anne-B5", "max"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-M4-first|M4-anne-total-B5", "min"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-SCREEN-first|SCREEN-anne-B5", "min"),
    ("appendix/g-additional-results.tex", "tab:builds", r"REV-pair", "all"),  # 75 of 102 against 76 of 116
]
for t in range(1, 6):
    for m in ("M1", "M3", "M8", "N"):
        RULES.append(("tables/e-full-results.tex", "tab:full-results", rf"{m}-anne-t{t}-({B})", "max"))
        if m != "N":
            RULES.append(("tables/e-decon-cells.tex", "tab:decon-cells", rf"{m}-annedecon-t{t}-({BD})", "max"))
    for scope in ("M1", "M3"):  # tab:scope: the higher of the prefix and the full build
        if t in (2, 3):
            RULES.append(("appendix/g-additional-results.tex", "tab:scope", rf"A1-t{t}-{scope}-(prefix|full)", "max"))
for t in range(1, 5):  # tab:prefixv2: the higher of the full and the prefix-discovered build
    for m in ("M1", "M3", "M8"):
        RULES.append(("appendix/g-additional-results.tex", "tab:prefixv2", rf"{m}-anne-t{t}-B5|PX-anne-t{t}-{m}", "max1"))
RULES.append(("appendix/g-additional-results.tex", "tab:prefixv2", r"M4-anne-t[1-4]-B5|PX-anne-t[1-4]-M4", "nonzero"))
RULES.append(("tables/e-full-results.tex", "tab:full-results", r"M4-anne-t\d-.*", "nonzero"))
RULES.append(("tables/e-decon-cells.tex", "tab:decon-cells", r"M4-annedecon-t\d-.*", "nonzero"))

STATS_NOTE = " Bold: the best mean of each metric among B1--B5, and each non-zero mean disclosure rate."
CELL = re.compile(r"\\res(?:pt)?\{([^}]*)\}")
MARKED = re.compile(r"\\best\{(\\res(?:pt)?\{[^}]*\})\}")


def values() -> dict[str, str]:
    out = {}
    for line in (PAPER / "results.tex").read_text(encoding="utf-8").split("\n"):
        m = re.match(r"\\declareres\{([^}]*)\}\{.*?\}\{(.*)\}(?:%.*)?$", line)
        if m:
            out[m.group(1)] = m.group(2).split("}%")[0]
    return out


def number(v: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", "").replace("$", ""))
    return float(m.group()) if m else None


def main() -> None:
    val = values()
    marks: dict[tuple[str, str], set[str]] = {}
    for file, label, rx, how in RULES:
        text = (PAPER / file).read_text(encoding="utf-8")
        end = text.index(f"\\label{{{label}}}")
        start = text.rindex("\\begin{tabular}", 0, end)
        keys = [k for k in dict.fromkeys(CELL.findall(text[start:end])) if re.fullmatch(rx, k)]
        nums = {k: number(val[k]) for k in keys if k in val and number(val[k]) is not None}
        assert nums, (label, rx)
        best = {"max": max, "max1": max, "min": min}[how](nums.values()) if how in ("max", "max1", "min") else None
        if how == "max1" and len(set(nums.values())) == 1:
            marks.setdefault((file, label), set())
            continue
        marks.setdefault((file, label), set()).update(
            k for k, x in nums.items() if how == "all" or (how == "nonzero" and x > 0) or x == best)
    for (file, label), keys in sorted(marks.items()):
        path = PAPER / file
        text = path.read_text(encoding="utf-8")
        end = text.index(f"\\label{{{label}}}")
        start = text.rindex("\\begin{tabular}", 0, end)
        block = MARKED.sub(r"\1", text[start:end])
        block = CELL.sub(lambda m: f"\\best{{{m.group(0)}}}" if m.group(1) in keys else m.group(0), block)
        tail = text[end:]
        if label == "tab:stats" and STATS_NOTE not in text:  # the generator rewrites this caption
            close = block.rindex("}")
            block = block[:close] + STATS_NOTE + block[close:]
        path.write_text(text[:start] + block + tail, encoding="utf-8", newline="\n")
        print(f"{label}: {len(keys)} cells")


if __name__ == "__main__":
    main()
