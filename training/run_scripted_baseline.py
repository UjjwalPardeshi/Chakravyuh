"""Day-1 baseline runner: run N episodes with scripted agents and log to WandB.

This establishes the "no-LLM" baseline we beat on Day 2.

Usage:
    python -m training.run_scripted_baseline --episodes 100
    python -m training.run_scripted_baseline --episodes 100 --no-wandb
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from chakravyuh_env import ChakravyuhEnv
from chakravyuh_env.schemas import VictimProfile

logger = logging.getLogger("chakravyuh.baseline")


def run_baseline(
    episodes: int,
    seed_base: int = 1000,
    profile: VictimProfile = VictimProfile.SEMI_URBAN,
    gullibility: float = 1.0,
    wandb_project: str | None = "chakravyuh-run-1",
    log_path: Path | None = None,
) -> dict[str, float | int]:
    wandb_run = None
    if wandb_project:
        try:
            import wandb  # type: ignore

            wandb_run = wandb.init(
                project=wandb_project,
                name=f"scripted-baseline-n{episodes}",
                config={
                    "episodes": episodes,
                    "profile": profile.value,
                    "gullibility": gullibility,
                    "agents": "all-scripted",
                },
            )
        except Exception as e:
            logger.warning("WandB init failed (%s); continuing without WandB.", e)

    env = ChakravyuhEnv(victim_profile=profile, gullibility=gullibility)
    category_counts: Counter[str] = Counter()
    outcomes_summary = {
        "money_extracted": 0,
        "victim_refused": 0,
        "analyzer_flagged": 0,
        "bank_flagged": 0,
        "bank_froze": 0,
        "sought_verification": 0,
    }
    detection_turns: list[int] = []
    rewards_analyzer: list[float] = []
    rewards_scammer: list[float] = []

    log_rows: list[dict] = []
    for i in range(episodes):
        obs = env.reset(seed=seed_base + i)
        done = False
        reward = None
        info: dict = {}
        while not done:
            obs, reward, done, info = env.step()
        outcome = info["outcome"]
        category_counts[outcome.scam_category.value] += 1
        outcomes_summary["money_extracted"] += int(outcome.money_extracted)
        outcomes_summary["victim_refused"] += int(outcome.victim_refused)
        outcomes_summary["analyzer_flagged"] += int(outcome.analyzer_flagged)
        outcomes_summary["bank_flagged"] += int(outcome.bank_flagged)
        outcomes_summary["bank_froze"] += int(outcome.bank_froze)
        outcomes_summary["sought_verification"] += int(outcome.victim_sought_verification)
        if outcome.detected_by_turn is not None:
            detection_turns.append(outcome.detected_by_turn)
        if reward is not None:
            rewards_analyzer.append(reward.analyzer)
            rewards_scammer.append(reward.scammer)
            if wandb_run is not None:
                wandb_run.log(
                    {
                        "ep": i,
                        "reward/analyzer": reward.analyzer,
                        "reward/scammer": reward.scammer,
                        "detection/flagged": int(outcome.analyzer_flagged),
                        "detection/turn": outcome.detected_by_turn or -1,
                        "outcome/money_extracted": int(outcome.money_extracted),
                    }
                )
        log_rows.append(
            {
                "ep": i,
                "seed": seed_base + i,
                "category": outcome.scam_category.value,
                "analyzer_flagged": outcome.analyzer_flagged,
                "detected_by_turn": outcome.detected_by_turn,
                "money_extracted": outcome.money_extracted,
                "victim_refused": outcome.victim_refused,
                "reward_analyzer": reward.analyzer if reward else None,
                "reward_scammer": reward.scammer if reward else None,
            }
        )

    detection_rate = outcomes_summary["analyzer_flagged"] / episodes
    extraction_rate = outcomes_summary["money_extracted"] / episodes
    avg_detection_turn = (
        sum(detection_turns) / len(detection_turns) if detection_turns else -1
    )
    avg_reward_analyzer = (
        sum(rewards_analyzer) / len(rewards_analyzer) if rewards_analyzer else 0.0
    )

    summary = {
        "episodes": episodes,
        "detection_rate": round(detection_rate, 4),
        "extraction_rate": round(extraction_rate, 4),
        "avg_detection_turn": round(avg_detection_turn, 2),
        "avg_reward_analyzer": round(avg_reward_analyzer, 4),
        **outcomes_summary,
        **{f"category/{k}": v for k, v in category_counts.items()},
    }

    logger.info("=== Baseline Summary ===")
    for k, v in summary.items():
        logger.info("  %s: %s", k, v)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"summary": summary, "rows": log_rows}, indent=2))
        logger.info("Wrote log to %s", log_path)

    if wandb_run is not None:
        wandb_run.summary.update(summary)
        wandb_run.finish()

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scripted baseline runner")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument(
        "--profile",
        type=str,
        default="semi_urban",
        choices=["senior", "young_urban", "semi_urban"],
    )
    parser.add_argument("--gullibility", type=float, default=1.0)
    parser.add_argument("--no-wandb", action="store_true")
    parser.add_argument("--log-path", type=Path, default=Path("logs/baseline_day1.json"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    profile = VictimProfile(args.profile)
    run_baseline(
        episodes=args.episodes,
        seed_base=args.seed_base,
        profile=profile,
        gullibility=args.gullibility,
        wandb_project=None if args.no_wandb else "chakravyuh-run-1",
        log_path=args.log_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
