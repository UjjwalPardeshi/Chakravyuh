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

Soft-leakage filter, enforced before training: every training example is min-hash compared to every bench example, and any pair above the similarity threshold is dropped from training. Code is at `training/grpo_analyzer.py:_filter_soft_leakage`. We publish the filter precisely so the claim is checkable. Final training corpus is 619 examples (456 scam + 204 benign templates) — already post-filter.

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

## 15. What's the most uncomfortable thing about your submission?

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
