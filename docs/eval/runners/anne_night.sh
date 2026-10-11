#!/bin/sh
# 2026-10-01 15:20 UTC: the maintainer paused the day's runners (Ollama held the GPU) to resume
# overnight. Everything left, in one sequential job, under freeze anne-v1q (LLM cache makes
# finished work ~$0). Supersedes the unfinished tails of anne_after.sh, anne_b2_t1.sh, anne_a1_redo.sh.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_night.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
retry() { for a in 1 2 3; do "$@" >> $O 2>&1 && return 0; log "  attempt $a failed: $*"; sleep 900; done; return 1; }
score() {  # as anne_after.sh: leak screen, cited sample, M3 inventory + all-population sample ($0, local)
  $PY scripts/eval/pipeline_page_leak.py "anne@$1" --upto $2 > "data/_score_anne_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 >> "data/_score_anne_$1_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "anne@$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 anne@$1 t=$2: ok" || log "  m3 anne@$1 t=$2 FAILED"
}
cell() { S=$1; T=$2; shift 2
  retry $PY scripts/baselines/run_baseline.py anne $S --upto $T "$@" && log "$S t=$T: ok" || { log "$S t=$T: FAILED"; return 1; }
  score "$(echo $S | tr A-Z a-z)" $T
}
log "night start, commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check anne-v1q >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
$PY scripts/run_series.py anne@p3 --upto 3 --from leak-t3 >> $O 2>&1 && log "A1 t=3 (redo): ok" || log "A1 t=3 (redo) checks FAILED"
score b3 5
for t in 1 2 3 4 5; do cell B4 $t --budget-tokens 20000; done
cell B2 1 --chunk-words 150 --budget-tokens 20000
log "night done"
