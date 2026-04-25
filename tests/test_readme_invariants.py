"""README invariants — assert public claims match the runtime reality.

These tests prevent the kind of drift that produced the original "199 →
231 → 233 → 235" zig-zag where the README, Makefile help string, and
dress-rehearsal log each told a different story about how many tests
ship.

Each invariant should be a *single, mechanical, false-able* claim. If
the README says "X tests pass", we count tests and assert the number
matches. Anything else (numbers, dates, percentages) is acceptable to
drift; only mechanically-verifiable claims belong here.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


def _collect_count() -> int:
    """Run pytest --collect-only and return the test count.

    Uses ``sys.executable -m pytest`` so the subprocess inherits the same
    interpreter (and therefore the same installed packages) as the active
    test session — invoking the system ``pytest`` would pick up a different
    venv with different plugins and produce different counts.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header", str(REPO_ROOT / "tests")],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    match = re.search(r"(\d+)\s+tests? collected", output)
    if not match:
        pytest.fail(f"could not parse pytest collection count from:\n{output[-400:]}")
    return int(match.group(1))


def test_readme_test_count_matches_actual() -> None:
    """README's stated `<N> collected` must equal the actual collected count."""
    actual = _collect_count()
    text = README.read_text()
    match = re.search(r"(\d+)\s+collected\s*·", text)
    assert match, "README does not declare a test count in the standard format"
    claimed = int(match.group(1))
    assert claimed == actual, (
        f"README claims {claimed} tests collected; actual is {actual}. "
        "Update README.md and Makefile help to match. This file enforces parity."
    )


def test_readme_local_links_exist() -> None:
    """Every `](relative/path)` reference in the README must resolve."""
    text = README.read_text()
    paths: list[str] = []
    for m in re.finditer(r"\]\(([^)]+)\)", text):
        target = m.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        # strip anchor
        target = target.split("#", 1)[0]
        if not target:
            continue
        paths.append(target)

    missing = [p for p in paths if not (REPO_ROOT / p).exists()]
    assert not missing, (
        "README references missing local paths:\n  - "
        + "\n  - ".join(missing)
        + "\n\nFix: either create the file or update the link."
    )
