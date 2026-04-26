# REPRODUCE.md

A judge-friendly five-step walkthrough for verifying every headline number in the README from a fresh clone. **Expected stdout snippets are inline so you know whether each step succeeded without reading our minds.**

If any step's output deviates from the tolerance band stated below, please file an issue at https://github.com/UjjwalPardeshi/Chakravyuh/issues with the title `REPRODUCE failed at step N` and we will investigate within seven days.

## Prerequisites

- Python ≥ 3.10 and ≤ 3.12 (the package's `pyproject.toml` pins `requires-python = ">=3.10, <3.13"`; CI runs 3.10 / 3.11 / 3.12 / 3.13).
- ~16 GB RAM (the bench can be evaluated with cached scores on CPU; full GPU re-inference needs ~14 GB GPU VRAM).
- ~5 GB free disk (model + bench + logs).
- An internet connection for the first run (downloads HF Hub assets to `~/.cache/huggingface/`).
- Optional: NVIDIA GPU + CUDA 12 if you want to re-run inference rather than use cached scores.
- No HF API key required for the cached path.
- `GROQ_API_KEY` is required only by `tests/test_explanation_judge.py` (2 tests will be skipped if absent — that is the documented behaviour).

## Step 1 — Clone

```bash
git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
```

Expected: `Cloning into 'Chakravyuh'...` followed by repository-write progress. No errors. Repo size ≈ 30 MB.

## Step 2 — Install (pinned, reproducible)

The repo ships a `uv.lock` file pinning every transitive dependency. The bit-reproducible path is:

```bash
pip install uv          # if not already installed
uv venv .venv           # create an isolated venv (Python 3.10–3.12)
source .venv/bin/activate
uv pip sync uv.lock     # install exact pinned versions
uv pip install -e '.[llm,eval,demo,dev]'   # editable install of this package
```

The non-pinned (latest) path is also supported but is **not bit-reproducible** across time:

```bash
pip install -e '.[llm,eval,demo,dev]'
```

Expected: `Successfully installed openenv-core-0.2.3 ...` and ~80 packages installed. No `error:` lines.

If `uv pip sync` fails due to a Python-version mismatch, double-check that you are inside the `.venv` activated above and that the venv was built with Python 3.10, 3.11, or 3.12.

## Step 3 — Tests

```bash
pytest tests/ -v --tb=short
```

Expected last line:

```
============= 338 passed, 3 skipped in N.Ns =============
```

(Counts may shift slightly as the suite grows; the floor is **338 passed, 3 skipped** (341 collected) for the canonical hackathon-submission state. The skips are GROQ-gated tests in `tests/test_explanation_judge.py` and `tests/test_explanation_rubric.py` that skip cleanly if `GROQ_API_KEY` is not in the environment — that is correct behaviour.)

If any test fails, please attach the full pytest output to the issue.

## Step 4 — Smoke test (in-process env)

```bash
make smoke-test
```

Expected:

```
Smoke test PASSED
```

The smoke test exercises one full env reset → step → state cycle in-process (no HTTP server, no GPU). Total runtime < 5 s on a typical laptop.

## Step 5 — Reproduce eval numbers

The fast path uses cached per-row scores (no GPU, ~10 minutes on CPU):

```bash
CHAKRAVYUH_SKIP_INFERENCE=1 make reproduce
```

Expected output ends with:

```
[reproduce] eval-v2: detection=0.993 fpr=0.067 f1=0.989 (n=174)
[reproduce] bootstrap: detection 95% CI [0.979, 1.000], fpr 95% CI [0.018, 0.207]
[reproduce] PASS — within 0.5pp of README claims
```

Tolerance band: **detection 99.3 ± 0.5 pp · FPR 6.7 ± 0.5 pp · F1 0.99 ± 0.005**. If your numbers fall inside that band, the run reproduced.

The full GPU path (re-runs inference end-to-end, ~2–4 hours on a single A100) is:

```bash
make reproduce          # without CHAKRAVYUH_SKIP_INFERENCE — re-runs the v2 LoRA on every bench scenario
```

Both paths emit:

- `logs/eval_v2_reproduce.json` — fresh metrics
- `logs/bootstrap_v2_reproduce.json` — fresh 10 000-iteration percentile CIs
- A diff against the canonical `logs/eval_v2.json` and `logs/bootstrap_v2.json` (printed to stdout)

## Step 6 (optional) — Verify the v1 → v2 statistical-significance claim

The README cites a permutation test for the FPR delta:

```bash
python eval/permutation_test_v1_v2.py
```

Expected JSON ends with:

```
"p_value_permutation": ~0.008,
"p_value_fisher_exact": ~0.010,
"interpretation_permutation": "significant (p ≈ 0.008)"
```

These are the values from `logs/permutation_test_v1_v2.json`. Both p-values are below α = 0.05 — the v1 → v2 FPR drop is statistically significant.

## Step 6b (optional) — Open-weight frontier comparison (HF credits or free)

```bash
# Free path — Groq's hosted Llama-3.3-70B (no HF credits, no money)
export GROQ_API_KEY=gsk_...   # https://console.groq.com (free tier)
python -m eval.frontier_baseline --providers groq --limit 30

# HF-credit path — pay-per-token from your HF compute credits, ~$2 for the 7-model
# bench we shipped (~$0.30 per 175-row run; cached after first run is free).
export HF_TOKEN=hf_...
python -m eval.frontier_baseline --providers hf --hf-models \
    meta-llama/Llama-3.3-70B-Instruct \
    Qwen/Qwen2.5-72B-Instruct \
    deepseek-ai/DeepSeek-V3-0324 \
    Qwen/Qwen2.5-7B-Instruct \
    openai/gpt-oss-120b \
    deepseek-ai/DeepSeek-R1 \
    google/gemma-3-27b-it
```

Output: `logs/frontier_comparison.csv` with one row per provider model + a scripted-baseline reference row. CIs are bootstrap 1 000-iteration. Permutation tests vs the scripted baseline are appended to the same CSV. Per-row scores cached at `logs/frontier_cache/<provider>:<sha1>.json` so re-runs of any subset are free after the first call. **Note**: Qwen2.5-7B-Instruct is the LoRA's base model — running it gives you the head-to-head that isolates the GRPO+LoRA training contribution.

## Step 7 (optional) — Verify the live demo

```bash
curl -sI https://ujjwalpardeshi-chakravyuh.hf.space/health | head -1
```

Expected: `HTTP/2 200`. Cold-start time is ~2.7 s (well under the 20 s OpenEnv requirement). The Space is kept warm by `.github/workflows/keepwarm.yml`.

## Common pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `2 tests skipped` in pytest output | `GROQ_API_KEY` not set; the two `test_explanation_judge` tests skip cleanly | Expected — no action needed |
| First `pytest` run is slow (~5 min) | HuggingFace download cache miss on first import (downloads ~14 GB of base model weights only if you trigger inference) | Expected on cold cache; subsequent runs use the cache |
| `make reproduce` hangs at "loading sentence-transformers" | Cold MiniLM-L6 download for the leakage audit (one-time ~80 MB) | Wait; subsequent runs are cached |
| `uv pip sync` complains about Python version | venv built with 3.13+ but `pyproject.toml` requires `<3.13` | Recreate venv with `python3.12 -m venv .venv` |
| Live HF Space `/demo/` returns 502 | First request after a long idle | Wait 5 s and retry; the Space cold-starts in 2.7 s |
| Pytest fails on `test_readme_invariants` with "test count drift" | The repo gained tests since the README claim was last updated | The test prints the new count; update README and Makefile to match |

## What `make reproduce` actually does

The `Makefile` target runs (in order):

1. `eval-v2` — re-evaluates the v2 LoRA on the canonical bench at `data/chakravyuh-bench-v0/scenarios.jsonl`. With `CHAKRAVYUH_SKIP_INFERENCE=1`, this loads cached per-row scores from `logs/eval_v2_per_row.jsonl` (when shipped) or falls back to the aggregate scores in `logs/eval_v2.json`.
2. `bootstrap` — runs 10 000-iteration percentile-bootstrap over the per-row outcomes to produce the published CIs.
3. Prints a one-line tolerance check against the README values.

Source: [`Makefile`](Makefile).

## Where the headline numbers come from

| Claim | Path | Tolerance |
|---|---|---|
| v2 detection 99.3 % | `logs/eval_v2.json:lora_v2.detection` | ±0.5 pp |
| v2 FPR 6.7 % | `logs/eval_v2.json:lora_v2.fpr` | ±0.5 pp |
| v2 F1 = 0.99 | `logs/eval_v2.json:lora_v2.f1` | ±0.005 |
| Bootstrap CI for FPR | `logs/bootstrap_v2.json` | recomputed each run; same data |
| v1 → v2 FPR drop is significant | `logs/permutation_test_v1_v2.json:aggregate_fpr_test` | p < 0.05 (typically ~0.008–0.011) |
| Scammer LoRA bypass best-of-8 (n=64) | `logs/b2_phase1_scammer_eval_n64_bestof8.json:aggregate.overall.bypass_rate` | 0.9375 ± 0.05 (Wilson CI shipped) |
| Held-out novel bypass best-of-8 | `logs/b2_phase1_scammer_eval_n64_bestof8.json:aggregate.held_out_seeds.bypass_rate` | 1.000 ± 0.05 |
| 44.8 % of bench has cosine > 0.85 to training | `logs/semantic_leakage_audit.json:summary.pct_above_0.85` | ±2 pp |

All paths are repo-relative and stable across commits.

## Where to file an issue

[https://github.com/UjjwalPardeshi/Chakravyuh/issues/new](https://github.com/UjjwalPardeshi/Chakravyuh/issues/new) with title format:

> `REPRODUCE failed at step N: <one-line summary>`

Please attach: the failing command's full output, your Python version (`python --version`), your OS, and the SHA of the commit you cloned (`git rev-parse HEAD`).
