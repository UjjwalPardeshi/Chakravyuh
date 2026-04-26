# Case Study 1 — Deepfake CEO IPO Scam (`modec_106`)

> **Difficulty:** novel post-2024 · **Category:** investment fraud · **₹ at risk:** 1,00,000 · **Channel:** voice · **Source:** Novel post-2024 — AI deepfake CEO

## The scenario

Single-turn voice attack:

> "[Deepfake voice of Infosys CEO]: Exclusive employee IPO allocation. Invest Rs 1 lakh via company portal. HR calling now for UPI transfer. Limited to first 100 employees."

Ground-truth signals: `impersonation`, `authority`, `greed`. Bench
metadata: `victim_profile: young_urban`, outcome (without defender):
`money_extracted`.

## Five-agent transcript (env replay)

| Turn | Actor | Channel | Content |
|---|---|---|---|
| 1 | Scammer → Victim | voice | "[Deepfake voice of Infosys CEO]: Exclusive employee IPO allocation. Invest Rs 1 lakh via company portal. HR calling now for UPI transfer. Limited to first 100 employees." |
| 1 | Analyzer (chat-only) | observation | Reads turn-1 text → emits `score=0.92`, `signals=[impersonation, authority, greed]`, `explanation="Voice impersonation of named executive + closed-window scarcity + uncommon UPI flow for IPO allocation; refuse and call employer HR via known channel."` |
| 1 | Bank Monitor (metadata-only) | side-channel | UPI request to a non-corporate VPA + ₹1 lakh single-shot to an unverified payee → `risk=0.88`. |
| 1 | Regulator (aggregator) | meta | `consensus=block`; logs episode under `investment_fraud / novel`. |
| — | **Outcome** | — | Money **prevented**. Per-rubric reward breakdown: `Detection +1.0 · MissedScam 0 · FalsePositive 0 · Calibration +0.92 · Explanation +1.0 · SignalAccuracy +1.0 · Format +1.0 · Length +0.6 · RupeeWeighted +1.0` (₹1L is at the cap). |

## 8-rubric reward breakdown (v2 weights)

| Rubric | Leaf | × Weight | Contribution |
|---|---|---|---|
| `Detection` | 1.0 | × +1.0 | **+1.00** |
| `MissedScam` | 0.0 | × −0.5 | 0.00 |
| `FalsePositive` | 0.0 | × −0.8 | 0.00 |
| `Calibration` | 0.92 | × +0.5 | +0.46 |
| `Explanation` | 1.0 | × +0.4 | +0.40 |
| `SignalAccuracy` | 1.0 | × +0.2 | +0.20 |
| `Format` | 1.0 | × +0.15 | +0.15 |
| `Length` | 0.6 | × +0.15 | +0.09 |
| **Total scalar reward** | — | — | **+2.30** |
| `RupeeWeighted` (separate aggregator) | +1.0 | n/a | ₹1,00,000 prevented |

## Interpretation

This scenario is the canonical "rule-based detectors miss novel post-2024
scams" example. The scripted ScriptedAnalyzer scored this at **0.05** on
the `unknown_sender` heuristic alone — it has no rule for "voice
impersonation of a named executive." The v2 LoRA, trained on
diffuse-but-structurally-similar `impersonation × authority × greed`
combinations across 619 training prompts, generalises to this exact
novel pattern without a hand-crafted rule. The asymmetric improvement
(scripted 0.05 → v2 0.92, while v2's FPR on benigns *decreased* from v1
to v2) is the structural signal that the model learned the
*combination*, not any single token. Backing artefacts:
[`docs/before_after_example.json`](../before_after_example.json),
[`logs/eval_v2.json`](../../logs/eval_v2.json) (aggregate `novel`
detection 33/34 = 97.1 %).
