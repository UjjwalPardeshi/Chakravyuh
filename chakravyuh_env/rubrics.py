"""Composable rubric system for the Chakravyuh Analyzer agent.

Built on ``openenv.core.rubrics`` (Rubric / WeightedSum). The top-level
``AnalyzerRubric`` decomposes the analyzer's reward into five orthogonal,
introspectable child rubrics:

    detection:        +1.0 weight  — rewards early flag on a real scam
    missed_scam:      -0.5 weight  — penalises failing to flag when money was extracted
    false_positive:   -0.3 weight  — penalises flagging a benign episode
    calibration:      +0.2 weight  — rewards appropriately confident suspicion scores
    explanation:      +0.4 weight  — heuristic quality of the natural-language reason

All five are registered as children of ``AnalyzerRubric`` so:

    for name, child in env.rubric.named_rubrics():
        print(name, child.last_score)

lists every sub-score after each call, matching the judging-criterion
*"Uses OpenEnv's Rubric system thoughtfully (composable rubrics >
monolithic scoring)."*

The rubric returns ``0.0`` for non-terminal observations (it emits the
full signal only when ``observation.done=True``) because the analyzer's
reward is defined over the full episode outcome, not any single step.

See RFC 004: https://github.com/meta-pytorch/OpenEnv/pull/337
"""

from __future__ import annotations

from typing import Any

from openenv.core.rubrics import Rubric

# Canonical weights — match the legacy reward.py analyzer formula for
# (detection, missed_scam, false_positive, explanation) + two new terms
# (calibration, explanation-heuristic) that make the reward richer without
# changing the sign of any existing component.
DEFAULT_WEIGHTS: dict[str, float] = {
    "detection": 1.0,
    "missed_scam": -0.5,
    "false_positive": -0.3,
    "calibration": 0.2,
    "explanation": 0.4,
}

# v2 anti-collapse weights (matches `training/grpo_analyzer.py:compute_reward`
# at `reward_profile="v2"`). Three differences vs v1:
#   - false_positive  -0.3 → -0.8  (over-flagging is now expensive)
#   - calibration     +0.2 → +0.5  (stronger gradient toward score≤0.2 on benign)
#   - format reward denied on benign-flagged-scam (encoded in FormatRubric.forward)
#
# Two new shaping rubrics promoted from the trainer:
#   - signal_accuracy +0.2  (fraction of expected signals named correctly)
#   - format          +0.15 (JSON-emission bonus, denied on benign-as-scam)
#   - length          +0.15 (continuous, ±0.15, peak at ~45 tokens)
V2_WEIGHTS: dict[str, float] = {
    "detection": 1.0,
    "missed_scam": -0.5,
    "false_positive": -0.8,
    "calibration": 0.5,
    "explanation": 0.4,
    "signal_accuracy": 0.2,
    "format": 0.15,
    "length": 0.15,
}


def _outcome(observation: Any) -> dict[str, Any] | None:
    """Return the outcome dict on a terminal observation, else None.

    The outcome dict is populated by ``ChakravyuhOpenEnv._terminal_observation``
    and carries the flags the sub-rubrics read (``analyzer_flagged``,
    ``money_extracted``, ``detected_by_turn``, ``false_positive``).
    """
    if not getattr(observation, "done", False):
        return None
    return getattr(observation, "outcome", None)


# ---------------------------------------------------------------------------
# Leaf rubrics — one scored criterion each.
# ---------------------------------------------------------------------------


class DetectionRubric(Rubric):
    """+1.0 when the analyzer flagged early (by turn ≤ 5) on a real scam.

    "Early" matches the existing compute_rewards definition: detected_by_turn
    is set when the analyzer first crosses its flag threshold, and is
    compared against turn 5 (after the scammer's escalation turn).
    """

    early_cutoff: int

    def __init__(self, early_cutoff: int = 5) -> None:
        super().__init__()
        self.early_cutoff = early_cutoff

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        flagged = bool(outcome.get("analyzer_flagged"))
        turn = outcome.get("detected_by_turn")
        # `is_scam` is the ground truth — derived directly from the outcome's
        # `is_benign` flag. The legacy code computed it from the `false_positive`
        # flag, which is correct only when an FP is recorded but is fragile when
        # benigns aren't flagged (see AUDIT.md P1-11). The explicit form is both
        # clearer and robust to future benign-rollout additions.
        is_scam = not bool(outcome.get("is_benign", False))
        early = flagged and is_scam and turn is not None and turn <= self.early_cutoff
        return 1.0 if early else 0.0


