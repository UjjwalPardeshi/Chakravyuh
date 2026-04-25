---
license: mit
language:
  - en
  - hi
  - ta
  - te
  - kn
  - bn
  - mr
base_model: Qwen/Qwen2.5-7B-Instruct
library_name: peft
pipeline_tag: text-generation
tags:
  - lora
  - peft
  - grpo
  - trl
  - unsloth
  - fraud-detection
  - upi
  - india
  - multi-agent
  - openenv
  - scalable-oversight
datasets:
  - ujjwalpardeshi/chakravyuh-bench-v0
metrics:
  - f1
  - precision
  - recall
model-index:
  - name: chakravyuh-analyzer-lora-v2
    results:
      - task:
          type: text-classification
          name: Indian UPI Fraud Detection (Chakravyuh bench-v0)
        dataset:
          name: chakravyuh-bench-v0
          type: custom
        metrics:
          - name: Detection (recall)
            type: recall
            value: 0.993
          - name: False Positive Rate
            type: fpr
            value: 0.067
          - name: Precision
            type: precision
            value: 0.986
          - name: F1
            type: f1
            value: 0.99
---

# Chakravyuh Analyzer — LoRA v2

LoRA adapter for **Qwen/Qwen2.5-7B-Instruct**, post-trained with TRL's GRPO on the [Chakravyuh](https://github.com/UjjwalPardeshi/Chakravyuh) multi-agent Indian UPI fraud-detection environment.

The Analyzer's job: read a multi-turn dialogue between a (scripted) Scammer and Victim and output a calibrated suspicion score plus a justified explanation, in real time, on the victim's device. This adapter is the **v2 of two** Chakravyuh trained adapters and is the **honest one** — see "v1 → v2 story" below.

## Quick numbers (full results in `logs/eval_v2.json` of the GitHub repo)

| Metric | v1 (reward-hacked) | **v2 (this adapter)** |
|---|---|---|
| Detection rate | 100.0% | **99.3%** |
| False positive rate | 36.0% | **6.7%** (5× better) |
| F1 | 0.96 | **0.99** |
| Bench size | 135 | 174 evaluated (175 total, 1 skipped) |

### Per-difficulty detection (scams only, n=144)

| Difficulty | n | Detection |
|---|---|---|
| Easy | 26 | 100% |
| Medium | 66 | 100% |
| Hard | 18 | 100% |
| Novel | 34 | 97% |

The dip on `novel` (post-2024 attack patterns) is the small honest crack that confirms the model is not collapsing to "always flag."

## v1 → v2 story (the reason this adapter exists)

v1 hit `detection=100% / FPR=36%` — a textbook **reward-hacking fingerprint**. The model had learned to flag *everything* and then defend the over-flagging with plausible-sounding reasoning. The reward components were:

- Detection (+1 correct / -0.5 wrong)
- False-positive penalty (−0.3) ← too light
- Format reward (+0.15) ← paid even when prediction was wrong
- Calibration (×0.3 for benign) ← too weak on benign side
- Explanation (×0.4)

After diagnosing the hack, three principled changes were applied for v2:

1. **FP penalty −0.3 → −0.8** — over-flagging is now expensive
2. **Format reward DENIED on benign-flagged-as-scam** — closes the "lazy over-flag" shortcut
3. **Benign calibration weight 0.3 → 0.5** — stronger gradient toward score ≤ 0.2 on benign

Plus the KL anchor was tightened (`β = 0.08 → 0.15`) so the model can't drift far from the base distribution under the new reward shape.

Result: detection barely moved (100% → 99%), but FPR dropped 5× (36% → 6.7%). That asymmetric improvement is the signature of the model actually learning the task instead of gaming the reward.

## Quick start

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

base_model_id = "Qwen/Qwen2.5-7B-Instruct"
adapter_id = "ujjwalpardeshi/chakravyuh-analyzer-lora-v2"

tokenizer = AutoTokenizer.from_pretrained(base_model_id)
base = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
model = PeftModel.from_pretrained(base, adapter_id)
model.eval()

system_prompt = (
    "You are Chakravyuh's Behavioral Analyzer, a fraud detection AI deployed "
    "on-device to monitor real-time chat for Indian UPI scam patterns. "
    "Output strict JSON with `score` in [0,1], `signals` from the taxonomy, "
    "and `explanation`."
)

user_prompt = (
    "Scammer messages:\n"
    "Urgent! Your bank account will be frozen. Share OTP to verify identity.\n\n"
    "Analyze these messages. Return strict JSON only."
)

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

with torch.no_grad():
    out = model.generate(
        **inputs,
        max_new_tokens=160,
        do_sample=False,
        temperature=0.0,
        pad_token_id=tokenizer.eos_token_id,
    )
response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print(response)
```

Expected output (JSON):

```json
{
  "score": 0.95,
  "signals": ["urgency", "info_request", "impersonation"],
  "explanation": "Asks for OTP with urgency pressure from a self-claimed bank agent; matches OTP-theft scam pattern."
}
```

## Training details

- **Base model:** Qwen/Qwen2.5-7B-Instruct (4-bit Unsloth quantization for training, bf16 inference)
- **LoRA rank:** 64
- **LoRA alpha:** 128
- **KL anchor (β):** 0.15
- **Training corpus:** 619 examples (456 scam + 204 benign templates, soft-leakage filtered against the test set; see `training/grpo_analyzer.py:_filter_soft_leakage`)
- **Algorithm:** GRPO via TRL
- **Steps:** 619 (1 full epoch over the corpus)
- **Reward function:** Composable 5-rubric system (detection, FP penalty, missed-scam penalty, calibration, explanation quality)
- **Hardware:** Single A100-80GB (Colab Pro+)

`trainer_state.json` (full training trajectory) is at [logs/v2_trainer_state.json](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/logs/v2_trainer_state.json) in the source repo.

## Limitations

1. **Small benign sample (n=30 evaluated, 1 of 31 in bench skipped due to empty text).** Wilson 95% CI on FPR is approximately [1.9%, 21.3%]. We stand behind the "5× FPR reduction vs v1" claim (statistically real) but not the precise "6.7%" figure as a tight estimate.
2. **Single-seed training.** Multi-seed retrains are deferred to v3.
3. **Bench is a proxy.** 175 curated scenarios do not span real-world Indian fraud diversity. Production performance will be lower.
4. **One epoch over 619 templates.** More data + more epochs are deferred to v3.
5. **English-dominant training.** Multi-language detection numbers (Tamil, Telugu, etc.) require per-language eval — not yet measured at the time of writing.

See [docs/RESPONSIBLE_USE.md](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/docs/RESPONSIBLE_USE.md) for intended use and dual-use considerations.

## Links

- **GitHub:** <https://github.com/UjjwalPardeshi/Chakravyuh>
- **OpenEnv Space (live env):** <https://huggingface.co/spaces/ujjwalpardeshi/chakravyuh>
- **Bench dataset:** <https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0> (release pending)
- **Hackathon:** Meta PyTorch OpenEnv Hackathon 2026, Bangalore

## Citation

```bibtex
@software{pardeshi2026chakravyuh,
  title  = {Chakravyuh: A Multi-Agent RL Environment for Indian UPI Fraud Detection},
  author = {Pardeshi, Ujjwal},
  year   = {2026},
  url    = {https://github.com/UjjwalPardeshi/Chakravyuh}
}
```

## License

MIT — see [LICENSE](https://github.com/UjjwalPardeshi/Chakravyuh/blob/main/LICENSE) in the source repo.
