"""Client for the Chakravyuh OpenEnv server.

Subclasses ``openenv.core.env_client.EnvClient`` to provide type-safe
reset / step / state calls against a running Chakravyuh HTTP server.

Example:
    >>> from chakravyuh_env.openenv_client import ChakravyuhEnvClient
    >>> from chakravyuh_env.openenv_models import ChakravyuhAction
    >>>
    >>> with ChakravyuhEnvClient(base_url="http://localhost:8000").sync() as env:
    ...     result = env.reset(seed=42)
    ...     obs = result.observation
    ...     # Analyzer LLM scores the chat
    ...     action = ChakravyuhAction(
    ...         score=0.82,
    ...         signals=["urgency", "info_request"],
    ...         explanation="Asks for OTP with urgency pressure.",
    ...     )
    ...     result = env.step(action)
    ...     if not result.done:
    ...         action2 = ChakravyuhAction(score=0.9, signals=["impersonation"])
    ...         result = env.step(action2)
    ...     print(result.reward, result.observation.metadata)
"""

from __future__ import annotations

from typing import Any

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from chakravyuh_env.openenv_models import (
    ChakravyuhAction,
    ChakravyuhObservation,
    ChakravyuhState,
)


class ChakravyuhEnvClient(
    EnvClient[ChakravyuhAction, ChakravyuhObservation, ChakravyuhState]
):
    """WebSocket/HTTP client for Chakravyuh OpenEnv servers."""

    def _step_payload(self, action: ChakravyuhAction) -> dict[str, Any]:
        return action.model_dump()

    def _parse_result(
        self, payload: dict[str, Any]
    ) -> StepResult[ChakravyuhObservation]:
        obs_data = payload.get("observation", {})
        reward = payload.get("reward")
        done = payload.get("done", False)

        observation = ChakravyuhObservation(
            chat_history=obs_data.get("chat_history", []),
            turn=obs_data.get("turn", 0),
            transaction=obs_data.get("transaction"),
            decision_index=obs_data.get("decision_index", 0),
            episode_id=obs_data.get("episode_id"),
            scam_category=obs_data.get("scam_category"),
            victim_profile=obs_data.get("victim_profile"),
            outcome=obs_data.get("outcome"),
            reward_breakdown=obs_data.get("reward_breakdown"),
            done=done,
            reward=reward,
        )
        return StepResult(observation=observation, reward=reward, done=done)

    def _parse_state(self, payload: dict[str, Any]) -> ChakravyuhState:
        return ChakravyuhState(**payload)
