"""Tests for LLMAnalyzer — prompt building + response parsing.

Model-loading paths aren't tested here (no GPU, no network). Those are
exercised on Day 2 via the Colab smoke run + dry-run integration.
"""

from __future__ import annotations

import pytest

from chakravyuh_env.agents.llm_analyzer import (
    LLMAnalyzer,
    MockLLMAnalyzer,
    parse_analyzer_response,
)
from chakravyuh_env.schemas import AnalyzerScore, ChatMessage, Observation


@pytest.mark.unit
def test_parse_valid_json_response():
    raw = '{"score": 0.87, "signals": ["urgency", "info_request"], "explanation": "OTP ask + urgency"}'
    score, signals, explanation = parse_analyzer_response(raw)
    assert score == 0.87
    assert "urgency" in signals
    assert "info_request" in signals
    assert "OTP" in explanation


@pytest.mark.unit
def test_parse_response_with_surrounding_text():
    raw = "Analysis:\n{\"score\": 0.5, \"signals\": [\"urgency\"], \"explanation\": \"meh\"}\nDone."
    score, signals, _ = parse_analyzer_response(raw)
    assert score == 0.5
    assert "urgency" in signals


@pytest.mark.unit
def test_parse_malformed_fallback_to_regex():
    raw = "score: 0.73 — detected urgency and info_request signals."
    score, signals, _ = parse_analyzer_response(raw)
    assert score == 0.73
    assert "urgency" in signals
    assert "info_request" in signals


@pytest.mark.unit
def test_parse_invalid_score_clamped_to_01():
    raw = '{"score": 1.5, "signals": [], "explanation": ""}'
    score, _, _ = parse_analyzer_response(raw)
    assert score == 1.0


@pytest.mark.unit
def test_parse_empty_response_returns_safe_defaults():
    score, signals, explanation = parse_analyzer_response("")
    assert score == 0.0
    assert signals == []
    assert isinstance(explanation, str)


@pytest.mark.unit
def test_parse_rejects_invalid_signal_names():
    raw = '{"score": 0.6, "signals": ["invalid_signal", "urgency"], "explanation": "x"}'
    _, signals, _ = parse_analyzer_response(raw)
    assert "invalid_signal" not in signals
    assert "urgency" in signals


@pytest.mark.unit
def test_mock_llm_analyzer_returns_analyzer_score():
    mock = MockLLMAnalyzer(fixed_score=0.77)
    obs = Observation(
        agent_role="analyzer",
        turn=1,
        chat_history=[ChatMessage(sender="scammer", turn=1, text="URGENT OTP")],
    )
    result = mock.act(obs)
    assert isinstance(result, AnalyzerScore)
    assert result.score == 0.77


@pytest.mark.unit
def test_mock_llm_analyzer_score_text_protocol():
    """Matches the AnalyzerProtocol used by Mode C runner."""
    mock = MockLLMAnalyzer(fixed_score=0.66)
    score = mock.score_text("test message")
    assert score == 0.66


@pytest.mark.unit
def test_llm_analyzer_build_prompt_includes_system_and_scammer_text():
    """Exercise prompt building without loading the model."""
    analyzer = LLMAnalyzer()  # lazy load — no model needed yet
    chat = [
        ChatMessage(sender="scammer", turn=1, text="Share your OTP urgently!"),
        ChatMessage(sender="victim", turn=2, text="Who are you?"),
    ]
    prompt = analyzer.build_prompt(chat)
    # Should contain the scammer message
    assert "Share your OTP" in prompt
    # Victim messages should NOT be in the analyzer prompt (scammer-only)
    assert "Who are you" not in prompt
    # System prompt contains the analyzer role language
    assert "Behavioral Analyzer" in prompt or "fraud" in prompt.lower()
