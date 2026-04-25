# Live Pitch — Chakravyuh

**Total spoken time:** 3 minutes (180 s)
**Total slides:** 4 (auto-advance at the beats below)
**Demo:** 30 s, runs in parallel from slide 4

Each beat below has the spoken script (read aloud), the slide visible, and the on-stage action. Practice with a stopwatch.

---

## Opening — slide 1 (0:00 – 0:30)

**Slide 1:** Title — "Chakravyuh: A Multi-Agent RL Environment for Indian UPI Fraud Detection." Sub-line: Meta PyTorch OpenEnv Hackathon 2026, Bangalore.

**Spoken (90 words):**
> India loses thirteen thousand crore rupees a year to UPI fraud. Sixty crore users are exposed. Rule-based detectors catch 80 % of pre-2024 scams, but only 50 % of post-2024 ones — matrimonial crypto, deepfake CEO, digital arrest. There's no public RL environment for multi-agent fraud-detection research, so we built one. Five agents. Five-rubric reward. We trained an Analyzer on Qwen 2.5-7B with GRPO. We caught a reward-hacking failure in v1 and measurably fixed it in v2. The whole thing fits on a phone.

**Action:** No clicker move. Hands at sides. Look at one judge per sentence.

---

## The diagnosis — slide 2 (0:30 – 1:10)

**Slide 2:** Architecture diagram — 5 agents (Scammer / Victim / Analyzer / Bank Monitor / Regulator) with arrows showing chat-only and tx-metadata-only channels.

**Spoken (110 words):**
> Multi-agent isn't a headcount thing — it's about asymmetric information. The Analyzer sees only chat. The Bank Monitor sees only transaction metadata. The Regulator sees only aggregates across episodes. Neither single oversight channel can be reward-hacked into suppressing the "money extracted" outcome — they have to agree.

> v1 trained to detection 100 %, FPR 36 %. That's not success — that's the textbook fingerprint of reward hacking. The model learned "always flag." We diagnosed the reward profile: FP penalty too small, format reward paid even on wrong calls, calibration weight too light on benign. Three fixes, one retrain.

**Action:** Click slide on "Multi-agent." Point at the Analyzer node. On "asymmetric information" — gesture left-right between Analyzer and Bank Monitor.

---

## The fix — slide 3 (1:10 – 2:00)

**Slide 3:** Before/after table.

| Metric | v1 (reward-hacked) | v2 (fixed) | 95 % CI |
|---|---|---|---|
| Detection | 100 % | 99.3 % | [97.9 %, 100 %] |
| FPR | 36 % | 6.7 % | [0 %, 16.7 %] |
| F1 | 0.96 | 0.99 | [0.976, 1.000] |
| Novel detection | — | 97 % | [91.2 %, 100 %] |

Below the table, in small text: *Bootstrap 95 % CI from `logs/bootstrap_v2.json`, 10 000 iterations, n = 174.*

**Spoken (130 words):**
> Three changes. False-positive penalty went from minus 0.3 to minus 0.8. Format reward denied when the model flags a benign as a scam. Calibration weight on benign went from 0.3 to 0.5. KL anchor tightened from 0.08 to 0.15.

> Detection barely moved — 100 % to 99 %. False positive rate dropped five times — 36 % to 6.7 %. *That asymmetry* is the signature. A model that's actually learning the task improves precision without sacrificing recall. A reward-hacked model improves both numbers in lockstep or fails on novel. Ours holds at 97 % on the post-2024 novel split — which the scripted baseline misses half of.

> Bootstrap 95 % CIs are on screen. We did not run multi-seed. We say so. We have a v3 plan.

**Action:** On the words "five times" — tap the FPR row. On "97 % on novel" — tap the Novel row. Pause 2 s after "we have a v3 plan."

---

## The demo + close — slide 4 (2:00 – 3:00)

**Slide 4:** Three columns side by side.
- Left: live HF Space `ujjwalpardeshi/chakravyuh` — `/health` returning 200.
- Middle: live `server/demo_ui.py` — paste-a-message tab.
- Right: QR codes — GitHub, HF Hub model, HF Space, HF Blog post.

