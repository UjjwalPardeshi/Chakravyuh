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
    "hours left", "don't miss", "hurry", "act fast", "deadline", "last date",
    "closes", "expiring", "expired", "cancel", "suspended", "block", "blocked",
    "turant", "jaldi", "abhi", "last 24", "valid till",
]
_IMPERSONATION_PHRASES = [
    # Banks
    "sbi", "hdfc", "icici", "axis bank", "yes bank", "kotak", "canara", "pnb",
    "indusind", "federal bank", "idfc", "rbl", "dbs", "au small", "bob ", "bank of",
    "indian bank", "union bank", "karur vysya", "muthoot",
    # Govt / regulators
    "rbi", "uidai", "income tax", "gst", "epfo", "pm ", "government", "police",
    "cyber cell", "customer care", "fraud team", "cbi", "trai", "uidai",
    "election commission", "ministry of", "it department", "lic", "indiapost",
    "crime branch",
    # Brands used for impersonation
    "amazon", "flipkart", "paytm", "phonepe", "gpay", "bhim", "bharatpe", "cred",
    "swiggy", "zomato", "blinkit", "dtdc", "fedex",
    # Self-identification phrases
    "this is", "main ", "bol raha", "calling from", "se hoon", "manager",
    "officer", "agent", "from sbi", "from hdfc", "fraud department",
]
_INFO_KEYWORDS = {
    AnalyzerSignal.INFO_REQUEST: [
        "otp", "share otp", "pin", "upi pin", "aadhaar", "adhar", "pan number",
        "cvv", "card number", "bank details", "account number", "password",
        "share the otp", "tell me otp", "read otp", "otp share", "otp batao",
        "pan ", "aadhaar photo", "photo bhejo", "verification code",
    ],
}
# Investment / loan / reward language — strong fraud indicators
_FINANCIAL_LURE_KEYWORDS = [
    "guaranteed return", "double your money", "doubling", "daily profit",
    "intraday tip", "stock tip", "pre-approved", "pre approved", "loan approved",
    "no documents", "no credit check", "instant loan", "processing fee",
    "gst charge", "activation fee", "evaluation charge", "membership fee",
    "you won", "lucky draw", "prize", "cashback", "reward", "refund pending",
    "refund stuck", "refund of rs", "deposit rs", "transfer rs", "pay rs",
    "invest rs", "send rs", "rs 999", "rs 499", "rs 299", "rs 1,", "rs 2,",
    "2% interest", "1% interest", "subvention",
]
_URL_PATTERN = re.compile(r"https?://\S+")
_SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".click", ".co", ".tk", ".gq", ".ml", ".in-kyc", ".in-update",
    ".in-gov", ".gov-in", ".gov-india", ".app-loan", ".in-gold", ".in-pan",
]
_URL_SHORTENERS = ["bit.ly", "tinyurl", "t.me", "ow.ly", "is.gd", "buff.ly"]


class ScriptedAnalyzer(Agent):
    """Rule-based baseline. Outputs suspicion score + explanation every turn."""

    def __init__(self, flag_threshold: float = 0.50, seed: int | None = None) -> None:
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
            score += 0.22
        if _contains_any(text_all, _INFO_KEYWORDS[AnalyzerSignal.INFO_REQUEST]):
            signals.append(AnalyzerSignal.INFO_REQUEST)
            score += 0.38
        if _has_suspicious_link(text_all):
            signals.append(AnalyzerSignal.SUSPICIOUS_LINK)
            score += 0.25
        if _contains_any(text_all, _FINANCIAL_LURE_KEYWORDS):
            # Reuse SUSPICIOUS_LINK as proxy for "financial lure" signal
            # in the limited enum. Logged in explanation separately.
            signals.append(AnalyzerSignal.UNUSUAL_AMOUNT)
            score += 0.20
        if observation.turn <= 2:
            signals.append(AnalyzerSignal.UNKNOWN_SENDER)
            score += 0.05

        # Multi-signal co-occurrence bonus — urgency + info_request is a
        # very strong combined indicator (both present in ~80% of real scams).
        if AnalyzerSignal.URGENCY in signals and AnalyzerSignal.INFO_REQUEST in signals:
            score += 0.08
        if AnalyzerSignal.IMPERSONATION in signals and AnalyzerSignal.INFO_REQUEST in signals:
            score += 0.06

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
        if any(short in low for short in _URL_SHORTENERS):
            return True
    # Also flag non-URL mentions of shorteners
    return any(short in text for short in _URL_SHORTENERS)


def _build_explanation(signals: list[AnalyzerSignal]) -> str:
    if not signals:
        return "No suspicion signals detected."
    parts = [s.value.replace("_", " ") for s in signals]
    return "Detected: " + ", ".join(parts) + "."
