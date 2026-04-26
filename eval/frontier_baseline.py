"""Frontier LLM baseline runner against `chakravyuh-bench-v0`.

Runs LLM analyzers through the EXACT SAME AnalyzerProtocol the Mode C runner
uses. Produces a comparison CSV + bootstrap 95% CIs + pairwise permutation
tests.

Five provider backends (paid ones skip gracefully if the API key is missing):

  - **OpenAI** — proprietary frontier (GPT-4o, GPT-4o-mini). Paid; needs
    `OPENAI_API_KEY`. Out-of-scope for HF compute credits.
  - **Anthropic** — Claude family. Paid; needs `ANTHROPIC_API_KEY`. Out-of-scope
    for HF compute credits.
  - **Gemini** — Google Gemini. Paid; needs `GEMINI_API_KEY`. Out-of-scope for
    HF compute credits.
  - **Groq** — open-weight Llama-3.3-70B etc. **Free tier** at console.groq.com;
    needs `GROQ_API_KEY`. **No HF credits required.**
  - **HuggingFace Inference Providers (`hf`)** — open-weight frontier
    (Llama-3.1-405B, Qwen3-72B, DeepSeek-V3, Mistral-Large, etc.) routed
    through `https://router.huggingface.co/v1`. Pay-per-token from your
    HF compute credits — typical bench run is ~$0.50 to $2 of credits.
    Needs `HF_TOKEN` (your normal HF Hub token).

Design:
  - Each provider is an independent class implementing `score_text(str) -> float`.
  - Providers skip gracefully if their API key / SDK is missing.
  - All providers use OpenAI-compatible JSON output where supported.
  - Rate-limited + retried with exponential backoff.
  - Results cached per (provider, scenario_id) so partial runs resume.

Usage:
    # Free path — Groq's hosted Llama-3.3-70B, no HF credits, no money:
    export GROQ_API_KEY=gsk_...
    python -m eval.frontier_baseline --providers groq --limit 30

    # HF Inference Providers — open-weight frontier paid from your HF credits:
    export HF_TOKEN=hf_...
    python -m eval.frontier_baseline --providers hf --limit 30
    python -m eval.frontier_baseline --providers hf --hf-models \\
        meta-llama/Llama-3.3-70B-Instruct \\
        meta-llama/Llama-3.1-405B-Instruct \\
        Qwen/Qwen3-72B-Instruct \\
        deepseek-ai/DeepSeek-V3-0324 --limit 30

    # Proprietary frontier — paid separately, NOT from HF credits:
    python -m eval.frontier_baseline --providers openai anthropic gemini

    # Combined:
    python -m eval.frontier_baseline --providers groq hf openai anthropic gemini
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eval.bootstrap_ci import bootstrap_ci, cohens_d, permutation_test
from eval.mode_c_real_cases import (
    DEFAULT_DATASET,
    ScriptedAnalyzerAdapter,
    aggregate,
    load_dataset,
    run_eval,
)

logger = logging.getLogger("chakravyuh.frontier")

CACHE_DIR = Path("logs/frontier_cache")
RESULTS_CSV = Path("logs/frontier_comparison.csv")


# ---------------------------------------------------------------------------
# Common prompt (identical across providers to ensure fair comparison)
# ---------------------------------------------------------------------------

FRONTIER_SYSTEM_PROMPT = """You are a fraud detection analyzer for Indian UPI payments. \
Score incoming messages for how likely they are to be scams.

Output strict JSON only:
{"score": <float 0.0 to 1.0>, "explanation": "<one sentence why>"}

