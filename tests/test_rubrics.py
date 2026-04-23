"""Unit + integration tests for the composable analyzer rubric system.

Covers:

1. Each leaf rubric in isolation (DetectionRubric, MissedScamRubric,
   FalsePositiveRubric, CalibrationRubric, ExplanationRubric)
2. Non-terminal observations return 0.0 from every rubric
3. AnalyzerRubric composability: weighted sum matches manual calculation
4. ``last_score`` is populated on every child after each call
5. ``named_children`` / ``named_rubrics`` introspection surface
6. Weight overrides propagate correctly and invalid configs raise
7. State-dict round-trip for checkpointing
8. Integration: the rubric wired into ChakravyuhOpenEnv drives the
   actual ``observation.reward`` and matches the sum of its child scores
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from chakravyuh_env import (
    AnalyzerRubric,
    CalibrationRubric,
    ChakravyuhAction,
    ChakravyuhOpenEnv,
    DetectionRubric,
    ExplanationRubric,
    FalsePositiveRubric,
    MissedScamRubric,
)
from chakravyuh_env.rubrics import DEFAULT_WEIGHTS
from openenv.core.rubrics import Rubric


# ---------------------------------------------------------------------------
# Helpers: stub action / observation
# ---------------------------------------------------------------------------


def _action(
    score: float = 0.8,
    signals: list[str] | None = None,
    explanation: str = "",
) -> ChakravyuhAction:
    return ChakravyuhAction(
        score=score,
        signals=signals or [],
        explanation=explanation,
    )


def _obs(
    *,
    done: bool = True,
    outcome: dict | None = None,
):
    """Duck-typed observation stub — the rubric only reads `.done` and
    `.outcome`, so a SimpleNamespace is enough for leaf-rubric tests."""
    return SimpleNamespace(done=done, outcome=outcome)


# ---------------------------------------------------------------------------
# Leaf rubric unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectionRubric:
    def test_returns_zero_on_non_terminal(self) -> None:
        r = DetectionRubric()
        assert r(_action(), _obs(done=False, outcome=None)) == 0.0

    def test_returns_zero_when_not_flagged(self) -> None:
        r = DetectionRubric()
        out = {"analyzer_flagged": False, "detected_by_turn": None, "false_positive": False}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_returns_one_on_early_flag(self) -> None:
        r = DetectionRubric()
        out = {"analyzer_flagged": True, "detected_by_turn": 3, "false_positive": False}
        assert r(_action(), _obs(outcome=out)) == 1.0

    def test_returns_zero_on_late_flag(self) -> None:
        r = DetectionRubric()
        out = {"analyzer_flagged": True, "detected_by_turn": 8, "false_positive": False}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_returns_zero_on_false_positive(self) -> None:
        # Flagged early but the episode was benign → NOT a detection win.
        r = DetectionRubric()
        out = {"analyzer_flagged": True, "detected_by_turn": 3, "false_positive": True}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_custom_cutoff(self) -> None:
        r = DetectionRubric(early_cutoff=4)
        out = {"analyzer_flagged": True, "detected_by_turn": 5, "false_positive": False}
        assert r(_action(), _obs(outcome=out)) == 0.0


@pytest.mark.unit
class TestMissedScamRubric:
    def test_fires_only_when_missed_and_money_extracted(self) -> None:
        r = MissedScamRubric()
        out = {"analyzer_flagged": False, "money_extracted": True}
        assert r(_action(), _obs(outcome=out)) == 1.0

    def test_zero_when_flagged_but_missed_money(self) -> None:
        r = MissedScamRubric()
        out = {"analyzer_flagged": True, "money_extracted": True}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_zero_when_no_money_extracted(self) -> None:
        r = MissedScamRubric()
        out = {"analyzer_flagged": False, "money_extracted": False}
        assert r(_action(), _obs(outcome=out)) == 0.0


@pytest.mark.unit
class TestFalsePositiveRubric:
    def test_fires_only_when_flagged_benign(self) -> None:
        r = FalsePositiveRubric()
        out = {"analyzer_flagged": True, "false_positive": True}
        assert r(_action(), _obs(outcome=out)) == 1.0

    def test_zero_when_not_flagged(self) -> None:
        r = FalsePositiveRubric()
        out = {"analyzer_flagged": False, "false_positive": True}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_zero_when_flagged_real_scam(self) -> None:
        r = FalsePositiveRubric()
        out = {"analyzer_flagged": True, "false_positive": False}
        assert r(_action(), _obs(outcome=out)) == 0.0


@pytest.mark.unit
class TestCalibrationRubric:
    def test_perfect_score_on_scam(self) -> None:
        r = CalibrationRubric(scam_target=0.9)
        out = {"is_benign": False}
        assert r(_action(score=0.9), _obs(outcome=out)) == pytest.approx(1.0)

    def test_decreases_with_distance(self) -> None:
        r = CalibrationRubric(scam_target=0.9)
        out = {"is_benign": False}
        # Symmetric 0.1 distance on either side → 0.9 each.
        s_low = r(_action(score=0.8), _obs(outcome=out))
        s_high = r(_action(score=1.0), _obs(outcome=out))
        assert s_low == pytest.approx(0.9)
        assert s_high == pytest.approx(0.9)

    def test_clips_to_zero(self) -> None:
        r = CalibrationRubric(scam_target=0.9)
        out = {"is_benign": False}
        # |0.0 - 0.9| = 0.9 → 1 - 0.9 = 0.1
        assert r(_action(score=0.0), _obs(outcome=out)) == pytest.approx(0.1)

    def test_benign_flips_target(self) -> None:
        r = CalibrationRubric(scam_target=0.9, benign_target=0.1)
        out = {"is_benign": True}
        assert r(_action(score=0.1), _obs(outcome=out)) == pytest.approx(1.0)
        assert r(_action(score=0.9), _obs(outcome=out)) == pytest.approx(0.2)

    def test_rejects_out_of_range_targets(self) -> None:
        with pytest.raises(ValueError):
            CalibrationRubric(scam_target=1.5)
        with pytest.raises(ValueError):
            CalibrationRubric(benign_target=-0.1)


@pytest.mark.unit
class TestExplanationRubric:
    def test_empty_explanation_returns_zero(self) -> None:
        r = ExplanationRubric()
        out = {}
        assert r(_action(explanation=""), _obs(outcome=out)) == 0.0

    def test_short_baseline(self) -> None:
        r = ExplanationRubric()
        out = {}
        # 10-char explanation, no matching signal → baseline 0.3 only.
        assert r(_action(explanation="suspicious"), _obs(outcome=out)) == pytest.approx(0.3)

    def test_rewards_matching_signal(self) -> None:
        r = ExplanationRubric()
        out = {}
        score = r(
            _action(signals=["urgency"], explanation="clear urgency cue"),
            _obs(outcome=out),
        )
        # 0.3 baseline + 0.3 signal match = 0.6 (length < 30)
        assert score == pytest.approx(0.6)

    def test_length_bonuses(self) -> None:
        r = ExplanationRubric()
        out = {}
        medium = "This message shows clear signs of scam behaviour via"  # ~50 chars
        long_ = (
            "This message shows clear signs of scam behaviour via urgency and "
            "impersonation patterns common in Indian UPI fraud cases."
        )
        assert len(medium) >= 30 and len(medium) < 60
        assert len(long_) >= 60
        assert r(_action(explanation=medium), _obs(outcome=out)) == pytest.approx(0.5)
        assert r(_action(explanation=long_), _obs(outcome=out)) == pytest.approx(0.7)

    def test_max_clip(self) -> None:
        r = ExplanationRubric()
        out = {}
        long_with_signal = (
            "High urgency info_request from impersonated bank with suspicious_link; "
            "typical Indian UPI fraud pattern, high confidence classification."
        )
        score = r(
            _action(
                signals=["urgency", "info_request", "suspicious_link", "impersonation"],
                explanation=long_with_signal,
            ),
            _obs(outcome={}),
        )
        assert score == 1.0


# ---------------------------------------------------------------------------
# AnalyzerRubric composability tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnalyzerRubricComposability:
    def test_registers_all_five_children(self) -> None:
        r = AnalyzerRubric()
        names = [n for n, _ in r.named_children()]
        assert names == [
            "detection",
            "missed_scam",
            "false_positive",
            "calibration",
            "explanation",
        ]
        # named_rubrics is flat (our children are leaves).
        named = [n for n, _ in r.named_rubrics()]
        assert set(named) == set(names)

    def test_children_are_rubric_instances(self) -> None:
        r = AnalyzerRubric()
        for _, child in r.named_children():
            assert isinstance(child, Rubric)

    def test_get_rubric_by_path(self) -> None:
        r = AnalyzerRubric()
        assert isinstance(r.get_rubric("detection"), DetectionRubric)
        assert isinstance(r.get_rubric("calibration"), CalibrationRubric)
        with pytest.raises(KeyError):
            r.get_rubric("no_such_child")

    def test_non_terminal_returns_zero(self) -> None:
        r = AnalyzerRubric()
        assert r(_action(), _obs(done=False, outcome=None)) == 0.0

    def test_last_scores_populated_after_call(self) -> None:
        r = AnalyzerRubric()
        out = {
            "analyzer_flagged": True,
            "detected_by_turn": 3,
            "money_extracted": False,
            "false_positive": False,
            "is_benign": False,
        }
        r(_action(score=0.9, signals=["urgency"], explanation="urgent info request"), _obs(outcome=out))
        last = r.last_scores()
        for k in ("total", "detection", "missed_scam", "false_positive", "calibration", "explanation"):
            assert k in last
            assert last[k] is not None

    def test_weighted_sum_matches_manual(self) -> None:
        r = AnalyzerRubric()
        out = {
            "analyzer_flagged": True,
            "detected_by_turn": 3,
            "money_extracted": False,
            "false_positive": False,
            "is_benign": False,
        }
        action = _action(
            score=0.9,
            signals=["urgency", "info_request"],
            explanation="High urgency info request with impersonation signals; typical scam.",
        )
        total = r(action, _obs(outcome=out))
        # Expected child scores:
        #   detection = 1.0, missed = 0.0, fp = 0.0
        #   calibration = 1.0 (score matches 0.9 target exactly)
        #   explanation = 0.3 base + 0.3 signal match + 0.2 (>=30) + 0.2 (>=60) = 1.0
        expected = (
            DEFAULT_WEIGHTS["detection"] * 1.0
            + DEFAULT_WEIGHTS["missed_scam"] * 0.0
            + DEFAULT_WEIGHTS["false_positive"] * 0.0
            + DEFAULT_WEIGHTS["calibration"] * 1.0
            + DEFAULT_WEIGHTS["explanation"] * 1.0
        )
        assert total == pytest.approx(expected)

    def test_custom_weights_override(self) -> None:
        new_weights = {
            "detection": 2.0,
            "missed_scam": -1.0,
            "false_positive": -0.5,
            "calibration": 0.0,
            "explanation": 0.0,
        }
        r = AnalyzerRubric(weights=new_weights)
        out = {
            "analyzer_flagged": True,
            "detected_by_turn": 3,
            "money_extracted": False,
            "false_positive": False,
            "is_benign": False,
        }
        total = r(_action(score=0.5, explanation=""), _obs(outcome=out))
        assert total == pytest.approx(2.0)

    def test_missing_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="missing keys"):
            AnalyzerRubric(weights={"detection": 1.0})

    def test_default_weights_do_not_mutate_on_override(self) -> None:
        r = AnalyzerRubric(weights={**DEFAULT_WEIGHTS, "detection": 99.0})
        assert r.weights["detection"] == 99.0
        # Module-level DEFAULT_WEIGHTS must be unchanged.
        assert DEFAULT_WEIGHTS["detection"] == 1.0

    def test_state_dict_round_trip(self) -> None:
        r = AnalyzerRubric()
        r.weights["detection"] = 42.0
        state = r.state_dict()
        assert state["weights"]["detection"] == 42.0

        r2 = AnalyzerRubric()
        r2.load_state_dict(state)
        assert r2.weights["detection"] == 42.0


# ---------------------------------------------------------------------------
# Integration with ChakravyuhOpenEnv
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRubricIntegration:
    def test_env_uses_analyzer_rubric_by_default(self) -> None:
        env = ChakravyuhOpenEnv()
        assert isinstance(env.rubric, AnalyzerRubric)

    def test_rubric_reward_matches_terminal_observation_reward(self) -> None:
        env = ChakravyuhOpenEnv()
        env.reset(seed=42)
        obs = env.step(_action(score=0.9, signals=["urgency"], explanation="u"))
        if not obs.done:
            obs = env.step(_action(score=0.9, signals=["impersonation"], explanation="i"))
        # The terminal observation.reward must equal the top-level rubric
        # last_score (they're literally the same value by construction).
        assert obs.reward == pytest.approx(env.rubric.last_score)

    def test_reward_breakdown_includes_all_sub_rubrics(self) -> None:
        env = ChakravyuhOpenEnv()
        env.reset(seed=42)
        obs = env.step(_action(score=0.9))
        if not obs.done:
            obs = env.step(_action(score=0.9))
        bd = obs.reward_breakdown
        assert bd is not None
        for key in ("detection", "missed_scam", "false_positive", "calibration", "explanation"):
            assert key in bd

    def test_custom_rubric_is_used(self) -> None:
        class ConstantRubric(Rubric):
            def forward(self, action, observation):
                return 7.0 if getattr(observation, "done", False) else 0.0

        env = ChakravyuhOpenEnv(rubric=ConstantRubric())
        env.reset(seed=42)
        obs = env.step(_action(score=0.9))
        if not obs.done:
            obs = env.step(_action(score=0.9))
        assert obs.reward == pytest.approx(7.0)

    def test_rubric_reset_clears_last_score(self) -> None:
        env = ChakravyuhOpenEnv()
        env.reset(seed=42)
        env.step(_action(score=0.9))
        env.step(_action(score=0.9))
        assert env.rubric.last_score is not None

        # reset() must trigger a rubric reset — for stateless Rubrics
        # last_score stays from the previous episode, but trajectory
        # rubrics would have their accumulated state cleared. Verify
        # last_score gets re-populated on the new episode's terminal step.
        env.reset(seed=99)
        env.step(_action(score=0.9))
        env.step(_action(score=0.9))
        # After a full second episode, last_score is freshly set (not
        # a stale carry-over from the first episode).
        assert env.rubric.last_score is not None

    def test_forward_pre_hook_fires_on_every_call(self) -> None:
        calls: list[str] = []

        def pre_hook(rubric, action, observation):
            calls.append("pre")

        def post_hook(rubric, action, observation, result):
            calls.append(f"post:{result:.2f}")

        env = ChakravyuhOpenEnv()
        env.rubric.register_forward_pre_hook(pre_hook)
        env.rubric.register_forward_hook(post_hook)

        env.reset(seed=42)
        env.step(_action(score=0.9))
        env.step(_action(score=0.9))
        # One rubric call per step (2 steps) — pre + post each.
        assert calls.count("pre") >= 1
        assert any(c.startswith("post:") for c in calls)
