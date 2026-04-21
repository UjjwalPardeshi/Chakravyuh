"""Scripted Behavioral Analyzer — Day-1 rule-based baseline.

This is the agent we will replace with a LoRA-trained Qwen2.5-7B on Day 2.
For Day 1, it demonstrates the detection pipeline end-to-end using keyword
heuristics. Baseline detection rate expected ~35-50%.

Signals tracked:
  - URGENCY keywords
  - IMPERSONATION phrases (bank/govt self-identification)
  - INFO_REQUEST (OTP/Aadhaar/CVV/PIN mentions)
  - SUSPICIOUS_LINK (http URLs in chat)
  - UNKNOWN_SENDER (first-contact heuristic)
"""

from __future__ import annotations

import re
from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    AnalyzerScore,
    AnalyzerSignal,
    Observation,
)

_URGENCY_KEYWORDS = [
    "urgent", "immediately", "now", "expires", "last chance", "within", "minutes",
    "hours left", "don't miss", "hurry", "act fast", "deadline",
]
_IMPERSONATION_PHRASES = [
    "sbi", "hdfc", "icici", "axis bank", "yes bank", "kotak", "canara", "pnb",
    "rbi", "uidai", "income tax", "gst", "epfo", "pm ", "government", "police",
    "cyber cell", "customer care", "fraud team",
]
_INFO_KEYWORDS = {
    AnalyzerSignal.INFO_REQUEST: [
        "otp", "share otp", "pin", "upi pin", "aadhaar", "adhar", "pan number",
        "cvv", "card number", "bank details", "account number", "password",
    ],
}
_URL_PATTERN = re.compile(r"https?://\S+")
_SUSPICIOUS_TLDS = [".xyz", ".top", ".click", ".co", ".tk", ".gq", ".ml", ".in-kyc"]


class ScriptedAnalyzer(Agent):
    """Rule-based baseline. Outputs suspicion score + explanation every turn."""

    def __init__(self, flag_threshold: float = 0.55, seed: int | None = None) -> None:
        super().__init__(name="analyzer", seed=seed)
        self.flag_threshold = flag_threshold

    def act(self, observation: Observation) -> Any:
        signals: list[AnalyzerSignal] = []
        score = 0.0
        text_all = " ".join(m.text.lower() for m in observation.chat_history if m.sender == "scammer")

        if _contains_any(text_all, _URGENCY_KEYWORDS):
            signals.append(AnalyzerSignal.URGENCY)
            score += 0.25
        if _contains_any(text_all, _IMPERSONATION_PHRASES):
            signals.append(AnalyzerSignal.IMPERSONATION)
            score += 0.20
        if _contains_any(text_all, _INFO_KEYWORDS[AnalyzerSignal.INFO_REQUEST]):
            signals.append(AnalyzerSignal.INFO_REQUEST)
            score += 0.35
        if _has_suspicious_link(text_all):
            signals.append(AnalyzerSignal.SUSPICIOUS_LINK)
            score += 0.25
        if observation.turn <= 2:
            signals.append(AnalyzerSignal.UNKNOWN_SENDER)
            score += 0.05

        score = min(1.0, score)
        explanation = _build_explanation(signals)
        return AnalyzerScore(score=score, signals=signals, explanation=explanation)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def _has_suspicious_link(text: str) -> bool:
    for url in _URL_PATTERN.findall(text):
        low = url.lower()
        if any(tld in low for tld in _SUSPICIOUS_TLDS):
            return True
        if "bit.ly" in low or "tinyurl" in low or "t.me" in low:
            return True
    return False


def _build_explanation(signals: list[AnalyzerSignal]) -> str:
    if not signals:
        return "No suspicion signals detected."
    parts = [s.value.replace("_", " ") for s in signals]
    return "Detected: " + ", ".join(parts) + "."
