"""[33] S16: run_cost.py separates sent calls, cache hits and errors, and per-volume runs."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location("run_cost", Path(__file__).parents[1] / "scripts/eval/run_cost.py")
run_cost = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_cost)


def _run(root: Path, run_id: str, volumes: list[int], calls: list[dict], sha: str = "abc123") -> None:
    d = root / run_id
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"volumes": volumes, "git_sha": sha, "command": "x"}))
    (d / "calls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in calls))


def test_cold_warm_and_per_volume(tmp_path):
    sent = {"stage": "claim_extract", "model": "m", "in_tokens": 100, "out_tokens": 10, "cost_usd": 0.5}
    hit = {**sent, "cache_hit": True, "cost_usd": 0.0}
    err = {"stage": "claim_extract", "model": "m", "error": "429"}
    _run(tmp_path, "20260101T000000-extract-v1-1", [1], [sent, hit, err])
    _run(tmp_path, "20260101T010000-verify", [1, 2], [sent], sha="zzz")
    s = run_cost.summarize(tmp_path)
    assert s["total"]["sent"] == 2 and s["total"]["cache_hits"] == 1 and s["total"]["errors"] == 1
    assert s["total"]["cost_usd"] == 1.0 and s["total"]["hit_in_tokens"] == 100
    assert s["by_volume"] == {"1": {**run_cost._blank(), "sent": 1, "cache_hits": 1, "errors": 1, "in_tokens": 100,
                                    "out_tokens": 10, "hit_in_tokens": 100, "hit_out_tokens": 10, "cost_usd": 0.5}}
    assert run_cost.summarize(tmp_path, sha="abc")["total"]["sent"] == 1  # frozen-tag filter
