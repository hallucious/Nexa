from __future__ import annotations

from src.engine.execution_event import ExecutionEvent
from src.storage.models.execution_record_model import (
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


def _record(*, trigger_type: str = "manual_run") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-07T00:00:00Z", started_at="2026-04-07T00:00:00Z", finished_at="2026-04-07T00:00:03Z", status="completed", title="Trace Run"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type=trigger_type),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=3000, event_count=4, node_order=["draft", "judge"], started_nodes=[NodeTimingCard(node_id="draft", started_at="2026-04-07T00:00:00Z")], completed_nodes=[NodeTimingCard(node_id="draft", finished_at="2026-04-07T00:00:01Z")], trace_ref="trace://run-001", event_stream_ref="events://run-001"),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="draft", status="success")]),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_read_trace_timeline_view_model_projects_execution_record_trace() -> None:
    vm = read_trace_timeline_view_model(_record())

    assert vm.source_mode == "execution_record_trace"
    assert vm.storage_role == "execution_record"
    assert vm.timeline_status == "finalized"
    assert vm.summary.total_event_count >= 3
    assert vm.lanes[0].lane_type == "node"
    assert vm.diagnostics.missing_trace_ref is False



def test_read_trace_timeline_view_model_marks_replay_runs_explicitly() -> None:
    vm = read_trace_timeline_view_model(_record(trigger_type="replay_run"))

    assert vm.source_mode == "replay_trace"
    assert vm.replay_state.replay_active is True
    assert vm.run_identity.replay_session_id == "run-001"



def test_read_trace_timeline_view_model_supports_live_event_stream_projection() -> None:
    live_events = [
        ExecutionEvent("execution_started", "run-live", None, 0, {}),
        ExecutionEvent("node_started", "run-live", "draft", 5, {"artifact_refs": ["artifact::1"]}),
    ]

    vm = read_trace_timeline_view_model(None, live_events=live_events)

    assert vm.source_mode == "live_event_stream"
    assert vm.timeline_status == "streaming"
    assert vm.events[-1].relative_offset_ms == 5
    assert vm.summary.artifact_link_count == 1
