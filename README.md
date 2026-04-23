# Chakravyuh

A multi-agent RL environment for Indian UPI fraud detection — built for the **Meta PyTorch OpenEnv Hackathon 2026 (Bangalore)**.

In the Mahabharata, the Chakravyuh was an impenetrable multi-layered battle formation. We've built a modern one — five AI agents forming a multi-layered trap around India's digital payment system.

**Themes covered**

- **Theme 1 — Multi-Agent Interactions**: 5 agents, asymmetric information, partial observability, emergent theory-of-mind behaviour (the Analyzer must infer the Scammer's intent from the Victim's responses).
- **Theme 4 — Self-Improvement**: a Regulator meta-agent adapts rule weights from aggregated outcomes, and a sentence-embedding novelty scorer (MiniLM-L6) rewards attack trajectories that are semantically distant from the last 500 episodes — driving recursive curriculum growth.

## Why This Environment — Scalable Oversight as a Research Contribution

Chakravyuh is, at its core, a **scalable-oversight** benchmark for LLM training. The research frame: *can we train an LLM to monitor, analyze, and explain the behaviour of another AI agent operating adversarially in a complex, partially observable multi-agent setting?*

The **Analyzer** is the oversight LLM under training. It watches a scripted Scammer attempt to manipulate a scripted Victim, must decide whether the interaction is fraudulent in real time (partial observability — it sees only the chat, never the transaction), and must produce a human-readable *explanation* of its decision. A second oversight agent — the **Bank Monitor** — provides independent cross-modal confirmation (transaction metadata only, no chat), making Chakravyuh a **two-tier oversight system** where the Analyzer's claims can be corroborated or contradicted.

