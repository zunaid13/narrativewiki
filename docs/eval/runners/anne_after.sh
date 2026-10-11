#!/bin/sh
# 2026-09-30: fixes found by auditing the chain's results. Orchestration only; every command is a
# frozen script (freeze anne-v1o). 2026-10-01: Vertex Standard (Flex on 429), so this runs BESIDE
# anne_resume.sh's A1 builds instead of after them; each Vertex step gets 3 attempts (the LLM cache
# makes a retry resume, e.g. after the $10 per-run hard stop, which Standard prices reach sooner).
#   1. X1 t=1..5 re-render: the closed-book prompt never named the work (CHANGES.md C7). ~$1.
#   2. B1 t=1..4, B2/B3/B4 t=1..5 re-render: prompts with passages no longer name the work, as B5's
#      never did (CHANGES.md C9). ~$20 (B1 t=5 is re-run by the chain itself under the new prompt).
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_after.out
log() { echo "$(date -u +%H:%M) $*" >> $O; }
retry() { for a in 1 2 3; do "$@" >> $O 2>&1 && return 0; log "  attempt $a failed: $*"; done; return 1; }
log "after-chain start (beside A1), commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check anne-v1o >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
for t in 1 2 3 4 5; do
  retry $PY scripts/baselines/run_baseline.py anne X1 --upto $t && log "X1 t=$t: ok" || { log "X1 t=$t: FAILED"; continue; }
  $PY scripts/eval/pipeline_page_leak.py anne@x1 --upto $t > "data/_score_anne_x1_v$t.log" 2>&1 || log "  leak-screen x1 t=$t FAILED"
  $PY scripts/eval/assertion_precision.py anne@x1 --upto $t --n 40 >> "data/_score_anne_x1_v$t.log" 2>&1 || log "  precision sample x1 t=$t FAILED"
  $PY scripts/eval/assertion_inventory.py anne@x1 --upto $t >> $O 2>&1 \
    && $PY scripts/eval/assertion_precision.py anne@x1 --upto $t --n 40 --population all >> $O 2>&1 \
    && log "m3 anne@x1 t=$t: ok" || log "m3 anne@x1 t=$t FAILED"
done
PYB3=.venv-b3/Scripts/python.exe
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
score() {  # $1 system (lowercase), $2 t: leak screen, cited sample, M3 inventory + all-population sample ($0)
  $PY scripts/eval/pipeline_page_leak.py "anne@$1" --upto $2 > "data/_score_anne_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 >> "data/_score_anne_$1_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "anne@$1" --upto $2 >> $O 2>&1     && $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 --population all >> $O 2>&1     && log "  m3 anne@$1 t=$2: ok" || log "  m3 anne@$1 t=$2 FAILED"
}
cell() { S=$1; T=$2; shift 2
  retry $PY scripts/baselines/run_baseline.py anne $S --upto $T "$@" && log "$S t=$T: ok" || { log "$S t=$T: FAILED"; return 1; }
  score "$(echo $S | tr A-Z a-z)" $T
}
cell X2 1 $FLEX2  # C11: the chain's X2 t=1 ran the old prompt (a B1 t=5 replay)
for t in 1 2 3 4; do cell B1 $t $FLEX2; done
for t in 1 2 3 4 5; do cell B2 $t --chunk-words 150 --budget-tokens 20000; done
for t in 1 2 3 4 5; do
  retry $PYB3 scripts/baselines/b3_lightrag.py anne --upto $t --mode mix --budget-tokens 20000 && { log "B3 t=$t: ok"; score b3 $t; } || log "B3 t=$t: FAILED"
done
for t in 1 2 3 4 5; do cell B4 $t --budget-tokens 20000; done
log "after-chain fixes done"
