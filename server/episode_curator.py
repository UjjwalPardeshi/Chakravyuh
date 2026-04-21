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

# Patterns to highlight inside scammer messages. Ordered by priority:
# highest-risk categories highlighted most prominently.
_HIGHLIGHT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    # (category, color, regex)
    (
        "info",
        "#C92A2A",
        r"\b(otp|aadhaar|adhar|pan|cvv|pin|upi\s+pin|card\s+number|bank\s+details)\b",
    ),
    (
        "urgency",
        "#E67E22",
        r"\b(urgent|urgently|immediately|now|expires?|expired|minutes?|hours?\s+left|within\s+\d+|last\s+chance|hurry|act\s+fast|deadline|suspended|block(?:ed)?)\b",
    ),
    (
        "impersonation",
        "#8E44AD",
        r"\b(sbi|hdfc|icici|axis\s+bank|yes\s+bank|kotak|canara|pnb|rbi|uidai|income\s+tax|epfo|cbi|police|cyber\s+cell|customer\s+care|fraud\s+team|manager|officer)\b",
    ),
)


def _highlight_keywords(text: str) -> str:
    """Wrap keyword matches in colored <mark> tags. HTML-safe."""
    escaped = _html_escape(text)
    # Also highlight suspicious URLs
    def _url_replacer(match: re.Match) -> str:
        url = match.group(0)
        low = url.lower()
        if any(tld in low for tld in _SUSPICIOUS_TLDS) or any(
            short in low for short in _URL_SHORTENERS
        ):
            return (
                f'<mark style="background:#FFE4B3;color:#C92A2A;'
                f'padding:2px 4px;border-radius:3px;font-weight:600;">'
                f"{url}</mark>"
            )
        return url

    escaped = _URL_PATTERN.sub(_url_replacer, escaped)
    for _, color, pattern in _HIGHLIGHT_PATTERNS:
        escaped = re.sub(
            pattern,
            lambda m, c=color: (
                f'<mark style="background:#FFF3CD;color:{c};'
                f'padding:1px 4px;border-radius:3px;font-weight:600;">'
                f"{m.group(0)}</mark>"
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
        accent = "#E85A4F" if msg.sender == "scammer" else "#4F81E8"
        bg = "#FEF2F1" if msg.sender == "scammer" else "#F1F5FE"
        text_color = "#1a1a1a"
        body = (
            _highlight_keywords(msg.text)
            if (highlight and msg.sender == "scammer")
            else _html_escape(msg.text)
        )
        rows.append(
            f'<div style="margin:8px 0;padding:12px;background:{bg};'
            f'border-left:4px solid {accent};border-radius:4px;'
            f'color:{text_color};font-size:14px;line-height:1.55;">'
            f'<b style="color:{accent}">T{msg.turn} — {who}:</b> '
            f'<span style="color:{text_color}">{body}</span>'
            f"</div>"
        )
    return "".join(rows) or '<i style="color:#888">No messages yet.</i>'


# -- (A) Suspicion timeline --------------------------------------------------


def format_suspicion_timeline(
    snapshots: list[AnalyzerSnapshot], up_to_turn: int | None = None
) -> str:
    """Render a mini-timeline of suspicion scores across analyzer turns."""
    visible = [s for s in snapshots if up_to_turn is None or s.turn <= up_to_turn]
    if not visible:
        return (
            '<div style="padding:12px;color:#888;font-style:italic;font-size:13px;">'
            "Analyzer has not evaluated yet."
            "</div>"
        )
    rows = ['<div style="padding:8px 4px;">']
    for snap in visible:
        pct = int(snap.score * 100)
        # Color by severity
        if snap.score >= 0.70:
            bar_color = "#E03131"
        elif snap.score >= 0.40:
            bar_color = "#E67E22"
        else:
            bar_color = "#2B8A3E"
        rows.append(
            f'<div style="margin:6px 0;font-size:13px;">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="color:#666;min-width:42px;font-weight:600;">T{snap.turn}</span>'
            f'<div style="flex:1;background:#eee;border-radius:3px;height:16px;position:relative;overflow:hidden;">'
            f'<div style="background:{bar_color};width:{pct}%;height:100%;"></div>'
            f'</div>'
            f'<span style="color:{bar_color};font-weight:700;min-width:44px;text-align:right;">{snap.score:.2f}</span>'
            f'</div>'
            f'</div>'
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
            '<div style="padding:16px;border:1px dashed #ccc;border-radius:6px;'
            'color:#888;font-size:13px;text-align:center;">'
            "Bank Monitor inactive — no transaction attempted yet."
            "</div>"
        )

    # Latest bank decision (or pending)
    if visible:
        latest = visible[-1]
        decision_color = {
            "approve": ("#2B8A3E", "#E8F6E9", "APPROVED"),
            "flag": ("#E67E22", "#FFF9DB", "FLAGGED"),
            "freeze": ("#C92A2A", "#FDECEA", "FROZEN"),
        }[latest.decision]
        fg, bg, label = decision_color
        tx = transaction
        rows = [
            f'<div style="background:{bg};border-left:4px solid {fg};'
            f'border-radius:4px;padding:14px;">',
            f'<div style="font-size:12px;letter-spacing:1px;color:#666;'
            f'text-transform:uppercase;margin-bottom:8px;">Bank Monitor · T{latest.turn}</div>',
            f'<div style="font-size:22px;font-weight:800;color:{fg};'
            f'margin-bottom:8px;">{label}</div>',
        ]
        if tx is not None:
            rows.append(
                f'<div style="color:#333;font-size:13px;line-height:1.7;">'
                f'<b>Amount:</b> ₹{tx.amount:,.0f}<br>'
                f'<b>Receiver:</b> {"🆕 NEW PAYEE" if tx.receiver_new else "Known"}<br>'
                f'<b>Frequency (24h):</b> {tx.frequency_24h} txns<br>'
                f'<b>Reason:</b> {_html_escape(latest.reason)}'
                f"</div>"
            )
        rows.append("</div>")
        return "".join(rows)

    # Pending — tx exists but bank hasn't acted yet
    return (
        '<div style="padding:14px;border:1px solid #ddd;border-radius:4px;'
        'color:#666;font-size:13px;">'
        f"Transaction pending bank review: ₹{transaction.amount:,.0f}"
        f" to {'new' if transaction.receiver_new else 'known'} payee."
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

# Per-agent brand colors (ACCESSIBLE on both light + dark backgrounds)
AGENT_COLORS: dict[str, dict[str, str]] = {
    "scammer":   {"accent": "#E85A4F", "soft": "rgba(232, 90, 79, 0.12)",  "icon": "🎭"},
    "victim":    {"accent": "#4F81E8", "soft": "rgba(79, 129, 232, 0.12)", "icon": "👤"},
    "analyzer":  {"accent": "#8E44AD", "soft": "rgba(142, 68, 173, 0.12)", "icon": "🔍"},
    "bank":      {"accent": "#2B8A3E", "soft": "rgba(43, 138, 62, 0.12)",  "icon": "🏦"},
    "regulator": {"accent": "#E67E22", "soft": "rgba(230, 126, 34, 0.12)", "icon": "📜"},
}


@dataclass(frozen=True)
class AgentState:
    """Snapshot of one agent's state at a specific turn."""

    agent: Literal["scammer", "victim", "analyzer", "bank", "regulator"]
    status: str   # "Attacking", "Complied", "HIGH RISK", etc.
    detail: str   # 1-line description
    tone: Literal["idle", "active", "warning", "critical", "safe"]


_TONE_COLOR: dict[str, str] = {
    "idle":     "#888",
    "active":   "#4F81E8",
    "warning":  "#E67E22",
    "critical": "#C92A2A",
    "safe":     "#2B8A3E",
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
    """Render 5-agent status cards as a horizontal grid."""
    cells = []
    for st in states:
        brand = AGENT_COLORS[st.agent]
        tone_color = _TONE_COLOR[st.tone]
        name = st.agent.capitalize()
        # Tone dot — small pulsing circle that signals "live"
        pulse = "pulse" if st.tone in ("critical", "warning") else ""
        cells.append(
            f'<div class="agent-card agent-card-{st.agent}" '
            f'style="background:{brand["soft"]};'
            f'border-top:3px solid {brand["accent"]};'
            f'border-radius:10px;padding:14px 12px;'
            f'display:flex;flex-direction:column;gap:6px;min-height:130px;">'
            # Header row
            f'<div style="display:flex;align-items:center;gap:6px;font-size:12px;'
            f'letter-spacing:1px;color:var(--body-text-color-subdued, #888);'
            f'text-transform:uppercase;font-weight:700;">'
            f'<span style="font-size:18px;">{brand["icon"]}</span>'
            f"{name}"
            f"</div>"
            # Status line
            f'<div class="{pulse}" '
            f'style="font-size:15px;font-weight:700;color:{tone_color};'
            f'line-height:1.2;">{_html_escape(st.status)}</div>'
            # Detail
            f'<div style="font-size:12px;color:var(--body-text-color, #333);'
            f'line-height:1.35;opacity:0.78;">{_html_escape(st.detail)}</div>'
            f"</div>"
        )
    return (
        '<div class="agent-grid" style="display:grid;'
        "grid-template-columns:repeat(5, minmax(0, 1fr));"
        'gap:10px;margin:8px 0 16px;">'
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
        if episode.outcome.money_extracted:
            return ("💸", "#C92A2A", "Turn 9 — Money extracted")
        if episode.outcome.bank_froze:
            return ("🔒", "#2B8A3E", "Turn 9 — Transaction blocked")
        return ("✅", "#2B8A3E", "Turn 9 — Outcome logged")
    return ("·", "#888", f"Turn {turn}")


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
        cells.append(
            f'<div title="{_html_escape(tooltip)}" '
            f'class="timeline-step" '
            f'style="display:flex;flex-direction:column;align-items:center;'
            f"gap:4px;opacity:{opacity};transition:opacity 0.3s ease;\">"
            f'<div style="width:34px;height:34px;border-radius:50%;'
            f"background:{color}20;border:2px solid {color};"
            f"display:flex;align-items:center;justify-content:center;"
            f'font-size:16px;{active_ring}">'
            f"{icon}"
            f"</div>"
            f'<div style="font-size:10px;color:var(--body-text-color-subdued, #888);'
            f'font-weight:600;">T{t}</div>'
            f"</div>"
        )
    return (
        '<div class="attack-timeline" '
        'style="display:flex;justify-content:space-between;align-items:flex-start;'
        'gap:4px;padding:12px 4px;max-width:640px;margin:0 auto;">'
        + "".join(cells)
        + "</div>"
    )
