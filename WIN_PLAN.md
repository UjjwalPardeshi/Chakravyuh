# CHAKRAVYUH — REMAINING WORK PLAN (v6, post-audit-v2-no-gpu-batch)

**Project:** Chakravyuh — Multi-Agent RL Environment for Indian UPI Fraud Detection
**Event:** Meta PyTorch OpenEnv Hackathon 2026, Bangalore
**Target:** Rank **#1**

> **Status as of 2026-04-25 (round 2):** All work that could be done locally without Colab / HF GPU credits / API budget is shipped. Remaining items fall into three buckets: **(A) user-action production** (video, slides PDF, notebook execution), **(B) GPU-bound onsite work** (adversarial Scammer, SFT baseline, calibration on real logits), and **(C) API-budget bound** (frontier baseline real run).
>
> **Round 1 (autonomous-execution batch, 2026-04-25)** shipped all P0 README/repo/demo work, every 0-unit eval (red-team, ablation, time-to-detection, error analysis), pre-submit dress-rehearsal log (13/13 gates green), `docs/judge_quickstart.md`, `docs/limitations.md`, and the Marp/Pandoc-ready slide markdown source.
>
> **Round 2 (audit-autonomous-fixes batch, 2026-04-25)** closed the open audit findings: unified the v1/v2 reward system into a single `AnalyzerRubricV2` (8 children, env-default), pinned `flag_threshold` to defeat threshold-tuning exploits, locked training/serving rubric parity into a regression test (`tests/test_v2_reward_parity.py`), shipped the v1↔v2 wow-moment toggle (`server/demo_v1_v2.py` + 5-scenario archived corpus with provenance disclosure), added research endpoints (`/eval`, `/eval/redteam`, `/eval/known-novel`, `POST /diagnose` with full rubric_breakdown), extended ablation to env-rollout source-mode (defends "3-of-5-inert" finding — `explanation` rubric now fires Δ -0.2384 on multi-turn), tightened CI (strict local link-check + allowed-fail external link probe), hardened Dockerfile HEALTHCHECK, and shipped a11y improvements on agent cards. Test count: **273 passed · 2 skipped** (275 collected).
>
> **Round 3 (audit-v2-no-gpu batch, 2026-04-26)** fixed the root cause of the production 404s on `/demo/` and `/eval/*` — `Dockerfile` and `.dockerignore` now COPY `logs/` and `data/` into the runtime image; the silent `_mount_demo` exception swallow now surfaces tracebacks. Shipped the **live red-team wow tab** (`server/redteam_handler.py` + new "🔴 Red-team it yourself" Gradio tab) — same scripted analyzer scoring, two reward profiles (v1 `DEFAULT_WEIGHTS` vs v2 `V2_WEIGHTS`), with an asymmetry badge that surfaces the reward-hacking signature on user input. Tightened OpenEnv contract (importable Pydantic submodels for ChatTurn / TransactionMeta / EpisodeOutcome / RewardBreakdown, `schema_version: "0.2.0"` field, MCP integration tests, JSON round-trip test). Added `/demo/preview` static fallback (boots instantly with the SHA-pinned per-difficulty chart while Gradio warms up) + `.github/workflows/keepwarm.yml` keep-warm cron. Failure-first README hero rewrite + methodological-contribution paragraph. `docs/architecture.md` GitHub-rendered Mermaid + `notebooks/env_exploration.ipynb` GPU-free tutorial (verified end-to-end). LIVE_PITCH tolerance bands replace fragile exact-match expectations; FALLBACK_A and FALLBACK_B pre-staged. Test count: **287 passed · 2 skipped** (289 collected; +14 net new). All in-process gates green; Docker container probe shows all 10 endpoints + `POST /diagnose` return 200 and the new red-team tab is present in `/demo/`. See `docs/dress_rehearsal_log.md` round-3 section.

---

# Operating Principles — Non-Negotiable

1. **Measurement before claim.** No number anywhere unless backed by a JSON artifact in `logs/` or a PNG in `plots/`.
2. **No fabricated numbers — even directionally.** If you didn't measure it, you don't write it.
3. **Cut beats stretch.** "Maybe" is "no" by default.
4. **Adverse-results plan first.** Before each experiment, write the worst-case story.
5. **Honesty is a differentiator.** Calibrated CIs + named limitations win over inflated point estimates.

