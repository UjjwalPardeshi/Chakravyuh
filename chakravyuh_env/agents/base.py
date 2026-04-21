"""Base Agent interface.

All agents in Chakravyuh implement this minimal contract so scripted, LLM-backed,
and LoRA-trained agents are interchangeable in the environment loop.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from chakravyuh_env.schemas import Observation


class Agent(ABC):
    """Abstract base: observe → act. Deterministic given seed."""

    def __init__(self, name: str, seed: int | None = None) -> None:
        self.name = name
        self._rng = random.Random(seed)

    @abstractmethod
    def act(self, observation: Observation) -> object:
        """Return an action validated by the agent-specific Pydantic schema."""

    def reset(self, seed: int | None = None) -> None:
        """Reset internal state. Called at the start of each episode."""
        if seed is not None:
            self._rng = random.Random(seed)
