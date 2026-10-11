"""Phase 0: LLM cache keying, JSON recovery, and budget accounting.

These test the machinery every later stage depends on. The JSON recovery cases are drawn from
what small local models actually do wrong — fences, preamble, and trailing commentary.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from narrativewiki.config import Profile
from narrativewiki.llm.budget import Budget, BudgetExceeded, estimate_tokens
from narrativewiki.llm.cache import CachedResponse, LLMCache, make_key
from narrativewiki.llm.client import _parse_json


# --- cache keying ----------------------------------------------------------


def test_key_is_stable_across_option_ordering():
    """An unordered dict must not produce two keys for one logical request."""
    a = make_key("ollama", "m", "sys", "prompt", {"temperature": 0.1, "num_ctx": 8192})
    b = make_key("ollama", "m", "sys", "prompt", {"num_ctx": 8192, "temperature": 0.1})
    assert a == b


@pytest.mark.parametrize(
    "changed",
    [
        {"provider": "anthropic"},
        {"model": "other"},
        {"system": "different"},
        {"prompt": "different"},
        {"options": {"temperature": 0.9}},
    ],
)
def test_key_changes_when_anything_that_affects_the_answer_changes(changed):
    base = dict(
        provider="ollama", model="m", system="sys", prompt="p", options={"temperature": 0.1}
    )
    assert make_key(**base) != make_key(**{**base, **changed})


def test_flex_paygo_does_not_change_the_key():
    """Switching Vertex to Flex PayGo changes the queue, not the answer: every cached call must
    still hit, or turning it on would re-bill a whole series."""
    opts = {"temperature": 0.4, "thinking_budget": 0}
    assert make_key("google", "m", None, "p", opts) == make_key(
        "google", "m", None, "p", {**opts, "shared_request_type": "flex"})
    assert make_key("google", "m", None, "p", opts) == make_key(
        "google", "m", None, "p", {**opts, "flex_on_429": True})


def test_standard_429_retries_the_same_model_on_flex(monkeypatch):
    """[33] Maintainer 2026-10-01: Standard for speed; a 429 goes to Flex, never another model."""
    from types import SimpleNamespace
    from narrativewiki.config import Profile
    from narrativewiki.llm.providers import google as G
    seen = []

    def fake_client(profile, tier=None):
        def generate_content(model, contents, config):
            seen.append((tier, model))
            if tier is None:
                raise RuntimeError("429 RESOURCE_EXHAUSTED")
            return SimpleNamespace(text="ok", usage_metadata=None)
        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    monkeypatch.setattr(G, "_client", fake_client)
    prof = Profile(name="v", provider="google", model="gemini-x", use_vertex=True,
                   options={"flex_on_429": True})
    assert G.complete(prof, "p").text == "ok"
    assert seen == [(None, "gemini-x"), ("flex", "gemini-x")]


def test_cache_roundtrip_and_stats(tmp_path):
    cache = LLMCache(directory=tmp_path)
    key = make_key("ollama", "m", None, "p", {})

    assert cache.get(key) is None
    cache.put(key, CachedResponse("hello", 10, 5))

    hit = cache.get(key)
    assert hit is not None
    assert (hit.text, hit.in_tokens, hit.out_tokens) == ("hello", 10, 5)
    assert cache.hits == 1 and cache.misses == 1


def test_corrupt_cache_entry_is_a_miss_not_a_crash(tmp_path):
    """An interrupted write must not take down a multi-hour run on the next attempt."""
    cache = LLMCache(directory=tmp_path)
    key = make_key("ollama", "m", None, "p", {})
    path = tmp_path / key[:2] / f"{key}.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"text": "trunca', encoding="utf-8")

    assert cache.get(key) is None


def test_disabled_cache_never_reads_or_writes(tmp_path):
    cache = LLMCache(directory=tmp_path, enabled=False)
    key = make_key("ollama", "m", None, "p", {})
    cache.put(key, CachedResponse("x", 1, 1))
    assert cache.get(key) is None
    assert not list(tmp_path.rglob("*.json"))


# --- JSON recovery ---------------------------------------------------------


class Claim(BaseModel):
    subject: str
    confidence: float


@pytest.mark.parametrize(
    "raw",
    [
        '{"subject": "shin", "confidence": 0.9}',
        '```json\n{"subject": "shin", "confidence": 0.9}\n```',
        '```\n{"subject": "shin", "confidence": 0.9}\n```',
        'Here is the JSON:\n{"subject": "shin", "confidence": 0.9}',
        '{"subject": "shin", "confidence": 0.9}\n\nLet me know if you need more.',
    ],
)
def test_parse_json_recovers_from_common_model_mistakes(raw):
    assert Claim.model_validate(_parse_json(raw)).subject == "shin"


def test_parse_json_handles_a_bare_array():
    assert _parse_json('[{"a": 1}, {"a": 2}]') == [{"a": 1}, {"a": 2}]


@pytest.mark.parametrize("raw", ["", "   ", "I cannot help with that."])
def test_parse_json_raises_on_unrecoverable_output(raw):
    with pytest.raises(ValueError):
        _parse_json(raw)


def test_parse_json_salvages_complete_elements_from_a_truncated_array():
    """Observed against real Ollama output: a fact-dense prompt made the model loop, repeating
    the same elements until it hit num_predict mid-object. The elements before the cut are still
    complete and worth keeping rather than losing the entire response."""
    raw = (
        '{"facts": [\n'
        '  {"predicate": "AGE", "kind": "attribute", "value": "16"},\n'
        '  {"predicate": "AFFILIATED_WITH", "kind": "relation", "object": "Spearhead Squadron"},\n'
        '  {"predicate": "AFFILIATED_WITH", "kind": "rela'  # cut off mid-token
    )
    result = _parse_json(raw)
    assert result == {
        "facts": [
            {"predicate": "AGE", "kind": "attribute", "value": "16"},
            {"predicate": "AFFILIATED_WITH", "kind": "relation", "object": "Spearhead Squadron"},
        ]
    }


def test_parse_json_salvage_returns_nothing_usable_when_truncated_before_any_complete_element():
    with pytest.raises(ValueError):
        _parse_json('{"facts": [\n  {"predicate": "AGE", "kind": "attr')


def test_parse_json_salvage_ignores_nested_objects_when_finding_the_cut_point():
    """A nested object's closing brace must not be mistaken for the top-level element boundary
    -- the second (incomplete) array element here nests an "evidence" object of its own."""
    raw = (
        '{"facts": [\n'
        '  {"predicate": "AGE", "kind": "attribute", "value": "16"},\n'
        '  {"predicate": "AFFILIATED_WITH", "evidence": {"para_id": "v01:c00:p0001"}, "cut'
    )
    result = _parse_json(raw)
    assert result == {"facts": [{"predicate": "AGE", "kind": "attribute", "value": "16"}]}


# --- budget ----------------------------------------------------------------


LOCAL = Profile(name="local", provider="ollama", model="qwen", price_in=0.0, price_out=0.0)
PAID = Profile(name="paid", provider="anthropic", model="opus", price_in=5.0, price_out=25.0)


def test_local_calls_record_tokens_but_cost_nothing():
    budget = Budget()
    budget.record("claim_extract", LOCAL, 100_000, 20_000)
    assert budget.total_cost == 0.0
    assert budget.total_tokens == (100_000, 20_000)


def test_paid_calls_are_priced_per_million_tokens():
    budget = Budget()
    budget.record("prose_polish", PAID, 1_000_000, 100_000)
    assert budget.total_cost == pytest.approx(5.0 + 2.5)


def test_cached_calls_are_counted_but_not_charged():
    budget = Budget()
    budget.record("prose_polish", PAID, 1_000_000, 1_000_000, cached=True)
    assert budget.total_cost == 0.0
    assert budget.stages["prose_polish"].cached == 1


def test_hard_stop_raises_before_the_next_call():
    budget = Budget(warn_usd=1.0, hard_stop_usd=5.0)
    budget.check_before_call("prose_polish")  # nothing spent yet
    budget.record("prose_polish", PAID, 2_000_000, 0)  # $10
    with pytest.raises(BudgetExceeded, match="hard stop"):
        budget.check_before_call("prose_polish")


def test_warn_fires_exactly_once():
    budget = Budget(warn_usd=1.0, hard_stop_usd=100.0)
    budget.record("prose_polish", PAID, 1_000_000, 0)
    assert budget.should_warn() is True
    assert budget.should_warn() is False


def test_budget_survives_a_save_load_roundtrip(tmp_path):
    budget = Budget()
    budget.record("claim_extract", LOCAL, 500, 100)
    budget.record("prose_polish", PAID, 1_000, 200)
    budget.save(tmp_path / "budget.json")

    restored = Budget.load(tmp_path / "budget.json")
    assert restored.total_tokens == (1_500, 300)
    assert restored.total_cost == pytest.approx(budget.total_cost)


def test_accumulate_merges_another_runs_ledger_in():
    """Phase 10: the series-wide cumulative budget.json is built by accumulating each run's own
    ledger, not by sharing one Budget instance across runs -- this is the merge step."""
    cumulative = Budget()
    cumulative.record("claim_extract", LOCAL, 100, 20)

    this_run = Budget()
    this_run.record("claim_extract", LOCAL, 50, 10)
    this_run.record("prose", PAID, 1_000_000, 100_000)

    cumulative.accumulate(this_run)
    assert cumulative.total_tokens == (100 + 50 + 1_000_000, 20 + 10 + 100_000)
    assert cumulative.stages["claim_extract"].calls == 2  # 1 from before + 1 from this_run
    assert cumulative.total_cost == pytest.approx(this_run.total_cost)


def test_estimate_tokens_is_never_zero():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100


# --- Phase 10: the frontier-tier scope interlock ----------------------------
#
# The user's operating rule -- a frontier model must never be reachable outside a narrow,
# explicitly-scoped run -- implemented in LLMClient._enforce_frontier_scope, called on every
# cache MISS just before a profile would actually be contacted. These construct LLMClient
# directly against a minimal stub Settings (only `client_config`/`budget_config` are read by
# __init__) rather than a full loaded Settings, since none of this needs real routing/YAML.


class _StubSettings:
    client_config: dict = {}
    budget_config: dict = {}


class _StubRun:
    """Just enough of provenance.RunContext for _enforce_frontier_scope's call-count check."""

    def __init__(self, frontier_calls_so_far: int) -> None:
        self._count = frontier_calls_so_far

    def frontier_call_count(self) -> int:
        return self._count

    def attach_budget(self, budget) -> None:  # pragma: no cover - exercised via __init__
        self.budget = budget

    def log_call(self, record: dict) -> None:
        pass


