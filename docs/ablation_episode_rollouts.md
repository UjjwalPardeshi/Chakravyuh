# Per-rubric ablation study

Post-hoc, eval-time sensitivity analysis. Each rubric weight is zeroed in turn, and the resulting change in average composite reward across the corpus is reported. **This is not a retrain ablation** — measuring how each rubric drives learning requires retraining v2 with each rubric removed (GPU; v3).

- Source: `logs/baseline_day1.json` (mode = `env-rollout`)
- Rubric: `AnalyzerRubricV2` (8 children for v2, 5 for v1)
- Scenarios: **n = 100**
- Flag threshold: `0.5`
- Composite reward (all rubrics on): `1.1264`

## Aggregate metrics (full rubric)

| Metric | Value |
|---|---|
| Detection | 0.5700 (57/100) |
| FPR | 0.0000 (0/0) |
| Precision | 1.0000 |
| F1 | 0.7261 |

## Ablation table

| Rubric zeroed | Default weight | Reward (full) | Reward (zeroed) | Δ reward | Verdict |
|---|---|---|---|---|---|
| `detection` | +1.00 | +1.1264 | +0.5664 | -0.5600 | rubric matters (reward dropped without it) |
| `missed_scam` | -0.50 | +1.1264 | +1.1264 | +0.0000 | no effect |
| `false_positive` | -0.80 | +1.1264 | +1.1264 | +0.0000 | no effect |
| `calibration` | +0.50 | +1.1264 | +0.7984 | -0.3280 | rubric matters (reward dropped without it) |
| `explanation` | +0.40 | +1.1264 | +0.8880 | -0.2384 | rubric matters (reward dropped without it) |
| `signal_accuracy` | +0.20 | +1.1264 | +1.1264 | +0.0000 | no effect |
| `format` | +0.15 | +1.1264 | +1.1264 | +0.0000 | no effect |
| `length` | +0.15 | +1.1264 | +1.1264 | +0.0000 | no effect |

## Caveats

1. Sensitivity ≠ training contribution. A rubric with small Δ may still
   be load-bearing during training (where it shapes the policy gradient).
2. The env-rollout corpus is **all-scam by construction** (the scripted
   Scammer never produces benign episodes), so `false_positive` and
   `format` (which fires on benign-flagged-scam) cannot move here. Run
   `--source-mode bench` for the FPR-sensitive view.
3. `missed_scam` is zero because the scripted Victim resists every
   episode in `baseline_day1.json` (extraction_rate = 0/100). Replay
   on a harder rollout where extraction > 0 will activate it.
4. `signal_accuracy` and `length` are zero because the env-rollout
   adapter synthesises identical per-row explanations and an empty
   signal list — the leaves are exercised, but with no per-row
   variance there is nothing to vary the score against.
5. v3 plan: rerun training with each rubric weight set to 0, measure
   on the same bench, and report **per-rubric retrain ablation** as
   the gold-standard composability proof.
