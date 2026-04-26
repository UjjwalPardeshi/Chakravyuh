"""FastAPI entrypoint for Chakravyuh — OpenEnv API + Gradio demo on one app.

Routes:
  /                — landing page (HTML)  ← was 404 before
  /demo            — interactive Gradio demo (mounted)
  /reset, /step,
  /state, /metadata,
  /schema, /health — OpenEnv contract
  /leaderboard, /submit — public leaderboard (E.10)
  /docs, /openapi.json — FastAPI swagger / schema
  /mcp/*           — MCP server (registered by openenv-core)

Run locally:
    uvicorn server.app:app --host 0.0.0.0 --port 8000

Hugging Face Space / Docker:
    Referenced by ``openenv.yaml`` as ``app: server.app:app``.
"""

from __future__ import annotations

import os

from fastapi.responses import HTMLResponse
from openenv.core.env_server import create_app

from chakravyuh_env.openenv_environment import ChakravyuhOpenEnv
from chakravyuh_env.openenv_models import ChakravyuhAction, ChakravyuhObservation
from server.diagnose_endpoint import attach_to_app as attach_diagnose
from server.eval_endpoint import attach_to_app as attach_eval
from server.leaderboard import attach_to_app

# One factory call per concurrent session → fully isolated episodes.
max_concurrent = int(os.getenv("MAX_CONCURRENT_ENVS", "8"))

app = create_app(
    ChakravyuhOpenEnv,
    ChakravyuhAction,
    ChakravyuhObservation,
    env_name="chakravyuh_env",
    max_concurrent_envs=max_concurrent,
)

# Public leaderboard endpoints (E.10): GET /leaderboard, POST /submit.
# Persistence at logs/leaderboard.jsonl (override via CHAKRAVYUH_LEADERBOARD_PATH).
attach_to_app(app)

# Research endpoints: GET /eval (and /eval/{bootstrap,known-novel,redteam,…}),
# POST /diagnose (single-message rubric breakdown using AnalyzerRubricV2).
attach_eval(app)
attach_diagnose(app)


# ---------------------------------------------------------------------------
# Landing page — replaces FastAPI's default 404 at `/` so the HF Space root
# shows something useful at-a-glance.
# ---------------------------------------------------------------------------

_LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only">
<title>Chakravyuh — Multi-Agent Fraud Arena</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
<style>
  :root { color-scheme: light only; }
  *, *::before, *::after { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0;
    background: #FFF3E6;
    color: #000000;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    line-height: 1.6;
  }
  .wrap {
    max-width: 880px;
    margin: 0 auto;
    padding: 56px 24px 64px;
  }
  .eyebrow {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #FFFFFF;
    background: #381932;
    padding: 5px 12px;
    border-radius: 999px;
    margin-bottom: 18px;
  }
  h1 {
    font-size: clamp(30px, 5vw, 44px);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.6px;
    margin: 0 0 12px;
    color: #000000;
  }
  .lede {
    font-size: clamp(15px, 1.5vw, 17px);
    line-height: 1.6;
    color: rgba(0, 0, 0, 0.78);
    max-width: 720px;
    margin: 0 0 32px;
  }
  .cta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin: 28px 0 36px;
  }
  .cta {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 13px 22px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 14px;
    text-decoration: none;
    border: 1px solid transparent;
    transition: transform .08s ease, background .15s ease, border-color .15s ease;
  }
  .cta:hover { transform: translateY(-1px); }
  .cta.primary {
    background: #381932; color: #FFFFFF; border-color: #381932;
  }
  .cta.primary:hover { background: #2A0F25; }
  .cta.secondary {
    background: #FFFFFF; color: #000000; border-color: rgba(56,25,50,0.30);
  }
  .cta.secondary:hover {
    background: rgba(56,25,50,0.08); border-color: #381932;
  }
  h2 {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    color: #000000;
    margin: 36px 0 14px;
    display: flex; align-items: center; gap: 10px;
  }
  h2::before {
    content: ""; width: 16px; height: 2px;
    background: #381932; border-radius: 999px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin: 0 0 24px;
  }
  .endpoint {
    display: block;
    padding: 14px 16px;
    background: #FFFBF5;
    border: 1px solid rgba(56,25,50,0.18);
    border-radius: 12px;
    text-decoration: none;
    color: #000000;
    transition: border-color .15s, transform .08s;
  }
  .endpoint:hover {
    border-color: #381932; transform: translateY(-1px);
  }
  .endpoint code {
    display: block;
    font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace;
    font-weight: 700;
    font-size: 13px;
    color: #381932;
    margin-bottom: 4px;
  }
  .endpoint span {
    font-size: 12px;
    color: rgba(0,0,0,0.72);
    line-height: 1.45;
    display: block;
  }
  .stat-row {
    display: flex; flex-wrap: wrap;
    gap: 8px;
    margin: 0 0 12px;
  }
  .stat {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    padding: 7px 13px;
    background: #FFFFFF;
    border: 1px solid rgba(56,25,50,0.18);
    border-radius: 999px;
    font-size: 12px;
  }
  .stat-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: rgba(0,0,0,0.72);
  }
  .stat-value {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-weight: 700;
    color: #000000;
    font-variant-numeric: tabular-nums;
  }
  footer {
    margin-top: 40px;
    padding-top: 18px;
    border-top: 1px solid rgba(56,25,50,0.18);
    font-size: 12px;
    color: rgba(0,0,0,0.72);
    line-height: 1.6;
  }
  footer a {
    color: #381932; font-weight: 600;
    text-decoration: underline;
    text-decoration-thickness: 1.5px;
    text-underline-offset: 3px;
  }
