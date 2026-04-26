"""Aggregate ₹ at risk across the bench and produce the headline economic-loss number.

For each scenario in `data/chakravyuh-bench-v0/scenarios.jsonl` we read
`metadata.loss_amount_inr` and join with a per-row eval log
(`logs/eval_v2_per_row.jsonl` by default) to compute:

  - ₹ at risk (sum of loss_amount_inr across scams in the bench)
  - ₹ prevented (sum across scams the analyzer flagged early)
  - ₹ leaked    (sum across scams the analyzer missed AND money was extracted)
  - bench-level prevention rate (₹ prevented / ₹ at risk)

The headline phrasing ("Chakravyuh prevented ₹X cr of expected loss
across the n=174 bench") is sourced from this script — never fabricated.

Usage:
    python eval/rupee_weighted_eval.py \
        --bench data/chakravyuh-bench-v0/scenarios.jsonl \
        --eval-log logs/eval_v2_per_row.jsonl \
        --output logs/rupee_weighted_eval.json

The eval log must be JSONL with at least these fields per row:
    scenario_id   (matches `id` in the bench)
    flagged       (bool)
    money_extracted (bool, optional — defaults to "missed scam = money lost")

If `--eval-log` is omitted the script computes only the gross ₹ at risk
and exits — useful as a bench summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RupeeReport:
    n_scenarios: int
    n_scams_with_amount: int
    rupees_at_risk: float
    rupees_prevented: float
    rupees_leaked: float
    prevention_rate: float
    notes: list[str]


def _load_bench(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        out[row["id"]] = row
    return out


def _load_eval_log(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        scenario_id = row.get("scenario_id") or row.get("id")
        if scenario_id is None:
            continue
        out[str(scenario_id)] = row
    return out


def compute(
    bench: dict[str, dict],
    eval_log: dict[str, dict] | None,
) -> RupeeReport:
    notes: list[str] = []
    rupees_at_risk = 0.0
    rupees_prevented = 0.0
    rupees_leaked = 0.0
    n_scams_with_amount = 0

    for sid, scenario in bench.items():
        metadata = scenario.get("metadata") or {}
        ground = scenario.get("ground_truth") or {}
        is_scam = bool(ground.get("is_scam", True))
        if not is_scam:
            continue
        loss_raw = metadata.get("loss_amount_inr")
        if loss_raw is None:
            continue
        try:
            loss = float(loss_raw)
        except (TypeError, ValueError):
            notes.append(f"{sid}: non-numeric loss_amount_inr={loss_raw!r}")
            continue
        if loss <= 0:
            continue
        n_scams_with_amount += 1
        rupees_at_risk += loss
        if eval_log is None:
            continue
        row = eval_log.get(sid)
        if row is None:
            notes.append(f"{sid}: no eval-log row")
            continue
        flagged = bool(row.get("flagged"))
        # If money_extracted is unspecified, assume the bench's labelled
        # outcome (most scams are "money_extracted" in the bench v0 set;
        # see `metadata.outcome`).
        if "money_extracted" in row:
            money = bool(row["money_extracted"])
        else:
            money = (metadata.get("outcome") == "money_extracted")
        if flagged:
            rupees_prevented += loss
        elif money:
            rupees_leaked += loss

    prevention_rate = (
        rupees_prevented / rupees_at_risk if rupees_at_risk > 0 else 0.0
    )
    return RupeeReport(
        n_scenarios=len(bench),
        n_scams_with_amount=n_scams_with_amount,
        rupees_at_risk=round(rupees_at_risk, 2),
        rupees_prevented=round(rupees_prevented, 2),
        rupees_leaked=round(rupees_leaked, 2),
        prevention_rate=round(prevention_rate, 4),
        notes=notes,
    )


def _format_inr(amount: float) -> str:
    if amount >= 1e7:
        return f"₹{amount / 1e7:.2f} cr"
    if amount >= 1e5:
        return f"₹{amount / 1e5:.2f} lakh"
    return f"₹{amount:,.0f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bench",
        type=Path,
        default=Path("data/chakravyuh-bench-v0/scenarios.jsonl"),
        help="Path to bench scenarios JSONL.",
    )
    parser.add_argument(
        "--eval-log",
        type=Path,
        default=None,
        help=(
            "Optional per-row JSONL with `scenario_id` + `flagged` "
            "(+ optional `money_extracted`). When omitted, only ₹ at risk is computed."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("logs/rupee_weighted_eval.json"),
        help="Path to write the JSON report.",
    )
    args = parser.parse_args()

    if not args.bench.exists():
        print(f"error: bench not found: {args.bench}", file=sys.stderr)
        return 2

    bench = _load_bench(args.bench)
    eval_log = _load_eval_log(args.eval_log) if args.eval_log else None
    report = compute(bench, eval_log)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    print(f"Bench: {report.n_scenarios} scenarios")
    print(f"Scams with loss_amount_inr: {report.n_scams_with_amount}")
    print(f"₹ at risk:    {_format_inr(report.rupees_at_risk)}")
    if eval_log is not None:
        print(f"₹ prevented:  {_format_inr(report.rupees_prevented)}")
        print(f"₹ leaked:     {_format_inr(report.rupees_leaked)}")
        print(f"Prevention rate: {report.prevention_rate * 100:.1f}%")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
