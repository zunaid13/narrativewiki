"""Reproduce TASK-0004's mining-channel gate comparison; zero LLM calls.

Run: python scripts/probe/gate_comparison_option_a.py
Scope is fixed to Spice and Wolf volumes 1-2. Requires completed render/@t01/@t02
gazetteers and candidates matching the current miner. Writes only the comparison
JSONL, after all four measurements succeed; does not rebuild pipeline artifacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from narrativewiki import config, paths, provenance
from narrativewiki.entities.candidates import mine_candidates
from narrativewiki.probe.channels.index import measure_candidate_mining
from narrativewiki.probe.report import write_jsonl

SERIES = "spice-and-wolf"
CUTOFFS = (1, 2)


def _validate_inputs(series_config: dict, row: dict, cutoff: int | None) -> None:
    """Reject mixed old/new candidates and incomplete or incorrectly scoped builds."""
    expected_volumes = list(range(1, (cutoff or max(CUTOFFS)) + 1))
    if row["shipped_gazetteer_volumes_covered"] != expected_volumes:
        raise ValueError(f"{paths.gazetteer()}: expected volumes {expected_volumes}")
    writer = provenance.last_run_for_stage("gazetteer")
    if writer is None or writer.get("outcome") != "ok":
        raise ValueError(f"{paths.gazetteer()}: requires a completed gazetteer run")
    if writer.get("volumes") != expected_volumes:
        raise ValueError(f"{writer['run_id']}: expected run volumes {expected_volumes}")
    volumes = {
        vol: [json.loads(line) for line in paths.parsed_volume(vol).read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()]
        for vol in expected_volumes
    }
    parameters = row["mining_parameters"]
    hints = {**(series_config.get("entities") or {}),
             "max_candidates_per_volume": parameters["max_candidates_per_volume"]}
    fresh = mine_candidates(
        volumes, {**series_config, "entities": hints},
        min_mentions=parameters["min_mentions"],
    )
    shipped = [json.loads(line) for line in paths.candidates().read_text(
        encoding="utf-8"
    ).splitlines() if line.strip()]
    # Compare records, not only counts: an equally sized stale candidate set can
    # still change first_vol, evidence, or the surfaces available to classification.
    if sorted(fresh, key=lambda c: c["surface"]) != sorted(shipped, key=lambda c: c["surface"]):
        raise ValueError(f"{paths.candidates()}: stale candidates; rebuild the gazetteer")


def main() -> None:
    paths.set_active_series(SERIES)
    settings = config.load_settings(SERIES)
    results = []
    try:
        for t in CUTOFFS:
            for gate in ("render", "build"):
                cutoff = t if gate == "build" else None
                paths.set_build_cutoff(cutoff)
                row = measure_candidate_mining(SERIES, settings.series, t)
                _validate_inputs(settings.series, row, cutoff)
                row["gate"] = gate
                results.append(row)
    finally:
        paths.set_build_cutoff(None)

    output = paths.DOCS_DIR / "probe" / "gate_comparison_spice-and-wolf.jsonl"
    write_jsonl(results, output)
    for row in results:
        missing = row["surfaces_missing_at_cutoff"]
        print(f"t={row['upto_vol']} {row['gate']}: leak={row['leak_rate']:.3f} "
              f"({len(missing)}/{row['cutoff_visible_surface_forms']}) "
              f"entities={row['cutoff_visible_entities']} missing={missing}")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
