"""Reward functions per CHAKRAVYUH_WIN_PLAN.md Part 3.

Each agent has its own reward signal. The environment computes them at episode
end from the `EpisodeOutcome` and passes them back through the step() return.
"""

from __future__ import annotations

from dataclasses import dataclass

from chakravyuh_env.schemas import EpisodeOutcome


@dataclass(frozen=True)
class RewardBreakdown:
    """Per-agent terminal rewards with per-term breakdown for logging."""

    scammer: float
    victim: float
    bank: float
    analyzer: float
    regulator: float
    terms: dict[str, float]


def compute_rewards(
    outcome: EpisodeOutcome,
    novelty: float = 0.0,
    explanation_quality_analyzer: float = 0.0,
    explanation_quality_bank: float = 0.0,
    baseline_catch_rate: float = 0.5,
    post_update_catch_rate: float | None = None,
    rule_minimality_bonus: float = 0.0,
    mass_false_positive_flag: bool = False,
) -> RewardBreakdown:
    terms: dict[str, float] = {}

    # --- Scammer ---
    r_scammer = 1.0 * float(outcome.money_extracted)
    r_scammer -= 0.5 * float(
        outcome.detected_by_turn is not None and outcome.detected_by_turn <= 5
    )
    r_scammer -= 0.1 * outcome.turns_used
    r_scammer += 0.2 * novelty
    terms["scammer/extraction"] = 1.0 * float(outcome.money_extracted)
    terms["scammer/detection_penalty"] = -0.5 * float(
        outcome.detected_by_turn is not None and outcome.detected_by_turn <= 5
    )
    terms["scammer/turn_cost"] = -0.1 * outcome.turns_used
    terms["scammer/novelty"] = 0.2 * novelty

    # --- Victim ---
    r_victim = 1.0 * float(outcome.victim_refused)
    r_victim -= 1.0 * float(outcome.money_extracted)
    r_victim += 0.3 * float(outcome.victim_sought_verification)
    terms["victim/refused"] = 1.0 * float(outcome.victim_refused)
    terms["victim/lost_money"] = -1.0 * float(outcome.money_extracted)
    terms["victim/verification"] = 0.3 * float(outcome.victim_sought_verification)

    # --- Bank Monitor ---
    bank_correct_flag = outcome.bank_flagged and outcome.money_extracted is False
    r_bank = 1.0 * float(bank_correct_flag)
    r_bank -= 0.7 * float(outcome.false_positive and outcome.bank_flagged)
    r_bank += 0.4 * explanation_quality_bank
    r_bank -= 0.2 * (outcome.detected_by_turn or outcome.turns_used) / 10.0
    terms["bank/correct_flag"] = 1.0 * float(bank_correct_flag)
    terms["bank/false_positive"] = -0.7 * float(
        outcome.false_positive and outcome.bank_flagged
    )
    terms["bank/explanation"] = 0.4 * explanation_quality_bank

    # --- Analyzer ---
    early_detection = outcome.analyzer_flagged and (
        outcome.detected_by_turn is not None and outcome.detected_by_turn <= 5
    )
    r_analyzer = 1.0 * float(early_detection)
    r_analyzer -= 0.5 * float(not outcome.analyzer_flagged and outcome.money_extracted)
    r_analyzer -= 0.3 * float(outcome.false_positive and outcome.analyzer_flagged)
    r_analyzer += 0.4 * explanation_quality_analyzer
    terms["analyzer/early_detection"] = 1.0 * float(early_detection)
    terms["analyzer/missed"] = -0.5 * float(
        not outcome.analyzer_flagged and outcome.money_extracted
    )
    terms["analyzer/false_positive"] = -0.3 * float(
        outcome.false_positive and outcome.analyzer_flagged
    )
    terms["analyzer/explanation"] = 0.4 * explanation_quality_analyzer

    # --- Regulator ---
    delta = 0.0
    if post_update_catch_rate is not None:
        delta = post_update_catch_rate - baseline_catch_rate
    r_regulator = 0.5 * delta
    r_regulator += 0.2 * rule_minimality_bonus
    r_regulator -= 1.0 * float(mass_false_positive_flag)
    terms["regulator/improvement"] = 0.5 * delta
    terms["regulator/minimality"] = 0.2 * rule_minimality_bonus
    terms["regulator/mass_fp"] = -1.0 * float(mass_false_positive_flag)

    return RewardBreakdown(
        scammer=round(r_scammer, 4),
        victim=round(r_victim, 4),
        bank=round(r_bank, 4),
        analyzer=round(r_analyzer, 4),
        regulator=round(r_regulator, 4),
        terms={k: round(v, 4) for k, v in terms.items()},
    )
