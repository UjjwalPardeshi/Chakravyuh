"""Time-to-detection metric — uses existing 100-episode scripted-baseline trace.

Reads ``logs/baseline_day1.json`` (100 episodes with ``detected_by_turn``),
computes:

- avg_detection_turn (when flagged)
- pct_detected_by_turn_2 / 3 / 5 (cumulative early-detection share)
- per-category breakdown
- detection-turn distribution (histogram)

A turn-2 flag is materially different from a turn-5 flag in fraud terms —
₹ at risk grows monotonically with delay.

Usage:
    python eval/time_to_detection.py
    python eval/time_to_detection.py --output logs/time_to_detection.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_DEFAULT = REPO_ROOT / "logs" / "baseline_day1.json"
OUTPUT_DEFAULT = REPO_ROOT / "logs" / "time_to_detection.json"


def compute(rows: list[dict]) -> dict:
    flagged_rows = [
        r for r in rows
        if r.get("analyzer_flagged") and isinstance(r.get("detected_by_turn"), int)
    ]
    detection_turns = [r["detected_by_turn"] for r in flagged_rows]

    summary: dict = {
        "n_episodes": len(rows),
        "n_flagged": len(flagged_rows),
        "detection_rate": round(len(flagged_rows) / len(rows), 4) if rows else 0.0,
        "avg_detection_turn": round(mean(detection_turns), 2) if detection_turns else None,
        "median_detection_turn": (
            sorted(detection_turns)[len(detection_turns) // 2]
            if detection_turns else None
        ),
        "min_detection_turn": min(detection_turns) if detection_turns else None,
        "max_detection_turn": max(detection_turns) if detection_turns else None,
    }

    # Cumulative early-detection share, conditioned on the full N (the metric
    # judges should care about: among all scams, what fraction was caught by
    # turn k? Late-flagged + missed both count as failures.)
    n_total = len(rows)
    for cutoff in (2, 3, 4, 5):
        early = sum(1 for t in detection_turns if t <= cutoff)
        summary[f"pct_detected_by_turn_{cutoff}"] = (
            round(early / n_total, 4) if n_total else 0.0
        )

    # Per-category breakdown
    by_cat: dict[str, dict] = defaultdict(lambda: {"n": 0, "n_flagged": 0, "turns": []})
    for r in rows:
        cat = r.get("category", "unknown")
        b = by_cat[cat]
        b["n"] += 1
        if r.get("analyzer_flagged"):
            b["n_flagged"] += 1
            t = r.get("detected_by_turn")
            if isinstance(t, int):
                b["turns"].append(t)
    summary["by_category"] = {
        cat: {
            "n": b["n"],
            "n_flagged": b["n_flagged"],
            "detection_rate": round(b["n_flagged"] / b["n"], 4) if b["n"] else 0.0,
            "avg_detection_turn": (
                round(mean(b["turns"]), 2) if b["turns"] else None
            ),
        }
        for cat, b in sorted(by_cat.items())
    }

    # Histogram of detection turn (1-9, plus 'never' for unflagged)
    histogram: Counter[str] = Counter()
    for r in rows:
        if r.get("analyzer_flagged") and isinstance(r.get("detected_by_turn"), int):
            histogram[f"T{r['detected_by_turn']}"] += 1
        else:
            histogram["never"] += 1
    summary["histogram"] = dict(histogram)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--input", type=Path, default=INPUT_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"input not found: {args.input}")

    data = json.loads(args.input.read_text())
    rows = data.get("rows", []) if isinstance(data, dict) else data
    if not rows:
        raise SystemExit("no rows in input file")

    summary = compute(rows)
    summary["source"] = str(args.input.relative_to(REPO_ROOT))
    summary["analyzer"] = "rule_based_scripted"
    summary["notes"] = (
        "Time-to-detection on the 100-episode env-rollout baseline (scripted "
        "scammer × scripted analyzer × scripted bank). LoRA-v2 time-to-detection "
        "in episode rollouts requires GPU re-inference — pending v3."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"time-to-detection: {args.output}")
    print(f"  detection_rate          = {summary['detection_rate']:.3f}")
    print(f"  avg_detection_turn      = {summary['avg_detection_turn']}")
    for cutoff in (2, 3, 4, 5):
        pct = summary[f"pct_detected_by_turn_{cutoff}"]
        print(f"  pct_detected_by_turn_{cutoff} = {pct:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
