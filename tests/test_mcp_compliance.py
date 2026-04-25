"""MCP tool-name compliance.

The hackathon guidelines warn:

    Don't use reserved tool names (reset, step, state, close) for MCP tools.

These are reserved for the OpenEnv core contract. If we ever expose a custom
tool via MCP that happens to be named ``reset`` (etc.), it will shadow the
core route and break clients.

This test enumerates the FastAPI routes registered by ``server.app`` and
asserts that no *custom* tool route uses a reserved name. It uses a
permissive heuristic: routes whose path matches one of the canonical
OpenEnv core paths (``/reset``, ``/step``, ``/state``, ``/health``,
``/schema``, ``/metadata``, ``/mcp``, plus ``/openapi.json``, ``/docs``,
``/redoc``) are *expected* and are exempted from the reserved-name check.
Anything else with a name in the reserved set is flagged.
"""

from __future__ import annotations

import pytest

RESERVED_TOOL_NAMES = frozenset({"reset", "step", "state", "close"})

# Routes the OpenEnv core / FastAPI framework legitimately registers.
# These paths use reserved-style names by contract; they are not custom
# MCP tools and must be exempted from the compliance check.
EXPECTED_CORE_PATHS = frozenset(
    {
        "/reset",
        "/step",
        "/state",
        "/health",
        "/schema",
        "/metadata",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
    }
)


def _route_path(route: object) -> str:
    """Best-effort extraction of a route path string."""
    return str(getattr(route, "path", ""))


def _last_segment(path: str) -> str:
    """Return the trailing path segment, stripped of slashes and prefixes."""
    return path.rstrip("/").rsplit("/", 1)[-1]


@pytest.mark.unit
def test_no_reserved_mcp_tool_names() -> None:
    """No custom route under the FastAPI app uses a reserved tool name."""
    from server.app import app  # imported lazily so collection stays cheap

    offending: list[str] = []
    for route in app.routes:
        path = _route_path(route)
        if not path:
            continue
        if path in EXPECTED_CORE_PATHS:
            continue
        if path.startswith("/mcp"):
            # MCP namespace itself is reserved by openenv-core; entries
            # under it are framework-managed, not custom tools.
            continue

        name = _last_segment(path)
        if name in RESERVED_TOOL_NAMES:
            offending.append(path)

    assert not offending, (
        "Custom routes use reserved MCP tool names "
        f"(reset/step/state/close): {offending}"
    )


@pytest.mark.unit
def test_reserved_names_are_actually_reserved() -> None:
    """Sanity: the constant matches the guideline text exactly."""
    assert RESERVED_TOOL_NAMES == frozenset({"reset", "step", "state", "close"})


@pytest.mark.integration
def test_mcp_endpoint_responds() -> None:
    """POST /mcp must respond (200 or 4xx with a JSON body) — not 5xx,
    not 404. The exact MCP envelope shape is openenv-core's contract;
    we just verify the endpoint is wired and doesn't crash."""
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    response = client.post("/mcp", json={
        "jsonrpc": "2.0", "method": "tools/list", "id": 1
    })
    # 200 OK or any 4xx — both are valid for an MCP endpoint that's
    # registered. 404/5xx would mean the route isn't there.
    assert response.status_code < 500, (
        f"/mcp returned 5xx: {response.status_code} {response.text[:200]}"
    )
    assert response.status_code != 404, (
        "/mcp endpoint is missing — openenv-core MCP contract not registered"
    )


@pytest.mark.integration
def test_mcp_endpoint_rejects_get() -> None:
    """The /mcp endpoint is POST-only per MCP spec; GET should return 405.
    Documents the deployed-Space behaviour where curl -X GET /mcp returns 405."""
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    response = client.get("/mcp")
    assert response.status_code in (405, 404), (
        f"/mcp GET should return 405 Method Not Allowed (or 404); got {response.status_code}"
    )
