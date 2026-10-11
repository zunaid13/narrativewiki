#!/bin/sh
# Re-run B3 t=2 (built on an incomplete LightRAG index before freeze anne-v1e) once the baselines
# chain has left B3; t=2's index is repaired in place (FAILED chapters re-inserted), then re-scored.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe; PYB3=.venv-b3/Scripts/python.exe
O=data/anne_baselines.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
n=0; until grep -qE "B1 t=1|B3 t=[0-9]: FAILED" $O; do sleep 120; n=$((n+1)); [ $n -gt 360 ] && { log "B3 redo: chain not past B3 after 12h - skipped"; exit 1; }; done
$PY scripts/papers/freeze.py check anne-v1e >> $O 2>&1 || { log "B3 redo: FREEZE CHECK FAILED - stopping"; exit 1; }
$PYB3 scripts/baselines/b3_lightrag.py anne --upto 2 --mode mix --budget-tokens 20000 >> $O 2>&1 && log "B3 t=2 redo (anne-v1e): ok" || log "B3 t=2 redo (anne-v1e): FAILED"
$PY scripts/eval/pipeline_page_leak.py anne@b3 --upto 2 > data/_score_anne_b3_v2.log 2>&1 || log "  leak-screen b3 t=2 FAILED"
$PY scripts/eval/assertion_precision.py anne@b3 --upto 2 --n 40 >> data/_score_anne_b3_v2.log 2>&1 || log "  precision sample b3 t=2 FAILED"