FRONTIER = Profile(
    name="vertex_frontier", provider="google", model="gemini-2.5-pro",
    tier="frontier", max_volumes=2,
)


def test_frontier_profile_within_scope_does_not_raise():
    from narrativewiki.llm.client import LLMClient

    client = LLMClient(_StubSettings(), volume_scope=2)
    client._enforce_frontier_scope(FRONTIER)  # noqa: SLF001 - test is in-family; must not raise


def test_frontier_profile_beyond_max_volumes_raises():
    from narrativewiki.llm.client import FrontierScopeExceeded, LLMClient

    client = LLMClient(_StubSettings(), volume_scope=5)
    with pytest.raises(FrontierScopeExceeded, match="capped at 2 volume"):
        client._enforce_frontier_scope(FRONTIER)  # noqa: SLF001


def test_frontier_profile_at_call_count_limit_raises():
    from narrativewiki.llm.client import FrontierScopeExceeded, LLMClient

    capped = Profile(
        name="vertex_frontier", provider="google", model="g", tier="frontier", max_calls_per_run=3,
    )
    client = LLMClient(_StubSettings(), run=_StubRun(3))
    with pytest.raises(FrontierScopeExceeded, match="already made 3"):
        client._enforce_frontier_scope(capped)  # noqa: SLF001


