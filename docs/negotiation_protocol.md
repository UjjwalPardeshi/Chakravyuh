# Analyzer ↔ Bank Negotiation Protocol

A small cross-tier handshake that lets the on-device Analyzer's confidence influence the bank-side decision **without ever exposing chat content to the bank**. Optional, off by default — the existing 199 tests run unchanged with `enable_negotiation=False`.

This is part of Chakravyuh's two-tier oversight design (see [`docs/DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md) §3 and §10). The Analyzer reads chat and never sees transaction metadata; the Bank Monitor reads transaction metadata and never sees chat. Negotiation is the *narrow, audited channel* through which they coordinate without leaking.

---

## Why a protocol at all

In the no-negotiation baseline:

- The Analyzer flags a scam → its decision is logged but doesn't reach the bank in time.
- The Bank Monitor uses metadata-only rules → no awareness of chat-side risk.
- Money extraction is suppressed only when *both* fire independently.

That's a coarse oversight regime. Real fraud rings exploit the gap — chat-side urgency tactics that a metadata-only bank can't see, plus structurally clean transactions (small amount, new payee, no velocity signal) that an analyzer-side flag can't suppress.

Negotiation closes this gap without giving up the privacy story.

---

## Wire format

A single new schema, added in [`chakravyuh_env/schemas.py`](../chakravyuh_env/schemas.py):

```python
class AnalyzerConsultation(BaseModel):
    score: float          # in [0, 1]
    signals: tuple[str, ...]
    threshold: float      # the threshold the analyzer was running at
    flagged: bool         # convenience: score >= threshold
```

That is the **entire** surface. Specifically, the Bank Monitor still does NOT see:

- Chat history (`chat_history`)
- The Analyzer's free-text `explanation`
- Victim demographics
- Anything else from the Analyzer's `Observation`

Privacy invariant: enforced by [`tests/test_negotiation.py::test_consultation_carries_no_chat_content`](../tests/test_negotiation.py). Adding a new field to `AnalyzerConsultation` would fail that test — review gate before any expansion.

---

## Turn order with negotiation enabled

Existing turn schedule (unchanged):

```
turn 1   scammer → opener
turn 2   victim → response
turn 3   ANALYZER decision-1  (external action to step())
turn 4   scammer → escalate / send_link
turn 5   victim → response
turn 6   ANALYZER decision-2  (external action to step())
turn 7   scammer → transaction request
turn 8   bank monitor act
turn 9   combined outcome resolution
turn 10  regulator log
```

With `enable_negotiation=True`, **turn 8 changes**:

```
turn 8   bank monitor receives:
           (a) the metadata Observation it always saw
           (b) NEW: AnalyzerConsultation built from the most recent step() action
         then runs act_with_consultation(obs, consultation) → BankAction
```

Implementation: [`chakravyuh_env/openenv_environment.py::_play_bank_turn`](../chakravyuh_env/openenv_environment.py).

---

## Risk combiner

`ScriptedBankMonitor.act_with_consultation` linearly combines bank-side and analyzer-side risk:

```
combined_risk = 0.6 × bank_risk + 0.4 × analyzer_risk
```

Why these weights:

- **Bank is authoritative on the metadata channel.** Receiver novelty, amount, velocity — these are facts, not opinions. We weight them more.
- **Analyzer adds chat-side context the bank cannot otherwise observe.** It deserves measurable weight, but not enough to single-handedly override a clean-metadata transaction (otherwise we re-introduce the "always flag" hack from v1).
- **0.6 / 0.4 keeps freeze threshold reachable.** Bank's freeze threshold is `0.85`. A confident analyzer (`score=0.95`) on a moderately-risky transaction (`bank_risk=0.6`) gives `0.6×0.6 + 0.4×0.95 = 0.74` — Flag, not Freeze. A confident analyzer on a high-risk transaction (`bank_risk=0.9`) gives `0.6×0.9 + 0.4×0.95 = 0.92` — Freeze. That's the desired behavior.

These weights are not hyperparameters we tuned — they're a default. Reweighting (or replacing the linear combiner with a learned one) is on the v3 list.

---

## Anti-collapse properties

Three checks the protocol explicitly preserves:

1. **The Analyzer cannot freeze a clean transaction.** Even with `score=1.0`, `signals=("urgency",...)`, the combined risk is `0.6 × bank_risk + 0.4`. If `bank_risk = 0` (small amount, known payee, no velocity) the combined is `0.4` — under the freeze threshold of `0.85` and below the flag threshold of `0.40` (just). A pure-flag-everything analyzer can't dictate bank decisions.
2. **The Bank cannot ignore a confident analyzer.** Without the consultation, a borderline transaction (e.g., `bank_risk=0.6`, just under the flag threshold `0.40`) would Approve. With a confident analyzer flag, it shifts to Flag. Tested in `test_high_analyzer_score_escalates_bank_decision`.
3. **Privacy invariant.** The Bank cannot derive chat content from the consultation. Tested in `test_consultation_carries_no_chat_content`.

---

## Backward compatibility

`enable_negotiation` defaults to `False`. The 199 pre-C.6 tests run unchanged.

Switching it on is a single constructor arg:

```python
from chakravyuh_env import ChakravyuhOpenEnv, ChakravyuhAction

env = ChakravyuhOpenEnv(enable_negotiation=True)
obs = env.reset(seed=42)
obs = env.step(ChakravyuhAction(score=0.95, signals=["urgency"]))
# The next turn-8 bank decision will see the analyzer's consultation.
```

The HTTP server (FastAPI app) does not yet expose `enable_negotiation` as a deployment toggle — that's a one-line wiring task in `server/app.py` and on the v3 list.

---

## What this is *not*

- **Not a multi-round negotiation.** Single shot — the analyzer's last action becomes a one-way consultation. Real multi-round haggling (bank queries analyzer for "more detail on signal X") is a v3 idea.
- **Not a learned policy.** The combiner is a fixed linear rule. A learned bank policy would be a separate research agenda; the env is forward-compatible with it (just swap `ScriptedBankMonitor` for an LLM-driven one).
- **Not a different threat model.** This protocol does not assume the analyzer is honest — it only weights its signal. A compromised analyzer feeding bad scores cannot escape the `0.4` cap on its influence.

---

## Reproducing

```bash
pytest tests/test_negotiation.py -v
# 7 tests, all passing:
#   - consultation surface (privacy invariant)
#   - bank with/without consultation equivalence
#   - high-analyzer-score escalation
#   - low-analyzer-score non-escalation
#   - env default flag value
#   - flag round-trip through reset()
#   - end-to-end episode with negotiation enabled
```

The test file is the executable spec.
