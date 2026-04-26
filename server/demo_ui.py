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
# Design system — two-color palette with strict white/black text rule
# ---------------------------------------------------------------------------
#
#   #FFF3E6  warm peach-cream      → page surface, cards, light states
#   #381932  deep aubergine plum   → accents, fills, selected states, dark states
#
# Text contract (no greys):
#   - On any light surface (#FFF3E6 / white) → BLACK
#   - On any plum fill (#381932)             → WHITE
#
# Severity / state encoding uses *fill density* — there are only two colors,
# so we vary how much plum is on the surface:
#   - HIGH / decisive (FROZEN / MONEY EXTRACTED / HIGH suspicion / direct-PII keyword)
#       → solid plum fill + white text
#   - MEDIUM (FLAGGED / MEDIUM suspicion / urgency keyword)
#       → white fill + plum border + plum-tinted accent + black text
#   - LOW / safe (APPROVED / LOW suspicion / regular text)
#       → cream / white fill + black text + hairline plum border
# ---------------------------------------------------------------------------

PALETTE = {
    "cream": "#FFF3E6",
    "plum":  "#381932",
}

CUSTOM_CSS = """
/* === Force light color-scheme — Gradio's default theme injects a
 *     prefers-color-scheme: dark block that flips body bg to #0E0A07 and
 *     swaps component tokens (textbox/example values) to white text on
 *     dark, which collides with our cream surfaces. We pin light mode. ===
 */
:root, html, body, gradio-app, .gradio-container { color-scheme: light !important; }

/* === Design tokens === */
:root {
  --ck-cream: #FFF3E6;                       /* page surface */
  --ck-cream-2: #FFFBF5;                     /* lifted surfaces */
  --ck-cream-3: #FFE8D2;                     /* subtle dividers / chip surface */
  --ck-plum: #381932;                        /* accent / dark fills */
  --ck-plum-hover: #2A0F25;                  /* button hover */
  --ck-plum-tint-08: rgba(56, 25, 50, 0.08); /* hover wash */
  --ck-plum-tint-12: rgba(56, 25, 50, 0.12);
  --ck-plum-tint-18: rgba(56, 25, 50, 0.18); /* hairline border */
  --ck-plum-tint-30: rgba(56, 25, 50, 0.30); /* stronger border */
  --ck-black: #000000;
  --ck-black-72: rgba(0, 0, 0, 0.72);        /* subtitle / secondary copy */
  --ck-white: #FFFFFF;

  --ck-radius-sm: 8px;
  --ck-radius-md: 12px;
  --ck-radius-lg: 16px;

  --ck-shadow-1: 0 1px 2px rgba(56, 25, 50, 0.06), 0 1px 1px rgba(56, 25, 50, 0.04);
  --ck-shadow-2: 0 6px 18px rgba(56, 25, 50, 0.10), 0 2px 4px rgba(56, 25, 50, 0.05);

  --ck-font-stack: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont,
                    system-ui, 'Helvetica Neue', sans-serif;
}

/* === Page surface === */
html, body, gradio-app, .gradio-container {
  background: var(--ck-cream) !important;
  color: var(--ck-black) !important;
  font-family: var(--ck-font-stack);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Override Gradio's default container chrome */
.gradio-container .main, .gradio-container .wrap,
.gr-block, .gr-form, .gr-panel, .gr-padded {
  background: transparent !important;
}

/* === Layout === */
.chakravyuh-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 48px;
}

/* === Hero === */
.chakravyuh-hero {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px 0 12px;
  border-bottom: 1px solid var(--ck-plum-tint-18);
  margin-bottom: 22px;
}
.chakravyuh-eyebrow {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--ck-white);
  background: var(--ck-plum);
  border: 1px solid var(--ck-plum);
  padding: 5px 12px;
  border-radius: 999px;
  align-self: flex-start;
  margin-bottom: 6px;
}
.chakravyuh-title {
  font-size: clamp(26px, 4.5vw, 38px) !important;
  font-weight: 800 !important;
  letter-spacing: -0.6px;
  line-height: 1.1;
  color: var(--ck-black) !important;
  margin: 0 !important;
}
.chakravyuh-subtitle {
  font-size: clamp(14px, 1.4vw, 16px) !important;
  line-height: 1.6;
  color: var(--ck-black-72) !important;
  max-width: 760px;
  margin: 0 !important;
}

/* === Tabs === */
.tab-nav,
div[role="tablist"] {
  border-bottom: 1px solid var(--ck-plum-tint-18) !important;
  background: transparent !important;
  margin-bottom: 22px !important;
  gap: 4px;
}
.tab-nav button,
div[role="tablist"] button,
button[role="tab"] {
  font-family: var(--ck-font-stack) !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: var(--ck-black) !important;
  opacity: 0.75 !important;
  padding: 12px 18px !important;
  border: 0 !important;
  background: transparent !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  transition: opacity .15s ease, border-color .15s ease, background .15s ease;
}
.tab-nav button:hover,
button[role="tab"]:hover {
  opacity: 1 !important;
  background: var(--ck-plum-tint-08) !important;
}
.tab-nav button.selected,
.tab-nav button[aria-selected="true"],
button[role="tab"][aria-selected="true"],
button[role="tab"].selected {
  opacity: 1 !important;
  color: var(--ck-black) !important;
  border-bottom: 3px solid var(--ck-plum) !important;
  background: transparent !important;
}

/* === Cards / panels === */
.gr-form, .gr-panel, .form, .block,
.gr-group, .gr-box {
  background: var(--ck-cream-2) !important;
  border: 1px solid var(--ck-plum-tint-18) !important;
  border-radius: var(--ck-radius-md) !important;
  box-shadow: var(--ck-shadow-1);
}

/* === Form controls — strict white bg + BLACK text === */
.gr-input, .gr-textarea, .gr-textbox textarea, .gr-textbox input,
.gr-dropdown, input[type="text"], textarea, input {
  background: var(--ck-white) !important;
  color: var(--ck-black) !important;
  -webkit-text-fill-color: var(--ck-black) !important;  /* Safari override */
  caret-color: var(--ck-plum) !important;
  border: 1px solid var(--ck-plum-tint-18) !important;
  border-radius: var(--ck-radius-sm) !important;
  font-family: var(--ck-font-stack) !important;
  font-size: 14px !important;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.gr-input:focus, .gr-textarea:focus, textarea:focus, input:focus {
  outline: none !important;
  border-color: var(--ck-plum) !important;
  box-shadow: 0 0 0 3px var(--ck-plum-tint-12) !important;
}
::placeholder, ::-webkit-input-placeholder, ::-moz-placeholder, :-ms-input-placeholder {
  color: rgba(0,0,0,0.40) !important;
  -webkit-text-fill-color: rgba(0,0,0,0.40) !important;
}

/* === Radios as pills (selected = solid plum + white text) === */
input[type="radio"], input[type="checkbox"] {
  accent-color: var(--ck-plum) !important;
}
.gr-radio, fieldset[data-testid="radio"], [data-testid="radio"] {
  gap: 8px !important;
  display: flex !important;
  flex-wrap: wrap !important;
}
.gr-radio label,
.gr-radio .wrap label,
[data-testid="radio"] label,
fieldset[data-testid="radio"] label {
  background: var(--ck-white) !important;
  border: 1px solid var(--ck-plum-tint-18) !important;
  border-radius: 999px !important;
  padding: 9px 16px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--ck-black) !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  transition: background .15s ease, border-color .15s ease, color .15s ease,
              box-shadow .15s ease;
}
.gr-radio label:hover,
[data-testid="radio"] label:hover {
  background: var(--ck-plum-tint-08) !important;
  border-color: var(--ck-plum-tint-30) !important;
}
/* SELECTED — solid plum bg, white text. Every common Gradio selector covered. */
.gr-radio label:has(input[type="radio"]:checked),
.gr-radio label.selected,
.gr-radio label[aria-checked="true"],
[data-testid="radio"] label:has(input[type="radio"]:checked),
[data-testid="radio"] label.selected,
[data-testid="radio"] label[aria-checked="true"],
fieldset[data-testid="radio"] label:has(input[type="radio"]:checked) {
  background: var(--ck-plum) !important;
  border-color: var(--ck-plum) !important;
  color: var(--ck-white) !important;
  box-shadow: var(--ck-shadow-1);
}
.gr-radio label:has(input[type="radio"]:checked) *,
[data-testid="radio"] label:has(input[type="radio"]:checked) *,
fieldset[data-testid="radio"] label:has(input[type="radio"]:checked) * {
  color: var(--ck-white) !important;   /* force every nested span/strong to white */
}

/* === Buttons === */
.gr-button, button.lg, button.sm, .primary {
  font-family: var(--ck-font-stack) !important;
  font-weight: 600 !important;
  border-radius: var(--ck-radius-sm) !important;
  padding: 10px 18px !important;
  font-size: 14px !important;
  letter-spacing: 0.1px;
  transition: background .15s ease, transform .08s ease, box-shadow .15s ease,
              border-color .15s ease;
}
.gr-button.primary, button.primary {
  background: var(--ck-plum) !important;
  color: var(--ck-white) !important;
  border: 1px solid var(--ck-plum) !important;
  box-shadow: var(--ck-shadow-1);
}
.gr-button.primary:hover, button.primary:hover {
  background: var(--ck-plum-hover) !important;
  transform: translateY(-1px);
  box-shadow: var(--ck-shadow-2);
}
.gr-button.secondary, button.secondary, .gr-button:not(.primary) {
  background: var(--ck-white) !important;
  color: var(--ck-black) !important;
  border: 1px solid var(--ck-plum-tint-30) !important;
}
.gr-button.secondary:hover, button.secondary:hover,
.gr-button:not(.primary):hover {
  background: var(--ck-plum-tint-08) !important;
  border-color: var(--ck-plum) !important;
}
.gr-button:disabled, button:disabled {
  opacity: 0.4; cursor: not-allowed; transform: none !important;
}

/* === Section heading === */
.panel-heading {
  font-size: 11px !important;
  font-weight: 800 !important;
  text-transform: uppercase;
  letter-spacing: 1.6px;
  color: var(--ck-black) !important;
  margin: 22px 0 12px !important;
  padding: 0 !important;
  display: flex;
  align-items: center;
  gap: 10px;
}
.panel-heading::before {
  content: "";
  width: 16px; height: 2px;
  background: var(--ck-plum);
  border-radius: 999px;
}

/* === Metadata chip strip === */
.metadata-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 14px;
  background: var(--ck-cream-2);
  border: 1px solid var(--ck-plum-tint-18);
  border-radius: var(--ck-radius-md);
  margin: 14px 0 10px;
  box-shadow: var(--ck-shadow-1);
}
.meta-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 12px;
  background: var(--ck-white);
  border: 1px solid var(--ck-plum-tint-18);
  border-radius: 999px;
  font-size: 12px;
  line-height: 1;
  color: var(--ck-black);
}
.meta-chip-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: var(--ck-black-72);
}
.meta-chip-value {
  font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-weight: 700;
  color: var(--ck-black);
  font-variant-numeric: tabular-nums;
}

/* === Form / block labels === */
.gr-block-label,
.block-label,
span[data-testid="block-label"],
.gr-form > label,
.gr-form > div > label,
fieldset > legend,
.gr-input-label,
.gr-radio > label:first-child,
.gr-radio > .wrap > label:first-child {
  color: var(--ck-black) !important;
  opacity: 1 !important;
  font-weight: 700 !important;
  font-size: 12px !important;
  text-transform: uppercase !important;
  letter-spacing: 1.2px !important;
  margin-bottom: 8px !important;
}

/* === Suspicion score panel === */
#suspicion-panel {
  border-radius: var(--ck-radius-md);
  padding: 22px 20px;
  text-align: center;
  transition: background .35s ease, border-color .35s ease;
  box-shadow: var(--ck-shadow-1);
}
#suspicion-score {
  font-size: clamp(40px, 6vw, 56px);
  font-weight: 800;
  margin: 6px 0 4px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  transition: color .35s ease;
}
#suspicion-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
}
#suspicion-explanation {
  font-size: 13px;
  line-height: 1.5;
  margin-top: 10px;
}

/* === Suspicion bar === */
.suspicion-bar-fill {
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1),
              background-color 0.35s ease;
  border-radius: 999px;
}

/* === Outcome badge === */
.outcome-badge {
  font-size: 16px;
  font-weight: 700;
  padding: 16px 20px;
  border-radius: var(--ck-radius-md);
  text-align: center;
  margin: 18px 0 6px;
  letter-spacing: 0.3px;
  transition: background .35s ease, color .35s ease;
  box-shadow: var(--ck-shadow-1);
}

/* === Attack timeline === */
.attack-timeline {
  border: 1px solid var(--ck-plum-tint-18);
  border-radius: var(--ck-radius-md);
  background: var(--ck-cream-2);
}
.timeline-step {
  transition: opacity 0.3s ease, transform 0.2s ease;
}

/* === Agent cards === */
.agent-grid { transition: opacity 0.3s ease; }
.agent-card {
  background: var(--ck-white) !important;
  border: 1px solid var(--ck-plum-tint-18) !important;
  border-radius: var(--ck-radius-md) !important;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
.agent-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--ck-shadow-2);
  border-color: var(--ck-plum) !important;
}

/* === Pulse === */
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.55; transform: scale(0.92); }
}
.pulse { animation: pulse-dot 1.6s ease-in-out infinite; }

/* === 5-agent hero cascade — entrance animation === */
@keyframes ck-agent-cascade {
  0%, 18%   { opacity: 0; transform: translateY(8px); }
  22%, 100% { opacity: 1; transform: translateY(0); }
}
@keyframes ck-rubric-grow {
  0%   { width: 0%; }
  100% { width: var(--ck-rubric-w, 60%); }
}
.ck-hero-strip {
  display: flex; gap: 10px; flex-wrap: wrap;
  margin: 4px 0 18px;
  padding: 14px 16px;
  background: var(--ck-cream-2);
  border: 1px solid var(--ck-plum-tint-18);
  border-radius: var(--ck-radius-md);
}
.ck-hero-agent {
  flex: 1 1 130px; min-width: 130px;
  padding: 10px 12px; text-align: center;
  background: var(--ck-cream);
  border: 1px solid var(--ck-plum-tint-18);
  border-radius: var(--ck-radius-sm);
  font-size: 12px; font-weight: 700; color: var(--ck-black);
  animation: ck-agent-cascade 5s ease-in-out infinite;
}
.ck-hero-agent:nth-child(1) { animation-delay: 0s; }
.ck-hero-agent:nth-child(2) { animation-delay: 1s; }
.ck-hero-agent:nth-child(3) { animation-delay: 2s; }
.ck-hero-agent:nth-child(4) { animation-delay: 3s; }
.ck-hero-agent:nth-child(5) { animation-delay: 4s; }
.ck-hero-agent .ck-hero-emoji {
  display: block; font-size: 24px; margin-bottom: 4px;
}
.ck-hero-agent .ck-hero-letter {
  display: inline-block; padding: 1px 6px;
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  background: var(--ck-plum); color: var(--ck-white);
  border-radius: 4px; margin-left: 4px;
}
@media (prefers-reduced-motion: reduce) {
  .ck-hero-agent { animation-duration: 0.01s !important; }
}

/* === Hot-key overlay modal === */
.ck-hotkey-modal {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.45); z-index: 9000;
  align-items: center; justify-content: center;
  font-family: var(--ck-font-stack);
}
.ck-hotkey-modal.open { display: flex; }
.ck-hotkey-modal-card {
  max-width: 460px; width: calc(100% - 32px);
  padding: 24px 28px; border-radius: var(--ck-radius-md);
  background: var(--ck-cream); color: var(--ck-black);
  border: 1px solid var(--ck-plum);
  box-shadow: var(--ck-shadow-2);
}
.ck-hotkey-modal h3 {
  margin: 0 0 12px; font-size: 16px; color: var(--ck-plum);
}
.ck-hotkey-row {
  display: flex; justify-content: space-between;
  align-items: center; padding: 6px 0;
  border-bottom: 1px solid var(--ck-plum-tint-12);
  font-size: 13px;
}
.ck-hotkey-row:last-child { border-bottom: 0; }
.ck-hotkey-key {
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 8px; border-radius: 4px;
  background: var(--ck-plum); color: var(--ck-white);
  font-size: 11px; font-weight: 700;
}
.ck-hotkey-hint {
  margin-top: 10px; font-size: 11px;
  color: var(--ck-black-72); text-align: center;
}

/* === Playback controls === */
#playback-controls {
  gap: 10px !important;
  margin: 16px 0 8px !important;
  flex-wrap: wrap;
}
#playback-controls button { min-width: 130px; }

/* === Examples === */
.examples-table, .gr-examples {
  background: transparent !important;
}
.examples-table button, .gr-examples button {
  background: var(--ck-white) !important;
  border: 1px solid var(--ck-plum-tint-18) !important;
  color: var(--ck-black) !important;
  font-family: var(--ck-font-stack) !important;
  border-radius: var(--ck-radius-sm) !important;
  text-align: left !important;
  padding: 12px 14px !important;
  transition: background .15s, border-color .15s;
}
.examples-table button:hover, .gr-examples button:hover {
  background: var(--ck-plum-tint-08) !important;
  border-color: var(--ck-plum) !important;
}

/* === Footer === */
.chakravyuh-footer {
  margin-top: 32px !important;
  padding-top: 18px !important;
  border-top: 1px solid var(--ck-plum-tint-18) !important;
  font-size: 12px !important;
  color: var(--ck-black-72) !important;
  line-height: 1.6;
}
.chakravyuh-footer a {
  color: var(--ck-plum) !important;
  text-decoration: underline;
  text-decoration-color: var(--ck-plum);
  text-decoration-thickness: 1.5px;
  text-underline-offset: 3px;
  font-weight: 600;
}

/* === Markdown copy === */
.gr-markdown, .markdown,
.prose, .gradio-container .prose,
.gradio-container p, .gradio-container li {
  color: var(--ck-black) !important;
  font-family: var(--ck-font-stack) !important;
}

/* Inline `code` — strong override against Gradio's dark default */
code, kbd, samp,
.gradio-container code,
.gr-markdown code,
.markdown code,
.prose code,
p code, span code, li code, td code, th code,
.gr-html code, .gr-html-content code {
  background: var(--ck-cream-3) !important;
  color: var(--ck-black) !important;
  border: 1px solid var(--ck-plum-tint-18) !important;
  border-radius: 4px !important;
  padding: 1px 7px !important;
  font-size: 0.92em !important;
  font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace !important;
  font-weight: 600 !important;
  white-space: nowrap;
}
code::before, code::after { content: none !important; }

/* === Scrollbars === */
*::-webkit-scrollbar { width: 8px; height: 8px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb {
  background: var(--ck-plum-tint-18);
  border-radius: 999px;
}
*::-webkit-scrollbar-thumb:hover { background: var(--ck-plum-tint-30); }

/* === Responsive: tablet === */
@media (max-width: 900px) {
  .chakravyuh-container { padding: 16px 14px 36px; }
  .chakravyuh-hero { padding: 18px 0 8px; margin-bottom: 16px; }
  .agent-grid { grid-template-columns: repeat(2, 1fr) !important; }
  .gr-row { flex-direction: column !important; gap: 0 !important; }
  .gr-row > .gr-column { width: 100% !important; max-width: 100% !important; }
}

/* === Responsive: mobile === */
@media (max-width: 600px) {
  .chakravyuh-container { padding: 12px 10px 28px; }
  .agent-grid { grid-template-columns: 1fr !important; }
  #suspicion-score { font-size: 40px; }
  .outcome-badge { font-size: 14px; padding: 12px; }
  .gr-button, button { width: 100% !important; min-width: 0 !important; }
  #playback-controls { flex-direction: column !important; }
  .tab-nav button { padding: 9px 12px !important; font-size: 13px !important; }
}

/* === Reduced motion === */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    transition-duration: 0.001ms !important;
  }
}

/* === Focus visible (a11y) === */
:focus-visible {
  outline: 2px solid var(--ck-plum) !important;
  outline-offset: 2px;
}

/* === Dark-mode safety net ===
 *
 * If the user's OS is in dark mode, Gradio applies dark-theme tokens to
 * many components (textbox, examples, dropdown, dataframe, …). We override
 * those tokens to keep the cream / plum contract consistent and the strict
 * white-on-plum / black-on-light text rule intact.
 *
 * Selectors chosen to win against Gradio's `!important` declarations.
 */
@media (prefers-color-scheme: dark) {
  html, body, gradio-app, .gradio-container,
  .gradio-container .main, .gradio-container .wrap {
    background: var(--ck-cream) !important;
    color: var(--ck-black) !important;
  }

  /* Cards, blocks, forms */
  .gradio-container .gr-block, .gradio-container .gr-form,
  .gradio-container .gr-panel, .gradio-container .gr-padded,
  .gradio-container .gr-box, .gradio-container .gr-group,
  .gradio-container .block, .gradio-container .form,
  .gradio-container fieldset {
    background: var(--ck-cream-2) !important;
    color: var(--ck-black) !important;
    border-color: var(--ck-plum-tint-18) !important;
  }

  /* Inputs / textareas — must always be white bg with BLACK value text */
  .gradio-container .gr-input,
  .gradio-container .gr-textarea,
  .gradio-container .gr-textbox,
  .gradio-container .gr-textbox textarea,
  .gradio-container .gr-textbox input,
  .gradio-container .gr-dropdown,
  .gradio-container input[type="text"],
  .gradio-container textarea,
  .gradio-container input {
    background: var(--ck-white) !important;
    color: var(--ck-black) !important;
    border-color: var(--ck-plum-tint-18) !important;
    -webkit-text-fill-color: var(--ck-black) !important;
  }
  .gradio-container ::placeholder {
    color: rgba(0, 0, 0, 0.40) !important;
    -webkit-text-fill-color: rgba(0, 0, 0, 0.40) !important;
  }

  /* Buttons — primary stays plum+white; secondary stays white+black */
  .gradio-container .gr-button.primary,
  .gradio-container button.primary {
    background: var(--ck-plum) !important;
    color: var(--ck-white) !important;
    border-color: var(--ck-plum) !important;
  }
  .gradio-container .gr-button:not(.primary),
  .gradio-container button:not(.primary):not([role="tab"]) {
    background: var(--ck-white) !important;
    color: var(--ck-black) !important;
    border-color: var(--ck-plum-tint-30) !important;
  }

  /* Examples table — Gradio defaults to dark text on dark in dark mode */
  .gradio-container .examples-table,
  .gradio-container .gr-examples,
  .gradio-container .examples-table table,
  .gradio-container .gr-examples table {
    background: transparent !important;
    color: var(--ck-black) !important;
  }
  .gradio-container .examples-table button,
  .gradio-container .gr-examples button,
  .gradio-container .examples-table td,
  .gradio-container .gr-examples td {
    background: var(--ck-white) !important;
    color: var(--ck-black) !important;
    border-color: var(--ck-plum-tint-18) !important;
  }

  /* Tabs */
  .gradio-container .tab-nav button,
  .gradio-container button[role="tab"] {
    background: transparent !important;
    color: var(--ck-black) !important;
  }
  .gradio-container button[role="tab"][aria-selected="true"],
  .gradio-container .tab-nav button.selected {
    color: var(--ck-black) !important;
    border-bottom-color: var(--ck-plum) !important;
  }

  /* Markdown / prose */
  .gradio-container .gr-markdown,
  .gradio-container .markdown,
  .gradio-container .prose,
  .gradio-container p,
  .gradio-container li,
  .gradio-container span:not(.meta-chip-label):not(.meta-chip-value) {
    color: var(--ck-black) !important;
  }

  /* Inline `code` again (Gradio's dark-mode variant) */
  .gradio-container code,
  .gradio-container .gr-markdown code,
  .gradio-container .markdown code,
  .gradio-container .prose code {
    background: var(--ck-cream-3) !important;
    color: var(--ck-black) !important;
    border: 1px solid var(--ck-plum-tint-18) !important;
  }

  /* Form / block labels */
  .gradio-container .gr-block-label,
  .gradio-container .block-label,
  .gradio-container span[data-testid="block-label"],
  .gradio-container fieldset > legend {
    color: var(--ck-black) !important;
  }

  /* Radio pills — re-assert selected = plum bg + white text */
  .gradio-container .gr-radio label,
  .gradio-container [data-testid="radio"] label {
    background: var(--ck-white) !important;
    color: var(--ck-black) !important;
    border-color: var(--ck-plum-tint-18) !important;
  }
  .gradio-container .gr-radio label:has(input[type="radio"]:checked),
  .gradio-container [data-testid="radio"] label:has(input[type="radio"]:checked),
  .gradio-container .gr-radio label[aria-checked="true"],
  .gradio-container [data-testid="radio"] label[aria-checked="true"] {
    background: var(--ck-plum) !important;
    color: var(--ck-white) !important;
    border-color: var(--ck-plum) !important;
  }
  .gradio-container .gr-radio label:has(input[type="radio"]:checked) *,
  .gradio-container [data-testid="radio"] label:has(input[type="radio"]:checked) * {
    color: var(--ck-white) !important;
    -webkit-text-fill-color: var(--ck-white) !important;
  }
}

/* ---------- How-it-works accordion ---------- */
.ck-howto > .label-wrap,
.ck-howto > button,
.ck-howto label {
  background: var(--ck-cream-2) !important;
  color: var(--ck-black) !important;
  font-weight: 700 !important;
  border: 1px solid var(--ck-plum-30) !important;
  border-radius: 12px !important;
}
.ck-howto-body {
  font-size: 14px;
  line-height: 1.65;
  color: var(--ck-black);
  padding: 14px 18px 6px;
}
.ck-howto-body p {
  margin: 0 0 8px;
}
.ck-howto-body p strong {
  color: var(--ck-plum);
}
.ck-howto-list {
  margin: 0 0 14px 22px;
  padding: 0;
}
.ck-howto-list li {
  margin: 4px 0;
}
.ck-howto-list li strong {
  color: var(--ck-plum);
}
.ck-howto-body code {
  background: var(--ck-cream-3) !important;
  color: var(--ck-black) !important;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace;
}

/* ---------- Decisive-moment micro-animations ---------- */
@keyframes ck-pulse-plum {
  0%   { transform: scale(1);     box-shadow: 0 0 0 0 rgba(56, 25, 50, 0.0); }
  35%  { transform: scale(1.025); box-shadow: 0 0 0 12px rgba(56, 25, 50, 0.18); }
  100% { transform: scale(1);     box-shadow: 0 0 0 0 rgba(56, 25, 50, 0.0); }
}
@keyframes ck-shake {
  0%, 100% { transform: translateX(0); }
  25%      { transform: translateX(-3px); }
  50%      { transform: translateX(3px); }
  75%      { transform: translateX(-2px); }
}
@keyframes ck-slide-in-success {
  0%   { opacity: 0; transform: translateY(-6px); }
  100% { opacity: 1; transform: translateY(0); }
}
.ck-bank-freeze,
.ck-bank-flag {
  animation: ck-pulse-plum 1.2s ease-out 1;
}
.agent-card-analyzer.agent-card-tone-critical,
.agent-card-bank.agent-card-tone-critical {
  animation: ck-pulse-plum 1.2s ease-out 1;
}
.agent-card-analyzer.agent-card-tone-critical .agent-emoji {
  animation: ck-shake 0.6s ease-in-out 1;
  display: inline-block;
}
.agent-card-victim.agent-card-tone-safe {
  animation: ck-slide-in-success 0.45s ease-out 1;
}
@media (prefers-reduced-motion: reduce) {
  .ck-bank-freeze,
  .ck-bank-flag,
  .agent-card-analyzer.agent-card-tone-critical,
  .agent-card-bank.agent-card-tone-critical,
  .agent-card-analyzer.agent-card-tone-critical .agent-emoji,
  .agent-card-victim.agent-card-tone-safe {
    animation: none !important;
  }
}

/* =============== Live red-team tab — reward-profile asymmetry =============== */
.redteam-empty {
  padding: 18px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px dashed rgba(0, 0, 0, 0.18);
  border-radius: 10px;
  color: #555;
  font-size: 14px;
  line-height: 1.6;
}
.redteam-card {
  padding: 16px;
  border-radius: 12px;
  border-left: 4px solid;
  background: rgba(255, 255, 255, 0.55);
  margin-bottom: 12px;
}
.redteam-v1 {
  border-left-color: #d32f2f;
  background: linear-gradient(180deg, rgba(211, 47, 47, 0.06), rgba(255, 255, 255, 0.6));
}
.redteam-v2 {
  border-left-color: #2e7d32;
  background: linear-gradient(180deg, rgba(46, 125, 50, 0.06), rgba(255, 255, 255, 0.6));
}
.redteam-card-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 10px;
}
.redteam-card-title {
  font-size: 15px;
  letter-spacing: 0.02em;
  color: #000;
}
.redteam-card-subtitle {
  font-size: 12px;
  opacity: 0.7;
  color: #000;
}
.redteam-card-score-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 8px;
}
.redteam-score {
  font-size: 28px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #000;
}
.redteam-flag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.redteam-flag.flagged {
  background: rgba(211, 47, 47, 0.15);
  color: #b71c1c;
  border: 1px solid rgba(211, 47, 47, 0.5);
}
.redteam-flag.clean {
  background: rgba(46, 125, 50, 0.12);
  color: #1b5e20;
  border: 1px solid rgba(46, 125, 50, 0.45);
}
.redteam-signals {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 6px 0 8px;
}
.redteam-sig {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 6px;
  font-size: 11px;
  color: #000;
}
.redteam-sig-empty { opacity: 0.5; }
.redteam-explanation {
  font-size: 13px;
  color: #333;
  margin: 6px 0 12px;
  line-height: 1.5;
}
.redteam-breakdown {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.redteam-breakdown th,
.redteam-breakdown td {
  padding: 4px 8px;
  text-align: right;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}
.redteam-breakdown thead th {
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #555;
  border-bottom: 1px solid rgba(0, 0, 0, 0.18);
}
.redteam-leaf-name {
  text-align: left !important;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 11px;
}
.redteam-leaf-val,
.redteam-leaf-weight,
.redteam-leaf-contrib {
  font-variant-numeric: tabular-nums;
}
.redteam-leaf-na { opacity: 0.3; }
.redteam-total-label {
  text-align: right !important;
  font-size: 11px;
  text-transform: uppercase;
  color: #000;
}
.redteam-total-val {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #000;
}
.redteam-asym {
  margin-top: 14px;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
}
.redteam-asym-warning {
  background: rgba(211, 47, 47, 0.10);
  border: 1px solid rgba(211, 47, 47, 0.35);
  color: #b71c1c;
}
.redteam-asym-mild {
  background: rgba(255, 152, 0, 0.10);
  border: 1px solid rgba(255, 152, 0, 0.35);
  color: #6d4c41;
}
.redteam-asym-agree {
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.12);
  color: #444;
}
@media (max-width: 768px) {
  #redteam-row > * { width: 100% !important; }
  .redteam-breakdown { font-size: 11px; }
  .ck-hero-strip { gap: 6px !important; flex-wrap: wrap !important; }
  .agent-card { font-size: 13px !important; padding: 8px !important; }
  .panel-heading { font-size: 14px !important; }
}
.live-empty {
  padding: 14px 16px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 10px;
  border: 1px dashed rgba(0, 0, 0, 0.18);
  font-size: 13px;
  line-height: 1.5;
  color: #444;
}
.live-error {
  padding: 14px 16px;
  background: rgba(211, 47, 47, 0.08);
  border-radius: 10px;
  border: 1px solid rgba(211, 47, 47, 0.35);
  font-size: 13px;
  color: #b71c1c;
}
.live-followup {
  margin-top: 10px;
  padding: 10px 12px;
  background: rgba(46, 125, 50, 0.08);
  border-radius: 8px;
  font-size: 13px;
  color: #1b5e20;
}
.ck-redteam-pointer {
  margin: 0 0 14px;
  padding: 10px 14px;
  border-left: 3px solid #d32f2f;
  background: rgba(211, 47, 47, 0.05);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.55;
  color: #000;
}
.ck-redteam-pointer em {
  font-style: normal;
  font-weight: 600;
  color: #b71c1c;
}
"""

