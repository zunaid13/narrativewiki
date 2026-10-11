"""Local MiniCheck diagnosis on fixed Spice and Wolf v1-2 claim inputs.

Run: .venv/Scripts/python.exe scripts/eval/nli_controls.py
Does not rebuild the graph, alter claims, or synthesize pages. Full evidence remains in the
gitignored run/cache artifacts; the checked-in report contains identifiers and scores only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from narrativewiki import paths, provenance
from narrativewiki.cli import _merge_claims_by_id
from narrativewiki.config import load_settings
from narrativewiki.graph import contradictions, support
from narrativewiki.llm.client import LLMClient


def main():
    paths.set_active_series("spice-and-wolf")
    settings = load_settings("spice-and-wolf")
    gaz = json.loads(paths.gazetteer().read_text(encoding="utf-8"))
    entities = {e["entity_id"]: e for e in gaz["entities"]}
    claim_files = [p for vol in (1, 2) for p in (paths.claims_volume(vol), paths.scene_claims_volume(vol))]
    claims = _merge_claims_by_id([
        json.loads(line) for path in claim_files for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ])
    selected = [c for c in claims if (c["subject"] == "zheren" and c["predicate"] == "OCCUPATION") or
                (c["subject"], c["predicate"], c.get("object")) in {
                    ("holo", "ENEMY_OF", "norah-arendt"),
                    ("norah-arendt", "SAVED", "remelio-company"),
                    ("jakob", "SAVED", "kraft-lawrence"),
                    ("holo", "KILLED", "saint-ruvinheigen"),
                }]
    if not selected:
        raise ValueError("No control claims found")
    run = provenance.start_run("spice-and-wolf", "nli_controls", scope="v1-2", volumes=[1, 2],
                               volume_scope=2, stage_keys=[], settings=settings)
    client = LLMClient(settings, run=run, volume_scope=2)
    scores = {}
    try:
        for claim in selected:
            result = support.score_claims([claim], entities, settings, client)[claim["claim_id"]]
            scores[claim["claim_id"]] = result
            print(f"{claim['claim_id']} {result['score']:.6f} {result['hypothesis']}", flush=True)
        occupations = [c for c in selected if c["predicate"] == "OCCUPATION"]
        before, _, _ = contradictions.build_graph(occupations, settings, None)
        after, _, arbitration = contradictions.build_graph(occupations, settings, None, support_scores=scores)
        report = {
            "series": "spice-and-wolf", "volumes": [1, 2], "run_id": run.run_id,
            "method": "MiniCheck FT5, discovery-volume +/-4 context, max chunk support",
            "scope": "diagnostic cases, not an accuracy benchmark or recall measurement",
            "cases": [{"claim_id": c["claim_id"], "subject": c["subject"], "predicate": c["predicate"],
                       "object": c.get("object"), "value": c.get("value"), "polarity": c.get("polarity"),
                       **{key: scores[c["claim_id"]][key] for key in (
                           "hypothesis", "score", "extracted_confidence", "model", "revision", "context_sha256", "evidence_cutoff")}}
                      for c in selected],
            "occupation_before": [i["value"] for i in before], "occupation_after": [i["value"] for i in after],
            "arbitration": arbitration["conflicts"],
            "input_sha256": {paths.relative(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in claim_files},
        }
        (ROOT / "docs/eval").joinpath("nli_controls_spice-and-wolf.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        run.finish("ok")
    except Exception as exc:
        run.finish("failed", error=str(exc))
        raise


if __name__ == "__main__":
    main()
