"""Scripted Victim agent with demographic-profile-driven trust dynamics.

The Victim is not trained. It simulates realistic human responses based on:
  - base gullibility per profile (SENIOR > SEMI_URBAN > YOUNG_URBAN)
  - rolling trust level updated by scammer's intent + info requests
  - threshold decision: comply / refuse / question / call_bank

Curriculum is handled by the environment via a gullibility multiplier.
"""

from __future__ import annotations

from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    InfoField,
    Intent,
    Observation,
    VictimCallBank,
    VictimComply,
    VictimProfile,
    VictimQuestion,
    VictimRefuse,
    VictimRespond,
)

# Base trust level per profile. Higher = more gullible.
_PROFILE_BASE_TRUST: dict[VictimProfile, float] = {
    VictimProfile.SENIOR: 0.65,
    VictimProfile.SEMI_URBAN: 0.45,
    VictimProfile.YOUNG_URBAN: 0.25,
}

# Intent → trust delta (how much a message of this style nudges trust).
_INTENT_TRUST_DELTA: dict[Intent, float] = {
    Intent.URGENCY: -0.05,   # urgency triggers slight suspicion
    Intent.AUTHORITY: +0.10,  # authority builds trust
    Intent.EMPATHY: +0.08,
    Intent.GREED: -0.02,
    Intent.FEAR: +0.03,
}


class ScriptedVictim(Agent):
    def __init__(
        self,
        profile: VictimProfile = VictimProfile.SEMI_URBAN,
        gullibility_multiplier: float = 1.0,
        seed: int | None = None,
    ) -> None:
        super().__init__(name="victim", seed=seed)
        self.profile = profile
        self.gullibility = gullibility_multiplier
        self._trust: float = 0.0

    def reset(self, seed: int | None = None) -> None:
        super().reset(seed)
        self._trust = _PROFILE_BASE_TRUST[self.profile] * self.gullibility
        self._trust = max(0.0, min(1.0, self._trust))

    @property
    def trust(self) -> float:
        return self._trust

    def act(self, observation: Observation) -> Any:
        last_scammer_msg = _last_scammer_message(observation)
        if last_scammer_msg is not None and last_scammer_msg.intent is not None:
            delta = _INTENT_TRUST_DELTA.get(last_scammer_msg.intent, 0.0)
            self._trust = max(0.0, min(1.0, self._trust + delta * self.gullibility))

        # Decision logic based on last action type. The scammer's most recent
        # intent influences whether we comply, refuse, question, or call bank.
        info_field = _detect_info_request(observation)
        if info_field is not None:
            if self._trust > 0.55:
                return VictimComply(field=info_field, value=_fake_value_for(info_field))
            if self._trust > 0.30:
                return VictimQuestion(target_info=info_field.value)
            return VictimRefuse(reason="Request seems suspicious")

        # No explicit info request — general chat response
        if self._trust > 0.70:
            return VictimRespond(text="Okay, tell me more.", trust_delta=+0.05)
        if self._trust < 0.20:
            return VictimCallBank()
        return VictimRespond(text="Who is this? Can you verify?", trust_delta=-0.03)


def _last_scammer_message(observation: Observation):
    for msg in reversed(observation.chat_history):
        if msg.sender == "scammer":
            return msg
    return None


def _detect_info_request(observation: Observation) -> InfoField | None:
    """Shallow heuristic: if latest scammer text mentions OTP/Aadhaar/etc., flag."""
    last = _last_scammer_message(observation)
    if last is None:
        return None
    text = last.text.lower()
    if "otp" in text:
        return InfoField.OTP
    if "aadhaar" in text or "adhar" in text:
        return InfoField.AADHAAR
    if "pan" in text and "paytm" not in text:
        return InfoField.PAN
    if "cvv" in text:
        return InfoField.CVV
    if "upi" in text and ("send" in text or "transfer" in text or "pay" in text):
        return InfoField.BANK_ACCOUNT
    if "pin" in text:
        return InfoField.PIN
    return None


def _fake_value_for(field: InfoField) -> str:
    """Placeholder sensitive value for compliance path — never real data."""
    return {
        InfoField.OTP: "XXXXXX",
        InfoField.PIN: "XXXX",
        InfoField.AADHAAR: "XXXX-XXXX-XXXX",
        InfoField.PAN: "XXXXX0000X",
        InfoField.CVV: "XXX",
        InfoField.CARD_NUMBER: "XXXX-XXXX-XXXX-XXXX",
        InfoField.BANK_ACCOUNT: "XXXXXXXX",
    }[field]
