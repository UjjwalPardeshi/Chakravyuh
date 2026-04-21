"""LLM-backed Analyzer — Qwen2.5-7B + optional LoRA adapter.

This is the Day-2 drop-in replacement for ScriptedAnalyzer. Exposes the SAME
interface — `act(obs) -> AnalyzerScore` and `score_text(text) -> float` —
so every other piece of the system (env, demo, Mode C eval) works unchanged.

Design principles:
  1. Lazy loading — importing this module is cheap. Model loads on first use.
  2. Deterministic — temperature=0, seed fixed.
  3. Graceful degradation — if transformers/torch unavailable, raise a clear
     error at load time (not import time) so scripted baselines remain usable.
  4. JSON-structured output — prompt the model to return strict JSON,
     parse with a forgiving parser that falls back to regex.

Usage:
    from chakravyuh_env.agents.llm_analyzer import LLMAnalyzer

    analyzer = LLMAnalyzer(
        model_name="Qwen/Qwen2.5-7B-Instruct",
        lora_path="checkpoints/analyzer_lora",  # optional
        use_unsloth=True,
    )
    score = analyzer.score_text("Your SBI KYC expires — share OTP")
    # → 0.94
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from chakravyuh_env.agents.base import Agent
from chakravyuh_env.schemas import (
    AnalyzerScore,
    AnalyzerSignal,
    ChatMessage,
    Observation,
)

logger = logging.getLogger("chakravyuh.llm_analyzer")


DEFAULT_SYSTEM_PROMPT = """You are Chakravyuh's Behavioral Analyzer, a fraud detection AI deployed \
on-device in India to protect users from UPI scams. Your job: score incoming \
scammer messages from 0.0 (safe) to 1.0 (definite scam).

You have deep knowledge of Indian fraud patterns: OTP theft, KYC fraud, \
loan-app fraud, investment fraud, impersonation (bank/govt/family/delivery). \
You understand Hindi + English + regional code-switching.

Output ONLY valid JSON with these exact keys:
{
  "score": <float 0.0 to 1.0>,
  "signals": <list of strings from: urgency, impersonation, info_request, suspicious_link, unusual_amount, unknown_sender, authority, fear, greed, empathy, financial_lure>,
  "explanation": <one sentence, <30 words, plain English>
}"""


DEFAULT_USER_PROMPT_TEMPLATE = """Scammer messages:
{chat}

Analyze these messages. Return strict JSON only."""


_VALID_SIGNAL_NAMES = {s.value for s in AnalyzerSignal}


@dataclass
class LLMAnalyzerConfig:
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    lora_path: str | None = None
    use_unsloth: bool = True
    load_in_4bit: bool = True
    max_new_tokens: int = 200
    temperature: float = 0.0
    top_p: float = 1.0
    device: str = "auto"           # "cuda", "cpu", "auto"
    seed: int = 42
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    user_prompt_template: str = DEFAULT_USER_PROMPT_TEMPLATE
    flag_threshold: float = 0.55


class LLMAnalyzer(Agent):
    """LLM-backed analyzer. Compatible with both the env and Mode C eval."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-7B-Instruct",
        lora_path: str | None = None,
        use_unsloth: bool = True,
        load_in_4bit: bool = True,
        max_new_tokens: int = 200,
        temperature: float = 0.0,
        flag_threshold: float = 0.55,
        seed: int | None = 42,
    ) -> None:
        super().__init__(name="analyzer", seed=seed)
        self.config = LLMAnalyzerConfig(
            model_name=model_name,
            lora_path=lora_path,
            use_unsloth=use_unsloth,
            load_in_4bit=load_in_4bit,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            flag_threshold=flag_threshold,
            seed=seed if seed is not None else 42,
        )
        self.flag_threshold = flag_threshold
        self._model: Any = None
        self._tokenizer: Any = None
        self._ready = False

    # ---- model lifecycle ----

    def load(self) -> None:
        """Actually load the model + tokenizer into memory. Call before `act()`."""
        if self._ready:
            return
        logger.info("Loading LLM analyzer (%s)...", self.config.model_name)
        model, tokenizer = _load_model(self.config)
        self._model = model
        self._tokenizer = tokenizer
        self._ready = True
        logger.info("LLM analyzer ready.")

    def unload(self) -> None:
        """Free model memory (useful in long-running processes)."""
        self._model = None
        self._tokenizer = None
        self._ready = False

    # ---- Agent interface ----

    def act(self, observation: Observation) -> AnalyzerScore:
        score, signals, explanation = self._predict_from_chat(
            observation.chat_history
        )
        return AnalyzerScore(
            score=score,
            signals=[AnalyzerSignal(s) for s in signals if s in _VALID_SIGNAL_NAMES],
            explanation=explanation,
        )

    # ---- Mode C eval interface (AnalyzerProtocol) ----

    def score_text(self, text: str) -> float:
        score, _, _ = self._predict_from_chat(
            [ChatMessage(sender="scammer", turn=1, text=text)]
        )
        return score

    # ---- internals ----

    def _predict_from_chat(
        self, chat: list[ChatMessage]
    ) -> tuple[float, list[str], str]:
        """Full pipeline: build prompt → generate → parse. Never raises."""
        self.load()
        prompt = self.build_prompt(chat)
        raw = self._generate(prompt)
        return parse_analyzer_response(raw)

    def build_prompt(self, chat: list[ChatMessage]) -> str:
        """Construct the model-ready chat prompt. Exposed for testing."""
        scammer_text = "\n".join(
            f"- {m.text}" for m in chat if m.sender == "scammer"
        )
        if not scammer_text.strip():
            scammer_text = "- (no messages yet)"
        user_msg = self.config.user_prompt_template.format(chat=scammer_text)

        if self._tokenizer is None:
            # Offline prompt — used in tests + when model not loaded yet
            return (
                f"<|system|>\n{self.config.system_prompt}\n"
                f"<|user|>\n{user_msg}\n<|assistant|>\n"
            )

        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": user_msg},
        ]
        return self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    def _generate(self, prompt: str) -> str:
        """Run a single deterministic completion through the loaded model."""
        assert self._model is not None and self._tokenizer is not None
        import torch  # local import — only required when model actually runs

        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        with torch.inference_mode():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                do_sample=self.config.temperature > 0.0,
                temperature=max(self.config.temperature, 1e-6),
                top_p=self.config.top_p,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        completion = self._tokenizer.decode(
            output_ids[0][inputs["input_ids"].shape[-1]:],
            skip_special_tokens=True,
        )
        return completion


