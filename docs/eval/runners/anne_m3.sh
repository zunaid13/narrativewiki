#!/bin/sh
# 2026-09-30: M3 (setup §5) is precision over ALL sampled assertions, uncited included. The resume
# chain's `score` samples cited lines only (X1: pool 0 at every t). This runs, per cell, the
# assertion inventory and a 40-assertion `--population all` sample. Local atomizer only, $0.
# Start it while the chain waits on Vertex (B1/X2), not beside the chain's own scoring.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_m3.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
for s in anne anne@x1 anne@b2 anne@b3 anne@b4; do
  for t in 1 2 3 4 5; do
    $PY scripts/eval/assertion_inventory.py $s --upto $t >> $O 2>&1 || { log "inventory $s t=$t FAILED"; continue; }
    $PY scripts/eval/assertion_precision.py $s --upto $t --n 40 --population all >> $O 2>&1 \
      && log "m3 $s t=$t: ok" || log "m3 sample $s t=$t FAILED"
  done
done
log "m3 all done"
