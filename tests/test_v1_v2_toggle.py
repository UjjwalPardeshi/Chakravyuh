"""Tests for the v1-vs-v2 archived-response toggle (`server/demo_v1_v2.py`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.demo_v1_v2 import (
    list_scenario_choices,
    load_archived_data,
    render_summary_banner,
    render_toggle_view,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_PATH = REPO_ROOT / "data" / "v1_v2_archived_responses.json"
BENCH_PATH = REPO_ROOT / "data" / "chakravyuh-bench-v0" / "scenarios.jsonl"


@pytest.mark.unit
def test_archive_file_loads() -> None:
    data = load_archived_data()
    assert "_provenance" in data
    assert "honest_note" in data["_provenance"]
    assert isinstance(data["scenarios"], list)
    assert len(data["scenarios"]) >= 5


@pytest.mark.unit
def test_each_archived_response_has_required_fields() -> None:
    data = load_archived_data()
    required_top = {"id", "label", "ground_truth", "category", "difficulty",
                    "prompt", "v1", "v2", "verdict"}
    required_resp = {"score", "flagged", "signals", "explanation"}
    for s in data["scenarios"]:
        missing = required_top - s.keys()
        assert not missing, f"scenario {s.get('id')!r} missing fields: {missing}"
        for v in ("v1", "v2"):
            missing = required_resp - s[v].keys()
            assert not missing, f"scenario {s['id']} {v} missing fields: {missing}"


@pytest.mark.unit
def test_archived_ground_truth_matches_bench() -> None:
    """Cross-check: each archived scenario's `ground_truth` matches bench v0."""
    bench = {}
    with BENCH_PATH.open() as f:
        for line in f:
            row = json.loads(line)
            bench[row["id"]] = row["ground_truth"]["is_scam"]
    archive = load_archived_data()
    for s in archive["scenarios"]:
        sid = s["id"]
        assert sid in bench, f"archived scenario {sid} not in bench"
        archived_is_scam = s["ground_truth"] == "scam"
        assert archived_is_scam == bench[sid], (
            f"{sid} archive says {s['ground_truth']!r} but bench is_scam={bench[sid]}"
        )


@pytest.mark.unit
def test_list_scenario_choices_returns_label_id_pairs() -> None:
    choices = list_scenario_choices()
    assert isinstance(choices, list)
    assert all(isinstance(t, tuple) and len(t) == 2 for t in choices)
    assert all(isinstance(label, str) and isinstance(sid, str) for label, sid in choices)


@pytest.mark.unit
def test_render_toggle_view_returns_four_strings() -> None:
    data = load_archived_data()
    sid = data["scenarios"][0]["id"]
    prompt, v1, v2, asymmetry = render_toggle_view(sid)
    assert all(isinstance(x, str) for x in (prompt, v1, v2, asymmetry))
    assert "v1" in v1.lower() or "reward-hacked" in v1.lower()
    assert "v2" in v2.lower() or "principled" in v2.lower()


@pytest.mark.unit
def test_render_summary_banner_includes_archived_disclosure() -> None:
    banner = render_summary_banner()
    assert "ARCHIVED" in banner.upper()
    assert "not a live re-run" in banner.lower()


@pytest.mark.unit
def test_render_toggle_view_unknown_id_does_not_crash() -> None:
    prompt, v1, v2, asymmetry = render_toggle_view("modec_NONEXISTENT")
    assert all(isinstance(x, str) for x in (prompt, v1, v2, asymmetry))
