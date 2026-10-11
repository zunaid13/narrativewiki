#!/bin/sh
# 2026-10-01: A1 t=2 failed 3x at `graph` (guard false positive, fixed in freeze anne-v1p) and the
# chain moved on. Waits for anne_resume.sh to end (one A1 job at a time), then resumes A1 t=2 from
# graph; everything before graph is on disk and cached. Orchestration only.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_a1_t2.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
n0=$(wc -l < data/anne_resume.out)
until tail -n +$((n0 + 1)) data/anne_resume.out | grep -qE "all done, spent|- stopping"; do sleep 300; done
log "chain finished; A1 t=2 from graph"
$PY scripts/papers/freeze.py check anne-v1p >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
for a in 1 2 3; do
  $PY scripts/run_series.py anne@p2 --upto 2 --from graph >> $O 2>&1 && { log "A1 t=2: ok"; exit 0; }
  log "A1 t=2: FAILED (attempt $a)"
done
