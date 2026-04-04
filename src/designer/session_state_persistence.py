from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Mapping

from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec
from src.designer.models.designer_proposal_control import (
    DesignerProposalControlState,
    ProposalAttemptRecord,
)
from src.designer.models.designer_session_state_card import (
    ApprovalState,
    AvailableResources,
    ConversationContext,
    CurrentFindingsState,
    CurrentRisksState,
    CurrentSelectionState,
    DesignerSessionStateCard,
    ForbiddenAuthority,
    OutputContract,
    ResourceAvailability,
    RevisionAttemptSummary,
    RevisionState,
    SessionTargetScope,
    WorkingSaveReality,
)
from src.storage.models.working_save_model import DesignerDraftModel, WorkingSaveModel

_SESSION_CARD_KEY = "designer_session_state_card"
_CONTROL_STATE_KEY = "designer_proposal_control_state"


def serialize_session_state_card(card: DesignerSessionStateCard) -> dict[str, Any]:
    return {
        "card_version": card.card_version,
        "session_id": card.session_id,
        "storage_role": card.storage_role,
        "current_working_save": {
            "mode": card.current_working_save.mode,
            "savefile_ref": card.current_working_save.savefile_ref,
            "current_revision": card.current_working_save.current_revision,
            "circuit_summary": card.current_working_save.circuit_summary,
            "node_list": list(card.current_working_save.node_list),
            "edge_list": list(card.current_working_save.edge_list),
            "output_list": list(card.current_working_save.output_list),
            "prompt_refs": list(card.current_working_save.prompt_refs),
            "provider_refs": list(card.current_working_save.provider_refs),
            "plugin_refs": list(card.current_working_save.plugin_refs),
            "draft_validity_status": card.current_working_save.draft_validity_status,
        },
        "current_selection": {
            "selection_mode": card.current_selection.selection_mode,
            "selected_refs": list(card.current_selection.selected_refs),
        },
        "target_scope": {
            "mode": card.target_scope.mode,
            "touch_budget": card.target_scope.touch_budget,
            "allowed_node_refs": list(card.target_scope.allowed_node_refs),
            "allowed_edge_refs": list(card.target_scope.allowed_edge_refs),
            "allowed_output_refs": list(card.target_scope.allowed_output_refs),
            "destructive_edit_allowed": card.target_scope.destructive_edit_allowed,
        },
        "available_resources": {
            "prompts": [_serialize_resource(item) for item in card.available_resources.prompts],
            "providers": [_serialize_resource(item) for item in card.available_resources.providers],
            "plugins": [_serialize_resource(item) for item in card.available_resources.plugins],
        },
        "objective": {
            "primary_goal": card.objective.primary_goal,
            "secondary_goals": list(card.objective.secondary_goals),
            "success_criteria": list(card.objective.success_criteria),
            "preferred_behavior": card.objective.preferred_behavior,
        },
        "constraints": {
            "cost_limit": card.constraints.cost_limit,
            "speed_priority": card.constraints.speed_priority,
            "quality_priority": card.constraints.quality_priority,
            "determinism_preference": card.constraints.determinism_preference,
            "provider_preferences": list(card.constraints.provider_preferences),
            "provider_restrictions": list(card.constraints.provider_restrictions),
            "plugin_preferences": list(card.constraints.plugin_preferences),
            "plugin_restrictions": list(card.constraints.plugin_restrictions),
            "human_review_required": card.constraints.human_review_required,
            "safety_level": card.constraints.safety_level,
            "output_requirements": list(card.constraints.output_requirements),
            "forbidden_patterns": list(card.constraints.forbidden_patterns),
        },
        "current_findings": {
            "blocking_findings": list(card.current_findings.blocking_findings),
            "warning_findings": list(card.current_findings.warning_findings),
            "confirmation_findings": list(card.current_findings.confirmation_findings),
            "finding_summary": card.current_findings.finding_summary,
        },
        "current_risks": {
            "risk_flags": list(card.current_risks.risk_flags),
            "severity_summary": card.current_risks.severity_summary,
            "unresolved_high_risks": list(card.current_risks.unresolved_high_risks),
        },
        "revision_state": {
            "revision_index": card.revision_state.revision_index,
            "based_on_intent_id": card.revision_state.based_on_intent_id,
            "based_on_patch_id": card.revision_state.based_on_patch_id,
            "prior_rejection_reasons": list(card.revision_state.prior_rejection_reasons),
            "retry_reason": card.revision_state.retry_reason,
            "user_corrections": list(card.revision_state.user_corrections),
            "last_control_action": card.revision_state.last_control_action,
            "last_terminal_status": card.revision_state.last_terminal_status,
            "attempt_history": [_serialize_attempt_summary(item) for item in card.revision_state.attempt_history],
        },
        "approval_state": {
            "approval_required": card.approval_state.approval_required,
            "approval_status": card.approval_state.approval_status,
            "confirmation_required": card.approval_state.confirmation_required,
            "blocking_before_commit": card.approval_state.blocking_before_commit,
        },
        "conversation_context": {
            "user_request_text": card.conversation_context.user_request_text,
            "clarified_interpretation": card.conversation_context.clarified_interpretation,
            "unresolved_questions": list(card.conversation_context.unresolved_questions),
            "explicit_user_preferences": list(card.conversation_context.explicit_user_preferences),
        },
        "output_contract": {
            "required_primary_output": card.output_contract.required_primary_output,
            "allowed_secondary_outputs": list(card.output_contract.allowed_secondary_outputs),
            "preview_required": card.output_contract.preview_required,
        },
        "forbidden_authority": {
            "may_commit_directly": card.forbidden_authority.may_commit_directly,
            "may_redefine_engine_contracts": card.forbidden_authority.may_redefine_engine_contracts,
            "may_bypass_precheck": card.forbidden_authority.may_bypass_precheck,
            "may_bypass_preview": card.forbidden_authority.may_bypass_preview,
            "may_bypass_approval": card.forbidden_authority.may_bypass_approval,
            "may_mutate_committed_truth_directly": card.forbidden_authority.may_mutate_committed_truth_directly,
        },
        "notes": deepcopy(card.notes),
    }


