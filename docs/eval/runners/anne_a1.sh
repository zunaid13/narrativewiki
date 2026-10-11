#!/bin/sh
# A1 (S13): prefix-built Anne at t=2,3,4 (t=1 = anne-m36 trial arm, t=5 = S01), 3.6 Flash on Flex,
# after the baseline cells. Budget guard before each build: skip unless cap - spent > estimate + $15.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne_a1.out
FLEX="--set models.profiles.vertex_flash.options.shared_request_type=flex --set models.profiles.vertex_flash.price_per_mtok.input=0.375 --set models.profiles.vertex_flash.price_per_mtok.output=1.875"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
n=0; until grep -q "baselines done" data/anne_baselines.out 2>/dev/null; do sleep 120; n=$((n+1)); [ $n -gt 360 ] && { log "baselines not done after 12h - A1 skipped"; exit 1; }; done
$PY scripts/papers/freeze.py check anne-v1e >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
# X1 and B2 cells made before freeze anne-v1c are re-rendered under it (cache hits except the two
# X1 pages that failed on null fields), then re-scored locally, so every cell is one freeze.
for c in "X1" "B2 --chunk-words 150 --budget-tokens 20000"; do for t in 1 2 3 4 5; do
  $PY scripts/baselines/run_baseline.py anne $c --upto $t >> $O 2>&1 && log "rerender $c t=$t: ok" || log "rerender $c t=$t: FAILED"
  sys=$(echo $c | cut -d" " -f1 | tr A-Z a-z)
  $PY scripts/eval/pipeline_page_leak.py anne@$sys --upto $t > data/_score_anne_${sys}_v$t.log 2>&1
  $PY scripts/eval/assertion_precision.py anne@$sys --upto $t --n 40 >> data/_score_anne_${sys}_v$t.log 2>&1
done; done
spent() { $PY - <<'PY'
import glob, json
t = sum((json.loads(l).get("cost_usd") or 0) for f in glob.glob("data/*/_runs/*/calls.jsonl") for l in open(f, encoding="utf-8"))
print(round(t + 2.19 + 0.40, 2))  # + billed offset + bake-off made outside a ledger
PY
}
for t in 2 3 4; do
  est=$((t * 5))           # ≈ $4.5 per volume on Flex, from S01 (Standard ≈ $9/volume)
  s=$(spent); room=$($PY -c "print(int(255 - $s))")
  if [ "$room" -lt $((est + 15)) ]; then log "A1 t=$t skipped: spent \$$s, room \$$room < estimate \$$est + 15"; continue; fi
  log "A1 t=$t start (spent \$$s, estimate \$$est)"
  $PY -m narrativewiki.cli gazetteer --series anne@p$t --volumes 1-$t --force $FLEX > data/_a1_gaz_p$t.log 2>&1 || { log "A1 t=$t gazetteer FAILED"; continue; }
  $PY scripts/run_series.py anne@p$t --upto $t $FLEX >> $O 2>&1 && log "A1 t=$t: ok" || log "A1 t=$t: FAILED (see data/anne@p$t/_driver)"
done
log "A1 done, spent \$$(spent)"
