"""Chakravyuh — multi-agent RL environment for Indian UPI fraud detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chakravyuh_env.environment import ChakravyuhEnv
from chakravyuh_env.openenv_environment import ChakravyuhOpenEnv
from chakravyuh_env.openenv_models import (
    ChakravyuhAction,
    ChakravyuhObservation,
    ChakravyuhState,
)
from chakravyuh_env.reward import RewardBreakdown, compute_rewards
from chakravyuh_env.rubrics import (
    AnalyzerRubric,
    AnalyzerRubricV2,
    CalibrationRubric,
    DetectionRubric,
    ExplanationRubric,
    FalsePositiveRubric,
    FormatRubric,
    LengthRubric,
    MissedScamRubric,
    RupeeWeightedRubric,
    SignalAccuracyRubric,
    V2_WEIGHTS,
)
from chakravyuh_env.schemas import (
    EpisodeLog,
    EpisodeOutcome,
    Observation,
    ScamCategory,
    VictimProfile,
)

if TYPE_CHECKING:
    from chakravyuh_env.agents.llm_analyzer import LLMAnalyzer

__version__ = "0.1.0"

# Default v2 LoRA adapter on the Hugging Face Hub.
DEFAULT_ANALYZER_ADAPTER = "ujjwalpardeshi/chakravyuh-analyzer-lora-v2"
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def get_trained_analyzer(
    adapter: str = DEFAULT_ANALYZER_ADAPTER,
    base_model: str = DEFAULT_BASE_MODEL,
    **config_overrides: object,
) -> "LLMAnalyzer":
    """Return an `LLMAnalyzer` pre-wired to the v2 LoRA adapter on the Hub.

    Lazy import of `LLMAnalyzer` avoids forcing the heavy `transformers` /
    `torch` dependencies on users who only want the env, not the trained model.

    Example
    -------
    >>> from chakravyuh_env import get_trained_analyzer  # doctest: +SKIP
    >>> analyzer = get_trained_analyzer()                # doctest: +SKIP
    >>> analyzer("Urgent! Share OTP to verify identity.")  # doctest: +SKIP
    {'score': 0.95, 'signals': ['urgency', ...], 'explanation': '...'}

    Parameters
    ----------
    adapter
        HF Hub repo id or local path of the LoRA adapter to load.
        Defaults to `ujjwalpardeshi/chakravyuh-analyzer-lora-v2`.
    base_model
        HF Hub repo id of the base model. Defaults to `Qwen/Qwen2.5-7B-Instruct`.
    **config_overrides
        Forwarded to `LLMAnalyzerConfig` (e.g. `device="cpu"`, `temperature=0.1`).

    Returns
    -------
    LLMAnalyzer
        Analyzer instance with `__call__(text) -> dict` and the existing
        `score_text(text) -> float` / `act(observation) -> AnalyzerScore` methods.
        Model weights are loaded lazily on first call.
    """
    from chakravyuh_env.agents.llm_analyzer import LLMAnalyzer

    return LLMAnalyzer(
        model_name=base_model,
        lora_path=adapter,
        **config_overrides,  # type: ignore[arg-type]
    )


__all__ = [
    "ChakravyuhEnv",
    "ChakravyuhOpenEnv",
    "ChakravyuhAction",
    "ChakravyuhObservation",
    "ChakravyuhState",
    "AnalyzerRubric",
    "AnalyzerRubricV2",
    "DetectionRubric",
    "MissedScamRubric",
    "FalsePositiveRubric",
    "CalibrationRubric",
    "ExplanationRubric",
    "SignalAccuracyRubric",
    "FormatRubric",
    "LengthRubric",
    "V2_WEIGHTS",
    "RewardBreakdown",
    "compute_rewards",
    "EpisodeLog",
    "EpisodeOutcome",
    "Observation",
    "ScamCategory",
    "VictimProfile",
    "get_trained_analyzer",
    "DEFAULT_ANALYZER_ADAPTER",
    "DEFAULT_BASE_MODEL",
]
