# Design Decisions

This document records the non-obvious choices that shaped Chakravyuh, with the alternatives we rejected and *why*. Each section is short by design — judges should read this in 5 minutes, not 50.

The bias throughout: **measurement before claim**, and small honest signals over large unverified ones.

---

## 1. Why GRPO over PPO

We use TRL's GRPO for Analyzer post-training. PPO was the obvious alternative.

| Axis | PPO | **GRPO (chosen)** |
|---|---|---|
| Critic / value head | Required (extra params + memory) | Not needed — group-relative baseline |
| Memory on a single A100-80 GB | Tight w/ 7B + critic | Comfortable |
| Reward shape that works | Dense | Tolerates sparse / categorical |
| Single-prompt rollouts | Awkward | Natural fit (group of completions per prompt) |

GRPO's group-relative advantage estimator removes the need for a separate value head. On Colab Pro+ (single A100-80) we could fit Qwen2.5-7B-Instruct + LoRA r=64 + 4-bit quantization with margin. With PPO we would have had to drop to a smaller base model or a smaller LoRA rank. Given the hackathon time budget, GRPO won outright.

Reward shape also favored GRPO: our 5-rubric reward emits one scalar per episode (not per token), which fits group-relative naturally and is awkward for PPO's dense advantage estimation.

---

## 2. Why Qwen2.5-7B-Instruct as the base

We considered Llama-3.1-8B-Instruct, Mistral-7B-Instruct, Qwen2.5-7B-Instruct, and Phi-3-medium.

**Chosen:** Qwen2.5-7B-Instruct.

- Strong multilingual coverage including **Hindi, Tamil, Telugu, Bengali, Marathi** — non-negotiable for Indian UPI fraud, where scams routinely arrive in regional scripts.
- Permissive license (Apache 2.0) — clears responsible-release path.
- 32k context — enough for a full multi-turn dialogue + system prompt + chain-of-thought signal taxonomy.
- Strong JSON-output behavior under instruction — important since our action schema is strict JSON.

**Why not Llama-3.1-8B:** comparable English performance but weaker on Tamil/Telugu/Marathi in our smoke tests.
**Why not Phi-3:** smaller (3.8B / 7B) but the 7B is gated and not as strong on multilingual.
**Why not Mistral-7B:** older instruction-following; weaker JSON adherence under our chat template.

---

## 3. Why on-device deployment (the architecture, not just an aesthetic)

The Analyzer runs **on the victim's phone**. Chat content never leaves the device — only the anonymized risk score reaches the bank.

This was a substantive architectural choice, not branding:

1. **Regulatory.** RBI and DPDP-Act-compliant: chat content stays with the user; no PII flows to a central server. We do not become a regulated data fiduciary by virtue of routing chat through cloud.
2. **Trust.** A bank-side detector that reads chat content would be rejected by users on day 1. Gmail's on-device spam filter works for the same reason.
3. **Latency.** Inference on-device cuts ~250 ms RTT and survives flaky networks (rural 2G/3G use cases).
4. **Multi-channel oversight, cleanly.** Because the Analyzer cannot see transaction metadata and the Bank Monitor cannot see chat, neither single oversight channel can be reward-hacked into suppressing the "money extracted" outcome alone — they must agree.

This shapes our 7B / LoRA / 4-bit-quant choice — the model has to fit on a flagship phone and answer in <2 s. A 70B frontier model is structurally ineligible.

---

## 4. Why 8 rubrics, and exactly these 8

The composable reward `AnalyzerRubricV2` ([`chakravyuh_env/rubrics.py`](../chakravyuh_env/rubrics.py)) decomposes into:

| Rubric | Weight (v2) | What it rewards |
|---|---|---|
| `DetectionRubric` | +1.0 | Early flag (turn ≤ 5) of a real scam |
| `MissedScamRubric` | −0.5 | Missed-scam where money was extracted |
| `FalsePositiveRubric` | −0.8 *(v1: −0.3)* | Benign incorrectly flagged |
| `CalibrationRubric` | +0.5 *(v1: +0.3)* | Score matches ground truth (high on scam, low on benign) |
| `ExplanationRubric` | +0.4 | Natural-language explanation references declared signals |
| `SignalAccuracyRubric` | +0.2 | Declared signal set is consistent with the rule-based heuristics on the same chat |
| `FormatRubric` | +0.1 | Strict-JSON output adheres to the schema; **denied** when the model flags benign as scam (v2 anti-collapse fix) |
| `LengthRubric` | +0.1 | Penalises both empty and run-on explanations; tightens the explanation channel |

The hackathon guide flagged reward hacking as the single biggest practical failure mode. Our prescription:

- **Multiple independent signals.** No single signal can be gamed in isolation. Each rubric reads a different slice of the action/outcome.
- **Non-compounding.** Each child clips to [0, 1] (or {0, 1}) — the top-level sum is bounded analytically, no multiplicative reward-stacking route.
- **Explicit FP penalty.** Makes "always flag" a dominated strategy.
- **Calibration.** Rewards low scores on benign — an "always 1.0" agent tanks calibration.
- **Explanation cross-references signals.** An empty-signals + boilerplate combination cannot collect the explanation bonus.
- **Format reward gated on benign-as-scam.** Removes the perverse incentive that let v1 collect format reward while over-flagging.
- **Trajectory awareness.** Detection requires `outcome.detected_by_turn ≤ 5`, not just a final-turn score flip.