---

# REMAINING WORK — concrete checklist

## Bucket A — User-side production (you must do these)

These are non-coding tasks. They block the JC submission minimums.

### A.1 — Render slide deck to PDF [BLOCKER for P0 minimums]
- **What:** Convert `docs/chakravyuh_slides.md` to `docs/chakravyuh_slides.pdf`.
- **How:**
  ```bash
  npx -y @marp-team/marp-cli docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf
  # OR: pandoc docs/chakravyuh_slides.md -t beamer -o docs/chakravyuh_slides.pdf -V theme=metropolis
  ```
- **Effort:** ~5 min. **Cost:** 0.

### A.2 — Record 2-minute overview video [BLOCKER for P0 minimums]
- **What:** Unlisted YouTube video, link from README `Submission Materials`.
- **6-beat script** (only mention measured artifacts):
  | Time | Beat |
  |---|---|
  | 0:00–0:15 | Hook: ₹13,000 cr/year UPI fraud, 60 cr users exposed |
  | 0:15–0:40 | 5-agent env, 5 composable rubrics, Analyzer is the only learnable agent |
  | 0:40–1:05 | GRPO loss curve + 5-rubric decomposition + v1 reward-hacking diagnosis |
  | 1:05–1:35 | v1 → v2 fix: 36% → 6.7% FPR (5×), F1 0.96 → 0.99 |
  | 1:35–1:55 | Per-difficulty ramp 50% scripted → 97% v2 on novel; cite frontier numbers ONLY if A.5 ran |
  | 1:55–2:00 | Close: HF Space link, "try it" |
- **Tools:** OBS Studio → DaVinci Resolve / CapCut → unlisted YouTube. Keep <150 MB.
- **Constraint:** Drop any beat whose backing artifact doesn't yet exist.
- **Effort:** 4–6 hrs. **Cost:** 0.

### A.3 — Execute three Colab notebooks end-to-end [BLOCKER for reproducibility floor]
- **Status:** Notebooks are committed but **0 of 39 cells have outputs**:
  `notebooks/v2_retrain_safe.ipynb` (0/13), `notebooks/plots_and_eval.ipynb` (0/15), `training/train_colab.ipynb` (0/11).
- **JC explicitly asks:** *"a working training script using Unsloth or HF TRL, ideally as a Colab notebook so judges can re-run it."* A judge clicking these and seeing naked code will downgrade you immediately.
- **How:** On Colab → Runtime → Run all → File → Download .ipynb (with outputs) → commit & push to GitHub + HF.
- **Eval-only reruns are sufficient** — v2 LoRA is already published on HF Hub.
- **Effort:** 2–4 hrs. **Cost:** ~3–5 Colab compute units.

### A.4 — Final dress rehearsal on fresh Docker [final gate before submit]
- **Why:** Local dress-rehearsal log is green ([docs/dress_rehearsal_log.md](docs/dress_rehearsal_log.md)). The one remaining gate is a **fresh-clone test on a clean image** to catch latent system-dependency surprises.
- **How:**
  ```bash
  docker run -it --rm ubuntu:22.04 bash
  apt update && apt install -y git python3 python3-pip python3-venv curl
  git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
  pip install -e '.[llm,eval]'
  pytest tests/
  uvicorn server.app:app --host 0.0.0.0 --port 8000 &
  sleep 6
  curl -sf http://localhost:8000/health
  curl -sf http://localhost:8000/leaderboard
  curl -sf http://localhost:8000/demo/
  ```
- **Fix every break.** Commit fixes. Then submit.
- **Effort:** ~1 hr. **Cost:** 0.

### A.5 — Frontier baseline real run [Conditional — needs API budget]
- **Status:** `eval/frontier_baseline.py` ready; the previous 1-row scripted-only stub has been renamed `logs/scripted_baseline_n5_archived.csv` so it is no longer mistakable for a frontier comparison. Real run = ~$40–80 OpenAI/Anthropic/Gemini fees.
- **How:**
  ```bash
  export OPENAI_API_KEY=... ANTHROPIC_API_KEY=... GOOGLE_API_KEY=...
  python eval/frontier_baseline.py \
    --models gpt-4o,claude-3-5-sonnet,gemini-1.5-pro,llama-3.1-70b \
    --bench data/chakravyuh-bench-v0/scenarios.jsonl \
    --output logs/frontier_comparison.csv
  ```
