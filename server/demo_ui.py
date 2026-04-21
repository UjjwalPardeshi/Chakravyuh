"""Gradio demo UI for Chakravyuh.

Replay-first design (per CHAKRAVYUH_WIN_PLAN.md Part 8.0):
  - Primary: 5 curated deterministic episodes (zero inference risk)
  - Secondary: Live inference tab for Q&A (custom scam message → suspicion score)

Launch:
    pip install -e '.[demo]'
    python -m server.demo_ui
    # Opens at http://127.0.0.1:7860
"""

from __future__ import annotations

import logging

import gradio as gr  # type: ignore[import-not-found]

from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
from chakravyuh_env.schemas import AnalyzerScore, ChatMessage, Observation
from server.episode_curator import (
    CURATED_EPISODES,
    format_chat_html,
    outcome_badge,
    replay,
)

logger = logging.getLogger("chakravyuh.demo")

# ---------------------------------------------------------------------------
# UI config
# ---------------------------------------------------------------------------

TITLE = "Chakravyuh — 5-Agent Fraud Arena"
SUBTITLE = (
    "A self-improving benchmark for Indian UPI fraud detection. "
    "Every episode below is deterministic (seed-reproducible) and grounded in real RBI/NPCI case studies."
)

CUSTOM_CSS = """
#suspicion-panel {
  border-radius: 8px;
  padding: 20px;
  margin-top: 12px;
  text-align: center;
}
#suspicion-score {
  font-size: 48px;
  font-weight: 800;
  margin: 0;
}
#suspicion-label {
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: #666;
}
#suspicion-explanation {
  font-size: 16px;
  margin-top: 8px;
  color: #333;
}
.outcome-badge {
  font-size: 20px;
  font-weight: 600;
  padding: 12px;
  border-radius: 6px;
  text-align: center;
  margin-top: 12px;
}
"""


def _suspicion_color(score: float) -> tuple[str, str]:
    """Return (background, text) colors for a suspicion score."""
    if score >= 0.7:
        return ("#FDECEA", "#C92A2A")  # red
    if score >= 0.4:
        return ("#FFF9DB", "#E67E22")  # yellow
    return ("#E8F6E9", "#2B8A3E")  # green


