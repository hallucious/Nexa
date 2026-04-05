from __future__ import annotations

from src.designer.models.designer_proposal_control import DesignerProposalControlState, ProposalControlPolicy
from src.designer.models.designer_session_state_card import (
    ApprovalState,
    AvailableResources,
    ConversationContext,
    CurrentSelectionState,
    DesignerSessionStateCard,
    SessionTargetScope,
    WorkingSaveReality,
)
from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec
from src.designer.proposal_control import DesignerProposalControlPlane
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.precheck_builder import DesignerPrecheckBuilder
from src.designer.models.validation_precheck import (
    AmbiguityAssessmentReport,
    CostAssessmentReport,
    EvaluatedScope,
    PreviewRequirements,
    ResolutionReport,
    ValidationPrecheck,
    ValidityReport,
)


class BlockedPrecheckBuilder(DesignerPrecheckBuilder):
    def build(self, intent, patch):  # noqa: ANN001
        return ValidationPrecheck(
            precheck_id=patch.patch_id.replace("patch-", "precheck-"),
            patch_ref=patch.patch_id,
            intent_ref=intent.intent_id,
            evaluated_scope=EvaluatedScope(mode="existing_circuit_patch"),
            overall_status="blocked",
            structural_validity=ValidityReport(status="blocked", summary="Broken structure."),
            dependency_validity=ValidityReport(status="blocked", summary="Broken structure."),
            input_output_validity=ValidityReport(status="blocked", summary="Broken structure."),
            provider_resolution=ResolutionReport(status="resolved", summary="Providers clear."),
            plugin_resolution=ResolutionReport(status="resolved", summary="Plugins clear."),
            safety_review=ValidityReport(status="valid", summary="Safety clear."),
            cost_assessment=CostAssessmentReport(status="unknown", summary="Cost not estimated."),
            ambiguity_assessment=AmbiguityAssessmentReport(status="clear", summary="No ambiguity."),
            preview_requirements=PreviewRequirements(required_sections=("scope_delta", "risk_summary")),
            blocking_findings=(
                __import__('src.designer.models.validation_precheck', fromlist=['PrecheckFinding']).PrecheckFinding(
                    issue_code="BLOCKED", message="Broken structure.", fix_hint="Revise patch."
                ),
            ),
            warning_findings=(),
            confirmation_findings=(),
            recommended_next_actions=("revise_patch",),
            explanation="The patch is blocked and must be revised.",
        )


def make_card(revision_index: int = 0, retry_reason: str | None = None) -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-control",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            circuit_summary="2 nodes",
            node_list=("node.answerer", "node.reviewer"),
            edge_list=("node.answerer->node.reviewer",),
            output_list=("final_answer",),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Improve circuit"),
        constraints=ConstraintSet(),
        approval_state=ApprovalState(),
        conversation_context=ConversationContext(user_request_text="placeholder"),
        notes={},
        revision_state=__import__('src.designer.models.designer_session_state_card', fromlist=['RevisionState']).RevisionState(
            revision_index=revision_index,
            retry_reason=retry_reason,
        ),
    )


def test_control_plane_returns_ready_for_approval_for_safe_bundle() -> None:
    controller = DesignerProposalControlPlane()
    result = controller.run(
        "Change provider in node answerer to Claude",
        working_save_ref="ws-001",
        session_state_card=make_card(),
    )
    assert result.ready_for_approval is True
    assert result.control_state.next_action == "proceed_to_approval"
    assert result.control_state.terminal_status == "ready_for_approval"
    assert result.updated_session_state_card is not None
    assert result.updated_session_state_card.approval_state.approval_status == "pending"


def test_control_plane_requests_interpretation_for_ambiguous_confirmation_bundle() -> None:
    controller = DesignerProposalControlPlane()
    result = controller.run("Modify node answerer to add a review step")
    assert result.bundle is not None
    assert result.control_state.next_action == "choose_interpretation"
    assert result.control_state.terminal_status == "awaiting_user_input"
    assert result.control_state.last_precheck_status == "confirmation_required"


def test_control_plane_falls_back_to_read_only_for_explain_request() -> None:
    controller = DesignerProposalControlPlane()
    result = controller.run(
        "Explain what this circuit does",
        working_save_ref="ws-001",
        session_state_card=make_card(),
    )
    assert result.bundle is None
    assert result.control_state.next_action == "fallback_to_read_only"
    assert result.control_state.terminal_status == "awaiting_user_input"
    assert result.control_state.normalization_attempts == 1
    assert result.updated_session_state_card is not None
    assert result.updated_session_state_card.target_scope.mode == "read_only"


def test_control_plane_requests_revision_for_blocked_precheck_with_remaining_budget() -> None:
    flow = DesignerProposalFlow(precheck_builder=BlockedPrecheckBuilder())
    controller = DesignerProposalControlPlane(proposal_flow=flow)
    result = controller.run(
        "Repair the broken connection in node reviewer",
        working_save_ref="ws-001",
        session_state_card=make_card(),
    )
    assert result.bundle is not None
    assert result.control_state.next_action == "request_user_revision"
    assert result.control_state.terminal_status == "awaiting_user_input"
    assert result.control_state.blocked_precheck_count == 1
    assert result.control_state.revision_rounds == 1


def test_control_plane_aborts_when_blocked_precheck_budget_is_exhausted() -> None:
    flow = DesignerProposalFlow(precheck_builder=BlockedPrecheckBuilder())
    controller = DesignerProposalControlPlane(proposal_flow=flow)
    state = DesignerProposalControlState(
        session_id="sess-control",
        revision_rounds=1,
        blocked_precheck_count=1,
    )
    result = controller.run(
        "Repair the broken connection in node reviewer",
        working_save_ref="ws-001",
        session_state_card=make_card(revision_index=1, retry_reason="blocked once"),
        control_state=state,
        control_policy=ProposalControlPolicy(max_revision_rounds=1, max_blocked_precheck_retries=1),
    )
    assert result.bundle is not None
    assert result.control_state.next_action == "abort"
    assert result.control_state.terminal_status == "exhausted"



def test_control_plane_tracks_mixed_referential_reason_code_in_attempt_history() -> None:
    controller = DesignerProposalControlPlane()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-mixed-control",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            circuit_summary="2 nodes",
            node_list=("node.answerer", "node.reviewer"),
            edge_list=("node.answerer->node.reviewer",),
            output_list=("final_answer",),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change and switch provider"),
        constraints=ConstraintSet(),
        approval_state=ApprovalState(),
        conversation_context=ConversationContext(
            user_request_text="Undo the last change and switch provider in node reviewer to Claude"
        ),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    result = controller.run(
        "Undo the last change and switch provider in node reviewer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )

    assert result.bundle is not None
    assert result.control_state.terminal_status == "awaiting_user_input"
    assert result.control_state.history[-1].reason_code == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert result.control_state.pending_reason is not None
    assert "reason_code=MIXED_REFERENTIAL_PROVIDER_CHANGE" in result.control_state.pending_reason
    assert result.updated_session_state_card is not None
    assert result.updated_session_state_card.revision_state.attempt_history[-1].reason_code == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert result.updated_session_state_card.notes["last_attempt_reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
