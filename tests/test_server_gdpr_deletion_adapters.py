from __future__ import annotations

from typing import Any, Mapping

import pytest

from src.server.gdpr_deletion_adapters import (
    GDPR_OBJECT_DELETE_FAILED_REASON,
    GdprDeletionAdapterSet,
    GdprObjectStorageDeletionAdapter,
    GdprPostgresDeletionAdapter,
    parse_object_storage_ref,
)
from src.server.gdpr_deletion_runtime import GdprDeletionPolicyError


class _FakeResult:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount


class _FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Mapping[str, Any]]] = []

    def execute(self, sql: Any, params: Mapping[str, Any]) -> _FakeResult:
        self.calls.append((str(sql), dict(params)))
        return _FakeResult(rowcount=2)

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class _FakeEngine:
    def __init__(self) -> None:
        self.connection = _FakeConnection()

    def begin(self) -> _FakeConnection:
        return self.connection


class _FakeS3:
    def __init__(self, *, status_code: int = 204) -> None:
        self.status_code = status_code
        self.calls: list[dict[str, str]] = []

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.calls.append({"Bucket": Bucket, "Key": Key})
        return {"ResponseMetadata": {"HTTPStatusCode": self.status_code}}


class _FailingS3:
    def delete_object(self, *, Bucket: str, Key: str) -> None:
        raise RuntimeError("delete failed with sk-object-secret")


def test_postgres_adapter_deletes_only_allowlisted_mutable_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    engine = _FakeEngine()
    adapter = GdprPostgresDeletionAdapter(engine=engine)

    deleted = adapter.delete_mutable_rows("workspace_memberships", "user_ref_001")

    assert deleted == 2
    sql, params = engine.connection.calls[0]
    assert sql == "DELETE FROM workspace_memberships WHERE user_id = :user_ref"
    assert params == {"user_ref": "user_ref_001"}


def test_postgres_adapter_rejects_immutable_table_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    adapter = GdprPostgresDeletionAdapter(engine=_FakeEngine())

    with pytest.raises(GdprDeletionPolicyError, match="immutable history table"):
        adapter.delete_mutable_rows("execution_record", "user_ref_001")

    with pytest.raises(GdprDeletionPolicyError, match="immutable history table"):
        adapter.cleanup_ttl_rows("user_deletion_audit", "user_ref_001")


def test_postgres_adapter_cleans_user_scoped_ttl_rows_and_skips_unmapped_dedupe(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    engine = _FakeEngine()
    adapter = GdprPostgresDeletionAdapter(engine=engine)

    assert adapter.cleanup_ttl_rows("quota_usage", "user_ref_001") == 2
    assert adapter.cleanup_ttl_rows("run_submission_dedupe", "user_ref_001") == 0

    sql, params = engine.connection.calls[0]
    assert sql == "DELETE FROM quota_usage WHERE user_id_ref = :user_ref"
    assert params == {"user_ref": "user_ref_001"}
    assert len(engine.connection.calls) == 1


def test_postgres_audit_writer_sanitizes_payload_before_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    engine = _FakeEngine()
    adapter = GdprPostgresDeletionAdapter(engine=engine)

    written = adapter.write_audit(
        {
            "deletion_request_id": "gdpr-001",
            "user_ref": "user_ref_001",
            "requested_by_ref": "actor_ref_001",
            "status": "completed",
            "reason": "user_requested_deletion",
            "api_key": "sk-audit-secret",
        }
    )

    assert written["api_key"] == "<redacted>"
    sql, params = engine.connection.calls[0]
    assert "INSERT INTO user_deletion_audit" in sql
    assert params["deletion_request_id"] == "gdpr-001"
    assert params["audit_payload"]["api_key"] == "<redacted>"


def test_object_storage_adapter_deletes_s3_refs_and_raw_keys() -> None:
    s3 = _FakeS3()
    adapter = GdprObjectStorageDeletionAdapter(object_storage_client=s3, default_bucket="default-bucket")

    assert adapter.delete_object("s3://nexa-uploads/path/to/file.pdf") is True
    assert adapter.delete_object("workspace/user/file.docx") is True

    assert s3.calls == [
        {"Bucket": "nexa-uploads", "Key": "path/to/file.pdf"},
        {"Bucket": "default-bucket", "Key": "workspace/user/file.docx"},
    ]


def test_object_storage_adapter_rejects_unresolvable_or_failed_deletes() -> None:
    with pytest.raises(GdprDeletionPolicyError, match="bucket and key"):
        GdprObjectStorageDeletionAdapter(object_storage_client=_FakeS3()).delete_object("raw/key/without/bucket")

    with pytest.raises(GdprDeletionPolicyError, match=GDPR_OBJECT_DELETE_FAILED_REASON):
        GdprObjectStorageDeletionAdapter(object_storage_client=_FailingS3(), default_bucket="bucket").delete_object("key")


def test_parse_object_storage_ref_supports_s3_and_default_bucket() -> None:
    assert parse_object_storage_ref("s3://bucket/a/b.txt") == ("bucket", "a/b.txt")
    assert parse_object_storage_ref("a/b.txt", default_bucket="bucket") == ("bucket", "a/b.txt")
    assert parse_object_storage_ref("", default_bucket="bucket") == (None, None)


def test_adapter_set_returns_route_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    adapter_set = GdprDeletionAdapterSet(
        postgres=GdprPostgresDeletionAdapter(engine=_FakeEngine()),
        object_storage=GdprObjectStorageDeletionAdapter(object_storage_client=_FakeS3(), default_bucket="bucket"),
        identity_deleter=lambda user_ref: True,
    )

    kwargs = adapter_set.route_kwargs()

    assert set(kwargs) == {
        "mutable_row_deleter",
        "ttl_row_cleaner",
        "object_storage_deleter",
        "audit_writer",
        "identity_deleter",
    }
    assert kwargs["identity_deleter"]("user_ref_001") is True
