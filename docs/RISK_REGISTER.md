# Chakravyuh Risk Register

**Last updated:** 2026-04-25

This register lists known failure modes that could affect the hackathon
submission and the planned mitigation for each. It is the canonical place
to consult when something breaks during execution.

| # | Risk | Probability | Impact | Mitigation / Plan B |
|---|---|---|---|---|
| 1 | HF Space deploy fails (Docker build error, dependency resolution, image size limit) | Medium | Blocking | Run the environment locally with `uvicorn server.app:app` and tunnel via `cloudflared`/`ngrok` for the live demo; keep the GitHub repo URL in the submission as a fallback. Adapter weights live on HF Hub model repo (separate from Space) so size limits affect only the Space build. |
| 2 | Adversarial Scammer training (P1.1) does not converge inside the 5-hour onsite budget (reward stuck, output degenerate, OOM at rank=64) | Medium | High | Fall back to "scripted Scammer with SFT generation head" — supervised fine-tune of Qwen2.5-0.5B on `scammer_templates.json` only, no RL. Frame the result honestly in the writeup as "in 2h, full RL did not converge; SFT-fine-tuned generation head released; full-RL Scammer is v3 work." |
| 3 | Frontier API quota exhausted mid-eval (OpenAI / Anthropic / Google) | Low | Medium | Document partial results honestly. Even a single-model comparison (e.g., GPT-4o only) still beats "no comparison." Do not extrapolate from the partial data to claim coverage you did not measure. |
| 4 | Colab or HF compute disconnects mid-training | High | Medium | All training jobs use `--save-steps` to checkpoint every ~35 steps and `--resume` to continue from the latest checkpoint. The v2 run already validated this path (auto-recovered from a network drop at step 619). |
| 5 | Live demo breaks on stage (network down at venue, model OOM, tokenizer mismatch) | Medium | High | Pre-record a 30-second backup demo video locally before onsite; play it as a fallback slide if the live demo fails. Judges accept canned demos so long as they are clearly labelled. |
| 6 | Bench results in `logs/eval_v2.json` do not match README claims after a re-run | Low | Critical | Operating Principle #1 binds: **update the README to match the artifact, never the other way around.** A lower-but-honest number always beats an unverifiable one. |
| 7 | Git LFS quota exceeded by adapter weights (~646 MB) | Low | Medium | Adapter is hosted on HF Hub model repo (`<user>/chakravyuh-analyzer-lora-v2`), not in the GitHub repo or HF Space repo. The repo only references the HF Hub URL. |
| 8 | API keys leaked during a screen-share or push | Low | Critical | All keys live in `.env` (gitignored). Pre-submission audit grep: `git log -p --all -- '*.py' '*.md' '*.json' \| grep -iE "sk-\|api_key\|bearer"`. If any leak, **rotate immediately** — do not delete the commit and pretend it didn't happen. |
| 9 | SFT controlled baseline (P1.14) beats RL on the novel split | Medium | Medium | Pivot framing: *"On a 619-example training corpus and our compute budget, SFT alone closes most of the novel-detection gap. Chakravyuh's distinctive value is the **environment + bench**, not the training algorithm — anyone can plug in their preferred trainer. Multi-seed and longer-training tests are v3 work."* |
| 10 | NPCI / RBI / bank outreach (P2.12) gets no response within hackathon timeline | High | Low | Drop the "institutional engagement" narrative entirely — do **not** quote unsent or unconfirmed correspondence. Fall back to citing public RBI / NPCI / I4C advisories that informed the bench scenario design. |
| 11 | HF Space build pulls a dependency that breaks `openenv validate` | Low | High | Pin every dependency in `pyproject.toml` to a known-working version. Test the build locally with `docker build .` before pushing the Space update. |
| 12 | Scammer adapter (if released per P3.6) is misused for actual scam generation | Low | Critical | Release path is gated behind HF Hub gated-access flag with mandatory acceptance of `docs/RESPONSIBLE_USE.md`. If misuse is reported, the gate is revoked immediately. |
| 13 | Reproducibility check (`make reproduce`) produces numbers >0.5pp off README claims | Medium | Medium | Document the discrepancy in `docs/PHASE_C_OUTCOMES.md`. Either tighten the eval seed (most likely cause: non-deterministic generation in the LoRA forward pass) or update README numbers. Operating Principle #1 wins ties. |
| 14 | Pre-submit dress rehearsal on a fresh Docker container reveals a missing dependency or path issue | High | Medium | This is the **point** of the dress rehearsal. Fix every break, then re-run. Allocate at least 2 hours to the dress rehearsal for this reason. |

## How to use this register

- When something breaks, find the matching row first; do not invent a new mitigation.
- When a new risk is discovered during execution, add a row.
- When a risk is retired (e.g., HF Space is live), strike through the row but keep it for audit.
- This file is gitignored from no path; commit updates as part of normal `chore:` commits.
