from __future__ import annotations

from src.server import (
    EngineResultEnvelope,
    EngineRunStatusSnapshot,
    EngineSignal,
    RequestAuthResolver,
    RunResultReadService,
    RunStatusReadService,
    RunAuthorizationContext,
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


def _run_context(*, owner: str = "user-owner") -> RunAuthorizationContext:
    return RunAuthorizationContext(
        run_id="run-001",
        workspace_context=_workspace(),
        run_owner_user_ref=owner,
    )


def _run_row(*, status: str = "running", status_family: str = "active") -> dict:
    return {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-001",
        "status": status,
        "status_family": status_family,
        "created_at": "2026-04-11T12:00:00+00:00",
        "started_at": "2026-04-11T12:00:05+00:00",
        "updated_at": "2026-04-11T12:00:10+00:00",
        "finished_at": None,
        "requested_by_user_id": "user-owner",
        "trace_available": False,
    }


def test_run_result_schema_and_migration_include_run_result_index() -> None:
    families = get_server_schema_families()
    result_index = next(table for family in families for table in family.tables if table.name == "run_result_index")
    column_names = {column.name for column in result_index.columns}
    migration = build_initial_server_migration()
    joined = "\n".join(migration.steps[0].statements)

    assert {"run_id", "workspace_id", "result_state", "final_status", "result_summary", "updated_at"}.issubset(column_names)
    assert "CREATE TABLE IF NOT EXISTS run_result_index" in joined
    assert "result_state TEXT NOT NULL" in joined


def test_status_read_uses_engine_snapshot_without_fabricating_progress() -> None:
    outcome = RunStatusReadService.read_status(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=_run_row(status="running", status_family="active"),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=(_run_row(status="running", status_family="active"),),
        provider_binding_rows=({"workspace_id": "ws-001", "binding_id": "binding-001", "updated_at": "2026-04-11T12:03:00+00:00"},),
        managed_secret_rows=({"workspace_id": "ws-001", "secret_ref": "secret://ws-001/openai", "last_rotated_at": "2026-04-11T12:04:00+00:00"},),
        provider_probe_rows=({"workspace_id": "ws-001", "probe_event_id": "probe-001", "provider_key": "openai", "provider_family": "openai", "display_name": "OpenAI", "probe_status": "reachable", "connectivity_state": "ok", "occurred_at": "2026-04-11T12:05:00+00:00"},),
        onboarding_rows=({"workspace_id": "ws-001", "user_id": "user-owner", "onboarding_state_id": "onboard-001", "updated_at": "2026-04-11T12:06:00+00:00"},),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="review_bundle",
            active_node_label="Review Bundle",
            progress_percent=42,
            progress_summary="Running review stage",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Review Bundle is currently executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.status == "running"
    assert outcome.response.workspace_title == "Primary Workspace"
    assert outcome.response.provider_continuity is not None
    assert outcome.response.provider_continuity.provider_binding_count == 1
    assert outcome.response.activity_continuity is not None
    assert outcome.response.activity_continuity.recent_onboarding_count == 1
    assert outcome.response.status_family == "active"
    assert outcome.response.progress is not None
    assert outcome.response.progress.percent == 42
    assert outcome.response.latest_engine_signal is not None
    assert outcome.response.links.result == "/api/runs/run-001/result"


def test_status_read_returns_visibility_gap_only_when_status_projection_missing() -> None:
    row = _run_row(status="", status_family="unknown")
    outcome = RunStatusReadService.read_status(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=row,
        engine_status=None,
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.status == "unknown"
    assert outcome.response.status_family == "unknown"
    assert outcome.response.message == "Run exists, but current status is temporarily unavailable."


def test_result_read_returns_not_ready_when_no_result_exists_yet() -> None:
    outcome = RunResultReadService.read_result(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=_run_row(status="running", status_family="active"),
        result_row=None,
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.result_state == "not_ready"
    assert outcome.response.message == "The run result is not available yet."
    assert outcome.response.final_status is None


def test_result_read_returns_ready_success_projection_from_rows() -> None:
    outcome = RunResultReadService.read_result(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=_run_row(status="completed", status_family="terminal_success"),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=(_run_row(status="completed", status_family="terminal_success"),),
        provider_binding_rows=({"workspace_id": "ws-001", "binding_id": "binding-001", "updated_at": "2026-04-11T12:03:00+00:00"},),
        managed_secret_rows=({"workspace_id": "ws-001", "secret_ref": "secret://ws-001/openai", "last_rotated_at": "2026-04-11T12:04:00+00:00"},),
        provider_probe_rows=({"workspace_id": "ws-001", "probe_event_id": "probe-001", "provider_key": "openai", "provider_family": "openai", "display_name": "OpenAI", "probe_status": "reachable", "connectivity_state": "ok", "occurred_at": "2026-04-11T12:05:00+00:00"},),
        onboarding_rows=({"workspace_id": "ws-001", "user_id": "user-owner", "onboarding_state_id": "onboard-001", "updated_at": "2026-04-11T12:06:00+00:00"},),
        result_row={
            "run_id": "run-001",
            "workspace_id": "ws-001",
            "result_state": "ready_success",
            "final_status": "completed",
            "result_summary": "The circuit produced a reviewed answer.",
            "trace_ref": "trace://run-001",
            "artifact_count": 1,
            "failure_info": None,
            "final_output": {"output_key": "result", "value_preview": "The document argues that...", "value_type": "text"},
            "metrics": {"duration_ms": 12440, "cost_estimate": 0.08},
            "updated_at": "2026-04-11T12:01:00+00:00",
        },
        artifact_rows=[
            {
                "artifact_id": "art-001",
                "artifact_type": "final_output",
                "payload_preview": "Reviewed answer",
                "metadata_json": {"label": "Reviewed answer"},
            }
        ],
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.result_state == "ready_success"
    assert outcome.response.workspace_title == "Primary Workspace"
    assert outcome.response.provider_continuity is not None
    assert outcome.response.provider_continuity.latest_managed_secret_ref == "secret://ws-001/openai"
    assert outcome.response.activity_continuity is not None
    assert outcome.response.activity_continuity.latest_onboarding_state_id == "onboard-001"
    assert outcome.response.final_status == "completed"
    assert outcome.response.result_summary is not None
    assert outcome.response.result_summary.title == "Run completed"
    assert outcome.response.final_output is not None
    assert outcome.response.final_output.output_key == "result"
    assert outcome.response.artifact_refs[0].artifact_id == "art-001"
    assert outcome.response.trace_ref is not None
    assert outcome.response.trace_ref.endpoint == "/api/runs/run-001/trace"


def test_result_read_can_project_directly_from_engine_result_envelope() -> None:
    outcome = RunResultReadService.read_result(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=_run_row(status="failed", status_family="terminal_failure"),
        engine_result=EngineResultEnvelope(
            run_id="run-001",
            final_status="failed",
            result_state="ready_failure",
            result_summary="Final node failed.",
            trace_ref="trace://run-001",
            metrics={"duration_ms": 2000},
            failure_info=None,
        ),
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.result_state == "ready_failure"
    assert outcome.response.final_status == "failed"
    assert outcome.response.result_summary is not None
    assert outcome.response.result_summary.title == "Run failed"


def test_result_read_rejects_forbidden_caller_before_returning_result_shape() -> None:
    forbidden_auth = RequestAuthResolver.resolve(
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-http-1"},
        session_claims={"sub": "user-stranger", "sid": "sess-001", "exp": 500, "roles": []},
        now_epoch_s=100,
    )
    outcome = RunResultReadService.read_result(
        request_auth=forbidden_auth,
        run_context=_run_context(owner="user-owner"),
        run_record_row=_run_row(status="completed", status_family="terminal_success"),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=(_run_row(status="completed", status_family="terminal_success"),),
        provider_binding_rows=({"workspace_id": "ws-001", "binding_id": "binding-001", "updated_at": "2026-04-11T12:03:00+00:00"},),
        managed_secret_rows=({"workspace_id": "ws-001", "secret_ref": "secret://ws-001/openai", "last_rotated_at": "2026-04-11T12:04:00+00:00"},),
        provider_probe_rows=({"workspace_id": "ws-001", "probe_event_id": "probe-001", "provider_key": "openai", "provider_family": "openai", "display_name": "OpenAI", "probe_status": "reachable", "connectivity_state": "ok", "occurred_at": "2026-04-11T12:05:00+00:00"},),
        onboarding_rows=({"workspace_id": "ws-001", "user_id": "user-owner", "onboarding_state_id": "onboard-001", "updated_at": "2026-04-11T12:06:00+00:00"},),
        result_row={
            "run_id": "run-001",
            "workspace_id": "ws-001",
            "result_state": "ready_success",
            "final_status": "completed",
            "result_summary": "ready",
        },
    )

    assert outcome.ok is False
    assert outcome.rejected is not None
    assert outcome.rejected.failure_family == "product_read_failure"
    assert outcome.rejected.reason_code in {"authorization.workspace_forbidden", "authorization.role_insufficient"}
    assert outcome.rejected.workspace_title == "Primary Workspace"
    assert outcome.rejected.provider_continuity is not None
    assert outcome.rejected.provider_continuity.provider_binding_count == 1
    assert outcome.rejected.activity_continuity is not None
    assert outcome.rejected.activity_continuity.recent_probe_count == 1


def test_status_read_exposes_worker_recovery_projection_for_active_claim() -> None:
    row = _run_row(status="running", status_family="active")
    row.update({
        "queue_job_id": "job-001",
        "claimed_by_worker_ref": "worker-a",
        "lease_expires_at": "2026-04-11T12:02:00+00:00",
        "worker_attempt_number": 1,
        "orphan_review_required": False,
        "latest_error_family": None,
    })

    outcome = RunStatusReadService.read_status(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=row,
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.recovery is not None
    assert outcome.response.recovery.recovery_state == "leased"
    assert outcome.response.recovery.queue_job_id == "job-001"
    assert outcome.response.recovery.worker_attempt_number == 1


def test_result_read_exposes_retry_pending_recovery_when_result_not_ready() -> None:
    row = _run_row(status="queued", status_family="pending")
    row.update({
        "queue_job_id": "job-002",
        "worker_attempt_number": 2,
        "orphan_review_required": False,
        "latest_error_family": "worker_infrastructure_failure",
    })

    outcome = RunResultReadService.read_result(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=row,
        result_row=None,
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.recovery is not None
    assert outcome.response.recovery.recovery_state == "retry_pending"
    assert outcome.response.recovery.worker_attempt_number == 2


def test_result_read_keeps_recovery_projection_on_ready_result_rows() -> None:
    row = _run_row(status="failed", status_family="terminal_failure")
    row.update({
        "queue_job_id": "job-003",
        "worker_attempt_number": 3,
        "orphan_review_required": True,
        "latest_error_family": "worker_infrastructure_failure",
    })

    outcome = RunResultReadService.read_result(
        request_auth=_auth_context(),
        run_context=_run_context(),
        run_record_row=row,
        result_row={
            "run_id": "run-001",
            "workspace_id": "ws-001",
            "result_state": "ready_failure",
            "final_status": "failed",
            "result_summary": "Worker infrastructure failed after retry exhaustion.",
        },
    )

    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.recovery is not None
    assert outcome.response.recovery.recovery_state == "manual_review_required"
    assert outcome.response.recovery.orphan_review_required is True
