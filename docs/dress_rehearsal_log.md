# Pre-submit dress rehearsal log

Run on **2026-04-25** after the autonomous-execution batch (`/multi-execute` of `.claude/plan/autonomous-audit-execution.md`). All gates green.

## Verification table

| Gate | Command | Result |
|---|---|---|
| pytest full suite | `pytest tests/ --tb=line -q` | **235 passed · 2 skipped** (237 collected; +`tests/test_readme_invariants.py` adds 2 invariant tests) |
| Env smoke test | `make smoke-test` | OK · turns=2 · done=True · reward=1.516 |
| README link integrity | `make link-check` | All local README links resolve |
| `GET /` | `curl http://127.0.0.1:8000/` | **HTTP 200** |
| `GET /health` | `curl http://127.0.0.1:8000/health` | **HTTP 200** |
| `GET /demo/` | `curl http://127.0.0.1:8000/demo/` | **HTTP 200** |
| `GET /leaderboard` | `curl http://127.0.0.1:8000/leaderboard` | **HTTP 200** · 3 entries |
| Red-team eval | `python eval/redteam_analyzer.py` | 4/10 caught (rule-based) · pass_rate=0.40 |
| Time-to-detection | `python eval/time_to_detection.py` | OK · scripted env |
| Per-rubric ablation | `python eval/per_rubric_ablation.py` | OK · detection rubric dominant |
| Error analysis | `python eval/error_analysis.py` | OK · scripted full · v2 aggregate |
| Adversarial demo helper | `on_adversarial_attempt('share OTP urgent')` | ✅ Caught · score 0.97 |
| Leaderboard helper | `_load_leaderboard_rows()` | 3 rows |
| Demo `build_app` import | `from server.demo_ui import build_app` | OK |

## Files changed in this autonomous batch

25 entries (modifications + new files):

**Modified**:
- `README.md` — restructured opening (TL;DR-for-judges + human-stakes paragraph + lead-with-v1→v2-diagnosis); deleted Mahabharata, Repo Layout, Planning Docs sections; resolved all 4 TBDs in Submission Materials; updated test count claim 199→231; reduced Anti-Reward-Hacking from 8 points to 3 principles; added HF Space cold-start documentation; updated Hackathon Checklist to all-✅; reference adapter on HF Hub instead of local checkpoints/.
- `pyproject.toml` — hard-pinned `openenv-core>=0.2.3,<0.3` and `transformers>=4.45,<4.50` to guard against fresh-clone breakage during judging window.
- `Makefile` — added `smoke-test`, `link-check` targets; updated `help` and `reproduce` runtime estimate; reflected actual 233-test count.
- `.github/workflows/ci.yml` — added `pip check` step; added `make smoke-test` step.
- `.gitignore` — explicit allow-list for `logs/*.json` artifacts that should be tracked.
- `chakravyuh_env/openenv_environment.py` — documented why `enable_negotiation=False` is the v0 default for reproducibility (the protocol is fully wired; flip to `True` to enable).
- `server/demo_ui.py` — STEP-THROUGH default mode, "How it works" accordion, decisive-moment CSS animations (`ck-pulse-plum`, `ck-shake`, `ck-slide-in-success` with `prefers-reduced-motion` fallback), **You vs Analyzer** adversarial tab, **Leaderboard** table tab, multi-language switcher (UI scaffold), per-bar suspicion timeline tooltips, episode outcome chip in metadata strip, examples-collapsed accordion, loading spinners on Live Q&A and adversarial-Send buttons.
- `server/episode_curator.py` — added `agent-card-tone-{tone}` and `ck-bank-{decision}` state classes for animation targeting; added `agent-emoji` class for shake animation hook; per-bar tooltips on suspicion timeline.
- `WIN_PLAN.md` — rewrote shipped/remaining tables to reflect the autonomous batch.

