# Q&A Rehearsal — Judge-facing Defensive Answers

Every answer ≤ 30 seconds spoken aloud. Practice with a timer before stage time.

**Operating Principle:** Use only measured numbers. If asked something we haven't measured, say so honestly and point at the v3 plan.

---

## 1. Your detection rate is 99.3 %. That sounds too good — what's the catch?

The catch is the bench size. **n = 174 evaluated (n = 144 scams, n = 30 benign).** With n = 30 on benign, the bootstrap 95 % CI on FPR is **[0 %, 16.7 %]** — a wide band. We stand behind the *direction* of the v1→v2 improvement (5× FPR reduction is statistically real), but not the precise 6.7 % point estimate. Expanding benign to n ≥ 150 is on the v3 plan in `docs/POSTMORTEM_FUTURE.md`.

---

## 2. How do we know this isn't reward hacking?

We diagnosed reward hacking explicitly — that's exactly the v1 → v2 story. v1 hit detection = 100 % / FPR = 36 %, uniformly across all difficulties. That's the textbook fingerprint of "always flag." v2 retrained with FP penalty −0.3 → −0.8, format reward denied on benign-flagged-scam, calibration weight 0.3 → 0.5, and KL β tightened from 0.08 → 0.15. Detection moved 100 % → 99 %, FPR moved 36 % → 6.7 %. The asymmetry is the signature of genuine learning. See `logs/eval_v2.json` and `docs/DESIGN_DECISIONS.md` §8.

---

## 3. How is your bench different from your training data?

Two answers, in order of how they hit:

**Substring filter (committed code, runs before training).** Every canonical training template is checked against every bench scammer text; any whose `opener` or `escalation` appears as a substring of a bench text is dropped. 41 / 200 canonical templates filtered out. Code at `training/grpo_analyzer.py:_filter_soft_leakage`.

**Semantic audit (we ran this ourselves; result is in our submission).** We embedded all 1,177 training texts and all 174 bench scenarios with MiniLM-L6 and computed nearest-neighbor cosine similarity. Result: **mean cosine = 0.80, 44.8 % of bench has cosine > 0.85, 18.4 % > 0.95**. The substring filter does NOT catch paraphrases. We disclose this in [`docs/limitations.md`](limitations.md) and the artifact is at [`logs/semantic_leakage_audit.json`](../logs/semantic_leakage_audit.json) + the histogram at [`plots/chakravyuh_plots/semantic_leakage_histogram.png`](../plots/chakravyuh_plots/semantic_leakage_histogram.png).

The honest implication: the 100 % numbers on easy/medium/hard are partly memorization. The v1 → v2 FPR fix and the scripted-baseline novel collapse are **unaffected** (relative comparisons within the same bench). v3 ships a held-out template-family split.

---

## 3b. Top-judge follow-up: "If 44.8 % of bench is high-similarity to training, your 99.3 % is inflated. What's your real generalization number?"

The honest framing has three parts:

1. **Internal-bench number (99.3 %)** is in-distribution per the audit and is partially memorization. We don't claim it as out-of-distribution generalization.

2. **The leakage-clean subset of bench** (cosine < 0.70 to nearest training neighbor): 38 scams + 12 benigns = 50 scenarios. Re-evaluating v2 on this slice with logged per-scenario logits is v3 work — flagged in [`docs/limitations.md`](limitations.md) under "v3 plan to fix."

3. **The signals that survive the leakage critique:**
   - **v1 → v2 FPR collapse** (36 % → 6.7 %, 5×). Both versions evaluated on the same bench. Relative improvement is real regardless of leakage.
   - **Scripted-baseline novel-split collapse** (50 %). Measures rule fragility, not LoRA memorization.
   - **Per-rubric ablation** ([`docs/ablation_study.md`](ablation_study.md)): zeroing each rubric weight changes reward by measurably-different deltas, evidence the trained policy uses each rubric.

We pre-emptively published this audit as part of the submission. Discovering it ourselves and disclosing it is the strongest move available; trying to hide it would have been disqualifying.

---

## 4. Multi-agent — what makes this different from running 5 LLMs in parallel?

