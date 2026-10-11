"""Phase 0: configuration loading, volume discovery, and routing behaviour.

The routing tests matter most. `resolve_role` is what makes the pipeline runnable with no API
key at all, and a regression there would silently route the bulk extraction stage at an API
provider — an expensive way to find out.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from narrativewiki import paths
from narrativewiki.config import (
    ConfigError,
    Settings,
    apply_schema_overrides,
    apply_set_overrides,
    load_settings,
    parse_attr_override,
    parse_chapter_range,
    parse_relation_override,
    parse_set_override,
    parse_trait_override,
    parse_volume_range,
)


@pytest.fixture(scope="module")
def settings():
    return load_settings("86")


# --- loading ---------------------------------------------------------------


def test_all_three_configs_load(settings):
    assert settings.series_id == "86"
    assert settings.series_title.startswith("86")
    assert settings.models["profiles"]
    assert settings.extraction["entity_types"]


def test_taxonomies_are_populated(settings):
    assert "CHARACTER" in settings.entity_types
    assert "AFFILIATED_WITH" in settings.relations
    assert "AGE" in settings.attributes
    assert "PERSONALITY" in settings.traits


# --- Phase 17: canonicalization config + relation conflicts_with -----------


def test_canonicalize_config_is_populated(settings):
    cfg = settings.canonicalize_config
    assert cfg["enabled"] is True
    assert 0.0 < cfg["similarity_threshold"] <= 1.0
    assert cfg["min_group_size"] >= 1


def test_friend_and_enemy_of_declare_each_other_as_conflicts(settings):
    assert "ENEMY_OF" in settings.relations["FRIEND_OF"]["conflicts_with"]
    assert "FRIEND_OF" in settings.relations["ENEMY_OF"]["conflicts_with"]


def test_every_conflicts_with_declaration_is_mutual(settings):
    """Phase 26: `graph/contradictions.py::_relation_conflict_groups` requires BOTH predicates
    to name each other and silently ignores a one-sided declaration — which is exactly how
    SAVED/KILLED and COMRADE_OF/ENEMY_OF went unarbitrated in the shipped v1-2 graph despite
    the machinery existing since Phase 17. A one-sided edit is invisible at runtime, so assert
    it here rather than pinning any single predicate's literal list."""
    one_sided = [
        (name, other)
        for name, cfg in settings.relations.items()
        for other in cfg.get("conflicts_with", [])
        if name not in settings.relations.get(other, {}).get("conflicts_with", [])
    ]
    assert not one_sided, f"one-sided conflicts_with declarations (silently ignored): {one_sided}"


# --- the page-routing rule the user asked for ------------------------------


def test_only_characters_get_unique_pages(settings):
    """Characters get their own page; everything else is an anchor on a shared codex page."""
    assert settings.entity_types["CHARACTER"]["page"] == "unique"
    for entity_type in ("FACTION", "LOCATION", "EVENT", "TECH"):
        assert settings.entity_types[entity_type]["page"] == "codex", entity_type


def test_route_for_builds_the_expected_urls(settings):
    assert settings.route_for("CHARACTER", "shinei-nouzen") == "/character/shinei-nouzen"
    assert settings.route_for("FACTION", "spearhead") == "/codex/factions#spearhead"
    # Locations and battles share one page, per the user's requirement.
    assert settings.route_for("LOCATION", "charite").startswith("/codex/places#")
    assert settings.route_for("EVENT", "morpho").startswith("/codex/places#")


def test_route_for_rejects_unknown_type(settings):
    with pytest.raises(ConfigError):
        settings.route_for("SPACESHIP", "x")


# --- volume discovery ------------------------------------------------------


@pytest.mark.skipif(not (paths.CORPUS_DIR / "86").is_dir(), reason="86 corpus not present")
def test_discovers_all_thirteen_volumes(settings):
    volumes = settings.discover_volumes()
    assert [v.vol for v in volumes] == list(range(1, 14))
    assert all(v.path.suffix == ".epub" for v in volumes)


def test_parse_volume_range_forms():
    available = list(range(1, 14))
    assert parse_volume_range(None, available) == available
    assert parse_volume_range("1-3", available) == [1, 2, 3]
    assert parse_volume_range("1,3,5", available) == [1, 3, 5]
    assert parse_volume_range("7", available) == [7]
    # Overlapping specs collapse rather than processing a volume twice.
    assert parse_volume_range("1-3,2-4", available) == [1, 2, 3, 4]


