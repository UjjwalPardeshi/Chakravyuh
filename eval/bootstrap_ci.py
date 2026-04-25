"""Statistical utilities for Chakravyuh eval.

Provides:
  - `bootstrap_ci()`: 95% bootstrap confidence interval for any metric
  - `permutation_test()`: two-sample permutation test for p-value
  - `cohens_d()`: effect size between two groups

All three are used in CHAKRAVYUH_WIN_PLAN.md Part 6 Day 3 to report
rigorous stats against frontier LLM baselines.
"""

from __future__ import annotations

import random
from typing import Callable, Sequence


def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = lambda v: sum(v) / len(v),
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float, float]:
    """Return (point_estimate, ci_low, ci_high) for the statistic.

    Uses percentile bootstrap. Default statistic is mean.

    >>> p, lo, hi = bootstrap_ci([0, 1, 1, 1, 0, 1, 1, 0, 1, 1], seed=42)
    >>> lo <= p <= hi
    True
    """
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    resamples = [
        statistic([values[rng.randrange(n)] for _ in range(n)])
        for _ in range(n_resamples)
    ]
    resamples.sort()
    alpha = (1.0 - confidence) / 2
    lo = resamples[int(alpha * n_resamples)]
    hi = resamples[int((1.0 - alpha) * n_resamples)]
    point = statistic(values)
    return float(point), float(lo), float(hi)


def permutation_test(
    group_a: Sequence[float],
    group_b: Sequence[float],
    n_permutations: int = 10000,
    seed: int | None = None,
) -> float:
    """Two-sample permutation test. Returns p-value (two-sided).

    Null hypothesis: group_a and group_b drawn from same distribution.
    Test statistic: absolute difference of means.

    >>> p = permutation_test([1]*50, [0]*50, n_permutations=1000, seed=42)
    >>> p < 0.05
    True
    """
    if not group_a or not group_b:
        return 1.0
    rng = random.Random(seed)
    observed_diff = abs(_mean(group_a) - _mean(group_b))
    combined = list(group_a) + list(group_b)
    n_a = len(group_a)
    extreme_count = 0
    for _ in range(n_permutations):
        rng.shuffle(combined)
        perm_diff = abs(_mean(combined[:n_a]) - _mean(combined[n_a:]))
        if perm_diff >= observed_diff:
            extreme_count += 1
    return extreme_count / n_permutations


def cohens_d(group_a: Sequence[float], group_b: Sequence[float]) -> float:
    """Cohen's d effect size between two groups.

    Interpretation:
        d ≈ 0.2  → small effect
        d ≈ 0.5  → medium effect
        d ≈ 0.8  → large effect

    Uses pooled standard deviation.
    """
    if not group_a or not group_b:
        return 0.0
    m_a, m_b = _mean(group_a), _mean(group_b)
    var_a, var_b = _variance(group_a), _variance(group_b)
    n_a, n_b = len(group_a), len(group_b)
    pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / max(1, n_a + n_b - 2)
    if pooled_var <= 0:
        return 0.0
    return (m_a - m_b) / (pooled_var**0.5)


# --- internals ---


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


# --- CLI ---------------------------------------------------------------------
#
# `make bootstrap` calls `python eval/bootstrap_ci.py --eval-file <json>
# --iterations 10000 --output <json>` and expects 95% CI bands on the
# headline metrics from logs/eval_v2.json.
#
# `eval_v2.json` only stores aggregated proportions and counts, not per-
# scenario predictions. For a Bernoulli proportion (detection rate, FPR,
# per-difficulty detection), the percentile bootstrap is well-defined on
# the *reconstructed* binary outcome array of length n. F1 is bootstrapped
# jointly over the scam outcomes (TP/FN) and benign outcomes (FP/TN).


def _binary_outcomes(rate: float, n: int) -> list[int]:
    """Reconstruct a binary outcome array from rate × n.

    Assumes the rate was computed as count / n with `count` an integer.
    """
    count = int(round(rate * n))
    count = max(0, min(n, count))
    return [1] * count + [0] * (n - count)


def _f1_from_outcomes(scam_correct: Sequence[int], benign_correct: Sequence[int]) -> float:
    """Compute F1 given per-scenario correctness on scams and benigns."""
    tp = sum(scam_correct)
    fn = len(scam_correct) - tp
    fp = len(benign_correct) - sum(benign_correct)
    if tp + fp == 0 or tp + fn == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _bootstrap_proportion(
    outcomes: Sequence[int],
    n_resamples: int,
    seed: int,
) -> tuple[float, float, float]:
    """Percentile bootstrap CI for a binary proportion."""
    return bootstrap_ci(
        outcomes,
        statistic=lambda v: sum(v) / len(v),
        n_resamples=n_resamples,
        seed=seed,
    )


