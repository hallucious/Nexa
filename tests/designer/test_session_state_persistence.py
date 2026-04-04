from __future__ import annotations

from src.designer.models.designer_approval_flow import UserDecision
from src.designer.models.designer_proposal_control import DesignerProposalControlState, ProposalControlPolicy
from src.designer.models.designer_session_state_card import (
    ApprovalState,
    AvailableResources,
    ConversationContext,
    CurrentSelectionState,
    DesignerSessionStateCard,
    RevisionAttemptSummary,
    RevisionState,
    SessionTargetScope,
    WorkingSaveReality,
)
from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec
from src.designer.approval_flow import DesignerApprovalCoordinator
from src.designer.commit_gateway import DesignerCommitGateway
from src.designer.patch_applier import DesignerPatchApplier
from src.designer.proposal_control import DesignerProposalControlPlane
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.precheck_builder import DesignerPrecheckBuilder
from src.designer.session_state_coordinator import DesignerSessionStateCoordinator
from src.designer.session_state_persistence import (
    load_persisted_approval_flow_state,
    load_persisted_commit_candidate_state,
    load_persisted_proposal_control_state,
    load_persisted_session_state_card,
    persist_designer_session_state,
)
from src.designer.session_state_card_builder import DesignerSessionStateCardBuilder
from src.designer.models.validation_precheck import (
    AmbiguityAssessmentReport,
    CostAssessmentReport,
    EvaluatedScope,
    PreviewRequirements,
    ResolutionReport,
    ValidationPrecheck,
    ValidityReport,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


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


def make_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="demo"),
        circuit=CircuitModel(
            nodes=[{"id": "node.answerer", "kind": "provider"}, {"id": "node.reviewer", "kind": "provider"}],
            edges=[{"from": "node.answerer", "to": "node.reviewer"}],
            outputs=[{"name": "final_answer", "source": "node.reviewer.output.result"}],
        ),
        resources=ResourcesModel(
            prompts={"prompt.review": {}},
            providers={"provider.gpt": {}, "provider.claude": {}},
            plugins={"plugin.search": {}},
        ),
        state=StateModel(),
        runtime=RuntimeModel(status="draft"),
        ui=UIModel(),
    )


def make_card() -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-persist",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            circuit_summary="2 nodes",
            node_list=("node.answerer", "node.reviewer"),
            edge_list=("node.answerer->node.reviewer",),
            output_list=("final_answer",),
        ),
        current_selection=CurrentSelectionState(selection_mode="node", selected_refs=("node.answerer",)),
        target_scope=SessionTargetScope(mode="node_only", touch_budget="minimal", allowed_node_refs=("node.answerer",)),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Change provider"),
        constraints=ConstraintSet(provider_restrictions=("provider.legacy",)),
        revision_state=RevisionState(
            revision_index=1,
            retry_reason="previous blocked precheck",
            last_control_action="request_user_revision",
            last_terminal_status="awaiting_user_input",
            attempt_history=(
                RevisionAttemptSummary(
                    attempt_index=1,
                    stage="precheck",
                    outcome="blocked",
                    reason_code="DESIGNER-PRECHECK-BLOCKED",
                    message="Previous proposal was blocked.",
                ),
            ),
        ),
        approval_state=ApprovalState(approval_required=True, approval_status="pending", confirmation_required=True),
        conversation_context=ConversationContext(user_request_text="Change provider in node answerer to Claude"),
        notes={"last_control_action": "request_user_revision"},
    )


def test_persisted_session_state_card_is_loaded_by_builder() -> None:
    working_save = make_working_save()
    card = make_card()
    control_state = DesignerProposalControlState(
        session_id="sess-persist",
        current_stage="precheck",
        next_action="request_user_revision",
        terminal_status="awaiting_user_input",
        revision_rounds=1,
        blocked_precheck_count=1,
        pending_reason="Previous proposal was blocked.",
    )
    persisted = persist_designer_session_state(working_save, session_state_card=card, control_state=control_state)

    builder = DesignerSessionStateCardBuilder()
    rebuilt = builder.build(request_text="Change provider in node answerer to Claude", artifact=persisted)

    assert rebuilt.session_id == "sess-persist"
    assert rebuilt.current_selection.selection_mode == "node"
    assert rebuilt.current_selection.selected_refs == ("node.answerer",)
    assert rebuilt.target_scope.mode == "node_only"
    assert rebuilt.revision_state.revision_index == 1
    assert rebuilt.revision_state.retry_reason == "previous blocked precheck"
    assert rebuilt.revision_state.last_control_action == "request_user_revision"
    assert rebuilt.revision_state.attempt_history[0].reason_code == "DESIGNER-PRECHECK-BLOCKED"


