from __future__ import annotations

import os
from typing import Any, Mapping

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.health_routes import ReadinessChecks
from src.server.pg.dependencies_factory import build_postgres_dependencies
from src.server.pg.engine import get_postgres_engine
from src.server.pg.readiness import build_postgres_readiness_checks


def build_default_dependencies() -> FastApiRouteDependencies:
    mode = os.environ.get("NEXA_DEPENDENCY_MODE", "in_memory").strip().lower()
    if mode == "in_memory":
        return FastApiRouteDependencies()
    if mode == "postgres":
        engine = get_postgres_engine()
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
        engine = get_postgres_engine()
        return build_postgres_readiness_checks(engine)

    raise RuntimeError(f"Unknown NEXA_DEPENDENCY_MODE: {mode!r}")
