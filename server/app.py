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
<meta name="description" content="A self-improving benchmark for Indian UPI fraud detection. Five agents compete under structural information asymmetry.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='15' fill='%23381932'/><circle cx='16' cy='16' r='6' fill='none' stroke='%23e8c97a' stroke-width='2'/><line x1='16' y1='2' x2='16' y2='10' stroke='%23e8c97a' stroke-width='2'/><line x1='16' y1='22' x2='16' y2='30' stroke='%23e8c97a' stroke-width='2'/><line x1='2' y1='16' x2='10' y2='16' stroke='%23e8c97a' stroke-width='2'/><line x1='22' y1='16' x2='30' y2='16' stroke='%23e8c97a' stroke-width='2'/><line x1='6.1' y1='6.1' x2='11.8' y2='11.8' stroke='%23e8c97a' stroke-width='2'/><line x1='20.2' y1='20.2' x2='25.9' y2='25.9' stroke='%23e8c97a' stroke-width='2'/><line x1='25.9' y1='6.1' x2='20.2' y2='11.8' stroke='%23e8c97a' stroke-width='2'/><line x1='11.8' y1='20.2' x2='6.1' y2='25.9' stroke='%23e8c97a' stroke-width='2'/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;0,800;1,700&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
<style>
  :root {
    --plum: #381932;
    --plum-dark: #2A0F25;
    --plum-light: rgba(56,25,50,0.08);
    --plum-border: rgba(56,25,50,0.18);
    --cream: #FFF3E6;
    --cream-2: #FFFBF5;
    --gold: #e8c97a;
    --text: #000000;
    --text-muted: rgba(0,0,0,0.62);
    --radius: 12px;
    --nav-h: 64px;
    color-scheme: light only;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body {
    background: var(--cream);
    color: var(--text);
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    line-height: 1.6;
    min-height: 100vh;
  }

  /* ── Navbar ── */
  .nav {
    position: sticky; top: 0; z-index: 100;
    background: rgba(255,243,230,0.85);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--plum-border);
    height: var(--nav-h);
  }
  .nav-inner {
    max-width: 1600px; margin: 0 auto;
    padding: 0 32px;
    height: 100%;
    display: flex; align-items: center; gap: 24px;
  }
  .nav-logo {
    display: flex; align-items: center; gap: 10px;
    text-decoration: none; color: var(--text);
    font-weight: 800; font-size: 16px; letter-spacing: -0.3px;
    flex-shrink: 0;
  }
  .nav-logo-badge {
    width: 32px; height: 32px; border-radius: 8px;
    background: var(--plum); color: var(--gold);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 800;
  }
  .nav-links {
    display: flex; align-items: center; gap: 4px;
    margin-left: auto;
  }
  .nav-link {
    padding: 6px 14px; border-radius: 8px;
    font-size: 14px; font-weight: 600;
    text-decoration: none; color: var(--text-muted);
    transition: color .15s, background .15s;
  }
  .nav-link:hover { color: var(--text); background: var(--plum-light); }
  .nav-cta {
    margin-left: 8px;
    padding: 8px 18px; border-radius: 8px;
    background: var(--plum); color: #fff;
    font-size: 14px; font-weight: 700;
    text-decoration: none;
    transition: background .15s, transform .08s;
    white-space: nowrap;
  }
  .nav-cta:hover { background: var(--plum-dark); transform: translateY(-1px); }
  .nav-ham { display: none; }

  /* ── Page shell ── */
  .page { max-width: 1600px; margin: 0 auto; padding: 0 32px; }

  /* ── Hero ── */
  .hero {
    display: grid;
    grid-template-columns: 1fr 420px;
    gap: 48px;
    align-items: center;
    padding: 72px 0 80px;
  }
  .hero-eyebrow {
    display: inline-block;
    font-size: 11px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase;
    color: #fff; background: var(--plum);
    padding: 5px 13px; border-radius: 999px;
    margin-bottom: 20px;
  }
  .hero h1 {
    font-size: clamp(32px, 3.8vw, 56px);
    font-weight: 800; line-height: 1.08; letter-spacing: -1px;
    margin-bottom: 20px;
  }
  .hero h1 em {
    font-style: normal; color: var(--plum);
  }
  .hero-lede {
    font-size: clamp(15px, 1.3vw, 17px);
    line-height: 1.7;
    color: var(--text-muted);
    max-width: 580px;
    margin-bottom: 36px;
  }
  .cta-row {
    display: flex; flex-wrap: wrap; gap: 12px;
    margin-bottom: 36px;
  }
  .cta {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 13px 24px; border-radius: var(--radius);
    font-weight: 700; font-size: 14px;
    text-decoration: none;
    border: 1.5px solid transparent;
    transition: transform .08s ease, background .15s ease, border-color .15s ease;
  }
  .cta:hover { transform: translateY(-2px); }
  .cta.primary { background: var(--plum); color: #fff; border-color: var(--plum); }
  .cta.primary:hover { background: var(--plum-dark); }
  .cta.secondary { background: #fff; color: var(--text); border-color: var(--plum-border); }
  .cta.secondary:hover { background: var(--plum-light); border-color: var(--plum); }
  .badge-row {
    display: flex; flex-wrap: wrap; gap: 8px;
  }
  .badge {
    display: inline-block;
    padding: 4px 10px; border-radius: 999px;
    font-size: 11px; font-weight: 600;
    background: #fff; border: 1px solid var(--plum-border);
    color: var(--text-muted);
  }

  /* ── Stat cards (hero right) ── */
  .stat-cards {
    display: flex; flex-direction: column; gap: 12px;
  }
  .stat-card {
    background: #fff;
    border: 1.5px solid var(--plum-border);
    border-radius: var(--radius);
    padding: 20px 24px;
  }
  .stat-card.accent {
    background: var(--plum); color: #fff;
    border-color: var(--plum);
  }
  .stat-card-label {
    font-size: 11px; font-weight: 700; letter-spacing: 1.4px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 6px;
  }
  .stat-card.accent .stat-card-label { color: rgba(255,255,255,0.65); }
  .stat-card-value {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 36px; font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1;
    color: var(--text);
  }
  .stat-card.accent .stat-card-value { color: var(--gold); }
  .stat-card-sub {
    font-size: 12px; color: var(--text-muted); margin-top: 4px;
  }
  .stat-card.accent .stat-card-sub { color: rgba(255,255,255,0.55); }
  .stat-pair {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
  }
  .stat-pair .stat-card-value { font-size: 26px; }

  /* ── Section heading ── */
  .section { padding: 64px 0; }
  .section-head {
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 28px;
  }
  .section-head::before {
    content: ""; flex-shrink: 0;
    width: 20px; height: 3px;
    background: var(--plum); border-radius: 999px;
  }
  .section-title {
    font-size: 11px; font-weight: 800; letter-spacing: 1.8px;
    text-transform: uppercase; color: var(--text);
  }

  /* ── Features grid ── */
  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
  }
  .feature-card {
    background: var(--cream-2);
    border: 1px solid var(--plum-border);
    border-radius: var(--radius);
    padding: 22px 20px;
    transition: border-color .15s, transform .08s;
  }
  .feature-card:hover { border-color: var(--plum); transform: translateY(-2px); }
  .feature-icon {
    font-size: 22px; margin-bottom: 12px; display: block;
  }
  .feature-name {
    font-size: 14px; font-weight: 700; margin-bottom: 6px;
  }
  .feature-desc {
    font-size: 13px; color: var(--text-muted); line-height: 1.55;
  }

  /* ── Endpoints grid ── */
  .endpoints-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .endpoint {
    display: block;
    padding: 16px 18px;
    background: var(--cream-2);
    border: 1px solid var(--plum-border);
    border-radius: var(--radius);
    text-decoration: none; color: var(--text);
    transition: border-color .15s, transform .08s;
  }
  .endpoint:hover { border-color: var(--plum); transform: translateY(-2px); }
  .endpoint code {
    display: block;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-weight: 700; font-size: 13px;
    color: var(--plum); margin-bottom: 5px;
  }
  .endpoint span {
    font-size: 12px; color: var(--text-muted);
    line-height: 1.5; display: block;
  }

  /* ── Divider ── */
  .divider {
    border: none; border-top: 1px solid var(--plum-border);
    margin: 0;
  }

  /* ── Footer ── */
  footer {
    background: var(--plum);
    padding: 40px 0;
    margin-top: 0;
  }
  .footer-inner {
    max-width: 1600px; margin: 0 auto;
    padding: 0 32px;
    display: flex; align-items: center;
    justify-content: space-between;
    gap: 24px; flex-wrap: wrap;
  }
  .footer-brand {
    font-size: 15px; font-weight: 700; color: #fff;
    margin-bottom: 4px;
  }
  .footer-copy {
    font-size: 12px; color: rgba(255,255,255,0.55);
    line-height: 1.6;
  }
  .footer-links {
    display: flex; flex-wrap: wrap; gap: 8px;
  }
  .footer-link {
    padding: 6px 14px; border-radius: 999px;
    font-size: 12px; font-weight: 600;
    text-decoration: none;
    color: rgba(255,255,255,0.75);
    border: 1px solid rgba(255,255,255,0.20);
    transition: background .15s, color .15s;
  }
  .footer-link:hover { background: rgba(255,255,255,0.12); color: #fff; }

  /* ── Responsive ── */
  @media (max-width: 1100px) {
    .hero { grid-template-columns: 1fr; gap: 40px; }
    .stat-cards { flex-direction: row; flex-wrap: wrap; }
    .stat-card { flex: 1 1 180px; }
  }
  @media (max-width: 900px) {
    .page { padding: 0 20px; }
    .nav-inner { padding: 0 20px; }
    .hero { padding: 48px 0 56px; }
    .nav-links .nav-link { display: none; }
    .footer-inner { padding: 0 20px; }
  }
  @media (max-width: 600px) {
    .hero { padding: 36px 0 44px; }
    .stat-pair { grid-template-columns: 1fr; }
    .cta { padding: 11px 18px; font-size: 13px; }
    .footer-inner { flex-direction: column; align-items: flex-start; }
  }
  @media (min-width: 1400px) {
    .features-grid { grid-template-columns: repeat(4, 1fr); }
  }
</style>
</head>
<body>

<!-- ── Navbar ── -->
<nav class="nav">
  <div class="nav-inner">
    <a class="nav-logo" href="/">
      <span class="nav-logo-badge">C</span>
      Chakravyuh
    </a>
    <div class="nav-links">
      <a class="nav-link" href="/demo/">Demo</a>
      <a class="nav-link" href="/leaderboard">Leaderboard</a>
      <a class="nav-link" href="/eval">Eval</a>
      <a class="nav-link" href="/docs">API</a>
      <a class="nav-cta" href="/demo/">Open Demo &rarr;</a>
    </div>
  </div>
</nav>

<!-- ── Hero ── -->
<div class="page">
  <section class="hero">
    <div class="hero-left">
      <span class="hero-eyebrow">Multi-Agent UPI Fraud Arena</span>
      <h1>The benchmark where <em>scammers train</em> against defenders.</h1>
      <p class="hero-lede">
        Five agents &mdash; Scammer, Victim, on-device Analyzer LLM, Bank Monitor, Regulator &mdash;
        run adversarial fraud episodes under structural information asymmetry.
        <strong>Two trained adapters:</strong> the Analyzer (Qwen2.5-7B + LoRA, 8-rubric GRPO)
        hits <strong>99.3&thinsp;% detection / 6.7&thinsp;% FPR</strong>; the Scammer
        (Qwen2.5-0.5B + LoRA, adversarial GRPO) bypasses rules at
        <strong>93.75&thinsp;%</strong> &mdash; a 0.5B model beating 70B+ frontier LLMs
        at detector evasion.
      </p>
      <div class="cta-row">
        <a class="cta primary" href="/demo/">Open interactive demo &rarr;</a>
        <a class="cta secondary" href="/docs">API docs (Swagger)</a>
        <a class="cta secondary" href="/leaderboard">Leaderboard</a>
      </div>
      <div class="badge-row">
        <span class="badge">OpenEnv Hackathon 2026</span>
        <span class="badge">MIT License</span>
        <span class="badge">CC-BY-4.0 Dataset</span>
        <span class="badge">n = 175 bench scenarios</span>
      </div>
    </div>

    <div class="stat-cards">
      <div class="stat-card accent">
        <div class="stat-card-label">v2 Detection rate</div>
        <div class="stat-card-value">99.3%</div>
        <div class="stat-card-sub">vs 100% v1 (reward-hacked)</div>
      </div>
      <div class="stat-pair">
        <div class="stat-card">
          <div class="stat-card-label">v2 FPR</div>
          <div class="stat-card-value">6.7%</div>
          <div class="stat-card-sub">v1 was 36%</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">F1 Score</div>
          <div class="stat-card-value">0.99</div>
          <div class="stat-card-sub">+0.03 vs v1</div>
        </div>
      </div>
      <div class="stat-pair">
        <div class="stat-card">
          <div class="stat-card-label">Novel det.</div>
          <div class="stat-card-value">97.1%</div>
          <div class="stat-card-sub">post-2024 scams</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">Bench size</div>
          <div class="stat-card-value">175</div>
          <div class="stat-card-sub">scenarios</div>
        </div>
      </div>
      <div class="stat-card accent">
        <div class="stat-card-label">Scammer LoRA bypass (0.5B)</div>
        <div class="stat-card-value">93.75%</div>
        <div class="stat-card-sub">best-of-8 vs rules &middot; beats 70B+ frontier LLMs</div>
      </div>
    </div>
  </section>

  <hr class="divider">

  <!-- ── Features ── -->
  <section class="section">
    <div class="section-head">
      <span class="section-title">Five-agent arena</span>
    </div>
    <div class="features-grid">
      <div class="feature-card">
        <span class="feature-icon">&#x1F3AD;</span>
        <div class="feature-name">Scammer</div>
        <div class="feature-desc">Qwen2.5-0.5B + LoRA trained via GRPO to craft convincing UPI fraud scripts across banking, KYC, OTP and CEO-deepfake categories.</div>
      </div>
      <div class="feature-card">
        <span class="feature-icon">&#x1F6E1;</span>
        <div class="feature-name">Analyzer LLM</div>
        <div class="feature-desc">Qwen2.5-7B LoRA post-trained on 8-rubric GRPO reward. v2 retrain fixed reward hacking: FPR dropped 5&times; while detection held at 99.3%.</div>
      </div>
      <div class="feature-card">
        <span class="feature-icon">&#x1F3E6;</span>
        <div class="feature-name">Bank Monitor</div>
        <div class="feature-desc">Rule-based transaction watchdog that applies velocity limits, amount thresholds, and beneficiary trust scores in real-time per episode.</div>
      </div>
      <div class="feature-card">
        <span class="feature-icon">&#x2696;&#xFE0F;</span>
        <div class="feature-name">Composable Reward</div>
        <div class="feature-desc">8-leaf rubric with independently tuneable weights. Reward hacking is made visible: toggle v1 vs v2 profiles on the same analyzer output.</div>
      </div>
    </div>
  </section>

  <hr class="divider">

  <!-- ── Endpoints ── -->
  <section class="section">
    <div class="section-head">
      <span class="section-title">API endpoints</span>
    </div>
    <div class="endpoints-grid">
      <a class="endpoint" href="/demo/">
        <code>/demo/</code>
        <span>Interactive Gradio UI &mdash; replay curated episodes or score your own message.</span>
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
        <span>Pydantic model JSON schemas for action and observation.</span>
      </a>
      <a class="endpoint" href="/leaderboard">
        <code>GET /leaderboard</code>
        <span>Ranked submissions on chakravyuh-bench-v0.</span>
      </a>
      <a class="endpoint" href="/eval">
        <code>GET /eval</code>
        <span>v2 eval artifact &mdash; detection / FPR / F1 / per-difficulty breakdown.</span>
      </a>
      <a class="endpoint" href="/eval/bootstrap">
        <code>GET /eval/bootstrap</code>
        <span>10k-iteration percentile bootstrap 95% confidence intervals.</span>
      </a>
      <a class="endpoint" href="/docs#/diagnose/post_diagnose_diagnose_post">
        <code>POST /diagnose</code>
        <span>Score one message; get full 8-rubric AnalyzerRubricV2 decomposition.</span>
      </a>
      <a class="endpoint" href="/docs">
        <code>/docs &middot; /openapi.json</code>
        <span>Interactive API explorer + OpenAPI 3.1 schema.</span>
      </a>
    </div>
  </section>
</div>

<!-- ── Footer ── -->
<footer>
  <div class="footer-inner">
    <div>
      <div class="footer-brand">Chakravyuh</div>
      <div class="footer-copy">
        Open-source benchmark for Indian UPI fraud detection &middot;
        Entry to the Meta PyTorch OpenEnv Hackathon 2026, Bangalore.<br>
        Built by <strong>Ujjwal Pardeshi</strong> &amp; <strong>Omkar Kadam</strong> &middot;
        MIT (code) &middot; CC-BY-4.0 (dataset)
      </div>
    </div>
    <div class="footer-links">
      <a class="footer-link" href="https://huggingface.co/datasets/ujjwalpardeshi/chakravyuh-bench-v0">Dataset</a>
      <a class="footer-link" href="https://huggingface.co/ujjwalpardeshi/chakravyuh-analyzer-lora-v2">Analyzer LoRA</a>
      <a class="footer-link" href="https://huggingface.co/ujjwalpardeshi/chakravyuh-scammer-lora-phase1">Scammer LoRA</a>
      <a class="footer-link" href="https://github.com/UjjwalPardeshi/Chakravyuh">GitHub</a>
      <a class="footer-link" href="/docs">API</a>
    </div>
  </div>
</footer>

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
         margin: 0; padding: 48px 24px; background: #FFF3E6; color: #000; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 26px; margin: 0 0 6px; }
  .sub { color: rgba(0,0,0,0.62); margin: 0 0 24px; font-size: 14px; }
  figure { margin: 0 0 24px; }
  img { max-width: 100%; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  figcaption { font-size: 12px; color: rgba(0,0,0,0.55); margin-top: 6px; }
  .pill { display: inline-block; padding: 4px 10px; border-radius: 999px;
          background: rgba(46,125,50,0.10); color: #1b5e20; font-size: 12px;
          letter-spacing: 0.04em; text-transform: uppercase; }
  a { color: #381932; font-weight: 600; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 16px 0 24px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; margin: 16px 0 24px; }
  .card { padding: 14px; background: #fff; border-radius: 10px;
          box-shadow: 0 1px 4px rgba(0,0,0,0.06); font-size: 13px; line-height: 1.5; }
  .card.v1 { border-left: 3px solid #9C1B1B; }
  .card.v2 { border-left: 3px solid #381932; }
  .card.scammer { border-left: 3px solid #e8c97a; background: #381932; color: #fff; }
  .card .label { font-weight: 700; font-size: 12px; letter-spacing: 0.6px; text-transform: uppercase; }
  .card.v1 .label { color: #9C1B1B; }
  .card.v2 .label { color: #381932; }
  .card.scammer .label { color: #e8c97a; }
  .card .stat { font-weight: 700; }
  .card.v1 .stat { color: #9C1B1B; }
  .card.v2 .stat { color: #381932; }
  .card.scammer .stat { color: #e8c97a; }
  @media (max-width: 900px) { .grid-3 { grid-template-columns: 1fr; } }
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
  <div class="grid-3">
    <div class="card v1">
      <div class="label">v1 · Analyzer (reward-hacked)</div>
      detection 100 % · FPR <span class="stat">36 %</span> · F1 0.96<br>
      the model learned to flag everything.
    </div>
    <div class="card v2">
      <div class="label">v2 · Analyzer (principled retrain)</div>
      detection 99.3 % · FPR <span class="stat">6.7 %</span> · F1 0.99<br>
      same detection, FPR collapsed 5&times;.
    </div>
    <div class="card scammer">
      <div class="label">Scammer LoRA (0.5B + GRPO)</div>
      best-of-8 bypass <span class="stat">93.75 %</span> vs rules<br>
      beats 70B+ frontier LLMs at evasion.
    </div>
  </div>
  <p style="font-size:13px;color:rgba(0,0,0,0.72)">Once the demo is live, you'll see eight tabs: Replay, Live Q&amp;A, You vs Analyzer, 🎭 Trained Scammer, Adversary Lab, v1↔v2 toggle, <strong>🔴 Red-team it yourself</strong>, and Leaderboard.</p>
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
