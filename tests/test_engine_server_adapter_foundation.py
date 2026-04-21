from __future__ import annotations

from src.contracts.artifact_contract import make_typed_artifact
from src.contracts.nex_contract import ValidationFinding
from src.contracts.execution_event_contract import ExecutionEvent
from src.server import (
    ArtifactReferenceAdapter,
    EngineLaunchAdapter,
    EngineStatusProjectionAdapter,
    ExecutionRecordResultAdapter,
    TraceEventAdapter,
    ValidationFindingAdapter,
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


def _record(*, status: str = "completed") -> ExecutionRecordModel:
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
    elif status == "paused":
        warnings = [
            ExecutionIssue(
                issue_code="runtime.review_required",
                category="runtime",
                severity="medium",
                location="review_node",
                message="Review required before continue",
            )
        ]
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-10T12:00:00Z",
            started_at="2026-04-10T12:00:01Z",
            finished_at="2026-04-10T12:00:30Z" if status != "running" else None,
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
            termination_reason="review_required" if status == "paused" else None,
            pause_boundary={"can_resume": True, "pause_node_id": "review_node"} if status == "paused" else None,
        ),
        observability=ExecutionObservabilityModel(metrics={"duration_ms": 29000, "cost_estimate": 0.08}),
    )


def test_engine_launch_adapter_creates_boundary_request_and_binding_without_hidden_mutation() -> None:
    request = EngineLaunchAdapter.build_request(
        run_request_id="req-001",
        workspace_ref="ws-123",
        target_type="commit_snapshot",
        target_ref="snap-456",
        input_payload={"question": "hello"},
        strict_determinism=True,
        trigger_source="webhook",
        automation_id="auto-001",
        auth_context_ref="auth-ctx-1",
        requested_by_user_ref="user-1",
        correlation_metadata={"request_path": "/api/runs"},
    )

    original_state = {"existing": {"safe": True}}
    binding = EngineLaunchAdapter.to_execution_binding(
        request,
        circuit={"id": "circuit-1", "nodes": []},
        state=original_state,
    )

    assert request.runtime_options.trigger_source == "event"
    assert binding.to_circuit_runner_kwargs() == {
        "strict_determinism": True,
        "trigger_source": "event",
        "automation_id": "auto-001",
    }
    assert binding.launch_metadata["run_request_id"] == "req-001"
    assert binding.launch_metadata["execution_target"]["target_ref"] == "snap-456"
    assert binding.input_payload == {"question": "hello"}
    assert binding.state == original_state
    assert binding.state is not original_state
    assert "input" not in binding.state


def test_validation_finding_adapter_preserves_code_severity_and_blocking() -> None:
    findings = [
        ValidationFinding(
            code="VAL_BLOCK",
            category="structural",
            severity="high",
            blocking=True,
            location="circuit.entry",
            message="Entry missing",
            hint="Add entry",
        ),
        ValidationFinding(
            code="VAL_WARN",
            category="runtime_section",
            severity="medium",
            blocking=False,
            location="runtime.status",
            message="Status is stale",
        ),
    ]

    envelope = ValidationFindingAdapter.from_findings(findings)

    assert envelope.overall_status == "blocked"
    assert envelope.blocking_count == 1
    assert envelope.warning_count == 1
    assert [item.code for item in envelope.findings] == ["VAL_BLOCK", "VAL_WARN"]
    assert envelope.findings[0].hint == "Add entry"


def test_artifact_reference_adapter_projects_record_and_typed_artifact() -> None:
    record_ref = ArtifactReferenceAdapter.from_artifact_record(
        ArtifactRecordCard(
            artifact_id="artifact::text::1",
            artifact_type="text",
            producer_node="final_node",
            hash="hash-1",
            ref="artifact://run-001/1",
            lineage_refs=["lineage-1"],
            trace_refs=["trace://run-001#1"],
            validation_status="valid",
            metadata={"label": "Primary"},
        ),
        run_id="run-001",
    )

    typed = make_typed_artifact(
        artifact_type="text",
        producer_ref="node.final_node",
        payload="hello world",
        trace_refs=["trace://run-001#typed"],
        lineage_refs=["lineage-typed"],
    )
    typed_ref = ArtifactReferenceAdapter.from_typed_artifact_envelope(typed, run_id="run-001")

    assert record_ref.artifact_id == "artifact::text::1"
    assert record_ref.run_id == "run-001"
    assert record_ref.metadata == {"label": "Primary"}
    assert typed_ref.artifact_type == "text"
    assert typed_ref.trace_refs == ["trace://run-001#typed"]
    assert typed_ref.lineage_refs == ["lineage-typed"]


def test_trace_event_adapter_projects_execution_event_and_dict_trace_event() -> None:
    execution_event = ExecutionEvent.now(
        "node_started",
        payload={"severity": "info", "message": "Started"},
        execution_id="run-001",
        node_id="node-a",
    )
    projected = TraceEventAdapter.from_execution_event(execution_event, sequence=3)
    assert projected.event_id == f"run-001:3:node_started"
    assert projected.sequence == 3
    assert projected.node_id == "node-a"
    assert projected.message == "Started"

    projected_dict = TraceEventAdapter.from_trace_event_dict(
        {
            "id": "evt-1",
            "type": "execution_failed",
            "timestamp_ms": 12345,
            "node_id": "node-b",
            "severity": "high",
            "message": "Failed",
            "payload": {"reason": "boom"},
        },
        sequence=4,
    )
    assert projected_dict.event_id == "evt-1"
    assert projected_dict.event_type == "execution_failed"
    assert projected_dict.payload == {"reason": "boom"}


def test_execution_record_result_adapter_projects_success_and_failure_envelopes() -> None:
    success = ExecutionRecordResultAdapter.from_execution_record(_record(status="completed"))
    assert success.result_state == "ready_success"
    assert success.final_status == "completed"
    assert success.final_output is not None
    assert success.final_output.output_key == "result"
    assert success.trace_ref == "events://run-001"
    assert success.artifact_refs[0].artifact_id == "artifact::text::1"

    failure = ExecutionRecordResultAdapter.from_execution_record(_record(status="failed"))
    assert failure.result_state == "ready_failure"
    assert failure.final_status == "failed"
    assert failure.failure_info is not None
    assert failure.failure_info.code == "runtime.node_failed"


def test_engine_status_projection_adapter_projects_progress_and_signals_truthfully() -> None:
    running_record = _record(status="running")
    running_snapshot = EngineStatusProjectionAdapter.from_execution_record(running_record)
    assert running_snapshot.status == "running"
    assert running_snapshot.progress_percent == 0
    assert running_snapshot.progress_summary == "Completed 0 of 2 nodes"
    assert running_snapshot.latest_signal is None

    paused_record = _record(status="paused")
    paused_snapshot = EngineStatusProjectionAdapter.from_execution_record(paused_record)
    assert paused_snapshot.status == "paused"
    assert paused_snapshot.active_node_id == "review_node"
    assert paused_snapshot.latest_signal is not None
    assert paused_snapshot.latest_signal.code == "runtime.review_required"
