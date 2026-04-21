"""Gradio demo UI for Chakravyuh — visual v2.

Upgrades in this iteration:
  A. Animated suspicion bars (CSS transitions)
  B. 5-agent status card grid (hero multi-agent visual)
  C. Theme-aware CSS using Gradio CSS variables (works on light + dark)
  D. Attack timeline — one icon per turn, color-coded by actor
  E. Larger typography + breathing room

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
    compute_agent_states,
    format_agent_cards_html,
    format_attack_timeline_html,
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

# ---------------------------------------------------------------------------
# Theme-aware CSS (Gradio CSS variables → auto-adapt light/dark)
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
.chakravyuh-container {
  max-width: 1200px;
  margin: 0 auto;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* Hero title */
.chakravyuh-title {
  font-size: 32px !important;
  font-weight: 800 !important;
  margin-bottom: 4px !important;
  letter-spacing: -0.5px;
}
.chakravyuh-subtitle {
  font-size: 14px !important;
  color: var(--body-text-color-subdued, #888) !important;
  margin-bottom: 16px !important;
}

/* Agent grid — hero multi-agent strip */
.agent-grid {
  transition: opacity 0.3s ease;
}
.agent-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.agent-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
}

/* Pulsing indicator for warning/critical states */
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.65; }
}
.pulse { animation: pulse-dot 1.6s ease-in-out infinite; }

/* Animated suspicion bar fill */
.suspicion-bar-fill {
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              background-color 0.35s ease;
}

/* Suspicion score panel */
#suspicion-panel {
  border-radius: 12px;
  padding: 18px;
  text-align: center;
  transition: background 0.35s ease;
}
#suspicion-score {
  font-size: 48px;
  font-weight: 800;
  margin: 4px 0;
  line-height: 1;
  transition: color 0.35s ease;
}
#suspicion-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  opacity: 0.85;
}
#suspicion-explanation {
  font-size: 13px;
  margin-top: 6px;
  color: var(--body-text-color, #333) !important;
  opacity: 0.85;
}

/* Outcome badge */
.outcome-badge {
  font-size: 20px;
  font-weight: 800;
  padding: 18px;
  border-radius: 10px;
  text-align: center;
  margin: 12px 0;
  letter-spacing: 0.3px;
}

/* Attack timeline */
.attack-timeline {
  border: 1px solid var(--border-color-primary, #e5e5e5);
  border-radius: 10px;
  background: var(--background-fill-secondary, rgba(127,127,127,0.04));
}
.timeline-step {
  transition: opacity 0.3s ease, transform 0.2s ease;
}

/* Panel headers — stronger hierarchy */
.panel-heading {
  font-size: 13px !important;
  font-weight: 700 !important;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--body-text-color-subdued, #888) !important;
  margin: 14px 0 6px !important;
}

/* Playback controls */
#playback-controls {
  gap: 12px;
  margin: 12px 0;
}
#playback-controls button {
  min-width: 120px;
  font-weight: 600;
}

/* Larger breathing room */
.gr-block {
  padding: 0 !important;
}
"""

MODE_AUTO = "Auto-play (full episode)"
MODE_STEP = "Step-through (turn by turn)"


def _suspicion_color(score: float) -> tuple[str, str]:
    """Return (background, foreground) colors for a suspicion score panel."""
    if score >= 0.7:
        return ("rgba(201, 42, 42, 0.10)", "#C92A2A")  # red
    if score >= 0.4:
        return ("rgba(230, 126, 34, 0.10)", "#E67E22")  # amber
    return ("rgba(43, 138, 62, 0.10)", "#2B8A3E")       # green


def _render_suspicion_score(score: float, explanation: str) -> str:
    bg, fg = _suspicion_color(score)
    pct = int(score * 100)
    return (
        f'<div id="suspicion-panel" style="background:{bg};'
        f'border:1px solid {fg}33;">'
        f'<p id="suspicion-label" style="color:{fg};">Suspicion Score</p>'
        f'<p id="suspicion-score" style="color:{fg};">{score:.2f}</p>'
        # Horizontal progress bar (animated via CSS)
        f'<div style="background:rgba(127,127,127,0.15);height:8px;'
        f'border-radius:4px;overflow:hidden;margin:10px 0 8px;">'
        f'<div class="suspicion-bar-fill" '
        f'style="background:{fg};width:{pct}%;height:100%;"></div>'
        f"</div>"
        f'<p id="suspicion-explanation">{explanation or "No signals detected."}</p>'
        "</div>"
    )


