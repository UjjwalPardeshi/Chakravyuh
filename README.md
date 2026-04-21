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

# Run tests
pytest tests/ -v
```

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

## Day-1 Baseline Results

100 episodes across mixed victim profiles, scripted agents only:

| Metric | Value |
|---|---|
| Analyzer detection rate | ~38% |
| Scam extraction rate | ~20% |
| Victim refusal rate | ~22% |
| Bank freeze rate | ~8% |
| Avg detection turn | 3.05 |

The scripted Analyzer is intentionally weak — it's the baseline we beat with a LoRA-trained Qwen2.5-7B on Day 2.

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
