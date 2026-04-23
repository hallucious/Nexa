from __future__ import annotations

from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
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
    NodeResultsModel,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.interaction_state_changes import read_interaction_state_change_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
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


def test_interaction_state_changes_project_workspace_panel_and_lifecycle_changes() -> None:
    vm = read_interaction_state_change_view_model(_working_save())

    assert vm.source_role == "working_save"
    assert vm.enabled_change_count >= 1
    run_change = next((item for item in vm.changes if item.action_id == "run_current"), None)
    assert run_change is not None
    assert run_change.target_stage_id == "execution"
    assert run_change.target_workspace_id == "runtime_monitoring"
    assert run_change.state_change_kind_label == "라이프사이클 전환"
    assert vm.state_change_status_label == "주의 필요"


def test_interaction_state_changes_map_run_from_commit_to_execution_stage() -> None:
    vm = read_interaction_state_change_view_model(_commit())

    change = next((item for item in vm.changes if item.action_id == "run_from_commit"), None)
    assert change is not None
    assert change.target_stage_id == "execution"
    assert change.target_workspace_id == "runtime_monitoring"
    assert change.target_panel_id == "execution"


def test_interaction_state_changes_map_execution_record_actions_to_history_stage() -> None:
    vm = read_interaction_state_change_view_model(_run())

    latest_run_change = next((item for item in vm.changes if item.action_id == "open_latest_run"), None)
    trace_change = next((item for item in vm.changes if item.action_id == "open_trace"), None)
    artifact_change = next((item for item in vm.changes if item.action_id == "open_artifacts"), None)

    assert latest_run_change is not None
    assert latest_run_change.target_stage_id == "history"
    assert latest_run_change.target_workspace_id == "runtime_monitoring"
    assert latest_run_change.target_panel_id == "execution"

    assert trace_change is not None
    assert trace_change.target_stage_id == "history"
    assert trace_change.target_panel_id == "trace_timeline"

    assert artifact_change is not None
    assert artifact_change.target_stage_id == "history"
    assert artifact_change.target_panel_id == "artifact"