- **Adverse plan:**
  - Beat frontier on novel → headline result.
  - Within ~5pp → "competitive at 7B with LoRA."
  - Worse → reframe as "trained smaller model approaches frontier on a specialised domain; v3 work is closing the gap."
- **If you skip this:** REMOVE every reference to `frontier_comparison.csv` from README and pitch — do NOT cite a stub.
- **Effort:** ~2 hrs. **Cost:** $40–80.

### A.6 — Community posts (48h before judging)
- **Channels:** OpenEnv Discord `#show-and-tell`, HF Forum OpenEnv tag, Twitter/X tagging `@MetaPyTorch + @huggingface`, LinkedIn tagging organizers.
- **Effort:** ~30 min. **Cost:** 0.

---

## Bucket B — Onsite GPU-bound (HF credits required)

These elevate the multi-agent claim from rhetoric to evidence.

### B.1 — SFT vs RL controlled experiment ⭐ (P1.14)
- **Why:** Single most defensible research claim. Hackathons reward calibrated reporting.
- **What:** Train SFT-only Qwen2.5-7B on the same 619-example corpus as a binary classifier, compare RL-trained v2 vs SFT on the novel split.
- **How:**
  ```bash
  python training/sft_baseline.py \
    --model-id Qwen/Qwen2.5-7B-Instruct \
    --train-file data/training_corpus.jsonl \
    --output-dir checkpoints/sft_baseline/ \
    --num-epochs 3 --batch-size 8

  python eval/mode_c_real_cases.py \
    --model-id checkpoints/sft_baseline/ \
    --bench data/chakravyuh-bench-v0/scenarios.jsonl \
    --output logs/eval_sft.json
  ```
- **Adverse plans:** RL wins ≥10pp → headline. Within 10pp → "RL marginally outperforms." SFT ties → pivot to "env-as-benchmark." SFT beats → publish honestly; multi-seed v3.
- **Effort:** ~1.5h A100.

### B.2 — Adversarial Scammer training ⭐ (P1.1)
- **Why:** Today only the Analyzer learns. A learning Scammer is the difference between "5 agents" rhetoric and demonstrable multi-agent dynamics. JC Theme #1 textbook example.
- **How:**
  1. Create `chakravyuh_env/agents/learned_scammer.py` (Qwen2.5-0.5B-Instruct + LoRA).
  2. Scammer reward: +1.0 OTP+not-flagged ≤turn5; +0.3 partial; −0.5 flagged ≤turn3; +0.2 novelty bonus (MiniLM-L6 distance from last 500 scams).
  3. Two-phase in `training/adversarial_selfplay.py`:
     - Phase 1: Scammer LoRA, 200 ep vs frozen scripted Analyzer (T4/L4, ~2h)
     - Phase 2: Freeze Scammer, retrain Analyzer LoRA 150 ep with **per-rubric W&B logging** (A100, ~3h) — also produces per-rubric trajectory plot
  4. Plot co-evolution curves: Scammer success vs Analyzer detection over time.
- **Adverse plan:** If full RL collapses, fall back to SFT-generation-only Qwen2.5-0.5B fine-tuned on `scammer_templates.json`; frame as "v3 work."
- **Effort:** ~5h GPU.

### B.3 — Emergent Scammer behavior analysis (P1.15, depends on B.2)
- **What:** Cluster outputs from learned Scammer using sentence embeddings; identify clusters with no template-library analog. Even 1–2 emergent centroids = Theme #1 evidence.
- **How:**
  ```bash
  python eval/scammer_generate.py --adapter <user>/chakravyuh-scammer-0.5b-v1 --n 500 --output data/learned_scammer_corpus.jsonl
  python eval/scammer_emergence.py --generated data/learned_scammer_corpus.jsonl --templates chakravyuh_env/scammer_templates.json --output docs/emergent_behavior_analysis.md
  ```
- **Skip if:** B.2 fell back to SFT-generation-only.
- **Effort:** ~0.5 unit T4.