def test_frontier_profile_under_call_count_limit_does_not_raise():
    from narrativewiki.llm.client import LLMClient

    capped = Profile(
        name="vertex_frontier", provider="google", model="g", tier="frontier", max_calls_per_run=3,
    )
    client = LLMClient(_StubSettings(), run=_StubRun(2))
    client._enforce_frontier_scope(capped)  # noqa: SLF001 - must not raise


def test_standard_tier_profile_is_never_scope_checked():
    """A non-frontier profile with volume_scope wildly out of any hypothetical range must never
    be blocked -- the interlock in _call only fires when profile.tier == 'frontier'."""
    from narrativewiki.llm.client import LLMClient

    client = LLMClient(_StubSettings(), volume_scope=999)
    client._enforce_frontier_scope(LOCAL)  # noqa: SLF001 - LOCAL is tier="standard" by default


def test_call_on_a_cache_hit_bypasses_the_frontier_interlock_entirely(tmp_path):
    """A cache hit costs no money and reveals no new spend, so it must never be blocked -- even
    for a frontier profile whose volume_scope is far outside its configured max_volumes."""
    from narrativewiki.llm.client import LLMClient

    cache = LLMCache(directory=tmp_path / "cache")
    merged_options = {**FRONTIER.options, "_json": False}
    key = make_key(FRONTIER.provider, FRONTIER.model, None, "hello", merged_options)
    cache.put(key, CachedResponse("cached answer", 10, 5))

    client = LLMClient(_StubSettings(), cache=cache, volume_scope=99)
    completion = client._call("outline", FRONTIER, "hello", None, False, None)  # noqa: SLF001
    assert completion.text == "cached answer"


