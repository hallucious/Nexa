from __future__ import annotations

import time
from typing import Any, Callable, Mapping
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from src.server.edge_observability_runtime import (
    edge_exception_event,
    edge_exception_payload,
    edge_request_completed_event,
    emit_edge_observation,
    request_observation_context,
)
from src.server.edge_rate_limit_runtime import build_edge_rate_limiter
from src.server.edge_security_runtime import (
    apply_security_headers,
    cors_headers,
    is_cors_preflight,
    path_is_rate_limited,
    rate_limit_identity,
    rate_limited_payload,
)
from src.server.fastapi_app_bootstrap import capture_fastapi_app_exception
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.otel_observability_runtime import build_otel_exception_event, build_otel_http_server_attributes
from src.server.safe_http_logging_runtime import emit_http_access_log

SessionClaimsResolver = Callable[[Request], Mapping[str, Any] | None]

OTEL_HTTP_SERVER_EVENT_TYPE = "otel.http.server"


def _resolve_redis_client(dependencies: FastApiRouteDependencies) -> Any | None:
    provider = getattr(dependencies, "edge_rate_limit_redis_client_provider", None)
    if provider is None:
        return None
    try:
        return provider()
    except Exception:
        return None


def _route_template(request: Request) -> str | None:
    scope = getattr(request, "scope", {})
    route = scope.get("route") if isinstance(scope, Mapping) else None
    template = getattr(route, "path", None)
    text = str(template or "").strip()
    return text or None


def _emit_http_access_log(
    *,
    dependencies: FastApiRouteDependencies,
    request: Request,
    request_id: str,
    status_code: int,
    started_at: float,
    extra: Mapping[str, Any] | None = None,
) -> None:
    writer = getattr(dependencies, "http_access_log_writer", None)
    if writer is None:
        return
    duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
    emit_http_access_log(
        writer,
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        duration_ms=duration_ms,
        request_id=request_id,
        route_template=_route_template(request),
        extra=extra,
    )


def _emit_otel_http_server_span(
    *,
    dependencies: FastApiRouteDependencies,
    config: FastApiBindingConfig,
    request: Request,
    request_id: str,
    status_code: int,
    started_at: float,
    session_claims: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
    exc: BaseException | None = None,
) -> None:
    """Emit a safe OTel HTTP server span projection.

    This function is SDK-independent. It emits only scrubbed attributes through
    an optional testable writer, so request/response bodies and credentials do
    not reach the projection boundary.
    """

    if not bool(getattr(config, "otel_enabled", False)):
        return
    writer = getattr(dependencies, "otel_span_writer", None)
    if writer is None:
        return
    duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
    span_extra: dict[str, Any] = {
        "nexa.edge_outcome": str((extra or {}).get("edge_outcome") or "completed"),
        "nexa.duration_ms": duration_ms,
        "nexa.otel_service_name": str(getattr(config, "otel_service_name", "nexa-server") or "nexa-server"),
        "nexa.otel_environment": str(getattr(config, "otel_environment", "local") or "local"),
    }
    if isinstance(extra, Mapping):
        for key, value in extra.items():
            span_extra.setdefault(str(key), value)
    attributes = build_otel_http_server_attributes(
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        request_id=request_id,
        headers=request.headers,
        query_params=dict(request.query_params),
        session_claims=session_claims,
        extra=span_extra,
    )
    event: dict[str, Any] = {
        "event_type": OTEL_HTTP_SERVER_EVENT_TYPE,
        "name": "http.server",
        "attributes": attributes,
    }
    if exc is not None:
        event["events"] = [build_otel_exception_event(exc=exc, attributes=attributes)]
    try:
        writer(event)
    except Exception:
        return


