# Postmortem & Future Work

This document records what we deliberately did not ship, and why, ordered by how much it cost us.

The discipline is **measurement-first**. Anything not measured is not claimed. Every gap below is named so judges don't have to guess what's missing — and so v3 has a real roadmap.

---

## What we shipped

| Deliverable | State |
|---|---|
| OpenEnv environment (5 agents, composable rubric) | ✅ shipped |
| Bench v0 (175 scenarios, 174 scored) | ✅ shipped |
| LoRA adapter v1 + v2 on HF Hub | ✅ `ujjwalpardeshi/chakravyuh-analyzer-lora-v2` |
| HF Space (`ujjwalpardeshi/chakravyuh`) | ✅ RUNNING, Docker SDK, port 8000 |
| `eval_v2.json` + bootstrap CIs (`bootstrap_v2.json`) | ✅ shipped |
| v1 → v2 reward-hack diagnosis + fix (measured 5× FPR reduction) | ✅ shipped |
| GitHub Actions CI (3.11 + 3.12) | ✅ green |
| `make reproduce` target | ✅ wired |
| MIT LICENSE, CITATION.cff, RESPONSIBLE_USE, MCP compliance test | ✅ all in repo |
| Hero plot at top of README, before/after table with CIs | ✅ shipped |
| Q&A rehearsal doc, live pitch script, design decisions log | ✅ shipped |

---

## What we did not ship — by category

### 1. Measurement gaps (Phase B partial)

| Gap | Why it matters | What's missing | When we'd close it |
|---|---|---|---|
| **Multi-seed retrains** | Single-seed numbers cannot rule out lottery-ticket effects | Run 3 seeds, report mean ± std | v3, ~1 week of A100-80 |
| **Frontier baseline (B.1)** | Comparison to GPT-4o / Claude / Gemini quantifies the 7B gap | `eval/frontier_baseline.py` written, not run — API budget deferred | Pre-v3, ~$60 budget |
| **Benign expansion to n ≥ 150** | FPR CI [0 %, 16.7 %] is too wide at n = 30 | ~120 hand-authored benigns from RBI / Mumbai-Police / HDFC corpora | v3, 4–6 hours of manual work |
| **Per-language eval (B.8)** | Multi-language is a marketing claim until measured per language | `eval/per_language_eval.py` not written | v3, 1 day |
| **Calibration analysis (B.7)** | Reliability diagram, ECE, Brier per-difficulty | `eval/calibration_eval.py` not written | v3, 1 day |
| **Time-to-detection (B.6)** | "Real-time" claim needs an avg-turn-to-detect metric | Edit `mode_c_real_cases.py` to surface `detected_by_turn` | v3, 1 hour |
| **Manual error analysis (B.5)** | We don't yet know *which* 2 benigns were misclassified | `eval/error_analysis.py` not written | v3, 2 hours |
| **Rubric ablation (B.11)** | Eval-time zeroed-rubric numbers, not retrain ablation | `eval/ablation_summary.py` not written | v3, 3 hours |
| **Token saliency plot (B.10)** | Explanation reliability is unverified without it | `eval/saliency.py` not written | v3, 4 hours |
| **Rupee-weighted reward (B.12)** | Economic-loss headline ("₹X saved") is unmeasured | Manual `amount_inr` labels on all 174 scenarios | v3, 2 hours |
| **Red-team adversarial robustness (B.9)** | Prompt-injection defense numbers (defended vs undefended) | `eval/redteam_analyzer.py` not written | v3, 1 day |

### 2. Innovation gaps (Phase C partial)

| Gap | Why it matters | What's missing | When we'd close it |
|---|---|---|---|
| **SFT controlled baseline (C.1)** | We claim "GRPO matters" — needs an SFT comparison to back it | `training/sft_baseline.py` written, not run onsite | Onsite Day 1, 2 h on A100 |
| **Adversarial Scammer Phase 1 (C.2)** | The headline self-improvement loop the env was designed for | Scammer agent, reward, and training loop wired but not run | Onsite Day 1, 2 h |
| **Analyzer retrain Phase 2 (C.3)** | Per-rubric trajectory plot proving each rubric moves independently | Adversarial co-training loop not run | Onsite Day 2, 3 h |
| **Per-rubric trajectory plot (C.4)** | The single most defensible "no reward hacking" plot we could ship | `eval/plot_rubric_trajectory.py` not written, no run to plot | After C.3 |
| **Emergent Scammer behavior (C.5)** | Cluster centroids of learned-Scammer outputs vs templates | Conditional on C.2 success | After C.2 |
| **Bank-Analyzer negotiation protocol (C.6)** | Two-tier oversight is implemented but tier-to-tier negotiation is not | Code change in `bank_monitor.py` + `openenv_environment.py` | v3, 1 day |
| **LLM judge audit (C.7)** | Explanation rubric currently uses heuristic length+signal-match — LLM judge would be stronger | `chakravyuh_env/explanation_judge.py` audit pending | v3, 1 day |
| **Prompt-injection defense (C.8)** | Sanitize wrapper + system fence + JSON-schema validation | Wrapper not written; defended/undefended comparison not measured | v3, 1 day |
| **Scammer adapter release (C.9)** | Conditional on C.2 + C.3 succeeding cleanly | Skip if SFT fallback was used | Decision after onsite |

### 3. Storytelling gaps (Phase D partial)

