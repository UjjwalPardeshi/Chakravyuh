"""Semantic leakage audit between training corpus and bench-v0.

Measures cosine similarity (MiniLM-L6) between every bench scenario and its
nearest neighbor in the training corpus. This is the single most direct test
of whether v2's headline numbers are inflated by memorization vs. real
generalization.

Method:
  1. Load all training texts (canonical + augmented + paraphrase + regional +
     multiturn + scam_novel + benign + benign_aug) — same set GRPO uses, before
     the substring soft-leakage filter.
  2. Load all bench scenarios from data/chakravyuh-bench-v0/scenarios.jsonl.
  3. Embed both with MiniLM-L6.
  4. For each bench scenario, compute cosine similarity to its nearest training
     neighbor.
  5. Output:
     - logs/semantic_leakage_audit.json — full per-scenario nearest-neighbor records
     - plots/chakravyuh_plots/semantic_leakage_histogram.png — distribution
     - Print summary: mean, median, %>0.85, %>0.95, %<0.50

Interpretation guide:
  - %>0.85 below 10%      → strong generalization claim defensible
  - %>0.85 between 10-30% → mixed; novel split is the real claim
  - %>0.85 above 30%      → most bench is memorization; need v3 retrain on
                            held-out template families

Usage:
  python eval/semantic_leakage_audit.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TRAINING_TEMPLATE_FILES = [
    REPO_ROOT / "chakravyuh_env" / "scammer_templates.json",
    REPO_ROOT / "chakravyuh_env" / "augmented_templates.json",
    REPO_ROOT / "chakravyuh_env" / "paraphrase_templates.json",
    REPO_ROOT / "chakravyuh_env" / "regional_templates.json",
    REPO_ROOT / "chakravyuh_env" / "multiturn_templates.json",
    REPO_ROOT / "chakravyuh_env" / "scam_novel.json",
    REPO_ROOT / "chakravyuh_env" / "benign_templates.json",
    REPO_ROOT / "chakravyuh_env" / "benign_augmented.json",
    REPO_ROOT / "chakravyuh_env" / "benign_augmented_v2.json",
]

BENCH_FILE = REPO_ROOT / "data" / "chakravyuh-bench-v0" / "scenarios.jsonl"
OUT_JSON = REPO_ROOT / "logs" / "semantic_leakage_audit.json"
OUT_PNG = REPO_ROOT / "plots" / "chakravyuh_plots" / "semantic_leakage_histogram.png"


def _load_training_texts() -> list[dict]:
    """Return list of {text, source_file, template_id}."""
    records: list[dict] = []
    for path in TRAINING_TEMPLATE_FILES:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("templates") or data.get("scenarios") or list(data.values())
        if not isinstance(data, list):
            continue
        for i, t in enumerate(data):
            if not isinstance(t, dict):
                continue
            for field in ("opener", "escalation", "text", "message", "body"):
                v = t.get(field)
                if isinstance(v, str) and len(v.strip()) >= 20:
                    records.append({
                        "text": v.strip(),
                        "source_file": path.name,
                        "template_id": t.get("id") or f"{path.stem}_{i}",
                        "field": field,
                    })
    return records


def _load_bench_texts() -> list[dict]:
    """Return list of {scenario_id, text, is_scam, difficulty, novel}."""
    records: list[dict] = []
    if not BENCH_FILE.exists():
        return records
    with BENCH_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            scen = json.loads(line)
            scammer_texts = [
                step.get("text", "")
                for step in scen.get("attack_sequence", [])
                if step.get("sender") == "scammer" and step.get("text")
            ]
            joined = " ".join(scammer_texts).strip()
            if len(joined) < 10:
                continue
            gt = scen.get("ground_truth", {})
            src = scen.get("source", {})
            is_novel = (
                src.get("category") == "novel_post_2024"
                or gt.get("difficulty") == "novel"
                or "2024" in str(src.get("date_range", ""))
                or "2025" in str(src.get("date_range", ""))
            )
            records.append({
                "scenario_id": scen.get("id"),
                "text": joined,
                "is_scam": bool(gt.get("is_scam", False)),
                "difficulty": gt.get("difficulty", "unknown"),
                "novel": is_novel,
            })
    return records


def main() -> int:
    print("Loading training corpus...")
    train_records = _load_training_texts()
    print(f"  {len(train_records)} training texts loaded")

    print("Loading bench corpus...")
    bench_records = _load_bench_texts()
    print(f"  {len(bench_records)} bench scenarios loaded")

    if not train_records or not bench_records:
        print("ERROR: missing corpus data", file=sys.stderr)
        return 1

    print("Embedding with MiniLM-L6 (this loads the model)...")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: pip install sentence-transformers", file=sys.stderr)
        return 1
    import numpy as np

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    train_texts = [r["text"] for r in train_records]
    bench_texts = [r["text"] for r in bench_records]

    print(f"  embedding {len(train_texts)} training texts...")
    train_emb = model.encode(train_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    print(f"  embedding {len(bench_texts)} bench texts...")
    bench_emb = model.encode(bench_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)

    # Cosine sim is dot product because vectors are L2-normalized.
    sim_matrix = bench_emb @ train_emb.T  # (n_bench, n_train)

    print("Computing per-bench nearest neighbors...")
    nearest_idx = sim_matrix.argmax(axis=1)
    nearest_sim = sim_matrix.max(axis=1)

    per_scenario = []
    for i, bench in enumerate(bench_records):
        nn = train_records[int(nearest_idx[i])]
        per_scenario.append({
            "scenario_id": bench["scenario_id"],
            "is_scam": bench["is_scam"],
            "difficulty": bench["difficulty"],
            "novel": bench["novel"],
            "max_cosine_to_training": float(nearest_sim[i]),
            "nearest_template_id": nn["template_id"],
            "nearest_source_file": nn["source_file"],
            "bench_text_preview": bench["text"][:100],
            "nearest_train_text_preview": nn["text"][:100],
        })

    sims = np.array([p["max_cosine_to_training"] for p in per_scenario])
    sims_scams = np.array([p["max_cosine_to_training"] for p in per_scenario if p["is_scam"]])
    sims_benign = np.array([p["max_cosine_to_training"] for p in per_scenario if not p["is_scam"]])
    sims_novel = np.array([p["max_cosine_to_training"] for p in per_scenario if p["novel"]])
    sims_known = np.array([p["max_cosine_to_training"] for p in per_scenario if not p["novel"]])

    def _stats(arr: np.ndarray) -> dict:
        if len(arr) == 0:
            return {"n": 0}
        return {
            "n": int(len(arr)),
            "mean": float(arr.mean()),
            "median": float(np.median(arr)),
            "p25": float(np.percentile(arr, 25)),
            "p75": float(np.percentile(arr, 75)),
            "min": float(arr.min()),
            "max": float(arr.max()),
            "pct_above_0.95": float((arr > 0.95).mean()),
            "pct_above_0.85": float((arr > 0.85).mean()),
            "pct_above_0.70": float((arr > 0.70).mean()),
            "pct_below_0.50": float((arr < 0.50).mean()),
        }

    summary = {
        "_meta": {
            "method": "MiniLM-L6 cosine similarity, max-over-training-set per bench scenario",
            "n_training_texts": len(train_records),
            "n_bench_scenarios": len(bench_records),
            "training_files": [p.name for p in TRAINING_TEMPLATE_FILES if p.exists()],
            "bench_file": str(BENCH_FILE.relative_to(REPO_ROOT)),
        },
        "overall": _stats(sims),
        "scams_only": _stats(sims_scams),
        "benign_only": _stats(sims_benign),
        "novel_only": _stats(sims_novel),
        "known_only": _stats(sims_known),
        "leakage_clean_bench_subset": {
            "_definition": "scenarios with max cosine to training < 0.70",
            "n_total": int((sims < 0.70).sum()),
            "n_scams": int((sims_scams < 0.70).sum()),
            "n_benign": int((sims_benign < 0.70).sum()),
        },
        "interpretation": _interpret(_stats(sims)["pct_above_0.85"]),
        "per_scenario": per_scenario,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Wrote {OUT_JSON}")

    # Histogram plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(10, 6))
        bins = np.linspace(0, 1, 41)
        ax.hist(sims_scams, bins=bins, alpha=0.65, color="#cc4444", label=f"Scam scenarios (n={len(sims_scams)})", edgecolor="black", linewidth=0.4)
        ax.hist(sims_benign, bins=bins, alpha=0.65, color="#4477aa", label=f"Benign scenarios (n={len(sims_benign)})", edgecolor="black", linewidth=0.4)
        ax.axvline(0.85, linestyle="--", color="black", linewidth=1, alpha=0.6, label="High-similarity threshold (0.85)")
        ax.axvline(0.70, linestyle=":", color="gray", linewidth=1, alpha=0.6, label="Leakage-clean threshold (0.70)")
        ax.set_xlabel("Max cosine similarity to nearest training-corpus text (MiniLM-L6)")
        ax.set_ylabel("Count of bench scenarios")
        ax.set_title("Semantic leakage audit: bench-v0 vs training corpus")
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT_PNG, dpi=140, bbox_inches="tight")
        plt.close()
        print(f"  Wrote {OUT_PNG}")
    except ImportError:
        print("  matplotlib not available; skipping plot")

    # Print summary
    print("\n" + "=" * 70)
    print("SEMANTIC LEAKAGE AUDIT — SUMMARY")
    print("=" * 70)
    print(f"\nOverall (n={len(sims)}):")
    for k, v in _stats(sims).items():
        if k == "n":
            continue
        if "pct" in k:
            print(f"  {k:25s} = {v:.1%}")
        else:
            print(f"  {k:25s} = {v:.4f}")
    print(f"\nNovel split only (n={len(sims_novel)}): mean cosine = {sims_novel.mean():.4f}")
    print(f"Known split only (n={len(sims_known)}): mean cosine = {sims_known.mean():.4f}")
    print(f"\nInterpretation: {summary['interpretation']}")
    print(f"\nLeakage-clean subset (cosine < 0.70):")
    print(f"  scams = {summary['leakage_clean_bench_subset']['n_scams']} / {len(sims_scams)}")
    print(f"  benign = {summary['leakage_clean_bench_subset']['n_benign']} / {len(sims_benign)}")
    return 0


def _interpret(pct_above_85: float) -> str:
    if pct_above_85 < 0.10:
        return (
            "STRONG generalization claim defensible. <10% of bench has high cosine "
            "similarity to training; v2's 99.3% detection mostly reflects real learning."
        )
    if pct_above_85 < 0.30:
        return (
            "MIXED. 10–30% of bench has high cosine similarity to training. The novel "
            "post-2024 split (97.1%) is the real generalization claim; the 100% on "
            "easy/medium/hard is partly memorization."
        )
    return (
        "SUBSTANTIAL semantic overlap. >30% of bench is highly similar to training. "
        "The 100% in-distribution numbers are heavily memorization-driven. The honest "
        "claim is the leakage-clean subset performance + novel split (97.1%). v3 "
        "must retrain on held-out template families."
    )


if __name__ == "__main__":
    sys.exit(main())