MODE_AUTO = "Auto-play (full episode)"
MODE_STEP = "Step-through (turn by turn)"


def _suspicion_style(score: float) -> tuple[str, str, str, str]:
    """Return (background, text_color, border, bar_color) for the suspicion panel.

    Two-color palette + strict white/black text rule:

      HIGH  (>= 0.70)  →  solid plum bg + WHITE text + white bar (high-contrast)
      MED   (>= 0.40)  →  white bg + BLACK text + plum border + plum bar
      LOW   (<  0.40)  →  cream-2 bg + BLACK text + plum hairline border + plum bar
    """
    if score >= 0.70:
        return ("#381932", "#FFFFFF", "#381932", "#FFFFFF")
    if score >= 0.40:
        return ("#FFFFFF", "#000000", "#381932", "#381932")
    return ("#FFFBF5", "#000000", "rgba(56,25,50,0.30)", "#381932")


def _render_suspicion_score(score: float, explanation: str) -> str:
    bg, fg, border, bar_color = _suspicion_style(score)
    pct = int(round(score * 100))
    # Bar track tinted relative to the panel: dark plum for light panels,
    # semi-transparent white for the dark high-suspicion panel.
    bar_track = "rgba(255,255,255,0.30)" if bg == "#381932" else "rgba(56,25,50,0.18)"
    return (
        f'<div id="suspicion-panel" style="background:{bg};color:{fg};'
        f'border:1px solid {border};">'
        f'<p id="suspicion-label" style="color:{fg};">Suspicion Score</p>'
        f'<p id="suspicion-score" style="color:{fg};">{score:.2f}</p>'
        f'<div style="background:{bar_track};height:6px;'
        f'border-radius:999px;overflow:hidden;margin:14px 0 10px;">'
        f'<div class="suspicion-bar-fill" '
        f'style="background:{bar_color};width:{pct}%;height:100%;"></div>'
        f"</div>"
        f'<p id="suspicion-explanation" style="color:{fg};">'
        f'{explanation or "No signals detected."}</p>'
        "</div>"
    )


