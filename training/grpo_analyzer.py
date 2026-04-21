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

from chakravyuh_env.agents.llm_analyzer import parse_analyzer_response
from chakravyuh_env.explanation_judge import build_judge
from chakravyuh_env.schemas import AnalyzerSignal

logger = logging.getLogger("chakravyuh.grpo")

DEFAULT_TEMPLATES_PATH = (
    Path(__file__).resolve().parent.parent
    / "chakravyuh_env"
    / "scammer_templates.json"
)
DEFAULT_BENIGN_PATH = Path("data/chakravyuh-bench-v0/scenarios.jsonl")


# ---------------------------------------------------------------------------
# Training prompt dataset
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainingExample:
    prompt_text: str   # The scammer message (or benign control)
    is_scam: bool
    category: str      # scam category, or "benign"
    signals: tuple[str, ...] = ()


def build_training_examples(
    templates_path: Path = DEFAULT_TEMPLATES_PATH,
    benign_path: Path = DEFAULT_BENIGN_PATH,
    benign_ratio: float = 0.2,
    seed: int = 42,
) -> list[TrainingExample]:
    """Mix 80% scam templates + 20% benign scenarios. Balanced per-category."""
    rng = random.Random(seed)
    examples: list[TrainingExample] = []

    # Scams from templates
    with open(templates_path, encoding="utf-8") as f:
        templates = json.load(f)["templates"]
    for t in templates:
        # Combine opener + escalation so the prompt represents the full attack
        parts = [t.get("opener", "")]
        if t.get("info_request"):
            parts.append(f"Please share your {t['info_request']}.")
        if t.get("escalation"):
            parts.append(t["escalation"])
        prompt = "\n".join(p for p in parts if p)

        # Derive expected signals from the template metadata
        signals: list[str] = []
        if t.get("info_request"):
            signals.append(AnalyzerSignal.INFO_REQUEST.value)
        if t.get("impersonation"):
            signals.append(AnalyzerSignal.IMPERSONATION.value)
        if t.get("link"):
            signals.append(AnalyzerSignal.SUSPICIOUS_LINK.value)
        if t.get("intent") == "urgency":
            signals.append(AnalyzerSignal.URGENCY.value)

        examples.append(
            TrainingExample(
                prompt_text=prompt,
                is_scam=True,
                category=t.get("category", "unknown"),
                signals=tuple(signals),
            )
        )

    # Benign scenarios from Mode C (only 15 of them)
    n_benign = int(len(examples) * benign_ratio / (1 - benign_ratio))
    try:
        with open(benign_path, encoding="utf-8") as f:
            benign_scenarios = [
                json.loads(line) for line in f if line.strip()
            ]
        benign_scenarios = [
            s for s in benign_scenarios if not s["ground_truth"]["is_scam"]
        ]
        # Repeat the small benign pool to get desired ratio
        while len(benign_scenarios) < n_benign and benign_scenarios:
            benign_scenarios.append(rng.choice(benign_scenarios))
        for s in benign_scenarios[:n_benign]:
            text = "\n".join(
                msg["text"] for msg in s["attack_sequence"]
                if msg["sender"] == "scammer"
            )
            examples.append(
                TrainingExample(
                    prompt_text=text,
                    is_scam=False,
                    category="benign",
                    signals=(),
                )
            )
    except FileNotFoundError:
        logger.warning("Benign set not found at %s — training on scams only", benign_path)

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
# ---------------------------------------------------------------------------


SYSTEM_PROMPT_TRAIN = """You are Chakravyuh's Behavioral Analyzer. \
Score messages 0.0 (safe) to 1.0 (scam). Output JSON: \
{"score": <0-1>, "signals": [...], "explanation": "<30 words>"}"""


def _build_instruction_prompt(scammer_text: str) -> str:
    """The string we hand to GRPOTrainer as each row's 'prompt'."""
    return (
        f"<|im_start|>system\n{SYSTEM_PROMPT_TRAIN}<|im_end|>\n"
        f"<|im_start|>user\nMessages:\n{scammer_text}<|im_end|>\n"
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
    trainer.train()
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

    from peft import LoraConfig, get_peft_model  # type: ignore[import-not-found]
    from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore[import-not-found]

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        trust_remote_code=True,
    )
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
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
