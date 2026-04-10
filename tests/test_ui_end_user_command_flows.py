from __future__ import annotations

from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.end_user_command_flows import read_end_user_command_flow_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def test_end_user_command_flows_project_engine_safe_user_flows() -> None:
    vm = read_end_user_command_flow_view_model(_working_save())

    assert vm.source_role == "working_save"
    assert vm.enabled_flow_count >= 1
    assert any(flow.action_id == "save_working_save" for flow in vm.flows)
    review_flow = next(flow for flow in vm.flows if flow.action_id == "review_draft")
    assert review_flow.preferred_workspace_id == "node_configuration"
    assert review_flow.steps[0].step_id == "intent"


def test_end_user_command_flows_localize_step_labels_for_korean_app_language() -> None:
    working = _working_save()
    working.ui.metadata["app_language"] = "ko-KR"

    vm = read_end_user_command_flow_view_model(working)
    review_flow = next(flow for flow in vm.flows if flow.action_id == "review_draft")

    assert review_flow.steps[0].label == "의도 생성"



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


def test_end_user_command_flows_mark_execution_record_history_flows_as_terminal() -> None:
    vm = read_end_user_command_flow_view_model(_execution_record())

    assert vm.source_role == "execution_record"
    assert vm.flow_status == "terminal"
    assert any(flow.flow_status == "terminal" and flow.target_stage_id == "history" for flow in vm.flows)
