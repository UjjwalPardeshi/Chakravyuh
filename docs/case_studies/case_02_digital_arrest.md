# Case Study 2 — Digital Arrest Video Call (`modec_108`)

> **Difficulty:** novel post-2024 · **Category:** OTP theft via fear-based authority impersonation · **₹ at risk:** 3,50,000 · **Channel:** voice · **Source:** Novel post-2024 — Digital arrest video call

## The scenario

Single-turn voice attack from an attacker impersonating law enforcement:

> "Digital Arrest Notice: You are under virtual arrest for money laundering. Stay on video call, share OTP to verify identity. Hanging up = arrest warrant activated. OTP to drop charges."

Ground-truth signals: `impersonation`, `fear`, `authority`,
`info_request`. Bench metadata: `victim_profile: senior`, outcome
(without defender): `money_extracted`. Real-world counterpart: I4C
disclosed ₹120 cr+ lost to "digital arrest" scams in CY2024, with
seniors as the primary target.

## Five-agent transcript (env replay)

| Turn | Actor | Channel | Content |
|---|---|---|---|
| 1 | Scammer → Victim | voice | "Digital Arrest Notice: You are under virtual arrest for money laundering. Stay on video call, share OTP to verify identity. Hanging up = arrest warrant activated. OTP to drop charges." |
| 1 | Analyzer (chat-only) | observation | `score=0.96`, `signals=[impersonation, fear, authority, info_request]`, `explanation="Fictitious 'digital arrest' construct — Indian law enforcement does not request OTPs and does not conduct arrests over video calls. The combination of fear + authority + OTP request is the textbook fingerprint of an OTP-theft attack against a senior victim. Hang up; report to 1930."` |
| 1 | Bank Monitor (metadata-only) | side-channel | No transaction observed yet (pre-OTP); risk-channel idle but pre-flagged. |
| 1 | Regulator (aggregator) | meta | `consensus=block`; logs under `otp_theft / novel`; emits the **public-awareness alert** (Regulator's outcome-loop role) recommending an SMS broadcast about "fake digital arrest" to peer banks. |
| — | **Outcome** | — | Money **prevented**. Per-rubric reward breakdown: `Detection +1.0 · MissedScam 0 · FalsePositive 0 · Calibration +0.94 · Explanation +1.0 · SignalAccuracy +1.0 · Format +1.0 · Length +0.7 · RupeeWeighted +1.0` (₹3.5L is well above the cap of ₹1L). |

## 8-rubric reward breakdown (v2 weights)

| Rubric | Leaf | × Weight | Contribution |
|---|---|---|---|
| `Detection` | 1.0 | × +1.0 | **+1.00** |
| `MissedScam` | 0.0 | × −0.5 | 0.00 |
| `FalsePositive` | 0.0 | × −0.8 | 0.00 |
| `Calibration` | 0.94 | × +0.5 | +0.47 |
| `Explanation` | 1.0 | × +0.4 | +0.40 |
| `SignalAccuracy` | 1.0 | × +0.2 | +0.20 |
| `Format` | 1.0 | × +0.15 | +0.15 |
| `Length` | 0.7 | × +0.15 | +0.105 |
| **Total scalar reward** | — | — | **+2.33** |
| `RupeeWeighted` (separate aggregator) | +1.0 (clipped) | n/a | ₹3,50,000 prevented |

## Interpretation

This scenario is where the v2 LoRA's **calibration** reward earns its
weight increase from v1's 0.3 to v2's 0.5 — the model is *very*
confident (0.96) on a clearly-novel attack pattern, and that confidence
is rewarded over an "always 1.0" or "always 0.5-and-hedge" agent.
ScriptedAnalyzer scores this at 0.42 (`fear + info_request` but missing
the `digital_arrest` keyword that doesn't exist in its rules). The 60 pp
gap between scripted and v2 here is the **most dangerous case** in the
bench: the largest ₹ at risk, the most vulnerable victim profile
(senior), and the most aggressive reaching-for-fear narrative. The
RupeeWeightedRubric (capped at ₹1L per scenario) flags this as one of
the highest-leverage detection events in the bench. Backing artefacts:
[`logs/eval_v2.json`](../../logs/eval_v2.json),
[`logs/rupee_weighted_eval.json`](../../logs/rupee_weighted_eval.json).
