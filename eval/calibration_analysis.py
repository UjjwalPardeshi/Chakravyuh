"""Compute Expected Calibration Error (ECE) + render reliability diagram.

Uses per-row eval data (`logs/eval_sft_per_row.jsonl`) to compute the
calibration of the SFT-baseline Analyzer. The v2 LoRA per-row scores
are not yet logged (B.12 in WIN_PLAN — needs GPU re-inference); when
they ship the same script renders both side by side.

Outputs:
  - logs/calibration_sft.json                    (ECE + per-bin counts)
  - plots/chakravyuh_plots/ece_reliability.png   (reliability diagram)

Reliability-diagram convention (Guo et al. 2017): bin scores into 10
equal-width bins, plot bin-mean confidence (x) vs bin-mean accuracy (y).
A perfectly calibrated model lies on y = x. ECE is the weighted average
of |confidence − accuracy| across bins, weighted by bin size.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class BinStats:
    bin_lo: float
    bin_hi: float
    n: int
    mean_score: float
    accuracy: float
    abs_gap: float


@dataclass(frozen=True)
class CalibrationReport:
    name: str
    n: int
    ece: float
    mce: float
    bins: list[BinStats]
    notes: list[str]


def _load_per_row(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _compute(name: str, rows: list[dict], n_bins: int = 10) -> CalibrationReport:
    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    bins: list[BinStats] = []
    notes: list[str] = []
    total_abs = 0.0
    n_total = 0
    mce = 0.0
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            in_bin = [r for r in rows if lo <= r["score"] <= hi]
        else:
            in_bin = [r for r in rows if lo <= r["score"] < hi]
        n = len(in_bin)
        if n == 0:
            bins.append(BinStats(lo, hi, 0, 0.0, 0.0, 0.0))
            continue
        mean_score = sum(r["score"] for r in in_bin) / n
        accuracy = sum(int(bool(r.get("ground_truth", r.get("is_scam")))) for r in in_bin) / n
        abs_gap = abs(mean_score - accuracy)
        bins.append(BinStats(lo, hi, n, mean_score, accuracy, abs_gap))
        total_abs += n * abs_gap
        n_total += n
        if abs_gap > mce:
            mce = abs_gap
    ece = total_abs / max(1, n_total)
    return CalibrationReport(
        name=name,
        n=n_total,
        ece=round(ece, 4),
        mce=round(mce, 4),
        bins=bins,
        notes=notes,
    )


def _plot(reports: list[CalibrationReport], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], "k:", linewidth=1, label="perfect calibration (y = x)")
    colors = {"sft": "#1565c0", "scripted": "#c62828", "v2_lora": "#558b2f"}
    for r in reports:
        color = colors.get(r.name, "#6a1b9a")
        xs = [b.mean_score for b in r.bins if b.n > 0]
        ys = [b.accuracy for b in r.bins if b.n > 0]
        sizes = [max(20, b.n * 4) for b in r.bins if b.n > 0]
        label = f"{r.name} (ECE = {r.ece:.3f}, n = {r.n})"
        ax.scatter(xs, ys, s=sizes, alpha=0.7, color=color, edgecolor="black", linewidth=0.5,
                   label=label)
        ax.plot(xs, ys, color=color, linewidth=1.2, alpha=0.6)
    ax.set_xlabel("Confidence (bin-mean predicted score)", fontsize=11)
    ax.set_ylabel("Accuracy (bin-mean ground-truth label)", fontsize=11)
    ax.set_title(
        "Reliability diagram — Chakravyuh defenders\n"
        "Lower ECE = better calibrated · marker size ∝ bin n",
        fontsize=12, fontweight="bold",
    )
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sft-per-row",
        type=Path,
        default=Path("logs/eval_sft_per_row.jsonl"),
        help="Per-row eval JSONL for the SFT baseline.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("logs/calibration_sft.json"),
    )
    parser.add_argument(
        "--out-plot",
        type=Path,
        default=Path("plots/chakravyuh_plots/ece_reliability.png"),
    )
    args = parser.parse_args()

    reports: list[CalibrationReport] = []
    if args.sft_per_row.exists():
        rows = _load_per_row(args.sft_per_row)
        report = _compute("sft", rows)
        reports.append(report)
        print(f"sft: ECE = {report.ece:.4f} · MCE = {report.mce:.4f} · n = {report.n}")
    else:
        print(f"warning: {args.sft_per_row} not found — skipping SFT")

    if not reports:
        print("error: no per-row data found")
        return 2

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps([asdict(r) for r in reports], indent=2, default=lambda o: asdict(o)),
        encoding="utf-8",
    )
    print(f"Wrote {args.out_json}")
    _plot(reports, args.out_plot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
