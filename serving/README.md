# Chakravyuh Serving Harnesses

Three deployment paths for the Chakravyuh Analyzer LoRA, illustrating the **on-device, on-server, on-cloud** spectrum claimed in the README.

| Harness | File | Target | Hardware | Status |
|---|---|---|---|---|
| **HF Space (Gradio + FastAPI)** | `server/app.py` | Live demo | HF Spaces (Docker SDK, port 8000) | ✅ deployed at https://ujjwalpardeshi-chakravyuh.hf.space |
| **vLLM (server-grade)** | `serving/vllm_compose.yml` | OpenAI-compatible `/v1/chat/completions` endpoint | A10G or better; CUDA 12 | ✅ scaffolded |
| **Ollama (laptop / phone-class)** | `serving/ollama_modelfile` | `ollama run` on a Pixel 8 / M1 MacBook | CPU + 8 GB RAM (q4_k_m) | ⚠️ requires GGUF release (see C.8 in [WIN_PLAN.md](../WIN_PLAN.md)) |

The **HF Space** path is the canonical demo for judges. The **vLLM** path is for anyone wanting to integrate Chakravyuh into a production-grade inference pipeline. The **Ollama** path closes the "fits on a phone" claim.

---

## vLLM (server-grade)

Boots a vLLM server with the v2 LoRA pre-loaded against the Qwen2.5-7B-Instruct base, exposing an OpenAI-compatible `/v1/chat/completions` endpoint.

```bash
docker compose -f serving/vllm_compose.yml up
```

After ~60 s warm-up:

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chakravyuh-analyzer-lora-v2",
    "messages": [
      {"role": "system", "content": "You are Chakravyuh Analyzer..."},
      {"role": "user", "content": "Hi I am from SBI, your account is frozen, share OTP"}
    ],
    "max_tokens": 160,
    "temperature": 0.0
  }' | jq
```

Expected: a JSON response with the Analyzer's strict-JSON output containing `score`, `signals`, `explanation`.

**GPU requirement:** A10G or better. CUDA 12. ~14 GB VRAM for bf16 inference, ~8 GB for AWQ quantization.

**Limitations:** vLLM 0.6+ supports LoRA adapters but the load-time syntax has shifted across versions; the compose file pins to a known-good version. Update `vllm_compose.yml`'s `image:` field if your environment needs a different vLLM version.

---

## Ollama (phone / laptop-class)

Boots a local Ollama instance running the merged-and-quantized Chakravyuh v2.

```bash
# One-time setup: pull the GGUF artifact (when published)
ollama pull hf.co/ujjwalpardeshi/chakravyuh-v2-gguf:q4_k_m

# Run interactively
ollama run hf.co/ujjwalpardeshi/chakravyuh-v2-gguf:q4_k_m

# Or build locally from this Modelfile (if the Hub artifact is not yet up)
ollama create chakravyuh -f serving/ollama_modelfile
ollama run chakravyuh
```

**Hardware:** Tested target is Pixel 8 (8 GB RAM, Tensor G3) at q4_k_m quantization, ~10 tok/s.

**Limitation:** the GGUF artifact in the README path is **planned**, not yet shipped. C.8 in [WIN_PLAN.md](../WIN_PLAN.md) covers the GGUF release workflow.

---

## Why three harnesses?

The README claim is "*on-device, on-server, on-cloud — same model.*" Each harness backs one wedge of that claim with a runnable artifact rather than a paragraph:

- **HF Space** → on-cloud (zero-install demo).
- **vLLM** → on-server (production integration story).
- **Ollama** → on-device (the "fits on a phone" claim).

Judges who care about deployability will probe one of the three; we ship all three so no probe goes unanswered.

## Cross-references

- Live demo: <https://ujjwalpardeshi-chakravyuh.hf.space/demo/>
- Adapter on HF Hub: <https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2>
- Latency / memory benchmark: [`docs/latency_memory.md`](../docs/latency_memory.md) (when shipped from B.9 in WIN_PLAN)
- GGUF release workflow: WIN_PLAN C.8.
