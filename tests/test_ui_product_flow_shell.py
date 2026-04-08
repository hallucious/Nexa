from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview, ConfirmationPreview, GraphViewModel, SummaryCard, StructuralPreview
from src.designer.models.circuit_patch_plan import ChangeScope, CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import AvailableResources, ConversationContext, CurrentSelectionState, DesignerSessionStateCard, SessionTargetScope, WorkingSaveReality
from src.designer.models.validation_precheck import AmbiguityAssessmentReport, CostAssessmentReport, EvaluatedScope, ResolutionReport, ValidationPrecheck, ValidityReport
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultCard, NodeResultsModel, NodeTimingCard, OutputResultCard
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.product_flow_shell import read_product_flow_shell_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Product Flow Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1", "label": "Draft Generator"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={"run_id": "run-001"}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_node_ids": ["n1"], "active_panel": "designer", "app_language": "ko-KR"}),
    )


def _validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN", category="structural", severity="medium", blocking=False, location="node:n1", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def _run_running() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-08T00:00:00Z", started_at="2026-04-08T00:00:00Z", status="running"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(
            total_duration_ms=500,
            event_count=1,
            node_order=["n1"],
            started_nodes=[NodeTimingCard(node_id="n1", started_at="2026-04-08T00:00:01Z")],
            completed_nodes=[],
        ),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="n1", status="partial")]),
        outputs=ExecutionOutputModel(output_summary="in progress", final_outputs=[OutputResultCard(output_ref="result", source_node="n1", value_summary="in progress", value_ref="art-1")]),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="artifact summary")], artifact_count=1, artifact_summary="1 artifact"),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _run_completed() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-002", record_format_version="1.0.0", created_at="2026-04-08T00:00:00Z", started_at="2026-04-08T00:00:00Z", finished_at="2026-04-08T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=2),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="n1", status="success")]),
        outputs=ExecutionOutputModel(output_summary="done", final_outputs=[OutputResultCard(output_ref="result", source_node="n1", value_summary="done", value_ref="art-1")]),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="artifact summary")], artifact_count=1, artifact_summary="1 artifact"),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _session_card() -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-001",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(mode="existing_draft", savefile_ref="working_save:ws-001", circuit_summary="single node"),
        current_selection=CurrentSelectionState(selection_mode="node", selected_refs=("node:n1",)),
        target_scope=SessionTargetScope(mode="existing_circuit"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Improve it"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Improve node"),
    )


def _intent() -> DesignerIntent:
    return DesignerIntent(
        intent_id="intent-001",
        category="MODIFY_CIRCUIT",
        user_request_text="Improve node",
        target_scope=TargetScope(mode="existing_circuit", savefile_ref="working_save:ws-001"),
        objective=ObjectiveSpec(primary_goal="Improve it"),
        constraints=ConstraintSet(),
        proposed_actions=(),
        assumptions=(),
        ambiguity_flags=(),
        risk_flags=(),
        requires_user_confirmation=False,
        confidence=0.8,
        explanation="improve node",
    )


def _patch() -> CircuitPatchPlan:
    return CircuitPatchPlan(
        patch_id="patch-001",
        patch_mode="modify_existing",
        summary="modify node",
        intent_ref="intent-001",
        change_scope=ChangeScope(scope_level="bounded", touch_mode="structural_edit", touched_nodes=("n1",)),
        operations=(PatchOperation(op_id="op-1", op_type="update_node_metadata", target_ref="node:n1"),),
        target_savefile_ref="working_save:ws-001",
    )


def _precheck() -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="pre-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch", touched_nodes=("n1",)),
        overall_status="pass",
        structural_validity=ValidityReport(status="valid"),
        dependency_validity=ValidityReport(status="valid"),
        input_output_validity=ValidityReport(status="valid"),
        provider_resolution=ResolutionReport(status="resolved"),
        plugin_resolution=ResolutionReport(status="resolved"),
        safety_review=ValidityReport(status="valid"),
        cost_assessment=CostAssessmentReport(status="acceptable"),
        ambiguity_assessment=AmbiguityAssessmentReport(status="clear"),
    )


