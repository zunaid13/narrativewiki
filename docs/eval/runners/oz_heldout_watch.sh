#!/bin/sh
# 2026-10-02 19:20 UTC: restart oz_heldout_resume.sh after it gives up on a Vertex 429 outage. The 429 is
# gemini-3.6-flash capacity, not a project quota (MEASUREMENTS 2026-10-02 19:10: 3.1-flash-lite and 2.5-flash
# answered on the same project while 3.6 refused), so it ends on Google's side; the same-model rule means
# waiting is the only option. Relaunches ONLY on "B5 (oz) FAILED - stopping"; any other ending is left for
# a human. Waits on the 10-minute probe first, so an outage costs one 8-token request per 10 minutes.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/oz_heldout.out
log() { echo "$(date -u +%H:%M) watch: $*" >> $O; }
while :; do
  while [ -f data/oz_heldout.lock ] && ps -ef | grep -v grep | grep -q "oz_heldout_resume.sh"; do sleep 300; done
  tail -1 $O | grep -q "B5 (oz) FAILED - stopping" || { log "runner ended without the 429 stop ($(tail -1 $O | cut -c1-60)); not restarting"; exit 0; }
  until $PY scripts/eval/vertex_probe.py >> $O 2>&1; do sleep 600; done
  rm -f data/oz_heldout.lock; log "429 stop seen and the probe answers: restarting oz_heldout_resume.sh"
  nohup sh docs/eval/runners/oz_heldout_resume.sh > /dev/null 2>&1 &
  sleep 120
done
