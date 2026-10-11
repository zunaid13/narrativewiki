#!/bin/sh
# 2026-10-07: second pass over the nine decontaminated cells of fix_v2_decon_rest.sh (B1 t=2..5, X2 t=1..5).
# Why a second pass: a long-context or full-text cell at t>=4 costs a little over the per-run stop
# (budget.hard_stop_usd, $10: B1 t=4 stopped at $10.10 with 29 of 33 pages written). That stop is resumable,
# every finished page is cached, and a rerun pays only for the pages left. fix_v2_decon_rest.sh treated any
# BudgetExceeded as final ("not retried"); here only the LIFETIME cap is final, a per-run stop is retried at once.
# It waits for the first pass to end (its lock), then runs the cells the log does not record as ok.
# Own output files per cell (data/_rest3_<SYS>_v<t>.log): a Python child appending to the shared log writes over
# other jobs' lines (ledger 2026-10-07; docs/eval/runners/log_keeper.sh restores them).
#   start:  sh docs/eval/runners/fix_v2_decon_rest2.sh       lock: data/fix_v2_decon.lock (after the first pass)
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/fix_v2_decon.out
S=anne-decon
RUNNER=decon
ROOM=decon
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
CAP="--set models.budget.lifetime_cap_usd=400"
export RUN_SERIES_429_RETRIES=0
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
LAST429=""
pick_api() {  # NEED WHAT (main project first, the temporary one only right after a 429 on it)
  while :; do
    if [ "$LAST429" != new ] && [ "$(room $ROOM)" -ge "$1" ]; then
      use_project new; probe && { LAST429=""; return 0; }
      grep -q 429 data/_probe_$RUNNER.out && log "  main project probe: 429"
    fi
    LAST429=""
    if [ "$(room old)" -ge "$1" ]; then use_project old; probe && return 0; fi
    [ "$(room $ROOM)" -ge "$1" ] || [ "$(room old)" -ge "$1" ] || { log "budget gate: no room for \$$1 ($2) - stopping"; exit 3; }
    sleep 600
  done
}
done_p() { grep -a -q "^[0-9:]* *$1: ok" $O; }
cell() {  # SYS T NEED: up to eight runs; a per-run stop resumes at once, the lifetime cap ends the cell
  SYS=$1; T=$2; NEED=$3
  done_p "$SYS t=$T" && return 0
  L="data/_rest3_${SYS}_v$T.log"
  for a in 1 2 3 4 5 6 7 8; do
    pick_api "$NEED" "$SYS t=$T"
    $PY scripts/baselines/run_baseline.py $S $SYS --upto $T $FLEX2 $CAP > "$L" 2>&1 && { log "$SYS t=$T: ok"; return 0; }
    if grep -q "lifetime cap is" "$L"; then log "  lifetime cap reached ($SYS t=$T): stopping"; return 1
    elif grep -q "hard stop is" "$L"; then log "  per-run stop ($SYS t=$T), run $a: resuming from the cache"
    elif grep -q "RESOURCE_EXHAUSTED\|: 429" "$L"; then log "  429 on $CUR ($SYS t=$T), run $a: switching"; [ "$CUR" = new ] && LAST429=new; sleep 60
    else log "  run $a failed ($CUR): $SYS t=$T (see $L)"; sleep 900
    fi
  done
  log "$SYS t=$T: FAILED"; return 1
}
score() {  # SERIES T ($0, local): as fix_v2_decon.sh, each step's output in the cell's own file
  done_p "m3 $1 t=$2" && return 0
  ensure_ollama
  SL="data/_score_$(echo $1 | tr @ _)_v$2.log"
  $PY scripts/eval/pipeline_page_leak.py "$1" --upto $2 > "$SL" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "$1" --upto $2 --n 40 >> "$SL" 2>&1 || log "  precision sample $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "$1" --upto $2 >> "${SL%.log}_r2.log" 2>&1 && $PY scripts/eval/assertion_precision.py "$1" --upto $2 --n 40 --population all >> "${SL%.log}_r2.log" 2>&1 && log "  m3 $1 t=$2: ok" || log "  m3 $1 t=$2 FAILED"
}
SLOCK=data/fix_v2_decon_score.lock
LOCK=data/fix_v2_decon_rest3.lock
while [ -f $LOCK ]; do sleep 120; done   # the first pass ends first: never two billed runners
echo "$(date -u +%m-%dT%H:%M) pid $$ (rest2)" > $LOCK
log "decon v2 rest3 (cap 400 for the last 16 pages, maintainer 2026-10-07: forget about all caps, keep going until finish): cells of B1 t=2..5 and X2 t=1..5 not yet ok, per-run stops resumed, commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check v2j > data/_rest3_freeze.log 2>&1 || { log "FREEZE CHECK FAILED - stopping"; rm -f $LOCK; exit 1; }
cell B1 5 3
cell X2 4 1; cell X2 5 4
log "decon v2 rest3 (cap 400 for the last 16 pages, maintainer 2026-10-07: forget about all caps, keep going until finish): billed steps done"
while [ -f $SLOCK ] || [ -f data/score_decon_worker2.lock ]; do sleep 300; done
for sys in b1 x2; do
  for t in 1 2 3 4 5; do
    U=$(echo $sys | tr a-z A-Z)
    grep -a -q "^[0-9:]* $U t=$t: ok" $O && score "$S@$sys" $t
  done
done
rm -f $LOCK
log "decon v2 rest3 (cap 400 for the last 16 pages, maintainer 2026-10-07: forget about all caps, keep going until finish) done"
