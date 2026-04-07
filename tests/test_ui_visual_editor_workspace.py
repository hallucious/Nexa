from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import GraphViewModel
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.visual_editor_workspace import read_visual_editor_workspace_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}, {"id": "n2"}], edges=[{"from": "n1", "to": "n2"}], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_node_ids": ["n2"], "app_language": "ko-KR"}),
    )


def _validation() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN_LINK", category="structural", severity="medium", blocking=False, location="edge:n1->n2", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def test_visual_editor_workspace_projects_phase5_editor_surface() -> None:
    overlay = GraphPreviewOverlay(
        overlay_id="preview-1",
        summary="add review node",
        added_node_ids=["n3"],
        updated_node_ids=["n2"],
        removed_edge_ids=["edge_0:n1->n2"],
    )

    vm = read_visual_editor_workspace_view_model(
        _working_save(),
        validation_report=_validation(),
        preview_overlay=overlay,
    )

    assert vm.workspace_status == "previewing"
    assert vm.storage_role == "working_save"
    assert vm.graph is not None
    assert vm.canvas_summary.node_count == 2
    assert vm.canvas_summary.selected_node_count == 1
    assert vm.canvas_summary.preview_change_count == 3
    assert vm.can_edit_graph is True
    assert vm.can_preview_changes is True
    assert vm.comparison_state.viewer_status == "ready"
    assert vm.action_schema.source_role == "working_save"
    assert vm.workspace_status_label == "변경 미리보기 중"
