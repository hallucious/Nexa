from __future__ import annotations

from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultCard, NodeResultsModel, NodeTimingCard, OutputResultCard
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.contracts.nex_contract import ValidationFinding, ValidationReport
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



def _run_completed() -> ExecutionRecordModel:
    run = _run_running()
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(**{**run.meta.__dict__, "status": "completed", "finished_at": "2026-04-07T00:00:05Z"}),
        source=run.source,
        input=run.input,
        timeline=run.timeline,
        node_results=run.node_results,
        outputs=run.outputs,
        artifacts=run.artifacts,
        diagnostics=run.diagnostics,
        observability=run.observability,
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
    assert vm.readiness.posture == "active_monitoring"
    assert vm.focus_hint.hint_kind == "active_run"
    assert vm.workspace_handoff.destination_workspace == "runtime_monitoring"
    assert vm.action_shortcuts[0].action.action_id == "watch_run_progress"
    assert vm.attention_targets[0].attention_kind == "watch_live_run"
    assert vm.progress_stages[1].stage_id == "monitor"
    assert vm.progress_stages[1].state == "current"
    assert vm.closure_barriers[0].barrier_kind == "run_in_progress"
    assert vm.closure_verdict.closure_state == "hold_runtime_monitoring"



def test_runtime_monitoring_workspace_marks_commit_snapshot_as_launch_ready_when_execution_can_start() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_commit())

    assert vm.storage_role == "commit_snapshot"
    assert vm.workspace_status == "launch_ready"
    assert vm.health.launch_available is True
    assert vm.workspace_status_label == "Launch ready"
    assert vm.readiness.posture == "ready_to_launch"
    assert vm.local_actions[0].action_id == "run_current"
    assert vm.progress_stages[0].stage_id == "launch"
    assert vm.progress_stages[0].state == "current"
    assert vm.closure_barriers[0].barrier_kind == "run_not_started"
    assert vm.closure_verdict.closure_state == "hold_runtime_monitoring"



def test_runtime_monitoring_workspace_marks_execution_record_as_terminal_review_when_not_live() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_run_completed())

    assert vm.storage_role == "execution_record"
    assert vm.workspace_status == "terminal_review"
    assert vm.workspace_status_label == "Terminal history review"
    assert vm.readiness.posture == "terminal_inspection"
    assert vm.focus_hint.hint_kind in {"artifact_review", "timeline_overview"}
    assert vm.progress_stages[2].stage_id == "inspect"
    assert vm.progress_stages[2].state == "current"
    assert vm.closure_verdict.closure_state == "workspace_chain_stable"



def test_runtime_monitoring_workspace_exposes_launch_guidance() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_commit())

    assert vm.workspace_status == "launch_ready"
    assert vm.explanation == "This approved workflow is ready to run. Start it to monitor progress here."



def test_runtime_monitoring_workspace_exposes_terminal_review_guidance() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_run_completed())

    assert vm.workspace_status == "terminal_review"
    assert vm.explanation == "Review the finished run results, outputs, and artifacts here."



def test_runtime_monitoring_workspace_exposes_suggested_actions_for_launch_ready() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_commit())

    assert vm.workspace_status == "launch_ready"
    assert [action.action_id for action in vm.suggested_actions] == [
        "run_current",
        "open_visual_editor",
    ]



def test_runtime_monitoring_workspace_exposes_suggested_actions_for_live_monitoring() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_working_save(), execution_record=_run_running())

    assert vm.workspace_status == "live_monitoring"
    assert [action.action_id for action in vm.suggested_actions] == [
        "watch_run_progress",
        "cancel_run",
        "open_result_history",
    ]



def test_runtime_monitoring_workspace_exposes_suggested_actions_for_terminal_review() -> None:
    vm = read_runtime_monitoring_workspace_view_model(_run_completed())

    assert vm.workspace_status == "terminal_review"
    assert [action.action_id for action in vm.suggested_actions] == [
        "open_result_history",
        "replay_latest",
        "open_feedback_channel",
    ]



def test_runtime_monitoring_workspace_failed_review_holds_workspace_chain() -> None:
    report = ValidationReport(
        role="working_save",
        findings=[
            ValidationFinding(
                code="runtime_block",
                category="runtime",
                severity="error",
                blocking=True,
                location="execution",
                message="Run review still blocked.",
                hint="Inspect the runtime evidence.",
            )
        ],
        blocking_count=1,
        warning_count=0,
        result="fail",
    )
    vm = read_runtime_monitoring_workspace_view_model(_working_save(), execution_record=_run_completed(), validation_report=report)

    assert vm.workspace_status == "failed_review"
    assert vm.readiness.posture == "failure_investigation"
    assert vm.attention_targets[0].attention_kind == "failure_review"
    assert vm.closure_verdict.closure_state == "hold_runtime_monitoring"
