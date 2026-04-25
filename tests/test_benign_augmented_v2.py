"""B.4 — schema + content tests for benign_augmented_v2.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


_PATH = Path("chakravyuh_env/benign_augmented_v2.json")


@pytest.fixture(scope="module")
def corpus() -> dict:
    return json.loads(_PATH.read_text())


@pytest.mark.unit
def test_corpus_top_level_keys(corpus: dict) -> None:
    for key in ("description", "version", "source", "split_intent", "templates"):
        assert key in corpus, f"missing top-level key: {key!r}"


@pytest.mark.unit
def test_corpus_intent_is_training_only(corpus: dict) -> None:
    assert "training" in corpus["split_intent"].lower(), (
        "benign_augmented_v2 must be flagged training-only — "
        "it must not leak into the v0.2 test bench"
    )


@pytest.mark.unit
def test_corpus_size(corpus: dict) -> None:
    n = len(corpus["templates"])
    assert n >= 60, f"expected >= 60 templates, got {n}"


@pytest.mark.unit
def test_template_ids_are_unique(corpus: dict) -> None:
    ids = [t["id"] for t in corpus["templates"]]
    assert len(ids) == len(set(ids)), "duplicate template ids"


@pytest.mark.unit
def test_each_template_has_required_fields(corpus: dict) -> None:
    for t in corpus["templates"]:
        assert "id" in t and "category" in t and "text" in t, (
            f"template missing required field: {t}"
        )
        assert t["text"].strip(), f"template {t['id']} has empty text"


@pytest.mark.unit
def test_hard_negatives_have_explanation(corpus: dict) -> None:
    """If marked hard_negative=True, must include 'why_hard' justification."""
    for t in corpus["templates"]:
        if t.get("hard_negative"):
            assert "why_hard" in t and t["why_hard"].strip(), (
                f"hard negative {t['id']} missing 'why_hard' justification"
            )


@pytest.mark.unit
def test_no_overlap_with_test_bench(corpus: dict) -> None:
    """No new template's text exactly matches a bench scenario (soft anti-leakage).

    Cheap exact-string match — a real soft-leakage filter (min-hash + Jaccard)
    is in training/grpo_analyzer.py:_filter_soft_leakage and runs at training
    time. This test is a fast first-line sanity check.
    """
    bench = Path("data/chakravyuh-bench-v0/scenarios.jsonl")
    if not bench.exists():
        pytest.skip("bench file missing")
    bench_texts: set[str] = set()
    with bench.open() as f:
        for line in f:
            row = json.loads(line)
            for turn in row.get("attack_sequence", []):
                bench_texts.add(turn.get("text", "").strip())
    for t in corpus["templates"]:
        assert t["text"].strip() not in bench_texts, (
            f"template {t['id']} duplicates a bench scenario verbatim"
        )
