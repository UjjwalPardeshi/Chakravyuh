"""Permutation test for the v1 → v2 FPR delta.

Bootstrap CIs (already shipped in `logs/bootstrap_v2.json`) tell you the spread
of v2's metric. They do *not* tell you whether the v1 → v2 FPR drop
(36 % → 6.7 %) is statistically significant. This script answers that with two
complementary tests on the same input data:

  1. **Aggregate-counts permutation** (always runs). Treats each model's
     bench evaluation as a 2 x 2 contingency over benigns:
         | predicted scam | predicted benign |
       v1 |     a          |      b           |
       v2 |     c          |      d           |
     and computes a permutation p-value on the difference of FPRs by
     repeatedly randomly relabelling rows under the null "v1 and v2 came from
     the same distribution," over `--n-perm` (default 10 000) iterations.
     Also reports the closed-form Fisher exact p-value as a cross-check.

  2. **Per-row paired permutation** (runs only when both per-row predictions
     exist). Uses the WIN_PLAN D.2 algorithm: for each scenario, randomly
     swap the (v1_correct, v2_correct) label assignment, recompute the
     mean accuracy delta, and tally how often the absolute delta exceeds
     the observed value.

Inputs
------
- `--v1-counts a,b` and `--v2-counts c,d` (or the defaults below) for test 1.
- `--v1-per-row` and `--v2-per-row` JSONL files for test 2 (optional).

Output
------
JSON written to `--output` (default `logs/permutation_test_v1_v2.json`) with
both p-values, observed deltas, sample sizes, and a one-line interpretation.

Defaults
--------
The aggregate counts are taken from the README claims that we want to
quantify the significance of:
  v1: FPR 36 % on n=30 benigns  → 11 false positives, 19 true negatives
  v2: FPR 6.7 % on n=30 benigns →  2 false positives, 28 true negatives

These come from `logs/eval_v2.json` (v2 side; threshold 0.55) and from the v1
training-time eval cited in `docs/training_diagnostics.md` (the v1 LoRA was not
re-pushed to HF Hub but its bench-time numbers are the ones cited in every
README/slide).

Run:
    python eval/permutation_test_v1_v2.py
or:
    python eval/permutation_test_v1_v2.py --n-perm 100000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Defaults — see module docstring for citation.
DEFAULT_V1_FP = 11
DEFAULT_V1_TN = 19
DEFAULT_V2_FP = 2
DEFAULT_V2_TN = 28


# ---------------------------------------------------------------------------
# Aggregate-counts permutation (always runs)
# ---------------------------------------------------------------------------

@dataclass
class AggregateResult:
    v1_fp: int
    v1_n: int
    v2_fp: int
    v2_n: int
    v1_fpr: float
    v2_fpr: float
    observed_delta: float
    n_perm: int
    p_value_permutation: float
    p_value_fisher_exact: float


def _fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Closed-form two-sided Fisher exact for a 2x2 table.

    Computes the probability of seeing a table at least as extreme as
    [[a, b], [c, d]] under the null of independence with the same row + column
    margins. Uses the standard log-factorial trick to avoid overflow.
    """
    n = a + b + c + d
    row1 = a + b
    row2 = c + d
    col1 = a + c
    col2 = b + d

    def log_choose(n_: int, k_: int) -> float:
        if k_ < 0 or k_ > n_:
            return -math.inf
        return math.lgamma(n_ + 1) - math.lgamma(k_ + 1) - math.lgamma(n_ - k_ + 1)

    log_denom = log_choose(n, col1)
    observed_log_p = log_choose(row1, a) + log_choose(row2, c) - log_denom
    observed_p = math.exp(observed_log_p)

    total_p = 0.0
    a_min = max(0, col1 - row2)
    a_max = min(row1, col1)
    for a_alt in range(a_min, a_max + 1):
        c_alt = col1 - a_alt
        log_p = log_choose(row1, a_alt) + log_choose(row2, c_alt) - log_denom
        p = math.exp(log_p)
        if p <= observed_p + 1e-12:
            total_p += p
    return min(1.0, total_p)


