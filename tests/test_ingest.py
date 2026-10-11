"""Phase 1: EPUB ingestion.

The traps in CLAUDE.md section 3 are the whole point of this module, so the tests target them
directly: image-to-dash substitution ordering (trap 5), chapter continuation across h1-less
documents (trap 2), and the corpus-wide para_raid non-zero invariant `wiki audit ingest` also
checks. The v01 test is skipped if the EPUB is not present, since `corpus/` is reference-corpus data
rather than a package asset.
"""

from __future__ import annotations

import warnings

import pytest
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from narrativewiki import paths
from narrativewiki.config import load_settings
from narrativewiki.ingest.epub import _classify_kind, parse_epub
from narrativewiki.ingest.normalize import normalize_paragraph_text, substitute_and_strip_images

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


# --- normalize.py ------------------------------------------------------------


def test_normalize_collapses_whitespace_and_nbsp():
    assert normalize_paragraph_text("  Friendly Units:\xa0\xa00  \n") == "Friendly Units: 0"


def test_image_substitution_happens_before_get_text():
    """trap 5: an mdash image mid-sentence must become '—', not vanish."""
    soup = BeautifulSoup(
        '<p>"thank you for saving m<img src="../Images/Art_mdash.jpg"/>e."</p>', "lxml"
    )
    p = soup.find("p")
    rules = [{"src_contains": "mdash", "text": "—"}]
    substitute_and_strip_images(p, rules, strip_remaining=True)
    assert p.get_text() == '"thank you for saving m—e."'


def test_unmatched_images_are_stripped_not_left_in_text():
    soup = BeautifulSoup('<p>before<img src="../Images/Art_P29.jpg"/>after</p>', "lxml")
    p = soup.find("p")
    substitute_and_strip_images(p, [], strip_remaining=True)
    assert p.get_text() == "beforeafter"
    assert p.find("img") is None


# --- epub.py: chapter kind classification -----------------------------------


@pytest.mark.parametrize(
    "number_text,epub_types,has_epigraph_div,expected",
    [
        ("PROLOGUE", set(), False, "prologue"),
        ("EPILOGUE II", set(), False, "epilogue"),
        ("INTERLUDE", set(), False, "interlude"),
        ("CHAPTER 3", set(), False, "chapter"),
        (None, {"frontmatter", "preface"}, True, "epigraph"),
        (None, {"frontmatter", "preface"}, False, "prologue"),
        (None, {"backmatter", "appendix"}, False, "afterword"),
        ("9.29", set(), False, "chapter"),  # v11 date-titled chapters
    ],
)
def test_classify_kind(number_text, epub_types, has_epigraph_div, expected):
    assert _classify_kind(number_text, epub_types, has_epigraph_div) == expected


# --- end-to-end against the reference corpus ---------------------------------


@pytest.fixture(scope="module")
def settings():
    return load_settings("86")


@pytest.fixture(scope="module")
def v01_path(settings):
    volumes = {v.vol: v.path for v in settings.discover_volumes()}
    if 1 not in volumes:
        pytest.skip("corpus/86 v01 EPUB not present")
    return volumes[1]


def test_v01_parses_with_no_zero_para_raid(settings, v01_path):
    raw = parse_epub(v01_path, 1, settings.series)
    speech = [p.speech for c in raw.chapters for p in c.paragraphs]
    assert speech.count("para_raid") > 0
    assert speech.count("machine") > 0


def test_v01_chapter_continuation_absorbs_h1_less_documents(settings, v01_path):
    """trap 2: chapter010/010a/010b must merge into one chapter, keyed off the h1-bearing doc."""
    raw = parse_epub(v01_path, 1, settings.series)
    ids = [c.chapter_id for c in raw.chapters]
    assert ids.count("chapter010") == 1
    assert "chapter010a" not in ids and "chapter010b" not in ids


