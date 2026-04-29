from __future__ import annotations

from typing import Any, Callable, Mapping

from src.server.fastapi_binding_models import FastApiBindingConfig
from src.server.fastapi_sentry_binding import capture_fastapi_sentry_exception, install_fastapi_sentry_observability
from src.server.sentry_observability_runtime import SentryCaptureResult


SessionClaimsResolver = Callable[[Any], Mapping[str, Any] | None]


def install_fastapi_app_observability_bootstrap(
    app: Any,
    config: FastApiBindingConfig,
    *,
    session_claims_resolver: SessionClaimsResolver | None = None,
) -> None:
    """Install app-level observability state for FastAPI bindings.

    This helper intentionally initializes/stores Sentry runtime posture only. It
    does not install a competing exception-response middleware; FastApiRouteBindings'
    edge middleware remains the canonical HTTP exception-response owner.
    """

    try:
        install_fastapi_sentry_observability(app, config)
    except Exception:
        return


def capture_fastapi_app_exception(
    *,
    app: Any,
    config: FastApiBindingConfig,
    exc: BaseException,
    method: str,
    path: str,
    headers: Mapping[str, Any] | None = None,
    query_params: Mapping[str, Any] | None = None,
    request_id: str | None = None,
    session_claims: Mapping[str, Any] | None = None,
    status_code: int | None = 500,
) -> SentryCaptureResult | None:
    """Best-effort Sentry capture from the canonical FastAPI edge exception path."""

    try:
        return capture_fastapi_sentry_exception(
            app=app,
            exc=exc,
            method=method,
            path=path,
            headers=headers,
            query_params=query_params,
            request_id=request_id,
            session_claims=session_claims,
            status_code=status_code,
        )
    except Exception:
        return None


__all__ = [
    "capture_fastapi_app_exception",
    "install_fastapi_app_observability_bootstrap",
]