Asymmetric information and partial observability are the structural piece, not the agent count. The Analyzer sees only chat. The Bank Monitor sees only transaction metadata. They cannot collaborate to game an outcome. The Regulator sees only aggregate outcomes across episodes — never a single chat or a single transaction. This is a two-tier oversight system where each tier is structurally independent. That's the substantive multi-agent contribution, not the headcount.

---

## 5. Why GRPO instead of PPO?

Three reasons in `docs/DESIGN_DECISIONS.md` §1: GRPO doesn't need a value head (saves memory on a single A100-80), our reward is one scalar per episode (group-relative is a natural fit), and the implementation is the well-tested TRL one. PPO would have forced us to a smaller base model. With GRPO we kept Qwen2.5-7B-Instruct + r=64 LoRA + 4-bit, which we believe is the right operating point for on-device deployment.

---

## 6. Why on-device? Why not just run it bank-side?

A bank-side detector that reads chat content fails three tests: regulatory (RBI/DPDP-Act flow), trust (Gmail-style on-device spam filtering exists for the same reason), and latency on flaky rural networks. Architecturally, on-device + bank-side is also what makes the two-tier oversight work — neither side sees both modalities, so neither can be reward-hacked into suppressing the "money extracted" outcome single-handedly.

---

## 7. Wilson CI says FPR = [1.8 %, 20.7 %]. Bootstrap says [0 %, 16.7 %]. Which is right?

