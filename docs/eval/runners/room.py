"""Budget room per Vertex project, in whole dollars of ledger cost. Prints one integer.

Run:  .venv/Scripts/python.exe docs/eval/runners/room.py new|old|decon   (or --show)

2026-10-04, maintainer: the rest of the work runs on the arnababir1 account's project; the temporary
account's project is used only when that one answers 429; the geminiprof2 project is never used.
  new  min2web-nsyss-4 budget $200 (maintainer 2026-10-04): stop at ledger 200 (the ledger runs above the console).
  old  gen-lang-client-0365142802: the stop as before, ledger 313 with the 19.85 offset (memory:
       billing-vs-ledger). Everything before SWITCH ran here.
  decon  what the decontaminated runner may spend on `new`: new's room minus what Oz has not spent yet
       of its estimate (Oz first; 0 once the Oz log says "oz done").
calls.jsonl carries no project, so each run is attributed from data/vertex_projects.log, where
`vertex.sh::use_project` appends "<UTC run-id time> <new|old> <runner>" whenever a runner changes project.
A run belongs to its runner by series (oz* -> oz, anne-decon/anne-remap -> decon) and to the project that
runner had last selected at the run's start. Lives here, not in scripts/, so the oz-v2 freeze holds.
"""
import glob
import json
import os
import sys

SWITCH = "20261004T1237"
OZ_ESTIMATE_LEFT = 60.0  # B3, B1, X2 on Oz at the 12:37 UTC pause; Oz's own estimate, ~$70 in all
RUNNER = {"oz": "oz", "anne-decon": "decon", "anne-remap": "decon", "anne": "fix", "middlemarch": "fix",
          "leagues": "fix"}  # fix: 2026-10-05 fix batch + public-domain dev checks


def _switches() -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    if os.path.exists("data/vertex_projects.log"):
        for line in open("data/vertex_projects.log", encoding="utf-8"):
            ts, project, runner = line.split()[:3]
            out.setdefault(runner, []).append((ts, project))
    return out


def _cost(line: str) -> float:
    # [34] 2026-10-05: a power cut left NUL bytes in a killed run's ledger, and the crash here stopped
    # every runner at its budget gate. An unreadable line is a call that never finished: no cost.
    try:
        return json.loads(line).get("cost_usd") or 0
    except ValueError:
        return 0


def spent() -> dict[str, float]:
    sw = _switches()
    tot = {"old": 0.0, "new": 0.0, "oz_new": 0.0}
    for f in glob.glob("data/*/_runs/*/calls.jsonl"):
        parts = os.path.normpath(f).split(os.sep)
        series, run = parts[-4].split("@")[0], parts[-2]
        cost = sum(_cost(line) for line in open(f, encoding="utf-8", errors="replace"))
        project = "old"
        if run >= SWITCH:
            runner = RUNNER.get(series)
            picks = [p for ts, p in sw.get(runner, []) if ts <= run]
            project = picks[-1] if picks else "old"
        tot[project] += cost
        if project == "new" and series == "oz":
            tot["oz_new"] += cost
    return tot


def rooms() -> dict[str, float]:
    s = spent()
    oz_done = os.path.exists("data/oz_heldout.out") and "oz done" in open(
        "data/oz_heldout.out", encoding="utf-8", errors="ignore").read()
    new = 200 - s["new"]
    return {"new": new, "old": 313 - (s["old"] - 19.85),
            "decon": new - (0.0 if oz_done else max(0.0, OZ_ESTIMATE_LEFT - s["oz_new"])),
            **{"spent_" + k: v for k, v in s.items()}}


if __name__ == "__main__":
    r = rooms()
    if sys.argv[1:] == ["--show"]:
        print(" ".join(f"{k} {v:.2f}" for k, v in r.items()))
    else:
        print(int(r[sys.argv[1]]))
