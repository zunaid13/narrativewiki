"""Phase 9: `paths.set_active_series` — series-segmented data/dist directories.

Every consumer in this codebase imports `paths.PARSED_DIR`/`paths.PAGES_DIR`/etc. as bare module
attributes (and several functions in `paths.py` itself reference them as free variables), so
`set_active_series` reassigns those globals in place rather than threading a `series_id`
parameter through the whole codebase — see the module's own docstring. These tests exist because
getting this wrong (segmenting the default series, or leaking a segmented path back to it) would
silently orphan the real, already-built 86 corpus on disk.
"""

from __future__ import annotations

import pytest

from narrativewiki import paths


@pytest.fixture(autouse=True)
def _restore_default_series():
    """Every other test file in this suite runs with no active series ever set (the pre-Phase-9
    behaviour) and reads `paths.PARSED_DIR`-style constants directly — leaking a segmented path
    out of this file would silently break them. Reset unconditionally after every test here,
    not just the ones that call `set_active_series` explicitly."""
    yield
    paths.set_active_series(None)


def test_default_series_is_unsegmented():
    """86 (or no --series at all) must resolve to the ORIGINAL data/dist layout, byte-identical
    to before this feature existed -- the real, already-built 86 corpus lives there."""
    paths.set_active_series("86")
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"
    assert paths.DIST_DIR == paths.PROJECT_ROOT / "dist"
    assert paths.SITE_DIR == paths.PROJECT_ROOT / "dist" / "wiki"
    assert paths.parsed_volume(1) == paths.PROJECT_ROOT / "data" / "01_parsed" / "v01.jsonl"


def test_no_call_at_all_is_also_unsegmented():
    """The state before any command has run (module import time) must match the default series
    exactly -- a test or script that never calls set_active_series must see the real 86 paths."""
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"
    assert paths.PARSED_DIR == paths.PROJECT_ROOT / "data" / "01_parsed"


def test_a_different_series_gets_its_own_subtree():
    paths.set_active_series("spice-and-wolf")
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data" / "spice-and-wolf"
    assert paths.DIST_DIR == paths.PROJECT_ROOT / "dist" / "spice-and-wolf"
    assert paths.SITE_DIR == paths.PROJECT_ROOT / "dist" / "spice-and-wolf" / "wiki"
    assert (
        paths.parsed_volume(1)
        == paths.PROJECT_ROOT / "data" / "spice-and-wolf" / "01_parsed" / "v01.jsonl"
    )
    assert paths.page_json("holo", 3) == (
        paths.PROJECT_ROOT / "data" / "spice-and-wolf" / "05_pages" / "holo" / "v03.json"
    )
    assert paths.scenes_volume(3) == (
        paths.PROJECT_ROOT / "data" / "spice-and-wolf" / "02b_scenes" / "v03.jsonl"
    )
    assert paths.scene_epithets(3) == (
        paths.PROJECT_ROOT / "data" / "spice-and-wolf" / "02b_scenes" / "epithets_v03.jsonl"
    )


def test_every_stage_dir_and_stage_dirs_map_move_together():
    paths.set_active_series("spice-and-wolf")
    root = paths.PROJECT_ROOT / "data" / "spice-and-wolf"
    assert paths.PARSED_DIR == root / "01_parsed"
    assert paths.ENTITIES_DIR == root / "02_entities"
    assert paths.SCENES_DIR == root / "02b_scenes"
    assert paths.CLAIMS_DIR == root / "03_claims"
    assert paths.GRAPH_DIR == root / "04_graph"
    assert paths.EVENTS_DIR == root / "04b_events"
    assert paths.PAGES_DIR == root / "05_pages"
    assert paths.BUNDLE_DIR == root / "06_bundle"
    assert paths.STAGE_DIRS == {
        "ingest": paths.PARSED_DIR,
        "gazetteer": paths.ENTITIES_DIR,
        "scenes": paths.SCENES_DIR,
        "claims": paths.CLAIMS_DIR,
        "graph": paths.GRAPH_DIR,
        "events": paths.EVENTS_DIR,
        "pages": paths.PAGES_DIR,
        "bundle": paths.BUNDLE_DIR,
    }
    assert list(paths.STAGE_DIRS) == ["ingest", "gazetteer", "scenes", "claims", "graph", "events", "pages", "bundle"]


def test_llm_cache_is_shared_across_series_not_segmented():
    """The LLM cache is content-addressed (llm/cache.py::make_key hashes provider+model+prompt+
    options) -- a cached answer is valid regardless of which series asked, so it must stay at one
    shared location rather than being duplicated per series."""
    unsegmented = paths.LLM_CACHE_DIR
    paths.set_active_series("spice-and-wolf")
    assert paths.LLM_CACHE_DIR == unsegmented
    assert paths.CACHE_DIR == unsegmented.parent


def test_switching_series_back_and_forth_is_clean():
    paths.set_active_series("spice-and-wolf")
    assert paths.DATA_DIR != paths.PROJECT_ROOT / "data"
    paths.set_active_series("86")
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"
    paths.set_active_series("spice-and-wolf")
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data" / "spice-and-wolf"


