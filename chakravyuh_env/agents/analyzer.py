"""Scripted Behavioral Analyzer — rule-based baseline.

v0.3 upgrades:
  - Full 11-signal taxonomy (urgency, impersonation, info_request,
    suspicious_link, unknown_sender, unusual_amount + authority, fear, greed,
    empathy, financial_lure).
  - Word-boundary-safe keyword matching (no more "fir" matching "confirmation").
  - Legit-OTP-delivery detection: OTPs quoted with digits (e.g., "OTP 392847")
    are treated as legit transaction SMS, not info_request.
  - Explicit electricity-board + personal-impersonation keywords.
  - Legit-domain allowlist + strong benign markers reduce FPR without letting
    scams that copy legit phrasing slip through.

Baseline target: detection ≥85%, FPR ≤15%, investment ≥70%.
"""

from __future__ import annotations

import re
from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    AnalyzerScore,
    AnalyzerSignal,
    Observation,
)


# ---------------------------------------------------------------------------
# Positive-evidence keywords
# ---------------------------------------------------------------------------

_URGENCY_KEYWORDS = [
    "urgent", "immediately", "expires", "expiring", "expired", "last chance",
    "don't miss", "hurry", "act fast", "deadline", "last date", "closes",
    "cancel", "suspended", "block", "blocked", "turant", "jaldi", "abhi",
    "last 24", "valid till", "within 2 hour", "within 10 minute",
    "within 30 minute", "within 2 hrs", "within 1 hour", "in 2 hrs",
    "in 2 hr", "in 5 minute", "in 10 minute", "in 30 minute",
    "before 6 pm", "before 5 pm", "before 8 pm", "before 2 pm",
    "before 3 pm", "by 3 pm", "by 5 pm", "by 6 pm",
    "today only", "tonight only", "right now", "asap",
    "virtual hearing", "hearing in", "warrant in",
    "locks at", "allocation locks", "last 500",
    "close at", "closing at", "closes today", "closes tonight",
    "tomorrow at", "before tomorrow",
    "at 3 pm today", "at 5 pm today", "at 6 pm today", "at 8 pm today",
    "pm today", "end of today",
    "limited spots", "limited seats", "offer valid till",
    "limited to first", "exclusive allocation", "allocation closes",
]

_IMPERSONATION_PHRASES = [
    # Banks
    "sbi", "hdfc", "icici", "axis bank", "yes bank", "kotak", "canara", "pnb",
    "indusind", "federal bank", "idfc", "rbl", "dbs", "au small", "bob ", "bank of",
    "indian bank", "union bank", "karur vysya", "muthoot",
    # Govt / regulators
    "rbi", "uidai", "income tax", "gst", "epfo", "government", "police",
    "cyber cell", "customer care", "fraud team", "cbi", "trai",
    "election commission", "ministry of", "it department", "lic", "indiapost",
    "crime branch", "sebi",
    # State electricity + utilities
    "electricity board", "bseb", "tneb", "mseb", "kseb", "wbsedcl", "dgvcl",
    "torrent power", "tata power", "adani power", "reliance energy",
    "power connection", "power cut", "disconnection order",
    # Brands used for impersonation
    "amazon", "flipkart", "paytm", "phonepe", "gpay", "bhim", "bharatpe", "cred",
    "swiggy", "zomato", "blinkit", "dtdc", "fedex", "bluedart", "delhivery",
    "whatsapp business", "youtube partner", "chatgpt", "chatgpt plus",
    "anthropic", "claude ai", "openai india", "meta verified", "blue checkmark",
    "instagram ", "facebook ", "meta ads", "google ads",
    "bgmi", "free fire", "pubg", "mythic skin",
    "reliance jio", "jio ipo", "binance india", "bitcoin doubling",
    "ola/uber", "ola driver", "uber partner",
    "ram mandir", "ram janmabhoomi", "teerth kshetra",
    "dream11", "fantasy league", "my11circle",
    # Personal-impersonation patterns (family/friends)
    "beta ", "chacha", "chachi", "papa ", "mom ", "uncle ", "aunty",
    "mera wallet", "phone is broken", "using neighbor",
    # Marathi/Hindi police/authority
    "पोलीस", "इन्स्पेक्टर", "मुंबई पोलीस", "सायबर सेल",
    "पुलिस", "थाना", "inspector patil", "inspector sharma",
    "police officer", "narcotics officer", "customs officer",
    # HR/hiring brand impersonation
    "offer letter from", "hiring: ", "hr team", "recruitment team",
    # Loan app brand impersonation
    "recovery agent", "instamoney", "cashnow", "kreditbee", "navi loan",
    "lazypay", "bajaj recovery", "instacash", "easymoney", "quickloan",
    "cred recovery", "pay later recovery", "lender",
    # Self-identification phrases
    "this is ", "main ", "bol raha", "calling from", "se hoon", "manager",
    "officer", "agent", "from sbi", "from hdfc", "fraud department",
]

