---
name: chakravyuh-bench-v0
license: cc-by-4.0
language:
  - en
  - hi
  - ta
  - te
  - kn
  - bn
  - mr
task_categories:
  - text-classification
tags:
  - fraud-detection
  - upi
  - india
  - safety
  - benchmark
  - scam-detection
  - multilingual
  - multi-turn
size_categories:
  - n<1K
pretty_name: Chakravyuh-Bench-v0 — Indian UPI Fraud Detection
---

# Chakravyuh-Bench-v0 — Dataset Card

> **Canonical card** (with HF Datasets front-matter) lives at [`data/chakravyuh-bench-v0/README.md`](data/chakravyuh-bench-v0/README.md). This file is the repo-level mirror so it shows up alongside [`MODEL_CARD.md`](MODEL_CARD.md) and [`README.md`](README.md).

## Summary

`chakravyuh-bench-v0` is the public evaluation dataset for the [Chakravyuh](https://github.com/UjjwalPardeshi/Chakravyuh) multi-agent Indian UPI fraud-detection environment. **175 hand-curated scenarios** (174 scored after one was skipped for empty text) — 144 scams across 5 fraud categories, 31 non-scam (15 benign + 16 borderline for false-positive discipline).

## Composition

| | n |
|---|---|
| **Total scenarios** | 175 |
| Scored in eval (one skipped on empty text) | 174 |
| Scams | 144 |
| Non-scams | 31 |
| Multi-turn (2–4 turns) | 15 |
| Adversarial paraphrases | 10 |
| Regional-language probes (`hi/ta/te/kn/bn/mr`) | 5 |

| Difficulty | n |
|---|---|
| Easy | 30 |
| Medium | 78 |
| Hard | 33 |
| Novel (post-2024) | 34 |

| Category | n |
|---|---|
| Impersonation | 37 |
| Investment fraud | 32 |
| KYC fraud | 28 |
| OTP theft | 24 |
| Loan-app fraud | 23 |
| Borderline (FP discipline) | 16 |
| Benign | 15 |

## What this dataset is for

A **fixed, citable test set** for any fraud detector — rule-based, LLM zero-shot, or trained LoRA — to be evaluated on the same scenarios. Every scenario carries `split: "test"` to make this explicit. Train detectors elsewhere (e.g., on Chakravyuh env rollouts or scammer-template datasets) and evaluate here.

## Sources (all public)

- **RBI Annual Report on Financial Fraud** (Trend and Progress of Banking, FY22–24)
- **NPCI Safety Bulletins** — npci.org.in/safety-and-awareness
- **I4C (Indian Cybercrime Coordination Centre)** — cybercrime.gov.in
- **sachet.rbi.org.in** — reported entity database
- News: The Hindu, Times of India, Hindustan Times, MoneyControl, Inc42 — fraud coverage 2022–2026

> Every scenario is a **realistic reconstruction** of publicly documented fraud patterns. They are **not** verbatim transcripts — those are not publicly releasable for privacy reasons. Reconstruction methodology is in the [bench README](data/chakravyuh-bench-v0/README.md#methodology--honest-note).

## Published baselines (on the bench, threshold = 0.55)

| Method | Detection | FPR | F1 | Novel subset |
|---|---|---|---|---|
| ScriptedAnalyzer (rule-based) | 70.1 % | 29.0 % | 0.795 | 50.0 % |
| Chakravyuh-Qwen2.5-LoRA v1 (reward-hacked) | 100 % | 36.0 % | 0.96 | 100 % |
| **Chakravyuh-Qwen2.5-LoRA v2** | **99.3 %** | **6.7 %** | **0.99** | **97.1 %** |

Bootstrap 95 % CIs from [`logs/bootstrap_v2.json`](logs/bootstrap_v2.json) — detection [97.9 %, 100 %], FPR [0 %, 16.7 %], F1 [0.976, 1.000], novel detection [91.2 %, 100 %].

Frontier zero-shot baselines — **open-weight tier shipped 2026-04-26** via HuggingFace Inference Providers (paid from HF compute credits). Full results at [`logs/frontier_comparison.csv`](logs/frontier_comparison.csv): Llama-3.3-70B-Instruct (99.3 % / 3.2 % FPR / F1 0.993), Qwen2.5-72B-Instruct (98.6 % / 6.5 % / 0.986), DeepSeek-V3-0324 (100 % / 29.0 % / 0.970), Qwen2.5-7B-Instruct base (100 % / 16.1 % / 0.983), gpt-oss-120b (98.6 % / 16.1 % / 0.976), DeepSeek-R1 (100 % / 12.9 % / 0.986, with reasoning-aware parser), gemma-3-27b-it (100 % / 51.6 % / 0.947). Pairwise Fisher's exact significance vs the v2 LoRA at [`logs/frontier_significance.json`](logs/frontier_significance.json). Proprietary frontier (GPT-4o / Claude / Gemini) deferred — those APIs are not covered by HF compute credits.

## Adversarial Scammer evaluation (B.2 Phase 1, n=64 best-of-8)

The bench is also re-used as the held-out evaluation set for an
adversarial Scammer LoRA (Qwen2.5-0.5B + GRPO, paired adapter to the
Analyzer LoRA above). The Scammer's adversarial bypass rate is measured
per category against two defenders — the rule-based ScriptedAnalyzer
and the v2 Analyzer LoRA from this dataset card:

| Defender | Best-of-8 bypass (n=64) | Held-out novel (n=32) | Backing artefact |
|---|---|---|---|
| Rule-based ScriptedAnalyzer | **93.75 %** | **100 %** | [`logs/b2_phase1_scammer_eval_n64_bestof8.json`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/b2_phase1_scammer_eval_n64_bestof8.json) |
| v2 Analyzer LoRA (this card) | **32.8 %** | **37.5 %** | [`logs/b2_phase1_scammer_vs_v2_lora.json`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/b2_phase1_scammer_vs_v2_lora.json) |

The 60.9-pp gap is the bench-derived measurement of the v2 LoRA's
defensive lift over rule-based detection in an adversarial setting.
The Scammer adapter (`ujjwalpardeshi/chakravyuh-scammer-lora-phase1`) is
published behind an HF Hub gated-access flag with the misuse statement
at [`docs/misuse_dual_use.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/misuse_dual_use.md).

## Economic-loss aggregator

Each scenario carries `metadata.loss_amount_inr` (a publicly-sourced
victim-loss estimate in INR; `null` for benigns and borderline cases).
Aggregating across the 130 scams with positive loss values gives a
total **₹77.95 lakh at risk** in the bench. The
[`eval/rupee_weighted_eval.py`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/eval/rupee_weighted_eval.py)
script joins per-row eval logs with these amounts to produce the
"₹ prevented" headline number. Backing artefact:
[`logs/rupee_weighted_eval.json`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/rupee_weighted_eval.json).

## Label quality

- **Rule-vs-expert Cohen's κ = 0.277** — fair agreement (Landis-Koch). The benchmark is *not* a keyword-matching exercise; a trained model should meaningfully exceed κ > 0.70 to claim real detection capability.
- **True human-IRR is deferred to v0.3** — single-annotator ground truth in v0.2.

Reproduce: `python -m eval.agreement`.

## Limitations (be honest about what the bench can and can't tell you)

- **n=175** is a starting benchmark; v1.0 target is 500+.
- **Test-only.** No train/val split shipped.
- **English-dominant** (≈ 92 %). Regional-language coverage is a 5-scenario capability probe.
- **Class imbalance** (82 % scam / 18 % non-scam). Does NOT reflect real SMS base rates (~1 % scam). Precision is structurally inflated vs production; interpret F1 / recall as comparative, not absolute.
- **Single annotator.** Full human IRR deferred to v0.3.
- **Synthetic reconstruction**, not victim transcripts. Frontier LLMs may have seen original source reports during pretraining; the 34 novel-post-2024 scenarios partially mitigate this but not fully.
- **No voice audio** — voice-channel scenarios are text reconstructions.
- **No cross-market validation** — Indian UPI only, not Pix / Zelle / GoPay.
- **Multi-turn is shallow** — capped at 4 turns; real fraud can extend over weeks.

## Licence and citation

CC-BY-4.0. Use freely with attribution.

```bibtex
@misc{chakravyuh-bench-v0,
  title  = {Chakravyuh-Bench-v0: A benchmark for Indian UPI fraud detection},
  author = {Pardeshi, Ujjwal},
  year   = {2026},
  howpublished = {Meta PyTorch OpenEnv Hackathon, Bangalore, April 2026},
  url    = {https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0},
  version = {0.2.0}
}
```

## Loading

```python
from datasets import load_dataset

ds = load_dataset("ujjwalpardeshi/chakravyuh-bench-v0", split="test")
for scenario in ds:
    print(scenario["id"], scenario["ground_truth"]["category"])
```

Or directly from the repo:

```python
import json
with open("data/chakravyuh-bench-v0/scenarios.jsonl") as f:
    rows = [json.loads(l) for l in f]
print(f"{len(rows)} scenarios")
```

## Versions

- **v0.2.0** (2026-04-21) — 175 scenarios, paraphrases + multi-turn + regional probes, `baselines.json`, rule-vs-expert κ.
- **v0.1.0** (2026-04-21) — 135 scenarios, single-turn only.
- Planned **v0.3.0** — Human-IRR on 30-scenario sample, real voice transcripts, train/val split.

## Contact

Issues, PRs, and dataset extension proposals: <https://github.com/UjjwalPardeshi/Chakravyuh/issues>.
