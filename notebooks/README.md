# Colab notebooks — GPU-tier indexed

Each notebook is named with the **GPU type** that fits its task and the **WIN_PLAN item** it ships. Pick the GPU type when you set up the Colab runtime (`Runtime → Change runtime type`).

## Available notebooks (verified, env-issue-handled)

| File | WIN_PLAN item | GPU | Colab units | Runtime | Output |
|---|---|---|---:|---:|---|
| [`T4_b12_per_row_eval.ipynb`](T4_b12_per_row_eval.ipynb) | **B.12** Per-row v2 LoRA logits + leakage-clean slice | T4 | ~1 | ~7 min | `logs/eval_v2_per_row.jsonl`, `logs/eval_v2_reproduce.json`, `docs/leakage_clean_eval.md` |
| [`T4_b5_lora_redteam.ipynb`](T4_b5_lora_redteam.ipynb) | **B.5** LoRA red-team (10 attacks vs v2 + sanitizer) | T4 | ~2 | ~3 min | `logs/analyzer_robustness_lora_v2.json` |

## Run order (Tier 1 priority)

1. **B.12 first** (`T4_b12_per_row_eval.ipynb`) — cheapest GPU spend, unblocks B.6 calibration + D.5 failure taxonomy + B.17 weight grid + the leakage-clean OOD headline number.
2. **B.5 second** (`T4_b5_lora_redteam.ipynb`) — measures whether v2 LoRA + input_sanitizer beats the 4/10 rule-based baseline on the 10 prompt-injection attacks.

**Total Tier-1 GPU spend: ~3 Colab units of your 50.**

## Run instructions (every notebook)

The Colab 2026 default image ships `torch` (CUDA 13) and `torchvision` (CUDA 12.8) — a mutually-incompatible binary pair that crashes `transformers` on Qwen2 model load. Each notebook handles this with a single setup cell that:

1. Wipes the broken torch+torchvision combo.
2. Installs a matched **cu121** pair from PyTorch's official wheels.
3. Installs Chakravyuh + `transformers==4.46.3` + `peft==0.13.2` + `accelerate==1.0.1` + `bitsandbytes==0.44.1` with `--no-deps` (so nothing pulls torchvision back).
4. Verifies `SlidingWindowCache` import succeeds.
5. **Hard-kills the Colab kernel** so the new torch is loaded fresh on auto-reconnect.

You'll see *"Your session crashed for an unknown reason"* — that's our intentional kill. After the auto-reconnect, run the remaining cells normally.

### Step-by-step

For each notebook:

1. **Open in Colab** via `https://colab.research.google.com/github/UjjwalPardeshi/Chakravyuh/blob/main/notebooks/<NOTEBOOK_NAME>.ipynb`
2. **Set runtime:** `Runtime → Change runtime type → GPU T4`
3. **Hard-restart:** `Runtime → Disconnect and delete runtime`, then **Connect**
4. Run cells in order. **Do NOT click "Run all"** — the kernel restart in Cell 3 needs you to manually run each cell.
5. After Cell 3 kills the kernel and Colab reconnects:
   - Re-run **Cell 2** (clone repo — idempotent, resets variables)
   - **SKIP Cell 3** (already done)
   - Run Cell 4 onwards normally

### Each notebook auto-downloads its outputs

The final cell uses `google.colab.files.download()` to save the artifacts to your local `~/Downloads/`. Drop them into the local repo and commit per the per-notebook instructions.

## Why these two notebooks (not more)?

Given your **50 Colab units + $30 HF credit** budget, the highest-leverage GPU spend is:

- **B.12** — under 1 unit, unblocks 4 downstream items (B.6, D.5, B.17, leakage-clean headline)
- **B.5** — under 2 units, gives you the v2 LoRA red-team number that's currently aggregate-only

Other Tier-1 GPU items (B.1 SFT baseline, B.14a KL early-stop retrain, B.2 Adversarial Scammer) require **A100** at ~18 units each. With ~47 units remaining after B.12 + B.5, you can afford **two of those three**. Pick:
- **B.1** to answer "did GRPO actually help" (high research credibility)
- **B.14a** to close the `docs/training_diagnostics.md` open item
- **B.2 phase 2** to convert "5 agents, 1 trained" into demonstrable multi-agent evidence

Tell me which to build next and I'll write the corresponding A100 notebook.

## What's intentionally NOT in these notebooks

- `unsloth` — Colab's torch shim breaks torchvision when unsloth tries to patch torch. Plain `transformers + bitsandbytes` 4-bit is ~30% slower but reliable. Acceptable.
- `sentence-transformers` — only needed for the leakage audit *script* (`eval/semantic_leakage_audit.py`), which we don't run from these notebooks (we read the pre-computed `logs/semantic_leakage_audit.json`).
- `--force-reinstall` — historically pulled torchvision back via transitive deps. Replaced with explicit `--no-deps` everywhere.
- "Run all" macros — the kernel-restart pattern requires manual cell-by-cell execution.

## If something fails

The two known recovery paths are:

1. **Kaggle** — same notebook works, Kaggle's torch+torchvision pair is consistent. 30 hours/week of free T4 or P100. Sign in at kaggle.com (no credit card).
2. **HF Inference Endpoints** — deploy v2 LoRA as a managed endpoint, hit it via HTTP from your laptop. ~$0.10–$1 of your $30 credit.

Tell me which fallback you want if a notebook errors out and I'll wire it up.
