#!/bin/sh
# Re-run the B3 t=2 cell (its index missed 5 v2 chapters before freeze anne-v1e), after the baselines.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe; PYB3=.venv-b3/Scripts/python.exe; O=data/anne_baselines.out
n=0; until grep -q "baselines done" $O 2>/dev/null; do sleep 120; n=$((n+1)); [ $n -gt 480 ] && exit 1; done
$PY scripts/papers/freeze.py check anne-v1e > /dev/null || { echo "$(date -u +%H:%M) B3 t=2 rerun: FREEZE CHECK FAILED" >> $O; exit 1; }
$PYB3 scripts/baselines/b3_lightrag.py anne --upto 2 --mode mix --budget-tokens 20000 >> data/anne_b3_t2.out 2>&1 \
  && echo "$(date -u +%H:%M) B3 t=2 rerun (complete index): ok" >> $O || echo "$(date -u +%H:%M) B3 t=2 rerun: FAILED" >> $O
$PY scripts/eval/pipeline_page_leak.py anne@b3 --upto 2 > data/_score_anne_b3_v2.log 2>&1
$PY scripts/eval/assertion_precision.py anne@b3 --upto 2 --n 40 >> data/_score_anne_b3_v2.log 2>&1
