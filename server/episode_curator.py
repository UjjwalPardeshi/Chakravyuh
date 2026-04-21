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
        seed=1,
        profile=VictimProfile.SENIOR,
        gullibility=1.5,
        outcome_kind="scripted_missed",
        description=(
            "Union Bank NRE-account KYC fake link. Scripted analyzer missed it "
            "(suspicion never crossed threshold). Money extracted. Demonstrates "
            "the gap that semantic LLM analysis closes on Day 2."
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
