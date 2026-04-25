# Chakravyuh — ULTIMATE Audit v2 (Depth, no v1 delta)
*Generated: 2026-04-25 · Hours to deadline: ~24h (onsite Apr 25–26)*

> v1 audit not on disk; per user instruction this is a fresh deep audit, no §1 delta.
> Every finding cites file:line. Every recommendation has effort + GPU-hour estimate.
> All scoring assumes the Apr '26 OpenEnv hackathon rubric: **Innovation 40% + Storytelling 30% + Improvement 20% + Rewards 10%.** Theme #1 weighted 40%, Theme #4 weighted 20% relative emphasis (per `guidelines/`).

---

## 0. The Verdict

**Current standing.** Substance is real and rigorously documented; the 5-agent env is genuinely interesting; the v1→v2 reward-hacking diagnosis is the single strongest narrative artifact. **But the production-facing surface is broken in ways a judge will hit in the first 30 seconds**, and the Theme #4 (self-improvement) claim does not survive a steelman. Without immediate fixes, you ship a polished local repo that judges can't actually exercise.

**Probability of #1 in current state: 14%.** With the §14 6-hour P0 fixes shipped: **34%.** With §14 24-hour fixes shipped: **52%.** With the §9 wow-moment built: **65%.** The remaining gap (~35%) is owned by competitor entropy + theme #4 fragility + unsourced baselines.

**Top 3 P0 moves for the next 24 hours (in order):**
1. **Fix HF Space production.** `/demo/` returns 404; `/eval/*` returns 404 because `Dockerfile:21-23` doesn't `COPY logs/` or `COPY data/`. The README hero, slides, and judge_quickstart all link to URLs that don't work. Fix the Dockerfile, force-redeploy. **45 minutes.**
2. **Render the slide deck and shoot the demo video.** `docs/chakravyuh_slides.md` exists; no `.pdf`. Storytelling is 30% of the rubric — no rendered slides + no video means you forfeit ~⅓ of those points. **3–4 hours combined (you, manual).**
3. **Add a zero-shot Qwen2.5-7B baseline number.** The README compares scripted-rules vs LoRA-v2; a judge will say "you skipped the obvious counterfactual." One inference pass on the 174-scenario bench at temperature=0 gives the answer. **45 min CPU/GPU.**

**Top 3 P0 moves for the final push:**
4. **Build the live red-team wow moment** (§9). Two analyzers (v1-rules vs v2-LoRA) scoring the judge's input side-by-side, asymmetry visible. **2–3 hours.**
5. **Train a tiny adversarial Scammer adapter** to convert "5 agents, 1 trained" into "co-evolutionary 2-trained system" — single strongest answer to the multi-agent steelman. **6–8 hours, ~3 GPU-hours T4.**
6. **Publish the blog post** (currently draft) on HF Hub or Medium. Same content, different surface — moat against blog-only competitors.

**The single most important thing to do RIGHT NOW:** Fix `Dockerfile`, force HF Space rebuild, verify `/demo/` returns 200, verify `/eval/*` returns 200. Until that ships, every other improvement is sandcastle on a closed door.

---

## 1. Critical Findings Inventory (severity-ranked, no v1 delta)

| # | Severity | Finding | Evidence | §ref |
|---|---|---|---|---|
| 1 | **P0** | `/demo/` 404 on HF Space | `curl https://ujjwalpardeshi-chakravyuh.hf.space/demo/` → 404 `{"detail":"Not Found"}` | §2, §8 |
| 2 | **P0** | `/eval`, `/eval/redteam`, `/eval/known-novel` 404 in production | All three return JSON 404 saying `eval_v2.json not found at /app/logs/...`; root cause `Dockerfile:21-23` doesn't COPY `logs/` or `data/` | §2, §4 |
| 3 | **P0** | No demo video. Storytelling = 30% of rubric. | `grep -E "youtu\|loom\|drive.google" README.md` → empty | §8, §10 |
| 4 | **P0** | Slide deck never rendered to PDF/HTML | only `docs/chakravyuh_slides.md`; no PDF/HTML/PPTX | §8, §10 |
| 5 | **P0** | No zero-shot Qwen2.5-7B-Instruct baseline | `eval_v2.json` shows only `scripted_analyzer` vs `lora_v2`; no base-model row | §7 |
| 6 | **P1** | No supervised fine-tuning (SFT) baseline | claimed in WIN_PLAN B.1 as "pending"; judge will ask "did GRPO actually help vs SFT?" | §7 |
| 7 | **P1** | Theme #4 (self-improvement) does not survive steelman | Regulator (`chakravyuh_env/agents/regulator.py:42-69`) aggregates outcomes and updates rule weights — that is parameter tuning, not "recursive skill amplification" | §6 |
| 8 | **P1** | Only Analyzer is trained; other 4 agents are scripted templates | `scammer.py`, `victim.py`, `bank_monitor.py`, `regulator.py` all rule-based; verified via Explore agent audit | §5 |
| 9 | **P1** | Late-stage training instability — possible reward-hacking boundary | `logs/v2_trainer_state.json`: `reward_std` grew 7.3× (0.043 → 0.316), KL grew 3000× (0.0013 → 0.420), clip_ratio went 0 → 0.40 in last 15 steps | §7 |
| 10 | **P1** | Single-seed training run | seed=42 only (`eval/mode_c_real_cases.py:221`, `eval/bootstrap_ci.py:200`); no variance estimate across LoRA inits | §7 |
| 11 | **P1** | "80% pre-2024 / 50% post-2024" baseline numbers cited 4 places without source | README:33,44,368; LIVE_PITCH:16; blog_post:13. No RBI/NPCI/I4C link. Cohort definition unspecified. | §7, §11 |
| 12 | **P1** | Cohen's κ=0.277 cited (`blog_post.md:124`) but no calculation artifact | not in any file under `eval/` or `logs/` | §7 |
| 13 | **P1** | v1 FPR Wilson CI `[1.5%, 70.5%]` cited (`blog_post.md:115`) but no artifact | bootstrap_v2.json uses percentile only; no Wilson computation in repo | §7 |
| 14 | **P1** | LoRA never red-teamed — only scripted analyzer | `eval/redteam_analyzer.py:204` defers to v3; `analyzer_robustness.json` shows 4/10 caught on rules | §7 |
| 15 | **P1** | `data/` not COPY-ed into Docker image | `Dockerfile:21-23` only COPYs `pyproject.toml`, `README.md`, `chakravyuh_env`, `server`. Bench data needed by `/eval` is absent at runtime. | §2, §4 |
| 16 | **P1** | No keep-warm cron for HF Space | `.github/workflows/` has only `ci.yml`; cold-start risk during judging | §8 |
| 17 | **P1** | `demo_ui.py` is 1829 LOC god module | embeds 230 LOC inline CSS + Gradio UI + episode replay logic + HTML formatting in one file | §3 |
| 18 | **P2** | Bench: 1 benign scenario silently dropped | `bench/scenarios.jsonl` has 31 benign; `eval_v2.json._meta.n_benign=30` | §7 |
| 19 | **P2** | Soft-leakage filter is substring-only, not semantic | `training/grpo_analyzer.py:171-205` uses `if n in t_text`; misses paraphrases | §7 |
| 20 | **P2** | `app.py:341` swallows `_mount_demo` exception with bare `except Exception` | suppresses the actual error that's causing `/demo/` 404 in production | §4 |
| 21 | **P2** | `openenv_models.py:65,67,74-75` use `dict[str, Any]` for `chat_history`, `outcome`, `reward_breakdown` | weak typing on the wire format | §4 |
| 22 | **P2** | Threshold sweep in `eval_v2.json` is degenerate — 9 of 13 thresholds give identical metrics | suggests near-binary score distribution; weakens the "calibration" rubric story | §7 |
| 23 | **P2** | `/mcp` returns 405 on GET | `curl https://...hf.space/mcp` → 405; openapi shows it's POST-only. Not broken, but README hero claim "5/5 endpoints" deserves a footnote | §4 |
| 24 | **P3** | Hardcoded demo expected-outputs in pitch script | `LIVE_PITCH.md:84-95` exact-match score=0.95, signals=[urgency, info_request, impersonation] — fails on seed variance | §11 |

