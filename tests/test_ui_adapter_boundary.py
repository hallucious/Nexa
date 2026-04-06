from __future__ import annotations

from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.adapter import NexaUIViewAdapter
from src.ui.graph_workspace import GraphPreviewOverlay
from src.engine.execution_event import ExecutionEvent


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )


def _run() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_ui_adapter_routes_read_models_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    preview = GraphPreviewOverlay(overlay_id="preview-001", summary="test preview")

    graph_vm = adapter.read_graph_view_model(_working_save(), preview_overlay=preview)
    storage_vm = adapter.read_storage_view_model(_working_save())
    diff_vm = adapter.read_diff_view_model(diff_mode="draft_vs_commit", source=_working_save(), target=_commit())

    assert graph_vm.storage_role == "execution_record"
    assert storage_vm.active_storage_role == "working_save"
    assert diff_vm.viewer_status == "ready"



def test_ui_adapter_routes_execution_trace_and_artifact_read_models_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    live_events = [
        ExecutionEvent("execution_started", "run-001", None, 0, {}),
        ExecutionEvent("node_started", "run-001", "n1", 5, {"stage": "provider"}),
    ]

    execution_vm = adapter.read_execution_panel_view_model(_working_save(), live_events=live_events)
    trace_vm = adapter.read_trace_timeline_view_model(_run(), live_events=live_events)
    artifact_vm = adapter.read_artifact_viewer_view_model(_run())

    assert execution_vm.source_mode == "live_execution"
    assert trace_vm.source_mode == "live_event_stream"
    assert artifact_vm.viewer_status in {"ready", "partial"}