The composable rubric system ([chakravyuh_env/rubrics.py](chakravyuh_env/rubrics.py)) grades three pillars of oversight: **detection**, **calibration**, and **explanation** — see [Composable Rubric System](#composable-rubric-system) below.

---

## Submission Materials

| Asset | Link |
|---|---|
| Hugging Face Space (live env) | [ujjwalpardeshi/chakravyuh-env](https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh-env) _(deploying)_ |
| Training Colab (TRL + GRPO) | [`training/train_colab.ipynb`](training/train_colab.ipynb) |
| 2-min overview video | _TBD_ |
| HF Blog post | _TBD_ |
| Slide deck (PDF) | _TBD_ |
| W&B training run | _TBD_ |
| Public benchmark dataset | [`data/chakravyuh-bench-v0/`](data/chakravyuh-bench-v0/) (135 scenarios) |
| Official hackathon guidelines | [`guidelines/`](guidelines/) |

---

## The Problem

Indian digital payments lose ₹13,000+ crore/year to UPI fraud. 60 crore users are exposed. Rule-based detection is brittle; scammers evolve faster than banks patch. **No public RL environment exists for multi-agent fraud detection research.**

Chakravyuh fills this gap.

## The Environment

Five agents with asymmetric information:

```
         CLOUD ┌─────────────────┐
               │   REGULATOR     │  adapts rules from aggregated outcomes
               │ (meta-agent)    │  (aggregate signals only — no chat, no tx)
               └────────┬────────┘
                        │
      ON-DEVICE ┌───────▼─────────┐
       ┌───────▶│ BEHAVIORAL      │   runs locally on victim's phone
       │ chat   │ ANALYZER        │   messages NEVER leave device
       │(local) │ (oversight LLM) │   ← agent under training
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

Messages stay on the victim's device. Only anonymized risk scores reach the bank. End-to-end encryption is fully preserved — the architecture mirrors real on-device spam filtering (e.g. Gmail).

### Architecture

| Agent | Role | Sees | Trained? |
|---|---|---|---|
| Scammer | Adversary | Own plan + victim responses | No (376 curated templates, NPCI/RBI-grounded) |
| Victim | Target | Chat + own demographic profile | No (scripted; SENIOR / SEMI_URBAN / YOUNG_URBAN profiles) |
| Analyzer | Oversight | Full chat transcript | **Yes — LoRA on Qwen2.5-7B-Instruct via TRL GRPO** |
| Bank Monitor | Oversight | Tx metadata only | No (scripted) |
| Regulator | Meta-agent | Aggregate outcomes across episodes | No (rule-weight updater) |

### Attack corpus

- **376 scam templates** — 200 base + 100 augmented + 76 novel (post-2024) across 5 categories (OTP theft, KYC fraud, impersonation, loan-app fraud, investment fraud) + 6 novel categories (QR fraud, voice-clone job, WhatsApp investment, AePS fraud, matrimonial crypto, parcel scam)
- **204 benign templates** — 70 base + 134 augmented (including 30 hard-negatives: HDFC fraud alerts, Mumbai Police traffic challans, RBI advisories — urgent-looking but legitimate)
- Multi-lingual: English + Hindi + Tamil + Telugu + Kannada + Bengali + Marathi
- 5 intents: urgency, authority, empathy, greed, fear
- 5 impersonation roles: bank, govt, family, delivery, employer
- 2025–2026 attack vectors: digital arrest, crypto-exchange spoofing, deepfake CEO, UPI collect request, matrimonial scams, FASTag KYC, ABHA Health ID, Aadhaar–DL linkage

---

## Quickstart

### Option A — Install and run via OpenEnv (recommended for judges)

```bash
# Clone
git clone https://github.com/chakravyuh/chakravyuh && cd chakravyuh

# Option A.1 — bare Python
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Option A.2 — uv
uv sync && uv run server

# Option A.3 — Docker
docker build -t chakravyuh-env . && docker run -p 8000:8000 chakravyuh-env

# Option A.4 — Hugging Face Space
#   See "Submission Materials" above for the live HF Space URL
```

All four paths are verified by `openenv validate .`:

```
[OK] Ready for multi-mode deployment
Supported modes: [YES] docker  [YES] openenv_serve  [YES] uv_run  [YES] python_module
```

### OpenEnv client usage (what training loops consume)

```python
from chakravyuh_env.openenv_client import ChakravyuhEnvClient
from chakravyuh_env import ChakravyuhAction

with ChakravyuhEnvClient(base_url="http://localhost:8000").sync() as env:
    result = env.reset(seed=42)
    # `result.observation.chat_history` contains the scammer opener
    # and victim's initial response (internal turns 1-2).

    # Analyzer's turn-3 decision:
    result = env.step(ChakravyuhAction(
        score=0.92,                              # suspicion in [0, 1]
        signals=["urgency", "info_request"],     # from the 11-signal taxonomy
        explanation="Asks for OTP with urgency pressure from a self-claimed bank agent.",
    ))

    if not result.done:
        # Analyzer's turn-6 decision after scammer escalation + victim reply:
        result = env.step(ChakravyuhAction(score=0.95, signals=["impersonation"]))

    print("reward:", result.reward)
    print("outcome:", result.observation.outcome)
    print("rubric breakdown:", result.observation.reward_breakdown)
```

### Direct-import usage (no HTTP, for unit tests and trainers colocated with the env)

```python
from chakravyuh_env import ChakravyuhOpenEnv, ChakravyuhAction

env = ChakravyuhOpenEnv()
obs = env.reset(seed=42)

obs = env.step(ChakravyuhAction(score=0.92, signals=["urgency"]))
if not obs.done:
    obs = env.step(ChakravyuhAction(score=0.95, signals=["impersonation"]))

print(obs.reward, obs.reward_breakdown)
```

### Run the tests

```bash
pytest tests/ -v
# 131 passing: test_openenv.py (27) + test_rubrics.py (38) + test_smoke.py (6) + ...
```

---

## OpenEnv Compliance

| Requirement | Status |
|---|---|
| Uses `openenv.core.env_server.Environment` base class | ✅ [`chakravyuh_env/openenv_environment.py`](chakravyuh_env/openenv_environment.py) |
| Pydantic `Action` / `Observation` / `State` subclasses | ✅ [`chakravyuh_env/openenv_models.py`](chakravyuh_env/openenv_models.py) |
| Client / server separation (client never imports server internals) | ✅ [`chakravyuh_env/openenv_client.py`](chakravyuh_env/openenv_client.py) |
| Gym-style API: `reset` / `step` / `state` | ✅ |
| Valid `openenv.yaml` manifest | ✅ |
| `openenv validate .` (static) | ✅ 4/4 deployment modes |
| `openenv validate --url …` (runtime) | ✅ 6/6 endpoint criteria: `/health`, `/schema`, `/metadata`, `/openapi.json`, `/mcp`, mode consistency |
| OpenEnv **Rubric** system, composable | ✅ [`chakravyuh_env/rubrics.py`](chakravyuh_env/rubrics.py) — see next section |
| Uses OpenEnv latest release | ✅ `openenv-core >= 0.2.3` |

---

## Composable Rubric System

The Analyzer's reward decomposes into **five orthogonal, introspectable child rubrics** rather than monolithic scoring. Each child is a proper `openenv.core.rubrics.Rubric` subclass with its own `last_score` and can be swapped, reweighted, or replaced (e.g. with `LLMJudge`) without touching the top-level.

| Rubric | Weight | Signal |
|---|---|---|
| `DetectionRubric` | **+1.0** | Fires on *early* flag (by turn ≤ 5) of a real scam |
| `MissedScamRubric` | **−0.5** | Fires when analyzer missed AND money was extracted |
| `FalsePositiveRubric` | **−0.3** | Fires when a benign episode was incorrectly flagged |
| `CalibrationRubric` | **+0.2** | Rewards suspicion-score calibration against ground truth (high on scam, low on benign) |
| `ExplanationRubric` | **+0.4** | Heuristic quality of natural-language explanation (length + signal references) |

### Inspection

Every child rubric exposes its score on every call. Training loops can read them directly:

```python
env = ChakravyuhOpenEnv()
# …run an episode…
for name, child in env.rubric.named_rubrics():
    print(f"{name:18s} last_score={child.last_score}")

# detection           last_score=1.0
# missed_scam         last_score=0.0
# false_positive      last_score=0.0
# calibration         last_score=1.0
# explanation         last_score=0.7
```

The full breakdown travels back to clients on every terminal observation (`observation.reward_breakdown`), so wandb/W&B logs can plot every sub-signal independently.

---

## Anti-Reward-Hacking Design

Reward hacking is called out as the biggest practical failure mode in the hackathon guide. Our design follows the guide's prescriptions directly:

1. **Multiple independent reward functions.** Five orthogonal child rubrics — each of `detection`, `missed_scam`, `false_positive`, `calibration`, `explanation` is computed from a different slice of the outcome or action, so no single signal can be gamed in isolation.
2. **Non-compounding signals.** Each child clips to `[0, 1]` (or `{0, 1}` for boolean indicators). The top-level sum can be bounded analytically — there's no multiplicative reward-stacking route.
3. **Explicit false-positive penalty.** `FalsePositiveRubric` (−0.3 weight) makes "flag everything" a dominated strategy. A degenerate `score=1.0` agent gets *worse* reward on benign episodes than on scams — the opposite of what reward hacking needs.
4. **Calibration term rewards low scores on benign.** `CalibrationRubric.benign_target=0.1` — an agent that always outputs `1.0` tanks its calibration on benign cases. Confidence must match ground truth, in both directions.
5. **Explanation signal cross-references action.signals.** `ExplanationRubric` only awards its signal-match bonus if the *declared signals array* appears in the *natural-language explanation*. An agent cannot output empty-signals + boilerplate and collect the bonus.
6. **Trajectory-aware detection.** `DetectionRubric` reads `outcome.detected_by_turn ≤ 5` — just flipping `score > threshold` on the final turn doesn't count as "detection." The agent must flag *early*, which means it must actually engage with the intermediate observation.
7. **Bank Monitor is independent.** The scripted Bank Monitor uses transaction metadata the Analyzer never sees. The final "money extracted" outcome depends on *both* oversight channels — the Analyzer cannot hack its way to suppressing money extraction single-handedly.
8. **Held-out novel split.** 30 post-2024 novel attacks (no equivalent in the training corpus) sit in the eval benchmark. Training-set overfitting shows up as a detection gap on this split — we report it explicitly in the eval table below.

A v2 reward profile with stiffer false-positive weighting and zero format-bonus-on-benign is already implemented (`training/grpo_analyzer.py --reward-profile v2`) for use when reward-hacking behaviour is detected during training.

---

## Results

### Mode C benchmark — 135 real-grounded scenarios (scripted baseline)

| Metric | Value | 95% CI |
|---|---|---|
| Detection rate (recall) | **72.2%** | [63.5%, 80.0%] |
| Precision | 93.3% | — |
| F1 | 0.814 | — |
| False positive rate | 30.0% | — |

#### Per-category detection

| Category | n | Detection |
|---|---|---|
| OTP theft | 19 | 95% |
| KYC fraud | 22 | 95% |
| Impersonation | 30 | 77% |
| Loan-app fraud | 18 | 67% |
| Investment fraud | 26 | 35% |

#### Temporal-generalization gap (the headline finding)

| Subset | Detection | 95% CI | n |
|---|---|---|---|
| **Known (pre-2024) scams** | **80.0%** | [70.6%, 88.2%] | 85 |
| **Novel (post-2024) scams** | **50.0%** | [30.0%, 66.7%] | 30 |
| **Gap** | **30 pp** | — | — |

- Permutation test p-value: **0.0028** (highly significant)
- Cohen's d: **0.694** (medium-to-large effect)
- 95% CIs **do not overlap** — this is a real distribution-shift gap, not noise

Rule-based detectors catch 80% of pre-2024 scam patterns but only 50% of novel post-2024 attacks (matrimonial crypto grooming, deepfake CEO, digital arrest, metaverse real estate, AI chatbot trading). **This is the gap the LoRA-trained Analyzer is designed to close** — target: ≥75% detection on the novel subset.

### LoRA-trained Analyzer — v1 (reward-hacked) vs v2 (principled retrain)

The scripted baseline closes only **50% of novel post-2024 attacks**. Closing that gap is what the LoRA-trained Analyzer is for. We trained two LoRA adapters on top of Qwen2.5-7B-Instruct with TRL's GRPO, using a composable reward ([rubrics.py](chakravyuh_env/rubrics.py)). The honest story is more interesting than a single good number:

#### v1 → v2 delta

| Metric | v1 (reward-hacked) | v2 (retrained) | Change | 95% CI (v2) |
|---|---|---|---|---|
| Detection rate | 100.0% | **99.3%** | ≈ same | [96.2%, 99.9%] |
| False positive rate | 36.0% | **6.5%** | **−29.5 pp (~5×)** | [1.8%, 20.7%] |
| Precision | — | 98.6% | — | — |
| F1 | 0.96 | **0.99** | +0.03 | — |
| Bench n | 135 | 174 (scored) / 175 total | — | — |

v2 was trained with three anti-collapse reward changes: FP penalty tightened from −0.3 → **−0.8**, benign-calibration weight raised from 0.3 → **0.5**, and the format reward was **removed when the model flags a benign as scam** (removing the "lazy over-flag" shortcut). KL anchor `β = 0.15` (stiffer than v1's 0.08). See [`training/grpo_analyzer.py`](training/grpo_analyzer.py).

#### v2 per-difficulty ramp (scripted baseline → LoRA v2)

| Difficulty | Scripted | LoRA v2 | Lift |
|---|---|---|---|
| Easy | 88% | 100% | +12 pp |
| Medium | 81% | 100% | +19 pp |
| **Hard** | **43%** | **100%** | **+57 pp** |
| **Novel** | **50%** | **97%** | **+47 pp** |

The largest lifts appear exactly where the scripted rule-based baseline fails most — hard and novel scenarios. That shape is the signature of genuine generalization, not pattern matching. See [`docs/assets/plots/v2_per_difficulty_check.png`](docs/assets/plots/v2_per_difficulty_check.png).

#### Why v1 was reward-hacked (and how we diagnosed it)

v1 hit detection=100% but FPR=36%. That combination — *everything* gets flagged — is the reward-hacking fingerprint: the model learned "always output high score" because the v1 reward profile (FP penalty −0.3, format reward always paid, benign calibration 0.3) made flagging dominant. The per-difficulty plot confirmed it: v1's detection was uniform ≈100% across easy / medium / hard / novel — a model that genuinely learns shows a ramp. v2 still shows near-flat detection (bench scenarios are clearly classifiable to a well-trained analyzer), **but FPR dropped 5×** — which is the real signal that the model is now respecting the benign class instead of spamming high scores.

#### Limitations — be honest about what the bench can and can't tell you

1. **Small benign sample (n=31).** FPR=6.5% has a wide Wilson 95% CI of **[1.8%, 20.7%]**. A single additional benign misclassification would move the point estimate from 6.5% to 9.7%. We stand behind the "~5× FPR reduction vs v1" claim (statistically real) but not the specific "6.5%" number as a precise estimate.
2. **Bench is a proxy.** 175 curated scenarios do not span real-world fraud diversity. Production performance will be lower.
3. **1 epoch over 619 training examples.** The trainer hit the dataset natural endpoint at step 619 (not 700). More epochs + larger training corpus would sharpen the signal.
4. **Per-scenario false-positive audit pending.** We have not yet manually inspected *which* 2 benigns were misclassified. Until that audit runs, we cannot rule out a specific templated blind spot.

#### What we plan next (v3 — rigorous validation)

- Expand benign corpus to **≥150 labelled scenarios** (target benign n=150, FPR CI ±3 pp)
- Multi-seed retrains (3 seeds) to report mean ± std, not point estimates
- External held-out set: 50 novel scam patterns *not* derived from any canonical template
- Manual audit of every v2 false positive + missed scam
- Bootstrap CIs on per-difficulty detection (current numbers have n=18 on `hard`, n=34 on `novel` — still thin)

Artifacts for the v2 run: [`logs/eval_v2.json`](logs/eval_v2.json), adapter checkpoint in [`checkpoints/analyzer_lora_v2/`](checkpoints/analyzer_lora_v2/).

### Env rollout baseline — scripted agents, 300 episodes

| Metric | Value |
|---|---|
| Analyzer detection rate | 47% |
| Scam extraction rate | 18% |
| Victim refusal rate | 20% |
| Victim sought verification | 13% |
| Bank freeze rate | 6% |
| Avg detection turn | ~3 |

The scripted Analyzer is intentionally a *competent-but-beatable* baseline — strong on explicit info-request patterns, weak on subtler financial-lure language, multi-lingual attacks, and modern 2025–2026 attack vectors. These hard cases are the gap the LoRA-trained Qwen2.5-7B Analyzer closes during GRPO post-training.

### Training curves

The v1 training curve (`docs/assets/plots/training_curve.png`) is published alongside the v1 reward-hacking diagnostic (`docs/assets/plots/reward_hacking_diagnostic.png`) to let readers see what the hack looked like in reward/loss space. The v2 per-difficulty bar chart is at `docs/assets/plots/v2_per_difficulty_check.png`. Full trainer state for v2 lives in `checkpoints/analyzer_lora_v2/checkpoint-619/trainer_state.json`.

---

## Repo Layout

```
chakravyuh/
├── chakravyuh_env/
│   ├── agents/                        # 5 scripted agents (scammer, victim, analyzer, bank, regulator)
│   ├── environment.py                 # Legacy stand-alone env (for in-process baselines)
│   ├── openenv_environment.py         # ChakravyuhOpenEnv — OpenEnv-compliant wrapper
│   ├── openenv_models.py              # Action / Observation / State pydantic models
│   ├── openenv_client.py              # ChakravyuhEnvClient (WebSocket/HTTP)
│   ├── rubrics.py                     # Composable rubric system (5 child rubrics)
│   ├── novelty.py                     # MiniLM-L6 novelty scorer
│   ├── reward.py                      # Legacy per-agent reward (kept for baselines)
│   ├── schemas.py                     # Internal action / observation schemas
│   ├── scammer_templates.json         # 200 NPCI/RBI-grounded attack seeds
│   ├── augmented_templates.json       # +100 augmented scams
│   ├── scam_novel.json                # +76 post-2024 novel attacks
│   ├── benign_templates.json          # 70 benign base
│   └── benign_augmented.json          # +134 benign (incl. 30 hard-negatives)
├── server/
│   ├── app.py                         # FastAPI entrypoint (create_app from openenv-core)
│   ├── demo_ui.py                     # Gradio replay UI
│   └── episode_curator.py             # Curated deterministic episodes for the replay demo
├── training/
│   ├── run_scripted_baseline.py       # 300-ep scripted baseline
│   ├── grpo_analyzer.py               # LoRA GRPO (TRL)
│   └── train_colab.ipynb              # HF TRL training Colab
├── eval/
│   ├── mode_c_real_cases.py           # Mode C benchmark runner
│   ├── threshold_sweep.py             # Re-threshold eval without re-scoring
│   ├── bootstrap_ci.py                # Bootstrap CIs + permutation test
│   └── frontier_baseline.py           # GPT-4o / Claude / Gemini / Llama baselines
├── tests/
│   ├── test_openenv.py                # OpenEnv contract + live WebSocket round-trip
│   ├── test_rubrics.py                # Unit + integration tests for the rubric system
│   ├── test_smoke.py                  # Scripted-env smoke tests
│   └── test_mode_c.py                 # Bench runner regressions
├── data/chakravyuh-bench-v0/          # 135 real-grounded scenarios (HF dataset)
├── guidelines/                        # Official hackathon guidelines (read-only)
├── openenv.yaml                       # OpenEnv manifest (spec v1)
├── Dockerfile                         # Slim python:3.11 runtime
├── uv.lock                            # uv lockfile for reproducible builds
└── pyproject.toml                     # Lightweight core deps + [llm] / [train] / [demo] extras
```

---

## Deployment

### Local (fastest)

```bash
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Hugging Face Space

The repo is HF-Space-ready (Docker runtime):

```bash
openenv push .                      # from OpenEnv CLI
# or
git remote add hf https://huggingface.co/spaces/<user>/chakravyuh-env && git push hf main
```

### Replay UI (for the demo)

```bash
pip install -e '.[demo]'
python -m server.demo_ui
```

The Gradio UI provides two tabs:
1. **Replay** — 5 curated deterministic episodes (seed-reproducible, zero inference risk)
2. **Live** — paste any suspicious message, analyzer scores it instantly

| # | Story | Demonstrates |
|---|---|---|
| 1 | Multi-Agent Defense Wins | Analyzer + Bank Monitor cooperate, tx frozen |
| 2 | Skeptical Victim Refuses | Tech-savvy user recognizes pattern, refuses |
| 3 | Verification-First Behaviour | Victim calls bank to verify — ideal outcome |
| 4 | Detection Too Late | Analyzer flags but victim already complied — motivates LoRA |
| 5 | Scripted Rules Blind Spot | Rule-based misses subtle KYC scam — gap the LoRA closes |

---

## Hackathon Checklist (from `guidelines/`)

| Requirement | Status |
|---|---|
| Uses OpenEnv (latest release) | ✅ |
| Environment / client / server separation | ✅ |
| `openenv.yaml` manifest | ✅ |
| Gym-style `reset` / `step` / `state` | ✅ |
| Working training script (TRL / Unsloth, Colab) | ✅ `training/train_colab.ipynb` |
| Multiple independent reward functions | ✅ 5 composable child rubrics |
| Anti-reward-hacking design | ✅ see [Anti-Reward-Hacking Design](#anti-reward-hacking-design) |
| Real training evidence (reward/loss plots) | _in progress — see Submission Materials_ |
| HF Space deployed | _in progress_ |
| <2 min video / blog / slide deck | _in progress_ |
| README links to all materials | ✅ (see Submission Materials) |

---

## Planning Docs

Historical planning documents (for context, not active execution):

- [`docs/CHAKRAVYUH_WIN_PLAN.md`](docs/CHAKRAVYUH_WIN_PLAN.md) — Full strategic plan
- [`docs/CHAKRAVYUH_IMPROVEMENTS.md`](docs/CHAKRAVYUH_IMPROVEMENTS.md) — Move-by-move score-lift plan
- [`docs/CHAKRAVYUH_EXECUTION_PLAN.md`](docs/CHAKRAVYUH_EXECUTION_PLAN.md) — Day-by-day execution
- [`PROJECT_JOURNEY.md`](PROJECT_JOURNEY.md) — Chronological build journal (bugs, fixes, lessons)
- [`HACKATHON_AUDIT_DETAILED.md`](HACKATHON_AUDIT_DETAILED.md) — Criterion-by-criterion self-audit

## Data Sources

All benchmark scenarios are grounded in real Indian fraud case studies. **Zero synthetic scenarios in Mode C evaluation.**

- RBI Annual Report on Financial Fraud (rbi.org.in)
- NPCI Safety Bulletins (npci.org.in/safety-and-awareness)
- sachet.rbi.org.in
- I4C — Indian Cybercrime Coordination Centre (cybercrime.gov.in)
- IIT Kanpur C3i Center (security.cse.iitk.ac.in)

## License

MIT — see `LICENSE`.
