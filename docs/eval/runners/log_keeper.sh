#!/bin/sh
# 2026-10-07: keeps the status lines of data/fix_v2_decon.out that the runners decide by. $0, no model call.
# Found today: with three jobs writing to that log, lines disappear. A Python child started with `>> $O` keeps
# the file position of its start; when it prints at its end (run_baseline's "wrote N pages", the inventory's
# summary) it writes over whatever the other jobs appended meanwhile. Lost so far: "scoring worker 2: ..." and
# "m3 anne-decon@b3 t=5: ok". The runners skip or pick a cell by grepping for "<SYS> t=<t>: ok" (built) and
# "m3 <series> t=<t>: ok" (scored), so a lost line means a labelled cell scored again (its labels wiped) or a
# built cell never scored.
# This loop (1) remembers every such line it sees in data/fix_v2_decon.keep, (2) adds "m3 ... ok" for every
# cell whose 40-row sample is on disk, (3) appends again any remembered line the log no longer holds.
# It ends when no runner lock is left.   start:  sh docs/eval/runners/log_keeper.sh
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
O=data/fix_v2_decon.out
K=data/fix_v2_decon.keep
touch $K
locks() { ls data/fix_v2_decon_score.lock data/score_decon_worker2.lock data/fix_v2_decon.lock 2>/dev/null | grep -q .; }
while locks; do
  grep -a -o -E "^[0-9]{2}:[0-9]{2} +(m3 anne-decon@[a-z0-9-]+ t=[1-5]: ok|(B1|B2|B3|B4|X1|X2) t=[1-5]: ok)" $O |
    sed 's/^[0-9:]* *//' | sort -u | while read -r key; do grep -q -F -x "$key" $K || echo "$key" >> $K; done
  for f in docs/eval/precision/anne-decon@*_all.jsonl; do
    [ "$(wc -l < "$f")" -ge 40 ] || continue
    s=$(basename "$f" _all.jsonl); key="m3 ${s%_v*} t=${s##*_v}: ok"
    grep -q -F -x "$key" $K || echo "$key" >> $K
  done
  while read -r key; do
    case "$key" in m3*) pad="   " ;; *) pad=" " ;; esac
    grep -a -q -E "^[0-9]{2}:[0-9]{2} +$key" $O || { echo "$(date -u +%H:%M)$pad$key" >> $O; echo "$(date -u +%H:%M) restored: $key"; }
  done < $K
  sleep 45
done
echo "$(date -u +%H:%M) no runner lock left: log keeper ends"
