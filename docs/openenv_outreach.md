# OpenEnv Reference-Example Outreach

**Status:** draft prepared 2026-04-26. Not yet sent. The "send" action is a user task.

---

## Purpose

Offer Chakravyuh as a documented multi-agent reference example in the upstream `meta-pytorch/OpenEnv` repository. Pairs naturally with the upstream PR opportunity in WIN_PLAN C.4 (any papercut found while building).

## Recommended target

**Primary:** OpenEnv maintainers (engineering org at Meta PyTorch). Channel: GitHub issue on `meta-pytorch/OpenEnv` first (public, indexable), then a follow-up email if no response in 7 days.

**Secondary:** OpenEnv Discord `#show-and-tell` thread.

## Draft GitHub issue body (for `meta-pytorch/OpenEnv`)

> **Title:** Reference-example offer: multi-agent fraud-detection environment (Chakravyuh)
>
> Hi OpenEnv team,
>
> We built a 5-agent OpenEnv-compliant environment for Indian UPI fraud detection (https://github.com/UjjwalPardeshi/Chakravyuh) and would like to offer it as a documented multi-agent reference example in the OpenEnv docs.
>
> **What it demonstrates** beyond the existing single-agent quickstart:
>
> 1. **Multi-agent dynamics with asymmetric information** — Analyzer sees only chat, Bank Monitor sees only transaction metadata, Regulator sees only aggregates. Maps cleanly to scalable-oversight literature.
> 2. **Composable rubric rewards** — `chakravyuh_env/rubrics.py` shows an `AnalyzerRubricV2` with 8 child rubrics composed via the standard OpenEnv reward interface.
> 3. **Adversarial co-evolution** — Phase 1 Scammer LoRA trained via TRL 0.14 GRPO with reward `1 - ScriptedAnalyzer.score`. Demonstrates the pattern of training one agent against a frozen opponent within a single OpenEnv environment.
> 4. **`/eval/*` and `POST /diagnose` endpoints** — extends the standard OpenEnv server with custom research endpoints while keeping `/mcp`, `/health`, and `/openapi.json` strictly compliant.
> 5. **Pydantic submodel pattern** — `chakravyuh_env/openenv_models.py` shows how to expose nested observation / action types in a way that round-trips cleanly through MCP JSON-RPC.
>
> The environment passes `openenv validate .` cleanly (both filesystem and live HF Space modes), schema_version is `0.2.0`, and the live deployment at https://ujjwalpardeshi-chakravyuh.hf.space has been up for the past two weeks with a keepwarm cron.
>
> **Concrete offer:** we're happy to submit a docs PR adding Chakravyuh to the multi-agent examples list, with whatever framing the OpenEnv docs prefer (one-paragraph callout, full reference-example chapter, or simply a link from the existing examples page). Happy to also publish a stripped-down "minimal multi-agent" reference based on the same structure if that's more useful than a full domain-specific environment.
>
> If you'd rather we just open a PR directly, let us know and we'll match your existing reference-example template.
>
> Thanks,
> Ujjwal Pardeshi (and the Chakravyuh team)

## Draft email (for follow-up if no GitHub response after 7 days)

> **Subject:** Chakravyuh — multi-agent OpenEnv reference example (offer)
>
> Hi OpenEnv team,
>
> Following up on the GitHub issue we filed at <issue link> on <date>. We're offering Chakravyuh — a 5-agent OpenEnv-compliant environment for Indian UPI fraud detection — as a documented reference example in the OpenEnv docs.
>
> Quick links:
> - Repo: https://github.com/UjjwalPardeshi/Chakravyuh
> - Live HF Space: https://ujjwalpardeshi-chakravyuh.hf.space
> - 5-step reproducibility doc: https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/REPRODUCE.md
>
> Three things that distinguish this from the existing quickstart: composable-rubric rewards, asymmetric-information multi-agent dynamics, and an adversarial co-evolution loop (B.2 in our backlog).
>
> Happy to open a docs PR directly against `meta-pytorch/OpenEnv` if that's the cleanest path.
>
> Thanks,
> Ujjwal Pardeshi
> ujjwal.pardeshi@riamona.com

## Tracking

- [ ] GitHub issue filed at `meta-pytorch/OpenEnv` — link: ___
- [ ] Date filed: ___
- [ ] Response received Y/N: ___
- [ ] If no response by ___ (7 days post-file), send follow-up email
- [ ] Follow-up email sent: ___
- [ ] Outcome: ___

## What success looks like

In rough order of value:

1. OpenEnv maintainers accept a docs PR linking Chakravyuh from their multi-agent examples list. — *highest leverage*
2. OpenEnv maintainers acknowledge but don't merge before submission deadline. Chakravyuh README cites the offer as a community-engagement signal.
3. No response. Treated as ecosystem-engagement effort regardless; the public GitHub issue is itself the artifact.

## Operating principle

Per the WIN_PLAN: *"Even an unmerged docs PR is framework-mastery credibility."* The file itself goes in the repo as evidence of the effort, regardless of outcome.
