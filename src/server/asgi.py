from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.server.dependency_factory import build_default_dependencies, build_default_readiness_checks
from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.health_routes import build_health_router
from src.server.p0_configuration import (
    _validate_p0_configuration,
    get_idempotency_window_s,
    get_max_run_duration_s,
)
from src.server.surface_profile import apply_surface_profile


_validate_p0_configuration(
    idempotency_window_s=get_idempotency_window_s(),
    max_run_duration_s=get_max_run_duration_s(),
)


def build_application(
    *,
    dependencies: FastApiRouteDependencies | None = None,
    config: FastApiBindingConfig | None = None,
    surface_profile: str | None = None,
) -> FastAPI:
    deps = dependencies or build_default_dependencies()
    app = create_fastapi_app(
        dependencies=deps,
        config=config or FastApiBindingConfig(title="Nexa API", version="0.1.0"),
    )
    checks = build_default_readiness_checks()
    app.include_router(
        build_health_router(
            db_check=checks.db_check,
            alembic_check=checks.alembic_check,
            provider_check=checks.provider_check,
        )
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in os.environ.get("NEXA_CORS_ORIGINS", "*").split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return apply_surface_profile(app, profile=surface_profile)


app = build_application()
