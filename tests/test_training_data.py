"""Training-data integrity tests.

CRITICAL: these tests guard against training-test contamination. The LoRA is
evaluated on chakravyuh-bench-v0 (scenarios.jsonl). If any training example
duplicates a test-set message, the evaluation numbers are invalid.

Run: pytest tests/test_training_data.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from training.grpo_analyzer import (
    DEFAULT_BENIGN_PATH,
    DEFAULT_MULTITURN_PATH,
    DEFAULT_PARAPHRASE_PATH,
    DEFAULT_REGIONAL_PATH,
    DEFAULT_TEMPLATES_PATH,
    TEST_SET_PATH,
    build_training_examples,
)


def _normalize(text: str) -> str:
    """Case-insensitive, whitespace-collapsed form for text comparison."""
    return " ".join(text.lower().split())


def _load_test_set_texts() -> set[str]:
    """Every scammer message in the benchmark test set, normalized."""
    texts: set[str] = set()
    with TEST_SET_PATH.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scenario = json.loads(line)
            for step in scenario.get("attack_sequence", []):
                if step.get("sender") == "scammer":
                    texts.add(_normalize(step.get("text", "")))
    return texts


@pytest.mark.unit
def test_all_training_source_files_exist():
    """All 5 training template files must exist on disk."""
    for path in (
        DEFAULT_TEMPLATES_PATH,
        DEFAULT_BENIGN_PATH,
        DEFAULT_PARAPHRASE_PATH,
        DEFAULT_REGIONAL_PATH,
        DEFAULT_MULTITURN_PATH,
    ):
        assert path.exists(), f"Missing training source: {path}"


@pytest.mark.unit
def test_training_examples_include_all_five_sources():
    """Built corpus should include scams from templates+paraphrase+regional+multiturn and benign from benign_templates.

    After soft-leakage filter drops ~53/200 canonical templates, corpus is
    ~227 scams + ~55 benign = ~283. Floor is set accordingly.
    """
    examples = build_training_examples()
    assert len(examples) >= 270, f"Expected 270+ training examples, got {len(examples)}"

    scams = [e for e in examples if e.is_scam]
    benigns = [e for e in examples if not e.is_scam]

    assert len(scams) >= 220, f"Expected 220+ scams after filter, got {len(scams)}"
    assert len(benigns) >= 50, f"Expected 50+ benigns, got {len(benigns)}"


@pytest.mark.unit
def test_no_training_scam_duplicates_test_set_scam():
    """CRITICAL: training scam messages must not appear in the benchmark test set."""
    test_texts = _load_test_set_texts()
    examples = build_training_examples()

    overlaps: list[tuple[str, str]] = []
    for ex in examples:
        if not ex.is_scam:
            continue
        normalized = _normalize(ex.prompt_text)
        # For multi-turn, check each segment
        segments = [normalized] + [
            _normalize(line) for line in ex.prompt_text.split("\n") if line.strip()
        ]
        for seg in segments:
            if len(seg) < 40:  # too short to meaningfully overlap
                continue
            if seg in test_texts:
                overlaps.append((ex.category, seg[:80]))

    assert not overlaps, (
        f"Found {len(overlaps)} training-scam / test-set overlaps. "
        f"First 3: {overlaps[:3]}"
    )


@pytest.mark.unit
def test_no_soft_substring_leakage_in_built_corpus():
    """CRITICAL: after soft-leakage filter, no training line is a substring of
    any test-set scammer text (and vice versa).

    This is the stronger leakage guarantee — catches cases where a canonical
    template opener appears verbatim inside a longer test scenario.
    """
    test_texts = _load_test_set_texts()
    examples = build_training_examples()

    violations: list[tuple[str, str]] = []
    for ex in examples:
        if not ex.is_scam:
            continue
        for line in ex.prompt_text.split("\n"):
            line_norm = _normalize(line)
            if len(line_norm) < 40:
                continue
            for t_text in test_texts:
                if line_norm in t_text or t_text in line_norm:
                    violations.append((ex.category, line_norm[:80]))
                    break

    assert not violations, (
        f"Soft-leakage filter failed: {len(violations)} training lines are "
        f"substrings of test-set messages. First 3: {violations[:3]}"
    )


@pytest.mark.unit
def test_no_training_benign_duplicates_test_set_benign():
    """CRITICAL: benign training SMS must not appear in the benchmark."""
    test_texts = _load_test_set_texts()
    examples = build_training_examples()

    overlaps: list[str] = []
    for ex in examples:
        if ex.is_scam:
            continue
        normalized = _normalize(ex.prompt_text)
        if normalized in test_texts:
            overlaps.append(normalized[:80])

    assert not overlaps, (
        f"Found {len(overlaps)} benign training/test overlaps: {overlaps[:3]}"
    )


@pytest.mark.unit
def test_training_covers_all_5_scam_categories():
    """LoRA needs representation of every scam category it will be evaluated on."""
    examples = build_training_examples()
    categories = {e.category for e in examples if e.is_scam}
    required = {
        "otp_theft",
        "kyc_fraud",
        "loan_app_fraud",
        "investment_fraud",
        "impersonation",
    }
    missing = required - categories
    assert not missing, f"Training missing scam categories: {missing}"


@pytest.mark.unit
def test_training_has_regional_language_coverage():
    """Training must include at least one non-English scam for multilingual transfer."""
    with DEFAULT_REGIONAL_PATH.open(encoding="utf-8") as f:
        regional = json.load(f)["templates"]

    # Verify the regional templates actually contain non-ASCII or specific non-English markers
    has_nonlatin = sum(
        1 for t in regional if any(ord(c) > 127 for c in t.get("opener", ""))
    )
    assert has_nonlatin >= 5, (
        f"Expected 5+ regional templates with non-Latin scripts, got {has_nonlatin}"
    )


@pytest.mark.unit
def test_training_has_multiturn_examples():
    """Multi-turn sequences must be represented so LoRA handles dialog context."""
    with DEFAULT_MULTITURN_PATH.open(encoding="utf-8") as f:
        mt = json.load(f)["templates"]
    assert len(mt) >= 10, f"Expected 10+ multi-turn templates, got {len(mt)}"
    for t in mt:
        assert len(t.get("turns", [])) >= 2, f"Multi-turn should have 2+ turns: {t['id']}"


@pytest.mark.unit
def test_benign_templates_balanced_across_categories():
    """Benign pool should span banking, delivery, utility, govt, subscription, otp_legit, misc."""
    with DEFAULT_BENIGN_PATH.open(encoding="utf-8") as f:
        benign = json.load(f)["templates"]

    categories = {t.get("category") for t in benign}
    required = {
        "banking",
        "delivery",
        "utility",
        "insurance",
        "govt",
        "subscription",
        "otp_legit",
        "misc",
    }
    missing = required - categories
    assert not missing, f"Benign pool missing categories: {missing}"
    assert len(benign) >= 70, f"Expected 70+ benign templates, got {len(benign)}"