def _render_outcome_badge(text: str) -> str:
    # Tone-aware background: success/danger/neutral based on content
    if "MONEY EXTRACTED" in text:
        bg, fg = "rgba(201, 42, 42, 0.12)", "#C92A2A"
    elif "FROZE" in text or "REFUSED" in text or "VERIFIED" in text:
        bg, fg = "rgba(43, 138, 62, 0.12)", "#2B8A3E"
    elif "FLAGGED" in text:
        bg, fg = "rgba(230, 126, 34, 0.12)", "#E67E22"
    else:
        bg, fg = "rgba(127,127,127,0.08)", "var(--body-text-color, #333)"
    return (
        f'<div class="outcome-badge" style="background:{bg};color:{fg};'
        f'border:1px solid {fg if isinstance(fg, str) and fg.startswith("#") else "#999"}33;">'
        f"{text}</div>"
    )


def _render_metadata(ep: ReplayedEpisode, current_turn: int, total_turns: int) -> str:
    return (
        f"&nbsp;&nbsp;**Seed**: `{ep.seed}` &nbsp;·&nbsp; "
        f"**Profile**: `{ep.profile.value}` &nbsp;·&nbsp; "
        f"**Category**: `{ep.outcome.scam_category.value}` &nbsp;·&nbsp; "
        f"**Turn**: `{current_turn}/{total_turns}`"
    )


# ---------------------------------------------------------------------------
# State & render orchestration
# ---------------------------------------------------------------------------


def _load_episode(label: str) -> ReplayedEpisode:
    ep = next((e for e in CURATED_EPISODES if e.label == label), None)
    if ep is None:
        ep = CURATED_EPISODES[0]
    return replay(ep)


def _render_all(
    label: str, mode: str, current_turn: int
) -> tuple[str, str, str, str, str, str, str, str, gr.update, gr.update]:
    """Produce ALL UI outputs for a given (label, mode, turn)."""
    episode = _load_episode(label)
    total = max_turn(episode)

    visible_turn = total if mode == MODE_AUTO else max(0, min(current_turn, total))
    cutoff = visible_turn if mode == MODE_STEP else None

    # 1. Agent cards
    states = compute_agent_states(episode, up_to_turn=cutoff)
    agent_cards_html = format_agent_cards_html(states)

    # 2. Attack timeline
    timeline_ribbon_html = format_attack_timeline_html(episode, up_to_turn=cutoff)

    # 3. Chat
    chat_html = format_chat_html(episode.chat_history, up_to_turn=cutoff)

    # 4. Suspicion score + timeline
    score, explanation = suspicion_score_for_turn(
        episode.analyzer_snapshots, up_to_turn=cutoff
    )
    suspicion_html = _render_suspicion_score(score, explanation)
    suspicion_timeline_html = format_suspicion_timeline(
        episode.analyzer_snapshots, up_to_turn=cutoff
    )

    # 5. Bank panel
    bank_html = format_bank_panel(
        episode.bank_snapshots, episode.transaction, up_to_turn=cutoff
    )

    # 6. Outcome badge
    if mode == MODE_AUTO or visible_turn >= total:
        outcome_html = _render_outcome_badge(outcome_badge(episode.outcome))
    else:
        outcome_html = _render_outcome_badge("— Episode in progress —")

    # 7. Metadata
    metadata = _render_metadata(episode, current_turn=visible_turn, total_turns=total)

    # 8. Button interactivity
    show_controls = mode == MODE_STEP
    prev_update = gr.update(interactive=show_controls and visible_turn > 0)
    next_update = gr.update(interactive=show_controls and visible_turn < total)

    return (
        agent_cards_html,
        timeline_ribbon_html,
        chat_html,
        suspicion_html,
        suspicion_timeline_html,
        bank_html,
        outcome_html,
        metadata,
        prev_update,
        next_update,
    )


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


def on_episode_change(label: str, mode: str) -> tuple:
    episode = _load_episode(label)
    total = max_turn(episode)
    current = 0 if mode == MODE_STEP else total
    ui = _render_all(label, mode, current)
    return (
        {"label": label, "mode": mode, "current_turn": current, "total_turns": total},
        *ui,
    )


