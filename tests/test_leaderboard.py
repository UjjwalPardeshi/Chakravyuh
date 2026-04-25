"""Leaderboard endpoint tests (E.10).

Verifies:
  - First call seeds 3 internal entries (Scripted, v1, v2).
  - GET /leaderboard returns ranked-by-F1 entries.
  - POST /submit accepts a well-formed submission and persists it.
  - POST /submit rejects out-of-range metrics (Pydantic).
  - MCP-compliance: routes are /leaderboard and /submit, not reset/step/state/close.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.leaderboard import (
    DEFAULT_STORE_PATH,
    LeaderboardStore,
    LeaderboardSubmission,
    attach_to_app,
)


def _isolated_store(tmp_path: Path) -> LeaderboardStore:
    return LeaderboardStore(store_path=tmp_path / "lb.jsonl")


@pytest.mark.unit
def test_seed_creates_three_entries(tmp_path: Path) -> None:
    store = _isolated_store(tmp_path)
    entries = store.list_ranked()
    assert len(entries) == 3
    methods = {e.method for e in entries}
    assert "Scripted baseline (rule-based)" in methods
    assert "Chakravyuh-Qwen2.5-LoRA v1 (reward-hacked)" in methods
    assert "Chakravyuh-Qwen2.5-LoRA v2" in methods
    # All seeded entries are flagged.
    assert all(e.seeded for e in entries)


@pytest.mark.unit
def test_ranking_is_by_f1_descending(tmp_path: Path) -> None:
    store = _isolated_store(tmp_path)
    entries = store.list_ranked()
    f1s = [e.f1 for e in entries]
    assert f1s == sorted(f1s, reverse=True)
    # v2 is on top by F1.
    assert entries[0].method == "Chakravyuh-Qwen2.5-LoRA v2"


@pytest.mark.unit
def test_persistence_round_trip(tmp_path: Path) -> None:
    """Add an entry, build a fresh store on the same path, see it again."""
    store_path = tmp_path / "lb.jsonl"
    store = LeaderboardStore(store_path=store_path)
    store.add(LeaderboardSubmission(
        method="external-method-A",
        submitter="alice",
        detection=0.9,
        fpr=0.1,
        f1=0.9,
    ))

    store2 = LeaderboardStore(store_path=store_path)
    methods = {e.method for e in store2.list_ranked()}
    assert "external-method-A" in methods
    assert len(store2.list_ranked()) == 4  # 3 seeded + 1


# ---- HTTP routes ---------------------------------------------------------


def _client(tmp_path: Path) -> TestClient:
    """Build a minimal FastAPI app with only the leaderboard router attached."""
    from fastapi import FastAPI

    app = FastAPI()
    store = LeaderboardStore(store_path=tmp_path / "lb.jsonl")
    attach_to_app(app, store=store)
    return TestClient(app)


@pytest.mark.unit
def test_get_leaderboard_returns_seeded_entries(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.get("/leaderboard")
    assert r.status_code == 200
    body = r.json()
    assert body["bench"] == "chakravyuh-bench-v0"
    assert body["ranked_by"] == "f1"
    assert body["n_entries"] == 3
    assert len(body["entries"]) == 3


@pytest.mark.unit
def test_post_submit_accepts_valid_payload(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.post("/submit", json={
        "method": "GPT-4o-mini (zero-shot)",
        "submitter": "external-team",
        "detection": 0.85,
        "fpr": 0.10,
        "f1": 0.87,
        "n_evaluated": 174,
        "artifact_url": "https://gist.github.com/external/abc123",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["entry"]["method"] == "GPT-4o-mini (zero-shot)"
    assert body["entry"]["seeded"] is False

    # Now visible in GET
    r2 = client.get("/leaderboard")
    methods = {e["method"] for e in r2.json()["entries"]}
    assert "GPT-4o-mini (zero-shot)" in methods


@pytest.mark.unit
def test_post_submit_rejects_out_of_range_metric(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.post("/submit", json={
        "method": "broken",
        "submitter": "x",
        "detection": 1.5,  # > 1.0 → rejected
        "fpr": 0.0,
        "f1": 0.0,
    })
    assert r.status_code == 422


@pytest.mark.unit
def test_post_submit_rejects_extra_fields(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.post("/submit", json={
        "method": "x",
        "submitter": "x",
        "detection": 0.5,
        "fpr": 0.5,
        "f1": 0.5,
        "evil_extra": "drop tables",  # extra='forbid'
    })
    assert r.status_code == 422


# ---- MCP compliance check (extra layer; main test is in test_mcp_compliance.py) -


@pytest.mark.unit
def test_leaderboard_routes_avoid_reserved_names(tmp_path: Path) -> None:
    """Ensure /submit and /leaderboard don't shadow reset/step/state/close."""
    client = _client(tmp_path)
    paths = {r.path for r in client.app.routes if hasattr(r, "path")}
    reserved = {"/reset", "/step", "/state", "/close"}
    assert "/leaderboard" in paths
    assert "/submit" in paths
    # the leaderboard router must not register any reserved-name route
    leaderboard_router_paths = {p for p in paths if p in {"/leaderboard", "/submit"}}
    assert leaderboard_router_paths.isdisjoint(reserved)
