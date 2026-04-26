"""Pairwise statistical-significance tests for the frontier comparison.

For each open-weight frontier model in ``logs/frontier_cache/``, computes:
  - 2x2 contingency vs the v2 LoRA aggregate (from ``logs/eval_v2.json``)
  - Fisher's exact two-sided p-value on the FPR delta
  - Wilson 95 % CI for each rate

Same-bench, same-prompt, same-threshold. The v2 LoRA aggregate is the only
non-per-row term (we don't have per-row logits yet — that's the B.12 work).
At n_benign ≈ 30, only large FPR gaps pass α = 0.05; the smaller deltas are
"directional" and call for the bench expansion in B.11. Honest disclosure.

Output: ``logs/frontier_significance.json`` — one entry per provider.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH = REPO_ROOT / "data" / "chakravyuh-bench-v0" / "scenarios.jsonl"
CACHE = REPO_ROOT / "logs" / "frontier_cache"
EVAL_V2 = REPO_ROOT / "logs" / "eval_v2.json"
OUT = REPO_ROOT / "logs" / "frontier_significance.json"

THRESHOLD = 0.5


def _cache_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _scenario_text(scenario: dict) -> str:
    return " ".join(
        msg["text"] for msg in scenario["attack_sequence"]
        if msg["sender"] == "scammer"
    )


def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom))


def _hypergeom_pmf(k: int, n: int, K: int, N: int) -> float:
    if k < max(0, n - (N - K)) or k > min(n, K):
        return 0.0
    return math.exp(
        math.lgamma(K + 1) - math.lgamma(k + 1) - math.lgamma(K - k + 1)
        + math.lgamma(N - K + 1) - math.lgamma(n - k + 1)
        - math.lgamma(N - K - n + k + 1)
        - math.lgamma(N + 1) + math.lgamma(n + 1) + math.lgamma(N - n + 1)
    )


def _fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    n = a + b + c + d
    row1 = a + b
    col1 = a + c
    p_obs = _hypergeom_pmf(a, row1, col1, n)
    k_lo = max(0, row1 - (n - col1))
    k_hi = min(row1, col1)
    p_value = 0.0
    for k in range(k_lo, k_hi + 1):
        p_k = _hypergeom_pmf(k, row1, col1, n)
        if p_k <= p_obs + 1e-12:
            p_value += p_k
    return min(1.0, max(0.0, p_value))


def _provider_counts(provider: str, bench: list[dict], threshold: float) -> dict | None:
    benign_total = benign_flagged = scam_total = scam_flagged = 0
    for s in bench:
        path = CACHE / f"{provider}:{_cache_key(_scenario_text(s))}.json"
        if not path.exists():
            continue
        try:
            score = float(json.loads(path.read_text())["score"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            continue
        is_scam = s["ground_truth"]["is_scam"]
        flagged = score >= threshold
        if is_scam:
            scam_total += 1
            scam_flagged += int(flagged)
        else:
            benign_total += 1
            benign_flagged += int(flagged)
    if benign_total == 0 or scam_total == 0:
        return None
    return {
        "benign_total": benign_total,
        "benign_flagged": benign_flagged,
        "scam_total": scam_total,
        "scam_flagged": scam_flagged,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    bench = [json.loads(l) for l in BENCH.read_text().splitlines() if l.strip()]
    eval_v2 = json.loads(EVAL_V2.read_text())["lora_v2"]
    lora_n_benign = 30
    lora_n_scam = 144
    lora_benign_flagged = round(eval_v2["fpr"] * lora_n_benign)
    lora_scam_flagged = round(eval_v2["detection"] * lora_n_scam)

    providers = sorted({
        p.name.split(":", 1)[0]
        for p in CACHE.glob("*.json")
        if ":" in p.name and p.name.startswith("hf-")
    })

    rows = []
    for prov in providers:
        counts = _provider_counts(prov, bench, args.threshold)
        if counts is None:
            continue
        bf = counts["benign_flagged"]
        bt = counts["benign_total"]
        sf = counts["scam_flagged"]
        st = counts["scam_total"]

        fpr = bf / bt
        det = sf / st
        fpr_lo, fpr_hi = _wilson_ci(bf, bt)
        det_lo, det_hi = _wilson_ci(sf, st)

        # vs v2 LoRA (rows: provider, lora)
        fpr_p = _fisher_exact_two_sided(
            bf, bt - bf, lora_benign_flagged, lora_n_benign - lora_benign_flagged,
        )
        det_p = _fisher_exact_two_sided(
            sf, st - sf, lora_scam_flagged, lora_n_scam - lora_scam_flagged,
        )

        rows.append({
            "provider": prov,
            "n_benign": bt,
            "n_scam": st,
            "fpr": fpr,
            "fpr_count": f"{bf}/{bt}",
            "fpr_wilson_95ci": [fpr_lo, fpr_hi],
            "detection": det,
            "detection_count": f"{sf}/{st}",
            "detection_wilson_95ci": [det_lo, det_hi],
            "vs_v2_lora": {
                "fpr_delta_pp": (fpr - eval_v2["fpr"]) * 100,
                "fpr_fisher_exact_two_sided_p": fpr_p,
                "fpr_significant_at_0.05": fpr_p < 0.05,
                "detection_delta_pp": (det - eval_v2["detection"]) * 100,
                "detection_fisher_exact_two_sided_p": det_p,
                "detection_significant_at_0.05": det_p < 0.05,
            },
        })

    out = {
        "v2_lora_reference": {
            "fpr": eval_v2["fpr"],
            "fpr_count": f"{lora_benign_flagged}/{lora_n_benign}",
            "detection": eval_v2["detection"],
            "detection_count": f"{lora_scam_flagged}/{lora_n_scam}",
            "source": "logs/eval_v2.json:lora_v2",
        },
        "threshold": args.threshold,
        "comment": (
            "All comparisons use Fisher's exact two-sided test on the 2x2 "
            "contingency between provider and v2 LoRA. The frontier providers "
            "use n_benign=31 (full bench file); v2 LoRA uses n_benign=30 (one "
            "row dropped on inference per logs/eval_v2.json — see "
            "docs/limitations.md). At this sample size only large FPR gaps "
            "(>~20 pp) reach alpha=0.05; smaller directional improvements "
            "call for B.11 benign-corpus expansion."
        ),
        "rows": rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2))

    print(f"\n=== Frontier vs v2 LoRA — Fisher's Exact (two-sided) ===")
    print(f"v2 LoRA reference: FPR {eval_v2['fpr']*100:.1f}% ({lora_benign_flagged}/{lora_n_benign})")
    print(f"{'Provider':<28} {'FPR':>7} {'ΔFPR':>8} {'p':>9} {'sig?':>6}")
    print("-" * 64)
    for r in rows:
        sig = "✓" if r["vs_v2_lora"]["fpr_significant_at_0.05"] else "—"
        print(
            f"{r['provider']:<28} {r['fpr']*100:>6.1f}% "
            f"{r['vs_v2_lora']['fpr_delta_pp']:>+7.1f}pp "
            f"{r['vs_v2_lora']['fpr_fisher_exact_two_sided_p']:>9.4f} "
            f"{sig:>6}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
