#!/bin/sh
# 2026-10-05 (Phase 34, CHANGES C33): RESUME of fix_v2_anne.sh from the site step, after its MiniCheck codex gate
# was replaced by a model check (the earlier steps are done and cached). Original header:
# 2026-10-04 (Phase 34, CHANGES C31): version 2 of NarrativeWiki (B5) and of B4 on Anne, built from the
# fix-batch code as the variant series `anne@v2` (its gazetteer was built and audited first, $0.04),
# then scored locally ($0). Same Vertex project handling, budget gate and retry rule as the other
# runners (vertex.sh); the version-1 trees are not touched.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/fix_v2_anne.out
S=anne@v2
RUNNER=fix
ROOM=new
C12="--set models.profiles.vertex_flash.concurrency=8"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
# The main project 429s under this load (19:38 and 02:38 UTC); the maintainer's rule is to switch to the
# temporary account on a 429. Same model on both, so only the bill changes. Main project only if its room is the
# only room left.
pick_api() {
  while :; do
    r=$(room old); if [ "$r" -ge "$1" ]; then use_project old; probe && return 0; fi
    r=$(room $ROOM); [ "$r" -ge "$1" ] || { log "budget gate: no room for \$$1 ($2) - stopping"; exit 3; }
    use_project new; probe && return 0
    sleep 600
  done
}
m3() {  # $1 series, $2 t ($0, local): the full assertion inventory and its 40-atom precision sample
  ensure_ollama
  $PY scripts/eval/assertion_inventory.py "$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 $1 t=$2: ok" || log "  m3 $1 t=$2 FAILED"
}
LOCK=data/fix_v2_anne_resume2.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "fix v2 anne RESUME2 at site (temporary project first), commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check v2d >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
retry 10 "B5 v2 from site" $PY scripts/run_series.py $S --upto 5 --from site $C12 && log "B5 v2 v1-5: ok" || { log "B5 v2 FAILED - stopping"; exit 1; }
for t in 1 2 3 4 5; do m3 $S $t; done
for t in 1 2 3 4 5; do
  retry 3 "B4 v2 t=$t" $PY scripts/baselines/run_baseline.py anne B4 --graph $S --upto $t --budget-tokens 20000 && log "B4 v2 t=$t: ok" || { log "B4 v2 t=$t: FAILED"; continue; }
  ensure_ollama
  $PY scripts/eval/pipeline_page_leak.py anne@b4-v2 --upto $t > "data/_score_anne_b4-v2_v$t.log" 2>&1 || log "  leak-screen b4-v2 t=$t FAILED"
  m3 anne@b4-v2 $t
done
log "fix v2 anne done"
