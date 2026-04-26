"""Live red-team handler — same analyzer, two reward profiles.

Demonstrates the v1→v2 reward-hacking story interactively without requiring
GPU. The user types any message; we score it once with the rule-based
ScriptedAnalyzer (CPU-only) and then evaluate the *same* prediction against
two reward profiles:

    - v1 profile: ``AnalyzerRubric`` with ``DEFAULT_WEIGHTS`` (5 leaves; the
      reward-hacked profile that produced 100% detection / 36% FPR).
    - v2 profile: ``AnalyzerRubricV2`` with ``V2_WEIGHTS`` (8 leaves; the
      principled retrain that holds 99.3% detection at 6.7% FPR).

The asymmetry between the two reward totals is the diagnostic. The model
itself is held fixed — we are showing what would have been *rewarded*
under each profile, which is the actual mechanism by which v1 learned to
over-flag.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from chakravyuh_env import AnalyzerRubric, AnalyzerRubricV2, V2_WEIGHTS
from chakravyuh_env.rubrics import DEFAULT_WEIGHTS
from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
from chakravyuh_env.openenv_models import ChakravyuhAction
from chakravyuh_env.schemas import AnalyzerScore, ChatMessage, Observation


def _score_message(message: str) -> tuple[float, list[str], str]:
    """Run the rule-based analyzer once. Returns (score, signals, explanation)."""
    analyzer = ScriptedAnalyzer()
    obs = Observation(
        agent_role="analyzer",
        turn=1,
        chat_history=[ChatMessage(sender="scammer", turn=1, text=message)],
    )
    action = analyzer.act(obs)
    if isinstance(action, AnalyzerScore):
        signals = [str(s.value if hasattr(s, "value") else s) for s in (action.signals or ())]
        return float(action.score), signals, action.explanation or ""
    return 0.0, [], "(no score returned)"


def _profile_breakdown(
    rubric_class: type,
    weights: dict[str, float],
    score: float,
    signals: list[str],
    explanation: str,
    *,
    is_benign_truth: bool | None,
) -> tuple[dict[str, float], float]:
    """Compute one reward profile's per-leaf scores + composite total."""
    rubric = rubric_class(weights=weights)
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
    action = ChakravyuhAction(
        score=float(score),
        signals=list(signals),
        explanation=explanation,
    )
    obs = SimpleNamespace(done=True, outcome=outcome)
    total = float(rubric.forward(action, obs))
    return rubric.last_scores(), total


def _classify_asymmetry(
    score: float,
    flagged: bool,
    v1_total: float,
    v2_total: float,
    is_benign_truth: bool | None,
) -> tuple[str, str]:
    """Return (badge_class, badge_text) — the reward-hacking diagnostic."""
    delta = v1_total - v2_total
    # Honesty: when there's no ground-truth label, asymmetry is informational.
    if is_benign_truth is True and flagged:
        return (
            "redteam-asym-warning",
            f"v1 reward profile rewards this false-positive (Δ = {delta:+.2f}). "
            f"v2's −0.8 false_positive penalty corrects it. "
            f"This is the reward-hacking signature in one input.",
        )
    if is_benign_truth is False and not flagged:
        return (
            "redteam-asym-warning",
            f"v1 reward profile under-rewards this missed scam (Δ = {delta:+.2f}). "
            f"v2's stronger missed_scam penalty would have nudged the model harder.",
        )
    if abs(delta) < 0.05:
        return (
            "redteam-asym-agree",
            f"Both profiles agree on this verdict (Δ = {delta:+.2f}).",
        )
    direction = "v1 rewards more" if delta > 0 else "v2 rewards more"
    return (
        "redteam-asym-mild",
        f"Mild asymmetry — {direction} (Δ = {delta:+.2f}). "
        f"Tag a benign / scam ground-truth to see the reward-hacking signature fire.",
    )