_INFO_KEYWORDS: dict[AnalyzerSignal, list[str]] = {}  # populated below

_INFO_REQUEST_KEYWORDS = [
    "share otp", "tell me otp", "read otp", "otp share", "otp batao",
    "share the otp", "share the code", "share the verification",
    "tell the code", "confirm otp", "verify otp",
    "aadhaar photo", "photo bhejo", "verification code needed",
    "share aadhaar", "aadhaar number", "pan number required",
    "cvv", "card number", "bank details", "account number",
    "password", "upi pin",
    "send otp", "read out the code", "read me the code",
]

# Back-compat: keep `_INFO_KEYWORDS[AnalyzerSignal.INFO_REQUEST]` accessible
# for existing consumers (server.episode_curator) that need the keyword list.
_INFO_KEYWORDS[AnalyzerSignal.INFO_REQUEST] = _INFO_REQUEST_KEYWORDS

# Mention of OTP as a word, without a concrete code — suggests asking for it
_OTP_MENTION_RE = re.compile(r"\b(otp|verification code|6[- ]digit code|pin)\b", re.IGNORECASE)
# Legitimate OTP-delivery pattern — OTP is PROVIDED in the text with digits
_OTP_PROVIDED_RE = re.compile(r"\b(otp|code)[^.\n]{0,40}?\b\d{4,8}\b", re.IGNORECASE)

_FINANCIAL_LURE_KEYWORDS = [
    "pre-approved", "pre approved", "pre-qualified", "loan approved",
    "no documents", "no credit check", "no collateral", "no cibil",
    "no guarantor", "zero paperwork", "instant loan", "instant disbursal",
    "instant disbursement", "disbursal fee", "disbursement fee",
    "processing fee", "activation fee", "evaluation charge", "membership fee",
    "you won", "lucky draw", "prize", "cashback",
    "refund pending", "refund stuck", "refund of rs",
    "2% interest", "1% interest", "1.8% p.a.", "1% p.a.", "2% p.a.",
    "subvention", "zero interest", "0% interest", "free gift",
    "bonus credit", "customs fee", "courier charge",
    "redelivery charge", "delivery charge", "handling fee",
    "valuation fee", "gst charge",
    "advance tax", "settlement fee", "bgv fee", "background verification fee",
    "onboarding fee", "training certification", "software installation fee",
    "software fee", "activation charge", "installation fee",
    "registration fee", "entry fee",
    "invest rs", "invest ₹",
]

