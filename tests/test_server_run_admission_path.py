from __future__ import annotations

from src.server import (
    EngineLaunchAdapter,
    EngineValidationFinding,
    ExecutionTargetCatalogEntry,
    ProductAdmissionPolicy,
    ProductClientContext,
    ProductExecutionTarget,
    ProductRunLaunchRequest,
    RequestAuthResolver,
    RunAdmissionService,
    WorkspaceAuthorizationContext,
    build_initial_server_migration,
    get_server_schema_families,
)


def _auth_context(*, user_id: str = "user-owner"):
    return RequestAuthResolver.resolve(
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-http-1"},
        session_claims={"sub": user_id, "sid": "sess-001", "exp": 500, "roles": ["editor"]},
        now_epoch_s=100,
    )


def _workspace() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        viewer_user_refs=("user-viewer",),
    )


def _commit_snapshot(ref: str = "snap-001") -> dict:
    return {
        "meta": {
            "format_version": "0.1.0",
            "storage_role": "commit_snapshot",
            "commit_id": ref,
        },
        "circuit": {"nodes": [], "edges": [], "entry": "n1", "outputs": [{"name": "x", "source": "state.working.x"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "validation": {"validation_result": "passed", "summary": {}},
        "approval": {"approval_completed": True, "approval_status": "approved", "summary": {}},
        "lineage": {"parent_commit_id": None, "metadata": {}},
    }


def _working_save(ref: str = "ws-save-001") -> dict:
    return {
        "meta": {
            "format_version": "0.1.0",
            "storage_role": "working_save",
            "working_save_id": ref,
        },
        "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
        "ui": {"layout": {}, "metadata": {}},
    }


def test_run_admission_accepts_approved_snapshot_and_builds_engine_request_and_run_record() -> None:
    request = ProductRunLaunchRequest(
        workspace_id="ws-001",
        execution_target=ProductExecutionTarget(target_type="approved_snapshot", target_ref="snap-001"),
        input_payload={"question": "hello"},
        client_context=ProductClientContext(source="web", request_id="req-client-1"),
    )
    outcome = RunAdmissionService.admit(
        request=request,
        request_auth=_auth_context(),
        workspace_context=_workspace(),
        target_catalog={
            "snap-001": ExecutionTargetCatalogEntry(
                workspace_id="ws-001",
                target_ref="snap-001",
                target_type="approved_snapshot",
                source=_commit_snapshot("snap-001"),
            )
        },
        run_id_factory=lambda: "run-001",
        now_iso="2026-04-11T12:00:00+00:00",
    )

    assert outcome.accepted is True
    assert outcome.accepted_response is not None
    assert outcome.accepted_response.run_id == "run-001"
    assert outcome.accepted_response.execution_target.target_type == "commit_snapshot"
    assert outcome.engine_request is not None
    assert outcome.engine_request.execution_target.target_type == "commit_snapshot"
    assert outcome.engine_request.execution_target.target_ref == "snap-001"
    assert outcome.run_record is not None
    assert outcome.run_record.to_row()["execution_target_type"] == "commit_snapshot"
    assert outcome.run_record.to_row()["execution_target_ref"] == "snap-001"
    assert outcome.run_record.status == "queued"
    assert outcome.run_record.status_family == "pending"


def test_run_admission_blocks_unauthenticated_product_launch_before_engine_boundary() -> None:
    anonymous = RequestAuthResolver.resolve(headers={"Authorization": "Bearer token"}, session_claims=None, now_epoch_s=100)
    request = ProductRunLaunchRequest(
        workspace_id="ws-001",
        execution_target=ProductExecutionTarget(target_type="approved_snapshot", target_ref="snap-001"),
    )
    outcome = RunAdmissionService.admit(
        request=request,
        request_auth=anonymous,
        workspace_context=_workspace(),
        target_catalog={"snap-001": ExecutionTargetCatalogEntry(workspace_id="ws-001", target_ref="snap-001", source=_commit_snapshot("snap-001"))},
    )

    assert outcome.accepted is False
    assert outcome.rejected_response is not None
    assert outcome.rejected_response.failure_family == "product_rejection"
    assert outcome.rejected_response.reason_code == "launch.authentication_required"
    assert outcome.engine_request is None


def test_run_admission_blocks_working_save_execution_when_policy_disables_it() -> None:
    request = ProductRunLaunchRequest(
        workspace_id="ws-001",
        execution_target=ProductExecutionTarget(target_type="working_save", target_ref="ws-save-001"),
    )
    outcome = RunAdmissionService.admit(
        request=request,
        request_auth=_auth_context(),
        workspace_context=_workspace(),
        target_catalog={"ws-save-001": ExecutionTargetCatalogEntry(workspace_id="ws-001", target_ref="ws-save-001", source=_working_save("ws-save-001"))},
        policy=ProductAdmissionPolicy(allow_working_save_execution=False),
    )

    assert outcome.accepted is False
    assert outcome.rejected_response is not None
    assert outcome.rejected_response.reason_code == "launch.working_save_execution_disabled"


def test_run_admission_preserves_engine_rejection_separately_from_product_rejection() -> None:
    request = ProductRunLaunchRequest(
        workspace_id="ws-001",
        execution_target=ProductExecutionTarget(target_type="approved_snapshot", target_ref="snap-001"),
    )

    def _engine_reject(_request):
        return EngineLaunchAdapter.rejected(
            findings=[
                EngineValidationFinding(
                    code="VAL_BLOCK",
                    category="structural",
                    severity="high",
                    blocking=True,
                    message="Entry missing",
                    location="circuit.entry",
                )
            ],
            engine_error_code="engine.validation.blocked",
            engine_message="Engine refused launch",
        )

    outcome = RunAdmissionService.admit(
        request=request,
        request_auth=_auth_context(),
        workspace_context=_workspace(),
        target_catalog={"snap-001": ExecutionTargetCatalogEntry(workspace_id="ws-001", target_ref="snap-001", source=_commit_snapshot("snap-001"))},
        engine_launch_decider=_engine_reject,
    )

    assert outcome.accepted is False
    assert outcome.rejected_response is not None
    assert outcome.rejected_response.failure_family == "engine_rejection"
    assert outcome.rejected_response.reason_code == "launch.engine_rejected"
    assert outcome.rejected_response.engine_error_code == "engine.validation.blocked"
    assert outcome.rejected_response.blocking_findings[0]["code"] == "VAL_BLOCK"
    assert outcome.run_record is None


def test_run_records_schema_and_migration_now_include_execution_target_and_status_family_fields() -> None:
    families = get_server_schema_families()
    run_records = next(table for family in families for table in family.tables if table.name == "run_records")
    column_names = {column.name for column in run_records.columns}
    index_names = {index.name for index in run_records.indexes}
    migration = build_initial_server_migration()
    statements = migration.steps[0].statements

    assert {"execution_target_type", "execution_target_ref", "status_family", "latest_error_family", "trace_available"}.issubset(column_names)
    assert "idx_run_records_execution_target" in index_names
    joined = "\n".join(statements)
    assert "execution_target_type TEXT NOT NULL" in joined
    assert "execution_target_ref TEXT NOT NULL" in joined
    assert "status_family TEXT" in joined
    assert "trace_available BOOLEAN NOT NULL DEFAULT FALSE" in joined
