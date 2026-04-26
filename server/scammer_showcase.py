"""Scammer LoRA Showcase — render the trained adversary's story for the demo UI.

Reads pre-computed artifacts:
  - logs/scammer_frontier_comparison.json  (frontier LLMs as scammers)
  - logs/scammer_significance.json         (OOD parity + best-of-8 lift)
  - logs/b2_phase1_scammer_vs_v2_lora.json (co-evolution gap)

Zero model dependencies — all data is pre-computed.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_LOGS = Path(__file__).resolve().parent.parent / "logs"


@lru_cache(maxsize=1)
def _load_frontier() -> dict | None:
    p = _LOGS / "scammer_frontier_comparison.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_significance() -> dict | None:
    p = _LOGS / "scammer_significance.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_coevolution() -> dict | None:
    p = _LOGS / "b2_phase1_scammer_vs_v2_lora.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def render_scammer_hero() -> str:
    sig = _load_significance()
    bo8 = "93.75 %"
    held_out = "100 %"
    if sig:
        meta = sig.get("scammer_lora_meta", {})
        bo8_val = meta.get("best_of_8_bypass", 0.9375)
        held_out_val = meta.get("held_out_best_of_8_bypass", 1.0)
        bo8 = f"{bo8_val * 100:.2f} %"
        held_out = f"{held_out_val * 100:.0f} %"

    return f"""
<div style="background:#381932;color:#fff;border-radius:12px;padding:24px 28px;margin:0 0 18px;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
    <span style="font-size:28px;">🎭</span>
    <div>
      <div style="font-size:18px;font-weight:800;letter-spacing:-0.3px;">
        Trained Scammer LoRA — Qwen2.5-0.5B + GRPO
      </div>
      <div style="font-size:13px;color:rgba(255,255,255,0.65);margin-top:2px;">
        LoRA r=16 · 200 GRPO episodes · reward = 1 − ScriptedAnalyzer.score
      </div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;">
    <div style="background:rgba(255,255,255,0.12);border-radius:8px;padding:14px 16px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
                  color:rgba(255,255,255,0.55);margin-bottom:4px;">Best-of-8 bypass</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;
                  color:#e8c97a;">{bo8}</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.50);margin-top:2px;">
        vs scripted defense (n=64)</div>
    </div>
    <div style="background:rgba(255,255,255,0.12);border-radius:8px;padding:14px 16px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
                  color:rgba(255,255,255,0.55);margin-bottom:4px;">Held-out novel</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;
                  color:#e8c97a;">{held_out}</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.50);margin-top:2px;">
        32/32 on unseen categories</div>
    </div>
    <div style="background:rgba(255,255,255,0.12);border-radius:8px;padding:14px 16px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
                  color:rgba(255,255,255,0.55);margin-bottom:4px;">Parameters</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;
                  color:#e8c97a;">0.5B</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.50);margin-top:2px;">
        beats 671B DeepSeek-V3 at evasion</div>
    </div>
    <div style="background:rgba(255,255,255,0.12);border-radius:8px;padding:14px 16px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
                  color:rgba(255,255,255,0.55);margin-bottom:4px;">Co-evolution gap</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;
                  color:#e8c97a;">60 pp</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.50);margin-top:2px;">
        93.75 % vs scripted → 32.8 % vs v2 LoRA</div>
    </div>
  </div>
