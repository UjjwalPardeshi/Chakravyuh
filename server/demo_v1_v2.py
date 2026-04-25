"""v1 vs v2 archived-response toggle — the wow moment.

Side-by-side rendering of v1 (reward-hacked) and v2 (fixed) analyzer
responses on the same scenario. Backed by `data/v1_v2_archived_responses.json`,
NOT a live re-run — see that file's `_provenance` block for honest framing.

This module is intentionally pure-data: the Gradio Tab consuming it lives
in `server/demo_ui.py` and only calls `render_toggle_view(scenario_id)`.
"""

from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "v1_v2_archived_responses.json"

PLUM = "#381932"
CREAM = "#FFF3E6"
CREAM_2 = "#FFFBF5"


@lru_cache(maxsize=1)
def load_archived_data() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text())


def list_scenario_choices() -> list[tuple[str, str]]:
    """Return ``[(label, scenario_id), …]`` for the Radio choice list."""
    data = load_archived_data()
    return [(s["label"], s["id"]) for s in data["scenarios"]]


def _render_panel(version: str, response: dict[str, Any], ground_truth: str) -> str:
    score = float(response["score"])
    flagged = bool(response["flagged"])
    signals = response.get("signals") or []
    explanation = response.get("explanation") or ""

    # Was the model's call correct? (compares flagged-vs-ground-truth)
    correct = (flagged and ground_truth == "scam") or (not flagged and ground_truth == "benign")
    correctness_chip = (
        '<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        'font-size:11px;font-weight:700;letter-spacing:0.4px;'
        + (
            'background:#0A6E3F;color:#FFFFFF;">✓ CORRECT</span>'
            if correct
            else 'background:#9C1B1B;color:#FFFFFF;">✗ WRONG</span>'
        )
    )

    score_color = PLUM if flagged else "#0A6E3F"
    score_label = "FLAGGED" if flagged else "PASSED"
    bar_pct = int(score * 100)

    version_pill_color = "#9C1B1B" if version == "v1" else PLUM
    version_pill_label = (
        "v1 · reward-hacked"
        if version == "v1"
        else "v2 · principled retrain"
    )

    sig_html = (
        "".join(
            f'<span style="display:inline-block;padding:2px 9px;margin:2px 4px 2px 0;'
            f'border-radius:999px;background:{CREAM_2};border:1px solid {PLUM}33;'
            f'font-size:11px;font-weight:600;color:{PLUM};">{html.escape(s)}</span>'
            for s in signals
        )
        or '<span style="font-size:11px;color:#000000;opacity:0.55;">(none)</span>'
    )

    return f"""
<div class="ck-vsversion-panel" style="
    padding:18px;border:1px solid {PLUM}33;border-radius:12px;
    background:{CREAM_2};font-family:Inter, system-ui, sans-serif;
    color:#000000;
">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
    <span style="display:inline-block;padding:4px 11px;border-radius:999px;
                 background:{version_pill_color};color:#FFFFFF;
                 font-size:11px;font-weight:800;letter-spacing:0.6px;">
      {version_pill_label}
    </span>
    {correctness_chip}
  </div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;
              margin-bottom:10px;">
    <span style="font-size:11px;font-weight:700;letter-spacing:0.8px;
                 text-transform:uppercase;color:#000000;opacity:0.72;">
      Suspicion score
    </span>
    <span style="font-size:24px;font-weight:800;color:{score_color};
                 font-variant-numeric:tabular-nums;">{score:.2f}</span>
  </div>
  <div style="height:8px;border-radius:4px;background:{PLUM}1A;
              overflow:hidden;margin-bottom:14px;">
    <div style="height:100%;width:{bar_pct}%;background:{score_color};
                transition:width .4s ease;"></div>
  </div>
  <div style="font-size:13px;font-weight:700;color:{score_color};
              margin-bottom:10px;letter-spacing:0.3px;">
    {score_label}
  </div>
  <div style="font-size:11px;font-weight:700;letter-spacing:0.6px;
              text-transform:uppercase;color:#000000;opacity:0.62;
              margin:8px 0 6px;">
    Signals
  </div>
  <div style="line-height:1.7;margin-bottom:14px;">{sig_html}</div>
  <div style="font-size:11px;font-weight:700;letter-spacing:0.6px;
              text-transform:uppercase;color:#000000;opacity:0.62;
              margin:8px 0 6px;">
    Reasoning
  </div>
  <p style="font-size:13px;line-height:1.55;margin:0;color:#000000;">
    {html.escape(explanation)}
  </p>
</div>
""".strip()


