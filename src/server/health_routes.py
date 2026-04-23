from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from fastapi import APIRouter
from fastapi.responses import JSONResponse


ReadinessCheck = Callable[[], Mapping[str, Any]]


@dataclass(frozen=True)
class ReadinessChecks:
    db_check: ReadinessCheck
    alembic_check: ReadinessCheck
    provider_check: ReadinessCheck


def _normalize_check_result(name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.setdefault("name", name)
    raw_ready = result.get("ready")
    if raw_ready is None:
        status_value = str(result.get("status") or "unknown").strip().lower()
        result["ready"] = status_value in {"ok", "ready", "pass", "passing"}
    else:
        result["ready"] = bool(raw_ready)
    result.setdefault("status", "ok" if result["ready"] else "not_ready")
    return result


def build_health_router(
    *,
    db_check: ReadinessCheck,
    alembic_check: ReadinessCheck,
    provider_check: ReadinessCheck,
) -> APIRouter:
    router = APIRouter()

    @router.get("/healthz")
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @router.get("/readyz")
    async def readyz() -> JSONResponse:
        checks = {
            "db": _normalize_check_result("db", db_check()),
            "alembic": _normalize_check_result("alembic", alembic_check()),
            "provider": _normalize_check_result("provider", provider_check()),
        }
        all_ready = all(bool(item.get("ready")) for item in checks.values())
        status_code = 200 if all_ready else 503
        body = {
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
        }
        return JSONResponse(body, status_code=status_code)

    return router
