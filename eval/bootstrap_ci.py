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