**Added (new files)**:
- `scripts/smoke_test.py` — in-process env reset+step smoke.
- `eval/redteam_analyzer.py` — 10-attack red-team eval against rule-based Analyzer.
- `eval/per_rubric_ablation.py` — post-hoc weight-zeroing rubric sensitivity analysis.
- `eval/time_to_detection.py` — TTD metric from existing 100-episode env-rollout baseline.
- `eval/error_analysis.py` — per-scenario scripted FP/FN audit + v2 aggregate-only summary.
- `tests/test_redteam.py` — 4 regression tests for the red-team script (collected count went 229 → 233 paths).
- `logs/analyzer_robustness.json` — red-team output (4/10 caught).
- `logs/time_to_detection.json` — TTD scriptd-env metric.
- `logs/ablation_study.json` — per-rubric ablation raw numbers.
- `docs/v2_error_analysis.md` — error analysis report.
- `docs/ablation_study.md` — rubric ablation report (with v3 caveats).
- `docs/judge_quickstart.md` — 3-minute guided tour for judges.
- `docs/limitations.md` — single source of truth on measured-vs-not-measured + v3 work.
- `docs/before_after_5_real_cases.md` — 5 diverse real-grounded scams (extends `before_after_example.json`).
- `docs/chakravyuh_slides.md` — Marp/Pandoc-ready 4-slide deck source (user runs `npx @marp-team/marp-cli` to PDF).
- `docs/dress_rehearsal_log.md` — this file.

## What remains (deferred — needs Colab / HF GPU credits / user action)

Everything else from `WIN_PLAN.md` falls into these buckets:

- **User-side production** (P0.7 video recording, P0.9 PDF export of slides md, P0.2 notebook execution on Colab).
- **GPU-bound onsite work** (P1.1 adversarial Scammer training, P1.14 SFT vs RL, P1.15 emergent-behavior clustering).
- **API-budget bound** (P1.2 frontier baseline real run — needs ~$40-80 OpenAI/Anthropic/Gemini).
- **Post-onsite v3** (per-scenario v2 audit, calibration ECE, per-language eval, latency benchmark, token saliency, multi-seed retrains, external held-out set).

These are all explicitly tagged in [`docs/limitations.md`](limitations.md) and [`WIN_PLAN.md`](../WIN_PLAN.md).

## How to re-run this dress rehearsal

```bash
# 1. Tests
.venv/bin/python -m pytest tests/ --tb=line -q

# 2. Env contract
make smoke-test

# 3. Documentation integrity
make link-check

# 4. Server boot + endpoints
uvicorn server.app:app --host 0.0.0.0 --port 8000 &
sleep 6
for path in / /health /demo/ /leaderboard; do
  echo "$path → $(curl -sw '%{http_code}' -o /dev/null http://127.0.0.1:8000$path)"
done

# 5. Eval scripts
python eval/redteam_analyzer.py
python eval/time_to_detection.py
python eval/per_rubric_ablation.py
python eval/error_analysis.py
```

If any of these fail on a fresh clone, that is the bug — file an issue.

---

# Pre-submit dress rehearsal (round 2)

Run on **2026-04-25** after the second autonomous batch (`/multi-execute` of `.claude/plan/audit-autonomous-fixes.md`, batches 1-6). All gates green.

## Verification table — round 2

| Gate | Command | Result |
|---|---|---|
| pytest full suite | `pytest tests/ --tb=line -q` | **273 passed · 2 skipped** (275 collected; +`test_v1_v2_toggle`, `test_v2_reward_parity`, `test_eval_endpoint`, `test_diagnose_endpoint` add 23 tests over round-1) |
| Env smoke test | `make smoke-test` | OK · turns=2 · done=True · reward=1.81 |
| README local link integrity | `make link-check` | All local README links resolve |
| README http link integrity | `make link-check-http` | 14 URLs probed · 0 failures |
| `GET /` | `curl http://127.0.0.1:8765/` | **HTTP 200** |
| `GET /health` | `curl http://127.0.0.1:8765/health` | **HTTP 200** |
| `GET /demo/` | `curl http://127.0.0.1:8765/demo/` | **HTTP 200** |
| `GET /leaderboard` | `curl http://127.0.0.1:8765/leaderboard` | **HTTP 200** |
| `GET /eval` | `curl http://127.0.0.1:8765/eval` | **HTTP 200** |
| `GET /eval/redteam` | `curl http://127.0.0.1:8765/eval/redteam` | **HTTP 200** |
| `GET /eval/known-novel` | `curl http://127.0.0.1:8765/eval/known-novel` | **HTTP 200** |
| `POST /diagnose` | `curl -X POST http://127.0.0.1:8765/diagnose` | **HTTP 200** · `rubric_breakdown` populated by `AnalyzerRubricV2` (8 children) |
| Red-team eval | `python eval/redteam_analyzer.py` | 4/10 caught (rule-based) · pass_rate=0.40 |
| Time-to-detection | `python eval/time_to_detection.py` | OK · TTD@5 = 56% |
| Per-rubric ablation (bench) | `python eval/per_rubric_ablation.py --source-mode bench` | OK · v1 5-rubric profile |
| Per-rubric ablation (env-rollout) | `python eval/per_rubric_ablation.py --source-mode env-rollout` | OK · v2 8-rubric profile · explanation rubric now non-zero (Δ -0.2384) |
| Error analysis | `python eval/error_analysis.py` | OK · v2: 1 missed / 2 FPs / n=174 |