def _render_outcome_badge(text: str) -> str:
    """Outcome badge — same plum/cream + black/white contract."""
    upper = text.upper()
    if "MONEY EXTRACTED" in upper:
        # Decisive negative → solid plum + white
        bg, fg, border = "#381932", "#FFFFFF", "#381932"
    elif "FROZE" in upper or "REFUSED" in upper or "VERIFIED" in upper:
        # Decisive positive resolution → also plum (matches "decisive action")
        bg, fg, border = "#381932", "#FFFFFF", "#381932"
    elif "FLAGGED" in upper:
        # Mid-state → white + plum border + black
        bg, fg, border = "#FFFFFF", "#000000", "#381932"
    else:
        # Neutral / in-progress → cream-2 + plum hairline
        bg, fg, border = "#FFFBF5", "#000000", "rgba(56,25,50,0.18)"
    return (
        f'<div class="outcome-badge" style="background:{bg};color:{fg};'
        f'border:1px solid {border};">{text}</div>'
    )


def _render_metadata(ep: ReplayedEpisode, current_turn: int, total_turns: int) -> str:
    """Episode metadata — rendered as a horizontal strip of readable chips."""
    items = [
        ("Seed", str(ep.seed)),
        ("Profile", ep.profile.value),
        ("Category", ep.outcome.scam_category.value),
        ("Turn", f"{current_turn} / {total_turns}"),
    ]
    # Outcome chip at terminal turn (judges see immediately how the episode resolved)
    if current_turn >= total_turns and total_turns > 0:
        oc = ep.outcome
        if oc.money_extracted:
            outcome_label = "💸 Scammed"
        elif oc.bank_froze:
            outcome_label = "🛡️ Bank froze"
        elif oc.victim_sought_verification:
            outcome_label = "📞 Verified"
        elif oc.victim_refused:
            outcome_label = "🙅 Refused"
        elif oc.analyzer_flagged:
            outcome_label = "🚨 Flagged"
        else:
            outcome_label = "—"
        items.append(("Outcome", outcome_label))
    chips = "".join(
        '<div class="meta-chip">'
        f'<span class="meta-chip-label">{label}</span>'
        f'<span class="meta-chip-value">{value}</span>'
        "</div>"
        for label, value in items
    )
    return (
        '<div class="metadata-strip" role="group" aria-label="Episode metadata">'
        f"{chips}</div>"
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


_LIVE_EMPTY_HINT = (
    '<div class="live-empty">'
    "Type any message above and click <strong>Analyze</strong>. Or try one of these:"
    '<ul style="margin:8px 0 0 18px;padding:0;">'
    '<li>"Share your OTP urgently — bank security check"</li>'
    '<li>"Hi, just confirming our meeting tomorrow at 11"</li>'
    '<li>"You\'ve won ₹5 lakh — click bit.ly/claim"</li>'
    "</ul></div>"
)


def on_live_analyze(user_text: str) -> str:
    if not user_text.strip():
        return _LIVE_EMPTY_HINT
    try:
        analyzer = ScriptedAnalyzer()
        obs = Observation(
            agent_role="analyzer",
            turn=1,
            chat_history=[ChatMessage(sender="scammer", turn=1, text=user_text)],
        )
        action = analyzer.act(obs)
    except Exception as exc:  # noqa: BLE001 — UI surface; never crash the page
        return (
            '<div class="live-error" role="alert">'
            "Something glitched while scoring this. Try a different message, or "
            "report at <a href=\"https://github.com/UjjwalPardeshi/Chakravyuh/issues\">"
            "the repo issues</a>. (Detail logged server-side.)"
            f"<details style=\"margin-top:6px;font-size:12px;opacity:.7;\">"
            f"<summary>technical detail</summary>{type(exc).__name__}: {exc}"
            "</details></div>"
        )
    if isinstance(action, AnalyzerScore):
        score = float(action.score)
        if score < 0.30 and not action.signals:
            # Likely benign + nothing suspicious; nudge user toward a scam example.
            return (
                _render_suspicion_score(score, action.explanation or "Looks benign.")
                + '<div class="live-followup">'
                "✅ This message looks benign. Try one of the scam examples below "
                "to see the model react."
                "</div>"
            )
        return _render_suspicion_score(score, action.explanation)
    return _render_suspicion_score(0.0, "Analyzer returned no score.")


def _load_leaderboard_rows() -> list[list[str]]:
    """Read logs/leaderboard.jsonl and return rows for gr.Dataframe.

    Columns: Rank · Method · F1 · Detection · FPR · n · Notes.
    """
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "logs" / "leaderboard.jsonl"
    rows: list[dict] = []
    if path.exists():
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    rows.sort(key=lambda e: -float(e.get("f1", 0.0)))

    table: list[list[str]] = []
    for i, e in enumerate(rows, start=1):
        det = float(e.get("detection", 0.0))
        fpr = float(e.get("fpr", 0.0))
        f1 = float(e.get("f1", 0.0))
        n = e.get("n_evaluated", "—")
        notes = (e.get("notes") or "").strip()
        if len(notes) > 110:
            notes = notes[:107] + "…"
        table.append([
            str(i),
            str(e.get("method", "(unknown)")),
            f"{f1:.3f}",
            f"{det * 100:.1f}%",
            f"{fpr * 100:.1f}%",
            str(n),
            notes,
        ])
    if not table:
        table = [["—", "(no submissions yet)", "—", "—", "—", "—", ""]]
    return table


def on_adversarial_attempt(user_text: str) -> tuple[float, str, dict, str, str]:
    """Adversarial 'You vs Analyzer' helper.

    Returns:
        (score, flagged_label, signals_dict, explanation, banner_html)
    """
    if not user_text.strip():
        empty_banner = (
            '<div style="padding:12px 16px;background:#FFFBF5;'
            'border:1px dashed rgba(56,25,50,0.30);border-radius:10px;'
            'color:#000000;font-size:13px;text-align:center;">'
            "Type a scam attempt above and press <strong>Send to Analyzer</strong>."
            "</div>"
        )
        return 0.0, "", {}, "", empty_banner

    try:
        analyzer = ScriptedAnalyzer()
        obs = Observation(
            agent_role="analyzer",
            turn=1,
            chat_history=[ChatMessage(sender="scammer", turn=1, text=user_text)],
        )
        action = analyzer.act(obs)
    except Exception as exc:  # noqa: BLE001
        err_html = (
            '<div style="padding:12px 16px;background:#FFE8D2;border:1px solid #381932;'
            'border-radius:10px;color:#000000;font-size:13px;">'
            f"Analyzer error: {exc!s}"
            "</div>"
        )
        return 0.0, "Error", {}, str(exc), err_html

    if not isinstance(action, AnalyzerScore):
        return 0.0, "Analyzer error", {}, "", (
            '<div style="padding:12px 16px;background:#FFE8D2;'
            'border:1px solid #381932;border-radius:10px;color:#000000;'
            'font-size:13px;">Analyzer returned no score.</div>'
        )

    score = float(action.score)
    threshold = 0.5
    flagged = score >= threshold

    signals_dict = {sig.name if hasattr(sig, "name") else str(sig): "fired"
                    for sig in (action.signals or [])}

    explanation = action.explanation or "(no explanation produced)"
    flagged_label = (
        "✅ YES — Analyzer flagged your attempt"
        if flagged else "❌ NO — Analyzer let it through"
    )

    if flagged:
        banner_html = (
            '<div style="padding:14px 18px;background:#381932;color:#FFFFFF;'
            'border-radius:10px;font-weight:700;font-size:15px;'
            'letter-spacing:0.3px;text-align:center;">'
            f'❌ CAUGHT — Analyzer scored {score:.2f} (≥ {threshold:.2f}). '
            "Try a subtler approach to bypass."
            "</div>"
        )
    else:
        banner_html = (
            '<div style="padding:14px 18px;background:#FFE8D2;color:#000000;'
            'border:2px solid #381932;border-radius:10px;font-weight:700;'
            'font-size:15px;letter-spacing:0.3px;text-align:center;">'
            f'🏴 BYPASSED — Analyzer scored {score:.2f} (&lt; {threshold:.2f}). '
            "Your attempt slipped past the rule-based detector."
            "</div>"
        )

    return score, flagged_label, signals_dict, explanation, banner_html


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


def build_app() -> gr.Blocks:
    labels = [e.label for e in CURATED_EPISODES]
    default_label = labels[0]
    default_mode = MODE_STEP

    with gr.Blocks(title=TITLE) as app:
        with gr.Column(elem_classes=["chakravyuh-container"]):
            gr.HTML(
                '<header class="chakravyuh-hero" role="banner">'
                '<span class="chakravyuh-eyebrow">Chakravyuh · Multi-Agent Fraud Arena</span>'
                f'<h1 class="chakravyuh-title">{TITLE}</h1>'
                f'<p class="chakravyuh-subtitle">{SUBTITLE}</p>'
                "</header>"
                # 5-agent CSS hero strip — pure animation, no interaction.
                '<div class="ck-hero-strip" role="img" '
                'aria-label="Five Chakravyuh agents: Scammer, Victim, Analyzer, Bank Monitor, Regulator">'
                '<div class="ck-hero-agent">'
                '<span class="ck-hero-emoji" aria-hidden="true">🪤</span>'
                'Scammer<span class="ck-hero-letter">S</span></div>'
                '<div class="ck-hero-agent">'
                '<span class="ck-hero-emoji" aria-hidden="true">📱</span>'
                'Victim<span class="ck-hero-letter">V</span></div>'
                '<div class="ck-hero-agent">'
                '<span class="ck-hero-emoji" aria-hidden="true">🛡️</span>'
                'Analyzer<span class="ck-hero-letter">A</span></div>'
                '<div class="ck-hero-agent">'
                '<span class="ck-hero-emoji" aria-hidden="true">🏦</span>'
                'Bank Monitor<span class="ck-hero-letter">B</span></div>'
                '<div class="ck-hero-agent">'
                '<span class="ck-hero-emoji" aria-hidden="true">⚖️</span>'
                'Regulator<span class="ck-hero-letter">R</span></div>'
                '</div>'
                # Hot-key overlay modal (CSS-only; toggled via inline script).
                '<div class="ck-hotkey-modal" id="ck-hotkey-modal" role="dialog" '
                'aria-label="Keyboard shortcuts" aria-hidden="true">'
                '<div class="ck-hotkey-modal-card">'
                '<h3>Keyboard shortcuts</h3>'
                '<div class="ck-hotkey-row">'
                '<span>Toggle this overlay</span><span class="ck-hotkey-key">?</span></div>'
                '<div class="ck-hotkey-row">'
                '<span>Close overlay</span><span class="ck-hotkey-key">Esc</span></div>'
                '<div class="ck-hotkey-row">'
                '<span>Scroll to next tab heading</span><span class="ck-hotkey-key">N</span></div>'
                '<div class="ck-hotkey-row">'
                '<span>Open the GitHub repo</span><span class="ck-hotkey-key">G</span></div>'
                '<p class="ck-hotkey-hint">'
                'Shortcuts ignore typing inside text inputs. Press <strong>?</strong> any time.'
                '</p>'
                '</div></div>'
                "<script>"
                "(function(){"
                "  function inField(t){return t&&t.matches&&t.matches('input,textarea,[contenteditable]');}"
                "  document.addEventListener('keydown',function(e){"
                "    if(inField(e.target))return;"
                "    var m=document.getElementById('ck-hotkey-modal');"
                "    if(e.key==='?'){m.classList.toggle('open');m.setAttribute('aria-hidden',m.classList.contains('open')?'false':'true');e.preventDefault();}"
                "    if(e.key==='Escape'){m.classList.remove('open');m.setAttribute('aria-hidden','true');}"
                "    if(e.key==='g'||e.key==='G'){window.open('https://github.com/UjjwalPardeshi/Chakravyuh','_blank');}"
                "  });"
                "})();"
                "</script>"
            )

            gr.Markdown(
                "> **Judges:** read [`docs/judge_quickstart.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/judge_quickstart.md) "
                "for the 3-minute guided tour · headline numbers in [`README.md`](https://github.com/UjjwalPardeshi/Chakravyuh#readme) · "
                "ask anything → [Q&A rehearsal](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/Q_AND_A_REHEARSAL.md)."
            )

            gr.HTML(
                '<details class="ck-howto" open>'
                '<summary style="cursor:pointer;font-weight:700;font-size:1.05rem;padding:0.5rem 0;">'
                '🎬 Story Mode — 30-second tour (click to collapse)'
                '</summary>'
                '<div class="ck-howto-body" style="padding:0.75rem 0 0.25rem 0;">'
                '<ol class="ck-howto-list" style="margin:0;padding-left:1.25rem;">'
                '<li><strong>Tab 1 — Replay</strong>: pick a curated episode and watch the 5-agent fraud arena play out turn-by-turn. Suspicion bars climb; the bank either freezes or releases.</li>'
                '<li><strong>Tab 3 — You vs Analyzer</strong>: paste any UPI message and get a live verdict (or click one of the 3 quick-test buttons: OTP-Hindi, matrimonial-crypto, deepfake-CEO).</li>'
                '<li><strong>Tab 4 — Adversary Lab</strong>: browse all 64 outputs from our trained Scammer LoRA. Side-by-side, scripted defender misses 60.9 pp more than the v2 LoRA — that is co-evolution, not a benchmark number.</li>'
                '<li><strong>Tab 5 — v1 vs v2</strong>: see the reward-hacking fix that took FPR from 36% → 6.7%.</li>'
                '<li><strong>Tab 6 — Red-team it yourself</strong>: try to bypass v2 (good luck — best-of-8 caps at 32.8%).</li>'
                '</ol>'
                '<p style="margin-top:0.5rem;font-size:0.92rem;color:rgba(0,0,0,0.72);">'
                'Headline: <strong>v2 LoRA F1 = 0.99</strong> on n=144 scams (Wilson 95% CI 95.1–99.9), '
                '<strong>FPR = 6.7%</strong> on n=30 benigns (CI 1.9–21.3), '
                '<strong>ECE = 0.039</strong> well-calibrated. All numbers reproducible in &lt;2 min on CPU.'
                '</p>'
                '</div>'
                '</details>'
            )

            with gr.Tabs():
                # =================================================
                # REPLAY TAB
                # =================================================
                with gr.Tab("Replay · Curated episodes"):
                    gr.HTML(
                        '<div class="ck-redteam-pointer" role="note">'
                        "5 archived episodes show how the system works. "
                        "<strong>Want to stress-test it yourself?</strong> "
                        "Skip to the <em>🔴 Red-team it yourself</em> tab to "
                        "score any input against both reward profiles."
                        "</div>"
                    )
                    with gr.Accordion("How this demo works (30 seconds)", open=False, elem_classes=["ck-howto"]):
                        gr.HTML(
                            '<div class="ck-howto-body">'
                            '<p><strong>The 9-turn schedule:</strong></p>'
                            '<ol class="ck-howto-list">'
                            '<li><strong>T1 Scammer opener</strong> → T2 Victim reply → '
                            '<strong>T3 Analyzer decision #1</strong></li>'
                            '<li>T4 Scammer escalates → T5 Victim reply → '
                            '<strong>T6 Analyzer decision #2</strong></li>'
                            '<li>T7 Scammer transaction ask → '
                            '<strong>T8 Bank Monitor decision</strong> → T9 Outcome</li>'
                            '</ol>'
                            '<p><strong>The 5 agents:</strong></p>'
                            '<ul class="ck-howto-list">'
                            '<li><strong>Scammer</strong> — adversary, 376 NPCI/RBI-grounded templates · 7 languages</li>'
                            '<li><strong>Victim</strong> — scripted target, profile-based gullibility (SENIOR / SEMI_URBAN / YOUNG_URBAN)</li>'
                            '<li><strong>Analyzer</strong> — oversight LLM under training (Qwen2.5-7B + LoRA via GRPO). Sees chat only.</li>'
                            '<li><strong>Bank Monitor</strong> — second-tier oversight. Sees transaction metadata only — never chat.</li>'
                            '<li><strong>Regulator</strong> — meta-agent that adapts rule weights from aggregate outcomes.</li>'
                            '</ul>'
                            '<p><strong>What to watch:</strong> The <em>Suspicion timeline</em> climbing across analyzer turns; the <em>Bank Monitor panel</em> changing from <code>review</code> → <code>flag</code> → <code>freeze</code>; the <em>Outcome</em> badge at T9 (✅ saved, ❌ scammed, or 🤝 verified).</p>'
                            '</div>'
                        )

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
                        language_picker = gr.Dropdown(
                            choices=[
                                "English",
                                "Hindi (हिन्दी)",
                                "Tamil (தமிழ்)",
                                "Telugu (తెలుగు)",
                                "Kannada (ಕನ್ನಡ)",
                                "Bengali (বাংলা)",
                                "Marathi (मराठी)",
                            ],
                            value="English",
                            label="Language",
                            info="Demo episodes are English. Bench v0 is primarily English (n=161/175) with Hindi (n=9) and 5 single-sample placeholder languages tracked as v3 expansion targets. See DATASET_CARD.md.",
                            interactive=False,
                        )

                    info_panel = gr.HTML("")

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
                                '<div class="panel-heading">🔍 Analyzer says…</div>'
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
                    _initial_total = max_turn(_load_episode(default_label))
                    state.value = {
                        "label": default_label,
                        "mode": default_mode,
                        # STEP mode starts at turn 0 so judges control playback;
                        # AUTO mode jumps straight to the final turn.
                        "current_turn": 0 if default_mode == MODE_STEP else _initial_total,
                        "total_turns": _initial_total,
                    }

                # =================================================
                # LIVE Q&A TAB
                # =================================================
                with gr.Tab("Live · Score your own message"):
                    gr.HTML(
                        '<div class="panel-heading">Try the Analyzer</div>'
                        '<p style="margin:0 0 18px;font-size:14px;line-height:1.6;'
                        'color:var(--ck-slate);opacity:0.8;max-width:760px;">'
                        "Paste any SMS or chat snippet — the rule-based "
                        "Analyzer returns a suspicion score, declared signals, and a "
                        "natural-language explanation in one round-trip. The trained "
                        "<code>Qwen2.5-7B-LoRA-v2</code> adapter is hot-swappable "
                        "with <code>get_trained_analyzer()</code> when a GPU is available."
                        "</p>"
                    )
                    with gr.Row():
                        with gr.Column(scale=3, min_width=320):
                            user_input = gr.Textbox(
                                label="Message",
                                placeholder=(
                                    "e.g. \"Dear customer, your SBI KYC expires today. "
                                    "Click https://sbi-kyc.xyz within 2 hours or account frozen.\""
                                ),
                                lines=5,
                            )
                            analyze_btn = gr.Button("Analyze message", variant="primary")
                        with gr.Column(scale=2, min_width=260):
                            live_suspicion = gr.HTML(
                                value=_render_suspicion_score(
                                    0.0, "Paste a message and press Analyze."
                                )
                            )
                    analyze_btn.click(
                        on_live_analyze,
                        inputs=[user_input],
                        outputs=[live_suspicion],
                        show_progress="full",
                    )
                    user_input.submit(
                        on_live_analyze,
                        inputs=[user_input],
                        outputs=[live_suspicion],
                        show_progress="full",
                    )
                    with gr.Accordion("Try these examples", open=False):
                        gr.Examples(
                            examples=[
                                "Dear customer, your SBI KYC expires today. Click https://sbi-kyc.xyz to update within 2 hours or account frozen.",
                                "Congratulations! You won Rs 25,000 in PNB lucky draw. Share OTP to claim.",
                                "Your Amazon order is out for delivery. Expected between 4-7 PM. Track at amazon.in/orders",
                                "Urgent! Income Tax refund of Rs 23,400 pending. Verify your Aadhaar at it-refund-portal.in within 24 hours.",
                                "RBI Sachet Advisory: Beware of fake KYC update messages. RBI / your bank will NEVER ask for OTP, CVV, PIN. Report fraud to 1930.",
                            ],
                            inputs=[user_input],
                            label="",
                        )

                # =================================================
                # YOU VS ANALYZER TAB
                # =================================================
                with gr.Tab("You vs Analyzer"):
                    gr.HTML(
                        '<div class="panel-heading">Try to bypass the Analyzer</div>'
                        '<p style="margin:0 0 18px;font-size:14px;line-height:1.6;'
                        'color:var(--ck-slate);opacity:0.85;max-width:760px;">'
                        "<strong>Note:</strong> this tab runs the rule-based <em>scripted</em> "
                        "Analyzer. Score ≥ 0.50 means caught; below means bypassed. The trained "
                        "<code>Qwen2.5-7B-LoRA-v2</code> adapter scores tighter — see the "
                        "<em>Leaderboard</em> tab for v1 vs v2 deltas. LoRA serving in this "
                        "Space requires a GPU; routing through HF Inference API is on the v3 roadmap."
                        "</p>"
                    )
                    with gr.Row():
                        adv_input = gr.Textbox(
                            label="Your scam attempt",
                            placeholder=(
                                "e.g. \"Hi, I'm Rohan from SBI. Your account will be "
                                "frozen at 6PM. Share OTP to verify.\""
                            ),
                            lines=4,
                        )
                    # Three one-click presets — load a known scam into the textbox without
                    # requiring the judge to type during a live demo.
                    with gr.Row():
                        quick_otp = gr.Button("Test: OTP scam (Hindi)", size="sm")
                        quick_grooming = gr.Button("Test: Matrimonial crypto (English)", size="sm")
                        quick_deepfake = gr.Button("Test: Deepfake CEO IPO (English)", size="sm")
                    quick_otp.click(
                        lambda: "SBI: Aapka account block ho gaya hai. Turant OTP share kijiye verify ke liye, warna account permanently band ho jayega.",
                        inputs=[],
                        outputs=[adv_input],
                    )
                    quick_grooming.click(
                        lambda: "Hi, I'm a Singapore software engineer interested in marriage. I trade crypto and have made good returns. Let me show you my setup — invest a small amount and you'll see for yourself.",
                        inputs=[],
                        outputs=[adv_input],
                    )
                    quick_deepfake.click(
                        lambda: "[Infosys CEO voice]: Exclusive employee IPO allocation. Invest Rs 1 lakh via company portal. HR will call now for UPI transfer. Limited to first 100 employees.",
                        inputs=[],
                        outputs=[adv_input],
                    )
                    with gr.Row():
                        adv_send = gr.Button("Send to Analyzer", variant="primary")
                        adv_clear = gr.Button("Clear")
                    adv_banner = gr.HTML(value="")
                    with gr.Row():
                        with gr.Column():
                            adv_score = gr.Number(
                                label="Suspicion score (0=clean · 1=scam)",
                                precision=3,
                                interactive=False,
                            )
                            adv_flagged = gr.Textbox(
                                label="Flagged?", interactive=False
                            )
                        with gr.Column():
                            adv_signals = gr.JSON(label="Signals fired")
                    adv_explanation = gr.Textbox(
                        label="Analyzer reasoning", lines=2, interactive=False
                    )

                    adv_send.click(
                        on_adversarial_attempt,
                        inputs=[adv_input],
                        outputs=[adv_score, adv_flagged, adv_signals, adv_explanation, adv_banner],
                        show_progress="full",
                    )
                    adv_input.submit(
                        on_adversarial_attempt,
                        inputs=[adv_input],
                        outputs=[adv_score, adv_flagged, adv_signals, adv_explanation, adv_banner],
                        show_progress="full",
                    )
                    adv_clear.click(
                        lambda: ("", 0.0, "", {}, "", ""),
                        inputs=[],
                        outputs=[adv_input, adv_score, adv_flagged, adv_signals, adv_explanation, adv_banner],
                    )

                # =================================================
                # ADVERSARY LAB TAB — trained Scammer outputs vs both defenders
                # =================================================
                with gr.Tab("Adversary Lab · trained Scammer vs both defenders"):
                    from server.adversary_lab import (
                        render_aggregate_banner,
                        render_sample,
                        sample_choice_labels,
                    )

                    gr.HTML(
                        '<div class="panel-heading">B.2 Phase-1 head-to-head — visible co-evolution</div>'
                        '<p style="margin:0 0 14px;font-size:14px;line-height:1.6;'
                        'color:#000000;max-width:760px;">'
                        "We trained a <code>Qwen2.5-0.5B</code> Scammer LoRA via TRL GRPO "
                        "with the adversarial reward <code>1 − ScriptedAnalyzer.score</code>. "
                        "Below are the <strong>n = 64 best-of-8 generated scams</strong>, "
                        "scored by <em>both</em> defenders side-by-side. The pairs where "
                        "scripted misses but v2 LoRA catches are <strong>the +60 pp "
                        "co-evolution gap made visible</strong> — Theme #1 in one click."
                        "</p>"
                    )
                    gr.HTML(value=render_aggregate_banner())
                    adv_lab_choices = sample_choice_labels()
                    if adv_lab_choices:
                        adv_lab_picker = gr.Dropdown(
                            choices=[label for label, _ in adv_lab_choices],
                            value=adv_lab_choices[0][0],
                            label="Browse the 64 generated scams (✓ = caught · ✗ = bypassed)",
                        )
                        adv_lab_panel = gr.HTML(value=render_sample(0))

                        def _on_adv_lab_pick(label: str) -> str:
                            for lbl, idx in adv_lab_choices:
                                if lbl == label:
                                    return render_sample(idx)
                            return render_sample(0)

                        adv_lab_picker.change(
                            _on_adv_lab_pick,
                            inputs=[adv_lab_picker],
                            outputs=[adv_lab_panel],
                        )
                    else:
                        gr.HTML(
                            '<div style="color:#b71c1c;padding:12px;">'
                            "Adversary Lab data not loaded — "
                            "<code>logs/b2_phase1_scammer_vs_v2_lora.json</code> missing."
                            "</div>"
                        )

                # =================================================
                # v1 vs v2 TAB — the wow moment
                # =================================================
                with gr.Tab("v1 vs v2 — the reward-hacking fix"):
                    from server.demo_v1_v2 import (
                        list_scenario_choices,
                        render_summary_banner,
                        render_toggle_view,
                    )

                    gr.HTML(
                        '<div class="panel-heading">Same scenario · Same model · Three reward changes</div>'
                        '<p style="margin:0 0 14px;font-size:14px;line-height:1.6;'
                        'color:#000000;max-width:760px;">'
                        "Pick a scenario. The v1 panel shows the reward-hacked adapter; "
                        "the v2 panel shows the principled retrain. The asymmetric "
                        "improvement — detection ≈ unchanged, FPR collapsed 5× — is the "
                        "signal that v2 learned the task instead of the proxy."
                        "</p>"
                    )
                    vs_banner = gr.HTML(value=render_summary_banner())
                    vs_choices = list_scenario_choices()
                    vs_default_id = vs_choices[1][1] if len(vs_choices) >= 2 else vs_choices[0][1]
                    vs_picker = gr.Radio(
                        choices=[label for label, _ in vs_choices],
                        value=next(label for label, sid in vs_choices if sid == vs_default_id),
                        label="Scenario (try the benigns to see v1 over-flag)",
                    )
                    vs_prompt = gr.HTML()
                    with gr.Row():
                        with gr.Column():
                            vs_v1 = gr.HTML()
                        with gr.Column():
                            vs_v2 = gr.HTML()
                    vs_asymmetry = gr.HTML()

                    def _vs_handler(label_value: str) -> tuple[str, str, str, str]:
                        sid = next(
                            (sid for label, sid in vs_choices if label == label_value),
                            vs_default_id,
                        )
                        return render_toggle_view(sid)

                    # Prime the initial render.
                    _initial_vs = _vs_handler(
                        next(label for label, sid in vs_choices if sid == vs_default_id)
                    )
                    vs_prompt.value = _initial_vs[0]
                    vs_v1.value = _initial_vs[1]
                    vs_v2.value = _initial_vs[2]
                    vs_asymmetry.value = _initial_vs[3]

                    vs_picker.change(
                        _vs_handler,
                        inputs=[vs_picker],
                        outputs=[vs_prompt, vs_v1, vs_v2, vs_asymmetry],
                    )

                # =================================================
                # LIVE RED-TEAM TAB — same analyzer, two reward profiles
                # =================================================
                with gr.Tab("🔴 Red-team it yourself"):
                    from server.redteam_handler import render_redteam_view

                    gr.HTML(
                        '<div class="panel-heading">Same analyzer · Two reward profiles</div>'
                        '<p style="margin:0 0 14px;font-size:14px;line-height:1.6;'
                        'color:#000000;max-width:760px;">'
                        "Type any scam attempt or borderline benign. The rule-based scripted "
                        "analyzer scores it once. Then we evaluate the same prediction "
                        "against the v1 reward profile (5 leaves, the reward-hacked one) "
                        "and the v2 reward profile (8 leaves, the principled retrain). "
                        "<strong>The difference between the two reward totals is the "
                        "reward-hacking signature</strong> — that asymmetry is exactly what "
                        "shaped v1's 36 % FPR and what v2 fixed. Optionally tag your "
                        "input as benign / scam to surface the diagnostic explicitly."
                        "</p>"
                    )
                    rt_input = gr.Textbox(
                        placeholder="e.g. 'Your KYC expires today, click bit.ly/verify-kyc'",
                        label="Your message",
                        lines=3,
                        elem_id="redteam-input",
                    )
                    rt_truth = gr.Radio(
                        choices=[
                            ("(unspecified)", "none"),
                            ("ground truth: scam", "scam"),
                            ("ground truth: benign", "benign"),
                        ],
                        value="none",
                        label="Optional ground-truth tag (sharpens the diagnostic)",
                    )
                    rt_btn = gr.Button(
                        "Score with both reward profiles",
                        variant="primary",
                        elem_id="redteam-score-btn",
                    )
                    with gr.Row(elem_id="redteam-row"):
                        with gr.Column():
                            rt_v1 = gr.HTML()
                        with gr.Column():
                            rt_v2 = gr.HTML()
                    rt_badge = gr.HTML()

                    def _rt_handler(message: str, truth: str) -> tuple[str, str, str]:
                        is_benign = (
                            True if truth == "benign"
                            else False if truth == "scam"
                            else None
                        )
                        try:
                            return render_redteam_view(message, is_benign_truth=is_benign)
                        except Exception as exc:  # noqa: BLE001
                            err = (
                                '<div style="padding:12px 16px;background:#FFE8D2;'
                                'border:1px solid #381932;border-radius:10px;'
                                f'color:#000000;font-size:13px;">Error: {exc!s}</div>'
                            )
                            return err, err, ""

                    rt_btn.click(
                        _rt_handler,
                        inputs=[rt_input, rt_truth],
                        outputs=[rt_v1, rt_v2, rt_badge],
                    )

                # =================================================
                # LEADERBOARD TAB
                # =================================================
                with gr.Tab("Leaderboard"):
                    gr.HTML(
                        '<div class="panel-heading">chakravyuh-bench-v0 leaderboard</div>'
                        '<p style="margin:0 0 18px;font-size:14px;line-height:1.6;'
                        'color:var(--ck-slate);opacity:0.85;max-width:760px;">'
                        "Methods ranked by F1 on the 175-scenario bench. "
                        "v1 (reward-hacked) is kept on the board to motivate v2's principled retrain. "
                        "Submit your model: <code>POST /submit</code> with the schema in "
                        "<code>server/leaderboard.py</code>."
                        "</p>"
                        '<p style="margin:0 0 18px;font-size:13px;line-height:1.55;'
                        'color:var(--ck-slate);opacity:0.78;max-width:760px;">'
                        "<strong>Why F1?</strong> F1 balances detection (recall) and false-positive "
                        "avoidance — a model that flags everything has high recall but low F1. The "
                        "asymmetric v1→v2 lift (recall ≈ unchanged, FPR ↓5×) is exactly the kind "
                        "of move F1 surfaces and detection-only ranking would hide."
                        "</p>"
                    )
                    leaderboard_table = gr.Dataframe(
                        headers=["#", "Method", "F1", "Detection", "FPR", "n", "Notes"],
                        value=_load_leaderboard_rows(),
                        datatype=["str", "str", "str", "str", "str", "str", "str"],
                        interactive=False,
                        wrap=True,
                        elem_classes=["ck-leaderboard"],
                    )
                    refresh_btn = gr.Button("↻ Refresh leaderboard")
                    refresh_btn.click(
                        lambda: _load_leaderboard_rows(),
                        inputs=[],
                        outputs=[leaderboard_table],
                    )

            gr.HTML(
                '<footer class="chakravyuh-footer">'
                "Chakravyuh is an open-source benchmark for Indian UPI fraud detection — "
                'an entry to the Meta PyTorch <abbr title="Open Reinforcement Learning Environment">OpenEnv</abbr> '
                "Hackathon 2026, Bangalore. "
                "Bench <code>chakravyuh-bench-v0</code> (n=175 scenarios) · "
                "Adapter <code>ujjwalpardeshi/chakravyuh-analyzer-lora-v2</code> · "
                "MIT-licensed code, CC-BY-4.0 dataset."
                "</footer>"
            )
    return app


def _build_theme() -> gr.themes.Base:
    """Two-color theme: deep plum (#381932) + warm cream (#FFF3E6).

    Strict white/black text rule — no greys. Plum scale built around #381932;
    neutral scale built around the cream surface. We start from `Base` so we
    can paint exact colors and not inherit Gradio's default blue/grey.
    """
    plum_scale = gr.themes.Color(
        c50="#FBEAF6",
        c100="#F5D2EA",
        c200="#E0A4C9",
        c300="#C476A8",
        c400="#9C4F87",
        c500="#7A3565",
        c600="#5A234C",
        c700="#381932",   # primary plum
        c800="#2A0F25",
        c900="#1A0717",
        c950="#0D030B",
    )
    neutral_scale = gr.themes.Color(
        c50="#FFFBF5",     # cream-2 (lifted)
        c100="#FFF3E6",    # cream (page surface)
        c200="#FFE8D2",    # cream-3
        c300="#F5D8BB",
        c400="#E2BEA0",
        c500="#B89880",
        c600="#8E7461",
        c700="#5C4B3F",
        c800="#3A2F27",
        c900="#1F1813",
        c950="#0E0A07",
    )
    return gr.themes.Base(
        primary_hue=plum_scale,
        secondary_hue=plum_scale,
        neutral_hue=neutral_scale,
        font=[gr.themes.GoogleFont("Inter"), "Segoe UI", "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "Consolas", "monospace"],
    ).set(
        # Light mode (the only mode we ship)
        body_background_fill="#FFF3E6",
        body_text_color="#000000",
        body_text_color_subdued="#000000",
        background_fill_primary="#FFF3E6",
        background_fill_secondary="#FFFBF5",
        block_background_fill="#FFFBF5",
        border_color_primary="rgba(56,25,50,0.18)",
        button_primary_background_fill="#381932",
        button_primary_background_fill_hover="#2A0F25",
        button_primary_text_color="#FFFFFF",
        button_secondary_background_fill="#FFFFFF",
        button_secondary_background_fill_hover="rgba(56,25,50,0.08)",
        button_secondary_text_color="#000000",
        input_background_fill="#FFFFFF",
        input_border_color="rgba(56,25,50,0.18)",
        input_border_color_focus="#381932",
        link_text_color="#381932",
        block_label_text_color="#000000",
        block_title_text_color="#000000",
        # Dark-mode overrides — applied when OS is in dark mode. We intentionally
        # mirror the light values so the UI stays cream + plum either way.
        body_background_fill_dark="#FFF3E6",
        body_text_color_dark="#000000",
        body_text_color_subdued_dark="#000000",
        background_fill_primary_dark="#FFF3E6",
        background_fill_secondary_dark="#FFFBF5",
        block_background_fill_dark="#FFFBF5",
        border_color_primary_dark="rgba(56,25,50,0.18)",
        button_primary_background_fill_dark="#381932",
        button_primary_background_fill_hover_dark="#2A0F25",
        button_primary_text_color_dark="#FFFFFF",
        button_secondary_background_fill_dark="#FFFFFF",
        button_secondary_background_fill_hover_dark="rgba(56,25,50,0.08)",
        button_secondary_text_color_dark="#000000",
        input_background_fill_dark="#FFFFFF",
        input_border_color_dark="rgba(56,25,50,0.18)",
        input_border_color_focus_dark="#381932",
        link_text_color_dark="#381932",
        block_label_text_color_dark="#000000",
        block_title_text_color_dark="#000000",
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = build_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=CUSTOM_CSS,
        theme=_build_theme(),
    )


if __name__ == "__main__":
    main()
