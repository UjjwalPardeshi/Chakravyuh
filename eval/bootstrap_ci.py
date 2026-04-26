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
from statistics import NormalDist
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


def bootstrap_ci_bca(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = lambda v: sum(v) / len(v),
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float, float]:
    """Bias-corrected and accelerated (BCa) bootstrap CI.

    Falls back to percentile when the resample distribution is degenerate
    (e.g. all bootstrap statistics identical, or jackknife variance zero) —
    that's the small-n / pathological-input regime where BCa is undefined.

    Reference: Efron (1987) "Better Bootstrap Confidence Intervals."
    Generally preferred over percentile for small samples and skewed
    distributions because it corrects for both bias (the median of the
    bootstrap distribution shifted away from the observed statistic) and
    skewness (acceleration via jackknife).

    >>> p, lo, hi = bootstrap_ci_bca([0, 1, 1, 1, 0, 1, 1, 0, 1, 1], seed=42)
    >>> lo <= p <= hi
    True
    """
    if not values:
        return 0.0, 0.0, 0.0
    n = len(values)
    if n < 2:
        # BCa is undefined for n < 2; return point estimate with degenerate CI.
        point = statistic(values)
        return float(point), float(point), float(point)

    rng = random.Random(seed)
    point = statistic(values)

    # 1. Bootstrap resampling (same as percentile)
    resamples = [
        statistic([values[rng.randrange(n)] for _ in range(n)])
        for _ in range(n_resamples)
    ]
    resamples.sort()

    # 2. Bias correction z0 — Phi^-1 of fraction of resamples below the observed stat.
    n_below = sum(1 for r in resamples if r < point)
    if n_below == 0 or n_below == n_resamples:
        # Degenerate: every resample is on one side of the point.
        # Fall back to percentile to avoid division by zero / infinite z0.
        return _percentile_from_sorted(resamples, point, confidence)
    p_below = n_below / n_resamples
    norm = NormalDist()
    z0 = norm.inv_cdf(p_below)

    # 3. Acceleration a — via jackknife.
    jack_estimates = []
    for i in range(n):
        leave_one_out = list(values[:i]) + list(values[i + 1:])
        jack_estimates.append(statistic(leave_one_out))
    jack_mean = sum(jack_estimates) / n
    diffs = [jack_mean - x for x in jack_estimates]
    num = sum(d ** 3 for d in diffs)
    denom = 6.0 * (sum(d ** 2 for d in diffs) ** 1.5)
    if denom == 0:
        return _percentile_from_sorted(resamples, point, confidence)
    a = num / denom

    # 4. Adjusted percentiles
    alpha = (1.0 - confidence) / 2
    z_lo = norm.inv_cdf(alpha)
    z_hi = norm.inv_cdf(1.0 - alpha)

    def _adjust(z: float) -> float:
        denom_ = 1.0 - a * (z0 + z)
        if denom_ == 0:
            return alpha
        return norm.cdf(z0 + (z0 + z) / denom_)

    alpha1 = _adjust(z_lo)
    alpha2 = _adjust(z_hi)
    # Clamp to (0, 1) to avoid index errors on tail cases.
    alpha1 = max(0.0, min(1.0 - 1.0 / n_resamples, alpha1))
    alpha2 = max(1.0 / n_resamples, min(1.0, alpha2))

    lo_idx = max(0, min(n_resamples - 1, int(alpha1 * n_resamples)))
    hi_idx = max(0, min(n_resamples - 1, int(alpha2 * n_resamples)))
    return float(point), float(resamples[lo_idx]), float(resamples[hi_idx])


