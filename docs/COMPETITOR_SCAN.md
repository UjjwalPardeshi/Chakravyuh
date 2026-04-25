# Competitor Scan — Meta PyTorch OpenEnv Hackathon 2026

**Compiled:** 2026-04-25 (pre-Day 1 finals)
**Sources:** `huggingface.co/openenv` org, HF Spaces filtered by `openenv` tag, `meta-pytorch/OpenEnv` GitHub PRs/issues (recent), Twitter/X for `#OpenEnvHackathon` `#MetaPyTorch`.
**Caveat:** Public visibility is partial. Some teams may not publish until submission. This list captures the strongest *visible* competition as of compile date.

---

## Top 5 visible competitors

### 1. ComtradeBench — _LLM tool-use reliability under adversarial APIs_
- **Submitter:** `yonghongzhang-io` ([Issue #527](https://github.com/meta-pytorch/OpenEnv/issues/527))
- **Domain:** Data retrieval / API agent reliability (UN Comtrade simulation)
- **Unique angle:** Six weighted scoring dimensions (correctness 30 / completeness 15 / robustness 15 / efficiency 15 / data quality 15 / observability 10), pagination + duplication + rate-limit chaos injection, procedural generation with deterministic seeds, validated with rule-based baseline (96.8/100) and GRPO-trained agents (94.4). No external API dependency.
- **Threat to Chakravyuh:** **Highest.** ComtradeBench is also doing measurement-first GRPO and multi-rubric scoring — they directly contest our "measurement-rigor" differentiator.
- **Where we still win:** They are single-agent. We have multi-agent (Scammer/Victim/Analyzer/Bank/Regulator), regional grounding (Indian UPI), v1→v2 reward-hacking diagnosis as a teaching artifact, and a real-stakes deployment story (₹485 cr UPI fraud loss FY24).

### 2. EmailTriageEnv — _safety-aware classification with progressive difficulty_
- **Submitter:** `Rhushya` ([PR #499](https://github.com/meta-pytorch/OpenEnv/pull/499))
- **Domain:** Business operations / customer-support classification
- **Unique angle:** Three-tier difficulty (easy/medium/hard), shaped rewards with explicit safety penalties against reward hacking, 120-email synthetic dataset, separate scored components (category accuracy + priority + escalation).
- **Threat to Chakravyuh:** **Moderate.** Their explicit "safety penalty against reward hacking" is structurally similar to our v1→v2 fix.
- **Where we still win:** Single-turn vs our multi-turn dialogue. No multi-agent. No diagnosed reward-hacking incident — we have the textbook fingerprint (det=100% / FPR=36% → 99% / 6.7%) backed by `logs/eval_v2.json`.

### 3. Cloud SRE & FinOps Environment
- **Submitter:** `naveenkumar982` ([PR #506](https://github.com/meta-pytorch/OpenEnv/pull/506))
- **Domain:** Cloud operations / DevOps RL
- **Unique angle:** Three operational tasks (Phantom Volume Cleanup, Latency Spike Remediation, Noisy Neighbor), seeded procedural generation, chaos event injection, deterministic grading, multi-step mitigation without collateral damage.
- **Threat to Chakravyuh:** **Moderate.** Strong procedural rigor.
- **Where we still win:** Single-agent. No regional/domain story. Operational utility is interesting but doesn't translate to a "₹X saved per user" headline like ours can.

### 4. Pathway Analysis Environment — _RNA-seq biology agent_
- **Submitter:** `parulsarma-a` ([PR #611](https://github.com/meta-pytorch/OpenEnv/pull/611))
- **Domain:** Computational biology
- **Unique angle:** DESeq2 + Fisher ORA pathway-discovery from RNA-seq data, FastAPI + WebSocket + Gradio architecture, benchmark infrastructure.
- **Threat to Chakravyuh:** **Low.** Specialized scientific domain. Public review notes flag missing type parameters, ground-truth leakage, and a path-traversal issue.
- **Where we still win:** No domain overlap, and our soft-leakage filter (`training/grpo_analyzer.py:_filter_soft_leakage`) is exactly the hygiene gap they're missing.

### 5. Football Play-Calling Environment
- **Submitter:** `afletcherstudent` ([HF Space](https://huggingface.co/spaces/afletcherstudent/football-play-caller))
- **Domain:** Sports analytics / strategic decision-making
- **Unique angle:** Interactive RL play-calling simulator with user-facing UI. Created 2026-03-08.
- **Threat to Chakravyuh:** **Low.** Limited public documentation. Strongest at user interactivity.
- **Where we still win:** Measurement infrastructure, scalable-oversight motivation, multi-agent.

---

## Competitive positioning summary

| Differentiator | ComtradeBench | EmailTriage | Cloud SRE | Pathway | Football | **Chakravyuh** |
|---|---|---|---|---|---|---|
| Multi-agent (≥3) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (5) |
| Regional grounding | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (UPI/IN) |
| v1→v2 reward-hack story | partial | partial | ❌ | ❌ | ❌ | ✅ (5× FPR drop measured) |
| Bootstrap CI on metrics | ? | ❌ | ❌ | ❌ | ❌ | ✅ (`logs/bootstrap_v2.json`) |
| Soft-leakage filter | ? | ❌ | ❌ | ❌ flagged | ❌ | ✅ |
| GRPO + 7B LoRA + frontier-class metric | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Ships with HF Space + adapter on Hub | ? | partial | partial | partial | ✅ | ✅ |

---

## Implications for our pitch

1. **Lead with multi-agent + regional grounding.** Both axes are uncontested in the visible field.
2. **Lean hard on the v1→v2 reward-hacking artifact.** Only EmailTriage gestures at this, and they have no diagnosed incident.
3. **Don't over-invest in measurement-vs-ComtradeBench.** They will match us point-for-point on rigor — beat them on *narrative depth* (real-life UPI scams, ₹485 cr loss, regulator-ready) and *scalable oversight* (5-rubric composable reward).
4. **Be careful with claims that ComtradeBench can verify against us.** If we say "first to apply bootstrap CIs to an OpenEnv submission," they will dispute. Stick with "first multi-agent reward-hacking diagnosis at the OpenEnv hackathon" — that's defensible.

---

## Notes on completeness

Only 5 well-documented competitors found at compile time. Two additional submissions (working titles _Stack Doctor_, _Vc Gemini V0_) surfaced but have insufficient public material to evaluate. We will refresh this list once Day-1 onsite presentations begin and we can see the live demo lineup.
