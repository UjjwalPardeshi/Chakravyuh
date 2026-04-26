"""Generate publication-quality co-evolution plots for B.2.

Reads result JSONs in `logs/` and writes PNGs to `plots/chakravyuh_plots/`.
Gracefully degrades if some JSONs are missing.

Usage:
    python eval/plot_coevolution.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
PLOTS = REPO / "plots" / "chakravyuh_plots"
PLOTS.mkdir(parents=True, exist_ok=True)

PHASE1_HEADTOHEAD = LOGS / "b2_phase1_scammer_vs_v2_lora.json"
PHASE2_EVAL = LOGS / "b2_phase2_coevolution_eval.json"
PHASE1_BESTOF8 = LOGS / "b2_phase1_scammer_eval_n64_bestof8.json"
PHASE1_SINGLESHOT = LOGS / "b2_phase1_scammer_eval_n64.json"

C_SCRIPTED = "#bdbdbd"
C_V2 = "#fb8c00"
C_COEVO = "#43a047"
C_TRAIN = "#1e88e5"
C_HELDOUT = "#8e24aa"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def _ci_err(rate: float, lo: float, hi: float) -> tuple[float, float]:
    """Convert Wilson CI to matplotlib's lower/upper-error format."""
    return rate - lo, hi - rate


def plot_coevolution_headline() -> Path | None:
    """Bar chart: Scripted / v2 / v2-coevolved bypass rates by split."""
    if not PHASE1_HEADTOHEAD.exists():
        print(f"[skip] no {PHASE1_HEADTOHEAD.name}")
        return None
    h2h = json.load(open(PHASE1_HEADTOHEAD))
    has_phase2 = PHASE2_EVAL.exists()
    p2 = json.load(open(PHASE2_EVAL)) if has_phase2 else None

    splits = ["overall", "train_seeds", "held_out_seeds"]
    labels = ["Overall (n=64)", "Train (n=32)", "Held-out (n=32)"]
    n_splits = len(splits)

    scripted = [h2h["aggregate"][s]["scripted_bypass_rate"] for s in splits]
    scripted_ci = [h2h["aggregate"][s]["scripted_wilson_95_ci"] for s in splits]
    v2 = [h2h["aggregate"][s]["v2_bypass_rate"] for s in splits]
    v2_ci = [h2h["aggregate"][s]["v2_wilson_95_ci"] for s in splits]

    if has_phase2:
        coevo = [p2["aggregate"][s]["coevolved_bypass_rate"] for s in splits]
        coevo_ci = [p2["aggregate"][s]["coevolved_wilson_95_ci"] for s in splits]
        n_bars = 3
    else:
        n_bars = 2

    x = np.arange(n_splits)
    w = 0.27 if n_bars == 3 else 0.4

    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Scripted bars
    s_err = np.array([_ci_err(r, lo, hi) for r, (lo, hi) in zip(scripted, scripted_ci)]).T
    ax.bar(x - w, scripted, w, yerr=s_err, capsize=4,
           color=C_SCRIPTED, label="ScriptedAnalyzer (rule-based)", edgecolor="#666", linewidth=0.5)

    # v2 bars
    v_err = np.array([_ci_err(r, lo, hi) for r, (lo, hi) in zip(v2, v2_ci)]).T
    ax.bar(x, v2, w, yerr=v_err, capsize=4,
           color=C_V2, label="v2 Analyzer LoRA (round 1)", edgecolor="#444", linewidth=0.5)

    if has_phase2:
        c_err = np.array([_ci_err(r, lo, hi) for r, (lo, hi) in zip(coevo, coevo_ci)]).T
        ax.bar(x + w, coevo, w, yerr=c_err, capsize=4,
               color=C_COEVO, label="v2-coevolved (round 2)", edgecolor="#222", linewidth=0.5)

    # Annotate bar tops with percentages
    bars_groups = [(x - w, scripted), (x, v2)]
    if has_phase2:
        bars_groups.append((x + w, coevo))
    for xs, ys in bars_groups:
        for xi, yi in zip(xs, ys):
            ax.text(xi, yi + 0.02, f"{yi:.0%}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("Scammer bypass rate (lower = stronger defender)", fontsize=11)
    ax.set_ylim(0, 1.10)
    ax.set_yticks([0, 0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    title = "B.2 Co-evolution head-to-head: same Scammer, three defenders"
    if has_phase2:
        title += " (round 1 vs round 2)"
    ax.set_title(title, fontsize=12, pad=12)
    ax.legend(loc="upper right", framealpha=0.95, fontsize=10)
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)

    out = PLOTS / "coevolution_headline.png"
    plt.tight_layout()
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"[ok] {out.name}")
    return out


def plot_per_category() -> Path | None:
    """Grouped bar chart: bypass rate per seed category, v2 vs v2-coevolved."""
    if not PHASE1_HEADTOHEAD.exists():
        print(f"[skip] no {PHASE1_HEADTOHEAD.name}")
        return None
    h2h = json.load(open(PHASE1_HEADTOHEAD))
    has_phase2 = PHASE2_EVAL.exists()
    p2 = json.load(open(PHASE2_EVAL)) if has_phase2 else None

    # Aggregate per-seed (8 train + 8 held-out)
    samples = h2h["samples"]
    p2_samples = {(s["seed"], s.get("split")): s for s in p2["samples"]} if has_phase2 else {}

    by_seed: dict[str, dict] = {}
    for s in samples:
        seed = s["seed"]
        d = by_seed.setdefault(seed, {"split": s["split"], "v2_byp": 0, "co_byp": 0, "n": 0})
        d["n"] += 1
        if s["v2_bypass"]:
            d["v2_byp"] += 1
        if has_phase2 and (seed, s["split"]) in p2_samples:
            if p2_samples[(seed, s["split"])].get("v2_coevolved_bypass"):
                d["co_byp"] += 1

    rows = sorted(by_seed.items(), key=lambda kv: (kv[1]["split"], -kv[1]["v2_byp"]))
    short_labels = []
    for seed, _ in rows:
        # Strip "Write a realistic " prefix and "scam ..." suffix for display
        s = seed.replace("Write a realistic ", "")
        for tail in (" scam message", " scam pretending", " scam asking", " scam promising",
                     " scam claiming", " scam threatening", " scam pre-approving",
                     " scam impersonating", " notification scam"):
            if tail in s:
                s = s.split(tail)[0]
                break
        short_labels.append(s[:35])

    v2_rates = [d["v2_byp"] / d["n"] for _, d in rows]
    co_rates = [d["co_byp"] / d["n"] for _, d in rows] if has_phase2 else None
    splits = [d["split"] for _, d in rows]

    y = np.arange(len(rows))
    h = 0.4

    fig, ax = plt.subplots(figsize=(11, 8))
    ax.barh(y - h / 2, v2_rates, h, color=C_V2, label="v2 Analyzer (round 1)",
            edgecolor="#444", linewidth=0.5)
    if has_phase2:
        ax.barh(y + h / 2, co_rates, h, color=C_COEVO, label="v2-coevolved (round 2)",
                edgecolor="#222", linewidth=0.5)

    # Color y-tick labels by split
    ax.set_yticks(y)
    ax.set_yticklabels(short_labels, fontsize=9)
    for tick, sp in zip(ax.get_yticklabels(), splits):
        tick.set_color(C_TRAIN if sp == "train" else C_HELDOUT)

    ax.set_xlabel("Scammer bypass rate (lower = stronger defender)", fontsize=11)
    ax.set_xlim(0, 1.05)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    title = "Per-category bypass: v2"
    if has_phase2:
        title += " vs v2-coevolved"
    title += " (blue = train, purple = held-out)"
    ax.set_title(title, fontsize=12, pad=12)
    ax.legend(loc="lower right", framealpha=0.95, fontsize=10)
    ax.grid(axis="x", alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.invert_yaxis()

    out = PLOTS / "coevolution_per_category.png"
    plt.tight_layout()
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"[ok] {out.name}")
    return out


def plot_score_movement() -> Path | None:
    """Scatter: v2 score (x) vs v2-coevolved score (y) per sample. Requires phase 2."""
    if not PHASE2_EVAL.exists():
        print("[skip] score-movement scatter (needs phase 2 eval)")
        return None
    p2 = json.load(open(PHASE2_EVAL))
    samples = p2["samples"]
    if not all("v2_score" in s and "v2_coevolved_score" in s for s in samples):
        print("[skip] phase 2 samples missing v2_score / v2_coevolved_score fields")
        return None

    train_pts = [(s["v2_score"], s["v2_coevolved_score"]) for s in samples if s["split"] == "train"]
    held_pts = [(s["v2_score"], s["v2_coevolved_score"]) for s in samples if s["split"] == "held_out"]

    fig, ax = plt.subplots(figsize=(7.5, 7.5))

    # Quadrant shading
    ax.axhspan(0.5, 1.0, xmin=0, xmax=0.5, color="#a5d6a7", alpha=0.25, label="caught by coevolved (was bypass)")
    ax.axhspan(0, 0.5, xmin=0, xmax=0.5, color="#ef9a9a", alpha=0.20, label="bypass under both (true hard)")
    ax.axhspan(0, 0.5, xmin=0.5, xmax=1.0, color="#fff59d", alpha=0.25, label="regression (caught by v2, missed by coevolved)")

    if train_pts:
        xs, ys = zip(*train_pts)
        ax.scatter(xs, ys, s=46, c=C_TRAIN, alpha=0.8, edgecolors="#0d47a1",
                   linewidth=0.6, label=f"train seeds (n={len(train_pts)})")
    if held_pts:
        xs, ys = zip(*held_pts)
        ax.scatter(xs, ys, s=46, c=C_HELDOUT, alpha=0.8, edgecolors="#4a148c",
                   linewidth=0.6, label=f"held-out seeds (n={len(held_pts)})")

    ax.plot([0, 1], [0, 1], color="#666", linestyle="--", linewidth=1, label="identity")
    ax.axhline(0.5, color="black", linewidth=0.6, linestyle=":")
    ax.axvline(0.5, color="black", linewidth=0.6, linestyle=":")

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("v2 Analyzer score (round 1)", fontsize=11)
    ax.set_ylabel("v2-coevolved Analyzer score (round 2)", fontsize=11)
    ax.set_title("Per-sample score movement: v2 → v2-coevolved\n(higher = stronger detection; threshold = 0.5)",
                 fontsize=11, pad=10)
    ax.legend(loc="lower right", framealpha=0.95, fontsize=9)
    ax.grid(alpha=0.3, linewidth=0.5)
    ax.set_aspect("equal")

    out = PLOTS / "coevolution_score_movement.png"
    plt.tight_layout()
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"[ok] {out.name}")
    return out


