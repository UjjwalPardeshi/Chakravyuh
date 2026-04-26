"""Traditional ML baselines on the 11-signal feature set.

Audit Gap 9. Question the audit raises: *"How does a cheap LogReg / XGBoost
on your 11 signals compare? If a 5-minute classifier matches your LoRA,
the GRPO training adds no value."*

This script extracts the 11 boolean AnalyzerSignal features that
:class:`ScriptedAnalyzer` computes from each scammer message, plus four
trivial text features (length, OTP-mention, OTP-provided, suspicious-link
flag), then trains:

  - ``LogisticRegression`` (linear baseline — close to the hand-tuned
    rule weights, but with weights *learned* from data)
  - ``GradientBoostingClassifier`` (sklearn's built-in tree booster —
    captures non-linear feature interactions)

Both are evaluated on the same 175-scenario bench used everywhere else.
**No GPU.** Total wall-clock <30 seconds.

CV protocol: stratified 5-fold cross-validation. Per-fold metrics are
averaged with the standard error reported. The "trained on the bench" is
intentional — these are not held-out generalization claims, they are the
"best you can do with traditional ML on these features" upper bound. If
this still loses to the LoRA, that's the strongest possible "GRPO + LoRA
adds value beyond feature engineering" evidence.

Output:
  - ``logs/traditional_ml_baselines.json`` — per-model metrics + CV stats
  - Updates ``data/chakravyuh-bench-v0/baselines.json`` `baselines` list
    with ``LogisticRegression`` and ``GradientBoostingClassifier`` rows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, stdev

REPO = Path(__file__).resolve().parent.parent
BENCH = REPO / "data" / "chakravyuh-bench-v0" / "scenarios.jsonl"
BASELINES = REPO / "data" / "chakravyuh-bench-v0" / "baselines.json"
OUT = REPO / "logs" / "traditional_ml_baselines.json"

SIGNAL_NAMES = [
    "urgency",
    "impersonation",
    "info_request",
    "suspicious_link",
    "unusual_amount",
    "unknown_sender",
    "authority",
    "fear",
    "greed",
    "empathy",
    "financial_lure",
]


def _scenario_text(scenario: dict) -> str:
    return " ".join(
        m["text"] for m in scenario["attack_sequence"]
        if m["sender"] == "scammer"
    )


def _signal_features(scenario: dict) -> list[float]:
    """11 boolean signal features (1.0 / 0.0) + 4 simple text features.

    Reuses the live `ScriptedAnalyzer` so the feature extraction is
    exactly what the rule baseline sees — fair comparison.
    """
    from chakravyuh_env.agents.analyzer import ScriptedAnalyzer
    from chakravyuh_env.schemas import ChatMessage, Observation  # noqa: WPS433

    text = _scenario_text(scenario)
    if not text:
        return [0.0] * (len(SIGNAL_NAMES) + 4)

    obs = Observation(
        agent_role="analyzer",
        turn=1,
        chat_history=[ChatMessage(sender="scammer", turn=1, text=text)],
    )
    analyzer = ScriptedAnalyzer()
    action = analyzer.act(obs)
    fired = {s.value if hasattr(s, "value") else str(s) for s in action.signals}
    booleans = [1.0 if name in fired else 0.0 for name in SIGNAL_NAMES]
    # Trivial text features (length, presence of OTP regex patterns,
    # suspicious-link flag) — strict superset of the rule features so
    # the ML model has at least the same information as the rules.
    extras = [
        float(min(len(text), 2000)) / 2000.0,        # length in [0, 1]
        1.0 if any(k in text.lower() for k in ("otp", "verification code", "pin")) else 0.0,
        1.0 if any(k in text.lower() for k in ("https://bit.ly", "tinyurl", "rb.gy")) else 0.0,
        1.0 if "₹" in text else 0.0,
    ]
    return booleans + extras


def _eval_model(model, X, y) -> dict:
    """Train on full set + report point metrics; CV for variance."""
    from sklearn.model_selection import StratifiedKFold

    model.fit(X, y)
    preds = model.predict(X)
    scores = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else preds

    # Aggregate metrics (training-set; the CV section below gives held-out)
    tp = sum(1 for p, t in zip(preds, y) if p == 1 and t == 1)
    fp = sum(1 for p, t in zip(preds, y) if p == 1 and t == 0)
    fn = sum(1 for p, t in zip(preds, y) if p == 0 and t == 1)
    tn = sum(1 for p, t in zip(preds, y) if p == 0 and t == 0)
    detection = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = 2 * precision * detection / (precision + detection) if (precision + detection) else 0.0

    cv_dets, cv_fprs, cv_f1s = [], [], []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for train_idx, test_idx in skf.split(X, y):
        # type: ignore[union-attr]
        X_tr = [X[i] for i in train_idx]
        y_tr = [y[i] for i in train_idx]
        X_te = [X[i] for i in test_idx]
        y_te = [y[i] for i in test_idx]
        m = model.__class__(**model.get_params())
        m.fit(X_tr, y_tr)
        p = m.predict(X_te)
        tp_ = sum(1 for pp, tt in zip(p, y_te) if pp == 1 and tt == 1)
        fp_ = sum(1 for pp, tt in zip(p, y_te) if pp == 1 and tt == 0)
        fn_ = sum(1 for pp, tt in zip(p, y_te) if pp == 0 and tt == 1)
        tn_ = sum(1 for pp, tt in zip(p, y_te) if pp == 0 and tt == 0)
        det = tp_ / (tp_ + fn_) if (tp_ + fn_) else 0.0
        fpr_ = fp_ / (fp_ + tn_) if (fp_ + tn_) else 0.0
        prec = tp_ / (tp_ + fp_) if (tp_ + fp_) else 0.0
        f1_ = 2 * prec * det / (prec + det) if (prec + det) else 0.0
        cv_dets.append(det)
        cv_fprs.append(fpr_)
        cv_f1s.append(f1_)

    return {
        "in_sample": {
            "detection": detection,
            "fpr": fpr,
            "precision": precision,
            "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        },
        "cv5_held_out": {
            "detection_mean": mean(cv_dets),
            "detection_std": stdev(cv_dets) if len(cv_dets) > 1 else 0.0,
            "fpr_mean": mean(cv_fprs),
            "fpr_std": stdev(cv_fprs) if len(cv_fprs) > 1 else 0.0,
            "f1_mean": mean(cv_f1s),
            "f1_std": stdev(cv_f1s) if len(cv_f1s) > 1 else 0.0,
        },
    }


def _update_baselines_json(model_results: dict[str, dict]) -> None:
    if not BASELINES.exists():
        return
    data = json.loads(BASELINES.read_text())
    existing = {b["name"] for b in data.get("baselines", [])}
    for model_name, res in model_results.items():
        if model_name in existing:
            continue
        data["baselines"].append({
            "name": model_name,
            "method": res["method"],
            "params": res["params"],
            "pretrained": False,
            "ran_on": "2026-04-26",
            "runtime_env": "CPU-only, sklearn 1.8, n=175 stratified 5-fold CV",
            "version": "v1.0",
            "results": {
                "overall": {
                    "n": 175,
                    "detection_rate": round(res["cv5_held_out"]["detection_mean"], 4),
                    "detection_rate_std": round(res["cv5_held_out"]["detection_std"], 4),
                    "false_positive_rate": round(res["cv5_held_out"]["fpr_mean"], 4),
                    "false_positive_rate_std": round(res["cv5_held_out"]["fpr_std"], 4),
                    "f1": round(res["cv5_held_out"]["f1_mean"], 4),
                    "f1_std": round(res["cv5_held_out"]["f1_std"], 4),
                    "in_sample_detection": round(res["in_sample"]["detection"], 4),
                    "in_sample_fpr": round(res["in_sample"]["fpr"], 4),
                    "in_sample_f1": round(res["in_sample"]["f1"], 4),
                    "cv_protocol": "stratified 5-fold, random_state=42",
                },
            },
        })
    BASELINES.write_text(json.dumps(data, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--no-update-baselines", action="store_true",
                    help="Skip writing rows into data/.../baselines.json")
    args = ap.parse_args()

    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier

    bench = [json.loads(l) for l in BENCH.read_text().splitlines() if l.strip()]
    X = [_signal_features(s) for s in bench]
    y = [1 if s["ground_truth"]["is_scam"] else 0 for s in bench]
    feature_names = SIGNAL_NAMES + ["text_length_normalized", "otp_mention", "url_shortener", "rupee_symbol"]

    models = {
        "LogisticRegression": (
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42),
            "L2-regularised logistic regression on 11 boolean rule signals + 4 trivial text features",
            {"C": 1.0, "class_weight": "balanced", "max_iter": 2000, "random_state": 42},
        ),
        "GradientBoostingClassifier": (
            GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
            "Sklearn gradient-boosted decision tree ensemble on the same 15-feature set",
            {"n_estimators": 100, "max_depth": 3, "random_state": 42},
        ),
    }

    out: dict = {
        "_meta": {
            "n_total": len(bench),
            "n_scams": sum(y),
            "n_benign": len(y) - sum(y),
            "feature_set": feature_names,
            "feature_count": len(feature_names),
            "cv_protocol": "stratified 5-fold, random_state=42",
            "comparison_question": (
                "Audit Gap 9: how does feature-engineered traditional ML "
                "compare to the GRPO+LoRA Analyzer on the same 175-scenario "
                "bench? Same input signals as ScriptedAnalyzer."
            ),
            "honest_caveat": (
                "These models are trained on the same bench they are evaluated "
                "on (5-fold CV). They are an *upper bound* for what traditional "
                "ML with these features can achieve, not a held-out novel-scam "
                "claim. The v2 LoRA's 99.3 %/6.7 % point estimate is also "
                "evaluated on the same bench; this comparison is therefore "
                "fair (same data, different methods)."
            ),
        },
        "models": {},
    }
    for name, (model, method, params) in models.items():
        res = _eval_model(model, X, y)
        res["method"] = method
        res["params"] = params
        out["models"][name] = res
        cv = res["cv5_held_out"]
        ins = res["in_sample"]
        print(f"=== {name} ===")
        print(f"  in-sample:    det {ins['detection']*100:5.1f}% / FPR {ins['fpr']*100:5.1f}% / F1 {ins['f1']:.3f}")
        print(f"  cv-5 held-out: det {cv['detection_mean']*100:5.1f}±{cv['detection_std']*100:.1f}% "
              f"/ FPR {cv['fpr_mean']*100:5.1f}±{cv['fpr_std']*100:.1f}% "
              f"/ F1 {cv['f1_mean']:.3f}±{cv['f1_std']:.3f}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {args.output}")

    if not args.no_update_baselines:
        _update_baselines_json(out["models"])
        print(f"Updated {BASELINES} with 2 new baseline rows")

    print("\nReference (other rows on this bench):")
    print("  Scripted (rule-based)     det 84.0% / FPR  9.7% / F1 0.903 (current bench)")
    print("  Llama-3.3-70B-Instruct    det 99.3% / FPR  3.2% / F1 0.993")
    print("  Chakravyuh v2 LoRA (7B)   det 99.3% / FPR  6.7% / F1 0.990")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