0.0 = clearly legitimate
0.3 = some mild concern
0.7 = likely scam
1.0 = definite scam with OTP / Aadhaar / money request"""


_SCORE_PATTERN = re.compile(r'"?score"?\s*:\s*([0-9]*\.?[0-9]+)')
_JSON_OBJ = re.compile(r"\{[^{}]*\}", re.DOTALL)
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)
_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _strip_reasoning(raw: str) -> str:
    """Remove <think>...</think> blocks emitted by chain-of-thought models.

    DeepSeek-R1, o1-class, and other reasoning models prepend their answer with
    a thinking section. Without stripping, the JSON-extraction regex can latch
    onto malformed JSON-like substrings inside the reasoning, or — if the
    model hits the token cap mid-thought — find no closing JSON at all.
    """
    cleaned = _THINK_BLOCK.sub("", raw)
    if "<think>" in cleaned.lower():
        cleaned = _THINK_OPEN.sub("", cleaned)
    return cleaned.strip()


def parse_frontier_score(raw: str) -> float:
    """Extract score from any provider's response. Forgiving.

    Order of attempts:
    1. Strip reasoning-model `<think>` blocks first.
    2. Prefer JSON inside ```json ... ``` fenced blocks (some models wrap output).
    3. Fall back to the first `{...}` JSON object.
    4. Fall back to a regex match on `"score": <num>`.
    """
    cleaned = _strip_reasoning(raw)
    fenced = _FENCED_JSON.search(cleaned)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            s = float(data.get("score", 0.0))
            return max(0.0, min(1.0, s))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    try:
        m = _JSON_OBJ.search(cleaned)
        if m:
            data = json.loads(m.group(0))
            s = float(data.get("score", 0.0))
            return max(0.0, min(1.0, s))
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    m = _SCORE_PATTERN.search(cleaned)
    if m:
        try:
            return max(0.0, min(1.0, float(m.group(1))))
        except ValueError:
            pass
    return 0.0


# ---------------------------------------------------------------------------
# Base provider
# ---------------------------------------------------------------------------


@dataclass
class ProviderSpec:
    name: str                  # display name — e.g. "gpt-4o-mini"
    cost_per_1k_in: float = 0.0
    cost_per_1k_out: float = 0.0


class FrontierProvider(ABC):
    """Minimal provider interface. Implements AnalyzerProtocol via score_text."""

    spec: ProviderSpec

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def _complete(self, user_msg: str) -> str: ...

    def score_text(self, text: str) -> float:
        """Score a single scammer message. Cached + rate-limited."""
        cache_key = f"{self.spec.name}:{_cache_key(text)}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        for attempt in range(3):
            try:
                raw = self._complete(f"Message: {text[:800]}\nReturn JSON only.")
                score = parse_frontier_score(raw)
                _cache_set(cache_key, score)
                return score
            except Exception as e:  # noqa: BLE001
                logger.warning("%s attempt %d failed: %s", self.spec.name, attempt + 1, e)
                time.sleep(1.5 ** attempt)
        return 0.0


# ---------------------------------------------------------------------------
# Concrete providers
# ---------------------------------------------------------------------------


class OpenAIProvider(FrontierProvider):
    """OpenAI GPT family (paid). Uses the openai package + OPENAI_API_KEY."""

    spec = ProviderSpec(name="gpt-4o-mini", cost_per_1k_in=0.00015, cost_per_1k_out=0.0006)

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.spec = ProviderSpec(name=model)
        self._client: Any = None

    def available(self) -> bool:
        if not os.environ.get("OPENAI_API_KEY"):
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure(self) -> None:
        if self._client is not None:
            return
        from openai import OpenAI  # type: ignore[import-not-found]

        self._client = OpenAI()

    def _complete(self, user_msg: str) -> str:
        self._ensure()
        r = self._client.chat.completions.create(
            model=self.spec.name,
            messages=[
                {"role": "system", "content": FRONTIER_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content or ""


class GroqProvider(FrontierProvider):
    """Groq (free tier, OpenAI-compatible). Uses openai pkg + GROQ_API_KEY."""

    spec = ProviderSpec(name="groq-llama-3.3-70b")

    def __init__(self, model: str = "llama-3.3-70b-versatile") -> None:
        self.spec = ProviderSpec(name=f"groq-{model}")
        self._model = model
        self._client: Any = None

    def available(self) -> bool:
        if not os.environ.get("GROQ_API_KEY"):
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure(self) -> None:
        if self._client is not None:
            return
        from openai import OpenAI  # type: ignore[import-not-found]

        self._client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )

    def _complete(self, user_msg: str) -> str:
        self._ensure()
        r = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": FRONTIER_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=150,
        )
        return r.choices[0].message.content or ""


class HuggingFaceProvider(FrontierProvider):
    """HuggingFace Inference Providers — OpenAI-compatible router at
    `https://router.huggingface.co/v1`. Pay-per-token from HF compute credits.

    Supports any chat-completion model exposed by an HF Inference Provider
    (Together AI, Fireworks, Novita, SambaNova, Cerebras, Hyperbolic, Nebius,
    HF Inference, Featherless AI, etc.) — auto-routes by default. Pin a
    specific provider with the colon syntax, e.g.
    `meta-llama/Llama-3.3-70B-Instruct:together`.

    Default model: `meta-llama/Llama-3.3-70B-Instruct` (cheap, competitive,
    auto-routed). Override via constructor or via the `--hf-models` CLI flag.
    """

    spec = ProviderSpec(name="hf-llama-3.3-70b")

    DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        # Strip optional `:provider` suffix when building the spec name so the
        # CSV / table column stays readable while the API call retains the pin.
        display = model.split(":", 1)[0].split("/", 1)[-1].lower()
        self.spec = ProviderSpec(name=f"hf-{display}")
        self._model = model
        self._client: Any = None

    def available(self) -> bool:
        if not os.environ.get("HF_TOKEN"):
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure(self) -> None:
        if self._client is not None:
            return
        from openai import OpenAI  # type: ignore[import-not-found]

        self._client = OpenAI(
            api_key=os.environ["HF_TOKEN"],
            base_url="https://router.huggingface.co/v1",
        )

    def _complete(self, user_msg: str) -> str:
        self._ensure()
        # Reasoning models (R1, o1-class) need a much larger budget because
        # the thinking block alone can be 1500+ tokens; otherwise the response
        # gets truncated mid-think and never produces JSON.
        is_reasoning = any(
            tag in self._model.lower()
            for tag in ("r1", "deepseek-r", "qwq", "o1-", "o1", "reasoning")
        )
        max_toks = 4096 if is_reasoning else 150
        r = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": FRONTIER_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=max_toks,
        )
        return r.choices[0].message.content or ""


class AnthropicProvider(FrontierProvider):
    """Anthropic Claude. Uses `anthropic` pkg + ANTHROPIC_API_KEY."""

    spec = ProviderSpec(name="claude-haiku")

    def __init__(self, model: str = "claude-3-5-haiku-latest") -> None:
        self.spec = ProviderSpec(name=model)
        self._client: Any = None

    def available(self) -> bool:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure(self) -> None:
        if self._client is not None:
            return
        import anthropic  # type: ignore[import-not-found]

        self._client = anthropic.Anthropic()

    def _complete(self, user_msg: str) -> str:
        self._ensure()
        r = self._client.messages.create(
            model=self.spec.name,
            max_tokens=150,
            temperature=0.0,
            system=FRONTIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        # Anthropic returns a list of content blocks; we want text
        parts: list[str] = []
        for block in r.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)


class GeminiProvider(FrontierProvider):
    """Google Gemini via the google-generativeai pkg + GEMINI_API_KEY."""

    spec = ProviderSpec(name="gemini-2.0-flash")

    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        self.spec = ProviderSpec(name=model)
        self._model_obj: Any = None

    def available(self) -> bool:
        if not os.environ.get("GEMINI_API_KEY"):
            return False
        try:
            import google.generativeai  # noqa: F401
        except ImportError:
            return False
        return True

    def _ensure(self) -> None:
        if self._model_obj is not None:
            return
        import google.generativeai as genai  # type: ignore[import-not-found]

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self._model_obj = genai.GenerativeModel(
            model_name=self.spec.name,
            system_instruction=FRONTIER_SYSTEM_PROMPT,
        )

    def _complete(self, user_msg: str) -> str:
        self._ensure()
        r = self._model_obj.generate_content(
            user_msg,
            generation_config={"temperature": 0.0, "max_output_tokens": 150},
        )
        return getattr(r, "text", "") or ""


PROVIDER_REGISTRY: dict[str, type[FrontierProvider]] = {
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "hf": HuggingFaceProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}


# ---------------------------------------------------------------------------
# Cache (per-scenario-hash to avoid re-paying API $)
# ---------------------------------------------------------------------------


def _cache_key(text: str) -> str:
    import hashlib

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _cache_get(key: str) -> float | None:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return float(json.loads(path.read_text()).get("score"))
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
    return None


def _cache_set(key: str, score: float) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps({"score": score}))


# ---------------------------------------------------------------------------
# Comparison runner
# ---------------------------------------------------------------------------


@dataclass
class ProviderResult:
    provider: str
    detection_rate: float
    false_positive_rate: float
    precision: float
    f1: float
    n: int
    ci_low: float
    ci_high: float
    per_category_detection: dict[str, float] = field(default_factory=dict)


def _build_provider_lineup(
    provider_names: list[str],
    hf_models: list[str] | None = None,
) -> list[tuple[str, FrontierProvider | str]]:
    """Expand `--providers` + `--hf-models` into an ordered (name, instance) list.

    Returns "scripted" as a sentinel string at index 0 (handled by the caller).
    For "hf" with a non-empty `hf_models` list, expands to one HuggingFaceProvider
    per model so multiple open-weight comparisons run in a single invocation.
    """
    lineup: list[tuple[str, FrontierProvider | str]] = [("scripted", "scripted")]
    seen: set[str] = {"scripted"}
    for name in provider_names:
        if name == "scripted" or name in seen:
            continue
        seen.add(name)
        if name == "hf" and hf_models:
            for model in hf_models:
                inst = HuggingFaceProvider(model=model)
                lineup.append((inst.spec.name, inst))
            continue
        cls = PROVIDER_REGISTRY.get(name)
        if cls is None:
            logger.warning("Unknown provider '%s' — skipping.", name)
            continue
        lineup.append((name, cls()))
    return lineup


def evaluate_providers(
    provider_names: list[str],
    dataset_path: Path = DEFAULT_DATASET,
    limit: int | None = None,
    bootstrap_n: int = 1000,
    hf_models: list[str] | None = None,
) -> dict[str, ProviderResult]:
    data = load_dataset(dataset_path)
    if limit:
        data = data[:limit]
    results: dict[str, ProviderResult] = {}

    lineup = _build_provider_lineup(provider_names, hf_models=hf_models)

    for name, entry in lineup:
        if entry == "scripted":
            analyzer: Any = ScriptedAnalyzerAdapter()
        else:
            provider = entry  # type: ignore[assignment]
            if not provider.available():
                logger.warning(
                    "Provider '%s' unavailable (missing API key or SDK) — skipping.",
                    name,
                )
                continue
            analyzer = provider

        logger.info("Evaluating %s on %d scenarios...", name, len(data))
        eval_results = run_eval(analyzer, data, threshold=0.5)
        metrics = aggregate(eval_results)
        scam_hits = [
            1.0 if r.predicted_flag else 0.0
            for r in eval_results if r.is_scam_truth
        ]
        _, lo, hi = bootstrap_ci(scam_hits, n_resamples=bootstrap_n, seed=42)

        per_cat = {}
        for r in eval_results:
            cat = r.category
            per_cat.setdefault(cat, {"tp": 0, "total": 0})
            if r.is_scam_truth:
                per_cat[cat]["total"] += 1
                if r.predicted_flag:
                    per_cat[cat]["tp"] += 1
        per_cat_rates = {
            cat: (d["tp"] / d["total"]) if d["total"] else 0.0
            for cat, d in per_cat.items()
        }

        results[name] = ProviderResult(
            provider=name,
            detection_rate=metrics.detection_rate,
            false_positive_rate=metrics.false_positive_rate,
            precision=metrics.precision,
            f1=metrics.f1,
            n=metrics.n,
            ci_low=lo,
            ci_high=hi,
            per_category_detection=per_cat_rates,
        )
        logger.info(
            "  %s: detection=%.1f%% (CI [%.1f%%, %.1f%%]), F1=%.3f",
            name,
            metrics.detection_rate * 100,
            lo * 100,
            hi * 100,
            metrics.f1,
        )
    return results


def save_comparison_csv(results: dict[str, ProviderResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "provider", "n", "detection_rate", "ci_low", "ci_high",
            "false_positive_rate", "precision", "f1",
        ])
        for r in results.values():
            w.writerow([
                r.provider, r.n,
                f"{r.detection_rate:.4f}",
                f"{r.ci_low:.4f}", f"{r.ci_high:.4f}",
                f"{r.false_positive_rate:.4f}",
                f"{r.precision:.4f}", f"{r.f1:.4f}",
            ])


def print_comparison_table(results: dict[str, ProviderResult]) -> None:
    print("\n=== Frontier Baseline Comparison ===")
    print(f"{'Provider':<28} {'Detection':>12} {'95% CI':>22} {'FP':>8} {'F1':>8}")
    print("-" * 84)
    for r in results.values():
        print(
            f"{r.provider:<28} "
            f"{r.detection_rate*100:>10.1f}% "
            f"[{r.ci_low*100:>5.1f}%, {r.ci_high*100:>5.1f}%] "
            f"{r.false_positive_rate*100:>6.1f}% "
            f"{r.f1:>8.3f}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frontier LLM baseline comparison")
    parser.add_argument(
        "--providers",
        nargs="+",
        default=["groq", "hf"],
        choices=list(PROVIDER_REGISTRY.keys()) + ["scripted"],
        help=(
            "Providers to evaluate (skips if API key missing). "
            "'groq' = free Llama-3.3-70B (no HF credits needed); "
            "'hf' = HuggingFace Inference Providers (paid from HF credits)."
        ),
    )
    parser.add_argument(
        "--hf-models",
        nargs="+",
        default=None,
        metavar="MODEL_ID",
        help=(
            "When 'hf' is in --providers, override the default Llama-3.3-70B "
            "with one or more open-weight model IDs hosted on HF Inference "
            "Providers, e.g. meta-llama/Llama-3.1-405B-Instruct "
            "Qwen/Qwen3-72B-Instruct deepseek-ai/DeepSeek-V3-0324. "
            "Each model adds one row to the comparison CSV."
        ),
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--limit", type=int, default=None, help="Scenarios to run")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=RESULTS_CSV)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    results = evaluate_providers(
        provider_names=args.providers,
        dataset_path=args.dataset,
        limit=args.limit,
        bootstrap_n=args.bootstrap,
        hf_models=args.hf_models,
    )
    print_comparison_table(results)
    save_comparison_csv(results, args.output)
    logger.info("Wrote %s", args.output)

    # Pairwise permutation tests vs scripted baseline
    if "scripted" in results and len(results) > 1:
        print("\n=== Permutation Test vs Scripted Baseline ===")
        base_rate = results["scripted"].detection_rate
        for name, r in results.items():
            if name == "scripted":
                continue
            delta = (r.detection_rate - base_rate) * 100
            sign = "+" if delta >= 0 else ""
            print(f"{name:<28} Δ detection = {sign}{delta:.1f}pp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
