from __future__ import annotations

from dataclasses import replace

from src.designer.models.designer_approval_flow import ApprovalPolicy, DecisionPoint, DesignerApprovalFlowState, UserDecision
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


def test_approval_resolution_tracks_recent_multi_step_revision_history() -> None:
    card = make_card()
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    approval = coordinator.create_state(bundle)

    first_resolved = coordinator.resolve(
        approval,
        (
            UserDecision(
                decision_point_id=approval.required_decision_points[0].decision_id,
                outcome="choose_interpretation",
                selected_option="Only modify node.reviewer.",
            ),
        ),
    )
    session_coordinator = DesignerSessionStateCoordinator()
    first_updated = session_coordinator.evolve_after_approval_resolution(card, first_resolved)

    second_resolved = coordinator.resolve(
        approval,
        (
            UserDecision(
                decision_point_id=approval.required_decision_points[0].decision_id,
                outcome="request_revision",
                note="Keep the provider change scoped to node.reviewer.",
            ),
        ),
    )
    second_updated = session_coordinator.evolve_after_approval_resolution(first_updated, second_resolved)

    assert second_updated.notes["approval_revision_recent_history_count"] == 2
    assert "Latest continuation mode" in second_updated.notes["approval_revision_recent_history_summary"]
    assert second_updated.notes["approval_revision_recent_history"][-1]["continuation_modes"] == ["request_revision"]


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




