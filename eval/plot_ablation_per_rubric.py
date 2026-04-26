"""Render per-rubric ablation bar chart from `logs/ablation_study.json`.

Each child rubric is zeroed in turn (eval-time, not retrain) and the
delta in average composite reward is plotted. Bars left of 0 → rubric
matters (reward dropped without it); bars right of 0 → rubric helps the
model game the metric (reward rose without it).

Output: plots/chakravyuh_plots/ablation_per_rubric.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> int:
    src = Path("logs/ablation_study.json")
    out = Path("plots/chakravyuh_plots/ablation_per_rubric.png")
    data = json.loads(src.read_text(encoding="utf-8"))
    rows = data["ablations"]
    full_avg = data["full_avg_reward"]

    rows_sorted = sorted(rows, key=lambda r: r["delta_reward"])
    names = [r["rubric_zeroed"] for r in rows_sorted]
    deltas = [r["delta_reward"] for r in rows_sorted]
    weights = [r["default_weight"] for r in rows_sorted]

    colors = ["#c62828" if d < 0 else "#558b2f" if d > 0 else "#9e9e9e" for d in deltas]
    fig, ax = plt.subplots(figsize=(8, 5))
    y_pos = list(range(len(names)))
    ax.barh(y_pos, deltas, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"{n}\n(w={w:+.2f})" for n, w in zip(names, weights)], fontsize=9)
    ax.axvline(0, color="black", linewidth=0.8)
    for i, d in enumerate(deltas):
        ax.text(
            d + (0.01 if d >= 0 else -0.01), i,
            f"{d:+.4f}",
            va="center", ha="left" if d >= 0 else "right",
            fontsize=9, fontweight="bold",
        )
    ax.set_xlabel("Δ avg composite reward (zeroed − full)", fontsize=11)
    ax.set_title(
        f"Per-rubric ablation — {data['rubric_class']} on n={data['n_scenarios']}\n"
        f"full reward = {full_avg:.4f} · negative bar = rubric matters",
        fontsize=11, fontweight="bold",
    )
    ax.grid(True, alpha=0.3, axis="x")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
