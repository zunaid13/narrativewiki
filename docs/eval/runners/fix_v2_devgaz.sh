#!/bin/sh
# 2026-10-05 (Phase 34): the v2 entity-resolution code (C31-C34) on the DEVELOPMENT series, to check that its
# rules (bare names by volume, later full names to the model, article/hyphen/"of" handling) generalise beyond
# the Anne series they were tuned on, on PUBLIC-DOMAIN development works only (maintainer 2026-10-05: Bookworm and
# the other light novels are copyrighted, "you cannot use copyrighted results"): Middlemarch (third person) and
# Twenty Thousand Leagues (first person, Aronnax narrates; maintainer 2026-10-05:
# "none of the solution can be specialized for Anne only"). Gazetteer only; main project first, temporary on 429.
cd "g:/UIU classes/Claude Code RAG+TKG pipeline" || exit 1
PY=.venv/Scripts/python.exe
O=data/fix_v2_devgaz.out
G="C:/Users/pc/AppData/Roaming/gcloud"
for sv in middlemarch:1-5 leagues:1-2; do s=${sv%%:*}; vols=${sv#*:}
  for proj in new old; do
    if [ $proj = new ]; then P=min2web-nsyss-4; C="$G/adc_arnababir1_min2web-nsyss-4.json"; else P=gen-lang-client-0365142802; C="$G/adc_temporary171842_gen-lang-client-0365142802.json"; fi
    echo "$(date -u +%Y%m%dT%H%M%S) $proj fix" >> data/vertex_projects.log
    GOOGLE_CLOUD_PROJECT=$P GOOGLE_APPLICATION_CREDENTIALS="$C" $PY -m narrativewiki.cli gazetteer --series "$s@v2" --volumes $vols --force --set models.profiles.vertex_flash.concurrency=8 > "data/fix_devgaz_$s.out" 2>&1 && { echo "$(date -u +%H:%M) $s@v2 gazetteer ok ($proj)" >> $O; break; }
    grep -q "RESOURCE_EXHAUSTED\|429" "data/fix_devgaz_$s.out" && { echo "$(date -u +%H:%M) $s@v2 429 on $proj" >> $O; continue; }
    echo "$(date -u +%H:%M) $s@v2 FAILED ($proj), see data/fix_devgaz_$s.out" >> $O; break
  done
done
echo "$(date -u +%H:%M) devgaz done" >> $O