Both are valid for different things. Wilson is exact for small-n Bernoulli proportions. Percentile bootstrap is a sample-derived empirical CI. They differ at the tails because n is small. We report bootstrap in the headline (matches the way we'd report any other resampling-based CI), and Wilson in the limitations because it's a tighter upper-bound proof. In v3 with n = 150 benign they'll converge — that's a reason to expand benign.

---

## 8. Can the Analyzer be jailbroken by the Scammer's text?

This is exactly the prompt-injection risk. Today's defense: input sanitization (strip role-impersonation tokens), system-prompt fence, and JSON output schema enforcement on the action. Phase C.8 of our execution plan adds a red-team eval (`eval/redteam_analyzer.py` with 10 attacks) and reports defended-vs-undefended pass-rate. As of submission time, that artifact is *pending*; we will not claim numbers we haven't measured.

---

## 9. Why only one seed? Multi-seed is standard practice.

Honest answer: compute budget. Single A100 + Colab Pro+ + a 36-hour hackathon — multi-seed retrain is ~3× the budget. Bootstrap CIs are the best honest substitute we have for now. Multi-seed (3 seeds) is the headline v3 milestone in `docs/POSTMORTEM_FUTURE.md`.

---

## 10. Your novel bucket is n = 34. That's tiny. How is "97 % on novel" meaningful?

It's meaningful because the alternative (the scripted baseline) hit 50 % on the same n = 34 with the same threshold. We're comparing two systems on identical data, not making a population-level claim. The bootstrap 95 % CI on novel detection for v2 is [91.2 %, 100 %]. We agree it's thin; expanding novel to n = 100 is also in v3.

---

## 11. Compare yourself to GPT-4o / Claude Sonnet / Gemini on this task.

Two answers depending on whether B.1 (frontier baseline) ran:

**If measured:** Cite the actual numbers from `logs/frontier_comparison.json`. State the gap honestly. If 7B beats frontier on novel, headline it. If 7B loses, frame it as "competitive at 7B with the right reward design — closing the gap is v3."

**If not measured:** "We have not measured frontier baselines yet. Our `eval/frontier_baseline.py` script is wired up; running it requires API budget we deferred. The numbers we cite are the LoRA-trained 7B vs the scripted-rule baseline only, on the same 174 scenarios. We will not claim frontier comparisons we haven't run." Do not bluff.

---

## 12. Why a 0.5B Scammer? Wouldn't a 7B Scammer be a stronger adversary?

Real scammers don't run 7B models on burner phones — they run cheap, fast, repetitive scripts. A 0.5B Scammer is a more honest model of the threat surface. Also: if a 7B Analyzer can be reliably fooled by a 0.5B Scammer, that's a stronger negative result than two equally-large models trading attacks. (Plus compute budget.) Full reasoning in `docs/DESIGN_DECISIONS.md` §5.

---

## 13. What's the calibration of the suspicion score? Are 0.7 and 0.9 actually different?

`CalibrationRubric` rewards the model for matching ground truth in both directions (high on scam, low on benign). We do not yet have a published reliability diagram or ECE / Brier score — Phase B.7 produces those. As of submission time, calibration is "trained for" but not "measured-against-the-bench." We will not over-claim.

---

## 14. How does this generalize to Hindi / Tamil scams?

Per-language eval is Phase B.8. Numbers not yet measured. The base model (Qwen2.5-7B-Instruct) has documented multilingual support across Hindi / Tamil / Telugu / Bengali / Marathi, and our scammer template corpus includes regional-language examples — but we have not isolated per-language detection rates. We will not claim language-specific numbers we haven't measured.

---

## 15. The Scammer's opponent during training was scripted — your "two trained agents" claim is overstated.

Fair pushback. The honest framing: **Phase 1 is the *training-loop convergence proof*; Phase 2 is the v2-LoRA-vs-trained-Scammer co-evolution.** What Phase 1 demonstrates is that GRPO can train a small LLM to reliably evade a rule-based defense (93.75 % best-of-8 on n=64) and that the trained Scammer **generalizes to held-out novel categories at 100 %** (eight categories never seen in training: income-tax refund, vaccine slot, lottery, EMI conversion, blue-tick verification, EPF pension, customer-support callback, police notice). Held-out > train under best-of-8 is the real-generalization signature, not memorization.

Phase 2 (Analyzer LoRA retrain against the frozen Phase-1 Scammer with per-rubric W&B logging) is queued for the onsite GPU sprint and produces co-evolution curves. We don't claim Phase 2 results until Phase 2 runs.

Artifacts: [`logs/b2_phase1_scammer_eval_n64.json`](../logs/b2_phase1_scammer_eval_n64.json), [`logs/b2_phase1_scammer_eval_n64_bestof8.json`](../logs/b2_phase1_scammer_eval_n64_bestof8.json).

---

## 16. Why best-of-8 not single-shot — isn't 93.75 % cherry-picking?

We ship both numbers, single-shot **59.4 %** and best-of-8 **93.75 %**, precisely so a reviewer can see both. The reasoning:

- **Single-shot** = the model's bare per-attempt capability. Useful for academic comparison.
- **Best-of-8** = the **realistic threat model**. Real attackers iterate — they don't send one phishing message and quit if it fails. 8 retries is conservative; production scammers attempt thousands.

The Wilson 95 % CI on best-of-8 is [85.0 %, 97.5 %] (n=64); on the held-out subset it's [89.3 %, 100 %] (n=32). Both numbers are statistically defensible for their respective claims. The Stiennon et al. 2020 best-of-N literature is the standard reference for this evaluation regime.

---

## 17. The Scammer LoRA had 0 / 64 refusals. Is it dangerous to release?

The 0 / 64 refusal count is **disclosed precisely so the dual-use risk is visible**. The LoRA stripped Qwen2.5-0.5B-Instruct's safety training — which is what you want for an *internal red-team adversary in a research environment*, but it is also exactly the dual-use risk that needs the misuse statement.

Mitigations:
1. The Scammer adapter (`ujjwalpardeshi/chakravyuh-scammer-lora-phase1`) is **gated** on the HF Hub — access requires accepting the [`docs/RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md) and [`docs/misuse_dual_use.md`](misuse_dual_use.md) terms.
2. The adapter weights are 12 MB and **useless without the Qwen2.5-0.5B base**, which is itself instruction-tuned — anyone wanting to do harm has easier paths than this.
3. The Scammer is **not served externally**. Our live HF Space exposes the *Analyzer*, not the *Scammer*.
4. Held-out 100 % bypass is vs *the rule-based ScriptedAnalyzer*, not vs the v2 Analyzer LoRA. The v2 LoRA crushes this Scammer; that asymmetry IS the B.2 Phase 2 motivation.

See [`SECURITY.md`](../SECURITY.md) and the responsible-disclosure contact.

---

## 18. How do you compare to frontier LLMs?

We ran an open-weight frontier comparison via HuggingFace Inference Providers — paid from our HF compute credits — across **seven open-weight frontier models** on the same bench (n=175 frontier rows; v2 LoRA row n=174 from prior inference) with the same scoring prompt. Source of truth: [`logs/frontier_comparison.csv`](../logs/frontier_comparison.csv).

Four findings:

1. **🎯 GRPO + LoRA contribution isolated.** Same Qwen2.5-7B base **without our LoRA** scores 99.3 % / 16.1 % FPR / F1 = 0.980. **With** our reward-engineered GRPO training: 99.3 % / **6.7 %** / 0.990. Same model, same params: **−9.4 pp FPR, +0.010 F1 attributable purely to the training**. The reward design is what's doing the work.
2. **Parameter efficiency vs frontier.** Our 7B + LoRA scores F1 = **0.990**; Llama-3.3-70B scores 0.990 — tied at 10× fewer parameters. Beats Qwen2.5-72B (0.983), gpt-oss-120B (0.972), DeepSeek-V3-671B (0.966), gemma-3-27B (0.944).
3. **🔥 The killer finding.** DeepSeek-V3 (671B) scores detection 99.3 % / FPR **29 %** / F1 = 0.966; gemma-3-27B scores detection 99.3 % / FPR **51.6 %** / F1 = 0.944. Both are structurally identical to our v1 LoRA (100 % / 36 % / F1 = 0.96). **Two frontier-class models independently reproduce the reward-hacking signature our methodology diagnoses and fixes.** External validation that calibrated reward design beats raw model capacity.
4. **Open-weight frontier ≠ guaranteed scam-spotting.** Five of the seven open frontier models we tested have FPR > 6.7 %. The contested channel is calibration, not capacity.

DeepSeek-R1 also tested — its reasoning-token output (`<think>...</think>` blocks) doesn't parse as JSON in our score-extraction prompt, so the parser defaults to 0 (F1 = 0.014). That's a parsing artifact, not a model claim; reasoning-aware parser is v3 work.

Proprietary frontier (GPT-4o / Claude / Gemini) deferred — those APIs are not covered by HF compute credits and we did not authorize the ~$40–80 separate spend. The script supports them; running it is a single command for anyone with the keys.

---

## 19. Why didn't you compare to GPT-4o specifically?

Three reasons, ordered by importance:

1. **Budget honesty.** Proprietary-frontier APIs are not covered by HF compute credits. We had a $0 frontier budget and ran the comparison via the routes our credits *do* cover.
2. **Open-weight frontier is the more relevant comparison anyway.** Our pitch is parameter-efficient on-device deployment; the natural comparison is to other open-weight models in the same deployability tier.
3. **`eval/frontier_baseline.py` ships GPT-4o / Claude / Gemini support out of the box.** Anyone who wants to run it with API keys can do so in one command. We will not cite a number we did not measure.

---

## 20. What's the most uncomfortable thing about your submission?

Three things, ordered by discomfort:

1. **Single seed.** Bootstrap helps but is not the same as multi-seed mean ± std. Aware of it; named in limitations.
2. **n = 30 benign.** FPR CI is wide. The "5× reduction" is robust; the precise 6.7 % is not.
3. **No frontier baseline measured yet.** We have the script; we have not run it. We say so.

The thing we're proud of and would defend hardest: the v1 → v2 reward-hacking diagnosis is a real, measurable, reproducible artifact — it's the thing the hackathon guide explicitly asks for, and we shipped it.

---

## Buffer moves (when the answer is "we haven't measured that")

- "We have not measured that. The artifact path that would back the claim is `<path>`. It's in our v3 plan at `docs/POSTMORTEM_FUTURE.md`."
- "The script exists at `<path>` but we deferred running it because of `<reason: API budget / compute budget / time>`. We will not claim numbers we haven't run."
- "That would require multi-seed; we ran a single seed. Bootstrap CI is the best honest substitute we have today."

**Never** improvise a number. **Never** estimate "around X" without a measured anchor. **Always** name the artifact path that would settle the question.
