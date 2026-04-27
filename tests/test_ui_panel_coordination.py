from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.designer_panel import read_designer_panel_view_model
from src.ui.artifact_viewer import read_artifact_viewer_view_model
from src.ui.trace_timeline_viewer import read_trace_timeline_view_model
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
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="summary")], artifact_count=1, artifact_summary="1 artifact"),
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



def test_panel_coordination_defaults_to_inspector_when_graph_selection_exists_and_no_active_panel_is_set() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-002", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_node_ids": ["n1"]}),
    )

    graph = read_graph_view_model(source)
    vm = read_panel_coordination_state(source, graph_view=graph)

    assert vm.active_panel == "inspector"
    assert vm.selection.primary_ref == "node:n1"


def test_panel_coordination_defaults_commit_snapshot_to_storage_when_no_explicit_panel_is_set() -> None:
    vm = read_panel_coordination_state(_commit())
    assert vm.active_panel == "storage"


def test_panel_coordination_defaults_execution_record_to_execution_when_no_explicit_panel_is_set() -> None:
    vm = read_panel_coordination_state(_run())
    assert vm.active_panel == "execution"


def test_panel_coordination_prefers_artifact_panel_when_artifact_selection_exists() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-003", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_artifact_ids": ["art-1"], "user_mode": "advanced"}),
    )
    validation = read_validation_panel_view_model(source, validation_report=_validation())
    execution = read_execution_panel_view_model(source, execution_record=_run(status="completed"))
    trace = read_trace_timeline_view_model(_run(status="completed"))
    artifact = read_artifact_viewer_view_model(_run(status="completed"), selected_artifact_id="art-1")

    vm = read_panel_coordination_state(source, validation_view=validation, execution_view=execution, trace_view=trace, artifact_view=artifact)

    assert vm.active_panel == "artifact"
    assert "artifact" in vm.visible_panels
    assert any(b.panel_id == "artifact" for b in vm.panel_badges)


def test_panel_coordination_prefers_trace_timeline_when_trace_selection_exists() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-004", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_trace_event_ids": ["event-1"], "user_mode": "advanced"}),
    )
    execution = read_execution_panel_view_model(source, execution_record=_run(status="completed"))
    trace = read_trace_timeline_view_model(_run(status="completed"))

    vm = read_panel_coordination_state(source, execution_view=execution, trace_view=trace)

    assert vm.active_panel == "trace_timeline"
    assert "trace_timeline" in vm.visible_panels
    assert any(b.panel_id == "trace_timeline" for b in vm.panel_badges)


def test_panel_coordination_defaults_empty_beginner_workspace_to_designer_and_hides_advanced_panels() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty Draft"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"visible_panels": ["graph", "designer", "diff", "trace_timeline", "artifact"]}),
    )
    graph = read_graph_view_model(source)
    designer = read_designer_panel_view_model(source)

    vm = read_panel_coordination_state(source, graph_view=graph, designer_view=designer)

    assert vm.active_panel == "designer"
    assert vm.visible_panels == ["designer"]
    assert "diff" not in vm.visible_panels
    assert "trace_timeline" not in vm.visible_panels
    assert "artifact" not in vm.visible_panels


def test_panel_coordination_unlocks_advanced_panels_after_first_success() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty-2", name="Empty Draft"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={
            "beginner_first_success_achieved": True,
            "visible_panels": ["graph", "designer", "diff", "trace_timeline", "artifact"],
        }),
    )
    graph = read_graph_view_model(source)
    designer = read_designer_panel_view_model(source)
    execution = read_execution_panel_view_model(source, execution_record=_run(status="completed"))
    trace = read_trace_timeline_view_model(_run(status="completed"))
    artifact = read_artifact_viewer_view_model(_run(status="completed"), selected_artifact_id="art-1")

    vm = read_panel_coordination_state(
        source,
        graph_view=graph,
        designer_view=designer,
        execution_view=execution,
        trace_view=trace,
        artifact_view=artifact,
    )

    assert "diff" in vm.visible_panels
    assert "trace_timeline" in vm.visible_panels
    assert "artifact" in vm.visible_panels


def test_panel_coordination_locks_deep_panels_for_nonempty_beginner_workspace_before_first_success() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-beginner-nonempty", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={
            "active_panel": "artifact",
            "selected_artifact_ids": ["art-1"],
            "visible_panels": ["graph", "inspector", "designer", "storage", "result_history", "diff", "trace_timeline", "artifact"],
            "pinned_panels": ["storage", "trace_timeline", "designer"],
            "panel_order": ["graph", "storage", "result_history", "artifact", "designer"],
        }),
    )
    graph = read_graph_view_model(source)
    designer = read_designer_panel_view_model(source)
    storage = read_storage_view_model(source)
    trace = read_trace_timeline_view_model(_run(status="completed"))
    artifact = read_artifact_viewer_view_model(_run(status="completed"), selected_artifact_id="art-1")

    vm = read_panel_coordination_state(
        source,
        graph_view=graph,
        designer_view=designer,
        storage_view=storage,
        trace_view=trace,
        artifact_view=artifact,
    )

    assert vm.active_panel == "inspector"
    assert "graph" in vm.visible_panels
    assert "inspector" in vm.visible_panels
    assert "designer" in vm.visible_panels
    assert "storage" not in vm.visible_panels
    assert "result_history" not in vm.visible_panels
    assert "diff" not in vm.visible_panels
    assert "trace_timeline" not in vm.visible_panels
    assert "artifact" not in vm.visible_panels
    assert "storage" not in vm.pinned_panels
    assert "trace_timeline" not in vm.pinned_panels
    assert all(badge.panel_id not in {"storage", "result_history", "diff", "trace_timeline", "artifact"} for badge in vm.panel_badges)