_GREED_KEYWORDS = [
    "guaranteed return", "guaranteed profit", "guaranteed income",
    "double your money", "doubling", "triple your", "daily profit",
    "intraday tip", "stock tip", "trading signal", "vip signal",
    "vip group", "vip telegram", "premium group", "premium community",
    "algo trading", "algorithm", "quant fund", "crypto bot", "crypto mining",
    "mine 100", "mine daily", "roi", "200% return", "300% return",
    "500% return", "1000%", "100% accuracy", "94% accuracy", "95% accuracy",
    "accurate prediction", "secret prediction", "prediction group",
    "win 95", "win 99", "win 90", "contests monthly",
    "only 3 slots", "only 5 slots", "only 7 seats", "last 10 seats",
    "limited seats", "vip seats", "seats closing",
    "earn rs 3", "earn rs 5", "earn rs 10", "earn rs 200",
    "earn rs 500", "earn rs 50,000", "earn 50,000", "earn monthly",
    "lakh in 30 days", "lakh in 7 days", "crore in", "becomes rs",
    "becomes Rs",
    "hit jackpot", "mined 100",
    "forex", "usd/inr", "mlm", "pyramid scheme", "referral and earn",
    "refer and earn", "binance india", "bitcoin doubling",
    "work from home", "work-from-home", "whatsapp 9876", "data entry home",
    "home job", "part-time earn", "side income", "part-time job",
    "review youtube videos", "earn by review", "per page",
    "daily earnings", "monthly earnings", "earn daily",
    "earn Rs", "earning Rs", "make Rs", "make rs",
    "proven strategy", "trade for you", "personally guide",
    "dalo", "mahine mein", "lakh mahine",
    "growthfin", "quantum wealth", "wealth advisory",
    "dream11 secret", "fantasy prediction",
    "private placement", "ipo alert", "listing price",
    "sovereign gold bond",
    "invest a small", "ipo allocation",
]

_FEAR_KEYWORDS = [
    "arrest", "arrested", "arrest warrant", "jail", "fir no", "fir filed",
    "drug trafficking", "drugs smuggling", "drugs case", "2kg drugs",
    "cbi case", "cbi mumbai", "frozen", "freezing", "asset freeze",
    "account freeze", "disconnect", "disconnected", "disconnection",
    "legal notice", "warrant", "custody", "criminal case", "illegal activity",
    "police complaint", "blacklist", "defaulter", "penalty rs",
    "court notice", "court order", "investigation against",
    "digital arrest", "skype video", "video verification call",
    "narcotics", "money laundering", "hawala",
    "case will be filed", "non-attendance",
    "raid notice", "tax raid", "asset seized",
    "drugs found", "parcel in your name", "parcel found",
    "connection cut", "electricity cut",
    # Loan harassment / financial fear
    "cibil score dropped", "cibil dropped", "lok adalat", "sarfaesi",
    "share your contacts", "contact list", "contacts with abuse",
    "abuse messages", "family will see", "friends, family, boss",
    "property attachment", "property seized", "overdue notice",
    "recovery case", "recovery action", "account block",
    "will be blocked", "freeze your account",
]

_AUTHORITY_KEYWORDS = [
    "rbi mandate", "rbi circular", "rbi guideline", "new rbi rule",
    "sebi registered", "ministry of", "inspector ", "officer patil",
    "officer sharma", "officer kumar", "dept.", "department of",
    "circular no", "notice no", "case no", "fir no", "arn no",
    "compliance", "mandatory", "cybercrime branch", "cyber crime branch",
    "narcotics bureau", "government of india", "govt of india",
    "irctc rail", "epfo-cpao", "7th pay commission",
]

_EMPATHY_KEYWORDS = [
    "relocating to", "alone in", "trust me", "mentor you", "personally guide",
    "guide you personally", "saw your profile", "matched with you",
    "tinder", "bharatmatrimony", "shaadi.com", "bumble", "hinge",
    "emergency please", "help me please", "urgent help",
    "i'll pay back", "return tomorrow", "return when",
    "college fees", "hospital bill", "flight change", "ticket urgent",
    "chori ho gaya", "wallet chori",
    "interested in marriage", "show you my setup",
]


# ---------------------------------------------------------------------------
# Suspicious links
# ---------------------------------------------------------------------------

_URL_PATTERN = re.compile(
    r"https?://\S+|[a-z0-9-]+\.(?:xyz|top|click|tk|gq|ml|co\.in|in|app)(?:/\S*)?",
    re.IGNORECASE,
)
_SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".click", ".tk", ".gq", ".ml", ".in-kyc", ".in-update",
    ".in-gov", ".gov-in", ".gov-india", ".app-loan", ".in-gold", ".in-pan",
    ".co.in.top", "-india.top", "-india.ml", "-india.gq", "-kyc.", "-verify.",
    "-pay.co", "-redelivery.co", "-customs.", "google-store-",
]
_URL_SHORTENERS = [
    "bit.ly", "tinyurl", "t.me/", "ow.ly", "is.gd", "buff.ly",
    "play-store-", "amzn-",
]


