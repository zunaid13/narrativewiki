#!/bin/sh
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
O=data/anne/_driver/s01_3.6.out
echo "$(date -u +%H:%M) graph --allow-partial after checking the guard's names (all extracted, 0 errors)" >> $O
.venv/Scripts/python.exe -m narrativewiki.cli graph build --series anne --allow-partial > data/anne/_driver/graph.log 2>&1 && echo "$(date -u +%H:%M) graph: ok (--allow-partial)" >> $O || { echo "$(date -u +%H:%M) graph: FAILED again" >> $O; exit 1; }
.venv/Scripts/python.exe scripts/run_series.py anne --upto 5 --from verify >> $O 2>&1
echo "$(date -u +%H:%M) S01 done rc=$?" >> $O
