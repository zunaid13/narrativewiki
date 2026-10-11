"""[33] Is the routed Vertex model answering? One 8-token call, no cache, exit 0 = yes.

Run:  .venv/Scripts/python.exe scripts/eval/vertex_probe.py [--stage claim_extract] [--series anne]

A runner waits on this before a billed step (`until vertex_probe.py; do sleep 600; done`) so that a
provider outage costs one tiny request every ten minutes instead of a burst of retries per stage
(MEASUREMENTS 2026-09-28: every retry during an outage is a request). It calls the provider
adapter directly: going through llm/client.py would answer from the cache and prove nothing. The
probe uses the stage's own profile and transport (Standard or Flex), so it tests what the stage
will use. A probe is not a measurement and is not logged in a run ledger.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from narrativewiki.config import load_settings  # noqa: E402
from narrativewiki.llm.providers import google  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="claim_extract")
    ap.add_argument("--series", default="anne")
    a = ap.parse_args()
    profile = load_settings(a.series).resolve_role(a.stage)
    if profile.provider != "google":
        print(f"probe: stage {a.stage} routes to {profile.provider}, nothing to probe")
        return 0
    tier, t0 = (profile.options or {}).get("shared_request_type"), time.time()
    # [34] Maintainer 2026-10-05: "dont probe so often.. only probe after like 15min". One real probe per
    # project per PROBE_MIN_INTERVAL_S (900); a check in between repeats that probe's answer, marked cached.
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    state_file = ROOT / "data" / "_probe_state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    last = state.get(project)
    if last and t0 - last["at"] < float(os.environ.get("PROBE_MIN_INTERVAL_S", "900")):
        print(f"{time.strftime('%H:%M', time.gmtime())} probe {profile.model} ({tier or 'standard'}): "
              f"cached from {time.strftime('%H:%M', time.gmtime(last['at']))}: {last['message']}")
        return 0 if last["ok"] else 1

    def remember(ok: bool, message: str) -> None:
        state[project] = {"at": t0, "ok": ok, "message": message}
        state_file.write_text(json.dumps(state), encoding="utf-8")

    try:
        client = google._build_client(profile, tier)  # keep the reference: the client closes when collected
        client.models.generate_content(
            model=profile.model, contents="Reply with the single word OK.",
            config={"max_output_tokens": 8, "temperature": 0.0, "thinking_config": {"thinking_budget": 0}})
    except Exception as exc:  # any failure means "not yet"; the caller sleeps and asks again
        remember(False, str(exc)[:70])
        print(f"{time.strftime('%H:%M', time.gmtime())} probe {profile.model} ({tier or 'standard'}): {str(exc)[:70]}")
        return 1
    remember(True, "ok")
    print(f"{time.strftime('%H:%M', time.gmtime())} probe {profile.model} ({tier or 'standard'}): ok in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
