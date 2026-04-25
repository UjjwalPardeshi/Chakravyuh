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


# ---------------------------------------------------------------------------
# C.7 — Adversarial cases (per WIN_PLAN.md P1.7)
#
# These pin the four explicit thresholds from the plan: an empty explanation
# scores < 0.2, a 3-word boilerplate < 0.4, a 2000-char garbage explanation
# < 0.5, and a signal-grounded explanation > 0.7. They run against the mock
# (deterministic, CI-friendly). When GROQ_API_KEY is set, the live judge is
# also exercised in `test_live_judge_*` (skipped otherwise).
# ---------------------------------------------------------------------------


_ADVERSARIAL_MSG = (
    "URGENT: Share OTP for SBI bank verification — pressure + impersonation"
)


@pytest.mark.unit
def test_judge_rejects_empty():
    """Adversarial 1: empty explanation must score < 0.2."""
    judge = MockExplanationJudge()
    score = judge.score(_ADVERSARIAL_MSG, "")
    assert score.total < 0.2, f"empty explanation got total={score.total:.3f}"


@pytest.mark.unit
def test_judge_rejects_boilerplate():
    """Adversarial 2: 3-word boilerplate must score < 0.4."""
    judge = MockExplanationJudge()
    score = judge.score(_ADVERSARIAL_MSG, "This is suspicious.")
    assert score.total < 0.4, f"boilerplate got total={score.total:.3f}"


@pytest.mark.unit
def test_judge_rejects_over_long():
    """Adversarial 3: 2000-char garbage explanation must score < 0.5."""
    judge = MockExplanationJudge()
    score = judge.score(_ADVERSARIAL_MSG, "x" * 2000)
    assert score.total < 0.5, f"over-long got total={score.total:.3f}"


@pytest.mark.unit
def test_judge_accepts_signal_grounded():
    """Adversarial 4: a signal-grounded explanation must score > 0.7."""
    judge = MockExplanationJudge()
    grounded = (
        "Do not share OTP. SBI bank impersonation with urgency pressure — "
        "classic OTP-theft scam."
    )
    score = judge.score(_ADVERSARIAL_MSG, grounded)
    assert score.total > 0.7, f"signal-grounded got total={score.total:.3f}"


# ---- live judge variants (only when GROQ_API_KEY is configured) -------------


@pytest.mark.skipif(
    not __import__("os").getenv("GROQ_API_KEY"),
    reason="live judge requires GROQ_API_KEY",
)
@pytest.mark.integration
def test_live_judge_rejects_empty():
    judge = ExplanationJudge()
    assert judge.score(_ADVERSARIAL_MSG, "").total < 0.2


@pytest.mark.skipif(
    not __import__("os").getenv("GROQ_API_KEY"),
    reason="live judge requires GROQ_API_KEY",
)
@pytest.mark.integration
def test_live_judge_accepts_signal_grounded():
    judge = ExplanationJudge()
    grounded = (
        "Do not share OTP. SBI bank impersonation with urgency pressure — "
        "classic OTP-theft scam."
    )
    assert judge.score(_ADVERSARIAL_MSG, grounded).total > 0.7
