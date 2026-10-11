#!/bin/sh
# 2026-10-01: B2 t=1 failed all 3 attempts inside the 03-07 UTC Vertex squeeze (Standard and Flex
# both 429). Waits for anne_after.sh to finish (never two writers on one tree), then re-runs it from
# the LLM cache and scores it exactly as anne_after.sh's score() does. Orchestration only.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_after.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
until grep -q "after-chain fixes done" $O; do sleep 300; done
$PY scripts/papers/freeze.py check anne-v1p >> $O 2>&1 || { log "B2 t=1 rerun: FREEZE CHECK FAILED"; exit 1; }
for a in 1 2 3; do
  $PY scripts/baselines/run_baseline.py anne B2 --upto 1 --chunk-words 150 --budget-tokens 20000 >> $O 2>&1 && break
  log "  B2 t=1 rerun attempt $a failed"; [ $a = 3 ] && { log "B2 t=1 rerun: FAILED"; exit 1; }; sleep 900
done
log "B2 t=1 (rerun): ok"
$PY scripts/eval/pipeline_page_leak.py anne@b2 --upto 1 > data/_score_anne_b2_v1.log 2>&1 || log "  leak-screen b2 t=1 FAILED"
$PY scripts/eval/assertion_precision.py anne@b2 --upto 1 --n 40 >> data/_score_anne_b2_v1.log 2>&1 || log "  precision sample b2 t=1 FAILED"
$PY scripts/eval/assertion_inventory.py anne@b2 --upto 1 >> $O 2>&1 \
  && $PY scripts/eval/assertion_precision.py anne@b2 --upto 1 --n 40 --population all >> $O 2>&1 \
  && log "  m3 anne@b2 t=1: ok" || log "  m3 anne@b2 t=1 FAILED"
