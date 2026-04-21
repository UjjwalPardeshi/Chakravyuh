"""Scripted Bank Monitor — oversight on transaction metadata only.

The Bank Monitor never sees chat content (partial observability, Part 2.4).
It only sees transaction amount, receiver novelty, frequency, and account history.
Day-1 baseline uses simple rules; later swappable for an LLM judge.
"""

from __future__ import annotations

from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    BankApprove,
    BankFlag,
    BankFreeze,
    Observation,
)


class ScriptedBankMonitor(Agent):
    def __init__(
        self,
        large_amount_threshold: float = 20000.0,
        new_payee_amount_threshold: float = 5000.0,
        freeze_confidence: float = 0.85,
        seed: int | None = None,
    ) -> None:
        super().__init__(name="bank_monitor", seed=seed)
        self.large_amount_threshold = large_amount_threshold
        self.new_payee_amount_threshold = new_payee_amount_threshold
        self.freeze_confidence = freeze_confidence

    def act(self, observation: Observation) -> Any:
        tx = observation.transaction
        if tx is None:
            return BankApprove(confidence=0.5)

        risk = 0.0
        reasons: list[str] = []

        if tx.receiver_new and tx.amount >= self.new_payee_amount_threshold:
            risk += 0.45
            reasons.append(f"new payee + Rs {tx.amount:.0f}")
        if tx.amount >= self.large_amount_threshold:
            risk += 0.25
            reasons.append(f"large amount Rs {tx.amount:.0f}")
        if tx.frequency_24h >= 3:
            risk += 0.15
            reasons.append(f"{tx.frequency_24h} txns in 24h")

        risk = min(1.0, risk)

        if risk >= self.freeze_confidence:
            return BankFreeze(reason="; ".join(reasons) or "high composite risk")
        if risk >= 0.40:
            return BankFlag(signal="; ".join(reasons), confidence=risk)
        return BankApprove(confidence=1.0 - risk)
