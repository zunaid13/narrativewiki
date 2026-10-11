"""Tests for graph/verify.py — Phase 22 C3's per-character verification pass."""

from __future__ import annotations

import json

import pytest

from narrativewiki import paths
from narrativewiki.graph import verify as VE


def _fact(predicate="AFFILIATED_WITH", value="Lawrence -> Medio", qualifier=None, quotes=("Medio's men seized him.",)):
    return {
        "kind": "relation", "predicate": predicate, "value": value, "qualifier": qualifier,
        "evidence": [{"quote": q, "para_id": "v02:c04:p0031"} for q in quotes],
    }


class _FakeVerifyClient:
    def __init__(self, response):
        self.response = response
        self.calls: list[tuple] = []

    def complete_json(self, stage, prompt, schema, system=None):
        self.calls.append((stage, prompt, system))
        return schema.model_validate(self.response)


def test_format_fact_includes_predicate_value_qualifier_and_quotes():
    fact = _fact(qualifier="captive", quotes=("Medio's men seized him.", "He was dragged away."))
    line = VE._format_fact(fact)
    assert line.startswith("AFFILIATED_WITH (captive)")
    assert '"Lawrence -> Medio"' in line
    assert '"Medio\'s men seized him."' in line
    assert '"He was dragged away."' in line


def test_format_fact_with_no_evidence_says_so():
    assert "(no quoted evidence)" in VE._format_fact(_fact(quotes=()))


def test_verify_facts_returns_empty_with_no_facts_and_makes_no_call():
    client = _FakeVerifyClient({"supported": True})
    assert VE.verify_facts("Kraft Lawrence", [], client) == []
    assert client.calls == []


def test_verify_facts_returns_empty_with_no_client_and_makes_no_call():
    # client is None entirely, not just a fake with no response -- nothing to call.
    assert VE.verify_facts("Kraft Lawrence", [_fact()], None) == []


def test_verify_fact_can_only_flag_the_fact_it_was_asked_about():
    """[30] The per-fact call exists because the per-character one flagged by list index, so a
    judgement could land on a fact it was never about: `norah-arendt COMMANDS enek` was withheld on
    a rationale arguing about Liebert (MEASUREMENTS section 28). One fact per prompt leaves no index
    to get wrong -- the flagged fact IS the fact asked about."""
    unsupported = _fact()
    client = _FakeVerifyClient({
        "supported": False,
        "rationale": "Evidence shows Medio captured him, not that he joined.",
    })
    flagged = VE.verify_facts("Kraft Lawrence", [unsupported], client)
    assert len(flagged) == 1
    assert flagged[0]["predicate"] == "AFFILIATED_WITH"
    assert flagged[0]["rationale"] == "Evidence shows Medio captured him, not that he joined."
    assert client.calls[0][0] == VE.STAGE
    # One fact per prompt, so no other fact can be implicated by this call.
    assert "AGE" not in client.calls[0][1]

    ok = _fact(predicate="AGE", value="25", quotes=("He was twenty-five.",))
    assert VE.verify_fact("Kraft Lawrence", ok, _FakeVerifyClient({"supported": True})) is None


def test_verify_facts_keeps_input_order_and_drops_the_supported_ones():
    facts = [_fact(predicate="AGE", value="25"), _fact(), _fact(predicate="ORIGIN", value="north")]

    class _PerFact:
        def __init__(self):
            self.calls = []

        def complete_json(self, stage, prompt, schema, system=None):
            self.calls.append(prompt)
            bad = "AFFILIATED_WITH" in prompt or "ORIGIN" in prompt
            return schema.model_validate({"supported": not bad, "rationale": "no" if bad else ""})

    client = _PerFact()
    flagged = VE.verify_facts("Holo", facts, client, workers=1)
    assert len(client.calls) == 3                       # one call per fact, not one per character
    assert [f["predicate"] for f in flagged] == ["AFFILIATED_WITH", "ORIGIN"]
    assert flagged[0]["rationale"] == "no"


