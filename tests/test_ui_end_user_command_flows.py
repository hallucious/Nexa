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
