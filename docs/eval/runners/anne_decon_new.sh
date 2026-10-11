#!/bin/sh
# 2026-10-04: the decontaminated Anne matrix from its gazetteer step on, on the arnababir1 project (the
# temporary account's on a 429; vertex.sh), budget room "decon" = the $200 project minus what Oz has not
# spent yet of its estimate (Oz first). Paraphrase and both memorization probes are done (MEASUREMENTS
# 2026-10-03); the gazetteer stopped by hand 2026-10-03 19:45 UTC and restarts with --force (its calls
# are cached). Same commands and settings as anne_decon.sh from line 57 on.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
PYB3=.venv-b3/Scripts/python.exe
O=data/anne_decon.out
S=anne-decon
RUNNER=decon
ROOM=decon
C12="--set models.profiles.vertex_flash.concurrency=12"
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
score() {  # $1 system (lowercase), $2 t ($0, local)
  ensure_ollama
  $PY scripts/eval/pipeline_page_leak.py "$S@$1" --upto $2 > "data/_score_${S}_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "$S@$1" --upto $2 --n 40 >> "data/_score_${S}_$1_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "$S@$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "$S@$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 $S@$1 t=$2: ok" || log "  m3 $S@$1 t=$2 FAILED"
}
cell() { SYS=$1; T=$2; NEED=$3; shift 3
  retry $NEED "$SYS t=$T" $PY scripts/baselines/run_baseline.py $S $SYS --upto $T "$@" && log "$SYS t=$T: ok" || { log "$SYS t=$T: FAILED"; return 1; }
  score "$(echo $SYS | tr A-Z a-z)" $T
}
LOCK=data/anne_decon.lock; [ -f $LOCK ] && { log "decon already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "decon RESUME at gazetteer on the arnababir1 project (temporary on 429), commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check oz-v3 >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
retry 5 "gazetteer" $PY -m narrativewiki.cli gazetteer --series $S --volumes 1-5 --force $C12 && log "gazetteer: ok" || { log "gazetteer FAILED - stopping"; exit 1; }
retry 25 "B5 build" $PY scripts/run_series.py $S --upto 5 $C12 && log "B5 (decon) v1-5: ok" || { log "B5 (decon) FAILED - stopping"; exit 1; }
ensure_ollama
for t in 1 2 3 4 5; do $PY scripts/eval/assertion_inventory.py $S --upto $t >> $O 2>&1 && $PY scripts/eval/assertion_precision.py $S --upto $t --n 40 --population all >> $O 2>&1 && log "  m3 $S t=$t: ok" || log "  m3 $S t=$t FAILED"; done
for t in 1 2 3 4 5; do cell X1 $t 2; done
for t in 1 2 3 4 5; do cell B2 $t 3 --chunk-words 150 --budget-tokens 20000; done
for t in 1 2 3 4 5; do cell B4 $t 3 --budget-tokens 20000; done
for t in 1 2 3 4 5; do
  retry 4 "B3 t=$t" $PYB3 scripts/baselines/b3_lightrag.py $S --upto $t --mode mix --budget-tokens 20000 && { log "B3 t=$t: ok"; score b3 $t; } || log "B3 t=$t: FAILED"
done
for t in 1 2 3 4 5; do cell B1 $t 12 $FLEX2; done
for t in 1 2 3 4 5; do cell X2 $t 12 $FLEX2; done
log "decon done"
