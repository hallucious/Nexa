from __future__ import annotations

from src.engine.execution_event import ExecutionEvent
from src.storage.models.execution_record_model import (
    ArtifactRecordCard,
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultCard,
    NodeResultsModel,
    NodeTimingCard,
)
from src.ui.trace_timeline_viewer import read_trace_timeline_view_model


VERIFIER_PAYLOAD = {
    "aggregate_status": "warning",
    "blocking_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"],
}


def _record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-trace-verifier",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:03Z",
            status="completed",
            title="Trace Verifier Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(
            total_duration_ms=3000,
            event_count=4,
            node_order=["draft"],
            started_nodes=[NodeTimingCard(node_id="draft", started_at="2026-04-07T00:00:00Z")],
            completed_nodes=[NodeTimingCard(node_id="draft", finished_at="2026-04-07T00:00:01Z")],
            trace_ref="trace://run-trace-verifier",
            event_stream_ref="events://run-trace-verifier",
        ),
        node_results=NodeResultsModel(
            results=[
                NodeResultCard(
                    node_id="draft",
                    status="success",
                    typed_artifact_refs=["artifact::validation_report::001", "artifact::json_object::001"],
                    verifier_status="warning",
                    verifier_reason_codes=["REQUIREMENT_TEXT_TOO_SHORT"],
                )
            ]
        ),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[
                ArtifactRecordCard(
                    artifact_id="artifact::validation_report::001",
                    artifact_type="validation_report",
                    producer_node="draft",
                    producer_ref="node.draft",
                    ref="artifact://run-trace-verifier/artifact::validation_report::001",
                    summary="verification report (warning)",
                    artifact_schema_version="1.0.0",
                    validation_status="partial",
                    recorded_at="2026-04-07T00:00:01Z",
                    trace_refs=["trace://run-trace-verifier/draft/verifier"],
                    metadata={"report_kind": "verifier", "aggregate_status": "warning"},
                    payload_preview=VERIFIER_PAYLOAD,
                ),
                ArtifactRecordCard(
                    artifact_id="artifact::json_object::001",
                    artifact_type="json_object",
                    producer_node="draft",
                    producer_ref="node.draft",
                    ref="artifact://run-trace-verifier/artifact::json_object::001",
                    summary="final typed output",
                    artifact_schema_version="1.0.0",
                    validation_status="partial",
                    recorded_at="2026-04-07T00:00:01Z",
                    trace_refs=["trace://run-trace-verifier/draft/output"],
                    metadata={"report_kind": "typed_output"},
                    payload_preview={"answer": "tiny"},
                ),
            ],
            artifact_count=2,
            artifact_summary="2 artifact ref(s) recorded",
        ),
        diagnostics=ExecutionDiagnosticsModel(),
        observability=ExecutionObservabilityModel(
            verifier_summary={"verifier_report_count": 1, "status_counts": {"warning": 1}}
        ),
    )



def test_step206_trace_timeline_projects_verifier_events_and_lanes() -> None:
    vm = read_trace_timeline_view_model(_record())

    verification_events = [event for event in vm.events if event.event_type == "verification_completed"]
    assert verification_events
    assert verification_events[0].lane_ref == "verification:draft"
    assert "artifact::validation_report::001" in verification_events[0].artifact_refs
    assert verification_events[0].severity == "warning"
    assert any(lane.lane_type == "verification" and lane.node_id == "draft" for lane in vm.lanes)
    assert any(lane.lane_type == "artifact" and lane.node_id == "draft" for lane in vm.lanes)
    assert vm.summary.verification_event_count == 1
    assert vm.summary.artifact_link_count >= 2



def test_step206_trace_timeline_live_projection_recognizes_verifier_lane() -> None:
    live_events = [
        ExecutionEvent("execution_started", "run-live", None, 0, {}),
        ExecutionEvent(
            "verification_completed",
            "run-live",
            "draft",
            5,
            {
                "status": "warning",
                "artifact_refs": ["artifact::validation_report::001", "artifact::json_object::001"],
            },
        ),
    ]

    vm = read_trace_timeline_view_model(None, live_events=live_events)

    assert any(event.lane_ref == "verification:draft" for event in vm.events)
    assert any(lane.lane_type == "verification" for lane in vm.lanes)
    assert vm.summary.verification_event_count == 1
    assert vm.summary.artifact_link_count == 2
