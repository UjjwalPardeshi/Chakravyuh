"""Scripted Scammer agent.

Draws from 50 hand-curated attack templates (NPCI/RBI-grounded). For the
template-based scripted scammer, each episode samples one template and
executes its turn progression deterministically given the seed.

This is the Day-1 baseline. An LLM-backed Scammer subclass can later plug
in via the same Agent interface, but per the improvements plan (Move 3)
we ship with the scripted Scammer and train only the Analyzer LoRA.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    ImpersonationRole,
    InfoField,
    Intent,
    LinkKind,
    Observation,
    ScammerEndScam,
    ScammerEscalateUrgency,
    ScammerImpersonate,
    ScammerRequestInfo,
    ScammerSendLink,
    ScammerSendMessage,
)

_DEFAULT_TEMPLATES = Path(__file__).resolve().parent.parent / "scammer_templates.json"


class ScriptedScammer(Agent):
    """Selects an attack template at reset() and plays it over the episode."""

    def __init__(
        self,
        templates_path: Path = _DEFAULT_TEMPLATES,
        seed: int | None = None,
    ) -> None:
        super().__init__(name="scammer", seed=seed)
        with open(templates_path, encoding="utf-8") as f:
            data = json.load(f)
        self._templates: list[dict[str, Any]] = data["templates"]
        self._current: dict[str, Any] | None = None
        self._turn_plan: list[str] = []

    def reset(self, seed: int | None = None) -> None:
        super().reset(seed)
        self._current = self._rng.choice(self._templates)
        # Fixed turn progression: open → impersonate → request → escalate → send_link → end
        # Only turns that are valid for the template are kept.
        plan = ["opener"]
        if self._current.get("impersonation"):
            plan.append("impersonate")
        if self._current.get("info_request"):
            plan.append("request_info")
        plan.append("escalate")
        if self._current.get("link"):
            plan.append("send_link")
        plan.append("end")
        self._turn_plan = plan

    def current_template(self) -> dict[str, Any]:
        if self._current is None:
            raise RuntimeError("reset() must be called before current_template()")
        return self._current

    def act(self, observation: Observation) -> list[Any]:
        """Return ALL plan steps scheduled for this scammer turn.

        Turn 1: opener + impersonate + request_info  (opening salvo)
        Turn 4: escalate + send_link                 (pressure phase)
        Turn 7: (env handles tx; scammer idle)
        """
        if self._current is None:
            self.reset()
        assert self._current is not None

        turn = observation.turn
        steps: list[str] = []
        if turn == 1:
            steps.append("opener")
            if self._current.get("impersonation"):
                steps.append("impersonate")
            if self._current.get("info_request"):
                steps.append("request_info")
        elif turn == 4:
            steps.append("escalate")
            if self._current.get("link"):
                steps.append("send_link")
        else:
            steps.append("end")
        return [self._build_action(step) for step in steps]

    def _build_action(self, step: str) -> Any:
        assert self._current is not None
        t = self._current
        intent = Intent(t["intent"])
        if step == "opener":
            return ScammerSendMessage(text=t["opener"], intent=intent)
        if step == "impersonate":
            role = ImpersonationRole(t["impersonation"])
            return ScammerImpersonate(role=role, claimed_identity=_identity_for(role))
        if step == "request_info":
            return ScammerRequestInfo(
                field=InfoField(t["info_request"]),
                pretext=t["opener"][:200],
            )
        if step == "escalate":
            return ScammerSendMessage(text=t["escalation"], intent=intent)
        if step == "send_link":
            kind = LinkKind(t["link"])
            return ScammerSendLink(kind=kind, url=_extract_url(t))
        return ScammerEndScam(reason="plan_complete")


def _identity_for(role: ImpersonationRole) -> str:
    identities = {
        ImpersonationRole.BANK: "SBI Customer Care Officer",
        ImpersonationRole.GOVERNMENT: "Income Tax Department Official",
        ImpersonationRole.FAMILY: "Cousin / Uncle",
        ImpersonationRole.EMPLOYER: "Loan / Investment Agent",
        ImpersonationRole.DELIVERY: "Amazon / Flipkart / Zomato Delivery",
    }
    return identities[role]


def _extract_url(template: dict[str, Any]) -> str:
    """Pull URL from opener/escalation text; fall back to generic."""
    for key in ("opener", "escalation"):
        text = template.get(key, "")
        for token in text.split():
            if token.startswith(("http://", "https://")):
                return token.rstrip(".,")
    return "https://suspicious.example.com"
