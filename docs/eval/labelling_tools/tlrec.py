"""tlrec.py <series> <t>: put labels_claude/<series>_v<t>.tlcite.json into timeline_cite_claude.json.

The labels file maps a sampled timeline row to [verdict S|P|I, note]. The evidence stored beside each verdict is
what the delivered timeline page prints under that line (read as m8view_any.py reads it). Every timeline row of
the sample that the page cites must have a verdict; a row with a verdict that is not such a row stops the run.
"""
import json, re, sys
from pathlib import Path

s, t = sys.argv[1], int(sys.argv[2])
ANCHOR = re.compile(r"#nw-v(\d+)-c(\d+)-p(\d+)")
M = {"S": "sufficient", "P": "partial", "I": "insufficient"}


def plain(x):
    return re.sub(r"\s+", " ", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", x).replace("*", "")).strip()


def timeline_cites(r):
    lines = (Path('dist') / s / 'wiki' / f'v{t:02d}' / r['page']).read_text(encoding='utf-8').splitlines()
    key = plain(r.get('unit') or r['value'])[:60]
    for i, line in enumerate(lines):
        if key and key in plain(line):
            for nxt in lines[i:i + 4]:
                ids = [f"v{int(a):02d}:c{int(b):02d}:p{int(c):04d}" for a, b, c in ANCHOR.findall(nxt)]
                if ids and 'ource' in nxt:
                    return ids
    return []


lab = json.load(open(f'docs/eval/precision/labels_claude/{s}_v{t}.tlcite.json', encoding='utf-8'))
rows = [json.loads(l) for l in open(f'docs/eval/precision/{s}_v{t}_all.jsonl', encoding='utf-8')]
need = {}
for i, r in enumerate(rows):
    if not r.get('evidence') and r['page'].startswith('timeline/') and r.get('human') != 'frame_error':
        ev = timeline_cites(r)
        if ev:
            need[str(i)] = ev
assert set(need) == set(lab), (sorted(set(need) - set(lab), key=int), sorted(set(lab) - set(need), key=int))
F = Path('docs/eval/precision/timeline_cite_claude.json')
d = json.loads(F.read_text(encoding='utf-8'))
d.setdefault(s, {})[str(t)] = {i: {"cite": M[lab[i][0]], "evidence": need[i], "note": lab[i][1]}
                               for i in sorted(lab, key=int)}
F.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
n = sum(1 for i in lab if lab[i][0] == 'S')
print(s, t, 'timeline rows', len(lab), 'sufficient', n)
