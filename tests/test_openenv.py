"""Integration tests for the OpenEnv-compliant ChakravyuhOpenEnv wrapper.

Exercise the full reset/step/state contract without going through HTTP —
this verifies the Environment subclass obeys the OpenEnv interface
(reset returns ObsT, step returns ObsT with done/reward, state is
introspectable) and that 2-decision episodes produce coherent rewards.
"""

from __future__ import annotations

import pytest

from chakravyuh_env import (
    ChakravyuhAction,
    ChakravyuhObservation,
    ChakravyuhOpenEnv,
    ChakravyuhState,
)
from chakravyuh_env.openenv_models import ChakravyuhAction as _A
from chakravyuh_env.schemas import VictimProfile


# ---------------------------------------------------------------------------
# Basic contract: reset/step/state shapes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reset_returns_observation() -> None:
    env = ChakravyuhOpenEnv()
    obs = env.reset(seed=42)

    assert isinstance(obs, ChakravyuhObservation)
    # Invariant: reset() returns a non-terminal observation so the agent
    # always gets at least one step (Gym/OpenEnv convention).
    assert obs.done is False
    assert obs.decision_index == 0
    # After reset we should be past scammer(1) + victim(2) → turn == 2.
    assert obs.turn == 2
    senders = {m["sender"] for m in obs.chat_history}
    assert senders == {"scammer", "victim"}


@pytest.mark.unit
def test_state_property_before_and_after_reset() -> None:
    env = ChakravyuhOpenEnv()
    state = env.state
    assert isinstance(state, ChakravyuhState)
    assert state.episode_id is None

    env.reset(seed=7)
    state = env.state
    assert state.episode_id is not None
    assert state.scam_category is not None
    assert state.victim_profile == VictimProfile.SEMI_URBAN.value


@pytest.mark.unit
def test_step_requires_prior_reset() -> None:
    env = ChakravyuhOpenEnv()
    with pytest.raises(RuntimeError, match="reset"):
        env.step(_A(score=0.5))


# ---------------------------------------------------------------------------
# Episode progression: 2-decision flow
# ---------------------------------------------------------------------------


def _run_episode(
    env: ChakravyuhOpenEnv,
    seed: int,
    score1: float = 0.9,
    score2: float = 0.9,
) -> ChakravyuhObservation:
    obs = env.reset(seed=seed)
    assert obs.done is False, "reset() must return a non-terminal observation"
    obs = env.step(_A(score=score1, signals=["urgency"], explanation="t1"))
    if obs.done:
        return obs
    obs = env.step(_A(score=score2, signals=["impersonation"], explanation="t2"))
    return obs


@pytest.mark.integration
@pytest.mark.parametrize("seed", [1, 42, 99, 256, 1000])
def test_episode_eventually_terminates(seed: int) -> None:
    env = ChakravyuhOpenEnv()
    obs = _run_episode(env, seed=seed)
    assert obs.done is True
    assert obs.reward is not None
    assert isinstance(obs.reward, float)
    # Analyzer reward is in [-0.8, +1.4]-ish; loose bound here.
    assert -5.0 < obs.reward < 5.0


@pytest.mark.integration
def test_high_suspicion_score_flags_scam() -> None:
    env = ChakravyuhOpenEnv()
    obs = env.reset(seed=42)
    if obs.done:
        pytest.skip("Episode ended at reset for this seed")

    # Flag aggressively at both decision points.
    env.step(_A(score=0.99, flag_threshold=0.5, signals=["urgency"], explanation="flag"))
    final = env.step(
        _A(score=0.99, flag_threshold=0.5, signals=["impersonation"], explanation="flag")
    ) if not env.state.done else None

    state = env.state
    assert state.analyzer_flagged is True
    assert state.done is True
    if final is not None:
        assert final.done is True
        assert final.outcome is not None
        assert final.outcome.get("analyzer_flagged") is True


@pytest.mark.integration
def test_low_suspicion_score_does_not_flag() -> None:
    env = ChakravyuhOpenEnv()
    obs = env.reset(seed=42)
    if obs.done:
        pytest.skip("Episode ended at reset for this seed")

    # Intentionally under-score at both decision points → no flag.
    env.step(_A(score=0.10, flag_threshold=0.55, explanation="ignore"))
    if not env.state.done:
        env.step(_A(score=0.10, flag_threshold=0.55, explanation="ignore"))

    assert env.state.analyzer_flagged is False


@pytest.mark.integration
def test_step_after_done_raises() -> None:
    env = ChakravyuhOpenEnv()
    obs = _run_episode(env, seed=3)
    assert obs.done is True
    with pytest.raises(RuntimeError, match="already done"):
        env.step(_A(score=0.5))


# ---------------------------------------------------------------------------
# Reward & observation payload sanity
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_terminal_observation_includes_reward_breakdown() -> None:
    env = ChakravyuhOpenEnv()
    obs = _run_episode(env, seed=11, score1=0.9, score2=0.9)
    assert obs.done is True
    assert obs.reward_breakdown is not None
    # New composable-rubric breakdown: one entry per child rubric +
    # the weighted total + the weight map used, plus a legacy-analyzer
    # reference value kept for comparison.
    for key in (
        "total",
        "detection",
        "missed_scam",
        "false_positive",
        "calibration",
        "explanation",
        "weights",
        "legacy_analyzer",
    ):
        assert key in obs.reward_breakdown, f"reward_breakdown missing {key}"
    assert obs.outcome is not None
    for key in ("money_extracted", "analyzer_flagged", "detected_by_turn"):
        assert key in obs.outcome


