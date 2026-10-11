"""[33] S10: the baselines' shared output contract matches what the evaluation tools parse."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "baselines"))
import common as C  # noqa: E402


def test_enforce_drops_citations_the_system_was_not_shown_and_caps_prose():
    page = C.Page(age=C.Cited(text="13", evidence=["v01:c01:p0001", "v03:c01:p0001"]),
                  personality=C.Cited(text=" ".join(f"Sentence {i}." for i in range(9)), evidence=[]),
                  quotes=[C.Quote(text="Hi.", para_id="v09:c01:p0001")])
    out, st = C.enforce(page, {"v01:c01:p0001"})
    assert out.age.evidence == ["v01:c01:p0001"] and st["citations_dropped"] == 1
    assert len(C.sentences(out.personality.text)) == C.PROSE_CAPS["personality"] and st["sentences_cut"] == 3
    assert out.quotes == []


def test_rendered_citations_use_the_anchor_assertion_precision_parses():
    page = C.Page(age=C.Cited(text="13", evidence=["v01:c26:p0004"]),
                  relationships=[C.Relation(name="Anne Shirley", predicate="FRIEND_OF", note="bosom friend",
                                            evidence=["v01:c12:p0021"])])
    md = C.render(page, "Diana Barry", "diana-barry", 1, "B1")
    assert "- **Age:** 13  <sub>[v1 c26 P4](../source/v01-c26.md#nw-v01-c26-p0004)</sub>" in md
    assert re.search(r"<sub>\[[^\]]+\]\([^)]*#nw-v01-c12-p0021\)</sub>", md)
    assert md.startswith("---\nentity_id: diana-barry")


def test_chunks_stay_inside_a_chapter_and_keep_their_ids():
    paras = [{"para_id": f"v01:c01:p{i:04d}", "text": "w " * 100} for i in range(3)] + \
            [{"para_id": "v01:c02:p0000", "text": "w " * 10}]
    chunks = C.chunk(paras, max_words=250)
    assert [[p["para_id"] for p in c["paras"]] for c in chunks] == [
        ["v01:c01:p0000", "v01:c01:p0001"], ["v01:c01:p0002"], ["v01:c02:p0000"]]


def test_bm25_ranks_the_named_chunk_first():
    bm = C.BM25([C.tokenize("Diana laughed with Anne"), C.tokenize("the cow in the orchard")])
    s = bm.scores(C.tokenize("Diana"))
    assert s[0] > s[1] == 0


def test_a_character_the_prefix_never_names_gets_no_page():
    assert C.present("Diana Barry", None, "Diana Barry came over.", 1)
    assert C.present("Diana Barry", 1, "Diana came over.", 1)  # a gold fact by t puts them in the cast
    assert not C.present("Rilla Blythe", None, "Anne and Diana.", 1)
    # [33] 2026-09-29: one shared word ("Aunt", "Little") no longer puts a future character in the cast
    assert not C.present("Aunt Jamesina", 3, "Aunt Josephine came.", 1)
    assert not C.present("Little Jem", 4, "Little Anne.", 1)


def test_a_quote_without_an_id_is_dropped_not_a_failed_page():
    """[33] X1 (closed book) returned quotes with para_id null for Anne at t=4; the page failed
    validation three times. An id-less quote is now accepted and removed by the citation check."""
    page = C.Page.model_validate({"quotes": [{"text": "Hi.", "para_id": None}, {"text": "Yes.", "para_id": "v01:c01:p0001"}]})
    out, _ = C.enforce(page, {"v01:c01:p0001"})
    assert [q.text for q in out.quotes] == ["Yes."]


def test_null_fields_are_absent_not_a_failed_page():
    """[33] X1 returned `"rank": {"text": null}` for Gilbert at t=5 and the page failed three times."""
    page = C.Page.model_validate({"rank": {"text": None, "evidence": None}, "traits": None,
                                  "relationships": [{"name": None, "predicate": None}, {"name": "Anne Shirley", "predicate": "FRIEND_OF"}]})
    out, _ = C.enforce(page, set())
    assert out.rank is None and out.traits == [] and [r.name for r in out.relationships] == ["Anne Shirley"]
    assert "**Rank:**" not in C.render(out, "Gilbert Blythe", "gilbert-blythe", 5, "X1")


def test_a_chunk_without_a_vector_matches_nothing():
    """[33] bge-m3 returned no vector (NaN) for one Anne v4 chunk and B2 t=4 crashed in _cos."""
    assert C._cos(None, [1.0, 0.0]) == 0.0 and C._cos([1.0, 0.0], None) == 0.0


def test_the_closed_book_prompt_names_the_work():
    """[33] X1 got no title and wrote Leslie Moore (Anne's House of Dreams) as a cryptographer."""
    p = C.prompt("", "Leslie Moore", 4, "Anne of Green Gables series")
    assert "Anne of Green Gables series" in p and "volumes 1-4" in p
    # ...and a system WITH passages is not (B5's prompts never name the novel).
    with_passages = C.prompt("[v01:c01:p0000] x", "Anne", 1, "Anne of Green Gables series")
    assert with_passages.startswith("Passages from a novel series") and "Green Gables" not in with_passages


def test_x2_states_the_cutoff_it_must_not_pass():
    """[33] X2 got "as known after volume 5" at every t -- byte-identical to B1 t=5 (all 14 X2 t=1
    calls were cache hits). It must see all volumes but be told the reader's cutoff."""
    p = C.prompt_future_informed("[v05:c01:p0001] x", "Anne", 2, 5)
    assert "volumes 1-5" in p and "ONLY volumes 1-2" in p and "as known after volume 2" in p
    assert p != C.prompt("[v05:c01:p0001] x", "Anne", 5, "T")
