"""[33] Gold character -> the system's page(s). B5's v1-5 rebuild filed Diana Barry under "Diana" and
split Anne over two pages; scored by gold slug alone, 12 of 43 gold characters read as page-less."""
from pathlib import Path

from narrativewiki import paths
from narrativewiki.probe import parametric as par


def test_mapped_names_union_and_unmapped_fall_back_to_the_gold_slug(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    (docs / "eval" / "parametric" / "pages").mkdir(parents=True)
    (docs / "eval" / "parametric" / "pages" / "w.yaml").write_text(
        "Diana Barry: [diana, di]\nAnne Shirley: [anne-shirley, anne]\n", encoding="utf-8")
    monkeypatch.setattr(paths, "DOCS_DIR", docs)
    cut = tmp_path / "v01"
    (cut / "character").mkdir(parents=True)
    for slug in ("diana", "anne-shirley", "gilbert-blythe"):
        (cut / "character" / f"{slug}.md").write_text(slug, encoding="utf-8")

    assert [p.stem for p in par.gold_pages("w", "Diana Barry", cut)] == ["diana"]  # `di` has no page yet
    assert [p.stem for p in par.gold_pages("w", "Anne Shirley", cut)] == ["anne-shirley"]
    assert [p.stem for p in par.gold_pages("w", "Gilbert Blythe", cut)] == ["gilbert-blythe"]  # unmapped
    assert par.gold_pages("w@b2", "Diana Barry", cut) == []  # a baseline: gold slug only, no page
    assert par.gold_pages("w", "Rilla Blythe", cut) == []    # page-less: still in the denominators


def test_the_anne_map_names_only_pages_the_b5_build_can_write():
    """Every mapped slug must be an entity id in the gazetteer, or the map silently finds nothing."""
    import json
    import yaml
    root = Path(__file__).resolve().parents[1]
    gaz_file = root / "data" / "anne" / "02_entities" / "gazetteer.json"
    if not gaz_file.is_file():  # data/ is gitignored; the check runs where the build exists
        return
    gaz = json.loads(gaz_file.read_text(encoding="utf-8"))
    ids = {e["entity_id"] for e in gaz.get("entities", gaz)}
    mapping = yaml.safe_load((root / "docs" / "eval" / "parametric" / "pages" / "anne.yaml").read_text(encoding="utf-8"))
    gold = yaml.safe_load((root / "docs" / "eval" / "parametric" / "anne.yaml").read_text(encoding="utf-8"))
    assert set(mapping) <= set(gold["characters"])
    assert {s for slugs in mapping.values() for s in slugs} <= ids
