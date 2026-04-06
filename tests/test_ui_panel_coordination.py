from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.designer_panel import read_designer_panel_view_model
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.graph_workspace import read_graph_view_model
from src.ui.panel_coordination import read_panel_coordination_state
from src.ui.storage_panel import read_storage_view_model
from src.ui.validation_panel import read_validation_panel_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={
            "selected_node_ids": ["n1"],
            "active_panel": "designer",
            "visible_panels": ["graph", "validation", "designer"],
            "pinned_panels": ["validation"],
            "panel_order": ["graph", "designer", "validation"],
        }),
    )


def _run(status: str = "running") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status=status),
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
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN", category="structural", severity="medium", blocking=False, location="node:n1", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def test_panel_coordination_projects_selection_active_panel_and_badges() -> None:
    source = _working_save()
    graph = read_graph_view_model(source)
    validation = read_validation_panel_view_model(source, validation_report=_validation())
    execution = read_execution_panel_view_model(source, execution_record=_run())
    designer = read_designer_panel_view_model(source, approval_flow=DesignerApprovalFlowState(approval_id="approval-1", intent_ref="intent-1", patch_ref="patch-1", precheck_ref="pre-1", preview_ref="preview-1", current_stage="awaiting_decision", final_outcome="pending"))
    storage = read_storage_view_model(source)

    vm = read_panel_coordination_state(source, graph_view=graph, validation_view=validation, execution_view=execution, designer_view=designer, storage_view=storage)
    assert vm.active_panel == "designer"
    assert vm.selection.primary_ref == "node:n1"
    assert vm.pinned_panels == ["validation"]
    assert any(b.panel_id == "validation" for b in vm.panel_badges)
    assert any(b.panel_id == "execution" for b in vm.panel_badges)
