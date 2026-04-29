from __future__ import annotations

import inspect

from src.server.fastapi_binding import FastApiRouteBindings, create_fastapi_app
from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.fastapi_route_registry import build_fastapi_router


def test_fastapi_binding_build_router_delegates_to_route_registry() -> None:
    source = inspect.getsource(FastApiRouteBindings.build_router)

    assert "build_fastapi_router" in source
    assert "@router.get" not in source
    assert "@router.post" not in source


def test_fastapi_route_registry_owns_route_decorators() -> None:
    source = inspect.getsource(build_fastapi_router)

    assert "@router.get" in source
    assert "@router.post" in source
    assert source.count("@router.") >= 100


def test_create_fastapi_app_still_registers_core_routes_after_split() -> None:
    app = create_fastapi_app(dependencies=FastApiRouteDependencies())
    paths = {route.path for route in app.routes}

    assert "/api/runs" in paths
    assert "/api/workspaces" in paths
    assert "/app" in paths
    assert "/app/workspaces/{workspace_id}" in paths