def test_parse_volume_range_rejects_missing_volumes():
    """A silent drop here would surface much later as a character missing half their facts."""
    with pytest.raises(ConfigError, match="only"):
        parse_volume_range("1-20", list(range(1, 14)))


def test_parse_volume_range_rejects_backwards_range():
    with pytest.raises(ConfigError, match="backwards"):
        parse_volume_range("9-2", list(range(1, 14)))


def test_parse_volume_range_error_text_unchanged_by_the_shared_refactor():
    """Phase 11 refactored parse_volume_range onto a shared _parse_range with parse_chapter_range
    -- this pins the exact historical message so that refactor never silently changes it."""
    with pytest.raises(
        ConfigError,
        match=r"Requested volume\(s\) \[20\] but only \[1, 2\] were found in the source "
        r"directory\. Check the filenames or `source\.volume_pattern`\.",
    ):
        parse_volume_range("20", [1, 2])


# --- parse_chapter_range -----------------------------------------------------


def test_parse_chapter_range_forms():
    available = list(range(5))
    assert parse_chapter_range(None, available) == available
    assert parse_chapter_range("1-3", available) == [1, 2, 3]
    assert parse_chapter_range("0,2,4", available) == [0, 2, 4]
    assert parse_chapter_range("3", available) == [3]


def test_parse_chapter_range_rejects_missing_chapter():
    with pytest.raises(ConfigError, match="only"):
        parse_chapter_range("9", [0, 1, 2])


def test_parse_chapter_range_rejects_backwards_range():
    with pytest.raises(ConfigError, match="backwards"):
        parse_chapter_range("3-1", [0, 1, 2, 3])


# --- model routing ---------------------------------------------------------


def test_bulk_stages_route_zero_cost_or_scope_capped(settings):
    """A stage may route to a PAID model only if that model fails closed outside the run scope.

    History: local-first (2026-09-03) -> OpenRouter free tier (2026-09-14) -> Vertex
    (2026-09-23, docs/vision/PHASE_28.md), when the maintainer activated Google Cloud credits and
    authorised paid routing. The old form of this test -- "every routed profile must price at
    $0" -- cannot survive that flip, but the thing it actually protects can: nothing may route
    to a paid model that can quietly spend without bound.

    So the invariant is now two-sided. A routed profile is acceptable when it is either:
      * $0 in both directions (local, or a sanctioned free tier), or
      * `tier: frontier` WITH a `max_volumes` cap -- which llm/client.py::_enforce_frontier_scope
        turns into a refusal before the provider is contacted once a run exceeds that scope.
    Anything else is the drift this test exists to catch: a paid model routed with no interlock.
    """
    sanctioned = {
        "local_fast", "local_prose", "local_small", "local_best",
        "mistral_fast", "mistral_prose",
        "groq_fast", "groq_prose",
        "openrouter_free", "openrouter_free_nex_pro",
    }
    for stage in ("entity_classify", "entity_alias", "claim_extract", "prose", "codex_summary"):
        profile = settings.resolve_role(stage)
        if profile.price_in == 0.0 and profile.price_out == 0.0:
            assert profile.name in sanctioned, (
                f"{stage} routed to {profile}, a $0 profile nobody sanctioned -- add it to "
                f"`sanctioned` deliberately, with a reason"
            )
            continue
        assert profile.tier == "frontier" and profile.max_volumes is not None, (
            f"{stage} routed to the PAID profile {profile} with no scope interlock "
            f"(tier: frontier + max_volumes in config/models.yaml) -- that is unbounded spend"
        )


def test_routing_falls_back_down_the_chain_as_credentials_disappear(settings, monkeypatch):
    """The routing chain is Vertex -> OpenRouter free tier -> local, and each rung is reached by
    the absence of the one above it (2026-09-23, docs/vision/PHASE_28.md).

    This is the guarantee `models.yaml`'s header makes: a machine with no Google Cloud project
    runs on the free tier exactly as it did before the Vertex flip, and a machine with no
    credentials at all still runs end to end, fully local. Vertex authenticates with ADC and a
    project rather than an api_key, which is why `Profile.is_callable` -- not `profile.api_key`
    -- is what decides each hop.
    """
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    load_settings.cache_clear()
    no_vertex = load_settings("86")
    assert no_vertex.resolve_role("prose_polish").name == "openrouter_free_nex_pro"
    assert no_vertex.resolve_role("arbitrate").name == "openrouter_free_nex_pro"

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    load_settings.cache_clear()
    no_keys = load_settings("86")
    assert no_keys.resolve_role("prose_polish").name == "local_prose"
    assert no_keys.resolve_role("arbitrate").name == "local_best"
    assert no_keys.resolve_role("claim_extract").name == "local_fast"
    load_settings.cache_clear()


