"""Tests for demo curator + state logic (Gradio-free)."""

from __future__ import annotations

import pytest

from chakravyuh_env.schemas import ChatMessage
from server.episode_curator import (
    CURATED_EPISODES,
    format_bank_panel,
    format_chat_html,
    format_suspicion_timeline,
    max_turn,
    outcome_badge,
    replay,
    replay_all,
    suspicion_score_for_turn,
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
    # Must neutralize the raw <script> tag — actual script tags not present
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.integration
def test_keyword_highlighting_marks_urgency_and_info_words():
    """Scammer messages with 'OTP' and 'urgent' should contain <mark> tags."""
    msgs = [
        ChatMessage(sender="scammer", turn=1, text="URGENT: Share OTP immediately!")
    ]
    html = format_chat_html(msgs, highlight=True)
    mark_count = html.count("<mark")
    assert mark_count >= 2  # both 'URGENT' and 'OTP' (and 'immediately') highlighted


@pytest.mark.integration
def test_victim_messages_never_highlighted():
    """Victim utterances should never get keyword highlighting."""
    msgs = [ChatMessage(sender="victim", turn=2, text="Please share OTP urgent")]
    html = format_chat_html(msgs, highlight=True)
    # Victim is blue-bg; highlight only runs on scammer
    assert "<mark" not in html


@pytest.mark.integration
def test_step_through_filters_by_turn():
    """format_chat_html(up_to_turn=N) must hide messages with turn > N."""
    msgs = [
        ChatMessage(sender="scammer", turn=1, text="one"),
        ChatMessage(sender="victim", turn=2, text="two"),
        ChatMessage(sender="scammer", turn=4, text="four"),
    ]
    html_turn_2 = format_chat_html(msgs, up_to_turn=2)
    assert "one" in html_turn_2
    assert "two" in html_turn_2
    assert "four" not in html_turn_2


@pytest.mark.integration
def test_suspicion_timeline_captures_all_analyzer_turns():
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    # Analyzer runs at turns 3 and 6
    turns = [s.turn for s in result.analyzer_snapshots]
    assert 3 in turns
    assert 6 in turns
    html = format_suspicion_timeline(result.analyzer_snapshots)
    assert "T3" in html
    assert "T6" in html


@pytest.mark.integration
def test_bank_panel_reflects_freeze_decision():
    """Episode 1 (multi_agent_save) must show FROZEN in bank panel."""
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    html = format_bank_panel(result.bank_snapshots, result.transaction)
    assert "FROZEN" in html


@pytest.mark.integration
def test_max_turn_returns_highest_turn_number():
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    t = max_turn(result)
    assert t >= 8  # bank acts on turn 8


@pytest.mark.integration
def test_suspicion_score_for_turn_respects_cutoff():
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    # Before turn 3, analyzer hasn't run → score 0
    s_before, _ = suspicion_score_for_turn(result.analyzer_snapshots, up_to_turn=1)
    assert s_before == 0.0
    # After turn 6, max score should be high (≥ 0.7)
    s_after, _ = suspicion_score_for_turn(result.analyzer_snapshots, up_to_turn=6)
    assert s_after >= 0.7


@pytest.mark.integration
def test_replayed_episode_captures_bank_snapshot():
    """Every episode that reaches turn 8 (bank) should have a bank snapshot."""
    for ep in CURATED_EPISODES:
        result = replay(ep)
        if result.outcome.turns_used >= 8:
            assert len(result.bank_snapshots) >= 1, (
                f"{ep.label} reached turn 8 but no bank snapshot"
            )


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