def _render_suspicion_panel(score: float, explanation: str) -> str:
    bg, fg = _suspicion_color(score)
    return (
        f'<div id="suspicion-panel" style="background:{bg};">'
        f'<p id="suspicion-label" style="color:{fg};">Suspicion Score</p>'
        f'<p id="suspicion-score" style="color:{fg};">{score:.2f}</p>'
        f'<p id="suspicion-explanation">{explanation or "No signals detected."}</p>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# Tab 1 — Replay mode (primary demo)
# ---------------------------------------------------------------------------


def on_replay_select(label: str) -> tuple[str, str, str, str]:
    """Replay the chosen curated episode; return HTML for each UI panel."""
    episode = next((e for e in CURATED_EPISODES if e.label == label), None)
    if episode is None:
        return ("", _render_suspicion_panel(0.0, ""), "—", "")
    result = replay(episode)
    chat_html = format_chat_html(result.chat_history)

    # Use max analyzer score across turns as the "final" panel display
    if result.analyzer_scores_per_turn:
        max_score = max(s for _, s, _ in result.analyzer_scores_per_turn)
        explanation = next(
            (e for _, s, e in result.analyzer_scores_per_turn if s == max_score),
            "",
        )
    else:
        max_score = 0.0
        explanation = ""
    suspicion_html = _render_suspicion_panel(max_score, explanation)

    outcome_html = (
        f'<div class="outcome-badge" style="background:#F8F9FA;border:1px solid #DEE2E6;">'
        f"{outcome_badge(result.outcome)}</div>"
    )

    info = (
        f"**Seed**: `{result.seed}` &nbsp;&nbsp; "
        f"**Profile**: `{result.profile.value}` &nbsp;&nbsp; "
        f"**Scam category**: `{result.outcome.scam_category.value}` &nbsp;&nbsp; "
        f"**Turns used**: `{result.outcome.turns_used}`"
    )
    return (chat_html, suspicion_html, outcome_html, info)


# ---------------------------------------------------------------------------
# Tab 2 — Live inference (for Q&A)
# ---------------------------------------------------------------------------


def on_live_analyze(user_text: str) -> str:
    """Score an arbitrary user-entered scam message. Rule-based until Day 2."""
    if not user_text.strip():
        return _render_suspicion_panel(0.0, "Enter a message above.")
    analyzer = ScriptedAnalyzer()
    obs = Observation(
        agent_role="analyzer",
        turn=1,
        chat_history=[ChatMessage(sender="scammer", turn=1, text=user_text)],
    )
    action = analyzer.act(obs)
    if isinstance(action, AnalyzerScore):
        return _render_suspicion_panel(action.score, action.explanation)
    return _render_suspicion_panel(0.0, "Analyzer returned no score.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


def build_app() -> gr.Blocks:
    labels = [e.label for e in CURATED_EPISODES]
    with gr.Blocks(title=TITLE, css=CUSTOM_CSS, theme=gr.themes.Soft()) as app:
        gr.Markdown(f"# {TITLE}")
        gr.Markdown(SUBTITLE)

        with gr.Tabs():
            # -- Replay Tab --
            with gr.Tab("🎬 Replay (5 Cherry-Picked Episodes)"):
                with gr.Row():
                    episode_picker = gr.Radio(
                        choices=labels,
                        value=labels[0],
                        label="Select episode",
                    )
                info_panel = gr.Markdown("")
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("### Conversation")
                        chat_display = gr.HTML(
                            value=format_chat_html([]),
                            label="Chat",
                        )
                    with gr.Column(scale=1):
                        gr.Markdown("### Analyzer Verdict")
                        suspicion_display = gr.HTML(
                            value=_render_suspicion_panel(0.0, ""),
                            label="Suspicion",
                        )
                        outcome_display = gr.HTML(value="")

                episode_picker.change(
                    on_replay_select,
                    inputs=[episode_picker],
                    outputs=[chat_display, suspicion_display, outcome_display, info_panel],
                )

                # Initial render with first episode
                chat0, susp0, outcome0, info0 = on_replay_select(labels[0])
                chat_display.value = chat0
                suspicion_display.value = susp0
                outcome_display.value = outcome0
                info_panel.value = info0

            # -- Live Inference Tab --
            with gr.Tab("🔬 Live (Try Your Own Message)"):
                gr.Markdown(
                    "Paste a suspicious message and the Analyzer will score it live. "
                    "Day 1 uses a rule-based baseline; Day 2+ swaps in the LoRA-trained Qwen2.5-7B."
                )
                with gr.Row():
                    user_input = gr.Textbox(
                        label="Message to analyze",
                        placeholder="e.g. 'Your SBI KYC expires today, share OTP to verify...'",
                        lines=4,
                    )
                analyze_btn = gr.Button("🔎 Analyze", variant="primary")
                live_suspicion = gr.HTML(
                    value=_render_suspicion_panel(0.0, "Enter a message and click Analyze.")
                )
                analyze_btn.click(
                    on_live_analyze,
                    inputs=[user_input],
                    outputs=[live_suspicion],
                )
                gr.Examples(
                    examples=[
                        "Dear customer, your SBI KYC expires today. Click https://sbi-kyc.xyz to update within 2 hours or account frozen.",
                        "Congratulations! You won Rs 25,000 in PNB lucky draw. Share OTP to claim.",
                        "Your Amazon order is out for delivery. Expected between 4-7 PM. Track at amazon.in/orders",
                    ],
                    inputs=[user_input],
                )

        gr.Markdown(
            "---\n*Chakravyuh is an open-source benchmark for Indian UPI fraud detection. "
            "Benchmark: `chakravyuh-bench-v0` (n=135). MIT license.*"
        )
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860, show_api=False)


if __name__ == "__main__":
    main()
