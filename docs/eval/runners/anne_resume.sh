#!/bin/sh
# 2026-09-29: replaces anne_s01d / anne_baselines / anne_a1 / anne_b3_redo after Vertex went 429 on
# every call (Flex too) from ~19:19 UTC. One chain, one job at a time (concurrent jobs preceded both
# 429 episodes), each step gated by a one-call capacity probe. Orchestration only; every command is a
# frozen script (freeze anne-v1n). Every step is cache-backed, so re-running a finished one is ~$0.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe; PYB3=.venv-b3/Scripts/python.exe
O=data/anne_resume.out
FLEX2="--set models.profiles.vertex_flash.concurrency=2"
log() { echo "$(date -u +%H:%M) $*" >> $O; }
gate() {  # one tiny call (retries off, no ledger, < $0.0001); probe every 30 min, give up after 10 h
  n=0
  until $PY - >> $O 2>&1 <<'PY'
import sys, uuid
sys.path.insert(0, "src")
from narrativewiki.config import apply_set_overrides, load_settings
from narrativewiki.llm.client import LLMClient
s = load_settings("anne")
apply_set_overrides(s, ["models.client.rate_limit_retries=0", "models.client.max_retries=0"])
p = s.resolve_role("verify")
try:
    LLMClient(s, volume_scope=1)._call("verify", p, "Reply with the single word OK. " + uuid.uuid4().hex, None, False, None)
except Exception as e:
    print("gate:", str(e)[:100]); sys.exit(1)
PY
  do n=$((n + 1)); [ $n -ge 20 ] && { log "gate: still no capacity after 10 h of probes - stopping"; exit 1; }; sleep 1800; done
}
try() {  # $1 label, rest = command; up to 3 gated attempts
  L=$1; shift
  for a in 1 2 3; do gate; "$@" >> $O 2>&1 && { log "$L: ok"; return 0; }; log "$L: FAILED (attempt $a)"; done
  return 1
}
score() {  # $1 system (lowercase), $2 t : local scoring, $0
  $PY scripts/eval/pipeline_page_leak.py "anne@$1" --upto $2 > "data/_score_anne_$1_v$2.log" 2>&1 || log "  leak-screen $1 t=$2 FAILED"
  $PY scripts/eval/assertion_precision.py "anne@$1" --upto $2 --n 40 >> "data/_score_anne_$1_v$2.log" 2>&1 || log "  precision sample $1 t=$2 FAILED"
}
cell() { S=$1; T=$2; shift 2; try "$S t=$T" $PY scripts/baselines/run_baseline.py anne $S --upto $T "$@"; score "$(echo $S | tr A-Z a-z)" $T; }

$PY scripts/papers/freeze.py check anne-v1n >> $O 2>&1 || { log "FREEZE CHECK FAILED - stopping"; exit 1; }
log "resume start, commit $(git rev-parse --short HEAD)"

# 1. S01 (the system): verify onward. Nothing else runs until it is done.
try "S01 from verify" $PY scripts/run_series.py anne --upto 5 --from verify || { log "S01 not finished - stopping (baselines need its graph for B4; rerun this script)"; exit 1; }

# 2. B3 t=1..5 (t=1 re-rendered for the v1f cast rule, query-only; t=2 index repaired in place; t=3.. copy the repaired prefix).
for t in 1 2 3 4 5; do
  try "B3 t=$t" $PYB3 scripts/baselines/b3_lightrag.py anne --upto $t --mode mix --budget-tokens 20000 || { log "B3 stops at t=$t (later cutoffs need it)"; break; }
  score b3 $t
done

# 3. X1 and B2 under the current freeze (v1f cast rule: surviving pages are cache hits; t=4, 5 failed before the fixes).
for t in 1 2 3 4 5; do cell X1 $t; done
for t in 1 2 3 4 5; do cell B2 $t --chunk-words 150 --budget-tokens 20000; done

# 4. B4 (reads the new Anne graph), then the expensive long-context cells B1 and X2 (X2 droppable).
for t in 1 2 3 4 5; do cell B4 $t --budget-tokens 20000; done
for t in 1 2 3 4 5; do cell B1 $t $FLEX2; done
for t in 1 2 3 4 5; do cell X2 $t $FLEX2; done
log "baselines done"
for s in x1 b1 b2 b3 b4 x2; do $PY scripts/eval/run_cost.py anne@$s >> $O 2>&1; done

# 5. A1 prefix builds t=2,3,4, each only if the cap leaves room (same guard as anne_a1.sh).
spent() { $PY - <<'PY'
import glob, json
t = sum((json.loads(l).get("cost_usd") or 0) for f in glob.glob("data/*/_runs/*/calls.jsonl") for l in open(f, encoding="utf-8"))
print(round(t + 2.19 + 0.40, 2))  # + billed offset + bake-off made outside a ledger
PY
}
for t in 2 3 4; do
  est=$((t * 5)); s=$(spent); room=$($PY -c "print(int(255 - $s))")
  if [ "$room" -lt $((est + 15)) ]; then log "A1 t=$t skipped: spent \$$s, room \$$room < estimate \$$est + 15"; continue; fi
  log "A1 t=$t start (spent \$$s, estimate \$$est)"
  try "A1 t=$t gazetteer" $PY -m narrativewiki.cli gazetteer --series anne@p$t --volumes 1-$t --force || continue
  try "A1 t=$t" $PY scripts/run_series.py anne@p$t --upto $t
done
log "all done, spent \$$(spent)"
