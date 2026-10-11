"""Replay recorded scene facts through current gates, without models or artifact mutation.

Spice and Wolf volumes 1-2 only. Counts are observations before claim-ID deduplication,
not recall or proof of entailment. Uses current gazetteer/mentions; hashes identify inputs.
Run: python scripts/eval/replay_scene_facts.py --run-id <scenes-run>
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from narrativewiki import paths
from narrativewiki.config import load_settings
from narrativewiki.extract.resolve import resolve_surface
from narrativewiki.extract.scene_schema import SceneDetailResult
from narrativewiki.extract.scenes import _build_participant_fact
from narrativewiki.extract.spans import Span, _format_span


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        parser.error("run-id must be a directory name")
    paths.set_active_series("spice-and-wolf")
    run = paths.run_dir(args.run_id)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("series_id") != "spice-and-wolf" or manifest.get("command") != "scenes"
            or manifest.get("outcome") != "ok" or not manifest.get("volumes")
            or not set(manifest["volumes"]) <= {1, 2}):
        parser.error("requires a successful Spice and Wolf scenes run scoped to volumes 1-2")
    settings = load_settings("spice-and-wolf")
    inputs = [manifest_path, run / "calls.jsonl", paths.gazetteer(), paths.mentions(),
              paths.extraction_config(), Path(__file__).resolve()]
    inputs += [ROOT / "src/narrativewiki/extract" / name for name in
               ("scenes.py", "adequacy.py", "resolve.py", "scene_schema.py", "schema.py", "spans.py")]
    entities = {e["entity_id"]: e for e in json.loads(paths.gazetteer().read_text(encoding="utf-8"))["entities"]}
    mentions = read_jsonl(paths.mentions())
    records = {}
    for vol in manifest["volumes"]:
        inputs.append(paths.parsed_volume(vol))
        records.update({r["para_id"]: r for r in read_jsonl(paths.parsed_volume(vol))})

    totals = Counter()
    by_subject = defaultdict(Counter)
    witnesses = []
    accepted_ids = defaultdict(set)
    seen = set()
    for call in read_jsonl(run / "calls.jsonl"):
        if call.get("stage") != "scene_extract":
            continue
        # Transport retry counts do not change a successful response's identity.
        # JSON repair prompts need explicit handling rather than double-counting facts.
        if "Your previous response" in call["prompt"]:
            raise ValueError("JSON repair present: replay requires an unrepaired recording")
        raw = json.loads(call["response"])
        if "participant_facts" not in raw:
            if "beat_summary" in raw:
                continue
            raise ValueError("Unrecognized scene response")
        key = call["cache_key"]
        if key in seen:
            raise ValueError("Duplicate detail call in recording")
        seen.add(key)
        detail = SceneDetailResult.model_validate(raw)
        ids = tuple(re.findall(r"^\[(v\d+:c\d+:p\d+)\]", call["prompt"], re.MULTILINE))
        if not ids or any(pid not in records for pid in ids):
            raise ValueError("Recorded passage is absent from scoped parsed inputs")
        first = records[ids[0]]
        if any((records[pid]["vol"], records[pid]["chapter_idx"]) !=
               (first["vol"], first["chapter_idx"]) for pid in ids):
            raise ValueError("Recorded span crosses chapters")
        # Verify the evidence text, not just IDs, against the exact recorded passage.
        for pid in ids:
            if f'[{pid}] {records[pid]["text"]}' not in call["prompt"]:
                raise ValueError(f"Parsed text drift: {pid}")
        passage = _format_span([records[pid] for pid in ids], 0, len(ids) - 1)
        span = Span(first["vol"], first["chapter_idx"], 0, ids, ids, passage)
        chapter_mentions = [m for m in mentions if m["para_id"].startswith(
            f'v{span.vol:02d}:c{span.chapter_idx:02d}:')]
        totals["detail_responses"] += 1
        raw_count = sum(len(g.get("facts", [])) for g in raw["participant_facts"])
        parsed_count = sum(len(g.facts) for g in detail.participant_facts)
        totals["raw_facts"] += raw_count
        totals["schema_dropped"] += raw_count - parsed_count
        for group in detail.participant_facts:
            subject = resolve_surface(group.subject, chapter_mentions, span.text)
            for fact in group.facts:
                drops = Counter()
                claim = None
                if subject is None:
                    drops["participant_fact_subject_unresolved"] += 1
                else:
                    claim = _build_participant_fact(subject, fact, span, chapter_mentions,
                        records, entities, settings, call["model"], drops)
                outcome = "accepted" if claim else next(iter(drops))
                totals[outcome] += 1
                by_subject[subject or f"unresolved:{group.subject}"][outcome] += 1
                if claim:
                    accepted_ids[subject].add(claim["claim_id"])
                witnesses.append({"cache_key": key, "subject": subject, "surface": group.subject,
                    "vol": span.vol, "fact": fact.model_dump(), "outcome": outcome,
                    "claim_id": claim["claim_id"] if claim else None})
    if not seen:
        raise ValueError("No detail responses found")
    for subject, entity in entities.items():
        if entity["type"] == "CHARACTER" and entity["first_vol"] <= max(manifest["volumes"]):
            by_subject[subject]["unique_accepted_claims"] = len(accepted_ids[subject])
            by_subject[subject]["indexed_mention_paragraphs"] = len({m["para_id"] for m in mentions
                if m["entity_id"] == subject and m["vol"] in manifest["volumes"]})
    totals["unique_accepted_claims"] = sum(map(len, accepted_ids.values()))
    replay_ids = set().union(*accepted_ids.values())
    persisted_ids = set()
    for vol in manifest["volumes"]:
        path = paths.scene_claims_volume(vol)
        inputs.append(path)
        persisted_ids.update(c["claim_id"] for c in read_jsonl(path))
    comparison = {"only_replayed": sorted(replay_ids - persisted_ids),
                  "only_persisted": sorted(persisted_ids - replay_ids)}
    report = {"run_id": args.run_id, "series": "spice-and-wolf", "volumes": manifest["volumes"],
        "model_calls": 0, "measurement": "recorded fact observations through current gates, not recall; no deduplication",
        "totals": dict(totals), "by_subject": dict(sorted(by_subject.items())), "witnesses": witnesses,
        "current_scene_claim_id_comparison": comparison,
        "input_sha256": {paths.relative(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    output = (ROOT / "docs/eval").joinpath("scene_facts_spice-and-wolf.json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"totals": totals, "by_subject": report["by_subject"],
                      "current_scene_claim_id_comparison": comparison}, indent=2))


if __name__ == "__main__":
    main()