def test_approval_revision_requested_propagates_mixed_referential_reason_code_into_revision_state() -> None:
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-mixed-approval",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change and switch provider"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Undo the last change and switch provider in node reviewer to Claude"
        ),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )
    controller = DesignerProposalControlPlane()
    control_result = controller.run(
        "Undo the last change and switch provider in node reviewer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )
    assert control_result.bundle is not None

    approval = DesignerApprovalCoordinator().create_state(control_result.bundle)
    decision_id = approval.required_decision_points[0].decision_id
    resolved = DesignerApprovalCoordinator().resolve(
        approval,
        (UserDecision(decision_point_id=decision_id, outcome="request_revision"),),
    )

    updated = DesignerSessionStateCoordinator().evolve_after_approval_resolution(
        control_result.updated_session_state_card or card,
        resolved,
    )

    assert updated.revision_state.retry_reason == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert updated.notes["last_revision_reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert updated.notes["active_mixed_referential_reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert updated.notes["active_mixed_referential_reason_stage"] == "approval_revision"
    assert updated.notes["active_mixed_referential_reason_status"] == "revision_requested"
    assert "reason_code=MIXED_REFERENTIAL_PROVIDER_CHANGE" in updated.conversation_context.unresolved_questions[-1]

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
    assert cleaned_card.notes["committed_summary_housekeeping_applied"] is True
    assert "resume_commit_candidate_ready" not in cleaned_card.notes
    assert "fresh_cycle_from_committed_baseline" not in cleaned_card.notes
    assert load_persisted_commit_candidate_state(cleaned) is None
    assert load_persisted_proposal_control_state(cleaned) is None
    restored_approval = load_persisted_approval_flow_state(cleaned)
    assert restored_approval is not None
    assert restored_approval.current_stage == "committed"


def test_cleanup_after_commit_archives_mixed_referential_reason_context() -> None:
    working_save = make_working_save()
    card = replace(
        make_card(),
        notes={
            **make_card().notes,
            "last_revision_reason_code": "MIXED_REFERENTIAL_PROVIDER_CHANGE",
            "active_mixed_referential_reason_code": "MIXED_REFERENTIAL_PROVIDER_CHANGE",
            "active_mixed_referential_reason_stage": "approval_revision",
            "active_mixed_referential_reason_status": "revision_requested",
            "active_mixed_referential_reason_source_note_key": "last_revision_reason_code",
            "active_mixed_referential_reason_retention_state": "active",
        },
        conversation_context=replace(
            make_card().conversation_context,
            user_request_text="Undo the last change and switch provider in node reviewer to Claude",
        ),
    )
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
        session_state_card=card,
        approval_flow_state=approved,
        commit_candidate_state=candidate_state,
    )

    cleaned = DesignerCommitGateway(coordinator=coordinator).commit_persisted_candidate(
        persisted,
        commit_id="commit-mixed-archive-1",
    ).cleaned_candidate_working_save

    cleaned_card = load_persisted_session_state_card(cleaned)
    assert cleaned_card is not None
    assert cleaned_card.notes["last_mixed_referential_reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert cleaned_card.notes["last_mixed_referential_reason_retention_state"] == "committed_history"
    assert cleaned_card.notes["mixed_referential_reason_history"][0]["commit_id"] == "commit-mixed-archive-1"
    assert cleaned_card.notes["mixed_referential_reason_history"][0]["retention_state"] == "committed_history"
    assert cleaned_card.notes["mixed_referential_reason_history"][0]["request_text"] == "Undo the last change and switch provider in node reviewer to Claude"
    assert "active_mixed_referential_reason_code" not in cleaned_card.notes
    assert "last_revision_reason_code" not in cleaned_card.notes



def test_new_request_after_commit_starts_fresh_cycle_from_committed_baseline() -> None:
    working_save = make_working_save()
    base_card = make_card()
    persisted_card = replace(
        base_card,
        revision_state=replace(
            base_card.revision_state,
            user_corrections=("Only change provider in node answerer.",),
        ),
        conversation_context=replace(
            base_card.conversation_context,
            clarified_interpretation="Only change provider in node answerer.",
            unresolved_questions=("Interpretation still pending.",),
        ),
        notes={
            "fresh_cycle_from_committed_baseline": True,
            "fresh_cycle_request_text": "Old request that should not survive.",
            "active_baseline_commit_id": "older-commit",
            "last_revision_reason_code": "MIXED_REFERENTIAL_PROVIDER_CHANGE",
            "active_mixed_referential_reason_code": "MIXED_REFERENTIAL_PROVIDER_CHANGE",
            "active_mixed_referential_reason_stage": "approval_revision",
            "active_mixed_referential_reason_status": "revision_requested",
            "active_mixed_referential_reason_source_note_key": "last_revision_reason_code",
            "active_mixed_referential_reason_retention_state": "active",
        },
    )
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
        session_state_card=persisted_card,
        approval_flow_state=approved,
        commit_candidate_state=candidate_state,
    )
    cleaned = DesignerCommitGateway(coordinator=coordinator).commit_persisted_candidate(
        persisted,
        commit_id="commit-fresh-1",
    ).cleaned_candidate_working_save

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Optimize node reviewer to reduce cost",
        artifact=cleaned,
    )
    next_bundle = DesignerProposalFlow().propose(
        "Optimize node reviewer to reduce cost",
        working_save_ref="ws-001",
        session_state_card=rebuilt,
    )

    assert rebuilt.approval_state.approval_status == "not_started"
    assert rebuilt.approval_state.approval_required is True
    assert rebuilt.current_selection.selection_mode == "none"
    assert rebuilt.target_scope.mode == "existing_circuit"
    assert rebuilt.revision_state.revision_index == 0
    assert rebuilt.revision_state.user_corrections == ()
    assert rebuilt.revision_state.last_control_action is None
    assert rebuilt.conversation_context.clarified_interpretation is None
    assert rebuilt.conversation_context.unresolved_questions == ()
    assert rebuilt.notes["fresh_cycle_from_committed_baseline"] is True
    assert rebuilt.notes["fresh_cycle_baseline_commit_id"] == "commit-fresh-1"
    assert rebuilt.notes["fresh_cycle_request_text"] == "Optimize node reviewer to reduce cost"
    assert rebuilt.notes["fresh_cycle_housekeeping_applied"] is True
    assert rebuilt.notes["last_mixed_referential_reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert rebuilt.notes["last_mixed_referential_reason_retention_state"] == "committed_history"
    assert rebuilt.notes["mixed_referential_reason_history"][0]["retention_state"] == "committed_history"
    assert rebuilt.notes["mixed_referential_reason_history"][0]["reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert rebuilt.notes["mixed_referential_reason_history"][0]["request_text"] == "Change provider in node answerer to Claude"
    assert "active_mixed_referential_reason_code" not in rebuilt.notes
    assert "last_revision_reason_code" not in rebuilt.notes
    assert "active_baseline_commit_id" not in rebuilt.notes
    assert next_bundle.intent.target_scope.node_refs == ("node.reviewer",)



def test_repeat_fresh_cycle_housekeeping_replaces_stale_markers() -> None:
    working_save = make_working_save()
    card = replace(
        make_card(),
        notes={
            "last_commit_id": "commit-repeat-2",
            "post_commit_cleanup_applied": True,
            "fresh_cycle_from_committed_baseline": True,
            "fresh_cycle_request_text": "stale request",
            "fresh_cycle_baseline_commit_id": "commit-repeat-1",
            "active_baseline_commit_id": "commit-repeat-1",
        },
    )
    committed_approval = DesignerApprovalCoordinator().mark_committed(
        DesignerApprovalCoordinator().resolve(
            DesignerApprovalCoordinator().create_state(
                DesignerProposalFlow().propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
            ),
            tuple(
                UserDecision(decision_point_id=point.decision_id, outcome="approve")
                for point in DesignerApprovalCoordinator().create_state(
                    DesignerProposalFlow().propose("Add a review node before final output in node reviewer", working_save_ref="ws-001")
                ).required_decision_points
            ),
        )
    )
    persisted = persist_designer_session_state(working_save, session_state_card=card, approval_flow_state=committed_approval)

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Create a cheaper review path for node answerer",
        artifact=persisted,
    )

    assert rebuilt.notes["fresh_cycle_from_committed_baseline"] is True
    assert rebuilt.notes["fresh_cycle_request_text"] == "Create a cheaper review path for node answerer"
    assert rebuilt.notes["fresh_cycle_baseline_commit_id"] == "commit-repeat-2"
    assert rebuilt.notes["post_commit_cleanup_applied"] is True
    assert "active_baseline_commit_id" not in rebuilt.notes


def test_committed_summary_retention_history_rotates_and_trims() -> None:
    working_save = make_working_save()
    base_card = replace(
        make_card(),
        notes={
            "commit_summary_history": [
                {
                    "commit_id": "commit-old-3",
                    "parent_commit_id": "parent-old-3",
                    "patch_ref": "patch-old-3",
                    "approval_stage": "committed",
                    "approval_outcome": "committed",
                    "candidate_consumed": True,
                    "touched_node_ids": ["node.reviewer"],
                },
                {
                    "commit_id": "commit-old-2",
                    "parent_commit_id": "parent-old-2",
                    "patch_ref": "patch-old-2",
                    "approval_stage": "committed",
                    "approval_outcome": "committed",
                    "candidate_consumed": True,
                },
                {
                    "commit_id": "commit-old-1",
                    "parent_commit_id": "parent-old-1",
                    "patch_ref": "patch-old-1",
                    "approval_stage": "committed",
                    "approval_outcome": "committed",
                    "candidate_consumed": False,
                },
            ],
        },
    )
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
        session_state_card=base_card,
        approval_flow_state=approved,
        commit_candidate_state=candidate_state,
    )

    cleaned = DesignerCommitGateway(coordinator=coordinator).commit_persisted_candidate(
        persisted,
        commit_id="commit-new-1",
    ).cleaned_candidate_working_save

    cleaned_card = load_persisted_session_state_card(cleaned)
    assert cleaned_card is not None
    history = cleaned_card.notes["commit_summary_history"]
    assert [entry["commit_id"] for entry in history] == ["commit-new-1", "commit-old-3", "commit-old-2"]
    assert cleaned_card.notes["committed_summary_retention_limit"] == 3
    assert history[0]["patch_ref"] == bundle.patch.patch_id
    assert history[0]["touched_node_ids"] == ["reviewer"]
    assert history[0]["candidate_consumed"] is True



