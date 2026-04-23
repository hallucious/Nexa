from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.designer_contract import (
    APPROVAL_FINAL_OUTCOMES,
    APPROVAL_STAGES,
    DECISION_OUTCOMES,
    PRECHECK_OVERALL_STATUSES,
)


@dataclass(frozen=True)
class ApprovalPolicy:
    policy_name: str = "manual_review"
    allow_auto_commit: bool = False

    def __post_init__(self) -> None:
        if not self.policy_name.strip():
            raise ValueError("ApprovalPolicy.policy_name must be non-empty")


@dataclass(frozen=True)
class DecisionPoint:
    decision_id: str
    label: str
    required: bool = True
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise ValueError("DecisionPoint.decision_id must be non-empty")
        if not self.label.strip():
            raise ValueError("DecisionPoint.label must be non-empty")


@dataclass(frozen=True)
class UserDecision:
    decision_point_id: str
    outcome: str
    note: str | None = None
    selected_option: str | None = None

    def __post_init__(self) -> None:
        if not self.decision_point_id.strip():
            raise ValueError("UserDecision.decision_point_id must be non-empty")
        if self.outcome not in DECISION_OUTCOMES:
            raise ValueError(f"Unsupported UserDecision.outcome: {self.outcome}")


@dataclass(frozen=True)
class DesignerApprovalFlowState:
    approval_id: str
    intent_ref: str
    patch_ref: str
    precheck_ref: str
    preview_ref: str
    current_stage: str
    approval_policy: ApprovalPolicy = field(default_factory=ApprovalPolicy)
    required_decision_points: tuple[DecisionPoint, ...] = ()
    current_decision_point_id: str | None = None
    user_decisions: tuple[UserDecision, ...] = ()
    final_outcome: str = "pending"
    explanation: str = ""
    precheck_status: str = "pass"
    blocking_finding_count: int = 0
    confirmation_finding_count: int = 0
    confirmation_resolved: bool = True
    validated_scope_ref: str | None = None
    approved_scope_ref: str | None = None
    scope_revalidated: bool = False
    destructive_edit_present: bool = False
    major_output_semantic_change: bool = False
    critical_provider_replacement: bool = False

    def __post_init__(self) -> None:
        if not self.approval_id.strip():
            raise ValueError("DesignerApprovalFlowState.approval_id must be non-empty")
        if not self.intent_ref.strip():
            raise ValueError("DesignerApprovalFlowState.intent_ref must be non-empty")
        if not self.patch_ref.strip():
            raise ValueError("DesignerApprovalFlowState.patch_ref must be non-empty")
        if not self.precheck_ref.strip():
            raise ValueError("DesignerApprovalFlowState.precheck_ref must be non-empty")
        if not self.preview_ref.strip():
            raise ValueError("DesignerApprovalFlowState.preview_ref must be non-empty")
        if self.current_stage not in APPROVAL_STAGES:
            raise ValueError(f"Unsupported DesignerApprovalFlowState.current_stage: {self.current_stage}")
        if self.final_outcome not in APPROVAL_FINAL_OUTCOMES:
            raise ValueError(f"Unsupported DesignerApprovalFlowState.final_outcome: {self.final_outcome}")
        if self.precheck_status not in PRECHECK_OVERALL_STATUSES:
            raise ValueError(f"Unsupported DesignerApprovalFlowState.precheck_status: {self.precheck_status}")
        if min(self.blocking_finding_count, self.confirmation_finding_count) < 0:
            raise ValueError("DesignerApprovalFlowState finding counts must be non-negative")
        point_ids = [point.decision_id for point in self.required_decision_points]
        if len(point_ids) != len(set(point_ids)):
            raise ValueError("DesignerApprovalFlowState.required_decision_points must be unique")
        declared_ids = set(point_ids)
        decision_ids = [decision.decision_point_id for decision in self.user_decisions]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("DesignerApprovalFlowState.user_decisions must be unique per decision point")
        unknown_decisions = set(decision_ids) - declared_ids
        if unknown_decisions:
            raise ValueError(
                f"DesignerApprovalFlowState.user_decisions reference unknown decision points: {sorted(unknown_decisions)}"
            )
        if self.current_decision_point_id is not None and self.current_decision_point_id not in declared_ids:
            raise ValueError("DesignerApprovalFlowState.current_decision_point_id must reference a declared decision point")
        if self.final_outcome == "approved_for_commit" and not self.commit_eligible:
            raise ValueError("DesignerApprovalFlowState may not mark approved_for_commit when commit_eligible is false")

    @property
    def unanswered_required_decision_points(self) -> tuple[DecisionPoint, ...]:
        answered = {decision.decision_point_id for decision in self.user_decisions}
        return tuple(point for point in self.required_decision_points if point.required and point.decision_id not in answered)

    @property
    def scope_mismatch(self) -> bool:
        if self.validated_scope_ref is None and self.approved_scope_ref is None:
            return False
        return self.validated_scope_ref != self.approved_scope_ref

    @property
    def commit_eligible(self) -> bool:
        if self.precheck_status == "blocked":
            return False
        if self.blocking_finding_count > 0:
            return False
        if self.confirmation_finding_count > 0 and not self.confirmation_resolved:
            return False
        if self.unanswered_required_decision_points:
            return False
        if self.final_outcome != "approved_for_commit":
            return False
        if self.scope_mismatch and not self.scope_revalidated:
            return False
        return True

    @property
    def auto_commit_allowed(self) -> bool:
        if not self.approval_policy.allow_auto_commit:
            return False
        if self.blocking_finding_count > 0 or self.precheck_status == "blocked":
            return False
        if self.unanswered_required_decision_points:
            return False
        if self.confirmation_finding_count > 0:
            return False
        if self.destructive_edit_present:
            return False
        if self.major_output_semantic_change:
            return False
        if self.critical_provider_replacement:
            return False
        if self.scope_mismatch:
            return False
        return True
