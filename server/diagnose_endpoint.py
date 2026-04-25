"""POST /diagnose — single-message rubric breakdown.

Takes one suspicious-looking message and returns the rule-based scripted
analyzer's verdict **plus** the V2 rubric decomposition for that verdict.
Designed for researchers and demo polish: one curl, eight-leaf reward.

The endpoint runs the `ScriptedAnalyzer` (CPU-only) so it works on the
HF Space without a GPU. The LoRA path is left as a future opt-in via
the `CHAKRAVYUH_DEMO_LORA=1` env flag.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from chakravyuh_env import AnalyzerRubricV2
from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
from chakravyuh_env.openenv_models import ChakravyuhAction
from chakravyuh_env.schemas import AnalyzerScore, ChatMessage, Observation


class DiagnoseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    expected_signals: list[str] | None = Field(
        default=None,
        description=(
            "Optional ground-truth signal taxonomy for the message. When "
            "provided, the SignalAccuracyRubric leaf reports recall against "
            "this set. Must be names from the AnalyzerSignal enum."
        ),
    )
    is_benign_truth: bool | None = Field(
        default=None,
        description=(
            "Optional ground-truth benign flag. When provided, the rubric "
            "decomposition treats the message as a benign sample (so the "
            "false_positive and benign-calibration leaves fire correctly)."
        ),
    )


class DiagnoseResponse(BaseModel):
    score: float
    flagged: bool
    threshold: float
    signals: list[str]
    explanation: str
    rubric_breakdown: dict[str, float | None]
    rubric_total: float
    analyzer: Literal["rule_based_scripted", "lora_v2_via_api"] = "rule_based_scripted"
    note: str = (
        "Score from the rule-based ScriptedAnalyzer. The rubric_breakdown "
        "is computed by AnalyzerRubricV2 (env-default; matches the v2 "
        "training reward profile) on a synthesized terminal observation. "
        "LoRA path requires GPU — currently CPU-only."
    )


def _score_with_scripted_analyzer(message: str) -> AnalyzerScore:
    analyzer = ScriptedAnalyzer()
    obs = Observation(
        agent_role="analyzer",
        turn=1,
        chat_history=[ChatMessage(sender="scammer", turn=1, text=message)],
    )
    action = analyzer.act(obs)
    if isinstance(action, AnalyzerScore):
        return action
    return AnalyzerScore(score=0.0, signals=(), explanation="(no score returned)")


def _build_rubric_breakdown(
    score: float,
    signals: list[str],
    explanation: str,
    expected_signals: list[str] | None,
    is_benign_truth: bool | None,
) -> tuple[dict[str, Any], float]:
    """Run AnalyzerRubricV2 on a synthesized terminal observation.

    The rubric is trajectory-aware (only fires on `done=True`); we
    synthesise a single-step terminal observation with the same shape
    the env emits so the leaf rubrics' `last_score` is populated.
    """
    rubric = AnalyzerRubricV2()
    flag_threshold = 0.5
    flagged = score >= flag_threshold
    is_benign = bool(is_benign_truth) if is_benign_truth is not None else False
    outcome: dict[str, Any] = {
        "analyzer_flagged": flagged,
        "detected_by_turn": 1 if (flagged and not is_benign) else None,
        "is_benign": is_benign,
        "false_positive": flagged and is_benign,
        "money_extracted": False,
    }
    if expected_signals:
        outcome["expected_signals"] = list(expected_signals)
    action = ChakravyuhAction(
        score=float(score),
        signals=list(signals),
        explanation=explanation,
    )

    class _Obs:
        done = True

    obs = _Obs()
    obs.outcome = outcome  # type: ignore[attr-defined]

    total = float(rubric.forward(action, obs))
    return rubric.last_scores(), total


def build_router() -> APIRouter:
    router = APIRouter(tags=["diagnose"])

    @router.post("/diagnose", response_model=DiagnoseResponse)
    def post_diagnose(req: DiagnoseRequest) -> DiagnoseResponse:
        scored = _score_with_scripted_analyzer(req.message)
        signals = [str(s.value if hasattr(s, "value") else s) for s in (scored.signals or ())]
        breakdown, total = _build_rubric_breakdown(
            score=float(scored.score),
            signals=signals,
            explanation=scored.explanation or "",
            expected_signals=req.expected_signals,
            is_benign_truth=req.is_benign_truth,
        )
        return DiagnoseResponse(
            score=float(scored.score),
            flagged=float(scored.score) >= 0.5,
            threshold=0.5,
            signals=signals,
            explanation=scored.explanation or "",
            rubric_breakdown=breakdown,
            rubric_total=total,
        )

    return router


def attach_to_app(app: FastAPI) -> None:
    app.include_router(build_router())
