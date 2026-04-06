from __future__ import annotations

from dataclasses import replace

from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.control_governance import (
    advance_recent_anchor_resolution_notes,
    advance_recent_revision_history_notes,
    advance_recent_revision_redirect_archive_notes,
    apply_control_governance_notes,
    clear_recent_anchor_resolution_notes,
    clear_recent_revision_redirect_archive_notes,
    governance_pending_anchor_applicability_for_request,
    governance_pending_anchor_is_fully_satisfied,
    governance_pending_anchor_resolution_summary,
    governance_revision_guidance_from_notes,
    governance_revision_snapshot_from_notes,
    is_governance_confirmation_issue_code,
    is_governance_decision_id,
)
from src.designer.models.designer_proposal_control import DesignerControlledProposalResult
from src.designer.models.designer_session_state_card import (
    ApprovalState,
    ConversationContext,
    CurrentFindingsState,
    DesignerSessionStateCard,
    RevisionAttemptSummary,
    RevisionState,
    SessionTargetScope,
)
_RECENT_APPROVAL_REVISION_HISTORY_LIMIT = 3

from src.designer.reason_codes import (
    activate_mixed_referential_reason_notes,
    clear_active_mixed_referential_reason_notes,
    first_mixed_referential_reason_code_from_decision_ids,
    is_designer_mixed_referential_reason_code,
)


