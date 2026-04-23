# Dockerfile for the Chakravyuh OpenEnv server.
#
# Designed for Hugging Face Spaces (type: docker). The runtime image
# only needs the lightweight core deps — torch / transformers etc. live
# in the [llm] extra and are not required to serve the environment.

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the environment package from source — installs only the
# minimal runtime deps (openenv-core, fastapi, uvicorn, pydantic, numpy).
COPY pyproject.toml README.md /app/
COPY chakravyuh_env /app/chakravyuh_env
COPY server /app/server
RUN pip install --upgrade pip && pip install .

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

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
