"""m8recf.py <series> <t>: record docs/eval/precision/labels_claude/<series>_v<t>.cite.json with m8rec.py (no shell quoting)."""
import json, subprocess, sys

s, t = sys.argv[1], sys.argv[2]
lab = json.load(open(f'docs/eval/precision/labels_claude/{s}_v{t}.cite.json', encoding='utf-8'))
sys.exit(subprocess.call([sys.executable, 'docs/eval/labelling_tools/m8rec.py', s, t, json.dumps(lab, ensure_ascii=False)]))
