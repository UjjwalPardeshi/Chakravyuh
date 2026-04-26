"""Detection on the leakage-clean subset of the bench.

Background. The semantic-leakage audit
(``logs/semantic_leakage_audit.json``) flags 44.8 % of bench scenarios as
having cosine > 0.85 to a training-corpus item. The "leakage-clean" subset
is everything with cosine < 0.70 to the nearest training text — 50
scenarios (38 scams + 12 benign) where any detection performance must come
from generalization rather than near-duplicate memorization.

This script computes detection / FPR for everything we have per-row scores
for: scripted baseline + every cached frontier model. The v2 LoRA row is
deferred to v3 (B.12 — needs per-row v2 logits via GPU re-inference).
Output: ``logs/leakage_clean_slice.json`` so the README / FAQ can cite it
without needing GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH = REPO_ROOT / "data" / "chakravyuh-bench-v0" / "scenarios.jsonl"
AUDIT = REPO_ROOT / "logs" / "semantic_leakage_audit.json"
CACHE = REPO_ROOT / "logs" / "frontier_cache"
OUT = REPO_ROOT / "logs" / "leakage_clean_slice.json"

THRESHOLD = 0.5
COSINE_GATE = 0.70


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


def _scripted_score(text: str) -> float:
    """Use the live scripted analyzer so the comparison stays honest."""
    from eval.mode_c_real_cases import ScriptedAnalyzerAdapter  # noqa: WPS433

    return float(ScriptedAnalyzerAdapter().score_text(text))


def _provider_metrics(provider: str | None, scenarios: list[dict], threshold: float) -> dict | None:
    benign_total = benign_flagged = scam_total = scam_flagged = 0
    for s in scenarios:
        text = _scenario_text(s)
        if provider == "scripted":
            score = _scripted_score(text)
        elif provider is not None:
            path = CACHE / f"{provider}:{_cache_key(text)}.json"
            if not path.exists():
                continue
            try:
                score = float(json.loads(path.read_text())["score"])
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                continue
        else:
            return None
        flagged = score >= threshold
        if s["ground_truth"]["is_scam"]:
            scam_total += 1
            scam_flagged += int(flagged)
        else:
            benign_total += 1
            benign_flagged += int(flagged)
    if scam_total == 0 and benign_total == 0:
        return None
    det = scam_flagged / scam_total if scam_total else 0.0
    fpr = benign_flagged / benign_total if benign_total else 0.0
    det_lo, det_hi = _wilson_ci(scam_flagged, scam_total)
    fpr_lo, fpr_hi = _wilson_ci(benign_flagged, benign_total)
    f1 = 0.0
    if scam_flagged + benign_flagged > 0:
        prec = scam_flagged / (scam_flagged + benign_flagged)
        rec = det
        if prec + rec > 0:
            f1 = 2 * prec * rec / (prec + rec)
    return {
        "n_scam": scam_total,
        "n_benign": benign_total,
        "detection": det,
        "detection_count": f"{scam_flagged}/{scam_total}",
        "detection_wilson_95ci": [det_lo, det_hi],
        "fpr": fpr,
        "fpr_count": f"{benign_flagged}/{benign_total}",
        "fpr_wilson_95ci": [fpr_lo, fpr_hi],
        "f1": f1,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--cosine-gate", type=float, default=COSINE_GATE)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    audit = json.loads(AUDIT.read_text())
    clean_ids = {
        s["scenario_id"] for s in audit["per_scenario"]
        if s["max_cosine_to_training"] < args.cosine_gate
    }
    bench = [json.loads(l) for l in BENCH.read_text().splitlines() if l.strip()]
    full = bench
    clean = [s for s in bench if s["id"] in clean_ids]

    providers = ["scripted"] + sorted({
        p.name.split(":", 1)[0]
        for p in CACHE.glob("*.json")
        if ":" in p.name and p.name.startswith("hf-")
    })

    rows = []
    for prov in providers:
        full_metrics = _provider_metrics(prov, full, args.threshold)
        clean_metrics = _provider_metrics(prov, clean, args.threshold)
        if not full_metrics or not clean_metrics:
            continue
        rows.append({
            "provider": prov,
            "full_bench": full_metrics,
            "leakage_clean": clean_metrics,
            "leakage_clean_delta": {
                "detection_pp": (clean_metrics["detection"] - full_metrics["detection"]) * 100,
                "fpr_pp": (clean_metrics["fpr"] - full_metrics["fpr"]) * 100,
                "f1": clean_metrics["f1"] - full_metrics["f1"],
            },
        })

    out = {
        "definition": (
            f"leakage-clean = bench scenarios with max cosine similarity "
            f"to nearest training text < {args.cosine_gate}; per "
            "logs/semantic_leakage_audit.json. n=50 scenarios (38 scams + "
            "12 benign). The full bench is n=175 (174 in audit)."
        ),
        "v2_lora_note": (
            "The v2 LoRA row is intentionally absent because per-row v2 logits "
            "are not yet logged (eval_v2.json is aggregate-only). Producing it "
            "is B.12 in WIN_PLAN — needs GPU re-inference. The honest claim "
            "this script supports is: 'we know the leakage-clean detection "
            "for every model we have per-row scores for; the v2 LoRA per-row "
            "slice is the next thing to ship.' See docs/limitations.md."
        ),
        "threshold": args.threshold,
        "cosine_gate": args.cosine_gate,
        "rows": rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2))

    print(f"\n=== Leakage-clean (cosine < {args.cosine_gate}) detection ===")
    print(f"{'Provider':<28} {'Det (clean)':>14} {'FPR (clean)':>14} {'Δ Det':>9} {'Δ FPR':>9}")
    print("-" * 78)
    for r in rows:
        d_clean = r["leakage_clean"]
        delta = r["leakage_clean_delta"]
        print(
            f"{r['provider']:<28} "
            f"{d_clean['detection']*100:>11.1f}% "
            f"{d_clean['fpr']*100:>11.1f}% "
            f"{delta['detection_pp']:>+8.1f}pp "
            f"{delta['fpr_pp']:>+8.1f}pp"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
