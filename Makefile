# Chakravyuh — reproducibility + dev convenience targets
#
# Designed so a fresh clone can produce every README claim with one command.
# All targets assume Python 3.11+ and a fresh virtualenv.

PYTHON ?= python
PIP    ?= pip
ADAPTER ?= ujjwalpardeshi/chakravyuh-analyzer-lora-v2
BENCH  ?= data/chakravyuh-bench-v0/scenarios.jsonl
SEED   ?= 42

.PHONY: help install test lint format reproduce \
        eval-v2 bootstrap clean

help:
	@echo "Chakravyuh make targets:"
	@echo "  install          Install repo + LLM + eval extras"
	@echo "  test             Run pytest (199 tests expected)"
	@echo "  lint             Run ruff lint (no auto-fix)"
	@echo "  format           Run black + ruff --fix"
	@echo "  eval-v2          Re-run v2 evaluation against the bench"
	@echo "  bootstrap        Compute 10k-iteration bootstrap CIs from the eval"
	@echo "  reproduce        eval-v2 + bootstrap (numbers within 0.5pp of README)"
	@echo "  clean            Remove pyc / pycache / build artifacts"

install:
	$(PIP) install -e '.[llm,eval]'

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check chakravyuh_env/ training/ eval/ server/ tests/

format:
	$(PYTHON) -m black chakravyuh_env/ training/ eval/ server/ tests/
	$(PYTHON) -m ruff check --fix chakravyuh_env/ training/ eval/ server/ tests/

eval-v2:
	$(PYTHON) eval/mode_c_real_cases.py \
	  --model-id $(ADAPTER) \
	  --bench $(BENCH) \
	  --seed $(SEED) \
	  --output logs/eval_v2_reproduce.json

bootstrap: eval-v2
	$(PYTHON) eval/bootstrap_ci.py \
	  --eval-file logs/eval_v2_reproduce.json \
	  --iterations 10000 \
	  --output logs/bootstrap_v2_reproduce.json

reproduce: install bootstrap
	@echo ""
	@echo "Reproduction complete. Compare these against README claims (target: within 0.5pp):"
	@echo "  - logs/eval_v2_reproduce.json     # detection, FPR, F1, per-difficulty"
	@echo "  - logs/bootstrap_v2_reproduce.json # 95% CI bands"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/
