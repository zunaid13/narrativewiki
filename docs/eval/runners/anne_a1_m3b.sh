#!/bin/sh
# 2026-10-02: redo of the A1 precision samples after C24 (the inventory no longer stops on a sentence
# the local atomizer cannot parse). Waits for anne_a1_m3.sh; finished atomizer calls are cached.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_a1_m3.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
until grep -q "a1 m3 done" $O; do sleep 120; done
for c in "p2 2" "p3 3"; do set -- $c
  [ -f "docs/eval/precision/anne@$1_v$2_all.jsonl" ] && continue
  $PY scripts/eval/assertion_inventory.py "anne@$1" --upto $2 >> $O 2>&1 \
    && $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 --population all >> $O 2>&1 \
    && log "  m3 anne@$1 t=$2 (A1 redo): ok" || log "  m3 anne@$1 t=$2 (A1 redo) FAILED"
done
log "a1 m3 redo done"
