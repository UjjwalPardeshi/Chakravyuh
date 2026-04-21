"""Novelty scorer for Scammer attack sequences.

Implements the formal novelty metric from CHAKRAVYUH_WIN_PLAN.md Part 3:

    novelty_score(attack_tau, history_buffer, threshold=0.35) ∈ [0, 1]

Uses `sentence-transformers/all-MiniLM-L6-v2` (local, ~90 MB) to embed the
scammer's flattened message sequence and computes cosine distance to the
nearest attack in the last 500 episodes.

Q&A-proof: "How do you measure novelty?" → "Cosine distance > 0.35 in
MiniLM embedding space against a 500-attack sliding window."

Lazy-loads the model so importing this module is fast; the model is only
loaded on first `score()` call.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable

import numpy as np


class NoveltyScorer:
    def __init__(
        self,
        threshold: float = 0.35,
        history_size: int = 500,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.threshold = threshold
        self.history_size = history_size
        self.model_name = model_name
        self._model = None
        self._history: deque[np.ndarray] = deque(maxlen=history_size)

    def _ensure_model(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

    def _embed(self, text: str) -> np.ndarray:
        self._ensure_model()
        assert self._model is not None
        vec = self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vec.astype(np.float32)

    def score(self, attack_sequence: Iterable[str]) -> float:
        joined = " ".join(attack_sequence).strip()
        if not joined:
            return 0.0
        emb = self._embed(joined)
        if not self._history:
            self._history.append(emb)
            return 1.0  # first attack is maximally novel

        # Cosine distance = 1 - cosine similarity. Embeddings are normalized
        # so dot product = cosine similarity.
        sims = np.array([float(np.dot(emb, h)) for h in self._history])
        min_dist = 1.0 - float(sims.max())
        self._history.append(emb)

        # Scale into [0, 1] with the threshold as lower bound
        raw = (min_dist - self.threshold) / max(1e-6, 1.0 - self.threshold)
        return max(0.0, min(1.0, raw))


class DummyNoveltyScorer:
    """Fallback when sentence-transformers is not installed.

    Returns a deterministic pseudo-novelty based on sequence length and a
    hash, so Day-1 smoke tests run without the heavy model download.
    """

    def __init__(self, **_: object) -> None:
        self._seen: set[str] = set()

    def score(self, attack_sequence: Iterable[str]) -> float:
        joined = " ".join(attack_sequence).strip()
        if not joined:
            return 0.0
        if joined in self._seen:
            return 0.0
        self._seen.add(joined)
        # Longer, more-detailed attacks get a small novelty bonus, bounded.
        return min(1.0, len(joined) / 1000.0 + 0.3)


def build_novelty_scorer(use_embeddings: bool = True, **kwargs: object) -> NoveltyScorer | DummyNoveltyScorer:
    """Factory. If sentence-transformers is unavailable, falls back to dummy."""
    if not use_embeddings:
        return DummyNoveltyScorer()
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return DummyNoveltyScorer()
    return NoveltyScorer(**kwargs)  # type: ignore[arg-type]
