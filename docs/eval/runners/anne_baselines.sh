#!/bin/sh
# Anne baseline cells (S11), all on freeze anne-v1. Orchestration only; every command is a frozen script.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe; PYB3=.venv-b3/Scripts/python.exe
O=data/anne_baselines.out
FLEX="--set models.profiles.vertex_flash.options.shared_request_type=flex --set models.profiles.vertex_flash.price_per_mtok.input=0.375 --set models.profiles.vertex_flash.price_per_mtok.output=1.875 --set models.profiles.vertex_flash.concurrency=2"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
$PY scripts/papers/freeze.py check anne-v1 >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
score() {  # $1 = system (lowercase), $2 = t : local scoring, $0
  $PY scripts/eval/pipeline_page_leak.py "anne@$1" --upto $2 > "data/_score_anne_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 >> "data/_score_anne_$1_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
}
cell() {  # $1 system upper, $2 t, rest = extra args
  S=$1; T=$2; shift 2
  $PY scripts/baselines/run_baseline.py anne $S --upto $T "$@" >> $O 2>&1 && log "$S t=$T: ok" || log "$S t=$T: FAILED"
  score "$(echo $S | tr A-Z a-z)" $T
}
log "baselines start, commit $(git rev-parse --short HEAD)"
for t in 1 2 3 4 5; do cell X1 $t; done
for t in 1 2 3 4 5; do cell B2 $t --chunk-words 150 --budget-tokens 20000; done
for t in 1 2 3 4 5; do
  $PYB3 scripts/baselines/b3_lightrag.py anne --upto $t --mode mix --budget-tokens 20000 >> $O 2>&1 && log "B3 t=$t: ok" || { log "B3 t=$t: FAILED (later cutoffs need it)"; break; }
  score b3 $t
done
for t in 1 2 3 4 5; do cell B1 $t $FLEX; done
for t in 1 2 3 4 5; do cell X2 $t $FLEX; done
n=0; until grep -q "all steps done" data/anne/_driver/s01_3.6.out 2>/dev/null; do sleep 60; n=$((n+1)); [ $n -gt 480 ] && { log "S01 not finished after 8h - B4 skipped"; exit 1; }; done
log "S01 finished; B4 uses the new Anne graph"
for t in 1 2 3 4 5; do cell B4 $t --budget-tokens 20000; done
log "baselines done"
$PY scripts/eval/run_cost.py anne@x1 >> $O 2>&1; for s in b1 b2 b3 b4 x2; do $PY scripts/eval/run_cost.py anne@$s >> $O 2>&1; done