def _preview() -> CircuitDraftPreview:
    return CircuitDraftPreview(
        preview_id="preview-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_mode="patch_modify",
        summary_card=SummaryCard(title="modify", one_sentence_summary="modify node", proposal_type="modify", change_scope="bounded", touched_node_count=1, touched_edge_count=0, touched_output_count=0),
        structural_preview=StructuralPreview(before_exists=True, before_node_count=1, after_node_count=1, before_edge_count=0, after_edge_count=0, modified_nodes=("n1",)),
        confirmation_preview=ConfirmationPreview(required_confirmations=(), auto_commit_allowed=False),
        graph_view_model=GraphViewModel(node_count=1, edge_count=0),
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


def test_product_flow_shell_prioritizes_live_execution_control_plane_navigation() -> None:
    vm = read_product_flow_shell_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run_running(),
        selected_artifact_id="art-1",
    )

    assert vm.stage.stage_id == "run"
    assert vm.shell_status == "live_run"
    assert vm.focus.active_workspace_id == "runtime_monitoring"
    assert vm.focus.active_right_panel_id == "execution"
    assert vm.focus.active_bottom_panel_id == "trace_timeline"
    assert vm.stage.visible_event_count >= 1
    assert vm.stage.visible_artifact_count == 1
    assert vm.e2e_path is not None
    assert vm.e2e_path.path_status in {"followthrough", "terminal", "actionable"}
    assert vm.closure is not None
    assert any(target.target_id == "artifact" for target in vm.bottom_dock_targets)
    assert vm.command_entry_count > 0


def test_product_flow_shell_prioritizes_review_diff_and_designer_when_approval_is_open() -> None:
    vm = read_product_flow_shell_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run_completed(),
        preview_overlay=GraphPreviewOverlay(overlay_id="preview-ov-1", preview_ref="preview:001", summary="preview"),
        selected_ref="node:n1",
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.stage.stage_id == "review"
    assert vm.shell_status == "review_focus"
    assert vm.focus.active_workspace_id == "node_configuration"
    assert vm.focus.active_right_panel_id == "designer"
    assert vm.focus.active_bottom_panel_id == "diff"
    assert vm.e2e_path is not None
    assert vm.workflow_hub is not None
    assert vm.dispatch_hub is not None
    assert vm.execution_adapter_hub is not None
    assert vm.end_user_flow_hub is not None
    assert vm.journey is not None
    assert vm.journey.current_step_id == "commit_snapshot"
    assert vm.transition is not None
    assert vm.transition.recommended_transition_id == "approval_to_commit"
    assert vm.gateway is not None
    assert vm.gateway.recommended_gateway_id == "commit"
    assert vm.stage.pending_approval_count >= 1
    assert vm.closure is not None
    assert any(target.target_id == "diff" and target.active for target in vm.bottom_dock_targets)


def test_product_flow_shell_exposes_runbook_and_prefers_runbook_action_when_review_chain_is_open() -> None:
    vm = read_product_flow_shell_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run_completed(),
        preview_overlay=GraphPreviewOverlay(overlay_id="preview-ov-2", preview_ref="preview:002", summary="preview"),
        selected_ref="node:n1",
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.runbook is not None
    assert vm.runbook.current_entry_id == "commit_snapshot"
    assert vm.readiness is not None
    assert vm.readiness.current_boundary_id == "commit"
    assert vm.handoff is not None
    assert vm.closure is not None
    assert vm.transition is not None
    assert vm.gateway is not None
    assert vm.handoff.primary_entry_id == "commit_snapshot"
    assert vm.handoff.followthrough_entry_id == "run_current"
    assert vm.focus.recommended_action_id == "commit_snapshot"
    assert vm.transition.next_action_id == "commit_snapshot"
    assert vm.focus.focus_reason == "handoff_primary"
