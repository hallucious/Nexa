from __future__ import annotations

import json
import re
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
        "document_content",
        "contract_text",
        "extracted_text",
        "raw_document_text",
        "clause_text",
        "plain_text",
        "why_it_matters",
        "question",
        "prompt",
        "rendered_prompt",
        "prompt_content",
        "provider_raw_output",
        "provider_output",
        "raw_provider_output",
        "raw_output",
        "completion_text",
        "model_output",
        "output_text",
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


def _path_segments(path: str) -> tuple[str, ...]:
    text = str(path or "").strip().lower().replace("-", "_")
    text = re.sub(r"\[\d+\]", "", text)
    return tuple(segment for segment in text.split(".") if segment)


def _normalize_path(path: str) -> str:
    return "_".join(_path_segments(path))


def _has_ordered_segments(segments: tuple[str, ...], required: tuple[str, ...]) -> bool:
    if not required:
        return False
    position = 0
    for segment in segments:
        if segment == required[position]:
            position += 1
            if position == len(required):
                return True
    return False


def _is_forbidden_observability_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    return normalized in FORBIDDEN_OBSERVABILITY_KEYS


def _is_forbidden_observability_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if not normalized:
        return False
    if normalized in FORBIDDEN_OBSERVABILITY_KEYS:
        return True

    segments = _path_segments(path)
    last = segments[-1] if segments else ""

    # Working Context and result-contract leakage shapes called out by the
    # observability/security plan. These are path-aware because the final key can
    # be innocuous (for example ``text`` or ``rendered``) while the full path is
    # sensitive (``input.text`` or ``prompt.main.rendered``).
    if _has_ordered_segments(segments, ("input", "text")):
        return True
    if "prompt" in segments and last == "rendered":
        return True
    if "provider" in segments and last in {"output", "raw_output"}:
        return True
    if "contract_review_result" in segments and "clauses" in segments and last in {"text", "plain_text", "why_it_matters"}:
        return True
    if "contract_review_result" in segments and "pre_signature_questions" in segments and last == "question":
        return True

    # Backward-compatible normalized suffix checks for callers that pass
    # pre-flattened dotted/underscored paths.
    if normalized.endswith("_input_text"):
        return True
    if "_prompt_" in f"_{normalized}_" and normalized.endswith("_rendered"):
        return True
    if "_provider_" in f"_{normalized}_" and normalized.endswith("_output"):
        return True
    if normalized.endswith("_provider_raw_output") or normalized.endswith("_raw_provider_output"):
        return True
    if normalized.endswith("_contract_review_result_clauses_text"):
        return True
    if normalized.endswith("_contract_review_result_clauses_plain_text"):
        return True
    if normalized.endswith("_contract_review_result_clauses_why_it_matters"):
        return True
    if normalized.endswith("_contract_review_result_pre_signature_questions_question"):
        return True
    return False


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


_RECURSABLE_FORBIDDEN_CONTAINER_KEYS = frozenset({"prompt"})


def _requires_redacted_value(*, key: Any, path: str, value: Any) -> bool:
    """Return whether this exact field value must collapse to REDACTED_VALUE.

    Some sensitive words are also structural containers in Nexa payloads. For
    example, ``prompt`` may be a container whose child ``main.rendered`` must be
    redacted while preserving the object shape. Body-like containers such as
    ``request_body`` or ``json`` are still collapsed wholesale.
    """

    key_text = str(key)
    normalized_key = _normalize_key(key_text)
    if _is_sensitive_key(key_text):
        return True
    if _is_forbidden_observability_key(key_text):
        if isinstance(value, (Mapping, list, tuple)) and normalized_key in _RECURSABLE_FORBIDDEN_CONTAINER_KEYS:
            return False
        return True
    if _is_forbidden_observability_path(path):
        return True
    return False

def sanitize_observability_payload(payload: Any, *, _path: str = "") -> Any:
    """Return a copy safe for logs, traces, metrics labels, and error payloads."""

    if isinstance(payload, Mapping):
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key)
            item_path = f"{_path}.{key_text}" if _path else key_text
            if _requires_redacted_value(key=key_text, path=item_path, value=value):
                sanitized[key_text] = REDACTED_VALUE
            elif isinstance(value, Mapping):
                sanitized[key_text] = sanitize_observability_payload(value, _path=item_path)
            elif isinstance(value, (list, tuple)):
                sanitized[key_text] = [
                    sanitize_observability_payload(item, _path=f"{item_path}[{index}]")
                    for index, item in enumerate(value)
                ]
            else:
                sanitized[key_text] = _redact_scalar(value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_observability_payload(item, _path=f"{_path}[{index}]") for index, item in enumerate(payload)]
    if isinstance(payload, tuple):
        return [sanitize_observability_payload(item, _path=f"{_path}[{index}]") for index, item in enumerate(payload)]
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
        if _requires_redacted_value(key=key_name, path=path, value=value) and value != REDACTED_VALUE:
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
