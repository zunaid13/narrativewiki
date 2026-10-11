"""NLI boundaries: source grounding, cutoff safety, cache, and pre-pruning arbitration.

These tests require no model downloads or optional inference libraries.
"""
import copy
import json
from types import SimpleNamespace

import pytest

from narrativewiki import paths, provenance
from narrativewiki.config import load_settings
from narrativewiki.graph import contradictions as CO, store, support
from narrativewiki.llm.cache import LLMCache
from narrativewiki.llm.client import LLMClient, LLMError
from narrativewiki.llm.providers import minicheck
from narrativewiki.llm.providers.base import Completion, ProviderError


ENTITIES = {
    "zheren": {"entity_id": "zheren", "canonical": "Zheren", "type": "CHARACTER", "first_vol": 1},
    "lawrence": {"entity_id": "lawrence", "canonical": "Lawrence", "type": "CHARACTER", "first_vol": 1},
}


def claim(cid="c_a", value="merchant", confidence=0.7, vol=1, **updates):
    return {"claim_id": cid, "subject": "zheren", "predicate": "OCCUPATION", "kind": "attribute",
            "object": None, "value": value, "qualifier": None, "first_vol": vol,
            "confidence": confidence, "polarity": "asserted", "source": "test",
            "evidence": [{"para_id": f"v{vol:02d}:c00:p0001", "quote": "Zheren is a merchant."}], **updates}


@pytest.fixture
def settings():
    return copy.deepcopy(load_settings("spice-and-wolf"))


@pytest.fixture
def parsed(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "parsed_volume", lambda vol: tmp_path / f"v{vol:02d}.jsonl")
    rows = [
        {"para_id": "v01:c00:p0000", "vol": 1, "text": "They met at the inn."},
        {"para_id": "v01:c00:p0001", "vol": 1, "text": "Zheren is a merchant."},
        {"para_id": "v01:c01:p0000", "vol": 1, "text": "OTHER CHAPTER SECRET"},
        {"para_id": "v02:c00:p0001", "vol": 2, "text": "FUTURE SECRET"},
    ]
    paths.parsed_volume(1).write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return tmp_path


class Scorer:
    def __init__(self, score=0.9):
        self.score = score
        self.calls = []

    def score_support(self, documents, hypothesis):
        self.calls.append((documents, hypothesis))
        return {"score": self.score, "chunks": [{"score": self.score, "document_index": 0, "text": documents[0]}],
                "model": "minicheck:test", "revision": "revision"}


def test_support_uses_discovery_volume_even_when_claim_has_later_evidence(parsed, settings):
    c = claim()
    c["evidence"].append({"para_id": "v02:c00:p0001", "quote": "FUTURE SECRET"})
    client = Scorer()
    result = support.score_claims([c], ENTITIES, settings, client)["c_a"]
    doc = " ".join(client.calls[0][0])
    assert "They met at the inn." in doc
    assert "Zheren is a merchant." in doc
    assert "SECRET" not in doc
    assert result["evidence_cutoff"] == 1
    assert result["extracted_confidence"] == 0.7
    assert len(result["context_sha256"]) == 64
    c["confidence"] = 1.0
    again = support.score_claims([c], ENTITIES, settings, client)["c_a"]
    assert again["context_sha256"] == result["context_sha256"]


@pytest.mark.parametrize("evidence", [[], [{"para_id": "v01:c00:p9999", "quote": "missing"}],
                                     [{"para_id": "v01:c00:p0001", "quote": "invented"}],
                                     [{"para_id": "invalid", "quote": "invented"}]])
def test_support_missing_grounding_never_becomes_a_verdict(parsed, settings, evidence):
    client = Scorer()
    with pytest.raises(ValueError):
        support.score_claims([claim(evidence=evidence)], ENTITIES, settings, client)
    assert client.calls == []


def test_support_hypothesis_keeps_direction_and_polarity(settings):
    c = claim(predicate="SAVED", kind="relation", object="lawrence", value=None)
    assert support.hypothesis(c, ENTITIES, settings) == "Zheren saved Lawrence."
    assert support.hypothesis({**c, "polarity": "denied"}, ENTITIES, settings) == "It is not true that Zheren saved Lawrence."
    assert support.hypothesis({**c, "polarity": "presumed"}, ENTITIES, settings).startswith("It is believed that ")
    with pytest.raises(ValueError, match="template"):
        support.hypothesis({**c, "predicate": "UNKNOWN_RELATION"}, ENTITIES, settings)


def test_support_ranks_all_candidates_before_pruning_without_mutating_confidence(settings):
    claims = [claim("public", "public witness", 1.0), claim("other", "soldier", 0.99),
              claim("merchant", "merchant", 0.72)]
    original = copy.deepcopy(claims)
    scores = {"public": {"score": 0.01}, "other": {"score": 0.03}, "merchant": {"score": 0.96}}
    intervals, _, doc = CO.build_graph(claims, settings, None, support_scores=scores)
    assert intervals[0]["value"] == "merchant"
    assert intervals[0]["confidence"] == 0.72
    assert claims == original
    assert {c["arbiter"] for c in doc["conflicts"]} == {"nli:lower_support_dropped", "nli:higher_support"}
    assert doc["support_scores"] == scores
    assert all("support_score" in c["a"] and "support_score" in c["b"] for c in doc["conflicts"])


@pytest.mark.parametrize("score", [None, float("nan"), float("inf"), -0.1, 1.1, True])
def test_support_missing_or_invalid_scores_cannot_fall_back_to_confidence(settings, score):
    with pytest.raises(ValueError, match="support score"):
        CO.build_graph([claim()], settings, None, support_scores={"c_a": {"score": score}})


