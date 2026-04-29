from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from src.server.observability_payload_guard import (
    REDACTED_VALUE,
    assert_observability_payload_safe,
    sanitize_observability_payload,
)


HTTP_ACCESS_LOG_EVENT_TYPE = "http.access"

HttpLogWriter = Callable[[Mapping[str, Any]], Any]

_ALLOWED_TOP_LEVEL_KEYS = {
    "event_type",
    "method",
    "path",
    "route_template",
    "status_code",
    "duration_ms",
    "request_id",
    "extra",
}


def _bounded_text(value: Any, *, default: str = "", max_length: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


def _safe_int(value: Any, *, default: int = 0, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    if minimum is not None and parsed < minimum:
        return minimum
    return parsed


def build_http_access_log_event(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int | float | None = None,
    request_id: str | None = None,
    route_template: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a narrow HTTP access log event.

    HTTP access logging is deliberately narrower than request observation:
    it includes method, path, status, duration, and request id, but never raw
    headers, query params, request bodies, or response bodies. Any optional
    ``extra`` metadata is still passed through the shared observability guard.
    """

    event: dict[str, Any] = {
        "event_type": HTTP_ACCESS_LOG_EVENT_TYPE,
        "method": _bounded_text(method, default="UNKNOWN", max_length=16).upper(),
        "path": _bounded_text(path, default="/", max_length=512),
        "status_code": _safe_int(status_code, default=0, minimum=0),
        "duration_ms": _safe_int(duration_ms if duration_ms is not None else 0, default=0, minimum=0),
    }
    normalized_request_id = _bounded_text(request_id, default="", max_length=128)
    if normalized_request_id:
        event["request_id"] = normalized_request_id
    normalized_route = _bounded_text(route_template, default="", max_length=512)
    if normalized_route:
        event["route_template"] = normalized_route
    if isinstance(extra, Mapping) and extra:
        event["extra"] = sanitize_observability_payload(dict(extra))
    # Top-level HTTP access-log fields are schema-controlled. Sensitive optional
    # data enters only through ``extra`` and is sanitized above; preserving the
    # path keeps route diagnostics stable and preserves existing tests.
    return event


def assert_http_access_log_event_safe(event: Mapping[str, Any], *, forbidden_markers: Iterable[str] = ()) -> None:
    """Assert the event uses the narrow HTTP access-log schema and has no leaks."""

    unexpected = set(event.keys()) - _ALLOWED_TOP_LEVEL_KEYS
    if unexpected:
        raise ValueError(f"unexpected HTTP access log fields: {sorted(unexpected)}")
    assert_observability_payload_safe(event, forbidden_markers=forbidden_markers)


def emit_http_access_log(
    writer: HttpLogWriter | None,
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int | float | None = None,
    request_id: str | None = None,
    route_template: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Emit a safe HTTP access log event.

    Best-effort only: writer errors must never affect user-visible request
    handling. The built event is returned for tests/diagnostics.
    """

    event = build_http_access_log_event(
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        request_id=request_id,
        route_template=route_template,
        extra=extra,
    )
    try:
        assert_http_access_log_event_safe(event)
        if writer is not None:
            writer(dict(event))
    except Exception:
        return event
    return event


__all__ = [
    "HTTP_ACCESS_LOG_EVENT_TYPE",
    "HttpLogWriter",
    "assert_http_access_log_event_safe",
    "build_http_access_log_event",
    "emit_http_access_log",
]