def _percentile_from_sorted(
    sorted_resamples: Sequence[float],
    point: float,
    confidence: float,
) -> tuple[float, float, float]:
    n = len(sorted_resamples)
    alpha = (1.0 - confidence) / 2
    lo = sorted_resamples[int(alpha * n)]
    hi = sorted_resamples[int((1.0 - alpha) * n)]
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
    method: str = "percentile",
) -> tuple[float, float, float]:
    """Bootstrap CI for a binary proportion. Method = 'percentile' or 'bca'."""
    fn = bootstrap_ci_bca if method == "bca" else bootstrap_ci
    return fn(
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
    method: str = "percentile",
) -> tuple[float, float, float]:
    """Joint bootstrap CI for F1 over scam + benign outcomes (percentile or BCa)."""
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
    point = _f1_from_outcomes(scam_outcomes, benign_outcomes)

    if method != "bca":
        lo = samples[int(0.025 * n_resamples)]
        hi = samples[int(0.975 * n_resamples)]
        return float(point), float(lo), float(hi)

    # BCa for the joint statistic — bias correction + jackknife acceleration.
    n_below = sum(1 for s in samples if s < point)
    if n_below == 0 or n_below == n_resamples:
        lo = samples[int(0.025 * n_resamples)]
        hi = samples[int(0.975 * n_resamples)]
        return float(point), float(lo), float(hi)
    norm = NormalDist()
    z0 = norm.inv_cdf(n_below / n_resamples)

    jack: list[float] = []
    for i in range(n_s):
        sub = list(scam_outcomes[:i]) + list(scam_outcomes[i + 1:])
        jack.append(_f1_from_outcomes(sub, benign_outcomes))
    for i in range(n_b):
        sub = list(benign_outcomes[:i]) + list(benign_outcomes[i + 1:])
        jack.append(_f1_from_outcomes(scam_outcomes, sub))
    jack_mean = sum(jack) / len(jack)
    diffs = [jack_mean - x for x in jack]
    num = sum(d ** 3 for d in diffs)
    denom = 6.0 * (sum(d ** 2 for d in diffs) ** 1.5)
    if denom == 0:
        lo = samples[int(0.025 * n_resamples)]
        hi = samples[int(0.975 * n_resamples)]
        return float(point), float(lo), float(hi)
    a = num / denom

    z_lo = norm.inv_cdf(0.025)
    z_hi = norm.inv_cdf(0.975)
    def _adjust(z: float) -> float:
        d = 1.0 - a * (z0 + z)
        if d == 0:
            return 0.025
        return norm.cdf(z0 + (z0 + z) / d)
    a1 = max(0.0, min(1.0 - 1.0 / n_resamples, _adjust(z_lo)))
    a2 = max(1.0 / n_resamples, min(1.0, _adjust(z_hi)))
    lo_idx = max(0, min(n_resamples - 1, int(a1 * n_resamples)))
    hi_idx = max(0, min(n_resamples - 1, int(a2 * n_resamples)))
    return float(point), float(samples[lo_idx]), float(samples[hi_idx])


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
    parser.add_argument(
        "--method",
        choices=["percentile", "bca"],
        default="percentile",
        help=(
            "Bootstrap CI method. 'percentile' (default, used by `make bootstrap` "
            "and the canonical `logs/bootstrap_v2.json`) or 'bca' (bias-corrected + "
            "accelerated; generally preferred for small / skewed samples)."
        ),
    )
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

    method_label = (
        "BCa (bias-corrected + accelerated) bootstrap on Bernoulli outcome "
        "arrays reconstructed from logs/eval_v2.json aggregates"
        if args.method == "bca"
        else "percentile bootstrap on Bernoulli outcome arrays reconstructed from logs/eval_v2.json aggregates"
    )
    out: dict = {
        "_meta": {
            "eval_file": args.eval_file,
            "iterations": args.iterations,
            "seed": args.seed,
            "method": method_label,
            "n_scams": n_scams,
            "n_benign": n_benign,
            "n_total": n_total,
        },
        "detection": _ci_dict(*_bootstrap_proportion(scam_outcomes, args.iterations, args.seed, args.method)),
        "fpr": _ci_dict(*_bootstrap_proportion([1 - o for o in benign_correct_outcomes], args.iterations, args.seed + 1, args.method)),
        "f1": _ci_dict(*_bootstrap_f1(scam_outcomes, benign_correct_outcomes, args.iterations, args.seed + 2, args.method)),
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
            "detection": _ci_dict(*_bootstrap_proportion(outcomes_d, args.iterations, args.seed + 10 + i, args.method)),
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