</div>
"""


def render_frontier_table() -> str:
    """Render the frontier-LLMs-as-scammer comparison table."""
    data = _load_frontier()
    if not data:
        return '<div style="color:#b71c1c;padding:12px;">Frontier scammer data not loaded.</div>'

    trained_ref = data.get("trained_scammer_reference", {})
    bo8 = trained_ref.get("scammer_lora_phase1_best_of_8", {})
    ss = trained_ref.get("scammer_lora_phase1_single_shot", {})
    frontier = data.get("frontier_results", [])

    rows_data = []

    rows_data.append({
        "name": "Chakravyuh Scammer LoRA (best-of-8)",
        "params": "0.5B + LoRA r=16",
        "bypass": bo8.get("bypass_rate", 0.9375),
        "ci": bo8.get("wilson_95ci", [0.85, 0.975]),
        "held_out": bo8.get("held_out_rate", 1.0),
        "highlight": True,
        "caveat": False,
    })

    for f in sorted(frontier, key=lambda x: -x.get("bypass_rate", 0)):
        model_id = f.get("model_id", "")
        short = model_id.split("/")[-1] if "/" in model_id else model_id
        params = _model_params(short)
        is_safety_refusal = "gpt-oss" in short.lower()
        display_name = f"{short} (untrained)"
        if is_safety_refusal:
            display_name += " *"
        rows_data.append({
            "name": display_name,
            "params": params,
            "bypass": f.get("bypass_rate", 0),
            "ci": f.get("wilson_95ci", [0, 0]),
            "held_out": f.get("held_out", {}).get("rate", 0),
            "highlight": False,
            "caveat": is_safety_refusal,
        })

    rows_data.append({
        "name": "Chakravyuh Scammer LoRA (single-shot)",
        "params": "0.5B + LoRA r=16",
        "bypass": ss.get("bypass_rate", 0.59375),
        "ci": ss.get("wilson_95ci", [0.471, 0.705]),
        "held_out": ss.get("held_out_rate", 0.5625),
        "highlight": True,
        "caveat": False,
    })

    def _row(d: dict) -> str:
        is_caveat = d.get("caveat", False)
        if d["highlight"]:
            bg = "background:#381932;color:#fff;"
        elif is_caveat:
            bg = "background:#FFF3E6;color:rgba(0,0,0,0.55);font-style:italic;"
        else:
            bg = "color:#000;"
        name_style = "font-weight:800;" if d["highlight"] else "font-weight:600;"
        ci_lo, ci_hi = d["ci"]
        return (
            f"<tr style='{bg}'>"
            f"<td style='padding:8px 12px;{name_style}'>{d['name']}</td>"
            f"<td style='padding:8px 12px;text-align:center;'>{d['params']}</td>"
            f"<td style='padding:8px 12px;text-align:center;font-weight:700;"
            f"font-family:\"JetBrains Mono\",monospace;'>{d['bypass'] * 100:.1f}%</td>"
            f"<td style='padding:8px 12px;text-align:center;font-size:11px;'>"
            f"[{ci_lo * 100:.1f}%, {ci_hi * 100:.1f}%]</td>"
            f"<td style='padding:8px 12px;text-align:center;'>{d['held_out'] * 100:.1f}%</td>"
            "</tr>"
        )

    rows_html = "\n".join(_row(d) for d in rows_data)

    return f"""
<div style="background:#fff;border:1px solid rgba(56,25,50,0.18);border-radius:12px;
            padding:18px 20px;margin:14px 0;">
  <div style="font-weight:700;font-size:14px;color:#381932;margin-bottom:12px;">
    Frontier LLMs as Scammers — who evades the scripted defense best?
  </div>
  <div style="overflow-x:auto;">
  <table style="border-collapse:collapse;font-size:13px;width:100%;min-width:580px;">
    <thead>
      <tr style="border-bottom:2px solid #381932;">
        <th style="padding:8px 12px;text-align:left;color:#381932;">Scammer model</th>
        <th style="padding:8px 12px;text-align:center;color:#381932;">Params</th>
        <th style="padding:8px 12px;text-align:center;color:#381932;">Bypass rate</th>
        <th style="padding:8px 12px;text-align:center;color:#381932;">95% CI</th>
        <th style="padding:8px 12px;text-align:center;color:#381932;">Held-out</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
  </div>
  <div style="margin-top:10px;font-size:12px;color:rgba(0,0,0,0.60);line-height:1.5;">
    All frontier models used the same 16 attack-category prompts (8 train + 8 held-out).
    <strong>*</strong> gpt-oss-120b "bypasses" at 87.5% mostly via <em>safety refusals</em>
    &mdash; the model refuses to generate scam text, which the analyzer scores as benign.
    The trained 0.5B Scammer generates <strong>actual</strong> scam text that evades keyword
    rules &mdash; a fundamentally different (and harder) capability.
  </div>
</div>
"""


def render_significance_panel() -> str:
    sig = _load_significance()
    if not sig:
        return ""

    t1 = sig.get("test_1_train_vs_held_out", {})
    t2 = sig.get("test_2_single_shot_vs_best_of_8", {})

    ss = t1.get("single_shot", {})
    bo8 = t1.get("best_of_8", {})

    return f"""
