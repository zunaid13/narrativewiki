"""[24] Re-analysis of the L_build headline (2026-09-13) -- disclosure predicate vs. set difference.

Why this exists:
    `probe/channels/index.py::measure_candidate_mining` answers "would cutoff-only mining have
    produced this surface form?" That is a *selection-consistency* question. It reported
    leak_rate 0.303 for the 86 series at t=1. This script answers the *disclosure* question the
    paper actually needs -- "could a reader who has read only volumes 1..t ever have SEEN this
    string?" -- by locating each shipped surface form's first verbatim occurrence in parsed text.

    Tier A (exact):      first occurrence of the surface as written.
    Tier B (normalised): leading article stripped, case-insensitive -- so "The Gran Mur" does not
                         count as unseeable when "the Gran Mur" appears 14 times in volume 1.

Outputs docs/probe/first_occurrence_<series>.jsonl. Zero LLM calls; reads only files on disk.
Run:    python scripts/probe/reanalysis_first_occurrence.py

Historical analysis only. For new measurements use the tested, series-scoped CLI:
    wiki probe run disclosure --series spice-and-wolf --volumes 1-2
The historical main block below includes a wider corpus scope and must not be run under the
current maintainer restriction. It is retained as the original analysis record.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SERIES = {
    "86": (ROOT / "data/02_entities/gazetteer.json", ROOT / "data/01_parsed", [1, 2, 3, 4]),
    "spice-and-wolf": (
        ROOT / "data/spice-and-wolf/02_entities/gazetteer.json",
        ROOT / "data/spice-and-wolf/01_parsed",
        [1, 2],
    ),
}


def _blob(parsed_dir: Path, vol: int) -> str:
    path = parsed_dir / f"v{vol:02d}.jsonl"
    return "\n".join(
        json.loads(line).get("text", "")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _normalise(surface: str) -> str:
    return re.sub(r"^(the|a|an)\s+", "", surface.strip(), flags=re.I)


def measure(series_id: str, gazetteer_path: Path, parsed_dir: Path, vols: list[int]) -> list[dict]:
    entities = json.loads(gazetteer_path.read_text(encoding="utf-8"))["entities"]
    blobs = {v: _blob(parsed_dir, v) for v in vols}
    rows = []
    for t in vols:
        visible = [e for e in entities if int(e.get("first_vol", 1)) <= t]
        surfaces = sorted({sf["text"] for e in visible for sf in e.get("surface_forms", [])})
        unseen_exact, unseen_norm = [], []
        for s in surfaces:
            seen_exact = any(re.search(re.escape(s), blobs[v]) for v in vols if v <= t)
            seen_norm = any(re.search(re.escape(_normalise(s)), blobs[v], re.I) for v in vols if v <= t)
            if not seen_exact:
                unseen_exact.append(s)
            if not seen_norm:
                unseen_norm.append(s)
        rows.append(
            {
                "channel": "L_build",
                "probe": "first_occurrence",
                "series": series_id,
                "upto_vol": t,
                "cutoff_visible_surface_forms": len(surfaces),
                "unseeable_exact": unseen_exact,
                "unseeable_rate_exact": len(unseen_exact) / len(surfaces) if surfaces else 0.0,
                "unseeable_normalised": unseen_norm,
                "unseeable_rate_normalised": len(unseen_norm) / len(surfaces) if surfaces else 0.0,
            }
        )
    return rows


if __name__ == "__main__":
    for series_id, (gz, parsed, vols) in SERIES.items():
        rows = measure(series_id, gz, parsed, vols)
        out = ROOT / f"docs/probe/first_occurrence_{series_id}.jsonl"
        out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        for r in rows:
            print(
                f"{series_id} t={r['upto_vol']}: exact {r['unseeable_rate_exact']:.3f} "
                f"({len(r['unseeable_exact'])}/{r['cutoff_visible_surface_forms']}), "
                f"normalised {r['unseeable_rate_normalised']:.3f} "
                f"({len(r['unseeable_normalised'])}/{r['cutoff_visible_surface_forms']})"
            )
        print(f"  -> {out.relative_to(ROOT)}")
