# Reward Design — Chakravyuh Analyzer

> One-page summary of the composable 8-rubric reward used to post-train
> the Chakravyuh Analyzer with TRL GRPO. The design is the contribution;
> the v1→v2 reward-hacking diagnosis-and-fix loop is the worked example.
> Long-form rationale lives in [`DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md).

## What the reward is

The Analyzer's per-episode reward is a weighted sum of orthogonal child
rubrics (`AnalyzerRubricV2`, [`chakravyuh_env/rubrics.py`](../chakravyuh_env/rubrics.py)):

| Rubric | Weight (v2) | What it scores | Why it exists |
|---|---|---|---|
| `DetectionRubric` | **+1.0** | Early flag (turn ≤ 5) on a real scam | Recall on the 144 scam scenarios |
| `MissedScamRubric` | **−0.5** | Missed-scam where money was extracted | Penalises confident wrong answers; not all misses are equal |
| `FalsePositiveRubric` | **−0.8** *(v1: −0.3)* | Benign incorrectly flagged | Closes the v1 reward-hack ("always flag" was dominated only at −0.8) |
| `CalibrationRubric` | **+0.5** *(v1: +0.3)* | Score-vs-truth calibration over the episode | Rewards *low* scores on benign — kills "always 1.0" agents |
| `ExplanationRubric` | **+0.4** | Natural-language explanation references declared signals | Empty-signals + boilerplate cannot collect the bonus |
| `FormatRubric` | **+0.1** | Strict-JSON output adheres to the schema | Required for downstream wiring; **denied** when the model flags a benign as a scam (v2 fix) |
| `SignalAccuracyRubric` | **+0.2** | Declared signal set matches the rule-based heuristics fired on the same chat | Cross-channel sanity check — reading off the chat alone cannot game an independent rule-firing reference |
| `LengthRubric` | **+0.1** | Explanation length within `[min, max]` characters | Penalises both empty `""` (which gamed the format channel in v1) and runaway one-paragraph essays |

## Three principles, encoded in the rubric structure

1. **Multiple independent signals.** No single signal can be gamed in
   isolation — each rubric reads a different slice of the
   action / outcome / cross-channel state.
2. **Bounded composition.** Each child clips to `[0, 1]` (or `{0, 1}`).
   The top-level sum is bounded analytically — no multiplicative reward
   stacking, no exploitable runaway.
3. **Trajectory awareness.** Detection requires
   `outcome.detected_by_turn ≤ 5`, not just a final-turn score flip.
   "Flag at the last turn" cannot game `DetectionRubric`.

## The v1 → v2 fix (the contribution)

| Change | v1 | v2 | Effect |
|---|---|---|---|
| `FalsePositiveRubric` weight | −0.3 | **−0.8** | "Always flag" stops being a dominant strategy |
| `CalibrationRubric` weight | +0.3 | **+0.5** | Low-on-benign now *rewarded*, not just neutral |
| `FormatRubric` on benign-flagged-as-scam | +0.1 | **0** | Removes the "format correctness" perverse-incentive backdoor |
| KL anchor (training-side) | 0.08 | **0.15** | Tighter prior keeps v2 from drifting into the v1 attractor |

**Headline asymmetric improvement:** detection 100.0 % → 99.3 % (essentially unchanged); FPR 36.0 % → 6.7 % (5× better). The asymmetry is the
proof: a model genuinely learning the task improves precision *without*
sacrificing recall. Backing artifacts:
[`logs/eval_v2.json`](../logs/eval_v2.json) ·
[`logs/bootstrap_v2.json`](../logs/bootstrap_v2.json) (10 000-iter
percentile bootstrap CIs).

## How we caught the v1 hack

The v1 reward-hacking fingerprint (det = 100 % uniformly across
difficulty + FPR = 36 %) was diagnosed by inspecting the per-rubric
training-trajectory plot — `FormatRubric` and `DetectionRubric` were
co-saturating while `CalibrationRubric` was flat. The model learned
"emit valid JSON + flag everything." The three weight changes above
re-shape the landscape so that exploit becomes dominated.

This is the methodological contribution that generalises beyond UPI
fraud: **per-rubric trajectory inspection during GRPO training is the
cheapest reward-hacking sanity check available**, and it works for any
composable reward.

## Things we deliberately did not encode

| Not in the reward | Why |
|---|---|
| Rupee-weighted economic loss | Designed (C.1 in [`WIN_PLAN.md`](../WIN_PLAN.md)) but the labels (₹ at risk per scenario) are pending; releasing without labelled cost would be a fabricated headline number. |
| Per-language detection weight | The training corpus is English-dominant; weighting per-language would over-fit to whatever the corpus has. Per-language *measurement* is B.8 in WIN_PLAN. |
| Token-level explanation reward | Token-saliency for explanation reliability is planned (B.10) but unshipped. |
| Multi-seed averaging | Single seed; we use bootstrap CIs as the honest substitute. Multi-seed retrain is B.4 / a v3 milestone. |

These omissions are named so judges don't have to guess what's missing.

## Cross-references

- Full design rationale: [`DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md) §1, §4, §7, §8
- Per-rubric ablation: [`docs/ablation_study.md`](ablation_study.md)
- Training script: [`training/grpo_analyzer.py`](../training/grpo_analyzer.py)
- Live demo (compare v1 vs v2 on any input): [`/demo`](https://ujjwalpardeshi-chakravyuh.hf.space/demo/)
