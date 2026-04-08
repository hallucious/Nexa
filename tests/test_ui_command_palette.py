from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.command_palette import read_command_palette_view_model
from src.ui.graph_workspace import GraphPreviewOverlay


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Palette Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1", "label": "Draft Generator"}, {"id": "n2", "label": "Final Judge"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={"run_id": "run-001"}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def _validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN", category="structural", severity="medium", blocking=False, location="node:n2", message="check final judge")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def _run() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-08T00:00:00Z", started_at="2026-04-08T00:00:00Z", finished_at="2026-04-08T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=2),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n2", hash="abc123", ref="artifact://art-1", summary="final answer")],
            artifact_count=1,
            artifact_summary="1 artifact",
        ),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
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


def test_command_palette_combines_jump_and_action_entries() -> None:
    vm = read_command_palette_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run(),
        preview_overlay=GraphPreviewOverlay(overlay_id="preview-001", preview_ref="preview:001", summary="preview"),
        approval_flow=_approval(),
    )
    assert vm.source_role == "working_save"
    assert vm.placeholder == "노드, 문제, 실행, 액션 검색"
    assert vm.jump_entry_count > 0
    assert vm.action_entry_count > 0
    labels = {entry.label for entry in vm.entries}
    assert "Draft Generator" in labels
    assert "현재 승인 결정을 열기" in labels
    assert "현재 트레이스 타임라인 열기" in labels
    assert "선택된 아티팩트 열기" in labels
    assert "현재 차이 보기 열기" in labels
    assert any(entry.action_id == "run_current" for entry in vm.entries if entry.entry_type == "action")
