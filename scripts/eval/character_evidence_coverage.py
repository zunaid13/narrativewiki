"""Offline evidence lineage for any series' cutoffs; no inference and no pipeline writes.

Paragraph overlap is provenance, NOT proof that a claim is expressed by a page. Graph
absence alone does not identify arbitration as the cause. Missing/stale optional artifacts
produce null measurements and explicit diagnostics, never successful zeroes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from narrativewiki import paths
from narrativewiki.graph import store

PARA = re.compile(r"^v(\d+):c\d+:p\d+$")


def visible_pid(pid, cutoff):
    match = PARA.fullmatch(pid)
    return bool(match and 1 <= int(match[1]) <= cutoff)


def citation_ids(value, cutoff):
    """Collect nested evidence IDs; never count arbitrary strings elsewhere as citations."""
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence" and isinstance(child, list):
                for item in child:
                    pid = item if isinstance(item, str) else item.get("para_id") if isinstance(item, dict) else None
                    if isinstance(pid, str) and visible_pid(pid, cutoff):
                        found.add(pid)
            else:
                found.update(citation_ids(child, cutoff))
    elif isinstance(value, list):
        for child in value:
            found.update(citation_ids(child, cutoff))
    return found


def request_coverage(calls, entities, records, cutoff, stage):
    """Recorded successful requests only; names in prompt rosters do not prove passage presence."""
    result = defaultdict(set)
    provenance = defaultdict(list)
    names = defaultdict(set)
    for entity in entities:
        names[entity["canonical"]].add(entity["entity_id"])
    seen = set()
    for call in calls:
        if call.get("stage") != stage or not call.get("response"):
            continue
        prompt = call["prompt"].split("\n\nYour previous response was rejected:")[0]
        all_ids = re.findall(r"^\[(v\d+:c\d+:p\d+)\]", prompt, re.MULTILINE)
        ids = [pid for pid in all_ids if visible_pid(pid, cutoff)]
        if not ids:
            continue
        if len(ids) != len(all_ids):
            raise ValueError("Request mixes visible and future paragraph IDs")
        if any(pid not in records or f'[{pid}] {records[pid]["text"]}' not in prompt for pid in ids):
            raise ValueError("Recorded request text differs from current parsed source")
        if stage == "claim_extract":
            match = re.match(r'Character: "([^"]+)"', prompt)
            subjects = names.get(match[1], set()) if match else set()
            if len(subjects) != 1:
                raise ValueError("Recorded character cannot be resolved uniquely against current roster")
            subject = next(iter(subjects))
        else:
            subject = "all"
        key = (subject, tuple(ids))
        if key in seen:
            continue
        seen.add(key)
        result[subject].update(ids)
        provenance[subject].append({"cache_key": call.get("cache_key"), "para_ids": ids})
    return {"paragraphs": dict(result), "requests": dict(provenance)}


def summarize(entity, cutoff, mentions, sources, graph, intervals, page, markdown, requests, replay):
    subject = entity["entity_id"]
    indexed = {m["para_id"] for m in mentions if m["entity_id"] == subject and visible_pid(m["para_id"], cutoff)}
    sets = {}
    claims = {}
    observations = {}
    for name, rows in sources.items():
        selected = None if rows is None else [c for c in rows if c["subject"] == subject and c["first_vol"] <= cutoff]
        observations[name] = None if selected is None else len(selected)
        sets[name] = None if selected is None else {c["claim_id"] for c in selected}
        for claim in selected or []:
            cid = claim["claim_id"]
            if cid not in claims:
                claims[cid] = {**claim, "evidence": list(claim["evidence"])}
            else:
                claims[cid]["evidence"].extend(claim["evidence"])
    graph_rows = None if graph is None else {c["claim_id"]: c for c in graph if c["first_vol"] <= cutoff}
    linked, active = set(), set()
    if intervals is not None and graph_rows is not None:
        for interval in intervals:
            if interval["vol_start"] > cutoff:
                continue
            ids = set(interval["claim_ids"]) & graph_rows.keys()
            linked.update(ids)
            if interval.get("vol_end") is None or interval["vol_end"] >= cutoff:
                active.update(ids)
    sections = None if page is None else {
        **{f"prose.{k}": {"present": bool(v and v.get("text")), "evidence": sorted(citation_ids(v, cutoff))}
           for k, v in page.get("prose", {}).items()},
        **{f"fields.{k}": {"present": bool(v), "evidence": sorted(citation_ids(v, cutoff))}
           for k, v in page.get("fields", {}).items()},
        "quotes": {"present": bool(page.get("quotes")), "evidence": sorted(citation_ids(page.get("quotes"), cutoff))},
        "relationship_prose": {"present": bool(page.get("relationship_prose")),
                               "evidence": sorted(citation_ids(page.get("relationship_prose"), cutoff))},
    }
    witnesses = []
    for cid, claim in sorted(claims.items()):
        evidence = citation_ids({"evidence": claim["evidence"]}, cutoff)
        status = ("graph_unavailable" if graph_rows is None else "absent_from_graph_claims" if cid not in graph_rows
                  else "intervals_unavailable" if intervals is None else "active_interval" if cid in active
                  else "historical_interval" if cid in linked else "not_linked_to_interval")
        witnesses.append({"claim_id": cid, "predicate": claim["predicate"], "value": claim.get("value"),
            "object": claim.get("object"), "polarity": claim["polarity"], "first_vol": claim["first_vol"],
            "sources": [name for name, ids in sets.items() if ids is not None and cid in ids],
            "evidence": sorted(evidence), "graph_status": status,
            "page_citation_overlap": None if sections is None else
                [name for name, section in sections.items() if evidence & set(section["evidence"])]})
    # Claims where this character is the OBJECT, not the subject. Without them the witness table
    # systematically overstates what a sparse page is missing: Saint Ruvinheigen's page renders
    # "Enemy of Holo -- attacked him in the past" from a claim whose subject is Holo, so a
    # subject-only view calls that fact absent when it is already on the page.
    inbound = []
    for name, rows in sources.items():
        for claim in rows or []:
            if claim.get("object") == subject and claim["first_vol"] <= cutoff:
                inbound.append({"claim_id": claim["claim_id"], "subject": claim["subject"],
                    "predicate": claim["predicate"], "polarity": claim["polarity"], "source": name,
                    "evidence": sorted(citation_ids({"evidence": claim["evidence"]}, cutoff)),
                    "graph_status": "graph_unavailable" if graph_rows is None
                        else "absent_from_graph_claims" if claim["claim_id"] not in graph_rows
                        else "in_graph"})
    inbound = list({(w["claim_id"], w["source"]): w for w in inbound}.values())
    scene_witnesses = None if replay is None else [w for w in replay if w.get("subject") == subject and w["vol"] <= cutoff]
    request_info = {}
    for name, coverage in requests.items():
        key = subject if name == "window" else "all"
        sent = None if coverage is None else coverage["paragraphs"].get(key, set())
        # The scene pass asks about every character at once, so its roster and provenance are
        # stage-level, not per-character: reported once at `scene_requests`, never copied here.
        # What IS per-character is the diff below -- the mention paragraphs no request carried.
        request_info[name] = {"recorded_paragraph_count": None if sent is None else len(sent),
            "mention_paragraphs_not_in_recorded_requests": None if sent is None else sorted(indexed - sent)}
        if name == "window":  # per-character; `recorded_paragraph_count` is the union of these
            request_info[name]["requests"] = None if coverage is None else coverage["requests"].get(key, [])
    return {"entity_id": subject, "canonical": entity["canonical"], "mention_paragraphs": sorted(indexed),
        "source_observations": observations,
        "source_unique_claims": {name: None if ids is None else len(ids) for name, ids in sets.items()},
        "observed_claim_union": len(claims), "claim_sources_complete": all(v is not None for v in sets.values()),
        "source_overlap_claim_ids": sorted(set.intersection(*(v for v in sets.values()))) if all(v is not None for v in sets.values()) else None,
        "graph_status_counts": None if graph_rows is None else dict(Counter(w["graph_status"] for w in witnesses)),
        "scene_proposals": None if scene_witnesses is None else {
            "observations": len(scene_witnesses), "outcomes": dict(Counter(w["outcome"] for w in scene_witnesses)),
            "accepted_unique": len({w["claim_id"] for w in scene_witnesses if w["outcome"] == "accepted"}),
            "witnesses": scene_witnesses},
        "requests": request_info, "page_sections": sections,
        "inbound_claims": inbound, "inbound_claim_count": len(inbound),
        "markdown_whitespace_tokens": None if markdown is None else len(markdown.split()),
        "inferred_fields": None if page is None else [k for k, v in page.get("fields", {}).items() if isinstance(v, dict) and v.get("inferred")],
        "claims": witnesses}


class Reader:
    def __init__(self):
        self.hashes = {}
        self.issues = []

    def read(self, path, kind="json", required=False):
        try:
            raw = path.read_bytes()
            self.hashes[paths.relative(path)] = hashlib.sha256(raw).hexdigest()
            text = raw.decode("utf-8")
            return json.loads(text) if kind == "json" else [json.loads(line) for line in text.splitlines() if line.strip()] if kind == "jsonl" else text
        except (OSError, ValueError) as exc:
            if required:
                raise ValueError(f"Required input unavailable: {path}: {exc}") from exc
            self.issues.append({"path": paths.relative(path), "issue": "unavailable", "detail": str(exc)})
            return None


def load_requests(reader, run_id, command, entities, records, cutoff):
    if Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("Invalid run ID")
    manifest_path = paths.run_dir(run_id) / "manifest.json"
    manifest = reader.read(manifest_path)
    if manifest is None:
        return None
    if (manifest.get("series_id") != paths.active_series() or manifest.get("command") != command
            or manifest.get("outcome") != "ok" or not manifest.get("volumes")
            or not set(manifest["volumes"]) <= set(ingested_volumes())
            or not set(range(1, cutoff + 1)) <= set(manifest["volumes"])):
        reader.issues.append({"path": paths.relative(manifest_path), "issue": "incompatible_or_incomplete_run"})
        return None
    calls = reader.read(paths.run_dir(run_id) / "calls.jsonl", "jsonl")
    if calls is None:
        return None
    try:
        return request_coverage(calls, entities, records, cutoff, "scene_extract" if command == "scenes" else "claim_extract")
    except ValueError as exc:
        reader.issues.append({"path": paths.relative(manifest_path), "issue": "stale_recording", "detail": str(exc)})
        return None


def load_replay(reader, path, cutoff, scene_run):
    replay = reader.read(path)
    if replay is None:
        return None
    if replay.get("run_id") != scene_run or not set(range(1, cutoff + 1)) <= set(replay.get("volumes", [])):
        reader.issues.append({"path": paths.relative(path), "issue": "incompatible_replay"})
        return None
    mismatches = []
    for name, expected in replay.get("input_sha256", {}).items():
        match = re.search(r"/(?:scene_)?v(\d+)\.jsonl$", name.replace("\\", "/"))
        if match and int(match[1]) > cutoff:
            continue
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT.resolve()):
            raise ValueError("Replay fingerprint path escapes repository")
        try:
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError:
            actual = None
        if actual != expected:
            mismatches.append(name)
    if not replay.get("input_sha256") or mismatches:
        reader.issues.append({"path": paths.relative(path), "issue": "stale_replay", "mismatches": mismatches})
        return None
    return replay["witnesses"]


def ingested_volumes():
    """The volumes this series actually has parsed on disk, ascending. The scope a report may
    cover is whatever was ingested -- not a literal volume list. The old `(1, 2)` guard was a
    spend guard copied into a script that makes no model calls, so all it did was stop the
    diagnostic being pointed at the next series."""
    return [v for v in range(1, 100) if paths.parsed_volume(v).is_file()]


def build_report(cutoff, scene_run, extract_run):
    available = ingested_volumes()
    if cutoff not in available:
        raise ValueError(f"No parsed volume {cutoff} for series {paths.active_series()!r}; "
                         f"ingested volumes are {available or 'none'}")
    reader = Reader()
    gazetteer = reader.read(paths.gazetteer(), required=True)
    entities = [e for e in gazetteer["entities"] if e["type"] == "CHARACTER" and e["first_vol"] <= cutoff]
    mentions = reader.read(paths.mentions(), "jsonl", required=True)
    records = {}
    sources = {"window": [], "scene": []}
    for vol in range(1, cutoff + 1):
        records.update({r["para_id"]: r for r in reader.read(paths.parsed_volume(vol), "jsonl", required=True)})
        for name, path in (("window", paths.claims_volume(vol)), ("scene", paths.scene_claims_volume(vol))):
            rows = reader.read(path, "jsonl")
            if rows is None:
                sources[name] = None
            elif sources[name] is not None:
                sources[name].extend(rows)
    requests = {"scene": load_requests(reader, scene_run, "scenes", entities, records, cutoff),
                "window": load_requests(reader, extract_run, "extract", entities, records, cutoff)}
    replay = load_replay(reader, ROOT / "docs/eval" / f"scene_facts_{paths.active_series()}.json",
                         cutoff, scene_run)
    graph = intervals = None
    try:
        # Read-only SQLite mode never creates a missing database or applies migrations.
        with store.connect(read_only=True) as conn:
            graph = [dict(r) for r in conn.execute("SELECT * FROM claims WHERE first_vol <= ?", (cutoff,))]
            intervals = [{**dict(r), "claim_ids": json.loads(r["claim_ids_json"])} for r in
                         conn.execute("SELECT * FROM intervals WHERE vol_start <= ?", (cutoff,))]
        reader.hashes[paths.relative(paths.graph_db())] = hashlib.sha256(paths.graph_db().read_bytes()).hexdigest()
    except (OSError, ValueError, store.sqlite3.Error) as exc:
        reader.issues.append({"path": paths.relative(paths.graph_db()), "issue": "graph_unavailable", "detail": str(exc)})
        graph = intervals = None
    characters = []
    for entity in sorted(entities, key=lambda e: e["entity_id"]):
        eid = entity["entity_id"]
        page = reader.read(paths.page_json(eid, cutoff))
        if page is not None and (page.get("upto_vol") != cutoff or page.get("entity_id") != eid):
            reader.issues.append({"path": paths.relative(paths.page_json(eid, cutoff)), "issue": "page_scope_mismatch"})
            page = None
        markdown = reader.read(paths.wiki_cutoff_dir(cutoff) / "character" / f"{eid}.md", "text")
        characters.append(summarize(entity, cutoff, mentions, sources, graph, intervals, page, markdown, requests, replay))
    lengths = [c["markdown_whitespace_tokens"] for c in characters if c["markdown_whitespace_tokens"] is not None]
    reader.read(Path(__file__), "text", required=True)
    return {"series": paths.active_series(), "cutoff": cutoff, "model_calls": 0,
        "source_runs": {"scene": scene_run, "window": extract_run},
        "definitions": {"page_length": "len(markdown.split()), including YAML, headings, links and placeholders; not natural-language word count",
            "page_citation_overlap": "shared paragraph provenance only, not semantic fact coverage",
            "graph_status": "claim-ID linkage, not proof of arbitration cause or render eligibility",
            "inbound_claims": "claims naming this character as OBJECT; they reach the page too, so subject-only counts understate coverage",
            "requests": "successful recorded requests; current selector intent is not reconstructed",
            "scene_requests": "stage-level: one scene request asks about every character, so this roster is not per-character",
            "scene_proposals": "parsed fact observations from a hash-validated replay; unresolved subjects remain separate"},
        "length_summary": {"measured_pages": len(lengths), "visible_characters": len(characters),
            "min": min(lengths) if lengths else None, "median": statistics.median(lengths) if lengths else None,
            "max": max(lengths) if lengths else None,
            "ratio": max(lengths) / min(lengths) if lengths and min(lengths) else None},
        "scene_requests": None if requests["scene"] is None else {
            "recorded_paragraph_count": len(requests["scene"]["paragraphs"].get("all", set())),
            "requests": requests["scene"]["requests"].get("all", [])},
        "unresolved_scene_proposals": None if replay is None else [w for w in replay if w["vol"] <= cutoff and w.get("subject") is None],
        "characters": characters, "issues": reader.issues, "input_sha256": reader.hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", "-s", default="spice-and-wolf")
    parser.add_argument("--cutoff", type=int, default=None,
                        help="Default: the highest ingested volume for this series.")
    parser.add_argument("--scene-run", default="20260922T211717-scenes-v1-2")
    parser.add_argument("--extract-run", default="20260922T212119-extract-v1-2")
    args = parser.parse_args()
    paths.set_active_series(args.series)
    cutoff = args.cutoff if args.cutoff is not None else max(ingested_volumes(), default=0)
    report = build_report(cutoff, args.scene_run, args.extract_run)
    output = ROOT / "docs/eval" / f"character_evidence_coverage_{args.series}_v{cutoff:02d}.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.name, "length_summary": report["length_summary"], "issues": report["issues"],
        "characters": [{"entity_id": c["entity_id"], "length": c["markdown_whitespace_tokens"],
                        "claims": c["source_unique_claims"], "graph": c["graph_status_counts"]}
                       for c in sorted(report["characters"], key=lambda c: c["markdown_whitespace_tokens"] or 0)]}, indent=2))


if __name__ == "__main__":
    main()
