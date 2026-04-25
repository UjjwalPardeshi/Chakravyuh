"""Regression tests for the red-team eval script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "eval" / "redteam_analyzer.py"


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    return tmp_path / "robustness.json"


def test_redteam_runs_end_to_end(output_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert output_path.exists()


def test_redteam_output_schema(output_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output_path)],
        cwd=REPO_ROOT,
        check=True,
        timeout=60,
    )
    payload = json.loads(output_path.read_text())
    for key in ("n_attacks", "n_caught", "n_bypassed", "pass_rate", "attacks"):
        assert key in payload, f"missing key: {key}"
    assert payload["n_attacks"] >= 10
    assert payload["n_caught"] + payload["n_bypassed"] == payload["n_attacks"]
    assert 0.0 <= payload["pass_rate"] <= 1.0


def test_redteam_is_deterministic(output_path: Path, tmp_path: Path) -> None:
    out2 = tmp_path / "robustness2.json"
    for path in (output_path, out2):
        subprocess.run(
            [sys.executable, str(SCRIPT), "--output", str(path)],
            cwd=REPO_ROOT,
            check=True,
            timeout=60,
        )
    a = json.loads(output_path.read_text())
    b = json.loads(out2.read_text())
    assert a["pass_rate"] == b["pass_rate"]
    assert [r["score"] for r in a["attacks"]] == [r["score"] for r in b["attacks"]]


def test_redteam_attack_taxonomy(output_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output_path)],
        cwd=REPO_ROOT,
        check=True,
        timeout=60,
    )
    payload = json.loads(output_path.read_text())
    categories = {a["category"] for a in payload["attacks"]}
    # Expect at least three categories represented.
    assert len(categories) >= 3
    for r in payload["attacks"]:
        assert r["verdict"] in ("caught", "bypassed")
        assert r["score"] >= 0.0
