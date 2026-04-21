"""Tests for Mode C evaluation pipeline + stats utilities."""

from __future__ import annotations

import pytest

from eval.bootstrap_ci import bootstrap_ci, cohens_d, permutation_test
from eval.mode_c_real_cases import (
    DEFAULT_DATASET,
    ScriptedAnalyzerAdapter,
    aggregate,
    load_dataset,
    per_category_breakdown,
    run_eval,
)


@pytest.mark.unit
def test_dataset_loads_and_is_expected_size():
    data = load_dataset(DEFAULT_DATASET)
    # Lower bound — may grow over time as community contributes
    assert len(data) >= 130


@pytest.mark.unit
def test_dataset_has_scam_and_benign():
    data = load_dataset(DEFAULT_DATASET)
    scam = sum(1 for s in data if s["ground_truth"]["is_scam"])
    benign = sum(1 for s in data if not s["ground_truth"]["is_scam"])
    assert scam > 0
    assert benign > 0
    assert scam + benign == len(data)


@pytest.mark.unit
def test_dataset_has_novel_subset_for_temporal_eval():
    """Temporal generalization eval requires n>=30 for statistical power."""
    data = load_dataset(DEFAULT_DATASET)
    novel = [s for s in data if s["ground_truth"]["difficulty"] == "novel"]
    assert len(novel) >= 30, f"Only {len(novel)} novel scenarios — need 30+ for CI"


@pytest.mark.unit
def test_bootstrap_ci_reasonable():
    # 80% positive rate in a large sample → CI should bracket 0.8
    samples = [1.0] * 80 + [0.0] * 20
    point, lo, hi = bootstrap_ci(samples, n_resamples=1000, seed=42)
    assert abs(point - 0.8) < 0.001
    assert lo < 0.8 < hi
    assert (hi - lo) < 0.2  # reasonably tight CI


@pytest.mark.unit
def test_permutation_test_detects_difference():
    group_a = [1.0] * 50
    group_b = [0.0] * 50
    p = permutation_test(group_a, group_b, n_permutations=1000, seed=42)
    assert p < 0.05


@pytest.mark.unit
def test_permutation_test_no_difference():
    group_a = [0.5, 0.5, 0.5, 0.5]
    group_b = [0.5, 0.5, 0.5, 0.5]
    p = permutation_test(group_a, group_b, n_permutations=500, seed=42)
    assert p > 0.05


@pytest.mark.unit
def test_cohens_d_large_effect():
    group_a = [10.0, 11.0, 9.0, 10.5, 11.5, 9.5]
    group_b = [1.0, 2.0, 0.5, 1.5, 2.5, 0.0]
    d = cohens_d(group_a, group_b)
    assert d > 0.8  # large effect


@pytest.mark.integration
def test_scripted_analyzer_catches_majority_of_scams():
    data = load_dataset(DEFAULT_DATASET)
    analyzer = ScriptedAnalyzerAdapter()
    results = run_eval(analyzer, data, threshold=0.5)
    metrics = aggregate(results)
    # Baseline scripted analyzer must catch at least 40% of scams (sanity bound)
    assert metrics.detection_rate >= 0.40
    # Benign cases should have SOME false positives (rule-based is crude)
    # but should NOT be > 60% (otherwise the analyzer is useless)
    assert metrics.false_positive_rate <= 0.60


@pytest.mark.integration
def test_per_category_covers_all_scam_categories():
    data = load_dataset(DEFAULT_DATASET)
    analyzer = ScriptedAnalyzerAdapter()
    results = run_eval(analyzer, data)
    by_cat = per_category_breakdown(results)
    for required_cat in (
        "otp_theft",
        "kyc_fraud",
        "loan_app_fraud",
        "investment_fraud",
        "impersonation",
        "benign",
    ):
        assert required_cat in by_cat, f"Missing category: {required_cat}"
