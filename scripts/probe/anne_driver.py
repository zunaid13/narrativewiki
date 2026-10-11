"""Unattended driver: finish the Anne principal-cast E2 run through intermittent Vertex 429s.

Run: .venv/Scripts/python.exe scripts/probe/anne_driver.py [--from <step>]
     (resume after a stop: pass the step it stopped on, e.g. --from extract-v5-6)
Each stage runs as its own `wiki` process with the per-run interlock override (plan 0010 review,
item 8) and concurrency 2. A stage that fails on 429 RESOURCE_EXHAUSTED is retried after 15
minutes, up to 3 times (the API sometimes stays down; a human should look rather than wait); every completed call is in the LLM cache, so a retry only re-sends
what failed, and a 429 is not billed. Any other failure stops the driver for a human to read.
Prints one line per step to stdout; full output goes to data/anne/_driver/<step>.log.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
# The 25-character principal cast (MEASUREMENTS §45); ANNE_CAST_FILE overrides it.
CAST = Path(os.environ.get("ANNE_CAST_FILE") or ROOT / "docs" / "eval" / "parametric" / "anne_cast.txt"
            ).read_text(encoding="utf-8").strip()
# max_calls_per_run: `graph build`'s verify pass is one call per fact, and six books hit the global
# 2000 (sized at ~3x a v1-2 run) at character 134 -- verification.json was never written and
# synthesis ran unverified (2026-09-26). Cache hits count toward the cap, so a re-run needs it too.
SET = ["--set", "models.profiles.vertex_flash.max_volumes=6", "--set", "models.profiles.vertex_flash.concurrency=2",
       "--set", "models.profiles.vertex_flash.max_calls_per_run=6000"]
CLI = [PY, "-m", "narrativewiki.cli"]
ENT = ["--entities", CAST] if CAST else []

STEPS: list[tuple[str, list[str]]] = [
    ("extract-v5-6", CLI + ["extract", "--series", "anne", "--volumes", "5-6", *ENT, *SET]),
    ("infobox", CLI + ["infobox", "--series", "anne", "--volumes", "1-6", *ENT, *SET]),
    ("backstory", CLI + ["infobox", "--series", "anne", "--volumes", "1-6", "--pass", "backstory", *ENT, *SET]),
    # --allow-partial: a principal-cast build leaves ~290 mentioned characters with zero claims by
    # design, which the crash-signature guard cannot tell from a crashed extract (checked 2026-09-26).
    ("graph", CLI + ["graph", "build", "--series", "anne", *(["--allow-partial"] if CAST else []), *SET]),
    ("events", CLI + ["events-build", "--series", "anne", "--force", *SET]),
    ("synthesize", CLI + ["synthesize", "--series", "anne", *SET]),
    ("site", CLI + ["site", "build", "--series", "anne", "--html", *SET]),
] + [(f"audit-{a}", CLI + ["audit", a, "--series", "anne"])
     for a in ("claims", "contradictions", "verify", "pages", "links", "events", "relationships", "outline")] \
  + [(f"leak-t{t}", [PY, str(ROOT / "scripts" / "eval" / "pipeline_page_leak.py"), "anne", "--upto", str(t)])
     for t in range(1, 6)]


def stamp() -> str:
    return datetime.now(UTC).strftime("%H:%M")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default=STEPS[0][0])
    args = ap.parse_args()
    names = [n for n, _ in STEPS]
    logdir = ROOT / "data" / "anne" / "_driver"
    logdir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for name, cmd in STEPS[names.index(args.start):]:
        for attempt in range(1, 4):
            proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
            out = proc.stdout + proc.stderr
            (logdir / f"{name}.log").write_text(out, encoding="utf-8")
            failed = proc.returncode != 0
            quota = "RESOURCE_EXHAUSTED" in out
            if not failed:
                print(f"{stamp()} {name}: ok (attempt {attempt})", flush=True)
                break
            if quota:
                print(f"{stamp()} {name}: 429, retry in 15 min (attempt {attempt})", flush=True)
                time.sleep(900)
                continue
            if name.startswith("audit"):
                print(f"{stamp()} {name}: FAIL, continuing (see {name}.log)", flush=True)
                break
            print(f"{stamp()} {name}: FAILED (exit {proc.returncode}), stopping; see data/anne/_driver/{name}.log", flush=True)
            return 1
        else:
            print(f"{stamp()} {name}: still 429 after 3 attempts, stopping", flush=True)
            return 2
    print(f"{stamp()} all steps done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