def test_builder_exposes_committed_summary_priority_notes() -> None:
    working_save = make_working_save()
    card = replace(
        make_card(),
        notes={
            "commit_summary_history": [
                {
                    "commit_id": "commit-latest",
                    "parent_commit_id": "parent-latest",
                    "patch_ref": "patch-latest",
                    "approval_stage": "committed",
                    "approval_outcome": "committed",
                    "candidate_consumed": True,
                    "touched_node_ids": ["node.reviewer"],
                },
                {
                    "commit_id": "commit-older",
                    "parent_commit_id": "parent-older",
                    "patch_ref": "patch-older",
                    "approval_stage": "committed",
                    "approval_outcome": "committed",
                    "candidate_consumed": True,
                    "touched_node_ids": ["node.answerer"],
                },
            ],
        },
    )
    persisted = persist_designer_session_state(working_save, session_state_card=card)

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Change provider in node answerer",
        artifact=persisted,
    )

    assert rebuilt.notes["committed_summary_exposure_applied"] is True
    assert rebuilt.notes["committed_summary_primary_priority"] == "high"
    assert rebuilt.notes["committed_summary_history_priority"] == "low"
    assert rebuilt.notes["committed_summary_primary"]["commit_id"] == "commit-latest"
    assert rebuilt.notes["committed_summary_recent_history"][0]["commit_id"] == "commit-older"
    assert rebuilt.notes["committed_summary_interpretation_policy"] == "latest_primary_history_reference_only"
    assert rebuilt.notes["committed_summary_reference_resolution_policy"] == "latest_auto_second_latest_when_explicit_exact_commit_id_match_otherwise_clarify_nonlatest"
    assert rebuilt.notes["committed_summary_auto_resolution_modes"] == ["latest_summary", "second_latest_when_explicit", "exact_commit_id_match"]
    assert rebuilt.notes["committed_summary_clarification_required_modes"] == ["older_change_without_anchor", "nonlatest_reference_without_exact_match"]
    assert rebuilt.notes["committed_summary_target_resolution_policy"] == "single_touched_node_auto_explicit_conflict_clarify_multi_target_clarify"
    assert rebuilt.notes["committed_summary_target_auto_resolution_modes"] == ["single_touched_node_when_no_explicit_target"]
    assert rebuilt.notes["committed_summary_target_clarification_required_modes"] == ["multiple_touched_nodes_without_explicit_target", "explicit_target_conflicts_with_referenced_summary", "referenced_summary_without_touched_nodes"]




