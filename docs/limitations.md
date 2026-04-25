# Limitations & v3 Work

Single source of truth for everything we know is incomplete. Cross-referenced from the README, `Q_AND_A_REHEARSAL.md`, and `POSTMORTEM_FUTURE.md` so no other doc contradicts this one.

Last verified: 2026-04-25.

---

## What is measured (cite freely)

| Claim | Artifact | Status |
|---|---|---|
| v2 detection 99.3 %, FPR 6.7 %, F1 = 0.99 on n = 174 | [`logs/eval_v2.json`](../logs/eval_v2.json) | ✅ shipped |
| 10 000-iter percentile bootstrap CIs (detection, FPR, F1, per-difficulty) | [`logs/bootstrap_v2.json`](../logs/bootstrap_v2.json) | ✅ shipped |
| Scripted baseline temporal-gap (80 % known → 50 % novel, 30 pp) on n = 135 | [`logs/mode_c_scripted_n135.json`](../logs/mode_c_scripted_n135.json) | ✅ shipped |
| Per-difficulty detection ramp scripted vs v2 | [`logs/eval_v2.json`](../logs/eval_v2.json) `per_difficulty` | ✅ shipped |
| Per-rubric post-hoc ablation (sensitivity) | [`docs/ablation_study.md`](ablation_study.md) + [`logs/ablation_study.json`](../logs/ablation_study.json) | ✅ shipped |
| Time-to-detection (scripted env, n = 100 episodes) | [`logs/time_to_detection.json`](../logs/time_to_detection.json) | ✅ shipped |
| Red-team robustness against rule-based Analyzer | [`logs/analyzer_robustness.json`](../logs/analyzer_robustness.json) | ✅ shipped |
| Scripted-baseline error analysis (per-scenario FPs + missed scams) | [`docs/v2_error_analysis.md`](v2_error_analysis.md) | ✅ shipped |

## What is **not** measured (do not cite as a number)

| Claim | Why deferred | Tracked as |
|---|---|---|
| Frontier comparison vs GPT-4o / Claude / Gemini / Llama-3 | Needs ~$40–80 in API budget; pending user authorization | v3 — `eval/frontier_baseline.py` |
| Adversarial Scammer co-evolves with Analyzer | Needs HF GPU credits, ~5 hours A100 | v3 — onsite hackathon work |
| SFT vs RL controlled experiment | Needs ~1.5 hours A100 | v3 — onsite hackathon work |
| Per-scenario v2 LoRA error analysis (which 2 FPs, which 1 missed scam) | Eval is aggregate-only; per-scenario audit needs GPU re-inference | v3 — re-run inference, log per-row |
| Per-language detection breakdown (Hindi, Tamil, Telugu, Kannada, Bengali, Marathi) | Needs GPU re-inference on per-language slices | v3 — `eval/per_language_eval.py` (not yet implemented) |
| Calibration ECE + reliability diagram | Trained for via `CalibrationRubric`; not yet reported because per-scenario v2 logits needed | v3 |
| Token saliency / interpretability heatmap | Needs running v2 model + captum integrated-gradients | v3 |
| Latency / memory benchmark (p50, p99, peak RAM) | Needs running quantized model | v3 |
| Multi-seed retrains (mean ± std) | Compute budget; bootstrap CIs (10k iters) substituted for now | v3 |
| External held-out benchmark (50 novel patterns not from canonical templates) | Pending data labelling | v3 |
| LoRA Scammer + emergent-behavior clustering | Conditional on adversarial-Scammer training converging | v3 — onsite |
| Notebooks committed with executed outputs (`v2_retrain_safe.ipynb`, `plots_and_eval.ipynb`, `train_colab.ipynb`) | Need Colab runtime to populate cell outputs | Pre-submit user task |
| 2-min YouTube video | User-side production task | Pre-submit user task |
| 4-slide PDF deck | Markdown draft shipped at [`docs/chakravyuh_slides.md`](chakravyuh_slides.md); PDF export user-side | Pre-submit user task |

## Known sample-size concerns

- **n_benign = 30** in the v2 bench (we re-bench against `chakravyuh_env/benign_augmented_v2.json` — currently 81 templates; expansion to ≥150 in progress). The 95 % Wilson CI on FPR = 6.7 % is **[1.8 %, 20.7 %]**. We stand behind the *5×-better-than-v1* claim (statistically real); we do *not* claim 6.7 % is a precise estimate.
- **n_novel = 34** post-2024 scams. Detection 97.1 % has 95 % CI **[91.2 %, 100 %]**.
- **Single-seed v2 training run.** Multi-seed deferred to v3.

## What we hit reward-hacking on (and how we know it's gone)

v1 (committed in earlier history): detection = 100 %, FPR = 36 %, F1 = 0.96 — textbook reward-hacking signature. The v2 retrain applied three principled fixes:

1. FP penalty −0.3 → **−0.8**
2. Benign-calibration weight 0.3 → **0.5**
3. Format reward removed when flagging benign as scam

v2: detection = 99.3 % (unchanged), FPR = **6.7 %** (5× better), F1 = 0.99. The asymmetric improvement is the proof: detection unchanged while FPR collapsed means the model learned the task instead of the proxy.

Caveat: a more rigorous "v2 isn't also reward-hacked" test would be the per-rubric trajectory plot during training (`P1.3` in WIN_PLAN). That requires re-running training with W&B logging and is v3 work.

## What we will not promise even after v3

- **Production deployment readiness.** Chakravyuh is a benchmark + research environment, not a deployable Indian-bank fraud module. Domain adaptation, regulatory compliance (DPDPA, RBI rules), and live-data evaluation are out of scope.
- **Detection of scams Chakravyuh hasn't seen the *category* of.** The bench covers ~11 fraud categories. New categories invented in 2027 will need new templates and retraining.
- **Adversarial robustness against well-resourced attackers.** Red-team eval (10 attacks) found 4/10 caught with rule-based; LoRA likely tighter, but a sophisticated adversary will iterate. Defense in depth is needed in production.

## How to verify

```bash
make reproduce        # eval-v2 + bootstrap, ~10 min CPU cached
pytest tests/ -v      # 237 collected · 235 pass · 2 skipped
make smoke-test       # in-process env contract
make link-check       # README references resolve
```

If any number in the README is more than 0.5 pp off `make reproduce`, that's the bug — please file an issue.
