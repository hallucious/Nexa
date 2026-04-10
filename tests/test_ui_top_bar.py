from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.top_bar import read_builder_top_bar_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Strategy Review"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )




def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )

def _run(status: str = "running") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-08T00:00:00Z", started_at="2026-04-08T00:00:00Z", finished_at=None if status == "running" else "2026-04-08T00:00:05Z", status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="blocked")],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )


def _approval() -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_ref="preview-001",
        current_stage="awaiting_decision",
        final_outcome="approved_for_commit",
    )


def test_top_bar_projects_role_status_actions_and_modes() -> None:
    source = _working_save()
    execution_vm = read_execution_panel_view_model(source, execution_record=_run())
    vm = read_builder_top_bar_view_model(
        source,
        validation_report=_validation_report(),
        execution_record=_run(),
        execution_view=execution_vm,
        approval_flow=_approval(),
    )
    assert vm.source_role == "working_save"
    assert vm.breadcrumb.workspace_title == "Strategy Review"
    assert vm.storage_badge.label == "워킹 세이브"
    assert vm.global_status.overall_status == "blocked"
    assert vm.global_status.blocking_count == 1
    assert vm.global_status.pending_approval_count == 1
    assert vm.quick_jump_placeholder == "노드, 문제, 실행, 액션 검색"
    assert any(button.action_id == "run_current" for button in vm.primary_actions)
    assert any(option.mode_id == "run" and option.active for option in vm.mode_options)


def test_top_bar_prioritizes_commit_snapshot_runtime_actions() -> None:
    vm = read_builder_top_bar_view_model(_commit())
    action_ids = [button.action_id for button in vm.primary_actions]
    assert "run_from_commit" in action_ids
    assert "save_working_save" not in action_ids


def test_top_bar_prioritizes_execution_record_inspection_actions() -> None:
    vm = read_builder_top_bar_view_model(_run())
    action_ids = [button.action_id for button in vm.primary_actions]
    assert "open_latest_run" in action_ids
    assert vm.source_role == "execution_record"
