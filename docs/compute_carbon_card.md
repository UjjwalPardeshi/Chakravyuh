# Compute & Carbon Disclosure

Following the [ML CO2 Impact](https://mlco2.github.io/impact) framework. Numbers are estimates; the input fields are stated explicitly so a reviewer can re-derive.

## Method

- **Calculator:** ML CO2 Impact (https://mlco2.github.io/impact).
- **Region:** US-East-1 (where Hugging Face Spaces typically allocates GPU). Carbon intensity ≈ **390 g CO2 / kWh** (EPA eGRID 2022 baseline; the calculator's default for US-East-1).
- **Hardware power figures:** A100-40GB ≈ 400 W under full RL training load; T4 ≈ 70 W; CPU only ≈ 30 W.

Round-trip carbon = `power_kW × hours × carbon_intensity_g_per_kWh / 1000`.

## Compute spent so far

| Phase | Hardware | Hours | kWh | g CO2 |
|---|---|---|---|---|
| v2 Analyzer LoRA training (single-seed, seed 42) | A100 | ~6 | 2.4 | ~936 |
| B.2 Phase 1 Scammer LoRA training (200 ep × 8 seeds) | T4 | ~3 | 0.21 | ~82 |
| B.2 Phase 1 Scammer eval (n=64 single + best-of-8) | T4 | ~0.6 | 0.042 | ~16 |
| Bench inference for `eval_v2.json` (n=174) | A100 | ~0.5 | 0.2 | ~78 |
| Bootstrap CI computation (10k iter) | CPU | ~0.02 | 0.0006 | ~0.2 |
| Semantic-leakage audit (MiniLM-L6 over 1,177 train × 174 bench) | CPU | ~0.05 | 0.0015 | ~0.6 |
| Frontier baseline — 7 open-weight models via HF Inference Providers (n=175 × 7) | hosted (3rd-party) | ~0.4 (wall-clock) | n/a | n/a |
| **Subtotal — shipped (Chakravyuh GPU-h)** | | **~10.2 GPU-h** | **2.85 kWh** | **~1,113 g CO2** |

**Frontier baseline note.** The 7-model frontier comparison ran on third-party hosted inference (HuggingFace Inference Providers), not on our compute. We paid ~$2 of HF compute credits for the full 7-model run; the energy/carbon attribution belongs to the hosting provider (Together AI / Fireworks / Novita / etc.) and is not included in our subtotal. Per-row scores cached at `logs/frontier_cache/` so re-runs are free and zero-emission for us.

## Compute planned for the 30-credit HF onsite spend

Reference: [`.claude/plan/perfect-project.md`](../.claude/plan/perfect-project.md) §1 credit-allocation table.

| Phase | Hardware | Hours | kWh | g CO2 |
|---|---|---|---|---|
| B.2 Phase 2 — Analyzer retrain vs Scammer | A100 | 3 | 1.2 | ~468 |
| B.7 — Held-out template-family retrain | A100 | 3 | 1.2 | ~468 |
| B.6 — Calibration ECE + reliability diagram | A100 | 0.5 | 0.2 | ~78 |
| B.4 — Multi-seed retrain (3 seeds, T4) | T4 | 3 | 0.21 | ~82 |
| B.5 + B.8 + B.11 + B.12 — eval-only (T4) | T4 | ~3 | 0.21 | ~82 |
| Buffer for B.2 Phase 2 re-run | A100 | 0.25 | 0.1 | ~39 |
| **Subtotal — planned onsite** | | **~12.75 GPU-h** | **3.12 kWh** | **~1,217 g CO2** |

## Project-total estimate

| | GPU-hours | kWh | g CO2 |
|---|---|---|---|
| Shipped | ~10.2 | 2.85 | ~1,113 |
| Planned onsite | ~12.75 | 3.12 | ~1,217 |
| **Project total (estimated)** | **~23 GPU-h** | **~5.97 kWh** | **~2.33 kg CO2** |

For reference: 2.33 kg CO2 ≈ a 12 km drive in an average passenger car, or ~5 hours of streaming HD video.

## What is NOT included

- Energy consumed by the always-on HF Space (small; ≈ CPU idle).
- Local laptop CPU work (writing, evaluation post-processing) — non-negligible by hours but tiny by power.
- The training runs that produced the **base** Qwen2.5-7B and Qwen2.5-0.5B models (Alibaba's compute, not ours).
- Network and storage (HF Hub, GitHub).

## Reproducibility

To re-derive these numbers:
1. Open https://mlco2.github.io/impact.
2. Select `A100 PCIe 40/80GB` or `T4` as appropriate.
3. Set hours per the table above.
4. Set provider = AWS, region = US East 1.
5. The calculator returns `~390 g CO2 / kWh × hours × power_kW` automatically.

Numbers above use `power_kW` of 0.4 (A100) and 0.07 (T4), which are common literature values; ML CO2 Impact uses similar defaults.
