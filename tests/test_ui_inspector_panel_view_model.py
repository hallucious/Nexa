from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionIssue, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultCard, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.inspector_panel import read_selected_object_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(
            nodes=[
                {"id": "draft", "type": "provider", "label": "Draft Generator", "inputs": {"question": "state.input.question"}, "outputs": {"draft": "state.working.draft"}},
                {"id": "review_bundle", "kind": "subcircuit", "label": "Review Bundle", "execution": {"subcircuit": {"child_circuit_ref": "internal:review_bundle"}}},
            ],
            edges=[{"from": "draft", "to": "review_bundle", "label": "flows to"}],
            entry="draft",
            outputs=[{"name": "final", "source": "state.working.final"}],
            subcircuits={"review_bundle": {"nodes": [{"id": "child-1"}], "edges": [], "outputs": []}},
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_node_ids": ["review_bundle"]}),
    )


def _commit() -> CommitSnapshotModel:
    working = _working_save()
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=working.circuit,
        resources=working.resources,
        state=working.state,
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )


def _execution_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-07T00:00:00Z", started_at="2026-04-07T00:00:00Z", finished_at="2026-04-07T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="review_bundle", status="failed", output_summary="failed", error_count=1)]),
        outputs=ExecutionOutputModel(),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(errors=[ExecutionIssue(issue_code="RUNTIME_ERROR", category="runtime", severity="high", location="node:review_bundle", message="provider failed")], warnings=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="MISSING_INPUT", category="structural", severity="high", blocking=True, location="node:review_bundle", message="input missing")],
        blocking_count=1,
        warning_count=0,
        result="failed",
    )


def test_read_selected_object_view_model_defaults_to_ui_selection() -> None:
    vm = read_selected_object_view_model(_working_save())
    assert vm.object_type == "node"
    assert vm.object_id == "review_bundle"
    assert vm.title == "Review Bundle"
    assert vm.status_summary.editability == "editable"


def test_read_selected_object_view_model_projects_node_cross_context() -> None:
    overlay = GraphPreviewOverlay(overlay_id="preview-001", summary="update review", updated_node_ids=["review_bundle"])
    vm = read_selected_object_view_model(
        _working_save(),
        selected_ref="node:review_bundle",
        validation_report=_validation_report(),
        execution_record=_execution_record(),
        preview_overlay=overlay,
    )
    assert vm.status_summary.overall_status == "failed"
    assert vm.related_validation_findings
    assert vm.related_execution_findings
    assert vm.related_preview_changes[0].change_type == "updated"
    assert any(field.field_key == "label" for field in vm.editable_fields)


def test_read_selected_object_view_model_projects_output_as_readonly_in_commit_snapshot() -> None:
    vm = read_selected_object_view_model(_commit(), selected_ref="output:final")
    assert vm.object_type == "output"
    assert vm.status_summary.editability == "readonly"
    assert vm.readonly_fields[0].field_key == "source"


def test_read_selected_object_view_model_localizes_field_labels_for_korean_app_language() -> None:
    working = _working_save()
    working.ui.metadata["app_language"] = "ko-KR"

    vm = read_selected_object_view_model(working, selected_ref="node:review_bundle")

    assert vm.readonly_fields[0].label == "노드 ID"
    assert any(constraint.label == "서브회로 경계" for constraint in vm.constraints)


def test_read_selected_object_view_model_defaults_to_execution_record_focus_when_commit_snapshot_has_run_history() -> None:
    vm = read_selected_object_view_model(_commit(), execution_record=_execution_record())

    assert vm.object_type == "node"
    assert vm.object_id == "review_bundle"
    assert vm.status_summary.overall_status == "failed"
    assert vm.status_summary.editability == "readonly"