def aggregate_permutation_test(
    v1_fp: int,
    v1_n: int,
    v2_fp: int,
    v2_n: int,
    *,
    n_perm: int = 10_000,
    seed: int = 42,
) -> AggregateResult:
    """Permutation test on the FPR delta from aggregate counts.

    Constructs the full label vector (1 = false positive, 0 = true negative)
    for v1 and v2, then under the null reshuffles the model labels and
    measures how often the absolute FPR delta exceeds the observed.
    """
    if v1_n <= 0 or v2_n <= 0:
        raise ValueError("Sample sizes must be positive")

    rng = random.Random(seed)
    v1_labels = [1] * v1_fp + [0] * (v1_n - v1_fp)
    v2_labels = [1] * v2_fp + [0] * (v2_n - v2_fp)
    pooled = v1_labels + v2_labels

    v1_fpr = v1_fp / v1_n
    v2_fpr = v2_fp / v2_n
    observed_delta = abs(v2_fpr - v1_fpr)

    extreme = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        perm_v1 = pooled[:v1_n]
        perm_v2 = pooled[v1_n:]
        delta = abs(sum(perm_v2) / v2_n - sum(perm_v1) / v1_n)
        if delta >= observed_delta - 1e-12:
            extreme += 1
    p_perm = extreme / n_perm

    p_fisher = _fisher_exact_two_sided(
        v1_fp, v1_n - v1_fp, v2_fp, v2_n - v2_fp
    )

    return AggregateResult(
        v1_fp=v1_fp,
        v1_n=v1_n,
        v2_fp=v2_fp,
        v2_n=v2_n,
        v1_fpr=v1_fpr,
        v2_fpr=v2_fpr,
        observed_delta=observed_delta,
        n_perm=n_perm,
        p_value_permutation=p_perm,
        p_value_fisher_exact=p_fisher,
    )


# ---------------------------------------------------------------------------
# Per-row paired permutation (optional — runs only with --v1-per-row + --v2-per-row)
# ---------------------------------------------------------------------------

@dataclass
class PerRowResult:
    n_paired: int
    v1_correct_count: int
    v2_correct_count: int
    observed_delta: float
    n_perm: int
    p_value_permutation: float


def per_row_paired_permutation(
    v1_correct: list[int],
    v2_correct: list[int],
    *,
    n_perm: int = 10_000,
    seed: int = 42,
) -> PerRowResult:
    """Paired-sample permutation test on per-scenario predictions.

    For each scenario, randomly swap the (v1, v2) correctness labels and
    measure how often the absolute mean-delta exceeds the observed.
    """
    if len(v1_correct) != len(v2_correct):
        raise ValueError("v1 and v2 per-row vectors must be the same length")
    n = len(v1_correct)
    if n == 0:
        raise ValueError("Empty input vectors")

    observed_delta = abs(
        sum(v2_correct) / n - sum(v1_correct) / n
    )

    rng = random.Random(seed)
    extreme = 0
    for _ in range(n_perm):
        diffs = []
        for v1_i, v2_i in zip(v1_correct, v2_correct):
            if rng.random() < 0.5:
                diffs.append(v2_i - v1_i)
            else:
                diffs.append(v1_i - v2_i)
        if abs(sum(diffs) / n) >= observed_delta - 1e-12:
            extreme += 1
    p_perm = extreme / n_perm

    return PerRowResult(
        n_paired=n,
        v1_correct_count=sum(v1_correct),
        v2_correct_count=sum(v2_correct),
        observed_delta=observed_delta,
        n_perm=n_perm,
        p_value_permutation=p_perm,
    )


