"""Phase 8: `--model` CLI overrides.

`config.py::resolve_role` is the one chokepoint every stage's model decision flows through
(see its own docstring); these tests cover the override layer bolted onto it —
`parse_model_override`/`apply_model_overrides` — without going through the CLI, plus the priority
order between an override and the ordinary routing table. `tests/test_config.py` already covers
plain `resolve_role` behaviour with no override in play; this file only adds override-specific
cases so the two suites don't duplicate each other.
"""

from __future__ import annotations

import pytest

from narrativewiki.config import (
    ConfigError,
    apply_model_overrides,
    load_settings,
    parse_model_override,
)


@pytest.fixture
def settings():
    """A fresh, unshared Settings per test -- overrides mutate it in place, and the module-scoped
    fixture other test files share must never see them leak in."""
    load_settings.cache_clear()
    s = load_settings("86")
    yield s
    load_settings.cache_clear()


# --- parse_model_override: the four accepted forms -------------------------


def test_role_only_targets_every_stage(settings):
    stage, adhoc, role = parse_model_override("vertex_flash", settings)
    assert stage == "*"
    assert adhoc is None
    assert role == "vertex_flash"


def test_stage_equals_role_targets_one_stage(settings):
    stage, adhoc, role = parse_model_override("claim_extract=mistral_fast", settings)
    assert stage == "claim_extract"
    assert adhoc is None
    assert role == "mistral_fast"


def test_provider_colon_model_targets_every_stage_adhoc(settings):
    stage, adhoc, role = parse_model_override("google:gemini-2.5-pro", settings)
    assert stage == "*"
    assert role is None
    assert adhoc is not None
    assert adhoc.provider == "google"
    assert adhoc.model == "gemini-2.5-pro"


def test_stage_equals_provider_colon_model_targets_one_stage_adhoc(settings):
    stage, adhoc, role = parse_model_override("prose=openai:some-new-model", settings)
    assert stage == "prose"
    assert role is None
    assert adhoc.provider == "openai"
    assert adhoc.model == "some-new-model"


def test_adhoc_clones_options_and_pricing_from_a_same_provider_profile(settings):
    """A bare model id carries no options/pricing/api_key/base_url -- those are provider-shaped
    (see llm/providers/*.py), so an ad-hoc override must inherit them from a real profile rather
    than starting from nothing. Stage "*" has no "current" profile to prefer, so this clones the
    first google profile declared in config/models.yaml (vertex_flash)."""
    vertex_flash = settings._build_profile("vertex_flash")  # noqa: SLF001 - test is in-family
    _, adhoc, _ = parse_model_override("google:some-new-model", settings)
    assert adhoc.options == vertex_flash.options
    assert adhoc.price_in == vertex_flash.price_in
    assert adhoc.price_out == vertex_flash.price_out
    # An ad-hoc Gemini id stays on Vertex and behind the paid-scope interlock (AI Studio retired).
    assert adhoc.use_vertex and adhoc.tier == "frontier" and adhoc.max_volumes == vertex_flash.max_volumes
    assert adhoc.model == "some-new-model"  # the one thing that must differ


def test_adhoc_prefers_the_stages_own_current_provider_when_it_matches(settings):
    """When a stage's OWN current role already uses the requested provider, an ad-hoc override
    for that stage should clone THAT profile's options, not just the first matching-provider
    profile declared in config/models.yaml. `prose` no longer routes directly to `openrouter_free`
    as of the routing history in config/models.yaml (it's fallback-only now) -- rather than couple
    this test to whichever stage happens to route to an `openai`-provider role today (config drifts
    over time; that coupling is exactly what silently made this test pass for the wrong reason
    before), point `prose`'s role at `openrouter_free` directly, in-memory, for this test only."""
    settings.models["routing"]["prose"] = {"role": "openrouter_free"}
    openrouter_free = settings._build_profile("openrouter_free")  # noqa: SLF001
    _, adhoc, _ = parse_model_override("prose=openai:some-new-model", settings)
    assert adhoc.options == openrouter_free.options


# --- error paths -------------------------------------------------------------


def test_unknown_stage_is_rejected(settings):
    with pytest.raises(ConfigError, match="Unknown stage"):
        parse_model_override("no_such_stage=mistral_fast", settings)


def test_unknown_role_is_rejected(settings):
    with pytest.raises(ConfigError, match="Unknown model role"):
        parse_model_override("claim_extract=no_such_role", settings)


def test_unknown_provider_is_rejected(settings):
    with pytest.raises(ConfigError, match="Unknown provider"):
        parse_model_override("prose=notaprovider:some-model", settings)


def test_missing_model_id_after_colon_is_rejected(settings):
    with pytest.raises(ConfigError, match="no model id"):
        parse_model_override("prose=google:", settings)


def test_empty_spec_after_equals_is_rejected(settings):
    with pytest.raises(ConfigError):
        parse_model_override("prose=", settings)


# --- apply_model_overrides + resolve_role priority --------------------------


def test_apply_sets_a_stage_specific_role_override(settings):
    apply_model_overrides(settings, ["claim_extract=vertex_pro"])
    assert settings.resolve_role("claim_extract").name == "vertex_pro"
    # An unrelated stage is untouched.
    assert settings.resolve_role("prose").name != "vertex_pro"


def test_apply_global_role_override_applies_to_every_stage(settings):
    apply_model_overrides(settings, ["vertex_flash"])
    for stage in settings.models["routing"]:
        assert settings.resolve_role(stage).name == "vertex_flash"


def test_stage_specific_override_wins_over_a_global_one(settings):
    apply_model_overrides(settings, ["vertex_flash", "claim_extract=mistral_fast"])
    assert settings.resolve_role("claim_extract").name == "mistral_fast"
    assert settings.resolve_role("prose").name == "vertex_flash"


def test_stage_specific_adhoc_wins_over_a_global_role_override(settings):
    apply_model_overrides(settings, ["vertex_flash", "prose=google:some-new-model"])
    assert str(settings.resolve_role("prose")) == "google:some-new-model"
    assert settings.resolve_role("arbitrate").name == "vertex_flash"


def test_override_bypasses_the_key_absent_fallback(settings, monkeypatch):
    """Normally a keyless `prose` role falls back to `vertex_flash` (config/models.yaml). An
    explicit --model override must be used as named instead -- the caller asked for this model
    specifically, so silently substituting a different one would be a worse surprise than the
    profile simply not working until its key is set."""
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    apply_model_overrides(settings, ["prose=mistral_fast"])
    resolved = settings.resolve_role("prose")
    assert resolved.name == "mistral_fast"  # not silently swapped to vertex_flash


def test_adhoc_override_warns_once_per_distinct_spec(settings):
    warnings_1 = apply_model_overrides(settings, ["prose=google:some-new-model"])
    assert len(warnings_1) == 1
    assert "ad-hoc override" in warnings_1[0]
    # Re-applying the identical spec (what `run-all` does once per stage command it chains)
    # must not warn again.
    warnings_2 = apply_model_overrides(settings, ["prose=google:some-new-model"])
    assert warnings_2 == []


def test_role_override_never_warns(settings):
    warnings = apply_model_overrides(settings, ["claim_extract=vertex_pro"])
    assert warnings == []


def test_no_overrides_is_a_no_op(settings):
    before = settings.resolve_role("claim_extract")
    apply_model_overrides(settings, None)
    apply_model_overrides(settings, [])
    assert settings.resolve_role("claim_extract") == before
