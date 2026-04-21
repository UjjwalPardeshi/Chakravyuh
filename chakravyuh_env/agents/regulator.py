"""Regulator meta-agent — adapts detection rule weights every N episodes.

The Regulator is the self-improvement loop at the environment level:
  1. Aggregates episode outcomes
  2. Identifies patterns that still succeed (low catch rate)
  3. Publishes rule-weight updates to the Analyzer's signal weights
  4. Never sees individual chat/tx content (aggregate-only)

This implements the Theme 4 (Self-Improving) primary claim.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    EpisodeOutcome,
    Observation,
    RegulatorAddRule,
    RegulatorBulletin,
)


class ScriptedRegulator(Agent):
    def __init__(self, update_every: int = 10, seed: int | None = None) -> None:
        super().__init__(name="regulator", seed=seed)
        self.update_every = update_every
        self._outcome_buffer: list[EpisodeOutcome] = []
        self._rule_weights: dict[str, float] = {
            "urgency": 0.25,
            "impersonation": 0.20,
            "info_request": 0.35,
            "suspicious_link": 0.25,
        }

    @property
    def rule_weights(self) -> dict[str, float]:
        return dict(self._rule_weights)

    def log_outcome(self, outcome: EpisodeOutcome) -> None:
        self._outcome_buffer.append(outcome)

    def should_update(self) -> bool:
        return len(self._outcome_buffer) > 0 and len(self._outcome_buffer) % self.update_every == 0

    def act(self, observation: Observation) -> Any:
        """Called when should_update() is True. Returns a rule update action."""
        if not self._outcome_buffer:
            return RegulatorBulletin(pattern_detected="none", guidance="baseline")

        recent = self._outcome_buffer[-self.update_every:]
        miss_categories = Counter(
            o.scam_category.value for o in recent if not o.analyzer_flagged and o.money_extracted
        )
        if not miss_categories:
            return RegulatorBulletin(
                pattern_detected="all_detected",
                guidance=f"catch rate stable after {len(self._outcome_buffer)} episodes",
            )

        most_missed, count = miss_categories.most_common(1)[0]
        signal_key = _category_to_signal(most_missed)
        old_w = self._rule_weights.get(signal_key, 0.10)
        new_w = min(1.0, old_w + 0.05)
        self._rule_weights[signal_key] = new_w

        return RegulatorAddRule(signal=signal_key, weight=new_w)


def _category_to_signal(category: str) -> str:
    mapping = {
        "otp_theft": "info_request",
        "kyc_fraud": "suspicious_link",
        "loan_app_fraud": "suspicious_link",
        "investment_fraud": "urgency",
        "impersonation": "impersonation",
    }
    return mapping.get(category, "urgency")
