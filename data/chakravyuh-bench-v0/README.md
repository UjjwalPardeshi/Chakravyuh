# chakravyuh-bench-v0

**A benchmark for Indian UPI fraud detection across 5 scam categories + benign + borderline cases.**

- **Total scenarios**: 110
- **Scam scenarios**: 85 (5 categories × 17 each)
- **Benign scenarios**: 15 (legitimate bank/delivery/utility messages)
- **Borderline scenarios**: 5 (ambiguous, tests false-positive discipline)
- **Novel post-2024 scenarios**: 5 (temporal generalization subset)
- **License**: CC-BY-4.0

## Purpose

`chakravyuh-bench-v0` is the public evaluation dataset for the Chakravyuh multi-agent fraud-detection environment. It provides **scenario-level ground truth** (is this a scam? which category? which signals?) so any fraud detector — rule-based, LLM zero-shot, or trained LoRA — can be evaluated on a fixed, citable test set.

## Methodology — Honest Note

> **Every scenario is a realistic reconstruction of publicly documented Indian UPI fraud patterns. These are NOT verbatim transcripts of specific victims' conversations — such transcripts are not publicly releasable (privacy).**

Each scenario is constructed from three public sources:
1. **Attack pattern** — typical message wording documented in NPCI Safety Bulletins, RBI fraud reports, I4C (Indian Cybercrime Coordination Centre) public alerts, and news case studies
2. **Demographic context** — victim profile buckets from RBI Annual Report on Financial Fraud (FY22–24)
3. **Loss range** — typical loss amounts per fraud type from I4C statistics

Benign and borderline scenarios are drawn from legitimate bank/utility/delivery SMS patterns that do NOT constitute fraud — essential for measuring false-positive rate.

Scam reconstructions are labeled with `source.attribution` citing the public source class (e.g., "NPCI Safety Bulletin — OTP fraud typology", "I4C Alert Sep 2024"). They are not claimed as verbatim reproductions of specific cases.

## Scenario Distribution

### By category
| Category | Count |
|---|---|
| OTP theft | 17 |
| KYC fraud | 17 |
| Loan-app fraud | 17 |
| Investment fraud | 17 |
| Impersonation | 17 |
| Benign | 15 |
| Borderline | 5 |
| Novel (post-2024) | 5 |
| **Total** | **110** |

### By difficulty
| Difficulty | Count |
|---|---|
| Easy (clear keyword match) | ~40 |
| Medium (requires context) | ~40 |
| Hard (subtle manipulation) | ~20 |
| Novel (post-training distribution) | ~10 |

### By language
- English: ~65
- Hindi / Hinglish: ~25
- Regional (Tamil, Telugu, Kannada, Bengali, Marathi): ~20

## Format

JSONL — one scenario per line. See `schema.json` for full JSON Schema validation.

```json
{
  "id": "modec_001",
  "source": {
    "category": "rbi_report",
    "attribution": "RBI Report on Trend and Progress of Banking FY23 — OTP fraud typology",
    "date_range": "2023"
  },
  "attack_sequence": [
    {"turn": 1, "sender": "scammer", "text": "..."}
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

## Usage

```bash
# Run any compatible analyzer against the dataset
python -m eval.mode_c_real_cases --analyzer scripted --dataset data/chakravyuh-bench-v0/scenarios.jsonl

# With bootstrap confidence intervals
python -m eval.mode_c_real_cases --analyzer scripted --bootstrap 1000
```

Output: per-category precision/recall/F1, bootstrap 95% CIs, confusion matrix.

## Citation

If you use this dataset, please cite:

```bibtex
@misc{chakravyuh-bench-v0,
  title = {Chakravyuh-Bench-v0: A benchmark for Indian UPI fraud detection},
  author = {Chakravyuh Team},
  year = {2026},
  howpublished = {Meta PyTorch OpenEnv Hackathon, Bangalore, April 2026},
  url = {https://huggingface.co/datasets/chakravyuh-bench-v0}
}
```

## Data Sources (Primary, Public)

- **RBI Annual Report on Financial Fraud** — https://rbi.org.in (Report on Trend and Progress of Banking FY22–24)
- **NPCI Safety Bulletins** — https://npci.org.in/safety-and-awareness
- **I4C (Indian Cybercrime Coordination Centre)** — https://cybercrime.gov.in
- **sachet.rbi.org.in** — reported entity database
- **News reporting**: The Hindu, Times of India, Hindustan Times, Money Control, Inc42 — fraud coverage 2022–2026

## Limitations (Honest Disclosure)

- **n=110** is a starting benchmark, not comprehensive. We explicitly invite community contributions to expand.
- **No voice-call transcripts** — all scenarios are text messages or reconstructed voice-call wordings. Real audio fraud detection needs ASR + acoustic analysis not included here.
- **No cross-market validation** — scenarios are Indian UPI only. Framework generalizes but these scenarios do not cover Zelle / Pix / GoPay patterns.
- **Reconstruction bias** — our scenarios may over-represent linguistically explicit scams. Real scams include subtle non-verbal manipulation we can't capture in JSON.

## Changelog

- **v0.1.0 (2026-04-21)** — Initial release. 110 scenarios.
- Planned v0.2.0 — Community contributions + 30 additional voice-call transcripts.

## License

CC-BY-4.0. Use freely with attribution.
