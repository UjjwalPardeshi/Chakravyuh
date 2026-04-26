"""Adversary Lab — browse the 64 trained-Scammer outputs vs both defenders.

Renders the B.2 Phase-1 head-to-head data from
`logs/b2_phase1_scammer_vs_v2_lora.json` as a Gradio-friendly HTML
panel. Each sample shows:

  - The seed prompt that triggered the Scammer
  - The actual generated scam text
  - Scripted ScriptedAnalyzer's verdict (bypassed / caught)
  - v2 Analyzer LoRA's verdict (score, signals, explanation)
  - The asymmetry — when scripted misses but v2 catches, that IS the
    co-evolution gap made visible

This file ships zero new model dependencies — the data is pre-computed
and committed to the repo. The Adversary Lab tab is the *visible*
Theme #1 demonstration: trained adversary vs trained defender, on real
generated scam text, no hand-waving.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "b2_phase1_scammer_vs_v2_lora.json"


@dataclass(frozen=True)
class AdversarySample:
    index: int
    seed: str
    split: str
    completion: str
    length_chars: int
    is_refusal: bool
    scripted_score: float
    scripted_caught: bool
    v2_score: float
    v2_caught: bool
    v2_signals: tuple[str, ...]
    v2_explanation: str


def _parse_v2_response(raw: str) -> tuple[tuple[str, ...], str]:
    """Best-effort parse of the v2 JSON response. Returns (signals, explanation)."""
    if not raw:
        return ((), "")
    try:
        # The v2 response is JSON-formatted; sometimes wrapped in code-fence
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
        decoded = json.loads(text)
        signals = decoded.get("signals", []) or []
        if not isinstance(signals, list):
            signals = [str(signals)]
        explanation = str(decoded.get("explanation", "") or "")
        return (tuple(str(s) for s in signals), explanation)
    except (json.JSONDecodeError, IndexError, KeyError):
        return ((), raw[:240])


@lru_cache(maxsize=1)
def load_samples() -> tuple[AdversarySample, ...]:
    if not LOG_PATH.exists():
        return ()
    raw = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    samples_raw = raw.get("samples") or []
    out: list[AdversarySample] = []
    for i, s in enumerate(samples_raw):
        # Scripted bypass = True means scripted *missed*; caught = NOT bypass.
        scripted_caught = not bool(s.get("bypass", False))
        scripted_score = (
            float(s.get("scripted_score", 1.0 - float(s.get("reward", 0.0))))
            if "scripted_score" in s
            else round(1.0 - float(s.get("reward", 0.5)), 3)
        )
        v2_signals, v2_explanation = _parse_v2_response(s.get("v2_raw_response", ""))
        out.append(
            AdversarySample(
                index=i,
                seed=str(s.get("seed", "")),
                split=str(s.get("split", "")),
                completion=str(s.get("completion", "")),
                length_chars=int(s.get("length_chars", len(s.get("completion", "")))),
                is_refusal=bool(s.get("is_refusal", False)),
                scripted_score=scripted_score,
                scripted_caught=scripted_caught,
                v2_score=float(s.get("v2_score", 0.0)),
                v2_caught=bool(s.get("v2_caught", False)),
                v2_signals=v2_signals,
                v2_explanation=v2_explanation,
            )
        )
    return tuple(out)


def aggregate_stats() -> dict[str, object]:
    samples = load_samples()
    if not samples:
        return {"n": 0}
    by_split: dict[str, dict[str, int]] = {}
    cells = {"both_caught": 0, "only_scripted_missed": 0, "only_v2_missed": 0, "both_missed": 0}
    for s in samples:
        slot = by_split.setdefault(s.split, {"n": 0, "scripted_caught": 0, "v2_caught": 0})
        slot["n"] += 1
        slot["scripted_caught"] += int(s.scripted_caught)
        slot["v2_caught"] += int(s.v2_caught)
        if s.scripted_caught and s.v2_caught:
            cells["both_caught"] += 1
        elif (not s.scripted_caught) and s.v2_caught:
            cells["only_scripted_missed"] += 1
        elif s.scripted_caught and (not s.v2_caught):
            cells["only_v2_missed"] += 1
        else:
            cells["both_missed"] += 1
    return {"n": len(samples), "by_split": by_split, "cells": cells}


def sample_choice_labels() -> list[tuple[str, int]]:
    samples = load_samples()
    out: list[tuple[str, int]] = []
    for s in samples:
        scripted_tag = "✓" if s.scripted_caught else "✗"
        v2_tag = "✓" if s.v2_caught else "✗"
        seed_short = s.seed[:55].replace("\n", " ")
        if len(s.seed) > 55:
            seed_short += "…"
        label = f"#{s.index:02d} [{s.split:8s}] scripted {scripted_tag} · v2 {v2_tag} — {seed_short}"
        out.append((label, s.index))
    return out


def _verdict_pill(caught: bool) -> str:
    if caught:
        return (
            '<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
            'background:#e8f5e9;color:#1b5e20;font-weight:700;font-size:12px;">CAUGHT</span>'
        )
    return (
        '<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        'background:#ffebee;color:#b71c1c;font-weight:700;font-size:12px;">BYPASSED</span>'
    )


def render_aggregate_banner() -> str:
    stats = aggregate_stats()
    if stats["n"] == 0:
        return '<div style="color:#b71c1c;">Adversary Lab data not loaded — `logs/b2_phase1_scammer_vs_v2_lora.json` missing.</div>'
    cells = stats["cells"]
    by_split = stats["by_split"]
    total = stats["n"]
    train = by_split.get("train", {"n": 0, "scripted_caught": 0, "v2_caught": 0})
    held = by_split.get("held_out", {"n": 0, "scripted_caught": 0, "v2_caught": 0})

    def _row(name: str, n: int, sc: int, v2c: int) -> str:
        sc_pct = 100 * (1 - sc / n) if n else 0
        v2_pct = 100 * (1 - v2c / n) if n else 0
        gap = sc_pct - v2_pct
        return (
            f"<tr><td style='padding:4px 12px;'>{name}</td>"
            f"<td style='padding:4px 12px;text-align:right;'>{n}</td>"
            f"<td style='padding:4px 12px;text-align:right;color:#b71c1c;font-weight:700;'>{sc_pct:.1f}%</td>"
            f"<td style='padding:4px 12px;text-align:right;color:#1b5e20;font-weight:700;'>{v2_pct:.1f}%</td>"
            f"<td style='padding:4px 12px;text-align:right;font-weight:700;'>+{gap:.1f} pp</td></tr>"
        )

    return f"""
