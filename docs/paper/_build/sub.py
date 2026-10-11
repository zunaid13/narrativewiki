"""sub.py FILE: apply exact-string replacements read from stdin as blocks  <<<old ||| new>>>  (no escapes)."""
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
for old, new in re.findall(r"<<<(.*?)\|\|\|(.*?)>>>", sys.stdin.read(), flags=re.S):
    old, new = old.strip("\n"), new.strip("\n")
    n = s.count(old)
    if n != 1:
        sys.exit(f"{p}: {n} matches for: {old[:70]!r}")
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
print("ok", p)
