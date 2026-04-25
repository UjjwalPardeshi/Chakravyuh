"""Pydantic schemas for Chakravyuh agent actions, observations, and episode state.

All inter-agent messages, observations, and actions are validated through these
models to prevent malformed data from breaking the training loop. Schemas mirror
the OpenEnv action/observation contract so the env plugs in cleanly.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScamCategory(str, Enum):
    OTP_THEFT = "otp_theft"
    KYC_FRAUD = "kyc_fraud"
    LOAN_APP = "loan_app_fraud"
    INVESTMENT = "investment_fraud"
    IMPERSONATION = "impersonation"


class VictimProfile(str, Enum):
    SENIOR = "senior"
    YOUNG_URBAN = "young_urban"
    SEMI_URBAN = "semi_urban"


class Channel(str, Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"


class Intent(str, Enum):
    URGENCY = "urgency"
    AUTHORITY = "authority"
    EMPATHY = "empathy"
    GREED = "greed"
    FEAR = "fear"


class ImpersonationRole(str, Enum):
    BANK = "bank"
    GOVERNMENT = "government"
    FAMILY = "family"
    EMPLOYER = "employer"
    DELIVERY = "delivery"


class InfoField(str, Enum):
    OTP = "otp"
    PIN = "pin"
    AADHAAR = "aadhaar"
    PAN = "pan"
    CVV = "cvv"
    CARD_NUMBER = "card_number"
    BANK_ACCOUNT = "bank_account"


class LinkKind(str, Enum):
    FAKE_KYC = "fake_kyc"
    FAKE_REFUND = "fake_refund"
    FAKE_REWARD = "fake_reward"
    FAKE_PAYMENT = "fake_payment"


class AnalyzerSignal(str, Enum):
    URGENCY = "urgency"
    IMPERSONATION = "impersonation"
    INFO_REQUEST = "info_request"
    SUSPICIOUS_LINK = "suspicious_link"
    UNUSUAL_AMOUNT = "unusual_amount"
    UNKNOWN_SENDER = "unknown_sender"
    AUTHORITY = "authority"
    FEAR = "fear"
    GREED = "greed"
    EMPATHY = "empathy"
    FINANCIAL_LURE = "financial_lure"


# ---------------------------------------------------------------------------
# Scammer actions
# ---------------------------------------------------------------------------


class ScammerSendMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["send_message"] = "send_message"
    text: str = Field(min_length=1, max_length=1000)
    intent: Intent


class ScammerRequestInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["request_info"] = "request_info"
    field: InfoField
    pretext: str = Field(default="", max_length=500)


class ScammerImpersonate(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["impersonate"] = "impersonate"
    role: ImpersonationRole
    claimed_identity: str = Field(max_length=200)


class ScammerSendLink(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["send_link"] = "send_link"
    kind: LinkKind
    url: str = Field(max_length=500)


class ScammerEscalateUrgency(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["escalate_urgency"] = "escalate_urgency"
    level: int = Field(ge=1, le=5)


class ScammerEndScam(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["end_scam"] = "end_scam"
    reason: str = Field(default="", max_length=200)


ScammerAction = (
    ScammerSendMessage
    | ScammerRequestInfo
    | ScammerImpersonate
    | ScammerSendLink
    | ScammerEscalateUrgency
    | ScammerEndScam
)


# ---------------------------------------------------------------------------
# Victim actions
# ---------------------------------------------------------------------------


class VictimRespond(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["respond"] = "respond"
    text: str = Field(max_length=500)
    trust_delta: float = Field(ge=-1.0, le=1.0, default=0.0)


class VictimQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["question"] = "question"
    target_info: str = Field(max_length=200)


class VictimComply(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["comply"] = "comply"
    field: InfoField
    value: str = Field(max_length=100)


class VictimRefuse(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["refuse"] = "refuse"
    reason: str = Field(default="", max_length=200)


class VictimCallBank(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["call_bank"] = "call_bank"


VictimAction = VictimRespond | VictimQuestion | VictimComply | VictimRefuse | VictimCallBank


# ---------------------------------------------------------------------------
# Analyzer / Bank Monitor oversight actions
# ---------------------------------------------------------------------------


class AnalyzerScore(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["score_suspicion"] = "score_suspicion"
    score: float = Field(ge=0.0, le=1.0)
    signals: list[AnalyzerSignal] = Field(default_factory=list)
    explanation: str = Field(max_length=300)


class AnalyzerFlag(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["flag"] = "flag"
    category: AnalyzerSignal
    explanation: str = Field(max_length=300)


AnalyzerAction = AnalyzerScore | AnalyzerFlag


class BankApprove(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["approve"] = "approve"
    confidence: float = Field(ge=0.0, le=1.0)


class BankFlag(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["bank_flag"] = "bank_flag"
    signal: str = Field(max_length=200)
    confidence: float = Field(ge=0.0, le=1.0)


class BankFreeze(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["freeze"] = "freeze"
    reason: str = Field(max_length=300)


BankAction = BankApprove | BankFlag | BankFreeze


class AnalyzerConsultation(BaseModel):
    """Cross-tier oversight handshake — the on-device Analyzer's opinion
    summarised for the Bank Monitor without leaking chat content.

    Used by the optional Analyzer↔Bank negotiation protocol
    (see ``docs/negotiation_protocol.md``). The Bank Monitor never sees the
    chat itself — the consultation is the only channel through which the
    Analyzer's signal influences the bank-side decision.

    Fields are deliberately minimal:
      - ``score``: scam suspicion in [0, 1]
      - ``signals``: declared signals from the Analyzer's taxonomy (no chat text)
      - ``threshold``: the threshold the Analyzer was operating at
      - ``flagged``: convenience boolean (``score >= threshold``)
    """

    model_config = ConfigDict(frozen=True)
    score: float = Field(ge=0.0, le=1.0)
    signals: tuple[str, ...] = Field(default_factory=tuple)
    threshold: float = Field(ge=0.0, le=1.0, default=0.55)
    flagged: bool = False


class RegulatorAddRule(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["add_rule"] = "add_rule"
    signal: str = Field(max_length=100)
    weight: float = Field(ge=0.0, le=1.0)


class RegulatorRemoveRule(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["remove_rule"] = "remove_rule"
    rule_id: str


class RegulatorBulletin(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["publish_bulletin"] = "publish_bulletin"
    pattern_detected: str = Field(max_length=200)
    guidance: str = Field(max_length=500)


RegulatorAction = RegulatorAddRule | RegulatorRemoveRule | RegulatorBulletin


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    sender: Literal["scammer", "victim"]
    turn: int
    text: str
    intent: Intent | None = None


class TransactionMeta(BaseModel):
    model_config = ConfigDict(frozen=True)
    amount: float = Field(ge=0.0)
    receiver_new: bool
    receiver_id_hash: str
    frequency_24h: int = Field(ge=0)


class Observation(BaseModel):
    """Partial observation sent to a specific agent each turn.

    Agents only see fields relevant to their role — enforces information asymmetry.
    """

    model_config = ConfigDict(frozen=True)
    agent_role: Literal["scammer", "victim", "analyzer", "bank", "regulator"]
    turn: int
    chat_history: list[ChatMessage] = Field(default_factory=list)
    victim_profile: VictimProfile | None = None
    transaction: TransactionMeta | None = None
    scam_category: ScamCategory | None = None


# ---------------------------------------------------------------------------
# Episode state
# ---------------------------------------------------------------------------


class EpisodeOutcome(BaseModel):
    """Terminal state of an episode. Drives reward computation."""

    model_config = ConfigDict(frozen=True)
    money_extracted: bool
    detected_by_turn: int | None = None
    turns_used: int
    victim_refused: bool
    victim_sought_verification: bool
    analyzer_flagged: bool
    bank_flagged: bool
    bank_froze: bool
    false_positive: bool
    scam_category: ScamCategory
    victim_profile: VictimProfile


class EpisodeLog(BaseModel):
    """Full episode record for eval, replay, and novelty-score computation."""

    model_config = ConfigDict(frozen=True)
    episode_id: str
    seed: int
    scam_category: ScamCategory
    victim_profile: VictimProfile
    chat_history: list[ChatMessage]
    outcome: EpisodeOutcome
    attack_sequence: list[str] = Field(default_factory=list)