@pytest.mark.integration
@pytest.mark.parametrize("seed", range(50))
def test_reset_is_always_non_terminal_across_seeds(seed: int) -> None:
    """Regression: reset() must never return done=True for any seed.

    Previously a YOUNG_URBAN victim with low trust + turn-1 info request
    could VictimRefuse on turn 2, returning a 0-step terminal episode
    from reset() — violating Gym/OpenEnv convention and breaking training
    loops that expect at least one step per trajectory.
    """
    # Sweep across all three victim profiles since the refuse path depends
    # on base trust level.
    for profile in VictimProfile:
        env = ChakravyuhOpenEnv(victim_profile=profile)
        obs = env.reset(seed=seed)
        assert obs.done is False, (
            f"reset() returned done=True on seed={seed}, profile={profile.value} "
            f"(chat_history={[m['text'][:50] for m in obs.chat_history]})"
        )
        assert obs.decision_index == 0


@pytest.mark.integration
def test_regulator_state_does_not_leak_across_resets() -> None:
    """Regression: the regulator's per-episode outcome buffer must be
    cleared by reset(). Previously it was created in __init__ once, so
    outcomes accumulated across resets within a single env instance —
    polluting downstream rule-update logic under WebSocket session reuse.
    """
    env = ChakravyuhOpenEnv()

    # Episode 1
    env.reset(seed=1)
    env.step(_A(score=0.9))
    if not env.state.done:
        env.step(_A(score=0.9))
    regulator_after_ep1 = env._regulator
    assert regulator_after_ep1 is not None
    assert len(regulator_after_ep1._outcome_buffer) == 1

    # Episode 2 — fresh regulator must replace the old one.
    env.reset(seed=2)
    regulator_after_ep2 = env._regulator
    assert regulator_after_ep2 is not None
    assert regulator_after_ep2 is not regulator_after_ep1, (
        "reset() must create a new regulator, not reuse the previous one"
    )
    assert len(regulator_after_ep2._outcome_buffer) == 0


@pytest.mark.integration
def test_concurrent_instances_have_isolated_regulators() -> None:
    """Two env instances created from the same factory must not share
    regulator state — required for SUPPORTS_CONCURRENT_SESSIONS=True."""
    env_a = ChakravyuhOpenEnv()
    env_b = ChakravyuhOpenEnv()

    env_a.reset(seed=1)
    env_b.reset(seed=2)

    env_a.step(_A(score=0.9))
    if not env_a.state.done:
        env_a.step(_A(score=0.9))

    # env_b has had no step() calls → its regulator must still be empty
    # even though env_a has logged an outcome.
    assert env_a._regulator is not env_b._regulator
    assert len(env_a._regulator._outcome_buffer) == 1
    assert len(env_b._regulator._outcome_buffer) == 0


@pytest.mark.integration
def test_invalid_signal_name_raises() -> None:
    env = ChakravyuhOpenEnv()
    obs = env.reset(seed=42)
    if obs.done:
        pytest.skip("Episode ended at reset for this seed")
    with pytest.raises(ValueError, match="AnalyzerSignal"):
        env.step(_A(score=0.9, signals=["not_a_real_signal"]))


@pytest.mark.integration
def test_determinism_same_seed_same_transcript() -> None:
    env1 = ChakravyuhOpenEnv()
    env2 = ChakravyuhOpenEnv()
    obs1 = env1.reset(seed=1234)
    obs2 = env2.reset(seed=1234)

    texts1 = [m["text"] for m in obs1.chat_history]
    texts2 = [m["text"] for m in obs2.chat_history]
    assert texts1 == texts2


# ---------------------------------------------------------------------------
# Server factory smoke test — ensures create_app wiring doesn't explode.
# Runs as a pure import/invocation test; no HTTP server is actually bound.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_fastapi_app_builds() -> None:
    from server.app import app

    assert app is not None
    # ``/health`` and ``/schema`` are part of the stock OpenEnv HTTP surface.
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in routes
    assert "/schema" in routes
    assert "/reset" in routes
    assert "/step" in routes
    assert "/state" in routes


@pytest.mark.integration
def test_websocket_full_episode_round_trip() -> None:
    """Exercise a real HTTP server + WebSocket client → the path judges use.

    Starts uvicorn as a subprocess on a free port, connects via
    ``ChakravyuhEnvClient`` (OpenEnv's standard WS client), runs a 2-step
    episode, and asserts terminal reward + outcome fields arrive intact.
    """
    import signal
    import socket
    import subprocess
    import sys
    import time
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent

    # Pick a free port by binding to 0 and releasing.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "server.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # Poll /health until the server is ready (up to 10 s).
        import urllib.request

        deadline = time.time() + 10
        url = f"http://127.0.0.1:{port}/health"
        while time.time() < deadline:
            try:
                urllib.request.urlopen(url, timeout=0.5).read()
                break
            except Exception:
                time.sleep(0.3)
        else:
            pytest.skip("Server failed to start in 10 s")

        from chakravyuh_env.openenv_client import ChakravyuhEnvClient

        with ChakravyuhEnvClient(base_url=f"http://127.0.0.1:{port}").sync() as env:
            r = env.reset(seed=42)
            assert not r.done
            assert r.observation.turn >= 2
            assert len(r.observation.chat_history) >= 2

            r = env.step(_A(score=0.9, signals=["urgency"]))
            if not r.done:
                r = env.step(_A(score=0.9, signals=["impersonation"]))

            assert r.done is True
            assert r.reward is not None
            assert r.observation.outcome is not None
            assert r.observation.reward_breakdown is not None
            assert r.observation.outcome.get("analyzer_flagged") is True
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
