"""Tests for site/mkdocs_wiki.py (Phase 25) -- the MkDocs Markdown wiki emitter that replaced
site/static_site.py. See tests/test_spoiler_leak.py for the pure-function link/cutoff-resolution
tests (`href`, `_relativize`, `resolve_cutoff`); this file covers `build_wiki`'s end-to-end
file-writing behaviour.
"""

from __future__ import annotations

import json
import re

from narrativewiki import paths
from narrativewiki.site import mkdocs_wiki as WE
from narrativewiki.site.mkdocs_wiki import build_wiki


class FakeSettings:
    series_id = "test"
    series_title = "Test Series"
    extraction = {"codex_pages": {"factions": {"title": "Factions & Organizations"}}}
    attributes: dict = {}
    # [30] Mirrors the real Settings property; a type with no `roster_labels` keeps
    # "Members"/"Adversaries", which is what these tests assert.
    entity_types: dict = {"FACTION": {}, "CHARACTER": {}}
    page_outline = [
        {"key": "lead", "kind": "lead", "title": ""},
        {"key": "overview", "kind": "fields", "title": "Overview"},
        {"key": "affiliations", "kind": "affiliations", "title": "Affiliations"},
        {"key": "relationships", "kind": "relationships", "title": "Relationships"},
    ]

    def route_for(self, entity_type, entity_id):
        return f"/character/{entity_id}" if entity_type == "CHARACTER" else f"/codex/factions#{entity_id}"


HOLO = {"entity_id": "holo", "canonical": "Holo", "type": "CHARACTER", "first_vol": 1}
LAWRENCE = {"entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence", "type": "CHARACTER", "first_vol": 1}
FRAM = {"entity_id": "the-spearhead", "canonical": "The Spearhead", "type": "FACTION", "first_vol": 1}
ENTITIES_BY_ID = {"holo": HOLO, "kraft-lawrence": LAWRENCE, "the-spearhead": FRAM}

PAGES_BUNDLE = {
    "holo": {
        "entity_id": "holo",
        "canonical": "Holo",
        "cutoffs": {
            "1": {
                "entity_id": "holo", "canonical": "Holo", "upto_vol": 1,
                "lead": "alive", "fields": {}, "prose": {},
            },
            "2": {
                "entity_id": "holo", "canonical": "Holo", "upto_vol": 2,
                "lead": "alive, travelling", "fields": {}, "prose": {},
            },
        },
    },
}

CODEX_BUNDLES = {
    "factions": {
        "the-spearhead": {
            "first_vol": 1,
            "kind": "factions",
            "cutoffs": {"1": {"summary": "A veteran unit.", "evidence": ["v01:c00:p0001"], "members": ["holo"]}},
        },
    },
}

RELATIONSHIP_BUNDLES = {
    "holo--kraft-lawrence": {
        "pair": ["holo", "kraft-lawrence"],
        "first_vol": 1,
        "cutoffs": {
            "1": {
                "relations": [
                    {"subject": "holo", "predicate": "TRAVELS_WITH", "display": "Travels with",
                     "object": "kraft-lawrence", "qualifier": None, "since_vol": 1}
                ],
                "history": [],
                "shared_scenes": [],
            },
        },
    },
}

TIMELINE_BUNDLES = {
    1: {
        "vol": 1,
        "chapters": [
            {"chapter_idx": 1, "events": [
                {"event_id": "ev1", "vol": 1, "location": None,
                 "beat_summary": "Lawrence meets Holo.", "participants": ["holo", "kraft-lawrence"],
                 "state_changes": [], "quotes": []},
            ]},
        ],
    },
}

INDEX_DOC = {
    "series": {"id": "test", "title": "Test Series"},
    "upto_vol": 2,
    "characters": [
        {"entity_id": "holo", "canonical": "Holo", "first_vol": 1, "importance": 1.0},
        {"entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence", "first_vol": 1, "importance": 0.9},
    ],
}


