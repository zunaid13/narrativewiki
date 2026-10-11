#!/bin/sh
# 2026-10-08 (Phase 34): entity discovery run per prefix, the comparison the paper lacked (review 6.3:
# "why is entity discovery not run per prefix, as the LightRAG baseline's index is?"). For t=1..4 the v2
# gazetteer is rebuilt from volumes 1..t alone (`wiki gazetteer --gate build`), written to
# data/<series>/@t<NN>/02_entities/ beside the full build, which is not touched. t=5 is the full build.
# Scored at $0 by scripts/eval/identity_dependence.py against 02_entities/_premerge (the full build
# before the epithet merge: a prefix gazetteer has no epithet channel).
#   start:  sh docs/eval/runners/prefix_gazetteer.sh [series]      lock: data/prefix_gazetteer.lock
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
S=${1:-anne@v2}
O=data/prefix_gazetteer.out
L="data/_prefix_gazetteer_$(echo $S | tr @ _).log"
RUNNER=fix
ROOM=new
CAP="--set models.budget.lifetime_cap_usd=425"   # ledger 415.12 at start; the estimate is under $4
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
LOCK=data/prefix_gazetteer.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$ $S" > $LOCK
log "prefix gazetteers $S t=1..4, commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check v2k >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; rm -f $LOCK; exit 1; }
rc=1
for a in 1 2 3; do   # resumable: finished cutoffs are skipped, every call is cached
  pick_api 4 "$S prefix gazetteers"
  $PY -m narrativewiki.cli gazetteer --series "$S" --volumes 1-4 --gate build --set models.profiles.vertex_flash.concurrency=8 $CAP > "$L" 2>&1 && { rc=0; break; }
  log "  attempt $a failed ($CUR), see $L"; sleep 300
done
[ $rc = 0 ] && log "$S prefix gazetteers: ok" || log "$S prefix gazetteers: FAILED after 3 attempts"
rm -f $LOCK
exit $rc
