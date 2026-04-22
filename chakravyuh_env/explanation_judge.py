"""Explanation Quality Judge — Llama-3-70B via Groq free tier.

Scores an analyzer's plain-English explanation on 3 dimensions
(CHAKRAVYUH_WIN_PLAN.md Part 3, Explanation Quality Score):

  1. Factual grounding   (0.0–0.4): Cites actual signals in the conversation?
  2. Interpretability    (0.0–0.3): Understandable in <2 sentences?
  3. Actionability       (0.0–0.3): Suggests what the user should do?

Total: [0.0, 1.0]. Plugs into analyzer + bank reward (Part 3).

Why Groq: Llama-3-70B is essentially free on Groq's free tier
(14,400 requests/day, 30 req/min). One call per episode = ~$0.002.

Fallback: MockExplanationJudge returns deterministic heuristic scores so
training loops and tests run without Groq.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("chakravyuh.judge")


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# Using 8B instead of 70B: separate TPD bucket on Groq free tier
# (70B: 100k TPD, 8B: 500k TPD) and much faster responses.
# Scoring quality drops slightly but remains useful for GRPO reward signal.
DEFAULT_JUDGE_MODEL = "llama-3.1-8b-instant"


_JUDGE_SYSTEM_PROMPT = """You grade fraud-detection explanations on 3 axes. Output strict JSON only.

Axes:
  factual_grounding  [0.0–0.4]: Does the explanation cite signals actually present in the message (OTP ask, urgency, impersonation, suspicious link)?
  interpretability   [0.0–0.3]: Is it understandable in <2 sentences, no jargon?
  actionability     [0.0–0.3]: Does it suggest what the user should do?

Return JSON:
{"factual": <float>, "interpretability": <float>, "actionability": <float>, "reason": <1-sentence reason>}"""


_JUDGE_USER_TEMPLATE = """Message: "{message}"
Analyzer's explanation: "{explanation}"

Score the explanation."""


@dataclass(frozen=True)
class ExplanationScore:
    factual: float       # 0–0.4
    interpretability: float  # 0–0.3
    actionability: float     # 0–0.3
    reason: str
    total: float             # 0–1.0 = sum of the three

    @staticmethod
    def from_parts(
        factual: float, interpretability: float, actionability: float, reason: str = ""
    ) -> "ExplanationScore":
        f = max(0.0, min(0.4, factual))
        i = max(0.0, min(0.3, interpretability))
        a = max(0.0, min(0.3, actionability))
        return ExplanationScore(
            factual=round(f, 3),
            interpretability=round(i, 3),
            actionability=round(a, 3),
            reason=reason,
            total=round(f + i + a, 3),
        )


class ExplanationJudge:
    """Groq-backed (Llama-3-70B) explanation quality judge.

    The `groq` Python package is not required; we use the OpenAI-compatible
    HTTP endpoint via the `openai` package with `base_url=` set. This keeps
    dependencies light — `openai` is the one SDK covering both.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_JUDGE_MODEL,
        base_url: str = GROQ_BASE_URL,
        timeout: float = 15.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Any = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Either set the env var or pass api_key."
            )
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError(
                "openai package not installed. "
                "Run `pip install openai>=1.0` to enable ExplanationJudge."
            ) from e
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    # ---- core scoring ----

    def score(self, message: str, explanation: str) -> ExplanationScore:
        """Score a single explanation. Raises on non-recoverable errors."""
        self._ensure_client()
        assert self._client is not None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": _JUDGE_USER_TEMPLATE.format(
                                message=message[:500],
                                explanation=explanation[:500],
                            ),
                        },
                    ],
                    max_tokens=200,
                    temperature=0.0,
                )
                raw = response.choices[0].message.content or ""
                return parse_judge_response(raw)
            except Exception as e:  # noqa: BLE001
                if attempt >= self.max_retries:
                    logger.warning("Judge failed after %d attempts: %s", attempt + 1, e)
                    return ExplanationScore.from_parts(0.0, 0.0, 0.0, reason=f"error: {e}")
                time.sleep(0.5 * (attempt + 1))
        return ExplanationScore.from_parts(0.0, 0.0, 0.0, reason="unreachable")

    def batch_score(
        self, items: list[tuple[str, str]]
    ) -> list[ExplanationScore]:
        """Score a batch sequentially. For large batches, build async later."""
        return [self.score(msg, expl) for msg, expl in items]


# ---------------------------------------------------------------------------
# Mock judge — for tests + local dev without Groq
# ---------------------------------------------------------------------------


class MockExplanationJudge:
    """Deterministic heuristic judge. Does not call any API."""

    def score(self, message: str, explanation: str) -> ExplanationScore:
        # Factual: reward if explanation overlaps with message vocab
        msg_words = set(re.findall(r"\w+", message.lower()))
        exp_words = set(re.findall(r"\w+", explanation.lower()))
        overlap = len(msg_words & exp_words) / max(1, len(exp_words))
        factual = min(0.4, 0.1 + 0.5 * overlap)

        # Interpretability: short + no jargon = good
        word_count = len(explanation.split())
        if 4 <= word_count <= 30:
            interp = 0.3
        elif word_count < 50:
            interp = 0.2
        else:
            interp = 0.1

        # Actionability: reward if common action verbs appear
        action_verbs = [
            "do not", "don't", "block", "refuse", "call bank", "verify",
            "avoid", "report", "ignore", "hang up",
        ]
        action_present = any(v in explanation.lower() for v in action_verbs)
        actionability = 0.25 if action_present else 0.10

        return ExplanationScore.from_parts(
            factual, interp, actionability,
            reason="mock heuristic score",
        )

    def batch_score(
        self, items: list[tuple[str, str]]
    ) -> list[ExplanationScore]:
        return [self.score(m, e) for m, e in items]


# ---------------------------------------------------------------------------
# Parser — tested without API access
# ---------------------------------------------------------------------------


_JSON_OBJECT = re.compile(r"\{[^{}]*\}", re.DOTALL)


def parse_judge_response(raw: str) -> ExplanationScore:
    """Parse Llama's JSON output into an ExplanationScore. Forgiving."""
    try:
        m = _JSON_OBJECT.search(raw)
        if m:
            data = json.loads(m.group(0))
            return ExplanationScore.from_parts(
                factual=float(data.get("factual", 0.0)),
                interpretability=float(data.get("interpretability", 0.0)),
                actionability=float(data.get("actionability", 0.0)),
                reason=str(data.get("reason", ""))[:200],
            )
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback — extract three numbers
    nums = re.findall(r"[0-9]*\.?[0-9]+", raw)
    if len(nums) >= 3:
        try:
            return ExplanationScore.from_parts(
                factual=float(nums[0]),
                interpretability=float(nums[1]),
                actionability=float(nums[2]),
                reason=f"parser fallback: {raw[:80]}",
            )
        except ValueError:
            pass
    return ExplanationScore.from_parts(0.0, 0.0, 0.0, reason="unparseable response")


def build_judge(mock: bool = False) -> ExplanationJudge | MockExplanationJudge:
    """Factory: returns MockExplanationJudge if `mock=True` OR Groq key missing."""
    if mock or not os.environ.get("GROQ_API_KEY"):
        return MockExplanationJudge()
    return ExplanationJudge()