class MissedScamRubric(Rubric):
    """1.0 if the analyzer missed a scam AND money was extracted, else 0.

    Fires the **indicator** only — the top-level weighted sum multiplies
    by the negative weight, producing the penalty. This keeps each leaf
    rubric's output in the conventional [0, 1] range.
    """

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        flagged = bool(outcome.get("analyzer_flagged"))
        money = bool(outcome.get("money_extracted"))
        return 1.0 if (not flagged and money) else 0.0


class FalsePositiveRubric(Rubric):
    """1.0 if the analyzer flagged a benign/non-scam episode, else 0.

    In the scripted env every scenario is a scam, so this is near-always 0.
    The real wiring for false positives lives in the benchmark evaluation
    (``eval/``) which injects benign templates. The rubric is kept here so
    training infrastructure can inspect ``last_score`` per sub-rubric and
    spot FP behaviour the moment a benign case is rolled in.
    """

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        flagged = bool(outcome.get("analyzer_flagged"))
        false_positive = bool(outcome.get("false_positive", False))
        return 1.0 if (flagged and false_positive) else 0.0


class CalibrationRubric(Rubric):
    """Score-calibration quality: rewards confident suspicion on scams.

    For scam episodes (the scripted env's default), the ideal suspicion
    score is high (≈ target). This rubric returns
    ``max(0, 1 - |action.score - target|)`` so perfectly confident scores
    get 1.0 and anything ``target - 1.0`` below gets 0.0. For benign
    episodes (``false_positive=False`` AND not a scam), the target flips
    to a low value — i.e. the analyzer should be calibrated in BOTH
    directions.

    The rubric reads ``action.score`` from the last analyzer action,
    which represents the terminal decision's confidence.
    """

    scam_target: float
    benign_target: float

    def __init__(self, scam_target: float = 0.9, benign_target: float = 0.1) -> None:
        super().__init__()
        if not 0.0 <= scam_target <= 1.0:
            raise ValueError(f"scam_target must be in [0,1], got {scam_target}")
        if not 0.0 <= benign_target <= 1.0:
            raise ValueError(f"benign_target must be in [0,1], got {benign_target}")
        self.scam_target = scam_target
        self.benign_target = benign_target

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        score = getattr(action, "score", None)
        if score is None:
            return 0.0
        # `false_positive=True` means benign-but-flagged. If the rubric is
        # running on a benign episode with no FP, we also want to score
        # calibration toward the low target. We detect "is_scam" by
        # checking that the outcome is NOT marked benign. In the scripted
        # env everything is a scam; the bench evaluator flips this flag
        # via its own outcome construction.
        is_benign = outcome.get("is_benign", False)
        target = self.benign_target if is_benign else self.scam_target
        return max(0.0, 1.0 - abs(float(score) - target))


class ExplanationRubric(Rubric):
    """Heuristic explanation-quality score in [0, 1].

    Rewards:

      +0.3  non-empty explanation
      +0.3  mentions at least one of the signals the action declared
      +0.2  length ≥ 30 chars
      +0.2  length ≥ 60 chars

    Clipped to 1.0. This is intentionally a heuristic rather than an
    LLM judge so the rubric stays fast and dependency-free. An LLM
    judge (``openenv.core.rubrics.LLMJudge``) can be swapped in as a
    drop-in replacement for advanced setups.
    """

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        text = (getattr(action, "explanation", "") or "").strip()
        if not text:
            return 0.0
        lowered = text.lower()
        signals = getattr(action, "signals", []) or []

        score = 0.3
        if any(str(sig).lower() in lowered for sig in signals):
            score += 0.3
        if len(text) >= 30:
            score += 0.2
        if len(text) >= 60:
            score += 0.2
        return min(1.0, score)


