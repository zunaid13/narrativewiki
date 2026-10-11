"""The reviewed sparse-character fixture must stay bound to the corpus it was read from.

A hand-made label file rots silently: a quote gets retyped, a claim_id changes when extraction
is rerun, a paragraph moves. Then a prompt experiment is scored against fiction. These checks
fail instead. They skip when the gitignored corpus/graph are absent (docs/vision/plans/0006: never turn
an unavailable recording into a successful zero).
"""
import json
from pathlib import Path

import pytest

from narrativewiki import paths
from narrativewiki.graph import store

FIXTURE = Path(__file__).resolve().parents[1] / "docs/eval/fixtures/sparse_character_evidence.json"
STATUSES = {"already_covered", "covered_with_defect", "missing", "must_not_assert"}


@pytest.fixture(scope="module")
def fixture_doc():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def corpus():
    paths.set_active_series("spice-and-wolf")
    records = {}
    for vol in (1, 2):
        path = paths.parsed_volume(vol)
        if not path.is_file():
            pytest.skip(f"{path} absent (gitignored corpus)")
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                records[record["para_id"]] = record["text"]
    return records


def test_fixture_is_well_formed_and_holds_out_some_facts(fixture_doc):
    facts = fixture_doc["facts"]
    assert len({f["id"] for f in facts}) == len(facts)
    assert {f["status"] for f in facts} <= STATUSES
    assert {f["split"] for f in facts} == {"dev", "holdout"}
    # A change designed on the dev facts has to be judged on facts it never saw.
    assert sum(f["split"] == "holdout" for f in facts) >= 3
    # Without both, the fixture measures only recall and would reward a change that invents facts.
    assert any(f["status"] == "missing" for f in facts)
    assert any(f["status"] == "must_not_assert" for f in facts)
    for fact in facts:
        assert fact["cutoff"] == int(fact["para_id"][1:3]), fact["id"]
        if fact["status"] in {"already_covered", "covered_with_defect"}:
            assert fact.get("covered_by_claim_id"), fact["id"]


def test_every_reviewed_quote_is_verbatim_in_the_paragraph_it_cites(fixture_doc, corpus):
    for fact in fixture_doc["facts"]:
        assert fact["para_id"] in corpus, f"{fact['id']}: {fact['para_id']} not in the corpus"
        assert fact["quote"] in corpus[fact["para_id"]], f"{fact['id']}: quote not verbatim"


def test_covered_facts_still_point_at_claims_that_exist(fixture_doc):
    paths.set_active_series("spice-and-wolf")
    if not paths.graph_db().is_file():
        pytest.skip("graph.db absent (gitignored)")
    cited = {f["covered_by_claim_id"] for f in fixture_doc["facts"] if f.get("covered_by_claim_id")}
    with store.connect(read_only=True) as conn:
        rows = conn.execute(
            f"SELECT claim_id FROM claims WHERE claim_id IN ({','.join('?' * len(cited))})",
            sorted(cited),
        ).fetchall()
    missing = cited - {r["claim_id"] for r in rows}
    assert not missing, f"fixture cites claim_ids the graph no longer has: {sorted(missing)}"
