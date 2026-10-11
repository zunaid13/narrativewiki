"""A/B a candidate `verify` system prompt on stored prompts, without a full re-verification.

Volumes 1-2 only. Re-sends the recorded user prompts of one `wiki verify` run -- every fact whose
verdict flipped against the series' earlier verify runs, plus every PERSONALITY fact (to catch a
candidate that rejects true traits) -- under `CANDIDATE`, through the cached, budgeted client.
Run: python scripts/eval/replay_verify_prompt.py <series> <verify-run-id>
Writes docs/eval/replay_verify_<series>.json.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from narrativewiki import paths, provenance
from narrativewiki.config import load_settings
from narrativewiki.graph import verify
from narrativewiki.llm.client import LLMClient

CANDIDATE = verify._SYSTEM_PROMPT + (
    " For a PERSONALITY fact, the evidence must show a lasting trait of this character: not a"
    " passing state (being drunk, tired or angry once), and not another character's tease,"
    " accusation or rhetorical question about them. For a relationship, the words in parentheses"
    " are part of the claim: if they describe a different relationship from the one named (e.g."
    ' "hired adventurer" for FRIEND_OF, "creator" for MENTOR_OF or CHILD_OF), the fact is not'
    " supported."
)


def verdicts(files):
    """fact line -> (supported, user prompt), later runs overriding earlier ones."""
    out = {}
    for f in files:
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            fact = re.search(r"^Fact: (.*)$", r["prompt"], re.M)
            if r.get("stage") != verify.STAGE or not fact:
                continue
            try:
                out[fact.group(1)] = (json.loads(r["response"])["supported"], r["prompt"])
            except (ValueError, KeyError):
                pass
    return out


def main(series: str, run_id: str) -> None:
    paths.set_active_series(series)
    settings = load_settings(series)
    runs = sorted(glob.glob(str(paths.DATA_DIR / "_runs" / "*-verify-*" / "calls.jsonl")))
    old = verdicts([f for f in runs if run_id not in f])
    new = verdicts([f for f in runs if run_id in f])
    picked = {k: v for k, v in new.items()
              if (k in old and old[k][0] != v[0]) or k.startswith("PERSONALITY")}
    run = provenance.start_run(series, "replay_verify_prompt", scope="upto2", volume_scope=2,
                               stage_keys=[], settings=settings)
    client = LLMClient(settings, run=run, volume_scope=2)
    rows = []
    try:
        for fact, (supported, prompt) in picked.items():
            v = client.complete_json(verify.STAGE, prompt, verify.FactVerdict, system=CANDIDATE)
            rows.append({"fact": fact[:200], "old": old.get(fact, (None,))[0], "new": supported,
                         "candidate": v.supported, "rationale": v.rationale})
            print(f"{str(rows[-1]['old']):5} {str(supported):5} {str(v.supported):5} {fact[:110]}")
        out = ROOT / "docs/eval" / f"replay_verify_{series}.json"
        out.write_text(json.dumps({"series": series, "verify_run": run_id, "replay_run": run.run_id,
                                   "candidate_suffix": CANDIDATE[len(verify._SYSTEM_PROMPT):],
                                   "rows": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        run.finish("ok")
    except Exception as exc:
        run.finish("failed", error=str(exc))
        raise


if __name__ == "__main__":
    main(*sys.argv[1:3])
