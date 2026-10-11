#!/bin/sh
# 2026-10-08 (Phase 34): the rest of the t=4 prefix build (anne@p4-v2), taken over from prefix_build_v2.sh
# at the backstory step. Maintainer 08:05 UTC: "if one gives 429, switch to the temporary email api then
# get back when the main one stops 429". prefix_build_v2.sh ran the whole series as one command, so a 429
# waited 15 min inside run_series on the refusing project (extract-v2, 06:32). Here each step is its own
# command with RUN_SERIES_429_RETRIES=0: the main project (min2web-nsyss-4) is probed before every step,
# and only the attempt right after a 429 on it goes to the temporary project. Same model on both.
# Ends as prefix_build_v2.sh would: BUILD_OK, data/prefix_build_v2.done (the scorer waits on both).
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/prefix_build_v2.out
S=anne@p4-v2
RUNNER=fix
ROOM=new
START=415.33
SET="--set models.profiles.vertex_flash.concurrency=12 --set models.budget.lifetime_cap_usd=462"
export RUN_SERIES_429_RETRIES=0
log() { echo "$(date -u +%H:%M) $*" >> $O; }
. docs/eval/runners/vertex.sh
spent() { $PY -c "from narrativewiki.llm.budget import lifetime_spent; print(round(lifetime_spent() - $START, 2))"; }
LAST429=""
pick_api() {  # NEED WHAT (as in fix_v2_anne_resume3.sh)
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

LOCK=data/prefix_build_v2.lock
echo "$(date -u +%m-%dT%H:%M) pid $$ (t4 takeover)" > $LOCK
log "build t=4 taken over from ${1:-graph}, one step per command, project re-picked per step"
go=0
for step in $($PY scripts/run_series.py $S --upto 4 --to audit-eval --list | tr -d '\r'); do
  [ "$step" = "${1:-graph}" ] && go=1   # backstory finished 08:16 under the old runner
  [ $go = 1 ] || continue
  retry 12 "t=4 $step" $PY scripts/run_series.py $S --upto 4 --from "$step" --to "$step" $SET \
    || { log "build t=4: FAILED at $step (see data/$S/_driver)"; rm -f $LOCK; exit 1; }
done
touch "data/$S/_driver/BUILD_OK"; log "build t=4: ok (runner spent \$$(spent))"
log "prefix build v2: billed steps done, runner spent \$$(spent)"
touch data/prefix_build_v2.done
rm -f $LOCK
