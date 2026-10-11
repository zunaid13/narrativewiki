#!/bin/sh
# 2026-10-07 (Phase 34): the nine decontaminated-Anne cells that fix_v2_decon.sh could not build, because the
# lifetime cap (318) was reached on 2026-10-06 23:24 UTC: long context (B1) t=2..5 and full text (X2) t=1..5.
# Maintainer, 2026-10-07, asked whether to raise the cap for them: "Raise to $390 and build".
# The cap is raised for these commands only (--set models.budget.lifetime_cap_usd=390): config/models.yaml is
# under freeze v2j and stays as frozen. Same commands, settings, log file and log lines as fix_v2_decon.sh, so
# its scoring instance (SCORE_ONLY) scores a cell built here when it reaches it; whatever it has passed by then
# is scored at the end of this script. Restartable: a cell the log records as ok is skipped.
#   start:  sh docs/eval/runners/fix_v2_decon_rest.sh      lock: data/fix_v2_decon.lock
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/fix_v2_decon.out
S=anne-decon
RUNNER=decon
ROOM=decon
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
CAP="--set models.budget.lifetime_cap_usd=390"
export RUN_SERIES_429_RETRIES=0
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
LAST429=""
pick_api() {  # NEED WHAT (as fix_v2_decon.sh: main project first, the temporary one only right after a 429 on it)
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
retry() {  # NEED WHAT CMD...: six attempts; after a 429 re-pick within a minute, otherwise wait 15 min
  NEED=$1; WHAT=$2; shift 2
  for a in 1 2 3 4 5 6; do
    pick_api "$NEED" "$WHAT"
    mark=$(wc -l < $O)
    "$@" >> $O 2>&1 && return 0
    if tail -n +$((mark + 1)) $O | grep -q "BudgetExceeded"; then
      log "  budget stop ($WHAT): not retried"; return 1
    elif tail -n +$((mark + 1)) $O | grep -q "RESOURCE_EXHAUSTED\|: 429"; then
      log "  429 on $CUR ($WHAT), attempt $a: switching"; [ "$CUR" = new ] && LAST429=new; sleep 60
    else
      log "  attempt $a failed ($CUR): $WHAT"; sleep 900
    fi
  done
  return 1
}
done_p() { grep -q "^[0-9:]* *$1: ok" $O; }
cell() {  # SYS T NEED [args]: one billed baseline cell
  SYS=$1; T=$2; NEED=$3; shift 3
  done_p "$SYS t=$T" && return 0
  retry $NEED "$SYS t=$T" $PY scripts/baselines/run_baseline.py $S $SYS --upto $T "$@" && log "$SYS t=$T: ok" || log "$SYS t=$T: FAILED"
}
score() {  # SERIES T ($0, local): leak screen, cited sample, full inventory and its 40-atom sample
  done_p "m3 $1 t=$2" && return 0
  ensure_ollama
  $PY scripts/eval/pipeline_page_leak.py "$1" --upto $2 > "data/_score_$(echo $1 | tr @ _)_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "$1" --upto $2 --n 40 >> "data/_score_$(echo $1 | tr @ _)_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 $1 t=$2: ok" || log "  m3 $1 t=$2 FAILED"
}
SLOCK=data/fix_v2_decon_score.lock
LOCK=data/fix_v2_decon.lock
[ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "decon v2 rest: B1 t=2..5 and X2 t=1..5 under a lifetime cap of 390 for these commands (maintainer 2026-10-07), commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check v2j >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; rm -f $LOCK; exit 1; }
# ---- billed ----
for t in 2 3 4 5; do cell B1 $t 12 $FLEX2 $CAP; done
for t in 1 2 3 4 5; do cell X2 $t 12 $FLEX2 $CAP; done
log "decon v2 rest: billed steps done"
# ---- $0 local scoring (GPU) of whatever the scoring instance did not reach ----
while [ -f $SLOCK ]; do sleep 300; done  # never two scorers on one cell: the SCORE_ONLY instance ends first
for sys in b1 x2; do
  for t in 1 2 3 4 5; do
    U=$(echo $sys | tr a-z A-Z)
    grep -q "^[0-9:]* $U t=$t: ok" $O && score "$S@$sys" $t
  done
done
rm -f $LOCK
log "decon v2 rest done"
