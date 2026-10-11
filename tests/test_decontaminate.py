"""[31] Reading-volume split of a standalone book, and the decontamination remap/paraphrase."""

import pytest

from narrativewiki.ingest.decontaminate import decontaminate_records, remap, report, residual
from narrativewiki.ingest.epub import RawChapter, RawVolume, select_reading_volume

MAP = {"Captain Nemo": "Captain Sorel", "Nemo": "Sorel", "Ned Land": "Tom Harlan", "Ned": "Tom"}


def test_remap_whole_word_case_and_longest_first():
    text = "Ned Land met Captain Nemo. NEMO’S ship. Nemoral land; Ned’s harpoon."
    assert remap(text, MAP) == "Tom Harlan met Captain Sorel. SOREL’S ship. Nemoral land; Tom’s harpoon."
    assert residual("Nemoral Sorel", MAP) == []
    assert residual("then Nemo spoke", MAP) == ["Nemo"]


def _records(*texts):
    return [{"para_id": f"v01:c00:p{i:04d}", "text": t, "chapter_title": "CAPTAIN NEMO", "n_words": len(t.split())}
            for i, t in enumerate(texts)]


def test_paraphrase_sees_only_remapped_text_and_bad_outputs_fall_back():
    seen = []

    def para(text):
        seen.append(text)
        return {"Sorel was silent.": "Nemo said nothing at all.",   # restores a name
                "Tom laughed.": "",                                  # empty
                "Tom Harlan swam.": "x" * 500}[text]                 # far too long

    src = _records("Nemo was silent.", "Ned laughed.", "Ned Land swam.")
    out = decontaminate_records(src, MAP, para)
    assert seen == ["Sorel was silent.", "Tom laughed.", "Tom Harlan swam."]
    assert [r["text"] for r in out] == ["Sorel said nothing at all.", "Tom laughed.", "Tom Harlan swam."]
    assert [r["decon"] for r in out] == ["paraphrased", "remap_only", "remap_only"]
    assert [r["para_id"] for r in out] == [r["para_id"] for r in src]
    assert out[0]["chapter_title"] == "CAPTAIN SOREL"
    rep = report(src, out, MAP)
    assert rep["residual_name_paragraphs"] == 0 and rep["paraphrased"] == 1


def test_a_copied_paraphrase_is_asked_for_again_and_never_counted_as_paraphrased():
    one = "Ned said that the long grey whale had been seen twice near the northern shore"
    two = "Nemo told the crew that the engines were to be stopped at noon on that day"
    again = []

    def retry(text):
        again.append(text)
        if text.startswith("Tom"):
            return "Twice, by the shore to the north, a whale long and grey had shown itself, Tom reported"
        return text  # the second paragraph is copied again

    out = decontaminate_records(_records(one, two, "Ned laughed."), MAP, lambda t: t, retry=retry)
    assert again == [remap(one, MAP), remap(two, MAP)]  # the three-word paragraph is too short to judge
    assert [r["decon"] for r in out] == ["paraphrased", "verbatim", "paraphrased"]
    assert out[0]["text"].startswith("Twice") and report(_records(one, two, "x"), out, MAP)["verbatim"] == 1


def _book():
    titles = ["The Project Gutenberg eBook of X", "PART ONE", "CHAPTER II", "PART TWO", "CHAPTER II"]
    return RawVolume(vol=1, title="X", isbn=None, pub_date=None, source_file="x.epub",
                     chapters=[RawChapter(i, f"c{i}", t, "chapter") for i, t in enumerate(titles)])


CFG = {"source": {"volume_breaks": ["^PART TWO"]}, "epub": {"drop_chapter_titles": ["^The Project Gutenberg"]}}


def test_select_reading_volume_splits_drops_and_renumbers():
    v1 = select_reading_volume(_book(), CFG)
    assert [(c.chapter_idx, c.chapter_title) for c in v1.chapters] == [(0, "PART ONE"), (1, "CHAPTER II")]
    book = _book()
    book.vol = 2
    v2 = select_reading_volume(book, CFG)
    assert [(c.chapter_idx, c.chapter_title) for c in v2.chapters] == [(0, "PART TWO"), (1, "CHAPTER II")]
    book = _book()
    book.vol = 3
    with pytest.raises(ValueError):
        select_reading_volume(book, CFG)
    assert len(select_reading_volume(_book(), {}).chapters) == 5
    # [31] One EPUB per book (the Anne series): drops apply, no slicing, at any volume number.
    book = _book()
    book.vol = 4
    kept = select_reading_volume(book, {"epub": CFG["epub"]})
    assert [c.chapter_title for c in kept.chapters] == ["PART ONE", "CHAPTER II", "PART TWO", "CHAPTER II"]