### B.4 — Process-level (per-turn) rewards (P1.8)
- **What:** Today reward is computed at episode end; HG section 9 asks for per-turn supervision.
- **How:** Add `compute_step_reward(turn_index, action, partial_observation)` to `chakravyuh_env/rubrics.py`. Use in B.2 phase 2 retrain only — do NOT re-run v2 alone.
- **Effort:** 0 (folded into B.2).

### B.5 — Calibration analysis (ECE + reliability diagram) (P1.18)
- **Why:** `CalibrationRubric` is trained for but never reported. Standard AI-safety metric.
- **How:**
  ```bash
  python eval/calibration_eval.py \
    --model-id <user>/chakravyuh-analyzer-lora-v2 \
    --bench data/chakravyuh-bench-v0/scenarios.jsonl \
    --output docs/calibration_analysis.md
  # Produces plots/chakravyuh_plots/reliability_diagram.png
  ```
- **Report:** ECE (target <0.05), reliability diagram, Brier score, per-difficulty.
- **Note:** Needs per-scenario v2 logits (~30 min A100 re-inference). Aggregate-only currently.
- **Effort:** ~1 unit T4 (after re-inference).

### B.6 — Per-language detection breakdown (P1.10)
- **Why:** README claims 7-language support. Prove each works. Be honest about gaps.
- **How:**
  ```bash
  python eval/per_language_eval.py \
    --model-id <user>/chakravyuh-analyzer-lora-v2 \
    --bench data/chakravyuh-bench-v0/scenarios.jsonl \
    --output logs/per_language_v2.json
  # Produces plots/chakravyuh_plots/per_language_detection.png
  ```
- **Effort:** ~1–2 units T4.

### B.7 — Token saliency interpretability (P1.22)
- **What:** Use integrated gradients (captum) to highlight which words triggered the Analyzer's flag.
- **How:**
  ```bash
  python eval/saliency.py \
    --model-id <user>/chakravyuh-analyzer-lora-v2 \
    --example "Urgent! Your bank account will be frozen. Share OTP to verify identity." \
    --output plots/chakravyuh_plots/saliency_example.png
  ```
- **Expected:** Heatmap with "OTP", "urgent", "frozen", "verify" lit up.
- **Effort:** ~1 unit T4.

### B.8 — Latency + memory footprint (P4.7)
- **Why:** Pitch is "on-device, on-phone." Back it with p50/p99 latency + memory.
- **How:**
  ```bash
  python eval/benchmark_inference.py \
    --model-id <user>/chakravyuh-analyzer-lora-v2 \
    --quantize 4bit --batch-size 1 --device cpu --iterations 100 \
    --output docs/latency_memory.md
  ```
- **Report:** p50/p99 per decision, peak RAM, quantized size; compare to mobile (Pixel 8: 8GB RAM).
- **Effort:** 0–1 unit.

### B.9 — Expand benign corpus to n ≥ 150 (P1.5)
- **Status:** `chakravyuh_env/benign_augmented_v2.json` has 81 entries. ~70 more roughly halves Wilson CI on FPR.
- **Sources:** real RBI advisories phrased as urgent warnings, HDFC/ICICI/SBI alert formats, traffic-challan SMS, Amazon/Flipkart delivery, UIDAI Aadhaar updates, GST/IT notices, airline/railway, electricity/water bills.
- **Re-run:** v2 inference on expanded corpus → recompute Wilson CI → update README.
- **Adverse:** If FPR goes UP, publish — becomes a v3 motivation paragraph.
- **Effort:** 0 (eval re-uses existing path) or ~30 min T4.

---

## Bucket C — Innovation polish (mostly 0-unit, but useful only if Bucket B partially lands)

### C.1 — Rupee-weighted reward function ⭐ (P1.19)
- **Why:** Replace unitless reward with **₹ saved**. Headline becomes "Chakravyuh v2 prevented ₹X cr in expected loss." Memorable on stage.
- **How:**
  1. Add `amount_inr` field to bench scenarios (manual labelling, ~30 min). Category typicals: OTP ~₹50k, investment ~₹5L, digital arrest ~₹10L, matrimonial crypto ~₹2cr.
  2. Modify `chakravyuh_env/rubrics.py`: `detection_reward = +1.0 × log(1 + amount_inr/10000)`; `FP_penalty = −0.3 × log(1 + avg_category_amount/10000)`.
  3. Compute aggregate ₹ saved across the bench for v2 vs scripted baseline.
