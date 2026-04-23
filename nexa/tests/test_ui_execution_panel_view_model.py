from __future__ import annotations

from src.contracts.execution_event_contract import ExecutionEvent
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
    OutputResultCard,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.execution_panel import read_execution_panel_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "draft"}], edges=[], entry="draft", outputs=[{"name": "out", "source": "draft"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _record(*, status: str = "completed", trigger_type: str = "manual_run") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status=status,
            title="Demo Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type=trigger_type),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(
            total_duration_ms=5000,
            event_count=4,
            node_order=["draft", "judge"],
            started_nodes=[NodeTimingCard(node_id="draft", started_at="2026-04-07T00:00:00Z", outcome="success")],
            completed_nodes=[NodeTimingCard(node_id="draft", finished_at="2026-04-07T00:00:02Z", outcome="success")],
            trace_ref="trace://run-001",
            event_stream_ref="events://run-001",
        ),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="draft", status="success", output_summary="draft ready")]),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="final", source_node="draft", value_summary="done", value_type="text")], output_summary="done"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="artifact::1", artifact_type="final_output", producer_node="draft", hash="abc")], artifact_count=1),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(provider_usage_summary={"openai": 1}, plugin_usage_summary={"normalize": 2}),
    )


def test_read_execution_panel_view_model_projects_historical_execution_record() -> None:
    vm = read_execution_panel_view_model(_record())

    assert vm.source_mode == "execution_record"
    assert vm.storage_role == "execution_record"
    assert vm.execution_status == "completed"
    assert vm.run_identity.run_id == "run-001"
    assert vm.progress.progress_mode == "node_count"
    assert vm.metrics.artifact_count == 1
    assert vm.control_state.can_replay is True
    assert vm.latest_outputs[0].value_summary == "done"



def test_read_execution_panel_view_model_projects_live_execution_context() -> None:
    record = _record(status="running")
    live_events = [
        ExecutionEvent("execution_started", "run-001", None, 0, {}),
        ExecutionEvent("node_started", "run-001", "draft", 10, {"stage": "provider"}),
    ]

    vm = read_execution_panel_view_model(_working_save(), execution_record=record, live_events=live_events)

    assert vm.source_mode == "live_execution"
    assert vm.execution_status == "running"
    assert vm.active_context.active_node_id == "draft"
    assert vm.recent_events[-1].event_type == "node_started"
    assert vm.control_state.can_cancel is True



def test_read_execution_panel_view_model_surfaces_idle_runnable_state_without_execution_record() -> None:
    vm = read_execution_panel_view_model(_working_save())

    assert vm.execution_status == "idle"
    assert vm.storage_role == "working_save"
    assert vm.control_state.can_run is True
    assert vm.control_state.can_replay is False



def test_read_execution_panel_view_model_exposes_record_output_payload_when_available() -> None:
    record = ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-002",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status="completed",
            title="Payload Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=5000, event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="final", source_node="draft", value_summary="done", value_payload={"answer": "ok"}, value_type="json")], output_summary="done"),
        artifacts=ExecutionArtifactsModel(artifact_count=0),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )

    vm = read_execution_panel_view_model(record)

    assert vm.latest_outputs[0].full_value == """{
  "answer": "ok"
}"""
    assert vm.latest_outputs[0].display_mode == "structured"
    assert vm.latest_outputs[0].preview_items == ["answer: ok"]
    assert vm.latest_outputs[0].item_count == 1
    assert vm.latest_outputs[0].copy_action_label == "Copy result"
    assert vm.latest_outputs[0].is_copyable is True
    assert vm.latest_outputs[0].streaming_in_progress is False


def test_read_execution_panel_view_model_projects_live_partial_and_final_outputs() -> None:
    record = _record(status="running")
    live_events = [
        ExecutionEvent("execution_started", "run-001", None, 0, {}),
        ExecutionEvent("token_chunk", "run-001", "draft", 5, {"output_ref": "final", "chunk": "Hel"}),
        ExecutionEvent("token_chunk", "run-001", "draft", 6, {"output_ref": "final", "chunk": "lo"}),
        ExecutionEvent("partial_output", "run-001", "draft", 7, {"output_ref": "final", "value": "Hello", "value_type": "text"}),
        ExecutionEvent("final_output", "run-001", "draft", 8, {"output_ref": "final", "value": "Hello world", "value_type": "text", "value_summary": "Hello world"}),
    ]

    vm = read_execution_panel_view_model(_working_save(), execution_record=record, live_events=live_events)

    assert vm.latest_outputs[0].output_ref == "final"
    assert vm.latest_outputs[0].full_value == "Hello world"
    assert vm.latest_outputs[0].display_mode == "text"
    assert vm.latest_outputs[0].copy_action_label == "Copy result"
    assert vm.latest_outputs[0].is_copyable is True
    assert vm.latest_outputs[0].streaming_in_progress is False


