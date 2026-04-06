from __future__ import annotations

from src.designer.models.circuit_draft_preview import (
    CircuitDraftPreview,
    ConfirmationPreview,
    CostPreview,
    GraphViewModel,
    SummaryCard,
    StructuralPreview,
)
from src.designer.models.circuit_patch_plan import (
    ChangeScope,
    CircuitPatchPlan,
    PatchOperation,
    PatchRiskReport,
    PreviewRequirements,
    ReversibilitySpec,
    ValidationRequirements,
)
from src.designer.models.designer_approval_flow import ApprovalPolicy, DecisionPoint, DesignerApprovalFlowState, UserDecision
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import (
    AvailableResources,
    ConversationContext,
    CurrentSelectionState,
    ResourceAvailability,
    SessionTargetScope,
    WorkingSaveReality,
    DesignerSessionStateCard,
)
from src.designer.models.validation_precheck import (
    AmbiguityAssessmentReport,
    CostAssessmentReport,
    EvaluatedScope,
    PreviewRequirements as PrecheckPreviewRequirements,
    ResolutionReport,
    ValidationPrecheck,
    ValidityReport,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.designer_panel import read_designer_panel_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "review_bundle"}], edges=[], entry="review_bundle", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _session_card() -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-001",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(mode="existing_draft", savefile_ref="working_save:ws-001", current_revision="rev-1", circuit_summary="1 node", node_list=("review_bundle",)),
        current_selection=CurrentSelectionState(selection_mode="node", selected_refs=("node:review_bundle",)),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded", allowed_node_refs=("review_bundle",)),
        available_resources=AvailableResources(providers=(ResourceAvailability(id="openai:gpt"),), plugins=(ResourceAvailability(id="plugin.search"),)),
        objective=ObjectiveSpec(primary_goal="Improve reliability"),
        constraints=ConstraintSet(safety_level="high", output_requirements="preserve output semantics"),
        conversation_context=ConversationContext(user_request_text="Replace provider and keep the output stable"),
    )


def _intent() -> DesignerIntent:
    return DesignerIntent(
        intent_id="intent-001",
        category="MODIFY_CIRCUIT",
        user_request_text="Replace provider and keep the output stable",
        target_scope=TargetScope(mode="existing_circuit", savefile_ref="working_save:ws-001", max_change_scope="bounded"),
        objective=ObjectiveSpec(primary_goal="Improve reliability"),
        constraints=ConstraintSet(safety_level="high", output_requirements="preserve output semantics"),
        proposed_actions=(),
        assumptions=(),
        ambiguity_flags=(),
        risk_flags=(),
        requires_user_confirmation=False,
        confidence=0.82,
        explanation="Normalize a provider replacement with preserved output semantics.",
    )


def _patch() -> CircuitPatchPlan:
    return CircuitPatchPlan(
        patch_id="patch-001",
        patch_mode="modify_existing",
        summary="Replace provider in review bundle",
        intent_ref="intent-001",
        change_scope=ChangeScope(scope_level="bounded", touch_mode="structural_edit", touched_nodes=("review_bundle",), touched_edges=(), touched_outputs=("final",)),
        operations=(PatchOperation(op_id="op-1", op_type="replace_node_component", target_ref="node:review_bundle", rationale="Switch provider"),),
        risk_report=PatchRiskReport(risks=("provider semantics may change",), requires_confirmation=False),
        reversibility=ReversibilitySpec(reversible=True, rollback_strategy="revert patch"),
        preview_requirements=PreviewRequirements(required_preview_areas=("summary",)),
        validation_requirements=ValidationRequirements(required_checks=("provider_resolution",)),
        target_savefile_ref="working_save:ws-001",
    )


def _precheck() -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="pre-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch", touched_nodes=("review_bundle",)),
        overall_status="pass_with_warnings",
        structural_validity=ValidityReport(status="valid"),
        dependency_validity=ValidityReport(status="warning"),
        input_output_validity=ValidityReport(status="valid"),
        provider_resolution=ResolutionReport(status="resolved"),
        plugin_resolution=ResolutionReport(status="resolved"),
        safety_review=ValidityReport(status="warning"),
        cost_assessment=CostAssessmentReport(status="warning"),
        ambiguity_assessment=AmbiguityAssessmentReport(status="clear"),
        preview_requirements=PrecheckPreviewRequirements(required_sections=("summary",)),
        warning_findings=(),
        recommended_next_actions=("Review preview",),
        explanation="warning-only change",
    )


def _preview() -> CircuitDraftPreview:
    return CircuitDraftPreview(
        preview_id="preview-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_mode="patch_modify",
        summary_card=SummaryCard(
            title="Replace provider",
            one_sentence_summary="Provider will be replaced in the review bundle.",
            proposal_type="modify",
            change_scope="bounded",
            touched_node_count=1,
            touched_edge_count=0,
            touched_output_count=1,
        ),
        structural_preview=StructuralPreview(before_exists=True, before_node_count=1, after_node_count=1, before_edge_count=0, after_edge_count=0, modified_nodes=("review_bundle",), structural_delta_summary="1 node updated"),
        cost_preview=CostPreview(cost_summary="small increase"),
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
        approval_policy=ApprovalPolicy(policy_name="manual_review", allow_auto_commit=False),
        required_decision_points=(DecisionPoint(decision_id="confirm-1", label="Approve provider replacement"),),
        user_decisions=(UserDecision(decision_point_id="confirm-1", outcome="approve"),),
        final_outcome="approved_for_commit",
        precheck_status="pass_with_warnings",
        confirmation_resolved=True,
    )


def test_read_designer_panel_view_model_projects_connected_designer_flow() -> None:
    vm = read_designer_panel_view_model(
        _working_save(),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )
    assert vm.session_mode == "modify_circuit"
    assert vm.request_state.request_status == "submitted"
    assert vm.intent_state.category == "MODIFY_CIRCUIT"
    assert vm.patch_state.operation_count == 1
    assert vm.precheck_state.overall_status == "pass_with_warnings"
    assert vm.preview_state.preview_status == "ready"
    assert vm.approval_state.commit_eligible is True
    assert any(action.action_type == "approve_for_commit" and action.enabled for action in vm.suggested_actions)
    assert vm.related_targets[0].target_ref == "node:review_bundle"
