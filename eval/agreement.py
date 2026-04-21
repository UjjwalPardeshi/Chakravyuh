"""Inter-annotator / rule-vs-expert agreement statistics.

v0 ships `rule_vs_expert_kappa` — Cohen's κ between the scripted analyzer's
binary is_scam predictions and the human-curated ground-truth labels. This
is NOT full inter-rater reliability (that requires two independent human
annotators). It IS a legitimate agreement measure between a rule-based
detector and the expert labels, and it provides a reproducible consistency
number for v0.2.

Full human IRR (Cohen's κ between two human labelers on a 30-scenario
sample) is deferred to v0.3.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
from chakravyuh_env.schemas import ChatMessage, Observation


def cohens_kappa(a: list[int], b: list[int]) -> float:
    """Cohen's κ for two binary label sequences of equal length."""
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} vs {len(b)}")
    n = len(a)
    if n == 0:
        return 0.0

    agree = sum(1 for x, y in zip(a, b) if x == y)
    p_o = agree / n

    # Expected agreement by chance
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    p_e = pa1 * pb1 + (1 - pa1) * (1 - pb1)

    if p_e == 1.0:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def scripted_label(text: str, threshold: float = 0.5) -> int:
    """Run the scripted analyzer on a message, return 1 if flagged, 0 else."""
    analyzer = ScriptedAnalyzer(flag_threshold=threshold)
    obs = Observation(
        agent_role="analyzer",
        turn=1,
        chat_history=[ChatMessage(sender="scammer", turn=1, text=text)],
    )
    score = analyzer.act(obs)
    return 1 if score.score >= threshold else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default="data/chakravyuh-bench-v0/scenarios.jsonl",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    scenarios = [json.loads(l) for l in Path(args.dataset).open()]

    expert_labels: list[int] = []
    rule_labels: list[int] = []

    for s in scenarios:
        # Concatenate all scammer turns (for multi-turn, we give the rule
        # detector the full sequence — same privilege the expert had).
        scammer_text = " ".join(
            step["text"] for step in s["attack_sequence"]
            if step["sender"] == "scammer"
        )
        if not scammer_text:
            continue
        expert_labels.append(1 if s["ground_truth"]["is_scam"] else 0)
        rule_labels.append(scripted_label(scammer_text, args.threshold))

    n = len(expert_labels)
    agree = sum(1 for x, y in zip(expert_labels, rule_labels) if x == y)
    kappa = cohens_kappa(expert_labels, rule_labels)

    print(f"Dataset: {args.dataset}")
    print(f"N compared: {n}")
    print(f"Raw agreement: {agree}/{n} = {agree/n:.3f}")
    print(f"Expert positive rate: {sum(expert_labels)/n:.3f}")
    print(f"Rule positive rate: {sum(rule_labels)/n:.3f}")
    print(f"Cohen's κ (rule vs expert): {kappa:.3f}")

    # Interpretation band
    if kappa < 0:
        interp = "worse than chance"
    elif kappa < 0.20:
        interp = "slight"
    elif kappa < 0.40:
        interp = "fair"
    elif kappa < 0.60:
        interp = "moderate"
    elif kappa < 0.80:
        interp = "substantial"
    else:
        interp = "almost perfect"
    print(f"Landis-Koch interpretation: {interp} agreement")


if __name__ == "__main__":
    main()
