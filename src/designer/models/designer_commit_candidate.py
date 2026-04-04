from __future__ import annotations

from dataclasses import dataclass

from src.contracts.designer_contract import APPROVAL_FINAL_OUTCOMES, APPROVAL_STAGES


@dataclass(frozen=True)
class DesignerCommitCandidateState:
    approval_id: str
    intent_ref: str
    patch_ref: str
    precheck_ref: str
    preview_ref: str
    approval_stage: str
    approval_outcome: str
    ready_for_commit: bool = False
    source_working_save_ref: str | None = None
    candidate_working_save_ref: str | None = None
    validated_scope_ref: str | None = None
    approved_scope_ref: str | None = None
    applied_operation_ids: tuple[str, ...] = ()
    created_node_ids: tuple[str, ...] = ()
    candidate_origin: str = "designer_patch_application"

    def __post_init__(self) -> None:
        if not self.approval_id.strip():
            raise ValueError("DesignerCommitCandidateState.approval_id must be non-empty")
        for field_name in ("intent_ref", "patch_ref", "precheck_ref", "preview_ref"):
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(f"DesignerCommitCandidateState.{field_name} must be non-empty")
        if self.approval_stage not in APPROVAL_STAGES:
            raise ValueError(f"Unsupported DesignerCommitCandidateState.approval_stage: {self.approval_stage}")
        if self.approval_outcome not in APPROVAL_FINAL_OUTCOMES:
            raise ValueError(f"Unsupported DesignerCommitCandidateState.approval_outcome: {self.approval_outcome}")
        if self.ready_for_commit and self.approval_outcome != "approved_for_commit":
            raise ValueError("DesignerCommitCandidateState may only be ready_for_commit when approval_outcome is approved_for_commit")
        if not self.candidate_origin.strip():
            raise ValueError("DesignerCommitCandidateState.candidate_origin must be non-empty")
