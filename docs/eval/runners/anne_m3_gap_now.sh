#!/bin/sh
# 2026-10-02 (20:50 UTC 10-01): Vertex answers 429 on Standard and Flex, so the night runner is stalled
# and the GPU is idle. Run anne_m3_gap.sh's five cells now ($0, local Ollama) instead of after
# "night done"; the waiting anne_m3_gap.sh was stopped so it does not repeat them. Orchestration only.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_m3_gap.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
for c in "b1 5" "x2 2" "x2 3" "x2 4" "x2 5"; do set -- $c
  $PY scripts/eval/assertion_inventory.py "anne@$1" --upto $2 >> $O 2>&1 \
    && $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 --population all >> $O 2>&1 \
    && log "  m3 anne@$1 t=$2 (gap): ok" || log "  m3 anne@$1 t=$2 (gap) FAILED"
done
log "m3 gap done"