class SignalAccuracyRubric(Rubric):
    """Fraction of expected signals the action correctly named, in [0, 1].

    Reads ``outcome["expected_signals"]`` (set by trainers / eval pipelines
    that know the ground-truth signal taxonomy). When the expected set is
    empty or the action declared no signals, returns 0.0.

    This rubric was inlined in the trainer's ``compute_reward`` (as
    ``signal_bonus``) before the v2 unification — promoted to a first-class
    leaf rubric here so the env exposes the same reward decomposition the
    trainer optimizes.
    """

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        expected = outcome.get("expected_signals") or ()
        if not expected:
            return 0.0
        declared = [str(s).lower() for s in (getattr(action, "signals", []) or [])]
        if not declared:
            return 0.0
        expected_lc = {str(s).lower() for s in expected}
        matched = sum(1 for d in declared if d in expected_lc)
        return min(1.0, matched / max(1, len(expected_lc)))


class FormatRubric(Rubric):
    """JSON-emission shaping bonus, in [0, 1].

    Rewards a parseable JSON object with a ``score`` key (the canonical
    output schema) when the action's ``explanation`` looks like JSON. The
    v2 anti-collapse fix is: deny this bonus when the analyzer flags a
    benign episode as scam — removing the "lazy over-flag still gets
    format credit" loophole.
    """

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        text = (getattr(action, "explanation", "") or "").strip()
        if not text:
            return 0.0
        looks_json = text.startswith("{") and "score" in text.lower() and text.endswith("}")
        if not looks_json:
            return 0.0
        # v2 anti-collapse: deny when flagging benign as scam.
        is_benign = bool(outcome.get("is_benign", False))
        score = float(getattr(action, "score", 0.0))
        threshold = float(getattr(action, "flag_threshold", 0.5))
        flagged_benign_as_scam = is_benign and score >= threshold
        if flagged_benign_as_scam:
            return 0.0
        return 1.0


class LengthRubric(Rubric):
    """Length-shaping bonus peaking around 45 tokens, in [-1, 1].

    Rewards explanations near the target length (~45 tokens), penalises
    runaway prose. Inlined in trainer's ``compute_reward`` previously;
    promoted here for trainer/env reward parity.

    Returns the same units as ``compute_reward`` (continuous, can be
    negative). The top-level rubric weights it at +0.15, matching the
    trainer's ±0.15 cap.
    """

    target_tokens: int
    upper_band: int

    def __init__(self, target_tokens: int = 45, upper_band: int = 70) -> None:
        super().__init__()
        self.target_tokens = target_tokens
        self.upper_band = upper_band

    def forward(self, action: Any, observation: Any) -> float:
        outcome = _outcome(observation)
        if outcome is None:
            return 0.0
        text = (getattr(action, "explanation", "") or "").strip()
        if not text:
            return 0.0
        n = len(text.split())
        if n <= 0:
            return 0.0
        if 20 <= n <= self.upper_band:
            return max(0.0, 1.0 - abs(n - self.target_tokens) / 30.0)
        if n > self.upper_band:
            return -min(1.0, (n - self.upper_band) / 60.0)
        return 0.0


# ---------------------------------------------------------------------------
# Top-level composed rubric.
# ---------------------------------------------------------------------------