def on_mode_change(label: str, mode: str, state: dict | None) -> tuple:
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
        with gr.Column(elem_classes=["chakravyuh-container"]):
            gr.Markdown(f'<div class="chakravyuh-title">{TITLE}</div>')
            gr.Markdown(f'<div class="chakravyuh-subtitle">{SUBTITLE}</div>')

            with gr.Tabs():
                # =================================================
                # REPLAY TAB
                # =================================================
                with gr.Tab("🎬 Replay (5 Cherry-Picked Episodes)"):
                    with gr.Row():
                        episode_picker = gr.Radio(
                            choices=labels,
                            value=default_label,
                            label="Episode",
                        )
                    with gr.Row():
                        mode_picker = gr.Radio(
                            choices=[MODE_AUTO, MODE_STEP],
                            value=default_mode,
                            label="Playback",
                        )

                    info_panel = gr.Markdown("")

                    # Hero: agent cards + attack timeline
                    gr.Markdown(
                        '<div class="panel-heading">The 5 Agents</div>'
                    )
                    agent_cards_display = gr.HTML(value=format_agent_cards_html([]))

                    gr.Markdown(
                        '<div class="panel-heading">Attack Timeline</div>'
                    )
                    timeline_ribbon_display = gr.HTML(value="")

                    # Two-column detail
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown(
                                '<div class="panel-heading">Conversation</div>'
                            )
                            chat_display = gr.HTML(value=format_chat_html([]))
                        with gr.Column(scale=1):
                            gr.Markdown(
                                '<div class="panel-heading">🔍 Analyzer Verdict</div>'
                            )
                            suspicion_display = gr.HTML(
                                value=_render_suspicion_score(0.0, "")
                            )
                            gr.Markdown(
                                '<div class="panel-heading">Suspicion Progression</div>'
                            )
                            suspicion_timeline_display = gr.HTML(
                                value=format_suspicion_timeline([])
                            )
                            gr.Markdown(
                                '<div class="panel-heading">🏦 Bank Monitor</div>'
                            )
                            bank_display = gr.HTML(
                                value=format_bank_panel([], None)
                            )

                    outcome_display = gr.HTML(value=_render_outcome_badge("—"))

                    with gr.Row(elem_id="playback-controls"):
                        prev_btn = gr.Button("◀ Prev Turn", interactive=False)
                        next_btn = gr.Button("Next Turn ▶", interactive=False)
                        reset_btn = gr.Button("↻ Reset to Start")

                    state = gr.State(
                        value={
                            "label": default_label,
                            "mode": default_mode,
                            "current_turn": 0,
                            "total_turns": 0,
                        }
                    )

                    ui_outputs = [
                        agent_cards_display,
                        timeline_ribbon_display,
                        chat_display,
                        suspicion_display,
                        suspicion_timeline_display,
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

                    # Prime initial render
                    (
                        ag,
                        tl,
                        ch,
                        su,
                        st_,
                        bk,
                        oc,
                        mt,
                        _,
                        _,
                    ) = _render_all(default_label, default_mode, 0)
                    agent_cards_display.value = ag
                    timeline_ribbon_display.value = tl
                    chat_display.value = ch
                    suspicion_display.value = su
                    suspicion_timeline_display.value = st_
                    bank_display.value = bk
                    outcome_display.value = oc
                    info_panel.value = mt
                    state.value = {
                        "label": default_label,
                        "mode": default_mode,
                        "current_turn": max_turn(_load_episode(default_label)),
                        "total_turns": max_turn(_load_episode(default_label)),
                    }

                # =================================================
                # LIVE Q&A TAB
                # =================================================
                with gr.Tab("🔬 Live (Try Your Own Message)"):
                    gr.Markdown(
                        "Paste a suspicious message and the Analyzer scores it live. "
                        "Day 1 uses a rule-based baseline; Day 2+ swaps in the LoRA-trained Qwen2.5-7B."
                    )
                    user_input = gr.Textbox(
                        label="Message to analyze",
                        placeholder="e.g. 'Your SBI KYC expires today, share OTP to verify...'",
                        lines=4,
                    )
                    analyze_btn = gr.Button("🔎 Analyze", variant="primary")
                    live_suspicion = gr.HTML(
                        value=_render_suspicion_score(
                            0.0, "Enter a message and click Analyze."
                        )
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
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