def test_volume_break_matches_a_book_heading_that_shares_the_chapter_segment():
    """[32] Middlemarch: "BOOK II. OLD AND YOUNG." opens the same segment as "CHAPTER XIII.", and
    the title keeps only the CHAPTER heading, so the break must read the chapter's headings."""
    chapters = [RawChapter(0, "c0", "CHAPTER XII.", "chapter"),
                RawChapter(1, "c1", "CHAPTER XIII.", "chapter", headings="BOOK II. OLD AND YOUNG. CHAPTER XIII.")]
    book = RawVolume(vol=2, title="M", isbn=None, pub_date=None, source_file="m.epub", chapters=chapters)
    v2 = select_reading_volume(book, {"source": {"volume_breaks": [r"^BOOK II\."]}})
    assert [c.chapter_title for c in v2.chapters] == ["CHAPTER XIII."]


def test_remap_only_ablation_uses_the_same_entity_map():
    import yaml

    from narrativewiki import paths

    def cfg(sid):
        return yaml.safe_load(paths.series_config(sid).read_text(encoding="utf-8"))["decontaminate"]

    for base in ("leagues", "anne"):
        assert cfg(f"{base}-remap")["entity_map"] == cfg(f"{base}-decon")["entity_map"]
        assert cfg(f"{base}-remap")["paraphrase"] is False and "paraphrase" not in cfg(f"{base}-decon")


def test_memorization_items_are_aligned_single_name_pairs():
    from narrativewiki.probe.memorization import select_items

    words = " word" * 40
    orig = [{"para_id": "v01:c00:p0000", "text": "Then Nemo spoke." + words, "n_words": 43},
            {"para_id": "v01:c00:p0001", "text": "Nemo and Ned left." + words, "n_words": 44},
            {"para_id": "v01:c00:p0002", "text": "Ned Land waited." + words, "n_words": 43}]
    decon = [{**r, "text": remap(r["text"], MAP)} for r in orig]
    items = select_items(orig, decon, MAP)
    assert [(i["para_id"], i["original_answer"], i["decon_answer"]) for i in items] == [("v01:c00:p0000", "Nemo", "Sorel")]
    assert items[0]["original_masked"].startswith("Then [MASK] spoke.")
    assert items[0]["decon_masked"].startswith("Then [MASK] spoke.")
    # A titled mention masks the name, not the title; "Ned Land" has no one-word key at its end.
    orig[2]["text"] = "Captain Nemo waited." + words
    decon = [{**r, "text": remap(r["text"], MAP)} for r in orig]
    items = select_items(orig, decon, MAP)
    assert items[1]["original_masked"].startswith("Captain [MASK] waited.")
    assert items[1]["decon_masked"].startswith("Captain [MASK] waited.")


def test_parametric_prompts_remap_names_and_keep_later_text_out():
    from narrativewiki.probe.parametric import build_prompts, summarize, valid_keywords, volume_text

    gold = {"characters": {"Captain Nemo": {"future": [{"claim": "Captain Nemo weeps.", "evidence": "v02"}]}}}
    recs = [{"vol": 1, "chapter_idx": 0, "chapter_title": "CHAPTER I", "text": "Captain Sorel sailed."}]
    jobs = build_prompts(gold, volume_text(recs), MAP)
    assert [(j["character"], j["mode"]) for j in jobs] == [
        ("Captain Sorel", "context"), ("Captain Sorel", "context_noguard"), ("Captain Sorel", "closed")]
    assert "do not reveal" in jobs[0]["prompt"] and "do not reveal" not in jobs[1]["prompt"]
    assert "Captain Sorel sailed." in jobs[0]["prompt"] and "Nemo" not in jobs[0]["prompt"]
    assert "sailed" not in jobs[2]["prompt"]
    gold["characters"]["Captain Nemo"]["future"][0]["keywords"] = ["sailed", "wept", "Nemo"]
    assert valid_keywords(gold, "Captain Sorel sailed.", MAP) == {"Captain Nemo weeps.": ["wept"]}
    rows = [{"mode": "context", "kind": "future", "supported": True, "character": "Captain Sorel", "claim": "x"},
            {"mode": "context", "kind": "control", "supported": False, "character": "Captain Sorel", "claim": "y"}]
    (s,) = summarize(rows, {("Captain Sorel", "context"): "a b c"})
    assert (s["future_leak_rate"], s["control_recall"], s["page_words"]) == (1.0, 0.0, 3)


