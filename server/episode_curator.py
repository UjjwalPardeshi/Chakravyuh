"""Episode curator: replays deterministic seeds to produce demo-ready episodes.

Separated from Gradio UI so it's testable without demo deps installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from chakravyuh_env import ChakravyuhEnv
from chakravyuh_env.schemas import ChatMessage, EpisodeOutcome, VictimProfile


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
class ReplayedEpisode:
    """Full result of replaying a curated episode."""

    label: str
    description: str
    seed: int
    profile: VictimProfile
    chat_history: list[ChatMessage]
    outcome: EpisodeOutcome
    analyzer_scores_per_turn: list[tuple[int, float, str]]
    # (turn, suspicion_score, explanation) for each analyzer call


def replay(episode: CuratedEpisode) -> ReplayedEpisode:
    """Replay a curated episode deterministically. Returns full trace.

    Identical inputs → identical outputs. This is the demo's contract.
    """
    env = ChakravyuhEnv(
        victim_profile=episode.profile,
        gullibility=episode.gullibility,
    )
    env.reset(seed=episode.seed)

    # Capture analyzer scores during each turn by intercepting the analyzer action
    analyzer_scores: list[tuple[int, float, str]] = []
    original_act = env.analyzer.act

    def capturing_act(obs):
        action = original_act(obs)
        if hasattr(action, "score"):
            analyzer_scores.append((obs.turn, action.score, action.explanation))
        return action

    env.analyzer.act = capturing_act  # type: ignore[method-assign]

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
        analyzer_scores_per_turn=analyzer_scores,
    )


def replay_all() -> list[ReplayedEpisode]:
    """Replay all curated episodes. Used for smoke testing."""
    return [replay(ep) for ep in CURATED_EPISODES]


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


def format_chat_html(chat: list[ChatMessage]) -> str:
    """Render chat as HTML for Gradio display."""
    rows = []
    for msg in chat:
        who = "Scammer" if msg.sender == "scammer" else "Victim"
        color = "#E85A4F" if msg.sender == "scammer" else "#4F81E8"
        bg = "#FEF2F1" if msg.sender == "scammer" else "#F1F5FE"
        rows.append(
            f'<div style="margin:8px 0;padding:12px;background:{bg};'
            f'border-left:4px solid {color};border-radius:4px;">'
            f'<b style="color:{color}">T{msg.turn} — {who}:</b> '
            f'{_html_escape(msg.text)}'
            f"</div>"
        )
    return "".join(rows) or '<i style="color:#888">No messages yet.</i>'


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