# ---------------------------------------------------------------------------
# Mock analyzer — for testing paths that require an LLMAnalyzer shape
# without actually loading a 7B model.
# ---------------------------------------------------------------------------


class MockLLMAnalyzer(LLMAnalyzer):
    """Non-loading stand-in that returns a fixed response. Used in tests."""

    def __init__(self, fixed_score: float = 0.85, seed: int | None = 42) -> None:
        super().__init__(seed=seed)
        self._fixed_score = fixed_score
        self._ready = True  # pretend loaded

    def load(self) -> None:
        self._ready = True

    def _predict_from_chat(
        self, chat: list[ChatMessage]
    ) -> tuple[float, list[str], str]:
        # Deterministic mock response for test shape-checking
        return (
            self._fixed_score,
            ["urgency", "info_request"],
            "Mock: urgency + info request detected.",
        )


# ---------------------------------------------------------------------------
# Response parser — pure function, testable without heavy deps
# ---------------------------------------------------------------------------


_JSON_OBJECT_PATTERN = re.compile(r"\{[^{}]*\}", re.DOTALL)
_SCORE_PATTERN = re.compile(r'"?score"?\s*:\s*([0-9]*\.?[0-9]+)')


def parse_analyzer_response(raw: str) -> tuple[float, list[str], str]:
    """Parse an LLM response into (score, signals, explanation).

    Forgiving parser — falls back to regex if the model's JSON is malformed.
    Always returns a valid (score in [0,1], signals list, explanation string).
    """
    # 1. Try strict JSON first
    try:
        match = _JSON_OBJECT_PATTERN.search(raw)
        if match:
            data = json.loads(match.group(0))
            score = float(data.get("score", 0.0))
            score = max(0.0, min(1.0, score))
            signals_raw = data.get("signals", []) or []
            if isinstance(signals_raw, str):
                signals_raw = [signals_raw]
            signals = [
                str(s).strip().lower()
                for s in signals_raw
                if str(s).strip().lower() in _VALID_SIGNAL_NAMES
            ]
            explanation = str(data.get("explanation", ""))[:300]
            return score, signals, explanation
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # 2. Fallback: regex for score, scan for known signal names
    m = _SCORE_PATTERN.search(raw)
    score = float(m.group(1)) if m else 0.0
    score = max(0.0, min(1.0, score))
    signals = [
        name for name in _VALID_SIGNAL_NAMES
        if re.search(rf"\b{re.escape(name)}\b", raw, re.IGNORECASE)
    ]
    explanation = _extract_explanation(raw) or "Parser fallback — unstructured output."
    return score, signals, explanation


def _extract_explanation(text: str) -> str | None:
    m = re.search(r'"?explanation"?\s*:\s*"([^"]+)"', text)
    if m:
        return m.group(1)[:300]
    # Take first sentence
    for line in text.split("\n"):
        line = line.strip()
        if 10 < len(line) < 200:
            return line
    return None


# ---------------------------------------------------------------------------
# Heavy dependency loader — kept isolated so importing this module is cheap
# ---------------------------------------------------------------------------


def _load_model(config: LLMAnalyzerConfig) -> tuple[Any, Any]:
    """Attempt to load the model via Unsloth; fall back to plain transformers."""
    if config.use_unsloth:
        try:
            return _load_via_unsloth(config)
        except ImportError:
            logger.warning("Unsloth unavailable, falling back to transformers.")
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Unsloth load failed (%s); falling back to transformers.", e
            )

    return _load_via_transformers(config)


def _load_via_unsloth(config: LLMAnalyzerConfig) -> tuple[Any, Any]:
    from unsloth import FastLanguageModel  # type: ignore[import-not-found]

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config.model_name,
        max_seq_length=2048,
        dtype=None,  # auto-detect
        load_in_4bit=config.load_in_4bit,
    )
    FastLanguageModel.for_inference(model)

    if config.lora_path:
        from peft import PeftModel  # type: ignore[import-not-found]

        model = PeftModel.from_pretrained(model, config.lora_path)
    return model, tokenizer


def _load_via_transformers(config: LLMAnalyzerConfig) -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore[import-not-found]

    tokenizer = AutoTokenizer.from_pretrained(
        config.model_name, trust_remote_code=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    load_kwargs: dict[str, Any] = {
        "device_map": config.device,
        "trust_remote_code": True,
    }
    if config.load_in_4bit:
        try:
            from transformers import BitsAndBytesConfig  # type: ignore[import-not-found]

            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype="bfloat16",
                bnb_4bit_quant_type="nf4",
            )
        except ImportError:
            logger.warning("bitsandbytes not available; loading fp16.")

    model = AutoModelForCausalLM.from_pretrained(config.model_name, **load_kwargs)

    if config.lora_path:
        from peft import PeftModel  # type: ignore[import-not-found]

        model = PeftModel.from_pretrained(model, config.lora_path)
    return model, tokenizer
