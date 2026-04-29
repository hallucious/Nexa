from __future__ import annotations

from typing import Any, Mapping

from src.server.sentry_observability_runtime import (
    SentryCaptureResult,
    SentryInitializationResult,
    build_sentry_request_context,
    capture_sentry_exception_for_app,
    install_sentry_observability_on_app,
)


def install_fastapi_sentry_observability(app: Any, config: Any, *, sdk_module: Any | None = None) -> SentryInitializationResult:
    """Install Sentry observability state on a FastAPI-compatible app.

    This is intentionally a thin adapter over the generic app lifecycle helper.
    It keeps the FastAPI integration point small and testable, while the actual
    privacy scrubber remains centralized in ``sentry_observability_runtime``.
    """

    return install_sentry_observability_on_app(app, config, sdk_module=sdk_module)


def build_fastapi_sentry_exception_context(
    *,
    method: str,
    path: str,
    headers: Mapping[str, Any] | None = None,
    query_params: Mapping[str, Any] | None = None,
    request_id: str | None = None,
    session_claims: Mapping[str, Any] | None = None,
    status_code: int | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the privacy-safe context expected by FastAPI exception capture."""

    return build_sentry_request_context(
        method=method,
        path=path,
        headers=headers,
        query_params=query_params,
        request_id=request_id,
        session_claims=session_claims,
        status_code=status_code,
        extra=extra,
    )


def capture_fastapi_sentry_exception(
    *,
    app: Any,
    exc: BaseException,
    method: str,
    path: str,
    headers: Mapping[str, Any] | None = None,
    query_params: Mapping[str, Any] | None = None,
    request_id: str | None = None,
    session_claims: Mapping[str, Any] | None = None,
    status_code: int | None = 500,
    extra: Mapping[str, Any] | None = None,
    sdk_module: Any | None = None,
) -> SentryCaptureResult:
    """Capture a FastAPI edge exception with redacted request context.

    This helper is ready to be called from FastAPI middleware exception paths.
    It never raises, never sends raw request bodies, and never stores a DSN in
    app state.
    """

    context = build_fastapi_sentry_exception_context(
        method=method,
        path=path,
        headers=headers,
        query_params=query_params,
        request_id=request_id,
        session_claims=session_claims,
        status_code=status_code,
        extra=extra,
    )
    return capture_sentry_exception_for_app(
        app=app,
        exc=exc,
        context=context,
        sdk_module=sdk_module,
    )


__all__ = [
    "build_fastapi_sentry_exception_context",
    "capture_fastapi_sentry_exception",
    "install_fastapi_sentry_observability",
]
