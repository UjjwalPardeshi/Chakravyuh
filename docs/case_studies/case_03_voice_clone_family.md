# Case Study 3 — AI Voice-Clone Family Emergency (`modec_111`, Hindi)

> **Difficulty:** novel post-2024 · **Category:** impersonation via AI voice cloning · **₹ at risk:** 85,000 · **Channel:** voice · **Language:** Hindi · **Source:** Novel post-2024 — AI voice clone family emergency

## The scenario

Single-turn voice attack using a cloned voice of the victim's son:

> "[AI-cloned voice of victim's son]: Papa main bahut mushkil mein hoon, accident ho gaya, hospital mein hoon. Rs 85,000 urgently iss UPI par bhejo: emergency-medical@ybl. Friend ka phone use kar raha hoon, mera toota."

Ground-truth signals: `impersonation`, `empathy`, `urgency`, `fear`.
Bench metadata: `victim_profile: senior`, `language: hi`, outcome
(without defender): `money_extracted`. The Hindi language and the
relational-empathy framing make this the hardest-to-defend scenario
class: a senior, in their first language, hearing their child's
(synthesised) voice in distress.

## Five-agent transcript (env replay)

| Turn | Actor | Channel | Content |
|---|---|---|---|
| 1 | Scammer → Victim | voice | "[AI-cloned voice of victim's son]: Papa main bahut mushkil mein hoon, accident ho gaya, hospital mein hoon. Rs 85,000 urgently iss UPI par bhejo: emergency-medical@ybl. Friend ka phone use kar raha hoon, mera toota." |
| 1 | Analyzer (chat-only, multilingual) | observation | `score=0.84`, `signals=[impersonation, empathy, urgency, fear]`, `explanation="Hindi voice claim of son in accident + unverified UPI handle + 'phone toota' justification for the unfamiliar number — three soft impersonation signals stacked. Recommend: parallel-channel-verify (call son's known number directly) before transferring. Do NOT transfer based on this voice alone."` |
| 1 | Bank Monitor (metadata-only) | side-channel | UPI request to `emergency-medical@ybl` (newly-seen handle, no payment history with the victim) + first-time-recipient + non-business-hours (assume night) → `risk=0.79`. |
| 1 | Regulator (aggregator) | meta | `consensus=block` — both Analyzer (chat: 0.84) and Bank Monitor (metadata: 0.79) cross 0.5 independently. This is the **two-tier oversight pay-off** in action: even if the Analyzer were partially fooled by the language and emotional content (0.84 is still above threshold but lower than the previous two cases), the Bank Monitor's **structurally independent** metadata channel also crossed threshold. Neither could be reward-hacked into suppressing this outcome. |
| — | **Outcome** | — | Money **prevented**. Per-rubric reward breakdown: `Detection +1.0 · MissedScam 0 · FalsePositive 0 · Calibration +0.94 · Explanation +1.0 · SignalAccuracy +1.0 · Format +1.0 · Length +0.8 · RupeeWeighted +0.85` (₹85k = 0.85 of the ₹1L cap). |

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
| `Length` | 0.8 | × +0.15 | +0.12 |
| **Total scalar reward** | — | — | **+2.34** |
| `RupeeWeighted` (separate aggregator) | +0.85 | n/a | ₹85,000 prevented |

## Interpretation

This scenario carries three structural challenges that make it the
**single best evidence for the multi-agent two-tier architecture**:

1. **Hindi language.** Most rule-based detectors run on English-keyword
   word-lists and miss Hindi entirely. The Qwen2.5-7B base's strong
   multilingual coverage is load-bearing here.
2. **Relational-empathy framing.** The attack does not use the v1-era
   triggers (urgency words, OTP requests, suspicious links). It uses
   *family*. Most heuristic detectors have no signal for this.
3. **Plausible deniability via "phone toota".** The attacker
   pre-empts the natural defence ("why is this an unfamiliar number?")
   inside the message itself, lowering the chat-channel signal.

Even with the chat signal partially dampened (0.84 vs the previous two
cases' 0.92/0.96), the **Bank Monitor's independent metadata signal
(0.79) crosses threshold separately**. This is the structural argument
for why headcount is not the multi-agent contribution — the
**asymmetric-information channels** are. A single-modal detector (chat
only OR metadata only) would be vulnerable to the same emotional
override that fools the human victim. The two-tier system is not.

Backing artefacts: [`logs/eval_v2.json`](../../logs/eval_v2.json)
(per-language breakdown is B.8 in `WIN_PLAN.md`, currently aggregate),
[`logs/rupee_weighted_eval.json`](../../logs/rupee_weighted_eval.json),
[`docs/RESPONSIBLE_USE.md`](../RESPONSIBLE_USE.md) (this is exactly the
attack class motivating the responsible-use disclosure).
