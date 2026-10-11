#!/bin/sh
# 2026-10-02 (21:35 UTC 10-01): supersedes the tail of anne_night.sh, which was failing its cells during a
# Vertex 429 outage (both tiers). What is left on the original text -- B4 t=3..5, B2 t=1 -- each after a
# tiny availability probe (scripts/eval/vertex_probe.py, one call per 10 min while the provider is down),
# then the decontaminated matrix (anne_decon.sh, map v2 / C21). Sequential: one API runner at a time.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_night.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
wait_api() { until $PY scripts/eval/vertex_probe.py >> $O 2>&1; do sleep 600; done; }
retry() { for a in 1 2 3; do wait_api; "$@" >> $O 2>&1 && return 0; log "  attempt $a failed: $*"; sleep 300; done; return 1; }
score() {  # as anne_night.sh: leak screen, cited sample, M3 inventory + all-population sample ($0, local)
  $PY scripts/eval/pipeline_page_leak.py "anne@$1" --upto $2 > "data/_score_anne_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 >> "data/_score_anne_$1_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "anne@$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 anne@$1 t=$2: ok" || log "  m3 anne@$1 t=$2 FAILED"
}
cell() { S=$1; T=$2; shift 2
  retry $PY scripts/baselines/run_baseline.py anne $S --upto $T "$@" && log "$S t=$T: ok" || { log "$S t=$T: FAILED"; return 1; }
  score "$(echo $S | tr A-Z a-z)" $T
}
log "rest start, commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check anne-v1x >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
for t in 3 4 5; do cell B4 $t --budget-tokens 20000; done
cell B2 1 --chunk-words 150 --budget-tokens 20000
log "night done"
sh docs/eval/runners/anne_decon.sh