def deserialize_session_state_card(data: Mapping[str, Any]) -> DesignerSessionStateCard:
    current_working_save = data.get("current_working_save", {})
    current_selection = data.get("current_selection", {})
    target_scope = data.get("target_scope", {})
    available_resources = data.get("available_resources", {})
    objective = data.get("objective", {})
    constraints = data.get("constraints", {})
    findings = data.get("current_findings", {})
    risks = data.get("current_risks", {})
    revision_state = data.get("revision_state", {})
    approval_state = data.get("approval_state", {})
    conversation = data.get("conversation_context", {})
    output_contract = data.get("output_contract", {})
    forbidden_authority = data.get("forbidden_authority", {})
    return DesignerSessionStateCard(
        card_version=str(data.get("card_version", "0.1")),
        session_id=str(data.get("session_id", "session-restored")),
        storage_role=str(data.get("storage_role", "working_save")),
        current_working_save=WorkingSaveReality(
            mode=str(current_working_save.get("mode", "empty_draft")),
            savefile_ref=current_working_save.get("savefile_ref"),
            current_revision=current_working_save.get("current_revision"),
            circuit_summary=str(current_working_save.get("circuit_summary", "")),
            node_list=tuple(current_working_save.get("node_list", ())),
            edge_list=tuple(current_working_save.get("edge_list", ())),
            output_list=tuple(current_working_save.get("output_list", ())),
            prompt_refs=tuple(current_working_save.get("prompt_refs", ())),
            provider_refs=tuple(current_working_save.get("provider_refs", ())),
            plugin_refs=tuple(current_working_save.get("plugin_refs", ())),
            draft_validity_status=str(current_working_save.get("draft_validity_status", "unknown")),
        ),
        current_selection=CurrentSelectionState(
            selection_mode=str(current_selection.get("selection_mode", "none")),
            selected_refs=tuple(current_selection.get("selected_refs", ())),
        ),
        target_scope=SessionTargetScope(
            mode=str(target_scope.get("mode", "existing_circuit")),
            touch_budget=str(target_scope.get("touch_budget", "bounded")),
            allowed_node_refs=tuple(target_scope.get("allowed_node_refs", ())),
            allowed_edge_refs=tuple(target_scope.get("allowed_edge_refs", ())),
            allowed_output_refs=tuple(target_scope.get("allowed_output_refs", ())),
            destructive_edit_allowed=bool(target_scope.get("destructive_edit_allowed", False)),
        ),
        available_resources=AvailableResources(
            prompts=tuple(_deserialize_resource(item) for item in available_resources.get("prompts", ())),
            providers=tuple(_deserialize_resource(item) for item in available_resources.get("providers", ())),
            plugins=tuple(_deserialize_resource(item) for item in available_resources.get("plugins", ())),
        ),
        objective=ObjectiveSpec(
            primary_goal=str(objective.get("primary_goal", "restored session")),
            secondary_goals=tuple(objective.get("secondary_goals", ())),
            success_criteria=tuple(objective.get("success_criteria", ())),
            preferred_behavior=objective.get("preferred_behavior"),
        ),
        constraints=ConstraintSet(
            cost_limit=constraints.get("cost_limit"),
            speed_priority=constraints.get("speed_priority"),
            quality_priority=constraints.get("quality_priority"),
            determinism_preference=constraints.get("determinism_preference"),
            provider_preferences=tuple(constraints.get("provider_preferences", ())),
            provider_restrictions=tuple(constraints.get("provider_restrictions", ())),
            plugin_preferences=tuple(constraints.get("plugin_preferences", ())),
            plugin_restrictions=tuple(constraints.get("plugin_restrictions", ())),
            human_review_required=bool(constraints.get("human_review_required", False)),
            safety_level=constraints.get("safety_level"),
            output_requirements=tuple(constraints.get("output_requirements", ())),
            forbidden_patterns=tuple(constraints.get("forbidden_patterns", ())),
        ),
        current_findings=CurrentFindingsState(
            blocking_findings=tuple(findings.get("blocking_findings", ())),
            warning_findings=tuple(findings.get("warning_findings", ())),
            confirmation_findings=tuple(findings.get("confirmation_findings", ())),
            finding_summary=str(findings.get("finding_summary", "")),
        ),
        current_risks=CurrentRisksState(
            risk_flags=tuple(risks.get("risk_flags", ())),
            severity_summary=str(risks.get("severity_summary", "")),
            unresolved_high_risks=tuple(risks.get("unresolved_high_risks", ())),
        ),
        revision_state=RevisionState(
            revision_index=int(revision_state.get("revision_index", 0)),
            based_on_intent_id=revision_state.get("based_on_intent_id"),
            based_on_patch_id=revision_state.get("based_on_patch_id"),
            prior_rejection_reasons=tuple(revision_state.get("prior_rejection_reasons", ())),
            retry_reason=revision_state.get("retry_reason"),
            user_corrections=tuple(revision_state.get("user_corrections", ())),
            last_control_action=revision_state.get("last_control_action"),
            last_terminal_status=revision_state.get("last_terminal_status"),
            attempt_history=tuple(_deserialize_attempt_summary(item) for item in revision_state.get("attempt_history", ())),
        ),
        approval_state=ApprovalState(
            approval_required=bool(approval_state.get("approval_required", True)),
            approval_status=str(approval_state.get("approval_status", "not_started")),
            confirmation_required=bool(approval_state.get("confirmation_required", False)),
            blocking_before_commit=bool(approval_state.get("blocking_before_commit", False)),
        ),
        conversation_context=ConversationContext(
            user_request_text=str(conversation.get("user_request_text", "(restored request)")),
            clarified_interpretation=conversation.get("clarified_interpretation"),
            unresolved_questions=tuple(conversation.get("unresolved_questions", ())),
            explicit_user_preferences=tuple(conversation.get("explicit_user_preferences", ())),
        ),
        output_contract=OutputContract(
            required_primary_output=str(output_contract.get("required_primary_output", "normalized_intent")),
            allowed_secondary_outputs=tuple(output_contract.get("allowed_secondary_outputs", ("patch_plan", "explanation", "ambiguity_report", "risk_report"))),
            preview_required=bool(output_contract.get("preview_required", True)),
        ),
        forbidden_authority=ForbiddenAuthority(
            may_commit_directly=bool(forbidden_authority.get("may_commit_directly", False)),
            may_redefine_engine_contracts=bool(forbidden_authority.get("may_redefine_engine_contracts", False)),
            may_bypass_precheck=bool(forbidden_authority.get("may_bypass_precheck", False)),
            may_bypass_preview=bool(forbidden_authority.get("may_bypass_preview", False)),
            may_bypass_approval=bool(forbidden_authority.get("may_bypass_approval", False)),
            may_mutate_committed_truth_directly=bool(forbidden_authority.get("may_mutate_committed_truth_directly", False)),
        ),
        notes=deepcopy(dict(data.get("notes", {}))),
    )


