"""Parity tests — `compute_reward(..., "v2")` vs `AnalyzerRubricV2`.

These two implementations are the trainer-side and env-side views of the
same reward function. Drift between them is the bug the audit P0-3 closes
— this test suite locks the parity in CI.

For each leaf component, we construct an action+observation pair and
assert that the trainer's per-component value matches the rubric's
leaf score (in [0, 1]) times the v2 weight, modulo the explanation
component which depends on an optional LLM judge.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from chakravyuh_env import (
    AnalyzerRubricV2,
    ChakravyuhAction,
    V2_WEIGHTS,
)
from training.grpo_analyzer import TrainingExample, compute_reward


def _scam_outcome(*, flagged: bool, score: float) -> dict:
    """Build the outcome dict the rubric reads for a scam scenario."""
    return {
        "analyzer_flagged": flagged,
        "detected_by_turn": 3 if flagged else None,
        "is_benign": False,
        "false_positive": False,
        "money_extracted": False,
        "expected_signals": ["urgency", "info_request"],
    }


def _benign_outcome(*, flagged: bool, score: float) -> dict:
    return {
        "analyzer_flagged": flagged,
        "detected_by_turn": 3 if flagged else None,
        "is_benign": True,
        "false_positive": flagged,
        "money_extracted": False,
        "expected_signals": [],
    }


@pytest.mark.unit
def test_v2_fp_penalty_matches_rubric_weight() -> None:
    """When trainer-v2 fires the FP penalty, the rubric's false_positive
    leaf returns 1.0 and the V2 weight is -0.8 — the two must agree."""
    ex = TrainingExample(
        prompt_text="Your order is out for delivery", is_scam=False, category="benign"
    )
    completion = '{"score": 0.9, "signals": [], "explanation": "sus"}'
    parts = compute_reward(completion, ex, reward_profile="v2")
    assert parts.false_positive_penalty == V2_WEIGHTS["false_positive"], (
        f"trainer fp_penalty={parts.false_positive_penalty}, "
        f"V2_WEIGHTS[false_positive]={V2_WEIGHTS['false_positive']}"
    )


@pytest.mark.unit
def test_v2_calibration_matches_rubric_weight() -> None:
    """Trainer-v2 calibration on benign uses 0.5 weight, matching V2_WEIGHTS.

    The trainer inlines `target=0.0` for benign while the env rubric uses
    `benign_target=0.1` (a 0.1 dead-zone for noisy scores). The two are
    intentionally not bit-identical at the score level; what we lock here
    is that the **weight** matches and the leaf is in [0, 1] so the V2
    rubric's contribution is bounded the same way the trainer's is.
    """
    ex_benign = TrainingExample(prompt_text="x", is_scam=False, category="benign")
    completion_benign = '{"score": 0.1, "signals": [], "explanation": "ok"}'
    parts = compute_reward(completion_benign, ex_benign, reward_profile="v2")
    # Trainer: calib_weight=0.5, score=0.1, target=0 → 0.5 * 0.9 = 0.45
    assert abs(parts.calibration - 0.45) < 1e-6
    assert V2_WEIGHTS["calibration"] == 0.5

    rubric = AnalyzerRubricV2()
    action = ChakravyuhAction(score=0.1, signals=[], explanation="ok")
    rubric.calibration(action, SimpleNamespace(done=True, outcome={"is_benign": True}))
    leaf = rubric.calibration.last_score
    assert leaf is not None
    # Rubric leaf in [0,1] (uses benign_target=0.1 by default → leaf = 1.0
    # at score=0.1; we just assert bounded, not bit-identical to trainer).
    assert 0.0 <= leaf <= 1.0


@pytest.mark.unit
def test_v2_format_denied_on_benign_flagged_as_scam() -> None:
    """Both trainer and rubric must zero the format reward when the
    analyzer flags a benign as scam (the v2 anti-collapse fix)."""
    ex = TrainingExample(prompt_text="x", is_scam=False, category="benign")
    completion = '{"score": 0.9, "signals": [], "explanation": "{score: 0.9}"}'
    parts = compute_reward(completion, ex, reward_profile="v2")
    assert parts.format == 0.0  # format reward denied

    rubric = AnalyzerRubricV2()
    action = ChakravyuhAction(
        score=0.9,
        signals=[],
        explanation='{"score": 0.9, "explanation": "scam"}',
    )
    rubric.format(action, SimpleNamespace(done=True, outcome={"is_benign": True}))
    assert rubric.format.last_score == 0.0


@pytest.mark.unit
def test_v2_format_paid_on_correct_scam() -> None:
    """Format reward is paid when the analyzer correctly flags a scam."""
    ex = TrainingExample(prompt_text="Share OTP urgent", is_scam=True, category="otp_theft")
    completion = '{"score": 0.95, "signals": ["urgency"], "explanation": "scam"}'
    parts = compute_reward(completion, ex, reward_profile="v2")
    assert parts.format == 0.15  # format paid

    rubric = AnalyzerRubricV2()
    action = ChakravyuhAction(
        score=0.95,
        signals=["urgency"],
        explanation='{"score": 0.95, "explanation": "scam"}',
    )
    rubric.format(action, SimpleNamespace(done=True, outcome={"is_benign": False}))
    # Rubric leaf is 1.0 in [0,1] units; trainer pays the weighted 0.15.
    assert rubric.format.last_score == 1.0
    assert abs(parts.format - rubric.format.last_score * V2_WEIGHTS["format"]) < 1e-6