def test_call_on_a_cache_miss_beyond_scope_raises_before_touching_any_provider(tmp_path):
    """No provider is ever contacted for a scope violation -- FrontierScopeExceeded is raised
    from inside _call before `_PROVIDERS.get(profile.provider)` is even reached."""
    from narrativewiki.llm.client import FrontierScopeExceeded, LLMClient

    cache = LLMCache(directory=tmp_path / "cache")
    client = LLMClient(_StubSettings(), cache=cache, volume_scope=5)
    with pytest.raises(FrontierScopeExceeded):
        client._call("outline", FRONTIER, "a genuinely new prompt", None, False, None)  # noqa: SLF001


# --- Phase 10: run-scoped provenance logging --------------------------------


def test_client_attaches_its_budget_to_the_run_on_construction():
    from narrativewiki.llm.client import LLMClient

    run = _StubRun(0)
    client = LLMClient(_StubSettings(), run=run)
    assert run.budget is client.budget


def test_call_logs_a_cache_hit_to_the_run(tmp_path, monkeypatch):
    from narrativewiki import paths, provenance
    from narrativewiki.llm.client import LLMClient

    monkeypatch.setattr(paths, "RUNS_DIR", tmp_path / "_runs")
    run = provenance.start_run("86", "synthesize", scope="upto1")

    cache = LLMCache(directory=tmp_path / "cache")
    merged_options = {**LOCAL.options, "_json": False}
    key = make_key(LOCAL.provider, LOCAL.model, "sys", "prompt text", merged_options)
    cache.put(key, CachedResponse("resp", 10, 5))

    client = LLMClient(_StubSettings(), cache=cache, run=run)
    client._call("prose", LOCAL, "prompt text", "sys", False, None)  # noqa: SLF001

    records = provenance.read_calls(run.run_id)
    assert len(records) == 1
    assert records[0]["cache_hit"] is True
    assert records[0]["prompt"] == "prompt text"
    assert records[0]["stage"] == "prose"
    assert records[0]["tier"] == "standard"


def test_call_without_a_run_never_touches_calls_jsonl(tmp_path):
    """Every pre-Phase-10 direct construction (run=None, the default) must behave exactly as
    before -- no calls.jsonl, no crash, nothing new to clean up."""
    from narrativewiki.llm.client import LLMClient

    cache = LLMCache(directory=tmp_path / "cache")
    merged_options = {**LOCAL.options, "_json": False}
    key = make_key(LOCAL.provider, LOCAL.model, None, "p", merged_options)
    cache.put(key, CachedResponse("resp", 10, 5))

    client = LLMClient(_StubSettings(), cache=cache)  # run defaults to None
    completion = client._call("prose", LOCAL, "p", None, False, None)  # noqa: SLF001
    assert completion.text == "resp"


# --- Phase 17: embeddings (value canonicalization) --------------------------


class _FakeHttpResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_ollama_embed_posts_a_batch_to_api_embed(monkeypatch):
    from narrativewiki.llm.providers import ollama as ollama_provider

    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeHttpResponse(200, {"embeddings": [[0.1, 0.2], [0.3, 0.4]], "prompt_eval_count": 12})

    monkeypatch.setattr(ollama_provider.httpx, "post", fake_post)
    profile = Profile(name="embed", provider="ollama", model="bge-m3", base_url="http://localhost:11434")

    result = ollama_provider.embed(profile, ["hello", "world"])
    assert captured["url"] == "http://localhost:11434/api/embed"
    assert captured["json"] == {"model": "bge-m3", "input": ["hello", "world"]}
    assert result.vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert result.in_tokens == 12


def test_ollama_embed_raises_provider_error_on_missing_model(monkeypatch):
    from narrativewiki.llm.providers import ollama as ollama_provider
    from narrativewiki.llm.providers.base import ProviderError

    monkeypatch.setattr(ollama_provider.httpx, "post", lambda url, json, timeout: _FakeHttpResponse(404, {}))
    profile = Profile(name="embed", provider="ollama", model="bge-m3", base_url="http://localhost:11434")
    with pytest.raises(ProviderError, match="bge-m3"):
        ollama_provider.embed(profile, ["hello"])


class _StubEmbedSettings:
    client_config: dict = {}
    budget_config: dict = {}

    def resolve_role(self, stage):
        assert stage == "canonicalize"
        return Profile(name="embed", provider="ollama", model="bge-m3", price_in=0.0, price_out=0.0)


