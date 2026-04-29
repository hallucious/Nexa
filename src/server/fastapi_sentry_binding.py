from __future__ import annotations

from typing import Any, Callable, Mapping

from src.server.sentry_observability_runtime import (
    SentryCaptureResult,
    SentryInitializationResult,
    build_sentry_request_context,
    capture_sentry_exception_for_app,
    install_sentry_observability_on_app,
)


FASTAPI_SENTRY_EXCEPTION_REASON = "fastapi_sentry_exception_captured"


FastApiSentryResponseFactory = Callable[..., Any]
FastApiSessionClaimsResolver = Callable[[Any], Mapping[str, Any] | None]


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


def _default_request_id(request: Any) -> str | None:
    headers = getattr(request, "headers", {})
    request_id = None
    if hasattr(headers, "get"):
        request_id = headers.get("x-nexa-request-id") or headers.get("x-request-id")
    text = str(request_id or "").strip()
    return text or None


def _default_exception_response(*, request_id: str | None = None, reason: str = FASTAPI_SENTRY_EXCEPTION_REASON, status_code: int = 500, capture_result: SentryCaptureResult | None = None):
    from fastapi.responses import JSONResponse

    payload: dict[str, Any] = {"status": "error", "reason": reason}
    if request_id:
        payload["request_id"] = request_id
    if capture_result is not None:
        payload["observability"] = capture_result.as_payload()
    return JSONResponse(status_code=status_code, content=payload, headers={"x-nexa-request-id": request_id} if request_id else None)


def install_fastapi_sentry_exception_middleware(
    app: Any,
    config: Any,
    *,
    sdk_module: Any | None = None,
    session_claims_resolver: FastApiSessionClaimsResolver | None = None,
    response_factory: FastApiSentryResponseFactory | None = None,
) -> SentryInitializationResult:
    """Install Sentry state and a privacy-safe FastAPI exception middleware.

    The middleware is intentionally small and self-contained so ``build_app()``
    can wire it with one call. It captures only scrubbed request context, never
    stores DSN in app state, and never lets Sentry failures become user-visible
    runtime failures.
    """

    result = install_fastapi_sentry_observability(app, config, sdk_module=sdk_module)
    make_response = response_factory or _default_exception_response

    @app.middleware("http")
    async def fastapi_sentry_exception_middleware(request, call_next):
        request_id = _default_request_id(request)
        try:
            return await call_next(request)
        except Exception as exc:
            session_claims = None
            if session_claims_resolver is not None:
                try:
                    session_claims = session_claims_resolver(request)
                except Exception:
                    session_claims = None
            capture_result = capture_fastapi_sentry_exception(
                app=app,
                sdk_module=sdk_module,
                exc=exc,
                method=str(getattr(request, "method", "")),
                path=str(getattr(getattr(request, "url", None), "path", "")),
                headers=getattr(request, "headers", {}),
                query_params=dict(getattr(request, "query_params", {})),
                request_id=request_id,
                session_claims=session_claims if isinstance(session_claims, Mapping) else None,
                status_code=500,
            )
            return make_response(
                request_id=request_id,
                reason=FASTAPI_SENTRY_EXCEPTION_REASON,
                status_code=500,
                capture_result=capture_result,
            )

    return result


__all__ = [
    "FASTAPI_SENTRY_EXCEPTION_REASON",
    "FastApiSentryResponseFactory",
    "FastApiSessionClaimsResolver",
    "build_fastapi_sentry_exception_context",
    "capture_fastapi_sentry_exception",
    "install_fastapi_sentry_exception_middleware",
    "install_fastapi_sentry_observability",
]