def test_builder_exposes_control_governance_notes_for_repeated_confirmation_cycles() -> None:
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-governance-repeat",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=2,
            last_control_action="choose_interpretation",
            last_terminal_status="awaiting_user_input",
            attempt_history=(
                RevisionAttemptSummary(
                    attempt_index=1,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
                RevisionAttemptSummary(
                    attempt_index=2,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
    )
    persisted = persist_designer_session_state(make_working_save(), session_state_card=card)

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Undo the last change",
        artifact=persisted,
    )

    assert rebuilt.notes["control_governance_applied"] is True
    assert rebuilt.notes["control_governance_recent_attempt_count"] == 2
    assert rebuilt.notes["control_governance_confirmation_loop_count"] == 2
    assert rebuilt.notes["control_governance_interpretation_safety_mode"] == "explicit_referential_anchor_required"
    assert rebuilt.notes["control_governance_requires_explicit_referential_anchor"] is True
    assert rebuilt.notes["control_governance_recent_attempts"][-1]["reason_code"] == "DESIGNER-CONFIRMATION-REQUIRED"
    assert rebuilt.notes["control_governance_policy_tier"] == "elevated"
    assert rebuilt.notes["control_governance_next_actions"] == ["provide_explicit_anchor"]


def test_builder_exposes_strict_control_governance_tier_after_three_confirmation_cycles() -> None:
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-governance-strict",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=3,
            last_control_action="choose_interpretation",
            last_terminal_status="awaiting_user_input",
            attempt_history=(
                RevisionAttemptSummary(
                    attempt_index=1,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
                RevisionAttemptSummary(
                    attempt_index=2,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
                RevisionAttemptSummary(
                    attempt_index=3,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
    )
    persisted = persist_designer_session_state(make_working_save(), session_state_card=card)

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Undo the last change",
        artifact=persisted,
    )

    assert rebuilt.notes["control_governance_policy_tier"] == "strict"
    assert rebuilt.notes["control_governance_requires_explicit_referential_anchor"] is True
    assert rebuilt.notes["control_governance_next_actions"] == ["provide_explicit_anchor", "restate_request_with_stronger_selector"]
    assert "strict governance mode" in rebuilt.notes["control_governance_precheck_message"]
    assert rebuilt.notes["control_governance_ambiguity_pressure_score"] == 4
    assert rebuilt.notes["control_governance_ambiguity_pressure_band"] == "strict"
    assert rebuilt.notes["control_governance_pressure_transition"] == "escalating_or_sustained_repeat_pressure"


def test_control_plane_persists_mixed_referential_attempt_reason_code_into_session_state() -> None:
    controller = DesignerProposalControlPlane()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-mixed-persist",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change and switch provider"),
        constraints=ConstraintSet(),
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

    updated = result.updated_session_state_card
    assert updated is not None
    assert updated.revision_state.attempt_history[-1].reason_code == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert updated.notes["last_attempt_reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert updated.notes["last_attempt_stage"] == "precheck"
    assert updated.notes["last_attempt_outcome"] == "confirmation_required"
    assert updated.notes["active_mixed_referential_reason_code"] == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
    assert updated.notes["active_mixed_referential_reason_stage"] == "precheck"
    assert updated.notes["active_mixed_referential_reason_status"] == "confirmation_required"


def test_control_governance_builder_records_thresholds_and_transition_summary() -> None:
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-governance-transition",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=3,
            last_control_action="choose_interpretation",
            last_terminal_status="awaiting_user_input",
            attempt_history=(
                RevisionAttemptSummary(1, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
                RevisionAttemptSummary(2, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
                RevisionAttemptSummary(3, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={"control_governance_policy_tier": "elevated"},
    )
    persisted = persist_designer_session_state(make_working_save(), session_state_card=card)

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Undo the last change",
        artifact=persisted,
    )

    assert rebuilt.notes["control_governance_thresholds"]["strict_repeat_threshold"] == 3
    assert rebuilt.notes["control_governance_previous_tier"] == "elevated"
    assert rebuilt.notes["control_governance_transition_direction"] == "escalated"
    assert "escalated from elevated to strict" in rebuilt.notes["control_governance_transition_summary"]


def test_approval_revision_requested_from_governance_decision_persists_anchor_guidance() -> None:
    flow = DesignerProposalFlow()
    base_card = DesignerSessionStateCardBuilder().build(
        request_text="Undo the last change",
        artifact=None,
        session_id="sess-governance-revision-guidance",
        target_scope_mode="existing_circuit",
    )
    card = replace(
        base_card,
        notes={
            **base_card.notes,
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_policy_tier": "strict",
            "control_governance_requires_explicit_referential_anchor": True,
            "control_governance_precheck_message": "Repeated referential ambiguity has triggered strict governance mode. Provide an explicit commit anchor, explicit node target, or explicit non-latest selector before approval can continue safely.",
            "control_governance_preview_hint": "Strict referential governance is active. The next safe step is to restate the request with a stronger anchor instead of relying on 'last change' style language.",
        },
    )
    bundle = flow.propose("Undo the last change", working_save_ref="ws-001", session_state_card=card)
    approval = DesignerApprovalCoordinator().create_state(bundle)
    decision_id = next(point.decision_id for point in approval.required_decision_points if point.decision_id == "referential_governance_strict")
    resolved = DesignerApprovalCoordinator().resolve(
        approval,
        (UserDecision(decision_point_id=decision_id, outcome="request_revision"),),
    )

    updated = DesignerSessionStateCoordinator().evolve_after_approval_resolution(card, resolved)

    assert updated.notes["control_governance_pending_anchor_requirement"] is True
    assert updated.notes["control_governance_pending_anchor_requirement_mode"] == "required"
    assert "explicit commit anchor" in updated.notes["control_governance_last_revision_guidance"]
    assert updated.notes["control_governance_last_revision_pressure_score"] == 4
    assert updated.notes["control_governance_last_revision_pressure_band"] == "strict"
    assert "4/5 (strict band)" in updated.notes["control_governance_last_revision_pressure_summary"]
    assert updated.notes["control_governance_last_revision_next_actions"] == [
        "provide_explicit_anchor",
        "restate_request_with_stronger_selector",
    ]
    assert any("explicit commit anchor" in item for item in updated.conversation_context.unresolved_questions)
    assert any("Next safe step:" in item for item in updated.conversation_context.unresolved_questions)




def test_persisted_session_rebuild_relaxes_strict_governance_one_tier_after_anchored_resolution_attempt() -> None:
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-governance-cooldown-rebuild",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change on node reviewer"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=3,
            attempt_history=(
                RevisionAttemptSummary(1, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
                RevisionAttemptSummary(2, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
                RevisionAttemptSummary(3, "preview", "ready_for_approval", "DESIGNER-GOVERNANCE-STRICT-ANCHORED-READY", "anchored"),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change on node reviewer"),
        notes={
            "control_governance_policy_tier": "strict",
            "control_governance_requires_explicit_referential_anchor": True,
        },
    )
    persisted = persist_designer_session_state(make_working_save(), session_state_card=card)

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Undo the last change on node reviewer",
        artifact=persisted,
    )

    assert rebuilt.notes["control_governance_policy_tier"] == "elevated"
    assert rebuilt.notes["control_governance_transition_rule"] == "anchored_resolution_cooldown"
    assert rebuilt.notes["control_governance_resolution_state"] == "partial_relief"


def test_persisted_session_rebuild_tracks_safe_cycle_decay_progress_for_strict_governance() -> None:
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-governance-safe-decay",
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
        objective=ObjectiveSpec(primary_goal="Change provider"),
        constraints=ConstraintSet(),
        approval_state=ApprovalState(),
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude"),
        notes={
            "control_governance_policy_tier": "strict",
            "control_governance_requires_explicit_referential_anchor": True,
            "control_governance_safe_cycle_decay_count": 1,
            "control_governance_ambiguity_pressure_score": 5,
        },
        revision_state=RevisionState(
            attempt_history=(
                RevisionAttemptSummary(
                    attempt_index=1,
                    stage="preview",
                    outcome="ready_for_approval",
                    reason_code="DESIGNER-READY-FOR-APPROVAL",
                    message="Proposal bundle passed into the approval boundary.",
                ),
            ),
        ),
    )
    persisted = persist_designer_session_state(make_working_save(), session_state_card=card)

    rebuilt = DesignerSessionStateCardBuilder().build(
        request_text="Change provider in node reviewer to Claude",
        artifact=persisted,
    )

    assert rebuilt.notes["control_governance_policy_tier"] == "elevated"
    assert rebuilt.notes["control_governance_transition_rule"] == "safe_cycle_decay_threshold"
    assert rebuilt.notes["control_governance_resolution_state"] == "safe_cycle_partial_relief"
    assert rebuilt.notes["control_governance_decay_path"] == "safe_nonreferential_cycles"
    assert rebuilt.notes["control_governance_safe_cycle_decay_count"] == 0
    assert rebuilt.notes["control_governance_safe_cycle_decay_threshold"] == 2
    assert rebuilt.notes["control_governance_ambiguity_pressure_score"] == 3
    assert rebuilt.notes["control_governance_ambiguity_pressure_band"] == "elevated"
    assert rebuilt.notes["control_governance_pressure_transition"] == "safe_cycle_relief_step"


def test_control_result_clears_pending_anchor_requirement_after_anchored_retry() -> None:
    flow = DesignerProposalFlow()
    card = replace(
        make_card(),
        conversation_context=ConversationContext(user_request_text="Undo the last change on node reviewer"),
        notes={
            **make_card().notes,
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_pending_anchor_requirement": True,
            "control_governance_pending_anchor_requirement_mode": "required",
            "control_governance_last_revision_guidance": "Provide an explicit commit anchor before the next revision attempt.",
            "control_governance_last_revision_pressure_summary": "Ambiguity pressure remains 5/5 (strict band), so do not fall back to loose selectors.",
            "control_governance_last_revision_pressure_score": 5,
            "control_governance_last_revision_pressure_band": "strict",
            "control_governance_last_revision_next_actions": [
                "provide_explicit_anchor",
                "restate_request_with_stronger_selector",
            ],
        },
    )

    controlled = flow.propose_with_control(
        "Undo the last change on node reviewer",
        working_save_ref="ws-001",
        session_state_card=card,
    )
    updated = DesignerSessionStateCoordinator().evolve_after_control_result(card, controlled)

    assert "control_governance_pending_anchor_requirement" not in updated.notes
    assert "control_governance_pending_anchor_requirement_mode" not in updated.notes
    assert updated.notes["control_governance_last_pending_anchor_resolution_status"] == "cleared_by_anchored_retry"
    assert updated.notes["control_governance_last_pending_anchor_resolution_request_text"] == "Undo the last change on node reviewer"
    assert "stronger referential anchor" in updated.notes["control_governance_last_pending_anchor_resolution_summary"]


def test_control_result_expires_recent_anchor_resolution_after_one_followup_cycle() -> None:
    flow = DesignerProposalFlow()
    card = replace(
        make_card(),
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude"),
        notes={
            **make_card().notes,
            "control_governance_last_pending_anchor_resolution_status": "cleared_by_anchored_retry",
            "control_governance_last_pending_anchor_resolution_summary": "Pending governance carryover was cleared because the stronger referential anchor was satisfied in the last cycle.",
            "control_governance_last_pending_anchor_resolution_request_text": "Undo the last change on node reviewer",
            "control_governance_last_pending_anchor_resolution_age": 0,
        },
    )

    controlled = flow.propose_with_control(
        "Change provider in node reviewer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )
    updated = DesignerSessionStateCoordinator().evolve_after_control_result(card, controlled)

    assert "control_governance_last_pending_anchor_resolution_status" not in updated.notes
    assert "control_governance_last_pending_anchor_resolution_summary" not in updated.notes
    assert "control_governance_last_pending_anchor_resolution_request_text" not in updated.notes
    assert "control_governance_last_pending_anchor_resolution_age" not in updated.notes


def test_control_result_keeps_pending_anchor_requirement_for_nonreferential_followup() -> None:
    flow = DesignerProposalFlow()
    card = replace(
        make_card(),
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude"),
        notes={
            **make_card().notes,
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_pending_anchor_requirement": True,
            "control_governance_pending_anchor_requirement_mode": "required",
            "control_governance_last_revision_guidance": "Provide an explicit commit anchor before the next revision attempt.",
            "control_governance_last_revision_pressure_summary": "Ambiguity pressure remains 5/5 (strict band), so do not fall back to loose selectors.",
            "control_governance_last_revision_pressure_score": 5,
            "control_governance_last_revision_pressure_band": "strict",
            "control_governance_last_revision_next_actions": [
                "provide_explicit_anchor",
                "restate_request_with_stronger_selector",
            ],
        },
    )

    controlled = flow.propose_with_control(
        "Change provider in node reviewer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )
    updated = DesignerSessionStateCoordinator().evolve_after_control_result(card, controlled)

    assert updated.notes["control_governance_pending_anchor_requirement"] is True
    assert updated.notes["control_governance_pending_anchor_requirement_mode"] == "required"
    assert "control_governance_last_pending_anchor_resolution_status" not in updated.notes




def test_control_result_expires_recent_approval_revision_history_after_second_followup() -> None:
    flow = DesignerProposalFlow()
    card = replace(
        make_card(),
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude"),
        notes={
            **make_card().notes,
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
            "approval_revision_recent_history_age": 1,
        },
    )

    controlled = flow.propose_with_control(
        "Change provider in node reviewer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )
    updated = DesignerSessionStateCoordinator().evolve_after_control_result(card, controlled)

    assert "approval_revision_recent_history" not in updated.notes
    assert "approval_revision_recent_history_count" not in updated.notes
    assert "approval_revision_recent_history_summary" not in updated.notes
    assert "approval_revision_recent_history_age" not in updated.notes

def test_new_revision_history_clears_redirect_archive_background() -> None:
    coordinator = DesignerSessionStateCoordinator()
    current = replace(
        make_card(),
        notes={
            **make_card().notes,
            "approval_revision_redirect_archived_status": "archived_background",
            "approval_revision_redirect_archived_summary": "Older revision-thread continuity is retained only as background history.",
            "approval_revision_redirect_archived_applied": True,
        },
    )
    approval = DesignerApprovalFlowState(
        approval_id="approval-redirect",
        intent_ref="intent-redirect",
        patch_ref="patch-redirect",
        precheck_ref="precheck-redirect",
        preview_ref="preview-redirect",
        current_stage="awaiting_decision",
        approval_policy=ApprovalPolicy(),
        required_decision_points=(DecisionPoint(decision_id="confirm.scope", label="Clarify scope"),),
        user_decisions=(
            UserDecision(
                decision_point_id="confirm.scope",
                outcome="request_revision",
                note="Please revise.",
            ),
        ),
        final_outcome="revision_requested",
        explanation="Revision requested before commit.",
        precheck_status="pass",
        blocking_finding_count=0,
        confirmation_finding_count=0,
        confirmation_resolved=True,
    )
    updated = coordinator.evolve_after_approval_resolution(current, approval_state=approval)
    assert "approval_revision_redirect_archived_status" not in updated.notes
    assert "approval_revision_redirect_archived_summary" not in updated.notes
    assert "approval_revision_redirect_archived_applied" not in updated.notes


def test_new_revision_history_preserves_reopened_origin_marker() -> None:
    coordinator = DesignerSessionStateCoordinator()
    current = replace(
        make_card(),
        notes={
            **make_card().notes,
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
            "approval_revision_recent_history_origin_status": "reopened_from_redirect_archive",
            "approval_revision_recent_history_origin_summary": "A previously redirected revision thread remains active continuity because the user explicitly reopened it.",
            "approval_revision_recent_history_origin_applied": True,
        },
    )
    approval = DesignerApprovalFlowState(
        approval_id="approval-reopened-history",
        intent_ref="intent-reopened-history",
        patch_ref="patch-reopened-history",
        precheck_ref="precheck-reopened-history",
        preview_ref="preview-reopened-history",
        current_stage="awaiting_decision",
        approval_policy=ApprovalPolicy(),
        required_decision_points=(DecisionPoint(decision_id="confirm.scope", label="Clarify scope"),),
        user_decisions=(
            UserDecision(
                decision_point_id="confirm.scope",
                outcome="request_revision",
                note="Please revise again.",
            ),
        ),
        final_outcome="revision_requested",
        explanation="Revision requested before commit.",
        precheck_status="pass",
        blocking_finding_count=0,
        confirmation_finding_count=0,
        confirmation_resolved=True,
    )
    updated = coordinator.evolve_after_approval_resolution(current, approval_state=approval)
    assert updated.notes["approval_revision_recent_history_origin_status"] == "reopened_from_redirect_archive"
    assert updated.notes["approval_revision_recent_history_origin_applied"] is True


def test_new_revision_history_replaces_reopened_origin_with_newer_active_thread() -> None:
    coordinator = DesignerSessionStateCoordinator()
    current = replace(
        make_card(),
        notes={
            **make_card().notes,
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
            "approval_revision_recent_history_origin_status": "reopened_from_redirect_archive",
            "approval_revision_recent_history_origin_summary": "A previously redirected revision thread remains active continuity because the user explicitly reopened it.",
            "approval_revision_recent_history_origin_applied": True,
        },
        conversation_context=replace(
            make_card().conversation_context,
            clarified_interpretation="Only modify node.final_judge.",
        ),
    )
    approval = DesignerApprovalFlowState(
        approval_id="approval-replaced-reopened-history",
        intent_ref="intent-replaced-reopened-history",
        patch_ref="patch-replaced-reopened-history",
        precheck_ref="precheck-replaced-reopened-history",
        preview_ref="preview-replaced-reopened-history",
        current_stage="awaiting_decision",
        approval_policy=ApprovalPolicy(),
        required_decision_points=(DecisionPoint(decision_id="confirm.scope", label="Clarify scope"),),
        user_decisions=(
            UserDecision(
                decision_point_id="confirm.scope",
                outcome="request_revision",
                note="Continue with node.final_judge instead.",
            ),
        ),
        final_outcome="revision_requested",
        explanation="Revision requested before commit.",
        precheck_status="pass",
        blocking_finding_count=0,
        confirmation_finding_count=0,
        confirmation_resolved=True,
    )

    updated = coordinator.evolve_after_approval_resolution(current, approval_state=approval)

    assert "approval_revision_recent_history_origin_status" not in updated.notes
    assert updated.notes["approval_revision_recent_history_replacement_status"] == "replaced_after_reopen"
    assert updated.notes["approval_revision_recent_history_replacement_applied"] is True
    assert "replaced by a newer active revision thread" in updated.notes["approval_revision_recent_history_replacement_summary"]
