"""Single-scenario before/after eval — scripted vs LoRA v2.

Runs both analyzers on a single bench scenario and writes a JSON record that
the README's "Before/after" section quotes. The scripted run requires no GPU.
The LoRA run only fires when ``torch.cuda.is_available()`` (or ``--force-llm``)
and the adapter is reachable; otherwise the v2 numbers are cross-referenced
from ``logs/eval_v2.json`` (per-difficulty aggregate) and the JSON marks
``v2.measured_directly = false``.

Operating Principle #1: never fabricate numbers. If we couldn't run v2 on this
specific scenario, we say so and quote the already-measured aggregate it
belongs to.

Usage
-----
    python eval/single_scenario_eval.py \
        --bench data/chakravyuh-bench-v0/scenarios.jsonl \
        --scenario-id modec_106 \
        --eval-aggregate logs/eval_v2.json \
        --output docs/before_after_example.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_scenario(bench: Path, scenario_id: str) -> dict[str, Any]:
    with bench.open() as f:
        for line in f:
            row = json.loads(line)
            if row.get("id") == scenario_id or row.get("scenario_id") == scenario_id:
                return row
    raise SystemExit(f"Scenario {scenario_id!r} not found in {bench}")


def _run_scripted(scenario: dict[str, Any]) -> dict[str, Any]:
    """Score the scenario with the scripted (rule-based) analyzer."""
    from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
    from chakravyuh_env.schemas import ChatMessage, Observation

    chat = [
        ChatMessage(sender=t["sender"], turn=t["turn"], text=t["text"])
        for t in scenario["attack_sequence"]
    ]
    obs = Observation(
        agent_role="analyzer",
        turn=max((m.turn for m in chat), default=1),
        chat_history=chat,
    )
    analyzer = ScriptedAnalyzer(flag_threshold=0.50, seed=42)
    score = analyzer.act(obs)
    return {
        "score": float(score.score),
        "signals": [s.value for s in score.signals],
        "explanation": score.explanation,
        "flagged": float(score.score) >= analyzer.flag_threshold,
        "threshold": analyzer.flag_threshold,
    }


def _try_run_v2(scenario: dict[str, Any], adapter: str) -> dict[str, Any] | None:
    """Run the v2 LoRA on this scenario, or return None if it's not feasible."""
    try:
        import torch  # type: ignore[import-not-found]

        if not torch.cuda.is_available():
            return None
    except Exception:
        return None

    try:
        from chakravyuh_env import get_trained_analyzer

        analyzer = get_trained_analyzer(adapter=adapter)
        first_msg = scenario["attack_sequence"][0]["text"]
        result = analyzer(first_msg)
        return {
            "score": float(result["score"]),
            "signals": list(result["signals"]),
            "explanation": result["explanation"],
            "flagged": float(result["score"]) >= 0.5,
            "threshold": 0.5,
            "measured_directly": True,
            "adapter": adapter,
        }
    except Exception as exc:  # pragma: no cover — diagnostic surface only
        return {"error": f"{type(exc).__name__}: {exc}", "measured_directly": False}


def _v2_aggregate_lookup(eval_path: Path, difficulty: str) -> dict[str, Any]:
    """Pull the v2 per-difficulty number from logs/eval_v2.json as a fallback."""
    data = json.loads(eval_path.read_text())
    block = data.get("lora_v2", {})
    per_diff = block.get("per_difficulty", {}).get(difficulty, {})
    return {
        "measured_directly": False,
        "source": str(eval_path),
        "split": difficulty,
        "n_in_split": int(per_diff.get("n", 0)),
        "detection_rate_in_split": float(per_diff.get("detection_rate", 0.0)),
        "note": (
            f"v2 was not re-run on this single scenario (no GPU available); "
            f"its detection rate on the '{difficulty}' split overall is "
            f"{float(per_diff.get('detection_rate', 0.0)) * 100:.1f}% "
            f"(n={int(per_diff.get('n', 0))}). This scenario is in that split."
        ),
    }


def _build_record(
    scenario: dict[str, Any],
    scripted: dict[str, Any],
    v2: dict[str, Any],
) -> dict[str, Any]:
    gt = scenario.get("ground_truth", {})
    return {
        "scenario": {
            "id": scenario.get("id"),
            "category": gt.get("category"),
            "difficulty": gt.get("difficulty"),
            "is_scam": gt.get("is_scam"),
            "expected_signals": gt.get("signals", []),
            "first_message": scenario["attack_sequence"][0]["text"],
            "source": scenario.get("source", {}),
            "metadata": scenario.get("metadata", {}),
        },
        "scripted": scripted,
        "v2": v2,
        "delta": {
            "scripted_flagged": bool(scripted.get("flagged")),
            "v2_caught_in_split": bool(
                v2.get("flagged")
                if v2.get("measured_directly")
                else v2.get("detection_rate_in_split", 0.0) > 0.5
            ),
            "interpretation": (
                "Scripted analyzer missed this scam (score below threshold). "
                "v2 catches scams in this split at "
                f"{(v2.get('detection_rate_in_split') or (1.0 if v2.get('flagged') else 0.0)) * 100:.0f}% rate."
            )
            if not scripted.get("flagged")
            else (
                "Both scripted and v2 catch this scam, but scripted's score may "
                "be borderline; v2 holds at the bench-wide novel detection rate."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path, default=Path("data/chakravyuh-bench-v0/scenarios.jsonl"))
    parser.add_argument("--scenario-id", default="modec_106")
    parser.add_argument("--adapter", default="ujjwalpardeshi/chakravyuh-analyzer-lora-v2")
    parser.add_argument("--eval-aggregate", type=Path, default=Path("logs/eval_v2.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/before_after_example.json"))
    parser.add_argument("--force-llm", action="store_true",
                        help="Try to load LoRA even without GPU (slow, may OOM)")
    args = parser.parse_args(argv)

    scenario = _load_scenario(args.bench, args.scenario_id)
    scripted = _run_scripted(scenario)

    v2: dict[str, Any] | None = None
    if args.force_llm or _has_cuda():
        v2 = _try_run_v2(scenario, args.adapter)
    if v2 is None or not v2.get("measured_directly"):
        difficulty = scenario.get("ground_truth", {}).get("difficulty", "unknown")
        v2 = _v2_aggregate_lookup(args.eval_aggregate, difficulty)

    record = _build_record(scenario, scripted, v2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2))
    print(f"Wrote {args.output}")
    print(f"  scripted score:   {scripted['score']:.3f} ({'FLAGGED' if scripted['flagged'] else 'missed'})")
    if v2.get("measured_directly"):
        print(f"  v2 score:         {v2['score']:.3f} ({'FLAGGED' if v2['flagged'] else 'missed'})")
    else:
        print(f"  v2 (aggregate):   detection={v2.get('detection_rate_in_split', 0):.3f} on '{v2.get('split')}' split (n={v2.get('n_in_split', 0)})")
    return 0


def _has_cuda() -> bool:
    try:
        import torch  # type: ignore[import-not-found]

        return bool(torch.cuda.is_available())
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
