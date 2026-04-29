from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.server.edge_observability_runtime import REDACTED_VALUE, redact_headers, redact_mapping
from src.server.observability_payload_guard import sanitize_observability_payload


OTEL_DISABLED_REASON = "otel_disabled"
OTEL_INITIALIZED_REASON = "otel_initialized"
OTEL_SDK_MISSING_REASON = "otel_sdk_missing"
OTEL_INIT_FAILED_REASON = "otel_init_failed"

OTEL_SPAN_KIND_SERVER = "server"
OTEL_SPAN_KIND_WORKER = "worker"

_SQL_ATTRIBUTE_KEYS = {
    "db.statement",
    "db.query.text",
    "sql",
    "sql.statement",
    "sql_query",
    "raw_sql",
    "query_text",
    "statement",
}
_REQUEST_BODY_KEYS = {
    "body",
    "raw_body",
    "request_body",
    "data",
    "json",
    "form",
    "files",
    "payload",
}
_SAFE_ATTRIBUTE_TYPES = (str, bool, int, float, type(None))


@dataclass(frozen=True)
class OtelInitializationResult:
    enabled: bool
    initialized: bool
    reason: str
    service_name: str
    environment: str
    exporter_endpoint_configured: bool

    def as_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "initialized": self.initialized,
            "reason": self.reason,
            "service_name": self.service_name,
            "environment": self.environment,
            "exporter_endpoint_configured": self.exporter_endpoint_configured,
        }


def _normalize_attribute_key(key: Any) -> str:
    return str(key or "").strip().lower().replace("-", "_")


def _is_sql_attribute_key(key: Any) -> bool:
    normalized = str(key or "").strip().lower().replace("-", "_")
    dotted = normalized.replace("_", ".")
    return normalized in _SQL_ATTRIBUTE_KEYS or dotted in _SQL_ATTRIBUTE_KEYS


def _is_request_body_key(key: Any) -> bool:
    normalized = _normalize_attribute_key(key)
    return normalized in _REQUEST_BODY_KEYS


def _redact_attribute_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    lowered = text.lower()
    if "sk-" in lowered or "bearer " in lowered or "secret" in lowered or "token" in lowered or "password" in lowered:
        return REDACTED_VALUE
    if len(text) > 240:
        return text[:237] + "..."
    return text


def _safe_attribute_value(key: str, value: Any) -> Any:
    if _is_sql_attribute_key(key) or _is_request_body_key(key):
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return build_otel_safe_attributes(value)
    if isinstance(value, (list, tuple)):
        return [_safe_attribute_value(key, item) for item in value]
    if isinstance(value, _SAFE_ATTRIBUTE_TYPES):
        return redact_mapping({key: _redact_attribute_scalar(value)}).get(key)
    return _redact_attribute_scalar(value)