<div style="background:#FFF3E6;border:1px solid #381932;border-radius:8px;padding:14px 18px;margin:6px 0 14px;">
  <div style="font-weight:700;font-size:15px;margin-bottom:8px;color:#381932;">
    B.2 Phase-1 head-to-head — same Scammer outputs vs both defenders (n={total})
  </div>
  <table style="border-collapse:collapse;font-size:13px;width:100%;">
    <thead>
      <tr style="border-bottom:1px solid #381932;color:#381932;">
        <th style="padding:4px 12px;text-align:left;">Split</th>
        <th style="padding:4px 12px;text-align:right;">n</th>
        <th style="padding:4px 12px;text-align:right;">Scripted bypass</th>
        <th style="padding:4px 12px;text-align:right;">v2 LoRA bypass</th>
        <th style="padding:4px 12px;text-align:right;">Gap</th>
      </tr>
    </thead>
    <tbody>
      {_row("Train", train['n'], train['scripted_caught'], train['v2_caught'])}
      {_row("Held-out (novel)", held['n'], held['scripted_caught'], held['v2_caught'])}
      {_row("Overall", total, train['scripted_caught'] + held['scripted_caught'],
            train['v2_caught'] + held['v2_caught'])}
    </tbody>
  </table>
  <div style="margin-top:10px;font-size:12px;color:#000;">
    <strong>Cross-tab:</strong>
    {cells['both_caught']} both caught ·
    <strong style="color:#1b5e20;">{cells['only_scripted_missed']} only-scripted-missed</strong>
    (the co-evolution wins) ·
    {cells['only_v2_missed']} only-v2-missed (v3 targets) ·
    {cells['both_missed']} both missed
  </div>
