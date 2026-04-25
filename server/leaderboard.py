"""Public leaderboard endpoint for the Chakravyuh OpenEnv submission.

Hackathon plan E.10: expose a `/submit` POST + `/leaderboard` GET pair so
external researchers can post their results against `chakravyuh-bench-v0`
and have them ranked in one place. Seeded with three internal entries
(scripted, v1, v2) so the leaderboard is non-empty at launch.

Design choices:

  - **In-memory + JSONL persistence.** Submissions are written to
    ``logs/leaderboard.jsonl`` (append-only) so the leaderboard survives
    server restarts and is auditable. The in-memory list is reloaded at
    startup. No external DB.
  - **Open submission, light validation.** Anyone can POST a submission;
    we validate the payload shape but make no claim that the numbers are
    correct. The leaderboard URL itself is the audit trail — if someone
    submits inflated numbers they have to publish a reproducible artifact
    pointer or be obviously fake.
  - **MCP-compliance safe.** Routes are ``/leaderboard`` and ``/submit``
    — neither name shadows OpenEnv core (``reset``/``step``/``state``/
    ``close``). Pinned by ``tests/test_mcp_compliance.py``.
  - **Headline metric only.** The ranked column is ``f1`` (single number,
    handles both detection-heavy and FPR-heavy methods fairly). Rich data
    (per-difficulty, per-language, CIs) is preserved on each entry but
    not used to rank.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("chakravyuh.leaderboard")

DEFAULT_STORE_PATH = Path("logs/leaderboard.jsonl")
MAX_ENTRIES_RETURNED = 200


class LeaderboardSubmission(BaseModel):
    """Payload for ``POST /submit``."""

    model_config = ConfigDict(extra="forbid")
    method: str = Field(min_length=1, max_length=120,
                        description="Method name, e.g. 'GPT-4o (zero-shot)'")
    submitter: str = Field(min_length=1, max_length=80,
                           description="Person or team handle")
    detection: float = Field(ge=0.0, le=1.0)
    fpr: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    bench_version: str = Field(default="chakravyuh-bench-v0", max_length=40)
    n_evaluated: int = Field(ge=1, default=174)
    artifact_url: str | None = Field(default=None, max_length=400,
                                     description="HF Hub repo / GitHub gist / blog URL backing the numbers")
    notes: str | None = Field(default=None, max_length=1000)


class LeaderboardEntry(BaseModel):
    """Stored / returned entry — `LeaderboardSubmission` plus server fields."""

    model_config = ConfigDict(extra="ignore")
    method: str
    submitter: str
    detection: float
    fpr: float
    f1: float
    bench_version: str = "chakravyuh-bench-v0"
    n_evaluated: int = 174
    artifact_url: str | None = None
    notes: str | None = None
    submitted_at: str  # ISO-8601 UTC
    seeded: bool = False  # internal vs external entry


_SEED_ENTRIES: list[dict[str, Any]] = [
    {
        "method": "Scripted baseline (rule-based)",
        "submitter": "chakravyuh-team",
        "detection": 0.701,
        "fpr": 0.290,
        "f1": 0.795,
        "n_evaluated": 174,
        "artifact_url": "https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/data/chakravyuh-bench-v0/baselines.json",
        "notes": "11-signal taxonomy + legit-SMS allowlist. Threshold = 0.50.",
        "seeded": True,
    },
    {
        "method": "Chakravyuh-Qwen2.5-LoRA v1 (reward-hacked)",
        "submitter": "chakravyuh-team",
        "detection": 1.0,
        "fpr": 0.360,
        "f1": 0.96,
        "n_evaluated": 135,
        "artifact_url": "https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/eval_v2.json",
        "notes": "Diagnostic baseline: this is the textbook reward-hacking fingerprint. Kept on the board to motivate v2.",
        "seeded": True,
    },
    {
        "method": "Chakravyuh-Qwen2.5-LoRA v2",
        "submitter": "chakravyuh-team",
        "detection": 0.993,
        "fpr": 0.067,
        "f1": 0.99,
        "n_evaluated": 174,
        "artifact_url": "https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2",
        "notes": "Bootstrap 95% CIs at logs/bootstrap_v2.json: detection [0.979, 1.000], FPR [0.000, 0.167], F1 [0.976, 1.000].",
        "seeded": True,
    },
]


class LeaderboardStore:
    """Thread-safe in-memory leaderboard with JSONL persistence."""

    def __init__(self, store_path: Path = DEFAULT_STORE_PATH) -> None:
        self.store_path = store_path
        self._lock = threading.Lock()
        self._entries: list[LeaderboardEntry] = []
        self._load_or_seed()

    def _load_or_seed(self) -> None:
        """Load persisted entries; if none, seed and persist."""
        if self.store_path.exists():
            with self.store_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._entries.append(LeaderboardEntry(**json.loads(line)))
                    except Exception as exc:  # pragma: no cover — diagnostic
                        logger.warning("Skipping malformed entry: %s", exc)
            if self._entries:
                return

        # First-run seeding
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("w") as f:
            for seed in _SEED_ENTRIES:
                entry = LeaderboardEntry(submitted_at=now, **seed)
                self._entries.append(entry)
                f.write(json.dumps(entry.model_dump()) + "\n")

    def add(self, submission: LeaderboardSubmission) -> LeaderboardEntry:
        entry = LeaderboardEntry(
            **submission.model_dump(),
            submitted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            seeded=False,
        )
        with self._lock:
            self._entries.append(entry)
            with self.store_path.open("a") as f:
                f.write(json.dumps(entry.model_dump()) + "\n")
        return entry

    def list_ranked(self, limit: int = MAX_ENTRIES_RETURNED) -> list[LeaderboardEntry]:
        """Return entries sorted by F1 descending; stable on submitted_at."""
        with self._lock:
            ordered = sorted(
                self._entries,
                key=lambda e: (-e.f1, e.fpr, e.submitted_at),
            )
        return ordered[:limit]

    def reset_for_tests(self) -> None:
        """Test helper — clear entries and reseed. Not exposed via HTTP."""
        with self._lock:
            self._entries = []
            try:
                self.store_path.unlink()
            except FileNotFoundError:
                pass
        self._load_or_seed()


def build_router(store: LeaderboardStore | None = None) -> APIRouter:
    """Return a FastAPI router with `/leaderboard` and `/submit` routes.

    The router is registered onto the main OpenEnv app in ``server/app.py``.
    """
    if store is None:
        store_path = Path(os.getenv("CHAKRAVYUH_LEADERBOARD_PATH", str(DEFAULT_STORE_PATH)))
        store = LeaderboardStore(store_path=store_path)

    router = APIRouter(tags=["leaderboard"])

    @router.get("/leaderboard")
    def get_leaderboard() -> dict[str, Any]:
        entries = store.list_ranked()
        return {
            "bench": "chakravyuh-bench-v0",
            "ranked_by": "f1",
            "n_entries": len(entries),
            "entries": [e.model_dump() for e in entries],
        }

    @router.post("/submit", status_code=status.HTTP_201_CREATED)
    def post_submit(submission: LeaderboardSubmission) -> dict[str, Any]:
        try:
            entry = store.add(submission)
        except Exception as exc:  # pragma: no cover — schema validation upstream
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to persist submission: {exc}",
            ) from exc
        rank = next(
            (i + 1 for i, e in enumerate(store.list_ranked()) if e.submitted_at == entry.submitted_at and e.method == entry.method),
            None,
        )
        return {
            "ok": True,
            "rank": rank,
            "n_total": len(store.list_ranked(limit=10_000)),
            "entry": entry.model_dump(),
        }

    return router


def attach_to_app(app: FastAPI, store: LeaderboardStore | None = None) -> None:
    """Register the leaderboard router on a FastAPI app instance."""
    app.include_router(build_router(store))
