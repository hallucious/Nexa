from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from src.server.gdpr_deletion_runtime import (
    CATEGORY_C_TTL_DELETABLE,
    DEFAULT_MUTABLE_USER_TABLES,
    DEFAULT_TTL_USER_TABLES,
    GdprDeletionPolicyError,
    IMMUTABLE_HISTORY_TABLES,
    PERMANENT_AUDIT_TABLES,
    table_gdpr_category,
)
from src.server.observability_payload_guard import sanitize_observability_payload

try:  # pragma: no cover - optional dependency
    from sqlalchemy import text
    from sqlalchemy.engine import Engine
except ModuleNotFoundError:  # pragma: no cover
    Engine = Any  # type: ignore[misc,assignment]
    text = None  # type: ignore[assignment]


GDPR_USER_DELETION_AUDIT_TABLE = "user_deletion_audit"
GDPR_OBJECT_DELETE_FAILED_REASON = "gdpr_object_delete_failed"
GDPR_UNMAPPED_TTL_TABLE_REASON = "gdpr_ttl_table_has_no_user_ref_column"

# Explicit allow-list. Never infer a column name from user input.
MUTABLE_USER_REF_COLUMNS: dict[str, str] = {
    "workspace_memberships": "user_id",
    "user_subscriptions": "user_id_ref",
    "user_preferences": "user_id_ref",
    "push_notification_tokens": "user_id_ref",
    "file_uploads": "user_id_ref",
}

TTL_USER_REF_COLUMNS: dict[str, str | None] = {
    "run_submissions": "submitter_user_ref",
    # run_submission_dedupe is keyed by dedupe_key/run_id and has no direct
    # user-ref column in the current schema. Leave it untouched here; it remains
    # TTL-cleaned by its normal expiry job rather than user-scoped deletion.
    "run_submission_dedupe": None,
    "quota_usage": "user_id_ref",
}


