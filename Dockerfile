# Dockerfile for the Chakravyuh OpenEnv server.
#
# Designed for Hugging Face Spaces (type: docker). Includes the [demo]
# extra so the Gradio demo UI is mounted at /demo. Heavy LLM deps (torch,
# transformers, peft) live in [llm] and are still excluded from the
# runtime image — the demo uses the rule-based scripted analyzer which
# needs no GPU.

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the environment package from source with [demo] extra so Gradio
# is available for the /demo route. Base deps: openenv-core, fastapi,
# uvicorn, pydantic, numpy. [demo] adds gradio.
COPY pyproject.toml README.md /app/
COPY chakravyuh_env /app/chakravyuh_env
COPY server /app/server
RUN pip install --upgrade pip && pip install '.[demo]'

# ---- runtime stage ----

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH" \
    MAX_CONCURRENT_ENVS=8 \
    HOST=0.0.0.0 \
    PORT=8000

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

WORKDIR /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=5 \
    CMD python -c "import sys, urllib.request; \
r = urllib.request.urlopen('http://localhost:8000/health', timeout=3); \
sys.exit(0 if 200 <= r.status < 300 else 1)" || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
