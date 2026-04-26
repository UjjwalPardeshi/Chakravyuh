"""Tests for the frontier baseline runner.

We don't actually hit any provider APIs in tests — we verify:
  - Parse function works
  - Provider registry is complete
  - Providers gracefully report unavailable when keys are missing
  - Comparison output structure is correct
"""

from __future__ import annotations

import pytest

from eval.frontier_baseline import (
    PROVIDER_REGISTRY,
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    HuggingFaceProvider,
    OpenAIProvider,
    _build_provider_lineup,
    parse_frontier_score,
)


@pytest.mark.unit
def test_all_five_providers_registered():
    assert "openai" in PROVIDER_REGISTRY
    assert "groq" in PROVIDER_REGISTRY
    assert "hf" in PROVIDER_REGISTRY
    assert "anthropic" in PROVIDER_REGISTRY
    assert "gemini" in PROVIDER_REGISTRY


@pytest.mark.unit
def test_parse_frontier_score_valid_json():
    raw = '{"score": 0.74, "explanation": "OTP ask + urgency"}'
    assert parse_frontier_score(raw) == 0.74


@pytest.mark.unit
def test_parse_frontier_score_clamped():
    assert parse_frontier_score('{"score": 2.0}') == 1.0
    assert parse_frontier_score('{"score": -0.5}') == 0.0


@pytest.mark.unit
def test_parse_frontier_score_regex_fallback():
    raw = "The score for this message is score: 0.64 because..."
    assert parse_frontier_score(raw) == 0.64


@pytest.mark.unit
def test_parse_frontier_score_empty_returns_zero():
    assert parse_frontier_score("") == 0.0
    assert parse_frontier_score("totally unstructured response") == 0.0


@pytest.mark.unit
def test_openai_provider_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = OpenAIProvider()
    assert p.available() is False


@pytest.mark.unit
def test_groq_provider_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    p = GroqProvider()
    assert p.available() is False


@pytest.mark.unit
def test_anthropic_provider_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = AnthropicProvider()
    assert p.available() is False


@pytest.mark.unit
def test_gemini_provider_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = GeminiProvider()
    assert p.available() is False


@pytest.mark.unit
def test_provider_spec_has_name():
    for name, cls in PROVIDER_REGISTRY.items():
        p = cls()
        assert p.spec.name  # non-empty


@pytest.mark.unit
def test_hf_provider_unavailable_without_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    p = HuggingFaceProvider()
    assert p.available() is False


@pytest.mark.unit
def test_hf_provider_default_model_id():
    p = HuggingFaceProvider()
    assert p._model == "meta-llama/Llama-3.3-70B-Instruct"
    assert p.spec.name == "hf-llama-3.3-70b-instruct"


@pytest.mark.unit
def test_hf_provider_custom_model_id():
    p = HuggingFaceProvider(model="Qwen/Qwen3-72B-Instruct")
    assert p._model == "Qwen/Qwen3-72B-Instruct"
    assert p.spec.name == "hf-qwen3-72b-instruct"


@pytest.mark.unit
def test_hf_provider_pinned_provider_suffix_strips_for_display():
    """`model:provider` pin syntax keeps the API call pinned but strips the suffix
    from the display name so the CSV column stays human-readable."""
    p = HuggingFaceProvider(model="meta-llama/Llama-3.1-405B-Instruct:together")
    assert p._model == "meta-llama/Llama-3.1-405B-Instruct:together"
    assert p.spec.name == "hf-llama-3.1-405b-instruct"


@pytest.mark.unit
def test_build_lineup_always_starts_with_scripted():
    lineup = _build_provider_lineup(["groq"])
    assert lineup[0] == ("scripted", "scripted")


@pytest.mark.unit
def test_build_lineup_dedupes_repeated_providers():
    lineup = _build_provider_lineup(["scripted", "groq", "groq", "openai"])
    names = [n for n, _ in lineup]
    assert names == ["scripted", "groq", "openai"]


@pytest.mark.unit
def test_build_lineup_skips_unknown_provider():
    lineup = _build_provider_lineup(["groq", "totally-bogus"])
    names = [n for n, _ in lineup]
    assert "totally-bogus" not in names


@pytest.mark.unit
def test_build_lineup_hf_default_single_instance():
    """Without --hf-models, the `hf` token in --providers yields one default instance."""
    lineup = _build_provider_lineup(["hf"])
    assert len(lineup) == 2  # scripted + one hf
    name, inst = lineup[1]
    assert name == "hf"
    assert isinstance(inst, HuggingFaceProvider)
    assert inst._model == HuggingFaceProvider.DEFAULT_MODEL


@pytest.mark.unit
def test_build_lineup_hf_models_expands_to_one_instance_per_model():
    models = [
        "meta-llama/Llama-3.3-70B-Instruct",
        "Qwen/Qwen3-72B-Instruct",
        "deepseek-ai/DeepSeek-V3-0324",
    ]
    lineup = _build_provider_lineup(["hf"], hf_models=models)
    # scripted + 3 hf instances
    assert len(lineup) == 1 + len(models)
    hf_entries = lineup[1:]
    seen_models = []
    for name, inst in hf_entries:
        assert isinstance(inst, HuggingFaceProvider)
        assert name.startswith("hf-")
        seen_models.append(inst._model)
    assert seen_models == models


@pytest.mark.unit
def test_build_lineup_hf_models_ignored_when_hf_not_in_providers():
    """If user passes --hf-models but doesn't include 'hf' in providers, it's a no-op."""
    lineup = _build_provider_lineup(
        ["groq"], hf_models=["meta-llama/Llama-3.3-70B-Instruct"]
    )
    names = [n for n, _ in lineup]
    assert "hf" not in names
    assert not any(n.startswith("hf-") for n in names)
    assert "groq" in names
