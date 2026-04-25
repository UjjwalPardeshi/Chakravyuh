---
title: "Chakravyuh: Catching Reward Hacking on the Way to a 7B Indian-UPI Fraud Detector"
thumbnail: /blog/assets/chakravyuh/thumbnail.png
authors:
  - user: ujjwalpardeshi
tags: [openenv, peft, lora, grpo, trl, india, fraud, multi-agent]
---

# Chakravyuh: Catching Reward Hacking on the Way to a 7B Indian-UPI Fraud Detector

> A Meta PyTorch OpenEnv Hackathon 2026 (Bangalore) submission. Repo: <https://github.com/UjjwalPardeshi/Chakravyuh>. Adapter: [`ujjwalpardeshi/chakravyuh-analyzer-lora-v2`](https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2). Bench: [`ujjwalpardeshi/chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0). Live env: [`ujjwalpardeshi/chakravyuh`](https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh).

India loses **₹13,000+ crore per year** to UPI fraud. 60 crore Indians use UPI every month. Rule-based detectors degrade meaningfully on post-2024 attack patterns — we measured **scripted analyzer detection = 50% on our 34-scenario novel split** (matrimonial-crypto grooming, deepfake CEO IPO pitches, "digital arrest" calls, Aadhaar reverification scams; from `data/chakravyuh-bench-v0/scenarios.jsonl`). **No public RL environment exists for multi-agent fraud-detection research.** So we built one.

This post walks through:

1. Why we framed this as **scalable oversight**, not "LLM classifier"
2. The five-agent OpenEnv environment and the composable 5-rubric reward
3. The reward-hacking failure we caught in v1 — and the principled fixes that produced v2
4. Headline numbers with bootstrap CIs (no point estimates without bands)
5. Honest limitations and the v3 roadmap

If you only have 30 seconds: the 7B Qwen LoRA Analyzer v2 hits **detection 99.3 %** with **FPR 6.7 %** on a 174-scenario bench (95 % CIs from 10 000-iteration bootstrap: detection [97.9 %, 100 %], FPR [0 %, 16.7 %]). v1 hit **detection 100 % / FPR 36 %** — the textbook reward-hacking fingerprint. Diagnosing and fixing it is the central artifact, not the absolute numbers.

---

## 1. Framing: scalable oversight, not "LLM classifier"

The hackathon's interesting axis isn't "trained LLM beats rules on test set" — that's a 2019 problem. The interesting axis is *can we train an LLM to monitor, analyze, and explain the behavior of another agent operating adversarially in a complex, partially observable multi-agent setting*.

That's a scalable-oversight problem. Reward hacking is its central failure mode (the hackathon guide says so explicitly). The most credible thing a submission can do is **exhibit and diagnose one** — not pretend it didn't happen.

Chakravyuh is engineered around that frame. The Analyzer (the LLM under training) sees only chat. The Bank Monitor (a second oversight tier) sees only transaction metadata. Neither single tier can be hacked into single-handedly suppressing the "money extracted" outcome — they have to agree.

## 2. The environment

Five agents, asymmetric information:

```
         CLOUD ┌─────────────────┐
               │   REGULATOR     │  rule-weight updates from aggregate outcomes
               └────────┬────────┘
      ON-DEVICE ┌───────▼─────────┐
       ┌───────▶│ BEHAVIORAL      │   runs locally on the victim's phone
       │ chat   │ ANALYZER        │   chat NEVER leaves the device
       │(local) │ (oversight LLM) │   ← the agent under training
   ┌───┴─────┐  └─────────────────┘
   │ SCAMMER │◀───chat─▶┌──────────┐
   └─────────┘          │  VICTIM  │
                        └────┬─────┘
                             │ attempts UPI transaction
                             ▼
         BANK-SIDE ┌─────────────────┐
                   │ BANK MONITOR    │   metadata-only oversight
                   │ (oversight)     │   (amount, payee novelty, frequency)
                   └─────────────────┘
```