def plot_training_curve() -> Path | None:
    """Phase 2 training trajectory. Plots GRPO reward if present; falls back to SFT loss.
    Needs `training_log_history` in phase 2 JSON's meta dict."""
    if not PHASE2_EVAL.exists():
        print("[skip] training curve (needs phase 2 eval)")
        return None
    p2 = json.load(open(PHASE2_EVAL))
    log_history = p2.get("meta", {}).get("training_log_history") or p2.get("training_log_history")
    if not log_history:
        print("[skip] training curve (no training_log_history in phase 2 JSON)")
        return None

    method = p2.get("meta", {}).get("phase2_training", {}).get("method", "").lower()
    has_reward = any("reward" in e for e in log_history)
    has_loss = any("loss" in e for e in log_history)

    fig, ax = plt.subplots(figsize=(10, 5.5))

    if has_reward:
        # GRPO regime — plot reward as primary signal
        steps = [e.get("step") for e in log_history if "reward" in e]
        rewards = [e.get("reward") for e in log_history if "reward" in e]
        ax.plot(steps, rewards, color=C_COEVO, linewidth=1.6, marker="o", markersize=3,
                label="mean reward (group)")
        ax.axhline(0, color="#999", linewidth=0.6, linestyle="-")
        ax.axhline(-0.3, color="#c62828", linewidth=0.8, linestyle="--",
                   label="SafetyEarlyStop threshold (-0.3)")
        ax.fill_between(steps, -0.3, min(rewards) - 0.05, color="#ffcdd2", alpha=0.25)
        ax.set_ylabel("Mean GRPO reward (higher = better detection)", fontsize=11)
        ax.set_title("Phase 2 GRPO training trajectory — v2 → v2-coevolved", fontsize=12, pad=10)

        kl_entries = [e for e in log_history if "kl" in e]
        if kl_entries:
            ax2 = ax.twinx()
            ax2.plot([e["step"] for e in kl_entries], [e["kl"] for e in kl_entries],
                     color="#1976d2", linewidth=1.2, alpha=0.6, linestyle=":",
                     label="KL(policy || base)")
            ax2.set_ylabel("KL divergence", color="#1976d2", fontsize=10)
            ax2.tick_params(axis="y", labelcolor="#1976d2")

    elif has_loss:
        # SFT regime — plot cross-entropy loss as primary signal
        steps = [e.get("step") for e in log_history if "loss" in e]
        losses = [e.get("loss") for e in log_history if "loss" in e]
        ax.plot(steps, losses, color=C_COEVO, linewidth=1.6, marker="o", markersize=3,
                label="cross-entropy loss")
        ax.set_ylabel("SFT loss (lower = better fit to gold JSON)", fontsize=11)
        ax.set_title("Phase 2 SFT training trajectory — v2 → v2-coevolved (hardened on bypass cases)",
                     fontsize=12, pad=10)
        if losses:
            ax.set_ylim(bottom=0, top=max(losses) * 1.1)

        lr_entries = [e for e in log_history if "learning_rate" in e]
        if lr_entries:
            ax2 = ax.twinx()
            ax2.plot([e["step"] for e in lr_entries], [e["learning_rate"] for e in lr_entries],
                     color="#1976d2", linewidth=1.2, alpha=0.6, linestyle=":",
                     label="learning rate (cosine decay)")
            ax2.set_ylabel("Learning rate", color="#1976d2", fontsize=10)
            ax2.tick_params(axis="y", labelcolor="#1976d2")
            ax2.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    else:
        print("[skip] log_history has neither 'reward' nor 'loss' entries")
        plt.close()
        return None

    ax.set_xlabel("Optimizer step", fontsize=11)
    ax.legend(loc="upper right" if has_loss else "lower right", framealpha=0.95, fontsize=10)
    ax.grid(alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)

    out = PLOTS / "coevolution_training_curve.png"
    plt.tight_layout()
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"[ok] {out.name}")
    return out


