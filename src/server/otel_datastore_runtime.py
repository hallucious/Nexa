from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.otel_observability_runtime import build_otel_exception_event, build_otel_safe_attributes


OTEL_DATASTORE_EVENT_TYPE = "otel.datastore"
OTEL_SPAN_KIND_CLIENT = "client"
OTEL_DB_SYSTEM_POSTGRESQL = "postgresql"
OTEL_DB_SYSTEM_REDIS = "redis"

OtelDatastoreSpanWriter = Callable[[Mapping[str, Any]], Any]


def _bounded_text(value: Any, *, default: str = "", max_length: int = 160) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


def _normalize_operation(value: Any, *, default: str = "unknown") -> str:
    text = _bounded_text(value, default=default, max_length=64)
    return text.upper() if text else default.upper()


def _normalize_db_system(value: Any, *, default: str = OTEL_DB_SYSTEM_POSTGRESQL) -> str:
    text = _bounded_text(value, default=default, max_length=64).lower().replace(" ", "_")
    return text or default


def _safe_identifier(value: Any, *, max_length: int = 120) -> str | None:
    text = _bounded_text(value, default="", max_length=max_length)
    if not text:
        return None
    lowered = text.lower()
    if "sk-" in lowered or "bearer " in lowered or "secret" in lowered or "token" in lowered or "password" in lowered:
        return REDACTED_VALUE
    return text


def _hash_value(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return sha256(text.encode("utf-8")).hexdigest()[:16]


def _redis_key_prefix(value: Any, *, explicit_prefix: str | None = None) -> str | None:
    if explicit_prefix is not None:
        return _safe_identifier(explicit_prefix, max_length=120)
    text = str(value or "").strip()
    if not text:
        return None
    parts = [part for part in text.split(":") if part]
    if not parts:
        return None
    prefix = ":".join(parts[: min(3, len(parts))])
    return _safe_identifier(prefix, max_length=120)


def build_otel_database_span_attributes(
    *,
    operation: str | None = None,
    db_system: str | None = OTEL_DB_SYSTEM_POSTGRESQL,
    table_name: str | None = None,
    query_label: str | None = None,
    statement: str | None = None,
    parameters: Mapping[str, Any] | Sequence[Any] | None = None,
    row_count: int | None = None,
    duration_ms: int | float | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build privacy-safe database span attributes.

    Raw SQL text and bound parameters are never treated as safe telemetry.
    Callers should provide ``operation``, ``table_name``, and ``query_label``
    as normalized diagnostic identifiers instead of relying on SQL statements.
    """

    attributes: dict[str, Any] = {
        "span.kind": OTEL_SPAN_KIND_CLIENT,
        "db.system": _normalize_db_system(db_system),
        "db.operation": _normalize_operation(operation),
    }
    safe_table = _safe_identifier(table_name)
    if safe_table:
        attributes["db.sql.table"] = safe_table
    safe_label = _safe_identifier(query_label)
    if safe_label:
        attributes["db.query.label"] = safe_label
    if statement is not None:
        attributes["db.statement"] = REDACTED_VALUE
    if parameters is not None:
        attributes["db.query.parameters"] = REDACTED_VALUE
    if row_count is not None:
        attributes["db.rows_affected"] = max(0, int(row_count))
    if duration_ms is not None:
        attributes["db.duration_ms"] = max(0, int(duration_ms))
    if isinstance(extra, Mapping):
        attributes.update(build_otel_safe_attributes(extra))
    return build_otel_safe_attributes(attributes)


def build_otel_redis_span_attributes(
    *,
    command: str | None = None,
    key: str | None = None,
    key_prefix: str | None = None,
    database_index: int | None = None,
    duration_ms: int | float | None = None,
    hit: bool | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build privacy-safe Redis span attributes.

    Redis keys can contain user ids, tokens, or document-derived identifiers, so
    this projection stores only a short hash and a bounded prefix. The raw key is
    never emitted.
    """

    attributes: dict[str, Any] = {
        "span.kind": OTEL_SPAN_KIND_CLIENT,
        "db.system": OTEL_DB_SYSTEM_REDIS,
        "db.operation": _normalize_operation(command),
    }
    hashed_key = _hash_value(key)
    if hashed_key:
        attributes["db.redis.key_hash"] = hashed_key
    safe_prefix = _redis_key_prefix(key, explicit_prefix=key_prefix)
    if safe_prefix:
        attributes["db.redis.key_prefix"] = safe_prefix
    if database_index is not None:
        attributes["db.redis.database_index"] = max(0, int(database_index))
    if duration_ms is not None:
        attributes["db.duration_ms"] = max(0, int(duration_ms))
    if hit is not None:
        attributes["db.redis.hit"] = bool(hit)
    if isinstance(extra, Mapping):
        attributes.update(build_otel_safe_attributes(extra))
    return build_otel_safe_attributes(attributes)


def build_otel_datastore_span_event(
    *,
    name: str,
    attributes: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a safe datastore span projection event."""

    event: dict[str, Any] = {
        "event_type": OTEL_DATASTORE_EVENT_TYPE,
        "name": _bounded_text(name, default="datastore.operation", max_length=120),
        "attributes": build_otel_safe_attributes(attributes),
    }
    if events:
        event["events"] = [build_otel_safe_attributes(item) for item in events]
    return event


def build_otel_datastore_exception_event(*, exc: BaseException, attributes: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a privacy-safe datastore exception event."""

    return build_otel_exception_event(exc=exc, attributes=attributes)


def emit_otel_datastore_span(
    writer: OtelDatastoreSpanWriter | None,
    *,
    name: str,
    attributes: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Emit a safe datastore span projection without affecting user flow."""

    event = build_otel_datastore_span_event(name=name, attributes=attributes, events=events)
    try:
        if writer is not None:
            writer(dict(event))
    except Exception:
        return event
    return event


__all__ = [
    "OTEL_DATASTORE_EVENT_TYPE",
    "OTEL_DB_SYSTEM_POSTGRESQL",
    "OTEL_DB_SYSTEM_REDIS",
    "OTEL_SPAN_KIND_CLIENT",
    "OtelDatastoreSpanWriter",
    "build_otel_database_span_attributes",
    "build_otel_datastore_exception_event",
    "build_otel_datastore_span_event",
    "build_otel_redis_span_attributes",
    "emit_otel_datastore_span",
]
