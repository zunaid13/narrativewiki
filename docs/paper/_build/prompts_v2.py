"""prompts_v2.py: appendix K (prompts and model exchanges) for the reported build. $0, no model call.

Run, from the repository root:
  .venv/Scripts/python.exe docs/paper/_build/prompts_v2.py

scripts/papers/prompt_appendix.py names the first build's run directory (`anne`) for every stage of the main
system. The reported build is `anne@v2`; scripts/ is not edited while a runner reads it, so the series is
replaced here and the generator is otherwise run unchanged.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("prompt_appendix", ROOT / "scripts" / "papers" / "prompt_appendix.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.STAGES = [(stage, "anne@v2" if series == "anne" else series, title, what) for stage, series, title, what in m.STAGES]
missing = [(stage, series) for stage, series, _, _ in m.STAGES if not m.pick(stage, series)]
assert not missing, f"no logged call for {missing}"
m.main()
