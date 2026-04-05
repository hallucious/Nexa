from __future__ import annotations

import pytest

from src.designer.approval_flow import DesignerApprovalCoordinator
from src.designer.commit_gateway import DesignerCommitGateway
from src.designer.patch_applier import DesignerPatchApplier
from src.designer.session_state_card_builder import DesignerSessionStateCardBuilder
from src.designer.session_state_persistence import (
    load_persisted_approval_flow_state,
    load_persisted_commit_candidate_state,
    load_persisted_proposal_control_state,
    persist_designer_session_state,
)
from src.designer.models.designer_approval_flow import UserDecision
from src.designer.proposal_flow import DesignerProposalFlow
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def make_candidate_working_save(*, working_save_id: str = "ws-001") -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            name="Designer Candidate",
            working_save_id=working_save_id,
        ),
        circuit=CircuitModel(
            nodes=[{"id": "node.start"}, {"id": "node.review"}],
            edges=[{"from": "node.start", "to": "node.review"}],
            entry="node.start",
            outputs=[{"name": "final_answer", "source": "node.review.output"}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={"question": "What is AI?"}, working={}, memory={}),
        runtime=RuntimeModel(status="validated", validation_summary={"blocking_count": 0}),
        ui=UIModel(layout={}, metadata={}),
    )


def test_approval_coordinator_creates_required_decision_points_from_confirmation_findings() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()

    state = coordinator.create_state(bundle)

    assert state.current_stage == "awaiting_decision"
    assert state.final_outcome == "pending"
    assert state.required_decision_points
    assert state.confirmation_resolved is False


def test_approval_coordinator_resolves_to_commit_eligible_state_after_approve() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)

    decisions = tuple(UserDecision(decision_point_id=point.decision_id, outcome="approve") for point in state.required_decision_points)
    approved = coordinator.resolve(state, decisions)

    assert approved.final_outcome == "approved_for_commit"
    assert approved.current_stage == "ready_to_commit"
    assert approved.commit_eligible is True
    assert approved.approved_scope_ref == approved.validated_scope_ref


def test_approval_coordinator_marks_revision_requested_when_scope_is_narrowed() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)

    revised = coordinator.resolve(
        state,
        [UserDecision(decision_point_id=state.required_decision_points[0].decision_id, outcome="narrow_scope")],
        approved_scope_ref="narrowed-scope",
        scope_revalidated=False,
    )

    assert revised.final_outcome == "revision_requested"
    assert revised.commit_eligible is False


def test_approval_coordinator_rejects_blocked_precheck_from_commit_path() -> None:
    from dataclasses import replace
    from src.designer.models.validation_precheck import PrecheckFinding

    flow = DesignerProposalFlow()
    bundle = flow.propose("Delete node judge from the whole circuit", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    blocked_precheck = replace(
        bundle.precheck,
        overall_status="blocked",
        blocking_findings=(PrecheckFinding(issue_code="BLOCKED", message="Broken structure.", severity="high"),),
        confirmation_findings=(),
    )
    blocked_bundle = replace(bundle, precheck=blocked_precheck)
    blocked = coordinator.create_state(blocked_bundle)

    assert blocked.precheck_status == "blocked"
    assert blocked.final_outcome == "rejected"
    assert blocked.commit_eligible is False


def test_commit_gateway_creates_commit_snapshot_from_commit_eligible_candidate() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)
    approved = coordinator.resolve(
        state,
        tuple(UserDecision(decision_point_id=point.decision_id, outcome="approve") for point in state.required_decision_points),
    )
    gateway = DesignerCommitGateway(coordinator=coordinator)

    result = gateway.commit_candidate(make_candidate_working_save(), approved, commit_id="commit-1")

    assert result.approval_state.current_stage == "committed"
    assert result.commit_snapshot.meta.commit_id == "commit-1"
    assert result.commit_snapshot.meta.storage_role == "commit_snapshot"
    assert result.commit_snapshot.approval.summary["approval_id"] == approved.approval_id
    assert result.serialized_commit_snapshot["meta"]["storage_role"] == "commit_snapshot"
    assert load_persisted_commit_candidate_state(result.cleaned_candidate_working_save) is None
    assert load_persisted_proposal_control_state(result.cleaned_candidate_working_save) is None
    restored_approval = load_persisted_approval_flow_state(result.cleaned_candidate_working_save)
    assert restored_approval is not None
    assert restored_approval.current_stage == "committed"
    rebuilt = DesignerSessionStateCardBuilder().build(request_text=bundle.request_text, artifact=result.cleaned_candidate_working_save)
    assert rebuilt.approval_state.approval_status == "committed"