def register_fastapi_edge_middleware(
    *,
    app: Any,
    config: FastApiBindingConfig,
    dependencies: FastApiRouteDependencies,
    session_claims_resolver: SessionClaimsResolver,
) -> None:
    """Install Nexa's FastAPI edge middleware.

    This is the edge-layer half of the former ``FastApiRouteBindings.build_app``
    implementation. Keeping it here prevents ``fastapi_binding.py`` from owning
    route registration, app bootstrap, CORS, rate limiting, security headers,
    Sentry side-channel capture, and edge observation at the same time.
    """

    rate_limiter = build_edge_rate_limiter(
        backend=str(getattr(config, "rate_limit_backend", "memory") or "memory"),
        requests_per_window=config.rate_limit_requests_per_window,
        window_seconds=config.rate_limit_window_seconds,
        redis_client=_resolve_redis_client(dependencies),
        redis_key_prefix=str(getattr(config, "rate_limit_redis_key_prefix", "nexa:edge:rate-limit") or "nexa:edge:rate-limit"),
        redis_fail_open=bool(getattr(config, "rate_limit_redis_fail_open", True)),
        datastore_span_writer=(getattr(dependencies, "otel_span_writer", None) if bool(getattr(config, "otel_enabled", False)) else None),
    )

    @app.middleware("http")
    async def edge_security_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        request_id = str(request.headers.get("x-nexa-request-id") or request.headers.get("x-request-id") or uuid4().hex)
        session_claims = session_claims_resolver(request)
        session_claims_map = dict(session_claims) if isinstance(session_claims, Mapping) else None
        request_context = request_observation_context(
            method=request.method,
            path=request.url.path,
            headers=request.headers,
            query_params=dict(request.query_params),
            session_claims=session_claims_map,
            request_id=request_id,
        )
        cors_header_values = cors_headers(
            origin=request.headers.get("origin"),
            allowed_origins=config.cors_allowed_origins,
            allowed_methods=config.cors_allowed_methods,
            allowed_headers=config.cors_allowed_headers,
            max_age_seconds=config.cors_max_age_seconds,
            requested_method=request.headers.get("access-control-request-method"),
            requested_headers=request.headers.get("access-control-request-headers"),
        )
        if is_cors_preflight(method=request.method, headers=request.headers):
            response = Response(status_code=204 if cors_header_values else 403)
            response.headers["x-nexa-request-id"] = request_id
            for key, value in cors_header_values.items():
                response.headers[key] = value
            if config.security_headers_enabled:
                apply_security_headers(response.headers)
            if config.edge_observability_enabled:
                emit_edge_observation(
                    dependencies.edge_observation_writer,
                    edge_request_completed_event(request_context=request_context, status_code=response.status_code),
                )
            extra = {"edge_outcome": "cors_preflight"}
            _emit_http_access_log(
                dependencies=dependencies,
                request=request,
                request_id=request_id,
                status_code=response.status_code,
                started_at=started_at,
                extra=extra,
            )
            _emit_otel_http_server_span(
                dependencies=dependencies,
                config=config,
                request=request,
                request_id=request_id,
                status_code=response.status_code,
                started_at=started_at,
                session_claims=session_claims_map,
                extra=extra,
            )
            return response

        if config.rate_limit_enabled and path_is_rate_limited(
            request.url.path,
            config.rate_limit_path_prefixes,
        ):
            client_host = request.client.host if request.client is not None else None
            rate_limit_key = rate_limit_identity(
                method=request.method,
                path=request.url.path,
                client_host=client_host,
                session_claims=session_claims_map,
            )
            allowed, retry_after = rate_limiter.record(rate_limit_key)
            if not allowed:
                response = JSONResponse(
                    status_code=429,
                    content=rate_limited_payload(),
                    headers={"retry-after": str(retry_after), "x-nexa-request-id": request_id},
                )
                for key, value in cors_header_values.items():
                    response.headers[key] = value
                if config.security_headers_enabled:
                    apply_security_headers(response.headers)
                if config.edge_observability_enabled:
                    emit_edge_observation(
                        dependencies.edge_observation_writer,
                        edge_request_completed_event(request_context=request_context, status_code=response.status_code),
                    )
                extra = {"edge_outcome": "rate_limited"}
                _emit_http_access_log(
                    dependencies=dependencies,
                    request=request,
                    request_id=request_id,
                    status_code=response.status_code,
                    started_at=started_at,
                    extra=extra,
                )
                _emit_otel_http_server_span(
                    dependencies=dependencies,
                    config=config,
                    request=request,
                    request_id=request_id,
                    status_code=response.status_code,
                    started_at=started_at,
                    session_claims=session_claims_map,
                    extra=extra,
                )
                return response

        direct_projection_emitted = False
        try:
            response = await call_next(request)
        except Exception as exc:
            if config.edge_observability_enabled and config.edge_exception_capture_enabled:
                capture_fastapi_app_exception(
                    app=app,
                    config=config,
                    exc=exc,
                    method=request.method,
                    path=request.url.path,
                    headers=request.headers,
                    query_params=dict(request.query_params),
                    request_id=request_id,
                    session_claims=session_claims_map,
                    status_code=500,
                )
                emit_edge_observation(
                    dependencies.edge_observation_writer,
                    edge_exception_event(request_context=request_context, exc=exc),
                )
                response = JSONResponse(
                    status_code=500,
                    content=edge_exception_payload(request_id=request_id),
                    headers={"x-nexa-request-id": request_id},
                )
                extra = {"edge_outcome": "exception"}
                _emit_http_access_log(
                    dependencies=dependencies,
                    request=request,
                    request_id=request_id,
                    status_code=response.status_code,
                    started_at=started_at,
                    extra=extra,
                )
                _emit_otel_http_server_span(
                    dependencies=dependencies,
                    config=config,
                    request=request,
                    request_id=request_id,
                    status_code=response.status_code,
                    started_at=started_at,
                    session_claims=session_claims_map,
                    extra=extra,
                    exc=exc,
                )
                direct_projection_emitted = True
            else:
                raise
        response.headers["x-nexa-request-id"] = request_id
        for key, value in cors_header_values.items():
            response.headers[key] = value
        if config.security_headers_enabled:
            apply_security_headers(response.headers)
        if config.edge_observability_enabled:
            emit_edge_observation(
                dependencies.edge_observation_writer,
                edge_request_completed_event(request_context=request_context, status_code=response.status_code),
            )
        if not direct_projection_emitted:
            extra = {"edge_outcome": "completed"}
            _emit_http_access_log(
                dependencies=dependencies,
                request=request,
                request_id=request_id,
                status_code=response.status_code,
                started_at=started_at,
                extra=extra,
            )
            _emit_otel_http_server_span(
                dependencies=dependencies,
                config=config,
                request=request,
                request_id=request_id,
                status_code=response.status_code,
                started_at=started_at,
                session_claims=session_claims_map,
                extra=extra,
            )
        return response


__all__ = ["OTEL_HTTP_SERVER_EVENT_TYPE", "register_fastapi_edge_middleware"]
