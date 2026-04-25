"""Scripted Bank Monitor — oversight on transaction metadata only.

The Bank Monitor never sees chat content (partial observability, Part 2.4).
It only sees transaction amount, receiver novelty, frequency, and account history.
Day-1 baseline uses simple rules; later swappable for an LLM judge.
"""

from __future__ import annotations

from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    AnalyzerConsultation,
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
        return self._decide(observation, consultation=None)

    def act_with_consultation(
        self,
        observation: Observation,
        consultation: AnalyzerConsultation,
    ) -> Any:
        """Decide *with* the Analyzer's consultation — the negotiation hook.

        Combines the bank-side risk (transaction metadata) and the analyzer-
        side risk (chat signals, summarised in ``consultation``) into a single
        composite risk. The bank still does not see chat content — only the
        consultation surface (``score``, ``signals``, ``flagged``).

        See ``docs/negotiation_protocol.md`` for the protocol semantics and
        the rationale for the linear combination weight (``0.6`` bank-side,
        ``0.4`` analyzer-side).
        """
        return self._decide(observation, consultation=consultation)

    # ---- internals ----------------------------------------------------

    def _decide(
        self,
        observation: Observation,
        consultation: AnalyzerConsultation | None,
    ) -> Any:
        tx = observation.transaction
        if tx is None:
            return BankApprove(confidence=0.5)

        bank_risk = 0.0
        reasons: list[str] = []

        if tx.receiver_new and tx.amount >= self.new_payee_amount_threshold:
            bank_risk += 0.45
            reasons.append(f"new payee + Rs {tx.amount:.0f}")
        if tx.amount >= self.large_amount_threshold:
            bank_risk += 0.25
            reasons.append(f"large amount Rs {tx.amount:.0f}")
        if tx.frequency_24h >= 3:
            bank_risk += 0.15
            reasons.append(f"{tx.frequency_24h} txns in 24h")

        bank_risk = min(1.0, bank_risk)

        if consultation is not None:
            analyzer_risk = float(consultation.score)
            # 0.6 bank / 0.4 analyzer — bank is authoritative on metadata,
            # analyzer adds chat-side context. Documented in
            # docs/negotiation_protocol.md §"Risk combiner".
            risk = 0.6 * bank_risk + 0.4 * analyzer_risk
            if consultation.flagged:
                tag = "+".join(consultation.signals) if consultation.signals else "flag"
                reasons.append(f"analyzer says scam ({tag}, s={analyzer_risk:.2f})")
            elif analyzer_risk > 0.0 and reasons:
                reasons.append(f"analyzer s={analyzer_risk:.2f}")
        else:
            risk = bank_risk

        if risk >= self.freeze_confidence:
            return BankFreeze(reason="; ".join(reasons) or "high composite risk")
        if risk >= 0.40:
            return BankFlag(signal="; ".join(reasons), confidence=risk)
        return BankApprove(confidence=1.0 - risk)
