from __future__ import annotations

from dataclasses import replace
import hashlib

from src.designer.models.designer_approval_flow import (
    ApprovalPolicy,
    DecisionPoint,
    DesignerApprovalFlowState,
    UserDecision,
)
from src.designer.proposal_flow import DesignerProposalBundle

_GENERIC_SCOPE_CONFIRMATION_ID = "confirm_scope_alignment"
_GENERIC_RISK_CONFIRMATION_ID = "confirm_risk_acceptance"
_GENERIC_DESTRUCTIVE_CONFIRMATION_ID = "confirm_destructive_change"


class DesignerApprovalCoordinator:
    """Step 3 approval-boundary coordinator.

    This class translates a non-committing proposal bundle into an explicit
    approval state and updates that state based on user decisions. It does not
    mutate savefiles or create commit snapshots by itself.
    """

    def create_state(
        self,
        bundle: DesignerProposalBundle,
        *,
        approval_policy: ApprovalPolicy | None = None,
    ) -> DesignerApprovalFlowState:
        decision_points = self._decision_points_for_bundle(bundle)
        blocked = bundle.precheck.overall_status == "blocked"
        return DesignerApprovalFlowState(
            approval_id=self._stable_id("approval", bundle.preview.preview_id),
            intent_ref=bundle.intent.intent_id,
            patch_ref=bundle.patch.patch_id,
            precheck_ref=bundle.precheck.precheck_id,
            preview_ref=bundle.preview.preview_id,
            current_stage="rejected" if blocked else "awaiting_decision",
            approval_policy=approval_policy or ApprovalPolicy(),
            required_decision_points=decision_points,
            current_decision_point_id=decision_points[0].decision_id if decision_points and not blocked else None,
            user_decisions=(),
            final_outcome="rejected" if blocked else "pending",
            explanation=bundle.preview.explanation or bundle.precheck.explanation,
            precheck_status=bundle.precheck.overall_status,
            blocking_finding_count=len(bundle.precheck.blocking_findings),
            confirmation_finding_count=len(bundle.precheck.confirmation_findings),
            confirmation_resolved=not decision_points,
            validated_scope_ref=self._scope_ref_from_bundle(bundle),
            approved_scope_ref=None,
            scope_revalidated=False,
            destructive_edit_present=bundle.patch.change_scope.touch_mode == "destructive_edit",
            major_output_semantic_change=bool(bundle.patch.output_effects.modified_outputs or bundle.patch.output_effects.removed_outputs),
            critical_provider_replacement=any(op.op_type == "set_node_provider" for op in bundle.patch.operations),
        )

    def resolve(
        self,
        state: DesignerApprovalFlowState,
        decisions: tuple[UserDecision, ...] | list[UserDecision],
        *,
        approved_scope_ref: str | None = None,
        scope_revalidated: bool = False,
    ) -> DesignerApprovalFlowState:
        merged_decisions = self._merge_decisions(state.user_decisions, tuple(decisions))
        decision_outcomes = {decision.outcome for decision in merged_decisions}
        confirmation_resolved = not self._unanswered_required_points(state.required_decision_points, merged_decisions)

        if state.precheck_status == "blocked" or state.blocking_finding_count > 0:
            next_outcome = "rejected"
            next_stage = "rejected"
        elif "abort" in decision_outcomes:
            next_outcome = "aborted"
            next_stage = "aborted"
        elif "reject" in decision_outcomes:
            next_outcome = "rejected"
            next_stage = "rejected"
        elif {"request_revision", "narrow_scope", "choose_interpretation"} & decision_outcomes:
            next_outcome = "revision_requested"
            next_stage = "awaiting_decision"
        else:
            next_outcome = "approved_for_commit"
            next_stage = "ready_to_commit"

        resolved_scope_ref = approved_scope_ref
        if next_outcome == "approved_for_commit" and resolved_scope_ref is None:
            resolved_scope_ref = state.validated_scope_ref

        current_point = None
        unanswered = self._unanswered_required_points(state.required_decision_points, merged_decisions)
        if unanswered and next_outcome == "pending":
            current_point = unanswered[0].decision_id

        return DesignerApprovalFlowState(
            approval_id=state.approval_id,
            intent_ref=state.intent_ref,
            patch_ref=state.patch_ref,
            precheck_ref=state.precheck_ref,
            preview_ref=state.preview_ref,
            current_stage=next_stage,
            approval_policy=state.approval_policy,
            required_decision_points=state.required_decision_points,
            current_decision_point_id=current_point,
            user_decisions=merged_decisions,
            final_outcome=next_outcome,
            explanation=state.explanation,
            precheck_status=state.precheck_status,
            blocking_finding_count=state.blocking_finding_count,
            confirmation_finding_count=state.confirmation_finding_count,
            confirmation_resolved=confirmation_resolved,
            validated_scope_ref=state.validated_scope_ref,
            approved_scope_ref=resolved_scope_ref,
            scope_revalidated=scope_revalidated,
            destructive_edit_present=state.destructive_edit_present,
            major_output_semantic_change=state.major_output_semantic_change,
            critical_provider_replacement=state.critical_provider_replacement,
        )

    def mark_committed(self, state: DesignerApprovalFlowState) -> DesignerApprovalFlowState:
        if not state.commit_eligible:
            raise ValueError("Cannot mark approval flow as committed when commit_eligible is false")
        return replace(state, current_stage="committed")

    def _decision_points_for_bundle(self, bundle: DesignerProposalBundle) -> tuple[DecisionPoint, ...]:
        decision_points: list[DecisionPoint] = []
        seen: set[str] = set()

        for finding in bundle.precheck.confirmation_findings:
            decision_id = self._normalize_decision_id(finding.issue_code)
            if decision_id in seen:
                continue
            seen.add(decision_id)
            decision_points.append(
                DecisionPoint(
                    decision_id=decision_id,
                    label=finding.message,
                    reason=finding.fix_hint or finding.location,
                )
            )

        if bundle.intent.requires_user_confirmation and _GENERIC_SCOPE_CONFIRMATION_ID not in seen:
            seen.add(_GENERIC_SCOPE_CONFIRMATION_ID)
            decision_points.append(
                DecisionPoint(
                    decision_id=_GENERIC_SCOPE_CONFIRMATION_ID,
                    label="Confirm the bounded scope of this designer proposal.",
                    reason="The request or proposal contains ambiguity or a high-severity risk.",
                )
            )

        if bundle.patch.risk_report.requires_confirmation and _GENERIC_RISK_CONFIRMATION_ID not in seen:
            seen.add(_GENERIC_RISK_CONFIRMATION_ID)
            decision_points.append(
                DecisionPoint(
                    decision_id=_GENERIC_RISK_CONFIRMATION_ID,
                    label="Acknowledge the proposal risk report before commit.",
                    reason="Patch risk report requires explicit confirmation.",
                )
            )

        if bundle.patch.change_scope.touch_mode == "destructive_edit" and _GENERIC_DESTRUCTIVE_CONFIRMATION_ID not in seen:
            seen.add(_GENERIC_DESTRUCTIVE_CONFIRMATION_ID)
            decision_points.append(
                DecisionPoint(
                    decision_id=_GENERIC_DESTRUCTIVE_CONFIRMATION_ID,
                    label="Confirm the destructive structural change.",
                    reason="Destructive edits must never be silently committed.",
                )
            )

        return tuple(decision_points)

    def _scope_ref_from_bundle(self, bundle: DesignerProposalBundle) -> str:
        parts = [
            bundle.patch.patch_id,
            bundle.patch.change_scope.scope_level,
            bundle.patch.change_scope.touch_mode,
            *sorted(bundle.patch.change_scope.touched_nodes),
            *sorted(bundle.patch.change_scope.touched_edges),
            *sorted(bundle.patch.change_scope.touched_outputs),
        ]
        return self._stable_id("scope", "|".join(parts))

    def _normalize_decision_id(self, issue_code: str) -> str:
        normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in issue_code).strip("_")
        return normalized or self._stable_id("decision", issue_code)

    def _merge_decisions(
        self,
        existing: tuple[UserDecision, ...],
        new_decisions: tuple[UserDecision, ...],
    ) -> tuple[UserDecision, ...]:
        merged: dict[str, UserDecision] = {decision.decision_point_id: decision for decision in existing}
        for decision in new_decisions:
            merged[decision.decision_point_id] = decision
        return tuple(merged[key] for key in sorted(merged))

    def _unanswered_required_points(
        self,
        points: tuple[DecisionPoint, ...],
        decisions: tuple[UserDecision, ...],
    ) -> tuple[DecisionPoint, ...]:
        answered = {decision.decision_point_id for decision in decisions}
        return tuple(point for point in points if point.required and point.decision_id not in answered)

    def _stable_id(self, prefix: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}-{digest}"