def test_llm_client_embed_caches_per_text_and_only_batches_misses(tmp_path, monkeypatch):
    from narrativewiki.llm import client as client_module
    from narrativewiki.llm.client import LLMClient
    from narrativewiki.llm.providers.base import Embedding

    calls: list[list[str]] = []

    def fake_embed(profile, texts, timeout=300.0):
        calls.append(list(texts))
        return Embedding(vectors=[[float(len(t)), 0.0] for t in texts], in_tokens=len(texts) * 2)

    monkeypatch.setattr(client_module.ollama_provider, "embed", fake_embed)

    cache = LLMCache(directory=tmp_path / "cache")
    client = LLMClient(_StubEmbedSettings(), cache=cache)

    vectors = client.embed("canonicalize", ["ab", "abc"])
    assert vectors == [[2.0, 0.0], [3.0, 0.0]]
    assert calls == [["ab", "abc"]]

    # A repeat text hits the cache; only the new text is sent to the provider.
    vectors2 = client.embed("canonicalize", ["ab", "xyz"])
    assert vectors2[0] == [2.0, 0.0]
    assert calls[-1] == ["xyz"]


def test_llm_client_embed_returns_empty_list_for_no_texts():
    from narrativewiki.llm.client import LLMClient

    client = LLMClient(_StubEmbedSettings())
    assert client.embed("canonicalize", []) == []


def test_llm_client_embed_raises_for_a_provider_with_no_embed_support():
    from narrativewiki.llm.client import LLMClient, LLMError

    class _NoEmbedSettings:
        client_config: dict = {}
        budget_config: dict = {}

        def resolve_role(self, stage):
            return Profile(name="paid", provider="anthropic", model="opus")

    client = LLMClient(_NoEmbedSettings())
    with pytest.raises(LLMError):
        client.embed("canonicalize", ["hello"])


# --- Phase 23 D1: `num_predict` (Ollama vocabulary) must not be silently dropped by a
# non-Ollama provider. extract/claims.py and extract/scenes.py hardcode
# {"num_predict": N, "repeat_penalty": 1.3} call options regardless of which provider a stage is
# routed to -- confirmed against a live run's calls.jsonl that this silently capped a
# num_predict=8192 chapter-span "detail" call at google_fast's profile default of
# max_output_tokens=1024 (0 of 112 detail responses carried a participant_facts list at all).
# One test per non-Ollama provider: the call-site's num_predict must win over the profile's own
# default, but an explicit provider-native override at the call site must still win over
# num_predict.


class _FakeGoogleResponse:
    def __init__(self, text: str):
        self.text = text
        self.usage_metadata = type(
            "Usage", (), {"prompt_token_count": 10, "candidates_token_count": 5}
        )()


def test_google_complete_uses_num_predict_when_profile_caps_lower(monkeypatch):
    from narrativewiki.llm.providers import google as google_provider

    captured = {}

    class _FakeModels:
        def generate_content(self, model, contents, config):
            captured["model"] = model
            captured["config"] = config
            return _FakeGoogleResponse("ok")

    class _FakeClient:
        models = _FakeModels()

    monkeypatch.setattr(google_provider, "_client", lambda profile, tier=None: _FakeClient())
    profile = Profile(
        name="google_fast", provider="google", model="gemini-flash-lite-latest",
        options={"max_output_tokens": 1024, "temperature": 0.1},
    )

    google_provider.complete(profile, "prompt", options={"num_predict": 8192, "repeat_penalty": 1.3})
    assert captured["config"]["max_output_tokens"] == 8192


def test_google_complete_lets_explicit_call_site_override_win_over_num_predict(monkeypatch):
    from narrativewiki.llm.providers import google as google_provider

    captured = {}

    class _FakeModels:
        def generate_content(self, model, contents, config):
            captured["config"] = config
            return _FakeGoogleResponse("ok")

    class _FakeClient:
        models = _FakeModels()

    monkeypatch.setattr(google_provider, "_client", lambda profile, tier=None: _FakeClient())
    profile = Profile(
        name="google_fast", provider="google", model="gemini-flash-lite-latest",
        options={"max_output_tokens": 1024},
    )

    google_provider.complete(
        profile, "prompt", options={"num_predict": 8192, "max_output_tokens": 2048}
    )
    assert captured["config"]["max_output_tokens"] == 2048


