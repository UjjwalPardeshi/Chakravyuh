"""Tests for GRPO reward function + training-example builder.

The reward function is pure (no model/API); fully testable.
"""

from __future__ import annotations

import pytest

from chakravyuh_env.explanation_judge import MockExplanationJudge
from training.grpo_analyzer import (
    TrainingExample,
    build_training_examples,
    compute_reward,
)


# ---- Reward function tests ----


@pytest.mark.unit
def test_reward_rewards_correct_scam_detection():
    """Good JSON output on a scam example gets positive reward."""
    ex = TrainingExample(
        prompt_text="Share OTP now",
        is_scam=True,
        category="otp_theft",
        signals=("urgency", "info_request"),
    )
    good_completion = (
        '{"score": 0.95, "signals": ["urgency", "info_request"], '
        '"explanation": "OTP ask + urgency = classic scam"}'
    )
    parts = compute_reward(good_completion, ex)
    assert parts.detection == 1.0
    assert parts.total > 1.0  # detection + calibration + signals


@pytest.mark.unit
def test_reward_penalizes_missed_scam():
    """Low score on an actual scam = wrong classification."""
    ex = TrainingExample(
        prompt_text="Share OTP now",
        is_scam=True,
        category="otp_theft",
    )
    bad_completion = (
        '{"score": 0.1, "signals": [], "explanation": "Seems fine"}'
    )
    parts = compute_reward(bad_completion, ex)
    assert parts.detection == -0.5
    assert parts.total < 0.5


@pytest.mark.unit
def test_reward_penalizes_false_positive():
    """High score on benign = false positive, gets extra penalty."""
    ex = TrainingExample(
        prompt_text="Your order is out for delivery",
        is_scam=False,
        category="benign",
    )
    fp_completion = (
        '{"score": 0.9, "signals": ["urgency"], "explanation": "sus"}'
    )
    parts = compute_reward(fp_completion, ex)
    assert parts.detection == -0.5
    assert parts.false_positive_penalty == -0.3  # FP penalty
    assert parts.total < 0


@pytest.mark.unit
def test_reward_rewards_correct_benign_classification():
    """Low score on benign = correct."""
    ex = TrainingExample(
        prompt_text="Your order is out for delivery",
        is_scam=False,
        category="benign",
    )
    correct_completion = (
        '{"score": 0.1, "signals": [], "explanation": "Legit delivery SMS"}'
    )
    parts = compute_reward(correct_completion, ex)
    assert parts.detection == 1.0
    assert parts.false_positive_penalty == 0.0  # no FP
    assert parts.calibration > 0  # 0.1 close to target 0.0


@pytest.mark.unit
def test_reward_signal_bonus_for_matched_signals():
    """Naming the right signals earns up to +0.2."""
    ex = TrainingExample(
        prompt_text="x",
        is_scam=True,
        category="otp_theft",
        signals=("urgency", "info_request"),
    )
    matched = (
        '{"score": 0.9, "signals": ["urgency", "info_request"], "explanation": "y"}'
    )
    none_matched = (
        '{"score": 0.9, "signals": [], "explanation": "y"}'
    )
    r_matched = compute_reward(matched, ex)
    r_none = compute_reward(none_matched, ex)
    assert r_matched.signal_bonus > r_none.signal_bonus


@pytest.mark.unit
def test_reward_calibration_peaks_at_correct_score():
    """Calibration term is highest when score ≈ target."""
    ex = TrainingExample(prompt_text="x", is_scam=True, category="otp_theft")
    perfect = '{"score": 1.0, "signals": [], "explanation": "y"}'
    off = '{"score": 0.51, "signals": [], "explanation": "y"}'
    r_perfect = compute_reward(perfect, ex)
    r_off = compute_reward(off, ex)
    assert r_perfect.calibration > r_off.calibration


@pytest.mark.unit
def test_reward_with_explanation_judge_adds_quality_bonus():
    """Passing a judge increases total by up to +0.4 * quality."""
    ex = TrainingExample(prompt_text="Share OTP", is_scam=True, category="otp_theft")
    good = (
        '{"score": 0.9, "signals": ["urgency"], '
        '"explanation": "OTP ask is a scam. Do not share. Call bank."}'
    )
    r_no_judge = compute_reward(good, ex)
    r_with_judge = compute_reward(good, ex, explanation_judge=MockExplanationJudge())
    assert r_with_judge.explanation > r_no_judge.explanation
    assert r_with_judge.total > r_no_judge.total


# ---- Training example builder tests ----


@pytest.mark.integration
def test_build_training_examples_returns_scams_plus_benign():
    examples = build_training_examples()
    scams = [e for e in examples if e.is_scam]
    benigns = [e for e in examples if not e.is_scam]
    assert len(scams) >= 150  # all 200 templates are scams
    assert len(benigns) >= 1  # at least some benign from Mode C


@pytest.mark.integration
def test_training_examples_have_prompt_text():
    examples = build_training_examples()
    for ex in examples[:10]:
        assert ex.prompt_text
        assert len(ex.prompt_text) > 20


@pytest.mark.integration
def test_training_examples_are_deterministic_with_seed():
    a = build_training_examples(seed=42)
    b = build_training_examples(seed=42)
    assert [e.prompt_text for e in a[:5]] == [e.prompt_text for e in b[:5]]