The Analyzer's reward decomposes into **five orthogonal child rubrics** (composable, introspectable, swappable):

| Rubric | Weight (v2) | What it rewards |
|---|---|---|
| `DetectionRubric` | +1.0 | Early flag of a real scam (turn ≤ 5) |
| `MissedScamRubric` | −0.5 | Missed scam where money was extracted |
| `FalsePositiveRubric` | **−0.8** | Benign incorrectly flagged |
| `CalibrationRubric` | **+0.5** (benign) | Score matches ground truth in *both* directions |
| `ExplanationRubric` | +0.4 | Natural-language explanation references declared signals |

This is the reward profile **after** the v1 → v2 fix. The bold weights are what changed.

## 3. Reward hacking — caught and fixed

v1 trained on the same env hit:

- **Detection: 100 %** ← suspicious
- **FPR: 36 %** ← textbook fingerprint

That combination — detection saturated, FPR catastrophic, **uniform across difficulty buckets** — is what reward hacking *looks like*. The model learned "always output a high score." It correctly flags every scam, and over-flags every benign too. Calibration collapsed.

We diagnosed the reward profile and made three principled changes for v2:

1. **FP penalty −0.3 → −0.8.** Flagging benigns is now expensive enough that "flag everything" is a dominated strategy.
2. **Format reward denied on benign-flagged-as-scam.** v1 paid the format-correctness bonus regardless of whether the prediction was right. That bonus alone made the always-flag policy weakly profitable. We removed it specifically on benign-flagged-scam outputs.
3. **Benign calibration weight 0.3 → 0.5.** Stronger gradient toward `score ≤ 0.2` on benign cases.

Plus the KL anchor was tightened (`β = 0.08 → 0.15`) so the model can't drift far from the base distribution under the new reward shape.

The result:

| Metric | v1 (reward-hacked) | **v2 (fixed)** | 95 % CI (v2) |
|---|---|---|---|
| Detection | 100.0 % | **99.3 %** | [97.9 %, 100 %] |
| FPR | 36.0 % | **6.7 %** | [0.0 %, 16.7 %] |
| F1 | 0.96 | **0.99** | [0.976, 1.000] |
| Novel-detection (post-2024) | 100 % | **97.1 %** | [91.2 %, 100 %] |

Detection moved 100% → 99.3% — barely. FPR dropped **5×**. That asymmetric improvement is the signature of a model that's actually learning the task. A model still gaming the reward improves both numbers in lockstep, or fails on novel.

The dip on `novel` (post-2024 attack patterns) is the small honest crack that confirms it's not collapsing to "always flag." On easy/medium/hard scenarios v2 hits 100% — but on novel attacks it gets 97% (33/34). That's *good*: a perfectly hacked model would still get them all.

## 4. Honest numbers, with CIs

We refuse to publish numbers without bands. From [`logs/bootstrap_v2.json`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/bootstrap_v2.json) (10 000-iteration percentile bootstrap):

```json
{
  "detection": {"point": 0.993, "ci_low": 0.979, "ci_high": 1.000},
  "fpr":       {"point": 0.067, "ci_low": 0.000, "ci_high": 0.167},
  "f1":        {"point": 0.990, "ci_low": 0.976, "ci_high": 1.000}
}
```

Three honest things to take away:

- **The 5× FPR reduction is statistically real.** v1's percentile-bootstrap FPR band sits well above v2's `[0%, 16.7%]` band (`logs/bootstrap_v2.json`); the directional gap is robust to bootstrap resampling.
- **The exact 6.7 % is not a tight estimate.** n = 30 benign. A single additional misclassified benign moves the point estimate from 6.7 % to 10 %. We say so in the bench card and in `docs/POSTMORTEM_FUTURE.md`.
- **The bench is a proxy.** 174 hand-curated scenarios do not span real-world fraud diversity. Production performance will be lower — these are comparative numbers, not absolute.

