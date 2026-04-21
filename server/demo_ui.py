"""Gradio demo UI for Chakravyuh.

Replay-first design (per CHAKRAVYUH_WIN_PLAN.md Part 8.0):
  - Primary: 5 curated deterministic episodes (zero inference risk)
  - Secondary: Live inference tab for Q&A (custom scam message → suspicion score)

Features:
  - Auto-play or step-through turn-by-turn (Prev / Next buttons)
  - Keyword highlighting on scammer messages (urgency / info_request / impersonation)
  - Suspicion timeline — watch the score climb across analyzer turns
  - Bank Monitor panel — independent oversight, separate from Analyzer

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
    ReplayedEpisode,
    format_bank_panel,
    format_chat_html,
    format_suspicion_timeline,
    max_turn,
    outcome_badge,
    replay,
    suspicion_score_for_turn,
)

logger = logging.getLogger("chakravyuh.demo")

TITLE = "Chakravyuh — 5-Agent Fraud Arena"
SUBTITLE = (
    "A self-improving benchmark for Indian UPI fraud detection. "
    "Every episode is deterministic (seed-reproducible) and grounded in real RBI/NPCI case studies."
)

CUSTOM_CSS = """
#suspicion-panel {
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
#suspicion-score {
  font-size: 44px;
  font-weight: 800;
  margin: 4px 0;
  line-height: 1;
}
#suspicion-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
}
#suspicion-explanation {
  font-size: 13px;
  margin-top: 6px;
}
.outcome-badge {
  font-size: 18px;
  font-weight: 700;
  padding: 14px;
  border-radius: 6px;
  text-align: center;
}
#playback-controls button {
  min-width: 120px;
}
"""

# Replay mode labels (strings used directly in radio/state)
MODE_AUTO = "Auto-play (full episode)"
MODE_STEP = "Step-through (turn by turn)"


def _suspicion_color(score: float) -> tuple[str, str]:
    """Return (background, foreground) colors for a suspicion score."""
    if score >= 0.7:
        return ("#FDECEA", "#C92A2A")
    if score >= 0.4:
        return ("#FFF9DB", "#E67E22")
    return ("#E8F6E9", "#2B8A3E")


def _render_suspicion_score(score: float, explanation: str) -> str:
    bg, fg = _suspicion_color(score)
    return (
        f'<div id="suspicion-panel" style="background:{bg};">'
        f'<p id="suspicion-label" style="color:{fg};">Suspicion Score</p>'
        f'<p id="suspicion-score" style="color:{fg};">{score:.2f}</p>'
        f'<p id="suspicion-explanation" style="color:#333;">'
        f"{explanation or 'No signals detected.'}</p>"
        "</div>"
    )


def _render_outcome_badge(text: str) -> str:
    return (
        '<div class="outcome-badge" style="background:#F8F9FA;'
        'border:1px solid #DEE2E6;color:#1a1a1a;">'
        f"{text}</div>"
    )


def _render_metadata(ep: ReplayedEpisode, current_turn: int, total_turns: int) -> str:
    return (
        f"**Seed**: `{ep.seed}` &nbsp;&nbsp; "
        f"**Profile**: `{ep.profile.value}` &nbsp;&nbsp; "
        f"**Scam category**: `{ep.outcome.scam_category.value}` &nbsp;&nbsp; "
        f"**Turn**: `{current_turn}/{total_turns}`"
    )


# ---------------------------------------------------------------------------
# State model
# ---------------------------------------------------------------------------
# State dict flows through gr.State:
#   {
#     "label": str,         # episode label currently loaded
#     "mode": str,          # MODE_AUTO or MODE_STEP
#     "current_turn": int,  # 0 = nothing shown yet; total = full
#     "total_turns": int,   # max turn number in the episode
#     "episode_cache": dict  # ReplayedEpisode cached as dict is hard; we re-replay
#   }
#
# Because ReplayedEpisode isn't trivially JSON-serializable by Gradio State,
# we re-run replay() on state changes (fast: ~milliseconds for scripted env).


def _load_episode(label: str) -> ReplayedEpisode:
    ep = next((e for e in CURATED_EPISODES if e.label == label), None)
    if ep is None:
        ep = CURATED_EPISODES[0]
    return replay(ep)


def _render_all(
    label: str, mode: str, current_turn: int
) -> tuple[str, str, str, str, str, str, gr.update, gr.update]:
    """Produce all UI outputs for a given (label, mode, turn)."""
    episode = _load_episode(label)
    total = max_turn(episode)

    visible_turn = total if mode == MODE_AUTO else max(0, min(current_turn, total))

    chat_html = format_chat_html(
        episode.chat_history, up_to_turn=visible_turn if mode == MODE_STEP else None
    )
    score, explanation = suspicion_score_for_turn(
        episode.analyzer_snapshots,
        up_to_turn=visible_turn if mode == MODE_STEP else None,
    )
    suspicion_html = _render_suspicion_score(score, explanation)
    timeline_html = format_suspicion_timeline(
        episode.analyzer_snapshots,
        up_to_turn=visible_turn if mode == MODE_STEP else None,
    )
    bank_html = format_bank_panel(
        episode.bank_snapshots,
        episode.transaction,
        up_to_turn=visible_turn if mode == MODE_STEP else None,
    )
    # Outcome only shown at the very end (step mode) or always (auto mode)
    if mode == MODE_AUTO or visible_turn >= total:
        outcome_html = _render_outcome_badge(outcome_badge(episode.outcome))
    else:
        outcome_html = _render_outcome_badge("— Episode in progress —")

    metadata = _render_metadata(
        episode,
        current_turn=visible_turn,
        total_turns=total,
    )

    # Button visibility — only relevant in step mode
    show_controls = mode == MODE_STEP
    prev_update = gr.update(interactive=show_controls and visible_turn > 0)
    next_update = gr.update(interactive=show_controls and visible_turn < total)

    return (
        chat_html,
        suspicion_html,
        timeline_html,
        bank_html,
        outcome_html,
        metadata,
        prev_update,
        next_update,
    )


def on_episode_change(label: str, mode: str) -> tuple:
    """User picked a different episode. Reset turn counter."""
    # In step-through mode, reset to turn 0 (nothing shown yet)
    # In auto-play, jump to end
    episode = _load_episode(label)
    total = max_turn(episode)
    current = 0 if mode == MODE_STEP else total
    ui = _render_all(label, mode, current)
    # Return new state + all UI outputs
    return (
        {"label": label, "mode": mode, "current_turn": current, "total_turns": total},
        *ui,
    )


def on_mode_change(label: str, mode: str, state: dict | None) -> tuple:
    """Toggle auto-play vs step-through."""
    episode = _load_episode(label)
    total = max_turn(episode)
    current = 0 if mode == MODE_STEP else total
    ui = _render_all(label, mode, current)
    return (
        {"label": label, "mode": mode, "current_turn": current, "total_turns": total},
        *ui,
    )


def on_next_turn(state: dict) -> tuple:
    if not state:
        return (state, *_render_all(CURATED_EPISODES[0].label, MODE_STEP, 0))
    new_turn = min(state["total_turns"], state["current_turn"] + 1)
    new_state = {**state, "current_turn": new_turn}
    ui = _render_all(state["label"], state["mode"], new_turn)
    return (new_state, *ui)


def on_prev_turn(state: dict) -> tuple:
    if not state:
        return (state, *_render_all(CURATED_EPISODES[0].label, MODE_STEP, 0))
    new_turn = max(0, state["current_turn"] - 1)
    new_state = {**state, "current_turn": new_turn}
    ui = _render_all(state["label"], state["mode"], new_turn)
    return (new_state, *ui)


def on_reset(state: dict) -> tuple:
    if not state:
        return (state, *_render_all(CURATED_EPISODES[0].label, MODE_STEP, 0))
    new_state = {**state, "current_turn": 0}
    ui = _render_all(state["label"], state["mode"], 0)
    return (new_state, *ui)


# ---------------------------------------------------------------------------
# Live Q&A tab
# ---------------------------------------------------------------------------


def on_live_analyze(user_text: str) -> str:
    if not user_text.strip():
        return _render_suspicion_score(0.0, "Enter a message above.")
    analyzer = ScriptedAnalyzer()
    obs = Observation(
        agent_role="analyzer",
        turn=1,
        chat_history=[ChatMessage(sender="scammer", turn=1, text=user_text)],
    )
    action = analyzer.act(obs)
    if isinstance(action, AnalyzerScore):
        return _render_suspicion_score(action.score, action.explanation)
    return _render_suspicion_score(0.0, "Analyzer returned no score.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


def build_app() -> gr.Blocks:
    labels = [e.label for e in CURATED_EPISODES]
    default_label = labels[0]
    default_mode = MODE_AUTO

    with gr.Blocks(title=TITLE) as app:
        gr.Markdown(f"# {TITLE}")
        gr.Markdown(SUBTITLE)

        with gr.Tabs():
            # ============= Replay Tab =============
            with gr.Tab("🎬 Replay (5 Cherry-Picked Episodes)"):
                episode_picker = gr.Radio(
                    choices=labels,
                    value=default_label,
                    label="Select episode",
                )

                mode_picker = gr.Radio(
                    choices=[MODE_AUTO, MODE_STEP],
                    value=default_mode,
                    label="Playback mode",
                )

                info_panel = gr.Markdown("")

                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("### Conversation")
                        chat_display = gr.HTML(value=format_chat_html([]))
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔍 Analyzer Verdict")
                        suspicion_display = gr.HTML(value=_render_suspicion_score(0.0, ""))
                        gr.Markdown("**Suspicion Timeline**")
                        timeline_display = gr.HTML(
                            value=format_suspicion_timeline([])
                        )
                        gr.Markdown("### 🏦 Bank Monitor")
                        bank_display = gr.HTML(value=format_bank_panel([], None))

                outcome_display = gr.HTML(value=_render_outcome_badge("—"))

                with gr.Row(elem_id="playback-controls"):
                    prev_btn = gr.Button("◀ Prev Turn", interactive=False)
                    next_btn = gr.Button("Next Turn ▶", interactive=False)
                    reset_btn = gr.Button("↻ Reset to Start")

                # State: track current episode + mode + turn
                state = gr.State(
                    value={
                        "label": default_label,
                        "mode": default_mode,
                        "current_turn": 0,
                        "total_turns": 0,
                    }
                )

                ui_outputs = [
                    chat_display,
                    suspicion_display,
                    timeline_display,
                    bank_display,
                    outcome_display,
                    info_panel,
                    prev_btn,
                    next_btn,
                ]

                episode_picker.change(
                    on_episode_change,
                    inputs=[episode_picker, mode_picker],
                    outputs=[state, *ui_outputs],
                )
                mode_picker.change(
                    on_mode_change,
                    inputs=[episode_picker, mode_picker, state],
                    outputs=[state, *ui_outputs],
                )
                next_btn.click(
                    on_next_turn,
                    inputs=[state],
                    outputs=[state, *ui_outputs],
                )
                prev_btn.click(
                    on_prev_turn,
                    inputs=[state],
                    outputs=[state, *ui_outputs],
                )
                reset_btn.click(
                    on_reset,
                    inputs=[state],
                    outputs=[state, *ui_outputs],
                )

                # Prime UI with the default episode in auto-play
                (
                    initial_chat,
                    initial_susp,
                    initial_timeline,
                    initial_bank,
                    initial_outcome,
                    initial_info,
                    _,
                    _,
                ) = _render_all(default_label, default_mode, 0)
                chat_display.value = initial_chat
                suspicion_display.value = initial_susp
                timeline_display.value = initial_timeline
                bank_display.value = initial_bank
                outcome_display.value = initial_outcome
                info_panel.value = initial_info
                state.value = {
                    "label": default_label,
                    "mode": default_mode,
                    "current_turn": max_turn(_load_episode(default_label)),
                    "total_turns": max_turn(_load_episode(default_label)),
                }

            # ============= Live Q&A Tab =============
            with gr.Tab("🔬 Live (Try Your Own Message)"):
                gr.Markdown(
                    "Paste a suspicious message and the Analyzer will score it live. "
                    "Day 1 uses a rule-based baseline; Day 2+ swaps in the LoRA-trained Qwen2.5-7B."
                )
                user_input = gr.Textbox(
                    label="Message to analyze",
                    placeholder="e.g. 'Your SBI KYC expires today, share OTP to verify...'",
                    lines=4,
                )
                analyze_btn = gr.Button("🔎 Analyze", variant="primary")
                live_suspicion = gr.HTML(
                    value=_render_suspicion_score(0.0, "Enter a message and click Analyze.")
                )
                analyze_btn.click(on_live_analyze, inputs=[user_input], outputs=[live_suspicion])
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
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
