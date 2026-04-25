"""Tests for the `POST /diagnose` endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.integration
def test_diagnose_flags_obvious_scam(client: TestClient) -> None:
    resp = client.post(
        "/diagnose",
        json={"message": "Urgent! Your bank account will be frozen. Share OTP to verify identity now."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score"] > 0.5
    assert body["flagged"] is True
    assert body["analyzer"] == "rule_based_scripted"
    assert isinstance(body["signals"], list) and body["signals"]
    assert isinstance(body["rubric_breakdown"], dict)


@pytest.mark.integration
def test_diagnose_passes_clean_text(client: TestClient) -> None:
    resp = client.post(
        "/diagnose",
        json={"message": "Hi, how are you doing today?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Plain greeting won't trigger many keywords; flagged should be False.
    assert body["flagged"] is False or body["score"] < 0.5


@pytest.mark.integration
def test_diagnose_includes_v2_rubric_leaves(client: TestClient) -> None:
    resp = client.post(
        "/diagnose",
        json={"message": "Share your OTP urgently to claim your refund."},
    )
    assert resp.status_code == 200
    breakdown = resp.json()["rubric_breakdown"]
    expected_leaves = {
        "detection",
        "missed_scam",
        "false_positive",
        "calibration",
        "explanation",
        "signal_accuracy",
        "format",
        "length",
    }
    assert expected_leaves.issubset(set(breakdown))


@pytest.mark.integration
def test_diagnose_with_benign_truth_fires_fp_leaf(client: TestClient) -> None:
    """Tagging the message as benign-truth + flagged should fire the FP leaf."""
    resp = client.post(
        "/diagnose",
        json={
            "message": "Urgent! Last chance to claim your refund.",
            "is_benign_truth": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    if body["flagged"]:
        # When the analyzer flags a benign-truth message, the FP rubric leaf
        # is 1.0 and contributes -0.8 to the rubric_total via V2_WEIGHTS.
        assert body["rubric_breakdown"]["false_positive"] == 1.0


@pytest.mark.integration
def test_diagnose_rejects_too_long_message(client: TestClient) -> None:
    resp = client.post(
        "/diagnose",
        json={"message": "x" * 3000},
    )
    assert resp.status_code == 422  # Pydantic validation, max_length=2000


@pytest.mark.integration
def test_diagnose_rejects_empty_message(client: TestClient) -> None:
    resp = client.post("/diagnose", json={"message": ""})
    assert resp.status_code == 422
