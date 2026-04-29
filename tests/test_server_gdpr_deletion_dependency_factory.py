from __future__ import annotations

import json
from typing import Any, Mapping

from fastapi.testclient import TestClient

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.gdpr_deletion_api import GDPR_DELETION_ROUTE
from src.server.gdpr_deletion_dependency_factory import build_gdpr_deletion_router_provider


class _FakeResult:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount


class _FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    def execute(self, sql: Any, params: Mapping[str, Any]) -> _FakeResult:
        self.calls.append((str(sql), dict(params)))
        return _FakeResult(rowcount=1)

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
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.calls.append({"Bucket": Bucket, "Key": Key})
        return {"ResponseMetadata": {"HTTPStatusCode": 204}}


def _admin_header() -> dict[str, str]:
    return {
        "x-nexa-session-claims": json.dumps(
            {
                "sub": "clerk_user_001",
                "roles": ["admin"],
                "permissions": ["admin.gdpr_delete_user"],
            }
        )
    }


def test_gdpr_router_provider_wires_concrete_adapters_into_fastapi_app(monkeypatch) -> None:  # noqa: ANN001
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    engine = _FakeEngine()
    s3 = _FakeS3()
    identity_deleted: list[str] = []
    provider = build_gdpr_deletion_router_provider(
        sync_engine=engine,
        object_storage_client=s3,
        default_bucket="nexa-uploads",
        identity_deleter=lambda user_ref: identity_deleted.append(user_ref) is None or True,
    )
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(gdpr_deletion_router_provider=provider)
    )
    client = TestClient(app)

    response = client.post(
        GDPR_DELETION_ROUTE,
        headers=_admin_header(),
        json={
            "user_ref": "user_ref_001",
            "deletion_request_id": "gdpr-001",
            "mutable_table_names": ["workspace_memberships"],
            "ttl_table_names": ["quota_usage"],
            "object_storage_refs": ["workspace/user/file.pdf"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert identity_deleted == ["user_ref_001"]
    assert s3.calls == [{"Bucket": "nexa-uploads", "Key": "workspace/user/file.pdf"}]
    sql_calls = [call[0] for call in engine.connection.calls]
    assert "DELETE FROM workspace_memberships WHERE user_id = :user_ref" in sql_calls
    assert "DELETE FROM quota_usage WHERE user_id_ref = :user_ref" in sql_calls
    assert any("INSERT INTO user_deletion_audit" in sql for sql in sql_calls)


def test_gdpr_router_provider_requires_object_storage_client() -> None:
    try:
        build_gdpr_deletion_router_provider(
            sync_engine=_FakeEngine(),
            object_storage_client=None,
            default_bucket="nexa-uploads",
        )
    except ValueError as exc:
        assert "object_storage_client" in str(exc)
    else:  # pragma: no cover - defensive assertion style for old pytest versions
        raise AssertionError("expected object_storage_client validation failure")
