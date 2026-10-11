"""Tests for graph/support.py — NLI evidence-support scoring (TASK-0005).

All tests use a fake client and fake EvidenceContext; no MiniCheck model is loaded.
These tests cover hypothesis(), evidence_documents(), score_claims(),
arbitration_claims(), and verify_intervals().
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from narrativewiki.graph import store as ST
from narrativewiki.graph import support as SU
from narrativewiki.graph import temporal as TE


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


class FakeSettings:
    """Minimal settings for support module tests."""

    attributes = {
        "OCCUPATION": {"single": True, "display": "occupation"},
        "AGE": {"single": True, "display": "age", "format": "number_or_range"},
        "TITLE": {"single": False, "display": "title"},
        "RANK": {"single": True, "display": "rank"},
    }
    relations = {
        "FRIEND_OF": {"symmetric": True},
        "PARENT_OF": {"inverse": "CHILD_OF"},
        "AFFILIATED_WITH": {},
    }
    conflicts_config = {"escalate_when_confidence_within": 0.10}
    extraction_behaviour = {
        "support": {
            "threshold": 0.5,
            "templates": {
                "OCCUPATION": "{subject} works as a {value}.",
                "PARENT_OF": "{subject} is a parent of {object}.",
                "AFFILIATED_WITH": "{subject} is a member or willing associate of {object}.",
            },
        }
    }


_SETTINGS = FakeSettings()


def _entity(entity_id, canonical):
    return {"entity_id": entity_id, "canonical": canonical, "type": "CHARACTER"}


_ENTITIES = {
    "holo": _entity("holo", "Holo"),
    "lawrence": _entity("lawrence", "Lawrence"),
    "zheren": _entity("zheren", "Zheren"),
}


def _claim(claim_id, subject, predicate, kind, first_vol, confidence, *,
           object=None, value=None, quote="The merchant traveled to town.", polarity="asserted"):
    return {
        "claim_id": claim_id,
        "subject": subject,
        "predicate": predicate,
        "kind": kind,
        "object": object,
        "value": value,
        "qualifier": None,
        "first_vol": first_vol,
        "confidence": confidence,
        "evidence": [{"para_id": f"v{first_vol:02d}:c01:p0001", "quote": quote}],
        "polarity": polarity,
        "source": "test",
    }


class FakeEvidenceContext:
    """Returns a paragraph containing the expected quote for any para_id."""

    def __init__(self, upto_vol: int = 2, extra_text: str = "") -> None:
        self.upto_vol = upto_vol
        self.extra_text = extra_text

    def for_facts(self, facts):
        result = {}
        for fact in facts:
            for ev in fact.get("evidence", []):
                pid = ev.get("para_id", "")
                result[pid] = [{"para_id": pid, "text": ev["quote"] + self.extra_text}]
        return result


class FakeSupportClient:
    """Fake score_support: returns the score from a pre-loaded mapping."""

    def __init__(self, scores: dict[str, float] | None = None, default: float = 0.8):
        self._scores = scores or {}
        self._default = default
        self.calls: list[tuple] = []

    def score_support(self, documents, claim, stage="support"):
        self.calls.append((documents, claim))
        score = self._scores.get(claim, self._default)
        return {
            "score": score,
            "chunks": [{"document_index": 0, "text": documents[0][:50], "score": score}],
            "model": "minicheck_ft5",
            "revision": "abc123",
        }


# ---------------------------------------------------------------------------
# hypothesis()
# ---------------------------------------------------------------------------


def test_hypothesis_attribute_uses_template_when_present():
    c = _claim("c1", "zheren", "OCCUPATION", "attribute", 1, 0.72, value="traveling merchant")
    text = SU.hypothesis(c, _ENTITIES, _SETTINGS)
    assert text == "Zheren works as a traveling merchant."


def test_hypothesis_attribute_falls_back_to_display_name_for_missing_template():
    # RANK has no template in FakeSettings; falls back to "{subject}'s rank is {value}."
    c = _claim("c1", "zheren", "RANK", "attribute", 1, 0.9, value="journeyman")
    text = SU.hypothesis(c, _ENTITIES, _SETTINGS)
    assert "Zheren" in text
    assert "rank" in text.lower()
    assert "journeyman" in text


def test_hypothesis_relation_uses_explicit_template():
    c = _claim("c1", "holo", "PARENT_OF", "relation", 1, 0.9, object="zheren")
    text = SU.hypothesis(c, _ENTITIES, _SETTINGS)
    assert text == "Holo is a parent of Zheren."


def test_hypothesis_relation_without_template_raises():
    settings_no_template = FakeSettings()
    settings_no_template.extraction_behaviour = {"support": {"threshold": 0.5, "templates": {}}}
    c = _claim("c1", "holo", "FRIEND_OF", "relation", 1, 0.9, object="lawrence")
    with pytest.raises(ValueError, match="No support hypothesis template for relation FRIEND_OF"):
        SU.hypothesis(c, _ENTITIES, settings_no_template)


def test_hypothesis_polarity_denied_prefixes():
    c = _claim("c1", "zheren", "OCCUPATION", "attribute", 1, 0.72, value="traveling merchant",
               polarity="denied")
    text = SU.hypothesis(c, _ENTITIES, _SETTINGS)
    assert text.startswith("It is not true that ")
    assert "Zheren works as a traveling merchant." in text


def test_hypothesis_polarity_presumed_prefixes():
    c = _claim("c1", "zheren", "OCCUPATION", "attribute", 1, 0.72, value="traveling merchant",
               polarity="presumed")
    text = SU.hypothesis(c, _ENTITIES, _SETTINGS)
    assert text.startswith("It is believed that ")


def test_hypothesis_unknown_polarity_raises():
    c = _claim("c1", "zheren", "OCCUPATION", "attribute", 1, 0.72, value="traveling merchant",
               polarity="maybe")
    with pytest.raises(ValueError, match="Unknown claim polarity"):
        SU.hypothesis(c, _ENTITIES, _SETTINGS)


# ---------------------------------------------------------------------------
# evidence_documents()
# ---------------------------------------------------------------------------


def test_evidence_documents_filters_future_volume():
    """Evidence in vol 3 at a cutoff-2 claim must be excluded."""
    c = {
        "claim_id": "c1",
        "first_vol": 1,
        "evidence": [
            {"para_id": "v01:c01:p0001", "quote": "He is a merchant."},
            {"para_id": "v03:c01:p0001", "quote": "Later, a merchant still."},  # future
        ],
    }
    ctx = FakeEvidenceContext(upto_vol=2)
    docs = SU.evidence_documents(c, ctx)
    assert len(docs) == 1
    assert "He is a merchant." in docs[0]


def test_evidence_documents_all_future_raises():
    """If all evidence is beyond the cutoff, raise ValueError."""
    c = {
        "claim_id": "c1",
        "first_vol": 1,
        "evidence": [{"para_id": "v05:c01:p0001", "quote": "Seen in vol 5."}],
    }
    ctx = FakeEvidenceContext(upto_vol=2)
    with pytest.raises(ValueError, match="No cutoff-safe evidence"):
        SU.evidence_documents(c, ctx)


def test_evidence_documents_deduplicates_same_context_window():
    """Two evidence items whose context paragraphs collapse to the same document string."""
    c = {
        "claim_id": "c1",
        "first_vol": 1,
        "evidence": [
            {"para_id": "v01:c01:p0001", "quote": "Evidence A."},
            {"para_id": "v01:c01:p0002", "quote": "Evidence B."},
        ],
    }
    # Context returns a single-paragraph window; both paragraphs -> same document string -> dedup.
    class SingleParaContext:
        def for_facts(self, facts):
            return {
                "v01:c01:p0001": [{"para_id": "v01:c01:p0001", "text": "Evidence A."}],
                "v01:c01:p0002": [{"para_id": "v01:c01:p0002", "text": "Evidence B."}],
            }

    docs = SU.evidence_documents(c, SingleParaContext())
    # Two distinct document strings (p0001 window != p0002 window), not deduplicated here.
    assert len(docs) == 2


# ---------------------------------------------------------------------------
# arbitration_claims()
# ---------------------------------------------------------------------------


def test_arbitration_claims_includes_relations():
    c_rel = _claim("c_rel", "holo", "FRIEND_OF", "relation", 1, 0.9, object="lawrence")
    c_att = _claim("c_att", "holo", "OCCUPATION", "attribute", 1, 0.8, value="deity")
    c_trait = _claim("c_trait", "holo", "TITLE", "attribute", 1, 0.7, value="Wisewolf")
    result = SU.arbitration_claims([c_rel, c_att, c_trait], _SETTINGS)
    # FRIEND_OF (relation) and OCCUPATION (single attribute) are in scope; TITLE (non-single) is not.
    ids = [c["claim_id"] for c in result]
    assert "c_rel" in ids
    assert "c_att" in ids
    assert "c_trait" not in ids


def test_arbitration_claims_excludes_non_single_attributes():
    c_title = _claim("c_t", "holo", "TITLE", "attribute", 1, 0.8, value="Wisewolf")
    result = SU.arbitration_claims([c_title], _SETTINGS)
    assert result == []


# ---------------------------------------------------------------------------
# score_claims()
# ---------------------------------------------------------------------------


def test_score_claims_returns_auditable_dict_shape(monkeypatch):
    c = _claim("c_occ", "zheren", "OCCUPATION", "attribute", 1, 0.72, value="traveling merchant",
               quote="Zheren was a traveling merchant.")
    client = FakeSupportClient(default=0.82)

    # Patch EvidenceContext where score_claims uses it (imported into the support module).
    import narrativewiki.graph.support as _sup

    class FixedContext:
        def for_facts(self, facts):
            return FakeEvidenceContext(upto_vol=1).for_facts(facts)

    monkeypatch.setattr(_sup, "EvidenceContext", lambda upto: FixedContext())

    result = _sup.score_claims([c], _ENTITIES, _SETTINGS, client)

    assert "c_occ" in result
    row = result["c_occ"]
    assert row["claim_id"] == "c_occ"
    assert row["hypothesis"] == "Zheren works as a traveling merchant."
    assert 0.0 <= row["score"] <= 1.0
    assert row["evidence_cutoff"] == 1
    assert row["extracted_confidence"] == 0.72
    assert "context_sha256" in row
    assert len(row["context_sha256"]) == 64



# ---------------------------------------------------------------------------
# verify_intervals()
# ---------------------------------------------------------------------------


def _build_test_db():
    """Minimal in-memory db with one OCCUPATION interval (single attr) for Zheren."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)  # creates tables; ST.reset() only deletes rows
    ST.reset(conn)
    # Write one entity (all required columns)
    conn.execute(
        "INSERT INTO entities (entity_id, canonical, type, first_vol, importance, aliases_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("zheren", "Zheren", "CHARACTER", 1, 0.5, "[]"),
    )
    # Write one claim (all required columns including kind)
    claim = _claim("c_occ", "zheren", "OCCUPATION", "attribute", 1, 0.72, value="traveling merchant",
                   quote="Zheren was a traveling merchant.")
    evidence_json = json.dumps(claim["evidence"])
    conn.execute(
        "INSERT INTO claims (claim_id, subject, predicate, kind, object, value, qualifier, "
        "first_vol, confidence, polarity, evidence_json, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (claim["claim_id"], claim["subject"], claim["predicate"], claim["kind"], claim["object"],
         claim["value"], claim["qualifier"], claim["first_vol"], claim["confidence"],
         claim["polarity"], evidence_json, claim["source"]),
    )
    # Write one interval
    interval_id = TE.make_interval_id("zheren", "OCCUPATION", "traveling merchant", 1)
    conn.execute(
        "INSERT INTO intervals (interval_id, subject, predicate, object, value, qualifier, "
        "vol_start, vol_end, claim_ids_json, superseded_by, confidence, evidence_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (interval_id, "zheren", "OCCUPATION", None, "traveling merchant", None,
         1, None, json.dumps(["c_occ"]), None, 0.72, 1),
    )
    conn.commit()
    return conn, interval_id




