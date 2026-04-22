"""Threshold sweep — score a trained LoRA analyzer once, re-threshold many times.

Use case: you've trained a LoRA and eval at threshold=0.5 shows strong recall but
high FPR (classic over-flagging from reward hacking). Rather than retrain, sweep
the flag threshold across [0.3, 0.4, ..., 0.9] to find the P/R sweet spot.

KEY OPTIMIZATION: the LoRA produces a CONTINUOUS score per scenario. We run it
ONCE across the 175 bench scenarios (~15 min), cache `(scenario_id, score)`, then
apply different thresholds to the cached scores — each re-threshold is <1 second.

Usage:
    # On Colab after training:
    python -m eval.threshold_sweep \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --lora /content/drive/MyDrive/chakravyuh/analyzer_lora \\
        --output /content/drive/MyDrive/chakravyuh/threshold_sweep.json

Output JSON:
    {
      "thresholds": {
        "0.3": {"detection": 1.00, "fpr": 0.48, "precision": 0.88, "f1": 0.94, ...},
        "0.4": {...},
        ...
      },
      "best_by_f1": {"threshold": 0.7, "f1": 0.945, ...},
      "best_by_fpr_under_15": {"threshold": 0.75, ...}
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from chakravyuh_env.agents.llm_analyzer import LLMAnalyzer
from eval.mode_c_real_cases import (
    DEFAULT_DATASET,
    aggregate,
    load_dataset,
    per_category_breakdown,
    per_difficulty_breakdown,
    run_eval,
)

logger = logging.getLogger("chakravyuh.threshold_sweep")

DEFAULT_THRESHOLDS = [0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]


def sweep(
    analyzer: LLMAnalyzer,
    dataset: list[dict],
    thresholds: list[float],
) -> dict:
    """Run inference once, aggregate at each threshold."""
    # One pass: collect continuous scores per scenario.
    base_results = run_eval(analyzer, dataset, threshold=0.5)  # threshold irrelevant here, we re-apply

    # Map for fast re-thresholding.
    logger.info("Scored %d scenarios. Re-thresholding %d cutoffs…", len(base_results), len(thresholds))

    out: dict[str, dict] = {}
    for thr in thresholds:
        # Re-flag every scenario at this threshold.
        rethresh = [
            type(r)(
                scenario_id=r.scenario_id,
                is_scam_truth=r.is_scam_truth,
                predicted_score=r.predicted_score,
                predicted_flag=(r.predicted_score >= thr),
                correct=((r.predicted_score >= thr) == r.is_scam_truth),
                category=r.category,
                difficulty=r.difficulty,
            )
            for r in base_results
        ]
        m = aggregate(rethresh)
        out[f"{thr:.2f}"] = {
            "threshold": thr,
            "n": m.n,
            "detection": round(m.detection_rate, 4),
            "fpr": round(m.false_positive_rate, 4),
            "precision": round(m.precision, 4),
            "recall": round(m.recall, 4),
            "f1": round(m.f1, 4),
            "accuracy": round(m.accuracy, 4),
        }
        logger.info(
            "thr=%.2f  det=%.1f%%  fpr=%.1f%%  P=%.1f%%  F1=%.3f",
            thr, m.detection_rate * 100, m.false_positive_rate * 100,
            m.precision * 100, m.f1,
        )

    return {
        "thresholds": out,
        "best_by_f1": max(out.values(), key=lambda x: x["f1"]),
        "best_by_fpr_under_15": min(
            (v for v in out.values() if v["fpr"] <= 0.15),
            key=lambda x: -x["f1"],
            default=None,
        ),
        "best_by_fpr_under_10": min(
            (v for v in out.values() if v["fpr"] <= 0.10),
            key=lambda x: -x["f1"],
            default=None,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sweep flag thresholds on a trained LoRA analyzer.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--lora", required=True, type=Path, help="Path to LoRA adapter dir")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, required=True, help="Where to write the sweep JSON")
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=DEFAULT_THRESHOLDS,
        help="Threshold values to try",
    )
    parser.add_argument("--load-in-4bit", action="store_true", help="Force 4-bit load (smaller VRAM)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Loading LoRA adapter from %s", args.lora)
    analyzer = LLMAnalyzer(
        model_name=args.model,
        lora_path=str(args.lora),
        use_unsloth=False,
        load_in_4bit=args.load_in_4bit,
    )
    analyzer.load()

    dataset = load_dataset(args.dataset)
    logger.info("Loaded %d scenarios from %s", len(dataset), args.dataset)

    result = sweep(analyzer, dataset, args.thresholds)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
    logger.info("Wrote sweep results to %s", args.output)

    # Print summary table.
    print()
    print("=== THRESHOLD SWEEP SUMMARY ===")
    print(f"{'thr':<6}{'det':<8}{'fpr':<8}{'prec':<8}{'f1':<8}")
    for thr_str, row in result["thresholds"].items():
        print(
            f"{thr_str:<6}"
            f"{row['detection']:.3f}  "
            f"{row['fpr']:.3f}  "
            f"{row['precision']:.3f}  "
            f"{row['f1']:.3f}"
        )
    print()
    best = result["best_by_f1"]
    print(f"Best F1:  thr={best['threshold']}  F1={best['f1']:.3f}  FPR={best['fpr']:.3f}")
    if result["best_by_fpr_under_15"]:
        b = result["best_by_fpr_under_15"]
        print(f"Best F1 with FPR<15%:  thr={b['threshold']}  F1={b['f1']:.3f}  FPR={b['fpr']:.3f}")
    if result["best_by_fpr_under_10"]:
        b = result["best_by_fpr_under_10"]
        print(f"Best F1 with FPR<10%:  thr={b['threshold']}  F1={b['f1']:.3f}  FPR={b['fpr']:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