def test_persisted_control_state_round_trips_from_working_save() -> None:
    working_save = make_working_save()
    control_state = DesignerProposalControlState(
        session_id="sess-persist",
        current_stage="approval_boundary",
        next_action="choose_interpretation",
        terminal_status="awaiting_user_input",
        fallback_count=1,
        last_precheck_status="confirmation_required",
        pending_reason="Two structural interpretations remain.",
    )
    persisted = persist_designer_session_state(working_save, session_state_card=make_card(), control_state=control_state)
    restored = load_persisted_proposal_control_state(persisted)

    assert restored is not None
    assert restored.session_id == "sess-persist"
    assert restored.next_action == "choose_interpretation"
    assert restored.pending_reason == "Two structural interpretations remain."


def test_control_plane_evolves_session_state_card_for_read_only_fallback() -> None:
    controller = DesignerProposalControlPlane()
    card = make_card()
    result = controller.run(
        "Explain what this circuit does",
        working_save_ref="ws-001",
        session_state_card=card,
    )

    updated = result.updated_session_state_card
    assert updated is not None
    assert updated.target_scope.mode == "read_only"
    assert updated.approval_state.approval_required is False
    assert updated.revision_state.last_control_action == "fallback_to_read_only"
    assert updated.conversation_context.unresolved_questions


def test_control_plane_evolves_session_state_card_for_blocked_precheck_revision() -> None:
    flow = DesignerProposalFlow(precheck_builder=BlockedPrecheckBuilder())
    controller = DesignerProposalControlPlane(proposal_flow=flow)
    card = make_card()
    result = controller.run(
        "Repair the broken connection in node reviewer",
        working_save_ref="ws-001",
        session_state_card=card,
        control_policy=ProposalControlPolicy(max_revision_rounds=2, max_blocked_precheck_retries=1),
    )
    updated = result.updated_session_state_card

    assert updated is not None
    assert updated.revision_state.revision_index == 2
    assert updated.revision_state.last_control_action == "request_user_revision"
    assert updated.revision_state.attempt_history[-1].reason_code == "DESIGNER-PRECHECK-BLOCKED"
    assert updated.approval_state.blocking_before_commit is True
    assert updated.current_findings.blocking_findings == ("Broken structure.",)


def test_load_persisted_session_state_card_returns_none_without_designer_snapshot() -> None:
    assert load_persisted_session_state_card(make_working_save()) is None



def test_persisted_approval_flow_state_round_trips_from_working_save() -> None:
    working_save = make_working_save()
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
    approval = DesignerApprovalCoordinator().create_state(bundle)

    persisted = persist_designer_session_state(
        working_save,
        session_state_card=make_card(),
        approval_flow_state=approval,
    )
    restored = load_persisted_approval_flow_state(persisted)

    assert restored is not None
    assert restored.approval_id == approval.approval_id
    assert restored.current_stage == "awaiting_decision"
    assert restored.required_decision_points[0].decision_id == approval.required_decision_points[0].decision_id


def test_approval_resolution_updates_session_state_for_interpretation_choice_and_persists() -> None:
    working_save = make_working_save()
    card = make_card()
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    approval = coordinator.create_state(bundle)
    resolved = coordinator.resolve(
        approval,
        (
            UserDecision(
                decision_point_id=approval.required_decision_points[0].decision_id,
                outcome="choose_interpretation",
                selected_option="Insert a manual review gate after node.reviewer only.",
            ),
        ),
    )

    session_coordinator = DesignerSessionStateCoordinator()
    updated = session_coordinator.evolve_after_approval_resolution(card, resolved)
    persisted = persist_designer_session_state(working_save, session_state_card=updated, approval_flow_state=resolved)
    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Add a review node before final output in node reviewer",
        artifact=persisted,
    )

    assert updated.revision_state.revision_index == card.revision_state.revision_index + 1
    assert updated.revision_state.last_control_action == "choose_interpretation"
    assert updated.conversation_context.clarified_interpretation == "Insert a manual review gate after node.reviewer only."
    assert rebuilt.conversation_context.clarified_interpretation == "Insert a manual review gate after node.reviewer only."
    assert rebuilt.approval_state.approval_status == "not_started"


