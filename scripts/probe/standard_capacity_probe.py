"""[33] Does a model's STANDARD PayGo pool keep up under the pipeline's normal load? (~$0.25)

Run:  .venv/Scripts/python.exe scripts/probe/standard_capacity_probe.py [--n 30] [--roles vertex_flash36 vertex_flash]

Question (maintainer, 2026-09-28): were today's hour-long 429s a property of gemini-3.1-flash-lite's
pool rather than of Standard PayGo on this account? For each role, sends N real stored S&W
`claim_extract` prompts (a seed the bake-off did not use; a trailing newline makes every call a
cache miss) on STANDARD (Flex header removed) at concurrency 4 with retries OFF, through
llm/client.py, and prints ok / 429 / other counts, median latency and wall time. Record the result
in docs/MEASUREMENTS.md with the UTC time: pool state changes by the hour.
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from narrativewiki.config import apply_model_overrides, apply_set_overrides, load_settings  # noqa: E402
from narrativewiki.llm.client import LLMClient, LLMError  # noqa: E402
from narrativewiki.llm.parallel import map_calls  # noqa: E402


def prompts(n: int, seed: int = 4242) -> list[dict]:
    seen, uniq = set(), []
    for f in sorted(glob.glob(str(ROOT / "data/spice-and-wolf/_runs/*extract-v[12]*/calls.jsonl"))):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if (r.get("stage") == "claim_extract" and r.get("model") == "gemini-3.1-flash-lite"
                    and r.get("response") and r["cache_key"] not in seen):
                seen.add(r["cache_key"])
                uniq.append(r)
    return random.Random(seed).sample(uniq, n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--roles", nargs="+", default=["vertex_flash36", "vertex_flash"])
    a = ap.parse_args()
    ps = prompts(a.n)
    print(time.strftime("%H:%M UTC", time.gmtime()))
    for role in a.roles:
        s = load_settings("spice-and-wolf")
        apply_model_overrides(s, [role])
        apply_set_overrides(s, [f"models.profiles.{role}.options.shared_request_type=null",  # Standard
                                "models.client.rate_limit_retries=0", "models.client.max_retries=0"])      # count, never retry
        c = LLMClient(s, volume_scope=2)
        prof = s.resolve_role("claim_extract")

        def one(r: dict) -> tuple[str, float]:
            t = time.time()
            try:
                c._call("claim_extract", prof, r["prompt"] + "\n", r.get("system") or None, True, None)  # noqa: SLF001
                return "ok", time.time() - t
            except LLMError as e:
                kind = "429" if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) else "err:" + str(e)[:80]
                return kind, time.time() - t

        t0 = time.time()
        res = map_calls(one, ps, workers=4)
        ok = sorted(d for k, d in res if k == "ok")
        print(f"{prof.model} STANDARD: {len(ok)}/{a.n} ok, {sum(k == '429' for k, _ in res)} x 429, "
              f"other {[k for k, _ in res if k not in ('ok', '429')][:3]}, "
              f"median {ok[len(ok) // 2] if ok else 0:.1f}s, wall {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