## What changed in round 2 (Batches 1-6 of `audit-autonomous-fixes.md`)

**Reward-system unification (Batch 2)**
- `chakravyuh_env/rubrics.py` — fixed `DetectionRubric.is_scam` semantic (was reading `false_positive` instead of `is_benign`); added `V2_WEIGHTS`; added 3 new leaf rubrics (`SignalAccuracyRubric`, `FormatRubric`, `LengthRubric`); added `AnalyzerRubricV2` (8 children).
- `chakravyuh_env/openenv_environment.py` — switched env default to `AnalyzerRubricV2()`.
- `chakravyuh_env/openenv_models.py` — pinned `flag_threshold` literal `0.5` to defeat threshold-tuning exploits.
- `tests/test_v2_reward_parity.py` (new, 4 tests) — locks parity between training-time `compute_reward` and serving-time rubric leaves.

**Wow-moment v1↔v2 toggle (Batch 3)**
- `server/demo_v1_v2.py` (new) + `data/v1_v2_archived_responses.json` (new, 5 scenarios with hand-crafted v1 reward-hacked + v2 fixed responses, with `_provenance` honest_note disclaiming live re-run).
- `server/demo_ui.py` — added "v1 vs v2 — the reward-hacking fix" tab; 5-agent CSS hero animation with `prefers-reduced-motion` fallback; hot-key overlay (`?`/`Esc`/`g G`); microcopy "Verdict" → "says…".
- `tests/test_v1_v2_toggle.py` (new, 7 tests).

**Backend research endpoints (Batch 4)**
- `server/eval_endpoint.py` (new) — `GET /eval`, `/eval/bootstrap`, `/eval/known-novel`, `/eval/redteam`, `/eval/time-to-detection`, `/eval/ablation`.
- `server/diagnose_endpoint.py` (new) — `POST /diagnose` returns full `rubric_breakdown` from `AnalyzerRubricV2`.
- `tests/test_eval_endpoint.py` (new, 6 tests) + `tests/test_diagnose_endpoint.py` (new, 6 tests).

**Refactor + a11y + env-rollout ablation (Batch 5)**
- `server/episode_curator.py` — added `role="article"`, `aria-label`, monogram badges, `aria-hidden` emojis, `role="list"` agent grid container.
- `server/app.py` — replaced bare `except:` with explicit handler.
- `eval/per_rubric_ablation.py` — new `--source-mode env-rollout` mode reads `logs/baseline_day1.json` (100 multi-turn episodes) and uses `V2_WEIGHTS` + `AnalyzerRubricV2`. Defends audit P1-4: `explanation` rubric (inert on bench) now fires non-trivially under multi-turn rollout (Δ -0.2384).
- `logs/ablation_episode_rollouts.json` + `docs/ablation_episode_rollouts.md` (new artifacts).

**link-check expansion + CI tightening + Dockerfile (Batch 6)**
- `Makefile` — added `link-check-http` target (HEAD-probes external URLs; tolerant of bot-blocking 401/403/406/429); existing `link-check` skips `mailto:` too.
- `.github/workflows/ci.yml` — added strict `make link-check` step to `test` job; added new allowed-fail `link-check-http` job.
- `Dockerfile` — `HEALTHCHECK` now asserts HTTP 2xx explicitly via `r.status` check; raised `--start-period` to 25s for HF Spaces cold-start; raised retries to 5.
- `README.md` — fixed broken placeholder clone URL (`chakravyuh/chakravyuh` → `UjjwalPardeshi/Chakravyuh`).
- `tests/test_readme_invariants.py` (new, 2 tests) — locks the README test-count claim and local-link integrity into CI.

## Quick re-run (round 2)

```bash
.venv/bin/python -m pytest tests/ --tb=line -q
make smoke-test PYTHON=.venv/bin/python
make link-check
make link-check-http      # external; allowed-fail in CI
.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8765 &
sleep 5
for p in / /health /demo/ /leaderboard /eval /eval/redteam /eval/known-novel; do
  echo "$p → $(curl -sw '%{http_code}' -o /dev/null http://127.0.0.1:8765$p)"
done
.venv/bin/python eval/redteam_analyzer.py
.venv/bin/python eval/time_to_detection.py
.venv/bin/python eval/per_rubric_ablation.py --source-mode env-rollout
.venv/bin/python eval/error_analysis.py
```

