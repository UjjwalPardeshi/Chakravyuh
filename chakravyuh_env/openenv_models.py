"""OpenEnv-compliant Action / Observation / State models for Chakravyuh.

These extend `openenv.core.env_server.{Action, Observation, State}` so
Chakravyuh plugs cleanly into the Meta PyTorch OpenEnv framework
(`Environment`, `create_app`, `EnvClient`).

The design:
    - Action  = a single analyzer decision (suspicion score + signals + explanation)
    - Observation = the chat history visible up to the current analyzer decision
                    point, plus the optional pending transaction at the bank turn
    - State  = full episode bookkeeping (flag status, outcome flags, etc.)

An episode exposes 2 analyzer decision points per conversation (mid-turn and
pre-transaction), corresponding to internal turns 3 and 6 of the underlying
multi-agent simulation. See `openenv_environment.ChakravyuhOpenEnv`.
"""

from __future__ import annotations

from typing import Any

from openenv.core.env_server import Action, Observation, State
from pydantic import Field


class ChakravyuhAction(Action):
    """Analyzer decision for one turn of the conversation.

    score: suspicion score in [0, 1]
    flag_threshold: pinned at 0.5. The training/eval reward and the env's
        flag-decision logic both compare ``score >= flag_threshold``. Allowing
        the agent to tune the threshold opens an exploit:
        ``score=0.95, flag_threshold=0.99`` collects calibration credit
        without paying the false-positive penalty (audit P2 reward-design).
        We accept any value in [0.5, 0.5] — i.e. exactly 0.5 — to keep the
        wire format unchanged while removing the gaming surface.
    signals: string names of AnalyzerSignal enum values (e.g. ``"urgency"``).
        Accepted as strings on the wire for maximum client-language
        portability; validated on the server against the AnalyzerSignal enum.
    explanation: short natural-language justification (≤300 chars).
    """

    score: float = Field(ge=0.0, le=1.0)
    flag_threshold: float = Field(default=0.5, ge=0.5, le=0.5)
    signals: list[str] = Field(default_factory=list)
    explanation: str = Field(default="", max_length=300)


class ChakravyuhObservation(Observation):
    """Partial observation for the analyzer at a decision point.

    chat_history: ordered list of ``{sender, turn, text, intent}`` dicts.
    turn: 1-indexed internal turn number of the simulation at this obs.
    transaction: optional dict ``{amount, receiver_new, receiver_id_hash,
        frequency_24h}`` — present only at the final decision point.
    decision_index: 0 for first decision, 1 for second, -1 when episode is
        terminal (no further action required).

    episode_id / scam_category / victim_profile / outcome / reward_breakdown
    are only populated on the terminal observation (when ``done=True``).
    They are explicit fields (not stashed in ``metadata``) because OpenEnv's
    ``serialize_observation`` strips ``metadata`` from the wire payload.
    """

    chat_history: list[dict[str, Any]] = Field(default_factory=list)
    turn: int = Field(default=0, ge=0)
    transaction: dict[str, Any] | None = None
    decision_index: int = Field(default=0)
    # Populated for every observation (survives the wire).
    episode_id: str | None = None
    scam_category: str | None = None
    victim_profile: str | None = None
    # Populated only on terminal observations.
    outcome: dict[str, Any] | None = None
    reward_breakdown: dict[str, Any] | None = None
    # Inherited from Observation: done, reward, metadata


class ChakravyuhState(State):
    """Episode state snapshot for introspection / debugging.

    scam_category / victim_profile are None until the first reset.
    """

    scam_category: str | None = None
    victim_profile: str | None = None
    analyzer_flagged: bool = False
    analyzer_flag_turn: int | None = None
    victim_complied: bool = False
    victim_refused: bool = False
    victim_sought_verification: bool = False
    bank_flagged: bool = False
    bank_froze: bool = False
    money_extracted: bool = False
    done: bool = False
