from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from src.server.observability_payload_guard import sanitize_observability_payload


EDGE_EXCEPTION_REASON = "edge_exception_captured"
REDACTED_VALUE = "<redacted>"

SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "session",
    "credential",
)
SENSITIVE_KEY_EXACT_MATCHES = {
    "key",
}
SENSITIVE_KEY_SUFFIXES = (
    "_key",
    "_token",
    "_secret",
    "_password",
    "_credential",
    "_credentials",
)

SAFE_HEADER_ALLOWLIST = {
    "accept",
    "content-type",
    "origin",
    "referer",
    "user-agent",
    "x-request-id",
    "x-nexa-request-id",
}


EdgeObservationWriter = Callable[[Mapping[str, Any]], Any]


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().lower().replace("-", "_")


def _is_sensitive_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    if not normalized:
        return False
    if normalized in SENSITIVE_KEY_EXACT_MATCHES:
        return True
    if any(part in normalized for part in SENSITIVE_KEY_PARTS):
        return True
    return any(normalized.endswith(suffix) for suffix in SENSITIVE_KEY_SUFFIXES)


def _redact_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    lowered = text.lower()
    if "sk-" in lowered or "bearer " in lowered or "secret" in lowered or "token" in lowered:
        return REDACTED_VALUE
    if len(text) > 160:
        return text[:157] + "..."
    return text


def redact_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mapping, Mapping):
        return {}
    redacted: dict[str, Any] = {}
    for key, value in mapping.items():
        key_text = str(key)
        if _is_sensitive_key(key_text):
            redacted[key_text] = REDACTED_VALUE
        elif isinstance(value, Mapping):
            redacted[key_text] = redact_mapping(value)
        elif isinstance(value, (list, tuple)):
            redacted[key_text] = [redact_mapping(item) if isinstance(item, Mapping) else _redact_scalar(item) for item in value]
        else:
            redacted[key_text] = _redact_scalar(value)
    return redacted


def redact_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(headers, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key, value in headers.items():
        normalized = str(key or "").strip().lower()
        if not normalized:
            continue
        if normalized in SAFE_HEADER_ALLOWLIST and not _is_sensitive_key(normalized):
            result[normalized] = _redact_scalar(value)
        elif _is_sensitive_key(normalized):
            result[normalized] = REDACTED_VALUE
    return result


def request_observation_context(
    *,
    method: str,
    path: str,
    headers: Mapping[str, Any] | None = None,
    query_params: Mapping[str, Any] | None = None,
    session_claims: Mapping[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "request_id": str(request_id or "").strip() or None,
        "method": str(method or "").upper(),
        "path": str(path or ""),
        "headers": redact_headers(headers),
        "query_params": redact_mapping(query_params),
        "session": redact_mapping(session_claims),
    }


@dataclass(frozen=True)
class EdgeObservationEvent:
    event_type: str
    request: dict[str, Any]
    status_code: int | None = None
    error_type: str | None = None
    reason: str | None = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_type": self.event_type,
            "request": dict(self.request),
        }
        if self.status_code is not None:
            payload["status_code"] = self.status_code
        if self.error_type:
            payload["error_type"] = self.error_type
        if self.reason:
            payload["reason"] = self.reason
        return payload


def edge_request_completed_event(*, request_context: Mapping[str, Any], status_code: int) -> dict[str, Any]:
    return EdgeObservationEvent(
        event_type="edge.http_request_completed",
        request=dict(request_context),
        status_code=int(status_code),
    ).as_payload()


def edge_exception_event(*, request_context: Mapping[str, Any], exc: BaseException) -> dict[str, Any]:
    return EdgeObservationEvent(
        event_type="edge.http_exception_captured",
        request=dict(request_context),
        status_code=500,
        error_type=exc.__class__.__name__,
        reason=EDGE_EXCEPTION_REASON,
    ).as_payload()


def edge_exception_payload(*, request_id: str | None = None) -> dict[str, Any]:
    payload = {"status": "error", "reason": EDGE_EXCEPTION_REASON}
    if request_id:
        payload["request_id"] = request_id
    return payload


def emit_edge_observation(writer: EdgeObservationWriter | None, event: Mapping[str, Any]) -> None:
    if writer is None:
        return
    try:
        writer(sanitize_observability_payload(dict(event)))
    except Exception:
        # Observability must never become the user-visible failure path.
        return


__all__ = [
    "EDGE_EXCEPTION_REASON",
    "EdgeObservationEvent",
    "EdgeObservationWriter",
    "edge_exception_event",
    "edge_exception_payload",
    "edge_request_completed_event",
    "emit_edge_observation",
    "redact_headers",
    "redact_mapping",
    "request_observation_context",
]
