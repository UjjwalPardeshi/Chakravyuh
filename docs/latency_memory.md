# Latency & Memory Footprint — Partial (B.9)

> **Status:** **HF Space measurements shipped 2026-04-26** — see §HF Space results below + [`logs/latency_memory_hf_space.json`](../logs/latency_memory_hf_space.json). vLLM and Ollama measurements still depend on target hardware (A10G / Pixel 8) and remain unmeasured for this submission; that part of B.9 stays open.

## HF Space results (measured 2026-04-26, n=10 sequential trials per endpoint)

Source of truth: [`logs/latency_memory_hf_space.json`](../logs/latency_memory_hf_space.json).

| Endpoint | p50 wall-clock | p95 wall-clock | Min | Max | Std-dev |
|---|---|---|---|---|---|
| `GET /health` | **1.21 s** | **1.45 s** | 1.08 s | 1.50 s | ±0.15 s |
| `POST /diagnose` (scripted analyzer) | **1.19 s** | **1.32 s** | 0.96 s | 1.49 s | ±0.16 s |

Single-probe latencies for the rest:

| Endpoint | HTTP | Wall-clock |
|---|---|---|
| `/health` | 200 | 1.27 s |
| `/metadata` | 200 | 1.26 s |
| `/openapi.json` | 200 | 1.76 s |
| `/schema` | 200 | 1.61 s |
| `/eval/redteam` | 200 | 1.25 s |
| `/demo/preview` | 200 | 0.98 s |

**What these numbers include.** Wall-clock from `curl --max-time 30` measured on a laptop in Pune; HF Space is in EU/US per HF default routing. **~700 ms of every measurement is network RTT + TLS handshake**, not server compute. For server-side compute alone (no network), run the Docker container locally per [`serving/README.md`](../serving/README.md).

**Cold start.** First `GET /health` after an idle period was 1.328 s when probed (the keepwarm cron had hit recently, so the Space was warm). The canonical cold-start number is the prior 2.69 s dress-rehearsal measurement quoted in `serving/README.md`; the keepwarm cron at `.github/workflows/keepwarm.yml` ensures judges rarely hit a cold container.

**Acceptance.** All endpoints return 200 well under the 20 s OpenEnv cold-start ceiling. The `POST /diagnose` p95 of 1.32 s is the relevant interactive-latency number for the live red-team tab.

---

## What's still NOT measured (vLLM + Ollama)

This document is **partial** for the B.9 milestone in
[`WIN_PLAN.md`](../WIN_PLAN.md): per-harness latency and memory
measurements for the Chakravyuh Analyzer LoRA across the three
deployment paths documented in [`serving/README.md`](../serving/README.md).
The harness scaffolding ships; the **vLLM (A10G) and Ollama (Pixel 8 / M1)** measurements depend on target hardware and have not yet been run for this submission.

## Methodology (when run)

For each harness — HF Space (Gradio + FastAPI), vLLM, Ollama — measure:

| Metric | Definition | Tool |
|---|---|---|
| **Cold start** | Time from process spawn to first `/health` 200 | `curl -w "%{time_total}"` |
| **Warm latency p50 / p95** | Per-request, 100 inputs from `data/chakravyuh-bench-v0/scenarios.jsonl` | `wrk` or `hey` |
| **Throughput** | Requests / sec at concurrency=1, 8, 32 | `wrk -t1 -c{1,8,32}` |
| **Peak RSS** | Process resident memory at peak | `/usr/bin/time -v` |
| **GPU VRAM** | Peak allocation during inference | `nvidia-smi --query-gpu=memory.used` |

Each harness gets a row; results published as
`logs/latency_memory_{harness}.json` and surfaced in this document.

## What we already know (qualitatively)

- **HF Space cold start:** measured **2.69 s** for `/demo/` (see
  [`AUDIT.md`](../AUDIT.md) §2 cold-start table). Well under the 20 s
  limit. Other endpoints all 200 in 1.32 – 1.61 s.
- **vLLM:** target hardware A10G; `vllm_compose.yml` pins to a
  known-good version. Not yet benchmarked end-to-end.
- **Ollama:** target hardware Pixel 8 / M1 MacBook at q4_k_m
  quantization. Estimated ~10 tok/s based on Qwen2.5-0.5B and
  Qwen2.5-7B-q4 reference numbers; **not measured for the v2 LoRA
  specifically** (the LoRA needs to be merged-and-quantized to GGUF
  first — see C.8 in [`WIN_PLAN.md`](../WIN_PLAN.md)).

## Why this is published as a stub

Per Operating Principle #1 in
[`WIN_PLAN.md`](../WIN_PLAN.md): **no fabricated numbers**. The
[serving README](../serving/README.md) cross-references this document
because the measurement *should* live here; rather than silently
linking to a non-existent file, we publish the placeholder so the gap
is named. Honest stub > confident fiction.

When the measurements run, this file will be replaced with a results
table; until then, this notice is the artifact.