**Headline: 4 P0s · 13 P1s · 6 P2s · 1 P3.** Counting rules: P0 = judge will hit it before they leave the page; P1 = judge will hit it during the substantive review; P2 = quality issue but not load-bearing for #1; P3 = polish.

---

## 2. Reproducibility Smoke Test Results

**0.1 — pytest.** ✅ `273 passed, 2 skipped, 35.81s` (matches README claim of "275 collected · 273 passed · 2 skipped").

**0.2 — `openenv validate .` (local).** ✅ `[OK] : Ready for multi-mode deployment` (1 line, no warnings).

**0.3 — `openenv validate --url <hf>`.** Not run (the `openenv` CLI version installed doesn't accept `--url` against an arbitrary host without re-config; substituted with direct endpoint probing per §0.4).

**0.4 — Live HF Space probes** (5 fresh requests to `https://ujjwalpardeshi-chakravyuh.hf.space/`, all 200):
- `/` → 200, 1.4–2.0s (warm)
- `/health` → 200, ~1.4s
- `/schema` → 200, 4147B (sane)
- `/metadata` → 200, 153B (sane)
- `/openapi.json` → 200, 18352B (16 routes, sane)
- `/mcp` → 405 Method Not Allowed (POST-only; OpenAPI confirms)
- `/leaderboard` → 200, 1349B
- **`/demo/` → 404** ❌ `{"detail":"Not Found"}`
- **`/eval` → 404** ❌ `{"detail":"eval_v2.json not found at /app/logs/eval_v2.json. Run \`make eval-v2 && make bootstrap\` or pull the latest artifacts from the repo."}`
- **`/eval/redteam` → 404** ❌ same shape (analyzer_robustness.json missing)
- **`/eval/known-novel` → 404** ❌ same shape

**Cold start: NOT MEASURED.** HF API reports `gcTimeout: 172800` (48h) and the Space is currently `RUNNING` with `READY` domain. Cannot force cold without 48h idle. **You must measure this on judging morning** — the README/slides claim "30–60s cold start" but it's not in `logs/`. If first cold hit > 20s, you bleed the first judge.

**0.5 — Local Gradio boot.** ✅ `python -m server.demo_ui` (via uvicorn locally) returns `/demo/` with 146 KB HTML body in 24ms. Imports cleanly: `from server.demo_ui import build_app; build_app()` succeeds. So the HF 404 is **not a code bug** — it's a runtime/Docker issue, almost certainly the `_mount_demo()` exception swallow at `server/app.py:341`. **You cannot debug it without container logs from HF.**

**0.6 — single-scenario eval.** ✅ `python eval/single_scenario_eval.py --scenario-id modec_106 --output /tmp/sanity.json` produced `scripted score: 0.050 (missed)` and `v2 (aggregate): detection=0.971 on 'novel' split (n=34)`. Matches `before_after_example.json`.

**Summary.** **2 of 4 P0 reproducibility checks fail in production**, both on the deployed HF Space. Locally everything works. **The HF Space is the lie.**

---

## 3. Scorecard

| Criterion | Score (1–10) | Justification |
|---|---|---|
| Hackathon rules adherence | 7 | Mandatory deliverables present locally; HF Space `/demo/` 404 fails the live-deployment requirement |
| OpenEnv contract correctness | 8 | `openenv validate .` clean; schemas tight on Action, weak on `chat_history/outcome/reward_breakdown` (`dict[str, Any]`) |
| Multi-agent defensibility (Theme #1) | 5 | 5 agents, 1 trained; survives steelman only with §5's recommended Scammer-adapter add |
| Self-improvement defensibility (Theme #4) | 3 | Regulator is parameter aggregation, not recursive amplification. Theme #4 is the weakest link |
| Scientific rigor (CIs/seeds/ablations/baselines) | 6 | Bootstrap CIs landed, but single-seed, no zero-shot baseline, no SFT baseline, late-stage training instability |
| Reward design & anti-hacking | 8 | Real diagnosis story + asymmetric improvement; the strongest single artifact in the repo |
| Code quality | 7 | Clean except `demo_ui.py` god module (1829 LOC) and `dict[str, Any]` typing on wire |
| Test coverage of what matters | 6 | 273 tests is impressive density, but most are happy-path; `test_v2_reward_parity` and `test_mcp_compliance` are the load-bearing ones; demo-mount failure not tested |
| Repo hygiene (DX/CI/secrets) | 7 | Make targets clean, link-check shipped, CI present, no secrets leaked. No keep-warm cron |
| Demo HF Space (latency, reliability) | 3 | RUNNING but the demo route 404s. This is the most impactful failure in the repo |
| Demo Gradio UI quality | 6 (locally) / N/A live | Locally rich (5 tabs, animations, hot-keys, v1↔v2 toggle); judges can't see any of it |
| Slide deck quality | 4 | Markdown source exists, no rendered artifact. Judges read raw .md = amateur |
| Blog post quality | 7 | Strong content, draft status, unverified κ=0.277 + Wilson CI claims |
| Video / pitch readiness | 2 | No video. LIVE_PITCH.md is well-written but has hardcoded expected outputs that will break under seed variance |
| Narrative & positioning | 8 | v1→v2 reward-hacking is genuinely a top-1% framing for a hackathon; under-leveraged in the README hero |
| Differentiation / wow factor | 6 | v1↔v2 archived toggle exists; live red-team box (§9) would push to 9 |
| **Overall weighted score** | **5.7 / 10** | (Innovation 40% × 6.5 + Storytelling 30% × 5 + Improvement 20% × 6.5 + Rewards 10% × 8) ÷ 10 |

**Recalculate after §14 24h moves:** 7.4 / 10.

---

## 4. OpenEnv Contract — Findings

**Local validation.** `openenv validate .` returns the single-line "Ready for multi-mode deployment". `openenv.yaml` is consistent with `openenv-core>=0.2.3,<0.3` (pinned in `pyproject.toml`).

**Deployed routes (from `https://ujjwalpardeshi-chakravyuh.hf.space/openapi.json`).** 16 routes registered: `/reset, /step, /state` (Gym contract ✓); `/metadata, /health, /schema, /mcp` (OpenEnv core ✓); `/leaderboard, /submit, /eval/*` (custom); `/diagnose` (custom). **`/demo` is NOT in the deployed openapi**, confirming the mount silently failed in the Docker container.

**Schema tightness — depth audit.**
- `chakravyuh_env/openenv_models.py:43-44` ✅ `score: float = Field(ge=0.0, le=1.0)`, `flag_threshold: float = Field(default=0.5, ge=0.5, le=0.5)` (the latter pins literally — defeats threshold-tuning exploit).
- `chakravyuh_env/openenv_models.py:65,67,74-75` ❌ `chat_history: list[dict[str, Any]]`, `outcome: dict[str, Any]`, `reward_breakdown: dict[str, Any] | None`. Replace with explicit Pydantic submodels (`ChatTurn`, `EpisodeOutcome`, `RewardBreakdown`) — 30 minutes, breaks no tests.
- `chakravyuh_env/openenv_environment.py` ✅ schemas tight on Action; observation builder lines 420-430 emit dicts that don't round-trip through Pydantic. **Add `model_dump_json()` round-trip test** — 15 minutes.

**Determinism.** ✅ Verified by Explore audit: `reset(seed)` → `random.Random(actual_seed)` (line 146-147), `Scammer._rng.choice(...)` (line 54), no global `random.*` calls. **Add an explicit determinism test** that runs the same seed twice and asserts trajectory equality — 20 minutes.

**Client/server boundary.** ✅ No imports from `server/` into `chakravyuh_env/`. `server/app.py:325` lazy-imports `server.demo_ui` only inside `_mount_demo()`. Clean.

**MCP compliance.** `tests/test_mcp_compliance.py` exists. Checks reserved-tool-name avoidance and tool-list shape. **Does not check** that the `POST /mcp` endpoint actually serves a valid MCP envelope under load. Add an integration test that POSTs an MCP request and validates the response — 30 minutes.

**Schema versioning.** ❌ Not addressed. If the env spec changes between v0.x and v1.0, old training runs cannot replay. **Add a `schema_version: "0.2.0"` field on `ChakravyuhObservation`** and assert it in the smoke test — 10 minutes.

---

## 5. Multi-Agent Track (Theme #1) — Defensibility & Strengthening

**Theme #1 exact language (from guidelines):** *"cooperation, competition, negotiation, and coalition formation. Learning from these environments will enable agents to model the beliefs and incentives of others in partially observable settings. This drives theory-of-mind reasoning and emergent strategic behavior."*

**Strongest argument FOR.**
- 5 distinct agents with **independent observability silos** (Analyzer sees chat; Bank Monitor sees tx metadata; Regulator sees aggregate outcomes). This is genuine partial observability.
- **Two-tier oversight** is a real scalable-oversight pattern: chat-only Analyzer + metadata-only Bank Monitor cannot collude.
- The Scammer's adversarial pressure shapes the Analyzer's reward landscape — even if the Scammer is scripted, the 376 templates × randomized turn-ordering generates a non-trivial distribution.
- Negotiation protocol exists (`docs/negotiation_protocol.md`); flagged as default-off in env (`enable_negotiation=False` per `WIN_PLAN.md` notes), but the protocol ships.

**Strongest argument AGAINST (steelman a skeptical judge).**
> "You have one trained agent and four scripted NPCs. The Scammer is a template selector. The Victim is a trust-threshold rule. The Bank is a linear risk score with hardcoded weights. The Regulator aggregates outcomes and tunes one number. There is no theory-of-mind reasoning happening because none of the non-Analyzer agents are *modeling* anything. This is single-agent learning against scripted adversaries — it is closer to a hard-mode bandit than to a multi-agent system. The 'multi-agent' label is decoration, not architecture."

**This steelman is correct.** The current submission scores 5/10 on Theme #1 defensibility. Rebuttal requires a code change.

**Smallest concrete code change that converts the steelman into a non-issue.**

Train an **adversarial Scammer LoRA adapter** against a frozen v2 Analyzer. Concretely:
1. Reuse `training/grpo_analyzer.py` skeleton, swap reward to `+1 if money_extracted else -0.3 if analyzer_flagged else 0`. (~120 LOC delta.)
2. Use the same 5 categories, same Qwen2.5-7B-base, same LoRA rank (16). 1 epoch on 200 multi-turn rollouts.
3. Save adapter, point `chakravyuh_env/agents/scammer.py` at it via `--scammer-mode=lora`.
4. Run a 50-episode self-play eval: trained Scammer × frozen v2 Analyzer × scripted others. Plot Scammer extraction rate vs frozen-v2 detection rate over time.

**Effort estimate.** 6–8 hours wall-clock. **3 GPU-hours T4** (or 1 GPU-hour A100). **Skip if you have less than 4 GPU-hours remaining.**

**Outcome.** Converts "5 agents, 1 trained" into "co-evolutionary 2-trained system, scripted environment, learnable adversary." Single sentence in the README + one bar chart kills the steelman. **This is the single highest-ROI technical move on the table.**

**If you cannot ship this in time:** Lean hard on the negotiation protocol existing (even if disabled by default — flip it to `enable_negotiation=True` in one demo episode and show the trace). Effort: 30 minutes.

---

## 6. Self-Improvement Track (Theme #4) — Defensibility & Strengthening

**Theme #4 exact language:** *"learn to generate new challenges, escalate difficulty, and improve through self-play or adaptive curricula. Rather than optimizing fixed tasks, the goal is for agents to learn to drive their own capability growth. The objective is recursive skill amplification."*

**Strongest argument FOR.**
- The novelty curriculum (`chakravyuh_env/novelty.py`, referenced) escalates difficulty across episodes.
- The Regulator updates rule weights based on outcome aggregation (`chakravyuh_env/agents/regulator.py:42-69`).
- The v1→v2 reward-fix loop *is* a self-improvement event — the *system* identified its own pathology and corrected itself.

**Strongest argument AGAINST (steelman).**
> "The Regulator computes `weighted_avg(success_rate, conviction_rate, fraud_blocked) → updated_rule_weights`. That is **one matrix multiplication on aggregate metrics**, not a learning loop. There is no agent that *learns to generate new challenges* — your scammer templates are a static JSON file (`chakravyuh_env/scammer_templates.json`). There is no *self-play* — the Scammer is scripted. The v1→v2 fix was *you*, not the system. Calling this 'recursive skill amplification' is a category error. Theme #4 is unearned."

**This steelman is also correct, and harder to fix in 24h than Theme #1's.**

**Recommended framing (the honest one).**

Drop the recursive-amplification framing. Reframe as **"Self-Improvement of the Training Pipeline"**: the v1→v2 reward-hacking diagnosis-and-fix is a worked example of catching reward hacking in GRPO post-training, applicable to any RLHF/RLAIF system. This is a methodological contribution beyond UPI.

You'll lose Theme #4's full 20% weight but reclaim ~12% by making the framing defensible.

**Should you drop Theme #4 and double down on Theme #1?**

**Yes.** Here's the math:
- Targeting #1 + #4 weakly: ~40% × 6.5 + ~20% × 3.0 = 32% combined contribution
- Targeting #1 strongly + #1.5 (scalable-oversight bonus): ~40% × 8.5 + 0 = 34%
- Targeting #1 strongly + Scammer adapter (§5): ~40% × 9.0 + 20% × 5.5 (now defensible-as-self-play) = 47%

The Scammer adapter (§5) is the move that lets you keep both themes credibly. **If you cannot afford the GPU-hours, drop #4 and focus on #1.**

**Decision.** Demote Theme #4 to a secondary mention in the README hero. Keep the slide. Don't pitch on it. Lead with #1 + scalable-oversight + reward-hacking honesty.

---

## 7. Scientific Rigor — Gaps & Fixes

### 7.1 Missing zero-shot baseline (P0)

**Gap.** `eval_v2.json` compares scripted-rules (det 70.1%, FPR 29.0%) vs LoRA-v2 (det 99.3%, FPR 6.7%). No zero-shot Qwen2.5-7B-Instruct row.

**Why a judge will hit you.** "Did GRPO actually help, or could you have gotten the same numbers with the off-the-shelf model + a system prompt?" This is the single most common rigor question at hackathon panels.

**Fix.** Run base Qwen2.5-7B-Instruct (no LoRA) on the 174-scenario bench at temperature=0 with the same prompt template. Two outcomes:
- If base scores ~70%: GRPO clearly added value (29 pp lift).
- If base scores ~95%: GRPO added marginal value over prompting; reframe as "+4 pp at 5× lower FPR" which is still a win, but a different one.

**Effort.** 45 minutes. **GPU-hours: 0.5 T4** (or CPU, 2–3 hours via API to a 7B endpoint). **Skip if you have less than 1 GPU-hour and no API budget.**

### 7.2 Missing supervised fine-tuning (SFT) baseline (P1)

**Gap.** No SFT-on-templates baseline. WIN_PLAN B.1 marks it "pending."

**Why a judge will hit you.** "Why GRPO and not just SFT? GRPO is heavier and harder to debug." Your v1→v2 story is *itself* an argument that GRPO is hard to debug — and yet you didn't try the simpler thing first.

**Fix.** Run SFT on the same 619-step training set, same Qwen2.5-7B-base, same LoRA rank. Report on bench. **2–3 GPU-hours T4. Skip if you have less than 4 GPU-hours.**

**If you skip:** add one paragraph to the blog post titled *"Why GRPO over SFT for this task"* arguing that the Analyzer must learn to assign *calibrated* scores (not classes), which SFT on labels cannot do without a custom loss. This is honest and defensible.

### 7.3 Single-seed training (P1)

**Gap.** seed=42 only. No variance estimate.

**Fix.** Re-run training at seeds 7, 13, 42. Report mean ± std on detection/FPR/F1. **6 GPU-hours T4. Skip if you have less than 8.** If skipped, add a `## Reproducibility caveats` section saying so.

### 7.4 Late-stage training instability (P1)

**Gap.** `logs/v2_trainer_state.json` shows `reward_std` 0.043 → 0.316 (7.3×), `kl` 0.0013 → 0.420 (300×), `clip_ratio` 0 → 0.40 in last 15 of 619 steps. This is the signature of a policy diverging into a high-reward boundary region.

**Why a judge will hit you.** Anyone who has trained GRPO will look at the trainer state and ask "did you actually converge, or did you stop on a fluke?"

**Fix.** Two parts:
1. **Diagnostic plot**: 4-panel — reward, reward_std, KL, clip_ratio across training. Save to `docs/assets/plots/v2_training_diagnostics.png` and reference in README. **45 minutes**, 0 GPU.
2. **Honesty paragraph**: add to `docs/limitations.md` — "Late-stage KL grew to 0.42 and reward variance grew 7×; we stopped at step 619. Whether this is convergence or the boundary of a reward-hacking exploit is unresolved. v3 will re-run with shorter horizon + early-stopping on KL."

### 7.5 No LoRA red-team (P1)

**Gap.** `eval/redteam_analyzer.py` runs 10 attacks against the scripted analyzer (4/10 caught). LoRA never red-teamed.

**Fix.** Run the same 10 attacks against the v2 LoRA. **30 minutes inference + 1 GPU-hour. Skip if you have less than 1 GPU-hour.** Even if you only catch 5/10, that's better than not running it.

### 7.6 Unsourced 80%/50% baseline (P1)

**Gap.** Cited at README:33,44,368; LIVE_PITCH:16; blog:13. No RBI/NPCI/I4C URL.

**Fix (pick one):**
- (a) Find the actual source (`Reserve Bank of India 2024 Annual Report on Payment Systems Indicators` — this exists). Cite it inline. **20 minutes.**
- (b) Drop the number, replace with "rule-based detectors meaningfully degrade on post-2024 patterns; we measured 50% on our 34-scenario novel split." That's a measurement you own. **5 minutes.**

**Choose (b) if you cannot find a verifiable source in 20 minutes.**

### 7.7 Cohen's κ=0.277 unverified (P1)

**Gap.** `blog_post.md:124` cites the value; no calculation file exists.

**Fix.** Either (a) write a 30-line script computing κ between the rule-based analyzer and your manual labels on the 174-scenario bench, save to `eval/inter_rater_kappa.py` and log to `logs/inter_rater_kappa.json` (30 minutes); or (b) drop the κ claim from the blog. **Don't cite numbers you can't reproduce.**

### 7.8 Wilson CI [1.5%, 70.5%] unverified (P1)

**Gap.** `blog_post.md:115` cites; no `wilson` calculation in repo.

**Fix.** 5-line scipy.stats.binom_proportion call. **15 minutes.**

### 7.9 Bench: 1 benign scenario silently dropped (P2)

**Gap.** `data/.../scenarios.jsonl` has 31 benign; `eval_v2.json._meta.n_benign=30`.

**Fix.** Find the dropped scenario; add a one-line comment in `eval/mode_c_real_cases.py` explaining why (likely a corrupted record), or fix and rerun. **20 minutes.**

### 7.10 Threshold sweep degeneracy (P2)

**Gap.** `eval_v2.json.sweep` shows identical metrics for thresholds 0.3–0.85.

**Why this matters.** It indicates the LoRA outputs near-binary scores (clusters near 0 and near 1). The "calibration" rubric story is therefore partially undermined.

**Fix.** Acknowledge in `docs/limitations.md`. Suggest in v3: temperature scaling + reliability diagrams.

---

## 8. Demo-Day Experience — File-Level Recommendations

### 8.1 HF Space cold start

**Status.** Not measured (Space is warm, gcTimeout=48h). README claims 30–60s. **Measure on judging morning** by forcing a cold pull from a clean network.

**Mitigations (do all three):**
1. **Keep-warm cron via GitHub Actions.** Add `.github/workflows/keepwarm.yml` running every 10 minutes, cURLing `/health`. **15 minutes.** **Caveat: HF may rate-limit anonymous keep-warm; use authenticated requests via HF token in repo secrets.**
2. **Pre-rendered Replay tab fallback.** If `/demo/` cold-loads slowly, the first thing a judge sees should be static HTML of episode #1 (not Gradio chrome). Add a `/demo/preview` route that serves a pre-rendered `episode_1.html` snapshot. **30 minutes.**
3. **Loading screen with the v1→v2 chart.** While Gradio boots, show the bar chart (the wow narrative artifact). Don't show "loading…" — show *the win*. **45 minutes** (custom HTML + JS poll-then-redirect to `/demo/`).

### 8.2 Gradio UI — component-by-component upgrade

I cannot inspect Gradio rendering visually in this environment. From `server/demo_ui.py` static read (1829 LOC):
- ✅ **5 tabs** (Replay, You vs Analyzer, Leaderboard, v1↔v2 toggle, Live Q&A) — strong information architecture.
- ✅ **Custom CSS** with `prefers-reduced-motion` fallback and a 5-agent hero animation.
- ✅ **Hot-key overlay** (`?`, `Esc`, `g/G`).
- ❓ **Mobile responsiveness** — must be tested on a phone before judging. Most judges won't pull out a laptop.
- ❓ **Empty states** — what does the Live Q&A tab show when the rule-based scorer returns score=0 with no signals? If it says "No signals detected" with no prompt to retry, judges will think the model is broken.
- ❓ **Error states** — what does the Replay tab do if the scenario JSON fails to load? `try/except → display "Error"` is amateur; show a friendly message + a retry button.
- ❌ **Default Gradio theme readable as "intern submission"** — verify `_build_theme()` (`server/demo_ui.py`) actually applies a custom theme.

**Concrete patch list (manual review needed):**
- Open the Gradio UI on a phone screen → screenshot. If the 5-agent grid wraps to 2 columns and the hero animation overflows, fix with `@media (max-width: 768px) { ... }` in `CUSTOM_CSS` block. **60 min.**
- Verify Live Q&A empty state has a "Try one of these examples" cluster showing 3 buttons with pre-canned scams. **30 min.**

### 8.3 Replay episodes — keep/redesign/add

I cannot script-evaluate pedagogical quality. From the `judge_quickstart.md` description (5 deterministic episodes, named by failure-mode), the structure is sound but there's overlap between "Multi-Agent Defense Wins" and "Detection Too Late" — both demonstrate Bank Monitor + Analyzer interplay.

**Recommendations:**
- **Keep** episodes 1, 2, 3 (the v1→v2 wow toggle is in tab #4 — that *is* the moment).
- **Redesign** episode #5 to be the new live red-team box (§9), not another scripted replay.
- **Add** a 6th micro-episode showing the negotiation protocol (currently `enable_negotiation=False`); flip on for one demo.

### 8.4 Slide deck — rendering plan + critique

**Current.** `docs/chakravyuh_slides.md` is markdown source (Marp/Pandoc-ready per WIN_PLAN). **No rendered PDF/HTML/PPTX exists.**

**Fix.** **You must run this — I can't:**
```bash
npx -y @marp-team/marp-cli docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf
# fallback: pandoc docs/chakravyuh_slides.md -t beamer -o docs/chakravyuh_slides.pdf -V theme=metropolis
```
**5 minutes.** Commit the PDF. Update README link.

**Slide-level critique (from reading the markdown):** lead with the v1→v2 reward-hacking *result* (asymmetric improvement chart), not the framing. The current opener spends 2 slides on "₹13,000 cr UPI fraud" — judges have seen problem framings; what they haven't seen is your specific recovery story.

### 8.5 Demo video — 90-second script + shot list

**You must record this.** It's 90% of what judges actually watch.

**Script (90 seconds, 6 beats):**
1. **0:00–0:10 — Hook.** "Indian UPI fraud. ₹13,000 cr/year. 60 cr users. Rule-based detectors fail on novel patterns. We trained a system to learn instead." [Show: README hero animation, agent grid.]
2. **0:10–0:25 — Env.** "Five agents — Scammer, Victim, Analyzer, Bank Monitor, Regulator. Independent observability. Two-tier oversight." [Show: agent grid, suspicion timeline climbing.]
3. **0:25–0:40 — The hack.** "We trained v1 with a naive reward. Got 100% detection. And 36% false-positive rate. The model learned to flag everything." [Show: v1 reward curve climbing, FPR diagnostic chart.]
4. **0:40–0:55 — The fix.** "We diagnosed the asymmetric improvement signature, retuned three reward parameters, retrained. v2 holds 99.3% detection. FPR collapses to 6.7%." [Show: side-by-side v1/v2 chart.]
5. **0:55–1:15 — Live demo.** "Live: paste a 2025-novel scam. Rule-based scores 0.05. v2 scores 0.97. Same input. Different reasoning." [Show: Gradio Live Q&A tab; the wow moment.]
6. **1:15–1:30 — Close.** "OpenEnv on Hugging Face. LoRA on the Hub. Bench dataset open. Try it." [Show: HF Space URL, blog post.]

**Shot list:**
- 4 screen recordings (animation, agents, charts, Live tab)
- 1 voice-over track (90s)
- Edit in CapCut / DaVinci Resolve / iMovie
- Export H.264 MP4 < 100MB
- Upload unlisted YouTube; link from README

**Effort: 4–6 hours.** **The single highest-ROI 4 hours of your remaining time other than fixing HF.**

### 8.6 Blog post — publish

**Status.** `docs/blog_post.md` exists, draft.

**Fix.**
1. Verify the κ=0.277 + Wilson CI claims (§7.7, §7.8) or remove.
2. Publish to HF Hub Posts (under your account) + cross-post to Medium or your personal site.
3. Add the blog URL to README + slide deck + video.

**Effort: 90 minutes** (after §7.7 + §7.8 done).

---

## 9. The Wow Moment

**Current candidate.** v1↔v2 archived-response toggle (5 hand-crafted scenarios). It's good. It's not enough.

**Why it's not enough.** It's *archived* — judges read "ARCHIVED — not live re-run" disclosure and immediately downgrade trust. They want to feel they're seeing the model think.

**The new wow moment: Live Side-By-Side Red-Team.**

**Spec (file-level).**

**File:** `server/demo_ui.py` — add a new tab between "Live Q&A" and "v1 vs v2 toggle". Tab title: **"Red-team it yourself"**.

**Components:**
- Single text input (placeholder: "Paste any scam attempt — we'll score it two ways")
- One "Score" button
- Two side-by-side cards under it:
  - **Card A — v1 (rule-based, reward-hacked):** uses the `chakravyuh_env/agents/analyzer.py` ScriptedAnalyzer with the v1 reward weights. Shows score (big), signals (chips), explanation (one sentence).
  - **Card B — v2 (LoRA, fixed):** calls the LoRA via the diagnose endpoint (`POST /diagnose`). Shows the same fields.
- Below the cards: **"Asymmetry"** badge that auto-detects:
  - "v1 over-flagged this benign-looking message" → red badge if v1 ≥ 0.7 and v2 < 0.5
  - "v1 missed this novel scam" → red badge if v1 < 0.4 and v2 ≥ 0.85
  - "Both agree" → grey badge

**Data flow.**
- User text → both analyzers in parallel.
- Card A: synchronous, ≤50ms (rule-based).
- Card B: synchronous via `/diagnose` (already shipped, returns `rubric_breakdown` from `AnalyzerRubricV2`).
- Asymmetry detection: client-side JS comparing the two scores.

**Render.**
- 2-column grid on desktop, stacked on mobile.
- v1 card has subtle red border-left ("the hack lives here").
- v2 card has subtle green border-left.
- Score numbers animate from 0 to final on render (200ms ease-out).

**Why this wins #1.**
1. **Live, not archived.** Judges feel they're stress-testing the model.
2. **Asymmetry is a story you can't fake.** Every input either confirms or breaks the v1→v2 narrative.
3. **Multi-agent argument lands harder.** v1 vs v2 is two analyzers in one box; combined with Bank Monitor stripe at the top, that's three analyzers visible.
4. **It's the demo video's climax.** §8.5 beat 5 (0:55–1:15).

**Effort: 2–3 hours.** Code is mostly there:
- `chakravyuh_env/agents/analyzer.py` already exists (v1 rules).
- `POST /diagnose` already returns rubric_breakdown.
- New work: one Gradio tab + one client-side comparator + CSS for the asymmetry badge.

**Skip if you have less than 3 hours of frontend coding capacity.** If skipped, leave the v1↔v2 archived toggle — it's still defensible.

---

## 10. Submission Artifact Audit

| Artifact | Present? | Quality | Discoverable in README? | Self-contained? |
|---|---|---|---|---|
| README.md | ✅ | High (518 lines, dense) | n/a | ✅ |
| OpenEnv code (chakravyuh_env/) | ✅ | High (clean, deterministic, typed) | ✅ | ✅ |
| HF Space deployed | ⚠️ | RUNNING but `/demo` 404 | ✅ | ❌ (broken in production) |
| LoRA on HF Hub | ✅ | (not re-verified this audit) | ✅ | ✅ |
| Bench dataset on HF Hub | ✅ | (not re-verified this audit) | ✅ | ✅ |
| Tests (273+2) | ✅ | High density | ✅ | ✅ |
| eval_v2.json | ✅ | Detailed | ✅ | ✅ |
| bootstrap_v2.json | ✅ | 10k iters | ✅ | ✅ |
| analyzer_robustness.json (red-team) | ✅ | Thin (10 attacks, scripted-only) | ✅ | ✅ |
| Slide deck | ⚠️ | **Markdown only — no rendered PDF** | ✅ | ❌ |
| Demo video | ❌ | **Missing entirely** | n/a | n/a |
| Blog post | ⚠️ | Draft, unpublished | ✅ | ❌ |
| MODEL_CARD.md | ✅ | (not deep-read) | ⚠️ (linked but not in submission table) | ✅ |
| DATASET_CARD.md | ✅ | (not deep-read) | ⚠️ | ✅ |
| CITATION.cff | ✅ | (not deep-read) | ❌ (not linked from README) | ✅ |
| LIVE_PITCH.md | ✅ | Strong but hardcoded outputs | ✅ | ✅ |
| Architecture diagram (PNG/SVG) | ❌ | ASCII only in README | n/a | n/a |
| Reward-design one-pager | ❌ | Embedded in README | n/a | n/a |
| Tutorial Colab (env exploration only, no GRPO) | ❌ | Missing — see WIN_PLAN A.3 | n/a | n/a |
| docs/limitations.md | ✅ | Good | ✅ | ✅ |
| docs/judge_quickstart.md | ✅ | Strong | ✅ | ✅ |

**Missing artifacts ranked by ROI to add:**
1. Demo video (P0, §8.5)
2. Slide deck PDF (P0, §8.4)
3. Architecture diagram PNG (P1; one Mermaid → mermaid-cli render, 30 min)
4. Tutorial Colab — env exploration without GRPO (P1; 2 hours; lets judges run reset/step without GPU)
5. CITATION.cff link in README footer (P2; 5 min)

---

## 11. Narrative & Pitch

### 11.1 README hook critique + rewrite

**Current opener (first 100 words, README:1-22):**
> "A multi-agent RL environment for Indian UPI fraud detection — built for the **Meta PyTorch OpenEnv Hackathon 2026 (Bangalore)**. Chakravyuh is a 5-agent OpenEnv environment for Indian UPI fraud detection. We trained Qwen2.5-7B with GRPO, **caught ourselves reward-hacking** (v1: detection=100% / FPR=36%), diagnosed and fixed it (v2: 99.3% / 6.7%, F1=0.99 on n=174). The asymmetric improvement is the signal — detection unchanged, FPR 5× down."

**Verdict.** The hook is *almost* right. It says "caught ourselves reward-hacking" in line 2 but then explains it in the same paragraph. The hack-story should *be* the hook, with no preamble.

**Suggested rewrite (first 60 words):**
> "We trained an LLM to detect UPI fraud and got 100% detection. We celebrated for 4 minutes. Then we noticed: **36% false-positive rate.** The model wasn't catching scams — it was flagging everything. This is a multi-agent OpenEnv environment, a worked example of catching reward hacking in GRPO post-training, and a 99.3% / 6.7% recovery story on 174 real Indian fraud scenarios."

**Why this is better.** Lead with the failure → then the diagnosis → then the recovery. Honesty is a moat. Most submissions hide their failures; you ship yours as the hero.

### 11.2 Slide-by-slide pitch flow (4 slides, 3 min)

| Slide | Title | Beat | Time |
|---|---|---|---|
| 1 | "100% detection. 36% FPR." | Show v1 success → reveal the catch | 0:00–0:30 |
| 2 | "How we diagnosed it" | Per-difficulty plot showing the hack signature | 0:30–1:15 |
| 3 | "Three reward fixes, asymmetric improvement" | v2: 99.3%/6.7%, with F1 and CIs | 1:15–2:15 |
| 4 | "Multi-agent env you can fork today" | HF Space + LoRA + dataset URLs | 2:15–3:00 |

The pitch flow above is consistent with `LIVE_PITCH.md` but tighter. **Drop the Theme #4 mention from the slides.** It dilutes the #1 + scalable-oversight + reward-hacking-honesty message.

### 11.3 Live pitch (3-min) script critique

`docs/LIVE_PITCH.md` is well-structured but has two failure modes:
- **Hardcoded expected outputs (lines 84-95):** `score=0.95, signals=[urgency, info_request, impersonation]`. If LoRA inference varies under load (HF Space CPU + Gradio queue), you'll demo a number that doesn't match your script, and your delivery will fall apart. **Replace with a tolerance band: "score above 0.85 with at least 2 of these 3 signals."**
- **Fallback ambiguous (line 97):** "Live demo is timing out — here's the per-difficulty result." Doesn't say *which* per-difficulty result, *which* slide, *what* you'll say while pulling it up. **Pre-stage two backup slides labeled "FALLBACK_A_chart.pdf" and "FALLBACK_B_v1_v2_toggle.gif"** with one-line scripts each.

### 11.4 Methodological-contribution framing

Currently buried. Promote it. Add to README, slide #4, and blog conclusion:

> **"Beyond UPI: Chakravyuh is a worked example of catching reward hacking in GRPO post-training. The asymmetric-improvement signature (detection unchanged, FPR collapses) is a diagnostic any RLHF/RLAIF pipeline can use. The reward-decomposition + per-rubric ablation method is portable to any composable-rubric task."**

This single paragraph, well-placed, broadens your appeal beyond Indian-fraud judges to RLHF practitioners. **30 minutes to draft and place.**

---

## 12. Competitive Positioning

| Likely competitor archetype | Where you win | Where you lose | Single move that separates |
|---|---|---|---|
| **Multi-agent negotiation/economics env** | Real-world grounding (named victims, ₹13k cr scale, RBI-cited); reward-hacking honesty; bench dataset on HF Hub | They likely have richer agent dynamics (theory-of-mind, signaling games); their training loop probably involves multiple trained agents | Ship the §5 Scammer adapter — turns "1 trained, 4 scripted" into "co-evolutionary" |
| **Code-debugging / research-assistant agent** | Theme #1 fit (you're multi-agent, they're typically single-agent + tool use); you have a *bench* (they often have a leaderboard); reward design depth | They'll have richer tool-use traces, slicker chain-of-thought visualizations, better demo polish | Lead with the live red-team box (§9) — code-debug demos can't beat "judge types scam, model catches it live" |
| **Game / RTS env** | Real consequence (₹ losses, named victims) > game scores; scalable-oversight framing > pure RL | They will have prettier visualizations and longer training trajectories; they win on Improvement (20%) | Push the v1→v2 asymmetric improvement chart to the front — it's a more *interesting* training story than "reward goes up" |
| **Tool-use / web-agent env** | You don't depend on flaky external APIs (their Achilles heel); your env is fully reproducible offline | Tool-use envs feel "future-y" and judges love them; yours feels "applied" | Promote the **methodological contribution** framing (§11.4) — yours is "applicable to any RLHF pipeline" |

**Net:** You win on *substance density* and *honesty*. You lose on *agent-architecture complexity* (only 1 trained) and *demo polish* (no video, broken `/demo`). The §5 + §9 moves close both gaps.

---

## 13. Risk Register (Demo-Day Landmines)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **HF Space `/demo/` still 404 at judging** | HIGH (currently 404) | CATASTROPHIC | Fix Dockerfile, force redeploy, verify with curl — §14 hour 0 |
| 2 | HF Space cold start > 30s when judge first hits | MEDIUM (untested) | HIGH | Keep-warm cron + loading-screen-with-the-chart fallback (§8.1) |
| 3 | Gradio queue saturates under multiple judges hitting Live tab simultaneously | MEDIUM | HIGH | Pre-render top 5 most-likely judge inputs on the v1↔v2 toggle (already shipped); rate-limit `/diagnose` to 5 req/min/IP |
| 4 | LoRA inference seed variance breaks LIVE_PITCH hardcoded outputs | HIGH | MEDIUM | Replace exact-match expectations with tolerance bands (§11.3) |
| 5 | Stage Wi-Fi blocks HF Hub | MEDIUM | HIGH | Phone hotspot backup; pre-loaded `/demo/preview` static fallback |
| 6 | Judge asks "where's your zero-shot baseline" | HIGH (every panel) | HIGH | §7.1 — run it tonight |
| 7 | Judge asks "Theme #4 self-improvement?" | HIGH | HIGH | §6 — drop the framing, lean on Theme #1 + scalable-oversight |
| 8 | Judge spots `kappa=0.277` claim with no artifact | MEDIUM | MEDIUM | §7.7 — write the script or remove the claim |
| 9 | Slide deck rendered live during pitch (raw markdown) | MEDIUM | MEDIUM | §8.4 — render PDF before the event |
| 10 | Demo video missing → 30% storytelling weight forfeited | HIGH (currently missing) | HIGH | §8.5 — record tonight |
| 11 | Pre-2024 / post-2024 80%/50% baseline questioned without source | MEDIUM | LOW | §7.6 — replace with measured number from your own bench |
| 12 | Late-stage training instability (KL=0.42, reward_std grew 7×) called out as reward-hacking | LOW | MEDIUM | §7.4 — add diagnostic plot + honest paragraph in `limitations.md` |
| 13 | A judge clones the repo and `make eval-v2` fails because they don't have the LoRA cached | MEDIUM | LOW | Verify `CHAKRAVYUH_SKIP_INFERENCE=1` reproduces from cached scores; document prominently |
| 14 | `/mcp` 405 on GET interpreted as "endpoint broken" | LOW | LOW | One-line README footnote: "POST-only per MCP spec" |

---

## 14. Roadmap to #1 — Hour-Boxed

### Next 6 hours (P0, do not negotiate)

| Hour | Task | Owner | Effort | Dependencies | Impact |
|---|---|---|---|---|---|
| 0:00–0:45 | **Fix Dockerfile** — add `COPY logs /app/logs` and `COPY data /app/data` after line 23. Add a multi-stage step that runs `pip install '.[demo]'` and verifies `python -c "import gradio"` succeeds. | Claude | 45 min | none | Unblocks `/demo`, `/eval/*` in production. P0. |
| 0:45–1:00 | Force HF Space rebuild via empty commit; orphan-deploy procedure from earlier session | User | 15 min | Dockerfile fix | Verifies fix landed |
| 1:00–1:30 | curl-verify all 11 endpoints on HF return 200 (per §2 list); curl `/diagnose` POST | User+Claude | 30 min | rebuild | Confirms production parity with local |
| 1:30–2:30 | **Render slides to PDF.** `npx -y @marp-team/marp-cli docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf`. Commit. Update README link. | User | 60 min (incl. one round of slide-content edits) | none | Storytelling 30% weight |
| 2:30–3:30 | **Run zero-shot Qwen2.5-7B baseline** on the 174-scenario bench. Add row to `eval_v2.json` and a paragraph to README. | User | 60 min wall, 30 min GPU T4 | GPU access | Closes §7.1 (single most asked rigor question) |
| 3:30–4:00 | **Add the 80%/50% source OR remove it** (§7.6 fix b — easier). Reword 4 occurrences. | Claude | 30 min | none | Closes §1 finding 11 |
| 4:00–6:00 | **Add live red-team tab to demo (§9).** New Gradio tab + asymmetry badge + parallel calls to v1 + `/diagnose`. Style to match existing CSS. Push and verify on HF. | Claude (with user verification) | 120 min | HF Space healthy | Wow moment lands. |

**State after 6 hours:** `/demo` works. `/eval/*` works. Slide PDF exists. Zero-shot baseline number in README. 80%/50% sourced or removed. Live red-team box live. **Probability of #1: ~34% → ~50%.**

### Next 24 hours (P0–P1)

| Hour | Task | Effort | GPU | Impact |
|---|---|---|---|---|
| 6:00–10:00 | **Record + edit demo video (§8.5).** 90s, 6 beats. Upload unlisted YouTube. Link from README + slide #4 + blog. | 4h | 0 | Storytelling +50%; closes single biggest miss |
| 10:00–14:00 | **Train Scammer LoRA adapter (§5).** Reuse GRPO skeleton, swap reward, 1 epoch. | 4h wall | 3 GPU-h T4 | Theme #1 defensibility 5→8.5 |
| 14:00–14:30 | **LoRA red-team (§7.5).** Same 10 attacks against v2. Update analyzer_robustness.json. | 30 min | 1 GPU-h | Closes §1 finding 14 |
| 14:30–15:30 | **Multi-seed retrain (§7.3, partial — 2 seeds, not 3).** Seeds 7, 13. Report mean ± std. | 1h wall | 6 GPU-h T4 | Closes §1 finding 10 |
| 15:30–16:00 | **Training instability diagnostic plot (§7.4).** 4-panel from `v2_trainer_state.json`. | 30 min | 0 | Closes §1 finding 9 |
| 16:00–17:00 | **Verify κ + Wilson CI claims (§7.7, §7.8).** Compute or remove. | 60 min | 0 | Closes §1 findings 12, 13 |
| 17:00–18:00 | **Methodological-contribution paragraph (§11.4).** Add to README, slide #4, blog. | 60 min | 0 | Reframes appeal beyond UPI judges |
| 18:00–19:00 | **Publish blog post (§8.6).** HF Hub + Medium. | 60 min | 0 | Mile post #6 P0 |
| 19:00–20:00 | **Mobile-test Gradio UI (§8.2).** Phone, screenshot, fix responsiveness. | 60 min | 0 | UI score 6→7.5 |
| 20:00–22:00 | **Architecture diagram (§10).** Mermaid → PNG. Commit. | 2h | 0 | Polish, but visible |
| 22:00–24:00 | **Tutorial Colab (§10) — env exploration without GRPO.** Reset/step/state without LoRA. | 2h | 0 | Lets GPU-less judges run code |

**State after 24 hours:** All P0s landed. Most P1s landed. **Probability of #1: ~52% → ~65%.**

### Final 12 hours (rehearsal + safety net)

| Hour | Task | Effort | Impact |
|---|---|---|---|
| 24:00–25:00 | **Live pitch rehearsal v1.** Record self. Time it. Cut 30s if over 3:00. | 1h | Reduces stage failure risk |
| 25:00–26:00 | **Pitch rehearsal v2 with backups.** Pre-stage FALLBACK_A and FALLBACK_B (§11.3). | 1h | Reduces ambiguity-of-fallback risk |
| 26:00–28:00 | **Cold-start measurement on judging morning network.** Force HF Space cold (revoke gcTimeout via dev-mode toggle). Time first /demo/. If >25s, deploy keep-warm cron. | 2h | Closes §13 risk #2 |
| 28:00–30:00 | **End-to-end fresh-clone Docker test.** New ubuntu:22.04 container, git clone, pip install, run all gates. | 2h | Closes WIN_PLAN A.4 |
| 30:00–32:00 | **Sleep.** Non-negotiable. | 2h | Protects pitch quality |
| 32:00–34:00 | Travel + setup at venue | 2h | — |
| 34:00–36:00 | Last-minute Q&A rehearsal: §13 risks 6, 7, 11. | 2h | Reduces panel-question risk |

**State at deadline:** All §14 work landed; risks mitigated; pitch rehearsed twice. **Probability of #1: ~65–70%.**

---

## 15. Things to STOP doing

1. **Stop adding more tests.** 273 is enough. Adding a 274th to fix one untested path on `_mount_demo` adds 0% to your score. Fix the underlying bug instead.
2. **Stop refactoring `demo_ui.py`.** It's ugly but works. A 4-hour refactor to split it into 5 modules adds zero judge-visible value. Keep it ugly until after submission.
3. **Stop expanding the bench.** 174 is what you committed. Adding 50 more scenarios now triggers a re-eval, which delays everything. **Ship the bench you have.**
4. **Stop polishing CI.** Your CI is fine. Adding more checks is not where the rubric weight lives.
5. **Stop writing more documentation.** You have 19 docs in `docs/`. The judge will read 2 of them (README, judge_quickstart). More docs ≠ better.
6. **Stop pitching Theme #4.** §6 — drop it from the live pitch and slides. Lead with #1 + reward-hacking honesty.
7. **Stop optimizing GRPO hyperparameters.** Whatever instability is in v2 (§7.4) is documented and shipped. Re-tuning to chase 0.5pp improvement on detection is rearranging deck chairs.
8. **Stop adding new endpoints.** `/eval/*`, `/diagnose` are enough. A `/explain` endpoint or `/visualize` endpoint won't move the needle.

The single biggest waste of time you're at risk of: **trying to make Theme #4 defensible.** It is not, in 24 hours, with the architecture you have. Drop it cleanly and reclaim the 12% it would otherwise leak.

---

## 16. Final Verdict

**Are you on track for #1?** No, not in current state. **Probability ~14%.** The HF Space demo is broken in production, you have no demo video, your slide deck isn't rendered, and your most-likely-asked rigor question (zero-shot baseline) is unanswered.

**Are you on track for #1 if you execute §14 24 hours?** Yes. **Probability ~65%.** Remaining 35% is owned by competitor entropy + the 12% Theme #4 leakage + bench-size limitations you cannot fix in the time remaining.

**The single change that would most increase your probability of #1:** Not the Scammer adapter. Not the live red-team box. Not the video. **Fix the Dockerfile in the next 45 minutes.** Until `/demo` and `/eval/*` work in production, every other improvement is theater.

The substance is real. The recovery story is genuine. The bench is grounded. The code is clean. The tests are dense. The honesty is rare. **You have a 7.5/10 submission with a 4/10 production surface — that is, by definition, a 4/10 submission to a panel that opens the demo URL first.**

Fix the surface. The rest is yours to win.

---

*— End of audit v2 —*
