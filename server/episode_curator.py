"""Episode curator: replays deterministic seeds to produce demo-ready episodes.

Separated from Gradio UI so it's testable without demo deps installed.

This module captures FULL turn-by-turn state for each replay:
  - Chat messages (for the conversation panel)
  - Analyzer suspicion scores with explanations (for the verdict timeline)
  - Bank Monitor actions with amount/payee info (for the bank panel)

Both the Gradio UI and the unit tests consume this structured output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from chakravyuh_env import ChakravyuhEnv
from chakravyuh_env.agents.analyzer import (
    _FINANCIAL_LURE_KEYWORDS,
    _IMPERSONATION_PHRASES,
    _INFO_KEYWORDS,
    _SUSPICIOUS_TLDS,
    _URGENCY_KEYWORDS,
    _URL_PATTERN,
    _URL_SHORTENERS,
)
from chakravyuh_env.schemas import (
    AnalyzerScore,
    AnalyzerSignal,
    BankApprove,
    BankFlag,
    BankFreeze,
    ChatMessage,
    EpisodeOutcome,
    TransactionMeta,
    VictimProfile,
)


OutcomeKind = Literal[
    "detection_too_late",  # analyzer flags but victim already complied
    "scripted_missed",      # scripted rules had blind spot — LoRA upgrade motivator
    "victim_refused",       # skeptical victim refuses without system help
    "multi_agent_save",     # analyzer flag + bank freeze = multi-layer defense wins
    "victim_verified",      # victim calls bank proactively
]


@dataclass(frozen=True)
class CuratedEpisode:
    """A pre-vetted episode selected for demo replay.

    The (seed, profile, gullibility) triple + deterministic env makes this
    100% reproducible — same result every replay, required for pitch-day safety.
    """

    label: str  # UI display name
    seed: int
    profile: VictimProfile
    gullibility: float
    outcome_kind: OutcomeKind
    description: str  # One-line description for judges


# Curated via scan of seeds 0-500. Each seed produces a deterministic episode
# demonstrating a different outcome path. Tested on Day 1.
CURATED_EPISODES: tuple[CuratedEpisode, ...] = (
    CuratedEpisode(
        label="1. 🛡️ Multi-Agent Defense Wins",
        seed=5,
        profile=VictimProfile.SENIOR,
        gullibility=1.5,
        outcome_kind="multi_agent_save",
        description=(
            "Senior victim complies with 'SBI YONO biometric' OTP scam. "
            "Analyzer suspicion hits 0.99 by turn 3. Bank Monitor independently "
            "detects new-payee + large amount — transaction FROZEN. Victim saved "
            "via multi-layer defense."
        ),
    ),
    CuratedEpisode(
        label="2. 🧠 Skeptical Victim Refuses",
        seed=0,
        profile=VictimProfile.YOUNG_URBAN,
        gullibility=0.7,
        outcome_kind="victim_refused",
        description=(
            "Young urban victim receives Union Bank manager impersonation asking "
            "for OTP. Low base-trust demographic recognizes the pattern immediately "
            "and refuses at turn 2 — before oversight even activates."
        ),
    ),
    CuratedEpisode(
        label="3. 📞 Verification-First Behavior",
        seed=2,
        profile=VictimProfile.YOUNG_URBAN,
        gullibility=0.7,
        outcome_kind="victim_verified",
        description=(
            "Victim receives 'CashNow loan approval' pitch. Instead of complying or "
            "refusing blindly, victim proactively CALLS BANK to verify — the ideal "
            "defensive behavior we want to shape with the reward function."
        ),
    ),
    CuratedEpisode(
        label="4. ⚠️ Detection Too Late (Motivates LoRA)",
        seed=3,
        profile=VictimProfile.SENIOR,
        gullibility=1.5,
        outcome_kind="detection_too_late",
        description=(
            "PAN 2.0 KYC fake-link scam. Analyzer eventually scores 1.00 suspicion "
            "— but only AFTER the senior has already complied at turn 2. Shows why "
            "we need faster + earlier detection (Day 2 LoRA upgrade target)."
        ),
    ),
    CuratedEpisode(
        label="5. 🎭 Scripted Rules Blind Spot",
        seed=13,
        profile=VictimProfile.SENIOR,
        gullibility=1.5,
        outcome_kind="scripted_missed",
        description=(
            "KYC fake-link scam phrased without the strong keyword signatures "
            "our rule-based analyzer looks for. Suspicion never crosses "
            "threshold. Money extracted. Demonstrates the gap that semantic "
            "LLM analysis closes on Day 2."
        ),
    ),
)


@dataclass(frozen=True)
class AnalyzerSnapshot:
    turn: int
    score: float
    explanation: str
    signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class BankSnapshot:
    turn: int
    decision: Literal["approve", "flag", "freeze"]
    amount_inr: float
    receiver_new: bool
    reason: str


@dataclass(frozen=True)
class ReplayedEpisode:
    """Full result of replaying a curated episode."""

    label: str
    description: str
    seed: int
    profile: VictimProfile
    chat_history: list[ChatMessage]
    outcome: EpisodeOutcome
    analyzer_snapshots: list[AnalyzerSnapshot] = field(default_factory=list)
    bank_snapshots: list[BankSnapshot] = field(default_factory=list)
    transaction: TransactionMeta | None = None


def replay(episode: CuratedEpisode) -> ReplayedEpisode:
    """Replay a curated episode deterministically. Returns full trace.

    Identical inputs → identical outputs. This is the demo's contract.
    """
    env = ChakravyuhEnv(
        victim_profile=episode.profile,
        gullibility=episode.gullibility,
    )
    env.reset(seed=episode.seed)

    analyzer_snapshots: list[AnalyzerSnapshot] = []
    bank_snapshots: list[BankSnapshot] = []

    original_analyzer_act = env.analyzer.act
    original_bank_act = env.bank_monitor.act

    def capturing_analyzer(obs):
        action = original_analyzer_act(obs)
        if isinstance(action, AnalyzerScore):
            analyzer_snapshots.append(
                AnalyzerSnapshot(
                    turn=obs.turn,
                    score=round(action.score, 3),
                    explanation=action.explanation,
                    signals=tuple(s.value for s in action.signals),
                )
            )
        return action

    def capturing_bank(obs):
        action = original_bank_act(obs)
        tx = obs.transaction
        if tx is None:
            return action
        if isinstance(action, BankApprove):
            decision: Literal["approve", "flag", "freeze"] = "approve"
            reason = f"confidence={action.confidence:.2f}"
        elif isinstance(action, BankFlag):
            decision = "flag"
            reason = action.signal
        elif isinstance(action, BankFreeze):
            decision = "freeze"
            reason = action.reason
        else:
            return action
        bank_snapshots.append(
            BankSnapshot(
                turn=obs.turn,
                decision=decision,
                amount_inr=tx.amount,
                receiver_new=tx.receiver_new,
                reason=reason,
            )
        )
        return action

    env.analyzer.act = capturing_analyzer  # type: ignore[method-assign]
    env.bank_monitor.act = capturing_bank  # type: ignore[method-assign]

    done = False
    info: dict = {}
    while not done:
        _, _, done, info = env.step()

    return ReplayedEpisode(
        label=episode.label,
        description=episode.description,
        seed=episode.seed,
        profile=episode.profile,
        chat_history=list(env._state.chat_history) if env._state else [],
        outcome=info["outcome"],
        analyzer_snapshots=analyzer_snapshots,
        bank_snapshots=bank_snapshots,
        transaction=env._state.transaction if env._state else None,
    )


def replay_all() -> list[ReplayedEpisode]:
    """Replay all curated episodes. Used for smoke testing."""
    return [replay(ep) for ep in CURATED_EPISODES]


# ---------------------------------------------------------------------------
# UI helpers — HTML rendering for Gradio panels
# ---------------------------------------------------------------------------


def outcome_badge(outcome: EpisodeOutcome) -> str:
    """One-line status for the UI header."""
    if outcome.money_extracted:
        return "❌ MONEY EXTRACTED — Victim lost money"
    if outcome.bank_froze:
        return "🛡️ BANK FROZE — Transaction blocked"
    if outcome.victim_sought_verification:
        return "✅ VERIFIED — Victim called bank"
    if outcome.victim_refused:
        return "✅ REFUSED — Victim refused explicitly"
    if outcome.analyzer_flagged:
        return "🚨 ANALYZER FLAGGED — Warning issued"
    return "— No action taken"


# -- (B) Keyword highlighting ------------------------------------------------

# Two-color palette + strict white/black text. Highlight priority is
# expressed via fill density on the plum (#381932) ramp:
#   info          → solid plum + WHITE text (heaviest, direct PII ask)
#   urgency       → white bg + 1.5px plum border + BLACK text (medium)
#   impersonation → cream-3 bg + plum hairline + BLACK text (lightest)
_HIGHLIGHT_STYLES: dict[str, str] = {
    "info":          "background:#381932;color:#FFFFFF;border:1px solid #381932;",
    "urgency":       "background:#FFFFFF;color:#000000;border:1.5px solid #381932;",
    "impersonation": "background:#FFE8D2;color:#000000;border:1px solid rgba(56,25,50,0.30);",
}
_HIGHLIGHT_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "info",
        r"\b(otp|aadhaar|adhar|pan|cvv|pin|upi\s+pin|card\s+number|bank\s+details)\b",
    ),
    (
        "urgency",
        r"\b(urgent|urgently|immediately|now|expires?|expired|minutes?|hours?\s+left|within\s+\d+|last\s+chance|hurry|act\s+fast|deadline|suspended|block(?:ed)?)\b",
    ),
    (
        "impersonation",
        r"\b(sbi|hdfc|icici|axis\s+bank|yes\s+bank|kotak|canara|pnb|rbi|uidai|income\s+tax|epfo|cbi|police|cyber\s+cell|customer\s+care|fraud\s+team|manager|officer)\b",
    ),
)


def _highlight_keywords(text: str) -> str:
    """Wrap keyword matches in palette-aligned <mark> tags. HTML-safe."""
    escaped = _html_escape(text)

    # Suspicious URLs — heaviest mark (solid plum + white text)
    def _url_replacer(match: re.Match) -> str:
        url = match.group(0)
        low = url.lower()
        if any(tld in low for tld in _SUSPICIOUS_TLDS) or any(
            short in low for short in _URL_SHORTENERS
        ):
            return (
                '<mark style="background:#381932;color:#FFFFFF;'
                'padding:2px 6px;border-radius:4px;font-weight:600;'
                'text-decoration:underline;text-decoration-color:#FFFFFF;'
                'text-underline-offset:2px;">'
                f"{url}</mark>"
            )
        return url

    escaped = _URL_PATTERN.sub(_url_replacer, escaped)
    for category, pattern in _HIGHLIGHT_PATTERNS:
        style = _HIGHLIGHT_STYLES[category]
        escaped = re.sub(
            pattern,
            lambda m, s=style: (
                f'<mark style="{s}padding:1px 6px;border-radius:4px;'
                f'font-weight:700;">{m.group(0)}</mark>'
            ),
            escaped,
            flags=re.IGNORECASE,
        )
    return escaped


def format_chat_html(
    chat: list[ChatMessage], up_to_turn: int | None = None, highlight: bool = True
) -> str:
    """Render chat as HTML for Gradio display.

    Args:
        chat: full chat history
        up_to_turn: only show messages with turn <= this value (for step-through)
        highlight: if True, wrap suspicious keywords in <mark> tags (scammer only)
    """
    rows = []
    for msg in chat:
        if up_to_turn is not None and msg.turn > up_to_turn:
            continue
        who = "Scammer" if msg.sender == "scammer" else "Victim"
        # Two-color contract:
        #   Scammer  → white bg + 3px plum left border (the threat — full ink edge)
        #   Victim   → cream-3 bg + 3px plum-tint left border (softer)
        # Both sides: BLACK text on light surface.
        if msg.sender == "scammer":
            bg = "#FFFFFF"
            accent = "#381932"
        else:
            bg = "#FFE8D2"
            accent = "rgba(56,25,50,0.30)"
        body = (
            _highlight_keywords(msg.text)
            if (highlight and msg.sender == "scammer")
            else _html_escape(msg.text)
        )
        rows.append(
            f'<div style="margin:10px 0;padding:14px 16px;background:{bg};'
            f'border-left:3px solid {accent};border-radius:8px;'
            'color:#000000;font-size:14px;line-height:1.6;'
            'border-top:1px solid rgba(56,25,50,0.10);'
            'border-right:1px solid rgba(56,25,50,0.10);'
            'border-bottom:1px solid rgba(56,25,50,0.10);">'
            '<div style="font-size:11px;font-weight:700;letter-spacing:1.4px;'
            'text-transform:uppercase;color:#381932;'
            f'margin-bottom:6px;">T{msg.turn} · {who}</div>'
            f'<div style="color:#000000;">{body}</div>'
            "</div>"
        )
    return "".join(rows) or (
        '<div style="padding:14px;color:#000000;opacity:0.55;font-style:italic;'
        'font-size:13px;text-align:center;background:#FFFBF5;'
        'border:1px dashed rgba(56,25,50,0.30);border-radius:8px;">'
        "No messages yet.</div>"
    )


# -- (A) Suspicion timeline --------------------------------------------------


def format_suspicion_timeline(
    snapshots: list[AnalyzerSnapshot], up_to_turn: int | None = None
) -> str:
    """Render a mini-timeline of suspicion scores across analyzer turns."""
    visible = [s for s in snapshots if up_to_turn is None or s.turn <= up_to_turn]
    if not visible:
        return (
            '<div style="padding:14px;color:#000000;opacity:0.65;font-style:italic;'
            'font-size:13px;text-align:center;background:#FFFBF5;'
            'border:1px dashed rgba(56,25,50,0.30);border-radius:8px;">'
            "Analyzer has not evaluated yet."
            "</div>"
        )
    rows = ['<div style="padding:10px 4px;">']
    for snap in visible:
        pct = int(snap.score * 100)
        # Two-color contract: bar is always plum; severity encoded by length.
        # Score number: BLACK on cream surface (always readable).
        bar_color = "#381932"
        # Tooltip: turn, score, top signal (if any), short explanation.
        top_signal = snap.signals[0] if snap.signals else "—"
        expl_short = (snap.explanation or "").strip()
        if len(expl_short) > 110:
            expl_short = expl_short[:107] + "…"
        tooltip = (
            f"T{snap.turn} · score={snap.score:.2f} · "
            f"top signal: {top_signal}"
            + (f" · {expl_short}" if expl_short else "")
        )
        rows.append(
            f'<div title="{_html_escape(tooltip)}" '
            'style="margin:8px 0;font-size:13px;cursor:help;">'
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<span style="color:#000000;min-width:40px;'
            'font-weight:700;font-size:11px;letter-spacing:1.2px;">'
            f'T{snap.turn}</span>'
            '<div style="flex:1;background:rgba(56,25,50,0.12);'
            'border-radius:999px;height:8px;overflow:hidden;">'
            f'<div class="suspicion-bar-fill" '
            f'style="background:{bar_color};width:{pct}%;height:100%;"></div>'
            "</div>"
            '<span style="color:#000000;font-weight:700;'
            'min-width:44px;text-align:right;font-variant-numeric:tabular-nums;">'
            f'{snap.score:.2f}</span>'
            "</div></div>"
        )
    rows.append("</div>")
    return "".join(rows)


def suspicion_score_for_turn(
    snapshots: list[AnalyzerSnapshot], up_to_turn: int | None = None
) -> tuple[float, str]:
    """Return the MAX suspicion score seen so far + its explanation."""
    visible = [s for s in snapshots if up_to_turn is None or s.turn <= up_to_turn]
    if not visible:
        return 0.0, "Analyzer has not evaluated yet."
    best = max(visible, key=lambda s: s.score)
    return best.score, best.explanation


# -- (C) Bank monitor panel --------------------------------------------------


def format_bank_panel(
    snapshots: list[BankSnapshot],
    transaction: TransactionMeta | None,
    up_to_turn: int | None = None,
) -> str:
    """Render the Bank Monitor oversight panel."""
    visible = [s for s in snapshots if up_to_turn is None or s.turn <= up_to_turn]

    if not visible and transaction is None:
        return (
            '<div style="padding:16px;border:1px dashed rgba(56,25,50,0.30);'
            'border-radius:12px;color:#000000;opacity:0.7;font-size:13px;'
            'text-align:center;background:#FFFBF5;">'
            "Bank Monitor inactive — no transaction attempted yet."
            "</div>"
        )

    # Latest bank decision (or pending)
    if visible:
        latest = visible[-1]
        # Two-color contract:
        #   approve → white bg, BLACK text (lightest, no friction)
        #   flag    → cream-3 bg, BLACK text, plum left-border (medium)
        #   freeze  → solid plum bg, WHITE text (heaviest — decisive action)
        if latest.decision == "freeze":
            bg, fg, accent = "#381932", "#FFFFFF", "#381932"
            label = "FROZEN"
        elif latest.decision == "flag":
            bg, fg, accent = "#FFE8D2", "#000000", "#381932"
            label = "FLAGGED"
        else:
            bg, fg, accent = "#FFFFFF", "#000000", "rgba(56,25,50,0.30)"
            label = "APPROVED"
        tx = transaction
        rows = [
            f'<div class="ck-bank-panel ck-bank-{latest.decision}" '
            f'style="background:{bg};border:1px solid {accent};'
            f'border-left:3px solid {accent};color:{fg};'
            'border-radius:12px;padding:16px 18px;">',
            f'<div style="font-size:10px;letter-spacing:1.6px;color:{fg};'
            'text-transform:uppercase;font-weight:700;'
            f'margin-bottom:10px;">Bank Monitor · T{latest.turn}</div>',
            f'<div style="font-size:20px;font-weight:800;color:{fg};'
            'letter-spacing:0.4px;margin-bottom:10px;line-height:1.1;">'
            f'{label}</div>',
        ]
        if tx is not None:
            # Hairline color depends on the panel: plum-tint on light bg,
            # white-tint on the dark FROZEN bg.
            divider = (
                "rgba(255,255,255,0.20)" if bg == "#381932"
                else "rgba(56,25,50,0.18)"
            )
            row_style = (
                "display:flex;justify-content:space-between;gap:8px;"
                f"padding:6px 0;border-top:1px solid {divider};"
                f"font-size:13px;color:{fg};"
            )
            label_style = f"font-weight:700;color:{fg};opacity:0.78;"
            rows.append(
                f'<div style="font-size:13px;line-height:1.55;color:{fg};">'
                f'<div style="{row_style}border-top:none;">'
                f'<span style="{label_style}">Amount</span>'
                '<span style="font-variant-numeric:tabular-nums;font-weight:700;">'
                f'₹{tx.amount:,.0f}</span></div>'
                f'<div style="{row_style}">'
                f'<span style="{label_style}">Receiver</span>'
                f'<span style="font-weight:600;">'
                f'{"New payee" if tx.receiver_new else "Known"}</span></div>'
                f'<div style="{row_style}">'
                f'<span style="{label_style}">Frequency · 24h</span>'
                '<span style="font-variant-numeric:tabular-nums;font-weight:600;">'
                f'{tx.frequency_24h} txn</span></div>'
                f'<div style="margin-top:10px;font-size:12px;line-height:1.55;'
                f'color:{fg};"><span style="{label_style}">'
                f'Reason · </span>{_html_escape(latest.reason)}</div>'
                "</div>"
            )
        rows.append("</div>")
        return "".join(rows)

    # Pending — tx exists but bank hasn't acted yet
    return (
        '<div style="padding:14px 16px;border:1px solid rgba(56,25,50,0.18);'
        'border-radius:12px;color:#000000;font-size:13px;background:#FFFBF5;">'
        f"Transaction pending bank review · ₹{transaction.amount:,.0f}"
        f" → {'new' if transaction.receiver_new else 'known'} payee."
        "</div>"
    )


# -- Misc helpers ------------------------------------------------------------


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def max_turn(episode: ReplayedEpisode) -> int:
    """Highest turn number across chat/analyzer/bank. Used for step-through bounds."""
    t = 0
    for msg in episode.chat_history:
        t = max(t, msg.turn)
    for snap in episode.analyzer_snapshots:
        t = max(t, snap.turn)
    for snap in episode.bank_snapshots:
        t = max(t, snap.turn)
    return t


# ---------------------------------------------------------------------------
# Agent-state derivation + card/timeline rendering
# ---------------------------------------------------------------------------

# Two-color palette. All agents share plum ink + alternating bg fill so the
# 5 cards form a paired cream / cream-2 / white rhythm:
#   scammer   = plum-tinted cream (subtle threat presence)
#   victim    = white            (the target — clearest)
#   analyzer  = cream-2          (the protagonist — lifted)
#   bank      = white            (oversight — clean)
#   regulator = cream-3          (passive meta — heavier ground)
# All accents are plum #381932; all body text is BLACK.
AGENT_COLORS: dict[str, dict[str, str]] = {
    "scammer":   {"accent": "#381932", "soft": "rgba(56,25,50,0.08)", "icon": "🎭"},
    "victim":    {"accent": "#381932", "soft": "#FFFFFF",             "icon": "👤"},
    "analyzer":  {"accent": "#381932", "soft": "#FFFBF5",             "icon": "🔍"},
    "bank":      {"accent": "#381932", "soft": "#FFFFFF",             "icon": "🏦"},
    "regulator": {"accent": "#381932", "soft": "#FFE8D2",             "icon": "📜"},
}


@dataclass(frozen=True)
class AgentState:
    """Snapshot of one agent's state at a specific turn."""

    agent: Literal["scammer", "victim", "analyzer", "bank", "regulator"]
    status: str   # "Attacking", "Complied", "HIGH RISK", etc.
    detail: str   # 1-line description
    tone: Literal["idle", "active", "warning", "critical", "safe"]


