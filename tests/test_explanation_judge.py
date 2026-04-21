"""Tests for ExplanationJudge — parser + mock fallback."""

from __future__ import annotations

import pytest

from chakravyuh_env.explanation_judge import (
    ExplanationJudge,
    ExplanationScore,
    MockExplanationJudge,
    build_judge,
    parse_judge_response,
)


@pytest.mark.unit
def test_score_from_parts_clamps_to_valid_ranges():
    s = ExplanationScore.from_parts(0.5, 0.5, 0.5)  # each > max
    assert s.factual == 0.4
    assert s.interpretability == 0.3
    assert s.actionability == 0.3
    assert s.total == pytest.approx(1.0, rel=0.01)


@pytest.mark.unit
def test_score_from_parts_clamps_negatives_to_zero():
    s = ExplanationScore.from_parts(-0.1, -0.5, 0.2)
    assert s.factual == 0.0
    assert s.interpretability == 0.0
    assert s.actionability == 0.2
    assert s.total == 0.2


@pytest.mark.unit
def test_parse_judge_valid_json():
    raw = (
        '{"factual": 0.3, "interpretability": 0.25, "actionability": 0.2, '
        '"reason": "cites signals + concise"}'
    )
    s = parse_judge_response(raw)
    assert s.factual == 0.3
    assert s.interpretability == 0.25
    assert s.actionability == 0.2
    assert "cites" in s.reason


@pytest.mark.unit
def test_parse_judge_malformed_fallback_to_numbers():
    raw = "The scores are 0.4 / 0.2 / 0.15 — reasonable."
    s = parse_judge_response(raw)
    # Fallback extracts first 3 numbers
    assert s.factual == 0.4
    assert s.interpretability == 0.2
    assert s.actionability == 0.15


@pytest.mark.unit
def test_parse_judge_empty_returns_zero_score():
    s = parse_judge_response("")
    assert s.total == 0.0


@pytest.mark.unit
def test_mock_judge_rewards_factual_overlap():
    """Explanation that shares words with message gets higher factual score."""
    mock = MockExplanationJudge()
    msg = "SBI KYC expires today, share OTP to avoid block"
    good = "SBI KYC expiring — OTP ask is a classic impersonation scam"
    bad = "This looks perfectly legitimate, no concerns whatsoever!!!"
    s_good = mock.score(msg, good)
    s_bad = mock.score(msg, bad)
    assert s_good.factual > s_bad.factual


@pytest.mark.unit
def test_mock_judge_rewards_actionability():
    """Explanation mentioning 'call bank' gets higher actionability score."""
    mock = MockExplanationJudge()
    msg = "SBI KYC expires today, share OTP"
    with_action = "Scam. Do not share OTP — call bank to verify."
    without_action = "Seems suspicious due to urgency markers."
    s_with = mock.score(msg, with_action)
    s_without = mock.score(msg, without_action)
    assert s_with.actionability > s_without.actionability


@pytest.mark.unit
def test_mock_judge_penalizes_verbose():
    """Very long explanations score lower on interpretability."""
    mock = MockExplanationJudge()
    msg = "test"
    terse = "OTP scam, obvious."
    verbose = " ".join(["lorem ipsum"] * 40)  # ~80 words
    s_terse = mock.score(msg, terse)
    s_verbose = mock.score(msg, verbose)
    assert s_terse.interpretability >= s_verbose.interpretability


@pytest.mark.unit
def test_build_judge_returns_mock_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    judge = build_judge()
    assert isinstance(judge, MockExplanationJudge)


@pytest.mark.unit
def test_build_judge_mock_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "sk-dummy")
    judge = build_judge(mock=True)
    assert isinstance(judge, MockExplanationJudge)


@pytest.mark.unit
def test_explanation_judge_requires_api_key_at_use(monkeypatch):
    """Constructor should not fail without API key; use should."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    judge = ExplanationJudge()
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        judge.score("message", "explanation")
