"""B.2 — known/novel re-bucket smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.known_vs_novel_split import _bucket_for, compute_split


@pytest.mark.unit
def test_bucket_for_explicit_novel_category() -> None:
    s = {
        "ground_truth": {"is_scam": True},
        "source": {"category": "novel_post_2024", "date_range": "2025-Q4"},
    }
    assert _bucket_for(s) == "novel"


@pytest.mark.unit
def test_bucket_for_year_threshold() -> None:
    s_2023 = {"ground_truth": {"is_scam": True}, "source": {"date_range": "2023"}}
    s_2024 = {"ground_truth": {"is_scam": True}, "source": {"date_range": "2024-Q1"}}
    assert _bucket_for(s_2023) == "known"
    assert _bucket_for(s_2024) == "novel"


@pytest.mark.unit
def test_bucket_for_benign() -> None:
    s = {"ground_truth": {"is_scam": False}, "source": {"date_range": "2024"}}
    assert _bucket_for(s) == "benign"


@pytest.mark.unit
def test_compute_split_writes_expected_keys(tmp_path: Path) -> None:
    bench = Path("data/chakravyuh-bench-v0/scenarios.jsonl")
    eval_v2 = Path("logs/eval_v2.json")
    out = compute_split(bench, eval_v2 if eval_v2.exists() else None)
    assert "_meta" in out
    assert "scripted" in out
    for key in ("known", "novel", "benign"):
        assert key in out["scripted"]
    assert "headline_gap_pp" in out
    # Bucket sizes must add up to 175 (the bench).
    s = out["scripted"]
    assert s["known"]["n"] + s["novel"]["n"] + s["benign"]["n"] == 175