def _load_per_row_correct(path: Path) -> list[int]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows.append(int(row["predicted"] == row["ground_truth"]))
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _interpret(p: float) -> str:
    if p < 1e-4:
        return "extremely significant (p < 0.0001)"
    if p < 1e-3:
        return f"highly significant (p = {p:.4g})"
    if p < 0.05:
        return f"significant (p = {p:.4g})"
    return f"not significant at alpha=0.05 (p = {p:.4g})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-fp", type=int, default=DEFAULT_V1_FP)
    parser.add_argument("--v1-n", type=int, default=DEFAULT_V1_FP + DEFAULT_V1_TN)
    parser.add_argument("--v2-fp", type=int, default=DEFAULT_V2_FP)
    parser.add_argument("--v2-n", type=int, default=DEFAULT_V2_FP + DEFAULT_V2_TN)
    parser.add_argument(
        "--v1-per-row",
        type=Path,
        default=None,
        help="Optional path to v1 per-row JSONL (one obj per scenario with `predicted`+`ground_truth`).",
    )
    parser.add_argument(
        "--v2-per-row",
        type=Path,
        default=None,
        help="Optional path to v2 per-row JSONL (B.12 output).",
    )
    parser.add_argument("--n-perm", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("logs/permutation_test_v1_v2.json"),
    )
    args = parser.parse_args()

    payload: dict[str, Any] = {
        "meta": {
            "script": "eval/permutation_test_v1_v2.py",
            "n_perm": args.n_perm,
            "seed": args.seed,
            "interpretation_threshold": "alpha=0.05",
            "tests_run": [],
        },
    }

    # Test 1 — aggregate counts (always runs)
    agg = aggregate_permutation_test(
        v1_fp=args.v1_fp,
        v1_n=args.v1_n,
        v2_fp=args.v2_fp,
        v2_n=args.v2_n,
        n_perm=args.n_perm,
        seed=args.seed,
    )
    payload["aggregate_fpr_test"] = {
        "input": {
            "v1_fp": agg.v1_fp,
            "v1_n": agg.v1_n,
            "v1_fpr": round(agg.v1_fpr, 4),
            "v2_fp": agg.v2_fp,
            "v2_n": agg.v2_n,
            "v2_fpr": round(agg.v2_fpr, 4),
        },
        "observed_fpr_delta_abs": round(agg.observed_delta, 4),
        "p_value_permutation": agg.p_value_permutation,
        "p_value_fisher_exact": agg.p_value_fisher_exact,
        "interpretation_permutation": _interpret(agg.p_value_permutation),
        "interpretation_fisher_exact": _interpret(agg.p_value_fisher_exact),
    }
    payload["meta"]["tests_run"].append("aggregate_fpr_test")

    # Test 2 — per-row paired (optional)
    if args.v1_per_row and args.v2_per_row:
        if not args.v1_per_row.exists():
            print(f"[warn] --v1-per-row {args.v1_per_row} not found; skipping per-row test", file=sys.stderr)
        elif not args.v2_per_row.exists():
            print(f"[warn] --v2-per-row {args.v2_per_row} not found; skipping per-row test", file=sys.stderr)
        else:
            v1_correct = _load_per_row_correct(args.v1_per_row)
            v2_correct = _load_per_row_correct(args.v2_per_row)
            if len(v1_correct) != len(v2_correct):
                print(
                    f"[warn] paired per-row lengths differ ({len(v1_correct)} vs {len(v2_correct)}); skipping",
                    file=sys.stderr,
                )
            else:
                pr = per_row_paired_permutation(
                    v1_correct,
                    v2_correct,
                    n_perm=args.n_perm,
                    seed=args.seed,
                )
                payload["per_row_paired_test"] = {
                    "input": {
                        "n_paired": pr.n_paired,
                        "v1_correct": pr.v1_correct_count,
                        "v2_correct": pr.v2_correct_count,
                    },
                    "observed_accuracy_delta_abs": round(pr.observed_delta, 4),
                    "p_value_permutation": pr.p_value_permutation,
                    "interpretation_permutation": _interpret(pr.p_value_permutation),
                }
                payload["meta"]["tests_run"].append("per_row_paired_test")
    else:
        payload["per_row_paired_test"] = None
        payload["meta"]["per_row_test_skipped_reason"] = (
            "B.12 per-row outputs not yet shipped (logs/eval_v2_per_row.jsonl + logs/eval_v1_per_row.jsonl). "
            "When B.12 produces them, re-run with --v1-per-row and --v2-per-row flags."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