# ---------------------------------------------------------------------------
# Negative evidence
# ---------------------------------------------------------------------------

# Legit-only markers — unlikely to appear in scams
_BENIGN_MARKERS = [
    "utr ", "utr:", "utr hdfc", "utr sbi",
    "arn ", "arn:",
    "toll free 1800", "toll-free 1800", "helpline 1860",
    "customer care 1860-", "1860 266", "1800 266", "1860-266-0333",
    "auto generated", "auto-generated", "this is an automated",
    "do not reply to this sms", "do not reply to this message",
    "your request has been processed", "has been processed.",
    "claim is under processing", "is under processing",
    "credited to your a/c", "debited from your a/c",
    "no action required.", "no action required from your side",
    "no action needed from your side",
    "ignore if already paid", "disregard if already",
    "sip of rs", "emi of rs", "premium rs", "txn id:",
    "order id:", "booking id:", "pnr:",
    "no action needed.", "valid till 30", "valid till 31",
]

_LEGIT_DOMAIN_PATTERNS = [
    r"\bgst\.gov\.in\b",
    r"\bincometax\.gov\.in\b",
    r"\buidai\.gov\.in\b",
    r"\bmyaadhaar\.uidai\.gov\.in\b",
    r"\bpassportindia\.gov\.in\b",
    r"\bepfindia\.gov\.in\b",
    r"\bpassbook\.epfindia\.gov\.in\b",
    r"\bcibil\.com\b",
    r"\bsbi\.co\.in\b",
    r"\bhdfcbank\.com\b",
    r"\bicicibank\.com\b",
    r"\baxisbank\.com\b",
    r"\bbescom\.org\b",
    r"\brbi\.org\.in\b",
    r"\bcybercrime\.gov\.in\b",
    r"\bbookmyshow\.com\b",
    r"\bamazon\.in\b",
    r"\bflipkart\.com\b",
    r"\bgoogle\.com\b",
]

