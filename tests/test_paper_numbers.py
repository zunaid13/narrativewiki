"""[33] S12: means over cutoffs within a work, character-clustered paired bootstrap, zero bounds."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("paper_numbers", Path(__file__).parents[1] / "scripts/eval/paper_numbers.py")
pn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pn)


def _obs(system, t, ch, num, metric="M1", work="anne", den=1, **kw):
    return {"work": work, "system": system, "cutoff": t, "character": ch, "metric": metric, "num": num, "den": den, **kw}


def _by_key(res):
    return {r["key"]: r for r in res}


def test_avg_is_the_mean_of_per_cutoff_ratios_not_pooled():
    # t1: 1/1; t2: 1/3 -> mean 0.667 (pooled would be 2/4 = 0.5)
    rows = [_obs("B5", 1, "a", 1), _obs("B5", 2, "a", 1), _obs("B5", 2, "b", 0), _obs("B5", 2, "c", 0)]
    r = _by_key(pn.compute(rows, reps=200))
    assert abs(r["M1-anne-avg-B5"]["value"] - (1 + 1 / 3) / 2) < 1e-9
    assert r["M1-anne-t2-B5"]["num"] == 1 and r["M1-anne-t2-B5"]["den"] == 3


def test_works_are_never_pooled():
    rows = [_obs("B5", 1, "a", 1, work="anne"), _obs("B5", 1, "a", 0, work="oz")]
    r = _by_key(pn.compute(rows, reps=50))
    assert r["M1-anne-avg-B5"]["value"] == 1 and r["M1-oz-avg-B5"]["value"] == 0


def test_design_weights_and_counts():
    rows = [_obs("B5", 1, "a", 1, metric="M3", weight=3.0), _obs("B5", 1, "b", 0, metric="M3", weight=1.0),
            {"work": "anne", "system": "B5", "cutoff": 1, "character": "a", "metric": "N", "num": 7}]
    r = _by_key(pn.compute(rows, reps=50))
    assert r["M3-anne-t1-B5"]["value"] == 0.75
    assert r["N-anne-t1-B5"]["value"] == 7


def test_zero_events_get_an_exact_bound_and_paired_diff_is_signed():
    # 10 items over 5 characters: the bound counts the 5 characters (clusters), not the 10 items.
    rows = [_obs("B5", 1, c, 0, metric="M4") for c in "abcde" for _ in (1, 2)] +            [_obs("B1", 1, c, 1, metric="M4") for c in "abcde"]
    r = _by_key(pn.compute(rows, reps=200, pairs=[("B5", "B1")]))
    assert r["M4-anne-t1-B5"]["den"] == 10
    assert abs(r["M4-anne-t1-B5"]["zero_event_upper95"] - (1 - 0.05 ** 0.2)) < 1e-12
    d = r["M4-anne-avg-B5-minus-B1"]
    assert d["value"] == -1 and d["ci95"] == [-1, -1]


def test_bootstrap_keeps_a_characters_trajectory_together():
    # Character a is 1 at both cutoffs, b is 0 at both: every resample's avg is a multiple of 1/2
    # only if trajectories stay together (a split draw could give e.g. 1/2 at t1 and 0 at t2).
    rows = [_obs("B5", t, "a", 1) for t in (1, 2)] + [_obs("B5", t, "b", 0) for t in (1, 2)]
    r = _by_key(pn.compute(rows, reps=300, seed=1))
    lo, hi = r["M1-anne-avg-B5"]["ci95"]
    assert lo in (0, 0.5) and hi in (0.5, 1)


_spec2 = importlib.util.spec_from_file_location("paper_observations", Path(__file__).parents[1] / "scripts/eval/paper_observations.py")
po = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(po)


def test_observations_use_only_hand_verdicts(tmp_path):
    import json
    gold = {"characters": {"Anne Shirley": {"facts": [{"claim": "c1", "evidence": "v01:c01:p0001"},
                                                      {"claim": "f3", "evidence": "v03:c01:p0001"},
                                                      {"claim": "f6", "evidence": "v06:c01:p0001"}]}}}
    (tmp_path / "recall_hand").mkdir()
    (tmp_path / "recall_hand" / "anne_v1.json").write_text(json.dumps({"Anne Shirley | c1": "yes", "Anne Shirley | f3": "no",
                                                                     "Anne Shirley | f6": "yes"}))
    (tmp_path / "leak_audit").mkdir()
    (tmp_path / "leak_audit" / "anne.jsonl").write_text(
        json.dumps({"t": 1, "character": "Anne Shirley", "claim": "f3", "verdict": "implied", "reader": "agent",
                    "page_sha": "cur"}) + "\n")
    (tmp_path / "precision").mkdir()
    row = lambda **k: json.dumps({"entity": "Anne Shirley", **k}) + "\n"
    (tmp_path / "precision" / "anne_v1_all.jsonl").write_text(row(human="partial") + row(screen="x"))
    (tmp_path / "precision" / "anne_v1.jsonl").write_text(row(human="supported"))  # cited-only: never M3
    kw = dict(page_sha=lambda t, ch: "cur", pages_mtime=lambda t: 0.0, eval_dir=tmp_path)
    obs, skipped = po.observations("anne", "B5", 1, "anne", gold, **kw)
    by = {(o["metric"], o["source"]): o for o in obs}
    assert by[("M1", "anne_v1.json")]["num"] == 1
    assert by[("M4", "anne.jsonl")]["num"] == 1 and ("M4", "anne_v1.json") not in by  # audit wins, counted once
    assert by[("M3", "anne_v1_all.jsonl")]["num"] == 0 and skipped["precision_unread"] == 1
    assert ("M3", "anne_v1.jsonl") not in by
    assert skipped["past_scope"] == 1 and len(obs) == 3  # reveal 6 > last_vol 5: not in F_t
    # A verdict on a page that has since changed is stale, never an observation.
    obs, skipped = po.observations("anne", "B5", 1, "anne", gold, **{**kw, "page_sha": lambda t, ch: "new"})
    assert not any(o["source"] == "anne.jsonl" for o in obs) and skipped["stale"] == 1
    obs, skipped = po.observations("anne", "B5", 1, "anne", gold, **{**kw, "pages_mtime": lambda t: 4e9})
    assert not any(o["metric"] in ("M1", "M3") for o in obs) and skipped["stale"] == 2
    # R2/R3 (C13): uncertain is not support but stays in the denominator; a frame error leaves it.
    (tmp_path / "precision" / "anne_v1_all.jsonl").write_text(
        row(human="uncertain", human_atom="supported") + row(human="frame_error"))
    obs, skipped = po.observations("anne", "B5", 1, "anne", gold, **kw)
    m3 = [o for o in obs if o["metric"] == "M3"]
    assert [(o["num"], o["label"], o["label_atom"]) for o in m3] == [(0, "uncertain", "supported")]
    assert skipped["frame_error"] == 1


_spec3 = importlib.util.spec_from_file_location("run_series", Path(__file__).parents[1] / "scripts/run_series.py")
rs = importlib.util.module_from_spec(_spec3)
_spec3.loader.exec_module(rs)


def test_retry_from_scenes_restores_the_pre_merge_gazetteer(tmp_path):
    """[33] C16: a driver retry must rebuild scenes on the gazetteer merge-epithets started from,
    not on its merged output (A1 t=2/t=3 re-billed every call and changed the protocol)."""
    for f in rs.MERGED:
        (tmp_path / f).write_text("clean " + f)
    assert rs.premerge_guard(tmp_path, "merge-epithets") == "snapshot"
    (tmp_path / "gazetteer.json").write_text("merged")  # what the merge writes, then the driver records it
    (tmp_path / "_premerge" / "merged.sha").write_text(rs._sha(tmp_path / "gazetteer.json"))
    assert rs.premerge_guard(tmp_path, "extract-v1") is None
    assert rs.premerge_guard(tmp_path, "scenes-v1") == "restored pre-merge gazetteer"
    assert (tmp_path / "gazetteer.json").read_text() == "clean gazetteer.json"
    # A gazetteer rebuilt since the merge is never reverted.
    rs.premerge_guard(tmp_path, "merge-epithets")
    (tmp_path / "_premerge" / "merged.sha").write_text("sha-of-an-older-merge")
    (tmp_path / "gazetteer.json").write_text("rebuilt")
    assert rs.premerge_guard(tmp_path, "scenes-v1") == "stale snapshot dropped"
    assert (tmp_path / "gazetteer.json").read_text() == "rebuilt"


def test_whole_tree_verdicts_are_the_m4_source_when_present(tmp_path):
    """C20 / R6: `<series>_tree.jsonl` replaces the per-page audit; a row for another tree is stale."""
    import json
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "eval"))
    import paper_observations as po
    gold = {"characters": {"Ann": {"facts": [{"claim": "later", "evidence": "v02:c00:p0000"}]}}}
    (tmp_path / "leak_audit").mkdir()
    rows = [{"t": 1, "character": "Ann", "claim": "later", "tree_sha": "now", "verdict": "uncertain"},
            {"t": 1, "character": "Ann", "claim": "later", "tree_sha": "old", "verdict": "stated"}]
    (tmp_path / "leak_audit" / "s_tree.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "leak_audit" / "s.jsonl").write_text(json.dumps(
        {"t": 1, "character": "Ann", "claim": "later", "page_sha": "p", "verdict": "stated"}) + "\n")
    obs, skipped = po.observations("s", "B5", 1, "s", gold, page_sha=lambda t, ch: "p", pages_mtime=lambda t: 0.0,
                                   eval_dir=tmp_path, tree_sha=lambda t: {"now"})
    assert [(o["metric"], o["num"], o["label"]) for o in obs] == [("M4", 0, "uncertain")] and skipped["stale"] == 1
