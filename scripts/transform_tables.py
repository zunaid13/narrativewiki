"""Reapply numeric paper table styling after table generation; no result edits or API calls.

Run: .venv/Scripts/python.exe scripts/transform_tables.py
Scales use printed estimates, disclosure numerators, and total in/out tokens.
"""
from collections import defaultdict
from pathlib import Path
import re

PAPER = Path(__file__).resolve().parents[1] / "docs" / "paper"
LABELS = {
    "main", "full-results", "stats", "paired", "seeds", "kinds", "b4",
    "scope", "identity", "prefixv2", "efficiency", "builds", "decon", "decon-cells",
}
TABLE = re.compile(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", re.S)
RESULT = re.compile(r"\\res(?:pt)?\{([^}]+)\}")
SHADE = re.compile(r"\\nwshade\{[\d.]+\}")
NUMBER = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
TRANSPOSED = "% Systems across columns (transposed)."
VALUE_CELL = re.compile(r"\\best\{\\res\{[^}]+\}\}|\\res\{[^}]+\}")


def transpose_table(table, label):
    """Preserve whole cells, including counts/bold, while swapping comparison axes."""
    if label not in {"stats", "decon-cells"} or TRANSPOSED in table:
        return table
    start = table.index(r"\begin{tabular}")
    end = table.index(r"\end{tabular}", start) + len(r"\end{tabular}")
    rows, metric, cutoff = [], "", ""
    for line in table[start:end].splitlines():
        if "&" not in line or not RESULT.search(line):
            continue
        cells = [c.strip() for c in line.rstrip().removesuffix(r"\\").split("&")]
        if label == "stats":
            metric = cells[0] or metric
            rows.append((metric, cells[1], cells[2], cells[3:]))
        else:
            cutoff = cells[0] or cutoff
            rows.append((cutoff, cells[1], cells[2:]))
    systems = ["B1", "B2", "B3", "B4", "B5", "X1", "X2"]
    if label == "stats":
        blocks = []
        for metric in dict.fromkeys(row[0] for row in rows):
            data = {s: values for m, s, n, values in rows if m == metric}
            n = next(n for m, s, n, values in rows if m == metric)
            block = [r"\begin{minipage}[t]{0.49\textwidth}", r"\centering",
                     rf"\textbf{{{metric}}} ($n={n}$)\par\smallskip",
                     r"\begin{tabular}{@{}lrrrrrrr@{}}", r"\toprule",
                     "Statistic & " + " & ".join(systems) + r" \\", r"\midrule"]
            for i, statistic in enumerate(["Mean", "SD", "Median", "Min", "Max"]):
                block.append(statistic + " & " + " & ".join(data[s][i] if s in data else "--" for s in systems) + r" \\")
            block.extend([r"\bottomrule", r"\end{tabular}", r"\end{minipage}"])
            blocks.append("\n".join(block))
        body = ("\n" + r"\hfill" + "\n").join(blocks[:2])
        body += "\n" + r"\par\medskip" + "\n"
        body += ("\n" + r"\hfill" + "\n").join(blocks[2:4])
        body += "\n" + r"\par\medskip" + "\n" + blocks[4]
        table = table.replace(r"\centering\small", r"\centering\footnotesize")
        table = table.replace(r"\setlength{\tabcolsep}{6pt}", r"\setlength{\tabcolsep}{2pt}")
        # Preamble length changes require recomputing the replacement bounds.
        start = table.index(r"\begin{tabular}")
        end = table.index(r"\end{tabular}", start) + len(r"\end{tabular}")
    else:
        data = {(t, "B5" if s == r"\sys" else s): values for t, s, values in rows}
        body = [r"\begin{tabular}{@{}lcrrrrrrr@{}}", r"\toprule",
                "Metric & $t$ & " + " & ".join(systems) + r" \\", r"\midrule"]
        for i, metric in enumerate(["Recall", "Precision", "Citation suff.", "Disclosed"]):
            if i:
                body.append(r"\midrule")
            for t in "12345":
                name = rf"\multirow{{5}}{{*}}{{{metric}}}" if t == "1" else ""
                body.append(name + " & " + t + " & " + " & ".join(data[t, s][i] for s in systems) + r" \\")
        body.extend([r"\bottomrule", r"\end{tabular}"])
        body = "\n".join(body)
        table = table.replace(r"\centering\small", r"\centering\footnotesize")
        table = table.replace(r"\setlength{\tabcolsep}{3pt}", r"\setlength{\tabcolsep}{2pt}")
        start = table.index(r"\begin{tabular}")
        end = table.index(r"\end{tabular}", start) + len(r"\end{tabular}")
    return table[:start] + TRANSPOSED + "\n" + body + table[end:]


def style_transposed(table, label, results):
    """Refresh scales by result key rather than by the transposed cell position."""
    table = SHADE.sub("", table)
    groups = defaultdict(list)
    def scale_key(key):
        parts = key.split("-")
        if label == "stats":
            return parts[1], "sd" if parts[-1] == "sd" else "value"
        return parts[0], parts[2]  # metric and cutoff
    for match in VALUE_CELL.finditer(table):
        key = RESULT.search(match[0])[1]
        groups[scale_key(key)].append(point(match[0], results))
    def shade(match):
        key = RESULT.search(match[0])[1]
        values = groups[scale_key(key)]
        lo, hi = min(values), max(values)
        intensity = 5 if lo == hi else 5 + 30 * (point(match[0], results) - lo) / (hi - lo)
        return rf"\nwshade{{{intensity:.1f}}}" + match[0]
    return VALUE_CELL.sub(shade, table)


def point(cell, results):
    """Read the primary value, ignoring SD, intervals and denominators."""
    match = RESULT.search(cell)
    value = results[match[1]] if match else cell
    numbers = NUMBER.findall(value)
    if not numbers:
        return None
    if re.fullmatch(r"\s*[\d.]+\s+/\s+[\d.]+\s*", value):
        return sum(float(n) for n in numbers)
    return float(numbers[0].replace(",", ""))


def group(label, row, column, block, metric):
    """Keep units and comparison populations separate."""
    if label in {"stats", "paired"}:
        return metric, "sd" if column == (4 if label == "stats" else 3) else "value"
    if label in {"full-results", "decon-cells", "kinds"}:
        return block, column
    if label == "prefixv2":
        return metric,
    if label == "builds":
        return row,
    if label == "scope":
        if row < 12:
            return "pages",
        if row < 14:
            return "recall",
        if row < 16:
            return "precision",
        return row,
    return column,


def style_table(table, results):
    label_match = re.search(r"\\label\{tab:([^}]+)\}", table)
    if not label_match or label_match[1] not in LABELS:
        return table
    label = label_match[1]
    if TRANSPOSED in table:
        return style_transposed(table, label, results)
    table = SHADE.sub("", table)
    table = re.sub(r"\$\\pm\$\s*(\\res\{[^}]+\})", r"\\sdev{\1}", table)
    start = table.index(r"\begin{tabular}")
    end = table.index(r"\end{tabular}", start)
    lines = table[start:end].splitlines(keepends=True)
    entries, groups = [], defaultdict(list)
    block, row, metric, body = -1, 0, "", False
    for index, line in enumerate(lines):
        if r"\midrule" in line:
            block += 1
            body = True
            continue
        if not body or "&" not in line or not line.rstrip().endswith(r"\\"):
            continue
        cells = line.rstrip().removesuffix(r"\\").split("&")
        if cells[0].strip():
            metric = cells[0].strip()
        first = 2 if label in {"main", "full-results", "decon-cells", "decon", "prefixv2", "stats", "paired"} else 1
        if label == "stats":
            first = 3
        for column in range(first, len(cells)):
            value = point(cells[column], results)
            if value is None:
                continue
            key = group(label, row, column, block, metric)
            entries.append((index, column, value, key))
            if label != "efficiency" or row < 8:
                groups[key].append(value)
        row += 1
    edits = defaultdict(dict)
    for index, column, value, key in entries:
        lo, hi = min(groups[key]), max(groups[key])
        intensity = 5 if hi == lo else 5 + 30 * max(0, min(1, (value - lo) / (hi - lo)))
        edits[index][column] = rf"\nwshade{{{intensity:.1f}}}"
    for index, columns in edits.items():
        cells = lines[index].split("&")
        for column, shade in columns.items():
            cells[column] = " " + shade + cells[column].lstrip()
        lines[index] = "&".join(cells)
    return transpose_table(table[:start] + "".join(lines) + table[end:], label)


def main():
    results = dict(re.findall(r"\\declareres\{([^}]+)\}\{[^}]*\}\{([^}]*)\}",
                              (PAPER / "results.tex").read_text(encoding="utf-8")))
    for directory in ("tables", "appendix"):
        for path in sorted((PAPER / directory).glob("*.tex")):
            source = path.read_text(encoding="utf-8")
            updated = TABLE.sub(lambda m: style_table(m[0], results), source)
            if source != updated:
                path.write_text(updated, encoding="utf-8")
                print(path.relative_to(PAPER))


if __name__ == "__main__":
    main()
