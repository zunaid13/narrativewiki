#!/bin/sh
# 2026-10-01 (CHANGES C16): A1 t=2 and t=3 on disk were built by retries that restarted at scenes on an
# already-merged gazetteer -- re-billed, and not the one-merge protocol B5 used. Rebuild both from a
# fresh gazetteer under freeze anne-v1q (driver restores the pre-merge gazetteer on any retry). Every
# step of each build's FIRST attempt is in the LLM cache, so scenes..backstory should be ~all hits:
# the runner checks that on scenes-v1 and stops if it is not (red flag, not a cheap path).
# Waits until no other A1 job runs (never two writers on one tree). Orchestration only.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_a1_redo.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
while ps -ef | grep -E "anne_resume.sh|anne_a1_t2.sh|run_series.py anne@p" | grep -qv grep; do sleep 300; done
log "redo start, commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check anne-v1q >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
for t in 2 3; do
  rm -rf "data/anne@p$t/02_entities/_premerge"
  $PY -m narrativewiki.cli gazetteer --series anne@p$t --volumes 1-$t --force >> $O 2>&1 || { log "A1 t=$t gazetteer FAILED - stopping"; exit 1; }
  $PY scripts/run_series.py anne@p$t --upto $t --to scenes-v1 >> $O 2>&1 || { log "A1 t=$t scenes-v1 FAILED - stopping"; exit 1; }
  rate=$($PY -c "import glob,json; f=sorted(glob.glob('data/anne@p$t/_runs/*-scenes-v1-1/calls.jsonl'))[-1]; r=[json.loads(l) for l in open(f,encoding='utf-8')]; print(int(100*sum(x.get('cache_hit',False) for x in r)/max(1,len(r))))")
  log "A1 t=$t scenes-v1 cache hits ${rate}%"
  [ "$rate" -ge 90 ] || { log "A1 t=$t: cache hits below 90% - not the first attempt's build, stopping"; exit 1; }
  ok=0
  for a in 1 2 3; do
    $PY scripts/run_series.py anne@p$t --upto $t --from scenes-v2 >> $O 2>&1 && { ok=1; break; }
    log "A1 t=$t: FAILED (attempt $a)"
  done
  [ $ok = 1 ] && log "A1 t=$t: ok" || log "A1 t=$t: gave up"
done
log "redo done"
