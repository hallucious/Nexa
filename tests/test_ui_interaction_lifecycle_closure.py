from __future__ import annotations

from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.interaction_lifecycle_closure import read_interaction_lifecycle_closure_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def test_interaction_lifecycle_closure_tracks_stage_closure_and_requirements() -> None:
    vm = read_interaction_lifecycle_closure_view_model(_working_save())

    assert vm.source_role == "working_save"
    assert vm.current_stage_id in {"drafting", "review", "commit", "execution", "history"}
    assert len(vm.stages) == 5
    assert any(stage.open_requirement is not None or stage.closeable for stage in vm.stages)
    assert vm.closure_status_label in {"주의 필요", "차단됨", "준비됨"}
    assert all(stage.stage_label for stage in vm.stages)



def _commit_snapshot() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", name="Approved"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={"blocking_count": 0, "warning_count": 0}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved"),
        lineage=CommitLineageModel(source_working_save_id="ws-001"),
    )


def _execution_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-10T00:00:00Z", started_at="2026-04-10T00:00:00Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=3),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(artifact_count=0, artifact_summary=""),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_interaction_lifecycle_closure_prefers_run_from_commit_for_commit_snapshot_execution_stage() -> None:
    vm = read_interaction_lifecycle_closure_view_model(_commit_snapshot())

    execution_stage = next(stage for stage in vm.stages if stage.stage_id == "execution")
    assert vm.source_role == "commit_snapshot"
    assert execution_stage.recommended_flow_id == "flow:run_from_commit"
    assert execution_stage.open_requirement in {None, "run_from_commit"}


def test_interaction_lifecycle_closure_accepts_role_aware_history_flows_for_execution_record() -> None:
    vm = read_interaction_lifecycle_closure_view_model(_execution_record())

    history_stage = next(stage for stage in vm.stages if stage.stage_id == "history")
    assert vm.source_role == "execution_record"
    assert history_stage.recommended_flow_id in {"flow:open_trace", "flow:open_artifacts", "flow:compare_runs", "flow:open_latest_run"}
    assert history_stage.open_requirement in {None, "open_trace", "open_artifacts", "compare_runs", "open_latest_run"}