class DesignerSessionStateCoordinator:
    """Updates the session card from proposal-control outcomes.

    This keeps revision state, findings, approval hints, and read-only fallback
    direction synchronized with the explicit proposal control result.
    """

    def evolve_after_control_result(
        self,
        session_state_card: DesignerSessionStateCard,
        control_result: DesignerControlledProposalResult,
    ) -> DesignerSessionStateCard:
        control_state = control_result.control_state
        bundle = control_result.bundle

        next_scope = session_state_card.target_scope
        if control_state.next_action == "fallback_to_read_only":
            next_scope = replace(
                session_state_card.target_scope,
                mode="read_only",
                touch_budget="minimal",
            )

        next_findings = session_state_card.current_findings
        next_approval = session_state_card.approval_state
        if bundle is not None:
            next_findings = CurrentFindingsState(
                blocking_findings=tuple(f.message for f in bundle.precheck.blocking_findings),
                warning_findings=tuple(f.message for f in bundle.precheck.warning_findings),
                confirmation_findings=tuple(f.message for f in bundle.precheck.confirmation_findings),
                finding_summary=bundle.precheck.explanation,
            )
            next_approval = ApprovalState(
                approval_required=control_state.next_action != "fallback_to_read_only",
                approval_status="pending" if control_state.terminal_status == "ready_for_approval" else "not_started",
                confirmation_required=bundle.precheck.overall_status == "confirmation_required",
                blocking_before_commit=bundle.precheck.overall_status == "blocked" or bool(bundle.precheck.blocking_findings),
            )
        elif control_state.next_action == "fallback_to_read_only":
            next_approval = ApprovalState(
                approval_required=False,
                approval_status="not_started",
                confirmation_required=False,
                blocking_before_commit=False,
            )

        prior_rejections = session_state_card.revision_state.prior_rejection_reasons
        if control_state.next_action in {"request_user_revision", "abort"} and control_state.pending_reason:
            prior_rejections = prior_rejections + (control_state.pending_reason,)
        # preserve uniqueness while keeping order
        deduped_rejections = tuple(dict.fromkeys(prior_rejections))

        next_revision = RevisionState(
            revision_index=control_state.revision_rounds,
            based_on_intent_id=bundle.intent.intent_id if bundle is not None else session_state_card.revision_state.based_on_intent_id,
            based_on_patch_id=bundle.patch.patch_id if bundle is not None else session_state_card.revision_state.based_on_patch_id,
            prior_rejection_reasons=deduped_rejections,
            retry_reason=control_state.pending_reason,
            user_corrections=session_state_card.revision_state.user_corrections,
            last_control_action=control_state.next_action,
            last_terminal_status=control_state.terminal_status,
            attempt_history=tuple(
                RevisionAttemptSummary(
                    attempt_index=item.attempt_index,
                    stage=item.stage,
                    outcome=item.outcome,
                    reason_code=item.reason_code,
                    message=item.message,
                )
                for item in control_state.history
            ),
        )

        next_conversation = ConversationContext(
            user_request_text=session_state_card.conversation_context.user_request_text,
            clarified_interpretation=session_state_card.conversation_context.clarified_interpretation,
            unresolved_questions=self._next_unresolved_questions(session_state_card, control_state, bundle),
            explicit_user_preferences=session_state_card.conversation_context.explicit_user_preferences,
        )

        latest_attempt = control_state.history[-1] if control_state.history else None
        pending_anchor_applicability = governance_pending_anchor_applicability_for_request(
            session_state_card.notes,
            session_state_card.conversation_context.user_request_text,
            available_node_refs=session_state_card.current_working_save.node_list,
            commit_history=tuple(item for item in session_state_card.notes.get("commit_summary_history", ()) if isinstance(item, dict)),
        )
        governance_issue_codes = tuple(
            finding.issue_code
            for finding in (bundle.precheck.confirmation_findings if bundle is not None else ())
            if is_governance_confirmation_issue_code(finding.issue_code)
        )
        next_notes = {
            **session_state_card.notes,
            "last_control_action": control_state.next_action,
            "last_terminal_status": control_state.terminal_status,
            **({
                "last_attempt_reason_code": latest_attempt.reason_code,
                "last_attempt_stage": latest_attempt.stage,
                "last_attempt_outcome": latest_attempt.outcome,
            } if latest_attempt is not None else {}),
        }
        if latest_attempt is not None and is_designer_mixed_referential_reason_code(latest_attempt.reason_code):
            next_notes = activate_mixed_referential_reason_notes(
                next_notes,
                reason_code=latest_attempt.reason_code,
                stage=latest_attempt.stage,
                status=latest_attempt.outcome,
                source_note_key="last_attempt_reason_code",
            )
        else:
            next_notes = clear_active_mixed_referential_reason_notes(next_notes)
        if governance_pending_anchor_is_fully_satisfied(
            pending_anchor_applicability,
            governance_issue_codes=governance_issue_codes,
        ):
            next_notes.pop("control_governance_pending_anchor_requirement", None)
            next_notes.pop("control_governance_pending_anchor_requirement_mode", None)
            next_notes.pop("control_governance_last_revision_guidance", None)
            next_notes.pop("control_governance_last_revision_pressure_summary", None)
            next_notes.pop("control_governance_last_revision_pressure_score", None)
            next_notes.pop("control_governance_last_revision_pressure_band", None)
            next_notes.pop("control_governance_last_revision_next_actions", None)
            next_notes["control_governance_last_pending_anchor_resolution_status"] = "cleared_by_anchored_retry"
            next_notes["control_governance_last_pending_anchor_resolution_summary"] = governance_pending_anchor_resolution_summary(
                pending_anchor_applicability
            )
            next_notes["control_governance_last_pending_anchor_resolution_request_text"] = (
                session_state_card.conversation_context.user_request_text
            )
            next_notes["control_governance_last_pending_anchor_resolution_age"] = 0
        else:
            next_notes = advance_recent_anchor_resolution_notes(next_notes)
        next_notes = advance_recent_revision_history_notes(next_notes)
        next_notes = advance_recent_revision_redirect_archive_notes(next_notes)
        next_notes = apply_control_governance_notes(next_notes, next_revision.attempt_history)
        return replace(
            session_state_card,
            target_scope=next_scope,
            current_findings=next_findings,
            revision_state=next_revision,
            approval_state=next_approval,
            conversation_context=next_conversation,
            notes=next_notes,
        )

    def _next_unresolved_questions(
        self,
        session_state_card: DesignerSessionStateCard,
        control_state,
        bundle,
    ) -> tuple[str, ...]:
        existing = list(session_state_card.conversation_context.unresolved_questions)
        if control_state.next_action == "choose_interpretation":
            existing.append(control_state.pending_reason or "A structural interpretation must be chosen before proceeding.")
        elif control_state.next_action == "await_user_confirmation":
            existing.append(control_state.pending_reason or "User confirmation is required before approval can begin.")
        elif control_state.next_action == "request_user_revision":
            existing.append(control_state.pending_reason or "A user revision is required before another proposal attempt.")
        elif control_state.next_action == "fallback_to_read_only":
            existing.append("The request should continue through a read-only explain/analyze path instead of mutation flow.")
        return tuple(dict.fromkeys(existing))


    def evolve_after_approval_resolution(
        self,
        session_state_card: DesignerSessionStateCard,
        approval_state: DesignerApprovalFlowState,
    ) -> DesignerSessionStateCard:
        choose_decisions = tuple(
            decision for decision in approval_state.user_decisions if decision.outcome == "choose_interpretation"
        )
        revision_decisions = tuple(
            decision for decision in approval_state.user_decisions if decision.outcome in {"request_revision", "narrow_scope"}
        )

        clarified_interpretation = session_state_card.conversation_context.clarified_interpretation
        if choose_decisions:
            clarified_interpretation = next(
                (decision.selected_option for decision in reversed(choose_decisions) if decision.selected_option),
                clarified_interpretation,
            )

        correction_notes = tuple(
            decision.note.strip()
            for decision in revision_decisions
            if decision.note is not None and decision.note.strip()
        )
        user_corrections = session_state_card.revision_state.user_corrections + correction_notes
        user_corrections = tuple(dict.fromkeys(user_corrections))

        mixed_revision_reason_code = self._mixed_revision_reason_code_from_approval_state(approval_state)

        unresolved_questions = list(session_state_card.conversation_context.unresolved_questions)
        if clarified_interpretation is not None:
            unresolved_questions = [
                item for item in unresolved_questions if "interpret" not in item.casefold()
            ]
        governance_revision_requested = any(
            is_governance_decision_id(decision.decision_point_id)
            for decision in approval_state.user_decisions
            if decision.outcome in {"request_revision", "narrow_scope", "choose_interpretation"}
        )
        governance_snapshot = governance_revision_snapshot_from_notes(session_state_card.notes) if governance_revision_requested else {}
        governance_guidance = governance_snapshot.get("message", "")
        if approval_state.final_outcome == "revision_requested" and not correction_notes and not choose_decisions:
            message = "A revised designer request is required before another approval attempt."
            if mixed_revision_reason_code is not None:
                message = f"{message} (reason_code={mixed_revision_reason_code})"
            unresolved_questions.append(message)
        if governance_guidance and approval_state.final_outcome == "revision_requested":
            unresolved_questions.append(governance_guidance)
            next_actions = governance_snapshot.get("next_actions", [])
            if next_actions:
                pretty = ", then ".join(str(item).replace("_", " ") for item in next_actions)
                unresolved_questions.append(f"Next safe step: {pretty}.")
        if approval_state.final_outcome == "approved_for_commit":
            unresolved_questions = []
        next_conversation = ConversationContext(
            user_request_text=session_state_card.conversation_context.user_request_text,
            clarified_interpretation=clarified_interpretation,
            unresolved_questions=tuple(dict.fromkeys(unresolved_questions)),
            explicit_user_preferences=session_state_card.conversation_context.explicit_user_preferences,
        )

        prior_rejections = list(session_state_card.revision_state.prior_rejection_reasons)
        if approval_state.final_outcome in {"revision_requested", "rejected", "aborted"}:
            if approval_state.explanation.strip():
                prior_rejections.append(approval_state.explanation.strip())
        next_action = session_state_card.revision_state.last_control_action
        next_terminal = session_state_card.revision_state.last_terminal_status
        next_retry_reason = session_state_card.revision_state.retry_reason
        revision_index = session_state_card.revision_state.revision_index
        if approval_state.final_outcome == "revision_requested":
            revision_index += 1
            next_action = "choose_interpretation" if choose_decisions else "request_user_revision"
            next_terminal = "awaiting_user_input"
            next_retry_reason = mixed_revision_reason_code or "approval_revision_requested"
        elif approval_state.final_outcome == "approved_for_commit":
            next_action = "proceed_to_approval"
            next_terminal = "ready_for_approval"
            next_retry_reason = None

        next_revision = RevisionState(
            revision_index=revision_index,
            based_on_intent_id=session_state_card.revision_state.based_on_intent_id,
            based_on_patch_id=session_state_card.revision_state.based_on_patch_id,
            prior_rejection_reasons=tuple(dict.fromkeys(prior_rejections)),
            retry_reason=next_retry_reason,
            user_corrections=user_corrections,
            last_control_action=next_action,
            last_terminal_status=next_terminal,
            attempt_history=session_state_card.revision_state.attempt_history,
        )

        summary_status = "not_started"
        if approval_state.final_outcome == "approved_for_commit":
            summary_status = "approved"
        elif approval_state.final_outcome in {"rejected", "aborted"}:
            summary_status = "rejected"
        elif approval_state.final_outcome == "revision_requested":
            summary_status = "not_started"
        elif approval_state.final_outcome == "pending" or approval_state.current_stage == "awaiting_decision":
            summary_status = "pending"

        next_approval = ApprovalState(
            approval_required=approval_state.final_outcome != "revision_requested",
            approval_status=summary_status,
            confirmation_required=bool(approval_state.unanswered_required_decision_points),
            blocking_before_commit=(approval_state.precheck_status == "blocked" or approval_state.blocking_finding_count > 0),
        )

        next_notes = dict(session_state_card.notes)
        next_notes["last_approval_stage"] = approval_state.current_stage
        next_notes["last_approval_outcome"] = approval_state.final_outcome
        next_notes = self._update_recent_approval_revision_history(
            next_notes,
            approval_state=approval_state,
            clarified_interpretation=clarified_interpretation,
            correction_notes=correction_notes,
            governance_snapshot=governance_snapshot,
            next_revision_index=revision_index,
        )
        if governance_guidance and approval_state.final_outcome == "revision_requested":
            next_notes["control_governance_pending_anchor_requirement"] = True
            next_notes["control_governance_last_revision_guidance"] = governance_guidance
            next_notes["control_governance_pending_anchor_requirement_mode"] = governance_snapshot.get("mode", "required")
            next_notes["control_governance_last_revision_pressure_summary"] = governance_snapshot.get("pressure_summary", "")
            next_notes["control_governance_last_revision_pressure_score"] = governance_snapshot.get("pressure_score", 0)
            next_notes["control_governance_last_revision_pressure_band"] = governance_snapshot.get("pressure_band", "standard")
            next_notes["control_governance_last_revision_next_actions"] = governance_snapshot.get("next_actions", [])
            next_notes = clear_recent_anchor_resolution_notes(next_notes)
        else:
            next_notes.pop("control_governance_pending_anchor_requirement", None)
            next_notes.pop("control_governance_last_revision_guidance", None)
            next_notes.pop("control_governance_pending_anchor_requirement_mode", None)
            next_notes.pop("control_governance_last_revision_pressure_summary", None)
            next_notes.pop("control_governance_last_revision_pressure_score", None)
            next_notes.pop("control_governance_last_revision_pressure_band", None)
            next_notes.pop("control_governance_last_revision_next_actions", None)
        if mixed_revision_reason_code is not None:
            next_notes["last_revision_reason_code"] = mixed_revision_reason_code
            next_notes = activate_mixed_referential_reason_notes(
                next_notes,
                reason_code=mixed_revision_reason_code,
                stage="approval_revision",
                status=approval_state.final_outcome,
                source_note_key="last_revision_reason_code",
            )
        else:
            next_notes.pop("last_revision_reason_code", None)
            next_notes = clear_active_mixed_referential_reason_notes(next_notes)
        next_notes = apply_control_governance_notes(next_notes, next_revision.attempt_history)

        return replace(
            session_state_card,
            revision_state=next_revision,
            approval_state=next_approval,
            conversation_context=next_conversation,
            notes=next_notes,
        )

    def _update_recent_approval_revision_history(
        self,
        notes: dict[str, object],
        *,
        approval_state: DesignerApprovalFlowState,
        clarified_interpretation: str | None,
        correction_notes: tuple[str, ...],
        governance_snapshot: dict[str, object],
        next_revision_index: int,
    ) -> dict[str, object]:
        cleaned = {
            key: value
            for key, value in notes.items()
            if key not in {
                "approval_revision_recent_history_count",
                "approval_revision_recent_history_summary",
                "approval_revision_recent_history_reopened_status",
                "approval_revision_recent_history_reopened_summary",
                "approval_revision_recent_history_reopened_applied",
            }
        }
        raw_history = cleaned.get("approval_revision_recent_history", ())
        history = [dict(item) for item in raw_history if isinstance(item, dict)] if isinstance(raw_history, (list, tuple)) else []
        history_origin_status = str(cleaned.get("approval_revision_recent_history_origin_status", "")).strip()
        history_origin_summary = str(cleaned.get("approval_revision_recent_history_origin_summary", "")).strip()
        history_origin_applied = bool(cleaned.get("approval_revision_recent_history_origin_applied"))

        if approval_state.final_outcome == "revision_requested":
            cleaned = clear_recent_revision_redirect_archive_notes(cleaned)
            modes: list[str] = []
            for decision in approval_state.user_decisions:
                if decision.outcome in {"choose_interpretation", "request_revision", "narrow_scope"} and decision.outcome not in modes:
                    modes.append(decision.outcome)
            entry = {
                "revision_index": next_revision_index,
                "approval_outcome": approval_state.final_outcome,
                "continuation_modes": modes,
                "selected_interpretation": clarified_interpretation or "",
                "correction_notes": list(correction_notes),
                "governance_pressure_band": str(governance_snapshot.get("pressure_band", "")).strip(),
                "governance_pressure_score": int(governance_snapshot.get("pressure_score", 0) or 0),
                "governance_guidance_active": bool(governance_snapshot.get("message")),
                "summary": approval_state.explanation.strip() or "Revision was requested before commit.",
            }
            history.append(entry)
            history = history[-_RECENT_APPROVAL_REVISION_HISTORY_LIMIT:]

        cleaned["approval_revision_recent_history"] = history
        cleaned["approval_revision_recent_history_count"] = len(history)
        if history:
            cleaned["approval_revision_recent_history_age"] = 0
            latest = history[-1]
            modes = ", ".join(str(item).replace("_", " ") for item in latest.get("continuation_modes", []) if str(item).strip())
            summary = f"Recent approval/revision continuity includes {len(history)} step(s). Latest continuation mode: {modes or 'revision requested'}."
            if latest.get("selected_interpretation"):
                summary = f"{summary} Latest clarified interpretation remains: {latest.get('selected_interpretation')}."
            cleaned["approval_revision_recent_history_summary"] = summary
            if history_origin_status == "reopened_from_redirect_archive":
                cleaned["approval_revision_recent_history_origin_status"] = history_origin_status
                cleaned["approval_revision_recent_history_origin_summary"] = history_origin_summary or (
                    "A previously redirected revision thread remains active continuity because the user explicitly reopened it."
                )
                cleaned["approval_revision_recent_history_origin_applied"] = history_origin_applied or True
            else:
                cleaned.pop("approval_revision_recent_history_origin_status", None)
                cleaned.pop("approval_revision_recent_history_origin_summary", None)
                cleaned.pop("approval_revision_recent_history_origin_applied", None)
        else:
            cleaned.pop("approval_revision_recent_history_summary", None)
            cleaned.pop("approval_revision_recent_history_age", None)
            cleaned.pop("approval_revision_recent_history_origin_status", None)
            cleaned.pop("approval_revision_recent_history_origin_summary", None)
            cleaned.pop("approval_revision_recent_history_origin_applied", None)
        return cleaned

    def _mixed_revision_reason_code_from_approval_state(
        self,
        approval_state: DesignerApprovalFlowState,
    ) -> str | None:
        prioritized_decision_ids = [
            decision.decision_point_id
            for decision in approval_state.user_decisions
            if decision.outcome in {"request_revision", "narrow_scope", "choose_interpretation"}
        ]
        reason_code = first_mixed_referential_reason_code_from_decision_ids(prioritized_decision_ids)
        if reason_code is not None:
            return reason_code
        return first_mixed_referential_reason_code_from_decision_ids(
            point.decision_id for point in approval_state.required_decision_points
        )