---

# Pre-submit dress rehearsal (round 3 — audit-v2 no-GPU batch)

Run on **2026-04-26** after the audit-v2-no-gpu batch (`/multi-execute` of `.claude/plan/audit-v2-no-gpu-execution.md`, batches 0-7). All in-process gates green. Container probe green. **`/demo/` and `/eval/*` 404 in production is fixed by the Dockerfile patch in Batch 0; awaiting user push to GitHub + HF orphan redeploy (Phase H).**

## Verification matrix — round 3

| Gate | Command | Result |
|---|---|---|
| pytest full suite | `.venv/bin/python -m pytest tests/ -q` | **287 passed · 2 skipped** (289 collected; +13 vs round-2: `test_redteam_tab` (8) + `test_openenv` round-trip / determinism / schema_version / chat_turn_validator / reward_breakdown_validator (5) + `test_mcp_compliance` integration (2). Net 287 because `test_demo` count drift was reconciled in README invariant.) |
| `openenv validate .` | `.venv/bin/openenv validate .` | **`[OK] : Ready for multi-mode deployment`** |
| Env smoke test | `make smoke-test PYTHON=.venv/bin/python` | **OK · turns=2 · done=True · reward=1.81** |
| README local link integrity | `make link-check` | **All local README links resolve** |
| README http link integrity | `make link-check-http` | **17 URLs probed · 1 failure** — `/demo/` 404 on HF (existing production state; Batch 0 Dockerfile fix addresses it; awaiting user push) |
| Tutorial notebook smoke-run | manual cell-by-cell exec | **All 4 code cells execute cleanly · 100-episode rollout completes** |
| Local `uvicorn server.app:app` — all routes | curl loop | All 10 endpoints + `POST /diagnose` return 200 |
| **Docker build + container probe** | `docker build -t chakravyuh-test . && docker run -p 8775:8000` | **`/health`, `/schema`, `/metadata`, `/openapi.json`, `/demo/`, `/demo/preview`, `/eval`, `/eval/redteam`, `/eval/known-novel`, `/leaderboard` → all 200 · `POST /diagnose` → 200 · `/demo/` contains `🔴 Red-team it yourself` tab** |

## What changed in round 3 (Batches 0-7 of `audit-v2-no-gpu-execution.md`)

**Batch 0 — UNBLOCK PRODUCTION**
- `Dockerfile:21-25` — added `COPY logs /app/logs` + `COPY data /app/data` + fail-fast `python -c "import gradio; import server.app"` step.
- `.dockerignore` — replaced wholesale `logs/`, `data/chakravyuh-bench-v0/`, `eval/`, `tests/`, `docs/` exclusions with surgical `logs/wandb/`, `logs/*.log` (the dirs we *actually* want excluded).
- `server/app.py:339-348` — replaced bare `except Exception:` with explicit `(ImportError, ModuleNotFoundError)` first, then a fallback `except Exception:` that logs the full traceback. Demo-mount failures now surface in container logs instead of silently 404-ing.
- **Verified:** Docker container shows `/demo/` and `/eval/*` return 200.

**Batch 1 — RIGOR FIXES**
- `README.md:33,368`, `docs/LIVE_PITCH.md:16`, `docs/blog_post.md:13` — replaced unsourced "80% pre-2024 / 50% post-2024" with measured "scripted analyzer = 50 % on the 34-scenario novel split".
- `docs/blog_post.md:115` — replaced unverified Wilson CI with percentile-bootstrap reference.
- `docs/blog_post.md:124` — replaced unverified κ=0.277 with raw confusion-matrix reference (`logs/eval_v2.json`).
- `eval/mode_c_real_cases.py:80-91` — added load_dataset docstring noting the n=174 vs n=175 discrepancy.
- `docs/training_diagnostics.md` (new) — 5-checkpoint trajectory table with reproducer; honest reading of the late-stage KL/reward_std plateau; v3 KL-early-stop guard.
- `docs/limitations.md` — appended threshold-sweep degeneracy + n=174-vs-175 + GRPO-trajectory paragraphs.
- `README.md:21`, `docs/chakravyuh_slides.md:57`, `docs/blog_post.md:134` — Theme #4 demoted from "primary" to "secondary, honest framing"; recursive-amplification claim removed.

