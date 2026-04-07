from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_workflow_hub import read_builder_workflow_hub_view_model
from src.ui.command_routing import read_builder_command_routing_view_model
from src.ui.interaction_transitions import read_builder_interaction_transition_view_model


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


def _validation() -> ValidationReport:
    return ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed")


def test_interaction_transition_switches_to_runtime_monitoring_for_run_action() -> None:
    workflow_hub = read_builder_workflow_hub_view_model(_working_save(), validation_report=_validation(), execution_record=_run())
    routing = read_builder_command_routing_view_model(
        _working_save(),
        action_schema=workflow_hub.shell.action_schema,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination,
    )

    transition = read_builder_interaction_transition_view_model(
        _working_save(),
        command_routing=routing,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination,
        selected_action_id="run_current",
    )

    assert transition.can_transition is True
    assert transition.target_workspace_id == "runtime_monitoring"
    assert transition.target_panel_id == "execution"
    assert transition.transition_kind in {"switch_workspace", "focus_panel", "stay"}
    assert transition.transition_status_label == "준비됨"
    assert transition.transition_kind_label in {"작업공간 전환", "패널 집중", "현재 보기 유지"}


def test_interaction_transition_uses_recommended_action_when_none_is_selected() -> None:
    workflow_hub = read_builder_workflow_hub_view_model(_working_save(), validation_report=_validation(), execution_record=_run())
    routing = read_builder_command_routing_view_model(
        _working_save(),
        action_schema=workflow_hub.shell.action_schema,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination,
    )
    transition = read_builder_interaction_transition_view_model(
        _working_save(),
        command_routing=routing,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination,
    )

    assert transition.recommended_action_id is not None
    assert transition.selected_action_id == transition.recommended_action_id
    assert transition.transition_status_label == "준비됨"
