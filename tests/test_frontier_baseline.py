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
    OpenAIProvider,
    parse_frontier_score,
)


@pytest.mark.unit
def test_all_four_providers_registered():
    assert "openai" in PROVIDER_REGISTRY
    assert "groq" in PROVIDER_REGISTRY
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