def test_read_execution_panel_view_model_projects_list_outputs_and_artifact_link() -> None:
    record = ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-003",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status="completed",
            title="List Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=5000, event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="final", source_node="draft", value_summary="3 items", value_payload=["alpha", "beta", "gamma"], value_type="list")], output_summary="3 items"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="artifact::result", ref="artifact://result", artifact_type="final_output", producer_node="draft", hash="abc")], artifact_count=1),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )

    vm = read_execution_panel_view_model(record)

    assert vm.latest_outputs[0].display_mode == "list"
    assert vm.latest_outputs[0].preview_items == ["alpha", "beta", "gamma"]
    assert vm.latest_outputs[0].item_count == 3
    assert vm.latest_outputs[0].artifact_ref == "artifact://result"
    assert vm.latest_outputs[0].open_artifact_action_label == "Open artifact"


def test_execution_panel_surfaces_policy_validation_warning_from_working_save_last_run() -> None:
    working_save = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "draft"}], edges=[], entry="draft", outputs=[{"name": "out", "source": "draft"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(
            status="draft",
            validation_summary={},
            last_run={
                "policy_validation": {
                    "status": "invalid",
                    "reason": "negative_weight",
                    "fallback_applied": True,
                }
            },
            errors=[],
        ),
        ui=UIModel(layout={}, metadata={}),
    )

    vm = read_execution_panel_view_model(working_save)

    signal = next(signal for signal in vm.governance_signals if signal.family == "policy_validation")
    assert signal.status == "invalid"
    assert signal.reason_code == "negative_weight"
    assert signal.severity == "warning"
    assert signal.label == "Policy validation"
    assert "Safe defaults were applied" in (signal.summary or "")


def test_execution_panel_surfaces_policy_validation_warning_from_execution_record_recovery_metrics() -> None:
    record = ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status="completed",
            title="Demo Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=5000, event_count=4, node_order=["draft", "judge"]),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="draft", status="success", output_summary="draft ready")]),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="final", source_node="draft", value_summary="done", value_type="text")], output_summary="done"),
        artifacts=ExecutionArtifactsModel(artifact_count=0),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(
            metrics={
                "recovery": {
                    "policy_validation": {
                        "status": "invalid",
                        "reason": "zero_total_weight",
                        "fallback_applied": True,
                    }
                }
            },
            provider_usage_summary={"openai": 1},
            plugin_usage_summary={"normalize": 2},
        ),
    )

    vm = read_execution_panel_view_model(record)

    signal = next(signal for signal in vm.governance_signals if signal.family == "policy_validation")
    assert signal.reason_code == "zero_total_weight"
    assert signal.severity == "warning"


def test_read_execution_panel_view_model_surfaces_result_reading_summary_for_completed_result() -> None:
    record = ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-004",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status="completed",
            title="Readable Result Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=5000, event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="final", source_node="draft", value_summary="Answer ready", value_payload="Hello world", value_type="text")], output_summary="Answer ready"),
        artifacts=ExecutionArtifactsModel(artifact_count=0),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )

    vm = read_execution_panel_view_model(record)

    assert vm.result_reading.visible is True
    assert vm.result_reading.state == "ready"
    assert vm.result_reading.title == "Result ready"
    assert vm.result_reading.summary == "Answer ready"
    assert vm.result_reading.primary_text == "Hello world"
    assert vm.result_reading.copy_action_label == "Copy result"


def test_read_execution_panel_view_model_surfaces_result_reading_summary_for_partial_stream() -> None:
    record = _record(status="running")
    live_events = [
        ExecutionEvent("token_chunk", "run-001", "draft", 5, {"output_ref": "final", "chunk": "Hel"}),
        ExecutionEvent("token_chunk", "run-001", "draft", 6, {"output_ref": "final", "chunk": "lo"}),
    ]

    vm = read_execution_panel_view_model(_working_save(), execution_record=record, live_events=live_events)

    assert vm.result_reading.visible is True
    assert vm.result_reading.state == "partial"
    assert vm.result_reading.title == "Partial result"
    assert vm.result_reading.primary_text == "Hello"