We rejected a 3-rubric simpler design (detection / FP / calibration) because v1 collapsed on it. The v1 → v2 fix promoted three previously-inline shaping signals (`signal_accuracy`, `format`, `length`) into first-class composable rubrics, alongside tightening `false_positive` (−0.3 → −0.8), raising `calibration` (+0.3 → +0.5), and denying `format` reward when benign is flagged. The recovered v2 numbers (FPR 36 % → 6.7 %, 5×) are the empirical evidence the v1 → v2 reward changes matter.

---

## 5. Why a 0.5B Scammer vs the same 7B as Analyzer

For the adversarial Phase-2 self-play (planned onsite), the Scammer LoRA is on Qwen2.5-**0.5B**-Instruct, not 7B.

- **Compute budget.** 7B-vs-7B self-play across 200 episodes is ~3× the HF-credit envelope we have.
- **Asymmetry by design.** Real scammers don't run frontier LLMs on burner phones — they run cheap, fast, repetitive scripts. A 0.5B Scammer mirrors the threat surface more honestly than a 7B Scammer would.
- **Detection still has to work.** If a 7B Analyzer can be reliably fooled by a 0.5B Scammer, that's a stronger negative result than two equally large models trading attacks.

Adverse-results plan (C.2): if the 0.5B Scammer doesn't converge in 2 h, fall back to an SFT generation head; do not pretend a non-convergent run worked.

---

## 6. Why bench size 175 (not 1k, not 50)

The bench is hand-curated from public RBI advisories, news incidents, and validated scammer scripts. We deliberately stopped at 175 rather than mass-generate to 1000.

- **Quality > quantity** for benchmarks of small-incidence phenomena. A 1k bench made of templated variants would inflate detection numbers without testing genuine generalization.
- **Soft-leakage filter.** All 175 scenarios are diff-checked against the 619-example training corpus via a min-hash similarity filter (`training/grpo_analyzer.py:_filter_soft_leakage`). Mass-generation would defeat the filter.
- **174 scored / 175 total.** One scenario was skipped (empty text). Reported as "174 evaluated" — Operating Principle #1: don't quietly drop denominators.

The trade-off is statistical thinness on benign (n = 30). We disclose this honestly and the bootstrap CI on FPR ([0 %, 16.7 %]) reflects it. Expanding benign to n ≥ 150 is an explicit v3 milestone.

---

## 7. Why bootstrap CIs (and not just point estimates)

Every headline number in the README has a 95 % bootstrap CI from [`logs/bootstrap_v2.json`](../logs/bootstrap_v2.json) (10 000 iterations, percentile method).

Why this matters:

- A point estimate "FPR = 6.7 %" without the [0 %, 16.7 %] band would be misleading at n = 30. One additional misclassified benign moves the point from 6.7 % to 10 %.
- Multi-seed retrains would be the gold standard — we run only one seed, so bootstrap is the best honest substitute. We say so plainly in the limitations section.
- It also gates the "5× FPR reduction" claim. The CI on v2's FPR ([0 %, 16.7 %]) does not include v1's 36 %, so the *direction* and *magnitude* of the improvement are statistically real even if the precise 6.7 % is not.

---

## 8. Why we kept the v1 reward-hacking story instead of deleting it

It would have been easy to delete `eval_v1.json` and present v2 as the only adapter. We chose the opposite: lead with v1 → v2 as a *teaching artifact*.

- **Reward hacking is the named failure mode** in the hackathon guide. The most credible thing a submission can do is *exhibit and diagnose one*.
- **The v1 fingerprint** (det = 100 % / FPR = 36 %, uniformly across difficulty) is textbook. v2 produced an asymmetric improvement (det unchanged, FPR 5× better) — the asymmetry is what proves we actually learned.
- The diagnosis itself — FP penalty −0.3 → −0.8, format reward denied on benign-flagged-scam, KL anchor 0.08 → 0.15 — is reusable knowledge for any scalable-oversight project.

---

## 9. Why we publish the soft-leakage filter

The filter ([`training/grpo_analyzer.py:_filter_soft_leakage`](../training/grpo_analyzer.py)) was enforced *before* training and the filter code itself is open. Two reasons:

1. The most common "great-results" failure on small benches is silent test-set bleed. Open filter = checkable claim.
2. Future submitters can run the same filter against the same bench — apples-to-apples comparisons need a reproducible filter.

---

## 10. Why we shipped a *Space*, not just a model card

The HF Space ([`ujjwalpardeshi/chakravyuh`](https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh)) runs the *full env*, not just the analyzer model. Judges (and future researchers) can:

- Hit `POST /reset` and `POST /step` directly to drive the env.
- See the full `/openapi.json` schema, including the action / observation models.
- Compare a scripted-baseline analyzer against a LoRA-loaded analyzer with one toggle.

A model card alone would only show one piece (the trained LoRA). The env is the contribution; we ship the env.

---

## What we deliberately did **not** decide

The following decisions are explicitly deferred to v3, with rationale in [`docs/POSTMORTEM_FUTURE.md`](POSTMORTEM_FUTURE.md):

- Multi-seed retrains (single seed currently).
- Per-language eval (English-dominant training; numbers per-language not measured).
- Adversarial Scammer Phase-2 retrain of the Analyzer (compute-gated, planned onsite).
- Token-level saliency for explanation reliability (planned, not shipped).
- Rupee-weighted economic loss reward (designed, labels pending).

Each of these is a real gap. We name them so judges don't have to guess what's missing.