</style>
</head>
<body>
<main class="wrap">
  <span class="eyebrow">Chakravyuh · Multi-Agent Fraud Arena</span>
  <h1>A self-improving benchmark for Indian UPI fraud detection.</h1>
  <p class="lede">Five agents — Scammer, Victim, on-device Analyzer LLM, Bank Monitor, Regulator —
  run multi-turn fraud episodes under structural information asymmetry. The Analyzer is a
  Qwen2.5-7B LoRA post-trained with TRL's GRPO on a composable 8-rubric reward.
  v1 hit detection 100 % / FPR 36 % (textbook reward-hack); v2 retrained with three principled
  fixes hits <strong>99.3 % detection</strong> / <strong>6.7 % FPR</strong>.</p>

  <div class="cta-row">
    <a class="cta primary" href="/demo/">Open the interactive demo →</a>
    <a class="cta secondary" href="/docs">API docs (Swagger)</a>
    <a class="cta secondary" href="/leaderboard">Leaderboard</a>
  </div>

  <h2>Headline numbers</h2>
  <div class="stat-row">
    <span class="stat"><span class="stat-label">Detection</span><span class="stat-value">99.3 %</span></span>
    <span class="stat"><span class="stat-label">FPR</span><span class="stat-value">6.7 %</span></span>
    <span class="stat"><span class="stat-label">F1</span><span class="stat-value">0.99</span></span>
    <span class="stat"><span class="stat-label">Bench</span><span class="stat-value">n = 175</span></span>
    <span class="stat"><span class="stat-label">Novel det.</span><span class="stat-value">97.1 %</span></span>
  </div>

  <h2>Endpoints</h2>
  <div class="grid">
    <a class="endpoint" href="/demo/">
      <code>/demo/</code>
      <span>Interactive Gradio UI — replay 5 curated episodes or score your own message.</span>
    </a>
    <a class="endpoint" href="/health">
      <code>GET /health</code>
      <span>OpenEnv liveness probe. Returns {"status": "healthy"}.</span>
    </a>
    <a class="endpoint" href="/metadata">
      <code>GET /metadata</code>
      <span>Environment metadata (action / observation schema, version).</span>
    </a>
    <a class="endpoint" href="/schema">
      <code>GET /schema</code>
      <span>Pydantic model JSON schemas.</span>
    </a>
    <a class="endpoint" href="/leaderboard">
      <code>GET /leaderboard</code>
      <span>Ranked submissions on chakravyuh-bench-v0 (3 seeded entries).</span>
    </a>
    <a class="endpoint" href="/eval">
      <code>GET /eval</code>
      <span>v2 eval artifact — detection / FPR / F1 / per-difficulty.</span>
    </a>
    <a class="endpoint" href="/eval/bootstrap">
      <code>GET /eval/bootstrap</code>
      <span>10k-iteration percentile bootstrap 95% CIs.</span>
    </a>
    <a class="endpoint" href="/docs#/diagnose/post_diagnose_diagnose_post">
      <code>POST /diagnose</code>
      <span>Score one message; get full 8-rubric AnalyzerRubricV2 decomposition.</span>
    </a>
    <a class="endpoint" href="/docs">
      <code>/docs · /openapi.json</code>
      <span>Interactive API explorer + OpenAPI 3.1 schema.</span>
    </a>
  </div>

  <footer>
    Chakravyuh — open-source benchmark for Indian UPI fraud detection · entry to the
    Meta PyTorch <strong>OpenEnv Hackathon 2026</strong>, Bangalore. Bench
    <a href="https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0">chakravyuh-bench-v0</a> ·
    Adapter <a href="https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2">chakravyuh-analyzer-lora-v2</a> ·
    Repo <a href="https://github.com/UjjwalPardeshi/Chakravyuh">UjjwalPardeshi/Chakravyuh</a> ·
    MIT (code) · CC-BY-4.0 (dataset).
  </footer>
</main>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing() -> HTMLResponse:
    """Friendly landing page at the Space root (was 404 before)."""
    return HTMLResponse(_LANDING_HTML)


@app.get("/manifest.json", include_in_schema=False)
def manifest() -> dict:
    """Minimal web-app manifest — eliminates the 404 that browser DevTools reports."""
    return {
        "name": "Chakravyuh",
        "short_name": "Chakravyuh",
        "description": "Multi-Agent UPI Fraud Detection Arena",
        "start_url": "/",
        "display": "browser",
        "background_color": "#FFF3E6",
        "theme_color": "#381932",
        "icons": [],
    }


