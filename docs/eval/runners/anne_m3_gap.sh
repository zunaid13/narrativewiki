#!/bin/sh
# 2026-10-01: B1 t=5 and X2 t=2..5 were built by the chain before the M3 all-assertion sampler ran on
# them, so they have no precision/<cell>_all.jsonl. Waits for anne_night.sh ("night done"), then
# inventories and samples them ($0, local Ollama). Orchestration only.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_night.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
until grep -q "night done" $O; do sleep 300; done
for c in "b1 5" "x2 2" "x2 3" "x2 4" "x2 5"; do set -- $c
  $PY scripts/eval/assertion_inventory.py "anne@$1" --upto $2 >> $O 2>&1 \
    && $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 --population all >> $O 2>&1 \
    && log "  m3 anne@$1 t=$2 (gap): ok" || log "  m3 anne@$1 t=$2 (gap) FAILED"
done
log "m3 gap done"
