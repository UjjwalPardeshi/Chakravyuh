"""Render the v2 Analyzer training curves from `logs/v2_trainer_state.json`.

Produces `plots/chakravyuh_plots/training_curves_v2.png` — a 4-panel
figure showing reward, loss, KL divergence, and gradient norm over the
615-step GRPO run.

This is the artifact the hackathon's "evidence you actually trained
— at minimum, loss and reward plots from a real run" non-negotiable
asks for. The data is the canonical TRL `trainer_state.json` log
captured during the v2 retrain (n=123 logged points at logging_steps=5).

Usage:
    python eval/plot_training_curves.py
    # → plots/chakravyuh_plots/training_curves_v2.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> int:
    log_path = Path("logs/v2_trainer_state.json")
    out_path = Path("plots/chakravyuh_plots/training_curves_v2.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    state = json.loads(log_path.read_text(encoding="utf-8"))
    history = state["log_history"]

    steps = [h["step"] for h in history]
    reward = [h["reward"] for h in history]
    reward_std = [h.get("reward_std", 0.0) for h in history]
    loss = [h["loss"] for h in history]
    kl = [h["kl"] for h in history]
    grad_norm = [h["grad_norm"] for h in history]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig.suptitle(
        "Chakravyuh Analyzer v2 — TRL GRPO training curves "
        f"(n={len(history)} logged steps · base = Qwen2.5-7B-Instruct + LoRA r=64)",
        fontsize=12,
        fontweight="bold",
    )

    # 1. Reward (with ±1 std band)
    ax = axes[0, 0]
    ax.plot(steps, reward, color="#1565c0", linewidth=1.8, label="Mean episode reward")
    upper = [r + s for r, s in zip(reward, reward_std)]
    lower = [r - s for r, s in zip(reward, reward_std)]
    ax.fill_between(steps, lower, upper, color="#1565c0", alpha=0.15, label="±1 std")
    ax.set_xlabel("Training step")
    ax.set_ylabel("Reward (8-rubric weighted sum)")
    ax.set_title("Episode reward — climbs and stabilises")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)

    # 2. Loss
    ax = axes[0, 1]
    ax.plot(steps, loss, color="#c62828", linewidth=1.8)
    ax.axhline(0.0, color="black", linestyle=":", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Training step")
    ax.set_ylabel("GRPO loss")
    ax.set_title("Loss — bounded around zero, clean (no divergence)")
    ax.grid(True, alpha=0.3)

    # 3. KL divergence — anti-collapse anchor
    ax = axes[1, 0]
    ax.plot(steps, kl, color="#558b2f", linewidth=1.8)
    ax.axhline(0.20, color="#e65100", linestyle="--", linewidth=1.0, alpha=0.7,
               label="KL guard threshold (v3 plan)")
    ax.set_xlabel("Training step")
    ax.set_ylabel("KL divergence vs reference")
    ax.set_title("KL — plateaus 0.25–0.45 (honest read in training_diagnostics.md)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)

    # 4. Gradient norm — stability indicator
    ax = axes[1, 1]
    ax.plot(steps, grad_norm, color="#6a1b9a", linewidth=1.8)
    ax.set_xlabel("Training step")
    ax.set_ylabel("Gradient norm")
    ax.set_title("Grad norm — well-behaved (no explosions)")
    ax.grid(True, alpha=0.3)

    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
