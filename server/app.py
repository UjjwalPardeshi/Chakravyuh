"""FastAPI entrypoint for the Chakravyuh OpenEnv server.

Run locally:
    uvicorn server.app:app --host 0.0.0.0 --port 8000

Hugging Face Space / Docker:
    Referenced by ``openenv.yaml`` as ``app: server.app:app``.

Users connect to a running server via ``ChakravyuhEnvClient``
(see ``chakravyuh_env.openenv_client``) or any OpenEnv-compatible
HTTP/WebSocket client.
"""

from __future__ import annotations

import os

from openenv.core.env_server import create_app

from chakravyuh_env.openenv_environment import ChakravyuhOpenEnv
from chakravyuh_env.openenv_models import ChakravyuhAction, ChakravyuhObservation

# One factory call per concurrent session → fully isolated episodes.
max_concurrent = int(os.getenv("MAX_CONCURRENT_ENVS", "8"))

app = create_app(
    ChakravyuhOpenEnv,
    ChakravyuhAction,
    ChakravyuhObservation,
    env_name="chakravyuh_env",
    max_concurrent_envs=max_concurrent,
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
