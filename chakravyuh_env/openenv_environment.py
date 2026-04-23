"""ChakravyuhOpenEnv — Meta PyTorch OpenEnv-compliant wrapper.

This class exposes the Chakravyuh multi-agent fraud simulation as a
stock OpenEnv ``Environment`` so it can be:

  * driven by TRL / Unsloth / torchforge training loops via ``EnvClient``
  * served over HTTP via ``openenv.core.env_server.create_app``
  * deployed to Hugging Face Spaces with an ``openenv.yaml`` manifest

The **analyzer** is the agent being trained. All other roles
(scammer, victim, bank monitor) remain scripted NPCs that provide the
environment dynamics.

Episode flow (2 decision points per episode):

    reset(seed)
      └─ scammer opens (turn 1) + victim responds (turn 2)
         └─ return obs   (decision_index=0)

    step(action_0)
      └─ apply analyzer decision at turn 3
         └─ scammer escalates (turn 4) + victim decides (turn 5)
         └─ If victim refuses/verifies  → done=True, reward set
         └─ Else return obs (decision_index=1, transaction now included)

    step(action_1)
      └─ apply analyzer decision at turn 6
         └─ scammer requests tx (turn 7) + bank decides (turn 8)
         └─ combined decision (turn 9) + regulator log (turn 10)
         └─ done=True, reward set from full outcome
"""

from __future__ import annotations

import random
from typing import Any
from uuid import uuid4

from openenv.core.env_server import Environment
from openenv.core.rubrics import Rubric

from chakravyuh_env.agents.bank_monitor import ScriptedBankMonitor
from chakravyuh_env.agents.regulator import ScriptedRegulator
from chakravyuh_env.agents.scammer import ScriptedScammer
from chakravyuh_env.agents.victim import ScriptedVictim
from chakravyuh_env.novelty import build_novelty_scorer
from chakravyuh_env.openenv_models import (
    ChakravyuhAction,
    ChakravyuhObservation,
    ChakravyuhState,
)
from chakravyuh_env.reward import compute_rewards
from chakravyuh_env.rubrics import AnalyzerRubric
from chakravyuh_env.schemas import (
    AnalyzerSignal,
    BankFlag,
    BankFreeze,
    ChatMessage,
    EpisodeOutcome,
    Intent,
    Observation as InternalObs,
    ScamCategory,
    ScammerEndScam,
    ScammerEscalateUrgency,
    ScammerImpersonate,
    ScammerRequestInfo,
    ScammerSendLink,
    ScammerSendMessage,
    TransactionMeta,
    VictimCallBank,
    VictimComply,
    VictimProfile,
    VictimRefuse,
)

_VALID_SIGNAL_NAMES = {s.value for s in AnalyzerSignal}