# Tone severity is encoded in the AGENT-CARD STATUS LINE COLOR ONLY.
# Strict white/black text rule: status text is always BLACK (on light card)
# except `critical` which gets a solid plum chip (white text) to demand
# attention without violating the contract.
#
# We return a tuple-style spec via two parallel dicts: the visible color of
# the status text, plus an optional inline "chip" wrapper for the critical
# state (handled in `format_agent_cards_html`).
_TONE_COLOR: dict[str, str] = {
    "idle":     "#000000",   # status will use opacity:0.40 in the card render
    "active":   "#000000",
    "warning":  "#000000",   # status will be wrapped in a plum hairline pill
    "critical": "#FFFFFF",   # status will be wrapped in a solid plum chip
    "safe":     "#000000",   # status will be wrapped in a plum hairline pill
}


def compute_agent_states(
    episode: ReplayedEpisode, up_to_turn: int | None = None
) -> list[AgentState]:
    """Derive each agent's visible state at the given turn cutoff."""
    cutoff = up_to_turn if up_to_turn is not None else max_turn(episode)

    # Scammer state
    scammer_msgs = [
        m for m in episode.chat_history
        if m.sender == "scammer" and m.turn <= cutoff
    ]
    # Turn 7 in env schedule = scammer requests transaction (env-level action,
    # not always a chat message). Check transaction existence directly.
    tx_requested = episode.transaction is not None and cutoff >= 7
    if not scammer_msgs:
        scammer = AgentState("scammer", "Idle", "Awaiting target", "idle")
    elif tx_requested:
        scammer = AgentState(
            "scammer", "Transaction ask", "Requesting money transfer", "critical"
        )
    elif any(m.turn >= 4 for m in scammer_msgs):
        scammer = AgentState(
            "scammer", "Escalating", "Applying pressure on victim", "warning"
        )
    else:
        scammer = AgentState(
            "scammer", "Pretexting", "Opening attack narrative", "active"
        )

    # Victim state — derive from most recent victim message
    victim_msgs = [
        m for m in episode.chat_history
        if m.sender == "victim" and m.turn <= cutoff
    ]
    if not victim_msgs:
        victim = AgentState("victim", "Idle", "Has not responded", "idle")
    else:
        latest = victim_msgs[-1].text
        if "[CALLED BANK" in latest:
            victim = AgentState(
                "victim", "Verifying", "Called bank to confirm — ideal", "safe"
            )
        elif "[REFUSED" in latest:
            victim = AgentState(
                "victim", "Refused", "Rejected scammer request", "safe"
            )
        elif "[COMPLIED" in latest:
            victim = AgentState(
                "victim", "Complied", "Shared sensitive info", "critical"
            )
        else:
            victim = AgentState(
                "victim", "Engaging", "Replying cautiously", "active"
            )

    # Analyzer state
    visible_analyzer = [s for s in episode.analyzer_snapshots if s.turn <= cutoff]
    if not visible_analyzer:
        analyzer = AgentState(
            "analyzer", "Watching", "Monitoring chat", "idle"
        )
    else:
        best = max(visible_analyzer, key=lambda s: s.score)
        if best.score >= 0.7:
            analyzer = AgentState(
                "analyzer", f"HIGH · {best.score:.2f}", best.explanation[:60], "critical"
            )
        elif best.score >= 0.4:
            analyzer = AgentState(
                "analyzer", f"MEDIUM · {best.score:.2f}", best.explanation[:60], "warning"
            )
        else:
            analyzer = AgentState(
                "analyzer", f"LOW · {best.score:.2f}", "No strong signals yet", "active"
            )

    # Bank state
    visible_bank = [s for s in episode.bank_snapshots if s.turn <= cutoff]
    if not visible_bank:
        if episode.transaction is not None and cutoff >= 7:
            bank = AgentState(
                "bank", "Reviewing",
                f"Tx Rs {episode.transaction.amount:,.0f} pending", "active"
            )
        else:
            bank = AgentState("bank", "Dormant", "No transaction yet", "idle")
    else:
        latest = visible_bank[-1]
        if latest.decision == "freeze":
            bank = AgentState(
                "bank", "FROZEN",
                f"Rs {latest.amount_inr:,.0f} blocked", "safe"
            )
        elif latest.decision == "flag":
            bank = AgentState(
                "bank", "Flagged",
                f"Confidence {latest.reason[:50]}", "warning"
            )
        else:
            bank = AgentState(
                "bank", "Approved",
                f"Rs {latest.amount_inr:,.0f} cleared", "active"
            )

    # Regulator state
    if cutoff >= 10 or episode.outcome.turns_used <= cutoff:
        regulator = AgentState(
            "regulator", "Logged",
            "Outcome recorded; rules may update", "active"
        )
    else:
        regulator = AgentState(
            "regulator", "Passive",
            "Awaiting episode end", "idle"
        )

    return [scammer, victim, analyzer, bank, regulator]