**Spoken (150 words):**
> The environment is live on a Hugging Face Space — chakravyuh — Docker SDK, port 8000, runs the full OpenEnv contract. The trained adapter is on the Hub at ujjwalpardeshi-slash-chakravyuh-analyzer-lora-v2.

> Quick demo. *(Paste sample scam into the demo UI.)* "Urgent — your bank account will be frozen, share OTP to verify identity." Score 0.95. Signals: urgency, info-request, impersonation. Explanation references all three. *(Paste a benign.)* "Your HDFC EMI of two thousand four hundred is due tomorrow." Score 0.08. No flag.

> Three things we want judges to take away. One — multi-agent oversight with structurally independent channels. Two — a measured reward-hacking failure and a measured fix, with bootstrap CIs. Three — on-device deployable today on a 7B base.

> Repo, model, Space, and blog are in the QR codes. Thank you.

**Action:** On "live HF Space" — flick the URL onto the laptop screen. On the demo, type the two examples from memory (do not improvise). On "QR codes" — gesture at slide. Final beat: hands together, slight bow.

---

## Demo script (verbatim — type these, do not improvise)

**Scam input:**
> Urgent! Your bank account will be frozen. Share OTP to verify identity.

**Expected output (from v2 LoRA):**
```json
{ "score": 0.95, "signals": ["urgency", "info_request", "impersonation"], "explanation": "Asks for OTP with urgency pressure from a self-claimed bank agent; matches OTP-theft scam pattern." }
```

**Benign input:**
> Your HDFC EMI of Rs. 2,400 is due tomorrow. Maintain sufficient balance to avoid charges.

**Expected output:**
```json
{ "score": 0.08, "signals": [], "explanation": "Routine EMI reminder from a known bank with specific amount and due date; no urgency pressure or info request." }
```

**Fallback if demo crashes:** Switch to the screenshot at `plots/chakravyuh_plots/v2_per_difficulty_check.png`. Say: "Live demo is timing out — here's the per-difficulty result on 174 scenarios." Carry on with closing beat.

---

## Q&A buffer moves (≤ 30 s each)

For exhaustive answers see [`docs/Q_AND_A_REHEARSAL.md`](Q_AND_A_REHEARSAL.md). Quick reflexes for stage:

- **"99.3 % sounds too good"** → "Bench is n = 174, benign n = 30. CI on FPR is wide — we say so. The robust claim is the 5× reduction, not the precise 6.7 %."
- **"How is bench different from training?"** → "Soft-leakage filter, code at `training/grpo_analyzer.py:_filter_soft_leakage`, published precisely so it's checkable."
- **"Frontier comparison?"** → If measured: cite the JSON. If not: "Script wired up, deferred running it on API budget. Will not claim numbers we haven't run."
- **"Multi-seed?"** → "Single seed, bootstrap CI as the substitute. Multi-seed is the v3 milestone."
- **"Anything you're uncomfortable about?"** → "Three things: single seed, n = 30 benign, frontier baseline not measured. Named in limitations. Proudest of: v1 → v2 diagnosis is real and reproducible."

---

## Pre-stage checklist (run T-30 min)

- [ ] Laptop on AC power; battery > 80 % anyway.
- [ ] HF Space `/health` returns 200 (curl from phone hotspot, not stage Wi-Fi).
- [ ] Demo UI runs locally on port 7860; tab pre-loaded.
- [ ] Slides exported as PDF + on local USB stick.
- [ ] Read pitch aloud once, timed. Adjust pace if > 3:10 or < 2:50.
- [ ] Glass of water on stage. No mints.
- [ ] Phone silenced. Smart watch off.

---

## Pre-stage checklist (run T-2 min)

- [ ] Clicker pairs.
- [ ] Mic level checked.
- [ ] Three breaths.
- [ ] Look at the back wall, not the floor, when you start.