@dataclass(frozen=True)
class GdprPostgresDeletionAdapter:
    """Concrete Postgres adapter for GDPR deletion execution callables.

    This adapter is intentionally narrow:
    - mutable/TTL table names are allow-listed,
    - immutable history tables are rejected before SQL execution,
    - SQL identifiers are never derived from untrusted arbitrary input,
    - values are parameterized,
    - audit payloads are sanitized before insertion.
    """

    engine: Engine
    audit_table_name: str = GDPR_USER_DELETION_AUDIT_TABLE

    def delete_mutable_rows(self, table_name: str, user_ref: str) -> int:
        normalized_table = _normalize_table_name(table_name)
        _assert_deletion_allowed(normalized_table)
        column_name = MUTABLE_USER_REF_COLUMNS.get(normalized_table)
        if column_name is None:
            raise GdprDeletionPolicyError(f"mutable table is not user-deletable by adapter: {normalized_table}")
        return _execute_delete_by_user_ref(
            self.engine,
            table_name=normalized_table,
            column_name=column_name,
            user_ref=user_ref,
        )

    def cleanup_ttl_rows(self, table_name: str, user_ref: str) -> int:
        normalized_table = _normalize_table_name(table_name)
        _assert_deletion_allowed(normalized_table)
        if normalized_table not in TTL_USER_REF_COLUMNS:
            raise GdprDeletionPolicyError(f"ttl table is not known to GDPR adapter: {normalized_table}")
        column_name = TTL_USER_REF_COLUMNS[normalized_table]
        if column_name is None:
            return 0
        return _execute_delete_by_user_ref(
            self.engine,
            table_name=normalized_table,
            column_name=column_name,
            user_ref=user_ref,
        )

    def write_audit(self, audit_payload: Mapping[str, Any]) -> dict[str, Any]:
        sanitized = sanitize_observability_payload(dict(audit_payload))
        _require_sqlalchemy()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {self.audit_table_name} (
                        deletion_request_id,
                        user_ref,
                        requested_by_ref,
                        status,
                        reason,
                        audit_payload
                    ) VALUES (
                        :deletion_request_id,
                        :user_ref,
                        :requested_by_ref,
                        :status,
                        :reason,
                        :audit_payload
                    )
                    """
                ),
                {
                    "deletion_request_id": str(sanitized.get("deletion_request_id") or ""),
                    "user_ref": str(sanitized.get("user_ref") or ""),
                    "requested_by_ref": str(sanitized.get("requested_by_ref") or ""),
                    "status": str(sanitized.get("status") or ""),
                    "reason": str(sanitized.get("reason") or ""),
                    "audit_payload": sanitized,
                },
            )
        return dict(sanitized)


@dataclass(frozen=True)
class GdprObjectStorageDeletionAdapter:
    """Object-storage deleter for GDPR user-owned object cleanup.

    The adapter supports S3-style clients exposing ``delete_object`` and accepts
    either ``s3://bucket/key`` refs or raw keys when ``default_bucket`` is set.
    """

    object_storage_client: Any
    default_bucket: str | None = None

    def delete_object(self, object_ref: str) -> bool:
        bucket, key = parse_object_storage_ref(object_ref, default_bucket=self.default_bucket)
        if not bucket or not key:
            raise GdprDeletionPolicyError("object_ref must resolve to a bucket and key")
        try:
            result = self.object_storage_client.delete_object(Bucket=bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            raise GdprDeletionPolicyError(GDPR_OBJECT_DELETE_FAILED_REASON) from exc
        status_code = _extract_response_status_code(result)
        return status_code is None or 200 <= status_code < 300


@dataclass(frozen=True)
class GdprDeletionAdapterSet:
    postgres: GdprPostgresDeletionAdapter
    object_storage: GdprObjectStorageDeletionAdapter
    identity_deleter: Callable[[str], bool] | None = None

    def route_kwargs(self) -> dict[str, Any]:
        """Return kwargs accepted by build_gdpr_deletion_router()."""

        return {
            "mutable_row_deleter": self.postgres.delete_mutable_rows,
            "ttl_row_cleaner": self.postgres.cleanup_ttl_rows,
            "object_storage_deleter": self.object_storage.delete_object,
            "audit_writer": self.postgres.write_audit,
            "identity_deleter": self.identity_deleter,
        }


def parse_object_storage_ref(object_ref: str, *, default_bucket: str | None = None) -> tuple[str | None, str | None]:
    text_ref = str(object_ref or "").strip()
    if not text_ref:
        return None, None
    parsed = urlparse(text_ref)
    if parsed.scheme == "s3":
        bucket = parsed.netloc.strip()
        key = parsed.path.lstrip("/").strip()
        return bucket or None, key or None
    bucket = str(default_bucket or "").strip() or None
    return bucket, text_ref.lstrip("/").strip() or None


def _execute_delete_by_user_ref(
    engine: Engine,
    *,
    table_name: str,
    column_name: str,
    user_ref: str,
) -> int:
    _require_sqlalchemy()
    with engine.begin() as connection:
        result = connection.execute(
            text(f"DELETE FROM {table_name} WHERE {column_name} = :user_ref"),
            {"user_ref": user_ref},
        )
    return int(getattr(result, "rowcount", 0) or 0)


def _assert_deletion_allowed(table_name: str) -> None:
    normalized = _normalize_table_name(table_name)
    if normalized in IMMUTABLE_HISTORY_TABLES or normalized in PERMANENT_AUDIT_TABLES:
        raise GdprDeletionPolicyError(f"immutable history table cannot be deleted: {normalized}")
    category = table_gdpr_category(normalized)
    if category not in {"B_mutable", CATEGORY_C_TTL_DELETABLE}:
        raise GdprDeletionPolicyError(f"table is not GDPR-deletable: {normalized}")


def _normalize_table_name(table_name: str) -> str:
    normalized = str(table_name or "").strip().lower()
    if not normalized:
        raise GdprDeletionPolicyError("table_name must be non-empty")
    if not normalized.replace("_", "").isalnum():
        raise GdprDeletionPolicyError(f"unsafe table name: {normalized}")
    return normalized


def _extract_response_status_code(result: Any) -> int | None:
    if not isinstance(result, Mapping):
        return None
    metadata = result.get("ResponseMetadata")
    if not isinstance(metadata, Mapping):
        return None
    status = metadata.get("HTTPStatusCode")
    try:
        return int(status)
    except Exception:
        return None


def _require_sqlalchemy() -> None:
    if text is None:
        raise ModuleNotFoundError("sqlalchemy is required for GDPR Postgres deletion adapters")


__all__ = [
    "GDPR_OBJECT_DELETE_FAILED_REASON",
    "GDPR_UNMAPPED_TTL_TABLE_REASON",
    "GDPR_USER_DELETION_AUDIT_TABLE",
    "GdprDeletionAdapterSet",
    "GdprObjectStorageDeletionAdapter",
    "GdprPostgresDeletionAdapter",
    "MUTABLE_USER_REF_COLUMNS",
    "TTL_USER_REF_COLUMNS",
    "parse_object_storage_ref",
]
