"""Attribute each Overfull hbox in _build/main.log to the .tex file being read when it was reported."""
import pathlib
import re

log = (pathlib.Path(__file__).parent / "main.log").read_text(encoding="latin-1")
for m in re.finditer(r"Overfull .hbox \(([\d.]+)pt too wide\)[^\n]*\n[^\n]*", log):
    files = re.findall(r"((?:sections|appendix|tables|figures)/[\w-]+\.tex)", log[: m.start()])
    print(f"{float(m.group(1)):7.1f}pt  {files[-1] if files else '?'}  | {m.group(0).splitlines()[0][-22:]} | {m.group(0).splitlines()[1][:70]}")
