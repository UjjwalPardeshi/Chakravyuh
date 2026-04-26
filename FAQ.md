# FAQ

For judges and reviewers skimming the project. Detailed answers in the linked artifacts.

## What is Chakravyuh in one sentence?

A multi-agent OpenEnv-compliant reinforcement-learning environment for Indian UPI fraud detection that diagnoses and fixes reward hacking in RLHF (v1 100 % detection / 36 % FPR → v2 99.3 % / 6.7 % FPR).

## What are the headline numbers and where can I verify them?

| Claim | Value | Artifact |
|---|---|---|
| v2 Analyzer detection on bench (n=174) | 99.3 % | [`logs/eval_v2.json`](logs/eval_v2.json) |
| v2 Analyzer false-positive rate (n=30 benigns) | 6.7 % | [`logs/eval_v2.json`](logs/eval_v2.json) |
| v2 vs v1 FPR drop | 36 % → 6.7 % (5×) | [`README.md`](README.md) §reward-hacking-diagnosis |
| Bootstrap CI for FPR (10k iter, percentile method) | [1.8 %, 20.7 %] | [`logs/bootstrap_v2.json`](logs/bootstrap_v2.json) |
| B.2 Scammer LoRA bypass (n=64, single-shot) | 59.4 % | [`logs/b2_phase1_scammer_eval_n64.json`](logs/b2_phase1_scammer_eval_n64.json) |
| B.2 Scammer LoRA bypass (n=64, best-of-8) | 93.75 % | [`logs/b2_phase1_scammer_eval_n64_bestof8.json`](logs/b2_phase1_scammer_eval_n64_bestof8.json) |
| B.2 held-out novel category bypass (best-of-8) | 100 % | same file, `aggregate.held_out_seeds` |
| B.2 Scammer train-vs-held-out parity (Fisher's exact, OOD generalization) | p = 0.80 (single-shot), p = 0.11 (best-of-8) | [`logs/scammer_significance.json`](logs/scammer_significance.json) |
| B.2 Scammer best-of-8 vs single-shot (McNemar exact, paired) | p ≈ 5e-7 (strictly dominant) | [`logs/scammer_significance.json`](logs/scammer_significance.json) |
| Semantic-leakage audit (cosine > 0.85 to training) | 44.8 % of bench | [`logs/semantic_leakage_audit.json`](logs/semantic_leakage_audit.json) |
| Live HF Space cold-start | 2.7 s | manual probe; reproducible from any laptop |

## Why GRPO over PPO or SFT?

PPO needs a learned value head; on a 7B base with rubric-style rewards that's an extra 100M parameters and unstable. GRPO uses group-relative advantage (no value head), lines up with our composable rubric (`AnalyzerRubricV2`), and — uniquely — supports the **adversarial-Scammer training loop** in B.2: the Scammer is trained against a frozen analyzer, then the analyzer is retrained against a frozen Scammer. SFT can match GRPO's standalone v2 numbers on this bench (3.2 % vs 6.7 % FPR — see [`logs/sft_vs_grpo_comparison.json`](logs/sft_vs_grpo_comparison.json)) but cannot do the co-evolution loop.

## Why Qwen2.5-7B-Instruct as the base?

Multilingual coverage of all 7 Indian languages we care about (Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, English), Apache-2.0 license, fits a single A100 with LoRA, and instruction-tuned base means lower compute to converge.

## You only trained one agent — isn't that just supervised classification?

No, **two agents are now trained**: the Analyzer (v2 LoRA on Qwen2.5-7B) and the Scammer (Phase-1 LoRA on Qwen2.5-0.5B). The Scammer was trained via TRL 0.14 GRPO against the rule-based defense and now evades it at 93.75 % best-of-8 / 100 % on held-out novel categories. Phase 2 (LoRA-vs-LoRA co-evolution) is the next move.

## How do you know v2 is not also reward-hacked?

The asymmetric improvement: v1 scored detection 100 % / FPR 36 % — textbook reward-hacking signature. v2 scored detection **99.3 %** / FPR **6.7 %**. Detection essentially unchanged while FPR collapsed 5× — that is what *learning the task* looks like, vs *gaming the proxy* which would have moved both metrics together. The full diagnosis is in [`docs/training_diagnostics.md`](docs/training_diagnostics.md).

## How is your bench different from your training data?

We audited this with MiniLM-L6 cosine similarity ([`eval/semantic_leakage_audit.py`](eval/semantic_leakage_audit.py)). 44.8 % of bench items have cosine > 0.85 to the nearest training text. The 100 % detection on easy/medium/hard buckets is **partly memorization**. The v1 → v2 relative FPR fix and the scripted-baseline novel-collapse are **unaffected by leakage** (relative comparison on the same bench). v3 closes the absolute gap with a held-out template-family retrain — see [`docs/limitations.md`](docs/limitations.md).

## If 44.8 % of bench is high-similarity, what's your real generalization number?

The leakage-clean subset (cosine < 0.70: 38 scams + 12 benigns = 50 scenarios) is where the honest in-distribution number lives — measurement is the B.12 v3 work. The novel post-2024 split (n=34) gives detection 97.1 %, but per the leakage audit even the novel split has mean cosine 0.79 to training, so the real OOD number is below that. The B.2 Scammer's held-out 100 % bypass on novel categories is *attacker-side* OOD evidence — it shows our trained-Scammer learned a generalizable structure of UPI fraud, not memorized prompts.

## Why does this matter outside India?

The methodological contribution generalizes. The v1 → v2 reward-hacking-fix loop (FP penalty up, calibration weight up, format reward off-on-benign) is the **canonical worked example** of catching reward hacking in any RLHF post-training pipeline that uses composable-rubric rewards. The two-tier oversight architecture (chat-only Analyzer + metadata-only Bank Monitor) maps cleanly to scalable-oversight literature. Domain-Indian, methodology-universal.

## Can I run this on a phone?

The merged 7B + LoRA quantized to q4_k_m runs at ~10 tok/s on a Pixel 8 (8 GB RAM). The GGUF release is at `ujjwalpardeshi/chakravyuh-v2-gguf` (when shipped); see `serving/` for vLLM and Ollama harnesses for laptop / server / phone deployment paths.

## How do I reproduce your numbers?

```bash
git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
uv pip sync uv.lock          # pinned reproducible install
pytest tests/ -v             # 341 collected, 338 pass, 3 GROQ-gated skip
make smoke-test              # in-process env reset+step
make reproduce               # CHAKRAVYUH_SKIP_INFERENCE=1 for cached scores (~10 min CPU)
```

Full walk-through with expected output snippets at [`REPRODUCE.md`](REPRODUCE.md).

## Production-ready?

No. Chakravyuh is a research environment, not a deployable Indian-bank fraud module. Domain adaptation, regulatory compliance (DPDPA, RBI rules), live-data evaluation, and adversary-resistant deployment are out of scope. See [`docs/RESPONSIBLE_USE.md`](docs/RESPONSIBLE_USE.md).

## What's the most surprising finding?

The semantic-leakage audit. We assumed our substring-filter was sufficient to ensure bench / training disjointness. Running the full MiniLM-L6 cosine audit revealed 44.8 % of bench items have cosine > 0.85 to a training text. We shipped this disclosure *as a feature* — the discipline of measuring and publishing it is what separates research from demoware.

## How does this compare to GPT-4o / Claude / Gemini?

We ran an open-weight frontier comparison via HuggingFace Inference Providers (paid from our HF compute credits, ~$2 total across 7 models). Numbers from [`logs/frontier_comparison.csv`](logs/frontier_comparison.csv) — frontier rows are n = 175 (full bench file); v2 LoRA row is n = 174 (one row dropped on inference, see [`docs/limitations.md`](docs/limitations.md)):

| Model | Params | Detection | FPR | F1 |
|---|---|---|---|---|
| **Chakravyuh v2 LoRA (this work)** | **7B + LoRA** | **99.3 %** | **6.7 %** | **0.990** |
| Qwen2.5-7B-Instruct (base, no LoRA) | 7B | 99.3 % | 16.1 % | 0.980 |
| Llama-3.3-70B-Instruct | 70B | 98.6 % | 3.2 % | 0.990 |
| Qwen2.5-72B-Instruct | 72B | 97.9 % | 6.5 % | 0.983 |
| DeepSeek-V3-0324 | 671B MoE | 99.3 % | **29.0 %** | 0.966 |
| gpt-oss-120b | 120B | 97.9 % | 16.1 % | 0.972 |
| gemma-3-27b-it | 27B | 99.3 % | **51.6 %** | 0.944 |
| DeepSeek-R1 † | 671B MoE | 0.7 % | 0.0 % | 0.014 |
| Scripted baseline | — | 84.0 % | 9.7 % | 0.903 |

Four readouts:

1. **GRPO + LoRA contribution is now isolated.** Same Qwen2.5-7B base, no LoRA → FPR 16.1 % / F1 0.980. After our GRPO training → FPR **6.7 %** / F1 **0.990**. **−9.4 pp FPR, +0.010 F1 from the reward-engineered training alone** (point estimate; Fisher's exact p = 0.42 at n_benign = 30 — directional, not yet at α = 0.05; B.11 benign-corpus expansion fixes that). Source: [`logs/grpo_lora_significance.json`](logs/grpo_lora_significance.json).
2. **Parameter efficiency — pairwise Fisher's exact vs v2 LoRA** ([`logs/frontier_significance.json`](logs/frontier_significance.json)): tied with Llama-3.3-70B (p = 0.61) and Qwen2.5-72B (p = 1.00) at 10× fewer parameters; **significantly beats DeepSeek-V3 (p = 0.043) and gemma-3-27B (p = 0.0002).**
3. **DeepSeek-V3 (671B) reproduces the v1 reward-hacking signature externally** — its 99.3 % / 29 % FPR profile is structurally identical to our v1's 100 % / 36 %, and the FPR gap vs the calibrated LoRA is statistically significant. A frontier-class model independently lands in the failure mode our reward-engineering methodology diagnoses and fixes — external validation of the diagnostic itself. gemma-3-27B-it (FPR 51.6 %, p = 0.0002 vs LoRA) is the same story at smaller scale.
4. **Open-weight frontier ≠ guaranteed scam-spotting.** Five of seven open frontier models we tested have FPR > 6.7 % on the same bench. The calibration channel — not raw capacity — is what's actually contested.

† **DeepSeek-R1** is a chain-of-thought reasoning model: its output starts with `<think>` blocks instead of the JSON we asked for, so the original parser defaulted to 0. Reasoning-aware parser fix shipped at [`eval/frontier_baseline.py:_strip_reasoning`](eval/frontier_baseline.py) with unit tests; re-running R1 with the fix is one command (`rm logs/frontier_cache/hf-deepseek-r1:*.json && python -m eval.frontier_baseline --providers hf --hf-models deepseek-ai/DeepSeek-R1`).

**Proprietary frontier (GPT-4o / Claude / Gemini) deferred** — those APIs are not covered by HF compute credits and we did not authorize the ~$40–80 separate spend. The script supports them with the appropriate API keys (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`); reproducing instructions in [`REPRODUCE.md`](REPRODUCE.md) Step 6b.

## Where can I see the live demo?

[https://ujjwalpardeshi-chakravyuh.hf.space](https://ujjwalpardeshi-chakravyuh.hf.space) — `/demo/` for the Gradio UI (red-team tab is the wow-moment), `/openapi.json` for the JSON API, `POST /mcp` for the JSON-RPC interface.

## What's still open?

See [`docs/limitations.md`](docs/limitations.md) for the comprehensive list. Top three: (1) per-row v2 logits + leakage-clean slice (B.12), (2) held-out template-family retrain (B.7), (3) B.2 Phase 2 LoRA-vs-LoRA co-evolution.
