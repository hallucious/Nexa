from __future__ import annotations

import json
from typing import Any, Mapping

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.server.gdpr_deletion_api import (
    GDPR_DELETION_DENIED_REASON,
    GDPR_DELETION_PERMISSION,
    GDPR_DELETION_ROUTE,
    authorize_gdpr_deletion,
    build_gdpr_deletion_router,
)
from src.server.gdpr_deletion_runtime import GDPR_DELETION_STATUS_COMPLETED


def _claims_header(claims: Mapping[str, Any]) -> dict[str, str]:
    return {"x-nexa-session-claims": json.dumps(dict(claims))}


def _client_with_wiring(calls: dict[str, list[Any]]) -> TestClient:
    app = FastAPI()

    def mutable_row_deleter(table_name: str, user_ref: str) -> int:
        calls.setdefault("mutable", []).append((table_name, user_ref))
        return 2

    def object_storage_deleter(object_ref: str) -> bool:
        calls.setdefault("objects", []).append(object_ref)
        return True

    def identity_deleter(user_ref: str) -> bool:
        calls.setdefault("identity", []).append(user_ref)
        return True

    def ttl_row_cleaner(table_name: str, user_ref: str) -> int:
        calls.setdefault("ttl", []).append((table_name, user_ref))
        return 1

    def audit_writer(row: Mapping[str, Any]) -> None:
        calls.setdefault("audit", []).append(dict(row))

    app.include_router(
        build_gdpr_deletion_router(
            mutable_row_deleter=mutable_row_deleter,
            object_storage_deleter=object_storage_deleter,
            identity_deleter=identity_deleter,
            ttl_row_cleaner=ttl_row_cleaner,
            audit_writer=audit_writer,
        )
    )
    return TestClient(app)


def test_authorize_gdpr_deletion_requires_admin_role_and_explicit_permission() -> None:
    denied_no_permission = authorize_gdpr_deletion({"roles": ["admin"], "user_ref": "userref_admin"})
    denied_no_role = authorize_gdpr_deletion({"permissions": [GDPR_DELETION_PERMISSION], "user_ref": "userref_admin"})
    allowed = authorize_gdpr_deletion(
        {"roles": ["admin"], "permissions": [GDPR_DELETION_PERMISSION], "user_ref": "userref_admin"}
    )

    assert denied_no_permission.allowed is False
    assert denied_no_role.allowed is False
    assert allowed.allowed is True
    assert allowed.actor_ref == "userref_admin"


def test_gdpr_deletion_route_denies_general_user_before_deletion_work() -> None:
    calls: dict[str, list[Any]] = {}
    client = _client_with_wiring(calls)

    response = client.post(
        GDPR_DELETION_ROUTE,
        headers=_claims_header({"roles": ["general_user"], "permissions": [], "sub": "clerk-user-001"}),
        json={"user_ref": "userref_target", "object_storage_refs": ["s3://bucket/user-doc.pdf"]},
    )

    assert response.status_code == 403
    assert response.json() == {"status": "denied", "reason": GDPR_DELETION_DENIED_REASON}
    assert calls.get("identity") is None
    assert calls.get("mutable") is None
    assert calls.get("objects") is None
    assert calls.get("ttl") is None
    assert len(calls.get("audit", [])) == 1
    denial = calls["audit"][0]
    assert denial["event_type"] == "gdpr_deletion_denied"
    assert denial["source_lookup_attempted"] is False
    assert denial["deletion_attempted"] is False
    assert denial["model_invocation_attempted"] is False
    assert "clerk-user-001" not in json.dumps(denial, sort_keys=True)


def test_gdpr_deletion_route_executes_authorized_deletion_and_audits_result() -> None:
    calls: dict[str, list[Any]] = {}
    client = _client_with_wiring(calls)

    response = client.post(
        GDPR_DELETION_ROUTE,
        headers=_claims_header(
            {
                "roles": ["admin"],
                "permissions": [GDPR_DELETION_PERMISSION],
                "sub": "clerk-admin-001",
            }
        ),
        json={
            "deletion_request_id": "gdpr_req_001",
            "user_ref": "userref_target",
            "object_storage_refs": ["s3://nexa-uploads/userref_target/contract.pdf"],
            "mutable_table_names": ["workspace_memberships", "file_uploads"],
            "ttl_table_names": ["run_submissions"],
            "raw_identity_hint": "person@example.com",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == GDPR_DELETION_STATUS_COMPLETED
    assert payload["deletion_request_id"] == "gdpr_req_001"
    assert calls["identity"] == ["userref_target"]
    assert calls["mutable"] == [("workspace_memberships", "userref_target"), ("file_uploads", "userref_target")]
    assert calls["objects"] == ["s3://nexa-uploads/userref_target/contract.pdf"]
    assert calls["ttl"] == [("run_submissions", "userref_target")]
    assert calls["audit"][-1]["status"] == GDPR_DELETION_STATUS_COMPLETED
    serialized = json.dumps(payload, sort_keys=True)
    assert "person@example.com" not in serialized
    assert "clerk-admin-001" not in serialized


def test_gdpr_deletion_route_rejects_direct_identity_without_deleting() -> None:
    calls: dict[str, list[Any]] = {}
    client = _client_with_wiring(calls)

    response = client.post(
        GDPR_DELETION_ROUTE,
        headers=_claims_header({"roles": ["admin"], "permissions": [GDPR_DELETION_PERMISSION], "user_ref": "userref_admin"}),
        json={"user_ref": "person@example.com"},
    )

    assert response.status_code == 400
    assert response.json()["status"] == "denied"
    assert calls.get("identity") is None
    assert calls.get("mutable") is None
    assert calls.get("objects") is None
    assert len(calls.get("audit", [])) == 1
    assert calls["audit"][0]["event_type"] == "gdpr_deletion_policy_denied"


def test_gdpr_deletion_route_rejects_immutable_table_targets_without_deleting() -> None:
    calls: dict[str, list[Any]] = {}
    client = _client_with_wiring(calls)

    response = client.post(
        GDPR_DELETION_ROUTE,
        headers=_claims_header({"roles": ["admin"], "permissions": [GDPR_DELETION_PERMISSION], "user_ref": "userref_admin"}),
        json={"user_ref": "userref_target", "mutable_table_names": ["execution_record"]},
    )

    assert response.status_code == 400
    assert response.json()["reason"] == "gdpr_deletion_policy_denied"
    assert calls.get("identity") is None
    assert calls.get("mutable") is None
    assert calls["audit"][0]["deletion_attempted"] is False
