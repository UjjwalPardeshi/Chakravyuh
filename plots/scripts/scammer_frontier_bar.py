"""Bar chart for the frontier-LLMs-as-Scammer comparison.

Shows bypass rate (single-shot) for each frontier model alongside our
trained 0.5B Scammer LoRA Phase 1 (single-shot AND best-of-8). Mirrors the
defender-side story: a small trained adversary should match or beat
untrained large models because evading rule-based defenses is a learnable
structure, not a capacity problem.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent.parent
CSV_PATH = REPO / "logs" / "scammer_frontier_comparison.csv"
OUT_DIR = REPO / "plots" / "chakravyuh_plots"

NICE_NAMES = {
    "scammer-lora-phase1-best-of-8": ("Scammer LoRA\n0.5B + r=16 (BO8)", "#0a7e44"),
    "scammer-lora-phase1-single-shot": ("Scammer LoRA\n0.5B + r=16 (SS)", "#34a853"),
    "hf-scammer-llama-3.3-70b-instruct": ("Llama-3.3-70B\n70B (untrained)", "#3b82f6"),
    "hf-scammer-qwen2.5-72b-instruct": ("Qwen2.5-72B\n72B (untrained)", "#3b82f6"),
    "hf-scammer-qwen2.5-7b-instruct": ("Qwen2.5-7B base\n7B (untrained)", "#f59e0b"),
    "hf-scammer-deepseek-v3-0324": ("DeepSeek-V3\n671B MoE (untrained)", "#ef4444"),
    "hf-scammer-gpt-oss-120b": ("gpt-oss-120b\n120B (untrained)", "#3b82f6"),
    "hf-scammer-gemma-3-27b-it": ("gemma-3-27b\n27B (untrained)", "#ef4444"),
}

ORDER = [
    "scammer-lora-phase1-best-of-8",
    "hf-scammer-gpt-oss-120b",
    "hf-scammer-llama-3.3-70b-instruct",
    "hf-scammer-qwen2.5-7b-instruct",
    "scammer-lora-phase1-single-shot",
    "hf-scammer-qwen2.5-72b-instruct",
    "hf-scammer-gemma-3-27b-it",
    "hf-scammer-deepseek-v3-0324",
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open() as f:
        rows = {r["provider"]: r for r in csv.DictReader(f)}

    labels: list[str] = []
    rates: list[float] = []
    cis: list[tuple[float, float]] = []
    colors: list[str] = []
    for prov in ORDER:
        if prov not in rows:
            continue
        r = rows[prov]
        label, color = NICE_NAMES.get(prov, (prov, "#9ca3af"))
        labels.append(label)
        rates.append(float(r["bypass_rate"]) * 100)
        cis.append((float(r["ci_low"]) * 100, float(r["ci_high"]) * 100))
        colors.append(color)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = list(range(len(labels)))
    yerr_lo = [r - c[0] for r, c in zip(rates, cis)]
    yerr_hi = [c[1] - r for r, c in zip(rates, cis)]
    ax.bar(
        x, rates, color=colors, edgecolor="#1f2937", linewidth=0.6,
        yerr=[yerr_lo, yerr_hi], capsize=4,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Scripted-defender bypass rate (%)", fontsize=11)
    ax.set_title(
        "Frontier-LLMs-as-Scammer · n=16 attack categories · defender = ScriptedAnalyzer\n"
        "Our trained 0.5B beats every untrained frontier model (BO8) — including 671B DeepSeek-V3",
        fontsize=11,
    )
    for i, v in enumerate(rates):
        ax.text(i, v + 2, f"{v:.1f}%", ha="center", fontsize=8)
    ax.set_ylim(0, 100)
    fig.tight_layout()
    out = OUT_DIR / "scammer_frontier_bar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
