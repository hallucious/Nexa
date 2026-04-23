from __future__ import annotations

import os

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from src.server.asgi import build_application
from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.health_routes import build_health_router
from src.server.p0_configuration import _validate_p0_configuration
from src.server.surface_profile import apply_surface_profile, filter_routes


@pytest.mark.parametrize(
    ("idempotency_window_s", "max_run_duration_s", "should_raise"),
    [
        (86400, 3600, False),
        (3600, 3600, True),
        (1800, 3600, True),
    ],
)
def test_validate_p0_configuration_enforces_window(idempotency_window_s: int, max_run_duration_s: int, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(RuntimeError):
            _validate_p0_configuration(idempotency_window_s, max_run_duration_s)
    else:
        _validate_p0_configuration(idempotency_window_s, max_run_duration_s)


def _build_route_probe_app() -> FastAPI:
    app = FastAPI()
    router = APIRouter()

    @router.get("/healthz")
    async def healthz():
        return {"ok": True}

    @router.get("/readyz")
    async def readyz():
        return {"ok": True}

    @router.get("/api/workspaces")
    async def list_workspaces():
        return {"items": []}

    @router.get("/api/workspaces/{workspace_id}")
    async def get_workspace(workspace_id: str):
        return {"workspace_id": workspace_id}

    @router.get("/api/runs/{run_id}")
    async def get_run(run_id: str):
        return {"run_id": run_id}

    @router.get("/api/runs/{run_id}/result")
    async def get_run_result(run_id: str):
        return {"run_id": run_id, "result": True}

    @router.get("/api/runs/{run_id}/trace")
    async def get_run_trace(run_id: str):
        return {"run_id": run_id, "trace": []}

    @router.get("/api/not-in-slice")
    async def other():
        return {"other": True}

    app.include_router(router)
    return app


def test_apply_surface_profile_limits_routes_to_p0_slice() -> None:
    app = _build_route_probe_app()
    apply_surface_profile(app, profile="p0_slice")
    paths = {getattr(route, "path", None) for route in app.router.routes}
    assert "/healthz" in paths
    assert "/readyz" in paths
    assert "/api/workspaces" in paths
    assert "/api/not-in-slice" not in paths


def test_build_health_router_returns_503_when_any_check_is_not_ready() -> None:
    router = build_health_router(
        db_check=lambda: {"status": "ok", "ready": True},
        alembic_check=lambda: {"status": "out_of_date", "ready": False},
        provider_check=lambda: {"status": "ok", "ready": True},
    )
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/readyz")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["alembic"]["ready"] is False


def test_build_application_exposes_healthz_in_in_memory_mode() -> None:
    old_mode = os.environ.get("NEXA_DEPENDENCY_MODE")
    os.environ["NEXA_DEPENDENCY_MODE"] = "in_memory"
    try:
        app = build_application(dependencies=FastApiRouteDependencies(), surface_profile="p0_slice")
        client = TestClient(app)
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/public/plugins").status_code == 404
    finally:
        if old_mode is None:
            os.environ.pop("NEXA_DEPENDENCY_MODE", None)
        else:
            os.environ["NEXA_DEPENDENCY_MODE"] = old_mode
