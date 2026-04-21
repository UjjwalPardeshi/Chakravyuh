"""Tests for demo curator + state logic (Gradio-free)."""

from __future__ import annotations

import pytest

from chakravyuh_env.schemas import ChatMessage
from server.episode_curator import (
    CURATED_EPISODES,
    format_chat_html,
    outcome_badge,
    replay,
    replay_all,
)


@pytest.mark.unit
def test_curated_episodes_are_five_with_distinct_seeds():
    assert len(CURATED_EPISODES) == 5
    seeds = [e.seed for e in CURATED_EPISODES]
    assert len(set(seeds)) == 5


@pytest.mark.unit
def test_curated_episodes_cover_all_outcome_kinds():
    kinds = {e.outcome_kind for e in CURATED_EPISODES}
    assert kinds == {
        "detection_too_late",
        "scripted_missed",
        "victim_refused",
        "multi_agent_save",
        "victim_verified",
    }


@pytest.mark.integration
def test_replay_is_deterministic():
    """Calling replay() twice with the same episode must produce identical output."""
    ep = CURATED_EPISODES[0]
    a = replay(ep)
    b = replay(ep)
    assert a.seed == b.seed
    assert a.outcome == b.outcome
    assert len(a.chat_history) == len(b.chat_history)
    for msg_a, msg_b in zip(a.chat_history, b.chat_history):
        assert msg_a.text == msg_b.text
        assert msg_a.sender == msg_b.sender


@pytest.mark.integration
def test_replay_all_produces_five_episodes_without_crash():
    results = replay_all()
    assert len(results) == 5
    for r in results:
        assert len(r.chat_history) >= 1
        assert r.outcome.turns_used >= 1


@pytest.mark.integration
def test_multi_agent_save_actually_saves():
    """Multi-agent defense episode: analyzer flags + bank freezes = victim saved."""
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    assert result.outcome.analyzer_flagged is True
    assert result.outcome.bank_froze is True
    assert result.outcome.money_extracted is False


@pytest.mark.integration
def test_victim_refused_episode_actually_refuses():
    refused = next(e for e in CURATED_EPISODES if e.outcome_kind == "victim_refused")
    result = replay(refused)
    assert result.outcome.victim_refused is True
    assert result.outcome.money_extracted is False


@pytest.mark.integration
def test_scripted_missed_demonstrates_analyzer_blind_spot():
    missed = next(e for e in CURATED_EPISODES if e.outcome_kind == "scripted_missed")
    result = replay(missed)
    # The whole point: analyzer did NOT flag at the threshold
    assert result.outcome.analyzer_flagged is False
    assert result.outcome.money_extracted is True


@pytest.mark.unit
def test_format_chat_html_escapes_safely():
    msgs = [ChatMessage(sender="scammer", turn=1, text="<script>alert(1)</script>")]
    html = format_chat_html(msgs)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.unit
def test_outcome_badge_never_empty():
    from chakravyuh_env.schemas import EpisodeOutcome, ScamCategory, VictimProfile

    outcome = EpisodeOutcome(
        money_extracted=False,
        detected_by_turn=None,
        turns_used=10,
        victim_refused=False,
        victim_sought_verification=False,
        analyzer_flagged=False,
        bank_flagged=False,
        bank_froze=False,
        false_positive=False,
        scam_category=ScamCategory.OTP_THEFT,
        victim_profile=VictimProfile.SEMI_URBAN,
    )
    assert outcome_badge(outcome).strip() != ""
