from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE
from src.storage.models.shared_sections import CircuitModel, MetaBase, ResourcesModel, StateModel


@dataclass(frozen=True)
class CommitSnapshotMeta(MetaBase):
    commit_id: str = ""
    source_working_save_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.storage_role != COMMIT_SNAPSHOT_ROLE:
            raise ValueError("CommitSnapshotMeta.storage_role must be 'commit_snapshot'")


@dataclass(frozen=True)
class CommitValidationModel:
    validation_result: str
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommitApprovalModel:
    approval_completed: bool
    approval_status: Optional[str] = None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommitLineageModel:
    parent_commit_id: Optional[str] = None
    source_working_save_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommitSnapshotModel:
    meta: CommitSnapshotMeta
    circuit: CircuitModel
    resources: ResourcesModel
    state: StateModel
    validation: CommitValidationModel
    approval: CommitApprovalModel
    lineage: CommitLineageModel
