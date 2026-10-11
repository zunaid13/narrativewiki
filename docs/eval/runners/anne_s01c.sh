#!/bin/sh
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
O=data/anne/_driver/s01_3.6.out
echo "$(date -u +%H:%M) S01 resume from infobox (Flex), commit $(git rev-parse --short HEAD)" >> $O
.venv/Scripts/python.exe scripts/run_series.py anne --upto 5 --from infobox >> $O 2>&1
echo "$(date -u +%H:%M) S01 done rc=$?" >> $O
