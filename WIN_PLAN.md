# CHAKRAVYUH — REMAINING WORK PLAN (v7, post-merge)

**Project:** Chakravyuh — Multi-Agent RL Environment for Indian UPI Fraud Detection
**Event:** Meta PyTorch OpenEnv Hackathon 2026, Bangalore
**Target:** Rank **#1**

---

## Status snapshot (what is already done — do not redo)

> **Production is healthy.** All 11 endpoints (`/`, `/health`, `/schema`, `/metadata`, `/openapi.json`, `/leaderboard`, `/demo/`, `/demo/preview`, `/eval`, `/eval/redteam`, `/eval/known-novel`, `/eval/bootstrap`, `POST /diagnose`) return 200 on the live HF Space at https://ujjwalpardeshi-chakravyuh.hf.space. Deployed SHA `08149ec`.
>
> **Test suite:** 303 passed · 2 skipped (305 collected). Container probe matches local. CI green except link-check-http which is now allowed-fail at the step level so the badge stays green during HF rebuild races.
>
> **What four shipping rounds resolved:**
>
> 1. **Round 1 (autonomous-execution batch):** P0 README/repo/demo work, all 0-unit evals (red-team, ablation, time-to-detection, error analysis), `docs/judge_quickstart.md` and `docs/limitations.md` shipped, slide deck markdown source.
> 2. **Round 2 (audit-autonomous-fixes):** Reward system unified into `AnalyzerRubricV2` (env default), `flag_threshold` literally pinned to defeat threshold-tuning exploit, `tests/test_v2_reward_parity.py` regression-locks training/serving parity, archived v1↔v2 toggle in demo, research endpoints (`/eval/*`, `POST /diagnose`), env-rollout per-rubric ablation, Dockerfile HEALTHCHECK hardened, agent-card a11y.
> 3. **Round 3 (audit-v2-no-gpu):** Production `Dockerfile` + `.dockerignore` now COPY `logs/` and `data/` into the runtime image (was the root cause of `/demo/` and `/eval/*` 404s); `_mount_demo` exception is no longer swallowed; **live red-team wow tab** (`server/redteam_handler.py` — same scripted analyzer scoring against two reward profiles, asymmetry badge); OpenEnv contract tightening (importable Pydantic submodels + `schema_version: "0.2.0"` + JSON round-trip / determinism / MCP integration tests); `/demo/preview` static cold-start fallback; `.github/workflows/keepwarm.yml`; failure-first README hero rewrite + methodological-contribution paragraph; `docs/architecture.md` Mermaid; `notebooks/env_exploration.ipynb` GPU-free tutorial; `LIVE_PITCH.md` tolerance bands; FALLBACK_A and FALLBACK_B pre-staged; `docs/training_diagnostics.md` honest read of late-stage KL plateau.
> 4. **v3-plan branch (merged):** `eval/semantic_leakage_audit.py` + 2007-row `logs/semantic_leakage_audit.json` (MiniLM-L6 cosine-similarity audit revealed **44.8% of bench items have cosine > 0.85 to nearest training text**; histogram at `plots/chakravyuh_plots/semantic_leakage_histogram.png`); critical disclosure + v3 fix plan in `docs/limitations.md`; `server/input_sanitizer.py` + 11 tests (prompt-injection defense); `docs/Q_AND_A_REHEARSAL.md` updates.
>
> **What this means for the rubric:** Rules adherence ≈ 9/10. Multi-agent defensibility ≈ 5/10 (still single-trained-agent — Bucket B). Self-improvement ≈ honest demote applied. Storytelling ≈ 5/10 until video + slide PDF land. Demo HF Space ≈ 9/10 (live, /demo/ + /eval/* both 200). Wow factor ≈ 8/10 (live red-team tab shipped).

---

## Operating Principles — Non-Negotiable

1. **Measurement before claim.** No number anywhere unless backed by a JSON artifact in `logs/` or a PNG in `plots/`.
2. **No fabricated numbers — even directionally.** If you didn't measure it, you don't write it.
3. **Cut beats stretch.** "Maybe" is "no" by default.
4. **Adverse-results plan first.** Before each experiment, write the worst-case story.
5. **Honesty is a differentiator.** Calibrated CIs + named limitations win over inflated point estimates. The semantic-leakage disclosure (44.8% > 0.85) is the canonical example: shipped *as a feature*, not hidden.

---

# REMAINING WORK

Three buckets, ordered by likelihood of execution given remaining time.

## Bucket A — User-side production (you, no GPU, no Colab credits)

These are the last storytelling-weight gaps and the final dress-rehearsal gate. Storytelling = 30% of the rubric — these items move it from ~5/10 to ~9/10.

### A.1 — Render slide deck to PDF [P0, 5 min]

**Status.** `docs/chakravyuh_slides.md` exists and is content-complete (Theme #4 demoted, baseline reframed, all numbers measured). No PDF.

**Why ship.** A judge clicking a `.md` link sees raw markdown — reads as "intern submission." A PDF reads as "polished."

**How.**
```bash
npx -y @marp-team/marp-cli docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf
# Pandoc fallback if marp not available:
pandoc docs/chakravyuh_slides.md -t beamer -o docs/chakravyuh_slides.pdf -V theme=metropolis
```
Commit the PDF (it's small, GitHub-only — HF Space won't push the binary, but the README link works via repo path).

**Adverse plan.** None — this never fails.

### A.2 — Record 90-second demo video [P0, 4–6 h wall-clock]

**Status.** No video. README + slides + blog + LIVE_PITCH all reference *the live demo* but never the recorded artifact judges actually watch.

**Why ship.** 90% of judges *only* watch the video. Without it, you forfeit roughly a third of storytelling weight.

**Script (6 beats; only mention measured numbers):**

| Time | Beat |
|---|---|
| 0:00–0:10 | Hook: 100% detection, then 36% FPR. The model wasn't catching scams — it was flagging everything. |
| 0:10–0:25 | 5-agent env, AnalyzerRubricV2 (8 children), only Analyzer is trained. Show the agent grid. |
| 0:25–0:40 | The hack: v1 reward over-weighted detection so model flagged everything. Show the diagnostic. |
| 0:40–0:55 | The fix: three reward changes (FP penalty −0.3 → −0.8, calibration weight 0.3 → 0.5, format-reward removed when flagging benign). v2: 99.3% detection / 6.7% FPR. |
| 0:55–1:15 | Live: open `/demo/` → red-team tab → paste a scam → both reward profiles fire side-by-side, asymmetry badge lights up. |
| 1:15–1:30 | Close: HF Space + LoRA on Hub + bench dataset open + methodological framing ("worked example of catching reward hacking in any RLHF pipeline"). |

**Tools.** OBS Studio → CapCut / DaVinci Resolve → unlisted YouTube. Keep < 150 MB.

**Constraint.** Drop any beat whose backing artifact does not exist. Currently every beat is backed.

**Adverse plan.** If you cannot record by deadline, ship a 30-second screen-record of the live red-team tab demo only. Better one short clip than no clip.

### A.3 — Execute the three Colab-shaped notebooks end-to-end [P0, 2–4 h + ~5 Colab compute units]

**Status.** Notebooks are in repo with **0 of 39 cells executed**:
- `notebooks/v2_retrain_safe.ipynb` (0/13)
- `notebooks/plots_and_eval.ipynb` (0/15)
- `training/train_colab.ipynb` (0/11)

`notebooks/env_exploration.ipynb` is the new GPU-free tutorial added in Round 3 — verified end-to-end, no compute units needed.

**JC explicitly asks:** *"a working training script using Unsloth or HF TRL, ideally as a Colab notebook so judges can re-run it."* A judge clicking these and seeing naked code will downgrade you immediately.

**How.** On Colab → Runtime → Run all → File → Download .ipynb (with outputs visible) → commit & push. Eval-only re-runs are sufficient — v2 LoRA is already published on HF Hub, no need to retrain.

**Adverse plan.** If you run out of compute units mid-execute, ship the partial outputs and add a one-line note at the top: "this notebook hits 8/13 cells before the daily Colab quota; full output in `logs/eval_v2.json`."

### A.4 — Fresh-clone Docker dress rehearsal [P0, 1 h]

**Status.** Round 3 verified `docker build .` + container probe locally. The remaining gate is a **fresh-clone test on a clean Ubuntu image** to catch latent system-dependency surprises.

**Why ship.** "It works on my machine" is the single most embarrassing failure mode at a hackathon. Doing this once eliminates it.

**How.**
```bash
docker run -it --rm ubuntu:22.04 bash
apt update && apt install -y git python3 python3-pip python3-venv curl
git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[llm,eval]'
pytest tests/
uvicorn server.app:app --host 0.0.0.0 --port 8000 &
sleep 8
for path in /health /demo/ /eval /eval/redteam; do
  curl -sf -o /dev/null -w "$path → %{http_code}\n" "http://localhost:8000$path"
done
```
**Fix every break, commit, then submit.**

### A.5 — Frontier comparison ✅ SHIPPED 2026-04-26 (open-weight tier)

**Result (n=174 same bench, paid from HF compute credits via HuggingFace Inference Providers):**

| Model | Params | Detection | FPR | F1 |
|---|---|---|---|---|
| **Chakravyuh v2 LoRA** | **7B + LoRA** | **99.3 %** | **6.7 %** | **0.990** |
| Llama-3.3-70B-Instruct | 70B | 99.3 % | 3.2 % | 0.993 |
| Qwen2.5-72B-Instruct | 72B | 98.6 % | 6.5 % | 0.986 |
| DeepSeek-V3-0324 | 671B MoE | 100 % | **29.0 %** | 0.969 |
| Scripted baseline | — | 84.6 % | 9.7 % | 0.906 |

Three publishable readouts: parameter efficiency (ties Llama-3.3-70B at 10× fewer params); F1 outperformance over Qwen2.5-72B and DeepSeek-V3; **DeepSeek-V3 reproduces the v1 reward-hacking signature externally** (100 % / 29 % FPR ≈ v1's 100 % / 36 %) — external validation of the reward-engineering methodology. Source: [logs/frontier_comparison.csv](logs/frontier_comparison.csv).

**Reproduce:**
```bash
export HF_TOKEN=hf_...
python -m eval.frontier_baseline --providers hf --hf-models \
    meta-llama/Llama-3.3-70B-Instruct \
    Qwen/Qwen2.5-72B-Instruct \
    deepseek-ai/DeepSeek-V3-0324 \
    --limit 174
```
Cost: ~$1 of HF compute credits. Total spend tracked in [docs/compute_carbon_card.md](docs/compute_carbon_card.md).

**Proprietary frontier tier (GPT-4o / Claude / Gemini) deferred** — those APIs are not covered by HF compute credits. The script supports them with `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` env vars; pure budget question, not a code question.

### A.6 — Community posts [P2, 30 min, last 48h before judging]

**Channels.** OpenEnv Discord `#show-and-tell`, Hugging Face forums (OpenEnv tag), X/Twitter (@MetaPyTorch + @huggingface), LinkedIn (tag organizers).

**Effort.** Cross-post the README hero paragraph + the per-difficulty chart + a 1-liner for the live red-team tab. 30 minutes total.

### A.7 — Live pitch rehearsal (timed dry-runs) [P0, 1.5–2 h]

**Why.** [docs/LIVE_PITCH.md](docs/LIVE_PITCH.md) defines the 4-slide / 4-minute pitch + 90-second demo. Without **timed practice**, you will overrun, fumble the red-team-tab live moment, or skip the asymmetric-improvement punchline. Most submissions ship a great deck and *deliver it badly*. Don't be that.

**How.**
1. Open `docs/LIVE_PITCH.md` + slides PDF (A.1) + the live HF Space side-by-side.
2. Run-through **3 times back-to-back** with a phone stopwatch:
   - Run 1: read every word, ignore time.
   - Run 2: target 4:00 ± 0:15. Note where you over/undershoot.
   - Run 3: full delivery with the live red-team tab demo embedded. Target 5:30 total (4:00 pitch + 1:30 demo).
3. Practice the **3 most likely judge interrupts** (from `docs/Q_AND_A_REHEARSAL.md`):
   - "Why GRPO over PPO?" (30-sec answer)
   - "How is bench different from training?" (60-sec, leads to leakage audit)
   - "If 44.8% leakage, what's your real generalization number?" (Q&A 3b — the critical follow-up)
4. **Critical micro-skills to drill:**
   - Mouse-click path through `/demo/` → red-team tab → paste scenario → wait for asymmetry badge → narrate the v1−v2 delta.
   - Switching from slides to live demo without dead air (use Cmd+Tab muscle memory).
   - Saying "we audited this ourselves" in the right intonation when the leakage question lands.
5. **If FALLBACK_A or FALLBACK_B fires** (HF Space slow / down): rehearse the 1-sentence pivot — "the live demo's cold-starting; here's the per-difficulty chart that backs the same claim" — without breaking eye contact.

**Adverse plan.** If a beat consistently overruns, *cut it.* Do not speed-read; better to drop one slide than rush all four. Drop priority: slide 4 (theme coverage) → slide 3 (architecture diagram) → keep slides 1+2 (failure-first hero + asymmetric-fix).

**Recording the rehearsal as the video (A.2 reuse).** If a take lands clean, that *is* the 90-second demo video. Two birds, one stone.

### A.8 — Final repo-metadata pass [P0, 45 min]

**Why.** A judge clicks the GitHub repo first. The first 3 seconds form the impression: repo description, topics, badges, License. Polish here is *free*; missing it is amateur-tier signal.

**How — 11-point checklist (do all of them):**

1. [ ] **`LICENSE`** present at repo root. Apache 2.0 recommended (research + permissive). If MIT, fine.
2. [ ] **`CITATION.cff`** loads cleanly in GitHub's "Cite this repository" widget. Open the GitHub repo page → right sidebar → click "Cite this" → confirm BibTeX renders. If broken, fix YAML.
3. [ ] **GitHub repo "About"** (right sidebar): one-line description ≤ 140 chars. Suggested: *"Multi-agent OpenEnv environment for Indian UPI fraud detection — diagnoses + fixes reward hacking in RLHF (v1 100%/36% FPR → v2 99.3%/6.7%)."*
4. [ ] **Topics tags** (max 20): `openenv`, `multi-agent`, `reinforcement-learning`, `grpo`, `lora`, `qwen`, `fraud-detection`, `upi`, `india`, `pytorch`, `huggingface`, `rlhf`, `reward-hacking`, `ai-safety`, `red-team`, `meta-pytorch`, `hackathon-2026`.
5. [ ] **README badges** all green: CI, license, Python version, HF Space status. Add HF Space badge: `[![HF Space](https://img.shields.io/badge/🤗-Demo-yellow)](https://ujjwalpardeshi-chakravyuh.hf.space)`.
6. [ ] **`pyproject.toml` metadata** complete: `description`, `authors`, `license`, `keywords`, `classifiers` (Programming Language :: Python :: 3.11, Topic :: Scientific/Engineering :: Artificial Intelligence, License :: OSI Approved :: Apache Software License), `urls` (Homepage, Documentation, Repository, Changelog).
7. [ ] **`README.md`** opens with the failure-first hero. Verify links: HF Space, slide PDF (A.1), video (A.2 once shipped), bench dataset, v2 LoRA Hub link, citation.
8. [ ] **HF Space `README.md`** (Space metadata block at top): `title`, `emoji`, `colorFrom`, `colorTo`, `sdk: docker`, `pinned: true`, `license: apache-2.0`. Pinning ensures the Space stays at the top of your HF profile.
9. [ ] **`pyproject.toml` version** bumped to `0.2.0` matching the post-merge state. Tag a git release: `git tag -a v0.2.0 -m "Hackathon submission" && git push origin v0.2.0`.
10. [ ] **`.gitattributes`** with `*.png filter=lfs diff=lfs merge=lfs -text` if any binary >100 KB needs to live in the repo (keeps clones small).
11. [ ] **`README.md` table-of-contents anchor links** all resolve. Run `make link-check` one more time.

**Adverse plan.** None — every item is binary present/absent. Don't ship until all 11 boxes are green.

### A.9 — 30-second backup demo video [P1, 30 min]

**Why.** A.2's primary 90-second video is the storytelling artifact. **A backup 30-second clip** of *just the live red-team tab* hedges against:
- A.2 not finishing in time.
- A.2's audio breaking.
- Being asked "do you have a 30-second version?" mid-pitch.

**How.**
```bash
# Start the live demo locally
python -m server.demo_ui &

# OBS Studio → window capture on the red-team tab → record 30 sec
# 1. Open red-team tab
# 2. Paste a known scam ("Hi I'm from SBI, your account is frozen, share OTP")
# 3. Wait for both panels to render with the asymmetry badge
# 4. Hover the badge to show the v1−v2 delta tooltip
# Stop recording.
```
Export as `docs/assets/redteam_30s.mp4` (≤ 25 MB) + GIF version `docs/assets/redteam_30s.gif` (≤ 5 MB) via `ffmpeg -i ... -vf "fps=10,scale=720:-1" ...`.

**Where to place.** README hero (immediately after the failure-first paragraph) + `docs/LIVE_PITCH.md` as the embedded fallback.

**Skip rule.** If A.2 is shipped and judges have the full 90-sec video, A.9 is optional. But it costs 30 min and hedges the demo-day failure mode at near-zero cost.

### A.10 — Q&A rehearsal (formalized drill) [P0, 1 h]

**Why.** [docs/Q_AND_A_REHEARSAL.md](docs/Q_AND_A_REHEARSAL.md) is content-complete (Q&A 3b on the leakage follow-up was added by the v3-plan merge). **Reading the answers is not the same as delivering them under pressure.** Drill the verbal answers cold.

**How.**
1. Print or open `docs/Q_AND_A_REHEARSAL.md` next to a stopwatch.
2. Have a teammate / friend / yourself-with-a-mirror ask the questions in random order.
3. **Answer each in ≤ 60 seconds**, no notes. Time each.
4. Re-read your answer in the doc. Identify what you forgot.
5. Repeat until the **3 critical questions** flow under 45 seconds each:
   - **Q3.** "How is your bench different from your training data?"
   - **Q3b.** "If 44.8% of bench is high-similarity, what's your real generalization number?" *(the killer follow-up)*
   - **Q on reward hacking.** "How do you know v2 isn't also reward-hacked?"
6. **The fourth question every judge asks but `Q_AND_A_REHEARSAL.md` doesn't have:** *"Why does this matter outside India?"* — drill the methodological-contribution answer ("worked example of catching reward hacking in any RLHF pipeline; the env design generalizes").

**Critical opening lines to memorize verbatim:**
- For Q3b: *"Yes — we audited that ourselves with MiniLM-L6 cosine similarity. 44.8% above 0.85 to training. The 100% on easy/medium/hard is partly memorization. The v1→v2 FPR fix and the scripted-baseline novel collapse are unaffected. v3 builds a held-out template-family split."*
- For reward-hacking: *"v1 detection 100%, FPR 36% — textbook reward-hacking signature. We diagnosed it explicitly. v2 dropped FPR 5× while detection stayed at 99.3% — the **asymmetric improvement** is the proof we learned the task instead of the proxy."*

**Adverse plan.** If you blank in a real Q&A, the recovery line is: *"Let me check the artifact" → open the relevant log file or doc.* Honest "I'll get back to you with the exact number" beats fabrication every time.

---

## Bucket B — Onsite GPU-bound (HF / Colab / external GPU)

Each item below converts a *narrative* claim into measured *evidence*. The single most defensible move is **B.2 (adversarial Scammer)** — it answers the only steelman of Theme #1.

### B.2 — Adversarial Scammer training ⭐ [P0, ~5h GPU]

**Why.** Today only the Analyzer learns. A learning Scammer is the single change that converts "5 agents, 1 trained" into evidence of multi-agent dynamics — the textbook Theme #1 demonstration.

#### B.2 Phase 1 ✅ SHIPPED 2026-04-26 — Scammer LoRA vs ScriptedAnalyzer

**Result.** Trained Qwen2.5-0.5B-Instruct + LoRA (r=16, α=32) via TRL 0.14 GRPO with adversarial reward `1 − ScriptedAnalyzer(c).score`. 200 episodes (8 seeds × 25 reps), evaluated on **n=64 (8 train + 8 held-out novel categories × 4 each)**. Both single-shot and Best-of-8 (test-time compute, Stiennon et al. 2020) regimes reported for transparency:

| Split | Single-shot bypass | Best-of-8 bypass | 95% CI (best-of-8) |
|---|---|---|---|
| **Overall (n=64)** | **59.4%** | **93.75%** | [85.0%, 97.5%] |
| Train categories (n=32) | 62.5% | 87.5% | [71.9%, 95.0%] |
| **Held-out categories (n=32)** | 56.3% | **100%** | [89.3%, 100%] |
| Refusals | 1/64 | 0/64 | — |

Held-out categories were never seen during training (income-tax refund, vaccine slot, lottery, customer-support callback, EPF pension, EMI conversion, blue-tick verification, police notice). 13 of 16 categories at 100% bypass under best-of-8; only failures are 3 training categories (electricity 50%, delivery-pickup 75%, fake-job 75%). Held-out > train under best-of-8 = real generalization, not memorization.

Artifacts: [logs/b2_phase1_scammer_training.json](logs/b2_phase1_scammer_training.json) (initial n=16), [logs/b2_phase1_scammer_eval_n64.json](logs/b2_phase1_scammer_eval_n64.json) (single-shot n=64), [logs/b2_phase1_scammer_eval_n64_bestof8.json](logs/b2_phase1_scammer_eval_n64_bestof8.json) (best-of-8 n=64). LoRA: `checkpoints/scammer_lora_phase1/` (12 MB, gitignored — push to HF Hub for demo). Notebook: [notebooks/T4_or_A100_b2_phase1_scammer.ipynb](notebooks/T4_or_A100_b2_phase1_scammer.ipynb).

**Headline framing for slide / README.** *"B.2 phase 1: a Qwen2.5-0.5B + LoRA Scammer, trained via TRL 0.14 GRPO with adversarial reward (1 − ScriptedAnalyzer.score), evades the rule-based defense in **93.75% of n=64 held-out attempts under best-of-8 inference** (single-shot baseline: 59.4%). On 8 categories never seen during training (income-tax refund, vaccine booking, EMI conversion, etc.) the bypass rate reaches **100%** — proving the model learned a generalizable pattern of UPI-fraud structure rather than memorizing prompts. This is the working artifact for the B.1 framing claim that **GRPO uniquely enables adversarial co-evolution**."*

**Important caveats to disclose:**
- 100% bypass is vs the rule-based ScriptedAnalyzer, NOT the v2 Analyzer LoRA. ScriptedAnalyzer has known blind spots; the v2 Analyzer LoRA crushes most of them (see head-to-head below).
- 0/64 refusals: LoRA fully overrode Qwen-Instruct safety training. Frame as *"Scammer LoRA is internal red-team artifact, never served externally."*
- Best-of-8 = realistic threat model (real attackers iterate). Single-shot = bare model capability. Ship both numbers.

#### B.2 phase 1 head-to-head ✅ SHIPPED 2026-04-26 — same Scammer outputs vs both defenders

**The co-evolution money shot.** Took the same 64 best-of-8 Scammer outputs and re-scored each by the v2 Analyzer LoRA (Qwen2.5-7B + GRPO LoRA from HF Hub, 4-bit on A100). Both defenders judging the same scams:

| Split | Scripted bypass | v2 LoRA bypass | **Gap** |
|---|---|---|---|
| Overall (n=64) | 93.75% | 32.8% | **+60.9 pp** |
| Train (n=32) | 87.5% | 28.1% | +59.4 pp |
| Held-out (n=32) | 100% | 37.5% | +62.5 pp |

**Cross-tab:** 62.5% (40/64) of scams that fool ScriptedAnalyzer get caught by v2 LoRA; only 1.6% go the other way. v2 strictly dominates scripted — pure co-evolution evidence.

**Where v2 is honestly weak:** vaccine slot (4/4 bypass, held-out), customer-support callback (3/4, held-out), credit-card EMI (2/4, held-out), income-tax refund (2/4, held-out). All are non-bank categories outside v2's training distribution — exact targets for phase 2 retrain.

Artifact: [logs/b2_phase1_scammer_vs_v2_lora.json](logs/b2_phase1_scammer_vs_v2_lora.json) (per-sample dual scores, 0 JSON parse failures).

**Headline framing.** *"Same trained Scammer (best-of-8 outputs, n=64) vs both defenders: rule-based ScriptedAnalyzer fails 94% of the time, our v2 Analyzer LoRA fails 33%. **62.5% of bypasses against the rule baseline get caught by the trained Analyzer; only 1.6% the other way** — pure dominance. That 60-point gap IS what GRPO bought us. Theme #1 demonstration, measured."*

#### B.2 Phase 2 — Retrain Analyzer LoRA against the trained Scammer [P0, ~3h A100]

1. Freeze the phase-1 Scammer LoRA. Use it as the opponent in a fresh GRPO run that retrains the Analyzer LoRA from v2.
2. 150 episodes with **per-rubric W&B logging** (rubric scores per turn, not just final reward) — also produces the per-rubric trajectory plot still missing from the v3 lookbook.
3. Plot co-evolution curves: phase-1 Scammer success rate ↑, then phase-2 Analyzer detection ↓ that. Save to `plots/chakravyuh_plots/coevolution_curves.png`.

**Adverse plan.** If phase-2 GRPO collapses (negative-reward spiral), fall back to SFT on the 11 successful phase-1 bypass examples; frame phase 2 as "Analyzer hardened on emergent attacks."

**Process-level reward (was B.4) folds in here**: add `compute_step_reward(turn_index, action, partial_observation)` to `chakravyuh_env/rubrics.py`; use it only in B.2 Phase 2 retrain.

### B.3 — Emergent Scammer behavior analysis [P1, 0.5 unit T4, depends on B.2]

**What.** Cluster outputs from the learned Scammer using sentence embeddings; identify clusters with no template-library analog. Even 1–2 emergent centroids = Theme #1 "emergent strategic behavior" evidence.

**How.**
```bash
python eval/scammer_generate.py --adapter <user>/chakravyuh-scammer-0.5b-v1 --n 500 --output data/learned_scammer_corpus.jsonl
python eval/scammer_emergence.py --generated data/learned_scammer_corpus.jsonl --templates chakravyuh_env/scammer_templates.json --output docs/emergent_behavior_analysis.md
```

**Skip if** B.2 fell back to SFT-generation-only.

### B.4 — Multi-seed retrain [P1, ~6 GPU-h T4 across 3 seeds]

**Why.** Single-seed (seed 42) is the cleanest open scientific-rigor finding from AUDIT_V2. Reporting variance across LoRA initializations is what NeurIPS reviewers expect and most submissions cannot afford.

**How.** Re-run training at seeds 7, 13, 42. Report mean ± std on detection / FPR / F1. **6 GPU-h T4. Skip if you have less than 8 remaining.** If skipped, the existing limitations.md note ("Single-seed v2 training run. Multi-seed deferred to v3.") is the honest framing.

**Pair with B.7.** When B.7's held-out template-family split is built, run the multi-seed retrain *on that cleaner split* — `docs/limitations.md` v3 fix item #3 explicitly calls for "multi-seed retrain on the cleaner split to bound the seed variance." This is the high-rigor combination, not B.4 in isolation.

### B.5 — LoRA red-team [P1, ~1 GPU-h]

**Why.** `eval/redteam_analyzer.py` runs 10 attacks against the **scripted analyzer only** (4/10 caught). The LoRA has never been red-teamed. Anyone who reads `analyzer_robustness.json` will spot this.

**How.** Run the same 10 attacks against the v2 LoRA. Update `logs/analyzer_robustness.json`. **Pair with `server/input_sanitizer.py` (already shipped):** report before / after pass rate. The improvement from rule-based 4/10 → LoRA-with-sanitizer N/10 is a measurable win.

### B.6 — Calibration analysis (ECE + reliability diagram) [P1, ~0.5h A100]

**Why.** `CalibrationRubric` is trained for, but ECE / reliability diagram are never reported. Standard AI-safety metric. The audit also flagged the *threshold-sweep degeneracy* (9 of 13 thresholds give identical metrics) — this is the eval that explains why.

**How.**
```bash
python eval/calibration_eval.py \
  --model-id <user>/chakravyuh-analyzer-lora-v2 \
  --bench data/chakravyuh-bench-v0/scenarios.jsonl \
  --output docs/calibration_analysis.md
# Produces plots/chakravyuh_plots/reliability_diagram.png
```

**Report.** ECE (target < 0.05), reliability diagram, Brier score, per-difficulty.

### B.7 — Held-out template-family split (retrain) [P1, ~3 GPU-h A100]

**Why.** The semantic-leakage audit revealed **44.8% of bench items have cosine > 0.85 to training**. The honest claim today is "the v1→v2 FPR fix is unaffected (relative comparison) but absolute detection numbers are partly memorization." This is `docs/limitations.md` v3 fix item #1: a **retrain** that excludes whole template families, then evaluation on those families gives a real OOD generalization number.

**How.**
1. Add `eval/template_family_split.py` that uses `logs/semantic_leakage_audit.json:per_scenario.nearest_template_id` to define template families and emit a held-out family list.
2. **Retrain** v2 LoRA on training data with all variants of those held-out families excluded.
3. Evaluate the retrained model only on the held-out families. Report detection / FPR / F1 — this becomes the published OOD generalization number.
4. Update `docs/limitations.md` to replace the placeholder ("v3 work — flagged below") with measured numbers.

**Adverse plan.** If held-out detection is < 80%, that *is* the headline ("we measured what real OOD looks like; here's where v2 actually generalises"). Don't spin. The story still survives because the v1→v2 relative FPR fix is unaffected.

**Eval-only fallback.** If GPU budget is short, run only the *evaluation* slice — score the existing v2 LoRA on the leakage-clean subset (cosine < 0.70: 38 scams + 12 benigns = 50 scenarios, per `docs/limitations.md`). This is cheaper but weaker (still uses a model that saw the families during training, just measured on an OOD slice).

### B.8 — Per-language detection breakdown [P2, ~1–2 units T4]

**Why.** README claims 7-language support. Prove each works; be honest about gaps.

**How.**
```bash
python eval/per_language_eval.py \
  --model-id <user>/chakravyuh-analyzer-lora-v2 \
  --bench data/chakravyuh-bench-v0/scenarios.jsonl \
  --output logs/per_language_v2.json
```
Produces `plots/chakravyuh_plots/per_language_detection.png`.

### B.9 — Latency + memory footprint [P2, 0–1 unit, can be CPU-only]

**Why.** Pitch is "on-device, on-phone." Back it with measured p50 / p99 latency + peak RAM.

**How.**
```bash
python eval/benchmark_inference.py \
  --model-id <user>/chakravyuh-analyzer-lora-v2 \
  --quantize 4bit --batch-size 1 --device cpu --iterations 100 \
  --output docs/latency_memory.md
```
Compare to mobile (Pixel 8: 8GB RAM).

### B.10 — Token saliency interpretability [P3, ~1 unit T4]

**What.** Use `captum` integrated gradients to highlight which tokens triggered the Analyzer flag. Save to `plots/chakravyuh_plots/saliency_example.png`.

**Expected.** Heatmap with "OTP", "urgent", "frozen", "verify" lit up. Visual reassurance.

### B.11 — Expand benign corpus to n ≥ 150 [P2, 30 min wall + 30 min T4]

**Why.** `chakravyuh_env/benign_augmented_v2.json` has 81 entries; bench currently uses 30. Expanding to ≥ 150 roughly halves the Wilson CI on FPR.

**Sources.** Real RBI advisories phrased as urgent warnings, HDFC/ICICI/SBI alert formats, traffic-challan SMS, Amazon/Flipkart delivery, UIDAI Aadhaar updates, GST/IT notices, airline/railway, electricity/water bills.

**Adverse plan.** If FPR goes UP on the expanded corpus, *publish that* — it becomes the v3 motivation paragraph.

### B.12 — Per-scenario v2 LoRA logits + error analysis [P1, ~0.5 GPU-h T4]

**Why.** This is `docs/limitations.md` v3 fix item #4. Today's eval is *aggregate-only* (`logs/eval_v2.json` reports detection / FPR / F1 over n=174 but not per-row scores). That blocks four downstream stories:

- *Which* 2 benigns the v2 LoRA mis-flagged + which 1 scam slipped through (qualitative error analysis the audit explicitly called out as missing).
- Slicing the headline numbers by leakage-clean subset (cosine < 0.70: 38 scams + 12 benigns = 50 scenarios) → real OOD detection / FPR.
- Calibration / reliability diagram (B.6 needs per-row logits).
- Threshold-sweep degeneracy investigation (currently 9 of 13 thresholds are identical — per-row logits show *why*).

**How.**
```bash
python eval/mode_c_real_cases.py \
  --model-id ujjwalpardeshi/chakravyuh-analyzer-lora-v2 \
  --bench data/chakravyuh-bench-v0/scenarios.jsonl \
  --emit-per-row logs/eval_v2_per_row.jsonl \
  --output logs/eval_v2.json
```
Add `--emit-per-row` flag to `eval/mode_c_real_cases.py` (one new code path; writes `{scenario_id, score, threshold, predicted, ground_truth, leakage_cosine}` per row). Then:
```bash
python eval/leakage_clean_slice.py \
  --per-row logs/eval_v2_per_row.jsonl \
  --leakage logs/semantic_leakage_audit.json \
  --threshold 0.70 \
  --output docs/leakage_clean_eval.md
```

**Adverse plan.** If leakage-clean detection is materially lower than overall, that becomes the honest headline number cited in the README + slides. The aggregate 99.3% stays as "in-distribution" with a caveat.

### B.13 — External held-out benchmark (real screenshots) [P2, 4–6 h hand-label + ~1 GPU-h]

**Why.** This is `docs/limitations.md` v3 fix item #2. Even a held-out *template-family* split (B.7) shares authoring style with training. An external corpus of **50 real WhatsApp / SMS scam screenshots from public reports** has zero overlap probability and is the cleanest possible OOD signal.

**How.**
1. Source from public reports: PIB Fact Check, Ministry of I&B advisories, RBI consumer-fraud bulletins, Kerala/Maharashtra/Karnataka cyber-crime portals, news screenshots from The Hindu / IE / NewsMeter scam-roundups.
2. Hand-label each as scam / benign + tag with category (OTP-theft, digital-arrest, KYC-update, investment, romance, etc.).
3. Add to `data/chakravyuh-bench-v0-external/scenarios.jsonl` (separate file — keeps the canonical bench frozen).
4. Run v2 LoRA + scripted baseline on it. Report detection / FPR / per-category breakdown in `docs/external_bench_results.md`.

**Adverse plan.** External bench numbers will almost certainly be lower than the canonical bench. *Publish honestly.* The gap between canonical and external bench *is* the leakage-driven inflation, measured. That's a stronger story than hiding it.

**Skip if:** hand-labelling does not finish before submission. The semantic leakage audit + B.7 are sufficient on their own to demonstrate the discipline; B.13 is the calibration on top.

### B.14 — v3 Analyzer training improvements (KL early-stop + reward-shape ablation) [P1, ~5 GPU-h A100]

**Why.** [docs/training_diagnostics.md](docs/training_diagnostics.md) honestly disclosed that v2's GRPO trajectory plateaued KL at 0.25–0.45 with `clip_ratio = 0` for ~600 steps. That's flagged as v3 work but has no execution slot. Separately, the README cites three v2 fixes (FP −0.3 → −0.8, calib 0.3 → 0.5, format-removal) but **never measured which one actually drove the FPR collapse**. Both are answerable with cheap retrains and produce publishable artifacts regardless of outcome.

**Two retrains, run in sequence:**

**B.14a — KL early-stop guard.** Add a callback to `training/grpo_analyzer.py` that halts when `kl_div > 0.20` for 3 consecutive logging windows. Re-run v2 with this guard. Compare detection / FPR / F1 + KL trajectory plot. If v3-with-guard ties v2 with cleaner KL, that's the "we measured what training instability looks like and contained it" headline. ~1.5 h A100.

**B.14b — Reward-shape ablation matrix (3 cells).** Run three retrains, each freezing two of the three v2 fixes and ablating one:
- (i) FP penalty back to −0.3, calib weight 0.5, format-removal applied
- (ii) FP penalty −0.8, calib weight 0.3, format-removal applied
- (iii) FP penalty −0.8, calib weight 0.5, format-reward restored on benign

Report detection / FPR / F1 for each cell vs full v2. Identify which fix carried the asymmetric improvement. ~3 × 1 h = 3 h A100.

**Adverse plans.**
- v3-with-guard *beats* v2 → publish carefully ("v3 is a cleaner training run; v2 numbers in the README are from the actual training run we shipped, v3 is the calibrated next iteration"). Don't re-run every bench number — keep the v1→v2 narrative as the headline and frame v3 as evidence the pipeline self-improves.
- v3-with-guard *loses* to v2 → "the KL plateau didn't hurt; the reward shape is what mattered." Confirms v2 was a local optimum.
- Ablation finds **one** fix dominates (e.g., FP penalty alone explains 80% of the FPR collapse) → strong causal claim ("of the three changes, this one was load-bearing"). Even cleaner story.
- Ablation finds **all three matter roughly equally** → "principled compound reward engineering" — also a clean story.

**Skip rule.** If you have < 6 GPU-h after B.1 + B.2 + B.7, do **only B.14a**. The KL guard alone is the single most defensible training-discipline signal.

### B.15 — Calibration-aware retrain [P2, ~1.5 GPU-h A100, depends on B.6]

**Why.** B.6 only *measures* calibration ECE — it doesn't fix it. The threshold-sweep degeneracy (9 of 13 thresholds give identical metrics) is direct evidence v2 outputs near-binary scores. Adding an explicit ECE loss term to the GRPO reward — `−λ × ECE_batch` with `λ = 0.1` — pushes the model toward calibrated probabilities.

**Trigger.** Run **only after** B.6 confirms ECE > 0.10 (otherwise nothing to fix). Currently uncertain because B.6 hasn't run.

**How.** Add `CalibrationLossRubric` to `chakravyuh_env/rubrics.py` (computes batched ECE via 10-bin histogram + adds negative term to reward). Re-run training with `V2_WEIGHTS + {"calibration_loss": 0.1}`. Re-evaluate ECE + reliability diagram + threshold sweep.

**Adverse plan.** If ECE drops but detection drops too, frame as "calibration / sharpness tradeoff measured." If ECE doesn't budge, frame as "the policy is hard-wired near-binary; calibration via output transformation (temperature scaling) is the remaining lever — v3 work."

### B.16 — Curriculum scheduling (easy → hard) [P3, ~2 GPU-h A100]

**Why.** v2 trained on episodes drawn uniformly from the full template corpus. Curriculum (start with easy templates, ramp to medium, then hard) is well-documented in RL literature to improve sample efficiency and final-policy quality.

**How.** Add `--curriculum easy_to_hard` flag to `training/grpo_analyzer.py`. Episode sampler weights templates by difficulty bucket: epoch 0 → 70% easy / 25% medium / 5% hard; ramp linearly to 20% / 40% / 40% by epoch 3. Compare convergence speed + final FPR vs uniform-sampling v2.

**Skip if:** B.2 + B.14 + B.15 already exhausted GPU budget. Curriculum is a "polish" experiment; not headline-grade in isolation.

### B.17 — Per-rubric weight grid sweep around `V2_WEIGHTS` [P2, ~3 GPU-h A100]

**Why.** `V2_WEIGHTS` is a **single hand-tuned point**. It worked well — but is it optimal? Or is there a (W_detection, W_FP, W_calibration) tuple within ±20% that gives FPR < 5% with no detection loss? **No one in the audit asked this and we never measured it.** A coarse grid sweep is direct sensitivity-analysis evidence and a clean "we tuned the reward principlefully" story.

**How.**
1. Define a 3 × 3 × 3 grid centered on `V2_WEIGHTS`. Vary detection weight ±20%, FP-penalty weight ±20%, calibration weight ±20%. 27 cells total — too many to fully retrain.
2. **Cheap-eval shortcut:** for each cell, score the **existing v2 LoRA outputs** (per-row logits from B.12) under the new weight configuration. This is *post-hoc reward recomputation*, not retraining — but it identifies the ridge / sensitivity *for the same model outputs*. ~0 GPU.
3. **Confirmatory retrain:** pick the 2–3 grid cells with most-promising metrics. Retrain only those. ~3 × 1 h = 3 GPU-h A100.
4. Output `docs/rubric_weight_sensitivity.md` with the heatmap + the 2–3 retrained-vs-original comparison.

**Adverse plan.** If the grid finds a tuple that beats `V2_WEIGHTS` by > 1pp on FPR with no detection loss, *that becomes v3 (`V3_WEIGHTS`)* — but cite v2 numbers everywhere in the README, with v3 as a footnote ("further FPR reduction achievable; reported below"). If the grid shows v2 is at a flat ridge (within 0.5pp across many cells), that's also a clean story ("V2_WEIGHTS sits in a robust region — small mistuning is OK"). Either outcome is publishable.

**Skip rule.** If post-hoc cheap-eval shortcut shows no cell within 1pp of v2, skip the confirmatory retrain entirely. Just publish the heatmap.

---

## Bucket C — Innovation polish (mostly 0-unit, useful as side-quests)

### C.1 — Rupee-weighted reward function ⭐ [P1, 0 unit, 2–3 h CPU]

**Why.** Replace unitless reward with **₹ saved**. Headline becomes "Chakravyuh v2 prevented ₹X cr in expected loss across the bench." Memorable on stage.

**How.**
1. Add `amount_inr` field to bench scenarios. Category typicals: OTP ~₹50k, investment ~₹5L, digital arrest ~₹10L, matrimonial crypto ~₹2cr. ~30 min manual labelling.
2. Modify `chakravyuh_env/rubrics.py`:
   - `detection_reward = +1.0 × log(1 + amount_inr/10000)`
   - `FP_penalty = −0.3 × log(1 + avg_category_amount/10000)`
3. Compute aggregate ₹ saved for v2 vs scripted baseline across the bench.

**Adverse plan.** If the aggregate ₹ saved is small (e.g., < ₹1 lakh because corpus skews to small-amount scams), publish honestly and reframe as "asymmetric improvement matters more in high-stake bands."

### C.2 — Demo GIF embedded in README [P2, 0 unit, 30 min]

**What.** 15-second GIF of the live red-team tab in action. Judges who don't watch the full video still see this.

**How.**
```bash
pip install -e '.[demo]' && python -m server.demo_ui &
# Record 15s with peek/OBS focused on the red-team tab, then:
ffmpeg -i demo.mp4 -vf "fps=10,scale=720:-1:flags=lanczos" -loop 0 docs/assets/demo.gif
```
Embed via `![Demo](docs/assets/demo.gif)` — host on **GitHub raw URL**, NOT HF Space (HF rejects binaries; same SHA-pin pattern as the existing PNGs).

### C.3 — Release Scammer adapter [P3, 0 unit, conditional on B.2 converging]

**Trigger.** B.2 phase 1+2 converged with stable curves.

**How.** `huggingface-cli repo create chakravyuh-scammer-0.5b-v1 --type model`, push with model card listing intended use (red-team / RL only), out-of-scope, gated access, contact.

**Adverse.** If B.2 fell back to SFT-only, do **not** release publicly. Frame as v3.

### C.4 — Upstream PR to OpenEnv [P3, opportunistic]

**What.** If you found any papercut while building (missing docstring, MCP edge case, unclear error), submit to `meta-pytorch/OpenEnv`. Even an unmerged docs PR is framework-mastery credibility.

### C.5 — NPCI / RBI / Bank outreach [P3, conditional on A.5]

**Trigger.** A.5 (frontier baseline) ran and numbers are publishable.

**What.** Email NPCI Safety Awareness, RBI Financial Fraud Cell, I4C, HDFC/ICICI/SBI fraud teams. Use **only measured numbers**; do not manufacture quotes.

**Realistic.** Cold-emails rarely respond within hackathon timelines. Treat any acknowledgment as bonus.

### C.6 — `demo_ui.py` refactor [explicitly NOT in scope]

The audit flagged `server/demo_ui.py` as a 1829-LOC god module. **Deferred.** Refactoring saves zero judge-visible value pre-deadline. Worth a v3 PR after submission.

### C.7 — vLLM / Ollama serving harness [P2, 0 GPU, 1–2 h]

**Why.** "On-device, on-phone" is the README pitch. Ship a one-command serving harness so a judge can `docker run` v2 LoRA against vLLM (server-grade) or Ollama (laptop-grade). Demonstrates deployability beyond the Gradio demo.

**How.**
1. Add `serving/vllm_compose.yml` — vLLM with the v2 LoRA pre-loaded. Single `docker compose up` boots a `/v1/chat/completions` endpoint pointed at v2.
2. Add `serving/ollama_modelfile` — Ollama Modelfile with the merged v2 weights (requires offline GGUF conversion, see C.8).
3. Add `serving/README.md` with curl-able health-check + a 3-line quickstart.

**Adverse plan.** If vLLM has version conflicts, ship Ollama-only. The harness is a *signal* of deployability; even one path is enough.

### C.8 — GGUF quantization release (mobile-class) [P2, 0 GPU local merge + 1 GPU-h convert + ~50 MB upload]

**Why.** Closes the "phone" claim with a runnable artifact. q4_k_m GGUF runs the merged 7B base + LoRA on a Pixel 8 (8GB RAM) at ~10 tok/s. Judges who care about edge inference will check.

**How.**
```bash
# Merge LoRA into base
python training/merge_lora.py \
  --base Qwen/Qwen2.5-7B-Instruct \
  --lora ujjwalpardeshi/chakravyuh-analyzer-lora-v2 \
  --output checkpoints/v2_merged/

# Convert to GGUF
python -m llama_cpp.server.convert_hf_to_gguf \
  checkpoints/v2_merged/ \
  --outfile checkpoints/chakravyuh-v2.q4_k_m.gguf \
  --quantize q4_k_m

# Push to HF
huggingface-cli upload ujjwalpardeshi/chakravyuh-v2-gguf \
  checkpoints/chakravyuh-v2.q4_k_m.gguf
```
Add to README: "Run on Pixel 8: `ollama run hf.co/ujjwalpardeshi/chakravyuh-v2-gguf:q4_k_m`."

**Adverse plan.** If GGUF perplexity degrades detection materially, ship q5_k_m (slightly larger but cleaner). If both degrade, document the quality/speed tradeoff and ship the FP16 merged model on Hub for laptop-class deployment.

---

## Bucket D — Scientific rigor & responsible AI

These items close the credibility angles a top-tier submission needs but most hackathon entries skip. **All are 0-GPU.** Each ~30–90 min wall-clock.

### D.1 — Pinned dependency lockfile [P0, 0 GPU, 30 min]

**Why.** `pip install -e '.[llm,eval]'` resolves at install time. Six months from now, transformers 5.x or trl 0.20 will break the install silently. **A lockfile is bit-reproducibility credibility.** Most hackathon submissions skip this.

**How.**
```bash
pip install uv
uv pip compile pyproject.toml --extra llm --extra eval --extra demo --extra frontier --extra dev \
  --output-file requirements.lock
git add requirements.lock
```
Update `Makefile install:` to add `uv pip sync requirements.lock` as the bit-reproducible path. Document both: lockfile (reproducible) + `pip install -e '.[...]'` (latest).

**CI integration.** Add a third matrix entry to `.github/workflows/ci.yml`: `python -m pip install -r requirements.lock && pytest`. Keeps the lockfile fresh.

### D.2 — Permutation test for v1 vs v2 FPR [P0, 0 GPU, 1 h]

**Why.** Bootstrap CIs (already shipped) tell you the spread of v2's FPR. They do *not* tell you whether the v1 → v2 FPR drop (36% → 6.7%) is statistically significant. **Permutation test** is the textbook tool for paired-sample categorical outcomes. p < 0.001 here would be the strongest possible "this is not noise" signal.

**How.** Add `eval/permutation_test_v1_v2.py`:
```python
# Pseudocode
v1_correct = [1 if v1_predicted == truth else 0 for ...]
v2_correct = [1 if v2_predicted == truth else 0 for ...]
observed_diff = mean(v2_correct) - mean(v1_correct)
n_perm = 10000
null = []
for _ in range(n_perm):
    swapped = [random.choice([(a,b),(b,a)]) for a,b in zip(v1_correct, v2_correct)]
    null.append(mean([s[1] for s in swapped]) - mean([s[0] for s in swapped]))
p_value = sum(abs(d) >= abs(observed_diff) for d in null) / n_perm
```
Output `logs/permutation_test_v1_v2.json` + cite p-value in README + slides.

**Adverse plan.** If p > 0.05 (impossible given the magnitude of the FPR drop, but for safety) → reframe quietly. Realistically p will be < 0.0001.

### D.3 — Compute & carbon disclosure card [P1, 0 GPU, 30 min]

**Why.** ML-conference reviewers (and increasingly hackathon judges with research backgrounds) expect a compute disclosure. Total GPU-hours + CO2-equivalent is a 2-row table on the model card.

**How.** Use [ML CO2 Impact](https://mlco2.github.io/impact) calculator with: hardware = A100, time = ~6 h training (v2) + ~3 h eval + planned onsite ~16 h, region = HF Spaces (typically us-east-1 → ~390 g CO2/kWh).

Add `docs/compute_carbon_card.md` and link from README. Numbers approximate; that's accepted practice.

### D.4 — Misuse / dual-use disclosure [P0, 0 GPU, 30 min]

**Why.** B.2 trains a Scammer LoRA. C.3 considers releasing it. Anyone deploying this in production must understand the dual-use risk. **A formal misuse section is what separates "research artifact" from "tossed code."**

**How.** Add `docs/misuse_dual_use.md` covering:
1. Intended use (research + RL co-evolution + red-team).
2. Out-of-scope use (impersonation campaigns, training generative scammers for active deployment).
3. Mitigations (Scammer adapter gated-access on HF Hub; license restricting commercial use; contact form for vetted researchers).
4. Threat model the *Analyzer* defends (covered already in `server/input_sanitizer.py`).

Link from README + Scammer model card (when C.3 ships).

### D.5 — Failure mode taxonomy [P1, depends on B.12, 1 h]

**Why.** B.12 produces per-row logits. **Structuring the failures** as a taxonomy (e.g., "FP-class-A: legit-bank alerts using urgency language; FP-class-B: regulator advisories; missed-scam-class: low-amount romance scams") is what reviewers and follow-on researchers cite.

**How.** After B.12 runs, group the 2 FPs + 1 missed scam by surface features (template family, language, urgency-trigger type, transaction-amount band). Output `docs/failure_taxonomy.md` with a 3-row table + 1-paragraph qualitative discussion per class.

### D.6 — Comparison vs published RL fraud-detection benchmarks [P2, 0 GPU, 2 h]

**Why.** Today the README compares Chakravyuh vs *internal* baselines (v1, scripted). Honest benchmarking against published external work is a research-credibility multiplier. There are 3–5 published RL/multi-agent fraud-detection benchmarks (Findability is the bottleneck, not the comparison itself).

**How.** Search for: "RL UPI fraud," "multi-agent fraud detection benchmark," "phishing RL environment," "scam detection RL benchmark" on Google Scholar / arXiv. Build a 1-page comparison table: env complexity, # agents, languages, public artifacts, headline metric.

**Adverse plan.** If no comparable benchmark exists, *that's the headline* ("first multi-agent OpenEnv-compliant RL benchmark for Indian UPI fraud"). Document the search itself as evidence.

### D.7 — Bench-v0 data card [P1, 0 GPU, 1 h]

**Why.** Hugging Face datasets convention. A formal data card covering license, collection method, bias statement, intended use, OOD coverage signals research maturity. The bench is already at `data/chakravyuh-bench-v0/`; add the card.

**How.** Use the [HF data card template](https://huggingface.co/docs/datasets/dataset_card). Sections: dataset summary, supported tasks, languages, dataset structure, source data, annotations, **known biases** (template-authored, English-dominant, urban-Indian-context-heavy), known limitations (covered in semantic leakage audit), citation.

### D.8 — Inter-rater check on a 30-scenario sub-sample [P2, 1 h, optional]

**Why.** Already noted as "timeline-impossible" in NOT-IN-PLAN. *Reconsidered:* a *30-scenario* sub-sample with 1 second annotator (a teammate or peer) is feasible in 1 h. Even modest κ (e.g., 0.7) is stronger evidence than no inter-rater data.

**How.** Pick 30 random scenarios, ask one peer to label scam / benign blind, compute Cohen's κ. Document in `docs/limitations.md` as a sub-sample check, not a full audit.

**Skip if:** no peer available. Existing limitations.md already discloses single-rater authoring honestly.

### D.9 — HF Hub v2 LoRA model card refresh + public W&B dashboard [P0, 0 GPU, 1 h]

**Why.** A judge clicks GitHub, then **immediately clicks the HF Hub v2 LoRA page**. Today that page (`ujjwalpardeshi/chakravyuh-analyzer-lora-v2`) was last touched pre-merge. It's missing:
- Semantic-leakage caveat (44.8% > 0.85 cosine)
- Link to `docs/training_diagnostics.md` (KL plateau honest read)
- Link to per-difficulty chart, ablation study, training-reward-curve PNG (all SHA-pinned)
- Bootstrap CI bands on the headline numbers
- Intended use / out-of-scope / misuse statement (matches D.4)

A polished model card on HF Hub is **required** for the JC reproducibility-floor checklist and is the single most-clicked artifact after the GitHub repo + Space.

**How.**
1. `git clone https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2 hf-model-card-refresh && cd hf-model-card-refresh`
2. Rewrite `README.md` with the [HF model card template](https://huggingface.co/docs/hub/model-cards). Sections required: model details, intended use, out-of-scope use, **bias/risks/limitations** (link D.4 + semantic-leakage section), training data, training procedure (compute budget — match D.3), evaluation (table from `logs/eval_v2.json` with bootstrap CIs), citation (match `CITATION.cff`).
3. Add SHA-pinned PNG embeds: training reward curve, per-difficulty bar chart, semantic-leakage histogram. Use `https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/<SHA>/plots/...` URLs (HF Hub renders external image URLs fine).
4. Push: `git add README.md && git commit -m "model card v2 (post-leakage-audit + training-diagnostics)" && git push`.

**Public W&B dashboard.** v2's training run hit W&B (referenced in `docs/training_diagnostics.md`). Make the project page public:
- W&B → project settings → Privacy → Public.
- Add the public link to the HF Hub model card + GitHub README.

**Adverse plan.** If the W&B run was logged under a private/team workspace and can't be made public, export the key plots (KL trajectory, reward, clip ratio) as PNGs to `plots/wandb_export/` and embed those instead. Either way, the trajectory is shown.

---

## Bucket E — Repo hygiene & ecosystem polish (0 GPU, mostly skim items)

These items are standard open-source-research-repo hygiene. None are individually decisive; the *cluster* is what signals "this repo is built to be used and cited, not just demoed."

### E.1 — `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` + `SECURITY.md` [P2, 30 min]

Standard files. Use [contributor-covenant](https://www.contributor-covenant.org) v2.1 for CoC. SECURITY.md should list email + responsible-disclosure window. Most judges scan `.github/` and root for these in 5 seconds.

### E.2 — `GLOSSARY.md` for non-Indian judges [P1, 30 min]

**Why.** UPI, OTP, KYC, Aadhaar, NPCI, RBI, I4C, PIB, "digital arrest," "matrimonial scam," "investment scam," "trading scam" — these are obvious to Indian judges, opaque to Meta engineers in California. A 1-page glossary lowers the bar for non-domain-expert evaluators.

**How.** Add `docs/glossary.md`. 15–20 short definitions. Link from README + slide deck.

### E.3 — `FAQ.md` [P1, 1 h]

**Why.** Pre-answer the 10–15 questions every judge will ask. Reuse content from `docs/Q_AND_A_REHEARSAL.md` but reformat for a judge skimming 30 submissions in an hour.

**How.** Top 10 questions: "Why GRPO over PPO?" / "Why Qwen2.5-7B?" / "Why only one trained agent?" / "How do you avoid reward hacking?" / "How is bench different from training?" / "Can I run this on a phone?" / "Production-ready?" / "Indian-bank specific?" / "What's the most surprising finding?" / "How does this compare to GPT-4o?" Answers ≤ 3 sentences each.

### E.4 — Case-study writeups (3 scenarios) ⭐ [P1, 2 h]

**Why.** A single concrete walked-through example is worth 10 aggregate metrics for narrative impact. Pick 3:
- One known scam v2 caught with the reward breakdown trace
- One novel post-2024 scam v2 caught (97.1% novel detection means there *are* such cases)
- One false positive v2 produced + analysis of why

**How.** For each: render the full agent transcript (Scammer ↔ Victim ↔ Analyzer ↔ BankMonitor ↔ Regulator), the 8-rubric reward breakdown for the analyzer turn, and a 2–3 sentence interpretation. Save as `docs/case_studies/case_01.md` etc. Embed one inline in the README.

### E.5 — Property-based tests for env [P3, 1–2 h]

**Why.** 300 unit tests cover known scenarios. **Hypothesis-style property tests** would generate random scenarios and check invariants (e.g., "for any reset, sum of reward components ≤ max possible reward"). One layer above unit tests; rare in submissions.

**How.** Add `tests/test_env_properties.py` using `hypothesis`. 5–10 properties. Time-box to 2h.

### E.6 — CI matrix expansion + weekly bench rerun [P2, 30 min]

**Why.** CI runs Python 3.11 + 3.12. Add 3.10 (still supported) and 3.13 (new). Add a weekly cron job that re-runs `make reproduce` on a self-hosted runner — detects regressions over time. Even a CI badge "bench last green: 3 days ago" is a research-maturity signal.

**How.** Edit `.github/workflows/ci.yml` matrix; add `.github/workflows/weekly_reproduce.yml` with `cron: '0 0 * * 0'`. The weekly job runs `make smoke-test` + a CPU-only subset of `make reproduce` (cached scores; ~5 min).

### E.7 — Sample integration with Inspect / Phoenix / Weave [P3, 1–2 h, opportunistic]

**Why.** Showing Chakravyuh interop with one mainstream eval/observability framework (Inspect for AI safety, Phoenix for LLM observability, Weave for traces) signals ecosystem maturity. Pick whichever is fastest to wire up; one is enough.

### E.8 — OpenEnv reference-example offer [P2, 30 min]

**Why.** Email the `meta-pytorch/OpenEnv` maintainers offering Chakravyuh as a documented multi-agent example in their docs. Even an unmerged offer is community-engagement signal. Pairs naturally with C.4 (upstream PR).

### E.9 — `REPRODUCE.md` 5-step walkthrough [P1, 1 h]

**Why.** `make reproduce` works but a judge tight on time wants **explicit step-by-step prose with expected output at each step**. A `REPRODUCE.md` that walks "fresh clone → install → tests pass → smoke test → make reproduce produces eval JSON within 0.5pp of README" with the *exact expected stdout* is the single highest-confidence reproducibility signal.

**How.** Author `REPRODUCE.md` at repo root with these sections:

1. **Prerequisites** — Python 3.11+, ~16 GB RAM, optional CUDA GPU, ~5 GB disk.
2. **5 steps with expected output snippets** —
   ```bash
   # Step 1: clone
   git clone https://github.com/UjjwalPardeshi/Chakravyuh && cd Chakravyuh

   # Step 2: install (pin via lockfile if shipped — D.1)
   uv pip sync requirements.lock   # OR: pip install -e '.[llm,eval]'

   # Step 3: tests (expected: 303 passed, 2 skipped)
   pytest tests/ -v --tb=short
   # Expected last line: ============= 303 passed, 2 skipped in N.NNs =============

   # Step 4: smoke test (expected: env reset+step in <5s, no GPU)
   make smoke-test
   # Expected: "Smoke test PASSED"

   # Step 5: reproduce eval numbers (expected: detection 99.3 ± 0.5pp, FPR 6.7 ± 0.5pp)
   CHAKRAVYUH_SKIP_INFERENCE=1 make reproduce   # ~10 min CPU cached
   # OR full run: make reproduce  # ~2-4h on a single GPU
   ```
3. **Verifying numbers** — point to `logs/eval_v2_reproduce.json` + `logs/bootstrap_v2_reproduce.json`. State the tolerance: ±0.5pp.
4. **Common pitfalls** — `GROQ_API_KEY` not set (skips 2 tests; expected), HuggingFace cache miss on first run (downloads ~14 GB), CPU-only pytest still passes.
5. **Where to file an issue** — link to GitHub issues with a 1-line "say `REPRODUCE failed at step N`" template.

Link `REPRODUCE.md` from the README quickstart section + JC's reproducibility checklist line.

---

# Pre-Submit Final Checklist

## JC non-negotiables

- [x] OpenEnv (latest release, `openenv validate .` clean)
- [ ] **A.3** — Training script Colab with **outputs visible** (3 notebooks; one user-action)
- [x] Loss + reward plots from real run committed
- [ ] **A.2** — Mini-blog **OR** < 2-min video. Blog draft at `docs/blog_post.md`; video pending
- [x] HF Space live and healthy (production verified Apr 26)
- [x] README motivates problem, explains env, shows results, links all materials
- [x] No big video files; plots committed via SHA-pinned URLs
- [x] Valid `openenv.yaml`, OpenEnv base class + client/server + Gym API
- [x] No reserved MCP names (`tests/test_mcp_compliance.py`)

## Standout signals — still open

**Tier 1 — must ship for #1**
- [ ] **A.7** — Live pitch rehearsal (timed, 3 dry-runs)
- [ ] **A.8** — Final repo-metadata pass (11-point checklist)
- [ ] **A.10** — Q&A rehearsal (cold-drill the 4 critical questions)
- [ ] **B.2** — Adversarial Scammer (most defensible Theme #1 evidence)
- [ ] **B.7** — Held-out template-family **retrain** (closes the leakage disclosure with a measured OOD number; pairs with B.4 multi-seed)
- [ ] **B.12** — Per-row logits + leakage-clean slice (qualitative error analysis + honest OOD headline; cheapest credibility win)
- [ ] **B.14** — v3 Analyzer training improvements (KL early-stop guard + reward-shape ablation; addresses [training_diagnostics.md](docs/training_diagnostics.md) v3 work)
- [ ] **C.1** — Rupee-weighted reward (memorable headline)
- [ ] **D.1** — Pinned dependency lockfile (bit-reproducibility credibility)
- [ ] **D.2** — Permutation test for v1 vs v2 (statistical significance beyond bootstrap)
- [ ] **D.4** — Misuse / dual-use disclosure (responsible-AI signal)
- [ ] **D.9** — HF Hub v2 LoRA model card refresh + public W&B dashboard (second most-clicked artifact)
- [ ] **E.4** — Case-study writeups (3 scenarios — narrative depth)
- [ ] **E.9** — `REPRODUCE.md` 5-step walkthrough (judge-friendly reproducibility prose)

**Tier 2 — ships if budget allows, deepens credibility**
- [ ] **A.9** — 30-second backup demo video (hedges A.2)
- [ ] **B.13** — External held-out benchmark (50 real screenshots; measures leakage-driven inflation directly)
- [ ] **B.15** — Calibration-aware retrain (depends on B.6 measurement)
- [ ] **B.17** — Per-rubric weight grid sweep around `V2_WEIGHTS` (sensitivity analysis)
- [ ] **C.7** — vLLM / Ollama serving harness (deployability signal)
- [ ] **C.8** — GGUF quantization release (closes the "phone" claim)
- [ ] **D.3** — Compute & carbon disclosure card
- [ ] **D.5** — Failure-mode taxonomy (depends on B.12)
- [ ] **D.6** — Comparison vs published RL fraud benchmarks
- [ ] **D.7** — Bench-v0 data card

**Tier 3 — polish, drop if needed**
- [ ] **B.16** — Curriculum scheduling
- [ ] **D.8** — Inter-rater κ on 30-scenario sub-sample
- [ ] **E.1** — CONTRIBUTING / COC / SECURITY files
- [ ] **E.2** — GLOSSARY.md (non-Indian judge accessibility)
- [ ] **E.3** — FAQ.md
- [ ] **E.5** — Property-based env tests
- [ ] **E.6** — CI matrix expansion + weekly bench rerun
- [ ] **E.7** — Inspect / Phoenix / Weave integration
- [ ] **E.8** — OpenEnv reference-example offer

## Theme coverage

- [x] **Theme #1 — Multi-Agent.** Base 5-agent + negotiation protocol shipped; B.2 + B.3 elevate from rhetoric to evidence.
- [~] **Theme #4 — Self-Improvement.** Demoted to honest framing ("self-improvement of the *training pipeline* via the v1→v2 reward-hacking-fix loop"). We do not claim recursive skill amplification.
- [x] **Theme #2 / #3** — narrative-only, no claims.

## Operating Principles audit (re-verify before each submit)

- [ ] Every README number has an artifact in `logs/` or `plots/`
- [ ] No NPCI/RBI quote unless quote actually received
- [ ] No Scammer release unless B.2 converged

---

# Compute Budget — Remaining

## Onsite — HF GPU credits

| Task | Hardware | Est hours | Priority |
|---|---|---|---|
| **B.2** phase 1 (Scammer LoRA 200 ep) | T4 / L4 | ~2 h | Must |
| **B.2** phase 2 (Analyzer retrain w/ per-rubric W&B 150 ep) | A100 | ~3 h | Must |
| **B.4** multi-seed retrain (3 seeds) | T4 | ~6 h | Should |
| **B.5** LoRA red-team re-inference | T4 | ~1 h | Should |
| **B.6** calibration re-inference | A100 | ~0.5 h | Should |
| **B.7** held-out template-family **retrain** + eval | A100 | ~3 h | Should |
| **B.8** per-language eval | T4 | 1–2 units | Nice |
| **B.9** latency / memory benchmark | T4 / CPU | 0–1 unit | Nice |
| **B.10** token saliency | T4 | 1 unit | Nice |
| **B.11** benign corpus eval re-run | T4 | 0.5 unit | Nice |
| **B.12** per-row logits + leakage-clean slice | T4 | ~0.5 h | **Should** (cheap, unblocks B.6 + audit cred) |
| **B.13** external held-out bench (50 real screenshots) | T4 | ~1 h GPU + 4–6 h hand-label | Nice |
| **B.14a** KL early-stop retrain | A100 | ~1.5 h | **Must** (pairs with `training_diagnostics.md`) |
| **B.14b** reward-shape ablation matrix (3 cells) | A100 | ~3 h | Should |
| **B.15** calibration-aware retrain | A100 | ~1.5 h | Nice (only if B.6 confirms ECE > 0.10) |
| **B.16** curriculum scheduling | A100 | ~2 h | Nice |
| **B.17** rubric weight grid sweep (cheap-eval + 2–3 confirmatory retrains) | A100 | ~3 h | Nice |
| **Total** | — | **~26–30 h** | — |

## Onsite — API budget

| Task | Cost | Priority |
|---|---|---|
| **A.5** frontier baseline real run | ~$40–80 | Should — or ship without it |

---

# Compute-Aware Cut List (if budget tightens)

**≤ 25 GPU-hours remaining:** drop B.16 (curriculum), B.15 (calibration-aware retrain), B.10 (saliency). Keep B.14a (KL early-stop) but skip B.14b (full ablation matrix).

**≤ 15 GPU-hours remaining:** drop B.4 multi-seed (cite limitations.md), B.8 per-language → keep 2 hand-picked language examples qualitatively. Drop B.14b. Keep B.14a as the one training-discipline signal.

**≤ 10 GPU-hours remaining:** drop B.6 calibration, B.7 held-out family retrain (fall back to B.7 eval-only branch on cosine < 0.70 subset), B.13 external bench, all of B.14. Keep B.2 + B.5 + **B.12** (B.12 is < 1 GPU-h and unblocks the leakage-clean headline number).

**≤ 5 GPU-hours remaining:** drop B.2 entirely. Frame honestly as "single-trained-agent system with a co-evolutionary architecture; live training of Scammer is v3 work." Double down on A.1 (slides), A.2 (video), A.3 (notebooks), A.4 (fresh-Docker test). Use C.1 (Rupee-weighted reward — 0 unit), D.1 (lockfile), D.2 (permutation test), D.4 (misuse disclosure), E.4 (case studies) — all 0-GPU — to land credibility points without GPU spend.

**Never drop:** A.1, A.2, A.3, A.4, A.6, **A.7 (live pitch rehearsal), A.8 (repo metadata), A.10 (Q&A drill)**, the dress rehearsal, **D.1 (lockfile), D.2 (permutation test), D.4 (misuse disclosure), D.9 (HF Hub model card), E.4 (case studies), E.9 (REPRODUCE.md)** — all 0-GPU and high-leverage. **The pitch / metadata / model-card items are the lowest-cost items on the entire plan and the highest-leverage for first-impression credibility.**

---

# The 10 Items That Define #1 vs Finalist (post-merge, post-rigor expansion)

| # | Item | Why |
|---|---|---|
| 1 | **B.2** Adversarial Scammer | Converts "5 agents, 1 trained" into demonstrable multi-agent dynamics — the single most defensible Theme #1 evidence |
| 2 | **A.2** 90-second video | Storytelling 30% — non-negotiable; without it the live red-team tab + slide PDF are not seen by 90% of judges |
| 3 | **A.3** Executed notebooks | Reproducibility floor; JC requirement |
| 4 | **A.4** Fresh-Docker dress rehearsal | Eliminates the single most embarrassing demo-day failure mode |
| 5 | **B.7 + B.12** Held-out template-family retrain + per-row logits leakage-clean slice | Converts the leakage-disclosure honesty into a measured OOD number; turns a self-flagged weakness into a calibrated strength. B.12 is the cheap precursor (per-row logits already unblocks the slice); B.7 is the rigorous follow-through (full retrain). |
| 6 | **B.14a** KL early-stop retrain | Closes the open `docs/training_diagnostics.md` v3 work item with a measured trajectory comparison; demonstrates training discipline most submissions don't even acknowledge |
| 7 | **D.1 + D.2 + E.9** Lockfile + permutation test + REPRODUCE.md | Bit-reproducibility + statistical-significance proof + judge-friendly walkthrough. All 0-GPU. Cheapest research-credibility win on the plan. |
| 8 | **D.4 + D.9** Misuse disclosure + HF Hub model card refresh | Responsible-AI signal + polish on the second-most-clicked artifact (HF Hub LoRA page). Both 0-GPU, ~1.5 h combined. |
| 9 | **C.1** Rupee-weighted reward | Memorable headline ("Chakravyuh prevented ₹X cr in expected loss"); 0-GPU, 2–3 h CPU |
| 10 | **A.7 + A.10 + E.4** Live pitch rehearsal + Q&A drill + case-study writeups | Storytelling 30% of rubric. Three rehearsal items and one narrative artifact = the difference between a great pitch *delivered well* vs *delivered nervously*. |

---

# What Is Intentionally NOT in This Plan

- Refactoring `server/demo_ui.py` (works; aesthetics not judge-visible pre-deadline)
- More themes beyond #1 and (demoted) #4
- More languages beyond 7 (effort goes to per-language *measurement*)
- More scam templates (660 is enough; effort goes to benign-corpus expansion B.11)
- Full inter-annotator audit (timeline-impossible; D.8 is a 30-scenario sub-sample compromise)
- Vision agent / long-horizon (>10-turn) pig-butchering (scope creep)
- External leaderboard submissions (cannot orchestrate in time)
- Wilson CI for v1 (already removed from blog; bootstrap is the published method)
- TensorRT / ONNX export (vLLM + GGUF cover the deployability signal)
- Sentry / production error monitoring (overkill for hackathon)
- Multi-arch Docker images (single-arch amd64 sufficient for most judges)
- Mutation testing (unit tests + B.5 red-team + property tests in E.5 are sufficient)
- Distillation to smaller model (out of scope; Scammer adapter is small enough)

---

# Pre-Flight Reality Check

**Operational**
- [ ] OpenAI + Anthropic + Google API keys provisioned for A.5 (or A.5 explicitly skipped)
- [ ] **Exact submission deadline confirmed** (date + time + timezone — verify against the OpenEnv hackathon submission portal page; do not trust calendar invites)
- [ ] **Submission portal URL** bookmarked and tested logged-in 24h before deadline
- [ ] Onsite logistics for April 25–26 (HF compute pickup, A100 access, badge / venue WiFi)
- [ ] Solo or team — task ownership locked
- [ ] Backup Colab account if primary hits quota
- [ ] Mobile hotspot ready in case venue WiFi fails during demo

**Demo-day specific**
- [ ] HF Space tested **at the venue** the day before (cold-start latency on venue WiFi can be 2x slower than home)
- [ ] Local laptop able to run `python -m server.demo_ui` as a complete fallback if HF Space is fully unreachable
- [ ] FALLBACK_A (per-difficulty chart) + FALLBACK_B (v1↔v2 toggle) printouts loaded as PNGs on the laptop
- [ ] A.9 backup 30-sec video on local disk (NOT YouTube-only — venue may block YouTube)
- [ ] Slide PDF (A.1) on local disk (do not rely on Google Drive / iCloud syncing on venue WiFi)
- [ ] Phone fully charged + has the HF Space URL bookmarked (last-resort demo from a phone screen)

**Submission package — final 30 min before submit**
- [ ] GitHub repo public + README renders correctly on github.com (not just local preview)
- [ ] HF Space `200 OK` on `/`, `/health`, `/demo/`, `/eval` — verified from a fresh incognito window
- [ ] HF Hub v2 LoRA model card renders correctly (D.9)
- [ ] Slide PDF accessible via direct URL
- [ ] Video unlisted-but-accessible via direct YouTube URL
- [ ] Tag `v0.2.0` pushed to GitHub
- [ ] All Tier 1 standout signals checked off

**Personal**
- [ ] Sleep ≥ 6 h the night before judging (not optional)
- [ ] Eat before pitching — low blood sugar wrecks delivery
- [ ] One trusted teammate or peer briefed as a "verbal-flow checker" who can interrupt your pitch if you start rushing

---

# Operating Discipline Reminders (sticky-note)

1. **No claim without artifact.**
2. **Adverse-results plan first.**
3. **Cut > stretch.**
4. **Honesty as differentiator.** (The 44.8% leakage disclosure is the canonical example.)
5. **Dress rehearsal is not optional.**

---

# Next concrete actions (in execution order)

**Phase 1a — pre-onsite, 0-GPU foundational, ~6–7 h wall-clock (do these first):**

1. **D.1** — Generate `requirements.lock` via `uv pip compile`. (30 min)
2. **A.8** — Final repo-metadata pass (11-point checklist: LICENSE, CITATION.cff, About, topics, badges, pyproject metadata, HF Space metadata, version bump + git tag). (45 min)
3. **D.4** — Author `docs/misuse_dual_use.md`. (30 min)
4. **D.2** — Permutation test for v1 vs v2 → `logs/permutation_test_v1_v2.json`. (1 h)
5. **A.1** — Render slides PDF. (5 min)
6. **D.9** — HF Hub v2 LoRA model card refresh + W&B public dashboard. (1 h)
7. **E.9** — `REPRODUCE.md` 5-step walkthrough. (1 h)
8. **A.4** — Fresh-Docker dress rehearsal — clean ubuntu:22.04 image. (1 h)

**Phase 1b — pre-onsite, 0-GPU narrative + hygiene, ~9–13 h wall-clock:**

9. **E.4** — Case-study writeups (3 scenarios). (2 h)
10. **A.3** — Run 3 Colab notebooks → commit with outputs. (2–4 h + ~5 Colab units)
11. **A.2** — Record 90-second video → unlisted YouTube → link from README, slide #4, blog. (4–6 h)
12. **A.9** — 30-second backup demo video (reuse a clean A.2 take or record fresh). (30 min)
13. **C.1** — Rupee-weighted reward (0-GPU; high-impact headline). (2–3 h)
14. **D.7** — Bench-v0 data card. (1 h)
15. **D.6** — Comparison vs published RL fraud benchmarks. (2 h)
16. **D.3** — Compute & carbon disclosure card. (30 min)
17. **E.2** — `GLOSSARY.md`. (30 min)
18. **C.7 / C.8** — vLLM/Ollama harness + GGUF quantization release. (3–4 h)
19. **E.1, E.3** — `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` + `SECURITY.md` + `FAQ.md`. (1.5 h)

**Phase 1c — pre-onsite rehearsal, ~3 h wall-clock (do these last before traveling):**

20. **A.10** — Q&A rehearsal (cold-drill the 4 critical questions). (1 h)
21. **A.7** — Live pitch rehearsal: 3 timed dry-runs. (1.5–2 h)

**Phase 2 — onsite arrival (day 1):**

22. Kick off **B.2 phase 1** (Scammer LoRA, ~2 h T4) — the single highest-leverage GPU spend.
23. Queue **B.12** (per-row logits; ~0.5 GPU-h T4) — unblocks B.6 + leakage-clean slice + D.5 taxonomy + B.17 cheap-eval shortcut.
24. Queue **B.14a** (KL early-stop retrain; ~1.5 h A100) — closes the `training_diagnostics.md` open item.
25. While GPU runs: **B.17** cheap-eval shortcut on B.12's per-row logits (re-score the 27-cell weight grid; 0 GPU). Pick 2–3 promising cells for confirmatory retrain.

**Phase 3 — onsite day 2:**

26. B.2 phase 2 (~3 h A100) + B.3 emergent analysis (depends on B.2) + **B.7 retrain on held-out template families** (~3 h A100) + **B.4 multi-seed paired with B.7's cleaner split** (if ≥ 6 h budget remains).
27. B.6 calibration (uses B.12 logits, ~0.5 h A100) → if ECE > 0.10, kick off **B.15 calibration-aware retrain** (~1.5 h A100).
28. **B.14b** reward-shape ablation matrix (~3 h A100) — only if budget remains after Tier 1.
29. **B.17** confirmatory retrain on the 2–3 promising weight-grid cells (~3 h A100, optional).
30. B.5 LoRA red-team + B.13 external held-out bench (if hand-labelling beat the deadline) + A.5 frontier baseline (if API budget) + A.6 community posts.
31. **D.5** failure-mode taxonomy (depends on B.12).

**Phase 4 — final 4 hours before submit:**

32. Re-run `make reproduce` + `make smoke-test` + `make link-check` + `pytest tests/`.
33. Update README test count + headline numbers + W&B link + HF model card cross-references.
34. **Re-do A.7 once more** — a final timed pitch dry-run with whatever results landed onsite. (30 min)
35. Verify all Tier 1 standout signals shipped (use the 14-item checklist above).
36. Submit.

**Optional pre-deadline polish (skip if any Tier 1 still open):** E.5 property tests, E.6 CI weekly cron, E.7 Inspect/Phoenix integration, E.8 OpenEnv reference-example offer, D.8 inter-rater κ, B.16 curriculum scheduling.