def test_verify_intervals_supported_verdict(monkeypatch):
    """An interval with score > threshold → 'supported', no character in flagged results."""
    import narrativewiki.graph.support as _sup

    conn, interval_id = _build_test_db()
    characters = [{"entity_id": "zheren", "canonical": "Zheren"}]
    entities = {"zheren": {"entity_id": "zheren", "canonical": "Zheren"}}

    class AlwaysSupported(FakeSupportClient):
        def score_support(self, documents, claim, stage="support"):
            return {"score": 0.9, "chunks": [{"document_index": 0, "text": "...", "score": 0.9}],
                    "model": "minicheck_ft5", "revision": "abc"}

    monkeypatch.setattr(_sup, "EvidenceContext",
                        lambda upto: FakeEvidenceContext(upto_vol=upto))

    client = AlwaysSupported()
    doc, verdicts = _sup.verify_intervals(conn, characters, entities, 2, _SETTINGS, client, "run1")
    conn.close()

    assert doc["summary"]["facts_checked"] == 1
    assert doc["summary"]["facts_flagged"] == 0
    assert doc["results"] == []
    assert len(verdicts) == 1
    assert verdicts[0]["verdict"] == "supported"


def test_verify_intervals_unsupported_verdict(monkeypatch):
    """An interval with score <= threshold → 'unsupported', character appears in results."""
    import narrativewiki.graph.support as _sup

    conn, interval_id = _build_test_db()
    characters = [{"entity_id": "zheren", "canonical": "Zheren"}]
    entities = {"zheren": {"entity_id": "zheren", "canonical": "Zheren"}}

    class AlwaysUnsupported(FakeSupportClient):
        def score_support(self, documents, claim, stage="support"):
            return {"score": 0.2, "chunks": [{"document_index": 0, "text": "...", "score": 0.2}],
                    "model": "minicheck_ft5", "revision": "abc"}

    monkeypatch.setattr(_sup, "EvidenceContext",
                        lambda upto: FakeEvidenceContext(upto_vol=upto))

    client = AlwaysUnsupported()
    doc, verdicts = _sup.verify_intervals(conn, characters, entities, 2, _SETTINGS, client, "run1")
    conn.close()

    assert doc["summary"]["facts_flagged"] == 1
    assert len(doc["results"]) == 1
    assert doc["results"][0]["entity_id"] == "zheren"
    assert verdicts[0]["verdict"] == "unsupported"


def test_verify_intervals_no_intervals_returns_empty(monkeypatch):
    """No intervals for a character → empty verdicts, no division-by-zero."""
    import narrativewiki.graph.support as _sup

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ST.SCHEMA)
    ST.reset(conn)
    conn.execute(
        "INSERT INTO entities (entity_id, canonical, type, first_vol, importance, aliases_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("zheren", "Zheren", "CHARACTER", 1, 0.5, "[]"),
    )
    conn.commit()

    monkeypatch.setattr(_sup, "EvidenceContext",
                        lambda upto: FakeEvidenceContext(upto_vol=upto))

    characters = [{"entity_id": "zheren", "canonical": "Zheren"}]
    entities = {"zheren": {"entity_id": "zheren", "canonical": "Zheren"}}
    client = FakeSupportClient()

    doc, verdicts = _sup.verify_intervals(conn, characters, entities, 2, _SETTINGS, client, "run1")
    conn.close()

    assert doc["summary"]["facts_checked"] == 0
    assert doc["summary"]["facts_flagged"] == 0
    assert verdicts == []
    assert doc["results"] == []
