from __future__ import annotations

from dataclasses import dataclass

from src.designer.approval_flow import DesignerApprovalCoordinator
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.serialization import serialize_commit_snapshot


@dataclass(frozen=True)
class DesignerCommitResult:
    approval_state: DesignerApprovalFlowState
    commit_snapshot: CommitSnapshotModel
    serialized_commit_snapshot: dict


class DesignerCommitGateway:
    """Step 3 commit gateway.

    Important boundary: this gateway commits an already materialized candidate
    Working Save. It does not apply Designer patch operations to a working save.
    That materialization step remains explicit and separate.
    """

    def __init__(self, *, coordinator: DesignerApprovalCoordinator | None = None) -> None:
        self._coordinator = coordinator or DesignerApprovalCoordinator()

    def commit_candidate(
        self,
        candidate_working_save: WorkingSaveModel,
        approval_state: DesignerApprovalFlowState,
        *,
        commit_id: str,
        parent_commit_id: str | None = None,
        approval_summary: dict | None = None,
        validation_result: str = "passed",
        validation_summary: dict | None = None,
        created_at: str | None = None,
    ) -> DesignerCommitResult:
        if not approval_state.commit_eligible:
            raise ValueError("Cannot create Commit Snapshot because the designer approval state is not commit-eligible")

        commit_snapshot = create_commit_snapshot_from_working_save(
            candidate_working_save,
            commit_id=commit_id,
            parent_commit_id=parent_commit_id,
            approval_status="approved",
            approval_summary=approval_summary
            or {
                "approval_id": approval_state.approval_id,
                "preview_ref": approval_state.preview_ref,
                "decision_count": len(approval_state.user_decisions),
            },
            validation_result=validation_result,
            validation_summary=validation_summary,
            created_at=created_at,
        )
        committed_state = self._coordinator.mark_committed(approval_state)
        return DesignerCommitResult(
            approval_state=committed_state,
            commit_snapshot=commit_snapshot,
            serialized_commit_snapshot=serialize_commit_snapshot(commit_snapshot),
        )