def serialize_proposal_control_state(state: DesignerProposalControlState) -> dict[str, Any]:
    return {
        "session_id": state.session_id,
        "current_stage": state.current_stage,
        "next_action": state.next_action,
        "terminal_status": state.terminal_status,
        "normalization_attempts": state.normalization_attempts,
        "revision_rounds": state.revision_rounds,
        "blocked_precheck_count": state.blocked_precheck_count,
        "fallback_count": state.fallback_count,
        "last_precheck_status": state.last_precheck_status,
        "pending_reason": state.pending_reason,
        "history": [
            {
                "attempt_index": item.attempt_index,
                "stage": item.stage,
                "outcome": item.outcome,
                "reason_code": item.reason_code,
                "message": item.message,
            }
            for item in state.history
        ],
    }


def deserialize_proposal_control_state(data: Mapping[str, Any]) -> DesignerProposalControlState:
    return DesignerProposalControlState(
        session_id=str(data.get("session_id", "proposal-control")),
        current_stage=str(data.get("current_stage", "normalize")),
        next_action=str(data.get("next_action", "retry_normalization")),
        terminal_status=str(data.get("terminal_status", "in_progress")),
        normalization_attempts=int(data.get("normalization_attempts", 0)),
        revision_rounds=int(data.get("revision_rounds", 0)),
        blocked_precheck_count=int(data.get("blocked_precheck_count", 0)),
        fallback_count=int(data.get("fallback_count", 0)),
        last_precheck_status=data.get("last_precheck_status"),
        pending_reason=data.get("pending_reason"),
        history=tuple(
            ProposalAttemptRecord(
                attempt_index=int(item.get("attempt_index", 1)),
                stage=str(item.get("stage", "normalize")),
                outcome=str(item.get("outcome", "retryable_failure")),
                reason_code=str(item.get("reason_code", "DESIGNER-RESTORED-STATE")),
                message=str(item.get("message", "Restored proposal-control history entry.")),
            )
            for item in data.get("history", ())
        ),
    )


