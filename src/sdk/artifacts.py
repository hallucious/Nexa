from __future__ import annotations

"""Official public artifact SDK boundary for Nexa.

This module is the supported import surface for role-aware `.nex` artifact
loading, validation, and lifecycle transitions. Callers that need deeper
storage internals should keep using internal modules explicitly; this package
exists to define the stable public boundary.
"""

from src.contracts.nex_contract import (
    COMMIT_SNAPSHOT_ROLE,
    WORKING_SAVE_ROLE,
    ValidationFinding,
    ValidationReport,
)
from src.storage import (
    create_commit_snapshot_from_working_save,
    create_execution_record_from_commit_snapshot,
    create_execution_record_from_snapshot,
    create_serialized_commit_snapshot_from_working_save,
    create_serialized_execution_record_from_commit_snapshot,
    create_serialized_working_save_from_commit_snapshot,
    create_working_save_from_commit_snapshot,
    load_nex,
    validate_commit_snapshot,
    validate_working_save,
)
from src.storage.models import (
    CircuitModel,
    CommitSnapshotModel,
    ExecutionRecordModel,
    LoadedNexArtifact,
    ResourcesModel,
    StateModel,
    WorkingSaveModel,
)
from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitValidationModel,
)
from src.storage.models.working_save_model import (
    DesignerDraftModel,
    RuntimeModel,
    UIModel,
    WorkingSaveMeta,
)

PUBLIC_ARTIFACT_SDK_SURFACE_VERSION = "1.0"

__all__ = [
    "PUBLIC_ARTIFACT_SDK_SURFACE_VERSION",
    "WORKING_SAVE_ROLE",
    "COMMIT_SNAPSHOT_ROLE",
    "ValidationFinding",
    "ValidationReport",
    "CircuitModel",
    "ResourcesModel",
    "StateModel",
    "WorkingSaveMeta",
    "RuntimeModel",
    "UIModel",
    "DesignerDraftModel",
    "WorkingSaveModel",
    "CommitSnapshotMeta",
    "CommitValidationModel",
    "CommitApprovalModel",
    "CommitLineageModel",
    "CommitSnapshotModel",
    "ExecutionRecordModel",
    "LoadedNexArtifact",
    "load_nex",
    "validate_working_save",
    "validate_commit_snapshot",
    "create_commit_snapshot_from_working_save",
    "create_working_save_from_commit_snapshot",
    "create_execution_record_from_snapshot",
    "create_execution_record_from_commit_snapshot",
    "create_serialized_commit_snapshot_from_working_save",
    "create_serialized_working_save_from_commit_snapshot",
    "create_serialized_execution_record_from_commit_snapshot",
]
