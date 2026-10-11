"""qual_shots.py: the screenshots of appendix M = scripts/papers/wiki_screenshots.py plus one panel. $0.

Run exactly as that script's docstring says (mkdocs build of dist/anne@v2, a local server on port 8765), with
this file in its place:
  .venv/Scripts/python.exe docs/paper/_build/qual_shots.py

The extra panel is the block "Shirley" on Gilbert Blythe's page at cutoff 4: the second page the reported build
keeps for Anne under her surname (OPEN_GAPS G15). It is added here, not in SHOTS there, because scripts/ is not
edited while a runner reads it.
"""
from pathlib import Path

p = Path(__file__).resolve().parents[3] / "scripts" / "papers" / "wiki_screenshots.py"
src = p.read_text(encoding="utf-8").rstrip()
tail = "asyncio.run(main())"
assert src.endswith(tail), "wiki_screenshots.py no longer ends by running main()"
ns = {"__file__": str(p), "__name__": "wiki_screenshots"}
exec(compile(src[: -len(tail)], str(p), "exec"), ns)
ns["SHOTS"].append(("gilbert-v04-shirley", "/v04/character/gilbert-blythe/", "#shirley-the-relationship", "#wilson"))
ns["asyncio"].run(ns["main"]())
