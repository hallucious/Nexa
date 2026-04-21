from __future__ import annotations

from src.contracts.execution_event_contract import ExecutionEvent
from src.server import (
    ExecutionTargetCatalogEntry,
    ProductExecutionTarget,
    ProductRunLaunchRequest,
    ProductClientContext,
    QueueSubmission,
    RequestAuthResolver,
    RunAdmissionService,
    WorkerLeasePolicy,
    WorkerQueueOrchestrationService,
    WorkspaceAuthorizationContext,
    build_initial_server_migration,
    get_server_schema_families,
)
from src.storage.models.execution_record_model import (
    ArtifactRecordCard,
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionIssue,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultsModel,
    OutputResultCard,
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


def _admitted_outcome():
    request = ProductRunLaunchRequest(
        workspace_id="ws-001",
        execution_target=ProductExecutionTarget(target_type="approved_snapshot", target_ref="snap-001"),
        input_payload={"question": "hello"},
        client_context=ProductClientContext(source="web", request_id="req-client-1"),
    )
    return RunAdmissionService.admit(
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


def _execution_record(*, status: str = "completed") -> ExecutionRecordModel:
    artifact = ArtifactRecordCard(
        artifact_id="artifact::text::1",
        artifact_type="text",
        producer_node="final_node",
        hash="abc123",
        ref="artifact://run-001/artifact::text::1",
        summary="Reviewed answer",
        producer_ref="node.final_node",
        validation_status="valid",
        lineage_refs=["lineage-1"],
        trace_refs=["events://run-001#artifact:1"],
        metadata={"label": "Reviewed answer"},
    )
    warnings = []
    errors = []
    if status == "failed":
        errors = [
            ExecutionIssue(
                issue_code="runtime.node_failed",
                category="runtime",
                severity="high",
                location="final_node",
                message="Final node failed",
            )
        ]
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-10T12:00:00Z",
            started_at="2026-04-10T12:00:01Z",
            finished_at="2026-04-10T12:00:30Z",
            status=status,
            title="Review completed",
            description="A sample record",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(input_summary={"question": "What changed?"}),
        timeline=ExecutionTimelineModel(
            total_duration_ms=29000,
            event_count=2,
            node_order=["draft_node", "final_node"],
            completed_nodes=["draft_node", "final_node"] if status == "completed" else ["draft_node"],
            trace_ref="trace://run-001",
            event_stream_ref="events://run-001",
        ),
        node_results=NodeResultsModel(results=[]),
        outputs=ExecutionOutputModel(
            final_outputs=[
                OutputResultCard(
                    output_ref="result",
                    source_node="final_node",
                    value_summary="The document argues that quality improved.",
                    value_payload={"text": "The document argues that quality improved."},
                    value_type="text",
                    value_ref="artifact://run-001/output/result",
                )
            ],
            output_summary="1 output(s) recorded",
            semantic_status="normal",
        ),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[artifact],
            artifact_count=1,
            artifact_summary="1 artifact ref(s) recorded",
        ),
        diagnostics=ExecutionDiagnosticsModel(
            warnings=warnings,
            errors=errors,
            failure_point="final_node" if status == "failed" else None,
        ),
        observability=ExecutionObservabilityModel(metrics={"duration_ms": 29000, "cost_estimate": 0.08}),
    )


def test_worker_queue_schema_and_migration_include_queue_jobs_and_liveness_columns() -> None:
    families = get_server_schema_families()
    run_records = next(table for family in families for table in family.tables if table.name == "run_records")
    queue_jobs = next(table for family in families for table in family.tables if table.name == "queue_jobs")
    run_columns = {column.name for column in run_records.columns}
    queue_columns = {column.name for column in queue_jobs.columns}
    migration = build_initial_server_migration()
    joined = "\n".join(migration.steps[0].statements)

    assert {"queue_job_id", "claimed_by_worker_ref", "lease_expires_at", "last_heartbeat_at", "worker_attempt_number", "orphan_review_required"}.issubset(run_columns)
    assert {"queue_job_id", "queue_state", "queue_name", "available_at", "worker_attempt_number"}.issubset(queue_columns)
    assert "CREATE TABLE IF NOT EXISTS queue_jobs" in joined
    assert "claimed_by_worker_ref TEXT" in joined


def test_queue_submission_and_claim_create_starting_run_with_lease_metadata() -> None:
    admission = _admitted_outcome()
    submission = WorkerQueueOrchestrationService.enqueue_admitted_run(
        admission,
        queue_job_id_factory=lambda: "job-001",
        now_iso="2026-04-11T12:01:00+00:00",
    )
    claim = WorkerQueueOrchestrationService.claim_submitted_run(
        submission,
        worker_ref="worker-a",
        lease_policy=WorkerLeasePolicy(lease_duration_s=30, heartbeat_extension_s=45, max_worker_attempts=3),
        now_iso="2026-04-11T12:01:10+00:00",
    )

    assert isinstance(submission, QueueSubmission)
    assert submission.queue_job.queue_state == "queued"
    assert submission.run_record_row["queue_job_id"] == "job-001"
    assert claim.queue_job.queue_state == "claimed"
    assert claim.run_record_row["status"] == "starting"
    assert claim.run_record_row["claimed_by_worker_ref"] == "worker-a"
    assert claim.run_record_row["worker_attempt_number"] == 1
    assert claim.run_record_row["lease_expires_at"] == "2026-04-11T12:01:40+00:00"


