# FALLBACK B — v1↔v2 reward-hacking story in one click

**When to use:** if you can hit the HF Space landing but `/demo/` is rendering empty, or you want to demonstrate the reward-hacking diagnosis without depending on live LoRA inference.

## Visible artifact

The **"v1 vs v2 — the reward-hacking fix"** tab in the deployed Gradio demo at:

  https://ujjwalpardeshi-chakravyuh.hf.space/demo/

(Falls back to the static preview at `/demo/preview` while booting — that page already shows the per-difficulty chart and is useful by itself.)

If the Space is fully unreachable, the same data lives in:

- [`data/v1_v2_archived_responses.json`](../../data/v1_v2_archived_responses.json) — the 5 archived scenarios with their v1 (reward-hacked) and v2 (fixed) responses, plus a `_provenance.honest_note` block disclosing they're archived, not live re-runs.
- [`server/demo_v1_v2.py`](../../server/demo_v1_v2.py) — the rendering helpers.

## What you say (one sentence, ~12 seconds)

> "Here's the reward-hacking story in one click. Same scenario, two reward profiles, asymmetric outcome. v1 over-flagged a benign EMI reminder because we rewarded *every* flag; v2 caught the same scam *and* let the benign through, because we added a −0.8 false-positive penalty. That single weight change collapsed FPR from 36 % to 6.7 %."

## Then carry on with closing beat

> "Repo public, adapter on the Hub, bench on Hugging Face datasets. Methodology — catching reward hacking in GRPO via asymmetric-improvement signature — is portable to any RLHF pipeline. Thanks."
