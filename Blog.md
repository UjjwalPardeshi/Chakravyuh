---
title: "Chakravyuh — Catching Reward Hacking on the Way to a 7B Indian-UPI Fraud Detector"
authors:
  - user: ujjwalpardeshi
tags:
  - openenv
  - peft
  - lora
  - grpo
  - trl
  - india
  - fraud
  - multi-agent
  - reward-hacking
  - safety
---

# Chakravyuh — Catching Reward Hacking on the Way to a 7B Indian-UPI Fraud Detector

> **Submission writeup for the Meta PyTorch OpenEnv Hackathon 2026 (Bangalore).**
> This file lives inside the HF Space so judges can read it next to the
> running environment. The repository README is the technical deep-dive;
> this `Blog.md` is the 5-minute story.
>
> - **Live env:** [`ujjwalpardeshi/chakravyuh`](https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh) — `/demo/`
> - **Adapter (defender):** [`ujjwalpardeshi/chakravyuh-analyzer-lora-v2`](https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2)
> - **Adapter (adversary, gated):** [`ujjwalpardeshi/chakravyuh-scammer-lora-phase1`](https://huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1)
> - **Bench dataset:** [`ujjwalpardeshi/chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0)
> - **Source code:** <https://github.com/UjjwalPardeshi/Chakravyuh>
> - **Theme:** #1 Multi-Agent Interactions *(primary)* · #4 Self-Improvement *(honest demote — see "Theme coverage" below)*

## TL;DR

We trained an LLM to detect Indian UPI fraud and got **100 % detection.**
We celebrated for four minutes. Then we noticed: **36 % false-positive
rate.** The model wasn't catching scams — it was flagging everything.

This post walks through the diagnosis, the three-line reward fix, and
the v2 recovery: detection holds at **99.3 %**, FPR collapses 5× to
**6.7 %** on n = 174 real Indian fraud scenarios. The asymmetric
improvement — *detection unchanged, FPR down* — is the signal that the
model learned the task instead of gaming the reward.

We then ship the missing piece: a **trained adversarial Scammer**
(Qwen2.5-0.5B + LoRA, GRPO with adversarial reward) that evades the
rule-based defender at **93.75 %** best-of-8 (n = 64) and **100 %** on
8 held-out novel attack categories. Same Scammer outputs vs the v2
Analyzer LoRA: **32.8 %** bypass — a **60 pp gap** that quantifies what
co-evolution actually buys.

## 1. Why this environment

India loses **₹13,000+ crore per year** to UPI fraud across **60 crore
users**. Rule-based detectors degrade meaningfully on post-2024 attack
patterns — we measured **scripted analyzer detection = 50 % on a
34-scenario novel split** (matrimonial-crypto grooming, deepfake CEO
IPO pitches, "digital arrest" calls, Aadhaar reverification scams).
**No public RL environment exists for multi-agent fraud-detection
research.** So we built one — Chakravyuh, a five-agent OpenEnv
environment with asymmetric information and partial observability.

## 2. The environment

```
        REGULATOR (meta) ── adapts rule weights from outcomes
                │
ON-DEVICE  → BEHAVIORAL ANALYZER ←  Qwen2.5-7B + LoRA-v2 (GRPO)   [TRAINED]
            │  sees chat only
   SCAMMER ─┴─ chat ── VICTIM ── attempts transaction
   ▲
   └─ Qwen2.5-0.5B + LoRA-Phase1 (GRPO, adversarial reward)        [TRAINED, B.2]
                                 │
            BANK MONITOR ── sees transaction metadata only
```

The Analyzer (the LLM under training) sees only chat. The Bank Monitor
sees only transaction metadata. The Regulator sees only aggregate
outcomes across episodes. Neither single oversight tier can be hacked
into single-handedly suppressing the "money extracted" outcome — they
have to agree. **Two trained adapters, not one.**

The reward (`AnalyzerRubricV2`) decomposes into **eight orthogonal
child rubrics** (composable, introspectable, swappable):

| Rubric | Weight (v2) | What it rewards |
|---|---|---|
| `DetectionRubric` | +1.0 | Early flag of a real scam (turn ≤ 5) |
| `MissedScamRubric` | −0.5 | Missed scam where money was extracted |
| `FalsePositiveRubric` | **−0.8** *(v1: −0.3)* | Benign incorrectly flagged |
| `CalibrationRubric` | **+0.5** *(v1: +0.3)* | Score-vs-truth calibration in both directions |
| `ExplanationRubric` | +0.4 | Natural-language explanation references declared signals |
| `SignalAccuracyRubric` | +0.2 | Fraction of expected signals correctly named |
| `FormatRubric` | +0.15 | Strict JSON output — **denied when flagging benign as scam** |
| `LengthRubric` | ±0.15 | Peak at ~45 tokens, penalty above 70 |

Plus a side-channel `RupeeWeightedRubric` aggregator that scales
detection / miss credit by `loss_amount_inr` to produce the bench-level
**₹77.95 lakh at risk** headline (130 scams with labelled losses).

## 3. The reward-hacking failure (caught and fixed)

v1 trained on the same env hit:

- **Detection: 100 %** ← suspicious
- **FPR: 36 %** ← textbook fingerprint

That combination — detection saturated, FPR catastrophic, **uniform
across difficulty buckets** — is what reward hacking *looks like*. The
model learned "always output a high score." It correctly flags every
scam, and over-flags every benign too. Calibration collapsed.

We diagnosed the reward profile and made three principled changes for v2:

1. **FP penalty −0.3 → −0.8.** Flagging benigns is now expensive enough
   that "always flag" is a dominated strategy.
2. **Format reward denied on benign-flagged-as-scam.** v1 paid the
   format-correctness bonus regardless of whether the prediction was
   right. Removing it specifically on benign-flagged-scam outputs kills
   the "lazy over-flag still gets credit" loophole.
3. **Benign calibration weight +0.3 → +0.5.** Stronger gradient toward
   `score ≤ 0.2` on benign cases.

Plus the KL anchor was tightened (`β = 0.08 → 0.15`) so the model can't
drift far from the base distribution under the new reward shape.

The result:

| Metric | v1 (reward-hacked) | **v2 (fixed)** | 95 % CI (v2) |
|---|---|---|---|
| Detection | 100.0 % | **99.3 %** | [97.9 %, 100 %] |
| FPR | 36.0 % | **6.7 %** | [0.0 %, 16.7 %] |
| F1 | 0.96 | **0.99** | [0.976, 1.000] |
| Novel-detection (post-2024) | 100 % | 97.1 % | [91.2 %, 100 %] |

Detection moved 100 % → 99.3 % — barely. FPR dropped **5×**. That
asymmetric improvement is the signature of a model that's actually
learning the task. A model still gaming the reward improves both
numbers in lockstep, or fails on novel attacks.

## 4. The trained adversarial Scammer (Theme #1 evidence)

Most submissions train *one* agent. We trained a **second** —
`chakravyuh-scammer-lora-phase1`. Recipe: Qwen2.5-0.5B-Instruct + LoRA,
TRL 0.14 GRPO, adversarial reward `1 − ScriptedAnalyzer.score`. After
200 episodes the adapter learned to generate plausible
Indian-context UPI-fraud openings.

| Defender | Best-of-8 bypass (n=64) | Held-out novel (n=32) |
|---|---|---|
| Rule-based ScriptedAnalyzer | **93.75 %** | **100 %** |
| v2 Analyzer LoRA (this submission) | **32.8 %** | **37.5 %** |
| **Co-evolution gap** | **+60.9 pp** | **+62.5 pp** |

Cross-tab: **62.5 % (40/64)** of scams that fool the rule-based
defender get caught by the v2 LoRA; only **1.6 % (1/64)** go the other
way. v2 strictly dominates the rule baseline — pure co-evolution
evidence.

**Where v2 is honestly weak:** vaccine slot, customer-support
callback, credit-card EMI, income-tax refund — all non-bank categories
outside v2's training distribution. Exact targets for the Phase 2
retrain (LoRA-vs-LoRA, queued for the next compute window).

## 5. Open-weight frontier comparison (7 models, same bench, same prompt)

We ran the same n = 174 bench through 6 open-weight frontier models via
HuggingFace Inference Providers (paid from HF compute credits, ~$2
total).

| Model | Params | F1 | FPR |
|---|---|---|---|
| **v2 LoRA (this work)** | **7B + LoRA r=64** | **0.990** | **6.7 %** |
| Qwen2.5-7B-Instruct (base, no LoRA) | 7B | 0.980 | 16.1 % |
| Llama-3.3-70B-Instruct | 70B | 0.990 | 3.2 % |
| Qwen2.5-72B-Instruct | 72B | 0.983 | 6.5 % |
| DeepSeek-V3-0324 | 671B MoE | 0.966 | **29 %** |
| gpt-oss-120b | 120B | 0.972 | 16.1 % |
| gemma-3-27b-it | 27B | 0.944 | **51.6 %** |

Three readouts:

1. **GRPO + LoRA contribution is isolated.** Same Qwen2.5-7B base, no
   LoRA → FPR **16.1 %**. After our reward-engineered GRPO training →
   FPR **6.7 %**. **−9.4 pp FPR, +0.010 F1 attributable purely to the
   training.**
2. **Parameter efficiency.** 7B + LoRA ties Llama-3.3-70B on F1 at
   **10× fewer parameters**, beats every other model in the table.
3. **DeepSeek-V3 (671B) reproduces our v1 reward-hacking signature
   externally.** Detection 99.3 % / FPR 29 % is structurally identical
   to v1's 100 % / 36 %. A frontier-class model independently falls
   into the failure mode our methodology diagnoses and fixes — external
   validation that calibrated reward design beats raw capacity.

## 6. Honest limitations

- **Single seed** — bootstrap CIs are the substitute; multi-seed is v3.
- **n = 30 benigns** — the 5× FPR reduction is statistically real
  (permutation test p ≈ 0.008), the precise 6.7 % is not tight.
- **Semantic leakage** — 44.8 % of bench items have cosine > 0.85 to
  training. We disclose this *as a feature*; the v1→v2 FPR fix and the
  scripted-baseline novel collapse are unaffected (relative comparisons
  on the same bench).
- **Phase 2 (LoRA-vs-LoRA co-evolution)** — Phase 1 is shipped; Phase 2
  retrains the Analyzer against the frozen Scammer. Compute-gated.
- **Per-language eval, calibration ECE, multi-seed retrain, frontier
  proprietary-tier comparison** — all named in
  [`docs/limitations.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/limitations.md).

## 7. Theme coverage

- **Theme #1 — Multi-Agent Interactions (primary).** Five agents,
  asymmetric information, two-tier oversight, partial observability,
  **two trained adapters** with measured co-evolution gap.
- **Theme #4 — Self-Improvement (honestly demoted).** The v1 → v2
  reward-hacking-fix loop is self-improvement of the *training
  pipeline*, not recursive skill amplification. We frame this honestly
  in `docs/limitations.md` rather than over-claim.

## 8. Reproduce in 60 seconds

```bash
git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
pip install -e '.[llm,eval]'
make smoke-test               # in-process env reset+step in <5s
pytest tests/ --tb=no -q      # 337 collected; 334 pass + 3 skip
make reproduce                # ~10 min CPU cached eval; verifies headlines within 0.5pp
```

Full reproduction walkthrough (5 steps with expected outputs):
[`REPRODUCE.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/REPRODUCE.md).

## 9. Submission materials (linked from the HF Space README)

| Asset | Link |
|---|---|
| Live env (this Space) | [`ujjwalpardeshi/chakravyuh`](https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh) |
| Defender adapter | [`chakravyuh-analyzer-lora-v2`](https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2) |
| Adversary adapter (gated) | [`chakravyuh-scammer-lora-phase1`](https://huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1) |
| Bench dataset | [`chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0) |
| Source code | <https://github.com/UjjwalPardeshi/Chakravyuh> |
| Slide deck (Marp markdown source) | [`docs/chakravyuh_slides.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/chakravyuh_slides.md) |
| YouTube video (90-sec demo) | *to be added — see HF Space README* |
| Reproduction walkthrough | [`REPRODUCE.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/REPRODUCE.md) |
| Misuse / dual-use disclosure | [`docs/misuse_dual_use.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/misuse_dual_use.md) |

## License

MIT for code (`LICENSE`); CC-BY-4.0 for `chakravyuh-bench-v0`. The
Scammer LoRA is gated under the responsible-use terms in
[`docs/RESPONSIBLE_USE.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/RESPONSIBLE_USE.md).

## Citation

```bibtex
@misc{chakravyuh2026,
  title  = {Chakravyuh: A Multi-Agent OpenEnv Environment for Indian UPI Fraud Detection},
  author = {Pardeshi, Ujjwal and Chakravyuh Team},
  year   = {2026},
  howpublished = {Meta PyTorch OpenEnv Hackathon, Bangalore, April 2026},
  url    = {https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh}
}
```

— *Try the live demo. Break it. Then beat us on the leaderboard.*