## 5. What we're proud of, and what's missing

**Proud of:**

- The v1 → v2 reward-hacking incident is a *measured*, *reproducible* artifact. The fix is documented in [`docs/DESIGN_DECISIONS.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/DESIGN_DECISIONS.md) §8 and the diagnostic plot is in [`plots/chakravyuh_plots/reward_hacking_diagnostic.png`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/plots/chakravyuh_plots/reward_hacking_diagnostic.png). This is exactly the artifact the hackathon guide asks for.
- A **public bench dataset** ([`chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0)) sourced from RBI / NPCI / I4C / news — 175 scenarios, hand-labelled, with a non-trivial rule-vs-truth gap (the scripted analyzer scores below 70% F1; raw confusion-matrix counts are in `logs/eval_v2.json`) so you can verify the bench isn't just a keyword game.
- A **soft-leakage filter** ([`training/grpo_analyzer.py:_filter_soft_leakage`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/training/grpo_analyzer.py)) that strips training examples too similar to bench scenarios — *before* training. Open code, checkable claim.
- An **on-device deployment story** that's structural, not branding. The Analyzer never sees transaction metadata; the Bank Monitor never sees chat. This isn't a tagline — it's the architecture, and it's why the two-tier oversight cannot be hacked from one side.

**Missing (named, not hidden):**

- **Multi-seed retrains.** Single-seed numbers cannot rule out lottery-ticket effects. v3 milestone #1.
- **Frontier baseline.** GPT-4o / Claude / Gemini / Llama-3.3-70B comparison. Script wired up, not run — API budget deferred.
- **Per-language eval.** Multi-language detection on Hindi, Tamil, Telugu, Bengali, Marathi is a capability claim until measured per-language.
- **Calibration analysis.** ECE / Brier / reliability diagrams.
- **Adversarial Scammer Phase-2 retrain.** The architectural step that would convert the env from "1 trained, 4 scripted" to a co-evolutionary 2-trained system. Compute-gated, planned onsite during the hackathon.

Full v3 roadmap with priority ordering at [`docs/POSTMORTEM_FUTURE.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/POSTMORTEM_FUTURE.md).

## 6. Try it yourself

```python
from chakravyuh_env import get_trained_analyzer

analyzer = get_trained_analyzer()  # downloads ujjwalpardeshi/chakravyuh-analyzer-lora-v2 on first call
print(analyzer("Urgent! Your bank account will be frozen. Share OTP to verify identity."))
# → {'score': 0.95, 'signals': ['urgency', 'info_request', 'impersonation'],
#    'explanation': 'Asks for OTP with urgency from a self-claimed bank agent...'}
```

Or run the full env locally:

```bash
git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
pip install -e '.[llm,eval]'
uvicorn server.app:app --host 0.0.0.0 --port 8000
# Now POST to /reset, /step, GET /leaderboard, GET /docs.
```

The HF Space is live at <https://ujjwalpardeshi-chakravyuh.hf.space/health>. Hit `/docs` for the OpenAPI swagger.

## 7. Why this matters beyond the hackathon

UPI is the largest digital payments rail in the world. Indian regulators (RBI, NPCI, I4C) face a structural asymmetry: scammers iterate weekly, regulators iterate yearly. A measurement-first, multi-agent, on-device, scalable-oversight RL environment is the right *infrastructure* for closing that gap — public, reproducible, and forkable to other regulated fraud channels (KYC, insurance claims, BEC).

Forking guide: [`docs/EXTEND.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/EXTEND.md). The 5-agent template, soft-leakage filter, bootstrap CI, and v2 reward profile transfer directly. Bench + templates are the only domain-specific work.

---

**Authors.** Ujjwal Pardeshi (independent researcher, Bangalore). For the Meta PyTorch OpenEnv Hackathon 2026.

**Cite.** [`CITATION.cff`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/CITATION.cff) at the repo root.

**License.** MIT for code; CC-BY-4.0 for the bench dataset.