def test_commit_gateway_rejects_non_commit_eligible_state() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)
    gateway = DesignerCommitGateway(coordinator=coordinator)

    with pytest.raises(ValueError):
        gateway.commit_candidate(make_candidate_working_save(), state, commit_id="commit-1")


def test_commit_gateway_can_resume_persisted_approval_ready_candidate() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)
    approved = coordinator.resolve(
        state,
        tuple(UserDecision(decision_point_id=point.decision_id, outcome="approve") for point in state.required_decision_points),
    )
    applier = DesignerPatchApplier()
    base = make_candidate_working_save()
    application = applier.apply_bundle(base, bundle)
    candidate_state = applier.build_commit_candidate_state(application, approved, source_working_save_ref="ws-001")
    card = DesignerSessionStateCardBuilder().build(request_text=bundle.request_text, artifact=application.candidate_working_save)
    persisted = persist_designer_session_state(
        application.candidate_working_save,
        session_state_card=card,
        approval_flow_state=approved,
        commit_candidate_state=candidate_state,
    )
    gateway = DesignerCommitGateway(coordinator=coordinator)

    result = gateway.commit_persisted_candidate(persisted, commit_id="commit-resume-1")

    assert result.approval_state.current_stage == "committed"
    assert result.commit_snapshot.meta.commit_id == "commit-resume-1"
    assert load_persisted_commit_candidate_state(result.cleaned_candidate_working_save) is None
    assert load_persisted_proposal_control_state(result.cleaned_candidate_working_save) is None
    cleaned_card = DesignerSessionStateCardBuilder().build(request_text=bundle.request_text, artifact=result.cleaned_candidate_working_save)
    assert cleaned_card.approval_state.approval_status == "committed"
    assert cleaned_card.notes["post_commit_cleanup_applied"] is True
    assert cleaned_card.notes["last_commit_id"] == "commit-resume-1"
    assert "resume_commit_candidate_ready" not in cleaned_card.notes

    with pytest.raises(ValueError):
        gateway.commit_persisted_candidate(result.cleaned_candidate_working_save, commit_id="commit-resume-2")


def test_approval_coordinator_surfaces_governance_next_step_in_decision_reason() -> None:
    flow = DesignerProposalFlow()
    card = DesignerSessionStateCardBuilder().build(request_text="Undo the last change", artifact=None, session_id="sess-gov-approval", target_scope_mode="existing_circuit")
    card = card.__class__(**{**card.__dict__, "notes": {
        **card.notes,
        "commit_summary_history": [
            {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
        ],
        "control_governance_policy_tier": "strict",
        "control_governance_requires_explicit_referential_anchor": True,
        "control_governance_precheck_message": "Repeated referential ambiguity has triggered strict governance mode. Provide an explicit commit anchor, explicit node target, or explicit non-latest selector before approval can continue safely.",
        "control_governance_preview_hint": "Strict referential governance is active. The next safe step is to restate the request with a stronger anchor instead of relying on 'last change' style language.",
        "control_governance_ambiguity_pressure_score": 5,
        "control_governance_ambiguity_pressure_band": "strict",
        "control_governance_pressure_transition": "escalating_or_sustained_repeat_pressure",
        "control_governance_pressure_summary": "Ambiguity pressure is high and still building (5/5, strict band).",
    }})
    bundle = flow.propose("Undo the last change", working_save_ref="ws-001", session_state_card=card)
    coordinator = DesignerApprovalCoordinator()

    state = coordinator.create_state(bundle)

    governance_point = next(point for point in state.required_decision_points if point.decision_id == "referential_governance_strict")
    assert "provide explicit anchor" in (governance_point.reason or "")
    assert "5/5, strict band" in (governance_point.reason or "")

