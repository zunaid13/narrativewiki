"""m8tab.py <series> ...: citation sufficiency per cutoff from the label files (timeline verdicts applied). $0."""
import json, sys, collections
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
EV = Path('docs/eval/precision')
TL = json.loads((EV / 'timeline_cite_claude.json').read_text(encoding='utf-8'))
for arg in sys.argv[1:]:
    s, ts = (arg.split(':') + [''])[:2]
    ts = [int(x) for x in ts.split(',')] if ts else [1, 2, 3, 4, 5]
    S = D = C = SC = 0
    cells = []
    for t in ts:
        rows = [json.loads(l) for l in (EV / f'{s}_v{t}_all.jsonl').open(encoding='utf-8') if l.strip()]
        c = collections.Counter()
        for i, r in enumerate(rows):
            if r.get('human') == 'frame_error':
                continue
            cite = (TL.get(s, {}).get(str(t), {}).get(str(i)) or r).get('cite') or ''
            c[cite] += 1
        d = sum(c.values())
        cited = d - c['none'] - c['']
        cells.append(f"t={t} {c['sufficient']}/{d}={c['sufficient'] / d:.3f} "
                     f"(P{c['partial']} I{c['insufficient']} none{c['none']})")
        S += c['sufficient']; D += d; C += cited; SC += c['sufficient']
    rates = []
    for cell in cells:
        a, b = cell.split()[1].split('=')[0].split('/')
        rates.append(int(a) / int(b))
    print(s, '|', ' · '.join(cells), f'| pooled {S}/{D} | mean over cutoffs {sum(rates) / len(rates):.3f} | among cited {SC}/{C}={SC / C:.3f}')
