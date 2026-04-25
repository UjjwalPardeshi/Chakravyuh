"""Error analysis — full audit of scripted-baseline FPs + v2 LoRA aggregate gaps.

Two parts:

1. **Scripted baseline (per-scenario)** — read ``logs/mode_c_scripted_n135.json``
   and enumerate every FP, FN, and missed scam, with category and difficulty
   tags. Full per-scenario fidelity.

2. **v2 LoRA (aggregate-level only)** — read ``logs/eval_v2.json`` and report
   per-difficulty error counts. Per-scenario v2 audit requires GPU re-inference
   and is v3 work.

Output: ``docs/v2_error_analysis.md`` (markdown for judges).

Usage:
    python eval/error_analysis.py
    python eval/error_analysis.py --output docs/v2_error_analysis.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTED = REPO_ROOT / "logs" / "mode_c_scripted_n135.json"
EVAL_V2 = REPO_ROOT / "logs" / "eval_v2.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "v2_error_analysis.md"


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing input: {path}")
    return json.loads(path.read_text())


def _scripted_errors(data: dict) -> dict:
    scenarios = data.get("scenarios", [])
    by_category: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "n_correct": 0, "fp": [], "fn": []}
    )
    for s in scenarios:
        cat = s.get("category", "unknown")
        truth = bool(s.get("is_scam_truth", False))
        flag = bool(s.get("predicted_flag", False))
        b = by_category[cat]
        b["n"] += 1
        if truth == flag:
            b["n_correct"] += 1
        if truth and not flag:
            b["fn"].append(s)
        elif (not truth) and flag:
            b["fp"].append(s)
    summary = {
        "n_total": len(scenarios),
        "by_category": {
            cat: {
                "n": b["n"],
                "n_correct": b["n_correct"],
                "accuracy": round(b["n_correct"] / b["n"], 4) if b["n"] else 0.0,
                "n_fp": len(b["fp"]),
                "n_fn": len(b["fn"]),
                "fp_examples": [
                    {
                        "scenario_id": s.get("scenario_id"),
                        "predicted_score": s.get("predicted_score"),
                        "difficulty": s.get("difficulty"),
                    }
                    for s in b["fp"]
                ],
                "fn_examples": [
                    {
                        "scenario_id": s.get("scenario_id"),
                        "predicted_score": s.get("predicted_score"),
                        "difficulty": s.get("difficulty"),
                    }
                    for s in b["fn"]
                ],
            }
            for cat, b in sorted(by_category.items())
        },
    }
    return summary


def _v2_aggregate_summary(eval_data: dict) -> dict:
    block = eval_data.get("lora_v2", {})
    n = int(block.get("n", 0))
    detection = float(block.get("detection", 0.0))
    fpr = float(block.get("fpr", 0.0))
    per_diff = block.get("per_difficulty", {})

    n_scams = sum(int(v.get("n", 0)) for v in per_diff.values())
    n_benign = max(n - n_scams, 0)
    n_missed_scams = round((1 - detection) * n_scams)
    n_fps = round(fpr * n_benign)

    return {
        "n_total": n,
        "n_scams": n_scams,
        "n_benign": n_benign,
        "n_missed_scams": n_missed_scams,
        "n_false_positives": n_fps,
        "detection_rate": round(detection, 4),
        "fpr": round(fpr, 4),
        "f1": float(block.get("f1", 0.0)),
        "per_difficulty": {
            diff: {
                "n": int(info.get("n", 0)),
                "detection_rate": float(info.get("detection_rate", 0.0)),
                "n_missed": round(int(info.get("n", 0)) * (1 - float(info.get("detection_rate", 0.0)))),
            }
            for diff, info in sorted(per_diff.items())
        },
        "threshold": float(block.get("threshold", 0.5)),
    }


def render(scripted: dict, v2: dict) -> str:
    L: list[str] = []
    L.append("# v2 Error Analysis")
    L.append("")
    L.append(
        "Honest accounting of where the analyzers fail. Two layers: "
        "**scripted baseline** has full per-scenario detail; **v2 LoRA** is "
        "aggregated (per-scenario audit requires GPU re-inference, v3 work)."
    )
    L.append("")

    # ---- Scripted baseline section ---- #
    L.append("## Scripted baseline (per-scenario, n=" + str(scripted["n_total"]) + ")")
    L.append("")
    L.append("Source: [`logs/mode_c_scripted_n135.json`](../logs/mode_c_scripted_n135.json)")
    L.append("")
    L.append("### Per-category breakdown")
    L.append("")
    L.append("| Category | n | Accuracy | False Positives | False Negatives (missed scams) |")
    L.append("|---|---|---|---|---|")
    total_fp = 0
    total_fn = 0
    for cat, b in scripted["by_category"].items():
        total_fp += b["n_fp"]
        total_fn += b["n_fn"]
        L.append(
            f"| `{cat}` | {b['n']} | {b['accuracy']:.3f} "
            f"| {b['n_fp']} | {b['n_fn']} |"
        )
    L.append(f"| **Total** | **{scripted['n_total']}** | — | **{total_fp}** | **{total_fn}** |")
    L.append("")

    L.append("### False-positive scenarios (scripted-baseline)")
    L.append("")
    if total_fp == 0:
        L.append("**None observed in this slice.**")
    else:
        L.append("| Category | Scenario | Score | Difficulty |")
        L.append("|---|---|---|---|")
        for cat, b in scripted["by_category"].items():
            for fp in b["fp_examples"]:
                L.append(
                    f"| `{cat}` | `{fp['scenario_id']}` "
                    f"| {fp['predicted_score']:.3f} "
                    f"| {fp['difficulty']} |"
                )
    L.append("")

    L.append("### Missed-scam scenarios (scripted-baseline false negatives)")
    L.append("")
    if total_fn == 0:
        L.append("**None observed in this slice.**")
    else:
        L.append("| Category | Scenario | Score | Difficulty |")
        L.append("|---|---|---|---|")
        for cat, b in scripted["by_category"].items():
            for fn in b["fn_examples"]:
                L.append(
                    f"| `{cat}` | `{fn['scenario_id']}` "
                    f"| {fn['predicted_score']:.3f} "
                    f"| {fn['difficulty']} |"
                )
    L.append("")

    # ---- v2 LoRA aggregate section ---- #
    L.append("## v2 LoRA (aggregate, n=" + str(v2["n_total"]) + ")")
    L.append("")
    L.append("Source: [`logs/eval_v2.json`](../logs/eval_v2.json)")
    L.append("")
    L.append(
        f"- Detection rate: **{v2['detection_rate']:.4f}** "
        f"({v2['n_scams'] - v2['n_missed_scams']}/{v2['n_scams']} scams caught)"
    )
    L.append(
        f"- False positive rate: **{v2['fpr']:.4f}** "
        f"({v2['n_false_positives']}/{v2['n_benign']} benign mislabelled)"
    )
    L.append(f"- F1: **{v2['f1']:.4f}**")
    L.append(f"- Threshold: `{v2['threshold']}`")
    L.append("")
    L.append("### Per-difficulty breakdown")
    L.append("")
    L.append("| Difficulty | n | Detection | Missed scams |")
    L.append("|---|---|---|---|")
    for diff, info in v2["per_difficulty"].items():
        L.append(
            f"| `{diff}` | {info['n']} | {info['detection_rate']:.3f} "
            f"| {info['n_missed']} |"
        )
    L.append("")

    L.append("### Why this is aggregate-only")
    L.append("")
    L.append(
        "The v2 evaluation logged aggregate detection/FPR/F1 + per-difficulty "
        "buckets, but not per-scenario predictions. To audit *which* "
        f"{v2['n_false_positives']} benign(s) the v2 model misclassified, or "
        f"*which* {v2['n_missed_scams']} novel scam(s) it missed, requires "
        "re-running inference with the LoRA adapter on every bench scenario "
        "and dumping per-row scores. That is a single-GPU, ~30-minute job — "
        "tracked as v3 work in [`docs/limitations.md`](limitations.md)."
    )
    L.append("")

    # ---- Cross-comparison + v3 plan ---- #
    L.append("## Comparison summary")
    L.append("")
    L.append("| Metric | Scripted (per-scenario) | v2 LoRA (aggregate) |")
    L.append("|---|---|---|")
    scripted_total = scripted["n_total"]
    scripted_acc = sum(b["n_correct"] for b in scripted["by_category"].values()) / max(scripted_total, 1)
    L.append(
        f"| Accuracy / detection | "
        f"{scripted_acc:.3f} (n={scripted_total}) | "
        f"{v2['detection_rate']:.3f} det · {v2['fpr']:.3f} FPR (n={v2['n_total']}) |"
    )
    L.append(f"| Total errors | {total_fp + total_fn} | {v2['n_missed_scams'] + v2['n_false_positives']} |")
    L.append("")

    L.append("## v3 plan")
    L.append("")
    L.append("1. Re-run v2 inference on the bench with per-scenario logging (~30 min on 1× A100).")
    L.append("2. Manually label each FP / FN root cause: scammer-template overlap, urgency-only signal, multi-language drift, etc.")
    L.append("3. Add fix-targeted templates to `chakravyuh_env/benign_augmented_v2.json` to push n_benign past 150.")
    L.append("4. Retrain v2.1 on the expanded corpus, re-eval, repeat audit.")
    L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--scripted-eval", type=Path, default=SCRIPTED)
    parser.add_argument("--v2-eval", type=Path, default=EVAL_V2)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    scripted = _scripted_errors(_load_json(args.scripted_eval))
    v2 = _v2_aggregate_summary(_load_json(args.v2_eval))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(scripted, v2))

    total_fp = sum(b["n_fp"] for b in scripted["by_category"].values())
    total_fn = sum(b["n_fn"] for b in scripted["by_category"].values())
    print(f"error analysis: {args.output}")
    print(
        f"  scripted: n={scripted['n_total']} · "
        f"FPs={total_fp} · missed scams={total_fn}"
    )
    print(
        f"  v2 LoRA: n={v2['n_total']} · "
        f"missed scams={v2['n_missed_scams']} · FPs={v2['n_false_positives']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
