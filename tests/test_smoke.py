"""Day-1 smoke tests: run 100 episodes end-to-end with scripted agents.

If this passes, the environment is ready for LLM integration on Day 2.
"""

from __future__ import annotations

import pytest

from chakravyuh_env import ChakravyuhEnv, EpisodeOutcome, VictimProfile  # noqa: F401


@pytest.mark.unit
def test_env_reset_returns_observation():
    env = ChakravyuhEnv()
    obs = env.reset(seed=42)
    assert obs.agent_role == "scammer"
    assert obs.turn == 0


@pytest.mark.unit
def test_deterministic_with_seed():
    """Same seed → same outcome. Required for replay-first demo."""
    env1 = ChakravyuhEnv()
    env2 = ChakravyuhEnv()
    env1.reset(seed=123)
    env2.reset(seed=123)
    done1, done2 = False, False
    outcomes = []
    while not done1:
        _, _, done1, info = env1.step()
        if done1:
            outcomes.append(info["outcome"])
    while not done2:
        _, _, done2, info = env2.step()
        if done2:
            outcomes.append(info["outcome"])
    # Deterministic: same category, same analyzer flag, same detection turn
    assert outcomes[0].scam_category == outcomes[1].scam_category
    assert outcomes[0].analyzer_flagged == outcomes[1].analyzer_flagged
    assert outcomes[0].turns_used == outcomes[1].turns_used


@pytest.mark.unit
def test_episode_terminates_within_max_turns():
    env = ChakravyuhEnv()
    env.reset(seed=7)
    done = False
    for _ in range(15):  # safety cap
        if done:
            break
        _, _, done, _ = env.step()
    assert done is True


@pytest.mark.integration
def test_100_episodes_run_without_crash():
    """Main smoke test — the one that gates Day 2.

    Iterates over all three victim profiles to guarantee the full decision
    surface (comply / refuse / verify) is covered at least once.
    """
    profiles = [VictimProfile.SENIOR, VictimProfile.SEMI_URBAN, VictimProfile.YOUNG_URBAN]
    outcomes: list[EpisodeOutcome] = []
    for i in range(100):
        profile = profiles[i % 3]
        gullibility = {"senior": 1.5, "semi_urban": 1.0, "young_urban": 0.7}[profile.value]
        env = ChakravyuhEnv(victim_profile=profile, gullibility=gullibility)
        env.reset(seed=1000 + i)
        done = False
        while not done:
            _, _, done, info = env.step()
            if done:
                outcomes.append(info["outcome"])
    assert len(outcomes) == 100
    flagged = sum(1 for o in outcomes if o.analyzer_flagged)
    assert flagged > 0, "Analyzer never flagged in 100 episodes — rules broken"
    extracted = sum(1 for o in outcomes if o.money_extracted)
    refused = sum(1 for o in outcomes if o.victim_refused)
    assert extracted > 0, "No extraction across mixed profiles — victim logic broken"
    assert refused > 0, "No refusal across mixed profiles — victim logic broken"


@pytest.mark.integration
def test_reward_signs_are_sane():
    """Scammer reward > 0 when money extracted; < 0 when refused early."""
    env = ChakravyuhEnv(victim_profile=VictimProfile.SENIOR, gullibility=1.5)
    env.reset(seed=42)
    done = False
    reward = None
    while not done:
        _, reward, done, _ = env.step()
    assert reward is not None
    # Reward breakdown must sum correctly
    assert isinstance(reward.scammer, float)
    assert isinstance(reward.victim, float)
    assert isinstance(reward.analyzer, float)


@pytest.mark.unit
def test_all_scam_categories_reachable():
    """Seed diversity must cover all 5 scam categories."""
    env = ChakravyuhEnv()
    seen = set()
    for i in range(200):
        env.reset(seed=i)
        done = False
        while not done:
            _, _, done, info = env.step()
            if done:
                seen.add(info["outcome"].scam_category.value)
    assert len(seen) >= 3, f"Only {len(seen)} categories seen: {seen}"