def load_persisted_session_state_card(working_save: WorkingSaveModel | None) -> DesignerSessionStateCard | None:
    if working_save is None or working_save.designer is None:
        return None
    snapshot = working_save.designer.data.get(_SESSION_CARD_KEY)
    if not isinstance(snapshot, Mapping):
        return None
    return deserialize_session_state_card(snapshot)


def load_persisted_proposal_control_state(working_save: WorkingSaveModel | None) -> DesignerProposalControlState | None:
    if working_save is None or working_save.designer is None:
        return None
    snapshot = working_save.designer.data.get(_CONTROL_STATE_KEY)
    if not isinstance(snapshot, Mapping):
        return None
    return deserialize_proposal_control_state(snapshot)


def persist_designer_session_state(
    working_save: WorkingSaveModel,
    *,
    session_state_card: DesignerSessionStateCard,
    control_state: DesignerProposalControlState | None = None,
) -> WorkingSaveModel:
    designer_data = deepcopy(working_save.designer.data if working_save.designer is not None else {})
    designer_data[_SESSION_CARD_KEY] = serialize_session_state_card(session_state_card)
    if control_state is not None:
        designer_data[_CONTROL_STATE_KEY] = serialize_proposal_control_state(control_state)
    return replace(working_save, designer=DesignerDraftModel(data=designer_data))


def _serialize_resource(item: ResourceAvailability) -> dict[str, Any]:
    return {
        "id": item.id,
        "availability_status": item.availability_status,
        "version": item.version,
        "tags": list(item.tags),
        "constraints": list(item.constraints),
        "notes": item.notes,
    }


def _deserialize_resource(data: Mapping[str, Any]) -> ResourceAvailability:
    return ResourceAvailability(
        id=str(data.get("id", "resource.unknown")),
        availability_status=str(data.get("availability_status", "unknown")),
        version=data.get("version"),
        tags=tuple(data.get("tags", ())),
        constraints=tuple(data.get("constraints", ())),
        notes=data.get("notes"),
    )


def _serialize_attempt_summary(item: RevisionAttemptSummary) -> dict[str, Any]:
    return {
        "attempt_index": item.attempt_index,
        "stage": item.stage,
        "outcome": item.outcome,
        "reason_code": item.reason_code,
        "message": item.message,
    }


def _deserialize_attempt_summary(data: Mapping[str, Any]) -> RevisionAttemptSummary:
    return RevisionAttemptSummary(
        attempt_index=int(data.get("attempt_index", 1)),
        stage=str(data.get("stage", "normalize")),
        outcome=str(data.get("outcome", "retryable_failure")),
        reason_code=str(data.get("reason_code", "DESIGNER-RESTORED-ATTEMPT")),
        message=str(data.get("message", "Restored attempt summary.")),
    )