def format_agent_cards_html(states: list[AgentState]) -> str:
    """Render 5-agent status cards. Two-color, strict white/black text."""
    cells = []
    for st in states:
        brand = AGENT_COLORS[st.agent]
        name = st.agent.capitalize()
        # Pulse only on the most demanding tones to avoid visual chatter.
        pulse_class = "pulse" if st.tone in ("critical", "warning") else ""

        # Status line styling per tone — all variants honour the
        # cream/plum + white/black contract.
        status_text = _html_escape(st.status)
        if st.tone == "critical":
            status_html = (
                f'<div class="{pulse_class}" style="display:inline-flex;'
                'align-items:center;padding:5px 11px;background:#381932;'
                'color:#FFFFFF;border-radius:999px;font-size:13px;'
                'font-weight:700;letter-spacing:0.2px;line-height:1.1;'
                f'align-self:flex-start;">{status_text}</div>'
            )
        elif st.tone == "warning":
            status_html = (
                f'<div class="{pulse_class}" style="display:inline-flex;'
                'align-items:center;padding:5px 11px;background:#FFFFFF;'
                'color:#000000;border:1.5px solid #381932;border-radius:999px;'
                'font-size:13px;font-weight:700;letter-spacing:0.2px;'
                f'line-height:1.1;align-self:flex-start;">{status_text}</div>'
            )
        elif st.tone == "safe":
            status_html = (
                '<div style="display:inline-flex;align-items:center;'
                'padding:5px 11px;background:#FFE8D2;color:#000000;'
                'border:1px solid rgba(56,25,50,0.30);border-radius:999px;'
                'font-size:13px;font-weight:700;letter-spacing:0.2px;'
                f'line-height:1.1;align-self:flex-start;">{status_text}</div>'
            )
        elif st.tone == "active":
            status_html = (
                '<div style="font-size:14px;font-weight:700;color:#000000;'
                f'line-height:1.25;letter-spacing:0.1px;">{status_text}</div>'
            )
        else:  # idle
            status_html = (
                '<div style="font-size:14px;font-weight:600;color:#000000;'
                'opacity:0.40;line-height:1.25;letter-spacing:0.1px;">'
                f'{status_text}</div>'
            )

        # Single-letter monogram in upper-right of each card — colorblind
        # users get shape+letter redundancy in addition to color encoding.
        monogram = name[0].upper()
        # Accessible state phrase, exposed to screen-readers via aria-label.
        accessible_state = f"{name} card, status: {st.status} ({st.tone}). {st.detail}"
        cells.append(
            f'<div class="agent-card agent-card-{st.agent} agent-card-tone-{st.tone}" '
            'role="article" '
            f'aria-label="{_html_escape(accessible_state)}" '
            f'style="background:{brand["soft"]};'
            'border:1px solid rgba(56,25,50,0.18);'
            f'border-top:3px solid {brand["accent"]};'
            'border-radius:12px;padding:14px 14px 16px;'
            'display:flex;flex-direction:column;gap:8px;min-height:138px;'
            'position:relative;">'
            # Monogram badge — colorblind-redundant identifier
            '<span style="position:absolute;top:8px;right:8px;'
            'font-family:JetBrains Mono, monospace;font-size:11px;font-weight:800;'
            'color:#FFFFFF;background:#381932;padding:2px 7px;border-radius:4px;'
            'letter-spacing:0.4px;" aria-hidden="true">'
            f'{monogram}</span>'
            # Header row
            '<div style="display:flex;align-items:center;gap:8px;font-size:10px;'
            'letter-spacing:1.6px;color:#000000;'
            'text-transform:uppercase;font-weight:800;">'
            '<span class="agent-emoji" aria-hidden="true" '
            'style="font-size:16px;line-height:1;">'
            f'{brand["icon"]}</span>{name}'
            "</div>"
            # Status line (already pre-rendered with proper contrast)
            f'{status_html}'
            # Detail line
            '<div style="font-size:12px;color:#000000;opacity:0.78;'
            'line-height:1.5;">'
            f'{_html_escape(st.detail)}</div>'
            "</div>"
        )
    return (
        '<div class="agent-grid" role="list" '
        'aria-label="Five Chakravyuh agents and their current state" '
        'style="display:grid;'
        "grid-template-columns:repeat(5, minmax(0, 1fr));"
        'gap:12px;margin:10px 0 18px;">'
        + "".join(cells)
        + "</div>"
    )


