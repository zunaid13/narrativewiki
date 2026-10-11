#!/bin/sh
# 2026-10-04: the held-out Oz matrix from B3 on (B5, X1, B2 t=1..5 built and scored). Same commands and
# settings as oz_heldout_resume.sh; only the Vertex project changes (vertex.sh): the arnababir1 project,
# the temporary account's project on a 429. Paused 12:37 UTC by the agent before B3 (no call in flight).
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
PYB3=.venv-b3/Scripts/python.exe
O=data/oz_heldout.out
S=oz
RUNNER=oz
ROOM=new
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
score() {  # $1 system (lowercase), $2 t ($0, local)
  ensure_ollama
  $PY scripts/eval/pipeline_page_leak.py "$S@$1" --upto $2 > "data/_score_${S}_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "$S@$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "$S@$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 $S@$1 t=$2: ok" || log "  m3 $S@$1 t=$2 FAILED"
}
cell() { SYS=$1; T=$2; NEED=$3; shift 3
  retry $NEED "$SYS t=$T" $PY scripts/baselines/run_baseline.py $S $SYS --upto $T "$@" && log "$SYS t=$T: ok" || { log "$SYS t=$T: FAILED"; return 1; }
  score "$(echo $SYS | tr A-Z a-z)" $T
}
LOCK=data/oz_heldout.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "oz RESUME at B3 on the arnababir1 project (temporary on 429), commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check oz-v3 >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
for t in 1 2 3 4 5; do
  retry 3 "B3 t=$t" $PYB3 scripts/baselines/b3_lightrag.py $S --upto $t --mode mix --budget-tokens 20000 && { log "B3 t=$t: ok"; score b3 $t; } || log "B3 t=$t: FAILED"
done
for t in 1 2 3 4 5; do cell B1 $t 8 $FLEX2; done
for t in 1 2 3 4 5; do cell X2 $t 10 $FLEX2; done
log "oz done"
