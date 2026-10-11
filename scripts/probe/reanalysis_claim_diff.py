"""[24] TASK-0001: does `--gate=build`'s cutoff-restricted entity registry change what
`wiki extract` actually pulls out of a volume's text, compared to today's render-mode extraction
(full registry, filtered only at render time)?

For each cutoff t in [1, 2] on spice-and-wolf: compare render-mode claims (data/03_claims/v{NN}.jsonl
for NN in 1..t, kept only where first_vol <= t) against build-mode claims
(data/@t{t:02d}/03_claims/v{NN}.jsonl for the same volumes), as sets keyed by
(subject, predicate, object, value). Reports:
    - only_render: found under the full registry, not under the cutoff-restricted one
    - only_build:  the reverse
    - differing_value: same (subject, predicate) but a different object/value between conditions

Outputs docs/probe/claim_diff_spice-and-wolf.jsonl. Zero LLM calls; reads only files on disk.
Run:    python scripts/probe/reanalysis_claim_diff.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERIES_ID = "spice-and-wolf"
SERIES_DIR = ROOT / "data" / SERIES_ID
CUTOFFS = [1, 2]


def _load_claims(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _key(claim: dict) -> tuple:
    return (claim["subject"], claim["predicate"], claim.get("object", ""), claim.get("value", ""))


def _sv_key(claim: dict) -> tuple:
    return (claim["subject"], claim["predicate"])


def measure(t: int) -> dict:
    render_claims = []
    for vol in range(1, t + 1):
        render_claims.extend(
            c for c in _load_claims(SERIES_DIR / "03_claims" / f"v{vol:02d}.jsonl") if c.get("first_vol", vol) <= t
        )
    build_claims = []
    for vol in range(1, t + 1):
        build_claims.extend(_load_claims(SERIES_DIR / f"@t{t:02d}" / "03_claims" / f"v{vol:02d}.jsonl"))

    render_by_key = {_key(c): c for c in render_claims}
    build_by_key = {_key(c): c for c in build_claims}
    render_keys, build_keys = set(render_by_key), set(build_by_key)

    only_render = sorted(render_keys - build_keys)
    only_build = sorted(build_keys - render_keys)

    render_by_sv: dict[tuple, list] = {}
    for k, c in render_by_key.items():
        render_by_sv.setdefault(_sv_key(c), []).append(k)
    build_by_sv: dict[tuple, list] = {}
    for k, c in build_by_key.items():
        build_by_sv.setdefault(_sv_key(c), []).append(k)
    differing_value = sorted(
        sv for sv in (render_by_sv.keys() & build_by_sv.keys())
        if set(render_by_sv[sv]) != set(build_by_sv[sv])
    )

    n_render = len(render_claims)
    return {
        "channel": "L_build",
        "probe": "claim_diff",
        "series": SERIES_ID,
        "upto_vol": t,
        "n_render_claims": n_render,
        "n_build_claims": len(build_claims),
        "only_render": len(only_render),
        "only_build": len(only_build),
        "differing_value": len(differing_value),
        "only_render_rate": (len(only_render) / n_render) if n_render else None,
        "only_build_rate": (len(only_build) / n_render) if n_render else None,
        "differing_value_rate": (len(differing_value) / n_render) if n_render else None,
    }


if __name__ == "__main__":
    out = ROOT / f"docs/probe/claim_diff_{SERIES_ID}.jsonl"
    rows = [measure(t) for t in CUTOFFS]
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    for r in rows:
        if r["n_render_claims"] == 0:
            print(f"{SERIES_ID} t={r['upto_vol']}: no render-mode claims on disk to compare against.")
            continue
        print(
            f"{SERIES_ID} t={r['upto_vol']}: only_render={r['only_render']} ({r['only_render_rate']:.3f}), "
            f"only_build={r['only_build']} ({r['only_build_rate']:.3f}), "
            f"differing_value={r['differing_value']} ({r['differing_value_rate']:.3f}) "
            f"[of {r['n_render_claims']} render claims]"
        )
    print(f"  -> {out.relative_to(ROOT)}")