# ---------------------------------------------------------------------------
# Attack timeline — icon per turn
# ---------------------------------------------------------------------------


def _turn_icon(episode: ReplayedEpisode, turn: int) -> tuple[str, str, str]:
    """Return (icon, accent_color, tooltip_text) for one turn in the timeline."""
    # Map by turn role per env schedule:
    #   1,4 scammer  2,5 victim  3,6 analyzer  7 scammer(tx)  8 bank  9 final
    if turn in (1, 4):
        return ("🎭", AGENT_COLORS["scammer"]["accent"], f"Turn {turn} — Scammer acts")
    if turn in (2, 5):
        # Check if victim complied/refused/verified
        vmsg = next(
            (m for m in episode.chat_history if m.sender == "victim" and m.turn == turn),
            None,
        )
        if vmsg and "[REFUSED" in vmsg.text:
            return ("🙅", AGENT_COLORS["victim"]["accent"], f"Turn {turn} — Victim refused")
        if vmsg and "[CALLED" in vmsg.text:
            return ("📞", AGENT_COLORS["victim"]["accent"], f"Turn {turn} — Victim called bank")
        if vmsg and "[COMPLIED" in vmsg.text:
            return ("⚠️", AGENT_COLORS["victim"]["accent"], f"Turn {turn} — Victim complied")
        return ("💬", AGENT_COLORS["victim"]["accent"], f"Turn {turn} — Victim replied")
    if turn in (3, 6):
        snap = next(
            (s for s in episode.analyzer_snapshots if s.turn == turn), None
        )
        if snap and snap.score >= 0.7:
            return ("🚨", AGENT_COLORS["analyzer"]["accent"], f"Turn {turn} — Analyzer HIGH RISK {snap.score:.2f}")
        if snap and snap.score >= 0.4:
            return ("🔍", AGENT_COLORS["analyzer"]["accent"], f"Turn {turn} — Analyzer MEDIUM {snap.score:.2f}")
        return ("🔍", AGENT_COLORS["analyzer"]["accent"], f"Turn {turn} — Analyzer low")
    if turn == 7:
        return ("💰", AGENT_COLORS["scammer"]["accent"], "Turn 7 — Transaction requested")
    if turn == 8:
        snap = next(iter(episode.bank_snapshots), None)
        if snap and snap.decision == "freeze":
            return ("🛡️", AGENT_COLORS["bank"]["accent"], "Turn 8 — Bank FROZE")
        if snap and snap.decision == "flag":
            return ("🚩", AGENT_COLORS["bank"]["accent"], "Turn 8 — Bank flagged")
        return ("✓", AGENT_COLORS["bank"]["accent"], "Turn 8 — Bank approved")
    if turn == 9:
        # All turn-9 outcome icons use plum — they're all "decisive" turns.
        if episode.outcome.money_extracted:
            return ("💸", "#381932", "Turn 9 — Money extracted")
        if episode.outcome.bank_froze:
            return ("🔒", "#381932", "Turn 9 — Transaction blocked")
        return ("✅", "#381932", "Turn 9 — Outcome logged")
    return ("·", "rgba(56,25,50,0.40)", f"Turn {turn}")