_DEMO_PREVIEW_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chakravyuh — warming up</title>
<style>
  body { font-family: -apple-system, system-ui, Segoe UI, sans-serif;
         margin: 0; padding: 48px 24px; background: #faf9f6; color: #1a1a1a; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 26px; margin: 0 0 6px; }
  .sub { color: #666; margin: 0 0 24px; font-size: 14px; }
  figure { margin: 0 0 24px; }
  img { max-width: 100%; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  figcaption { font-size: 12px; color: #777; margin-top: 6px; }
  .pill { display: inline-block; padding: 4px 10px; border-radius: 999px;
          background: rgba(46,125,50,0.10); color: #1b5e20; font-size: 12px;
          letter-spacing: 0.04em; text-transform: uppercase; }
  a { color: #1565c0; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 16px 0 24px; }
  .card { padding: 14px; background: #fff; border-radius: 10px;
          box-shadow: 0 1px 4px rgba(0,0,0,0.06); font-size: 13px; line-height: 1.5; }
  .card strong { color: #b71c1c; }
  @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
</style>
</head><body><main>
  <span class="pill">Warming up · ~10–30s</span>
  <h1>Chakravyuh — multi-agent UPI fraud detection</h1>
  <p class="sub">The interactive demo is booting. While it warms up, here's the headline result.</p>
  <figure>
    <img src="https://raw.githubusercontent.com/UjjwalPardeshi/Chakravyuh/a9e723bf495182724845dbf1f69f8968434a9e02/docs/assets/plots/v2_per_difficulty_check.png"
         alt="Per-difficulty detection: scripted analyzer vs Chakravyuh v2 LoRA — scripted catches 50% on novel post-2024 scams; v2 catches 97%.">
    <figcaption>Per-difficulty detection — scripted vs Chakravyuh v2 (n = 175 bench scenarios).</figcaption>
  </figure>
  <div class="grid">
    <div class="card">
      <strong>v1 (reward-hacked)</strong><br>
      detection 100 % · FPR <strong>36 %</strong> · F1 0.96 · the model learned to flag everything.
    </div>
    <div class="card">
      <strong>v2 (principled retrain)</strong><br>
      detection 99.3 % · FPR <strong>6.7 %</strong> · F1 0.99 · same detection, FPR collapsed 5×.
    </div>
  </div>
  <p style="font-size:13px;color:#444">Once the demo is live, you'll see five tabs: Replay, Live Q&amp;A, You vs Analyzer, v1↔v2 toggle, <strong>🔴 Red-team it yourself</strong>, and Leaderboard.</p>
  <p><a href="/">← back to landing</a> · <a href="/demo/" id="live-link">try the live demo</a></p>
<script>
  // Poll /demo/ every 2s; redirect when 200.
  (function poll() {
    fetch('/demo/', { method: 'HEAD', cache: 'no-store' }).then(function(r){
      if (r.ok) { window.location.href = '/demo/'; }
      else { setTimeout(poll, 2000); }
    }).catch(function(){ setTimeout(poll, 2000); });
  })();
</script>
</main></body></html>"""


@app.get("/demo/preview", response_class=HTMLResponse, include_in_schema=False)
def demo_preview() -> HTMLResponse:
    """Static fallback that renders instantly while Gradio /demo/ warms up.
    Self-redirects to /demo/ once that route returns 200."""
    return HTMLResponse(_DEMO_PREVIEW_HTML)


# ---------------------------------------------------------------------------
# Mount the Gradio demo at /demo. Lazy-import so importing server.app stays
# cheap for tools that only want the FastAPI app (the existing test suite).
# ---------------------------------------------------------------------------

def _mount_demo() -> None:
    """Mount the Gradio demo at /demo. Lazy imports keep the OpenEnv API
    alive even if `gradio` is not installed (e.g. in a slim runtime image)."""
    import gradio as gr  # type: ignore[import-not-found]

    from server.demo_ui import build_app as _build_demo, _build_theme, CUSTOM_CSS
    demo_blocks = _build_demo()
    gr.mount_gradio_app(
        app,
        demo_blocks,
        path="/demo",
        theme=_build_theme(),
        css=CUSTOM_CSS,
    )


# Mount on import so uvicorn picks it up without a separate startup hook.
# Failures here must not crash the OpenEnv API surface — log full traceback
# and continue so /reset, /step, /state, /eval, /diagnose still serve.
try:
    _mount_demo()
except (ImportError, ModuleNotFoundError) as _demo_err:
    import logging
    logging.getLogger("chakravyuh.app").error(
        "Gradio not installed; /demo route disabled. Error: %s", _demo_err
    )
except Exception:
    import logging
    logging.getLogger("chakravyuh.app").exception(
        "Unexpected failure mounting Gradio demo at /demo — /demo will 404 "
        "but other OpenEnv routes remain healthy. See traceback above."
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )


if __name__ == "__main__":
    main()
