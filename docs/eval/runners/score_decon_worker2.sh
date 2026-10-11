#!/bin/sh
# 2026-10-07: a second local scoring worker for the decontaminated matrix (maintainer: "you can parallelize
# local gpu if needed"). $0, no billed call. It scores the cells named on the command line, in that order, with
# the same three commands and the same log lines as score() of fix_v2_decon.sh, so the first scorer skips a
# cell this one has finished ("m3 <series> t=<t>: ok" in data/fix_v2_decon.out). The first scorer cannot see a
# cell in progress here, so give this worker cells from the END of the first scorer's order, and few enough
# that it finishes long before the first one arrives. A cell the first scorer has already started (its
# data/_score_<series>_v<t>.log exists) is left alone.
#   sh docs/eval/runners/score_decon_worker2.sh b1:1 b3:5 b3:4 b3:3
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/fix_v2_decon.out
S=anne-decon
RUNNER=decon
ROOM=decon
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh   # ensure_ollama only; nothing here selects a project or makes a billed call
done_p() { grep -q "^[0-9:]* *$1: ok" $O; }
LOCK=data/score_decon_worker2.lock
[ -f $LOCK ] && { echo "already started ($(cat $LOCK))"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "scoring worker 2: $*"
for cell in "$@"; do
  sys=${cell%%:*}; t=${cell##*:}; series="$S@$sys"
  U=$(echo $sys | cut -d- -f1 | tr a-z A-Z)
  SL="data/_score_$(echo $series | tr @ _)_v$t.log"
  done_p "m3 $series t=$t" && continue
  grep -q "^[0-9:]* $U t=$t: ok" $O || { log "  worker 2: $series t=$t is not built - skipped"; continue; }
  [ -f "$SL" ] && { log "  worker 2: $series t=$t already started by the first scorer - skipped"; continue; }
  ensure_ollama
  $PY scripts/eval/pipeline_page_leak.py "$series" --upto $t > "$SL" 2>&1 || log "  leak-screen $series t=$t FAILED"
  $PY scripts/eval/assertion_precision.py "$series" --upto $t --n 40 >> "$SL" 2>&1 || log "  precision sample $series t=$t FAILED"
  $PY scripts/eval/assertion_inventory.py "$series" --upto $t >> "${SL%.log}_w2.log" 2>&1 && $PY scripts/eval/assertion_precision.py "$series" --upto $t --n 40 --population all >> "${SL%.log}_w2.log" 2>&1 && log "  m3 $series t=$t: ok" || log "  m3 $series t=$t FAILED"
done
rm -f $LOCK
log "scoring worker 2 done"
