"""Chakravyuh demo server — Gradio UI + replay curator."""

from server.episode_curator import (
    CURATED_EPISODES,
    CuratedEpisode,
    ReplayedEpisode,
    format_chat_html,
    outcome_badge,
    replay,
    replay_all,
)

__all__ = [
    "CURATED_EPISODES",
    "CuratedEpisode",
    "ReplayedEpisode",
    "format_chat_html",
    "outcome_badge",
    "replay",
    "replay_all",
]
