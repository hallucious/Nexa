from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview, ConfirmationPreview, GraphViewModel, SummaryCard, StructuralPreview
from src.designer.models.circuit_patch_plan import ChangeScope, CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import AvailableResources, ConversationContext, CurrentSelectionState, DesignerSessionStateCard, SessionTargetScope, WorkingSaveReality
from src.designer.models.validation_precheck import AmbiguityAssessmentReport, CostAssessmentReport, EvaluatedScope, ResolutionReport, ValidationPrecheck, ValidityReport
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.node_configuration_workspace import read_node_configuration_workspace_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1", "label": "Node 1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _validation() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN_NODE", category="structural", severity="medium", blocking=False, location="node:n1", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
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
        confidence=0.9,
        explanation="improve",
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
        overall_status="pass_with_warnings",
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
    return DesignerApprovalFlowState(approval_id="approval-001", intent_ref="intent-001", patch_ref="patch-001", precheck_ref="pre-001", preview_ref="preview-001", current_stage="awaiting_decision", final_outcome="approved_for_commit")


def test_node_configuration_workspace_projects_phase5_configuration_surface() -> None:
    vm = read_node_configuration_workspace_view_model(
        _working_save(),
        selected_ref="node:n1",
        validation_report=_validation(),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.workspace_status == "designer_review"
    assert vm.storage_role == "working_save"
    assert vm.inspector is not None
    assert vm.validation is not None
    assert vm.designer is not None
    assert vm.selection_summary.object_type == "node"
    assert vm.can_edit_configuration is True
    assert vm.can_submit_designer_request is True
    assert vm.review_state.commit_eligible is True
