"""Mode C evaluation runner: scores any analyzer against chakravyuh-bench-v0.

Usage:
    python -m eval.mode_c_real_cases --analyzer scripted
    python -m eval.mode_c_real_cases --analyzer scripted --bootstrap 1000 --permutation
    python -m eval.mode_c_real_cases --analyzer scripted --output logs/mode_c_results.json

The runner is analyzer-agnostic — it calls `AnalyzerProtocol.score_text(text) -> float`
so any scripted, LLM zero-shot, or LoRA-trained analyzer plugs in via the same
interface. Day-2 LLM analyzer just implements that one method.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
from chakravyuh_env.schemas import AnalyzerScore, ChatMessage, Observation
from eval.bootstrap_ci import bootstrap_ci, cohens_d, permutation_test

logger = logging.getLogger("chakravyuh.eval.mode_c")

DEFAULT_DATASET = Path("data/chakravyuh-bench-v0/scenarios.jsonl")


class AnalyzerProtocol(Protocol):
    """Minimal interface any analyzer must implement for Mode C eval."""

    def score_text(self, text: str) -> float: ...


class ScriptedAnalyzerAdapter:
    """Adapts the ScriptedAnalyzer.act() output to a simple score."""

    def __init__(self) -> None:
        self.inner = ScriptedAnalyzer()

    def score_text(self, text: str) -> float:
        # Fake a one-turn observation so the rule-based analyzer can score
        obs = Observation(
            agent_role="analyzer",
            turn=1,
            chat_history=[ChatMessage(sender="scammer", turn=1, text=text)],
        )
        action = self.inner.act(obs)
        if isinstance(action, AnalyzerScore):
            return action.score
        return 0.0


@dataclass(frozen=True)
class EvalResult:
    scenario_id: str
    is_scam_truth: bool
    predicted_score: float
    predicted_flag: bool
    correct: bool
    category: str
    difficulty: str


@dataclass(frozen=True)
class AggregateMetrics:
    n: int
    detection_rate: float  # scam-only: recall
    false_positive_rate: float  # benign-only: FP / total_benign
    precision: float
    recall: float
    f1: float
    accuracy: float


def load_dataset(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_eval(
    analyzer: AnalyzerProtocol,
    dataset: list[dict],
    threshold: float = 0.5,
) -> list[EvalResult]:
    results: list[EvalResult] = []
    for scenario in dataset:
        text = " ".join(
            msg["text"] for msg in scenario["attack_sequence"] if msg["sender"] == "scammer"
        )
        score = analyzer.score_text(text)
        flagged = score >= threshold
        is_scam = scenario["ground_truth"]["is_scam"]
        results.append(
            EvalResult(
                scenario_id=scenario["id"],
                is_scam_truth=is_scam,
                predicted_score=score,
                predicted_flag=flagged,
                correct=(flagged == is_scam),
                category=scenario["ground_truth"]["category"],
                difficulty=scenario["ground_truth"]["difficulty"],
            )
        )
    return results


def aggregate(results: list[EvalResult]) -> AggregateMetrics:
    n = len(results)
    if n == 0:
        return AggregateMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    tp = sum(1 for r in results if r.is_scam_truth and r.predicted_flag)
    fn = sum(1 for r in results if r.is_scam_truth and not r.predicted_flag)
    fp = sum(1 for r in results if not r.is_scam_truth and r.predicted_flag)
    tn = sum(1 for r in results if not r.is_scam_truth and not r.predicted_flag)

    scam_count = tp + fn
    benign_count = fp + tn

    detection_rate = tp / scam_count if scam_count else 0.0
    false_positive_rate = fp / benign_count if benign_count else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = detection_rate
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / n

    return AggregateMetrics(
        n=n,
        detection_rate=detection_rate,
        false_positive_rate=false_positive_rate,
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
    )


def per_category_breakdown(results: list[EvalResult]) -> dict[str, AggregateMetrics]:
    by_cat: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    return {cat: aggregate(rs) for cat, rs in sorted(by_cat.items())}


def per_difficulty_breakdown(results: list[EvalResult]) -> dict[str, AggregateMetrics]:
    by_diff: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_diff[r.difficulty].append(r)
    return {d: aggregate(rs) for d, rs in sorted(by_diff.items())}


def format_report(
    analyzer_name: str,
    metrics: AggregateMetrics,
    by_cat: dict[str, AggregateMetrics],
    by_diff: dict[str, AggregateMetrics],
    ci_bounds: tuple[float, float] | None = None,
) -> str:
    lines = [
        f"=== Mode C Results: {analyzer_name} ===",
        f"N = {metrics.n}",
        f"Detection rate (scam recall): {metrics.detection_rate:.1%}",
        f"False positive rate: {metrics.false_positive_rate:.1%}",
        f"Precision: {metrics.precision:.1%}",
        f"F1 score: {metrics.f1:.3f}",
        f"Accuracy: {metrics.accuracy:.1%}",
    ]
    if ci_bounds is not None:
        lines.append(f"Detection 95% CI: [{ci_bounds[0]:.1%}, {ci_bounds[1]:.1%}]")
    lines.append("")
    lines.append("Per-category:")
    for cat, m in by_cat.items():
        marker = "[FP]" if cat in ("benign", "borderline") else "    "
        lines.append(f"  {marker} {cat}: det={m.detection_rate:.1%}, fpr={m.false_positive_rate:.1%}, n={m.n}")
    lines.append("")
    lines.append("Per-difficulty:")
    for diff, m in by_diff.items():
        lines.append(f"  {diff}: det={m.detection_rate:.1%}, n={m.n}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mode C real-cases evaluator")
    parser.add_argument(
        "--analyzer",
        type=str,
        default="scripted",
        choices=["scripted", "llm"],
        help="Which analyzer to evaluate",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--bootstrap", type=int, default=0, help="Bootstrap resamples (0 = off)")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    dataset = load_dataset(args.dataset)
    logger.info("Loaded %d scenarios from %s", len(dataset), args.dataset)

    if args.analyzer == "scripted":
        analyzer: AnalyzerProtocol = ScriptedAnalyzerAdapter()
        name = "ScriptedAnalyzer (rule-based baseline)"
    else:
        raise NotImplementedError("LLM analyzer will be wired on Day 2")

    results = run_eval(analyzer, dataset, threshold=args.threshold)
    metrics = aggregate(results)
    by_cat = per_category_breakdown(results)
    by_diff = per_difficulty_breakdown(results)

    ci: tuple[float, float] | None = None
    if args.bootstrap > 0:
        scam_hits = [1.0 if r.predicted_flag else 0.0 for r in results if r.is_scam_truth]
        _, lo, hi = bootstrap_ci(scam_hits, n_resamples=args.bootstrap, seed=42)
        ci = (lo, hi)

    report = format_report(name, metrics, by_cat, by_diff, ci)
    print(report)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "analyzer": name,
            "n": metrics.n,
            "detection_rate": metrics.detection_rate,
            "false_positive_rate": metrics.false_positive_rate,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "accuracy": metrics.accuracy,
            "detection_ci_95": list(ci) if ci else None,
            "per_category": {k: v.__dict__ for k, v in by_cat.items()},
            "per_difficulty": {k: v.__dict__ for k, v in by_diff.items()},
            "scenarios": [r.__dict__ for r in results],
        }
        args.output.write_text(json.dumps(payload, indent=2))
        logger.info("Wrote %s", args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())


# Convenience re-exports for stats scripts
__all__ = [
    "AggregateMetrics",
    "EvalResult",
    "aggregate",
    "bootstrap_ci",
    "cohens_d",
    "load_dataset",
    "per_category_breakdown",
    "per_difficulty_breakdown",
    "permutation_test",
    "run_eval",
]
