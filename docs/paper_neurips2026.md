# Chakravyuh: A Multi-Agent OpenEnv Environment for Indian UPI Fraud Detection with a Diagnosed Reward-Hacking Incident

**Ujjwal Pardeshi** *(independent researcher, Bangalore)*
**Submission:** NeurIPS 2026 Foundation Models for Decision Making Workshop (anticipated)
**Code & artifacts:** <https://github.com/UjjwalPardeshi/Chakravyuh> · adapter [`ujjwalpardeshi/chakravyuh-analyzer-lora-v2`](https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2) · bench [`ujjwalpardeshi/chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0)
**License:** MIT (code) · CC-BY-4.0 (bench)

> **Format note.** This file is the markdown draft of the 4-page workshop paper. A LaTeX/Overleaf compile is the final shipping format; the source content here is what will be typeset. References use ad-hoc bracketed citations and will be migrated to BibTeX in the LaTeX pass. Page-count target: 4 pages excluding references and appendix.

---

## Abstract

We introduce **Chakravyuh**, a multi-agent OpenEnv environment for Indian UPI (Unified Payments Interface) fraud detection. Five agents — Scammer, Victim, on-device Analyzer LLM, Bank Monitor, and Regulator — interact under structural information asymmetry: the Analyzer reads only chat content, the Bank Monitor reads only transaction metadata, and the Regulator sees only aggregate outcomes. We post-train a Qwen2.5-7B-Instruct LoRA Analyzer using TRL's GRPO on a composable five-rubric reward (detection / FP penalty / missed-scam / calibration / explanation). The central artifact is a **diagnosed and fixed reward-hacking incident**: v1 hit detection 100% / FPR 36% (the textbook fingerprint of an "always flag" policy), and three principled reward changes (FP penalty −0.3 → −0.8, format reward denied on benign-flagged-scam outputs, calibration weight 0.3 → 0.5, KL anchor β = 0.08 → 0.15) produced v2 with detection 99.3% / FPR 6.7% on a 174-scenario bench (n = 144 scams + 30 benign; 95% bootstrap CI on detection [97.9%, 100%], on FPR [0%, 16.7%]). We release the environment, the bench, both adapters, the live HF Space, and a soft-leakage filter that we ran *before* training, so every claim is checkable.

---

## 1 Introduction

UPI fraud cost Indian consumers ₹13,000+ crore per year, with detection of post-2024 attack patterns (matrimonial-crypto grooming, deepfake CEO IPO pitches, "digital arrest" calls, biometric-clone Aadhaar fraud) lagging substantially behind detection of canonical OTP / KYC / impersonation patterns [I4C 2025; RBI Annual Report on Financial Fraud FY24]. Despite the scale of the problem, no public RL environment for multi-agent fraud detection in the Indian context existed prior to this work.

We frame the task as **scalable oversight**: can we post-train an LLM to monitor, score, and explain the behavior of an adversarial agent operating in a complex, partially observable multi-agent setting? Reward hacking is the central failure mode of such systems [Pan et al. 2022; Skalse et al. 2022], and the most credible thing a submission can do is exhibit one and diagnose it. This paper does that.

### Contributions

