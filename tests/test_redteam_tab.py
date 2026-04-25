"""Live red-team tab — same analyzer, two reward profiles."""

from __future__ import annotations

import pytest

from server.redteam_handler import (
    _classify_asymmetry,
    _profile_breakdown,
    _score_message,
    render_redteam_view,
)
from chakravyuh_env import AnalyzerRubric, AnalyzerRubricV2, V2_WEIGHTS
from chakravyuh_env.rubrics import DEFAULT_WEIGHTS


@pytest.mark.unit
def test_render_returns_three_html_strings_on_empty() -> None:
    v1, v2, badge = render_redteam_view("")
    assert "Type a scam attempt" in v1
    assert "Type a scam attempt" in v2
    assert badge == ""


@pytest.mark.unit
def test_render_returns_three_html_strings_on_clear_scam() -> None:
    v1, v2, badge = render_redteam_view("Share your OTP urgently to claim your prize")
    # Both cards render full structure.
    assert 'redteam-card' in v1
    assert 'redteam-card' in v2
    assert 'redteam-v1' in v1
    assert 'redteam-v2' in v2
    # Score should be high → both cards show FLAGGED chip.
    assert 'flagged' in v1.lower()
    assert 'flagged' in v2.lower()
    # Badge present.
    assert "Asymmetry diagnostic" in badge


@pytest.mark.unit
def test_score_message_returns_tuple() -> None:
    score, signals, explanation = _score_message("Share your OTP urgently")
    assert 0.0 <= score <= 1.0
    assert isinstance(signals, list)
    assert isinstance(explanation, str)


@pytest.mark.unit
def test_v2_profile_has_more_leaves_than_v1() -> None:
    """The v2 reward profile has 8 leaves; v1 has 5."""
    score, signals, expl = _score_message("Share your OTP urgently to claim prize")
    v1_breakdown, _ = _profile_breakdown(
        AnalyzerRubric, DEFAULT_WEIGHTS, score, signals, expl,
        is_benign_truth=False,
    )
    v2_breakdown, _ = _profile_breakdown(
        AnalyzerRubricV2, V2_WEIGHTS, score, signals, expl,
        is_benign_truth=False,
    )
    assert len(V2_WEIGHTS) > len(DEFAULT_WEIGHTS)
    assert "format" in V2_WEIGHTS  # v2-only leaf
    assert "length" in V2_WEIGHTS  # v2-only leaf
    assert "format" not in DEFAULT_WEIGHTS


@pytest.mark.unit
def test_classify_asymmetry_warns_on_false_positive() -> None:
    """When ground-truth is benign and the analyzer flagged → reward-hacking signature."""
    cls, text = _classify_asymmetry(
        score=0.8, flagged=True,
        v1_total=1.0, v2_total=-0.5,
        is_benign_truth=True,
    )
    assert cls == "redteam-asym-warning"
    assert "false-positive" in text.lower()


@pytest.mark.unit
def test_classify_asymmetry_warns_on_missed_scam() -> None:
    """When ground-truth is scam and the analyzer did not flag → missed-scam signature."""
    cls, text = _classify_asymmetry(
        score=0.3, flagged=False,
        v1_total=0.0, v2_total=-0.5,
        is_benign_truth=False,
    )
    assert cls == "redteam-asym-warning"
    assert "missed" in text.lower()


@pytest.mark.unit
def test_classify_asymmetry_neutral_on_agreement() -> None:
    """When v1 and v2 totals agree → no asymmetry signal."""
    cls, text = _classify_asymmetry(
        score=0.5, flagged=True,
        v1_total=0.5, v2_total=0.51,
        is_benign_truth=None,
    )
    assert cls == "redteam-asym-agree"


@pytest.mark.unit
def test_render_with_benign_ground_truth_surfaces_diagnostic() -> None:
    """Tagging a flagged input as benign-truth should surface the warning."""
    _, _, badge = render_redteam_view(
        "Share your OTP urgently",
        is_benign_truth=True,
    )
    assert "redteam-asym-warning" in badge or "false-positive" in badge.lower()
