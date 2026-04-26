---
title: "Chakravyuh: A Multi-Agent OpenEnv for UPI Fraud, with a Measured Reward-Hacking Fix"
authors:
  - user: ujjwalpardeshi
tags:
  - openenv
  - grpo
  - trl
  - lora
  - multi-agent
  - fraud-detection
  - reward-hacking
  - safety
---

# Chakravyuh: A Multi-Agent OpenEnv for UPI Fraud, with a Measured Reward-Hacking Fix

This is our official written submission artifact for the Meta PyTorch OpenEnv Hackathon 2026.

- Live environment: [`ujjwalpardeshi/chakravyuh`](https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh)
- Defender adapter: [`ujjwalpardeshi/chakravyuh-analyzer-lora-v2`](https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2)
- Adversary adapter (gated): [`ujjwalpardeshi/chakravyuh-scammer-lora-phase1`](https://huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1)
- Benchmark dataset: [`ujjwalpardeshi/chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0)
- Source code: <https://github.com/UjjwalPardeshi/Chakravyuh>

## TL;DR

We trained an LLM for Indian UPI fraud detection and initially got **100% detection**.
Then we found the failure: **36% false-positive rate**. The model was over-flagging.

We treated that as a reward-hacking incident, changed the reward profile, retrained, and shipped v2:

- Detection: **99.3%**
- False positive rate: **6.7%** (about **5x lower** than v1)
- F1: **0.99**
- Bench size: **n = 174**

The core artifact is not "one big number"; it is a measured v1 -> v2 diagnosis and fix.

---

## Why This Problem

India loses ₹13,000+ crore/year to UPI fraud and 60 crore users are exposed.
Rule-based systems degrade on novel attacks; in our bench, the scripted baseline catches **76.5 % (26/34)** of the post-2024 novel split — the v2 LoRA closes that to **97.1 %**, a 20.6 pp lift on exactly the high-loss patterns (matrimonial crypto, deepfake CEO, digital arrest) where keyword rules are weakest.

Chakravyuh is built as a research environment for this gap: trainable, reproducible, and adversarial by design.

---

## Environment Design (Theme #1: Multi-Agent)

Chakravyuh has 5 agents with asymmetric information:

- Scammer
- Victim
- Analyzer (trained oversight LLM)
- Bank Monitor (metadata-only oversight)
- Regulator (aggregate-feedback meta-agent)

The Analyzer sees chat content. The Bank Monitor sees transaction metadata. These channels are intentionally separated, so one weak signal cannot dominate the final decision pathway.

The trained Analyzer reward is composable (`AnalyzerRubricV2`) with eight child rubrics, including detection, false positives, calibration, explanation quality, and strict output formatting.

---

## Training Pipeline (OpenEnv + TRL/GRPO)

We use OpenEnv for environment interaction and TRL GRPO for post-training:

- Base model: Qwen2.5-7B-Instruct
- Method: LoRA + GRPO
- Output target: calibrated scam probability + grounded explanation
- Training notebooks are included and linked from README:
  - `training/train_colab.ipynb`
  - `notebooks/v2_retrain_safe.ipynb`

This satisfies the "working training script with evidence of real training" requirement in the submission guidelines.

---

## Reward-Hacking Incident and Fix (Main Contribution)

### What failed in v1

- Detection: 100%
- FPR: 36%

That pattern strongly indicates reward hacking: the model learns to over-flag to maximize reward components tied to scam detection.

### What we changed in v2

1. Increased false-positive penalty (**-0.3 -> -0.8**)
2. Removed format-reward payout when benign content is wrongly flagged
3. Increased benign calibration weight (**0.3 -> 0.5**)
4. Tightened KL anchor (**0.08 -> 0.15**)

### Result

| Metric | v1 | v2 |
|---|---:|---:|
| Detection | 100.0% | **99.3%** |
| False Positive Rate | 36.0% | **6.7%** |
| F1 | 0.96 | **0.99** |

The asymmetric shift (recall stable, FPR sharply down) is the key evidence that v2 learned better behavior instead of exploiting reward shortcuts.

---

## Evidence of Improvement (Judging 20%)

We publish:

- Eval artifacts (`logs/eval_v2.json`)
- Bootstrap confidence intervals (`logs/bootstrap_v2.json`)
- Training traces (`logs/v2_trainer_state.json`)
- Public benchmark dataset on HF (`chakravyuh-bench-v0`)

Plus four CPU-runnable diagnostics that go past the headline F1:

**Training curves** — reward + loss + KL + grad-norm over 615 GRPO steps, rendered from the trainer state.

![v2 GRPO training curves](https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/main/plots/chakravyuh_plots/training_curves_v2.png)

**Calibration** — SFT baseline ECE = 0.039 across n=175. The model is not just accurate, its confidence is meaningful.

![SFT calibration reliability diagram](https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/main/plots/chakravyuh_plots/ece_reliability.png)

**Per-rubric ablation** — zero each child rubric in turn. Detection (-0.61) and calibration (-0.13) carry the eval-time signal. False-positive rubric does not show up in average reward but does show up in the FPR — which is the whole point of v1 → v2.

![Per-rubric ablation](https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/main/plots/chakravyuh_plots/ablation_per_rubric.png)

**Leakage-clean slice** — re-evaluate every provider on the n=50 subset where nearest training text has cosine < 0.7. Scripted holds within 2.4 pp. Frontier LLMs do not improve on the clean slice — their failure is structural (no Indian-fraud priors), not memorisation.

![Leakage-clean slice](https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/main/plots/chakravyuh_plots/leakage_clean_slice.png)

**SFT vs v2-GRPO fingerprint** — same base, same LoRA, same corpus; only the algorithm differs. GRPO buys +5.6 pp on hard at the cost of +3.4 pp FPR — a real trade-off, not noise.

![SFT vs v2 GRPO fingerprint](https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/main/plots/chakravyuh_plots/v1_vs_v2_fingerprint.png)

This keeps claims auditable and rerunnable.

---

## Adversarial Co-Evolution Signal

We also trained a Scammer adapter (`Qwen2.5-0.5B + LoRA + GRPO`) to pressure-test defenses:

- Best-of-8 bypass vs scripted rule baseline: **93.75%** (n=64)
- Same outputs bypass vs v2 Analyzer LoRA: **32.8%**
- Gap: about **60 percentage points**

This gives concrete multi-agent evidence that the trained Analyzer materially outperforms scripted detection under adaptive attack pressure.

---

## Honest Limitations

We explicitly disclose where this version is not complete:

- Single-seed training (multi-seed pending)
- Small benign sample for FPR calibration uncertainty
- Semantic leakage risks are documented and measured
- Phase-2 LoRA-vs-LoRA co-evolution retraining is compute-gated
- Per-row v2 LoRA scores (for v2 ECE + per-language calibration) need GPU re-inference (B.12); the SFT-baseline ECE is shipped as-is

All are documented in `docs/limitations.md` and planned as next milestones.

---

## Submission Checklist Mapping

How this project aligns with official guidance:

- **OpenEnv usage:** Yes (`openenv-core`, environment API, Space deployment)
- **Working training script (TRL/Unsloth style requirement):** Yes (TRL GRPO notebooks included)
- **Evidence of real training:** Yes (curves, trainer state, eval artifacts)
- **Short writeup:** Yes (this blog)
- **HF Space deployment:** Yes (official submission URL above)
- **README with links to materials:** Yes (models, dataset, notebooks, docs)

---

## Reproduce Quickly

```bash
git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
pip install -e '.[llm,eval]'
make smoke-test
pytest tests/ --tb=no -q
make reproduce
```

Full walkthrough: [`REPRODUCE.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/REPRODUCE.md)

---

## Final Note

Chakravyuh is a practical template for reward-engineered oversight training in adversarial settings: detect failure early, quantify it, fix the reward, and publish enough artifacts for others to verify or challenge the result.

If you are evaluating this submission, start with the live Space, then inspect `README.md`, `logs/eval_v2.json`, and `logs/bootstrap_v2.json`.
