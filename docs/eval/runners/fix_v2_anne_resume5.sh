#!/bin/sh
# 2026-10-05 (Phase 34): resume of the anne@v2 run after the PC shut down at ~10:05 UTC; the B5 v2 build had finished (10:03), so this starts at the GPU scoring (m3) and never re-runs run_series (a re-render would make every label stale). MAIN project first for B4.
# Maintainer 03:00 UTC: "probe the arnababir's api key whenever possible.. as soon as 429 is lifted, you should
# attempt to use that one (i think this is because of daily limits)". So every billed attempt probes the main
# project (min2web-nsyss-4) first; only the attempt right after a 429 on it goes to the temporary project, and
# the next attempt tries the main one again. run_series hands a 429 back at once (RUN_SERIES_429_RETRIES=0)
# instead of waiting 45 min on the refusing project. Same model on both: only the bill changes.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/fix_v2_anne.out
S=anne@v2
RUNNER=fix
ROOM=new
C8="--set models.profiles.vertex_flash.concurrency=8"
export RUN_SERIES_429_RETRIES=0
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
LAST429=""
pick_api() {  # NEED WHAT
  while :; do
    if [ "$LAST429" != new ] && [ "$(room new)" -ge "$1" ]; then
      use_project new; probe && { LAST429=""; return 0; }
      grep -q 429 data/_probe_$RUNNER.out && log "  main project probe: 429"
    fi
    LAST429=""
    if [ "$(room old)" -ge "$1" ]; then use_project old; probe && return 0; fi
    [ "$(room new)" -ge "$1" ] || [ "$(room old)" -ge "$1" ] || { log "budget gate: no room for \$$1 ($2) - stopping"; exit 3; }
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
      log "  attempt $a failed ($CUR): $*"; sleep 900
    fi
  done
  return 1
}
m3() {  # $1 series, $2 t ($0, local): the full assertion inventory and its 40-atom precision sample
  ensure_ollama
  $PY scripts/eval/assertion_inventory.py "$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 $1 t=$2: ok" || log "  m3 $1 t=$2 FAILED"
}
LOCK=data/fix_v2_anne_resume5.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "fix v2 anne RESUME5 at m3 after the shutdown (B5 v2 build done 10:03), commit $(git rev-parse --short HEAD)"
# B4 generation is billed and API-bound, m3 is local and GPU-bound: run them side by side, then B4's own GPU steps.
( for t in 1 2 3 4 5; do
    retry 3 "B4 v2 t=$t" $PY scripts/baselines/run_baseline.py anne B4 --graph $S --upto $t --budget-tokens 20000 && log "B4 v2 t=$t: ok" || log "B4 v2 t=$t: FAILED"
  done ) &
B4PID=$!
for t in 1 2 3 4 5; do m3 $S $t; done
wait $B4PID
for t in 1 2 3 4 5; do
  grep -q "B4 v2 t=$t: ok" $O || continue
  ensure_ollama
  $PY scripts/eval/pipeline_page_leak.py anne@b4-v2 --upto $t > "data/_score_anne_b4-v2_v$t.log" 2>&1 || log "  leak-screen b4-v2 t=$t FAILED"
  m3 anne@b4-v2 $t
done
log "fix v2 anne done"