def test_openai_complete_uses_num_predict_when_profile_caps_lower(monkeypatch):
    from narrativewiki.llm.providers import openai as openai_provider

    captured = {}

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

    def fake_post(url, json, timeout, headers):
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(openai_provider.httpx, "post", fake_post)
    profile = Profile(
        name="openrouter_free", provider="openai", model="m", api_key="k",
        base_url="http://x", options={"max_tokens": 1024},
    )

    openai_provider.complete(profile, "prompt", options={"num_predict": 8192})
    assert captured["json"]["max_tokens"] == 8192


def test_anthropic_complete_uses_num_predict_when_profile_caps_lower(monkeypatch):
    from narrativewiki.llm.providers import anthropic as anthropic_provider

    captured = {}

    class _FakeBlock:
        type = "text"
        text = "ok"

    class _FakeUsage:
        input_tokens = 10
        output_tokens = 5

    class _FakeResponse:
        content = [_FakeBlock()]
        usage = _FakeUsage()

    class _FakeMessages:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return _FakeResponse()

    class _FakeClient:
        def with_options(self, timeout):
            return self

        messages = _FakeMessages()

    monkeypatch.setattr(anthropic_provider, "_client", lambda profile: _FakeClient())
    profile = Profile(
        name="local_best", provider="anthropic", model="claude", options={"max_tokens": 2048}
    )

    anthropic_provider.complete(profile, "prompt", options={"num_predict": 8192})
    assert captured["kwargs"]["max_tokens"] == 8192


# --- Phase 27: the spend ceiling that does not reset between runs --------------------------


def test_lifetime_cap_counts_spend_from_previous_runs(tmp_path):
    """`hard_stop_usd` is per-run and resets on every process start, so a SEQUENCE of runs is
    unbounded by it -- the realistic way a bill runs away is many re-runs each individually
    under the ceiling. This is the limit that survives "just run it once more"."""
    from narrativewiki.llm.budget import Budget, BudgetExceeded, StageLedger

    spent = Budget()
    spent.stages["claim_extract"] = StageLedger(stage="claim_extract", cost_usd=9.0)
    ledger = tmp_path / "budget.json"
    spent.save(ledger)

    # a NEW run, its own ledger empty, well under the per-run hard stop
    fresh = Budget(hard_stop_usd=25.0, lifetime_cap_usd=10.0,
                   already_spent_usd=Budget.load(ledger).total_cost)
    fresh.check_before_call("claim_extract")          # $9 of $10 -- still allowed
    fresh.stages["claim_extract"] = StageLedger(stage="claim_extract", cost_usd=1.5)
    with pytest.raises(BudgetExceeded) as exc:
        fresh.check_before_call("claim_extract")      # $10.50 lifetime, though only $1.50 this run
    assert "does NOT reset" in str(exc.value)
    assert "lifetime cap" in str(exc.value)


def test_lifetime_cap_unset_changes_nothing(tmp_path):
    """Default off: an existing deployment must behave exactly as before."""
    from narrativewiki.llm.budget import Budget, StageLedger

    b = Budget(hard_stop_usd=25.0)                    # no lifetime_cap_usd
    b.stages["prose"] = StageLedger(stage="prose", cost_usd=1000.0)
    b.already_spent_usd = 1000.0
    with pytest.raises(Exception):
        b.check_before_call("prose")                  # still stops -- on the per-run rule
    assert b.lifetime_cap_usd is None


# --- rate limiting (2026-09-23) --------------------------------------------
#
# A 429 is "not yet", not a failure. Vertex's shared quota answered one for minutes at a time
# under a parallel stage, and the old single 3-attempt/14-second ladder crashed `wiki scenes`
# mid-volume twice, so throttling now has its own retry budget and its own longer waits.


class _LocalRoutingSettings:
    """Enough Settings for LLMClient.complete: one local profile for every stage."""

    client_config: dict = {}
    budget_config: dict = {}

    def __init__(self, client_config: dict) -> None:
        self.client_config = client_config

    def resolve_role(self, stage: str) -> Profile:
        return Profile(name="local_fast", provider="ollama", model="m")


def _retry_client(tmp_path, cfg: dict):
    from narrativewiki.llm.client import LLMClient

    return LLMClient(
        _LocalRoutingSettings({**cfg, "cache_dir": str(tmp_path)}),
        cache=LLMCache(directory=tmp_path),
    )


