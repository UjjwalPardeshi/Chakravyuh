"""Tests for eval/permutation_test_v1_v2.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.permutation_test_v1_v2 import (
    DEFAULT_V1_FP,
    DEFAULT_V1_TN,
    DEFAULT_V2_FP,
    DEFAULT_V2_TN,
    aggregate_permutation_test,
    per_row_paired_permutation,
    _fisher_exact_two_sided,
)


def test_aggregate_permutation_significant_for_real_v1_v2_delta():
    result = aggregate_permutation_test(
        v1_fp=DEFAULT_V1_FP,
        v1_n=DEFAULT_V1_FP + DEFAULT_V1_TN,
        v2_fp=DEFAULT_V2_FP,
        v2_n=DEFAULT_V2_FP + DEFAULT_V2_TN,
        n_perm=2_000,
        seed=42,
    )
    assert result.v1_fpr == pytest.approx(11 / 30, abs=1e-6)
    assert result.v2_fpr == pytest.approx(2 / 30, abs=1e-6)
    assert result.observed_delta == pytest.approx(0.3, abs=1e-6)
    assert result.p_value_permutation < 0.05
    assert result.p_value_fisher_exact < 0.05


def test_aggregate_permutation_not_significant_for_no_delta():
    result = aggregate_permutation_test(
        v1_fp=5, v1_n=30, v2_fp=5, v2_n=30, n_perm=2_000, seed=7
    )
    assert result.observed_delta == pytest.approx(0.0, abs=1e-9)
    assert result.p_value_permutation >= 0.5
    assert result.p_value_fisher_exact == pytest.approx(1.0, abs=1e-9)


def test_aggregate_permutation_p_in_unit_interval():
    result = aggregate_permutation_test(
        v1_fp=10, v1_n=30, v2_fp=3, v2_n=30, n_perm=1_000, seed=1
    )
    assert 0.0 <= result.p_value_permutation <= 1.0
    assert 0.0 <= result.p_value_fisher_exact <= 1.0


def test_fisher_exact_matches_known_table():
    p = _fisher_exact_two_sided(11, 19, 2, 28)
    assert 0.005 < p < 0.02


def test_per_row_paired_significant_when_clearly_better():
    n = 50
    v1 = [1] * 25 + [0] * 25
    v2 = [1] * 45 + [0] * 5
    result = per_row_paired_permutation(v1, v2, n_perm=2_000, seed=42)
    assert result.n_paired == n
    assert result.v1_correct_count == 25
    assert result.v2_correct_count == 45
    assert result.observed_delta == pytest.approx(0.4, abs=1e-9)
    assert result.p_value_permutation < 0.05


def test_per_row_paired_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        per_row_paired_permutation([1, 0], [1, 0, 1], n_perm=10, seed=0)


def test_per_row_paired_rejects_empty():
    with pytest.raises(ValueError):
        per_row_paired_permutation([], [], n_perm=10, seed=0)


def test_aggregate_rejects_zero_sample_size():
    with pytest.raises(ValueError):
        aggregate_permutation_test(v1_fp=0, v1_n=0, v2_fp=0, v2_n=10, n_perm=10)


def test_logged_artifact_matches_invocation_defaults():
    """The shipped artifact in logs/ must match what the script writes by default."""
    artifact = Path("logs/permutation_test_v1_v2.json")
    if not artifact.exists():
        pytest.skip("logs/permutation_test_v1_v2.json not shipped yet")
    payload = json.loads(artifact.read_text())
    assert "aggregate_fpr_test" in payload
    agg = payload["aggregate_fpr_test"]
    assert agg["input"]["v1_fp"] == DEFAULT_V1_FP
    assert agg["input"]["v2_fp"] == DEFAULT_V2_FP
    assert agg["p_value_permutation"] < 0.05
    assert agg["p_value_fisher_exact"] < 0.05
