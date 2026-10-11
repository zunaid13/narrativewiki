#!/bin/sh
# 2026-10-05: the B4 v2 generation half of fix_v2_anne_resume5.sh, re-run after room.py crashed on a ledger line the
# power cut left as NUL bytes (11:20 UTC budget-gate stop). Same log, so resume5 scores these cells after its m3 loop.
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
LOCK=data/fix_v2_anne_b4.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "B4 v2 generation restart after the room.py fix, commit $(git rev-parse --short HEAD)"
for t in 1 2 3 4 5; do
  retry 3 "B4 v2 t=$t" $PY scripts/baselines/run_baseline.py anne B4 --graph $S --upto $t --budget-tokens 20000 && log "B4 v2 t=$t: ok" || log "B4 v2 t=$t: FAILED"
done
log "B4 v2 generation done"
