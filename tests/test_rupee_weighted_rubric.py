"""Unit tests for RupeeWeightedRubric — economic-loss-aware reward leaf.

Tests cover:

  * non-terminal observation → 0.0
  * benign episode (any flagged/money state) → 0.0
  * scam without `loss_amount_inr` → 0.0
  * malformed `loss_amount_inr` → 0.0
  * detected scam → +loss / cap (clipped to +1.0)
  * missed scam + money extracted → -loss / cap (clipped to -1.0)
  * missed scam without money → 0.0
  * scam flagged AND money still extracted → 0.0 (defender did its job by
    flagging; the bench scenario's pre-defender outcome doesn't penalize)
  * cap_inr validation
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from chakravyuh_env import RupeeWeightedRubric
from chakravyuh_env.openenv_models import ChakravyuhAction


def _action(score: float = 0.8) -> ChakravyuhAction:
    return ChakravyuhAction(score=score, signals=[], explanation="")


def _obs(*, done: bool = True, outcome: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(done=done, outcome=outcome)


@pytest.mark.unit
class TestRupeeWeightedRubric:
    def test_returns_zero_on_non_terminal(self) -> None:
        r = RupeeWeightedRubric()
        assert r(_action(), _obs(done=False, outcome=None)) == 0.0

    def test_returns_zero_on_benign(self) -> None:
        r = RupeeWeightedRubric()
        out = {"is_benign": True, "loss_amount_inr": 50_000, "analyzer_flagged": True}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_returns_zero_when_loss_missing(self) -> None:
        r = RupeeWeightedRubric()
        out = {"is_benign": False, "analyzer_flagged": True}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_returns_zero_when_loss_malformed(self) -> None:
        r = RupeeWeightedRubric()
        out = {"is_benign": False, "loss_amount_inr": "n/a", "analyzer_flagged": True}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_returns_zero_when_loss_non_positive(self) -> None:
        r = RupeeWeightedRubric()
        out = {"is_benign": False, "loss_amount_inr": 0, "analyzer_flagged": True}
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_positive_reward_on_detected_scam(self) -> None:
        r = RupeeWeightedRubric(cap_inr=100_000.0)
        out = {
            "is_benign": False,
            "loss_amount_inr": 50_000,
            "analyzer_flagged": True,
            "money_extracted": False,
        }
        assert r(_action(), _obs(outcome=out)) == pytest.approx(0.5)

    def test_positive_reward_clipped_to_one(self) -> None:
        r = RupeeWeightedRubric(cap_inr=100_000.0)
        out = {
            "is_benign": False,
            "loss_amount_inr": 1_000_000,
            "analyzer_flagged": True,
            "money_extracted": False,
        }
        assert r(_action(), _obs(outcome=out)) == pytest.approx(1.0)

    def test_negative_reward_on_missed_scam_with_loss(self) -> None:
        r = RupeeWeightedRubric(cap_inr=100_000.0)
        out = {
            "is_benign": False,
            "loss_amount_inr": 75_000,
            "analyzer_flagged": False,
            "money_extracted": True,
        }
        assert r(_action(), _obs(outcome=out)) == pytest.approx(-0.75)

    def test_zero_when_missed_but_no_money_extracted(self) -> None:
        r = RupeeWeightedRubric()
        out = {
            "is_benign": False,
            "loss_amount_inr": 50_000,
            "analyzer_flagged": False,
            "money_extracted": False,
        }
        assert r(_action(), _obs(outcome=out)) == 0.0

    def test_zero_when_flagged_and_money_still_extracted(self) -> None:
        r = RupeeWeightedRubric()
        out = {
            "is_benign": False,
            "loss_amount_inr": 50_000,
            "analyzer_flagged": True,
            "money_extracted": True,
        }
        # The flag earns no economic credit if money still leaked — the
        # rubric is a *prevented-loss* signal, not a detection signal.
        assert r(_action(), _obs(outcome=out)) == 0.0

    @pytest.mark.parametrize("bad_cap", [0.0, -1.0, -100_000.0])
    def test_invalid_cap_raises(self, bad_cap: float) -> None:
        with pytest.raises(ValueError, match="cap_inr must be positive"):
            RupeeWeightedRubric(cap_inr=bad_cap)
