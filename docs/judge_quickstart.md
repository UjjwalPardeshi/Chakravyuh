# Judge Quickstart

A 3-minute guided tour of the Chakravyuh submission. Click in this order; everything else is supporting material.

---

## 1 · The live demo (60 seconds)

→ **[https://ujjwalpardeshi-chakravyuh.hf.space/demo/](https://ujjwalpardeshi-chakravyuh.hf.space/demo/)**

Open the **Replay** tab and click `Next Turn ▶` through Episode 1 (*Multi-Agent Defense Wins*). Watch the 5-agent grid update each turn, the suspicion timeline climb, and the Bank Monitor flip from review → flag → freeze. Then click the **You vs Analyzer** tab and try to bypass the rule-based scorer with your own scam attempt.

If the Space is cold, the first request takes ~30–60s while the container boots; subsequent requests are <1s. Use `/health` to poll readiness.

---

## 2 · The hero plot + 60-second pitch (60 seconds)

→ **[README.md](../README.md)** — open and read the first 3 sections only:

1. **TL;DR for judges** (1 paragraph)
2. **Hero plot** — per-difficulty detection, scripted vs Chakravyuh v2
3. **Why this matters — one named victim** (1 paragraph)

These three blocks are the entire pitch. If you stop reading after them, the headline is: *we built a 5-agent multi-agent fraud-detection environment, caught ourselves reward-hacking in v1, diagnosed and fixed it in v2, and the asymmetric improvement (detection unchanged, FPR 5× down) is the signal*.

---

## 3 · The v1 → v2 reward-hacking diagnosis (60 seconds)

→ **[README.md § Results — v1 (reward-hacked) vs v2 (principled retrain)](../README.md#lora-trained-analyzer--v1-reward-hacked-vs-v2-principled-retrain)**

This is the most distinctive contribution. We hit reward-hacking, *recognized* it from the per-difficulty signature (flat ~100% across all difficulties), diagnosed the cause (FP penalty too weak, format reward paid on benign-flagging, calibration weight under-loaded), and retrained with three principled fixes. The result: detection 99.3% (unchanged), FPR 6.7% (5× better), F1 = 0.99.

→ Backing artifact: [`logs/eval_v2.json`](../logs/eval_v2.json) and [`logs/bootstrap_v2.json`](../logs/bootstrap_v2.json) (10k-iteration percentile bootstrap CIs).

---

## 4 · Five most distinctive contributions

If you only have 30 more seconds, these are what differentiates Chakravyuh from a typical submission:

1. **Diagnosed reward-hacking incident** — committed v1 numbers showing the hack, principled v2 fix, asymmetric FPR drop as proof it worked. Most submissions hide failures; we lead with one.
2. **Composable rubric system** ([`chakravyuh_env/rubrics.py`](../chakravyuh_env/rubrics.py)) — 5 child rubrics (`detection`, `missed_scam`, `false_positive`, `calibration`, `explanation`), each subclassing `openenv.core.rubrics.Rubric`. Per-rubric ablation in [`docs/ablation_study.md`](ablation_study.md).
3. **Two-tier oversight** — Analyzer sees only chat; Bank Monitor sees only transaction metadata. Genuine partial observability, structurally separated. Negotiation protocol wired in [`docs/negotiation_protocol.md`](negotiation_protocol.md).
4. **Real-incident grounding** — the bench is built from 2025 Indian fraud cases (matrimonial crypto, deepfake CEO, AePS biometric cloning). Sources cited in README; templates NPCI/RBI-grounded.
5. **Honesty as a discipline** — [`docs/Q_AND_A_REHEARSAL.md`](Q_AND_A_REHEARSAL.md) names every gap with measured artifacts; [`docs/POSTMORTEM_FUTURE.md`](POSTMORTEM_FUTURE.md) lists what won't ship and why; bootstrap CIs disclosed; small benign sample acknowledged in every results paragraph.

---

## 5 · What to ignore (work-in-progress)

These are real but explicitly tagged as v3 / pending GPU compute:

- **v2 per-scenario error analysis** — eval is aggregate-only; per-scenario audit needs GPU re-inference. Currently shipped: scripted-baseline per-scenario audit + v2 aggregate counts in [`docs/v2_error_analysis.md`](v2_error_analysis.md).
- **Frontier baseline** — script exists at [`eval/frontier_baseline.py`](../eval/frontier_baseline.py); requires API budget to run. The CSV that previously lived at `logs/frontier_comparison.csv` was a 1-row scripted-baseline stub — renamed to [`logs/scripted_baseline_n5_archived.csv`](../logs/scripted_baseline_n5_archived.csv) so nobody reads it as a frontier comparison. Until the real eval runs, no frontier claim is made.
- **Adversarial Scammer training** — onsite GPU work. Today's submission ships scripted Scammer + scripted Victim + trained Analyzer; the multi-agent learning loop is v3. Honest framing.
- **Calibration ECE** — `CalibrationRubric` is trained for; ECE not yet computed (would need per-scenario v2 logits).

---

## 6 · The fastest path to verifying the env works

Five terminal commands (60 seconds total on a clean machine with the venv installed):

```bash
pip install -e '.[llm,eval]'
make smoke-test               # in-process env reset+step in <5s
pytest tests/ --tb=no -q      # 233 collected; 231 pass + 2 skip
make link-check               # every README link resolves
make reproduce                # ~10 min CPU cached eval; verifies headline numbers within 0.5pp
```

If any of these fail on your fresh clone, please tell us — that's a serious issue, not a curiosity.

---

## 7 · The pitch in one sentence

> *Chakravyuh is the only multi-agent OpenEnv fraud-detection environment with a documented reward-hacking diagnosis-and-fix loop, grounded in real 2025 Indian UPI fraud cases — submitted with calibrated CIs and an honest list of v3 work.*
