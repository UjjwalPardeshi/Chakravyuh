"""B.2 — Known (pre-2024) vs Novel (post-2024) detection split.

Re-buckets the bench by year and reports detection / FPR for the scripted
baseline on each bucket. The v2 LoRA detection rate is **not** re-run here
(that requires GPU); instead the v2 number is sourced from
``logs/eval_v2.json``'s `per_difficulty.novel` field as a cross-reference,
since the bench's ``difficulty == "novel"`` and ``source.category ==
"novel_post_2024"`` buckets are by construction the same 34 scenarios.

Bucket rule (operate-on-source-fields, no model):
  - **novel** if ``source.category == "novel_post_2024"`` OR the leading
    year of ``source.date_range`` is ≥ 2024.
  - **known** otherwise (scams with year < 2024).
  - Benign scenarios are kept separate to compute FPR.

Output: a JSON record with both bucket sizes, scripted detection per bucket,
and the v2 cross-reference. Pinned by tests/test_known_vs_novel_split.py.

Usage
-----
    python eval/known_vs_novel_split.py \
        --bench data/chakravyuh-bench-v0/scenarios.jsonl \
        --eval-v2 logs/eval_v2.json \
        --output logs/eval_v2_known_novel.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
from chakravyuh_env.schemas import ChatMessage, Observation


def _bucket_for(scenario: dict[str, Any]) -> str:
    """Return ``"novel"``, ``"known"``, or ``"benign"`` for a scenario."""
    gt = scenario.get("ground_truth", {})
    if not gt.get("is_scam"):
        return "benign"
    src = scenario.get("source", {})
    if src.get("category") == "novel_post_2024":
        return "novel"
    year_str = (src.get("date_range") or "").split("-", 1)[0]
    try:
        year = int(year_str)
    except ValueError:
        year = 0
    return "novel" if year >= 2024 else "known"


def _normalize_sender(raw: str) -> str:
    """ChatMessage only accepts 'scammer' / 'victim'.

    The bench has some entries with `bank_official` (4 cases) — they are
    scam-side messages impersonating a bank. Normalise them to ``scammer``
    so the analyzer scores them on the chat content as it would in
    deployment. ``victim`` passes through unchanged.
    """
    return "victim" if raw == "victim" else "scammer"


def _score_with_scripted(analyzer: ScriptedAnalyzer, scenario: dict[str, Any]) -> float:
    chat = [
        ChatMessage(
            sender=_normalize_sender(t["sender"]),
            turn=t["turn"],
            text=t["text"],
        )
        for t in scenario["attack_sequence"]
    ]
    obs = Observation(
        agent_role="analyzer",
        turn=max((m.turn for m in chat), default=1),
        chat_history=chat,
    )
    return float(analyzer.act(obs).score)


def compute_split(
    bench_path: Path,
    eval_v2_path: Path | None,
    threshold: float = 0.50,
) -> dict[str, Any]:
    with bench_path.open() as f:
        rows = [json.loads(line) for line in f if line.strip()]

    analyzer = ScriptedAnalyzer(flag_threshold=threshold, seed=42)
    buckets: dict[str, list[float]] = {"known": [], "novel": [], "benign": []}
    for row in rows:
        bucket = _bucket_for(row)
        score = _score_with_scripted(analyzer, row)
        buckets[bucket].append(score)

    def _detection(scores: list[float]) -> float:
        if not scores:
            return 0.0
        return sum(1 for s in scores if s >= threshold) / len(scores)

    def _fpr(scores: list[float]) -> float:
        if not scores:
            return 0.0
        return sum(1 for s in scores if s >= threshold) / len(scores)

    out: dict[str, Any] = {
        "_meta": {
            "bench": str(bench_path),
            "threshold": threshold,
            "method": "scripted-rule baseline; v2 cross-reference from logs/eval_v2.json",
            "rule": "novel = source.category=='novel_post_2024' OR source.date_range year >= 2024",
        },
        "scripted": {
            "known": {
                "n": len(buckets["known"]),
                "detection_rate": _detection(buckets["known"]),
            },
            "novel": {
                "n": len(buckets["novel"]),
                "detection_rate": _detection(buckets["novel"]),
            },
            "benign": {
                "n": len(buckets["benign"]),
                "fpr": _fpr(buckets["benign"]),
            },
        },
    }

    if eval_v2_path and eval_v2_path.exists():
        eval_v2 = json.loads(eval_v2_path.read_text())
        per_diff = eval_v2.get("lora_v2", {}).get("per_difficulty", {})
        novel_block = per_diff.get("novel", {})
        # All non-novel difficulties together stand in for "known".
        known_n = sum(int(per_diff[k]["n"]) for k in ("easy", "medium", "hard") if k in per_diff)
        known_caught = sum(
            int(per_diff[k]["n"]) * float(per_diff[k]["detection_rate"])
            for k in ("easy", "medium", "hard")
            if k in per_diff
        )
        out["v2_crossref"] = {
            "source": str(eval_v2_path),
            "novel": {
                "n": int(novel_block.get("n", 0)),
                "detection_rate": float(novel_block.get("detection_rate", 0.0)),
            },
            "known": {
                "n": known_n,
                "detection_rate": known_caught / known_n if known_n else 0.0,
                "note": "easy + medium + hard buckets aggregated as a known-scam proxy",
            },
        }

    sk = out["scripted"]["known"]["detection_rate"]
    sn = out["scripted"]["novel"]["detection_rate"]
    out["headline_gap_pp"] = round((sk - sn) * 100, 1)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path,
                        default=Path("data/chakravyuh-bench-v0/scenarios.jsonl"))
    parser.add_argument("--eval-v2", type=Path,
                        default=Path("logs/eval_v2.json"))
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--output", type=Path,
                        default=Path("logs/eval_v2_known_novel.json"))
    args = parser.parse_args(argv)

    record = compute_split(args.bench, args.eval_v2, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2))

    s = record["scripted"]
    print(f"Wrote {args.output}")
    print(f"  scripted known  : {s['known']['detection_rate']:.3f}  (n={s['known']['n']})")
    print(f"  scripted novel  : {s['novel']['detection_rate']:.3f}  (n={s['novel']['n']})")
    print(f"  scripted benign : FPR={s['benign']['fpr']:.3f}  (n={s['benign']['n']})")
    print(f"  scripted gap    : {record['headline_gap_pp']} pp (known − novel)")
    if "v2_crossref" in record:
        v = record["v2_crossref"]
        print(f"  v2 crossref known: {v['known']['detection_rate']:.3f}  (n={v['known']['n']})")
        print(f"  v2 crossref novel: {v['novel']['detection_rate']:.3f}  (n={v['novel']['n']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
