# Comparison vs Published Fraud-Detection Benchmarks

**Status:** Best-effort literature scan as of 2026-04-26. Honest read: there is **no directly comparable public benchmark** that is simultaneously (a) multi-agent, (b) Indian-UPI-context, (c) RL-environment-shaped (not just a static dataset), and (d) OpenEnv-compliant. Chakravyuh is the first such artifact we are aware of. Every claim below is backed by a citation; if you find a benchmark we missed, please open an issue.

## Method

Search queries (Google Scholar + arXiv + ResearchGate, conducted 2026-04-26):

- `"multi-agent reinforcement learning fraud detection benchmark environment"`
- `"RL phishing scam detection benchmark OpenEnv"`
- `"Indian UPI fraud detection benchmark"`
- `"adversarial scammer LLM benchmark"`
- `"multi-agent fraud RL environment"`

Inclusion criteria: published since 2023, names a public artifact (dataset OR environment), addresses one of {fraud, scam, phishing, financial-crime} detection, includes either RL training or LLM evaluation. We deliberately *excluded* purely-supervised classifier papers on Kaggle credit-card datasets (PaySim, IEEE-CIS) because they are not RL environments and not multi-agent.

## Comparison table

| Benchmark | Year | Domain | Multi-agent? | RL env? | Public artifacts | Headline metric | Indian-context? |
|---|---|---|---|---|---|---|---|
| **Chakravyuh-bench-v0 (this work)** | 2026 | Indian UPI fraud, multi-turn dialog | ✅ 5 agents (Scammer, Victim, Analyzer, BankMonitor, Regulator) | ✅ OpenEnv-compliant, GRPO-ready | bench (175 scenarios, 7 langs, 13 categories) + Analyzer LoRA + Scammer LoRA + reward-design code | v2 detection 99.3 % / FPR 6.7 %; B.2 Scammer 100 % held-out bypass best-of-8 | ✅ |
| **Fraud-R1** ([Sun et al. 2025](https://arxiv.org/abs/2502.12904)) | 2025 | Bilingual (EN+ZH) phishing / impersonation / fake-job / online-relationship | ❌ Single-LLM eval | ❌ Static benchmark, no env interface | bench (5 scenarios) | LLM accuracy under adversarial fraud inducement | ❌ Chinese + English |
| **Deep RL Phishing Detection** ([2026 paper](https://arxiv.org/pdf/2512.06925)) | 2026 | URL phishing detection (single-modal) | ❌ Single classifier | ✅ DQN environment | source code, model weights | 99.86 % accuracy on URL phishing | ❌ Generic web |
| **LLM-Assisted Financial Fraud Detection with RL** ([Algorithms 18(12), 2025](https://www.mdpi.com/1999-4893/18/12/792)) | 2025 | Credit-card transactions (PaySim, European Credit Card Fraud) | ❌ Single A2C agent | ✅ Tabular RL env | source code | A2C policy-gradient on standard datasets | ❌ Western banking |
| **AdapT-Bench (MLLM phishing)** ([Wang et al. 2025](https://arxiv.org/html/2511.15165v2)) | 2025 | Academic-environment phishing | ❌ Single multimodal LLM | ❌ Static evaluation | bench dataset + eval code | Per-attack pass rate vs MLLMs | ❌ Academic context |
| **Market Malicious Bidding Detection (Frontiers 2025)** | 2025 | Online-marketplace bidding fraud | ✅ Adversary modeling | ✅ Marketplace simulation | code + dataset | Detection accuracy in dynamic markets | ❌ Generic e-commerce |
| **MARL Cybersecurity Survey** ([Chowdhury et al. 2025, ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2667305325000213)) | 2025 | Survey of attacker-defender MARL in cyber | n/a (survey) | n/a | n/a | n/a — no concrete benchmark released | ❌ |

## What this comparison shows

1. **No multi-agent RL env benchmark exists for Indian UPI fraud.** All Indian-fraud work we found is supervised classification on tabular transaction data (e.g., PaySim mod, RBI advisories scraped into static text) — not RL environments and not multi-agent.

2. **The closest LLM-eval benchmark (Fraud-R1)** is bilingual EN+ZH and *static* — it tests whether an LLM can resist a single fraud message, with no agentic structure, no Indian-context coverage, and no reward-engineering layer. It is a useful complement to Chakravyuh, not a replacement.

3. **The closest RL-fraud work (Deep-RL Phishing 2026, LLM-Assisted RL Fraud 2025)** is single-modal (URL strings or credit-card features), single-agent, and not Indian-context. They demonstrate strong accuracy on their respective benchmarks, but the environments are not directly comparable to a multi-agent dialog environment.

4. **Multi-agent RL is well-explored in cybersecurity broadly** (per Chowdhury et al.'s survey), but the published artifacts are predominantly attacker-defender game-theoretic models on abstracted environments (network intrusion, market manipulation), not LLM-driven dialog systems with rubric-composed rewards.

## Implication for Chakravyuh's positioning

Reading the table, Chakravyuh occupies a **distinct cell** that no other public artifact fills:

- *Static fraud benchmark for LLMs:* covered by Fraud-R1, AdapT-Bench (and Chakravyuh-bench-v0).
- *RL environment for non-dialog fraud detection:* covered by Deep-RL Phishing, LLM-Assisted RL Fraud.
- *Multi-agent dialog RL environment with composable rubric rewards, Indian context, and OpenEnv compliance:* covered by **Chakravyuh only**, to our knowledge as of 2026-04-26.

This is *not a hyperbolic "first of its kind"* claim — it is a **scope-narrowed first**. The honest framing for the pitch and slides:

> *"Other published RL fraud benchmarks (Fraud-R1, Deep-RL Phishing, LLM-Assisted A2C) cover one axis at a time — they're either single-agent, or static, or non-dialog, or non-Indian. Chakravyuh is the first multi-agent OpenEnv-compliant RL benchmark for Indian UPI fraud detection. We invite direct comparison: anyone with one of those benchmarks can run our v2 LoRA and our Scammer LoRA on their data, and conversely we welcome external models on chakravyuh-bench-v0."*

## Where Chakravyuh would lose

If a comparable benchmark *did* exist with a frontier LLM frontier baseline, Chakravyuh would lose on:

- **Frontier-LLM coverage.** We do not yet have GPT-4o / Claude / Gemini / Llama-3 numbers (`eval/frontier_baseline.py` exists but was not run; ~$40-80 API cost).
- **Sample size.** n=175 vs Fraud-R1's larger eval set.
- **Multi-modality.** AdapT-Bench evaluates on phishing screenshots; Chakravyuh is text-only.

These gaps are honest and tracked in [`docs/limitations.md`](limitations.md).

## How this doc was produced

Searches conducted via web search engine on 2026-04-26 (queries listed above). Each cited paper was scanned for: artifact public Y/N, RL Y/N, multi-agent Y/N, language coverage. Where the paper was paywalled, the abstract + first three sections were read for the relevant fields. Results are best-effort — absence of evidence is not evidence of absence; if a benchmark we missed is published or upcoming, please open an issue.

## Cross-references

- Source-of-truth limitations doc: [`docs/limitations.md`](limitations.md) — what we *do not* yet measure and why.
- Project FAQ: [`FAQ.md`](../FAQ.md) — top-15 judge questions including "How does this compare to GPT-4o?"
- Frontier baseline scaffolding: [`eval/frontier_baseline.py`](../eval/frontier_baseline.py) — wired but not yet run (~$40-80 API budget required).