def format_attack_timeline_html(
    episode: ReplayedEpisode, up_to_turn: int | None = None
) -> str:
    """Render a horizontal attack timeline — one icon per turn."""
    total = max(max_turn(episode), 9)  # always at least 9 turns
    cutoff = up_to_turn if up_to_turn is not None else total
    cells = []
    for t in range(1, total + 1):
        icon, color, tooltip = _turn_icon(episode, t)
        visible = t <= cutoff
        opacity = "1" if visible else "0.25"
        active_ring = (
            f"box-shadow:0 0 0 2px {color}, 0 2px 6px rgba(0,0,0,0.1);"
            if t == cutoff and visible
            else ""
        )
        # White circle on cream surface, plum 1.5px ring + plum icon.
        cells.append(
            f'<div title="{_html_escape(tooltip)}" '
            'class="timeline-step" '
            'style="display:flex;flex-direction:column;align-items:center;'
            f'gap:6px;opacity:{opacity};transition:opacity 0.3s ease;">'
            '<div style="width:36px;height:36px;border-radius:50%;'
            'background:#FFFFFF;'
            f'border:1.5px solid {color};'
            'display:flex;align-items:center;justify-content:center;'
            f'font-size:16px;color:{color};{active_ring}">'
            f"{icon}"
            "</div>"
            '<div style="font-size:10px;color:#000000;opacity:0.7;'
            'font-weight:700;letter-spacing:0.8px;">'
            f'T{t}</div>'
            "</div>"
        )
    return (
        '<div class="attack-timeline" '
        'style="display:flex;justify-content:space-between;align-items:flex-start;'
        'gap:6px;padding:14px 8px;max-width:680px;margin:0 auto;">'
        + "".join(cells)
        + "</div>"
    )
