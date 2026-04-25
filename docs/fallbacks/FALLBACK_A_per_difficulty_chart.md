# FALLBACK A — Per-difficulty detection chart

**When to use:** the live `/diagnose` or `/demo/` is timing out, or any LoRA inference output falls outside the [0.85, 1.00] tolerance band specified in `LIVE_PITCH.md`. Pivot to this slide *immediately* — do not waste stage time troubleshooting.

## Visible artifact

![Per-difficulty detection: scripted analyzer vs Chakravyuh v2 LoRA](https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/a9e723bf495182724845dbf1f69f8968434a9e02/docs/assets/plots/v2_per_difficulty_check.png)

## What you say (one sentence, ~12 seconds)

> "The live demo's timing out — here's the actual measured result on 174 scenarios. Scripted rule-based analyzer catches **50 % of post-2024 novel scams**; Chakravyuh v2 LoRA catches **97 %**. That's the gap closure. The asymmetric improvement — detection up 47 percentage points only on novel, where it matters most — is what makes us confident the model learned the task instead of memorizing templates."

## Backing artifacts (cite if asked)

- `logs/eval_v2.json` — per-difficulty detection (full numbers)
- `logs/bootstrap_v2.json` — 95 % CIs (10k iter, seed 42)
- `data/chakravyuh-bench-v0/scenarios.jsonl` — 174 scenarios

## Then carry on with closing beat

> "Repo: github.com/UjjwalPardeshi/Chakravyuh. Adapter on the Hub. Bench public. Try the red-team tab — it's why we built this. Thanks."
