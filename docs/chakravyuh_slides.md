<!--
Chakravyuh · Pitch deck (4 slides)
====================================
Source markdown — Marp / Slidev / Pandoc compatible.

Render to PDF (Marp CLI):
  npx -y @marp-team/marp-cli docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf

Render to PDF (Pandoc + Beamer):
  pandoc docs/chakravyuh_slides.md -t beamer -o docs/chakravyuh_slides.pdf \
    -V theme=metropolis -V colortheme=seahorse

Notes for the deck:
  - Each slide is separated by a horizontal rule (---).
  - All numbers cite an artifact path. Do not fabricate.
  - 4 slides total — keep it tight.
-->

---
marp: true
theme: default
paginate: true
backgroundColor: "#FFF3E6"
color: "#000000"
header: "Chakravyuh · Multi-Agent Fraud Arena"
footer: "Meta PyTorch OpenEnv Hackathon 2026 · Bangalore"
style: |
  section { font-family: 'Inter', system-ui, sans-serif; padding: 56px 64px; }
  h1 { color: #381932; letter-spacing: -0.5px; }
  h2 { color: #381932; }
  strong { color: #381932; }
  em { color: rgba(0,0,0,0.78); }
  .kpi { display: inline-block; padding: 8px 14px; background: #FFFBF5; border: 1px solid rgba(56,25,50,0.30); border-radius: 999px; margin: 4px 6px 4px 0; font-weight: 700; }
---

# Chakravyuh

### A multi-agent OpenEnv environment for **Indian UPI fraud detection**

We built the only multi-agent fraud-detection benchmark on OpenEnv — and **caught ourselves reward-hacking** the first time we trained on it.

This deck shows what we measured, what we fixed, and what we still need to ship.

---

## 1 · Problem & theme fit

> **Indian digital payments lose ₹13 000+ crore/year to UPI fraud · 60 crore users exposed.**

- Scripted analyzer detection = 50 % on the 34-scenario novel split
  (matrimonial crypto · deepfake CEO · digital arrest · AePS biometric cloning).
- No public RL environment exists for multi-agent fraud-detection research — so we built one.

**Theme coverage** (per JC):

- **Theme #1 — Multi-Agent Interactions** *(primary)*: 5 agents · asymmetric information · two-tier oversight · partial observability
- **Theme #4 — Self-Improvement** *(secondary, honest framing)*: the v1→v2 reward-hacking diagnosis-and-fix loop is self-improvement of the *training pipeline*; we do not claim recursive skill amplification

Real-incident grounding cited in [README](https://github.com/UjjwalPardeshi/Chakravyuh#real-incidents-chakravyuh-is-built-for) (Hyderabad ₹11.17 lakh, Mumbai ₹1 crore, Pan-India AePS ₹2 400 crore).

---

## 2 · Environment & 5-rubric reward design

```
        REGULATOR (meta) ── adapts rule weights from outcomes
                │
ON-DEVICE  → BEHAVIORAL ANALYZER ←  oversight LLM (Qwen2.5-7B + LoRA via GRPO)
            │  sees chat only
   SCAMMER ─┴─ chat ── VICTIM ── attempts transaction
                                 │
            BANK MONITOR ── sees transaction metadata only
```

**Composable rubric system** ([`chakravyuh_env/rubrics.py`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/chakravyuh_env/rubrics.py)):

| Rubric | Weight | Signal |
|---|---|---|
| `DetectionRubric` | **+1.0** | Early flag (turn ≤ 5) on a scam |
| `MissedScamRubric` | **−0.5** | Missed scam + money extracted |
| `FalsePositiveRubric` | **−0.8** *(v2: was −0.3)* | Flagged a benign |
| `CalibrationRubric` | **+0.5** *(v2: was +0.3)* | Score-vs-truth calibration |
| `ExplanationRubric` | **+0.4** | Signal-grounded reasoning |

Per-rubric ablation in [`docs/ablation_study.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/ablation_study.md). Hard-to-game by design (3-principle anti-hacking — see README).

---

## 3 · Results — measured, not predicted

| Metric | v1 *(reward-hacked)* | **v2** *(this submission)* | 95 % CI (v2) |
|---|---|---|---|
| Detection (scam recall, n=144) | 100.0 % | **99.3 %** | [97.9 %, 100 %] |
| **False-positive rate** (n=30) | 36.0 % | **6.7 %** | [0.0 %, 16.7 %] |
| F1 | 0.96 | **0.99** | [0.976, 1.000] |
| Detection on `novel` post-2024 (n=34) | 100 % | 97.1 % | [91.2 %, 100 %] |

<span class="kpi">⏱ scripted: 50 % on novel</span>
<span class="kpi">🎯 v2 LoRA: 97 % on novel</span>
<span class="kpi">📉 FPR 5× better</span>
<span class="kpi">📊 10 000-iter percentile bootstrap</span>

**The asymmetric improvement is the proof.** *Detection unchanged · FPR collapsed* = model learned the task, not the proxy. Backing artifacts: [`logs/eval_v2.json`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/eval_v2.json) · [`logs/bootstrap_v2.json`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/bootstrap_v2.json).

Frontier comparison + SFT-vs-RL controlled experiment + adversarial Scammer self-play are listed honestly as v3 work in [`docs/limitations.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/limitations.md).

---

## 4 · Demo & call to action

- **Live demo**: [`https://ujjwalpardeshi-chakravyuh.hf.space/demo/`](https://ujjwalpardeshi-chakravyuh.hf.space/demo/)
- **Adapter**: [`huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2`](https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2)
- **Bench**: [`huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0)
- **Code**: [`github.com/UjjwalPardeshi/Chakravyuh`](https://github.com/UjjwalPardeshi/Chakravyuh)

```bash
pip install -e '.[llm,eval]'
python -m chakravyuh_env.openenv_client       # client demo
make reproduce                                 # verify headline numbers
```

> *"Chakravyuh is the only multi-agent OpenEnv fraud-detection environment with a documented reward-hacking diagnosis-and-fix loop, grounded in real 2025 Indian UPI fraud cases — submitted with calibrated CIs and an honest list of v3 work."*

— **Try the live demo. Break it. Then beat us on the leaderboard.**