def test_approval_resolution_appends_revision_note_and_normalizer_uses_persisted_context() -> None:
    working_save = make_working_save()
    card = make_card()
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    approval = coordinator.create_state(bundle)
    resolved = coordinator.resolve(
        approval,
        (
            UserDecision(
                decision_point_id=approval.required_decision_points[0].decision_id,
                outcome="request_revision",
                note="Change provider only in node reviewer and keep the rest unchanged.",
            ),
        ),
    )

    session_coordinator = DesignerSessionStateCoordinator()
    updated = session_coordinator.evolve_after_approval_resolution(card, resolved)
    persisted = persist_designer_session_state(working_save, session_state_card=updated, approval_flow_state=resolved)
    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Change provider",
        artifact=persisted,
    )
    intent = DesignerProposalFlow().propose(
        "Change provider",
        working_save_ref="ws-001",
        session_state_card=rebuilt,
    ).intent

    assert "Change provider only in node reviewer and keep the rest unchanged." in updated.revision_state.user_corrections
    assert rebuilt.revision_state.user_corrections[-1] == "Change provider only in node reviewer and keep the rest unchanged."
    assert intent.target_scope.node_refs == ("node.reviewer",)


def test_persisted_commit_candidate_state_round_trips_and_builder_surfaces_resume_hint() -> None:
    working_save = make_working_save()
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)
    approved = coordinator.resolve(
        state,
        tuple(UserDecision(decision_point_id=point.decision_id, outcome="approve") for point in state.required_decision_points),
    )
    applier = DesignerPatchApplier()
    application = applier.apply_bundle(working_save, bundle)
    candidate_state = applier.build_commit_candidate_state(application, approved, source_working_save_ref="ws-001")

    persisted = persist_designer_session_state(
        application.candidate_working_save,
        session_state_card=make_card(),
        approval_flow_state=approved,
        commit_candidate_state=candidate_state,
    )
    restored = load_persisted_commit_candidate_state(persisted)

    assert restored is not None
    assert restored.ready_for_commit is True
    assert restored.patch_ref == bundle.patch.patch_id

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Add a review node before final output in node reviewer",
        artifact=persisted,
    )
    assert rebuilt.approval_state.approval_status == "approved"
    assert rebuilt.notes["resume_commit_candidate_ready"] is True
    assert rebuilt.notes["resume_commit_candidate_patch_ref"] == bundle.patch.patch_id


def test_cleanup_after_commit_clears_resume_state_and_preserves_revision_history() -> None:
    working_save = make_working_save()
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)
    approved = coordinator.resolve(
        state,
        tuple(UserDecision(decision_point_id=point.decision_id, outcome="approve") for point in state.required_decision_points),
    )
    applier = DesignerPatchApplier()
    application = applier.apply_bundle(working_save, bundle)
    candidate_state = applier.build_commit_candidate_state(application, approved, source_working_save_ref="ws-001")
    persisted = persist_designer_session_state(
        application.candidate_working_save,
        session_state_card=make_card(),
        control_state=DesignerProposalControlState(
            session_id="sess-persist",
            current_stage="approval_boundary",
            next_action="proceed_to_approval",
            terminal_status="ready_for_approval",
        ),
        approval_flow_state=approved,
        commit_candidate_state=candidate_state,
    )
    gateway = DesignerCommitGateway(coordinator=coordinator)
    result = gateway.commit_persisted_candidate(persisted, commit_id="commit-clean-1")
    cleaned = result.cleaned_candidate_working_save

    cleaned_card = load_persisted_session_state_card(cleaned)
    assert cleaned_card is not None
    assert cleaned_card.approval_state.approval_status == "committed"
    assert cleaned_card.approval_state.approval_required is False
    assert cleaned_card.revision_state.retry_reason is None
    assert cleaned_card.revision_state.attempt_history[0].reason_code == "DESIGNER-PRECHECK-BLOCKED"
    assert cleaned_card.notes["post_commit_cleanup_applied"] is True
    assert cleaned_card.notes["last_commit_id"] == "commit-clean-1"
    assert "resume_commit_candidate_ready" not in cleaned_card.notes
    assert load_persisted_commit_candidate_state(cleaned) is None
    assert load_persisted_proposal_control_state(cleaned) is None
    restored_approval = load_persisted_approval_flow_state(cleaned)
    assert restored_approval is not None
    assert restored_approval.current_stage == "committed"
