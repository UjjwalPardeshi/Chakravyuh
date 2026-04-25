# Per-rubric ablation study

Post-hoc, eval-time sensitivity analysis. Each rubric weight is zeroed in turn, and the resulting change in average composite reward across the corpus is reported. **This is not a retrain ablation** — measuring how each rubric drives learning requires retraining v2 with each rubric removed (GPU; v3).

- Source: `logs/mode_c_scripted_n135.json` (mode = `bench`)
- Rubric: `AnalyzerRubric` (8 children for v2, 5 for v1)
- Scenarios: **n = 135**
- Flag threshold: `0.5`
- Composite reward (all rubrics on): `0.7336`

## Aggregate metrics (full rubric)

| Metric | Value |
|---|---|
| Detection | 0.7217 (83/115) |
| FPR | 0.3000 (6/20) |
| Precision | 0.9326 |
| F1 | 0.8137 |

## Ablation table

| Rubric zeroed | Default weight | Reward (full) | Reward (zeroed) | Δ reward | Verdict |
|---|---|---|---|---|---|
| `detection` | +1.00 | +0.7336 | +0.1188 | -0.6148 | rubric matters (reward dropped without it) |
| `missed_scam` | -0.50 | +0.7336 | +0.7336 | +0.0000 | no effect |
| `false_positive` | -0.30 | +0.7336 | +0.7469 | +0.0133 | rubric helps (reward rose without it) |
| `calibration` | +0.20 | +0.7336 | +0.6015 | -0.1321 | rubric matters (reward dropped without it) |
| `explanation` | +0.40 | +0.7336 | +0.7336 | +0.0000 | no effect |

## Caveats

1. Sensitivity ≠ training contribution. A rubric with small Δ may still
   be load-bearing during training (where it shapes the policy gradient).
2. The bench scenarios are single-turn predictions; multi-turn rubrics
   like `missed_scam`, `explanation`, and `bank_freeze` are not
   exercised here. Run `--source-mode env-rollout` for the multi-turn
   view that activates them.
3. v3 plan: rerun training with each rubric weight set to 0, measure
   on the same bench, and report **per-rubric retrain ablation** as
   the gold-standard composability proof.
