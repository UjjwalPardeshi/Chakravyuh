# v2 Error Analysis

Honest accounting of where the analyzers fail. Two layers: **scripted baseline** has full per-scenario detail; **v2 LoRA** is aggregated (per-scenario audit requires GPU re-inference, v3 work).

## Scripted baseline (per-scenario, n=135)

Source: [`logs/mode_c_scripted_n135.json`](../logs/mode_c_scripted_n135.json)

### Per-category breakdown

| Category | n | Accuracy | False Positives | False Negatives (missed scams) |
|---|---|---|---|---|
| `benign` | 15 | 0.733 | 4 | 0 |
| `borderline` | 5 | 0.600 | 2 | 0 |
| `impersonation` | 30 | 0.767 | 0 | 7 |
| `investment_fraud` | 26 | 0.346 | 0 | 17 |
| `kyc_fraud` | 22 | 0.955 | 0 | 1 |
| `loan_app_fraud` | 18 | 0.667 | 0 | 6 |
| `otp_theft` | 19 | 0.947 | 0 | 1 |
| **Total** | **135** | — | **6** | **32** |

### False-positive scenarios (scripted-baseline)

| Category | Scenario | Score | Difficulty |
|---|---|---|---|
| `benign` | `modec_089` | 1.000 | hard |
| `benign` | `modec_091` | 0.500 | medium |
| `benign` | `modec_092` | 0.500 | hard |
| `benign` | `modec_098` | 1.000 | hard |
| `borderline` | `modec_102` | 1.000 | hard |
| `borderline` | `modec_104` | 0.720 | hard |

### Missed-scam scenarios (scripted-baseline false negatives)

| Category | Scenario | Score | Difficulty |
|---|---|---|---|
| `impersonation` | `modec_074` | 0.470 | medium |
| `impersonation` | `modec_079` | 0.270 | hard |
| `impersonation` | `modec_084` | 0.270 | medium |
| `impersonation` | `modec_116` | 0.050 | novel |
| `impersonation` | `modec_119` | 0.050 | novel |
| `impersonation` | `modec_130` | 0.300 | novel |
| `impersonation` | `modec_134` | 0.270 | novel |
| `investment_fraud` | `modec_051` | 0.250 | easy |
| `investment_fraud` | `modec_055` | 0.250 | medium |
| `investment_fraud` | `modec_059` | 0.250 | medium |
| `investment_fraud` | `modec_060` | 0.050 | medium |
| `investment_fraud` | `modec_061` | 0.250 | hard |
| `investment_fraud` | `modec_063` | 0.250 | easy |
| `investment_fraud` | `modec_064` | 0.270 | medium |
| `investment_fraud` | `modec_065` | 0.050 | hard |
| `investment_fraud` | `modec_107` | 0.050 | novel |
| `investment_fraud` | `modec_109` | 0.050 | novel |
| `investment_fraud` | `modec_110` | 0.300 | novel |
| `investment_fraud` | `modec_113` | 0.050 | novel |
| `investment_fraud` | `modec_122` | 0.050 | novel |
| `investment_fraud` | `modec_125` | 0.470 | novel |
| `investment_fraud` | `modec_126` | 0.470 | novel |
| `investment_fraud` | `modec_128` | 0.300 | novel |
| `investment_fraud` | `modec_133` | 0.050 | novel |
| `kyc_fraud` | `modec_034` | 0.300 | medium |
| `loan_app_fraud` | `modec_035` | 0.470 | easy |
| `loan_app_fraud` | `modec_041` | 0.270 | medium |
| `loan_app_fraud` | `modec_042` | 0.250 | medium |
| `loan_app_fraud` | `modec_044` | 0.050 | hard |
| `loan_app_fraud` | `modec_049` | 0.250 | medium |
| `loan_app_fraud` | `modec_129` | 0.250 | novel |
| `otp_theft` | `modec_108` | 0.430 | novel |

## v2 LoRA (aggregate, n=174)

Source: [`logs/eval_v2.json`](../logs/eval_v2.json)

- Detection rate: **0.9931** (143/144 scams caught)
- False positive rate: **0.0667** (2/30 benign mislabelled)
- F1: **0.9896**
- Threshold: `0.55`

### Per-difficulty breakdown

| Difficulty | n | Detection | Missed scams |
|---|---|---|---|
| `easy` | 26 | 1.000 | 0 |
| `hard` | 18 | 1.000 | 0 |
| `medium` | 66 | 1.000 | 0 |
| `novel` | 34 | 0.971 | 1 |

### Why this is aggregate-only

The v2 evaluation logged aggregate detection/FPR/F1 + per-difficulty buckets, but not per-scenario predictions. To audit *which* 2 benign(s) the v2 model misclassified, or *which* 1 novel scam(s) it missed, requires re-running inference with the LoRA adapter on every bench scenario and dumping per-row scores. That is a single-GPU, ~30-minute job — tracked as v3 work in [`docs/limitations.md`](limitations.md).

## Comparison summary

| Metric | Scripted (per-scenario) | v2 LoRA (aggregate) |
|---|---|---|
| Accuracy / detection | 0.719 (n=135) | 0.993 det · 0.067 FPR (n=174) |
| Total errors | 38 | 3 |

## v3 plan

1. Re-run v2 inference on the bench with per-scenario logging (~30 min on 1× A100).
2. Manually label each FP / FN root cause: scammer-template overlap, urgency-only signal, multi-language drift, etc.
3. Add fix-targeted templates to `chakravyuh_env/benign_augmented_v2.json` to push n_benign past 150.
4. Retrain v2.1 on the expanded corpus, re-eval, repeat audit.

