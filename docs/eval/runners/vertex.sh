# Sourced by the runners started 2026-10-04. Needs $PY, $O (log), log(), $RUNNER (oz|decon) and $ROOM
# (the room.py key this runner's budget is read from on the main project: new or decon).
# Maintainer 2026-10-04: the rest of the work runs on the arnababir1 project (min2web-nsyss-4, $200);
# the temporary account's project only when the main one answers 429; never the geminiprof2 project.
# Same model on both (gemini-3.6-flash, Flex): switching project never changes a result, only the bill.
G="C:/Users/pc/AppData/Roaming/gcloud"
CUR=""
use_project() {
  case $1 in
    new) GOOGLE_CLOUD_PROJECT=min2web-nsyss-4; GOOGLE_APPLICATION_CREDENTIALS="$G/adc_arnababir1_min2web-nsyss-4.json" ;;
    old) GOOGLE_CLOUD_PROJECT=gen-lang-client-0365142802; GOOGLE_APPLICATION_CREDENTIALS="$G/adc_temporary171842_gen-lang-client-0365142802.json" ;;
  esac
  export GOOGLE_CLOUD_PROJECT GOOGLE_APPLICATION_CREDENTIALS
  # room.py attributes each run to the project its runner last selected; keep this line before any call.
  [ "$CUR" = "$1" ] || { echo "$(date -u +%Y%m%dT%H%M%S) $1 $RUNNER" >> data/vertex_projects.log; log "project -> $1 ($GOOGLE_CLOUD_PROJECT)"; CUR=$1; }
}
room() { $PY docs/eval/runners/room.py $1; }
probe() { $PY scripts/eval/vertex_probe.py > data/_probe_$RUNNER.out 2>&1; rc=$?; cat data/_probe_$RUNNER.out >> $O; return $rc; }
# pick_api NEED WHAT: before every billed attempt. Main project when it answers; the temporary one only
# when the main one answers 429 and has room; any other failure waits (one probe per 10 min).
pick_api() {
  while :; do
    r=$(room $ROOM); [ "$r" -ge "$1" ] || { log "budget gate: $ROOM room \$$r < \$$1 needed for $2 - stopping"; exit 3; }
    use_project new; probe && return 0
    if grep -q 429 data/_probe_$RUNNER.out; then
      r=$(room old)
      if [ "$r" -ge "$1" ]; then use_project old; probe && return 0
      else log "main project 429 and the temporary project's room \$$r < \$$1: waiting"; fi
    fi
    sleep 600
  done
}
# retry NEED WHAT CMD...: three attempts fifteen minutes apart, re-picking the project before each.
retry() { NEED=$1; WHAT=$2; shift 2
  for a in 1 2 3; do pick_api "$NEED" "$WHAT"; "$@" >> $O 2>&1 && return 0; log "  attempt $a failed ($CUR): $*"; sleep 900; done; return 1; }
# G11: the evaluation atomizer is local-only and falls back silently, so the server must be up first.
ensure_ollama() { curl -s -m 5 localhost:11434/api/version > /dev/null || {
  nohup "C:/Users/pc/AppData/Local/Programs/Ollama/ollama.exe" serve > /dev/null 2>&1 & sleep 20; log "ollama was down: started"; }; }
