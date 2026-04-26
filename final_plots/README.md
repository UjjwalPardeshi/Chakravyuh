# Final plots — submission-ready figures for judging

Maps directly to the 4 judging criteria:
- **Reward curves** → training trajectory of the v2 GRPO run
- **Metrics** → per-difficulty, threshold sweep, calibration, ablation, leakage
- **Before/after behavior** → v1 vs v2 fix, scripted vs trained, co-evolution rounds

Regenerate with: `python3 eval/build_final_plots.py` (or re-run the source notebooks then `eval/plot_coevolution.py`).

## Inventory

| File | Category | What it shows |
|---|---|---|
| `training_curves_v2.png` | Reward curve | v2 Analyzer GRPO training: mean reward + std band, KL divergence, loss, gradient norm across 619 steps. THE training reward curve. |
| `reward_hacking_diagnostic.png` | Before/after | v1 LoRA's uniform 100% detection across all difficulty buckets — the visible signature of reward hacking that triggered the v1→v2 fix. |
| `v2_per_difficulty_check.png` | Metrics | Per-difficulty detection of v2 LoRA vs scripted: 100/100/100/97% across easy/medium/hard/novel. |
| `baseline_vs_trained_overall.png` | Before/after | Aggregate detection: scripted baseline vs v2 LoRA on the 174-scenario bench. |
| `baseline_vs_trained_per_category.png` | Before/after | Per-category detection: scripted vs v2 LoRA, broken out by scam category. |
| `v1_vs_v2_fingerprint.png` | Before/after | B.1 controlled experiment: SFT baseline vs v2 GRPO, same LoRA + same training data, only algorithm differs. |
| `ece_reliability.png` | Metrics | Calibration: Expected Calibration Error + reliability diagram for v2 (B.6). |
| `ablation_per_rubric.png` | Metrics | Per-rubric ablation: contribution of each of 8 reward rubrics to final v2 detection/FPR. |
| `leakage_clean_slice.png` | Metrics | Leakage-clean OOD slice: v2 detection on cosine<0.70 subset (50 scenarios) — generalization, not memorization. |
| `semantic_leakage_histogram.png` | Metrics | Cosine-similarity histogram between bench and training corpus — honest disclosure of 44.8% high-leakage. |
| `temporal_gap_closure.png` | Before/after | Detection gap closure on post-2024 novel attacks: scripted (76.5%) vs v2 LoRA (97.1%). |
| `rubric_decomposition.png` | Metrics | Per-rubric reward decomposition over training — which rubrics dominated learning. |
| `coevolution_headline.png` | Before/after | B.2 co-evolution headline: bypass rate for ScriptedAnalyzer vs v2 LoRA across train/held-out splits. |
| `coevolution_per_category.png` | Before/after | B.2 per-category bypass: where v2 LoRA holds and where it has known gaps (vaccine, customer-support, EMI). |
| `scammer_phase1_per_category.png` | Before/after | B.2 phase 1 Scammer LoRA: per-category bypass of rule-based defense, single-shot vs best-of-8. |
| `headline_v1_vs_v2_reward_fix.png` | Before/after | THE dramatic v1→v2 headline: detection stable at 99.3%+, FPR drops 36% → 6.7% (5× better). Asymmetric improvement = real learning vs reward-hacking. |
| `metrics_v2_threshold_sweep.png` | Metrics | Threshold-degeneracy plot: 12 of 13 thresholds yield identical metrics. Demonstrates v2 produces a bimodal score distribution — model is confident, not borderline. |
| `metrics_b1_sft_vs_grpo.png` | Metrics | B.1 controlled experiment: SFT baseline ties v2 GRPO within Wilson CIs. Honest research-rigor signal — answers 'did GRPO actually help?' |
