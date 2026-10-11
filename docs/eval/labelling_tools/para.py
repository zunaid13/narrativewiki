"""para.py <series> <regex> <para_id> [para_id ...]: sentences of the given paragraphs that match the regex ('.' = whole).

Reads data/<series before @>/01_parsed. Used when the 520-character window of m8view_any.py cuts the part needed.
"""
import json, re, sys, glob

sys.stdout.reconfigure(encoding='utf-8')
s, rx, ids = sys.argv[1].split('@')[0], sys.argv[2], sys.argv[3:]
text = {}
for f in glob.glob(f'data/{s}/01_parsed/v*.jsonl'):
    for line in open(f, encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            text[r['para_id']] = r['text']
for pid in ids:
    p = text.get(pid, '(missing)')
    if rx == '.':
        print(f'<{pid}> {p}')
        continue
    hits = [x.strip() for x in re.split(r'(?<=[.!?”])\s+', p) if re.search(rx, x, re.I)]
    print(f'<{pid}> ' + (' || '.join(hits) if hits else f'(no match; {len(p)} chars)'))
