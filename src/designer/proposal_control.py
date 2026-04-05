from __future__ import annotations

from dataclasses import replace

from src.designer.models.designer_proposal_control import (
    DesignerControlledProposalResult,
    DesignerProposalControlState,
    ProposalAttemptRecord,
    ProposalControlPolicy,
)
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.proposal_flow import DesignerProposalBundle, DesignerProposalFlow
from src.designer.reason_codes import first_mixed_referential_reason_from_findings
from src.designer.session_state_coordinator import DesignerSessionStateCoordinator


class DesignerProposalControlPlane:
    """Phase 2 proposal-flow control foundation.

    This layer does not auto-commit and does not silently mutate scope.
    It makes retry / fallback / revision handling explicit around the existing
    non-committing proposal flow.
    """

    def __init__(self, *, proposal_flow: DesignerProposalFlow | None = None, session_state_coordinator: DesignerSessionStateCoordinator | None = None) -> None:
        self._proposal_flow = proposal_flow or DesignerProposalFlow()
        self._session_state_coordinator = session_state_coordinator or DesignerSessionStateCoordinator()

    def run(
        self,
        request_text: str,
        *,
        working_save_ref: str | None = None,
        session_state_card: DesignerSessionStateCard | None = None,
        control_state: DesignerProposalControlState | None = None,
        control_policy: ProposalControlPolicy | None = None,
    ) -> DesignerControlledProposalResult:
        policy = control_policy or ProposalControlPolicy()
        state = control_state or self._initial_state(session_state_card)
        try:
            bundle = self._proposal_flow.propose(
                request_text,
                working_save_ref=working_save_ref,
                session_state_card=session_state_card,
            )
        except ValueError as exc:
            result = self._from_exception(state, policy, exc)
        else:
            result = self._from_bundle(state, policy, bundle)

        if session_state_card is not None:
            return replace(
                result,
                updated_session_state_card=self._session_state_coordinator.evolve_after_control_result(
                    session_state_card,
                    result,
                ),
            )
        return result

    def _initial_state(self, session_state_card: DesignerSessionStateCard | None) -> DesignerProposalControlState:
        if session_state_card is None:
            return DesignerProposalControlState(session_id="proposal-control")
        return DesignerProposalControlState(
            session_id=session_state_card.session_id,
            revision_rounds=session_state_card.revision_state.revision_index,
            pending_reason=session_state_card.revision_state.retry_reason,
        )

    def _from_exception(
        self,
        state: DesignerProposalControlState,
        policy: ProposalControlPolicy,
        exc: ValueError,
    ) -> DesignerControlledProposalResult:
        message = str(exc)
        next_attempt_index = len(state.history) + 1
        if "mutation-oriented" in message and policy.allow_read_only_fallback:
            next_state = replace(
                state,
                current_stage="normalize",
                next_action="fallback_to_read_only",
                terminal_status="awaiting_user_input",
                normalization_attempts=state.normalization_attempts + 1,
                fallback_count=state.fallback_count + 1,
                pending_reason="Explain/analyze request cannot continue through mutation-oriented proposal flow.",
                history=state.history
                + (
                    ProposalAttemptRecord(
                        attempt_index=next_attempt_index,
                        stage="normalize",
                        outcome="fallback_selected",
                        reason_code="DESIGNER-FALLBACK-READ-ONLY",
                        message="Fallback to read-only path is required for explain/analyze requests.",
                    ),
                ),
            )
            return DesignerControlledProposalResult(
                control_state=next_state,
                explanation="The request was normalized into a read-only fallback rather than a mutation proposal.",
            )

        attempts = state.normalization_attempts + 1
        retryable = attempts < policy.max_normalization_attempts
        next_state = replace(
            state,
            current_stage="normalize",
            next_action="retry_normalization" if retryable else "request_user_revision",
            terminal_status="in_progress" if retryable else "exhausted",
            normalization_attempts=attempts,
            pending_reason=message,
            history=state.history
            + (
                ProposalAttemptRecord(
                    attempt_index=next_attempt_index,
                    stage="normalize",
                    outcome="retryable_failure" if retryable else "terminal_failure",
                    reason_code="DESIGNER-NORMALIZE-ERROR",
                    message=message,
                ),
            ),
        )
        return DesignerControlledProposalResult(
            control_state=next_state,
            explanation="The proposal flow stopped during normalization and now requires explicit retry or revision handling.",
        )

    def _from_bundle(
        self,
        state: DesignerProposalControlState,
        policy: ProposalControlPolicy,
        bundle: DesignerProposalBundle,
    ) -> DesignerControlledProposalResult:
        next_attempt_index = len(state.history) + 1
        status = bundle.precheck.overall_status
        if status == "blocked":
            exhausted = (
                state.blocked_precheck_count + 1 > policy.max_blocked_precheck_retries
                or state.revision_rounds + 1 > policy.max_revision_rounds
            )
            next_state = replace(
                state,
                current_stage="precheck",
                next_action="request_user_revision" if not exhausted else "abort",
                terminal_status="awaiting_user_input" if not exhausted else "exhausted",
                blocked_precheck_count=state.blocked_precheck_count + 1,
                revision_rounds=state.revision_rounds + 1,
                last_precheck_status=status,
                pending_reason=bundle.precheck.explanation,
                history=state.history
                + (
                    ProposalAttemptRecord(
                        attempt_index=next_attempt_index,
                        stage="precheck",
                        outcome="blocked" if not exhausted else "terminal_failure",
                        reason_code="DESIGNER-PRECHECK-BLOCKED",
                        message=bundle.precheck.explanation,
                    ),
                ),
            )
            return DesignerControlledProposalResult(
                control_state=next_state,
                bundle=bundle,
                explanation="The patch reached precheck but is blocked. The next transition must be an explicit revision or abort.",
            )

        if status == "confirmation_required":
            next_action = "choose_interpretation" if bundle.intent.ambiguity_flags else "await_user_confirmation"
            confirmation_reason_code, confirmation_message = first_mixed_referential_reason_from_findings(
                bundle.precheck.confirmation_findings
            )
            next_state = replace(
                state,
                current_stage="approval_boundary",
                next_action=next_action,
                terminal_status="awaiting_user_input",
                fallback_count=state.fallback_count + (1 if next_action == "choose_interpretation" else 0),
                last_precheck_status=status,
                pending_reason=confirmation_message or bundle.precheck.explanation,
                history=state.history
                + (
                    ProposalAttemptRecord(
                        attempt_index=next_attempt_index,
                        stage="precheck",
                        outcome="confirmation_required",
                        reason_code=confirmation_reason_code or "DESIGNER-CONFIRMATION-REQUIRED",
                        message=confirmation_message or bundle.precheck.explanation,
                    ),
                ),
            )
            return DesignerControlledProposalResult(
                control_state=next_state,
                bundle=bundle,
                explanation="The proposal is previewable but cannot advance until ambiguity or confirmation is explicitly resolved.",
            )

        next_state = replace(
            state,
            current_stage="approval_boundary",
            next_action="proceed_to_approval",
            terminal_status="ready_for_approval",
            last_precheck_status=status,
            pending_reason=None,
            history=state.history
            + (
                ProposalAttemptRecord(
                    attempt_index=next_attempt_index,
                    stage="preview",
                    outcome="ready_for_approval",
                    reason_code="DESIGNER-READY-FOR-APPROVAL",
                    message="Proposal bundle passed into the approval boundary.",
                ),
            ),
        )
        return DesignerControlledProposalResult(
            control_state=next_state,
            bundle=bundle,
            explanation="The proposal bundle is ready to cross into the explicit approval flow.",
        )
