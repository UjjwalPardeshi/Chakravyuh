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
        eval-v2 bootstrap smoke-test link-check link-check-http clean

help:
	@echo "Chakravyuh make targets:"
	@echo "  install          Install repo + LLM + eval extras"
	@echo "  test             Run pytest (286 collected; 284 pass + 2 skip)"
	@echo "  smoke-test       In-process env reset+step smoke test (~5s, no GPU)"
	@echo "  link-check       Check every local README link / asset path resolves"
	@echo "  link-check-http  HEAD-probe every http(s) README link (allowed-fail; external)"
	@echo "  lint             Run ruff lint (no auto-fix)"
	@echo "  format           Run black + ruff --fix"
	@echo "  eval-v2          Re-run v2 evaluation against the bench (~10 min CPU cached, ~2-4h fresh GPU)"
	@echo "  bootstrap        Compute 10k-iteration bootstrap CIs from the eval (~1 min CPU)"
	@echo "  reproduce        eval-v2 + bootstrap (numbers within 0.5pp of README; set CHAKRAVYUH_SKIP_INFERENCE=1 to use cached scores)"
	@echo "  clean            Remove pyc / pycache / build artifacts"

install:
	$(PIP) install -e '.[llm,eval]'

test:
	$(PYTHON) -m pytest tests/ -v

smoke-test:
	$(PYTHON) scripts/smoke_test.py

link-check:
	@echo "Checking local file references in README.md..."
	@missing=0; \
	for path in $$(grep -oE '\]\([^)]+\)' README.md | sed -E 's/\]\(([^)]+)\).*/\1/' | grep -v '^http' | grep -v '^#' | grep -v '^mailto:' | cut -d'#' -f1); do \
	    [ -e "$$path" ] || { echo "BROKEN: $$path"; missing=$$((missing+1)); }; \
	done; \
	if [ "$$missing" -eq 0 ]; then echo "All local README links resolve."; else echo "$$missing broken link(s)."; exit 1; fi

# Best-effort external link probe. HEAD requests with a short timeout; we accept
# 2xx, 301/302 redirects, and 403 (some hosts block bots — newsmeter, pib, etc.)
# but flag 404/410/500. Skips localhost URLs and URLs containing shell glue
# (` ` or `&&`) which are illustrative command snippets, not real links. This
# target is allowed to fail in CI because external availability is flaky.
link-check-http:
	@echo "HEAD-probing http(s) links in README.md..."
	@bad=0; checked=0; \
	urls=$$(grep -oE 'https?://[^)[:space:]]+' README.md | sed -E 's/[`",]+$$//' | sort -u | grep -v 'localhost' | grep -v ' ' | grep -v '&&'); \
	for url in $$urls; do \
	    checked=$$((checked+1)); \
	    code=$$(curl -sS -L --max-time 8 -o /dev/null -w '%{http_code}' -A 'Chakravyuh-LinkCheck/1.0' -I "$$url" 2>/dev/null || echo 000); \
	    case "$$code" in \
	        2*|301|302|307|308|401|403|405|406|429) ;; \
	        *) echo "BROKEN[$$code]: $$url"; bad=$$((bad+1)) ;; \
	    esac; \
	done; \
	echo "Probed $$checked URL(s); $$bad failure(s)."; \
	if [ "$$bad" -ne 0 ]; then exit 1; fi

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