def render_toggle_view(scenario_id: str) -> tuple[str, str, str, str]:
    """Return ``(prompt_html, v1_html, v2_html, asymmetry_html)``."""
    data = load_archived_data()
    matches = [s for s in data["scenarios"] if s["id"] == scenario_id]
    if not matches:
        empty = "<em>scenario not found</em>"
        return empty, empty, empty, empty
    scenario = matches[0]
    ground_truth = scenario["ground_truth"]

    gt_color = "#0A6E3F" if ground_truth == "benign" else "#9C1B1B"
    gt_label = "ground truth: benign" if ground_truth == "benign" else "ground truth: scam"

    prompt_html = (
        f'<div style="padding:14px 18px;background:{CREAM_2};border:1px solid {PLUM}1F;'
        f'border-radius:10px;font-family:Inter, system-ui, sans-serif;color:#000000;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<span style="font-size:11px;font-weight:700;letter-spacing:0.8px;'
        f'text-transform:uppercase;color:#000000;opacity:0.72;">Scenario · '
        f'{html.escape(scenario["id"])} · {html.escape(scenario["difficulty"])}</span>'
        f'<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        f'background:{gt_color};color:#FFFFFF;font-size:11px;font-weight:700;'
        f'letter-spacing:0.4px;">{gt_label}</span></div>'
        f'<p style="margin:0;font-size:14px;line-height:1.55;color:#000000;">'
        f'<strong>Prompt:</strong> {html.escape(scenario["prompt"])}</p></div>'
    )

    v1_html = _render_panel("v1", scenario["v1"], ground_truth)
    v2_html = _render_panel("v2", scenario["v2"], ground_truth)

    verdict = scenario.get("verdict") or ""
    asymmetry_html = (
        f'<div style="padding:14px 18px;background:{CREAM};border:1.5px solid {PLUM};'
        f'border-radius:10px;color:#000000;font-size:13px;line-height:1.6;'
        f'margin-top:14px;">'
        f'<strong style="color:{PLUM};">What this shows:</strong> '
        f'{html.escape(verdict)}'
        f'</div>'
    )

    return prompt_html, v1_html, v2_html, asymmetry_html


def render_summary_banner() -> str:
    """The persistent "archived not live" + headline-numbers banner."""
    data = load_archived_data()
    summary = data["summary"]
    note = data["_provenance"]["honest_note"]
    return f"""
<div style="padding:14px 18px;background:{CREAM_2};border:1px solid {PLUM}55;
            border-radius:10px;font-size:13px;line-height:1.6;color:#000000;
            font-family:Inter, system-ui, sans-serif;margin-bottom:18px;">
  <div style="font-size:11px;font-weight:800;letter-spacing:0.8px;
              text-transform:uppercase;color:{PLUM};margin-bottom:4px;">
    ARCHIVED RESPONSES — not a live re-run
  </div>
  <p style="margin:0 0 8px;font-size:13px;color:#000000;">
    {html.escape(note)}
  </p>
  <p style="margin:0;font-size:13px;color:#000000;">
    <strong>Aggregate evidence (live):</strong>
    v1 = {summary['v1']['detection']*100:.0f}% / FPR {summary['v1']['fpr']*100:.0f}% (n={summary['v1']['n']});
    v2 = {summary['v2']['detection']*100:.1f}% / FPR {summary['v2']['fpr']*100:.1f}% (n={summary['v2']['n']}).
    <em>{summary['delta']['interpretation']}</em>
  </p>
</div>
""".strip()
