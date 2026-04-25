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