def test_a_429_retries_on_its_own_longer_ladder(tmp_path, monkeypatch):
    from narrativewiki.llm.providers.base import Completion, ProviderError

    calls = {"n": 0}
    slept: list[float] = []

    def flaky(profile, prompt, system=None, json_mode=False, timeout=300.0, options=None):
        calls["n"] += 1
        if calls["n"] <= 4:
            raise ProviderError("429 RESOURCE_EXHAUSTED: Resource exhausted, try again later.")
        return Completion("ok", 1, 1)

    client = _retry_client(tmp_path, {"max_retries": 1, "rate_limit_retries": 8,
                                      "rate_limit_backoff_seconds": 0.01,
                                      "retry_backoff_seconds": 0.01})
    monkeypatch.setattr("narrativewiki.llm.client.time.sleep", lambda s: slept.append(s))
    monkeypatch.setattr("narrativewiki.llm.providers.ollama.complete", flaky)

    assert client.complete("prose", "hi") == "ok"
    assert calls["n"] == 5                                      # 4 throttled attempts, then ok
    # [33] Doubling per 429, jittered +-20%: 0.01, 0.02, 0.04, 0.08.
    for got, base in zip(slept, [0.01, 0.02, 0.04, 0.08], strict=True):
        assert 0.8 * base <= got <= 1.2 * base


def test_a_non_rate_limit_failure_still_stops_at_max_retries(tmp_path, monkeypatch):
    """The long ladder is only for 429s -- an ordinary error must not get eight tries."""
    from narrativewiki.llm.client import LLMError
    from narrativewiki.llm.providers.base import ProviderError

    calls = {"n": 0}

    def broken(profile, prompt, system=None, json_mode=False, timeout=300.0, options=None):
        calls["n"] += 1
        raise ProviderError("connection reset")

    client = _retry_client(tmp_path, {"max_retries": 2, "rate_limit_retries": 8,
                                      "rate_limit_backoff_seconds": 0.01,
                                      "retry_backoff_seconds": 0.01})
    monkeypatch.setattr("narrativewiki.llm.client.time.sleep", lambda s: None)
    monkeypatch.setattr("narrativewiki.llm.providers.ollama.complete", broken)

    with pytest.raises(LLMError, match="connection reset"):
        client.complete("prose", "hi")
    assert calls["n"] == 3                                      # first attempt plus max_retries


def test_cache_only_mode_refuses_a_miss_and_still_serves_a_hit(tmp_path, monkeypatch):
    """[30] Replaying a stage over stored responses must never bill: a miss raises before any
    provider is looked up, while a hit is served as usual."""
    from narrativewiki.llm.client import LLMClient, LLMError

    monkeypatch.setenv("NARRATIVEWIKI_CACHE_ONLY", "1")
    cache = LLMCache(directory=tmp_path / "cache")
    key = make_key(LOCAL.provider, LOCAL.model, None, "hello", {**LOCAL.options, "_json": False})
    cache.put(key, CachedResponse("cached answer", 10, 5))
    client = LLMClient(_StubSettings(), cache=cache)

    assert client._call("prose", LOCAL, "hello", None, False, None).text == "cached answer"  # noqa: SLF001
    with pytest.raises(LLMError, match="CACHE_ONLY"):
        client._call("prose", LOCAL, "a new prompt", None, False, None)  # noqa: SLF001


def test_a_content_block_goes_to_the_next_rung_once_and_is_not_retried(tmp_path, monkeypatch):
    """[30] Gemini's PROHIBITED_CONTENT filter blocked a harmless Bookworm passage; the whole
    extract stage failed after four identical retries. Now one attempt, then the next rung."""
    from types import SimpleNamespace
    from narrativewiki.llm import client as client_mod
    from narrativewiki.llm.providers.base import Completion, ContentBlocked

    calls = []

    def blocked(profile, prompt, **_):
        calls.append(profile.name)
        raise ContentBlocked("blocked")

    def answers(profile, prompt, **_):
        calls.append(profile.name)
        return Completion("ok", 1, 1)

    monkeypatch.setitem(client_mod._PROVIDERS, "google", SimpleNamespace(complete=blocked))
    monkeypatch.setitem(client_mod._PROVIDERS, "ollama", SimpleNamespace(complete=answers))
    primary = Profile(name="vertex", provider="google", model="m")
    rung = Profile(name="local", provider="ollama", model="q")

    class Settings(_StubSettings):
        client_config = {"content_block_fallback": True}  # [33] opt-in since the same-model rule

        def fallbacks_after(self, stage, profile):
            return [rung] if profile.name == "vertex" else []

    client = client_mod.LLMClient(Settings(), cache=LLMCache(directory=tmp_path / "c"))
    assert client._call("claim_extract", primary, "p", None, True, None).text == "ok"  # noqa: SLF001
    assert calls == ["vertex", "local"]


