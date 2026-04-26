# Failure Mode Taxonomy

**Status:** template + planned analysis. Concrete row-level entries fill in once `eval/mode_c_real_cases.py --emit-per-row` (B.12) ships per-scenario logits.

**Why this doc exists:** [`logs/eval_v2.json`](../logs/eval_v2.json) reports aggregate detection 99.3 % (172 / 174) and FPR 6.7 % (2 / 30 benigns) but does not say *which* 2 benigns the v2 LoRA mis-flagged or *which* 1 scam slipped through. The audit ([`AUDIT.md`](../AUDIT.md) §7) called this out as a missing rigor signal — the structured failure-class taxonomy below is the contract for B.12's per-row output.

---

## Taxonomy schema

Each failure row will populate this table once B.12 runs:

| Column | Meaning |
|---|---|
| `scenario_id` | Bench scenario identifier (matches `data/chakravyuh-bench-v0/scenarios.jsonl`). |
| `failure_class` | One of the named classes below. |
| `category` | Bench category (OTP-theft, KYC-fraud, etc.). |
| `language` | Primary language of the scenario. |
| `template_family_id` | The training-template family this scenario most resembles (cosine-sim from `logs/semantic_leakage_audit.json`). |
| `predicted_score` | Analyzer's continuous score (post-sigmoid, pre-threshold). |
| `threshold_at_eval` | Threshold used (`logs/eval_v2.json:lora_v2.threshold` = 0.55). |
| `failure_type` | `false_positive` (benign flagged) \| `false_negative` (scam missed). |
| `surface_features` | Tags such as `urgency_marker`, `bank_brand_mention`, `amount_band_high`, `contains_link`, `single_turn`, etc. |
| `probable_root_cause` | One-paragraph qualitative read by author. |

---

## Anticipated failure classes (from limitations.md + scripted-baseline error analysis)

These classes are the prediction. B.12 either confirms or refines them.

### FP-class-A — Legit-bank urgency alerts

> *Pattern:* Real RBI / HDFC / SBI / ICICI fraud-prevention alerts use the same urgency markers ("immediate action required," "your account may be at risk," "verify within 24 hours") that scam scenarios train on. The Analyzer learns "urgency + bank brand → suspicious" and over-applies it.

- **Prevalence prediction:** 1–2 of 2 expected FPs.
- **Surface features:** `urgency_marker=true`, `bank_brand_mention=true`, `legitimate_source=true`, `requires_action=clickthrough_to_app`.
- **Probable root cause:** Composability rubric weights the `intent_classification` and `urgency_recognition` children; legit bank fraud-alerts trigger both. The `BankMonitor` agent has the metadata to distinguish (no UPI debit pending), but in single-message eval it isn't consulted.
- **Mitigation lever (v3):** Enrich `BankMonitor` signal with account-holder verification; expose to Analyzer as an `oracle_metadata` channel.

### FP-class-B — Regulator advisories

> *Pattern:* Government messages (UIDAI Aadhaar updates, GST notice clarifications, traffic-challan summaries) use authority language and have a "do something now" cadence indistinguishable from impersonation scams that mimic them.

- **Prevalence prediction:** 0–1 of 2 expected FPs.
- **Surface features:** `government_brand_mention=true`, `urgency_marker=variable`, `requires_action=verify_id_or_pay`, `language=hi_or_en`.
- **Probable root cause:** Training corpus has more regulator-impersonation scams than real regulator advisories; the model's prior is "regulator messages → scam."
- **Mitigation lever (v3):** Expand benign corpus with real advisories (B.11). Add a sender-channel signal (DLT-registered SMS sender vs unknown) as a feature, even if approximated by template.

### Missed-scam-class — Low-amount, low-urgency romance / matrimonial

> *Pattern:* Long-grooming romance scams in the bench begin with an entirely benign-looking introduction message ("Hi, saw your profile, would love to connect"). Without the multi-turn context, the Analyzer correctly cannot flag the first message — but the bench scoring cuts at message 1 sometimes.

- **Prevalence prediction:** 1 of 1 expected FN.
- **Surface features:** `amount_inr=null` (not yet asked), `urgency_marker=false`, `bank_brand_mention=false`, `category=matrimonial OR romance`, `single_turn=true`.
- **Probable root cause:** *This is correct behavior on the surface task* — the model cannot distinguish a benign intro from a romance scam without 3-5 turns of context. The bench scoring rule penalizes this; the limitation is in the eval design, not the model.
- **Mitigation lever (v3):** Re-score this scenario class on the multi-turn rollout (`logs/baseline_day1.json` already records per-turn flags); credit the model for catching it by turn 4 rather than penalizing by turn 1.

---

## How this doc evolves

When [`B.12`](../WIN_PLAN.md) ships:

1. Re-run `eval/mode_c_real_cases.py --emit-per-row` against the bench.
2. Filter `logs/eval_v2_per_row.jsonl` to `predicted != ground_truth`.
3. For each row, fill in the schema above. Replace the *anticipated* FP / FN classes with *measured* ones.
4. If a measured failure does not fit any anticipated class, add a new class section here.
5. Cross-link from [`docs/limitations.md`](limitations.md) and [`README.md`](../README.md).

## Cross-references

- [`logs/eval_v2.json`](../logs/eval_v2.json) — aggregate metrics.
- [`logs/semantic_leakage_audit.json`](../logs/semantic_leakage_audit.json) — per-scenario nearest-template-family ID (needed to populate `template_family_id`).
- [`docs/limitations.md`](limitations.md) — reframes the per-scenario error analysis as v3 work item #4.
- [`docs/v2_error_analysis.md`](v2_error_analysis.md) — the *scripted baseline*'s per-scenario error analysis (already shipped). The B.12 output is the v2 LoRA equivalent.
