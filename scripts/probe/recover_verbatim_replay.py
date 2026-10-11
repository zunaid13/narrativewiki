"""Replay stored `claim_extract` responses through the verbatim-quote gate, with and without
`resolve.recover_verbatim` -- how many facts the old gate dropped only for lost quote marks.

$0: reads `_runs/<id>/calls.jsonl` and `01_parsed/`, makes no LLM call. Counts facts, not claims:
a rescued fact still has to pass the later gates (confidence, adequacy) to become a claim.

    python scripts/probe/recover_verbatim_replay.py spice-and-wolf 20260924T170809-extract-v1-1 20260924T171218-extract-v2-2
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from narrativewiki.extract.resolve import recover_verbatim, unwrap_quote

series, run_ids = sys.argv[1], sys.argv[2:]
data = Path("data") / series
paras = {}
for f in (data / "01_parsed").glob("v*.jsonl"):
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            paras[r["para_id"]] = r["text"]

counts: Counter[str] = Counter()
for run_id in run_ids:
    for line in (data / "_runs" / run_id / "calls.jsonl").read_text(encoding="utf-8").splitlines():
        call = json.loads(line)
        if call.get("stage") != "claim_extract":
            continue
        try:
            facts = json.loads(call.get("response") or "{}").get("facts") or []
        except json.JSONDecodeError:
            counts["unparsable_response"] += 1
            continue
        for fact in facts:
            text = paras.get(fact.get("para_id") or "")
            quote = unwrap_quote((fact.get("quote") or "").strip())
            if text is None or not quote:
                counts["no_paragraph_or_quote"] += 1
            elif quote in text:
                counts["verbatim"] += 1
            elif recover_verbatim(quote, text) is not None:
                counts["rescued_by_quote_marks"] += 1
            else:
                counts["still_not_verbatim"] += 1

print(json.dumps(dict(counts), indent=2))
