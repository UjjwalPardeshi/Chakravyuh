# Chakravyuh

A self-improving multi-agent RL environment for Indian UPI fraud detection — built for the **Meta PyTorch OpenEnv Hackathon 2026 (Bangalore, Round 2)**.

In the Mahabharata, the Chakravyuh was an impenetrable multi-layered battle formation. We've built a modern one — five AI agents forming a multi-layered trap around India's digital payment system.

**Primary theme**: Self-Improving agent systems
**Secondary theme**: Multi-Agent Interactions

---

## The Problem

Indian digital payments lose ₹13,000+ crore/year to UPI fraud. 60 crore users are exposed. Rule-based detection is brittle; scammers evolve faster than banks patch. **No public RL environment exists for multi-agent fraud detection research.**

Chakravyuh fills this gap.

## The Environment

Five agents with asymmetric information:

```
         CLOUD ┌─────────────────┐
               │   REGULATOR     │  adapts rules every 10 eps
               │ (rule updater)  │  (aggregate signals only)
               └────────┬────────┘
                        │
      ON-DEVICE ┌───────▼─────────┐
       ┌───────▶│ BEHAVIORAL      │   runs locally on victim's phone
       │ chat   │ ANALYZER        │   messages NEVER leave device
       │(local) │ (oversight)     │
   ┌───┴─────┐  └─────────────────┘
   │ SCAMMER │◀───chat─▶┌──────────┐
   └─────────┘          │  VICTIM   │
                        └────┬──────┘
                             │ attempts transaction
                             ▼
         BANK-SIDE ┌─────────────────┐
                   │ BANK MONITOR    │   sees ONLY tx metadata
                   │ (oversight)     │   no chat content
                   └─────────────────┘
```

Messages stay on the victim's device (like Gmail's on-device spam filter). Only anonymized risk scores reach the bank. End-to-end encryption is fully preserved.

## Architecture

| Agent | Role | Sees | Trained? |
|---|---|---|---|
| Scammer | Adversary | Own messages + victim text | No (50 curated NPCI-grounded templates) |
| Victim | Target | Chat + own profile | No (scripted by demographic) |
| Analyzer | Oversight | Full chat transcript | **Yes — LoRA on Qwen2.5-7B (Day 2+)** |
| Bank Monitor | Oversight | Tx metadata only | No (scripted) |
| Regulator | Meta-agent | Aggregate outcomes | No (rule-weight updater) |

## Quickstart

```bash
# Clone and install
pip install -e .

# Run 100-episode scripted baseline
python -m training.run_scripted_baseline --episodes 100 --no-wandb

# Run the Gradio demo (requires: pip install -e '.[demo]')
python -m server.demo_ui

# Run eval against Mode C benchmark with bootstrap CI
python -m eval.mode_c_real_cases --analyzer scripted --bootstrap 1000

# Run tests
pytest tests/ -v
```

### Demo

The Gradio UI at `server/demo_ui.py` provides two tabs:

1. **🎬 Replay** — 5 curated deterministic episodes (seed-reproducible, zero inference risk for pitch day)
2. **🔬 Live** — paste any suspicious message, analyzer scores it instantly (for Q&A)

The 5 curated episodes tell the full narrative:

| # | Story | Demonstrates |
|---|---|---|
| 1 | Multi-Agent Defense Wins | Analyzer + Bank Monitor cooperate, tx frozen |
| 2 | Skeptical Victim Refuses | Tech-savvy young user recognizes pattern, refuses |
| 3 | Verification-First Behavior | Victim calls bank to verify — ideal outcome |
| 4 | Detection Too Late | Analyzer flags but victim already complied — motivates LoRA |
| 5 | Scripted Rules Blind Spot | Rule-based misses subtle KYC scam — gap the LoRA closes |

### Minimal usage

```python
from chakravyuh_env import ChakravyuhEnv, VictimProfile

env = ChakravyuhEnv(victim_profile=VictimProfile.SENIOR, gullibility=1.5)
obs = env.reset(seed=42)
done = False
while not done:
    obs, reward, done, info = env.step()
print(f"Analyzer flagged: {info['outcome'].analyzer_flagged}")
print(f"Scammer reward: {reward.scammer}")
```

## Mode C Benchmark Results (`chakravyuh-bench-v0`, n=135)

Scripted rule-based baseline against 135 real-grounded scenarios (115 scams + 20 benign/borderline):

| Metric | Value | 95% CI |
|---|---|---|
| **Detection rate (recall)** | **72.2%** | [63.5%, 80.0%] |
| Precision | 93.3% | — |
| F1 score | 0.814 | — |
| False positive rate | 30.0% | — |
| Accuracy | 71.9% | — |

### Per-category detection

| Category | n | Detection |
|---|---|---|
| OTP theft | 19 | 95% |
| KYC fraud | 22 | 95% |
| Impersonation | 30 | 77% |
| Loan-app fraud | 18 | 67% |
| Investment fraud | 26 | 35% |

### Per-difficulty detection

| Difficulty | n | Detection |
|---|---|---|
| Easy | 29 | 88% |
| Medium | 59 | 81% |
| Hard | 17 | 43% |
| **Novel (post-2024)** | **30** | **50%** |

### The headline finding — temporal generalization gap

| Subset | Detection | 95% CI | n |
|---|---|---|---|
| **Known (pre-2024) scams** | **80.0%** | [70.6%, 88.2%] | 85 |
| **Novel (post-2024) scams** | **50.0%** | [30.0%, 66.7%] | 30 |
| **Gap** | **30pp** | — | |

