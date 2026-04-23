from __future__ import annotations

from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_end_user_flow_hub import read_builder_end_user_flow_hub_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def test_builder_end_user_flow_hub_unifies_user_flows_and_lifecycle_closure() -> None:
    vm = read_builder_end_user_flow_hub_view_model(_working_save())

    assert vm.source_role == "working_save"
    assert vm.end_user_flows is not None
    assert vm.lifecycle_closure is not None
    assert vm.executable_flow_count == vm.end_user_flows.enabled_flow_count
    assert vm.hub_status_label == "주의 필요"



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


def test_builder_end_user_flow_hub_marks_execution_record_terminal() -> None:
    vm = read_builder_end_user_flow_hub_view_model(_execution_record())

    assert vm.source_role == "execution_record"
    assert vm.hub_status == "terminal"