def plot_scammer_phase1_summary() -> Path | None:
    """Scammer-side context: bypass rate vs ScriptedAnalyzer per category (single-shot vs best-of-8)."""
    if not (PHASE1_BESTOF8.exists() and PHASE1_SINGLESHOT.exists()):
        print("[skip] scammer phase1 summary (needs both eval files)")
        return None
    bo8 = json.load(open(PHASE1_BESTOF8))
    ss = json.load(open(PHASE1_SINGLESHOT))

    # Per-seed map for both runs
    bo8_per = {seed: r["bypass_rate"] for seed, r in bo8["per_seed"].items()}
    ss_per = {seed: r["bypass_rate"] for seed, r in ss["per_seed"].items()}
    seed_split = {s["seed"][:70]: s["split"] for s in bo8["samples"]}

    seeds = sorted(bo8_per.keys(), key=lambda s: (seed_split.get(s, "?"), -bo8_per[s]))
    short = []
    for s in seeds:
        t = s.replace("Write a realistic ", "")
        for tail in (" scam message", " scam pretending", " scam asking", " scam promising",
                     " scam claiming", " scam threatening", " scam pre-approving",
                     " scam impersonating", " notification scam"):
            if tail in t:
                t = t.split(tail)[0]
                break
        short.append(t[:35])
    splits = [seed_split.get(s, "?") for s in seeds]
    ss_rates = [ss_per[s] for s in seeds]
    bo8_rates = [bo8_per[s] for s in seeds]

    y = np.arange(len(seeds))
    h = 0.4

    fig, ax = plt.subplots(figsize=(11, 8))
    ax.barh(y - h / 2, ss_rates, h, color="#90caf9",
            edgecolor="#444", linewidth=0.5, label="single-shot inference")
    ax.barh(y + h / 2, bo8_rates, h, color="#1565c0",
            edgecolor="#222", linewidth=0.5, label="best-of-8 inference")

    ax.set_yticks(y)
    ax.set_yticklabels(short, fontsize=9)
    for tick, sp in zip(ax.get_yticklabels(), splits):
        tick.set_color(C_TRAIN if sp == "train" else C_HELDOUT)

    ax.set_xlabel("Scammer bypass rate vs ScriptedAnalyzer (higher = stronger attacker)", fontsize=11)
    ax.set_xlim(0, 1.05)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_title("B.2 phase 1 Scammer: per-category bypass of rule-based defense\n"
                 "(blue tick labels = training categories, purple = held-out novel)",
                 fontsize=11, pad=10)
    ax.legend(loc="lower right", framealpha=0.95, fontsize=10)
    ax.grid(axis="x", alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.invert_yaxis()

    out = PLOTS / "scammer_phase1_per_category.png"
    plt.tight_layout()
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"[ok] {out.name}")
    return out


def main() -> None:
    print(f"Reading from: {LOGS}")
    print(f"Writing to:   {PLOTS}\n")
    generated = []
    for fn in (
        plot_coevolution_headline,
        plot_per_category,
        plot_score_movement,
        plot_training_curve,
        plot_scammer_phase1_summary,
    ):
        out = fn()
        if out:
            generated.append(out)
    print(f"\nGenerated {len(generated)} plot(s):")
    for p in generated:
        print(f"  {p.relative_to(REPO)}")


if __name__ == "__main__":
    main()