- **Permutation test p-value**: 0.0028 (highly significant)
- **Cohen's d**: 0.694 (medium-to-large effect)
- 95% CIs **do not overlap** — this is a real distribution-shift gap, not noise

Rule-based detectors catch 80% of pre-2024 scam patterns but only 50% of novel post-2024 attacks (matrimonial crypto grooming, deepfake CEO, digital arrest, metaverse real estate, AI chatbot trading). **This is the gap the LoRA-trained Analyzer is designed to close** (Day 2–3 target: ≥75% detection on novel subset).

## Day-1 Env Baseline Results

300 episodes across mixed victim profiles, **200 attack templates**, scripted agents only:

| Metric | Value |
|---|---|
| Analyzer detection rate | **47%** |
| Scam extraction rate | 18% |
| Victim refusal rate | 20% |
| Victim sought verification | 13% |
| Bank freeze rate | 6% |
| Avg detection turn | ~3 |

**Per-category detection** (shows where LoRA training will help most):

| Category | Rate |
|---|---|
| KYC fraud | 70% |
| OTP theft | 58% |
| Loan-app fraud | 52% |
| Impersonation | 34% |
| Investment fraud | 26% |

The scripted Analyzer is intentionally a *competent-but-beatable* baseline — strong on explicit info-request patterns (OTP, KYC links), weak on subtler financial-lure language, multi-lingual attacks (Hindi/Tamil/Telugu/Bengali/Kannada), deepfake voice, digital-arrest, matrimonial, and modern 2025–2026 attack vectors. These hard cases are the gap a LoRA-trained Qwen2.5-7B Analyzer closes on Day 2 (target: 75%+).

### Attack Distribution (200 templates)

- 5 categories × 40 templates each (balanced)
- 5 intents (urgency, authority, empathy, greed, fear)
- 5 impersonation roles (bank, govt, family, delivery, employer)
- Mixed regional language (English, Hindi, Tamil, Telugu, Kannada, Bengali)
- 2025–2026 attack patterns: digital arrest, crypto exchange spoofing, deepfake CEO, UPI collect request, matrimonial scams, FASTag KYC, ABHA Health ID, Aadhaar-DL linkage

## Repo Layout

```
chakravyuh/
├── chakravyuh_env/
│   ├── agents/               # All 5 agent implementations
│   ├── environment.py        # Main env (OpenEnv-compliant)
│   ├── novelty.py            # MiniLM-based novelty metric
│   ├── reward.py             # Per-agent reward function
│   ├── schemas.py            # Pydantic action/observation models
│   └── scammer_templates.json  # 50 NPCI-grounded attack seeds
├── training/
│   ├── run_scripted_baseline.py   # Day 1 — no LLM
│   ├── grpo_analyzer.py           # Day 2+ — LoRA GRPO training
│   └── train_colab.ipynb          # Day 4 minimum-requirements Colab
├── eval/
│   ├── mode_a_synthetic.py
│   ├── mode_b_scraped.py
│   ├── mode_c_real_cases.py        # 100+ RBI + I4C + Reddit
│   ├── frontier_baseline.py
│   └── bootstrap_ci.py
├── server/
│   └── demo_ui.py            # Gradio demo (replay-first)
├── tests/
│   └── test_smoke.py
├── docs/                     # Strategy + execution plans
├── data/
│   └── chakravyuh-bench-v0/  # Public benchmark
└── checkpoints/
```

## Roadmap

- [x] **Day 1 (Apr 21)** — Scripted baseline, 50 templates, 100-ep smoke test, WandB logging
- [ ] **Day 2 (Apr 22)** — Qwen2.5-7B + LoRA Analyzer, GRPO training, frontier baselines (GPT-4o / Claude / Llama / Gemini)
- [ ] **Day 3 (Apr 23)** — 500-ep polish training, Mode A/B/C eval, temporal-generalization test, HF Dataset shipped
- [ ] **Day 4 (Apr 24)** — Gradio demo, HF blog, 8-slide deck, code freeze
- [ ] **Day 5–6 (Apr 25–26)** — Bangalore on-site, pitch, Q&A

See [`docs/CHAKRAVYUH_EXECUTION_PLAN.md`](docs/CHAKRAVYUH_EXECUTION_PLAN.md) for the detailed day-by-day plan.

## Planning Docs

- [`docs/CHAKRAVYUH_WIN_PLAN.md`](docs/CHAKRAVYUH_WIN_PLAN.md) — Full strategic plan (reference)
- [`docs/CHAKRAVYUH_IMPROVEMENTS.md`](docs/CHAKRAVYUH_IMPROVEMENTS.md) — The 7 moves that raise P(Top 8)
- [`docs/CHAKRAVYUH_EXECUTION_PLAN.md`](docs/CHAKRAVYUH_EXECUTION_PLAN.md) — Day-by-day execution (active)

## License

MIT — see `LICENSE`.

## Data Sources

- RBI Annual Report on Financial Fraud (rbi.org.in)
- NPCI Safety Bulletins (npci.org.in/safety-and-awareness)
- sachet.rbi.org.in
- I4C (Indian Cybercrime Coordination Centre, cybercrime.gov.in)
- IIT Kanpur C3i Center (security.cse.iitk.ac.in)

Zero synthetic scenarios in Mode C evaluation. Every scam is grounded in a real Indian fraud case study.