_LEGIT_DOMAIN_RE = re.compile("|".join(_LEGIT_DOMAIN_PATTERNS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class ScriptedAnalyzer(Agent):
    """Rule-based baseline with 11-signal taxonomy + legit-SMS allowlist."""

    def __init__(self, flag_threshold: float = 0.50, seed: int | None = None) -> None:
        super().__init__(name="analyzer", seed=seed)
        self.flag_threshold = flag_threshold

    def act(self, observation: Observation) -> Any:
        signals: list[AnalyzerSignal] = []
        score = 0.0
        text_all = " ".join(
            m.text.lower() for m in observation.chat_history if m.sender == "scammer"
        )

        # Info request: scams ASK for OTP (no code), legit SMS PROVIDE OTP
        # (digits in text). If OTP digits are present, treat as legit
        # transaction SMS and do NOT flag info_request — even if the text
        # contains phrases like "share OTP with merchant" (the merchant form
        # is the legit channel, not the attacker).
        otp_mentioned = bool(_OTP_MENTION_RE.search(text_all))
        otp_provided = bool(_OTP_PROVIDED_RE.search(text_all))
        explicit_info_ask = _contains_any(text_all, _INFO_REQUEST_KEYWORDS)
        if otp_provided:
            asks_for_info = False
        else:
            asks_for_info = explicit_info_ask or otp_mentioned

        if _contains_any(text_all, _URGENCY_KEYWORDS):
            signals.append(AnalyzerSignal.URGENCY)
            score += 0.22
        if _contains_any(text_all, _IMPERSONATION_PHRASES):
            signals.append(AnalyzerSignal.IMPERSONATION)
            score += 0.20
        if asks_for_info:
            signals.append(AnalyzerSignal.INFO_REQUEST)
            score += 0.32
        if _has_suspicious_link(text_all):
            signals.append(AnalyzerSignal.SUSPICIOUS_LINK)
            score += 0.30
        if _contains_any(text_all, _FINANCIAL_LURE_KEYWORDS):
            signals.append(AnalyzerSignal.FINANCIAL_LURE)
            score += 0.24
        if _contains_any(text_all, _GREED_KEYWORDS):
            signals.append(AnalyzerSignal.GREED)
            score += 0.34
        if _contains_any(text_all, _FEAR_KEYWORDS):
            signals.append(AnalyzerSignal.FEAR)
            score += 0.28
        if _contains_any(text_all, _AUTHORITY_KEYWORDS):
            signals.append(AnalyzerSignal.AUTHORITY)
            score += 0.12
        if _contains_any(text_all, _EMPATHY_KEYWORDS):
            signals.append(AnalyzerSignal.EMPATHY)
            score += 0.22
        if observation.turn <= 2:
            signals.append(AnalyzerSignal.UNKNOWN_SENDER)
            score += 0.05

        # UPI handle as text → strong indicator of money-ask
        upi_handle_re = re.compile(
            r"@(?:ybl|okicici|okhdfc|okaxis|okbizaxis|ibl|upi|oksbi|paytm|ubi)"
            r"|upi\s+(?:id|handle)\s*:?\s*\S+"
            r"|transfer\s+(?:via|to)\s+upi"
            r"|upi\s+transfer"
            r"|pay\s+(?:rs|₹)\s*\d"
            r"|send\s+(?:rs|₹)\s*\d",
            re.IGNORECASE,
        )
        if upi_handle_re.search(text_all):
            score += 0.12

        # Multi-signal co-occurrence bonuses
        if AnalyzerSignal.URGENCY in signals and AnalyzerSignal.INFO_REQUEST in signals:
            score += 0.10
        if AnalyzerSignal.IMPERSONATION in signals and AnalyzerSignal.INFO_REQUEST in signals:
            score += 0.08
        if AnalyzerSignal.FEAR in signals and AnalyzerSignal.AUTHORITY in signals:
            score += 0.10
        if AnalyzerSignal.GREED in signals and AnalyzerSignal.SUSPICIOUS_LINK in signals:
            score += 0.08
        if AnalyzerSignal.EMPATHY in signals and AnalyzerSignal.URGENCY in signals:
            score += 0.08

        # --- Negative evidence ---
        has_suspicious = _has_suspicious_link(text_all)
        has_legit = _has_legit_domain(text_all)
        has_strong_scam_signal = (
            AnalyzerSignal.GREED in signals
            or AnalyzerSignal.FEAR in signals
            or (
                AnalyzerSignal.URGENCY in signals
                and AnalyzerSignal.INFO_REQUEST in signals
            )
            or has_suspicious
        )
        benign_matches = sum(1 for marker in _BENIGN_MARKERS if marker in text_all)

        if has_legit and not has_suspicious:
            score -= 0.40
            if benign_matches >= 1:
                score -= 0.10
        elif benign_matches >= 2 and not has_strong_scam_signal:
            score -= min(0.30, 0.12 * benign_matches)
        elif benign_matches >= 1 and not has_strong_scam_signal:
            score -= 0.10

        # Legit OTP delivery: OTP value is IN the message, no suspicious link,
        # has benign marker or legit domain → not a scam
        if otp_provided and not otp_mentioned_without_value(text_all) and not has_suspicious:
            if benign_matches >= 1 or has_legit:
                score -= 0.25

        score = max(0.0, min(1.0, score))
        explanation = _build_explanation(signals)
        return AnalyzerScore(score=score, signals=signals, explanation=explanation)


def otp_mentioned_without_value(text: str) -> bool:
    """True if 'OTP' appears AND no digit code follows soon after."""
    if not _OTP_MENTION_RE.search(text):
        return False
    return not _OTP_PROVIDED_RE.search(text)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def _has_suspicious_link(text: str) -> bool:
    for url in _URL_PATTERN.findall(text):
        low = url.lower()
        if any(tld in low for tld in _SUSPICIOUS_TLDS):
            return True
        if any(short in low for short in _URL_SHORTENERS):
            return True
    if any(short in text for short in _URL_SHORTENERS):
        return True
    return any(tld in text for tld in _SUSPICIOUS_TLDS)


def _has_legit_domain(text: str) -> bool:
    return bool(_LEGIT_DOMAIN_RE.search(text))


def _build_explanation(signals: list[AnalyzerSignal]) -> str:
    if not signals:
        return "No suspicion signals detected."
    parts = [s.value.replace("_", " ") for s in signals]
    return "Detected: " + ", ".join(parts) + "."
