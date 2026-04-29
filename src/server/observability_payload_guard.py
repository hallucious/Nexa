from __future__ import annotations

import json
from typing import Any, Iterable, Mapping


REDACTED_VALUE = "<redacted>"

FORBIDDEN_OBSERVABILITY_KEYS = frozenset(
    {
        "body",
        "raw_body",
        "request_body",
        "response_body",
        "raw_response_body",
        "json",
        "form",
        "files",
        "payload",
        "document_text",
        "extracted_text",
        "raw_document_text",
        "prompt",
        "rendered_prompt",
        "prompt_content",
        "provider_raw_output",
        "raw_output",
        "completion_text",
        "model_output",
    }
)

SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "credential",
    "jwt",
    "presigned",
)

SENSITIVE_KEY_SUFFIXES = (
    "_key",
    "_token",
    "_secret",
    "_password",
    "_credential",
    "_credentials",
)


class ObservabilityPayloadLeakError(ValueError):
    """Raised when a payload still contains forbidden observability content."""


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().lower().replace("-", "_").replace(".", "_")


def _is_forbidden_observability_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    return normalized in FORBIDDEN_OBSERVABILITY_KEYS


def _is_sensitive_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    if not normalized:
        return False
    if any(part in normalized for part in SENSITIVE_KEY_PARTS):
        return True
    return any(normalized.endswith(suffix) for suffix in SENSITIVE_KEY_SUFFIXES)


def _redact_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    lowered = text.lower()
    if (
        "sk-" in lowered
        or "bearer " in lowered
        or "secret" in lowered
        or "token" in lowered
        or "password" in lowered
        or "aws_access_key" in lowered
    ):
        return REDACTED_VALUE
    if len(text) > 240:
        return text[:237] + "..."
    return text


def sanitize_observability_payload(payload: Any) -> Any:
    """Return a copy safe for logs, traces, metrics labels, and error payloads."""

    if isinstance(payload, Mapping):
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key)
            if _is_forbidden_observability_key(key_text) or _is_sensitive_key(key_text):
                sanitized[key_text] = REDACTED_VALUE
            elif isinstance(value, Mapping):
                sanitized[key_text] = sanitize_observability_payload(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key_text] = [sanitize_observability_payload(item) for item in value]
            else:
                sanitized[key_text] = _redact_scalar(value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_observability_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return [sanitize_observability_payload(item) for item in payload]
    return _redact_scalar(payload)


def _walk_paths(value: Any, *, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}" if path else key_text
            yield next_path, item
            yield from _walk_paths(item, path=next_path)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            next_path = f"{path}[{index}]"
            yield next_path, item
            yield from _walk_paths(item, path=next_path)


def assert_observability_payload_safe(payload: Any, *, forbidden_markers: Iterable[str] = ()) -> None:
    """Assert that a payload contains no raw forbidden observability content."""

    for path, value in _walk_paths(payload):
        key_name = path.rsplit(".", 1)[-1].split("[", 1)[0]
        if (_is_forbidden_observability_key(key_name) or _is_sensitive_key(key_name)) and value != REDACTED_VALUE:
            raise ObservabilityPayloadLeakError(f"unsafe observability field at {path}")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    for marker in forbidden_markers:
        if marker and marker in serialized:
            raise ObservabilityPayloadLeakError(f"unsafe observability marker present: {marker}")


__all__ = [
    "FORBIDDEN_OBSERVABILITY_KEYS",
    "ObservabilityPayloadLeakError",
    "REDACTED_VALUE",
    "assert_observability_payload_safe",
    "sanitize_observability_payload",
]
