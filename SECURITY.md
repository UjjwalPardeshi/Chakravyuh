# Security Policy

## Reporting a vulnerability

Please report security issues privately. Do **not** open a public GitHub issue.

**Contact:** [ujjwal.pardeshi@riamona.com](mailto:ujjwal.pardeshi@riamona.com) — subject prefix `[chakravyuh-security]`.

We will acknowledge receipt within 7 days and aim to provide a remediation timeline within 14 days.

## Scope

In scope:

- Code in the `chakravyuh_env/`, `server/`, `eval/`, and `training/` packages.
- The HF Space deployment at https://ujjwalpardeshi-chakravyuh.hf.space (information disclosure, SSRF, prompt-injection bypass of `server/input_sanitizer.py`).
- Published artifacts on the Hugging Face Hub: model adapters, dataset.
- The reward design and training pipeline (reward hacking, optimizer-side data exfiltration via prompt rewriting).

Out of scope:

- Issues that depend on attacker-controlled inputs to *the deployed Analyzer* that the Analyzer is *designed* to detect (e.g., a scammer message — the project's job is to flag, not refuse such inputs).
- Denial-of-service against the HF Space at a level that requires sustained traffic.
- Vulnerabilities in upstream dependencies (transformers, trl, peft) — please report to those projects directly.

## Dual-use note

The Scammer LoRA adapter is gated on the Hugging Face Hub and intended for internal red-team and adversarial-co-evolution research only. Any use of the Scammer adapter to generate live attack content is explicitly out of scope for this project; see [`docs/RESPONSIBLE_USE.md`](docs/RESPONSIBLE_USE.md) for the full statement.

## Disclosure timeline

We follow coordinated disclosure with a default 90-day window from initial report to public disclosure, with extensions on request when remediation requires upstream library changes.

## Acknowledgements

Reporters who follow this policy are credited in the relevant release notes (with consent).
