"""m8group.py <series> <t> [cap=1000]: the cited rows of a precision sample grouped by page, each cited paragraph once.

Same content as m8view_any.py (which prints a paragraph again for every row that cites it), cheaper to read.
A paragraph longer than cap is cut around the words of the atoms that cite it; para.py prints the rest.
Timeline rows read their citations from the delivered page, as m8view_any.py does.
"""
import json, re, sys, collections
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('.')
s, t = sys.argv[1], int(sys.argv[2])
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
STOP = set("the a an and of to in on at for with by from is was were are be been his her their its that this as it he she "
           "they who whom which had has have not but or after before into over while when also".split())
ANCHOR = re.compile(r"#nw-v(\d+)-c(\d+)-p(\d+)")


def words(x):
    return {w for w in re.findall(r"[a-z']+", x.lower()) if w not in STOP and len(w) > 2}


def plain(x):
    return re.sub(r"\s+", " ", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", x).replace("*", "")).strip()


text = {}
for v in range(1, t + 1):
    for line in (ROOT / 'data' / s.split('@')[0] / '01_parsed' / f'v{v:02d}.jsonl').open(encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            text[r['para_id']] = r['text']


def timeline_cites(r):
    lines = (ROOT / 'dist' / s / 'wiki' / f'v{t:02d}' / r['page']).read_text(encoding='utf-8').splitlines()
    key = plain(r.get('unit') or r['value'])[:60]
    for i, line in enumerate(lines):
        if key and key in plain(line):
            for nxt in lines[i:i + 4]:
                ids = [f"v{int(a):02d}:c{int(b):02d}:p{int(c):04d}" for a, b, c in ANCHOR.findall(nxt)]
                if ids and 'ource' in nxt:
                    return ids
    return []


pages = collections.OrderedDict()
for i, line in enumerate((ROOT / 'docs/eval/precision' / f'{s}_v{t}_all.jsonl').open(encoding='utf-8')):
    r = json.loads(line)
    ev, tag = list(r.get('evidence') or []), ''
    if not ev and r['page'].startswith('timeline/'):
        ev, tag = timeline_cites(r), 'TIMELINE '
    if not ev:
        continue
    pages.setdefault(r['page'], []).append((i, r, ev, tag))

for page, rows in pages.items():
    print(f"\n=== {page}")
    want = collections.defaultdict(set)
    for i, r, ev, tag in rows:
        for pid in ev:
            want[pid] |= words(r['value'])
    for pid in sorted(want):
        p = text.get(pid, '(not in volumes <= t)')
        if len(p) > cap:
            hits = [m.start() for m in re.finditer(r"[A-Za-z']+", p) if m.group(0).lower() in want[pid]]
            a = max(0, min((hits[len(hits) // 2] if hits else 0) - cap // 2, len(p) - cap))
            p = ('...' if a else '') + p[a:a + cap] + ('...' if a + cap < len(text[pid]) else '') + f' (of {len(text[pid])})'
        print(f"  <{pid[4:]}> {p}" if all(x.startswith(pid[:3]) for x in want) else f"  <{pid}> {p}")
    for i, r, ev, tag in rows:
        short = ' '.join(e[4:] if e.startswith(sorted(want)[0][:3]) and all(x.startswith(e[:3]) for x in want) else e for e in ev)
        fe = ' FRAME_ERROR' if r.get('human') == 'frame_error' else ''
        print(f"  [{i}] {tag}{r['surface']} {r.get('human')}{fe} | {r['value']} | {short}")