def test_split_within_documents_cuts_at_headings_and_keeps_number_title_pairs(monkeypatch):
    """[31] Gutenberg #544 holds ~12 chapters per XHTML file: <h3>CHAPTER 10</h3><h3>LESLIE
    MOORE</h3><p>..</p>. Each chapter must become its own segment, the pair staying together."""
    from narrativewiki.ingest import epub as E

    class Item:
        file_name = "OEBPS/x.xhtml"
        def get_id(self): return "x"
        def get_content(self):
            return (b"<html><body><h1>BOOK</h1><h3>CHAPTER 1</h3><h3>ONE</h3><p>a</p><p>b</p>"
                    b"<div><a id='c2'/></div><h3>CHAPTER 2</h3><h3>TWO</h3><p>c</p></body></html>")

    monkeypatch.setattr(E, "_spine_documents", lambda book: [Item()])
    segs = [s for _, s in E._documents(None, set(), ["h3"])]
    assert [[h.get_text() for h in s.find_all("h3")] for s in segs] == [[], ["CHAPTER 1", "ONE"], ["CHAPTER 2", "TWO"]]
    assert [len(s.find_all("p")) for s in segs] == [0, 2, 1]
    assert len([s for _, s in E._documents(None, set(), [])]) == 1   # unset: one soup per document


def test_gold_facts_are_future_or_control_by_cutoff():
    """[31] Multi-cutoff gold: the evidence id's volume decides, so one fact file serves every t."""
    from narrativewiki.probe.parametric import facts_of, valid_keywords

    entry = {"facts": [{"claim": "a", "evidence": "v01:c00:p0001"},
                       {"claim": "b", "evidence": "v03:c02:p0004", "keywords": ["Redmond"]},
                       {"claim": "c", "evidence": "v05:c01:p0000", "keywords": ["Ingleside"]}],
             "future": [{"claim": "d", "evidence": "v02:c00:p0000"}]}
    assert [(f["claim"], f["first_vol"]) for f in facts_of(entry)] == [("a", 1), ("b", 3), ("c", 5), ("d", 2)]
    gold = {"characters": {"Anne": entry}}
    assert valid_keywords(gold, "text", {}, t=3) == {"c": ["Ingleside"]}
    assert valid_keywords(gold, "went to Redmond", {}, t=2) == {"b": [], "c": ["Ingleside"]}


def test_a_missing_page_is_a_recall_miss_but_not_a_leak_denominator():
    """2026-09-28 (known-answer case 9): an empty/missing page scores 0 without a classifier
    call; its control facts count against recall, its future facts are reported apart."""
    from narrativewiki.probe.parametric import score, summarize

    class NoCalls:
        def score_support(self, *a, **k):
            raise AssertionError("an empty page must not reach the classifier")

    gold = {"characters": {"Tobin": {"facts": [{"claim": "a", "evidence": "v01:c01:p0001"},
                                               {"claim": "b", "evidence": "v02:c01:p0001"}]}}}
    rows = score(NoCalls(), [{"character": "Tobin", "mode": "m"}], [""], gold, {}, {}, 1)
    [s] = summarize(rows, {("Tobin", "m"): ""})
    assert (s["n_control"], s["control_recall"]) == (1, 0.0)
    assert (s["n_future"], s["n_future_no_page"], s["future_leak_rate"]) == (0, 1, None)


def test_decontaminated_baseline_cast_is_the_source_gold_remapped():
    """[33] Baselines on anne-decon score the same people as on anne, under the text's own names."""
    import sys
    from pathlib import Path
    root = Path(__file__).parents[1]
    sys.path.insert(0, str(root / "scripts" / "baselines"))
    import run_baseline as rb
    from narrativewiki.config import load_settings
    orig, decon = rb.gold_cast(load_settings("anne")), rb.gold_cast(load_settings("anne-decon"))
    assert len(orig) == len(decon) == 43 and decon["Nell Harcourt"] == orig["Anne Shirley"]
    assert "Anne Shirley" not in decon and "Hugh Carrow" in decon
