from __future__ import annotations

from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultCard, NodeResultsModel, NodeTimingCard, OutputResultCard
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.runtime_monitoring_workspace import read_runtime_monitoring_workspace_view_model




def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )

def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )


def _run_running() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-07T00:00:00Z", started_at="2026-04-07T00:00:00Z", status="running"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(
            total_duration_ms=500,
            event_count=1,
            node_order=["n1"],
            started_nodes=[NodeTimingCard(node_id="n1", started_at="2026-04-07T00:00:01Z")],
            completed_nodes=[],
        ),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="n1", status="partial")]),
        outputs=ExecutionOutputModel(output_summary="in progress", final_outputs=[OutputResultCard(output_ref="result", source_node="n1", value_summary="in progress", value_ref="art-1")]),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="summary")], artifact_count=1, artifact_summary="1 artifact"),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_runtime_monitoring_workspace_projects_phase5_monitoring_surface() -> None:
    vm = read_runtime_monitoring_workspace_view_model(
        _working_save(),
        execution_record=_run_running(),
        selected_artifact_id="art-1",
    )

    assert vm.workspace_status == "live_monitoring"
    assert vm.execution is not None
    assert vm.trace_timeline is not None
    assert vm.artifact is not None
    assert vm.focus.run_id == "run-001"
    assert vm.focus.active_node_id == "n1"
    assert vm.focus.selected_artifact_id == "art-1"
    assert vm.focus.visible_artifact_count == 1
    assert vm.health.cancel_available is True
    assert vm.health.execution_status == "running"
    assert vm.workspace_status_label == "실시간 모니터링"


def test_runtime_monitoring_workspace_marks_commit_snapshot_as_launch_ready_when_execution_can_start() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_commit())

    assert vm.storage_role == "commit_snapshot"
    assert vm.workspace_status == "launch_ready"
    assert vm.health.launch_available is True
    assert vm.workspace_status_label == "Launch ready"
