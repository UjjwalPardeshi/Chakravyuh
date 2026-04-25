# Extending Chakravyuh to Other Fraud Domains

Chakravyuh is engineered to be forked. The 5-agent shape (Adversary / Target / Analyzer / Channel-Monitor / Regulator) and the composable rubric system are domain-agnostic. The expensive, high-value pieces — measurement-first training hygiene, soft-leakage filter, bootstrap CI, MCP-compliant FastAPI — work for any text-based fraud channel.

This guide shows how to fork Chakravyuh to a new domain in **a single weekend**.

---

## When this is the right tool

Use Chakravyuh as a starting point if:

- The domain has a **multi-turn text channel** between adversary and target (chat, email, SMS, IVR transcripts, customer-service tickets).
- Detection is **partially observable** — the analyzer cannot see all signals, only one channel's worth.
- The threat surface is **regional / regulated** — i.e. a bank-side or central-server detector is structurally inadequate (privacy, regulation, latency).
- You want to **post-train an LLM** on the detection task with RL, not just fine-tune.

If your domain is *image fraud* (deepfake KYC selfies), *transactional fraud* (graph-shape detection on tx data), or *single-shot classification* (one SMS, no dialogue) — fork a different repo.

---

## The 5-agent template

| Slot | Chakravyuh role | Generic role | Replace with… |
|---|---|---|---|
| **Adversary** | Scammer | Sends adversarial messages | Phisher (email), call-center scammer (IVR transcript), insurance-claim filer (text claim) |
| **Target** | Victim | Receives + responds | The end-user being attacked, scripted with profile demographics |
| **Analyzer** | On-device LLM | Reads channel, outputs `{score, signals, explanation}` | Same — this is the thing you train |
| **Channel Monitor** | Bank Monitor | Sees a *different* channel; cross-confirms outcome | Insurance-claim adjuster, payment-provider risk model, email-server header analyzer |
| **Regulator** | Rule-weight updater | Aggregates outcomes across episodes; tunes rule weights | Same — meta-agent |

The template is a **two-tier oversight system**: Analyzer and Channel Monitor see *different* slices of the world and must agree on the final outcome. Neither can single-handedly hack the reward.

---

## Step-by-step fork

### Step 1 — Replace the attack and benign corpora

The two files that define your domain:

- [`chakravyuh_env/scammer_templates.json`](../chakravyuh_env/scammer_templates.json) — adversarial templates (e.g. for email-fraud, replace with phishing email patterns)
- `chakravyuh_env/benign_templates.json` — legitimate-looking content that *should not* be flagged (replace with newsletter / receipt / OTP-from-real-bank patterns)

Templates use Jinja-style `{{var}}` placeholders for `amount`, `bank`, `victim_name`, etc. Categories used by Chakravyuh: `otp_theft`, `kyc_fraud`, `impersonation`, `loan_app_fraud`, `investment_fraud`, plus 6 "novel" buckets. Replace with categories from your domain — phishing has `credential_harvest`, `wire_fraud`, `executive_impersonation`, etc.

**Soft-leakage filter** (in `training/grpo_analyzer.py:_filter_soft_leakage`) is domain-agnostic — it min-hashes string similarity against the bench. **Keep it.** Without it, your eval numbers will silently inflate.

### Step 2 — Replace the agent scripts

Three Python files to edit (all under `chakravyuh_env/agents/`):

- [`scammer.py`](../chakravyuh_env/agents/scammer.py) — picks templates, tracks turns
- [`victim.py`](../chakravyuh_env/agents/victim.py) — scripted responses based on demographic profile
- [`bank_monitor.py`](../chakravyuh_env/agents/bank_monitor.py) — reads metadata channel (rename + adapt)

The `Analyzer` agent and `Regulator` are **domain-independent** — leave them as-is unless your action schema needs different `signals` (see Step 3).

### Step 3 — Adapt the action / observation schemas

Edit [`chakravyuh_env/openenv_models.py`](../chakravyuh_env/openenv_models.py):

- `ChakravyuhAction.signals` — list of `Literal[...]` signal names. Replace with your domain's taxonomy (e.g., for email phishing: `urgency`, `credential_request`, `suspicious_link`, `executive_impersonation`, `wire_request`).
- `ChakravyuhObservation` — usually fine as-is; the chat history field is generic.

Make sure to keep these MCP-reserved names *out* of any custom routes: `reset`, `step`, `state`, `close`. Test enforces this — see [`tests/test_mcp_compliance.py`](../tests/test_mcp_compliance.py).

### Step 4 — Adapt the rubrics

Edit [`chakravyuh_env/rubrics.py`](../chakravyuh_env/rubrics.py). The 5 rubrics are well-shaped templates:

