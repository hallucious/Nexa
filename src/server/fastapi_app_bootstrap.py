from __future__ import annotations

from typing import Any, Callable, Mapping

from src.server.fastapi_binding_models import FastApiBindingConfig
from src.server.fastapi_sentry_binding import install_fastapi_sentry_exception_middleware


SessionClaimsResolver = Callable[[Any], Mapping[str, Any] | None]


def install_fastapi_app_observability_bootstrap(
    app: Any,
    config: FastApiBindingConfig,
    *,
    session_claims_resolver: SessionClaimsResolver | None = None,
) -> None:
    """Install app-level observability middleware for FastAPI bindings.

    This keeps FastApiRouteBindings.build_app() focused on app composition while
    moving Sentry/bootstrap-specific wiring into a narrow helper. The helper is
    intentionally best-effort: observability setup must not break app creation.
    """

    try:
        install_fastapi_sentry_exception_middleware(
            app,
            config,
            session_claims_resolver=session_claims_resolver,
        )
    except Exception:
        return


__all__ = ["install_fastapi_app_observability_bootstrap"]
