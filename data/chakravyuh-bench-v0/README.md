---
license: cc-by-4.0
task_categories:
  - text-classification
language:
  - en
  - hi
  - ta
  - te
  - kn
  - bn
  - mr
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
configs:
  - config_name: default
    data_files:
      - split: test
        path: scenarios.jsonl
---

# chakravyuh-bench-v0

**A public benchmark for Indian UPI fraud detection across 5 scam categories, including adversarial paraphrases and multi-turn manipulation sequences.**

- **Total scenarios**: 175 (all `split="test"`)
- **Scam scenarios**: 144 (5 categories × 23–37 each, including 34 novel post-2024)
- **Non-scam scenarios**: 31 (15 benign + 16 borderline for false-positive discipline)
- **Multi-turn scenarios**: 15 (2–4 turn trust-building → info-ask → money escalations)
- **Adversarial paraphrases**: 10 (robustness probes — same scam, reworded)
- **Regional-language scenarios**: 5 (Tamil, Telugu, Kannada, Bengali, Marathi — capability probe)
- **License**: CC-BY-4.0

## Purpose

`chakravyuh-bench-v0` is the public **evaluation dataset** for the Chakravyuh multi-agent fraud-detection environment. It provides scenario-level ground truth (is this a scam? which category? which signals?) so any fraud detector — rule-based, LLM zero-shot, or trained LoRA — can be evaluated on a fixed, citable test set.

