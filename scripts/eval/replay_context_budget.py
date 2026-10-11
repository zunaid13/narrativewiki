"""Offline request-sizing comparison, Spice and Wolf volumes 1-2 only; no model calls.

Run from the repository root: python scripts/eval/replay_context_budget.py
The recording client returns no facts: this measures request fit/coverage, NOT extraction yield.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from narrativewiki import paths
from narrativewiki.config import load_settings
from narrativewiki.extract.claims import extract_volume
from narrativewiki.llm.budget import estimate_tokens


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class Recorder:
    def __init__(self, profile, bounded, safety_tokens):
        self.profile = profile if bounded else replace(profile, options={})
        self.context = profile.options["num_ctx"]
        self.safety_tokens = safety_tokens
        self.sizes = []
        self.paragraphs = set()

    def profile_for(self, stage):
        return self.profile

    def complete_json(self, stage, prompt, schema, system=None, options=None):
        self.sizes.append(estimate_tokens(system + "\n" + prompt) + options["num_predict"] + self.safety_tokens)
        self.paragraphs.update(re.findall(r"^\[(v\d+:c\d+:p\d+)\]", prompt, re.MULTILINE))
        return schema(facts=[])

    def summary(self, drops):
        return {
            "requests": len(self.sizes), "max_estimated_total_tokens": max(self.sizes, default=0),
            "over_context_requests": sum(size > self.context for size in self.sizes),
            "distinct_paragraphs_sent": len(self.paragraphs), "drops": dict(drops),
        }


def main():
    paths.set_active_series("spice-and-wolf")
    settings = load_settings("spice-and-wolf")
    settings.model_overrides["claim_extract"] = "local_fast"
    profile = settings.resolve_role("claim_extract")
    safety_tokens = settings.extraction_behaviour["window"].get("context_safety_tokens", 256)
    gaz = json.loads(paths.gazetteer().read_text(encoding="utf-8"))
    mentions = read_jsonl(paths.mentions())
    inputs = [paths.gazetteer(), paths.mentions(), paths.extraction_config(), paths.models_config(),
              ROOT / "src/narrativewiki/extract/claims.py", Path(__file__).resolve()]
    report = {"series": "spice-and-wolf", "volumes": [1, 2], "model_calls": 0,
              "profile": str(profile), "num_ctx": profile.options["num_ctx"], "safety_tokens": safety_tokens,
              "measurement": "estimated initial request sizing; empty model responses, no fact-yield or recall measurement",
              "results": {}}
    for vol in (1, 2):
        inputs.append(paths.parsed_volume(vol))
        records = read_jsonl(paths.parsed_volume(vol))
        entities = [e for e in gaz["entities"] if e["first_vol"] <= vol]
        characters = [e for e in entities if e["type"] == "CHARACTER"]
        scoped_mentions = [m for m in mentions if m["vol"] == vol]
        clients = [Recorder(profile, bounded=False, safety_tokens=safety_tokens),
                   Recorder(profile, bounded=True, safety_tokens=safety_tokens)]
        result = {}
        for label, client in zip(("before", "after"), clients):
            _, drops = extract_volume(characters, vol, records, scoped_mentions, entities, settings, client)
            result[label] = client.summary(drops)
        result["paragraphs_lost"] = sorted(clients[0].paragraphs - clients[1].paragraphs)
        report["results"][f"v{vol:02d}"] = result
    report["input_sha256"] = {paths.relative(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    output = (ROOT / "docs/eval").joinpath("context_budget_spice-and-wolf.json")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["results"], indent=2))


if __name__ == "__main__":
    main()