def build_otel_safe_attributes(attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return OTel-safe attributes with sensitive fields scrubbed.

    This function is SDK-independent. It is the shared projection boundary used
    before any attributes may reach OpenTelemetry spans, events, logs, or tests.
    """

    if not isinstance(attributes, Mapping):
        return {}
    safe: dict[str, Any] = {}
    for key, value in attributes.items():
        key_text = str(key)
        safe[key_text] = _safe_attribute_value(key_text, value)
    sanitized = sanitize_observability_payload(safe)
    return dict(sanitized) if isinstance(sanitized, Mapping) else {}


def build_otel_http_server_attributes(
    *,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    request_id: str | None = None,
    headers: Mapping[str, Any] | None = None,
    query_params: Mapping[str, Any] | None = None,
    session_claims: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build privacy-safe HTTP server span attributes."""

    attributes: dict[str, Any] = {
        "span.kind": OTEL_SPAN_KIND_SERVER,
        "http.request.method": str(method or "").upper(),
        "url.path": str(path or ""),
        "http.request.headers": redact_headers(headers if isinstance(headers, Mapping) else {}),
        "http.request.query": redact_mapping(query_params if isinstance(query_params, Mapping) else {}),
    }
    if status_code is not None:
        attributes["http.response.status_code"] = int(status_code)
    if request_id:
        attributes["nexa.request_id"] = str(request_id)
    if isinstance(session_claims, Mapping):
        attributes["nexa.session"] = redact_mapping(session_claims)
    if isinstance(extra, Mapping):
        attributes.update(build_otel_safe_attributes(extra))
    return build_otel_safe_attributes(attributes)


def build_otel_worker_attributes(
    *,
    job_name: str | None = None,
    run_id: str | None = None,
    workspace_id: str | None = None,
    payload: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build privacy-safe worker span attributes."""

    attributes: dict[str, Any] = {
        "span.kind": OTEL_SPAN_KIND_WORKER,
        "messaging.operation.name": str(job_name or ""),
    }
    if run_id:
        attributes["nexa.run_id"] = str(run_id)
    if workspace_id:
        attributes["nexa.workspace_id"] = str(workspace_id)
    if isinstance(payload, Mapping):
        attributes["nexa.worker.payload"] = build_otel_safe_attributes(payload)
    if isinstance(extra, Mapping):
        attributes.update(build_otel_safe_attributes(extra))
    return build_otel_safe_attributes(attributes)


def build_otel_exception_event(*, exc: BaseException, attributes: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a privacy-safe OTel exception event projection."""

    event_attributes = {
        "exception.type": exc.__class__.__name__,
        # Exception messages commonly contain raw input, SQL fragments, provider
        # output, or document excerpts. O3 treats the message as unsafe by
        # default rather than attempting content inference.
        "exception.message": REDACTED_VALUE,
    }
    if isinstance(attributes, Mapping):
        event_attributes.update(build_otel_safe_attributes(attributes))
    return {
        "name": "exception",
        "attributes": build_otel_safe_attributes(event_attributes),
    }


def initialize_otel_observability(
    *,
    enabled: bool,
    service_name: str = "nexa-server",
    environment: str = "local",
    exporter_endpoint: str | None = None,
    sdk_module: Any | None = None,
) -> OtelInitializationResult:
    """Initialize OTel if explicitly enabled and available.

    This is deliberately conservative. It avoids introducing a hard dependency
    and records a structured no-op posture when the SDK is unavailable.
    """

    service = str(service_name or "nexa-server").strip() or "nexa-server"
    env = str(environment or "local").strip() or "local"
    endpoint_configured = bool(str(exporter_endpoint or "").strip())
    if not enabled:
        return OtelInitializationResult(
            enabled=False,
            initialized=False,
            reason=OTEL_DISABLED_REASON,
            service_name=service,
            environment=env,
            exporter_endpoint_configured=endpoint_configured,
        )
    sdk = sdk_module
    if sdk is None:
        try:
            import opentelemetry.trace as sdk  # type: ignore[no-redef]
        except Exception:
            return OtelInitializationResult(
                enabled=True,
                initialized=False,
                reason=OTEL_SDK_MISSING_REASON,
                service_name=service,
                environment=env,
                exporter_endpoint_configured=endpoint_configured,
            )
    try:
        if not hasattr(sdk, "get_tracer_provider"):
            return OtelInitializationResult(
                enabled=True,
                initialized=False,
                reason=OTEL_SDK_MISSING_REASON,
                service_name=service,
                environment=env,
                exporter_endpoint_configured=endpoint_configured,
            )
        # Do not install exporters here yet. This first O2 slice only proves
        # safe bootstrap posture and safe attribute projection while still
        # touching the SDK provider boundary so bootstrap is observable/testable.
        sdk.get_tracer_provider()
    except Exception:
        return OtelInitializationResult(
            enabled=True,
            initialized=False,
            reason=OTEL_INIT_FAILED_REASON,
            service_name=service,
            environment=env,
            exporter_endpoint_configured=endpoint_configured,
        )
    return OtelInitializationResult(
        enabled=True,
        initialized=True,
        reason=OTEL_INITIALIZED_REASON,
        service_name=service,
        environment=env,
        exporter_endpoint_configured=endpoint_configured,
    )


__all__ = [
    "OTEL_DISABLED_REASON",
    "OTEL_INIT_FAILED_REASON",
    "OTEL_INITIALIZED_REASON",
    "OTEL_SDK_MISSING_REASON",
    "OTEL_SPAN_KIND_SERVER",
    "OTEL_SPAN_KIND_WORKER",
    "OtelInitializationResult",
    "build_otel_exception_event",
    "build_otel_http_server_attributes",
    "build_otel_safe_attributes",
    "build_otel_worker_attributes",
    "initialize_otel_observability",
]