def test_v01_has_a_hard_scene_break(settings, v01_path):
    raw = parse_epub(v01_path, 1, settings.series)
    breaks = [p.scene_break_before for c in raw.chapters for p in c.paragraphs]
    assert "hard" in breaks


def test_v01_word_count_is_in_expected_range(settings, v01_path):
    raw = parse_epub(v01_path, 1, settings.series)
    total_words = sum(len(p.text.split()) for c in raw.chapters for p in c.paragraphs)
    assert 65_000 < total_words < 85_000


# --- epub.heading_tags (docs/vision/plans/0008-pre-full-scale-audit.md S2) ----


def _write_h2_epub(path, *, navigation_position=None) -> None:
    """A minimal, real EPUB (via ebooklib, not a hand-rolled fixture) using <h2> instead of <h1>
    for its chapter headings -- 86 and Spice and Wolf both happen to use <h1>, so this trap has
    never shown up against the reference corpus; a source using a different heading tag needs its
    own fixture to prove the config knob actually works."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("test-h2")
    book.set_title("Test")
    book.set_language("en")
    c1 = epub.EpubHtml(title="C1", file_name="c1.xhtml", lang="en")
    c1.content = (
        '<html><body><section><h2 class="chapter-number">Chapter 1</h2>'
        "<p>Hello world.</p></section></body></html>"
    )
    c2 = epub.EpubHtml(title="C2", file_name="c2.xhtml", lang="en")
    c2.content = (
        '<html><body><section><h2 class="chapter-number">Chapter 2</h2>'
        "<p>Goodbye world.</p></section></body></html>"
    )
    book.add_item(c1)
    book.add_item(c2)
    book.toc = (c1, c2)
    book.add_item(epub.EpubNcx())
    navigation = epub.EpubNav(file_name="renamed-contents.xhtml")
    book.add_item(navigation)
    book.spine = [c1, c2]
    if navigation_position is not None:
        book.spine.insert(navigation_position, navigation)
    epub.write_epub(str(path), book)


def test_h2_headings_are_detected_without_the_config_knob(tmp_path):
    """The bug S2 named: a source using <h2> instead of <h1> for chapter headings silently lost
    its chapter boundaries with the default config. [30] `_detect_heading_tags` now picks the
    tag the book actually uses when the series does not set `heading_tags`."""
    path = tmp_path / "test.epub"
    _write_h2_epub(path)
    raw = parse_epub(path, 1, {"epub": {"chapter_start_selector": "h2.chapter-number"}})
    assert len(raw.chapters) == 2


def test_epub_heading_tags_config_fixes_h2_chapter_detection(tmp_path):
    """Setting `epub.heading_tags: ["h2"]` in a series config restores correct chapter
    splitting -- the fix, proven against the exact failure the previous test demonstrates."""
    path = tmp_path / "test.epub"
    _write_h2_epub(path)
    raw = parse_epub(
        path, 1,
        {"epub": {"chapter_start_selector": "h2.chapter-number", "heading_tags": ["h2"]}},
    )
    assert len(raw.chapters) == 2
    assert [p.text for c in raw.chapters for p in c.paragraphs] == ["Hello world.", "Goodbye world."]


@pytest.mark.parametrize("navigation_position", [0, 1, 2])
def test_spine_navigation_does_not_create_chapters_or_shift_ids(tmp_path, navigation_position):
    path = tmp_path / "navigation.epub"
    _write_h2_epub(path, navigation_position=navigation_position)
    raw = parse_epub(path, 1, {"epub": {
        "chapter_start_selector": "h2.chapter-number", "heading_tags": ["h1", "h2"],
    }})
    assert [c.chapter_idx for c in raw.chapters] == [0, 1]
    assert [c.chapter_id for c in raw.chapters] == ["chapter_0", "chapter_1"]
    assert [[p.text for p in c.paragraphs] for c in raw.chapters] == [
        ["Hello world."], ["Goodbye world."],
    ]


# --- [25] Image capture from art-plate documents ----------------------------


def _make_jpeg_bytes(size: int) -> bytes:
    """Minimal but structurally valid JPEG bytes (SOI + APP0 + EOI) padded to `size`."""
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    eoi = b"\xff\xd9"
    payload = soi + app0 + b"\x00" * max(0, size - len(soi) - len(app0) - len(eoi)) + eoi
    return payload


def _write_epub_with_art_plate(path, *, image_size: int = 20_000, n_chapters: int = 1) -> None:
    """EPUB with one chapter and one art-plate document containing a JPEG image."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("test-artplate")
    book.set_title("Test With Art")
    book.set_language("en")

    # The illustration image item.
    img_item = epub.EpubItem(
        uid="art-p1",
        file_name="Images/Art_P1.jpg",
        media_type="image/jpeg",
        content=_make_jpeg_bytes(image_size),
    )
    book.add_item(img_item)

    # The art-plate HTML document (no heading, just an <img>).
    art = epub.EpubHtml(title="Art", file_name="art.xhtml", lang="en")
    art.content = '<html><body><section><img src="../Images/Art_P1.jpg"/></section></body></html>'
    book.add_item(art)

    # A real chapter with an h2 heading.
    chapter = epub.EpubHtml(title="C1", file_name="c1.xhtml", lang="en")
    chapter.content = (
        '<html><body><section><h2 class="chapter-number">Chapter 1</h2>'
        "<p>Hello world.</p></section></body></html>"
    )
    book.add_item(chapter)

    book.toc = (art, chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = [art, chapter]
    epub.write_epub(str(path), book)


def test_art_plate_page_contributes_no_chapter_or_paragraph(tmp_path):
    """An image-only page is dropped from the text (Phase 32 removed image capture itself)."""
    path = tmp_path / "art.epub"
    _write_epub_with_art_plate(path)
    raw = parse_epub(path, 1, {"epub": {
        "chapter_start_selector": "h2.chapter-number",
        "heading_tags": ["h2"],
    }})
    assert [len(c.paragraphs) for c in raw.chapters] == [1]
    assert not hasattr(raw, "images")


def test_british_single_quote_dialogue_is_dialogue_by_default():
    """[30] With only “ as the default opening quote, a British novel's ‘dialogue’ read as narration."""
    import re
    from bs4 import BeautifulSoup
    from narrativewiki.ingest.epub import DEFAULT_OPEN_QUOTES, _classify_speech
    never = re.compile(r"^$^")
    for text in ("‘Hello,’ said he.", '"Hello," said he.', "« Bonjour », dit-il."):
        p = BeautifulSoup(f"<p>{text}</p>", "lxml").p
        assert _classify_speech(
            p, set(), p.get_text(), para_raid_pattern=never, machine_container_pattern=never,
            machine_text_pattern=never, dialogue_open_quotes=tuple(DEFAULT_OPEN_QUOTES),
        ) == "dialogue"


def test_back_matter_catalogue_is_dropped_for_every_series():
    """[34] Oz volume 3 ended with "Books by L. Frank Baum": blurbs of books 4-7 inside a cutoff-3
    text (OPEN_GAPS G12). Dropped by title with no series config at all."""
    from narrativewiki.ingest.epub import RawChapter, RawVolume, select_reading_volume

    titles = ["CHAPTER 1. A Ride", "CHAPTER 2. Home", "Books by L. Frank Baum", "Transcriber's Note"]
    rv = RawVolume(vol=3, title="Oz", isbn=None, pub_date=None, source_file="oz.epub",
                   chapters=[RawChapter(i, f"c{i}", t, "chapter") for i, t in enumerate(titles)])
    kept = select_reading_volume(rv, {})
    assert [c.chapter_title for c in kept.chapters] == titles[:2]
    assert [c.chapter_idx for c in kept.chapters] == [0, 1]
