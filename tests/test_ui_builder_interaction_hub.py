from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_interaction_hub import read_builder_interaction_hub_view_model
from src.engine.execution_event import ExecutionEvent


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def _run(status: str = "completed") -> ExecutionRecordModel:
    finished = None if status in {"running", "queued"} else "2026-04-06T00:00:05Z"
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at=finished, status=status),
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


def test_builder_interaction_hub_exposes_recommended_action_and_transition() -> None:
    hub = read_builder_interaction_hub_view_model(_working_save(), validation_report=_validation(), execution_record=_run())
    assert hub.workflow_hub is not None
    assert hub.command_routing is not None
    assert hub.interaction_transition is not None
    assert hub.enabled_command_count >= 1
    assert hub.recommended_action_id == hub.interaction_transition.recommended_action_id
    assert hub.active_workspace_label == "비주얼 에디터"


def test_builder_interaction_hub_prefers_runtime_monitoring_during_live_run() -> None:
    live_events = [ExecutionEvent("execution_started", "run-001", None, 0, {})]
    hub = read_builder_interaction_hub_view_model(
        _working_save(),
        validation_report=_validation(),
        execution_record=_run("running"),
        live_events=live_events,
    )
    assert hub.active_workspace_id == "runtime_monitoring"
    assert hub.recommended_action_id in {"cancel_run", "open_diff", "replay_latest", "run_current"}
    assert hub.active_workspace_label == "런타임 모니터링"



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


def test_builder_interaction_hub_prefers_run_from_commit_for_commit_snapshot() -> None:
    hub = read_builder_interaction_hub_view_model(_commit())
    assert hub.recommended_action_id == "run_from_commit"
    assert hub.interaction_transition is not None
    assert hub.interaction_transition.target_workspace_id == "runtime_monitoring"
    assert hub.interaction_transition.target_panel_id == "execution"


def test_builder_interaction_hub_prefers_open_latest_run_for_execution_record() -> None:
    hub = read_builder_interaction_hub_view_model(_run())
    assert hub.recommended_action_id == "open_latest_run"
    assert hub.interaction_transition is not None
    assert hub.interaction_transition.target_workspace_id == "runtime_monitoring"
    assert hub.interaction_transition.target_panel_id == "execution"



def test_builder_interaction_hub_marks_blocked_when_selected_transition_is_blocked() -> None:
    failed_validation = ValidationReport(role="working_save", findings=[], blocking_count=1, warning_count=0, result="failed")
    hub = read_builder_interaction_hub_view_model(
        _working_save(),
        validation_report=failed_validation,
        execution_record=_run(),
        selected_action_id="run_current",
    )
    assert hub.interaction_transition is not None
    assert hub.interaction_transition.transition_status == "blocked"
    assert hub.hub_status == "blocked"


def test_builder_interaction_hub_surfaces_attention_when_routing_is_attention() -> None:
    hub = read_builder_interaction_hub_view_model(_working_save(), validation_report=_validation(), execution_record=_run())
    assert hub.command_routing is not None
    assert hub.command_routing.routing_status == "attention"
    assert hub.hub_status == "attention"


def test_builder_interaction_hub_propagates_terminal_status_for_execution_record() -> None:
    hub = read_builder_interaction_hub_view_model(_run())
    assert hub.hub_status == "terminal"


def test_builder_interaction_hub_respects_workflow_attention_state() -> None:
    hub = read_builder_interaction_hub_view_model(
        _working_save(),
        validation_report=_validation(),
        execution_record=_run(),
    )
    assert hub.workflow_hub is not None
    assert hub.workflow_hub.hub_status in {"attention", "ready"}
    assert hub.hub_status == "attention"
