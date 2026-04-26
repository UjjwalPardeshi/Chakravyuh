# Misuse / Dual-Use Disclosure

> This document is the **dual-use risk and misuse statement** that gates the
> Hugging Face Hub gated repository for the B.2 Phase-1 Scammer LoRA
> (`ujjwalpardeshi/chakravyuh-scammer-lora-phase1`). The full responsible-use
> framing — intended use, out-of-scope use, mitigations, and disclosure
> contact — is in [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md). This file is
> the shorter, gating-first version that is also published as the
> Scammer-LoRA HF Hub model card.

## What this artifact is

A **0.5 B-parameter LoRA adapter** trained on top of `Qwen/Qwen2.5-0.5B-Instruct`
via TRL 0.14 GRPO with the adversarial reward `1 - ScriptedAnalyzer.score`.
After 200 episodes the adapter learned to generate UPI-fraud-style
conversational openings that evade the rule-based ScriptedAnalyzer at
**93.75 % best-of-8 (n=64)** and **100 % on 8 held-out novel categories**
(income-tax refund · vaccine slot · lottery · customer-support callback ·
EPF pension · EMI conversion · blue-tick verification · police notice).
Same outputs scored by the v2 Analyzer LoRA: **32.8 % bypass** — a 60 pp
gap that is the actual research result.

Per-sample artifacts:

- [`logs/b2_phase1_scammer_eval_n64_bestof8.json`](../logs/b2_phase1_scammer_eval_n64_bestof8.json)
- [`logs/b2_phase1_scammer_vs_v2_lora.json`](../logs/b2_phase1_scammer_vs_v2_lora.json)

## Why this is dual-use

The adapter generates plausible Indian-context UPI-fraud openings. The
adversarial training reward explicitly drives it **away** from the
instruction-tuned safety behaviour of the base model: in the n=64
evaluation set there are **0 refusals**. That is intentional — an
adversarial agent that refuses to play the adversary is useless for
training a defender — but it is exactly the dual-use risk that needs
mitigation.

## Intended uses (allowed)

1. Independent verification of the Phase-1 result (load the adapter,
   re-run [`logs/b2_phase1_scammer_eval_n64_bestof8.json`](../logs/b2_phase1_scammer_eval_n64_bestof8.json),
   confirm the bypass rate within Wilson CIs).
2. Adversarial-co-evolution research (training defender models against
   this adapter, the same way we trained v2 → v3 internally).
3. Red-team test-set augmentation for fraud-detection systems
   (paraphrase the generated openings into your own evaluation set).
4. Reproducibility checks of the B.2 framing in the
   [README](../README.md) and [WIN_PLAN.md](../WIN_PLAN.md).

## Out-of-scope uses (disallowed)

The following uses are explicitly **disallowed**. Requesting gated
access constitutes acceptance of these terms:

- Generating live scam content for distribution at scale (SMS, email,
  WhatsApp, social media, voice).
- Probing a deployed Analyzer's decision boundary in production
  systems without prior written authorization from the operator.
- Training derivative offensive models (adapters or merges that
  inherit the safety-stripping behaviour).
- Any use against a real human being, financial institution, regulator,
  or law-enforcement agency.

## Mitigations applied

| Mitigation | Where |
|---|---|
| **HF Hub gated access** — download requires acceptance of these terms | Repo settings on the HF Hub |
| **Adapter-only release** — useless without the base model and runtime | The 12 MB adapter has no inference engine of its own |
| **Public eval that exposes the bypass capability** — a defender knows what it has to defend against; we do not hide it | [`logs/b2_phase1_scammer_eval_n64_bestof8.json`](../logs/b2_phase1_scammer_eval_n64_bestof8.json) |
| **Public head-to-head vs the v2 LoRA** — the actual residual bypass rate (32.8 %) is published, not hidden, so the *defender* gain is the headline | [`logs/b2_phase1_scammer_vs_v2_lora.json`](../logs/b2_phase1_scammer_vs_v2_lora.json) |
| **No serving endpoint** — the live HF Space ([ujjwalpardeshi/chakravyuh](https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh)) exposes the *Analyzer*, not the *Scammer*. There is no public endpoint that calls the Scammer to generate text on demand | [`server/`](../server/) |
| **0/64 refusal rate is disclosed up-front** — reviewers see the dual-use risk explicitly rather than discovering it | This document + [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md) |

## Disclosure contact

For misuse reports, ethical concerns, or vulnerability disclosures:

- Email: `ujjwal.pardeshi@riamona.com`
- GitHub: file an issue marked `[security]` at <https://github.com/UjjwalPardeshi/Chakravyuh/issues>

We acknowledge within seven days, treat reports as confidential until a
fix is shipped or a coordinated disclosure date is agreed, and credit
reporters in release notes (with permission). We do **not** threaten
legal action against good-faith researchers and do **not** demand
deletion of findings after a fix.

## License

The adapter weights are released under the same license as
[`Qwen/Qwen2.5-0.5B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
(Apache-2.0). The Chakravyuh codebase that produced them is MIT
([`LICENSE`](../LICENSE)).

## Cross-references

- Full responsible-use framing: [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md)
- Project README: [`README.md`](../README.md)
- Defender-side artifact: [`huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2`](https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2)
- Bench dataset: [`huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0`](https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0)