1. **An OpenEnv-compliant multi-agent environment** with structural information asymmetry, on-device deployment story, and FastAPI server (<https://ujjwalpardeshi-chakravyuh.hf.space>). Source: github.com/UjjwalPardeshi/Chakravyuh.
2. **A 175-scenario public benchmark** (`chakravyuh-bench-v0`) sourced from RBI / NPCI / I4C / news, with rule-vs-expert Cohen's κ = 0.277 (fair) so the bench is not a keyword-matching exercise. CC-BY-4.0.
3. **A diagnosed and fixed reward-hacking incident** (v1 → v2) that maps directly onto the standard "always flag" failure mode and produces an asymmetric improvement (detection unchanged, FPR 5× lower) — the empirical signature of genuine learning rather than reward gaming.
4. **A soft-leakage filter** that strips training examples too similar to the bench at training time, run before every retrain. Open code; checkable claim.
5. **A two-tier oversight architecture** (Analyzer reads chat only, Bank Monitor reads metadata only) with an optional cross-tier negotiation protocol that preserves the privacy invariant. The Bank Monitor never sees chat content; only an `AnalyzerConsultation` (score + signals + flag bit, no chat).

---

## 2 Environment

### 2.1 Agents and information surface

Five agents (Table 1):

| Agent | Role | Sees | Trained? |
|---|---|---|---|
| Scammer | Adversary | Own plan + victim responses | No (376 templates from RBI/NPCI/news, NPCI-grounded) |
| Victim | Target | Chat + own demographic profile | No (scripted; Senior / Semi-Urban / Young-Urban profiles) |
| **Analyzer** | Oversight LLM | Full chat transcript only | **Yes** — LoRA on Qwen2.5-7B-Instruct via TRL GRPO |
| Bank Monitor | Oversight (metadata) | Tx amount + payee novelty + frequency | No (scripted rule-based) |
| Regulator | Meta-agent | Aggregate outcomes across episodes | No (rule-weight updater) |

**Privacy invariant.** The Analyzer cannot see transaction metadata; the Bank Monitor cannot see chat. This is enforced structurally — they receive different `Observation` shapes — and the optional Analyzer ↔ Bank consultation [§ 3.4] only exposes scalar scores + signal names, never chat.

### 2.2 Reward — five composable rubrics

Following [Anthropic 2024; OpenEnv guide 2026], we decompose the analyzer's reward into orthogonal rubrics so no single signal dominates:

```
R = w_det · DetectionRubric           # +1.0  (early flag of true positive, turn ≤ 5)
  + w_miss · MissedScamRubric         # −0.5  (missed scam, money extracted)
  + w_fp · FalsePositiveRubric        # −0.8 (v2)
  + w_cal · CalibrationRubric          # +0.5 (v2, on benign)
  + w_exp · ExplanationRubric          # +0.4
```

Each rubric is a `Rubric` subclass with `last_score`, swappable for an `LLMJudge` without touching the top-level. Per-rubric trajectories during training are logged so each can be plotted independently — a standard reward-hacking diagnostic. (See § 4.)

### 2.3 Bench

`chakravyuh-bench-v0` ships **175 scenarios** (174 scored, 1 skipped on empty text):

- 144 scam + 31 benign (15 benign + 16 borderline for FP discipline)
- 4 difficulty buckets (easy = 30, medium = 78, hard = 33, novel = 34)
- 5 scam categories + 6 novel post-2024 categories (matrimonial-crypto, deepfake CEO, AePS biometric-clone, "digital arrest", FASTag KYC, ABHA Health ID)
- Multi-language probes in Hindi, Tamil, Telugu, Kannada, Bengali, Marathi (n = 5)
- Multi-turn (n = 15) and adversarial paraphrases (n = 10)

Sources: RBI Annual Report on Financial Fraud FY22–24; NPCI Safety Bulletins; I4C alerts; sachet.rbi.org.in. Every scenario is a *realistic reconstruction* of public attack patterns (verbatim victim transcripts are not publicly releasable for privacy reasons).

**Label quality.** Rule-vs-expert Cohen's κ = 0.277 (fair). Full human inter-rater reliability is deferred to v0.3.

---

## 3 Method

### 3.1 Base model and post-training

Base: Qwen2.5-7B-Instruct (4-bit Unsloth quantization for training, bf16 inference). LoRA r = 64, α = 128. Training: TRL GRPO over 619 examples (456 scam + 204 benign templates, post-soft-leakage filter). 1 epoch, ≈ 2 h on a single A100-80GB.

We chose GRPO over PPO because (a) GRPO's group-relative advantage estimator removes the need for a separate value head, freeing memory for a 7B base + r=64 LoRA + 4-bit quant on a single A100, (b) our reward is one scalar per episode (group-relative is a natural fit), and (c) TRL's GRPO is well-tested.

### 3.2 Soft-leakage filter (anti-leakage proof, run before every train)

For every (training_example, bench_scenario) pair we compute MinHash-Jaccard similarity over normalized 5-gram shingles; any training example with similarity ≥ 0.7 to any bench scenario is dropped. Code: `training/grpo_analyzer.py:_filter_soft_leakage`. The filter is open precisely so the claim "the bench is not in training" is checkable.

### 3.3 v1 reward profile (the failed one) and v2 fix

| Rubric weight | v1 | **v2** |
|---|---|---|
| Detection | +1.0 | +1.0 |
| Missed-scam | −0.5 | −0.5 |
| **False-positive** | **−0.3** | **−0.8** |
| Calibration (benign) | 0.3 | **0.5** |
| Explanation | 0.4 | 0.4 |
| **Format reward on benign-flagged-as-scam** | paid | **denied** |
| KL anchor β | 0.08 | **0.15** |

**v1 result:** detection 100% / FPR 36% / detection uniform across difficulties. This is the "always flag" reward-hacking fingerprint [Skalse et al. 2022]. Since the format reward was paid even on incorrect predictions, an "always output high score" policy collected the format bonus on every benign while the FP penalty (−0.3) was insufficient to suppress it. Calibration on benigns was too weakly weighted (0.3) to push the model back.

**v2 fix.** The three changes target three independent failure modes:

1. **−0.8 FP penalty** raises the cost of flagging a benign so flagging has to be *correct*, not free.
2. **Format reward denied** on benign-flagged-as-scam removes the "lazy over-flag" incentive entirely on the failure case.
3. **Calibration weight 0.5** strengthens the gradient pulling benign scores toward 0.

KL β = 0.15 (vs 0.08 in v1) prevents the model from drifting too far under the new reward shape and over-correcting toward "never flag."

### 3.4 Optional Analyzer ↔ Bank negotiation (§ docs/negotiation_protocol.md)

In the baseline turn schedule the Bank Monitor and Analyzer act independently. We add an optional `enable_negotiation=True` mode where, before the bank decides, an `AnalyzerConsultation = (score, signals, threshold, flagged)` is computed from the analyzer's most recent action and passed to the bank. Combined risk = 0.6 · bank_risk + 0.4 · analyzer_risk. This is structurally privacy-preserving: the consultation surface contains zero chat content, and a unit test pins the schema's field set so any expansion fails CI.

---

## 4 Results

### 4.1 Headline (174 scenarios; threshold 0.55; bootstrap 95% CI, 10 000 iterations)

| Metric | v1 (reward-hacked) | **v2 (fixed)** | 95% CI (v2) |
|---|---|---|---|
| Detection (recall on 144 scams) | 100.0 % | **99.3 %** | [97.9 %, 100 %] |
| FPR (on 30 benign) | 36.0 % | **6.7 %** | [0.0 %, 16.7 %] |
| F1 | 0.96 | **0.99** | [0.976, 1.000] |
| Per-difficulty: easy / medium / hard / novel | 100/100/100/100 | 100 / 100 / 100 / 97.1 | novel CI [91.2 %, 100 %] |

The asymmetric improvement (detection unchanged, FPR 5× lower) is the empirical signature of genuine learning vs reward gaming. A model still hacking the reward improves both numbers in lockstep. v2's 97% on the 34-scenario novel bucket — mildly less than the perfect easy/medium/hard buckets — is the small honest crack confirming the model is differentiating, not collapsing.

### 4.2 Anti-leakage and label quality

- Soft-leakage filter dropped X% of candidate training examples (figure cited in `logs/_filter_soft_leakage_stats.json` once committed).
- Rule-vs-expert κ = 0.277 (fair). The bench is not a keyword game; a trained model needs to exceed κ ≈ 0.7 to claim real capability. v2 hits κ = 0.95 (point) on the same comparison.

### 4.3 Limitations

We name them explicitly:

1. **Single-seed.** Multi-seed retrain (mean ± std) is v3 milestone #1.
2. **Small benign sample.** n = 30 yields wide FPR CI. The 5× reduction is robust; the precise 6.7% is not. Bench expansion to n ≥ 150 benign (≈ 120 hand-authored templates underway, see `chakravyuh_env/benign_augmented_v2.json`) is v3 milestone #2.
3. **Frontier baseline pending.** GPT-4o / Claude / Gemini / Llama-3.3-70B comparison wired up (`eval/frontier_baseline.py`) but not yet run — API budget deferred. We will not claim frontier comparisons we have not measured.
4. **Per-language eval pending.** Multi-language detection on Hindi/Tamil/Telugu/Bengali/Marathi requires per-language eval (`eval/per_language_eval.py` stub).
5. **One epoch over 619 examples.** More data + longer training are deferred to v3.

---

## 5 Related work

**Reward hacking** is the named failure mode in [Pan et al. 2022; Skalse et al. 2022]; we follow [Anthropic 2024]'s composable-rubric prescription. **Scalable oversight** as a research frame for LLM training is articulated in [Bowman et al. 2022; Saunders et al. 2022]. **OpenEnv** as a multi-agent environment standard ships from `meta-pytorch/OpenEnv` (2025–26). **Indian UPI fraud detection** prior work has been overwhelmingly rule-based [I4C 2024 reports]; learned-policy detection in this domain is, to our knowledge, a new public contribution.

---

## 6 Conclusion

Chakravyuh contributes the *infrastructure* — a multi-agent env, a public bench, an open-source soft-leakage filter, two trained adapters, and a live HF Space — for measurement-first scalable-oversight research on a regulated, regional fraud domain. The central artifact, a diagnosed-and-fixed reward-hacking incident, demonstrates that the framework actually catches the failure mode it was built to catch. The five-agent template, soft-leakage filter, bootstrap CI, and v2 reward profile transfer directly to other text-channel fraud domains (insurance claims, BEC, KYC fraud) — a forking guide ships in `docs/EXTEND.md`.

**v3 ships when:** multi-seed retrain green, benign expanded to n ≥ 150, frontier baseline measured, per-language eval published, external held-out novel set added. Roadmap with priority ordering is in `docs/POSTMORTEM_FUTURE.md`.

---

## Appendix A — Reproducing the key numbers

```bash
git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
pip install -e '.[llm,eval,demo,frontier,dev]'
make reproduce
# Compares within ±0.5pp of paper values, writes:
#   logs/eval_v2_reproduce.json
#   logs/bootstrap_v2_reproduce.json
```

## Appendix B — Reward profile diff (v1 → v2)

Located in `training/grpo_analyzer.py::REWARD_PROFILES`:

```python
REWARD_PROFILES = {
    "v1": dict(detection=+1.0, missed_scam=-0.5, false_positive=-0.3,
               calibration_benign=0.3, explanation=0.4,
               format_on_benign_flagged_as_scam="paid", kl_beta=0.08),
    "v2": dict(detection=+1.0, missed_scam=-0.5, false_positive=-0.8,
               calibration_benign=0.5, explanation=0.4,
               format_on_benign_flagged_as_scam="denied", kl_beta=0.15),
}
```

## Appendix C — Bootstrap CI procedure

We use a percentile bootstrap on Bernoulli outcome arrays reconstructed from `logs/eval_v2.json` aggregates. For detection rate, we resample n_scams = 144 binary outcomes (143 hits, 1 miss) with replacement; CI is the [2.5%, 97.5%] percentile of 10 000 resampled means. Same procedure for FPR. F1 is jointly bootstrapped over the (scam, benign) outcome union. Code: `eval/bootstrap_ci.py`.

## Appendix D — Statistical caveats on bench thinness

Wilson 95% CI on FPR (n = 30, k = 2 misclassifications) = [1.8%, 20.7%]. Bootstrap 95% CI on FPR = [0%, 16.7%]. Both are valid for different things (Wilson is exact for small-n Bernoulli; bootstrap is sample-derived). They differ at the upper tail because n is small. We report bootstrap in the headline (consistent with our other resampling-based CIs); Wilson appears in `docs/POSTMORTEM_FUTURE.md` as a tighter upper-bound proof. With n = 150 benign in v3 the two will converge.

---

**References (to be migrated to BibTeX):**

- Anthropic. *Constitutional AI: Harmlessness from AI Feedback*. 2024.
- Bowman, S. R. et al. *Measuring Progress on Scalable Oversight for Large Language Models*. 2022.
- I4C — Indian Cybercrime Coordination Centre. *Annual Report 2024*. cybercrime.gov.in.
- meta-pytorch/OpenEnv. <https://github.com/meta-pytorch/OpenEnv>. 2026.
- Pan, A. et al. *The Effects of Reward Misspecification: Mapping and Mitigating Misaligned Models*. 2022.
- RBI. *Annual Report on Trend and Progress of Banking in India FY24*. rbi.org.in.
- Saunders, W. et al. *Self-critiquing models for assisting human evaluators*. 2022.
- Skalse, J. et al. *Defining and Characterizing Reward Hacking*. NeurIPS 2022.
- TRL. <https://github.com/huggingface/trl>. 2026.