def _build(tmp_path, monkeypatch, upto=2):
    monkeypatch.setattr(paths, "SITE_DIR", tmp_path / "wiki")
    monkeypatch.setattr(paths, "DIST_DIR", tmp_path)
    build_wiki(
        FakeSettings(),
        pages_bundle=PAGES_BUNDLE,
        codex_bundles=CODEX_BUNDLES,
        relationship_bundles=RELATIONSHIP_BUNDLES,
        timeline_bundles=TIMELINE_BUNDLES,
        index_doc=INDEX_DOC,
        entities_by_id=ENTITIES_BY_ID,
        upto=upto,
    )
    return tmp_path / "wiki"


def test_writes_one_directory_per_cutoff_volume(tmp_path, monkeypatch):
    site_dir = _build(tmp_path, monkeypatch, upto=2)
    assert (site_dir / "v01").is_dir()
    assert (site_dir / "v02").is_dir()
    assert not (site_dir / "v03").exists()


def test_character_page_uses_the_cutoff_resolved_snapshot(tmp_path, monkeypatch):
    site_dir = _build(tmp_path, monkeypatch, upto=2)
    v1_text = (site_dir / "v01" / "character" / "holo.md").read_text(encoding="utf-8")
    v2_text = (site_dir / "v02" / "character" / "holo.md").read_text(encoding="utf-8")
    assert "alive" in v1_text and "travelling" not in v1_text
    assert "travelling" in v2_text


def test_codex_page_renders_as_anchors(tmp_path, monkeypatch):
    site_dir = _build(tmp_path, monkeypatch, upto=1)
    text = (site_dir / "v01" / "codex" / "factions.md").read_text(encoding="utf-8")
    assert "## The Spearhead {#the-spearhead}" in text
    assert "A veteran unit." in text
    assert "Holo" in text  # members bucket resolved to a canonical name


def test_relationship_page_is_written_and_named_by_the_bundle_key(tmp_path, monkeypatch):
    site_dir = _build(tmp_path, monkeypatch, upto=1)
    path = site_dir / "v01" / "relationships" / "holo--kraft-lawrence.md"
    assert path.is_file()
    assert "Travels with" in path.read_text(encoding="utf-8")


def test_timeline_page_only_appears_at_or_after_its_own_volume(tmp_path, monkeypatch):
    site_dir = _build(tmp_path, monkeypatch, upto=2)
    assert (site_dir / "v01" / "timeline" / "v01.md").is_file()
    assert (site_dir / "v02" / "timeline" / "v01.md").is_file()  # still visible, permanently stable


def test_mkdocs_yml_is_generated_with_strict_mode(tmp_path, monkeypatch):
    _build(tmp_path, monkeypatch, upto=1)
    yml = (tmp_path / "mkdocs.yml").read_text(encoding="utf-8")
    assert "strict: true" in yml
    assert "Test Series" in yml
    assert "docs_dir: wiki" in yml  # a sibling of SITE_DIR, never SITE_DIR's own parent


def test_no_character_page_written_for_a_cutoff_before_first_vol(tmp_path, monkeypatch):
    """A character with cutoffs starting at "1" never gets a page in a hypothetical earlier
    cutoff dir -- this repo's minimum cutoff is 1, so this is really the resolve_cutoff(None)
    path exercised end-to-end rather than a real first_vol > 1 case (covered directly by
    tests/test_spoiler_leak.py's resolve_cutoff tests)."""
    site_dir = _build(tmp_path, monkeypatch, upto=1)
    assert (site_dir / "v01" / "character" / "holo.md").is_file()


