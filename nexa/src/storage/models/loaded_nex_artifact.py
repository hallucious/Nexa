from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.contracts.nex_contract import LoadStatus, StorageRole, ValidationFinding
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel


@dataclass(frozen=True)
class LoadedNexArtifact:
    storage_role: StorageRole
    raw_data: dict[str, Any]
    parsed_model: Optional[WorkingSaveModel | CommitSnapshotModel]
    findings: list[ValidationFinding]
    load_status: LoadStatus
    source_path: Optional[str] = None
    migration_notes: list[str] | None = None
