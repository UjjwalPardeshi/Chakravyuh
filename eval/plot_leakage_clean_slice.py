"""Render leakage-clean slice chart from `logs/leakage_clean_slice.json`.

Shows detection rate on the full bench (n=175) vs the leakage-clean slice
(n=50; max cosine sim to nearest training text < 0.7) for each provider
we have per-row scores for. The point: detection holds up on novel text.

Output: plots/chakravyuh_plots/leakage_clean_slice.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


_PROVIDER_LABELS = {
    "scripted": "scripted rules",
    "hf-deepseek-r1": "DeepSeek-R1",
    "hf-deepseek-v3-0324": "DeepSeek-V3",
    "hf-gemma-3-27b-it": "Gemma-3-27B",
    "hf-gpt-oss-120b": "GPT-OSS-120B",
    "hf-llama-3.3-70b-instruct": "Llama-3.3-70B",
    "hf-qwen2.5-72b-instruct": "Qwen2.5-72B",
    "hf-qwen2.5-7b-instruct": "Qwen2.5-7B",
}


def main() -> int:
    src = Path("logs/leakage_clean_slice.json")
    out = Path("plots/chakravyuh_plots/leakage_clean_slice.png")
    data = json.loads(src.read_text(encoding="utf-8"))
    rows = data["rows"]

    rows_sorted = sorted(rows, key=lambda r: r["leakage_clean"]["detection"], reverse=True)
    labels = [_PROVIDER_LABELS.get(r["provider"], r["provider"]) for r in rows_sorted]
    full = [r["full_bench"]["detection"] for r in rows_sorted]
    clean = [r["leakage_clean"]["detection"] for r in rows_sorted]
    deltas = [r["leakage_clean_delta"]["detection_pp"] for r in rows_sorted]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    w = 0.38
    ax.bar(x - w / 2, full, w, label=f"full bench (n={data['rows'][0]['full_bench']['n_scam'] + data['rows'][0]['full_bench']['n_benign']})",
           color="#1565c0", edgecolor="black", linewidth=0.5)
    ax.bar(x + w / 2, clean, w, label=f"leakage-clean (n={data['rows'][0]['leakage_clean']['n_scam'] + data['rows'][0]['leakage_clean']['n_benign']})",
           color="#558b2f", edgecolor="black", linewidth=0.5)

    for i, (f, c, d) in enumerate(zip(full, clean, deltas)):
        ax.text(i - w / 2, f + 0.015, f"{f:.2f}", ha="center", fontsize=8)
        ax.text(i + w / 2, c + 0.015, f"{c:.2f}", ha="center", fontsize=8)
        sign = "+" if d >= 0 else ""
        ax.text(i, max(f, c) + 0.08, f"Δ {sign}{d:.1f}pp", ha="center",
                fontsize=8, color="#c62828" if d < -1 else "#37474f")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Detection rate", fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.set_title(
        f"Leakage-clean slice — cosine gate {data['cosine_gate']} to nearest training text\n"
        "If detection drops on the clean slice, the model leaned on memorisation",
        fontsize=11, fontweight="bold",
    )
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
