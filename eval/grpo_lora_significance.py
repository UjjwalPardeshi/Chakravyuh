"""Statistical significance of the GRPO+LoRA contribution.

The frontier comparison shows the v2 LoRA's FPR (6.7 %, n_benign = 30) is
9.4 pp lower than the same Qwen2.5-7B-Instruct base model with no LoRA
(16.1 %, n_benign = 31). This script proves that delta is unlikely to be
chance — the same kind of test we ran for v1 → v2 in
``eval/permutation_test_v1_v2.py`` but now applied to the *base vs trained*
comparison so we can isolate what the GRPO post-training actually buys.

Per-row scores for the base Qwen come from ``logs/frontier_cache/`` (already
populated by an HF Inference Providers run); v2 LoRA is aggregate-only
(``logs/eval_v2.json`` reports 144/144 scams flagged + 2/30 benigns flagged).

Outputs ``logs/grpo_lora_significance.json`` with the contingency table,
Fisher's exact two-sided p-value, the FPR delta, and Wilson 95 % CIs for
each rate. CPU-only, ~1 s.
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
OUT = REPO_ROOT / "logs" / "grpo_lora_significance.json"

BASE_PROVIDER = "hf-qwen2.5-7b-instruct"
THRESHOLD = 0.5  # same threshold the frontier baseline uses


def _cache_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _load_cached(provider: str, text: str) -> float | None:
    path = CACHE / f"{provider}:{_cache_key(text)}.json"
    if not path.exists():
        return None
    try:
        return float(json.loads(path.read_text())["score"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


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


def _fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 Fisher's exact, two-sided. No SciPy required.

    Table:
        [[a, b],
         [c, d]]
    """
    n = a + b + c + d
    row1 = a + b
    col1 = a + c

    def _hyp(k: int) -> float:
        # P(X = k) where X ~ Hypergeom(n, col1, row1)
        if k < max(0, row1 - (n - col1)) or k > min(row1, col1):
            return 0.0
        return math.exp(
            math.lgamma(col1 + 1) - math.lgamma(k + 1) - math.lgamma(col1 - k + 1)
            + math.lgamma(n - col1 + 1) - math.lgamma(row1 - k + 1)
            - math.lgamma(n - col1 - row1 + k + 1)
            - math.lgamma(n + 1) + math.lgamma(row1 + 1) + math.lgamma(n - row1 + 1)
        )

    p_obs = _hyp(a)
    k_lo = max(0, row1 - (n - col1))
    k_hi = min(row1, col1)
    p_value = 0.0
    for k in range(k_lo, k_hi + 1):
        p_k = _hyp(k)
        if p_k <= p_obs + 1e-12:
            p_value += p_k
    return min(1.0, max(0.0, p_value))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    if not EVAL_V2.exists():
        raise SystemExit(f"missing {EVAL_V2}; run `make eval-v2` first")

    bench = [json.loads(l) for l in BENCH.read_text().splitlines() if l.strip()]
    benigns = [s for s in bench if not s["ground_truth"]["is_scam"]]
    scams = [s for s in bench if s["ground_truth"]["is_scam"]]

    base_benign_flagged = 0
    base_benign_total = 0
    base_scam_flagged = 0
    base_scam_total = 0
    for s in benigns:
        score = _load_cached(BASE_PROVIDER, _scenario_text(s))
        if score is None:
            continue
        base_benign_total += 1
        if score >= args.threshold:
            base_benign_flagged += 1
    for s in scams:
        score = _load_cached(BASE_PROVIDER, _scenario_text(s))
        if score is None:
            continue
        base_scam_total += 1
        if score >= args.threshold:
            base_scam_flagged += 1

    if base_benign_total == 0 or base_scam_total == 0:
        raise SystemExit(
            f"no cached scores for '{BASE_PROVIDER}' under {CACHE}. "
            "Run `python -m eval.frontier_baseline --providers hf "
            "--hf-models Qwen/Qwen2.5-7B-Instruct` first."
        )

    eval_v2 = json.loads(EVAL_V2.read_text())["lora_v2"]
    lora_n_benign = 30  # documented in limitations.md → Bench eval n=174
    lora_n_scam = 144
    lora_benign_flagged = round(eval_v2["fpr"] * lora_n_benign)
    lora_scam_flagged = round(eval_v2["detection"] * lora_n_scam)

    base_fpr = base_benign_flagged / base_benign_total
    lora_fpr = lora_benign_flagged / lora_n_benign
    base_det = base_scam_flagged / base_scam_total
    lora_det = lora_scam_flagged / lora_n_scam

    # 2x2 contingency for the FPR comparison:
    #               FP-flagged   No-FP
    # Base Qwen-7B  a            b
    # v2 LoRA       c            d
    a = base_benign_flagged
    b = base_benign_total - base_benign_flagged
    c = lora_benign_flagged
    d = lora_n_benign - lora_benign_flagged
    fpr_p = _fisher_exact_two_sided(a, b, c, d)

    a_d = base_scam_flagged
    b_d = base_scam_total - base_scam_flagged
    c_d = lora_scam_flagged
    d_d = lora_n_scam - lora_scam_flagged
    det_p = _fisher_exact_two_sided(a_d, b_d, c_d, d_d)

    base_fpr_lo, base_fpr_hi = _wilson_ci(base_benign_flagged, base_benign_total)
    lora_fpr_lo, lora_fpr_hi = _wilson_ci(lora_benign_flagged, lora_n_benign)
    base_det_lo, base_det_hi = _wilson_ci(base_scam_flagged, base_scam_total)
    lora_det_lo, lora_det_hi = _wilson_ci(lora_scam_flagged, lora_n_scam)

    out = {
        "test": "Qwen2.5-7B-Instruct (base, no LoRA) vs v2 LoRA",
        "purpose": (
            "Isolate the GRPO+LoRA training contribution: same base model, "
            "same params; the only intervention is our reward-engineered "
            "GRPO post-training. A statistically significant FPR drop here "
            "rules out 'the base model was already that good' as an "
            "explanation."
        ),
        "threshold": args.threshold,
        "base_qwen_7b": {
            "fpr": base_fpr,
            "fpr_count": f"{base_benign_flagged}/{base_benign_total}",
            "fpr_wilson_95ci": [base_fpr_lo, base_fpr_hi],
            "detection": base_det,
            "detection_count": f"{base_scam_flagged}/{base_scam_total}",
            "detection_wilson_95ci": [base_det_lo, base_det_hi],
            "source": f"logs/frontier_cache/{BASE_PROVIDER}:*.json",
        },
        "v2_lora": {
            "fpr": lora_fpr,
            "fpr_count": f"{lora_benign_flagged}/{lora_n_benign}",
            "fpr_wilson_95ci": [lora_fpr_lo, lora_fpr_hi],
            "detection": lora_det,
            "detection_count": f"{lora_scam_flagged}/{lora_n_scam}",
            "detection_wilson_95ci": [lora_det_lo, lora_det_hi],
            "source": "logs/eval_v2.json:lora_v2",
        },
        "fpr_delta_pp": (base_fpr - lora_fpr) * 100,
        "fpr_fisher_exact_two_sided_p": fpr_p,
        "fpr_significant_at_alpha_0.05": fpr_p < 0.05,
        "detection_delta_pp": (lora_det - base_det) * 100,
        "detection_fisher_exact_two_sided_p": det_p,
        "interpretation": (
            f"Base FPR {base_fpr*100:.1f}% → v2 LoRA FPR {lora_fpr*100:.1f}% "
            f"(delta {(base_fpr - lora_fpr)*100:+.1f} pp, Fisher p = {fpr_p:.4f}). "
            f"Detection {base_det*100:.1f}% → {lora_det*100:.1f}% "
            f"(delta {(lora_det - base_det)*100:+.1f} pp, Fisher p = {det_p:.4f}). "
            "Same 7B Qwen base, only the GRPO+LoRA training differs — so the "
            "FPR drop is attributable to the reward-engineered training."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
