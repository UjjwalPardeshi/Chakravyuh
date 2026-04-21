"""GRPO training loop for the Chakravyuh Analyzer LoRA.

Produces a LoRA adapter on Qwen2.5-7B-Instruct optimized via TRL's GRPO
against a composite reward:
    R = +1.0 × detection_correctness         (scam flagged / benign approved)
        +0.4 × explanation_quality            (Llama-3-70B judge, optional)
        -0.5 × 𝟙[false_positive]              (benign mislabeled)
        -0.3 × calibration_penalty            (|predicted - ground_truth|)

Design:
  - Prompts are drawn from our 200-template attack library + benign control set
  - Each prompt has an implicit ground truth (scam category or benign)
  - GRPO samples 4–8 completions per prompt, computes per-completion reward,
    then updates the policy toward high-reward completions
  - KL penalty keeps us close to base Qwen (prevents mode collapse)
  - Unsloth accelerates 2–4× vs plain transformers

Usage:
    # Local smoke test (CPU fallback)
    python -m training.grpo_analyzer --episodes 8 --no-unsloth --dry-run

    # On RunPod A100
    python -m training.grpo_analyzer \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --episodes 200 \\
        --output checkpoints/analyzer_lora \\
        --wandb-project chakravyuh-run-1

Pre-flight checklist (Day 2 morning):
    1. `pip install -e '.[llm,train]'`
    2. Set GROQ_API_KEY for explanation judge (optional)
    3. `python -m training.grpo_analyzer --dry-run` to verify pipeline
    4. `python -m training.grpo_analyzer --episodes 50` for smoke test
    5. `python -m training.grpo_analyzer --episodes 200` for checkpoint
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from chakravyuh_env.agents.llm_analyzer import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT_TEMPLATE,
    parse_analyzer_response,
)
from chakravyuh_env.explanation_judge import build_judge
from chakravyuh_env.schemas import AnalyzerSignal

logger = logging.getLogger("chakravyuh.grpo")

_ENV_DIR = Path(__file__).resolve().parent.parent / "chakravyuh_env"

DEFAULT_TEMPLATES_PATH = _ENV_DIR / "scammer_templates.json"
DEFAULT_BENIGN_PATH = _ENV_DIR / "benign_templates.json"
DEFAULT_PARAPHRASE_PATH = _ENV_DIR / "paraphrase_templates.json"
DEFAULT_REGIONAL_PATH = _ENV_DIR / "regional_templates.json"
DEFAULT_MULTITURN_PATH = _ENV_DIR / "multiturn_templates.json"
DEFAULT_AUGMENTED_PATH = _ENV_DIR / "augmented_templates.json"

# Test-set path — used ONLY to verify no overlap with training data, never for training.
TEST_SET_PATH = Path("data/chakravyuh-bench-v0/scenarios.jsonl")


# ---------------------------------------------------------------------------
# Training prompt dataset
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainingExample:
    prompt_text: str   # The scammer message (or benign control)
    is_scam: bool
    category: str      # scam category, or "benign"
    signals: tuple[str, ...] = ()


def _flat_template_to_prompt(t: dict) -> tuple[str, list[str]]:
    """Render one scammer_templates.json / paraphrase_templates.json entry as a
    single prompt string + derived signal list."""
    parts: list[str] = []
    if t.get("opener"):
        parts.append(t["opener"])
    if t.get("info_request"):
        parts.append(f"Please share your {t['info_request']}.")
    if t.get("escalation"):
        parts.append(t["escalation"])
    prompt = "\n".join(parts).strip()

    # Prefer explicit `signals` if the template declares them, else derive.
    if t.get("signals"):
        signals = list(t["signals"])
    else:
        signals = []
        if t.get("info_request"):
            signals.append(AnalyzerSignal.INFO_REQUEST.value)
        if t.get("impersonation"):
            signals.append(AnalyzerSignal.IMPERSONATION.value)
        if t.get("link"):
            signals.append(AnalyzerSignal.SUSPICIOUS_LINK.value)
        intent = t.get("intent")
        if intent == "urgency":
            signals.append(AnalyzerSignal.URGENCY.value)
        elif intent == "fear":
            signals.append(AnalyzerSignal.FEAR.value)
        elif intent == "greed":
            signals.append(AnalyzerSignal.GREED.value)
        elif intent == "empathy":
            signals.append(AnalyzerSignal.EMPATHY.value)
        elif intent == "authority":
            signals.append(AnalyzerSignal.AUTHORITY.value)
    return prompt, signals


def _multiturn_to_prompt(t: dict) -> tuple[str, list[str]]:
    """Render a multi-turn scenario as a chronological message stream."""
    turns = t.get("turns", [])
    prompt_lines = [f"[Message {i + 1}] {text}" for i, text in enumerate(turns)]
    prompt = "\n".join(prompt_lines).strip()
    signals = list(t.get("signals", []))
    return prompt, signals


def _load_json_templates(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f).get("templates", [])


def _normalize_for_overlap(text: str) -> str:
    """Case-insensitive, whitespace-collapsed form used for leakage detection."""
    return " ".join(text.lower().split())


def _load_test_set_scammer_texts(test_path: Path = TEST_SET_PATH) -> set[str]:
    """Load every scammer utterance from the benchmark test set (normalized).

    Used ONLY by `_filter_soft_leakage` to drop training templates whose
    wording appears in the published test set.
    """
    texts: set[str] = set()
    if not test_path.exists():
        return texts
    with test_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scenario = json.loads(line)
            for step in scenario.get("attack_sequence", []):
                if step.get("sender") == "scammer":
                    texts.add(_normalize_for_overlap(step.get("text", "")))
    return texts


def _filter_soft_leakage(
    templates: list[dict], test_texts: set[str], min_chars: int = 40
) -> tuple[list[dict], int]:
    """Drop any canonical template whose opener or escalation appears as a
    substring of any test-set scammer text.

    The benchmark scenarios were authored from the canonical-template
    patterns. 41/200 canonical openers appear verbatim inside test
    scenarios — which is not full-text leakage but is *soft* leakage: the
    LoRA would see verbatim n-grams at training time that also appear at
    test time. Filtering these out at training load time gives a
    methodologically clean training corpus.

    Returns (surviving_templates, n_filtered).
    """
    surviving: list[dict] = []
    filtered = 0
    for t in templates:
        candidates = [t.get("opener", ""), t.get("escalation", "")]
        overlapping = False
        for c in candidates:
            n = _normalize_for_overlap(c)
            if len(n) < min_chars:
                continue
            for t_text in test_texts:
                if n in t_text:
                    overlapping = True
                    break
            if overlapping:
                break
        if overlapping:
            filtered += 1
        else:
            surviving.append(t)
    return surviving, filtered


def build_training_examples(
    templates_path: Path = DEFAULT_TEMPLATES_PATH,
    benign_path: Path = DEFAULT_BENIGN_PATH,
    paraphrase_path: Path = DEFAULT_PARAPHRASE_PATH,
    regional_path: Path = DEFAULT_REGIONAL_PATH,
    multiturn_path: Path = DEFAULT_MULTITURN_PATH,
    augmented_path: Path = DEFAULT_AUGMENTED_PATH,
    benign_ratio: float = 0.2,
    seed: int = 42,
) -> list[TrainingExample]:
    """Build the training corpus from 5 synthetic template sources.

    Scam sources:
      - scammer_templates.json   : 200 canonical templates (5 categories × 40)
      - paraphrase_templates.json: 40 reworded variants (robustness)
      - regional_templates.json  : 15 regional-language variants (Tamil/Telugu/…)
      - multiturn_templates.json : 10 multi-turn sequences

    Benign source:
      - benign_templates.json    : hand-written legit Indian SMS

    **Crucially disjoint from chakravyuh-bench-v0 test set** — verified by
    tests/test_training_data.py (zero text overlap). This avoids test-set
    contamination and makes LoRA-vs-baseline comparisons methodologically sound.
    """
    rng = random.Random(seed)
    examples: list[TrainingExample] = []

    # Load test set texts once, for soft-leakage filtering of canonical templates.
    # The paraphrase/regional/multiturn sources were hand-written post-benchmark
    # and are already guaranteed disjoint, so they skip the filter.
    test_texts = _load_test_set_scammer_texts(TEST_SET_PATH)

    # --- Scam examples from all scam sources ---
    for source_path, kind in (
        (templates_path, "canonical"),
        (paraphrase_path, "paraphrase"),
        (augmented_path, "augmented"),
        (regional_path, "regional"),
    ):
        raw_templates = _load_json_templates(source_path)
        if kind == "canonical" and test_texts:
            filtered, n_drop = _filter_soft_leakage(raw_templates, test_texts)
            if n_drop:
                logger.info(
                    "Filtered %d/%d canonical templates whose opener/escalation "
                    "overlap test-set text (soft leakage)",
                    n_drop, len(raw_templates),
                )
            raw_templates = filtered
        for t in raw_templates:
            prompt, signals = _flat_template_to_prompt(t)
            if not prompt:
                continue
            examples.append(
                TrainingExample(
                    prompt_text=prompt,
                    is_scam=True,
                    category=t.get("category", "unknown"),
                    signals=tuple(signals),
                )
            )
    for t in _load_json_templates(multiturn_path):
        prompt, signals = _multiturn_to_prompt(t)
        if not prompt:
            continue
        examples.append(
            TrainingExample(
                prompt_text=prompt,
                is_scam=True,
                category=t.get("category", "unknown"),
                signals=tuple(signals),
            )
        )

    n_scams = len(examples)
    if n_scams == 0:
        raise RuntimeError(
            "No scam training examples loaded. Check that "
            f"{templates_path} exists."
        )

    # --- Benign examples (target benign_ratio of total) ---
    benign_templates = _load_json_templates(benign_path)
    if not benign_templates:
        logger.warning(
            "No benign templates at %s — training will be scam-only, "
            "which biases LoRA toward over-flagging. Create "
            "chakravyuh_env/benign_templates.json.",
            benign_path,
        )
    else:
        target_n_benign = int(n_scams * benign_ratio / (1 - benign_ratio))
        # Shuffle benign pool then sample with replacement if needed for ratio.
        pool = list(benign_templates)
        rng.shuffle(pool)
        selected: list[dict] = []
        while len(selected) < target_n_benign:
            selected.extend(pool)
            if len(pool) == 0:
                break
        for b in selected[:target_n_benign]:
            text = b.get("text", "").strip()
            if not text:
                continue
            examples.append(
                TrainingExample(
                    prompt_text=text,
                    is_scam=False,
                    category="benign",
                    signals=(),
                )
            )

    rng.shuffle(examples)
    return examples


def examples_to_hf_dataset(examples: list[TrainingExample]) -> Any:
    """Convert to a Hugging Face Datasets object for TRL."""
    from datasets import Dataset  # type: ignore[import-not-found]

    rows = [
        {
            "prompt": _build_instruction_prompt(ex.prompt_text),
            "is_scam": ex.is_scam,
            "category": ex.category,
            "signals": list(ex.signals),
        }
        for ex in examples
    ]
    return Dataset.from_list(rows)


# ---------------------------------------------------------------------------
# Prompt template used at TRAINING time
#
# IMPORTANT: must match LLMAnalyzer's inference prompt exactly, else the LoRA
# trains on one distribution and evaluates on another. We reuse the same
# constants (DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT_TEMPLATE) so prompt
# drift is impossible.
# ---------------------------------------------------------------------------


def _build_instruction_prompt(scammer_text: str) -> str:
    """The string we hand to GRPOTrainer as each row's 'prompt'.

    Produces the same Qwen2.5 ChatML string that `LLMAnalyzer.build_prompt()`
    yields at inference time, modulo the formatted {chat} body (inference
    passes dash-bulleted lines; training passes the raw template text).
    """
    chat_body = "\n".join(f"- {line}" for line in scammer_text.split("\n") if line.strip())
    user_msg = DEFAULT_USER_PROMPT_TEMPLATE.format(chat=chat_body or "- (no messages)")
    return (
        f"<|im_start|>system\n{DEFAULT_SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


# ---------------------------------------------------------------------------
# Reward function (pure — testable without a model)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RewardParts:
    detection: float
    calibration: float
    explanation: float
    false_positive_penalty: float
    signal_bonus: float
    total: float


def compute_reward(
    completion: str,
    ground_truth: TrainingExample,
    explanation_judge: Any | None = None,
) -> RewardParts:
    """Reward a single completion given its ground truth.

    Total reward is bounded in roughly [-0.5, +1.7].
    """
    score, signals, explanation = parse_analyzer_response(completion)

    # Detection: +1 if correctly classified, -0.5 if wrong
    predicted_scam = score >= 0.5
    if predicted_scam == ground_truth.is_scam:
        detection_r = 1.0
    else:
        detection_r = -0.5

    # False positive: extra penalty for flagging benign
    fp_penalty = 0.0
    if not ground_truth.is_scam and predicted_scam:
        fp_penalty = -0.3

    # Calibration: reward scores close to target (1.0 for scam, 0.0 for benign)
    target = 1.0 if ground_truth.is_scam else 0.0
    calibration_r = 0.3 * (1.0 - abs(score - target))

    # Signal bonus: reward naming the expected signals
    signal_bonus = 0.0
    if ground_truth.signals and signals:
        matched = set(signals) & set(ground_truth.signals)
        signal_bonus = 0.2 * len(matched) / max(1, len(ground_truth.signals))

    # Explanation quality (optional, +0.4 max)
    explanation_r = 0.0
    if explanation_judge is not None and explanation.strip():
        try:
            exp_score = explanation_judge.score(
                message=ground_truth.prompt_text, explanation=explanation
            )
            explanation_r = exp_score.total * 0.4
        except Exception as e:  # noqa: BLE001
            logger.debug("Explanation judge error (non-fatal): %s", e)

    total = detection_r + fp_penalty + calibration_r + signal_bonus + explanation_r

    return RewardParts(
        detection=round(detection_r, 4),
        calibration=round(calibration_r, 4),
        explanation=round(explanation_r, 4),
        false_positive_penalty=round(fp_penalty, 4),
        signal_bonus=round(signal_bonus, 4),
        total=round(total, 4),
    )


# ---------------------------------------------------------------------------
# Training orchestration
# ---------------------------------------------------------------------------


def train(
    model_name: str = "Qwen/Qwen2.5-7B-Instruct",
    episodes: int = 200,
    output_dir: Path = Path("checkpoints/analyzer_lora"),
    use_unsloth: bool = True,
    lora_rank: int = 16,
    lora_alpha: int = 32,
    learning_rate: float = 1e-5,
    batch_size: int = 4,
    grad_accum: int = 2,
    num_generations: int = 4,
    beta: float = 0.04,          # KL penalty
    max_prompt_length: int = 512,
    max_completion_length: int = 256,
    wandb_project: str | None = "chakravyuh-run-1",
    seed: int = 42,
    dry_run: bool = False,
    resume_from_checkpoint: bool = False,
) -> None:
    """Main training entrypoint. `dry_run=True` only builds dataset + reward."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    examples = build_training_examples(seed=seed)
    logger.info(
        "Built %d training examples (%d scam / %d benign)",
        len(examples),
        sum(1 for e in examples if e.is_scam),
        sum(1 for e in examples if not e.is_scam),
    )

    if dry_run:
        logger.info("Dry-run: skipping model loading and training")
        # Sanity-check the reward function on 5 mock completions
        for ex in examples[:3]:
            mock_completion = (
                '{"score": 0.9, "signals": ["urgency", "info_request"], '
                '"explanation": "OTP + urgency combo."}'
            )
            parts = compute_reward(mock_completion, ex)
            logger.info(
                "  [%s] total=%.3f (%s)",
                ex.category, parts.total, asdict(parts)
            )
        logger.info("Dry-run complete.")
        return

    # Heavy imports only when actually training
    model, tokenizer = _load_training_model(model_name, use_unsloth, lora_rank, lora_alpha)

    from trl import GRPOConfig, GRPOTrainer  # type: ignore[import-not-found]

    # Truncate episode count to dataset size if smaller
    dataset_all = examples_to_hf_dataset(examples)
    n_steps = min(episodes, len(examples))
    train_ds = dataset_all.select(range(n_steps))

    judge = build_judge(mock=False)

    # TRL's reward_funcs signature: (prompts, completions, **kwargs) -> list[float]
    def reward_fn(prompts: list[str], completions: list[str], **kwargs: Any) -> list[float]:
        rewards: list[float] = []
        is_scam_col: list[bool] = kwargs.get("is_scam", [])
        category_col: list[str] = kwargs.get("category", [])
        signals_col: list[list[str]] = kwargs.get("signals", [])
        for i, completion in enumerate(completions):
            # Build a TrainingExample from the row batch columns
            ex = TrainingExample(
                prompt_text=prompts[i][:400] if i < len(prompts) else "",
                is_scam=bool(is_scam_col[i]) if i < len(is_scam_col) else True,
                category=category_col[i] if i < len(category_col) else "unknown",
                signals=tuple(signals_col[i]) if i < len(signals_col) else (),
            )
            parts = compute_reward(completion, ex, explanation_judge=judge)
            rewards.append(parts.total)
        return rewards

    cfg = GRPOConfig(
        output_dir=str(output_dir),
        num_train_epochs=1,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=learning_rate,
        logging_steps=10,
        save_steps=max(1, n_steps // 4),
        num_generations=num_generations,
        max_prompt_length=max_prompt_length,
        max_completion_length=max_completion_length,
        beta=beta,
        seed=seed,
        report_to="wandb" if wandb_project else "none",
        run_name=f"grpo-analyzer-ep{n_steps}",
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        reward_funcs=[reward_fn],
        args=cfg,
    )

    if wandb_project:
        import wandb  # type: ignore[import-not-found]

        wandb.init(project=wandb_project, name=cfg.run_name)

    logger.info("Launching GRPO training for %d steps...", n_steps)
    trainer.train(resume_from_checkpoint=resume_from_checkpoint or None)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    logger.info("Training complete. Adapter saved to %s", output_dir)


def _load_training_model(
    model_name: str, use_unsloth: bool, lora_rank: int, lora_alpha: int
) -> tuple[Any, Any]:
    """Load the base model + attach a trainable LoRA adapter."""
    if use_unsloth:
        try:
            from unsloth import FastLanguageModel  # type: ignore[import-not-found]

            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_name,
                max_seq_length=1024,
                dtype=None,
                load_in_4bit=True,
            )
            model = FastLanguageModel.get_peft_model(
                model,
                r=lora_rank,
                target_modules=[
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                ],
                lora_alpha=lora_alpha,
                use_gradient_checkpointing="unsloth",
                random_state=42,
            )
            return model, tokenizer
        except ImportError:
            logger.warning("Unsloth not installed; falling back to plain PEFT.")

    # PEFT fallback — loads the base model in 4-bit via bitsandbytes so T4 can
    # fit Qwen2.5-3B + TRL's GRPO deepcopy'd reference model in ~14 GB VRAM.
    # Without 4-bit, the reference-model deepcopy at GRPOTrainer init OOMs.
    import torch  # type: ignore[import-not-found]
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # type: ignore[import-not-found]
    from transformers import (  # type: ignore[import-not-found]
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # T4 is Turing (sm_75) — no bfloat16 support. Use float16 compute dtype.
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        trust_remote_code=True,
        quantization_config=bnb_config,
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_alpha,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    return model, tokenizer


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GRPO Analyzer training")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("checkpoints/analyzer_lora"))
    parser.add_argument("--no-unsloth", action="store_true")
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--grad-accum", type=int, default=2)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--beta", type=float, default=0.04, help="KL penalty")
    parser.add_argument("--wandb-project", default="chakravyuh-run-1")
    parser.add_argument("--no-wandb", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Resume from latest checkpoint in --output dir")
    args = parser.parse_args(argv)

    train(
        model_name=args.model,
        episodes=args.episodes,
        output_dir=args.output,
        use_unsloth=not args.no_unsloth,
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        num_generations=args.num_generations,
        beta=args.beta,
        wandb_project=None if args.no_wandb else args.wandb_project,
        seed=args.seed,
        dry_run=args.dry_run,
        resume_from_checkpoint=args.resume,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