def _bootstrap_f1(
    scam_outcomes: Sequence[int],
    benign_outcomes: Sequence[int],
    n_resamples: int,
    seed: int,
) -> tuple[float, float, float]:
    """Joint percentile bootstrap CI for F1 over scam + benign outcomes."""
    rng = random.Random(seed)
    n_s, n_b = len(scam_outcomes), len(benign_outcomes)
    if n_s == 0 or n_b == 0:
        return 0.0, 0.0, 0.0
    samples = []
    for _ in range(n_resamples):
        s_resample = [scam_outcomes[rng.randrange(n_s)] for _ in range(n_s)]
        b_resample = [benign_outcomes[rng.randrange(n_b)] for _ in range(n_b)]
        samples.append(_f1_from_outcomes(s_resample, b_resample))
    samples.sort()
    lo = samples[int(0.025 * n_resamples)]
    hi = samples[int(0.975 * n_resamples)]
    point = _f1_from_outcomes(scam_outcomes, benign_outcomes)
    return float(point), float(lo), float(hi)


def _ci_dict(point: float, lo: float, hi: float) -> dict:
    return {"point": point, "ci_low": lo, "ci_high": hi}


def _run_cli() -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Bootstrap 95% CIs for Chakravyuh eval metrics")
    parser.add_argument("--eval-file", required=True, help="Path to logs/eval_v2.json")
    parser.add_argument("--iterations", type=int, default=10000, help="Bootstrap resamples")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True, help="Path to write bootstrap CI JSON")
    args = parser.parse_args()

    eval_data = json.loads(Path(args.eval_file).read_text())
    if "lora_v2" not in eval_data:
        raise SystemExit(f"{args.eval_file} missing 'lora_v2' section")
    block = eval_data["lora_v2"]

    n_total = int(block["n"])
    detection = float(block["detection"])
    fpr = float(block["fpr"])
    per_diff = block.get("per_difficulty", {})
    n_scams = sum(int(v["n"]) for v in per_diff.values())
    n_benign = n_total - n_scams
    if n_scams <= 0 or n_benign <= 0:
        raise SystemExit(
            f"Cannot derive scam/benign split from per_difficulty (n_scams={n_scams}, n_benign={n_benign})"
        )

    scam_outcomes = _binary_outcomes(detection, n_scams)
    benign_correct_outcomes = _binary_outcomes(1.0 - fpr, n_benign)

    out: dict = {
        "_meta": {
            "eval_file": args.eval_file,
            "iterations": args.iterations,
            "seed": args.seed,
            "method": "percentile bootstrap on Bernoulli outcome arrays reconstructed from logs/eval_v2.json aggregates",
            "n_scams": n_scams,
            "n_benign": n_benign,
            "n_total": n_total,
        },
        "detection": _ci_dict(*_bootstrap_proportion(scam_outcomes, args.iterations, args.seed)),
        "fpr": _ci_dict(*_bootstrap_proportion([1 - o for o in benign_correct_outcomes], args.iterations, args.seed + 1)),
        "f1": _ci_dict(*_bootstrap_f1(scam_outcomes, benign_correct_outcomes, args.iterations, args.seed + 2)),
        "per_difficulty": {},
    }

    for i, (name, info) in enumerate(per_diff.items()):
        n_d = int(info["n"])
        rate_d = float(info["detection_rate"])
        if n_d <= 0:
            continue
        outcomes_d = _binary_outcomes(rate_d, n_d)
        out["per_difficulty"][name] = {
            "n": n_d,
            "detection": _ci_dict(*_bootstrap_proportion(outcomes_d, args.iterations, args.seed + 10 + i)),
        }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2))
    det = out["detection"]
    fp = out["fpr"]
    f1 = out["f1"]
    print(f"Wrote {args.output}")
    print(f"  detection: {det['point']:.4f}  95% CI [{det['ci_low']:.4f}, {det['ci_high']:.4f}]")
    print(f"  fpr:       {fp['point']:.4f}  95% CI [{fp['ci_low']:.4f}, {fp['ci_high']:.4f}]")
    print(f"  f1:        {f1['point']:.4f}  95% CI [{f1['ci_low']:.4f}, {f1['ci_high']:.4f}]")


if __name__ == "__main__":
    _run_cli()