- **Effort:** 0 unit (CPU eval).

### C.2 — Prompt-injection defense (P1.21)
- **Why:** Pair with the already-shipped red-team eval (4/10 caught is the baseline). Defense should improve that to 8/10+.
- **How:** Wrap Analyzer with input sanitizer (strip `<|im_start|>`, `[INST]`; cap length 2000), system-prompt fence, JSON output schema (outlines/pydantic). Re-run `eval/redteam_analyzer.py`; report before/after pass rate.
- **Effort:** 0 unit.

### C.3 — Demo GIF embedded in README (P2.3)
- **What:** 15-second GIF of the Gradio replay UI in action.
- **How:**
  ```bash
  pip install -e '.[demo]' && python -m server.demo_ui
  # Record 15s with peek/OBS, then:
  ffmpeg -i demo.mp4 -vf "fps=10,scale=720:-1:flags=lanczos" -loop 0 docs/assets/demo.gif
  ```
- **Embed:** `![Demo](docs/assets/demo.gif)` — host on **GitHub raw URL**, NOT HF Space (HF rejects binaries; same pattern as plot PNGs).
- **Effort:** 0 unit.

### C.4 — Release Scammer adapter (P3.6, conditional on B.2)
- **Trigger:** B.2 phase 1+2 converged with stable curves.
- **How:** `huggingface-cli repo create chakravyuh-scammer-0.5b-v1 --type model`, push with model card listing intended use (red-team / RL), out-of-scope, gated access, contact.
- **Adverse:** If B.2 fell back to SFT-only, do NOT release publicly. Frame as v3.
- **Effort:** 0 unit.

### C.5 — Upstream PR to OpenEnv (P1.23, opportunistic)
- **What:** If you found any papercut while building (missing docstring, MCP edge case, unclear error), submit to `meta-pytorch/OpenEnv`. Even an unmerged docs PR is framework-mastery credibility.
- **Effort:** 0 unit.

### C.6 — NPCI / RBI / Bank outreach (P2.12, conditional on A.5)
- **Trigger:** A.5 (frontier baseline) shipped AND numbers acceptable.
- **What:** Email NPCI Safety Awareness, RBI Financial Fraud Cell, I4C, HDFC/ICICI/SBI fraud teams. Use only measured numbers; do NOT manufacture quotes.
- **Realistic:** Cold-emails rarely respond within hackathon timelines. Treat any acknowledgment as bonus.
- **Effort:** 0 unit.

---

# Pre-Submit Final Checklist

## JC non-negotiables
- [x] OpenEnv (latest release)
- [ ] **A.3** — Training script Colab with **outputs visible**
- [x] Loss + reward plots from real run committed (`rubric_decomposition.png`, `training_reward_curve.png`)
- [ ] **A.2** — Mini-blog OR <2-min video — blog draft done at `docs/blog_post.md`; video pending
- [x] HF Space live (`https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh`)
- [x] README motivates problem, explains env, shows results, links all materials
- [x] No big video files, plots committed
- [x] Valid `openenv.yaml`, OpenEnv base class + client/server + Gym API
- [x] No reserved MCP names (`tests/test_mcp_compliance.py`)

## Standout signals — still open
- [ ] **B.1** — Trained vs SFT baseline (frontier scaffold ✓; SFT pending)
- [ ] **B.2 phase 2** — Multi-run / per-rubric trajectory from live retrain
- [ ] **C.1** — Rupee-weighted reward (composable rubrics ✓)
- [ ] **C.2** — Prompt-injection defense (red-team baseline shipped 4/10)

## Theme coverage
- [x] Theme #1 (Multi-Agent) — base 5-agent + negotiation protocol shipped; **B.2 + B.3 elevate from rhetoric to evidence**
- [x] Theme #4 (Self-Improvement) — leaderboard ✓ + novelty curriculum ✓
- [x] Theme #2/3 narrative-only

## Operating Principles audit (re-verify before each submit)
- [ ] Every README number has an artifact in `logs/` or `plots/`
- [ ] No fabricated SFT vs RL numbers (only after B.1)
- [ ] No NPCI/RBI quote unless quote actually received
- [ ] No Scammer release unless B.2 converged

---

# Compute Budget — Remaining

## Onsite — HF GPU credits

