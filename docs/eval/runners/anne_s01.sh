#!/bin/sh
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/anne/_driver/s01_3.6.out
echo "$(date -u +%H:%M) S01 start: Anne v1-5 on gemini-3.6-flash Standard, commit $(git rev-parse --short HEAD)" >> $O
$PY -m narrativewiki.cli gazetteer --series anne --volumes 1-5 --force > data/anne/_driver/gazetteer_3.6.log 2>&1 || { echo "$(date -u +%H:%M) gazetteer FAILED" >> $O; exit 1; }
echo "$(date -u +%H:%M) gazetteer: ok" >> $O
$PY scripts/run_series.py anne --upto 5 >> $O 2>&1
echo "$(date -u +%H:%M) S01 done rc=$?" >> $O
