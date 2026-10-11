#!/bin/sh
# 2026-10-01 night (maintainer: "start the decontamination work ... until $300 total API cost"): the
# decontaminated condition of Anne v1-5 (names remapped with the reviewed map, every paragraph
# paraphrased), then B5 and the baselines on it in value order, each scored as on the original.
# Flex transport (same model); a budget gate before every billed step stops cleanly at the cap.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
PYB3=.venv-b3/Scripts/python.exe
O=data/anne_decon.out
S=anne-decon
C12="--set models.profiles.vertex_flash.concurrency=12"  # Flex queues instead of 429; throughput only
log() { echo "$(date -u +%H:%M) $*" >> $O; }
room() { $PY -c "
import glob,json
t=sum((json.loads(l).get('cost_usd') or 0) for f in glob.glob('data/*/_runs/*/calls.jsonl') for l in open(f,encoding='utf-8'))
oz=sum((json.loads(l).get('cost_usd') or 0) for f in glob.glob('data/oz*/_runs/*/calls.jsonl') for l in open(f,encoding='utf-8'))
import os
done=os.path.exists('data/oz_heldout.out') and 'oz done' in open('data/oz_heldout.out',encoding='utf-8',errors='ignore').read()
# 2026-10-02: runs beside the held-out matrix; what that matrix has not spent yet is kept for it.
# 2026-10-03: reserve 45 -> 70, the Oz runner's own estimate with X2 (45 let decon spend money Oz needs; maintainer: Oz first).
print(int(300 - (t - 38.58) - (0 if done else max(0.0, 70 - oz))))"; }
gate() { r=$(room); [ "$r" -ge "$1" ] || { log "budget gate: room \$$r < \$$1 needed for $2 - stopping (ask the maintainer for more budget)"; exit 3; }; }
# 2026-10-02: a provider outage is waited out with one tiny probe every 10 min, not with retry bursts.
wait_api() { until $PY scripts/eval/vertex_probe.py >> $O 2>&1; do sleep 600; done; }
retry() { for a in 1 2 3; do "$@" >> $O 2>&1 && return 0; log "  attempt $a failed: $*"; sleep 900; done; return 1; }
score() {  # $1 system (lowercase), $2 t ($0, local)
  $PY scripts/eval/pipeline_page_leak.py "$S@$1" --upto $2 > "data/_score_${S}_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "$S@$1" --upto $2 --n 40 >> "data/_score_${S}_$1_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
  $PY scripts/eval/assertion_inventory.py "$S@$1" --upto $2 >> $O 2>&1 && $PY scripts/eval/assertion_precision.py "$S@$1" --upto $2 --n 40 --population all >> $O 2>&1 && log "  m3 $S@$1 t=$2: ok" || log "  m3 $S@$1 t=$2 FAILED"
}
cell() { SYS=$1; T=$2; NEED=$3; shift 3; gate $NEED "$SYS t=$T"; wait_api
  retry $PY scripts/baselines/run_baseline.py $S $SYS --upto $T "$@" && log "$SYS t=$T: ok" || { log "$SYS t=$T: FAILED"; return 1; }
  score "$(echo $SYS | tr A-Z a-z)" $T
}
# 2026-10-02: started beside anne_rest.sh (maintainer: use every API window, run to the $300 stop); the lock
# keeps the copy that anne_rest.sh launches at its end from running a second time over the same trees.
LOCK=data/anne_decon.lock; [ -f $LOCK ] && { log "decon already started ($(cat $LOCK)) - not starting twice"; exit 0; }
echo "$(date -u +%m-%dT%H:%M) pid $$" > $LOCK
log "decon start, commit $(git rev-parse --short HEAD)"
$PY scripts/papers/freeze.py check oz-v2 >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
# C21: the name map is audited before any paraphrase is paid for (collisions, one person with two names).
$PY scripts/eval/decon_map_audit.py $S >> $O 2>&1 || { log "MAP AUDIT FAILED - stopping"; exit 1; }
gate 10 "paraphrase"; wait_api
retry $PY -m narrativewiki.cli decontaminate --series $S --volumes 1-5 --force $C12 && log "paraphrase: ok" || { log "paraphrase FAILED - stopping"; exit 1; }
# 2026-10-02: the treated text is checked before a build is paid for on it. A residual original name or
# more than 1% of paragraphs left unparaphrased stops the run; copied paragraphs are logged, not blocking.
$PY -c "
import json,sys
r=json.load(open('data/$S/01_parsed/decon_report.json',encoding='utf-8'))
n=sum(v['n_paragraphs'] for v in r.values()); k=lambda f: sum(v.get(f,0) for v in r.values())
print('treated text: %d paragraphs, %d paraphrased, %d verbatim, %d remap-only, %d with a residual name, words %d -> %d' % (n,k('paraphrased'),k('verbatim'),k('remap_only'),k('residual_name_paragraphs'),k('words_source'),k('words_derived')))
sys.exit(1 if len(r)<5 or k('residual_name_paragraphs') or k('remap_only')>0.01*n else 0)" >> $O 2>&1 || { log "TREATED TEXT CHECK FAILED - stopping"; exit 1; }
# Recognition probe (appendix I): name cloze and title identification on the same paragraphs of the
# original, the treated text and the names-only variant. ~800 short calls each; not blocking.
for M in $S anne-remap; do gate 2 "memorization $M"; wait_api
  retry $PY -m narrativewiki.cli probe run memorization --series $M --volumes 1-5 --n 200 --json docs/eval/memorization_$M.jsonl && log "memorization ($M): ok" || log "memorization ($M) FAILED (continuing)"
done
gate 5 "gazetteer"; wait_api
retry $PY -m narrativewiki.cli gazetteer --series $S --volumes 1-5 --force $C12 && log "gazetteer: ok" || { log "gazetteer FAILED - stopping"; exit 1; }
gate 25 "B5 build"; wait_api
retry $PY scripts/run_series.py $S --upto 5 $C12 && log "B5 (decon) v1-5: ok" || { log "B5 (decon) FAILED - stopping"; exit 1; }
for t in 1 2 3 4 5; do cell X1 $t 2; done
for t in 1 2 3 4 5; do cell B2 $t 3 --chunk-words 150 --budget-tokens 20000; done
for t in 1 2 3 4 5; do cell B4 $t 3 --budget-tokens 20000; done
for t in 1 2 3 4 5; do gate 4 "B3 t=$t"; wait_api
  retry $PYB3 scripts/baselines/b3_lightrag.py $S --upto $t --mode mix --budget-tokens 20000 && { log "B3 t=$t: ok"; score b3 $t; } || log "B3 t=$t: FAILED"
done
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
for t in 1 2 3 4 5; do cell B1 $t 12 $FLEX2; done
for t in 1 2 3 4 5; do cell X2 $t 12 $FLEX2; done
log "decon done"