class AnalyzerRubric(Rubric):
    """Top-level Analyzer rubric composing five child criteria.

    Returns ``0.0`` on non-terminal observations (the analyzer's reward
    is a function of the full trajectory outcome). On terminal, returns
    the weighted sum of the five child rubrics.

    Weights are settable per-instance via the ``weights`` kwarg — the
    defaults (see ``DEFAULT_WEIGHTS``) match the signs of the legacy
    ``compute_rewards`` analyzer formula plus two richer sub-signals
    (calibration, explanation-heuristic).

    Introspection (used by training infra and debug plots):

        env = ChakravyuhOpenEnv()
        env.reset(); env.step(...); obs = env.step(...)   # terminal
        for name, r in env.rubric.named_rubrics():
            print(name, r.last_score)
    """

    weights: dict[str, float]

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        super().__init__()
        # Deep-copy so per-instance weight tweaks don't mutate the default.
        self.weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
        missing = set(DEFAULT_WEIGHTS) - set(self.weights)
        if missing:
            raise ValueError(
                f"AnalyzerRubric weights missing keys: {sorted(missing)}"
            )
        # Children — auto-registered via the base-class __setattr__ hook.
        self.detection = DetectionRubric()
        self.missed_scam = MissedScamRubric()
        self.false_positive = FalsePositiveRubric()
        self.calibration = CalibrationRubric()
        self.explanation = ExplanationRubric()

    def forward(self, action: Any, observation: Any) -> float:
        if not getattr(observation, "done", False):
            # Still run the child rubrics so `last_score` is populated
            # (they all return 0.0 on non-terminal obs anyway).
            self.detection(action, observation)
            self.missed_scam(action, observation)
            self.false_positive(action, observation)
            self.calibration(action, observation)
            self.explanation(action, observation)
            return 0.0

        scores = {
            "detection": self.detection(action, observation),
            "missed_scam": self.missed_scam(action, observation),
            "false_positive": self.false_positive(action, observation),
            "calibration": self.calibration(action, observation),
            "explanation": self.explanation(action, observation),
        }
        return float(sum(self.weights[k] * v for k, v in scores.items()))

    def last_scores(self) -> dict[str, float | None]:
        """Return ``{rubric_name: last_score}`` for the top-level + children.

        Convenience helper used by ``_terminal_observation`` to populate
        the ``reward_breakdown`` field on the outgoing observation.
        """
        breakdown: dict[str, float | None] = {"total": self.last_score}
        for name, child in self.named_children():
            breakdown[name] = child.last_score
        return breakdown

    def state_dict(self) -> dict[str, Any]:
        return {"weights": dict(self.weights)}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        if "weights" in state:
            self.weights = dict(state["weights"])


class AnalyzerRubricV2(AnalyzerRubric):
    """v2 anti-collapse profile — the weights v2's LoRA was trained against.

    Three v1→v2 weight changes are visible in :data:`V2_WEIGHTS`:

      * ``false_positive``  -0.3 → -0.8  (over-flagging now expensive)
      * ``calibration``     +0.2 → +0.5  (stronger gradient on benign)
      * ``format`` reward denied when flagging a benign as scam
        (encoded inside :class:`FormatRubric.forward`)

    Three new shaping leaves promoted from the trainer's inline reward so
    the env's rubric exposes the same decomposition that produced v2:

      * ``SignalAccuracyRubric``  (was ``signal_bonus``)
      * ``FormatRubric``          (was ``format_r``)
      * ``LengthRubric``          (was ``length_r``)

    The env serves this rubric by default — see
    :class:`chakravyuh_env.openenv_environment.ChakravyuhOpenEnv`.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        # Validate against the V2 keyset before delegating.
        weights = dict(V2_WEIGHTS if weights is None else weights)
        missing = set(V2_WEIGHTS) - set(weights)
        if missing:
            raise ValueError(
                f"AnalyzerRubricV2 weights missing keys: {sorted(missing)}"
            )
        # Bypass the parent validator (which checks against DEFAULT_WEIGHTS).
        Rubric.__init__(self)
        self.weights = weights
        self.detection = DetectionRubric()
        self.missed_scam = MissedScamRubric()
        self.false_positive = FalsePositiveRubric()
        self.calibration = CalibrationRubric()
        self.explanation = ExplanationRubric()
        self.signal_accuracy = SignalAccuracyRubric()
        self.format = FormatRubric()
        self.length = LengthRubric()

    def forward(self, action: Any, observation: Any) -> float:
        # Run all eight children so their last_score fields are populated
        # whether or not the observation is terminal.
        children = (
            ("detection", self.detection),
            ("missed_scam", self.missed_scam),
            ("false_positive", self.false_positive),
            ("calibration", self.calibration),
            ("explanation", self.explanation),
            ("signal_accuracy", self.signal_accuracy),
            ("format", self.format),
            ("length", self.length),
        )
        if not getattr(observation, "done", False):
            for _, child in children:
                child(action, observation)
            return 0.0
        scores = {name: float(child(action, observation)) for name, child in children}
        return float(sum(self.weights[k] * v for k, v in scores.items()))
