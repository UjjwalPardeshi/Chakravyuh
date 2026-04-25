"""Bank–Analyzer negotiation protocol tests (C.6).

Verifies the optional Analyzer↔Bank consultation hook:

  1. Backward compat: ``enable_negotiation=False`` (default) is identical to
     pre-C.6 behavior — no consultation is sent, no bank decision changes.
  2. Forward effect: with ``enable_negotiation=True`` and a high-confidence
     analyzer flag, the bank's combined risk crosses the freeze threshold on
     borderline transactions.
  3. Containment: the consultation surface contains *no* chat content — only
     score/signals/threshold/flagged. This is the privacy invariant that
     keeps the on-device deployment story consistent.

Spec: ``docs/negotiation_protocol.md``.
"""

from __future__ import annotations

import pytest

from chakravyuh_env.agents.bank_monitor import ScriptedBankMonitor
from chakravyuh_env.openenv_environment import ChakravyuhOpenEnv
from chakravyuh_env.openenv_models import ChakravyuhAction
from chakravyuh_env.schemas import (
    AnalyzerConsultation,
    BankApprove,
    BankFlag,
    BankFreeze,
    Observation,
    TransactionMeta,
)


# --- consultation surface (privacy contract) ---------------------------------


@pytest.mark.unit
def test_consultation_carries_no_chat_content() -> None:
    """The consultation type only exposes score/signals/threshold/flagged."""
    consultation = AnalyzerConsultation(
        score=0.92,
        signals=("urgency", "info_request"),
        threshold=0.55,
        flagged=True,
    )
    fields = set(AnalyzerConsultation.model_fields.keys())
    assert fields == {"score", "signals", "threshold", "flagged"}, (
        "consultation surface must not grow chat-content fields without explicit review"
    )


# --- bank-side risk combiner -------------------------------------------------


def _borderline_tx() -> TransactionMeta:
    """Borderline transaction — bank-only risk is just under the freeze threshold."""
    return TransactionMeta(
        amount=10000.0,
        receiver_new=True,
        receiver_id_hash="rx_test",
        frequency_24h=0,
    )


def _bank_obs(tx: TransactionMeta) -> Observation:
    return Observation(agent_role="bank", turn=8, transaction=tx)


@pytest.mark.unit
def test_bank_without_consultation_matches_act() -> None:
    """`act_with_consultation` w/o consultation must equal the original `act`."""
    bank = ScriptedBankMonitor(seed=42)
    obs = _bank_obs(_borderline_tx())

    a1 = bank.act(obs)
    a2 = bank._decide(obs, consultation=None)
    assert type(a1) is type(a2)
    assert a1.model_dump() == a2.model_dump()


@pytest.mark.unit
def test_high_analyzer_score_escalates_bank_decision() -> None:
    """A confident analyzer flag pushes a borderline tx toward freeze/flag."""
    bank = ScriptedBankMonitor(seed=42)
    obs = _bank_obs(_borderline_tx())

    no_consult = bank.act(obs)
    with_consult = bank.act_with_consultation(
        obs,
        AnalyzerConsultation(score=0.95, signals=("urgency",), flagged=True),
    )

    # Either the action class strengthens (Approve→Flag, or Flag→Freeze)
    # or the same-class confidence rises (Flag confidence increases).
    if isinstance(no_consult, BankApprove):
        assert isinstance(with_consult, (BankFlag, BankFreeze))
    elif isinstance(no_consult, BankFlag) and isinstance(with_consult, BankFlag):
        assert with_consult.confidence >= no_consult.confidence
    else:  # already Freeze in baseline → just stay Freeze
        assert isinstance(with_consult, BankFreeze)


@pytest.mark.unit
def test_low_analyzer_score_does_not_invent_risk() -> None:
    """A low analyzer score must not push a clean tx into Flag/Freeze."""
    bank = ScriptedBankMonitor(seed=42)
    clean_tx = TransactionMeta(
        amount=500.0,
        receiver_new=False,
        receiver_id_hash="rx_clean",
        frequency_24h=0,
    )
    obs = _bank_obs(clean_tx)

    action = bank.act_with_consultation(
        obs,
        AnalyzerConsultation(score=0.05, signals=(), flagged=False),
    )
    assert isinstance(action, BankApprove)


# --- env-level integration ---------------------------------------------------


@pytest.mark.unit
def test_env_negotiation_disabled_is_default() -> None:
    """`ChakravyuhOpenEnv()` must default to negotiation disabled."""
    env = ChakravyuhOpenEnv()
    assert env._enable_negotiation is False


@pytest.mark.unit
def test_env_negotiation_flag_round_trip() -> None:
    """The flag is settable and survives reset() without resetting state."""
    env = ChakravyuhOpenEnv(enable_negotiation=True)
    env.reset(seed=7)
    assert env._enable_negotiation is True


@pytest.mark.unit
def test_env_with_negotiation_completes_episode() -> None:
    """End-to-end smoke: an episode with negotiation enabled terminates cleanly."""
    env = ChakravyuhOpenEnv(enable_negotiation=True)
    obs = env.reset(seed=11)
    assert obs is not None
    # Two analyzer decisions (turn 3 + turn 6); the second triggers
    # transaction → bank consultation → outcome.
    obs1 = env.step(ChakravyuhAction(score=0.92, signals=["urgency"]))
    if not obs1.done:
        obs2 = env.step(ChakravyuhAction(score=0.95, signals=["impersonation"]))
        assert obs2.done
    else:
        assert obs1.done
