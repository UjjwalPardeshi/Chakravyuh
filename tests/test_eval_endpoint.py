"""Tests for the research endpoints (`/eval` family)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.integration
def test_get_eval_returns_v2_artifact(client: TestClient) -> None:
    resp = client.get("/eval")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "lora_v2" in body
    lora = body["lora_v2"]
    assert lora["n"] == 174
    assert 0.99 <= lora["detection"] <= 1.0
    assert 0.0 <= lora["fpr"] <= 0.1


@pytest.mark.integration
def test_get_eval_bootstrap_returns_cis(client: TestClient) -> None:
    resp = client.get("/eval/bootstrap")
    assert resp.status_code == 200
    body = resp.json()
    assert "detection" in body and "ci_low" in body["detection"]
    assert "fpr" in body
    assert "f1" in body


@pytest.mark.integration
def test_get_eval_redteam_returns_robustness(client: TestClient) -> None:
    resp = client.get("/eval/redteam")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_attacks"] == 10
    assert body["n_caught"] + body["n_bypassed"] == 10
    assert "by_category" in body


@pytest.mark.integration
def test_get_eval_time_to_detection(client: TestClient) -> None:
    resp = client.get("/eval/time-to-detection")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_episodes"] == 100
    assert "avg_detection_turn" in body


@pytest.mark.integration
def test_get_eval_ablation(client: TestClient) -> None:
    resp = client.get("/eval/ablation")
    assert resp.status_code == 200
    body = resp.json()
    assert "ablations" in body
    assert isinstance(body["ablations"], list)


@pytest.mark.integration
def test_unknown_eval_path_returns_404(client: TestClient) -> None:
    resp = client.get("/eval/this-does-not-exist")
    # FastAPI returns 404 for unmatched routes; our endpoints don't define
    # this path so the catch-all route must not exist.
    assert resp.status_code == 404
