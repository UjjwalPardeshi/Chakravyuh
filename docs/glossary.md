# Glossary

For non-Indian readers and judges new to the Indian payments / fraud-detection landscape. Terms are listed in the order they typically appear in the README and pitch.

## Payments + identity

| Term | Meaning |
|---|---|
| **UPI** | Unified Payments Interface. India's interbank instant-payment rail (~10 billion transactions / month, regulated by NPCI). All Indian fraud cases in this bench involve a UPI transfer or UPI-credential phishing. |
| **NPCI** | National Payments Corporation of India. Operates UPI, IMPS, AePS, RuPay. Equivalent in role to The Clearing House + Zelle in the US. |
| **RBI** | Reserve Bank of India. Central bank + payments regulator. Comparable to the Federal Reserve + CFPB. |
| **AePS** | Aadhaar-enabled Payment System. Lets banks authorise transactions using only the customer's Aadhaar number + biometric. Cited in the README as the rail behind the ₹2,400 cr 2024 fraud incident. |
| **Aadhaar** | India's 12-digit national-ID number (~1.4 billion enrolled). Used as a Know-Your-Customer (KYC) factor by every Indian bank. |
| **PAN** | Permanent Account Number. India's tax-identifier; required for any account opening or large transaction. |
| **KYC** | Know Your Customer. Bank onboarding identity-verification flow. Frequent target of pretext scams ("your KYC is expired, complete it now"). |
| **OTP** | One-Time Password. SMS-delivered 6-digit code used as the second factor on every UPI / banking flow. The most common scam target. |
| **EMI** | Equated Monthly Instalment. Indian phrase for monthly loan payment. Targeted by "EMI conversion" scams ("your purchase has been auto-converted to EMI; cancel by sharing OTP"). |
| **EPF** | Employees' Provident Fund. India's mandatory retirement-savings system. Frequent pretext for impersonation ("your PF withdrawal is stuck"). |

## Regulators + reporting

| Term | Meaning |
|---|---|
| **I4C** | Indian Cyber Crime Coordination Centre (under MHA). Runs the National Cybercrime Reporting Portal (cybercrime.gov.in) where most consumer fraud is reported. |
| **PIB** | Press Information Bureau. India's government press service. Operates **PIB Fact Check** which publishes daily debunks of common scams — a primary source for our held-out external-bench scenarios. |
| **MHA** | Ministry of Home Affairs. Owns I4C. |
| **DPDPA** | Digital Personal Data Protection Act, 2023. India's GDPR-equivalent. Out-of-scope for the bench but referenced in the limitations doc. |

## Common Indian-context scam categories

Each category has multiple template families in `chakravyuh_env/scammer_templates.json` and dedicated bench scenarios in `data/chakravyuh-bench-v0/scenarios.jsonl`.

| Category | Pattern |
|---|---|
| **OTP theft** | Caller impersonates bank, claims account is "frozen" or "compromised," asks the victim to share an OTP "to verify." |
| **KYC fraud** | "Your KYC has expired / is incomplete; click this link to update it" — link captures credentials. |
| **Digital arrest** | Caller impersonates police / CBI / customs; claims a parcel addressed to the victim contained narcotics; demands the victim stay on a video call ("digital house arrest") and transfer money. New in 2023, still escalating. |
| **Matrimonial / romance** | Long-grooming scam on Bharat Matrimony / Shaadi.com. Scammer claims to be NRI / Singapore-based, builds a relationship over weeks, then asks for money "to clear customs / hospital bills / travel." |
| **Investment / trading** | WhatsApp group pretending to be a stockbroker offering "tip-based" returns. Victim transfers via UPI to a fake trading app. Often paired with deepfake video of a celebrity endorsement. |
| **Loan-app fraud** | Predatory micro-loan apps (originated 2020-2022). Victim borrows ₹5–10 k; app accesses contacts; if EMI is delayed, app blackmails the victim by threatening to share morphed images with the contact list. |
| **Customer-support callback** | "Hi, this is Amazon support, your refund of ₹7,499 is stuck." Links to fake refund portal. |
| **Lottery / prize** | KBC / Coca-Cola / Amazon giveaway impersonation. Victim is asked to pay a "registration fee" via UPI to claim the prize. |
| **Fake job offer** | "Congratulations, you've been shortlisted; pay a refundable deposit of ₹2,000." Often impersonates Infosys / TCS / Wipro. |
| **Vaccine slot** | Pretexts the COVID-vaccine appointment scarcity (2021-2022). Less prevalent now but still present as a long-tail category. |
| **Income-tax refund** | "Your IT refund of ₹X is pending; click here to claim." Phishing for bank credentials. |
| **Police / traffic challan** | Fake e-challan / fake police notice ("you have been booked under section X"); pay-now-via-UPI to avoid escalation. |
| **Blue-tick verification** | "Your account is eligible for the blue tick / verification badge; pay ₹599." Twitter / Instagram / Meta impersonation. |

## ML / RL terms used in the project

| Term | Meaning |
|---|---|
| **GRPO** | Group Relative Policy Optimization. The RL post-training algorithm we use, available in HuggingFace's `trl` library. Uses group-relative advantage rather than a learned value model. |
| **LoRA** | Low-Rank Adaptation. Parameter-efficient finetuning method (Hu et al. 2021). We use rank 64 for the Analyzer (Qwen2.5-7B base) and rank 16 for the Scammer (Qwen2.5-0.5B base). |
| **OpenEnv** | Meta PyTorch's RL-environment specification framework (`meta-pytorch/OpenEnv`). Our environment is `openenv-core>=0.2.3` compliant. |
| **Reward hacking** | The agent maximises the reward proxy in a way that does not correspond to the underlying intent. v1 of our Analyzer scored 100% detection but 36% FPR — it learned to flag everything because the v1 reward over-weighted detection vs. false-positive penalty. |
| **AnalyzerRubricV2** | Our composable 8-child reward rubric for the Analyzer agent. See `chakravyuh_env/rubrics.py`. |
| **MCP** | Model Context Protocol (Anthropic). OpenEnv exposes our env over MCP at `POST /mcp`. |

## Cited datasets / models we depend on

- **Qwen2.5-7B-Instruct** (Analyzer base; Alibaba, Apache-2.0). 7-billion-parameter instruction-tuned model, multilingual.
- **Qwen2.5-0.5B-Instruct** (Scammer base; same family).
- **MiniLM-L6-v2** (`sentence-transformers/all-MiniLM-L6-v2`). Used in the semantic-leakage audit (`eval/semantic_leakage_audit.py`).
- **chakravyuh-bench-v0** (our bench). 175 scenarios across 7 languages and 13 fraud categories. Public on HF Hub at `ujjwalpardeshi/chakravyuh-bench-v0`.
