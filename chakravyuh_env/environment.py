"""ChakravyuhEnv — OpenEnv-compliant multi-agent fraud simulation.

Turn structure (10 turns max, per Part 2.2):
    1. Scammer opens
    2. Victim responds
    3. Analyzer scores
    4. Scammer escalates
    5. Victim decides (continue / question / refuse)
    6. Analyzer re-scores
    7. Scammer requests transaction
    8. Bank Monitor analyzes tx metadata
    9. Combined decision: execute / block
    10. Regulator logs (rule update every 10 episodes)

The `reset()` / `step()` API matches standard RL env contracts (Gymnasium,
OpenEnv). Each call to `step()` advances ONE full turn (all 5 agents act as
appropriate for that turn index).

The loop is fully deterministic given the `seed` argument to `reset()`.
This is non-negotiable for the replay-first demo (Part 8.0).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
from chakravyuh_env.agents.bank_monitor import ScriptedBankMonitor
from chakravyuh_env.agents.base import Agent
from chakravyuh_env.agents.regulator import ScriptedRegulator
from chakravyuh_env.agents.scammer import ScriptedScammer
from chakravyuh_env.agents.victim import ScriptedVictim
from chakravyuh_env.novelty import build_novelty_scorer
from chakravyuh_env.reward import RewardBreakdown, compute_rewards
from chakravyuh_env.schemas import (
    AnalyzerScore,
    BankFlag,
    BankFreeze,
    ChatMessage,
    EpisodeLog,
    EpisodeOutcome,
    InfoField,
    Intent,
    Observation,
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

MAX_TURNS = 10


@dataclass
class EpisodeState:
    episode_id: str
    seed: int
    turn: int = 0
    chat_history: list[ChatMessage] = field(default_factory=list)
    transaction: TransactionMeta | None = None
    analyzer_flagged: bool = False
    analyzer_flag_turn: int | None = None
    bank_flagged: bool = False
    bank_froze: bool = False
    victim_complied: bool = False
    victim_refused: bool = False
    victim_sought_verification: bool = False
    ended: bool = False
    attack_sequence: list[str] = field(default_factory=list)


class ChakravyuhEnv:
    """Multi-agent environment compatible with OpenEnv reset/step API."""

    def __init__(
        self,
        scammer: Agent | None = None,
        victim: Agent | None = None,
        analyzer: Agent | None = None,
        bank_monitor: Agent | None = None,
        regulator: ScriptedRegulator | None = None,
        victim_profile: VictimProfile = VictimProfile.SEMI_URBAN,
        gullibility: float = 1.0,
        analyzer_threshold: float = 0.55,
        use_embeddings: bool = False,
    ) -> None:
        self.scammer = scammer or ScriptedScammer()
        self.victim = victim or ScriptedVictim(
            profile=victim_profile, gullibility_multiplier=gullibility
        )
        self.analyzer = analyzer or ScriptedAnalyzer(flag_threshold=analyzer_threshold)
        self.bank_monitor = bank_monitor or ScriptedBankMonitor()
        self.regulator = regulator or ScriptedRegulator()
        self.novelty_scorer = build_novelty_scorer(use_embeddings=use_embeddings)
        self._state: EpisodeState | None = None
        self._rng: random.Random = random.Random()

    # ---- core API ----

    def reset(self, seed: int | None = None) -> Observation:
        actual_seed = seed if seed is not None else random.randint(0, 2**31 - 1)
        self._rng = random.Random(actual_seed)
        self._state = EpisodeState(
            episode_id=uuid4().hex[:12], seed=actual_seed
        )
        for agent in (self.scammer, self.victim, self.analyzer, self.bank_monitor):
            agent.reset(seed=actual_seed)
        return self._observation_for("scammer")

    def step(self) -> tuple[Observation, RewardBreakdown | None, bool, dict[str, Any]]:
        """Advance one turn. Returns (obs, reward_or_None, done, info).

        Reward is None until the episode ends. Follows OpenAI Gym-style contract.
        """
        if self._state is None:
            raise RuntimeError("Call reset() before step()")
        if self._state.ended:
            raise RuntimeError("Episode already ended; call reset()")

        self._state.turn += 1
        info: dict[str, Any] = {"turn": self._state.turn}

        # Turn-by-turn orchestration
        if self._state.turn in (1, 4):
            self._scammer_turn()
        elif self._state.turn in (2, 5):
            self._victim_turn()
        elif self._state.turn in (3, 6):
            self._analyzer_turn()
        elif self._state.turn == 7:
            self._scammer_request_transaction()
        elif self._state.turn == 8:
            self._bank_turn()
        elif self._state.turn == 9:
            self._combined_decision()
        elif self._state.turn == 10:
            self._state.ended = True

        done = self._state.ended or self._state.turn >= MAX_TURNS
        reward = None
        if done:
            outcome = self._finalize()
            novelty = self.novelty_scorer.score(self._state.attack_sequence)
            reward = compute_rewards(outcome=outcome, novelty=novelty)
            info["outcome"] = outcome
            info["episode_log"] = self._build_log(outcome)
            self.regulator.log_outcome(outcome)

        next_obs = self._observation_for("scammer")
        return next_obs, reward, done, info

    # ---- turn handlers ----

    def _scammer_turn(self) -> None:
        assert self._state is not None
        obs = self._observation_for("scammer")
        result = self.scammer.act(obs)
        actions = result if isinstance(result, list) else [result]
        for action in actions:
            self._apply_scammer_action(action)
            if self._state.ended:
                break

    def _victim_turn(self) -> None:
        assert self._state is not None
        obs = self._observation_for("victim")
        action = self.victim.act(obs)
        text = ""
        if isinstance(action, VictimComply):
            self._state.victim_complied = True
            text = f"[COMPLIED: {action.field.value}]"
        elif isinstance(action, VictimRefuse):
            self._state.victim_refused = True
            text = f"[REFUSED: {action.reason}]"
            self._state.ended = True
        elif isinstance(action, VictimCallBank):
            self._state.victim_sought_verification = True
            text = "[CALLED BANK TO VERIFY]"
            self._state.ended = True
        else:
            text = getattr(action, "text", "[responded]")
        self._state.chat_history.append(
            ChatMessage(sender="victim", turn=self._state.turn, text=text)
        )

    def _analyzer_turn(self) -> None:
        assert self._state is not None
        obs = self._observation_for("analyzer")
        action = self.analyzer.act(obs)
        if isinstance(action, AnalyzerScore) and action.score >= getattr(
            self.analyzer, "flag_threshold", 0.55
        ):
            if not self._state.analyzer_flagged:
                self._state.analyzer_flagged = True
                self._state.analyzer_flag_turn = self._state.turn

    def _scammer_request_transaction(self) -> None:
        assert self._state is not None
        template = getattr(self.scammer, "current_template", lambda: {})()
        category = template.get("category", "otp_theft")
        # Synthesize a plausible transaction for the scam category
        amount_by_category = {
            "otp_theft": 49999.0,
            "kyc_fraud": 2000.0,
            "loan_app_fraud": 999.0,
            "investment_fraud": 10000.0,
            "impersonation": 1500.0,
        }
        amount = amount_by_category.get(category, 5000.0) + self._rng.uniform(-500, 500)
        self._state.transaction = TransactionMeta(
            amount=max(100.0, amount),
            receiver_new=True,
            receiver_id_hash=f"rx_{self._rng.randint(10000, 99999)}",
            frequency_24h=self._rng.randint(0, 5),
        )

    def _bank_turn(self) -> None:
        assert self._state is not None
        obs = self._observation_for("bank")
        action = self.bank_monitor.act(obs)
        if isinstance(action, (BankFlag, BankFreeze)):
            self._state.bank_flagged = True
            if isinstance(action, BankFreeze):
                self._state.bank_froze = True

    def _combined_decision(self) -> None:
        assert self._state is not None
        # Money is extracted only if:
        #   victim complied, AND episode not already ended, AND bank didn't freeze
        # ...also requires the victim to have actually gone through with tx.
        extracted = (
            self._state.victim_complied
            and not self._state.bank_froze
            and not self._state.ended
        )
        self._state.ended = True
        # Track whether money was extracted for _finalize()
        setattr(self._state, "_money_extracted", extracted)

    def _finalize(self) -> EpisodeOutcome:
        assert self._state is not None
        money_extracted = getattr(self._state, "_money_extracted", False)
        # Determine "detected by turn" — first oversight flag
        detected_by_turn: int | None = self._state.analyzer_flag_turn
        template = getattr(self.scammer, "current_template", lambda: {})()
        category = template.get("category", "otp_theft")
        profile = self.victim.profile if hasattr(self.victim, "profile") else VictimProfile.SEMI_URBAN
        false_positive = (
            self._state.analyzer_flagged and not self._state.victim_complied
            and not money_extracted
        ) and category is None  # truly benign — we don't generate benign now, placeholder
        return EpisodeOutcome(
            money_extracted=money_extracted,
            detected_by_turn=detected_by_turn,
            turns_used=self._state.turn,
            victim_refused=self._state.victim_refused,
            victim_sought_verification=self._state.victim_sought_verification,
            analyzer_flagged=self._state.analyzer_flagged,
            bank_flagged=self._state.bank_flagged,
            bank_froze=self._state.bank_froze,
            false_positive=false_positive,
            scam_category=ScamCategory(category),
            victim_profile=profile,
        )

    def _build_log(self, outcome: EpisodeOutcome) -> EpisodeLog:
        assert self._state is not None
        return EpisodeLog(
            episode_id=self._state.episode_id,
            seed=self._state.seed,
            scam_category=outcome.scam_category,
            victim_profile=outcome.victim_profile,
            chat_history=list(self._state.chat_history),
            outcome=outcome,
            attack_sequence=list(self._state.attack_sequence),
        )

    # ---- observation builder ----

    def _observation_for(self, role: str) -> Observation:
        assert self._state is not None
        template = getattr(self.scammer, "current_template", lambda: {})()
        category = template.get("category")
        scam_cat = ScamCategory(category) if category else None

        if role == "scammer":
            return Observation(
                agent_role="scammer",
                turn=self._state.turn,
                chat_history=list(self._state.chat_history),
                scam_category=scam_cat,
            )
        if role == "victim":
            return Observation(
                agent_role="victim",
                turn=self._state.turn,
                chat_history=list(self._state.chat_history),
                victim_profile=getattr(self.victim, "profile", VictimProfile.SEMI_URBAN),
            )
        if role == "analyzer":
            return Observation(
                agent_role="analyzer",
                turn=self._state.turn,
                chat_history=list(self._state.chat_history),
            )
        if role == "bank":
            return Observation(
                agent_role="bank",
                turn=self._state.turn,
                transaction=self._state.transaction,
            )
        return Observation(agent_role="regulator", turn=self._state.turn)

    # ---- action applier ----

    def _apply_scammer_action(self, action: object) -> None:
        assert self._state is not None
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
            self._state.ended = True
        self._state.chat_history.append(
            ChatMessage(sender="scammer", turn=self._state.turn, text=text, intent=intent)
        )
        self._state.attack_sequence.append(text)
