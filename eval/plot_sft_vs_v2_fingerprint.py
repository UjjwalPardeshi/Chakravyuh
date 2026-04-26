"""Render SFT (imitation) vs v2 (GRPO) per-difficulty 'fingerprint' plot.

Both checkpoints share the same Qwen2.5-7B base, the same LoRA hyperparameters
(r=32, α=64, all linear), and the same training corpus. Only the algorithm
differs: SFT minimises NLL on gold answers, v2-GRPO maximises composite
reward against `AnalyzerRubricV2` online.

The fingerprint per-difficulty makes the trade-off visible:
  - SFT: easy=1.0 medium=1.0 hard=0.94 novel=1.0  · FPR=3.2%
  - v2 : easy=1.0 medium=1.0 hard=1.0  novel=0.97 · FPR=6.7%

GRPO buys +5.6 pp on hard at the cost of -2.9 pp on novel and +3.4 pp FPR.

Output: plots/chakravyuh_plots/v1_vs_v2_fingerprint.png
  (filename kept as v1_vs_v2 for backward-compat with .gitignore exception
  + README cross-references — the plot itself labels SFT and v2-GRPO.)
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> int:
    src_sft = json.loads(Path("logs/eval_sft.json").read_text(encoding="utf-8"))
    src_v2 = json.loads(Path("logs/eval_v2.json").read_text(encoding="utf-8"))
    out = Path("plots/chakravyuh_plots/v1_vs_v2_fingerprint.png")

    sft = src_sft["sft_baseline"]
    v2 = src_v2["lora_v2"]
    diffs = ["easy", "medium", "hard", "novel"]

    sft_rates = [sft["per_difficulty"][d]["detection_rate"] for d in diffs]
    v2_rates = [v2["per_difficulty"][d]["detection_rate"] for d in diffs]
    sft_n = [sft["per_difficulty"][d]["n"] for d in diffs]
    v2_n = [v2["per_difficulty"][d]["n"] for d in diffs]

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(13, 5.5),
                                            gridspec_kw={"width_ratios": [3, 1.2]})

    x = np.arange(len(diffs))
    w = 0.38
    ax_left.bar(x - w / 2, sft_rates, w, label=f"SFT baseline (n={sft['n']})",
                color="#1565c0", edgecolor="black", linewidth=0.5)
    ax_left.bar(x + w / 2, v2_rates, w, label=f"v2 GRPO (n={v2['n']})",
                color="#558b2f", edgecolor="black", linewidth=0.5)

    for i, (s, v, sn, vn) in enumerate(zip(sft_rates, v2_rates, sft_n, v2_n)):
        ax_left.text(i - w / 2, s + 0.012, f"{s:.2f}", ha="center", fontsize=9)
        ax_left.text(i + w / 2, v + 0.012, f"{v:.2f}", ha="center", fontsize=9)
        ax_left.text(i - w / 2, -0.05, f"n={sn}", ha="center", fontsize=8, color="#666")
        ax_left.text(i + w / 2, -0.05, f"n={vn}", ha="center", fontsize=8, color="#666")
        delta = (v - s) * 100
        sign = "+" if delta >= 0 else ""
        color = "#558b2f" if delta > 0 else "#c62828" if delta < 0 else "#666"
        ax_left.text(i, max(s, v) + 0.07, f"Δ {sign}{delta:.1f}pp",
                     ha="center", fontsize=9, fontweight="bold", color=color)

    ax_left.set_xticks(x)
    ax_left.set_xticklabels(diffs, fontsize=10)
    ax_left.set_ylabel("Detection rate", fontsize=11)
    ax_left.set_ylim(-0.08, 1.18)
    ax_left.set_title("Detection by difficulty", fontsize=11, fontweight="bold")
    ax_left.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax_left.grid(True, alpha=0.3, axis="y")

    cats = ["FPR\n(benign)", "F1"]
    sft_vals = [sft["fpr"], sft["f1"]]
    v2_vals = [v2["fpr"], v2["f1"]]
    xc = np.arange(len(cats))
    ax_right.bar(xc - w / 2, sft_vals, w, label="SFT",
                 color="#1565c0", edgecolor="black", linewidth=0.5)
    ax_right.bar(xc + w / 2, v2_vals, w, label="v2 GRPO",
                 color="#558b2f", edgecolor="black", linewidth=0.5)
    for i, (s, v) in enumerate(zip(sft_vals, v2_vals)):
        ax_right.text(i - w / 2, s + 0.012, f"{s:.3f}", ha="center", fontsize=8)
        ax_right.text(i + w / 2, v + 0.012, f"{v:.3f}", ha="center", fontsize=8)
    ax_right.set_xticks(xc)
    ax_right.set_xticklabels(cats, fontsize=10)
    ax_right.set_ylim(0, 1.10)
    ax_right.set_title("Aggregate trade-off", fontsize=11, fontweight="bold")
    ax_right.grid(True, alpha=0.3, axis="y")

    fig.suptitle(
        "SFT (imitation) vs v2 GRPO (online RL) — same base, same LoRA, different algorithm",
        fontsize=12, fontweight="bold", y=1.00,
    )
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