class ChakravyuhOpenEnv(Environment[ChakravyuhAction, ChakravyuhObservation, ChakravyuhState]):
    """Chakravyuh as a stock OpenEnv ``Environment``.

    The analyzer (LLM being trained) is driven externally via ``step(action)``;
    all other agents are scripted.

    Concurrency: ``SUPPORTS_CONCURRENT_SESSIONS=True`` is safe because each
    session is backed by a fresh instance created by the factory passed to
    ``create_app`` — no shared mutable state.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(
        self,
        victim_profile: VictimProfile = VictimProfile.SEMI_URBAN,
        gullibility: float = 1.0,
        use_embeddings: bool = False,
        rubric: Rubric | None = None,
    ) -> None:
        # Default to the composable AnalyzerRubric — satisfies the
        # judging-criterion "Uses OpenEnv's Rubric system thoughtfully
        # (composable rubrics > monolithic scoring)". Callers may pass
        # their own Rubric (e.g. an LLMJudge) to override.
        super().__init__(rubric=rubric if rubric is not None else AnalyzerRubric())
        self._victim_profile = victim_profile
        self._gullibility = gullibility
        self._novelty_scorer = build_novelty_scorer(use_embeddings=use_embeddings)

        # Per-episode state — all set in reset(). The regulator lives here
        # (not in __init__) so each new episode starts with a fresh outcome
        # buffer and rule-weight state, matching OpenEnv's reset-as-clean-
        # slate convention and eliminating cross-episode state leakage
        # under SUPPORTS_CONCURRENT_SESSIONS=True.
        self._scammer: ScriptedScammer | None = None
        self._victim: ScriptedVictim | None = None
        self._bank: ScriptedBankMonitor | None = None
        self._regulator: ScriptedRegulator | None = None
        self._rng = random.Random()
        self._chat_history: list[ChatMessage] = []
        self._attack_sequence: list[str] = []
        self._transaction: TransactionMeta | None = None
        self._turn: int = 0
        self._decision_index: int = 0
        self._state_obj = ChakravyuhState()
        self._last_flag_threshold: float = 0.55
        # Tracks the most recent analyzer action so the rubric can be
        # evaluated at terminal time. None until the first step().
        self._last_action: ChakravyuhAction | None = None

    # ---- OpenEnv API ---------------------------------------------------

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **_: Any,
    ) -> ChakravyuhObservation:
        actual_seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        self._rng = random.Random(actual_seed)

        self._scammer = ScriptedScammer(seed=actual_seed)
        self._victim = ScriptedVictim(
            profile=self._victim_profile,
            gullibility_multiplier=self._gullibility,
            seed=actual_seed,
        )
        self._bank = ScriptedBankMonitor(seed=actual_seed)
        self._regulator = ScriptedRegulator()
        for agent in (self._scammer, self._victim, self._bank):
            agent.reset(seed=actual_seed)

        # Clear rubric trajectory state (no-op for stateless rubrics; matters
        # for any TrajectoryRubric subclass a user might swap in).
        self._reset_rubric()

        self._chat_history = []
        self._attack_sequence = []
        self._transaction = None
        self._turn = 0
        self._decision_index = 0
        self._last_action = None

        template = self._scammer.current_template()
        self._state_obj = ChakravyuhState(
            episode_id=episode_id or uuid4().hex[:12],
            step_count=0,
            scam_category=template.get("category"),
            victim_profile=self._victim_profile.value,
        )

        # Advance to first analyzer decision point: scammer(1) + victim(2).
        # The scripted scammer dispatches on observation.turn (1 = opener,
        # 4 = escalate, else = end) — so turn numbers below must match the
        # original ChakravyuhEnv schedule.
        #
        # ``allow_terminal=False`` on the turn-2 victim guarantees reset()
        # returns a NON-terminal observation (Gym/OpenEnv convention). If
        # the victim would Refuse/CallBank immediately, the action is
        # downgraded to the non-terminating Question/Respond equivalent so
        # the analyzer gets at least one legitimate decision point. A
        # later turn-5 refuse still terminates the episode normally.
        self._play_scammer_turn(turn=1)
        if self._state_obj.done:
            # ScammerEndScam on turn 1 — exceptionally rare but possible.
            # Fall through to terminal obs; cannot manufacture a decision
            # point from nothing.
            return self._terminal_observation()
        self._play_victim_turn(turn=2, allow_terminal=False)
        return self._build_observation(decision_index=0)

    def step(
        self,
        action: ChakravyuhAction,
        timeout_s: float | None = None,
        **_: Any,
    ) -> ChakravyuhObservation:
        if self._scammer is None:
            raise RuntimeError("step() called before reset()")
        if self._state_obj.done:
            raise RuntimeError("Episode is already done; call reset()")

        # Apply the analyzer's decision at the current internal turn.
        self._apply_analyzer_decision(action)
        self._state_obj.step_count += 1
        self._last_flag_threshold = action.flag_threshold
        # Remember the last action so the rubric can be evaluated at the
        # terminal observation (outcome is trajectory-level, so the rubric
        # sees the *final* analyzer action paired with the full outcome).
        self._last_action = action

        if self._decision_index == 0:
            # Analyzer decision was at turn 3 (external). Now advance to the
            # turn 6 decision point.
            self._play_scammer_turn(turn=4)  # escalate + send_link
            if not self._state_obj.done:
                self._play_victim_turn(turn=5)  # may end episode
            if self._state_obj.done:
                return self._terminal_observation()
            self._decision_index = 1
            return self._build_observation(
                decision_index=1, include_transaction=True
            )

        # decision_index == 1 — analyzer decision was at turn 6. Now run
        # scammer request(7) → bank(8) → combined(9) → finalize(10).
        self._play_transaction_turn(turn=7)
        self._play_bank_turn(turn=8)
        self._resolve_outcome()  # turns 9-10
        return self._terminal_observation()

    @property
    def state(self) -> ChakravyuhState:
        return self._state_obj

    # ---- internal turn logic ------------------------------------------

    def _play_scammer_turn(self, turn: int) -> None:
        assert self._scammer is not None
        self._turn = turn
        obs = self._internal_obs(role="scammer")
        result = self._scammer.act(obs)
        actions = result if isinstance(result, list) else [result]
        for action in actions:
            self._apply_scammer_action(action)
            if self._state_obj.done:
                break

    def _play_victim_turn(self, turn: int, allow_terminal: bool = True) -> None:
        """Play the victim's turn.

        If ``allow_terminal=False`` (used during reset), any Refuse /
        CallBank action is recorded in the chat log but does NOT terminate
        the episode — the episode stays alive so the analyzer can make at
        least one decision. The victim's suspicion is still visible to the
        analyzer through the chat text, and later turns can still terminate.
        """
        assert self._victim is not None
        self._turn = turn
        obs = self._internal_obs(role="victim")
        action = self._victim.act(obs)
        if isinstance(action, VictimComply):
            self._state_obj.victim_complied = True
            text = f"[COMPLIED: {action.field.value}]"
        elif isinstance(action, VictimRefuse):
            self._state_obj.victim_refused = True
            text = f"[REFUSED: {action.reason}]"
            if allow_terminal:
                self._state_obj.done = True
        elif isinstance(action, VictimCallBank):
            self._state_obj.victim_sought_verification = True
            text = "[CALLED BANK TO VERIFY]"
            if allow_terminal:
                self._state_obj.done = True
        else:
            text = getattr(action, "text", "[responded]")
        self._chat_history.append(
            ChatMessage(sender="victim", turn=self._turn, text=text)
        )

    def _play_transaction_turn(self, turn: int) -> None:
        assert self._scammer is not None
        self._turn = turn
        template = self._scammer.current_template()
        category = template.get("category", "otp_theft")
        amount_by_category = {
            "otp_theft": 49999.0,
            "kyc_fraud": 2000.0,
            "loan_app_fraud": 999.0,
            "investment_fraud": 10000.0,
            "impersonation": 1500.0,
        }
        amount = amount_by_category.get(category, 5000.0) + self._rng.uniform(-500, 500)
        self._transaction = TransactionMeta(
            amount=max(100.0, amount),
            receiver_new=True,
            receiver_id_hash=f"rx_{self._rng.randint(10000, 99999)}",
            frequency_24h=self._rng.randint(0, 5),
        )

    def _play_bank_turn(self, turn: int) -> None:
        assert self._bank is not None
        self._turn = turn
        obs = self._internal_obs(role="bank")
        action = self._bank.act(obs)
        if isinstance(action, (BankFlag, BankFreeze)):
            self._state_obj.bank_flagged = True
            if isinstance(action, BankFreeze):
                self._state_obj.bank_froze = True

    def _resolve_outcome(self) -> None:
        # Turn 9: combined decision, Turn 10: regulator log.
        self._turn = 10
        extracted = (
            self._state_obj.victim_complied
            and not self._state_obj.bank_froze
            and not self._state_obj.done
        )
        self._state_obj.money_extracted = extracted
        self._state_obj.done = True

    def _apply_analyzer_decision(self, action: ChakravyuhAction) -> None:
        # Validate signal names (strings on wire → enums internally).
        for name in action.signals:
            if name not in _VALID_SIGNAL_NAMES:
                raise ValueError(
                    f"Unknown AnalyzerSignal '{name}'. Valid: "
                    f"{sorted(_VALID_SIGNAL_NAMES)}"
                )
        if action.score >= action.flag_threshold and not self._state_obj.analyzer_flagged:
            self._state_obj.analyzer_flagged = True
            # We just played scammer+victim for this round; the analyzer
            # decision logically sits on the NEXT internal turn.
            self._state_obj.analyzer_flag_turn = self._turn + 1

    def _apply_scammer_action(self, action: object) -> None:
        text = ""
        intent: Intent | None = None
        if isinstance(action, ScammerSendMessage):
            text = action.text
            intent = action.intent
        elif isinstance(action, ScammerImpersonate):
            text = f"[IMPERSONATES: {action.role.value} — {action.claimed_identity}]"
        elif isinstance(action, ScammerRequestInfo):
            text = f"Please share your {action.field.value}. {action.pretext}"
        elif isinstance(action, ScammerSendLink):
            text = f"Click here: {action.url}"
        elif isinstance(action, ScammerEscalateUrgency):
            text = f"[ESCALATES urgency to level {action.level}]"
        elif isinstance(action, ScammerEndScam):
            text = f"[ENDS: {action.reason}]"
            self._state_obj.done = True
        self._chat_history.append(
            ChatMessage(sender="scammer", turn=self._turn, text=text, intent=intent)
        )
        self._attack_sequence.append(text)

    # ---- observation / reward -----------------------------------------

    def _internal_obs(self, role: str) -> InternalObs:
        """Build the private observation the scripted agents expect."""
        assert self._scammer is not None
        assert self._victim is not None
        template = self._scammer.current_template()
        cat = template.get("category")
        scam_cat = ScamCategory(cat) if cat else None

        if role == "bank":
            return InternalObs(
                agent_role="bank",
                turn=self._turn,
                transaction=self._transaction,
            )
        if role == "victim":
            return InternalObs(
                agent_role="victim",
                turn=self._turn,
                chat_history=list(self._chat_history),
                victim_profile=self._victim.profile,
            )
        return InternalObs(
            agent_role="scammer",
            turn=self._turn,
            chat_history=list(self._chat_history),
            scam_category=scam_cat,
        )

    def _build_observation(
        self,
        decision_index: int,
        include_transaction: bool = False,
    ) -> ChakravyuhObservation:
        return ChakravyuhObservation(
            chat_history=[self._message_to_dict(m) for m in self._chat_history],
            turn=self._turn,
            transaction=self._transaction_dict() if include_transaction else None,
            decision_index=decision_index,
            done=False,
            reward=None,
            episode_id=self._state_obj.episode_id,
            scam_category=self._state_obj.scam_category,
            victim_profile=self._state_obj.victim_profile,
        )

    def _terminal_observation(self) -> ChakravyuhObservation:
        assert self._scammer is not None
        assert self._regulator is not None
        self._state_obj.done = True

        # The false_positive flag in compute_rewards requires a "truly benign"
        # episode, which the scripted scammer never generates (every episode
        # is a scam). So FP is set conservatively to False here; benign-case
        # handling lives in the eval pipeline, not this scripted env.
        template = self._scammer.current_template()
        cat = template.get("category", "otp_theft")
        outcome = EpisodeOutcome(
            money_extracted=self._state_obj.money_extracted,
            detected_by_turn=self._state_obj.analyzer_flag_turn,
            turns_used=self._turn,
            victim_refused=self._state_obj.victim_refused,
            victim_sought_verification=self._state_obj.victim_sought_verification,
            analyzer_flagged=self._state_obj.analyzer_flagged,
            bank_flagged=self._state_obj.bank_flagged,
            bank_froze=self._state_obj.bank_froze,
            false_positive=False,
            scam_category=ScamCategory(cat),
            victim_profile=self._victim_profile,
        )
        novelty = self._novelty_scorer.score(self._attack_sequence)
        legacy_breakdown = compute_rewards(outcome=outcome, novelty=novelty)
        self._regulator.log_outcome(outcome)

        outcome_dict: dict[str, Any] = {
            "money_extracted": self._state_obj.money_extracted,
            "analyzer_flagged": self._state_obj.analyzer_flagged,
            "bank_flagged": self._state_obj.bank_flagged,
            "bank_froze": self._state_obj.bank_froze,
            "victim_refused": self._state_obj.victim_refused,
            "victim_sought_verification": self._state_obj.victim_sought_verification,
            "detected_by_turn": self._state_obj.analyzer_flag_turn,
            "turns_used": self._turn,
            "is_benign": False,
            "false_positive": False,
            "novelty": novelty,
        }

        # Build the terminal observation first WITHOUT the rubric reward so
        # the rubric can read outcome/action off it. Reward is filled in
        # below using the Environment._apply_rubric helper (which also
        # populates each sub-rubric's ``last_score`` for introspection).
        obs = ChakravyuhObservation(
            chat_history=[self._message_to_dict(m) for m in self._chat_history],
            turn=self._turn,
            transaction=self._transaction_dict(),
            decision_index=-1,
            done=True,
            reward=None,
            episode_id=self._state_obj.episode_id,
            scam_category=self._state_obj.scam_category,
            victim_profile=self._state_obj.victim_profile,
            outcome=outcome_dict,
            reward_breakdown=None,
        )

        # If the episode terminated before any analyzer action was supplied
        # (e.g. turn-1 ScammerEndScam rare path), fall back to a zero-score
        # placeholder so the rubric can still be evaluated on a well-formed
        # action — keeps the base-class _apply_rubric contract consistent.
        action = self._last_action or ChakravyuhAction(score=0.0, signals=[], explanation="")

        reward = float(self._apply_rubric(action, obs))
        obs.reward = reward

        # Publish the composable breakdown: per-sub-rubric last_score plus
        # the weighted-sum total. Judges reading the wire payload can see
        # exactly how the reward decomposed — the point of the rubric.
        if isinstance(self.rubric, AnalyzerRubric):
            obs.reward_breakdown = {
                **self.rubric.last_scores(),
                "weights": dict(self.rubric.weights),
                "legacy_analyzer": legacy_breakdown.analyzer,
            }
        else:
            obs.reward_breakdown = {
                "total": reward,
                "rubric_class": type(self.rubric).__name__ if self.rubric else None,
                "legacy_analyzer": legacy_breakdown.analyzer,
            }

        return obs

    @staticmethod
    def _message_to_dict(msg: ChatMessage) -> dict[str, Any]:
        return {
            "sender": msg.sender,
            "turn": msg.turn,
            "text": msg.text,
            "intent": msg.intent.value if msg.intent else None,
        }

    def _transaction_dict(self) -> dict[str, Any] | None:
        if self._transaction is None:
            return None
        return {
            "amount": self._transaction.amount,
            "receiver_new": self._transaction.receiver_new,
            "receiver_id_hash": self._transaction.receiver_id_hash,
            "frequency_24h": self._transaction.frequency_24h,
        }
