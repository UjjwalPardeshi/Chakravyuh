# Chakravyuh — Independent Audit
*Generated: 2026-04-26 · Team member: anonymous · Hours to deadline: 12 (DEFAULT — please confirm)*
*Last updated: 2026-04-26 evening — post-n=64 head-to-head + 0-GPU production polish*
*Audit scope: full independent examination from first principles. No findings inherited from prior reports.*

---

> ## Update header — what changed since this audit was first written
>
> The body of this audit was written when B.2 Phase 1 had only n=16
> evaluation samples and the Scammer LoRA was not on the Hub. Three
> things changed during the day:
>
> 1. **B.2 Phase 1 evaluation expanded** to n=64 + best-of-8: bypass
>    vs ScriptedAnalyzer is **93.75 %** (held-out novel = 100 %), not
>    68.75 %. Backing artifact:
>    [`logs/b2_phase1_scammer_eval_n64_bestof8.json`](logs/b2_phase1_scammer_eval_n64_bestof8.json).
> 2. **B.2 Phase 1 head-to-head shipped** — the same Scammer outputs
>    re-scored by the v2 Analyzer LoRA show **32.8 % bypass**, a
>    **60.9-pp gap** that quantifies co-evolution. Backing artifact:
>    [`logs/b2_phase1_scammer_vs_v2_lora.json`](logs/b2_phase1_scammer_vs_v2_lora.json).
> 3. **Scammer LoRA HF repo path standardized** to
>    [`ujjwalpardeshi/chakravyuh-scammer-lora-phase1`](https://huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1)
>    (the older `-0.5b-v1` name appears in this audit's body but is
>    superseded). The Hub push is still the trainer-machine action
>    described in §5; the model card content is at
>    [`docs/misuse_dual_use.md`](docs/misuse_dual_use.md).
> 4. **0-GPU production polish landed** — slide PDF, requirements.lock,
>    architecture SVG, reward-design one-pager, three case studies,
>    Rupee-weighted reward + eval (₹77.95 lakh at risk in bench), 3
>    quick-test buttons + judge banner in demo. Test count is now
>    **337 collected · 334 passed · 3 skipped** (was 305/302/3). Commit:
>    `8f1fff6`.
>
> Treat the body below as the strategic frame; the four numbers above
> are the current ground truth.

## 0. The Verdict

**Current standing.** Chakravyuh is a top-tier finalist submission with a research-grade story (v1→v2 reward-hacking diagnosis), credible engineering (302/305 tests, all 11 HF endpoints live, 2.7s cold start), and uncommonly honest self-disclosure (semantic-leakage audit shipped *as a feature*). **Major update since first audit pass:** B.2 phase 1 SHIPPED — a Qwen2.5-0.5B + LoRA Scammer trained via TRL 0.14 GRPO evades the rule-based ScriptedAnalyzer in **11/16 = 68.75%** of held-out attempts ([logs/b2_phase1_scammer_training.json](logs/b2_phase1_scammer_training.json)). This **converts "5 agents, 1 trained" → "5 agents, 2 trained against each other"** and is the single most important Theme #1 lift the project could have made. The remaining fragility is **demo-day production hygiene**: slide deck still unrendered, 90-second video still does not exist, all 8 Colab notebooks have 0 of 72 cells executed. The **Scammer LoRA itself is NOT yet on HF Hub** (HTTP 401) — local-only on the trainer's machine, gitignored — judges can read about it but not try it. The **SFT-vs-GRPO** result remains double-edged: SFT slightly outperforms GRPO on FPR (3.2% vs 6.7%) — defensible only with the exact framing in `WIN_PLAN.md` B.1, delivered cleanly. **The B.2 result strengthens that B.1 framing**: GRPO's unique value is now demonstrated, not asserted.

**Probability of #1 in current state:** **40–48%** (was 30–35% pre-B.2; the trained Scammer is worth +8–13pp because it neutralizes the strongest Theme #1 steelman).
**Probability with the recommended P0 actions:** **70–80%** (was 65–75% pre-B.2).

**Top 3 P0 actions (sorted by impact):**
1. **Push the Scammer LoRA to HF Hub** as `ujjwalpardeshi/chakravyuh-scammer-lora-phase1` (gated, with a misuse statement). It is a 12 MB upload that converts a *paragraph claim* into a *clickable artifact*. Without this push, the 68.75% bypass-rate result is unverifiable for judges.
2. **Render the slide deck to PDF.** 5-minute Marp/Pandoc command. Without it judges see raw markdown — reads as intern submission. ([WIN_PLAN A.1](WIN_PLAN.md))
3. **Execute the 8 Colab notebooks end-to-end** (eval-only re-runs OK; v2 LoRA already on HF Hub). 0/72 cells executed today; JC explicitly requires *"a working training script ... so judges can re-run it."*

(P0 #4 just behind these: **record the 90-second demo video** — script in `WIN_PLAN A.2`; without it, 30% of the rubric is mostly forfeited.)

**The one thing to do RIGHT NOW:** `huggingface-cli upload ujjwalpardeshi/chakravyuh-scammer-lora-phase1 checkpoints/scammer_lora_phase1/` from the training machine. Five minutes. Converts B.2 phase 1 from a JSON log into a judge-clickable HF Hub artifact. After that, render the slide PDF.

---

## 1. Orientation Results

**Working directory:** `/home/omkar-kadam/Desktop/Rubacus/Chakravyuh` ✅

**Git state:**
- Branch: `main`, up to date with `origin/main` after pull from `b98167a → ae052d7` (2 incoming commits, fast-forward, stash auto-merged with 0 conflicts).
- **Two uncommitted changes:** `WIN_PLAN.md` (B.1 entry removed locally; B.2 phase 1 SHIPPED entry merged in cleanly from teammate) + `AUDIT.md` (this file). Commit both before submission.
- No stashes
- Latest commit `ae052d7` ships the trained Scammer LoRA training results JSON (`logs/b2_phase1_scammer_training.json`); preceding commits are the trl 0.14 fixes that got the GRPO loop to converge.

**Python environment:**
- `python3` only on PATH (no `python` symlink). Documentation that says `python ...` will fail for cold reproducers — flag as a low-priority README nit.
- Key versions: `openenv-core 0.2.3`, `torch 2.5.1+cpu`, `transformers 5.6.0`, `gradio 6.13.0`, `sentence-transformers 5.4.1`, `pytest 9.0.3`. `trl` and `peft` not in the local venv (training-only).

**Repo tree (highlights):**
- `chakravyuh_env/` — env package with `openenv_environment.py` (538 LOC), `rubrics.py`, 5 agent modules, 9 template JSON files
- `server/` — `app.py` + `demo_ui.py` (**2,133 LOC**), `redteam_handler.py`, `demo_v1_v2.py`, `diagnose_endpoint.py`, `eval_endpoint.py`, `leaderboard.py`, `input_sanitizer.py`
- `eval/` — 11 scripts including new `semantic_leakage_audit.py`, `redteam_analyzer.py`, `time_to_detection.py`
- `tests/` — 21 test modules
- `docs/` — 19 markdown files (judge_quickstart, LIVE_PITCH, blog_post, slides, ablation, limitations, etc.)
- `notebooks/` — **8 notebooks** including 4 just-shipped GPU-tier-named ones for B.2/B.5/B.12
- `logs/` — 16 JSON artifacts (eval_v2, bootstrap_v2, sft_vs_grpo_comparison, analyzer_robustness_lora_v2, semantic_leakage_audit, etc.)
- `plots/chakravyuh_plots/` — 1 file: `semantic_leakage_histogram.png`. **Other PNGs are SHA-pinned via raw.githubusercontent.com because HF Space rejects binaries** (this is intentional and documented).

---

## 2. Reproducibility Smoke Test Results

| Stage | Result | Notes |
|---|---|---|
| **S0.1 Install + tests** | ✅ 302 passed · 3 skipped · 0 failed in 78.54s (post-pull) | 305 collected; skips are `tests/test_explanation_judge.py` GROQ-gated (acceptable) |
| **S0.2 `openenv validate .`** | ✅ `[OK] Ready for multi-mode deployment` | All 4 deployment modes valid |
| **S0.3 `openenv validate --url <hf>`** | ✅ All required checks passed including `mode_endpoint_consistency` and POST `/mcp` JSON-RPC | Output verbatim shows reset/step/state all true |
| **S0.4 Endpoint health (11 endpoints)** | ✅ 11/11 functional | `/mcp` returns HTTP 405 on GET (correct — it's POST-only); validator's POST against `/mcp` returns 200 |
| **S0.5 Local demo boot** | ⏸️ Not run (would block; covered by HF Space at 2.7s cold) | Live HF Space `/demo/` = HTTP 200 in 2.7s ✅ |
| **S0.6 Sanity eval** | ✅ `python eval/single_scenario_eval.py --scenario-id modec_106` runs and writes `/tmp/sanity.json`; no diff vs reference | Output: `scripted score: 0.050 (missed); v2 (aggregate): detection=0.971 on 'novel'` |

**Cold-start timings (every endpoint, in seconds):**
| Endpoint | HTTP | Time |
|---|---|---|
| `/` | 200 | 1.32s |
| `/health` | 200 | 1.41s |
| `/schema` | 200 | 1.49s |
| `/metadata` | 200 | 1.32s |
| `/openapi.json` | 200 | 1.61s |
| `/mcp` (GET) | 405 | 1.60s |
| `/demo/` | 200 | **2.69s** |
| `/eval` | 200 | 1.35s |
| `/eval/redteam` | 200 | 1.41s |
| `/eval/known-novel` | 200 | 1.62s |
| `/leaderboard` | 200 | 1.61s |

**Verdict: every Stage 0 check is green.** No P0 reproducibility blocker. Cold start 2.7s is well under the 20s limit (DEFAULT keepwarm cron in `.github/workflows/keepwarm.yml` is doing its job).

---

## 3. Full Independent Scorecard

| Dimension | Score | One-line justification |
|---|---|---|
| Hackathon rules adherence | 8/10 | OpenEnv contract + 5-rubric + Space + bench all shipped. Video and slide PDF still missing — the only two non-negotiable JC line items not yet checked off. |
| OpenEnv contract correctness | 9/10 | `openenv validate` clean both local and live. All 11 endpoints 200. Pydantic submodels properly importable (Round 3 fix). Schema_version `0.2.0`. |
| Multi-Agent track defensibility | **7/10** ↑ | **B.2 phase 1 SHIPPED** — Scammer LoRA evades ScriptedAnalyzer 68.75% (n=16). Two trained agents now. Adversary is still the *scripted* (not v2 LoRA) Analyzer; phase-2 co-evolution loop is the remaining gap. Was 5/10 pre-Scammer. |
| Self-Improvement track defensibility | **4/10** | Honestly demoted in `WIN_PLAN.md` to "self-improvement of the *training pipeline* via the v1→v2 reward-hacking-fix loop." This is an honest framing but a thin Theme-#4 claim if the judge knows the canonical examples (self-play arenas, evolving curricula). |
| Scientific rigor | 8/10 | 10k-iter percentile bootstrap CIs, semantic-leakage audit (44.8% > 0.85), per-rubric ablation, time-to-detection, B.5 LoRA red-team ensemble (9/10). Single-seed remains the open hole; honestly disclosed. |
| Reward design & anti-hacking | 9/10 | `AnalyzerRubricV2` (8 children) unified into env default, `flag_threshold` literally pinned to defeat tuning exploits, `tests/test_v2_reward_parity.py` regression-locks training/serving parity. Best-in-class for this hackathon. |
| Code quality | 6/10 | `server/demo_ui.py` is 2,133 LOC — god module. Env package and rubrics are clean. Imports OK (`from server` never appears outside `server/` and `tests/`). |
| Test coverage of what matters | 8/10 | 303 passing including parity, MCP compliance, leakage subset, red-team. Two GROQ-gated skips are appropriate. Property-based tests (E.5) and CI matrix breadth (E.6) are gaps but minor. |
| Repo hygiene | 7/10 | LICENSE, CITATION.cff, MODEL_CARD, DATASET_CARD, `.github/workflows/{ci,keepwarm}` shipped. **Missing:** `requirements.lock` (D.1), `CONTRIBUTING.md`/`SECURITY.md`/`CODE_OF_CONDUCT.md` (E.1), `REPRODUCE.md` (E.9), `GLOSSARY.md` (E.2), `FAQ.md` (E.3). |
| HF Space demo | **9/10** | All 11 endpoints live, 2.7s cold start, keepwarm cron active. Live red-team tab is the wow-moment hook. |
| Gradio UI quality | 6/10 | Functional but `demo_ui.py` is 2,133 LOC; UI polish is acceptable not exceptional. Default Gradio theme. The red-team tab + asymmetry badge is the best single component. |
| Slide deck quality | **3/10** | `docs/chakravyuh_slides.md` is content-complete and well-written. **No PDF.** Judges who click the link see raw markdown. Trivial to fix; massive presentation impact. |
| Blog post quality | 5/10 | `docs/blog_post.md` is a draft. Not yet published to HF Hub or anywhere external. |
| Video / pitch readiness | **2/10** | **No video at all.** `docs/LIVE_PITCH.md` is excellent (3-minute scripted pitch with clicker actions + Q&A buffers) — but the recorded artifact judges actually watch is missing. |
| Narrative & positioning | 8/10 | Failure-first README hero ("100% detection — celebrated for four minutes — then noticed 36% FPR") is genuinely strong. The methodological-contribution angle ("worked example of catching reward hacking in any RLHF pipeline") gives it reach beyond Indian UPI. |
| Differentiation / wow factor | 8/10 | Live red-team tab + v1↔v2 toggle + asymmetry badge is the standout. Semantic-leakage audit shipped *as a feature* is unusually candid. The thing that lifts this from 8 to 10 is the video. |
| **Overall weighted score** | **6.9/10** ↑ | B.2 phase 1 SHIPPED lifts Multi-Agent +2 and unlocks competitive parity vs likely top-3 archetypes. Storytelling production remains the gating factor. |

**Headline:** Chakravyuh is **engineered like a winner** but **packaged like a finalist**. The Theme #1 hole closed today with the Scammer LoRA training result. Every remaining gap to #1 lives in the storytelling layer (slides, video, narrative-tied artifacts) — plus the **Scammer LoRA Hub push** that turns the new result into a verifiable artifact. All P0s are 0-GPU and finishable in the next 6–8 hours.

---

## 4. OpenEnv Contract — Findings

**Pydantic schemas** ([chakravyuh_env/openenv_models.py](chakravyuh_env/openenv_models.py)): tight. Fields use `Literal` and typed lists where structure is known. Round-2 / Round-3 fixes (`schema_version: "0.2.0"`, importable submodels, JSON round-trip + determinism + MCP integration tests) hold up.

**Client-server boundary:** `grep -rn "from server" $(find . -name "*.py" | grep -v server | grep -v tests)` returned **zero hits**. ✅ Client never imports server internals.

**`openenv.yaml`:** valid, `spec_version: 1`, `runtime: fastapi`, `app: server.app:app`, `port: 8000`. Consistent with `pyproject.toml` `openenv-core>=0.2.3,<0.3` pin.

**MCP compliance:** `tests/test_mcp_compliance.py` checks reserved tool names. `openenv validate --url` confirms MCP JSON-RPC POST returns 200 with `jsonrpc: "2.0"`. ✅

**Determinism:** `tests/test_openenv.py` round-trip and determinism tests pass. ✅

**Action item — none P0.** OpenEnv layer is the strongest part of the submission.

---

## 5. Multi-Agent Track — Defensibility & Strengthening

### Strongest argument FOR (UPDATED post-B.2-phase-1)
> *"Multi-agent isn't a headcount thing — it's about asymmetric information **plus** trained-vs-trained dynamics. The Analyzer sees only chat. The Bank Monitor sees only transaction metadata. The Regulator sees only aggregates across episodes. **And we trained the Scammer too** — a Qwen2.5-0.5B + LoRA via TRL 0.14 GRPO with adversarial reward `1 − ScriptedAnalyzer.score`. After 200 episodes it evades the rule-based defense in **68.75% of held-out attempts** (11/16, [`logs/b2_phase1_scammer_training.json`](logs/b2_phase1_scammer_training.json)). Two trained agents, with the Analyzer-side retrain (phase 2) wired up next."*

The two-tier oversight architecture (chat-only Analyzer + metadata-only Bank Monitor) maps cleanly to scalable-oversight literature. AePS pan-India case (₹2,400 cr) is a clean illustration of why two-tier matters. **B.2 phase 1 adds the missing piece** — the *trained* adversary that the rest of the system has to defend against.

### Strongest steelman AGAINST (refreshed)
> *"OK, you trained the Scammer. But its opponent during training is the **scripted rule-based Analyzer**, not your v2 LoRA. So you've shown a 0.5B LLM can beat a Python-rules detector — that's a nice-to-have, not a co-evolution proof. n=16 evaluation samples is small (95% bootstrap CI on 68.75% bypass is roughly [44%, 88%] — wide). And the Scammer's outputs (`logs/b2_phase1_scammer_training.json`) include refusals turned off (0/16), which is the dual-use red flag. Where's phase 2?"*

Three sub-points the team must be ready for:
1. **Opponent is scripted, not LoRA.** The honest framing: phase 1 is the *training-loop convergence proof*; phase 2 is the v2-LoRA-vs-trained-Scammer co-evolution. Don't claim phase 2 results until phase 2 runs.
2. **n=16 is a tight evaluation set.** Bypass rate 68.75% has a wide CI. State the CI in the slide.
3. **0/16 refusals.** The LoRA stripped instruction-tuned safety — *which is what you want for an adversarial agent in a research env*, but it is also exactly the dual-use risk that needs the misuse statement (D.4).

### Smallest concrete code change to neutralize the remaining steelman
**Phase 2 is the next move.** Freeze the phase-1 Scammer LoRA, retrain the Analyzer LoRA (from v2) against it for 150 episodes with **per-rubric W&B logging** (which doubles as the per-rubric trajectory plot still missing). Effort: **~3h A100**.

**Concretely needed after phase 2:**
- Push v2.1 (post-co-evolution Analyzer) LoRA to HF Hub as a sibling of v2
- Plot co-evolution curves: Scammer success rate ↑ during phase 1; Analyzer detection rate ↑ during phase 2 → `plots/chakravyuh_plots/coevolution_curves.png`
- One paragraph in README "What B.2 added": both adapters, both trajectories

### **IMMEDIATE P0 (do this NOW, before phase 2):** Push the phase-1 Scammer LoRA to HF Hub
The training machine has `checkpoints/scammer_lora_phase1/` (12 MB per WIN_PLAN). This machine has only `.gitkeep` — the adapter is gitignored (correctly — git is wrong for binaries) but **not yet pushed to HF Hub** (verified: HTTP 401 on `huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1`).

```bash
# From the training machine (NOT this machine):
huggingface-cli login
huggingface-cli repo create chakravyuh-scammer-lora-phase1 --type model
cd checkpoints/scammer_lora_phase1
git init && git remote add origin https://huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1
huggingface-cli lfs-enable-largefiles .
git add adapter_config.json adapter_model.safetensors README.md   # README = gated model card, see D.4
git commit -m "feat: B.2 phase 1 Scammer LoRA — 68.75% bypass vs ScriptedAnalyzer (n=16)"
git push origin main

# Then add gated-access flag in the HF Hub UI (Settings → Access).
```

**Effort: 15 minutes.** **Without this push, the 68.75% bypass result is not verifiable for judges.** They can read the JSON, but they can't load the adapter and try it. That's a credibility gap on a result that otherwise lifts the project a full 8–13pp on win probability.

### Recommendation (post-B.2-phase-1)
- **Lead the pitch with B.2 phase 1.** Slide 2 should now read *"two trained agents — Analyzer and Scammer — with measured 68.75% bypass after 200 episodes."*
- **Push the Scammer LoRA to HF Hub immediately** (P0).
- **Run phase 2 if ≥3 A100-hours available** — this becomes the strongest possible Theme #1 evidence (co-evolution curves).
- If phase 2 is not feasible in 12 hours, ship phase 1 + the demoted-honestly framing for phase 2 ("co-evolution loop wired; adversarial Analyzer retrain is v3 onsite work").

---

## 6. Self-Improvement Track — Defensibility & Strengthening

### Strongest argument FOR
> *"The v1 → v2 reward-hacking fix loop *is* self-improvement of the training pipeline. We diagnosed our own model's failure (100% detection / 36% FPR — textbook reward-hacking signature), redesigned the reward function, and measurably improved the system (FPR 5× down to 6.7%). The trajectory from v1's hacked behavior to v2's principled behavior is a worked example of recursive pipeline improvement. The Regulator agent + novelty scorer additionally enable adaptive curricula in v3."*

### Strongest steelman AGAINST
> *"The guidelines specifically describe Theme #4 as 'agents that learn to generate new challenges, escalate difficulty, and improve through self-play or adaptive curricula.' What you describe is *human-in-the-loop pipeline iteration*, not agent self-improvement. By the strict reading of the guidelines, you don't qualify."*

This is fair. The team's WIN_PLAN already acknowledges this with the honest demote: *"We do not claim recursive skill amplification."*

### Recommended framing (paste verbatim into pitch + slides)
> *"We deliberately demote our Theme #4 claim. Self-improvement in the strict guideline sense — agent-driven curriculum, recursive skill amplification — is not what this work demonstrates. What we **do** demonstrate is the pipeline-level analog: a measurable diagnosis-and-fix loop (v1 → v2) that other RLHF teams can apply to their own reward functions. The methodology generalizes; the recursive-self-play demonstration is v3 work via the B.2 adversarial Scammer."*

### Decision: **target both themes, but lead with Multi-Agent and explicitly demote Self-Improvement**
**Reasoning:** `WIN_PLAN.md` already does this. Doubling down on Theme #1 only would forfeit the genuine pipeline-self-improvement story (which is itself rare in hackathon submissions). Demoting Theme #4 honestly is *itself* a credibility move — judges reward calibrated framing.

**Action — add this single paragraph to README** after the "60-second pitch" section, replacing any current Theme #4 claim:
> *"Theme coverage: **#1 Multi-Agent** (primary) — five agents, asymmetric-information oversight, two-tier verification. **#4 Self-Improvement** (demoted) — we frame this as pipeline self-improvement via the v1→v2 reward-hacking-fix loop, not agent-driven self-play. v3 work toward stricter Theme-#4 demonstration is documented in `docs/limitations.md`."*

---

## 7. Scientific Rigor — Gaps & Fixes

| Gap | Exact metric (from logs) | Why a judge hits you | Exact fix | Hours | GPU-hours |
|---|---|---|---|---|---|
| **Single-seed v2 training** | `seed=42` only in `logs/v2_trainer_state.json` | "Could be a lucky seed; no variance bound" | B.4 — retrain at seeds 7, 13, 42; report mean ± std | ~2h wall + 6h GPU | 6 GPU-h T4 |
| **n_benign = 30** | `logs/eval_v2.json:fpr` over n=30 → bootstrap CI [0.0%, 16.7%] | "Your headline 6.7% number is one mistake from being 10%" | B.11 — expand benign corpus to ≥150 + re-eval | ~1h wall | 0.5 GPU-h |
| **Semantic leakage 44.8% > 0.85** | `logs/semantic_leakage_audit.json` shipped & disclosed | "Your 100% on easy/medium/hard is partly memorization" | B.7 — held-out template-family retrain + B.12 per-row leakage-clean slice | ~3h GPU + 0.5h | 3.5 GPU-h |
| **Per-row v2 logits not logged** | aggregate-only `logs/eval_v2.json` | "Which 2 benigns? Which 1 missed scam?" | B.12 — `--emit-per-row` flag in `eval/mode_c_real_cases.py` | ~1h | 0.5 GPU-h T4 |
| **No frontier baseline** | `logs/scripted_baseline_n5_archived.csv` is the renamed stub | "How does a 7B LoRA compare to GPT-4o on novel?" | A.5 — run `eval/frontier_baseline.py`; spend ~$40–80 OR ship without and don't cite | 2h | 0 GPU + $40–80 API |
| **Calibration ECE never reported** | trained for via `CalibrationRubric` but no `ece` key anywhere | "You trained for it; show it" | B.6 — `eval/calibration_eval.py`; produce reliability diagram | 1h | 0.5 GPU-h A100 |
| **Threshold-sweep degeneracy** | `logs/eval_v2.json:sweep` — 9 of 13 thresholds give *identical* metrics | "Your model is binary-output; calibration didn't shape outputs" | B.6 + add 1-line README disclosure pointing to `docs/limitations.md` | 30 min | 0 |
| **No permutation test for v1→v2 FPR delta** | bootstrap CI shipped; permutation p-value not | "Bootstrap shows spread, not significance" | D.2 — `eval/permutation_test_v1_v2.py`; expected p < 0.0001 | 1h | 0 |
| **No per-language detection breakdown** | claim is 7-language; no per-language number anywhere | "Tamil and Telugu — show the numbers" | B.8 — `eval/per_language_eval.py`; produce per-language bar chart | 1h | 1 GPU-h T4 |
| **B.5 LoRA red-team only ensemble-tested** | `logs/analyzer_robustness_lora_v2.json:raw_lora_caught: 4` | "Your 9/10 is the *sanitizer* doing the work, not the model" | This is *honest* in the JSON `note` field — no fix needed; just be ready to defend it | 0 | 0 |

**SFT-vs-GRPO finding (B.1) — CRITICAL FRAMING NOTE:**
`logs/sft_vs_grpo_comparison.json` shows SFT achieves **99.3% / 3.2% FPR** vs GRPO **99.3% / 6.7% FPR**. SFT is *slightly better* on FPR by 3.4pp. The team's framing in `WIN_PLAN.md` B.1 is *correct but delicate*:

> *"Statistically tied within Wilson CIs at n=30-31 benigns. The contribution of Chakravyuh is the environment design + reward-hacking diagnosis methodology, not the training algorithm. GRPO uniquely enables (a) reward-hacking diagnosis via training-trajectory inspection — our v1 → v2 fix came from this — and (b) adversarial Scammer co-evolution (B.2)."*

A skeptical judge will press: *"If SFT works as well, why is GRPO load-bearing?"* The answer above is correct — **but only if delivered cleanly**. Drill it in A.10 Q&A rehearsal.

---

## 8. Demo-Day Experience — File-Level Recommendations

### Cold start mitigation
**Status: GREEN.** `/demo/` cold-start measured at **2.69s** — well under the 20s limit. `.github/workflows/keepwarm.yml` is already pinging the Space. **No action required.**

### Gradio UI upgrades — `server/demo_ui.py` (2,133 LOC)
This file is a god module. Refactoring is explicitly NOT in scope per `WIN_PLAN.md` C.6 (correct call given time budget). However, **two surface-level polish items are high-ROI**:

1. **Theme override** — top of `server/demo_ui.py`, change the Gradio Blocks instantiation to use a custom theme:
   ```python
   theme = gr.themes.Soft(
       primary_hue="indigo",
       neutral_hue="slate",
       text_size="lg",
   ).set(button_primary_background_fill="*primary_500")
   demo = gr.Blocks(theme=theme, title="Chakravyuh — Live Demo")
   ```
   *15 minutes; instantly reads less "intern submission" and more "production demo."*

2. **Add a one-line judge banner** at the top of every tab pointing to `docs/judge_quickstart.md`:
   ```python
   gr.Markdown("> **Judges:** Read [`docs/judge_quickstart.md`](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/judge_quickstart.md) for the 3-minute guided tour.")
   ```
   *5 minutes; converts demo viewers into README readers.*

### Replay episodes
Read `server/episode_curator.py` shipped 6 commits ago. Verify each episode advances a *distinct* argument:
- Episode 1: *Multi-Agent Defense Wins* — argues the two-tier oversight value
- Episode 2: *Skeptical Victim Refuses* — argues victim modeling depth
- Episode 3: *Verification-First Behaviour* — argues realistic outcomes
- Episode 4: *Detection Too Late* — argues the *limit* of pure detection (motivates LoRA)
- Episode 5: *Scripted Rules Blind Spot* — argues the gap LoRA closes

**Verdict: episode design is strong** — each one carries a specific argument. Don't redesign.

### Slide deck rendering — **P0**
```bash
npx -y @marp-team/marp-cli docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf
# OR
pandoc docs/chakravyuh_slides.md -t beamer -o docs/chakravyuh_slides.pdf -V theme=metropolis
git add docs/chakravyuh_slides.pdf
git commit -m "ship rendered slide PDF (Marp/Pandoc)"
git push
```
**Effort: 5 minutes. Impact: removes a P0 instantly.**

### Demo video — **P0**
Re-use the script in `WIN_PLAN.md` A.2 verbatim. Tools: OBS Studio + CapCut. Upload as YouTube *Unlisted*. Link from README under Submission Materials.

**90-second shot list (single take, no editing required if you nail it):**
| Time | Shot | Voiceover |
|---|---|---|
| 0:00–0:10 | Slide 1 (failure-first hero) | *"We trained an LLM to detect UPI fraud and got 100% detection. We celebrated for four minutes."* |
| 0:10–0:20 | Slide 1 + zoom on the 36% FPR figure | *"Then we noticed: 36% false positive rate. The model wasn't catching scams — it was flagging everything."* |
| 0:20–0:35 | Switch to live HF Space `/demo/` → click v1↔v2 toggle | *"Here's what reward hacking looks like, side by side."* |
| 0:35–0:55 | Click red-team tab, paste a known scam, watch both reward profiles fire | *"Three reward changes — false positive penalty up, format reward off on benign, calibration weight up — and the asymmetric improvement signature appears: detection holds at 99.3%, false positives drop 5×."* |
| 0:55–1:15 | Switch to per-difficulty chart from README | *"On post-2024 novel scams the rules miss half. Our v2 catches 33 of 34."* |
| 1:15–1:30 | Back to slide 1 with HF Space URL overlay | *"Live demo, open-source, audit-disclosed. ujjwalpardeshi-chakravyuh dot hf dot space slash demo."* |

**Effort: 4–6 hours wall (rehearsal dominates; recording is 5 min). Skip-rule: if you can't finish the 90-second video, ship a 30-second screen-record of just the red-team tab — it's better than nothing.**

### Blog post publish checklist
`docs/blog_post.md` is a draft. To ship:
1. Resolve any TODOs in the draft
2. Add SHA-pinned PNG embeds (training reward curve, per-difficulty, semantic-leakage histogram)
3. Publish to `huggingface.co/blog/<user>/chakravyuh` via the HF web editor
4. Add the URL to README Submission Materials table
5. Cross-link from slide 4

**Effort: 1.5 hours.**

---

## 9. The Wow Moment

### Recommendation
**Keep the existing live red-team tab + asymmetry badge.** It's already shipped (`server/redteam_handler.py`), already wired into `/demo/`, and answers both Theme #1 (visual two-analyzer asymmetry) and the v1→v2 narrative simultaneously.

### Specification (already implemented)
- File: `server/redteam_handler.py` (8,850 bytes)
- Mounted in `server/demo_ui.py` as a `gr.Tab("You vs Analyzer")`
- User pastes a message → both v1 and v2 profile scores render side-by-side
- Asymmetry badge appears when v2 score < v1 score by ≥ 0.2

### Single small enhancement (40 minutes)
Add a **"3 known-scam quick-test" button row** above the input box:
```python
# Inside the red-team tab
with gr.Row():
    btn_otp = gr.Button("Test: OTP scam (Hindi)")
    btn_grooming = gr.Button("Test: Matrimonial crypto (English)")
    btn_deepfake = gr.Button("Test: Deepfake CEO IPO (English)")
btn_otp.click(lambda: "Sir aapka SBI account block ho gaya hai. OTP share kijiye.", outputs=user_input)
btn_grooming.click(lambda: "Hi, I'm a Singapore software engineer interested in marriage. I trade crypto. Let me show you my setup.", outputs=user_input)
btn_deepfake.click(lambda: "[Infosys CEO voice]: Exclusive employee IPO allocation. Invest Rs 1 lakh via company portal. HR calling now for UPI transfer.", outputs=user_input)
```
**Why this matters:** during live judging, you don't want to type. One click → instant asymmetry demo. **Effort: 40 minutes. Impact: turns a 30-second live moment into a 10-second one. Stage-time gold.**

### Why NOT to switch to a different wow moment
The other WIN_PLAN candidates (adversarial self-play loop, multilingual live panel) require GPU work that may not finish. Stick with what's shipped and polish it.

---

## 10. Submission Artifact Audit

| Artifact | Working? | Production-quality? | Discoverable? | Self-contained? | Notes |
|---|---|---|---|---|---|
| HF Space (live env) | ✅ | ✅ | ✅ via README | ✅ | All 11 endpoints 200; cold start 2.7s |
| HF Hub Analyzer LoRA (`ujjwalpardeshi/chakravyuh-analyzer-lora-v2`) | ✅ | ⚠️ model card pre-merge state | ✅ | ✅ | **D.9** — refresh card with semantic-leakage caveat + bootstrap CIs (1h) |
| **HF Hub Scammer LoRA (`ujjwalpardeshi/chakravyuh-scammer-lora-phase1`)** | **❌ NOT PUSHED** (HTTP 401) | — | ❌ | — | **P0 §5** — 12 MB upload from training machine; gated + misuse statement (15 min) |
| Scammer training results JSON | ✅ `logs/b2_phase1_scammer_training.json` | ✅ 116 lines, 16 eval samples + meta + reward shape | ✅ committed | ✅ | But useless without the LoRA itself — judges can read the result, not try it |
| HF Hub dataset (`chakravyuh-bench-v0`) | ✅ | ⚠️ no DATASET_CARD on HF | ✅ | ✅ | Root `DATASET_CARD.md` exists; sync to HF Hub data card |
| Slide deck | ⚠️ markdown only | **❌ NO PDF** | ⚠️ `.md` link | ✅ | **P0 A.1** — `marp` it |
| 90-sec demo video | **❌ MISSING** | — | — | — | **P0 A.2** — script in WIN_PLAN |
| Blog post | ⚠️ draft only | ⚠️ unpublished | ❌ | ⚠️ | **P0 A.6 sub-item** — publish to HF blog (must add B.2 phase 1 paragraph + bypass-rate stat) |
| Notebooks (8) | ⚠️ committed | **❌ 0/72 cells executed** | ⚠️ judges click and see naked code | ✅ | **P0 A.3** — eval-only re-runs sufficient |
| README Submission Materials | ✅ | ⚠️ no Scammer-LoRA link yet | ✅ | ✅ | After Hub push, add row to Submission Materials table |
| LIVE_PITCH script | ✅ | ⚠️ doesn't yet mention 68.75% bypass rate | ✅ in docs/ | ✅ | A.7 — drill it (refreshed for B.2) |
| Q&A rehearsal doc | ✅ | ⚠️ no B.2 question rehearsed yet | ✅ | ✅ | A.10 — add Q on "your Scammer's opponent is scripted" |
| Architecture diagram | ✅ Mermaid `docs/architecture.mmd` | ⚠️ render to SVG/PNG; doesn't yet show trained-Scammer arrow | ⚠️ | ✅ | 5-min Mermaid CLI export + small edit |
| Reward-design one-pager | ⚠️ | partially in `DESIGN_DECISIONS.md` §8 | ⚠️ | ✅ | Could extract as standalone `docs/reward_design.md` (30 min) |
| Tutorial notebook (no GPU) | ✅ `notebooks/env_exploration.ipynb` | ⚠️ 0/4 cells executed | ⚠️ | ✅ | Same fix as A.3 |
| Architecture SVG | ❌ | — | — | — | Add `docs/architecture.svg` (Mermaid CLI, 5 min) |
| `requirements.lock` | ❌ | — | — | — | **D.1** — `uv pip compile` (30 min) |
| `REPRODUCE.md` | ❌ | — | — | — | **E.9** (1h) |
| Co-evolution curves PNG (post-phase-2) | ❌ | — | — | — | B.2 phase 2 deliverable; ~3h A100 |

**Top 6 missing-artifact P0/P1 items (revised post-B.2-phase-1):**
1. **Push Scammer LoRA to HF Hub** (P0, 15 min, off this machine — needs trainer's session)
2. Slide PDF (P0, 5 min)
3. Demo video (P0, 4–6h) — *must mention the 68.75% bypass rate in voiceover*
4. Notebook outputs (P0, 2–4h + ~5 Colab units)
5. README Submission Materials row for Scammer LoRA + Q&A doc + LIVE_PITCH refresh for B.2 (P1, 1h total)
6. Blog post publish with B.2 phase 1 paragraph (P1, 1.5h)

---

## 11. Narrative & Pitch

### README hook critique
**Current opening (line 21):**
> *"We trained an LLM to detect UPI fraud and got 100 % detection. We celebrated for four minutes. Then we noticed: 36 % false-positive rate."*

**Verdict: this is genuinely good.** Failure-first opener is rare in hackathon submissions and lands within 10 seconds. **Keep verbatim.** No rewrite needed.

### Slide-by-slide flow critique (per `LIVE_PITCH.md`)
| Slide | Time | Lands? | Notes |
|---|---|---|---|
| 1 (Title) | 0–30s | ✅ Strong opener with stats | The 90-word voiceover is well-paced |
| 2 (Architecture) | 30–70s | ✅ "Asymmetric information not headcount" framing is the strongest defense available | Add one sentence about the AePS pan-India case (already in README) for memorability |
| 3 (v1→v2 fix table) | 70–120s | ✅ This is the slide that wins or loses Theme #4 demote-vs-claim | Bootstrap CIs in fine print — perfect calibrated framing |
| 4 (Demo + close) | 120–180s | ⚠️ This is where the live red-team tab demo runs in parallel | **Critical:** practice the slide-to-demo handoff 3× minimum (A.7) |

### Live pitch script critique (`LIVE_PITCH.md`)
- **Strong:** every slide has a 90-130-word spoken script timed to fit; clicker actions specified per beat; Q&A buffer phrases included
- **Add:** the 4th common judge question — *"Why does this matter outside India?"* — rehearse the methodological-contribution answer ("worked example of catching reward hacking in any RLHF pipeline; the env design generalizes")
- **Add:** the SFT-vs-GRPO defense from §7 above — judges who read the SFT artifact will press here

### Blog post — sections to add
The current `docs/blog_post.md` covers diagnosis well. **Add:**
1. The semantic-leakage audit narrative — embed `plots/chakravyuh_plots/semantic_leakage_histogram.png` and the 3-paragraph "we audited ourselves" framing
2. The B.5 ensemble red-team result (raw LoRA 4/10 + sanitizer = 9/10)
3. Link to the HF Hub model card (after D.9 refresh)

### Methodological framing recommendation
**Lead with both layers:**
- Domain layer: *"Multi-agent OpenEnv environment for Indian UPI fraud detection."*
- Methodological layer: *"Worked example of catching reward hacking in GRPO post-training — the v1→v2 diagnosis methodology generalizes to any RLHF pipeline."*

This is already in the README TL;DR. Reinforce in slide 1 voiceover.

---

## 12. Competitive Positioning

| Likely top-3 archetype | Where Chakravyuh wins | Where Chakravyuh loses | Single separating move |
|---|---|---|---|
| **Multi-agent negotiation/economics env** | Real-world impact framing (₹13,000 cr); honest leakage disclosure; v1→v2 worked example | Their multi-agent dynamics are likely more emergent; if their agents truly co-evolve they crush Theme #1 | **Execute B.2 phase 1** — even a partial Scammer LoRA closes the dynamics gap |
| **Code-debugging / SWE-bench-style agent env** | Domain specificity + multilingual + on-device deployment story | They have unambiguous task verifiability + likely better reward signal | Lean into the **scalable-oversight framing** (R&D-grade contribution) and the **methodological generalization** angle |
| **Game / RTS / strategy env** | Real-world stakes; calibrated CIs; rigor | Better visual demo; longer episodes; richer state | **The live red-team tab is your visual demo equivalent** — make sure it lands in 10 seconds (the 3-button quick-test row from §9) |
| **Tool-use / web-agent env** | Cleaner reward design (rubric vs sparse task success); responsible-AI signal | Bigger action space; more "wow factor" from web automation | **B.5 ensemble result** (9/10 vs 4/10 baseline) is your tool-use-equivalent robustness signal — cite it in the pitch |

**The single move that most separates Chakravyuh from any of these archetypes:** **the public, self-disclosed semantic leakage audit.** No other team will have done this. It is a credibility multiplier that survives every Q&A. Make sure it appears in the video (slide 3 voiceover should mention it in one sentence).

---

## 13. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Scammer LoRA never reaches HF Hub before submission** (still HTTP 401 today) | **High** | **High** — paragraph claim without artifact = "where is it?" credibility hit | **§5 IMMEDIATE P0** — 15-min upload from trainer's machine; gated repo + misuse statement; verify with `curl -I huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1` |
| Judge asks to load + try the Scammer adapter live; it isn't on Hub yet | Medium | High | Bring a 60s recorded clip of a local `peft.PeftModel.from_pretrained(...)` load + sample generation as fallback |
| Judge presses on B.2 opponent being scripted (not v2 LoRA) | High | Medium | Honest framing: "phase 1 is the *training-loop convergence proof*; phase 2 is the LoRA-vs-LoRA co-evolution — onsite work." Don't oversell. |
| Judge presses on n=16 evaluation set + wide CI on bypass rate | Medium | Medium | Quote 95% bootstrap CI [44%, 88%] on slide; state phase 2 expands eval set |
| Judge presses on 0/16 refusals from Scammer (dual-use) | Medium | Medium | Cite `docs/misuse_dual_use.md` (D.4 — write it BEFORE submission) + the gated-Hub access flag |
| HF Space cold-starts mid-pitch (rare given keepwarm cron) | Low | Medium | Pre-warm 30 min before pitch; have local `python -m server.demo_ui` ready as fallback |
| Slide PDF not rendered in time | Medium (today) | High | Run `marp` command in next 5 minutes |
| Video not recorded in time | High (today) | High (caps Storytelling at ~16/30) | Schedule the 4-6h block today; **OR** ship 30s backup demo video as the minimum |
| Demo video records BEFORE B.2 paragraph is added — looks dated | Medium | Medium | Update LIVE_PITCH + slide 3 voiceover to mention "we trained two adapters" *before* hitting record |
| Live red-team tab demo breaks during pitch | Low | High | Pre-tested with 3 known scams; have screenshot + 30s recorded clip as fallback |
| Judge presses on SFT-vs-GRPO finding | High | Medium | Drill A.10 Q&A — strengthened by B.2: GRPO uniquely enables the adversarial Scammer training loop |
| Judge presses on semantic leakage | High | **Low** (we self-disclosed) | Q&A 3b in `docs/Q_AND_A_REHEARSAL.md` is rehearsed; lean into "we audited this ourselves" |
| Notebook judges click → empty cells → trust collapse | High | High | **Execute notebooks (A.3) BEFORE submitting** — including B.2 phase-1 notebook now that it has results |
| WIN_PLAN.md + AUDIT.md uncommitted changes ship in submission diff | High | Low | Commit both before submission |
| Venue WiFi blocks YouTube during demo | Medium | Medium | Have video on local disk + the 30s clip downloaded |
| HF Space rate-limited during judging spike | Low | High | Keepwarm cron is up; have local demo as fallback |
| Trainer is asleep / unreachable during the 12h sprint and the Hub push window closes | Medium | High | Coordinate Hub push handoff *now* (DM trainer with the exact 4 commands from §5) — do not wait for asynchronous catch-up |

---

## 14. Roadmap to #1 — Hour-Boxed (12 hours assumed, post-B.2-phase-1)

### Phase 1 — Next 2 hours (zero-GPU, JC minimums + the Hub push)
| Task | Effort | Dependency | Impact |
|---|---|---|---|
| **§5 IMMEDIATE** Push Scammer LoRA to HF Hub (gated, with misuse statement) — *off-machine; coordinate with trainer NOW* | 15 min | Trainer's session | **The single highest-leverage move available** — converts B.2 phase 1 from a JSON log into a verifiable artifact (+8–13pp on win probability is locked in only after this) |
| **A.1** Render slide PDF (`marp` or `pandoc`) — *after* updating slide 2 to mention "two trained adapters" + the 68.75% bypass stat | 10 min (5 edit + 5 render) | None | Removes a P0; satisfies JC slide-deck minimum |
| **D.1** Generate `requirements.lock` (`uv pip compile`) | 30 min | None | Bit-reproducibility credibility |
| **D.4** Author `docs/misuse_dual_use.md` (Scammer LoRA dual-use disclosure — REQUIRED before Hub push) | 30 min | None | Responsible-AI signal; gates the gated-repo `README` |
| **A.8** Final repo metadata pass (LICENSE, About, topics, badges, version bump to `v0.3.0` for B.2 phase 1, git tag) | 45 min | None | First-impression polish |
| **D.2** Permutation test for v1↔v2 FPR delta → `logs/permutation_test_v1_v2.json` | 1 h | None | Statistical significance proof beyond bootstrap |
| Commit uncommitted `WIN_PLAN.md` + `AUDIT.md` | 2 min | None | Hygiene |

### Phase 2 — Hours 2–6 (production sprint, parallel where possible)
| Task | Effort | Dependency | Impact |
|---|---|---|---|
| **A.3** Execute 8 notebooks end-to-end → commit with outputs (now includes B.2 phase 1 notebook) | 2–4 h | ~5 Colab units | Removes a P0; satisfies JC training-script minimum; B.2 phase-1 notebook now has real outputs to display |
| **A.2** Record 90-second demo video → upload unlisted YouTube → link in README — *script must mention 68.75% Scammer bypass rate (slide 2 voiceover)* | 4–6 h | A.1 + Hub push | Removes a P0; lifts Storytelling 30% from ~16 to ~26 |
| **README + LIVE_PITCH refresh** for B.2 phase 1: add Submission Materials row for Scammer LoRA, update LIVE_PITCH slide 2 script, add Q3c "your opponent is scripted" to Q&A doc | 1 h | Hub push | Threads the new result into every judge touchpoint |
| **D.9** HF Hub v2 Analyzer LoRA model card refresh + W&B public dashboard | 1 h | None | Polish on the second-most-clicked artifact |
| **E.9** `REPRODUCE.md` 5-step walkthrough (include B.2 phase-1 reproduction steps) | 1 h | D.1 | Judge-friendly reproducibility prose |
| **§9 enhancement** Add 3 quick-test buttons in red-team tab | 40 min | None | Stage-time gold for the demo |

### Phase 3 — Hours 6–10 (onsite GPU sprint if available; B.2 phase 2 is now the lift)
| Task | Effort | Dependency | Impact |
|---|---|---|---|
| **B.2 phase 2** Freeze phase-1 Scammer; retrain v2 Analyzer LoRA against it for 150 ep with W&B per-rubric logging → push v2.1 + plot co-evolution curves → `plots/chakravyuh_plots/coevolution_curves.png` | ~3 h A100 + 1 h wall | A100 access, Hub push done | Converts "two trained agents" into "two trained agents with measured co-evolution" — the strongest possible Theme #1 evidence |
| **B.12** Per-row v2 logits + leakage-clean slice → `docs/leakage_clean_eval.md` | ~0.5 h GPU + 30 min wall | T4 access | Converts the leakage disclosure into a measured OOD number |
| **B.6** Calibration ECE + reliability diagram | ~0.5 h GPU + 30 min | A100 access | Closes a known rigor gap; doubles as the per-rubric trajectory plot |

### Phase 4 — Final 2 hours (drill + dress rehearsal + submit)
| Task | Effort | Dependency | Impact |
|---|---|---|---|
| **A.7** Live pitch rehearsal — 3 timed dry-runs *with* the new B.2 framing | 1.5 h | A.1 done | Storytelling delivery is ≥ 30% of the rubric |
| **A.10** Q&A drill — cold-answer all 5 critical questions (added: "your Scammer's opponent is scripted") | 1 h | None | Live defense |
| **A.4** Fresh-Docker dress rehearsal (last 30 min) | 1 h | None | Eliminates the most embarrassing demo-day failure mode |
| Final submit | 15 min | All above | — |

**Topological order (do not skip ahead):**
§5 Hub push (off-machine, parallel) ‖ D.4 misuse doc → A.1 slide PDF → D.1 → A.8 → D.2 → commit WIN_PLAN+AUDIT → A.3 ‖ A.2 ‖ README/LIVE_PITCH refresh ‖ D.9 ‖ E.9 ‖ §9-enhancement → (if A100) **B.2-phase-2** ‖ B.12 ‖ B.6 → A.7 → A.10 → A.4 → submit.

**The single critical-path edge: D.4 misuse doc must complete before §5 Hub push, because the gated-repo `README` *is* the misuse statement.**

---

## 15. Things to STOP Doing

These are time sinks that do not move the #1 needle. Cut every one.

1. **Refactoring `server/demo_ui.py`** (it's 2,133 LOC; correctly NOT in scope per WIN_PLAN C.6). Judges don't read source.
2. **Multi-seed retrain unless ≥6 GPU-h are *spare* after Phase 3.** The bootstrap CI is sufficient defensive cover; multi-seed is v3 work.
3. **Frontier baseline (A.5)** unless API budget is already in hand. Do NOT cite a frontier number that wasn't measured.
4. **Adding more languages/templates.** 7 languages and 660 templates is enough; effort goes to *measuring* them (B.8) not adding more.
5. **Property-based tests (E.5), CI matrix expansion (E.6), Inspect/Phoenix integration (E.7).** Polish; cut.
6. **Inter-rater κ (D.8).** Timeline-impossible; existing limitations.md disclosure is honest enough.
7. **Curriculum scheduling (B.16), per-rubric weight grid (B.17), calibration-aware retrain (B.15), GGUF release (C.8).** All v3 work; not visible to judges in 12 hours.
8. **Polishing `docs/blog_post.md` beyond the publish minimum.** Publish a 90% draft over a perfect-but-unpublished 100%.
9. **Creating new docs.** You have 19. The next doc judges don't read is the next doc judges don't read.
10. **Anything in WIN_PLAN Bucket E except E.9 (REPRODUCE.md).** All polish; cut.

---

## 16. Final Verdict

**On track for #1?** **Closer than this morning.** B.2 phase 1 SHIPPED converted the single largest defensibility hole (Theme #1 — "you only trained one agent") into a measured result (68.75% Scammer bypass on n=16). **The gap to #1 is now (a) storytelling production + (b) the 15-minute Hub push that turns the new result into a clickable artifact.**

**Honest probability of #1 today as-is (post-B.2-phase-1, pre-Hub-push):** **40–48%**. Strong finalist; the trained Scammer is in a JSON file, not on Hub yet.

**Honest probability after the §5 Hub push (15 min):** **48–55%**. Same evidence, but now verifiable — judges can `peft.PeftModel.from_pretrained(...)` and reproduce. This step alone is worth +5–8pp because it converts a paragraph into an artifact, and *artifacts* are what survive a 5-minute judge skim.

**Honest probability after Phase 1 + Phase 2:** **62–72%**. JC minimums (slide PDF, video, executed notebooks) all satisfied; storytelling cap lifts from ~16/30 to ~26/30.

**Honest probability after Phase 1 + 2 + B.2 phase 2 (co-evolution loop):** **70–80%**. Multi-agent defensibility goes from "two trained agents" to "two trained agents with measured co-evolution curves" — the strongest possible Theme #1 evidence.

**The single change that most increases #1 probability *right now*:**
> **Coordinate the Scammer LoRA HF Hub push with the trainer in the next 15 minutes.** Off-machine work (the adapter files live on the trainer's machine, not this one), but it gates everything downstream — the demo video voiceover, the README submission table, the slide deck refresh, the gated-repo misuse statement. Without the push, "we trained two agents" is a JSON-file-flavored claim; with it, it is a verifiable artifact.

**The two-line action sequence for the next 30 minutes:**
```bash
# 1. On THIS machine — write the misuse statement (D.4) so the Hub README is ready
$EDITOR docs/misuse_dual_use.md   # ~30 min, see WIN_PLAN D.4

# 2. On the TRAINER's machine — push the LoRA (with the misuse doc as the model README)
huggingface-cli login
huggingface-cli repo create chakravyuh-scammer-lora-phase1 --type model
cd checkpoints/scammer_lora_phase1
cp /path/to/Chakravyuh/docs/misuse_dual_use.md README.md
git init && git remote add origin https://huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1
huggingface-cli lfs-enable-largefiles .
git add adapter_config.json adapter_model.safetensors README.md
git commit -m "feat: B.2 phase 1 Scammer LoRA — 68.75% bypass vs ScriptedAnalyzer (n=16)"
git push origin main
# Then in the HF Hub UI: Settings → Access → "Gated"
```

After that: `marp docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf` — go.
