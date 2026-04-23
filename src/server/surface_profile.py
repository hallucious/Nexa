from __future__ import annotations

import os
from typing import Iterable, Sequence

from fastapi import FastAPI
from starlette.routing import BaseRoute

P0_SLICE_PATHS = frozenset(
    {
        "/healthz",
        "/readyz",
        "/api/workspaces",
        "/api/workspaces/{workspace_id}",
        "/api/runs",
        "/api/runs/{run_id}",
        "/api/runs/{run_id}/result",
        "/api/runs/{run_id}/trace",
    }
)


def current_surface_profile() -> str:
    return os.environ.get("NEXA_SURFACE_PROFILE", "full").strip().lower()


def filter_routes(routes: Sequence[BaseRoute], *, profile: str | None = None) -> list[BaseRoute]:
    """Return a filtered route list for the active surface profile."""
    selected_profile = (profile or current_surface_profile()).strip().lower()
    if selected_profile == "full":
        return list(routes)
    if selected_profile == "p0_slice":
        return [route for route in routes if getattr(route, "path", None) in P0_SLICE_PATHS]
    raise RuntimeError(f"Unknown NEXA_SURFACE_PROFILE: {selected_profile!r}")


def apply_surface_profile(app: FastAPI, *, profile: str | None = None) -> FastAPI:
    app.router.routes[:] = filter_routes(app.router.routes, profile=profile)
    return app
