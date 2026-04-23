from __future__ import annotations

import os
from typing import Any, Mapping

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.health_routes import ReadinessChecks


def _not_implemented_postgres_mode() -> RuntimeError:
    return RuntimeError(
        "NEXA_DEPENDENCY_MODE=postgres is reserved for the P0 Postgres dependency "
        "factory, which is not implemented in this batch yet. Use in_memory for now."
    )


def build_default_dependencies() -> FastApiRouteDependencies:
    mode = os.environ.get("NEXA_DEPENDENCY_MODE", "in_memory").strip().lower()
    if mode == "in_memory":
        return FastApiRouteDependencies()
    if mode == "postgres":
        try:
            from src.server.pg.dependencies_factory import build_postgres_dependencies  # type: ignore
            from src.server.pg.engine import create_async_engine_from_env  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - exercised by tests through RuntimeError branch
            raise _not_implemented_postgres_mode() from exc
        engine = create_async_engine_from_env()
        return build_postgres_dependencies(engine)
    raise RuntimeError(f"Unknown NEXA_DEPENDENCY_MODE: {mode!r}")


def build_default_readiness_checks() -> ReadinessChecks:
    mode = os.environ.get("NEXA_DEPENDENCY_MODE", "in_memory").strip().lower()

    if mode == "in_memory":
        return ReadinessChecks(
            db_check=lambda: {"status": "skipped", "ready": False, "reason": "in_memory_mode"},
            alembic_check=lambda: {"status": "skipped", "ready": False, "reason": "in_memory_mode"},
            provider_check=lambda: {"status": "skipped", "ready": False, "reason": "in_memory_mode"},
        )

    if mode == "postgres":
        raise _not_implemented_postgres_mode()

    raise RuntimeError(f"Unknown NEXA_DEPENDENCY_MODE: {mode!r}")