def test_a_content_block_is_never_answered_by_another_model_by_default(tmp_path, monkeypatch):
    """[33] Same model for every compared number: a refused passage yields the schema's empty
    answer (no facts), and the next rung is never called."""
    from types import SimpleNamespace
    from narrativewiki.extract.schema import ExtractionResult
    from narrativewiki.llm import client as client_mod
    from narrativewiki.llm.providers.base import ContentBlocked

    calls = []

    def blocked(profile, prompt, **_):
        calls.append(profile.name)
        raise ContentBlocked("blocked")

    monkeypatch.setitem(client_mod._PROVIDERS, "google", SimpleNamespace(complete=blocked))
    monkeypatch.setitem(client_mod._PROVIDERS, "ollama", SimpleNamespace(complete=lambda *a, **k: 1 / 0))
    primary = Profile(name="vertex", provider="google", model="m")

    class Settings(_StubSettings):
        def fallbacks_after(self, stage, profile):
            return [Profile(name="local", provider="ollama", model="q")]

        def resolve_role(self, stage):
            return primary

    client = client_mod.LLMClient(Settings(), cache=LLMCache(directory=tmp_path / "c"))
    assert client.complete_json("claim_extract", "p", ExtractionResult).facts == []
    assert calls == ["vertex"]
    with pytest.raises(client_mod.ContentRefused):
        client.complete("claim_extract", "p")


def test_one_unencodable_text_does_not_fail_its_embed_batch(tmp_path, monkeypatch):
    """[30] bge-m3 returned NaN for one Bookworm motivation; the batch failed and canonicalization
    switched off for the rest of the graph build. Now the batch retries text by text."""
    from types import SimpleNamespace
    from narrativewiki.llm import client as client_mod
    from narrativewiki.llm.providers.base import ProviderError

    def embed(profile, texts, timeout=None):
        if "bard" in " ".join(texts):
            raise ProviderError("Ollama returned 500: unsupported value: NaN")
        return SimpleNamespace(vectors=[[1.0, 0.0] for _ in texts], in_tokens=len(texts))

    monkeypatch.setitem(client_mod._PROVIDERS, "ollama", SimpleNamespace(embed=embed))
    profile = Profile(name="embed", provider="ollama", model="bge-m3")

    class Settings(_StubSettings):
        def resolve_role(self, stage):
            return profile

    client = client_mod.LLMClient(Settings(), cache=LLMCache(directory=tmp_path / "c"))
    assert client.embed("canonicalize", ["a merchant", "or a bard", "an apprentice"]) == [
        [1.0, 0.0], None, [1.0, 0.0]]
    # Every other text now a cache hit: the lone NaN miss must still not raise.
    assert client.embed("canonicalize", ["a merchant", "or a bard"]) == [[1.0, 0.0], None]


def test_the_lifetime_cap_counts_every_series_ledger(tmp_path, monkeypatch):
    """[30] The cap seeded from data/cache/llm/budget.json, which nothing writes since ledgers went
    per-series: every process started the $20 cap at $0 while $12.79 had been spent."""
    from narrativewiki import paths
    from narrativewiki.llm.budget import lifetime_spent
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    for series, tokens in (("a", 1_000_000), ("b", 2_000_000)):
        b = Budget()
        b.record("extract", PAID, in_tokens=tokens, out_tokens=0)
        (tmp_path / "data" / series).mkdir(parents=True)
        b.save(tmp_path / "data" / series / "budget.json")
    assert lifetime_spent() == pytest.approx(3 * 5.0)  # PAID: $5 per million input tokens


def test_a_quote_copied_with_its_inner_quotes_is_repaired_not_resent():
    """[33] 3.6 Flash copied `"...Anne"—"I don't want to die."` into a JSON string unescaped; a
    deterministic re-ask reproduced it. The parser escapes the stray quotes itself."""
    from narrativewiki.llm.client import _parse_json

    bad = '{"quotes": [{"quote": "And, oh, Anne"\u2014"I don\'t want to die.", "para_id": "v03:c14:p0011"}], "n": 1}'
    assert _parse_json(bad) == {"quotes": [{"quote": 'And, oh, Anne"\u2014"I don\'t want to die.',
                                            "para_id": "v03:c14:p0011"}], "n": 1}


def test_unparsable_json_names_the_position_for_the_repair_prompt():
    from narrativewiki.llm.client import _parse_json

    with pytest.raises(ValueError, match=r"invalid JSON at character \d+"):
        _parse_json('{"a": [1, 2,, 3]}')
