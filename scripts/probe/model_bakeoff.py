"""Stored-prompt bake-off: re-send real calls answered by the routed model to candidate profiles.

Run:  .venv/Scripts/python.exe scripts/probe/model_bakeoff.py <series> <role> [<role> ...]
      [--per-stage claim_extract=12,scene_extract=6,verify=6] [--volumes 2]

Sends each sampled prompt through llm/client.py (cached, budgeted) under each candidate role and
compares with the stored gemini-3.1-flash-lite answer: JSON validity, items returned (the first
list in the answer: facts / scenes / verdicts), latency, tokens, cost. Output:
docs/probe/model_bakeoff_<series>_<date>.jsonl. Picks the model; never routes it.
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path

from narrativewiki.config import apply_model_overrides, load_settings
from narrativewiki.llm.client import LLMClient

ROOT = Path(__file__).resolve().parents[2]
BASE = "gemini-3.1-flash-lite"


def items(text: str) -> int | None:
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(obj, list):
        return len(obj)
    lists = [v for v in obj.values() if isinstance(v, list)] if isinstance(obj, dict) else []
    return len(lists[0]) if lists else 0


def sample(series: str, per_stage: dict[str, int], vmax: int) -> list[dict]:
    seen, pool = set(), {s: [] for s in per_stage}
    for f in sorted(glob.glob(str(ROOT / f"data/{series}/_runs/*/calls.jsonl"))):
        run = Path(f).parent.name
        if any(f"-v{v}" in run for v in range(vmax + 1, 20)):
            continue
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if (r.get("stage") in pool and r.get("model") == BASE and not r.get("error")
                    and r.get("response") and r["cache_key"] not in seen):
                seen.add(r["cache_key"])
                pool[r["stage"]].append(r)
    rng = random.Random(28)
    return [r for s, n in per_stage.items() for r in rng.sample(pool[s], min(n, len(pool[s])))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("series")
    ap.add_argument("roles", nargs="+")
    ap.add_argument("--per-stage", default="claim_extract=12,scene_extract=6,verify=6")
    ap.add_argument("--volumes", type=int, default=2)
    a = ap.parse_args()
    per_stage = {k: int(v) for k, v in (kv.split("=") for kv in a.per_stage.split(","))}
    calls = sample(a.series, per_stage, a.volumes)
    out = ROOT / f"docs/probe/model_bakeoff_{a.series}_{datetime.now(UTC):%Y%m%d}.jsonl"
    with out.open("a", encoding="utf-8") as fh:
        for role in a.roles:
            settings = load_settings(a.series)
            apply_model_overrides(settings, [role])
            client = LLMClient(settings, volume_scope=a.volumes)
            profile = settings.resolve_role("claim_extract")
            for r in calls:
                t = time.time()
                row = {"role": role, "model": profile.model, "stage": r["stage"], "cache_key_base": r["cache_key"],
                       "base_items": items(r["response"]), "base_out_tokens": r.get("out_tokens")}
                try:
                    # _call, not complete(): complete() returns only the text, and the bake-off
                    # needs the token counts (a cache hit returns the stored ones).
                    stage_profile = settings.resolve_role(r["stage"])
                    c = client._call(r["stage"], stage_profile, r["prompt"], r.get("system") or None, True, None)  # noqa: SLF001
                    row |= {"ok": True, "items": items(c.text), "in_tokens": c.in_tokens, "out_tokens": c.out_tokens,
                            "cost_usd": (c.in_tokens * profile.price_in + c.out_tokens * profile.price_out) / 1e6}
                except Exception as exc:  # noqa: BLE001 - a bake-off records failures, it does not stop
                    row |= {"ok": False, "error": str(exc)[:300]}
                row["seconds"] = round(time.time() - t, 1)  # a cache hit's time is not the model's
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(role, r["stage"], row.get("items"), "vs", row["base_items"], row["seconds"], "s",
                      "" if row["ok"] else row["error"][:80], flush=True)
    print(out)


if __name__ == "__main__":
    main()
