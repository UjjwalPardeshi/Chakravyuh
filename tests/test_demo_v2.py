"""Tests for v2 UI upgrades: agent cards + attack timeline + state derivation."""

from __future__ import annotations

import pytest

from server.episode_curator import (
    AGENT_COLORS,
    CURATED_EPISODES,
    AgentState,
    compute_agent_states,
    format_agent_cards_html,
    format_attack_timeline_html,
    max_turn,
    replay,
)


@pytest.mark.unit
def test_all_five_agents_have_brand_colors():
    for agent in ("scammer", "victim", "analyzer", "bank", "regulator"):
        assert agent in AGENT_COLORS
        assert "accent" in AGENT_COLORS[agent]
        assert "soft" in AGENT_COLORS[agent]
        assert "icon" in AGENT_COLORS[agent]


@pytest.mark.integration
def test_compute_agent_states_returns_all_five():
    for ep in CURATED_EPISODES:
        result = replay(ep)
        states = compute_agent_states(result, up_to_turn=None)
        assert len(states) == 5
        assert {s.agent for s in states} == {
            "scammer",
            "victim",
            "analyzer",
            "bank",
            "regulator",
        }
        for s in states:
            assert isinstance(s, AgentState)
            assert s.tone in ("idle", "active", "warning", "critical", "safe")
            assert s.status
            assert s.detail


@pytest.mark.integration
def test_agent_states_evolve_with_turn():
    """At turn 0 all agents should be idle; at end they should have acted."""
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)

    states_t0 = compute_agent_states(result, up_to_turn=0)
    tones_t0 = {s.agent: s.tone for s in states_t0}
    assert tones_t0["scammer"] == "idle"
    assert tones_t0["victim"] == "idle"
    assert tones_t0["analyzer"] == "idle"
    assert tones_t0["bank"] == "idle"

    states_end = compute_agent_states(result, up_to_turn=None)
    tones_end = {s.agent: s.tone for s in states_end}
    # After full episode: analyzer should be critical (0.99), bank safe (FROZEN)
    assert tones_end["analyzer"] == "critical"
    assert tones_end["bank"] == "safe"


@pytest.mark.integration
def test_victim_refused_episode_shows_victim_safe_tone():
    refused = next(e for e in CURATED_EPISODES if e.outcome_kind == "victim_refused")
    result = replay(refused)
    states = compute_agent_states(result, up_to_turn=None)
    victim_state = next(s for s in states if s.agent == "victim")
    assert victim_state.tone == "safe"
    assert "Refused" in victim_state.status


@pytest.mark.integration
def test_victim_verified_episode_shows_called_bank():
    verified = next(e for e in CURATED_EPISODES if e.outcome_kind == "victim_verified")
    result = replay(verified)
    states = compute_agent_states(result, up_to_turn=None)
    victim_state = next(s for s in states if s.agent == "victim")
    assert victim_state.tone == "safe"
    assert "Verif" in victim_state.status  # "Verifying"


@pytest.mark.unit
def test_agent_cards_html_contains_all_five_agents():
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    states = compute_agent_states(result, up_to_turn=None)
    html = format_agent_cards_html(states)
    for agent in ("Scammer", "Victim", "Analyzer", "Bank", "Regulator"):
        assert agent in html
    # Must contain all five brand icons
    for brand in AGENT_COLORS.values():
        assert brand["icon"] in html


@pytest.mark.unit
def test_attack_timeline_has_9_turns_minimum():
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    html = format_attack_timeline_html(result, up_to_turn=None)
    # Expect T1 through T9 labels at minimum
    for t in range(1, 10):
        assert f">T{t}<" in html


@pytest.mark.integration
def test_timeline_step_through_fades_future_turns():
    """At cutoff=3, turns 4+ should have reduced opacity in the HTML."""
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    html = format_attack_timeline_html(result, up_to_turn=3)
    # "opacity:0.25" marks faded future turns
    assert "opacity:0.25" in html
    # "opacity:1" for visible turns
    assert "opacity:1" in html


@pytest.mark.integration
def test_scammer_shows_transaction_ask_after_turn_7():
    """Past turn 7, scammer state should flip to Transaction ask."""
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    states_t8 = compute_agent_states(result, up_to_turn=8)
    scammer = next(s for s in states_t8 if s.agent == "scammer")
    assert "Transaction" in scammer.status
    assert scammer.tone == "critical"


@pytest.mark.integration
def test_bank_pending_tone_between_tx_and_bank_turn():
    """At turn 7 (tx exists, bank hasn't acted yet) → bank 'active' not 'idle'."""
    saved = next(e for e in CURATED_EPISODES if e.outcome_kind == "multi_agent_save")
    result = replay(saved)
    states_t7 = compute_agent_states(result, up_to_turn=7)
    bank = next(s for s in states_t7 if s.agent == "bank")
    assert bank.tone == "active"
    assert "Reviewing" in bank.status