def test_support_ambiguous_tie_is_flagged_independent_of_input_order_and_confidence(settings):
    a, b = claim("a", "merchant", 0.6), claim("b", "soldier", 1.0)
    scores = {"a": {"score": 0.9}, "b": {"score": 0.9}}
    for rows in ([a, b], [b, a]):
        intervals, _, doc = CO.build_graph(rows, settings, None, support_scores=scores)
        assert intervals[0]["value"] == "merchant"
        assert doc["conflicts"][0]["resolution"] == "flag"
        assert doc["conflicts"][0]["arbiter"] == "nli:ambiguous"


def test_support_no_supported_winner_stays_flagged(settings):
    rows = [claim("a", "merchant"), claim("b", "soldier")]
    _, _, doc = CO.build_graph(rows, settings, None, support_scores={"a": {"score": 0.4}, "b": {"score": 0.01}})
    assert doc["conflicts"][0]["resolution"] == "flag"


def test_support_relation_conflict_uses_scores(settings):
    a = claim("a", None, 1.0, predicate="FRIEND_OF", kind="relation", object="lawrence")
    b = claim("b", None, 0.6, predicate="ENEMY_OF", kind="relation", object="lawrence")
    intervals, _, doc = CO.build_graph([a, b], settings, None, support_scores={"a": {"score": 0.1}, "b": {"score": 0.95}})
    assert intervals[0]["predicate"] == "ENEMY_OF"
    assert doc["conflicts"][0]["arbiter"] == "nli:higher_support"


def test_support_future_reverse_relation_cannot_drop_earlier_direction(settings):
    a = claim("a", None, 0.6, predicate="SAVED", kind="relation", object="lawrence")
    b = claim("b", None, 1.0, vol=2, predicate="SAVED", kind="relation", subject="lawrence", object="zheren")
    scores = {"a": {"score": 0.7}, "b": {"score": 0.99}}
    before, _, _ = CO.build_graph([a], settings, None, support_scores=scores)
    after, _, _ = CO.build_graph([a, b], settings, None, support_scores=scores)
    assert [i for i in after if i["vol_start"] == 1] == before


def test_support_verdict_score_persists_and_legacy_write_clears_it(tmp_path):
    conn = store.connect(tmp_path / "graph.db")
    row = {"target_id": "i_a", "verdict": "unsupported", "support_score": 0.2,
           "support_threshold": 0.5, "context_sha256": "hash", "evidence_cutoff": 1, "model_revision": "revision"}
    store.write_verdicts(conn, [row])
    result = store.read_verdicts(conn)["i_a"]
    for key in row.keys() - {"target_id"}:
        assert result[key] == row[key]
    store.write_verdicts(conn, [{"target_id": "i_a", "verdict": "supported"}])
    assert "support_score" not in store.read_verdicts(conn)["i_a"]
    conn.close()


def test_support_client_uses_cache_and_logs_every_call(tmp_path, monkeypatch, settings):
    calls = []
    def complete(*args, **kwargs):
        calls.append(args)
        return Completion(json.dumps({"score": 0.9, "chunks": [{"score": 0.9, "document_index": 0, "text": "evidence"}]}), 5, 1)
    monkeypatch.setattr(minicheck, "complete", complete)
    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "runs")
    run = provenance.start_run("spice-and-wolf", "nli_test", scope="v1", stage_keys=[])
    client = LLMClient(settings, cache=LLMCache(tmp_path / "cache"), run=run)
    first = client.score_support(["evidence"], "claim")
    assert client.score_support(["evidence"], "claim") == first
    assert len(calls) == 1
    logs = [json.loads(line) for line in run.calls_path.read_text(encoding="utf-8").splitlines()]
    assert [row["cache_hit"] for row in logs] == [False, True]
    client.score_support(["new evidence"], "claim")
    assert len(calls) == 2


def test_support_client_refuses_chat_provider(settings):
    settings.model_overrides["support"] = "local_fast"
    with pytest.raises(LLMError, match="classifier"):
        LLMClient(settings).score_support(["evidence"], "claim")


@pytest.mark.parametrize("response", [
    {"score": 0.9, "chunks": []}, {"score": 0.9, "chunks": [{"score": 0.2}]},
    {"score": float("nan"), "chunks": [{"score": 0.2}]},
])
def test_support_client_rejects_invalid_classifier_response(tmp_path, monkeypatch, settings, response):
    monkeypatch.setattr(minicheck, "complete", lambda *a, **k: Completion(json.dumps(response), 1, 1))
    with pytest.raises(LLMError, match="Invalid"):
        LLMClient(settings, cache=LLMCache(tmp_path)).score_support(["evidence"], "claim")


def test_classifier_chunking_preserves_evidence_and_hypothesis():
    tokenizer = SimpleNamespace(eos_token=" </s> ")
    class Tokenizer:
        eos_token = tokenizer.eos_token
        def __call__(self, text, **kwargs):
            assert kwargs["truncation"] is False
            return {"input_ids": list(range(len(text.split())))}
    chunks = list(minicheck._chunks("one two three four five six seven eight", "claim words", Tokenizer(), 8))
    assert " ".join(chunk for chunk, _ in chunks) == "one two three four five six seven eight"
    assert all(text.endswith("claim words") for _, text in chunks)
    with pytest.raises(ProviderError, match="without truncating"):
        list(minicheck._chunks("one", "a very long untruncatable claim", Tokenizer(), 3))
