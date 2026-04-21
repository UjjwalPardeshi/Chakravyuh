"""Chakravyuh — multi-agent RL environment for Indian UPI fraud detection."""

from chakravyuh_env.environment import ChakravyuhEnv
from chakravyuh_env.reward import RewardBreakdown, compute_rewards
from chakravyuh_env.schemas import (
    EpisodeLog,
    EpisodeOutcome,
    Observation,
    ScamCategory,
    VictimProfile,
)

__version__ = "0.1.0"

__all__ = [
    "ChakravyuhEnv",
    "RewardBreakdown",
    "compute_rewards",
    "EpisodeLog",
    "EpisodeOutcome",
    "Observation",
    "ScamCategory",
    "VictimProfile",
]