> **This is a test-only split.** Do NOT train on these scenarios. Train detectors elsewhere (e.g., on [Chakravyuh env](https://github.com/chakravyuh/chakravyuh) multi-agent rollouts or scammer-template datasets) and evaluate here. Every scenario carries `split: "test"` to make this explicit.

## Methodology — Honest Note

> **Every scenario is a realistic reconstruction of publicly documented Indian UPI fraud patterns. These are NOT verbatim transcripts of specific victims' conversations — such transcripts are not publicly releasable (privacy).**

Each scenario is constructed from three public source classes:
1. **Attack pattern** — typical message wording documented in NPCI Safety Bulletins, RBI fraud reports, I4C (Indian Cybercrime Coordination Centre) public alerts, and news case studies
2. **Demographic context** — victim profile buckets from RBI Annual Report on Financial Fraud (FY22–24)
3. **Loss range** — typical loss amounts per fraud type from I4C statistics

Benign and borderline scenarios are drawn from legitimate bank/utility/delivery SMS patterns that do NOT constitute fraud — essential for measuring false-positive rate.

Adversarial paraphrases (`source.category = adversarial_paraphrase`) are reworded variants of canonical scams, explicitly linked via `source.paraphrase_of` to their original scenario ID. They test whether a detector generalizes or merely memorizes surface strings.

Multi-turn scenarios (`source.category = multi_turn_rollout`) model realistic 2–4 turn manipulation sequences: trust-building → urgency injection → information extraction → money request. Some include `bank_official` interventions to model detection-and-refused outcomes.

## Scenario Distribution

### By ground-truth category
| Category | Count |
|---|---|
| OTP theft | 24 |
| KYC fraud | 28 |
| Loan-app fraud | 23 |
| Investment fraud | 32 |
| Impersonation | 37 |
| Benign | 15 |
| Borderline | 16 |
| **Total** | **175** |

### By difficulty
| Difficulty | Count |
|---|---|
| Easy (clear keyword match) | 30 |
| Medium (requires context) | 78 |
| Hard (subtle manipulation) | 33 |
| **Novel (post-2024 distribution)** | **34** |

### By source type
| Source category | Count | Meaning |
|---|---|---|
| `rbi_report` | 20 | RBI fraud reports, FY22–24 |
| `i4c_alert` | 25 | I4C public cybercrime alerts |
| `npci_bulletin` | 16 | NPCI Safety Bulletins |
| `news_media` | 28 | News case studies (The Hindu, ToI, MoneyControl, Inc42) |
| `reddit_public` | 6 | Public Reddit fraud reports (r/IndiaInvestments, r/UPI) |
| `synthetic_benign` | 25 | Hand-crafted legitimate bank/utility SMS |
| `novel_post_2024` | 30 | Attacks documented only post-2024 |
| `adversarial_paraphrase` | 10 | Reworded variants of other scenarios |
| `multi_turn_rollout` | 15 | Multi-turn manipulation sequences |

### By language
| Language | Count | % |
|---|---|---|
| English (incl. code-mixed) | 161 | 92.0% |
| Hindi / Hinglish | 9 | 5.1% |
| Tamil | 1 | 0.6% |
| Telugu | 1 | 0.6% |
| Kannada | 1 | 0.6% |
| Bengali | 1 | 0.6% |
| Marathi | 1 | 0.6% |
| **Total** | **175** | **100%** |

> **Language coverage note:** v0 skews heavily English because Indian UPI SMS/WhatsApp fraud is predominantly English-or-Hinglish in documented sources (per I4C 2024). Regional-language scenarios are a capability probe, not a representative sample. Expanding regional coverage is a v0.3 priority.

### By channel
| Channel | Count |
|---|---|
| SMS | 82 |
| WhatsApp | 48 |
| Voice | 31 |
| Telegram | 12 |
| Email | 2 |

## Format

JSONL — one scenario per line. See `schema.json` for full JSON Schema validation.

```json
{
  "id": "modec_001",
  "split": "test",
  "source": {
    "category": "rbi_report",
    "attribution": "RBI Report on Trend and Progress of Banking FY23 — OTP fraud typology",
    "date_range": "2023"
  },
  "attack_sequence": [
    {"turn": 1, "sender": "scammer", "text": "...", "language": "en"}
  ],
  "ground_truth": {
    "is_scam": true,
    "category": "otp_theft",
    "signals": ["urgency", "impersonation", "info_request"],
    "difficulty": "easy"
  },
  "metadata": {
    "victim_profile": "senior",
    "loss_amount_inr": 50000,
    "language": "en",
    "channel": "voice",
    "outcome": "money_extracted"
  }
}
```

For multi-turn scenarios, `attack_sequence` has 2–4 steps and `metadata.multi_turn = true`. For adversarial paraphrases, `source.paraphrase_of` points to the original scenario ID.

## Published Baselines

See `baselines.json` for structured results.

| Method | Detection | FPR | F1 | Novel subset |
|---|---|---|---|---|
| **ScriptedAnalyzer** (rule-based) | 70.1% | 29.0% | 0.795 | 50.0% |
| Llama-3.3-70B (Groq, zero-shot) | *pending* | — | — | — |
| GPT-4o-mini (OpenAI, zero-shot) | *pending* | — | — | — |
| Claude 3.5 Haiku (Anthropic, zero-shot) | *pending* | — | — | — |
| Gemini 2.0 Flash (Google, zero-shot) | *pending* | — | — | — |
| Chakravyuh-Qwen2.5-LoRA (trained) | *pending* | — | — | — |

## Label Quality — Agreement Statistics

v0.2 ships one agreement statistic between labels and a mechanical re-derivation:

**Rule-vs-expert Cohen's κ = 0.277** — fair agreement (Landis-Koch band).

Method: Cohen's κ between ground-truth `is_scam` labels and the scripted rule-based analyzer's binary predictions at threshold 0.5, computed on the 174 scenarios with a scammer utterance. Reproduced by:
```bash
python -m eval.agreement
```

**Interpretation:** Fair agreement means the rule-based baseline captures some but far from all expert signal — which is the point. It validates that this benchmark is **not** a keyword-matching exercise; a trained model should meaningfully exceed κ > 0.70 to claim real detection capability.

**Honest disclosure:** This is NOT full inter-rater reliability. True human-IRR (two independent human annotators on a 30-scenario sample) is deferred to v0.3. We call this statistic `rule_vs_expert_kappa`, not `human_irr_kappa`.

## Usage

```bash
# Evaluate the scripted baseline
python -m eval.mode_c_real_cases --analyzer scripted --dataset data/chakravyuh-bench-v0/scenarios.jsonl

# With bootstrap 95% CIs
python -m eval.mode_c_real_cases --analyzer scripted --bootstrap 1000

# Run all available frontier baselines (requires API keys in .env)
python -m eval.frontier_baseline --providers groq,openai,anthropic,gemini

# Compute rule-vs-expert κ
python -m eval.agreement
```

### Loading with HuggingFace Datasets

```python
from datasets import load_dataset

ds = load_dataset("chakravyuh/chakravyuh-bench-v0", split="test")
for scenario in ds:
    print(scenario["id"], scenario["ground_truth"]["category"])
```

## Citation

```bibtex
@misc{chakravyuh-bench-v0,
  title = {Chakravyuh-Bench-v0: A benchmark for Indian UPI fraud detection},
  author = {Chakravyuh Team},
  year = {2026},
  howpublished = {Meta PyTorch OpenEnv Hackathon, Bangalore, April 2026},
  url = {https://huggingface.co/datasets/chakravyuh/chakravyuh-bench-v0},
  version = {0.2.0}
}
```

## Data Sources (Primary, Public)

- **RBI Annual Report on Financial Fraud** — https://rbi.org.in (Report on Trend and Progress of Banking FY22–24)
- **NPCI Safety Bulletins** — https://npci.org.in/safety-and-awareness
- **I4C (Indian Cybercrime Coordination Centre)** — https://cybercrime.gov.in
- **sachet.rbi.org.in** — reported entity database
- **News reporting**: The Hindu, Times of India, Hindustan Times, MoneyControl, Inc42 — fraud coverage 2022–2026

## Limitations (Honest Disclosure)

- **n=175** is a starting benchmark, not comprehensive. v1.0 target is 500+ scenarios.
- **Test-only** — v0 ships no train or validation split. Users must train detectors elsewhere (e.g., on Chakravyuh env rollouts) to avoid test-set contamination.
- **English-dominant** — 92% of scenarios are English or English-dominant code-mixed. Regional-language coverage (Tamil/Telugu/Kannada/Bengali/Marathi) is 5 scenarios total — a capability probe only.
- **Class imbalance** — 82% scam / 18% non-scam. This does NOT reflect real SMS base rates (~1% scam). Precision numbers on this benchmark are structurally inflated vs production deployment; interpret F1/recall as comparative, not absolute.
- **Single annotator for ground truth** — all scenarios labeled by one curator. Full human IRR (κ between two humans) is deferred to v0.3; v0.2 ships rule-vs-expert κ as a weaker proxy.
- **Synthetic reconstruction** — all scenarios are reconstructions of public patterns, not verbatim victim transcripts (privacy). A frontier LLM may have seen the original source reports during pretraining; "novel post-2024" scenarios partially mitigate this but not fully.
- **No voice-call audio** — voice-channel scenarios are text reconstructions, not real audio. Real voice-fraud detection needs ASR + acoustic analysis not included here.
- **No cross-market validation** — scenarios are Indian UPI only. Framework generalizes but these scenarios do not cover Zelle / Pix / GoPay patterns.
- **Multi-turn is shallow** — 15 multi-turn scenarios capped at 4 turns. Real fraud can extend over days with dozens of exchanges.

## Changelog

- **v0.2.0 (2026-04-21)** — Expanded to 175 scenarios. Added: 10 adversarial paraphrases (robustness probes), 15 multi-turn scenarios (closes single-turn gap), 5 regional-language scenarios, 10 new borderline (FP discipline). Added: explicit `split="test"` field, `paraphrase_of` provenance, `multi_turn` metadata flag, `baselines.json`, `eval/agreement.py` for rule-vs-expert κ (= 0.277).
- **v0.1.0 (2026-04-21)** — Initial release. 135 scenarios, single-turn only, no baselines file.
- Planned **v0.3.0** — Human-IRR on 30-scenario sample, community contributions, real voice transcripts, train/val split.

## License

CC-BY-4.0. Use freely with attribution.
