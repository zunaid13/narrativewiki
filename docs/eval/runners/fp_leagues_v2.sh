#!/bin/sh
# 2026-10-05 (Phase 34): the first-person sample. Maintainer: "we only need anne, decontaminated anne, and a
# small sample for a first person novel". Twenty Thousand Leagues (narrated by Aronnax), parts 1-2, built with
# the v2 code as leagues@v2 on the gazetteer already made by fix_v2_devgaz.sh. Billed steps only, through the
# site build and the $0 audits; the GPU evaluation steps (leak screens, precision samples) are left out so this
# runs beside anne@v2's local scoring. Main project first, temporary on a 429, as fix_v2_anne_resume4.sh.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/fp_leagues_v2.out
S=leagues@v2
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
LOCK=data/fp_leagues_v2.lock; [ -f $LOCK ] && { log "already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "first-person sample leagues@v2 v1-2 from scenes-v1 (main project first, temporary on 429), commit $(git rev-parse --short HEAD)"
FROM=scenes-v1
for a in 1 2 3 4 5 6; do
  pick_api 6 "leagues v2"
  mark=$(wc -l < $O)
  $PY scripts/run_series.py $S --upto 2 --from $FROM --to audit-eval $C8 >> $O 2>&1 && { log "leagues v2 v1-2: ok"; exit 0; }
  # resume from the step that failed; every finished call is cached
  FROM=$(tail -n +$((mark + 1)) $O | grep -oE "^[0-9:]+ [a-z0-9-]+: (FAILED|429 \(RESOURCE)" | tail -1 | awk '{print $2}' | tr -d :)
  [ -n "$FROM" ] || FROM=scenes-v1
  if tail -n +$((mark + 1)) $O | grep -q "RESOURCE_EXHAUSTED\|: 429"; then
    log "  429 on $CUR, attempt $a: switching (resume at $FROM)"; [ "$CUR" = new ] && LAST429=new; sleep 60
  else
    log "  attempt $a failed ($CUR), resume at $FROM"; sleep 900
  fi
done
log "leagues v2 FAILED after 6 attempts - stopping"; exit 1
