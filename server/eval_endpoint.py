"""GET /eval, /eval/bootstrap, /eval/leaderboard — research endpoints.

Each endpoint returns a cached eval artifact from ``logs/`` so judges and
researchers can fetch the load-bearing numbers in one HTTP call without
spinning up a GPU. The artifacts themselves are version-pinned in git
(see ``.gitignore`` allow-list).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def _load_json(name: str) -> dict[str, Any]:
    path = LOGS_DIR / name
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"{name} not found at {path}. Run `make eval-v2 && make bootstrap` "
                "or pull the latest artifacts from the repo."
            ),
        )
    return json.loads(path.read_text())


def build_router() -> APIRouter:
    router = APIRouter(tags=["eval"])

    @router.get("/eval")
    def get_eval() -> dict[str, Any]:
        """Return the v2 eval artifact (`logs/eval_v2.json`)."""
        return _load_json("eval_v2.json")

    @router.get("/eval/bootstrap")
    def get_bootstrap() -> dict[str, Any]:
        """Return the 10k-iter percentile bootstrap CIs (`logs/bootstrap_v2.json`)."""
        return _load_json("bootstrap_v2.json")

    @router.get("/eval/known-novel")
    def get_known_novel() -> dict[str, Any]:
        """Return the known-vs-novel split eval (`logs/eval_v2_known_novel.json`)."""
        return _load_json("eval_v2_known_novel.json")

    @router.get("/eval/redteam")
    def get_redteam() -> dict[str, Any]:
        """Return the rule-based-analyzer red-team eval."""
        return _load_json("analyzer_robustness.json")

    @router.get("/eval/time-to-detection")
    def get_ttd() -> dict[str, Any]:
        """Return the time-to-detection metric on the env-rollout baseline."""
        return _load_json("time_to_detection.json")

    @router.get("/eval/ablation")
    def get_ablation() -> dict[str, Any]:
        """Return the per-rubric ablation study."""
        return _load_json("ablation_study.json")

    return router


def attach_to_app(app: FastAPI) -> None:
    app.include_router(build_router())
