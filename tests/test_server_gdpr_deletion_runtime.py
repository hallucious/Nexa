from __future__ import annotations

import json

import pytest

from src.server.gdpr_deletion_runtime import (
    CATEGORY_A_APPEND_ONLY,
    CATEGORY_B_MUTABLE,
    CATEGORY_D_PERMANENT_AUDIT,
    GDPR_ACTION_DELETE_MUTABLE_ROWS,
    GDPR_ACTION_DELETE_OBJECT,
    GDPR_ACTION_PRESERVE_IMMUTABLE_HISTORY,
    GDPR_DELETION_STATUS_COMPLETED,
    GDPR_DELETION_STATUS_FAILED,
    GDPR_DELETION_STATUS_PLANNED,
    GdprDeletionPolicyError,
    GdprDeletionRequest,
    build_gdpr_deletion_plan,
    execute_gdpr_deletion_plan,
    table_gdpr_category,
)


def test_table_gdpr_category_preserves_immutable_and_audit_tables() -> None:
    assert table_gdpr_category("execution_record") == CATEGORY_A_APPEND_ONLY
    assert table_gdpr_category("artifact_index") == CATEGORY_A_APPEND_ONLY
    assert table_gdpr_category("user_deletion_audit") == CATEGORY_D_PERMANENT_AUDIT
    assert table_gdpr_category("workspace_memberships") == CATEGORY_B_MUTABLE


def test_build_gdpr_deletion_plan_deletes_mutable_refs_and_preserves_immutable_history() -> None:
    request = GdprDeletionRequest(
        deletion_request_id="gdpr-001",
        user_ref="userref_abc123",
        requested_by_ref="operatorref_001",
        object_storage_refs=("s3://nexa/private/userref_abc123/file.pdf",),
        raw_identity_hint="person@example.com",
    )

    plan = build_gdpr_deletion_plan(request)
    payload = plan.as_payload()
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["status"] == GDPR_DELETION_STATUS_PLANNED
    assert "person@example.com" not in serialized
    assert "workspace_memberships" in serialized
    assert "user_subscriptions" in serialized
    assert "file_uploads" in serialized
    assert "execution_record" in serialized
    assert any(action.action_type == GDPR_ACTION_DELETE_MUTABLE_ROWS and action.target == "workspace_memberships" for action in plan.actions)
    assert any(action.action_type == GDPR_ACTION_DELETE_OBJECT for action in plan.actions)
    assert any(action.action_type == GDPR_ACTION_PRESERVE_IMMUTABLE_HISTORY and action.target == "execution_record" for action in plan.actions)
    assert "user_deletion_audit" in payload["audit_record"]["permanent_audit_tables_preserved"]


def test_gdpr_deletion_plan_rejects_direct_identity_refs() -> None:
    with pytest.raises(GdprDeletionPolicyError, match="must be opaque"):
        GdprDeletionRequest(
            deletion_request_id="gdpr-raw-email",
            user_ref="person@example.com",
            requested_by_ref="operatorref_001",
        )

    with pytest.raises(GdprDeletionPolicyError, match="must be opaque"):
        GdprDeletionRequest(
            deletion_request_id="gdpr-clerk",
            user_ref="userref_ok",
            requested_by_ref="clerk_user_123",
        )


def test_gdpr_deletion_plan_rejects_attempt_to_delete_immutable_history_tables() -> None:
    request = GdprDeletionRequest(
        deletion_request_id="gdpr-bad-table",
        user_ref="userref_abc123",
        requested_by_ref="operatorref_001",
        mutable_table_names=("workspace_memberships", "execution_record"),
    )

    with pytest.raises(GdprDeletionPolicyError, match="immutable history"):
        build_gdpr_deletion_plan(request)


def test_execute_gdpr_deletion_plan_calls_only_mutable_object_identity_and_audit_boundaries() -> None:
    request = GdprDeletionRequest(
        deletion_request_id="gdpr-exec-001",
        user_ref="userref_abc123",
        requested_by_ref="operatorref_001",
        mutable_table_names=("workspace_memberships", "user_subscriptions"),
        object_storage_refs=("s3://nexa/private/userref_abc123/file.pdf",),
    )
    plan = build_gdpr_deletion_plan(request)
    mutable_deletes: list[tuple[str, str]] = []
    object_deletes: list[str] = []
    identity_deletes: list[str] = []
    audits: list[dict] = []

    result = execute_gdpr_deletion_plan(
        plan,
        mutable_row_deleter=lambda table, user_ref: mutable_deletes.append((table, user_ref)) or 2,
        object_storage_deleter=lambda object_ref: object_deletes.append(object_ref) or True,
        identity_deleter=lambda user_ref: identity_deletes.append(user_ref) or True,
        audit_writer=lambda audit: audits.append(dict(audit)),
    )

    assert result.status == GDPR_DELETION_STATUS_COMPLETED
    assert identity_deletes == ["userref_abc123"]
    assert mutable_deletes == [
        ("workspace_memberships", "userref_abc123"),
        ("user_subscriptions", "userref_abc123"),
    ]
    assert object_deletes == ["s3://nexa/private/userref_abc123/file.pdf"]
    assert audits and audits[0]["status"] == GDPR_DELETION_STATUS_COMPLETED
    completed_text = json.dumps(result.as_payload(), sort_keys=True)
    assert "delete_mutable_rows" in completed_text
    assert "execution_record" in completed_text
    assert "deleted_count" in completed_text


def test_execute_gdpr_deletion_plan_writes_failed_audit_without_mutating_immutable_history() -> None:
    request = GdprDeletionRequest(
        deletion_request_id="gdpr-exec-fail",
        user_ref="userref_abc123",
        requested_by_ref="operatorref_001",
        mutable_table_names=("workspace_memberships",),
    )
    plan = build_gdpr_deletion_plan(request)
    audits: list[dict] = []

    def _failing_deleter(table: str, user_ref: str) -> int:
        raise RuntimeError("database failed with sk-secret")

    result = execute_gdpr_deletion_plan(
        plan,
        mutable_row_deleter=_failing_deleter,
        object_storage_deleter=lambda object_ref: True,
        audit_writer=lambda audit: audits.append(dict(audit)),
    )

    assert result.status == GDPR_DELETION_STATUS_FAILED
    assert result.error_code == "RuntimeError"
    assert audits and audits[0]["status"] == GDPR_DELETION_STATUS_FAILED
    serialized = json.dumps(result.as_payload(), sort_keys=True)
    assert "sk-secret" not in serialized
    assert "execution_record" in serialized
    assert "preserve_immutable_history" not in json.dumps(result.completed_actions, sort_keys=True)


def test_audit_writer_failure_is_reported_without_retrying_immutable_mutation() -> None:
    request = GdprDeletionRequest(
        deletion_request_id="gdpr-audit-fail",
        user_ref="userref_abc123",
        requested_by_ref="operatorref_001",
        mutable_table_names=("workspace_memberships",),
    )
    plan = build_gdpr_deletion_plan(request)

    def _bad_audit_writer(_audit):
        raise RuntimeError("audit unavailable")

    result = execute_gdpr_deletion_plan(
        plan,
        mutable_row_deleter=lambda table, user_ref: 1,
        object_storage_deleter=lambda object_ref: True,
        audit_writer=_bad_audit_writer,
    )

    assert result.status == GDPR_DELETION_STATUS_FAILED
    assert result.error_code == "audit_write_failed"
    assert result.audit_record.status == GDPR_DELETION_STATUS_FAILED