def test_none_resets_to_unsegmented():
    paths.set_active_series("spice-and-wolf")
    paths.set_active_series(None)
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"


def test_ensure_dirs_creates_the_active_series_subtree(monkeypatch, tmp_path):
    """`wiki doctor`/every stage command calls `ensure_dirs()` after `_settings()` has already
    called `set_active_series` -- it must create directories under the ACTIVE series's subtree,
    not always the default one. Monkeypatching PROJECT_ROOT sandboxes the writes into tmp_path
    rather than the real repo; CACHE_DIR/LLM_CACHE_DIR are fixed at import time against the REAL
    PROJECT_ROOT (see the module docstring -- they are deliberately not series-aware at all), so
    this test only checks the directories set_active_series actually moved."""
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    paths.set_active_series("spice-and-wolf")
    paths.ensure_dirs()
    assert (tmp_path / "data" / "spice-and-wolf" / "01_parsed").is_dir()
    assert (tmp_path / "data" / "spice-and-wolf" / "02b_scenes").is_dir()
    assert (tmp_path / "data" / "spice-and-wolf" / "06_bundle" / "pages").is_dir()
    assert (tmp_path / "data" / "spice-and-wolf" / "06_bundle" / "codex").is_dir()
    assert (tmp_path / "dist" / "spice-and-wolf" / "wiki").is_dir()


# ---------------------------------------------------------------------------
# set_build_cutoff -- Phase 24, --gate=build
# ---------------------------------------------------------------------------


def test_set_build_cutoff_redirects_entities_and_claims_dirs():
    paths.set_active_series("spice-and-wolf")
    render_entities_dir = paths.ENTITIES_DIR
    render_claims_dir = paths.CLAIMS_DIR

    paths.set_build_cutoff(1)
    assert paths.build_cutoff() == 1
    assert paths.ENTITIES_DIR == paths.DATA_DIR / "@t01" / "02_entities"
    assert paths.gazetteer() == paths.DATA_DIR / "@t01" / "02_entities" / "gazetteer.json"
    assert paths.mentions() == paths.DATA_DIR / "@t01" / "02_entities" / "mentions.jsonl"
    assert paths.candidates() == paths.DATA_DIR / "@t01" / "02_entities" / "candidates.jsonl"
    # Claims now move too, as of the claim-extraction extension of --gate=build -- graph/pages
    # are still out of scope (paths.py::set_build_cutoff's own docstring says so explicitly).
    assert paths.CLAIMS_DIR == paths.DATA_DIR / "@t01" / "03_claims"
    assert paths.claims_volume(1) == paths.DATA_DIR / "@t01" / "03_claims" / "v01.jsonl"
    assert paths.STAGE_DIRS["claims"] == paths.CLAIMS_DIR
    assert paths.STAGE_DIRS["gazetteer"] == paths.ENTITIES_DIR

    paths.set_build_cutoff(None)
    assert paths.build_cutoff() is None
    assert paths.ENTITIES_DIR == render_entities_dir
    assert paths.CLAIMS_DIR == render_claims_dir
    assert paths.STAGE_DIRS["claims"] == render_claims_dir
    assert paths.STAGE_DIRS["gazetteer"] == render_entities_dir
    paths.set_active_series(None)


def test_set_active_series_clears_a_stale_build_cutoff():
    """A build_cutoff redirect from a previous series/command must not leak into the next one
    just because nobody explicitly called set_build_cutoff(None)."""
    paths.set_active_series("spice-and-wolf")
    paths.set_build_cutoff(2)
    assert paths.build_cutoff() == 2

    paths.set_active_series("86")
    assert paths.build_cutoff() is None
    assert paths.ENTITIES_DIR == paths.DATA_DIR / "02_entities"
    paths.set_active_series(None)


def test_different_cutoffs_get_different_directories():
    paths.set_active_series("spice-and-wolf")
    paths.set_build_cutoff(1)
    t1_dir = paths.ENTITIES_DIR
    paths.set_build_cutoff(2)
    t2_dir = paths.ENTITIES_DIR
    assert t1_dir != t2_dir
    paths.set_build_cutoff(None)
    paths.set_active_series(None)


def test_a_variant_series_reads_its_base_config_and_text_but_writes_its_own_tree():
    """[33] `<base>@<variant>` (a baseline's pages) shares the base's config, parsed text and gold
    and never writes into the base's data tree."""
    from narrativewiki.config import load_settings

    load_settings.cache_clear()
    try:
        paths.set_active_series("anne@b1")
        assert paths.series_config("anne@b1").name == "series.anne.yaml"
        assert paths.PARSED_DIR == paths.PROJECT_ROOT / "data" / "anne" / "01_parsed"
        assert paths.PAGES_DIR == paths.PROJECT_ROOT / "data" / "anne@b1" / "05_pages"
        assert paths.RUNS_DIR == paths.PROJECT_ROOT / "data" / "anne@b1" / "_runs"
        assert paths.wiki_cutoff_dir(1).is_relative_to(paths.PROJECT_ROOT / "dist" / "anne@b1")
        assert load_settings("anne@b1").series["gold_from"] == "anne"
        assert paths.variant_base("anne") is None
    finally:
        paths.set_active_series(None)
        load_settings.cache_clear()
