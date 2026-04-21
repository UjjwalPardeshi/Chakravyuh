"""Self-play orchestrator — runs full Chakravyuh episodes with the LoRA Analyzer.

Unlike `grpo_analyzer.py` (which trains the Analyzer on isolated prompts),
this module exercises the trained LoRA INSIDE the full 5-agent environment:
  - Scripted Scammer plays templates
  - Scripted Victim responds (demographic-driven trust)
  - LoRA Analyzer scores conversations (what we just trained)
  - Scripted Bank Monitor oversees transactions
  - Scripted Regulator adapts rules every 10 eps

This produces the data for Day-3's self-play analysis + the "emergent
behavior" pitch finding ("Analyzer's attention pattern evolved from X→Y").
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from chakravyuh_env import ChakravyuhEnv
from chakravyuh_env.schemas import VictimProfile

logger = logging.getLogger("chakravyuh.self_play")


@dataclass
class SelfPlayResults:
    episodes: int = 0
    detection_rate: float = 0.0
    extraction_rate: float = 0.0
    refusal_rate: float = 0.0
    bank_freeze_rate: float = 0.0
    verification_rate: float = 0.0
    avg_detection_turn: float = 0.0
    per_category_detection: dict[str, float] = field(default_factory=dict)
    avg_reward_analyzer: float = 0.0


def run_self_play(
    episodes: int = 100,
    analyzer: Any = None,
    seed_base: int = 1000,
    profiles_cycle: tuple[VictimProfile, ...] = (
        VictimProfile.SENIOR,
        VictimProfile.SEMI_URBAN,
        VictimProfile.YOUNG_URBAN,
    ),
    gullibility_by_profile: dict[str, float] | None = None,
    use_embeddings: bool = False,
    wandb_project: str | None = None,
    log_path: Path | None = None,
) -> SelfPlayResults:
    """Run N episodes with given analyzer (or default scripted).

    Parameters
    ----------
    analyzer :
        Custom Analyzer instance (e.g. LLMAnalyzer with LoRA). If None, uses
        the default ScriptedAnalyzer.
    """
    gullibility_by_profile = gullibility_by_profile or {
        "senior": 1.5,
        "semi_urban": 1.0,
        "young_urban": 0.7,
    }

    wandb_run = None
    if wandb_project:
        try:
            import wandb  # type: ignore[import-not-found]

            wandb_run = wandb.init(
                project=wandb_project,
                name=f"self-play-n{episodes}",
                config={
                    "episodes": episodes,
                    "analyzer": type(analyzer).__name__ if analyzer else "scripted",
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("WandB init failed (%s)", e)

    detection_turns: list[int] = []
    rewards: list[float] = []
    counts = Counter[str]()
    cat_totals: dict[str, int] = {}
    cat_flagged: dict[str, int] = {}

    logs: list[dict[str, Any]] = []

    for i in range(episodes):
        profile = profiles_cycle[i % len(profiles_cycle)]
        gull = gullibility_by_profile[profile.value]
        env = ChakravyuhEnv(
            analyzer=analyzer,
            victim_profile=profile,
            gullibility=gull,
            use_embeddings=use_embeddings,
        )
        env.reset(seed=seed_base + i)
        done = False
        info: dict = {}
        reward = None
        while not done:
            _, reward, done, info = env.step()
        o = info["outcome"]
        counts["money_extracted"] += int(o.money_extracted)
        counts["refused"] += int(o.victim_refused)
        counts["analyzer_flagged"] += int(o.analyzer_flagged)
        counts["bank_froze"] += int(o.bank_froze)
        counts["sought_verification"] += int(o.victim_sought_verification)
        if o.detected_by_turn is not None:
            detection_turns.append(o.detected_by_turn)
        cat = o.scam_category.value
        cat_totals[cat] = cat_totals.get(cat, 0) + 1
        if o.analyzer_flagged:
            cat_flagged[cat] = cat_flagged.get(cat, 0) + 1
        if reward is not None:
            rewards.append(reward.analyzer)
            if wandb_run is not None:
                wandb_run.log({
                    "ep": i,
                    "reward/analyzer": reward.analyzer,
                    "reward/scammer": reward.scammer,
                    "detection/flagged": int(o.analyzer_flagged),
                    "detection/turn": o.detected_by_turn or -1,
                    "outcome/extracted": int(o.money_extracted),
                })
        logs.append({
            "ep": i,
            "seed": seed_base + i,
            "profile": profile.value,
            "category": cat,
            "analyzer_flagged": o.analyzer_flagged,
            "money_extracted": o.money_extracted,
            "reward_analyzer": reward.analyzer if reward else None,
        })

    per_cat = {
        cat: round(cat_flagged.get(cat, 0) / cat_totals[cat], 4)
        for cat in cat_totals
    }
    results = SelfPlayResults(
        episodes=episodes,
        detection_rate=round(counts["analyzer_flagged"] / episodes, 4),
        extraction_rate=round(counts["money_extracted"] / episodes, 4),
        refusal_rate=round(counts["refused"] / episodes, 4),
        bank_freeze_rate=round(counts["bank_froze"] / episodes, 4),
        verification_rate=round(counts["sought_verification"] / episodes, 4),
        avg_detection_turn=round(
            sum(detection_turns) / len(detection_turns), 2
        ) if detection_turns else -1.0,
        per_category_detection=per_cat,
        avg_reward_analyzer=round(
            sum(rewards) / len(rewards), 4
        ) if rewards else 0.0,
    )

    logger.info("=== Self-Play Results ===")
    for k, v in asdict(results).items():
        logger.info("  %s: %s", k, v)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"summary": asdict(results), "rows": logs}, indent=2))

    if wandb_run is not None:
        wandb_run.summary.update(asdict(results))
        wandb_run.finish()

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self-play orchestrator")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument("--lora-path", type=Path, default=None,
                        help="Path to LoRA adapter (enables LLM analyzer)")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--no-wandb", action="store_true")
    parser.add_argument("--log-path", type=Path, default=Path("logs/self_play.json"))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    analyzer = None
    if args.lora_path:
        from chakravyuh_env.agents.llm_analyzer import LLMAnalyzer

        analyzer = LLMAnalyzer(
            model_name=args.model,
            lora_path=str(args.lora_path),
        )
        analyzer.load()

    run_self_play(
        episodes=args.episodes,
        analyzer=analyzer,
        seed_base=args.seed_base,
        wandb_project=None if args.no_wandb else "chakravyuh-run-1",
        log_path=args.log_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
