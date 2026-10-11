"""Local MiniCheck score distribution over EVERY arbitration-scope Spice and Wolf v1-2 claim.

Run: .venv/Scripts/python.exe scripts/eval/nli_kind_sweep.py

Answers the fork PHASE_26.md left open on 2026-09-20 -- "give relation predicates a separately
calibrated threshold OR a different verifier" -- by measuring the score distribution per kind and
per predicate, rather than on the five hand-picked cases `nli_controls.py` covers.

Reads only; does not rebuild the graph, alter claims, or synthesize pages. Writes
`nli_kind_sweep_<series>.json` with identifiers, scores and hypotheses -- no evidence text, same
convention as `nli_controls_spice-and-wolf.json`.
"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from narrativewiki import paths, provenance
from narrativewiki.cli import _merge_claims_by_id
from narrativewiki.config import load_settings
from narrativewiki.graph import support
from narrativewiki.llm.client import LLMClient

SERIES = "spice-and-wolf"
VOLUMES = (1, 2)


def summarize(label, scores):
    """Median plus the flagged-fraction at three candidate thresholds -- the question is not
    'what is the average' but 'how much would each cutoff throw away'."""
    s = sorted(scores)
    if not s:
        return None
    frac = lambda t: sum(1 for x in s if x < t) / len(s)
    return {"label": label, "n": len(s), "median": statistics.median(s),
            "p10": s[len(s) // 10], "p90": s[-max(1, len(s) // 10)],
            "flagged_at_0.5": frac(0.5), "flagged_at_0.1": frac(0.1), "flagged_at_0.02": frac(0.02)}


def main():
    paths.set_active_series(SERIES)
    settings = load_settings(SERIES)
    entities = {e["entity_id"]: e
                for e in json.loads(paths.gazetteer().read_text(encoding="utf-8"))["entities"]}
    files = [p for vol in VOLUMES for p in (paths.claims_volume(vol), paths.scene_claims_volume(vol))]
    claims = _merge_claims_by_id([json.loads(line) for path in files
                                  for line in path.read_text(encoding="utf-8").splitlines()
                                  if line.strip()])
    templates = settings.extraction_behaviour.get("support", {}).get("templates", {})
    scope = [c for c in support.arbitration_claims(claims, settings)
             if (c["kind"] != "relation" or c["predicate"] in templates)
             and c["subject"] in entities
             and (not c.get("object") or c["object"] in entities)]
    if not scope:
        raise ValueError("No in-scope claims found")
    print(f"scoring {len(scope)} claims", flush=True)

    run = provenance.start_run(SERIES, "nli_kind_sweep", scope=f"v{VOLUMES[0]}-{VOLUMES[-1]}",
                               volumes=list(VOLUMES), volume_scope=VOLUMES[-1], stage_keys=[],
                               settings=settings)
    client = LLMClient(settings, run=run, volume_scope=VOLUMES[-1])
    rows = []
    try:
        for i, claim in enumerate(scope):
            result = support.score_claims([claim], entities, settings, client)[claim["claim_id"]]
            rows.append({"claim_id": claim["claim_id"], "kind": claim["kind"],
                         "predicate": claim["predicate"], "score": result["score"],
                         "extracted_confidence": claim["confidence"],
                         "hypothesis": result["hypothesis"]})
            if i % 25 == 0:
                print(f"  {i}/{len(scope)}", flush=True)
        run.finish("ok")
    except BaseException as exc:
        run.finish("failed", error=str(exc))
        raise

    by_kind = collections.defaultdict(list)
    by_predicate = collections.defaultdict(list)
    for r in rows:
        by_kind[r["kind"]].append(r["score"])
        by_predicate[f"{r['kind'][:3]}:{r['predicate']}"].append(r["score"])
    report = {
        "series": SERIES, "volumes": list(VOLUMES), "run_id": run.run_id,
        "method": "MiniCheck FT5, discovery-volume +/-4 context, max chunk support",
        "scope": "every arbitration-scope claim with a support hypothesis template; a score "
                 "DISTRIBUTION, not an accuracy benchmark -- these claims carry no correctness labels",
        "by_kind": [summarize(k, v) for k, v in sorted(by_kind.items())],
        "by_predicate": [summarize(k, v) for k, v in
                         sorted(by_predicate.items(), key=lambda kv: -len(kv[1]))],
        "claims": rows,
    }
    out = (ROOT / "docs/eval").joinpath(f"nli_kind_sweep_{SERIES}.json")
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for row in report["by_kind"] + report["by_predicate"]:
        print(f"{row['label']:22s} n={row['n']:4d} median={row['median']:.3f} "
              f"p90={row['p90']:.3f} flagged@0.5={row['flagged_at_0.5']:.0%} "
              f"@0.1={row['flagged_at_0.1']:.0%} @0.02={row['flagged_at_0.02']:.0%}")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