def render_redteam_view(
    message: str,
    *,
    is_benign_truth: bool | None = None,
) -> tuple[str, str, str]:
    """Public entry point — returns three HTML fragments (v1 card, v2 card, badge).

    is_benign_truth is optional; when provided, the asymmetry diagnostic
    can name the reward-hacking signature explicitly. When None, we report
    the raw v1−v2 delta without claiming it's a hack.
    """
    if not message or not message.strip():
        empty = (
            '<div class="redteam-empty">'
            "Type a scam attempt above and click <strong>Score</strong>. "
            "Try borderline benigns to see v1 over-flag."
            "</div>"
        )
        return empty, empty, ""

    try:
        score, signals, explanation = _score_message(message)
    except Exception as exc:  # noqa: BLE001
        err = (
            f'<div style="padding:12px 16px;background:#FFE8D2;border:1px solid #381932;'
            f'border-radius:10px;color:#000000;font-size:13px;">Analyzer error: {exc!s}</div>'
        )
        return err, err, ""

    flagged = score >= 0.5

    try:
        v1_breakdown, v1_total = _profile_breakdown(
            AnalyzerRubric, DEFAULT_WEIGHTS, score, signals, explanation,
            is_benign_truth=is_benign_truth,
        )
        v2_breakdown, v2_total = _profile_breakdown(
            AnalyzerRubricV2, V2_WEIGHTS, score, signals, explanation,
            is_benign_truth=is_benign_truth,
        )
    except Exception as exc:  # noqa: BLE001
        err = (
            f'<div style="padding:12px 16px;background:#FFE8D2;border:1px solid #381932;'
            f'border-radius:10px;color:#000000;font-size:13px;">Reward profile error: {exc!s}</div>'
        )
        return err, err, ""

    v1_html = _render_card(
        title="v1 reward profile",
        subtitle="reward-hacked · 5 leaves · DEFAULT_WEIGHTS",
        score=score,
        flagged=flagged,
        signals=signals,
        explanation=explanation,
        breakdown=v1_breakdown,
        weights=DEFAULT_WEIGHTS,
        total=v1_total,
        accent="v1",
    )
    v2_html = _render_card(
        title="v2 reward profile",
        subtitle="principled retrain · 8 leaves · V2_WEIGHTS",
        score=score,
        flagged=flagged,
        signals=signals,
        explanation=explanation,
        breakdown=v2_breakdown,
        weights=V2_WEIGHTS,
        total=v2_total,
        accent="v2",
    )
    badge_class, badge_text = _classify_asymmetry(
        score, flagged, v1_total, v2_total, is_benign_truth
    )
    badge_html = (
        f'<div class="redteam-asym {badge_class}" role="status" aria-live="polite">'
        f"<strong>Asymmetry diagnostic:</strong> {badge_text}"
        "</div>"
    )
    return v1_html, v2_html, badge_html


def _render_card(
    *,
    title: str,
    subtitle: str,
    score: float,
    flagged: bool,
    signals: list[str],
    explanation: str,
    breakdown: dict[str, float],
    weights: dict[str, float],
    total: float,
    accent: str,
) -> str:
    """Render one side of the side-by-side reward-profile comparison."""
    chip = (
        '<span class="redteam-flag flagged">FLAGGED</span>'
        if flagged
        else '<span class="redteam-flag clean">not flagged</span>'
    )
    sig_html = (
        " ".join(f'<span class="redteam-sig">{s}</span>' for s in signals)
        if signals
        else '<span class="redteam-sig redteam-sig-empty">no signals</span>'
    )
    rows: list[str] = []
    for name in weights:
        leaf_value = breakdown.get(name)
        weight = weights[name]
        if leaf_value is None:
            cell = '<td class="redteam-leaf-na">—</td>'
        else:
            contribution = float(leaf_value) * weight
            cell = f'<td class="redteam-leaf-val">{leaf_value:+.2f}</td>'
            cell += (
                f'<td class="redteam-leaf-weight">×{weight:+.2f}</td>'
                f'<td class="redteam-leaf-contrib">{contribution:+.2f}</td>'
            )
        rows.append(
            f'<tr><th class="redteam-leaf-name">{name}</th>'
            + (cell if leaf_value is None else cell)
            + "</tr>"
        )
    body = (
        f'<div class="redteam-card redteam-{accent}" role="article" '
        f'aria-label="{title}">'
        f'<div class="redteam-card-head">'
        f'<strong class="redteam-card-title">{title}</strong>'
        f'<span class="redteam-card-subtitle">{subtitle}</span>'
        f"</div>"
        f'<div class="redteam-card-score-row">'
        f'<div class="redteam-score">{score:.2f}</div>'
        f'<div class="redteam-flag-wrap">{chip}</div>'
        f"</div>"
        f'<div class="redteam-signals" aria-label="signals fired">{sig_html}</div>'
        f'<div class="redteam-explanation"><em>{explanation}</em></div>'
        f'<table class="redteam-breakdown"><thead>'
        f'<tr><th>leaf</th><th>score</th><th>weight</th><th>contribution</th></tr>'
        f'</thead><tbody>{"".join(rows)}</tbody>'
        f'<tfoot><tr><th colspan="3" class="redteam-total-label">Composite</th>'
        f'<th class="redteam-total-val">{total:+.2f}</th></tr></tfoot></table>'
        f"</div>"
    )
    return body