| Keep | Possibly adapt |
|---|---|
| `DetectionRubric` (early flag of true positive) | Threshold on `detected_by_turn` may differ — chat is 6 turns, email is 1 |
| `MissedScamRubric` | Outcome variable name (`money_extracted` → `claim_paid`, `data_exfiltrated`, etc.) |
| `FalsePositiveRubric` | Weight depends on domain — high in low-volume / regulated domains, lower in high-volume |
| `CalibrationRubric` | The `benign_target=0.1` assumption is universal |
| `ExplanationRubric` | The signal-cross-reference logic is universal — just point it at your taxonomy |

**Key principle:** keep the *count* at 5 and the *independence* between them. v1 → v2 demonstrated that fewer signals collapse to reward hacking.

### Step 5 — Build a domain bench

Hand-author 100–200 scenarios. Per-difficulty buckets (`easy` / `medium` / `hard` / `novel`) are the most useful structure — they let you measure generalization rather than memorization.

**Soft-leakage filter must run before training.** Document the resulting `n_filtered` in your `data/<bench>/README.md`.

### Step 6 — Train

The training script ([`training/grpo_analyzer.py`](../training/grpo_analyzer.py)) is domain-independent given the rubric and template files above. Swap in your `.[llm]` extras and run:

```bash
python training/grpo_analyzer.py \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --train-file data/<your_corpus>.jsonl \
  --output-dir checkpoints/your_domain_v1/ \
  --reward-profile v2  # use the anti-collapse profile from day 1
```

### Step 7 — Eval

```bash
python eval/mode_c_real_cases.py \
  --model-id checkpoints/your_domain_v1/ \
  --bench data/<your_bench>/scenarios.jsonl \
  --output logs/eval_your_domain.json

python eval/bootstrap_ci.py \
  --eval-file logs/eval_your_domain.json \
  --iterations 10000 \
  --output logs/bootstrap_your_domain.json
```

Inspect `eval_your_domain.json`. If detection ≥ 95 % across all difficulties uniformly with FPR > 20 %, **you have v1's reward-hacking fingerprint.** Apply the v2 fix (FP penalty −0.8, calibration 0.5, format reward denied on benign-flagged-scam, KL β = 0.15) and retrain.

---

## Concrete fork ideas

| Domain | Adversary | Target | Channel Monitor | Real-world stakes |
|---|---|---|---|---|
| **Indian KYC fraud (Aadhaar / DL spoofing)** | Identity fraudster | KYC desk | UIDAI verification API | Low-thousands of crore/year |
| **Insurance claim fraud (text-claim)** | Fraudulent filer | Claims handler | Loss-adjuster (sees photos) | $100B/yr globally |
| **Customer-support social engineering** | Pretexter | Support agent | Help-desk system (sees account history) | High blast radius |
| **B2B wire-fraud / BEC** | Executive impersonator | Finance team | Bank wire-screening | $50B/yr globally |
| **Romance / matrimonial scam** | Scammer | User | Platform moderation queue | Thin individual loss × many users |
| **Job-app fraud (loan-app, refund-app)** | Fraudster running a fake app | App user | App-store review pipeline | Growing fast in IN, BR, ID |

For each: the 5-agent template, soft-leakage filter, bootstrap CI, and v2 reward profile transfer directly. The bench and templates are the only domain-specific work.

---

## What you will have to write yourself

- The bench (100–200 scenarios with `easy/medium/hard/novel` labels).
- The scammer + benign template corpora.
- The signal taxonomy in `openenv_models.py`.
- A short `data/<bench>/README.md` that documents provenance — *especially* if you use any commercial / regulated source. **Cite RBI / NCRB / industry-report sources when possible.**

What you do **not** have to write: the env contract, the FastAPI server, the OpenEnv compliance, the rubric base classes, the soft-leakage filter, the bootstrap CI, the CI workflow, the MCP compliance test, the responsible-use scaffolding.

---

## When you publish

Three asks:

1. **Cite us** in your `CITATION.cff` (the entry from our [`CITATION.cff`](../CITATION.cff) plus your fork's domain).
2. **Open an issue** on this repo with a link to your fork — we'll list it in the README's "Forks & Extensions" section.
3. **If your domain is regulated** (banking, insurance, healthcare), make sure your `RESPONSIBLE_USE.md` covers the dual-use considerations specific to your channel. Our [`RESPONSIBLE_USE.md`](RESPONSIBLE_USE.md) is a starting template.

Building scalable-oversight infrastructure for fraud detection is a cooperative game. The more domains the same template covers, the stronger the meta-claim that *measurement-first reward design* generalizes beyond UPI.