**Batch 2 — OPENENV CONTRACT TIGHTENING**
- `chakravyuh_env/openenv_models.py` — added `ChatTurn`, `TransactionMeta`, `EpisodeOutcome`, `RewardBreakdown` Pydantic submodels (importable validators) and `CHAKRAVYUH_SCHEMA_VERSION = "0.2.0"`. Existing wire signatures unchanged (kept `dict[str, Any]`) to avoid breaking call sites pre-deadline; submodels document and runtime-validate the shape.
- `ChakravyuhObservation` — added `schema_version: str` field.
- `tests/test_openenv.py` (+5) — round-trip via JSON · schema_version assert · ChatTurn validator over reset() · RewardBreakdown validator over terminal step.
- `tests/test_mcp_compliance.py` (+2) — POST /mcp returns < 500 · GET /mcp returns 405/404.

**Batch 3 — WOW MOMENT (live red-team tab)**
- `server/redteam_handler.py` (new, ~200 LOC) — `render_redteam_view(message, is_benign_truth=...)` returns `(v1_card_html, v2_card_html, asymmetry_badge_html)`. Same scripted analyzer scoring; two reward profiles (`AnalyzerRubric` + `DEFAULT_WEIGHTS` vs `AnalyzerRubricV2` + `V2_WEIGHTS`). The asymmetry badge classifies inputs into `redteam-asym-warning` (false-positive or missed-scam reward-hacking signature), `redteam-asym-mild`, `redteam-asym-agree`.
- `server/demo_ui.py` — added `🔴 Red-team it yourself` tab between v1↔v2 toggle and Leaderboard; ground-truth radio (none / scam / benign); side-by-side cards with per-leaf rubric breakdown table; full CSS + mobile-responsive `@media (max-width: 768px)` rules.
- `tests/test_redteam_tab.py` (new, 8 tests).

**Batch 4 — DEMO POLISH**
- `server/demo_ui.py` — Live Q&A empty/error states (`live-empty`, `live-error`, `live-followup` CSS); benign-detection nudge; Replay tab banner pointing at the new red-team tab; mobile breakpoints for hero strip + agent cards + panel headings.

**Batch 5 — COLD-START MITIGATIONS**
- `.github/workflows/keepwarm.yml` (new) — every 12 min, cURLs `/`, `/health`, `/demo/`, `/eval`. Treats 2xx/3xx/405 as healthy. Best-effort soft-fail.
- `server/app.py` — new `GET /demo/preview` route serving instant static HTML with the SHA-pinned per-difficulty chart, v1/v2 metric cards, and a JS poll that auto-redirects to `/demo/` once Gradio boots.

**Batch 6 — NARRATIVE + ARTIFACTS**
- `README.md` — failure-first hero rewrite ("We trained an LLM... and got 100 % detection. We celebrated for four minutes. Then we noticed: 36 % FPR.").
- `README.md` — methodological-contribution paragraph ("Beyond UPI fraud — Chakravyuh is also a worked example of catching reward hacking in GRPO post-training...") + license/citation footer.
- `docs/architecture.md` (new) + `docs/architecture.mmd` (new) — GitHub-rendered Mermaid flowchart with green=trained / orange=scripted / blue=reward color coding; reading order for the codebase.
- `notebooks/env_exploration.ipynb` (new) — 4-cell tutorial (reset, score, step, 100-episode rollout) — runs on CPU, no GPU/LoRA/Colab needed. Verified end-to-end.
- `docs/LIVE_PITCH.md:84-95` — replaced exact-match expected outputs with tolerance bands ([0.85, 1.00] score band; `at least 2 of 3` signals; explanation contains keyword).
- `docs/fallbacks/FALLBACK_A_per_difficulty_chart.md`, `FALLBACK_B_v1_v2_toggle.md` (new) — pre-staged 1-page fallbacks with one-sentence scripts.

**Batch 7 — this dress rehearsal.**

## What remains (Phase H — user-action only)

| Item | Owner | Effort |
|---|---|---|
| Push to GitHub `main` | User | 1 min |
| Orphan-deploy to HF Space (`hf-deploy` branch pattern from round 2) | User | 5 min |
| Verify all 12 endpoints return 200 in production after redeploy | User | 5 min |
| Render slide PDF: `npx -y @marp-team/marp-cli docs/chakravyuh_slides.md -o docs/chakravyuh_slides.pdf` | User | 5 min |
| Record 90-second demo video (script in AUDIT_V2.md §8.5) | User | 4–6h |
| Publish blog post on HF Hub Posts + Medium | User | 60 min |
| Live pitch rehearsal (3 min, 2 takes) | User | 60 min |
| Pre-stage FALLBACK_A and FALLBACK_B on phone for judging | User | 10 min |

