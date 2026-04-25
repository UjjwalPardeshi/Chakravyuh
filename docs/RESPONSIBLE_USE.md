# Responsible Use Statement

Chakravyuh is a fraud-detection research environment. Fraud detection is
**dual-use**: the same artifacts that train a defender can, in principle,
help an attacker. This document states the intended use, the out-of-scope
use, the dual-use mitigations we have applied, and the disclosure contact.

## Intended use

- Training and evaluating Large Language Models (LLMs) on adversarial
  Indian UPI fraud detection.
- Reinforcement-learning research on multi-agent oversight, scalable
  oversight, and reward design.
- Benchmarking fraud-detection systems against the public
  `chakravyuh-bench-v0` corpus.
- Education and awareness — using replays of fraudulent dialogue patterns
  to teach end-users to recognise scams.
- Ablation, calibration, and red-team studies of detection systems
  conducted on the project's own bench (or other consented corpora).

## Out-of-scope use

The following uses are explicitly **not** intended and are **discouraged**:

- Surveillance of private communications.
- Credential harvesting, account takeover, or any deceptive use against
  real human beings.
- Training of attack tools intended to deceive humans, financial
  institutions, regulators, or law-enforcement agencies.
- Automated generation of scam content for distribution at scale.
- Bypassing or weakening fraud-detection systems deployed at banks,
  payment networks, or regulators.

## Dual-use risk and our mitigations

| Risk | Mitigation |
|---|---|
| Adversarial Scammer adapter could be misused as a scam-generation tool | If released (per WIN_PLAN.md task P3.6), the Scammer adapter is published behind an HF Hub gated-access flag requiring acceptance of these terms before download. |
| Bench scenarios could be reverse-engineered into convincing scams | Bench scenarios are paraphrased from publicly disclosed real fraud patterns (RBI / NPCI / I4C advisories, news reports). They do not include personally identifying information of real victims. |
| Trained Analyzer could be probed to learn its decision boundary | We publish a red-team evaluation (see `logs/analyzer_robustness.json` once produced) so any blind spots are documented openly rather than silently. |
| Reward-design exploits | The reward is composed of five orthogonal rubrics. We diagnose and document our own reward-hacking failure (v1 → v2 retrain) in the README. |

## What we will and will not do with disclosed vulnerabilities

If a third party discloses a vulnerability — for example, an attack that
reliably bypasses the Analyzer, or a way to game the reward — we will:

1. Acknowledge receipt within seven days.
2. Treat the report as confidential until a fix is shipped or a coordinated
   disclosure date is agreed.
3. Credit the reporter in the model card and release notes (with their
   permission).
4. Add the attack class to the public red-team suite (in anonymized form)
   so future trained models are evaluated against it.

We will **not**:

- Threaten legal action against good-faith researchers.
- Demand that a researcher delete or hide their findings after a fix.

## Compliance and regulatory note

Chakravyuh is a research artifact. It is **not** a certified fraud-detection
product. Operators who deploy any model trained with this environment in
production must independently satisfy applicable Indian regulations —
including but not limited to RBI master directions on fraud risk management,
the Digital Personal Data Protection Act, and applicable NPCI guidelines.

## Disclosure contact

For vulnerability reports, ethical concerns, or responsible-use questions:

- Email: `ujjwal.pardeshi@riamona.com`
- GitHub: file an issue marked `[security]` at
  <https://github.com/UjjwalPardeshi/Chakravyuh/issues>

Please do not file public issues for sensitive security disclosures. Use
email first, and we will agree on a disclosure timeline.