def test_prose_stays_local_when_no_credentials_exist_at_all(settings, monkeypatch):
    """With neither a Google Cloud project nor any API key, every generative stage is local and
    the pipeline still runs -- the promise that has survived all three routing flips."""
    for var in ("GOOGLE_CLOUD_PROJECT", "OPENROUTER_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    load_settings.cache_clear()
    fresh = load_settings("86")
    for stage in ("entity_classify", "claim_extract", "scene_extract", "prose", "prose_polish",
                  "codex_summary", "arbitrate", "verify"):
        assert fresh.resolve_role(stage).is_local, f"{stage} is not local with zero credentials"
    load_settings.cache_clear()


def test_unknown_stage_names_the_known_ones(settings):
    with pytest.raises(ConfigError, match="claim_extract"):
        settings.resolve_role("no_such_stage")


def test_every_routed_role_exists(settings):
    """A typo in `routing` should fail here, not three hours into a run."""
    profiles = settings.models["profiles"]
    for stage, entry in settings.models["routing"].items():
        role = entry.get("role") if isinstance(entry, dict) else entry
        assert role in profiles, f"{stage} routes to undefined profile {role!r}"
        fallback = entry.get("fallback") if isinstance(entry, dict) else None
        # `fallback` is a single role or an ordered chain of them (2026-09-23).
        for name in (fallback if isinstance(fallback, list) else [fallback] if fallback else []):
            assert name in profiles, f"{stage} falls back to undefined profile {name!r}"


def test_groq_profiles_are_defined_and_openai_compatible(settings):
    """Phase 8: .env carries GROQ_API_KEY but nothing routed to it by default -- these profiles
    exist so `--model <stage>=groq_fast` works without a config or code edit."""
    for role in ("groq_fast", "groq_prose"):
        profile = settings._build_profile(role)  # noqa: SLF001 - test is in-family
        assert profile.provider == "openai"  # Groq is OpenAI-compatible; reuses that adapter
        assert profile.base_url == "https://api.groq.com/openai/v1"


def test_every_gemini_profile_is_vertex(settings):
    """2026-09-28: the AI Studio API (generativelanguage.googleapis.com, GOOGLE_API_KEY) is
    retired -- every `provider: google` profile must be a Vertex profile behind the paid-scope
    interlock, and the adapter refuses one that is not."""
    vertex_profiles = set()
    for role in settings.models["profiles"]:
        profile = settings._build_profile(role)  # noqa: SLF001
        if profile.provider == "google":
            assert profile.use_vertex, f"{role}: a Gemini profile on the retired AI Studio API"
        if profile.use_vertex:
            vertex_profiles.add(role)
            assert profile.provider == "google", f"{role}: use_vertex on a non-google provider"
            assert profile.tier == "frontier" and profile.max_volumes is not None, (
                f"{role}: a paid Vertex profile with no scope interlock"
            )
    assert vertex_profiles, "the Vertex profiles vanished from config/models.yaml"


def test_google_adapter_refuses_a_non_vertex_profile(settings):
    from narrativewiki.llm.providers import google
    from narrativewiki.llm.providers.base import ProviderError

    studio = replace(settings._build_profile("vertex_flash"), name="studio", use_vertex=False)  # noqa: SLF001
    with pytest.raises(ProviderError, match="AI Studio"):
        google._build_client(studio)


# --- per-series extraction overlay (VISION.md 2026-09-04) ------------------


def _bare_settings(extraction: dict) -> Settings:
    return Settings(series_id="test", series={}, models={"routing": {}, "profiles": {}}, extraction=extraction)


# --- CLI schema tuning: --attr / --trait / --relation / --only / --skip ----


def test_parse_attr_override_default_single_valued():
    name, cfg = parse_attr_override('KARMA=short_text:"Karma"')
    assert name == "KARMA"
    assert cfg == {"single": True, "format": "short_text", "display": "Karma"}


def test_parse_attr_override_multi_valued():
    name, cfg = parse_attr_override('EPITHET=short_phrase:"Epithet":multi')
    assert name == "EPITHET"
    assert cfg["single"] is False


def test_parse_attr_override_rejects_malformed_spec():
    with pytest.raises(ConfigError):
        parse_attr_override("KARMA")  # no '='
    with pytest.raises(ConfigError):
        parse_attr_override("KARMA=short_text")  # no display segment


def test_parse_trait_override_default_max_words():
    name, cfg = parse_trait_override('CATCHPHRASE="Catchphrase"')
    assert name == "CATCHPHRASE"
    assert cfg == {"display": "Catchphrase", "max_words": 10}
    name, cfg = parse_trait_override('CATCHPHRASE="Catchphrase":6')
    assert cfg["max_words"] == 6


def test_parse_relation_override_symmetric_and_inverse():
    name, cfg = parse_relation_override('ALLY_OF="Ally of":symmetric')
    assert name == "ALLY_OF"
    assert cfg == {"display": "Ally of", "symmetric": True}
    name, cfg = parse_relation_override('MENTOR2_OF="Mentor of":inverse=STUDENT2_OF')
    assert cfg["inverse"] == "STUDENT2_OF"


def test_apply_schema_overrides_adds_ad_hoc_predicate():
    settings = _bare_settings({"attributes": {"AGE": {"single": True}}})
    notes = apply_schema_overrides(settings, attrs=['KARMA=short_text:"Karma"'])
    assert "KARMA" in settings.attributes
    assert "AGE" in settings.attributes  # additive, not a replacement
    assert notes and "KARMA" in notes[0]


def test_apply_schema_overrides_only_restricts_to_named_predicates():
    settings = _bare_settings({"attributes": {"AGE": {}, "RANK": {}, "OCCUPATION": {}}})
    apply_schema_overrides(settings, only=["AGE"])
    assert set(settings.attributes) == {"AGE"}


def test_apply_schema_overrides_only_accepts_a_kind_word():
    """`--only trait` keeps every trait but excludes every attribute/relation."""
    settings = _bare_settings({
        "attributes": {"AGE": {}}, "relations": {"FRIEND_OF": {}}, "traits": {"SKILL": {}},
    })
    apply_schema_overrides(settings, only=["trait"])
    assert settings.attributes == {}
    assert settings.relations == {}
    assert settings.traits == {"SKILL": {}}


def test_apply_schema_overrides_skip_excludes_named_predicate_or_kind():
    settings = _bare_settings({"attributes": {"AGE": {}, "RANK": {}}, "relations": {"FRIEND_OF": {}}})
    apply_schema_overrides(settings, skip=["RANK", "relation"])
    assert set(settings.attributes) == {"AGE"}
    assert settings.relations == {}


def test_apply_schema_overrides_skip_can_exclude_its_own_ad_hoc_addition():
    """A predicate added by --attr is still subject to --skip naming it -- an ad-hoc addition
    isn't privileged over a restriction in the same invocation."""
    settings = _bare_settings({"attributes": {}})
    apply_schema_overrides(settings, attrs=['KARMA=short_text:"Karma"'], skip=["KARMA"])
    assert "KARMA" not in settings.attributes


# --- --set (generic dotted-key config override) -----------------------------


def test_parse_set_override_types_the_value_like_yaml():
    assert parse_set_override("extraction.page_gate.min_claims=2") == (
        "extraction", ["page_gate", "min_claims"], 2,
    )
    assert parse_set_override("extraction.canonicalize.similarity_threshold=0.86") == (
        "extraction", ["canonicalize", "similarity_threshold"], 0.86,
    )
    assert parse_set_override("series.entities.min_mentions=null") == (
        "series", ["entities", "min_mentions"], None,
    )
    assert parse_set_override("extraction.page_outline.history.traits=[BACKGROUND]") == (
        "extraction", ["page_outline", "history", "traits"], ["BACKGROUND"],
    )


def test_parse_set_override_rejects_unknown_root():
    with pytest.raises(ConfigError, match="unknown config root"):
        parse_set_override("bogus.key=1")


def test_parse_set_override_rejects_missing_equals_or_short_key():
    with pytest.raises(ConfigError):
        parse_set_override("extraction.page_gate.min_claims")
    with pytest.raises(ConfigError):
        parse_set_override("extraction=1")  # no field under the root


def test_apply_set_overrides_merges_a_nested_key_without_clobbering_siblings():
    settings = _bare_settings({"page_gate": {"min_claims": 1, "other": True}})
    apply_set_overrides(settings, ["extraction.page_gate.min_claims=3"])
    assert settings.extraction["page_gate"] == {"min_claims": 3, "other": True}


def test_apply_set_overrides_null_deletes_the_key():
    settings = _bare_settings({"page_gate": {"min_claims": 1}})
    apply_set_overrides(settings, ["extraction.page_gate.min_claims=null"])
    assert "min_claims" not in settings.extraction["page_gate"]


def test_apply_set_overrides_targets_series_and_models_too():
    settings = Settings(
        series_id="test",
        series={"entities": {"min_mentions": 3}},
        models={"routing": {}, "profiles": {}},
        extraction={},
    )
    apply_set_overrides(settings, ["series.entities.min_mentions=5"])
    assert settings.series["entities"]["min_mentions"] == 5


def test_apply_set_overrides_returns_no_note_on_a_repeated_noop_application():
    """`run-all` re-applies the same --set specs once per stage it calls, each resolving the
    shared lru_cache'd Settings -- a second application of an already-applied override must not
    print a second note, mirroring apply_model_overrides' own repeat-application behaviour."""
    settings = _bare_settings({"page_gate": {"min_claims": 1}})
    first = apply_set_overrides(settings, ["extraction.page_gate.min_claims=3"])
    second = apply_set_overrides(settings, ["extraction.page_gate.min_claims=3"])
    assert first
    assert not second


def test_a_standalone_novel_without_a_volume_number_is_volume_one(settings, tmp_path):
    """[30] "hound.epub" carries no volume number, and ingest refused the book outright."""
    from dataclasses import replace
    (tmp_path / "hound.epub").write_bytes(b"")
    solo = replace(settings, series={"source": {"dir": str(tmp_path)}})
    assert [(v.vol, v.path.name) for v in solo.discover_volumes()] == [(1, "hound.epub")]
    (tmp_path / "sequel.epub").write_bytes(b"")
    with pytest.raises(ConfigError):  # two unnumbered books have no order to guess
        solo.discover_volumes()


def test_a_part_group_numbers_books_in_reading_order(settings, tmp_path):
    """[30] Bookworm restarts at v01 in every Part; a `part` group makes that one sequence."""
    from dataclasses import replace
    for name in ("Part 2 v01.epub", "Part 1 v02.epub", "Part 1 v01.epub", "Part 10 v01.epub"):
        (tmp_path / name).write_bytes(b"")
    parts = replace(settings, series={"source": {
        "dir": str(tmp_path), "volume_pattern": r"Part (?P<part>\d+) v(?P<vol>\d+)"}})
    assert [(v.vol, v.path.name) for v in parts.discover_volumes()] == [
        (1, "Part 1 v01.epub"), (2, "Part 1 v02.epub"), (3, "Part 2 v01.epub"), (4, "Part 10 v01.epub")]


def test_no_profile_buys_priority_capacity(settings):
    """[33] Maintainer, 2026-09-28: never pay a premium to force capacity. Flex (cheaper) and
    standard are allowed; Vertex "priority" PayGo is not."""
    for name, prof in settings.models["profiles"].items():
        tier = str((prof.get("options") or {}).get("shared_request_type", "standard")).lower()
        assert tier in {"standard", "flex"}, f"profile {name!r} selects {tier!r} capacity"


def test_lifetime_spent_counts_billed_calls_of_runs_that_never_finished(tmp_path, monkeypatch):
    """[33] budget.json grows only when a run finishes; B1 t=5's stopped attempts ($14.79) were
    billed but never counted, so the lifetime cap -- the only bound on the real bill -- ran $17.91 low."""
    import json
    from narrativewiki import paths
    from narrativewiki.llm import budget as B
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    s = tmp_path / "data" / "w"
    (s / "_runs" / "r1").mkdir(parents=True)
    (s / "budget.json").write_text(json.dumps({"total_cost_usd": 1.0, "stages": {}}), encoding="utf-8")
    (s / "_runs" / "r1" / "calls.jsonl").write_text(
        "\n".join(json.dumps({"cost_usd": c, "cache_hit": False}) for c in (2.5, 0.5)), encoding="utf-8")
    assert abs(B.lifetime_spent() - 3.0) < 1e-9
