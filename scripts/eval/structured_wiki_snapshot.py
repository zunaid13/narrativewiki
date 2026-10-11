"""Read-only review of S&W v1-2 plus synthetic counterexamples; no model calls.

Writes only docs/eval/structured_wiki_snapshot_spice-and-wolf.json. Production databases are opened mode=ro.
Counterexamples establish behavior, not its frequency in the live corpus.
"""
from pathlib import Path
import hashlib
import json
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from narrativewiki.extract.schema import ExtractedFact, make_claim_id
from narrativewiki.extract.claims import _merge_claim
from narrativewiki.graph import store, temporal
from narrativewiki.site.bundle import _relation_entries_between, _members_and_related
from narrativewiki.synth.assemble import _is_renderable
from narrativewiki.eval.gold import score_fact_precision, score_fact_recall, GoldFact


def main():
    report = {"review_id": "20260924-structured-wiki-review", "series": "spice-and-wolf",
              "volumes": [1, 2], "model_calls": 0,
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    fact = ExtractedFact(kind="attribute", predicate="STATUS", value="dead",
                         para_id="v01:c00:p0001", quote="If he died", polarity="hypothetical")
    first = dict(claim_id=make_claim_id("a", "STATUS", "dead", 1), polarity="asserted",
                 qualifier="report A", evidence=[{"para_id": "v01:c00:p0001", "quote": "A"}], confidence=.8)
    second = dict(first, polarity="denied", qualifier="report B",
                  evidence=[{"para_id": "v01:c00:p0002", "quote": "B"}])
    _merge_claim(first, second)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(store.SCHEMA)
    conn.execute("INSERT INTO intervals VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 ("i_test", "a", "AFFILIATED_WITH", "f", None, "member", 1, 1, '["c_test"]', "i_future", .9, 1))
    conn.execute("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 ("c_test", "a", "AFFILIATED_WITH", "relation", "f", None, "member", 1, .9, "denied", "[]", "fixture"))
    row = conn.execute("SELECT * FROM intervals").fetchone()
    entry = _relation_entries_between([row], {"AFFILIATED_WITH": {"display": "Affiliated with"}})
    members, _, _ = _members_and_related(conn, "f", 2, {"a": {"type": "CHARACTER"}, "f": {"type": "FACTION"}},
                                         {"AFFILIATED_WITH": {"membership": True}})
    report["synthetic"] = {
        "invalid_polarity_hypothetical_becomes": fact.polarity,
        "same_claim_id_opposite_polarity_merge": {"polarity_retained": first["polarity"],
                                                 "qualifier_retained": first["qualifier"],
                                                 "evidence_items": len(first["evidence"])},
        "expired_relation_returned_by_relations_at": len(temporal.relations_at(conn, "a", 2)),
        "expired_relation_returned_by_relations_between": len(temporal.relations_between(conn, "a", "f", 2)),
        "denied_relation_pair_projection": entry,
        "denied_expired_relation_codex_members": members,
        "no_verdict_renderable": _is_renderable(row, {}),
        "future_cutoff_unsupported_verdict_hides_earlier_row": not _is_renderable(row, {
            "i_test": {"verdict": "unsupported", "evidence_cutoff": 2}}),
    }
    # Separate future endpoint witness: at cutoff 1, end=2 reveals a future boundary.
    conn.execute("UPDATE intervals SET vol_end=2")
    visible = temporal.relations_between(conn, "a", "f", 1)
    report["synthetic"]["future_endpoint_at_cutoff_1"] = _relation_entries_between(visible, {})[0].get("until_vol")
    conn.close()

    data = ROOT / "data/spice-and-wolf"
    db = data / "04_graph/graph.db"
    live = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
    live.row_factory = sqlite3.Row
    counts = {}
    for table in ["claims", "intervals", "verdicts"]:
        counts[table] = live.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    counts["claim_polarities"] = dict(live.execute("SELECT polarity,COUNT(*) FROM claims GROUP BY polarity"))
    counts["verdicts_by_cutoff"] = [list(r) for r in live.execute("SELECT evidence_cutoff,verdict,COUNT(*) FROM verdicts GROUP BY evidence_cutoff,verdict")]
    report["live"] = counts
    report["live"]["nonasserted_relations"] = [dict(r) for r in live.execute(
        "SELECT claim_id,subject,predicate,object,polarity,first_vol FROM claims WHERE kind='relation' AND polarity!='asserted' AND first_vol<=2")]
    live.close()
    # A positive match plus arbitrary unsupported prose must not be mistaken for full precision.
    gold = GoldFact(text="Alice has blue eyes", in_scope=True)
    page = {"canonical": "Alice", "prose": {"appearance": {"text": "Alice has blue eyes. Alice rules the moon."}}}
    report["synthetic"]["selected_gold_precision_with_unjudged_extra_assertion"] = score_fact_precision([gold], [], page)
    report["synthetic"]["structured_trait_only_recall"] = score_fact_recall(
        [GoldFact(text="Alice can see in darkness", in_scope=True)],
        {"canonical": "Alice", "traits": {"abilities": [{"value": "can see in darkness"}]}})
    pair_path = data / "06_bundle/relationships/kraft-lawrence--zheren.json"
    pair = json.loads(pair_path.read_text(encoding="utf-8"))
    report["live"]["zheren_pair_cutoff_1_relations"] = pair["cutoffs"]["1"]["relations"]
    files = ["src/narrativewiki/extract/schema.py", "src/narrativewiki/extract/claims.py",
             "src/narrativewiki/graph/temporal.py", "src/narrativewiki/graph/store.py",
             "src/narrativewiki/site/bundle.py", "src/narrativewiki/synth/assemble.py",
             "src/narrativewiki/eval/gold.py", "config/extraction.yaml",
             "data/spice-and-wolf/04_graph/graph.db",
             "data/spice-and-wolf/06_bundle/relationships/kraft-lawrence--zheren.json",
             "docs/eval/character_evidence_coverage_spice-and-wolf_v02.json"]
    report["input_sha256"] = {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    output = ROOT / "docs/eval/structured_wiki_snapshot_spice-and-wolf.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "input_sha256"}, indent=2))


if __name__ == "__main__":
    main()