def test_every_emitted_link_stays_inside_its_own_cutoff_tree(tmp_path, monkeypatch):
    """The cross-cutoff-leak check: no ](...) target under v01/ may resolve outside v01/ after
    normalizing ../ segments."""
    import os
    import re

    site_dir = _build(tmp_path, monkeypatch, upto=2)
    link_re = re.compile(r"\]\(([^)\s]+)\)")
    root_links = 0
    for md_file in site_dir.rglob("*.md"):
        rel_parts = md_file.relative_to(site_dir).parts
        # [30] The root index.md belongs to no cutoff; routing readers INTO each cutoff is its
        # job. Only files inside a cutoff tree are held to containment, which is where a
        # cross-cutoff link would be an actual spoiler leak.
        cutoff_root = rel_parts[0] if len(rel_parts) > 1 else None
        for target in link_re.findall(md_file.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://")):
                continue
            resolved = os.path.normpath(os.path.join(md_file.parent, target.split("#")[0]))
            resolved_rel = os.path.relpath(resolved, site_dir)
            top = resolved_rel.split(os.sep)[0]
            if cutoff_root is None:
                # ...but it must still land on a real file inside the site.
                assert not resolved_rel.startswith(".."), f"{md_file}: link {target!r} escapes the site"
                assert os.path.isfile(resolved), f"{md_file}: link {target!r} does not resolve"
                root_links += 1
                continue
            assert top in (cutoff_root, "img"), f"{md_file}: link {target!r} escapes its cutoff dir"
    assert root_links >= 2, "the root index should route readers into each cutoff"


def _write_parsed(tmp_path, monkeypatch, records_by_vol):
    """Stand in for data/<series>/01_parsed/vNN.jsonl, the only data/ read build_wiki does."""
    parsed = tmp_path / "parsed"
    parsed.mkdir(exist_ok=True)
    for vol, records in records_by_vol.items():
        (parsed / f"v{vol:02d}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in records), encoding="utf-8"
        )
    monkeypatch.setattr(paths, "parsed_volume", lambda vol: parsed / f"v{vol:02d}.jsonl")


def _para(vol, chapter_idx, seq, text, **extra):
    return {
        "para_id": f"v{vol:02d}:c{chapter_idx:02d}:p{seq:04d}",
        "vol": vol, "chapter_idx": chapter_idx, "seq": seq, "text": text,
        "chapter_title": f"Chapter {chapter_idx + 1}", "print_page": 10 + seq,
        "scene_break_before": "none", **extra,
    }


PARSED = {
    1: [_para(1, 0, 0, "The rolling hills continued endlessly."),
        _para(1, 0, 1, "Boulders were prominent.")],
    2: [_para(2, 0, 0, "A second volume paragraph."),
        _para(2, 1, 0, "Another chapter entirely.")],
}


def test_source_pages_are_written_one_per_volume_chapter(tmp_path, monkeypatch):
    _write_parsed(tmp_path, monkeypatch, PARSED)
    wiki = _build(tmp_path, monkeypatch)
    assert (wiki / "v02" / "source" / "v01-c00.md").exists()
    assert (wiki / "v02" / "source" / "v02-c00.md").exists()
    assert (wiki / "v02" / "source" / "v02-c01.md").exists()
    assert (wiki / "v02" / "source" / "index.md").exists()


def test_every_paragraph_carries_its_para_id_as_an_anchor(tmp_path, monkeypatch):
    """The anchor a citation link resolves to. `attr_list` is already an enabled markdown
    extension, so no mkdocs.yml change is needed for these to become real HTML ids."""
    _write_parsed(tmp_path, monkeypatch, PARSED)
    wiki = _build(tmp_path, monkeypatch)
    page = (wiki / "v02" / "source" / "v01-c00.md").read_text(encoding="utf-8")
    assert "{: #nw-v01-c00-p0000 }" in page
    assert "{: #nw-v01-c00-p0001 }" in page
    assert "The rolling hills continued endlessly." in page


def test_source_view_never_contains_a_volume_after_its_own_cutoff(tmp_path, monkeypatch):
    """CLAUDE.md §1. The source view is the one page kind that emits raw corpus text, so its
    cutoff bound is the single most load-bearing filter in the emitter."""
    _write_parsed(tmp_path, monkeypatch, PARSED)
    wiki = _build(tmp_path, monkeypatch)
    v01_sources = sorted(p.name for p in (wiki / "v01" / "source").glob("v*.md"))
    assert v01_sources == ["v01-c00.md"], v01_sources
    assert not (wiki / "v01" / "source" / "v02-c00.md").exists()
    assert "A second volume paragraph." not in (wiki / "v01" / "source" / "index.md").read_text(encoding="utf-8")


def test_build_wiki_still_works_with_no_parsed_data(tmp_path, monkeypatch):
    """Degrades to no source pages rather than failing the build -- `wiki site build` must not
    require the ingest stage's output to be present."""
    monkeypatch.setattr(paths, "parsed_volume", lambda vol: tmp_path / "missing" / f"v{vol:02d}.jsonl")
    wiki = _build(tmp_path, monkeypatch)
    assert (wiki / "v02" / "character" / "holo.md").exists()
    assert not (wiki / "v02" / "source").exists()


def test_paragraph_starting_with_a_markdown_block_character_is_escaped(tmp_path, monkeypatch):
    _write_parsed(tmp_path, monkeypatch, {1: [_para(1, 0, 0, "- not a list item")], 2: []})
    wiki = _build(tmp_path, monkeypatch)
    assert r"\- not a list item" in (wiki / "v01" / "source" / "v01-c00.md").read_text(encoding="utf-8")


def test_every_citation_link_in_the_tree_resolves_to_an_emitted_anchor(tmp_path, monkeypatch):
    """The real end-to-end assertion for Phase 26: a citation that does not land on a real
    paragraph is worse than no citation, because it looks verifiable and is not."""
    _write_parsed(tmp_path, monkeypatch, PARSED)
    wiki = _build(tmp_path, monkeypatch)

    anchors = {
        (f.parent.parent.name, f.stem): set(re.findall(r"\{: #(nw-[a-z0-9\-]+) \}", f.read_text(encoding="utf-8")))
        for f in wiki.rglob("source/*.md")
    }
    link = re.compile(r"\]\(\.\./source/([a-z0-9\-]+)\.md#(nw-[a-z0-9\-]+)\)")
    broken = [
        (f, stem, anchor)
        for f in wiki.rglob("*.md")
        if f.parent.name != "source"
        for stem, anchor in link.findall(f.read_text(encoding="utf-8"))
        if anchor not in anchors.get((f.parent.parent.name, stem), set())
    ]
    assert not broken, broken


def test_relationship_heading_is_not_linked_when_the_partner_has_no_page_at_this_cutoff(tmp_path, monkeypatch):
    """Phase 26 part B: the live v1-2 wiki emitted `### [Jakob](../character/jakob.md)` on v01's
    Lawrence page. Jakob's first page is v02 (one claim in v01, below `page_gate.min_claims`), so
    the v01 file does not exist and `wiki audit links` FAILed on the dangling link. The partner
    must still be NAMED -- the relationship is real evidence, only its link target is missing."""
    monkeypatch.setattr(paths, "SITE_DIR", tmp_path / "wiki")
    monkeypatch.setattr(paths, "DIST_DIR", tmp_path)
    relationships = [
        {"entity_id": "kraft-lawrence", "predicate": "RIVAL_OF", "blurb": "Rival of — former town rogue",
         "since_vol": 1, "current": True, "evidence": []},
    ]
    pages_bundle = {
        "holo": {
            "entity_id": "holo", "canonical": "Holo",
            "cutoffs": {"1": {"entity_id": "holo", "canonical": "Holo", "upto_vol": 1,
                              "lead": "alive", "fields": {"relationships": relationships}, "prose": {}}},
        },
        # Lawrence's own first page is v02 -- so at v01 he is a name, not a link.
        "kraft-lawrence": {
            "entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence",
            "cutoffs": {"2": {"entity_id": "kraft-lawrence", "canonical": "Kraft Lawrence", "upto_vol": 2,
                              "lead": "alive", "fields": {}, "prose": {}}},
        },
    }
    build_wiki(
        FakeSettings(), pages_bundle=pages_bundle, codex_bundles={}, relationship_bundles={},
        timeline_bundles={}, index_doc=INDEX_DOC, entities_by_id=ENTITIES_BY_ID, upto=2,
    )
    site_dir = tmp_path / "wiki"
    v1 = (site_dir / "v01" / "character" / "holo.md").read_text(encoding="utf-8")
    assert not (site_dir / "v01" / "character" / "kraft-lawrence.md").exists()
    assert "### Kraft Lawrence" in v1
    assert "kraft-lawrence.md" not in v1
    # ...and at v02, where the page does exist, it is linked as before.
    v2 = (site_dir / "v02" / "character" / "holo.md").read_text(encoding="utf-8")
    assert "### [Kraft Lawrence](../character/kraft-lawrence.md)" in v2
    # [31] The volume index and the nav list him from his first PAGE, not his index first_vol
    # (Anne's strict build failed on exactly this: Irene Howard in the v04 index, page from v06).
    assert "kraft-lawrence.md" not in (site_dir / "v01" / "index.md").read_text(encoding="utf-8")
    assert "kraft-lawrence.md" in (site_dir / "v02" / "index.md").read_text(encoding="utf-8")
    nav = (tmp_path / "mkdocs.yml").read_text(encoding="utf-8")
    # [33] The shared nav is written into every page's HTML, so it names no character at all.
    assert "character/" not in nav and "Kraft Lawrence" not in nav


# --- [26C] stale pages ------------------------------------------------------------------------


def test_a_page_the_previous_build_wrote_is_removed(tmp_path, monkeypatch):
    """The shipped v1-2 wiki carried six pages from older builds, including a relationship page
    asserting "Holo -- Killed -- Saint Ruvinheigen" that the current graph does not support.
    `wiki audit links` cannot see it: a stale page's own links resolve fine."""
    site_dir = _build(tmp_path, monkeypatch, upto=2)
    stale = site_dir / "v02" / "relationships" / "holo--saint-ruvinheigen.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("# Holo & Saint Ruvinheigen\n\n- Holo — Killed — Saint Ruvinheigen\n", encoding="utf-8")

    _build(tmp_path, monkeypatch, upto=2)
    assert not stale.exists()
    # the pages this build DOES support are still there
    assert (site_dir / "v02" / "character" / "holo.md").exists()


# ---------------------------------------------------------------------------
# Phase 29 -- codex connectivity, empty kinds, and honest portraits
# ---------------------------------------------------------------------------


def test_codex_roster_names_are_links_not_plain_text(tmp_path, monkeypatch):
    """A roster that names Holo without linking her is a one-way edge -- her own page has
    linked back to the faction since Phase 7."""
    site_dir = _build(tmp_path, monkeypatch, upto=1)
    text = (site_dir / "v01" / "codex" / "factions.md").read_text(encoding="utf-8")
    assert "**Members:** [Holo](../character/holo.md)" in text


def test_ppr_related_bucket_is_not_rendered(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SITE_DIR", tmp_path / "wiki")
    monkeypatch.setattr(paths, "DIST_DIR", tmp_path)
    bundles = {
        "factions": {
            "the-spearhead": {
                "first_vol": 1,
                "kind": "factions",
                "cutoffs": {"1": {"summary": "A veteran unit.", "evidence": [],
                                  "members": ["holo"], "related": ["kraft-lawrence"]}},
            },
        },
    }
    build_wiki(
        FakeSettings(), pages_bundle=PAGES_BUNDLE, codex_bundles=bundles,
        relationship_bundles={}, timeline_bundles={}, index_doc=INDEX_DOC,
        entities_by_id=ENTITIES_BY_ID, upto=1,
    )
    text = (tmp_path / "wiki" / "v01" / "codex" / "factions.md").read_text(encoding="utf-8")
    assert "Related:" not in text


def test_a_codex_kind_with_nothing_to_show_is_not_written_or_linked(tmp_path, monkeypatch):
    """`tech.md` shipped for two volumes as a bare `# Technology` heading, reachable from the
    volume index and the nav."""
    monkeypatch.setattr(paths, "SITE_DIR", tmp_path / "wiki")
    monkeypatch.setattr(paths, "DIST_DIR", tmp_path)

    class Settings(FakeSettings):
        extraction = {
            "codex_pages": {
                "factions": {"title": "Factions & Organizations"},
                "tech": {"title": "Technology"},
            }
        }

    build_wiki(
        Settings(), pages_bundle=PAGES_BUNDLE, codex_bundles={**CODEX_BUNDLES, "tech": {}},
        relationship_bundles={}, timeline_bundles={}, index_doc=INDEX_DOC,
        entities_by_id=ENTITIES_BY_ID, upto=1,
    )
    assert not (tmp_path / "wiki" / "v01" / "codex" / "tech.md").exists()
    assert (tmp_path / "wiki" / "v01" / "codex" / "factions.md").is_file()
    index = (tmp_path / "wiki" / "v01" / "index.md").read_text(encoding="utf-8")
    assert "Technology" not in index
    assert "Factions & Organizations" in index
    assert "codex/tech.md" not in (tmp_path / "mkdocs.yml").read_text(encoding="utf-8")


def test_codex_roster_heading_follows_the_entry_entity_type():
    """[30] "Members" is a FACTION word. Pasloe, a village, shipped "**Members:** Count
    Ehrendott, Holo" because ORIGIN_FROM declares `membership: true`, so being *from* a place
    filed you as one of its members. Config names the roster per type."""
    class S(FakeSettings):
        entity_types = {"LOCATION": {"roster_labels": {"members": "Associated with"}},
                        "FACTION": {}}

    bundles = {
        "pasloe": {"first_vol": 1, "cutoffs": {"1": {"summary": "A village.", "members": ["holo"]}}},
        "milone": {"first_vol": 1, "cutoffs": {"1": {"summary": "A company.", "members": ["holo"]}}},
    }
    entities = {"pasloe": {"canonical": "Pasloe", "type": "LOCATION"},
                "milone": {"canonical": "Milone", "type": "FACTION"},
                "holo": {"canonical": "Holo", "type": "CHARACTER"}}
    out = WE._render_codex_kind("places", "Places", bundles, 1, S(), entities)
    assert "**Associated with:** " in out          # the LOCATION entry
    assert "**Members:** " in out                  # the FACTION entry, unchanged


def test_codex_roster_and_timeline_name_a_pageless_character_without_linking_it():
    """[33] Anne's places roster linked Wilson, Blythe and Margaret, who have no page at any
    cutoff; the strict MkDocs build failed on the dead links. Named, not linked."""
    bundles = {"pasloe": {"first_vol": 1, "cutoffs": {"1": {"summary": "A village.", "members": ["holo", "wilson"]}}}}
    entities = {"pasloe": {"canonical": "Pasloe", "type": "LOCATION"},
                "holo": {"canonical": "Holo", "type": "CHARACTER"},
                "wilson": {"canonical": "Wilson", "type": "CHARACTER"}}
    out = WE._render_codex_kind("places", "Places", bundles, 1, FakeSettings(), entities, {"holo"})
    assert "[Holo](" in out and "Wilson" in out and "[Wilson](" not in out
    doc = {"vol": 1, "chapters": [{"chapter_idx": 0, "events": [{"participants": ["holo", "wilson"], "beat_summary": "x"}]}]}
    tl = WE._render_timeline(doc, entities, {"holo"})
    assert "[Holo](" in tl and "[Wilson](" not in tl and "Wilson" in tl


def test_relationship_page_links_both_parties_and_keeps_the_qualifier():
    """[30] The relationship pages named both characters in plain text while those characters'
    pages linked back here - the one-way edge Phase 29 removed from the codex rosters, still live
    on all 18 of them. They also rendered `display` alone, dropping the `qualifier` that says what
    the relationship actually is, and `since_vol`."""
    doc = {"pair": ["holo", "kraft-lawrence"], "cutoffs": {"1": {"relations": [{
        "subject": "holo", "predicate": "COMRADE_OF", "display": "Comrade of",
        "object": "kraft-lawrence", "qualifier": "traveling companion", "since_vol": 1,
    }]}}}
    entities = {"holo": {"canonical": "Holo", "type": "CHARACTER"},
                "kraft-lawrence": {"canonical": "Kraft Lawrence", "type": "CHARACTER"}}

    out = WE._render_relationship(doc, 1, entities, FakeSettings())
    assert "[Holo](../character/holo.md)" in out
    assert "[Kraft Lawrence](../character/kraft-lawrence.md)" in out
    assert "traveling companion" in out and "since v1" in out

    # Without settings there are no routes to build, so it degrades to the old plain names.
    plain = WE._render_relationship(doc, 1, entities)
    assert "Holo — Comrade of — Kraft Lawrence" in plain
    assert "](" not in plain.split("## ")[0]

    # [31] A party with no page at this cutoff is named, not linked (Anne's strict build failed
    # on Leslie Moore & West at v04, West's page starting at v05).
    partial = WE._render_relationship(doc, 1, entities, FakeSettings(), written_ids={"holo"})
    assert "[Holo](../character/holo.md)" in partial
    assert "kraft-lawrence.md" not in partial and "Kraft Lawrence" in partial


def test_relationship_evidence_notice_fires_only_when_assembly_recorded_none():
    """A bundle written before citation-carrying assembly has no `evidence` key at all; stamping
    "source evidence unavailable" onto every such row tells the reader the wiki has no sources when
    really the artifact is stale. Only a recorded empty list is a claim about the evidence."""
    def doc(relation_extra):
        return {"pair": ["holo", "kraft-lawrence"], "cutoffs": {"1": {"relations": [{
            "subject": "holo", "predicate": "COMRADE_OF", "display": "Comrade of",
            "object": "kraft-lawrence", "qualifier": "traveling companion", "since_vol": 1,
            **relation_extra,
        }]}}}
    entities = {"holo": {"canonical": "Holo", "type": "CHARACTER"},
                "kraft-lawrence": {"canonical": "Kraft Lawrence", "type": "CHARACTER"}}

    stale = WE._render_relationship(doc({}), 1, entities, FakeSettings())
    assert "source evidence unavailable" not in stale

    looked_and_found_nothing = WE._render_relationship(doc({"evidence": []}), 1, entities, FakeSettings())
    assert "source evidence unavailable" in looked_and_found_nothing

    cited = WE._render_relationship(doc({"evidence": ["v01:c00:p0001"]}), 1, entities, FakeSettings())
    assert "source evidence unavailable" not in cited
    assert "../source/v01-c00.md#nw-v01-c00-p0001" in cited


def test_chapter_labels_count_front_matter_out_of_the_numbering():
    """[30] Volume 1 opens with a titled PROLOGUE at index 0, so `chapter_idx + 1` labelled the
    book's own Chapter One as "Chapter 2" and every citation inherited it -- `v1 ch.2 P62` sent a
    reader holding the book to the wrong chapter. Volume 2 has no front matter and was correct by
    luck, which is how this survived."""
    chapters = {
        1: {0: [{"chapter_title": "PROLOGUE"}], 1: [{"chapter_title": None}],
            2: [{"chapter_title": None}], 3: [{"chapter_title": "AFTERWORD"}]},
        2: {0: [{"chapter_title": None}], 1: [{"chapter_title": None}]},
    }
    try:
        WE.set_chapter_labels(chapters)
        assert WE.chapter_label(1, 0) == "PROLOGUE"
        assert WE.chapter_label(1, 1) == "Chapter 1"   # was "Chapter 2"
        assert WE.chapter_label(1, 2) == "Chapter 2"
        assert WE.chapter_label(1, 3) == "AFTERWORD"
        assert WE.chapter_label(2, 0) == "Chapter 1"   # no front matter: unchanged
        assert WE.citation_label("v01:c01:p0062") == "v1 ch.1 P62"
        assert WE.citation_label("v01:c00:p0012") == "v1 PROLOGUE P12"
    finally:
        WE.set_chapter_labels({})
    # With no map set the renderers stay pure functions of their inputs.
    assert WE.citation_label("v01:c01:p0062") == "v1 ch.2 P62"


def test_a_pair_page_is_written_only_when_it_has_a_relation_and_its_characters_link_to_it():
    """2026-09-25: all 30 shipped pair pages were orphans -- the nav leaves them out and no
    character page linked to them. Nine of those carried no relation at all (every one withheld by
    verification), one of them a bare heading. Such a page is not written, and a page that is
    written is linked from each party's Relationships heading."""
    from narrativewiki.site import okf

    entities = {"holo": {"canonical": "Holo", "type": "CHARACTER"},
                "weiz": {"canonical": "Weiz", "type": "CHARACTER"}}
    withheld = {"pair": ["holo", "weiz"], "cutoffs": {"1": {"relations": [], "history": [],
                                                            "shared_scenes": [{"vol": 1}]}}}
    assert WE._render_relationship(withheld, 1, entities, FakeSettings()) is None

    page = {"entity_id": "holo", "fields": {"relationships": [
        {"entity_id": "weiz", "blurb": "Friend of", "since_vol": 1, "evidence": []}]}}
    linked = okf._relationship_lines(page, entities, FakeSettings(), 2, {"holo", "weiz"}, {"holo--weiz"})
    assert "[the relationship](../relationships/holo--weiz.md)" in linked[0]
    unlinked = okf._relationship_lines(page, entities, FakeSettings(), 2, {"holo", "weiz"}, set())
    assert "the relationship" not in unlinked[0]


def test_timeline_names_chapters_and_links_its_participants():
    """[30] Headings were the raw index ("## Chapter 1" for v2's "The Road to Washi"), and a
    character named only as a participant had no inbound link anywhere."""
    from narrativewiki.site import mkdocs_wiki as MW
    MW.set_chapter_labels({2: {0: [{"chapter_title": "Prologue"}], 1: [{"chapter_title": "The Road to Washi"}]}})
    try:
        md = MW._render_timeline(
            {"vol": 2, "chapters": [{"chapter_idx": 1, "events": [
                {"participants": ["gerda", "guild"], "beat_summary": "Myne is babysat."}]}]},
            {"gerda": {"canonical": "Gerda", "type": "CHARACTER"},
             "guild": {"canonical": "Merchant’s Guild", "type": "FACTION"}})
    finally:
        MW.set_chapter_labels({})
    assert "## The Road to Washi" in md
    assert "[Gerda](../character/gerda.md)" in md and "Merchant’s Guild" in md


def test_no_page_or_pair_page_before_any_of_the_entitys_names_is_known(tmp_path, monkeypatch):
    """[33] Anne's v3 "Will Leslie" line was resolved to Leslie Moore, whose every name is first seen
    in v4; a v3 page titled "Leslie Moore" disclosed her. A page (and a pair page) waits for the
    entity's gazetteer first_vol even when a misresolved claim gives it content earlier."""
    import copy
    ents = copy.deepcopy(ENTITIES_BY_ID)
    ents["holo"]["first_vol"] = 2  # the fixture's bundle has Holo content from v1
    monkeypatch.setattr(paths, "SITE_DIR", tmp_path / "wiki")
    monkeypatch.setattr(paths, "DIST_DIR", tmp_path)
    build_wiki(FakeSettings(), pages_bundle=PAGES_BUNDLE, codex_bundles=CODEX_BUNDLES,
               relationship_bundles=RELATIONSHIP_BUNDLES, timeline_bundles=TIMELINE_BUNDLES,
               index_doc=INDEX_DOC, entities_by_id=ents, upto=2)
    wiki = tmp_path / "wiki"
    assert not (wiki / "v01" / "character" / "holo.md").exists()
    assert (wiki / "v02" / "character" / "holo.md").is_file()
    assert not list((wiki / "v01").glob("relationships/holo--*.md"))