</div>
"""


def render_sample(index: int) -> str:
    samples = load_samples()
    if index < 0 or index >= len(samples):
        return '<div style="color:#b71c1c;">Sample index out of range.</div>'
    s = samples[index]
    seed_html = (
        s.seed.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
    completion_html = (
        s.completion.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
    explanation_html = (
        s.v2_explanation.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    signals_html = " ".join(
        f'<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
        f'background:#FFF3E6;border:1px solid #381932;color:#381932;'
        f'margin:2px 4px 2px 0;font-size:11px;">{sig}</span>'
        for sig in s.v2_signals
    )
    if not signals_html:
        signals_html = '<span style="color:#666;font-size:12px;">(no signals declared)</span>'

    asymmetry_note = ""
    if (not s.scripted_caught) and s.v2_caught:
        asymmetry_note = (
            '<div style="background:#e8f5e9;border-left:4px solid #1b5e20;padding:8px 12px;'
            'margin-top:10px;font-size:13px;color:#1b5e20;">'
            "<strong>This is the co-evolution win.</strong> The trained Scammer evaded the "
            "rule-based detector — but the v2 Analyzer LoRA (trained on the env's 8-rubric "
            "reward) catches it. This is the kind of pair that the +60 pp head-to-head gap "
            "is built from."
            "</div>"
        )
    elif s.scripted_caught and (not s.v2_caught):
        asymmetry_note = (
            '<div style="background:#fff3e0;border-left:4px solid #e65100;padding:8px 12px;'
            'margin-top:10px;font-size:13px;color:#bf360c;">'
            "<strong>v3 target.</strong> Scripted's keyword rules caught this, but our "
            "v2 LoRA missed it — typically a non-bank category outside v2's training "
            "distribution. Phase-2 LoRA-vs-LoRA retrain (queued for onsite GPU) closes "
            "exactly these cases."
            "</div>"
        )

    return f"""
<div style="background:#fff;border:1px solid #381932;border-radius:8px;padding:16px 18px;">
  <div style="font-size:11px;color:#666;margin-bottom:6px;">
    Sample #{s.index} · split = <strong>{s.split}</strong> · {s.length_chars} chars
    {' · <strong style="color:#b71c1c;">REFUSAL</strong>' if s.is_refusal else ''}
  </div>

  <div style="font-weight:700;font-size:13px;color:#381932;margin-bottom:4px;">
    Seed prompt (what the trained Scammer was asked to write)
  </div>
  <div style="background:#FFF3E6;padding:10px 12px;border-radius:6px;margin-bottom:14px;
              font-size:13px;line-height:1.5;color:#000;">{seed_html}</div>

  <div style="font-weight:700;font-size:13px;color:#381932;margin-bottom:4px;">
    Generated scam text (Qwen2.5-0.5B + LoRA, after 200 GRPO episodes)
  </div>
  <div style="background:#FFF;border:1px dashed #381932;padding:10px 12px;border-radius:6px;
              margin-bottom:14px;font-size:13px;line-height:1.5;color:#000;
              font-family:'SF Mono','Menlo',monospace;">{completion_html}</div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
    <div style="background:#FFF;border:2px solid #b71c1c;border-radius:6px;padding:12px;">
      <div style="font-weight:700;font-size:13px;color:#381932;margin-bottom:6px;">
        Defender 1 — rule-based <code>ScriptedAnalyzer</code>
      </div>
      <div style="font-size:13px;color:#000;">
        Score: <strong>{s.scripted_score:.2f}</strong> · {_verdict_pill(s.scripted_caught)}
      </div>
    </div>
    <div style="background:#FFF;border:2px solid #1b5e20;border-radius:6px;padding:12px;">
      <div style="font-weight:700;font-size:13px;color:#381932;margin-bottom:6px;">
        Defender 2 — <code>chakravyuh-analyzer-lora-v2</code> (trained)
      </div>
      <div style="font-size:13px;color:#000;margin-bottom:6px;">
        Score: <strong>{s.v2_score:.2f}</strong> · {_verdict_pill(s.v2_caught)}
      </div>
      <div style="font-size:11px;color:#666;margin-bottom:4px;">Signals declared:</div>
      <div style="margin-bottom:8px;">{signals_html}</div>
      <div style="font-size:11px;color:#666;margin-bottom:2px;">Explanation:</div>
      <div style="font-size:12px;line-height:1.5;color:#000;">{explanation_html or '<em style="color:#666;">(no parseable explanation)</em>'}</div>
    </div>
  </div>

  {asymmetry_note}
</div>
"""
