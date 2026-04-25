# v2 GRPO training diagnostics — what the trainer state actually shows

This is a transparent post-hoc diagnostic on the v2 LoRA training trajectory captured in [`logs/v2_trainer_state.json`](../logs/v2_trainer_state.json). 619 global steps across 1 epoch, 123 log records sampled every 5 steps, captured by TRL's GRPOTrainer.

## Trajectory at 5 evenly-spaced checkpoints

| Step | Loss | Reward (mean) | Reward (std) | KL | Clip ratio (low_mean) |
|---:|---:|---:|---:|---:|---:|
| 5 | −0.0034 | 1.290 | 0.043 | **0.0013** | 0.0000 |
| 155 | +0.0313 | 1.911 | 0.054 | 0.3926 | 0.0000 |
| 305 | +0.0564 | 1.278 | 0.511 | 0.4155 | 0.0000 |
| 455 | +0.0526 | 1.805 | 0.343 | 0.3810 | 0.0000 |
| 615 | +0.0278 | 1.822 | 0.316 | 0.4196 | 0.0000 |

(Numbers above are pulled from `logs/v2_trainer_state.json:log_history` and verified by the reproducer at the bottom.)

## What the numbers actually say

**1. KL diverged very early, then stayed high.** At step 5, KL = 0.0013 (negligible). By step 15, KL = 0.36; it never returns below 0.25 for the rest of training. This is *not* a smooth ramp — the policy distribution moved sharply away from base Qwen2.5-7B-Instruct in the first ~15 steps and oscillated inside the [0.25, 0.45] band thereafter.

**2. Clip ratios remained at zero throughout training.** PPO's importance-sampling clip never engaged — `clip_ratio/low_mean` and `clip_ratio/high_mean` are 0 across all 123 logged steps. This rules out one common reward-hacking signature (clipping flooded out the gradient signal). The KL drift came from the GRPO advantage signal, not from numerical instability.

**3. Reward is highly batch-variable.** Reward(mean) bounces between 1.28 and 2.00 across consecutive 5-step windows. This is the natural per-batch variance from a 175-scenario corpus where different scams admit very different reward regimes (a clear OTP-share scam scores ~2.0; a borderline benign scores ~1.0). It is *not* monotone climb.

**4. Reward variance has localized spikes.** Most steps show reward_std in [0.02, 0.05]; specific steps (40, 305, 595, 615) show reward_std of 0.21–0.51. These spikes correlate with batches that contained one or more benign scenarios — the asymmetric `false_positive=-0.8` weight in the v2 rubric blows the per-batch variance up when a benign appears.

## Honest reading

This is **not** a clean monotonic-improvement curve. It is a fast-divergence trajectory followed by a noisy oscillation around a high-KL plateau. Three readings sit in this data:

1. **Successful task-specific RL post-training.** The high KL is the expected price of teaching Qwen to score in our task's specific format. Bench detection holds at 99.3% with FPR 6.7% — the policy learned the task.
2. **Onset of reward-hacking exploit boundary, masked by KL stability.** GRPO's advantage signal alone could be reward-hacked even with stable KL. The reward variance spikes on benign-containing batches are exactly what an asymmetric reward landscape should produce — that's intended, not a bug. But it's not absolute proof of robustness.
3. **A combination, dominated by (1).** Most likely. The bench numbers post-training are consistent with (1); we cannot distinguish (1) from (1+2) without an external held-out set.

## What we did and didn't do

- **No early-stopping was applied** in v2 training; the run completed all 619 steps.
- **The bench numbers post-training are real**: detection 99.3%, FPR 6.7%, F1 0.99 with `[97.9%, 100%]` and `[0%, 16.7%]` 95% bootstrap CIs (`logs/bootstrap_v2.json`, 10k iterations, seed 42).
- **Per-difficulty novel split shows 97.1%** (33/34); the missed scenario is the natural cap from the corpus.
- **We have not retrained at multiple seeds.** Variance estimates across LoRA initializations are unmeasured. v3 work.

## What v3 will do

Three tactical guards informed by this trajectory:

1. **KL early-stop.** Trigger checkpoint save and stop when `kl > 0.30` for 3 consecutive validation cycles. (Would fire by step ~30 in this trajectory.)
2. **Reward-variance ceiling.** Halt training if `reward_std / reward_mean > 0.20` over a 50-step window.
3. **Per-rubric retrain ablation.** Re-run training with each rubric weight individually set to zero. Currently this is a *post-hoc* eval-time ablation in [`eval/per_rubric_ablation.py`](../eval/per_rubric_ablation.py); the gold-standard composability proof requires retraining.

## Reproducing this analysis

```bash
.venv/bin/python -c "
import json
log = json.load(open('logs/v2_trainer_state.json'))['log_history']
for c in [5, 155, 305, 455, 615]:
    r = next(r for r in log if r.get('step') == c)
    print(f'{r[\"step\"]:>4} | {r[\"loss\"]:+.4f} | {r[\"reward\"]:.3f} | {r[\"reward_std\"]:.3f} | {r[\"kl\"]:.4f} | {r.get(\"clip_ratio/low_mean\", 0):.4f}')
"
```
