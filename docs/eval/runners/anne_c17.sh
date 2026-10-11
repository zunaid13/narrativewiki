#!/bin/sh
# 2026-10-01 (CHANGES C17): rebuild M3 inventories with the cited-quote fix and re-draw each labelled
# sample with --resample-from (rows still in the pool keep their labels; the rest are fresh draws).
# Atomizer calls are cached ($0, local). Touches no tree the night run writes (B4, B2 t=1).
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_c17.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
$PY scripts/papers/freeze.py check anne-v1r >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
for c in "anne 1" "anne 2" "anne 3" "anne 4" "anne 5" "anne@x1 1" "anne@x1 2" "anne@x1 3" "anne@x1 4" "anne@x1 5" \
         "anne@x2 1" "anne@b1 1" "anne@b1 2" "anne@b1 3" "anne@b1 4" "anne@b2 2" "anne@b2 3" "anne@b2 4" \
         "anne@b2 5" "anne@b3 1" "anne@b3 2" "anne@b3 3" "anne@b3 4" "anne@b3 5"; do set -- $c
  F="docs/eval/precision/$1_v$2_all.jsonl"; OLD="docs/eval/precision/$1_v$2_all_preC17.jsonl"
  [ -f "$OLD" ] || cp "$F" "$OLD"
  rm -f "$F"
  $PY scripts/eval/assertion_inventory.py "$1" --upto $2 >> $O 2>&1 || { log "inventory $1 t=$2 FAILED"; cp "$OLD" "$F"; continue; }
  $PY scripts/eval/assertion_precision.py "$1" --upto $2 --n 40 --population all --resample-from "$OLD" >> $O 2>&1 \
    && log "c17 $1 t=$2: ok" || { log "c17 $1 t=$2 sample FAILED"; cp "$OLD" "$F"; }
done
log "c17 done"
