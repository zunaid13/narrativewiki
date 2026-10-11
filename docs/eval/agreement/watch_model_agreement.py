"""Hourly local supervisor: resume failed jobs, then score complete model sheets.

No LLM polling or chat tokens. Existing jobs continue independently. Retries use
the same cached runner and persisted Gemini allowance. Never changes pipeline caps.
"""
import argparse
import ctypes
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from build_packet import HERE, ROOT
from compare_model_labels import compare
from narrativewiki import paths

STATUS = HERE / "automation_status.json"
JOBS = {
    "openrouter_ultra": {"role": "agreement_openrouter_ultra", "extra": ["--interval", "3.2"]},
    "gemini_pro": {"role": "agreement_vertex_pro", "extra": ["--additional-budget-usd", "20"]},
}


def is_alive(pid):
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
    finally:
        kernel.CloseHandle(handle)


def save(state):
    state["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    temp = STATUS.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temp.replace(STATUS)


def finish(state):
    output = HERE / "model_comparison"
    report = compare(HERE / "model_runs/openrouter_ultra", HERE / "model_runs/gemini_pro", output)
    marker = output / "measurements_recorded.json"
    command = ".venv/Scripts/python.exe docs/eval/agreement/compare_model_labels.py docs/eval/agreement/model_runs/openrouter_ultra docs/eval/agreement/model_runs/gemini_pro"
    if not marker.exists():
        rows = ["\n## 2026-10-10 — Completed independent model agreement\n\n",
                "| Date | Observation | Value / finding | Exact command or source | Run id / limits |\n",
                "|---|---|---|---|---|\n"]
        for task, result in report["tasks"].items():
            rows.append(f"| 2026-10-10 | Model-model {task} nominal agreement | n={result['n']}; agreement={result['agreement']}; kappa={result['kappa']}; chance={result['chance_agreement']} | `{command}` | agreement-model-comparison-20261010; independent model labels, not human agreement or accuracy |\n")
        pair = report["tasks"]["P"]["pair_scene"]
        rows.append(f"| 2026-10-10 | Pair-scene model agreement | n={pair['n']}; agreement={pair['agreement']}; kappa={pair['kappa']} | `{command}` | agreement-model-comparison-20261010; placement distinct from factual support |\n")
        for labeler in report["labelers"]:
            rows.append(f"| 2026-10-10 | {labeler['model']} recorded usage | cost USD={labeler['recorded_cost_usd']}; usage={json.dumps(labeler['usage'])} | `{command}`; run budgets/calls | {'; '.join(labeler['runs'])}; configured-rate ledger, thinking included, not reconciled billing-console cost |\n")
        rows.append(f"| 2026-10-10 | Agreement review exports | {report['items_all_agree']} items agree on all decisions; {report['items_any_disagreement']} have at least one disagreement. Full packet completed by both models. | `{command}`; docs/eval/agreement/model_comparison | agreement-model-comparison-20261010; no pooled mixed-task kappa |\n")
        with (ROOT / "docs/MEASUREMENTS.md").open("a", encoding="utf-8") as f:
            f.writelines(rows)
        marker.write_text(json.dumps({"recorded": True, "command": command}) + "\n")
    state.update({"status": "complete", "report": str(output / "README.md"),
                  "agreement": {k: {x: v[x] for x in ("n", "agreement", "kappa")} for k, v in report["tasks"].items()}})
    save(state)
    # Maintainer standing instruction: commit completed work; stage only owned outputs.
    owned = ["docs/MEASUREMENTS.md", str(STATUS.relative_to(ROOT)), str(output.relative_to(ROOT))]
    for name in JOBS:
        owned.extend(str((HERE / "model_runs" / name / f).relative_to(ROOT))
                     for f in ("answers.csv", "responses.jsonl", "metadata.json"))
    subprocess.run(["git", "add", "--", *owned], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", "Record independent model labels and Cohen agreement for Anne review packet", "--", *owned], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--interval-seconds", type=int, default=3600)
    parser.add_argument("--snapshot-only", action="store_true")
    args = parser.parse_args()
    paths.set_active_series("anne")
    state = json.loads(STATUS.read_text()) if STATUS.exists() else {"status": "running", "jobs": {}}
    while True:
        complete = True
        for name, spec in JOBS.items():
            directory = HERE / "model_runs" / name
            entry = state["jobs"].setdefault(name, {"pids": [], "restart_attempts": 0})
            meta = json.loads((directory / "metadata.json").read_text())
            responses = directory / "responses.jsonl"
            count = len(responses.read_text(encoding="utf-8").splitlines()) if responses.exists() else 0
            entry.update({"completed_items": count, "expected_items": meta["expected_items"], "model": meta["model"]})
            if meta.get("status") == "complete" and count == meta["expected_items"]:
                entry["status"] = "complete"
                continue
            complete = False
            entry["pids"] = [pid for pid in entry["pids"] if is_alive(pid)]
            if entry["pids"]:
                entry["status"] = "running"
                continue
            manifest = json.loads((paths.run_dir(meta["runs"][-1]) / "manifest.json").read_text())
            if args.snapshot_only:
                entry["status"] = "snapshot"
                continue
            if not manifest.get("finished_ts"):
                entry["status"] = "needs_attention: prior process ended without a finalized budget; no automatic paid restart"
                continue
            if entry["restart_attempts"] >= 3:
                entry["status"] = "needs_attention: hourly retries exhausted"
                continue
            cmd = [sys.executable, "-u", str(HERE / "run_model_labels.py"), "--role", spec["role"],
                   "--output", str(directory), "--jobs", "4", *spec["extra"]]
            with (directory / "hourly_resume.log").open("a", encoding="utf-8") as log:
                proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
            entry.update({"pids": [proc.pid], "restart_attempts": entry["restart_attempts"] + 1, "status": "running"})
        if complete and not args.snapshot_only:
            try:
                finish(state)
            except Exception as exc:
                state.update({"status": "needs_attention", "error": str(exc)})
                save(state)
            return
        state["status"] = "needs_attention" if all(e["status"].startswith("needs_attention") or e["status"] == "complete" for e in state["jobs"].values()) else "running"
        save(state)
        if args.snapshot_only or state["status"] == "needs_attention":
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
