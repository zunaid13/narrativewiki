#!/bin/sh
# 2026-10-02: A1 precision samples for the two prefix-built wikis (anne@p2 at t=2, anne@p3 at t=3).
# $0, local Ollama. Waits for anne_m3_gap_now.sh so the two do not share the GPU; the atomizer's
# calls are cached, so the inventory started (and stopped by a time limit) at 22:08 UTC resumes.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_a1_m3.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
until grep -q "m3 gap done" data/anne_m3_gap.out; do sleep 120; done
for c in "p2 2" "p3 3"; do set -- $c
  $PY scripts/eval/assertion_inventory.py "anne@$1" --upto $2 >> $O 2>&1 \
    && $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 --population all >> $O 2>&1 \
    && log "  m3 anne@$1 t=$2 (A1): ok" || log "  m3 anne@$1 t=$2 (A1) FAILED"
done
log "a1 m3 done"
