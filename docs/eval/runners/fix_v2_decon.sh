#!/bin/sh
# 2026-10-05 (Phase 34): the whole decontaminated-Anne matrix with the v2 code, unattended. Maintainer 11:20 UTC:
# "just run a full script for the api and then stop auditing for a while. the full api things should be complete
# by the script running". Every billed step first (gazetteer, B5 build, then X1, B2, B3, B1, X2 and B4 from the
# v2 decon graph, t=1..5), every $0 local scoring step after, so the API work ends as early as it can.
# Same commands and settings as anne_decon_new.sh (v1, stopped 2026-10-04 at events). Room key "decon".
# Project choice as fix_v2_anne_resume4.sh: main first, the temporary project only right after a 429 on it.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
PYB3=.venv-b3/Scripts/python.exe
O=data/fix_v2_decon.out
S=anne-decon
V=anne-decon@v2
RUNNER=decon
ROOM=decon
C12="--set models.profiles.vertex_flash.concurrency=12"
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
export RUN_SERIES_429_RETRIES=0
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
LAST429=""
pick_api() {  # NEED WHAT
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
    if tail -n +$((mark + 1)) $O | grep -q "RESOURCE_EXHAUSTED\|: 429"; then
      log "  429 on $CUR ($WHAT), attempt $a: switching"; [ "$CUR" = new ] && LAST429=new; sleep 60
    else
      log "  attempt $a failed ($CUR): $WHAT"; sleep 900
    fi
  done
  return 1
}
build() {  # the B5 build, resumed at the step that failed; every finished call is cached
  FROM=scenes-v1
  for a in 1 2 3 4 5 6 7 8; do
    pick_api 25 "B5 decon build"
    mark=$(wc -l < $O)
    $PY scripts/run_series.py $V --upto 5 --from $FROM --to audit-eval $C12 >> $O 2>&1 && return 0
    F=$(tail -n +$((mark + 1)) $O | grep -oE "^[0-9:]+ [a-z0-9-]+: (FAILED|429 \(RESOURCE)" | tail -1 | awk '{print $2}' | tr -d :)
    [ -n "$F" ] && FROM=$F
    if tail -n +$((mark + 1)) $O | grep -q "RESOURCE_EXHAUSTED\|: 429"; then
      log "  429 on $CUR (B5 decon at $FROM), attempt $a: switching"; [ "$CUR" = new ] && LAST429=new; sleep 60
    else
      log "  B5 decon attempt $a failed ($CUR), resume at $FROM"; sleep 900
    fi
  done
  return 1
}
# Restartable since the power cut of 2026-10-06 05:32 UTC: a step this log already records as ok is not run
# again, so after a dead run remove the lock and start the same script. SCORE_ONLY=1 starts a second
# instance that only scores the cells already built ($0, GPU) while this one goes on with the billed steps.
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
LOCK=data/fix_v2_decon.lock; [ -n "$SCORE_ONLY" ] && LOCK=$SLOCK
[ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "decon v2 matrix${SCORE_ONLY:+ (scoring of built cells only)}: billed steps first, scoring after (main project first, temporary on 429), commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check v2j >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
if [ -z "$SCORE_ONLY" ]; then
# ---- billed ----
done_p "B5 (decon v2) v1-5" || {
  retry 5 "gazetteer" $PY -m narrativewiki.cli gazetteer --series $V --volumes 1-5 --force $C12 && log "gazetteer: ok" || { log "gazetteer FAILED - stopping"; exit 1; }
  $PY scripts/eval/entity_merge_audit.py $S $V >> $O 2>&1
  build && log "B5 (decon v2) v1-5: ok" || { log "B5 (decon v2) FAILED - stopping"; exit 1; }
  $PY scripts/eval/remap_page_map.py anne@v2 $V >> $O 2>&1 || log "  page map FAILED (B4 falls back to exact names)"
}
for t in 1 2 3 4 5; do cell X1 $t 2; done
for t in 1 2 3 4 5; do cell B2 $t 3 --chunk-words 150 --budget-tokens 20000; done
for t in 1 2 3 4 5; do cell B4 $t 3 --graph $V --budget-tokens 20000; done
ensure_ollama  # B3 embeds with the local bge-m3
for t in 1 2 3 4 5; do
  done_p "B3 t=$t" && continue
  retry 4 "B3 t=$t" $PYB3 scripts/baselines/b3_lightrag.py $S --upto $t --mode mix --budget-tokens 20000 && log "B3 t=$t: ok" || log "B3 t=$t: FAILED"
done
for t in 1 2 3 4 5; do cell B1 $t 12 $FLEX2; done
for t in 1 2 3 4 5; do cell X2 $t 12 $FLEX2; done
log "decon v2: billed steps done"
while [ -f $SLOCK ]; do sleep 300; done  # never two scorers at once: the SCORE_ONLY instance ends first
fi
# ---- $0 local scoring (GPU) ----
for t in 1 2 3 4 5; do score $V $t; done
for sys in x1 b2 b4-v2 b3 b1 x2; do
  for t in 1 2 3 4 5; do
    U=$(echo $sys | cut -d- -f1 | tr a-z A-Z)
    grep -q "^[0-9:]* $U t=$t: ok" $O && score "$S@$sys" $t
  done
done
[ -n "$SCORE_ONLY" ] && { rm -f $SLOCK; log "decon v2: scoring of built cells done"; exit 0; }
log "decon v2 done"
