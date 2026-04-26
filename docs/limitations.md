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
| **Semantic leakage audit (training corpus ↔ bench-v0)** | [`logs/semantic_leakage_audit.json`](../logs/semantic_leakage_audit.json) + [`plots/chakravyuh_plots/semantic_leakage_histogram.png`](../plots/chakravyuh_plots/semantic_leakage_histogram.png) | ✅ shipped |

---

## ⚠️ Semantic leakage between training and bench (critical disclosure)

**Method.** MiniLM-L6 cosine similarity between every bench scenario and its nearest neighbor in the 1,177-record training corpus (canonical + augmented + paraphrase + regional + multi-turn + scam_novel + benign templates). Reproducible with [`eval/semantic_leakage_audit.py`](../eval/semantic_leakage_audit.py).

**Findings (n = 174 bench scenarios):**

| Statistic | Value |
|---|---|
| Mean cosine similarity to nearest training text | **0.80** |
| Median cosine similarity | 0.82 |
| % bench items with cosine > 0.95 (near-duplicates after substring filter) | **18.4 %** |
| % bench items with cosine > 0.85 (highly similar) | **44.8 %** |
| % bench items with cosine > 0.70 (recognisably similar) | **71.3 %** |
| % bench items with cosine < 0.50 (genuinely OOD) | 1.7 % |

**Interpretation.** Our existing `_filter_soft_leakage` removes substring duplicates only. It does NOT remove paraphrases, translations, or semantically-equivalent variants. The bench-v0 was authored from the same template families as the training corpus, so the LoRA has effectively seen paraphrased versions of most bench scenarios. **The 100 % detection on easy / medium / hard difficulty buckets is partially memorization-driven.**

**The honest claim.**

1. The **leakage-clean subset** of bench (cosine < 0.70): 38 scams + 12 benigns = 50 scenarios. Re-evaluating v2 specifically on this subset is v3 work (requires GPU re-inference; flagged below).
2. The **novel post-2024 split** (n = 34): mean cosine to training = 0.79, the same as overall. v2 detects 33/34 = **97.1 %** here. This is in-distribution per the leakage audit, so even the novel-split number is partly memorization. Real OOD performance is likely lower.
3. The **scripted baseline gap** (80 % known → 50 % novel) demonstrates pre-training distribution-shift. v2's lift is real but smaller than the headline implies.

**What this does NOT invalidate.**

- The **v1 → v2 fix narrative** (FPR 36 % → 6.7 %, 5×) — both v1 and v2 evaluated on the same bench, so the relative improvement is unaffected by leakage. This is a valid demonstration of principled reward-engineering.
- The **scripted baseline collapse on novel** (50 %) — measures rule fragility against new attack vectors, independent of LoRA training distribution.
- The **environment design** itself (5-agent, composable rubric, two-tier oversight). Leakage is a bench-construction issue, not an environment issue.

**v3 plan to fix.**

1. Build a **held-out template-family split**: select template *families* (e.g., entire OTP-theft-v3 family) and exclude all variants from training, evaluate only on those families.
2. **External held-out benchmark**: source 50 real WhatsApp / SMS scam screenshots from public reports, hand-label, evaluate v2 with no chance of overlap.
3. **Multi-seed retrain** on the cleaner split to bound the seed variance.
4. **Per-scenario v2 logits** logged during eval, sliced by leakage-clean subset for honest reporting.

**One-line answer for Q&A.** *"Yes, we audited semantic leakage with MiniLM-L6 cosine similarity. 44.8 % of bench has cosine > 0.85 to training. The 100 % on easy/medium/hard is partly memorization; the v1→v2 FPR fix and the scripted-baseline novel collapse are unaffected. v3 builds a held-out template-family split."*

---

## What is **not** measured (do not cite as a number)

| Claim | Why deferred | Tracked as |
|---|---|---|
| Frontier comparison — proprietary tier (GPT-4o / Claude / Gemini) | Needs ~$40–80 in API budget; not covered by HF compute credits; pending user authorization | v3 — `eval/frontier_baseline.py` (script supports it; just needs the keys) |
| ~~Frontier comparison — open-weight tier (Llama-3.3-70B / Qwen2.5-72B / DeepSeek-V3)~~ | **✅ SHIPPED 2026-04-26** — paid from HF compute credits via HuggingFace Inference Providers; v2 LoRA ties Llama-3.3-70B at 10× fewer params, beats Qwen2.5-72B + DeepSeek-V3 on F1; DeepSeek-V3 (671B) reproduces v1 reward-hacking signature externally | [`logs/frontier_comparison.csv`](../logs/frontier_comparison.csv) |
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

## Threshold sweep degeneracy

The v2 LoRA produces near-binary scores: 9 of 13 thresholds in the 0.30–0.85 sweep yield identical detection / FPR. The composable [`CalibrationRubric`](../chakravyuh_env/rubrics.py) exists in the env but cannot reward fine-grained calibration on a near-binary distribution. The v2 detection / FPR point estimate is correct; the calibration *channel* of the rubric is partially inert on this output distribution. **v3 work:** temperature-scaled logits + reliability diagrams.

## Bench eval n = 174 (one benign less than 175)

The bench file [`data/chakravyuh-bench-v0/scenarios.jsonl`](../data/chakravyuh-bench-v0/scenarios.jsonl) has 175 scenarios (144 scams + 31 benign). The v2 LoRA inference batch (Apr 21) excluded one benign that produced a malformed model output, so [`logs/eval_v2.json`](../logs/eval_v2.json) reports n = 174 (n_benign = 30). The asymmetric-improvement direction (FPR 36% → 6.7%) is unaffected by the one-row delta. The bench file is the single source of truth; the eval n discrepancy is a one-time inference artifact, not a bench claim.

## v2 GRPO training trajectory has high KL throughout

KL divergence reached 0.36 by step 15 and stayed in the [0.25, 0.45] band for the remaining ~600 steps; PPO clip ratios remained at 0 throughout. See [`docs/training_diagnostics.md`](training_diagnostics.md) for the full trajectory, three honest readings, and the v3 KL-early-stop guard.

## How to verify

```bash
make reproduce        # eval-v2 + bootstrap, ~10 min CPU cached
pytest tests/ -v      # 237 collected · 235 pass · 2 skipped
make smoke-test       # in-process env contract
make link-check       # README references resolve
```

If any number in the README is more than 0.5 pp off `make reproduce`, that's the bug — please file an issue.
