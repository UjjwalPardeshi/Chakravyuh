# Latency & Memory Footprint — Pending (B.9)

> **Status:** measurements not yet run.
>
> This document is a **placeholder** for the B.9 milestone in
> [`WIN_PLAN.md`](../WIN_PLAN.md): per-harness latency and memory
> measurements for the Chakravyuh Analyzer LoRA across the three
> deployment paths documented in [`serving/README.md`](../serving/README.md).
> The harness scaffolding ships; the measurements depend on access to
> the target hardware (A10G for vLLM, Pixel 8 for Ollama) and have not
> been run for this submission.

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