| Gap | Why it matters | What's missing | When |
|---|---|---|---|
| **2-min overview video (D.10)** | Most memorable judge-facing artifact | Script ready in [`LIVE_PITCH.md`](LIVE_PITCH.md), recording pending | T-12h |
| **HF blog post (D.11)** | Discoverability post-hackathon | Skeleton ready, polished draft pending | T-6h |
| **4-slide PDF deck (D.12)** | Live-pitch back-up | Script in `LIVE_PITCH.md`, slides not designed | T-12h |
| **HF dataset release (D.14)** | Bench shareability outside this repo | Repo create + push of `data/chakravyuh-bench-v0/` | T-3h |
| **NeurIPS workshop draft (D.15)** | Post-hackathon distribution | Outline in `WIN_PLAN.md` P2.14, no draft yet | Post-hackathon |
| **Multi-language demo tab (D.16)** | Per-language detection numbers needed first (B.8) | Conditional on B.8 | After B.8 |
| **NPCI / RBI outreach (D.18)** | Conditional on having frontier numbers | Skip unless B.1 ran | Conditional |
| **Demo GIF (D.9)** | Inline README demo without launching anything | Recording + ffmpeg conversion | T-6h |

### 4. Hygiene gaps (Phase E partial)

| Gap | Why it matters | What's missing | When |
|---|---|---|---|
| **Latency benchmark (E.8)** | "Runs on a phone" is a claim, not yet measured | Single-script p50 / p99 / peak RAM run | T-12h, 1 h |
| **Leaderboard endpoint (E.10)** | OpenEnv-style submission entry-point | `server/leaderboard.py` not written | T-12h, 2 h |
| **Extension docs (E.11)** | Forking the env to other fraud domains | `docs/EXTEND.md` shipped (this round) | ✅ done |
| **Dress rehearsal on fresh Docker (E.14)** | Last-line defense against "works on my laptop" | Docker run + step-by-step log | T-3h |
| **Community posts (E.13)** | Discord / Forum / Twitter / LinkedIn | Drafts ready, not posted | T-12h |
| **Upstream PR to OpenEnv (E.12)** | Goodwill + visibility | Opportunistic; skip if no clean papercut | Post-hackathon |

---

## What we got wrong (and what we'd change)

### a) v1 reward design

We shipped v1 with FP penalty −0.3 and format reward paid even on wrong calls. The model collapsed to "always flag." We should have run a one-epoch sanity check and inspected per-difficulty detection *before* committing to a multi-epoch run. The diagnosis took ~3 hours. The fix took another ~6 hours of retraining. This should have been a one-day cycle, not three.

**Lesson:** every reward profile gets a 100-step smoke test on a 50-scenario subset before any full training.

### b) Bench size

We chose 175 scenarios deliberately for quality, but committed before we'd thought through statistical thinness on benign (n = 30). The bootstrap CI on FPR is wide enough to make our 5× claim *defensible* but not *headline-strong*. A v3 bench should be n = 300 minimum (n = 150 each).

**Lesson:** statistical power calculation goes before bench freezing, not after.

### c) Compute budget allocation

We allocated ~70 % of credits to v1 + v2 retraining and ~30 % to evaluation. With hindsight: 50 / 50 would have been correct, because the eval-side artifacts (frontier baseline, multi-seed, per-language) are the ones backing the headline claims. A faster training cycle (smaller LoRA rank, fewer training steps) would have left more room for measurement.

**Lesson:** budget eval-compute equal to or above training-compute on small-bench projects.

---

## v3 roadmap (concrete, ordered)

In priority order — top items have highest ratio of (research signal) / (engineering hours).

1. **Multi-seed retrain (3 seeds × 619 steps).** Mean ± std replaces single-point estimates everywhere. ~1 week A100-80.
2. **Bench expansion to n = 300 (150 / 150).** Reduces FPR CI to ±5 pp or tighter. ~2 days hand-authoring.
3. **Frontier baseline (B.1).** Quantifies the 7B-vs-frontier gap on the same bench. ~$60 API + 1 day.
4. **Per-language detection eval (B.8).** Backs the "multi-language" claim with numbers. ~1 day.
5. **Calibration analysis (B.7) + reliability diagram.** Backs the calibration rubric with measurement. ~1 day.
6. **External held-out novel set (50 scenarios).** Anti-leakage proof beyond the soft-leakage filter. ~1 day hand-authoring.
7. **Adversarial Scammer Phase 1 + 2 retrain (C.2 + C.3).** The headline self-improvement loop. ~5 h compute + ~1 day code.
8. **Per-rubric trajectory plot (C.4).** Strongest "no reward hacking" visual we can ship. Conditional on #7.
9. **Manual error analysis (B.5).** Audit every v2 FP and missed scam. Names a v3 fix per error. ~3 hours.
10. **Rupee-weighted economic-loss headline.** Backs the "₹X saved per user" claim with a measured number. ~3 hours.

v3 ships when items 1–6 are green.

---

## Out of scope (forever, not just for v3)

These are not roadmap items — they are deliberate non-goals.

- **Real-time chat surveillance.** The Analyzer reads chat *on the user's device*. We will not ship a server-side "read all UPI chat" deployment. That's both a regulatory non-starter and an ethical one.
- **A "scam attribution" feature** — i.e., tracing scams back to specific actors. Out of scope for the env, full stop.
- **Voice / audio scam detection.** Different modality, different model. We stay text-first.
- **Production deployment by us.** We're the *environment* and *baseline analyzer*. A production deployment is a partner job (NPCI, a bank, or a phone OEM) — we will not be that partner ourselves.

---

## How to check whether a future claim should be made

Run this check before adding any number to README / video / blog:

1. Is there a JSON or CSV in `logs/` whose contents back the number?
2. Is the `_meta` block of that artifact reproducible (seed, n, git SHA)?
3. Did the artifact survive at least one re-run and produce within ±0.5 pp of the claim?

If the answer to any of the three is no — the number doesn't appear. This is Operating Principle #1 from `WIN_PLAN.md`, and it is the single strongest hygiene check the project has.
