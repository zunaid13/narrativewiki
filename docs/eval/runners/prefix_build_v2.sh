#!/bin/sh
# 2026-10-08 (Phase 34): version 2 of NarrativeWiki built on PREFIX entity indexes, t=1..4 (maintainer:
# "need to run it cause i need the data. run it"). For each t the variant series `anne@p<t>-v2` takes the
# index of volumes 1..t that prefix_gazetteer.sh built (data/anne@v2/@t<NN>/02_entities, copied, so the
# index scored by identity_dependence.py is the index the build uses), then runs every stage on volumes
# 1..t with the frozen v2 code. It gives the page-level comparison the paper lacks for the reported
# build: recall, precision and disclosure of a prefix-discovered wiki against anne@v2 at the same cutoff.
# Scene prompts list the index's aliases, so few calls are cache hits: estimate 6.5 USD per volume built.
#   build:  sh docs/eval/runners/prefix_build_v2.sh build     lock: data/prefix_build_v2.lock
#   score:  sh docs/eval/runners/prefix_build_v2.sh score     ($0, local; follows the build log)
# Budget: a cutoff starts only if what this runner has spent plus its estimate stays within BUDGET.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/prefix_build_v2.out
RUNNER=fix
ROOM=new
BUDGET=45
START=415.33   # ledger before this runner (MEASUREMENTS 2026-10-08)
SET="--set models.profiles.vertex_flash.concurrency=12 --set models.budget.lifetime_cap_usd=462"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
spent() { $PY -c "from narrativewiki.llm.budget import lifetime_spent; print(round(lifetime_spent() - $START, 2))"; }
# State is kept in marker files, not read back from the log: two processes appending to one log on
# this machine have written over each other (ledger 2026-10-07).
built() { [ -f "data/anne@p$1-v2/_driver/BUILD_OK" ]; }

if [ "$1" = score ]; then   # cutoff t of each finished build: lexical screen, inventory, 40-atom sample
  SL=data/prefix_build_v2_score.lock; [ -f $SL ] && { log "scorer already started - not starting twice"; exit 0; }
  echo "$(date -u +%m-%dT%H:%M) pid $$" > $SL
  O=data/prefix_build_v2_score.out
  while :; do
    last=0; [ -f data/prefix_build_v2.done ] && last=1
    for t in 1 2 3 4; do
      S="anne@p$t-v2"
      built $t || continue
      [ -f "data/$S/_driver/SCORED" ] && continue
      ensure_ollama
      L="data/_score_anne_p$t-v2_v$t.log"
      $PY scripts/eval/pipeline_page_leak.py "$S" --upto $t > "$L" 2>&1 || log "  leak-screen $S FAILED"
      $PY scripts/eval/assertion_inventory.py "$S" --upto $t >> "$L" 2>&1 \
        && $PY scripts/eval/assertion_precision.py "$S" --upto $t --n 40 --population all >> "$L" 2>&1 \
        && log "score t=$t: ok" || log "score t=$t: FAILED (see $L)"
      touch "data/$S/_driver/SCORED"
    done
    [ $last = 1 ] && break
    sleep 120
  done
  rm -f $SL; log "prefix build v2: scoring done"
  exit 0
fi

LOCK=data/prefix_build_v2.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "prefix build v2 START (t=1..4, budget \$$BUDGET), commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check v2l >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; rm -f $LOCK; exit 1; }
for t in 1 2 3 4; do
  S="anne@p$t-v2"
  built $t && continue
  s=$(spent); est=$($PY -c "print(6.5 * $t)")
  $PY -c "import sys; sys.exit(0 if $s + $est <= $BUDGET else 1)" || { log "build t=$t not started: spent \$$s + estimate \$$est > budget \$$BUDGET"; continue; }
  E="data/$S/02_entities"
  if [ ! -f "$E/gazetteer.json" ]; then
    mkdir -p "$E" && cp "data/anne@v2/@t0$t/02_entities/"*.* "$E/" || { log "build t=$t: index copy FAILED"; continue; }
  fi
  log "build t=$t start (runner spent \$$s, estimate \$$est)"
  retry 8 "prefix v2 t=$t" $PY scripts/run_series.py "$S" --upto $t --to audit-eval $SET \
    && { touch "data/$S/_driver/BUILD_OK"; log "build t=$t: ok (runner spent \$$(spent))"; } || log "build t=$t: FAILED (see data/$S/_driver)"
done
log "prefix build v2: billed steps done, runner spent \$$(spent)"
touch data/prefix_build_v2.done
rm -f $LOCK