def test_unreadable_verdict_never_passes_a_fact_silently():
    """The lesson carried over from the schema this replaced: that one defaulted `flags` to empty,
    so a wrong-shaped answer read as "nothing flagged" and 49 real flags vanished with nothing
    raised. A verification pass that fails OPEN is worse than one that crashes, so `supported` has
    no default and an unreadable answer raises instead of quietly approving the fact."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        VE.FactVerdict.model_validate({"rationale": "the evidence does not support this"})
    with pytest.raises(pydantic.ValidationError):
        VE.FactVerdict.model_validate({"supported": "probably not"})


@pytest.mark.parametrize(
    "raw,expected",
    [
        ({"supported": False}, False),
        ({"supported": "no"}, False),
        ({"supported": "unsupported"}, False),
        ({"verdict": "unsupported"}, False),
        ({"verdict": "supported"}, True),
        ({"supported": "yes"}, True),
        (True, True),
        ({"supported": False, "reason": "wrong company"}, False),
    ],
)
def test_verdict_shapes_models_actually_return(raw, expected):
    verdict = VE.FactVerdict.model_validate(raw)
    assert verdict.supported is expected
    if isinstance(raw, dict) and raw.get("reason"):
        assert verdict.rationale == "wrong company"


def test_overlong_rationale_is_truncated_not_rejected():
    """A model that explains itself at length has still answered; rejecting it would turn a usable
    judgement into a crash."""
    assert len(VE.FactVerdict.model_validate({"supported": False, "rationale": "x" * 900}).rationale) == 300


def _write_context(tmp_path, monkeypatch, vol, rows):
    monkeypatch.setattr(paths, "PARSED_DIR", tmp_path)
    paths.parsed_volume(vol).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _context_fact(para_id):
    fact = _fact()
    fact["evidence"][0]["para_id"] = para_id
    return fact


def test_context_is_bounded_by_radius_chapter_and_volume(tmp_path, monkeypatch):
    rows = [{"para_id": f"v01:c01:p{i:04d}", "vol": 1, "text": f"text-{i}"} for i in range(6)]
    rows.insert(0, {"para_id": "v01:c00:p0000", "vol": 1, "text": "previous chapter"})
    rows.append({"para_id": "v01:c02:p0000", "vol": 1, "text": "next chapter"})
    rows.insert(3, {"para_id": "v02:c01:p0001", "vol": 2, "text": "future spoiler"})
    _write_context(tmp_path, monkeypatch, 1, rows)
    paths.parsed_volume(2).write_text("invalid JSON must not be read", encoding="utf-8")
    resolver = VE.EvidenceContext(1, radius=1)
    result = resolver.for_facts([_context_fact("v01:c01:p0000"), _context_fact("v02:c01:p0001")])
    assert list(result) == ["v01:c01:p0000"]
    assert [p["text"] for p in result["v01:c01:p0000"]] == ["text-0", "text-1"]
    assert 2 not in resolver._volumes


def test_context_supplies_banter_before_quote_and_deduplicates_overlaps(tmp_path, monkeypatch):
    rows = [{"para_id": f"v02:c02:p{i:04d}", "vol": 2, "text": f"paragraph {i}"} for i in range(7)]
    rows[1]["text"] = "Everyone in the guild is my son or daughter."
    rows[4]["text"] = "Then I am your son."
    _write_context(tmp_path, monkeypatch, 2, rows)
    facts = [_context_fact("v02:c02:p0004"), _context_fact("v02:c02:p0005")]
    contexts = VE.EvidenceContext(2).for_facts(facts)
    client = _FakeVerifyClient({"supported": False, "rationale": "Figurative guild kinship."})
    flagged = VE.verify_facts("Lawrence", facts[:1], client, context=contexts)
    prompt = client.calls[0][1]
    assert prompt.count(rows[1]["text"]) == 1
    assert "interpretation only" in prompt
    assert "Figurative guild kinship." == flagged[0]["rationale"]
    assert "context" not in flagged[0]  # does not become part of persisted evidence


def test_context_cache_is_per_run_and_missing_legacy_paragraph_is_allowed(tmp_path, monkeypatch):
    _write_context(tmp_path, monkeypatch, 1, [{"para_id": "v01:c01:p0000", "vol": 1, "text": "original"}])
    fact = _context_fact("v01:c01:p0000")
    resolver = VE.EvidenceContext(1)
    assert resolver.for_facts([fact])["v01:c01:p0000"][0]["text"] == "original"
    paths.parsed_volume(1).write_text("bad JSON", encoding="utf-8")
    assert resolver.for_facts([fact])["v01:c01:p0000"][0]["text"] == "original"
    with pytest.raises(ValueError):
        VE.EvidenceContext(1).for_facts([fact])
    assert VE.EvidenceContext(2).for_facts([_context_fact("v02:c01:p0000")]) == {}
    assert resolver.for_facts([_context_fact("v01:c01:p9999")]) == {}


@pytest.mark.parametrize("fact_moved", [False, True])
def test_verify_keeps_a_verdict_whose_fact_has_not_moved(tmp_path, monkeypatch, fact_moved):
    """[30] `graph build` used to wipe `verdicts`, so a rebuild re-asked the model about every
    character and re-rolled judgements on facts nothing had touched -- 12 reader-visible gates
    flipped after a rebuild that changed one relation, taking the wiki from 34 relation rows to 23
    (MEASUREMENTS §28). A verdict now survives, and is kept when `fact_context_sha256` still
    matches. When the fact HAS moved, the stale verdict must not be honoured."""
    import typer  # noqa: F401
    from narrativewiki import cli
    from narrativewiki.config import Settings
    from narrativewiki.graph import store, verify as verify_mod
    from narrativewiki.llm import client as client_mod
    from narrativewiki.synth import assemble

    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    paths.set_active_series("spice-and-wolf")
    try:
        paths.ensure_dirs()
        paths.graph_db().write_bytes(b"fixture")
        paths.gazetteer().write_text(json.dumps({"entities": [
            {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER"},
        ]}), encoding="utf-8")
        paths.parsed_volume(1).write_text(json.dumps({
            "para_id": "v01:c01:p0000", "vol": 1, "text": "The guild kinship was figurative."
        }), encoding="utf-8")
        settings = Settings(series_id="spice-and-wolf", series={}, models={}, extraction={})
        monkeypatch.setattr(settings, "resolve_role", lambda stage: "fixture")
        monkeypatch.setattr(cli, "_settings", lambda *args: settings)
        fake_client = _FakeVerifyClient({"supported": True})
        monkeypatch.setattr(client_mod, "LLMClient", lambda *args, **kwargs: fake_client)

        fact = {**_context_fact("v01:c01:p0000"), "interval_id": "i_fixture"}
        monkeypatch.setattr(assemble, "fact_set_for_verification", lambda *args: [fact])
        from types import SimpleNamespace
        monkeypatch.setattr(store, "connect", lambda: SimpleNamespace(close=lambda: None))
        persisted = []
        monkeypatch.setattr(store, "write_verdicts", lambda conn, rows: persisted.extend(rows))

        judged = dict(fact) if not fact_moved else {**fact, "qualifier": "something else"}
        monkeypatch.setattr(store, "read_verdicts", lambda conn: {"i_fixture": {
            "verdict": "unsupported", "rationale": "Figurative kinship.", "model": "fixture",
            "run_id": "run_0", "context_sha256": verify_mod.fact_context_sha256(judged),
            "evidence_cutoff": 1, "model_revision": verify_mod.METHOD_REVISION,
        }})
        cli.verify(series="spice-and-wolf", upto=1)

        summary = json.loads(paths.verification().read_text(encoding="utf-8"))["summary"]
        if fact_moved:
            assert fake_client.calls, "a fact that changed must be re-verified"
            assert summary["facts_reused"] == 0
            assert persisted[0]["verdict"] == "supported"        # the fresh call flags nothing
        else:
            assert fake_client.calls == [], "an unchanged fact must not be re-asked"
            assert summary["facts_reused"] == 1
            assert persisted[0]["verdict"] == "unsupported"       # the earlier judgement is kept
            assert persisted[0]["rationale"] == "Figurative kinship."
            # A carried-over flag still has to reach verification.json, or reuse would quietly
            # shrink what `wiki audit verify` reports as wrong.
            assert summary["facts_flagged"] == 1
            assert summary["characters_flagged"] == 1
    finally:
        paths.set_active_series(None)


def test_a_verdict_from_a_superseded_method_is_not_reused(tmp_path, monkeypatch):
    """[30] `fact_context_sha256` fingerprints the FACT, so it cannot notice that the verification
    method changed. The facts were untouched when this pass went from one batched call per character
    to one call per fact, so without `METHOD_REVISION` every judgement made by the replaced method
    would have been carried straight over it."""
    from narrativewiki import cli
    from narrativewiki.config import Settings
    from narrativewiki.graph import store, verify as verify_mod
    from narrativewiki.llm import client as client_mod
    from narrativewiki.synth import assemble

    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    paths.set_active_series("spice-and-wolf")
    try:
        paths.ensure_dirs()
        paths.graph_db().write_bytes(b"fixture")
        paths.gazetteer().write_text(json.dumps({"entities": [
            {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER"},
        ]}), encoding="utf-8")
        paths.parsed_volume(1).write_text(json.dumps({
            "para_id": "v01:c01:p0000", "vol": 1, "text": "The guild kinship was figurative."
        }), encoding="utf-8")
        settings = Settings(series_id="spice-and-wolf", series={}, models={}, extraction={})
        monkeypatch.setattr(settings, "resolve_role", lambda stage: "fixture")
        monkeypatch.setattr(cli, "_settings", lambda *args: settings)
        fake_client = _FakeVerifyClient({"supported": True})
        monkeypatch.setattr(client_mod, "LLMClient", lambda *args, **kwargs: fake_client)
        fact = {**_context_fact("v01:c01:p0000"), "interval_id": "i_fixture"}
        monkeypatch.setattr(assemble, "fact_set_for_verification", lambda *args: [fact])
        from types import SimpleNamespace
        monkeypatch.setattr(store, "connect", lambda: SimpleNamespace(close=lambda: None))
        persisted = []
        monkeypatch.setattr(store, "write_verdicts", lambda conn, rows: persisted.extend(rows))
        monkeypatch.setattr(store, "read_verdicts", lambda conn: {"i_fixture": {
            "verdict": "unsupported", "rationale": "Judged by the old batched call.",
            "model": "fixture", "run_id": "run_0",
            "context_sha256": verify_mod.fact_context_sha256(fact),   # the fact itself is unchanged
            "evidence_cutoff": 1, "model_revision": "some-older-method",
        }})
        cli.verify(series="spice-and-wolf", upto=1)

        assert fake_client.calls, "a superseded method's verdict must be re-judged"
        assert persisted[0]["verdict"] == "supported"
        assert persisted[0]["model_revision"] == verify_mod.METHOD_REVISION
    finally:
        paths.set_active_series(None)


@pytest.mark.parametrize("corrupt_context", [False, True])
def test_verify_cli_passes_context_and_never_persists_verdicts_on_context_failure(
    tmp_path, monkeypatch, corrupt_context
):
    import typer
    from narrativewiki import cli, provenance
    from narrativewiki.config import Settings
    from narrativewiki.graph import store
    from narrativewiki.llm import client as client_mod
    from narrativewiki.synth import assemble

    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    paths.set_active_series("spice-and-wolf")
    try:
        paths.ensure_dirs()
        paths.graph_db().write_bytes(b"fixture")
        paths.gazetteer().write_text(json.dumps({"entities": [
            {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER"},
            {"entity_id": "lawrence", "canonical": "Lawrence", "type": "CHARACTER"},
        ]}), encoding="utf-8")
        paths.parsed_volume(1).write_text(
            "bad JSON" if corrupt_context else json.dumps({
                "para_id": "v01:c01:p0000", "vol": 1, "text": "The guild kinship was figurative."
            }), encoding="utf-8"
        )
        settings = Settings(series_id="spice-and-wolf", series={}, models={}, extraction={})
        monkeypatch.setattr(settings, "resolve_role", lambda stage: "fixture")
        monkeypatch.setattr(cli, "_settings", lambda *args: settings)
        fake_client = _FakeVerifyClient({"supported": False, "rationale": "Figurative kinship."})
        monkeypatch.setattr(client_mod, "LLMClient", lambda *args, **kwargs: fake_client)
        fact = {**_context_fact("v01:c01:p0000"), "interval_id": "i_fixture"}
        monkeypatch.setattr(assemble, "fact_set_for_verification", lambda *args: [fact])
        closed = []
        from types import SimpleNamespace
        monkeypatch.setattr(store, "connect", lambda: SimpleNamespace(close=lambda: closed.append(True)))
        persisted = []
        monkeypatch.setattr(store, "write_verdicts", lambda conn, rows: persisted.extend(rows))
        # [30] verify now reads the stored verdicts first, to keep the ones whose fact has not
        # moved. Nothing is stored here, so every character is verified as before.
        monkeypatch.setattr(store, "read_verdicts", lambda conn: {})
        if corrupt_context:
            with pytest.raises(typer.Exit):
                cli.verify(series="spice-and-wolf", upto=1)
            assert persisted == []
            assert fake_client.calls == []
            assert provenance.list_runs()[0]["outcome"] == "failed"
        else:
            cli.verify(series="spice-and-wolf", upto=1)
            assert "The guild kinship was figurative." in fake_client.calls[0][1]
            assert persisted[0]["verdict"] == "unsupported"
            assert len(persisted) == 1
            summary = json.loads(paths.verification().read_text(encoding="utf-8"))["summary"]
            assert summary == {"characters_checked": 2, "facts_reused": 0,
                               "characters_flagged": 2, "facts_checked": 1, "facts_flagged": 1}
            assert provenance.list_runs()[0]["outcome"] == "ok"
        assert closed == [True]
    finally:
        paths.set_active_series(None)


# --- 2026-09-23: the shape models actually answer in ------------------------


def test_verify_prompt_states_the_json_shape_it_wants():
    """The prompt used to ask in prose to "list the index of every fact", and models answered with
    a bare JSON array -- obeying the words, failing the schema. It now asks one yes/no question and
    shows the exact object it wants back."""
    prompt = VE._user_prompt("Holo", {"predicate": "AGE", "value": "25",
                                      "evidence": [{"para_id": "v01:c00:p1", "quote": "q"}]})
    assert '"supported"' in prompt
    assert "fact_index" not in prompt and '"flags"' not in prompt
    assert "Character: Holo" in prompt


def test_a_relation_is_judged_with_its_pairs_other_relations_and_nothing_wider():
    """[30] Per-fact verify released 16 relations, all relations (MEASUREMENTS section 30): judged
    alone, a relation no longer saw what else is asserted about the pair. Siblings restore that --
    the same pair's relations only, never another pair's, never an attribute."""
    spouse = {**_fact("SPOUSE_OF", "Holo -> Lawrence"), "pair": ["holo", "kraft-lawrence"]}
    travels = {**_fact("TRAVELS_WITH", "Lawrence -> Holo"), "pair": ["holo", "kraft-lawrence"]}
    other = {**_fact("ENEMY_OF", "Holo -> Enek"), "pair": ["enek", "holo"]}
    trait = _fact("PERSONALITY", "proud")
    facts = [spouse, travels, other, trait]
    VE.attach_pair_siblings(facts)

    assert spouse["pair_siblings"] == ['TRAVELS_WITH = "Lawrence -> Holo"']
    assert other["pair_siblings"] == []
    assert "pair_siblings" not in trait
    prompt = VE._user_prompt("Holo", spouse)
    assert 'TRAVELS_WITH = "Lawrence -> Holo"' in prompt and "ENEMY_OF" not in prompt
    # No siblings -> the prompt is byte-identical to before, so an unchanged fact is a cache hit.
    assert "Other relations" not in VE._user_prompt("Holo", other)

    # A sibling can move the verdict, so it must move the fingerprint.
    before = VE.fact_context_sha256(spouse)
    spouse["pair_siblings"] = ['ENEMY_OF = "Lawrence -> Holo"']
    assert VE.fact_context_sha256(spouse) != before


def test_the_verifier_is_told_the_names_visible_at_the_cutoff():
    """[30] Given only "Ainz Ooal Gown", the verifier withheld Momon's armour as being about
    someone else. Aliases revealed after the cutoff are not listed."""
    ainz = {"canonical": "Ainz Ooal Gown", "surface_forms": [
        {"text": "Ainz Ooal Gown", "first_vol": 1}, {"text": "Momonga", "first_vol": 1},
        {"text": "Momon", "first_vol": 2}]}
    assert VE.subject_label(ainz, 1) == "Ainz Ooal Gown (also called: Momonga)"
    assert VE.subject_label(ainz, 2) == "Ainz Ooal Gown (also called: Momonga, Momon)"
    assert VE.subject_label({"canonical": "Weiz", "surface_forms": []}, 2) == "Weiz"
