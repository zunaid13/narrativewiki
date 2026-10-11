#!/bin/sh
# 2026-10-02: the HELD-OUT work (Oz, books 1-5), plan 0015 step 7 / review concern 10. Maintainer: "pick
# the best option, budget will be increased later" -> the held-out matrix runs before the decontaminated
# one: it fits in what is left under the $300 stop (estimate ~$70 with X2), it answers the review's
# generalisation concern directly, and no model stage has ever run on Oz (data/oz/_runs empty at freeze
# oz-v1). Starts after anne_rest.sh logs "night done" (the current paper's cells come first).
# Same commands and settings as the Anne cells; orchestration only, every command is a frozen script.
# Order: cheapest first, the two long-context systems last, so the budget gate stops where it must.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
PYB3=.venv-b3/Scripts/python.exe
O=data/oz_heldout.out
S=oz
C12="--set models.profiles.vertex_flash.concurrency=12"
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
room() { $PY -c "
import glob,json
t=sum((json.loads(l).get('cost_usd') or 0) for f in glob.glob('data/*/_runs/*/calls.jsonl') for l in open(f,encoding='utf-8'))
print(int(313 - (t - 19.85)))"; }
gate() { r=$(room); [ "$r" -ge "$1" ] || { log "budget gate: room \$$r < \$$1 needed for $2 - stopping (ask the maintainer for more budget)"; exit 3; }; }
wait_api() { until $PY scripts/eval/vertex_probe.py >> $O 2>&1; do sleep 600; done; }
retry() { for a in 1 2 3; do "$@" >> $O 2>&1 && return 0; log "  attempt $a failed: $*"; sleep 900; done; return 1; }
score() {  # $1 system (lowercase), $2 t ($0, local)
  $PY scripts/eval/pipeline_page_leak.py "$S@$1" --upto $2 > "data/_score_${S}_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "$S@$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "$S@$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 $S@$1 t=$2: ok" || log "  m3 $S@$1 t=$2 FAILED"
}
cell() { SYS=$1; T=$2; NEED=$3; shift 3; gate $NEED "$SYS t=$T"; wait_api
  retry $PY scripts/baselines/run_baseline.py $S $SYS --upto $T "$@" && log "$SYS t=$T: ok" || { log "$SYS t=$T: FAILED"; return 1; }
  score "$(echo $SYS | tr A-Z a-z)" $T
}
LOCK=data/oz_heldout.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
# 2026-10-02 09:50 UTC, maintainer: "start everything" -> no longer waits for anne_rest.sh; runs beside it and
# beside anne_decon.sh (which keeps a reserve for this matrix in its budget gate).
log "oz start, commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check oz-v2 >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
gate 3 "gazetteer"; wait_api
retry $PY -m narrativewiki.cli gazetteer --series $S --volumes 1-5 $C12 && log "gazetteer: ok" || { log "gazetteer FAILED - stopping"; exit 1; }
gate 18 "B5 build"; wait_api
retry $PY scripts/run_series.py $S --upto 5 $C12 && log "B5 (oz) v1-5: ok" || { log "B5 (oz) FAILED - stopping"; exit 1; }
for t in 1 2 3 4 5; do $PY scripts/eval/assertion_inventory.py $S --upto $t >> $O 2>&1 && $PY scripts/eval/assertion_precision.py $S --upto $t --n 40 --population all >> $O 2>&1 && log "  m3 $S t=$t: ok" || log "  m3 $S t=$t FAILED"; done
for t in 1 2 3 4 5; do cell X1 $t 1; done
for t in 1 2 3 4 5; do cell B2 $t 2 --chunk-words 150 --budget-tokens 20000; done
for t in 1 2 3 4 5; do gate 3 "B3 t=$t"; wait_api
  retry $PYB3 scripts/baselines/b3_lightrag.py $S --upto $t --mode mix --budget-tokens 20000 && { log "B3 t=$t: ok"; score b3 $t; } || log "B3 t=$t: FAILED"
done
for t in 1 2 3 4 5; do cell B1 $t 8 $FLEX2; done
for t in 1 2 3 4 5; do cell X2 $t 10 $FLEX2; done
log "oz done"