def test_worker_heartbeat_refreshes_liveness_without_inventing_progress() -> None:
    admission = _admitted_outcome()
    submission = WorkerQueueOrchestrationService.enqueue_admitted_run(admission, queue_job_id_factory=lambda: "job-001", now_iso="2026-04-11T12:01:00+00:00")
    claim = WorkerQueueOrchestrationService.claim_submitted_run(
        submission,
        worker_ref="worker-a",
        lease_policy=WorkerLeasePolicy(lease_duration_s=30, heartbeat_extension_s=60, max_worker_attempts=3),
        now_iso="2026-04-11T12:01:10+00:00",
    )
    refreshed = WorkerQueueOrchestrationService.refresh_heartbeat(claim, now_iso="2026-04-11T12:01:25+00:00")

    assert refreshed.run_record_row["status"] == "starting"
    assert refreshed.run_record_row["status_family"] == "pending"
    assert refreshed.run_record_row["last_heartbeat_at"] == "2026-04-11T12:01:25+00:00"
    assert refreshed.run_record_row["lease_expires_at"] == "2026-04-11T12:02:25+00:00"


def test_orphan_review_and_requeue_keep_worker_failure_distinct() -> None:
    admission = _admitted_outcome()
    submission = WorkerQueueOrchestrationService.enqueue_admitted_run(admission, queue_job_id_factory=lambda: "job-001", now_iso="2026-04-11T12:01:00+00:00")
    claim = WorkerQueueOrchestrationService.claim_submitted_run(
        submission,
        worker_ref="worker-a",
        lease_policy=WorkerLeasePolicy(lease_duration_s=30, heartbeat_extension_s=45, max_worker_attempts=3, requeue_orphans=True),
        now_iso="2026-04-11T12:01:10+00:00",
    )
    review = WorkerQueueOrchestrationService.review_orphaned_claim(claim, now_iso="2026-04-11T12:01:45+00:00")
    recovered = WorkerQueueOrchestrationService.recover_orphaned_claim(
        claim,
        review,
        queue_job_id_factory=lambda: "job-002",
        now_iso="2026-04-11T12:01:46+00:00",
    )

    assert review.is_orphaned is True
    assert recovered.failure_family == "worker_infrastructure_failure"
    assert recovered.run_record_row["status"] == "queued"
    assert recovered.run_record_row["latest_error_family"] == "worker_infrastructure_failure"
    assert recovered.run_record_row["orphan_review_required"] is True
    assert recovered.queue_job_row["queue_job_id"] == "job-002"
    assert recovered.queue_job_row["queue_state"] == "queued"


def test_worker_completion_projects_terminal_result_artifacts_and_trace_rows() -> None:
    admission = _admitted_outcome()
    submission = WorkerQueueOrchestrationService.enqueue_admitted_run(admission, queue_job_id_factory=lambda: "job-001", now_iso="2026-04-11T12:01:00+00:00")
    claim = WorkerQueueOrchestrationService.claim_submitted_run(submission, worker_ref="worker-a", now_iso="2026-04-11T12:01:10+00:00")
    event = ExecutionEvent(
        type="node_completed",
        execution_id="run-001",
        node_id="final_node",
        timestamp_ms=1712836870000,
        payload={"severity": "info", "message": "Final node completed"},
        trigger_source="manual",
        automation_id=None,
    )
    bundle = WorkerQueueOrchestrationService.complete_claimed_run(
        claim,
        execution_record=_execution_record(status="completed"),
        trace_events=[event],
        now_iso="2026-04-11T12:01:40+00:00",
    )

    assert bundle.run_record_row["status"] == "completed"
    assert bundle.run_record_row["status_family"] == "terminal_success"
    assert bundle.run_record_row["artifact_count"] == 1
    assert bundle.run_record_row["trace_event_count"] == 1
    assert bundle.queue_job_row["queue_state"] == "completed"
    assert bundle.result_row is not None
    assert bundle.result_row["result_state"] == "ready_success"
    assert bundle.artifact_rows[0]["artifact_id"] == "artifact::text::1"
    assert bundle.trace_rows[0]["event_type"] == "node_completed"


def test_worker_infrastructure_failure_is_not_labeled_as_engine_failure() -> None:
    admission = _admitted_outcome()
    submission = WorkerQueueOrchestrationService.enqueue_admitted_run(admission, queue_job_id_factory=lambda: "job-001", now_iso="2026-04-11T12:01:00+00:00")
    claim = WorkerQueueOrchestrationService.claim_submitted_run(submission, worker_ref="worker-a", now_iso="2026-04-11T12:01:10+00:00")
    bundle = WorkerQueueOrchestrationService.mark_infrastructure_failure(
        claim,
        reason_code="worker.bootstrap_failure",
        message="Worker bootstrap failed before engine execution could begin.",
        now_iso="2026-04-11T12:01:20+00:00",
    )

    assert bundle.failure_family == "worker_infrastructure_failure"
    assert bundle.run_record_row["latest_error_family"] == "worker_infrastructure_failure"
    assert bundle.result_row is not None
    assert bundle.result_row["failure_info"]["code"] == "worker.bootstrap_failure"