| Task | Hardware | Est hours | Priority |
|---|---|---|---|
| **B.2** phase 1 (Scammer LoRA 200 ep) | T4/L4 | ~2h | Must |
| **B.2** phase 2 (Analyzer retrain w/ per-rubric logging 150 ep) | A100 | ~3h | Must |
| **B.1** SFT baseline 3 epochs | A100 | ~1.5h | Must |
| **B.5** calibration re-inference | A100 | ~0.5h | Should |
| All bench evals across variants | T4 | ~1h | Must |
| **B.6** per-language eval | T4 | 1–2 units | Should |
| **B.7** token saliency | T4 | 1 unit | Nice |
| **B.8** latency / memory | T4/CPU | 0–1 unit | Nice |
| **B.3** Scammer clustering (post-B.2) | T4 | 0.5 unit | Nice |
| **Total** | — | **~9–10h** | — |

## Onsite — API budget
| Task | Cost | Priority |
|---|---|---|
| **A.5** frontier baseline real run | ~$40–80 | Should — or remove all references |

---

# Compute-Aware Cut List (if budget tightens)

**≤ 20 units remaining:**
- B.6 per-language → qualitative examples only (0 units)
- B.7 token saliency → skip
- B.8 latency → cite published Qwen2.5-7B numbers (0 units)

**≤ 10 units:**
- C.1 rupee-weighted → narrative only ("we designed for amount-weighted reward; v3 work")
- B.2 phase 2 → keep Scammer phase 1 only

**≤ 5 units — emergency:**
- Skip B.2 entirely. Frame honestly as "single-agent oversight against templated adversary." Double down on A.1, A.2, A.3, A.4 (all 0-GPU).

**Never drop:** A.1, A.2, A.3, A.4, B.1, A.6, the dress rehearsal.

---

# The 7 Items That Still Define #1 vs Finalist

| # | Item | Why |
|---|---|---|
| 1 | **B.1** SFT vs RL | Single most defensible research claim |
| 2 | **B.2** Adversarial Scammer | "5 agents" becomes evidence, not rhetoric |
| 3 | **B.3** Emergent Scammer behavior | Theme #1 evidence (depends on B.2) |
| 4 | **A.2** 2-min video | Storytelling 30% — non-negotiable |
| 5 | **A.4** Fresh-Docker dress rehearsal | Eliminates demo-day failure mode |
| 6 | **A.3** Executed notebooks | Reproducibility floor |
| 7 | **A.5** Frontier baseline | Either headline win or honest framing pivot |

---

# What Is Intentionally NOT in This Plan

- More tests (suite at 233 — keep it that way)
- Refactoring agent code (works)
- More themes beyond #1 and #4 (covered via narrative)
- More languages (7 is enough; effort goes to per-language *measurement*)
- More scam templates (660 is enough; effort goes to benign expansion B.9)
- Multi-seed retrain (bootstrap CIs substitute)
- Inter-annotator labelling (timeline-impossible)
- Vision agent / long-horizon pig-butchering (scope creep)
- External leaderboard submissions (cannot orchestrate in time)

---

# Pre-Flight Reality Check

- [ ] OpenAI + Anthropic + Google API keys provisioned for A.5
- [ ] Exact submission deadline confirmed (date + time + timezone)
- [ ] Onsite logistics for April 25–26 (HF compute pickup, A100 access)
- [ ] Solo or team — task ownership locked
- [ ] Backup Colab account if primary hits quota

---

# Operating Discipline Reminders (sticky-note)

1. **No claim without artifact.**
2. **Adverse-results plan first.**
3. **Cut > stretch.**
4. **Honesty as differentiator.**
5. **Dress rehearsal is not optional.**

---

**Next concrete actions (in order):**

1. **A.1** — Render slides PDF. (5 min)
2. **A.3** — Run 3 Colab notebooks → commit with outputs. (2–4 hrs)
3. **A.2** — Record 2-min video → unlisted YouTube → link from README. (4–6 hrs)
4. **A.4** — Fresh-Docker dress rehearsal. (1 hr)
5. **Onsite arrival**: kick off B.2 phase 1 + B.1 SFT baseline in parallel.
6. **Onsite day 2**: B.2 phase 2 + B.3 emergent + A.5 frontier (if budget) + A.6 community posts → submit.