<div style="background:#FFFBF5;border:1px solid rgba(56,25,50,0.18);border-radius:12px;
            padding:18px 20px;margin:14px 0;">
  <div style="font-weight:700;font-size:14px;color:#381932;margin-bottom:12px;">
    Statistical evidence — the Scammer generalizes, and best-of-8 is real
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
    <div style="background:#fff;border:1px solid rgba(56,25,50,0.18);border-radius:8px;padding:14px;">
      <div style="font-size:12px;font-weight:700;color:#381932;margin-bottom:8px;">
        OOD Generalization (Fisher's exact)
      </div>
      <div style="font-size:13px;line-height:1.6;color:#000;">
        Train vs held-out bypass rates are <strong>not significantly different</strong>:
        <br>Single-shot: p = {ss.get('fisher_two_sided_p', 0.80):.3f}
        <br>Best-of-8: p = {bo8.get('fisher_two_sided_p', 0.11):.3f}
        <br><span style="color:rgba(0,0,0,0.55);font-size:12px;">
          Large p = the Scammer generalizes to unseen categories.
        </span>
      </div>
    </div>
    <div style="background:#fff;border:1px solid rgba(56,25,50,0.18);border-radius:8px;padding:14px;">
      <div style="font-size:12px;font-weight:700;color:#381932;margin-bottom:8px;">
        Best-of-8 Lift (McNemar exact)
      </div>
      <div style="font-size:13px;line-height:1.6;color:#000;">
        Best-of-8 strictly dominates single-shot:
        <br>p &approx; {t2.get('exact_two_sided_p', 4.77e-7):.1e}
        <br>Discordant: {t2.get('discordant_ss_miss_bo8_hit', 22)} cases where
        best-of-8 won but single-shot lost; <strong>0</strong> in reverse.
        <br><span style="color:rgba(0,0,0,0.55);font-size:12px;">
          Small p = the lift is real, not cherry-picking.
        </span>
      </div>
    </div>
  </div>
</div>
"""


def render_coevolution_panel() -> str:
    data = _load_coevolution()
    if not data:
        return ""

    overall = data.get("aggregate", {}).get("overall", {})
    n = overall.get("n", 64)

    scripted_bypass = overall.get("scripted_bypass_rate", 0.9375)
    v2_bypass = overall.get("v2_bypass_rate", 0.328125)
    gap = overall.get("gap_pp", (scripted_bypass - v2_bypass) * 100)

    return f"""
<div style="background:#fff;border:2px solid #381932;border-radius:12px;
            padding:18px 20px;margin:14px 0;">
  <div style="font-weight:700;font-size:14px;color:#381932;margin-bottom:12px;">
    Co-evolution in one number — the same scam outputs vs two defenders
  </div>
  <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:center;">
    <div style="text-align:center;padding:16px;background:#ffebee;border-radius:8px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
                  color:#b71c1c;margin-bottom:4px;">vs Scripted rules</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:700;color:#b71c1c;">
        {scripted_bypass * 100:.1f}%</div>
      <div style="font-size:11px;color:#b71c1c;opacity:0.7;">bypass rate</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:800;
                  color:#381932;">→ {gap:.0f} pp →</div>
      <div style="font-size:11px;color:rgba(0,0,0,0.55);">defensive lift</div>
    </div>
    <div style="text-align:center;padding:16px;background:#e8f5e9;border-radius:8px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
                  color:#1b5e20;margin-bottom:4px;">vs v2 LoRA defender</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:700;color:#1b5e20;">
        {v2_bypass * 100:.1f}%</div>
      <div style="font-size:11px;color:#1b5e20;opacity:0.7;">bypass rate</div>
    </div>
  </div>
  <div style="margin-top:12px;font-size:13px;color:#000;line-height:1.55;">
    The same {n} Scammer-generated outputs were scored by both defenders.
    The trained v2 Analyzer LoRA catches <strong>{gap:.0f} percentage points more</strong> than
    the rule-based baseline — that gap IS the multi-agent co-evolution, measured on identical inputs.
    Browse individual samples in the <strong>Adversary Lab</strong> tab.
  </div>
</div>
"""


def _model_params(short_name: str) -> str:
    mapping = {
        "Llama-3.3-70B-Instruct": "70B",
        "Qwen2.5-72B-Instruct": "72B",
        "DeepSeek-V3-0324": "671B MoE",
        "Qwen2.5-7B-Instruct": "7B",
        "gpt-oss-120b": "120B",
        "gemma-3-27b-it": "27B",
    }
    for key, val in mapping.items():
        if key.lower() in short_name.lower():
            return val
    return "—"
