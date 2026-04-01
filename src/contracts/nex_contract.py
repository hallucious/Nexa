from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

StorageRole = Literal["working_save", "commit_snapshot"]
FindingCategory = Literal[
    "parse",
    "top_level_shape",
    "storage_role",
    "shared_schema",
    "role_schema",
    "structural",
    "resource_resolution",
    "state_shape",
    "runtime_section",
    "approval_section",
    "lineage_section",
    "semantic",
]
FindingSeverity = Literal["low", "medium", "high"]
ValidationResult = Literal["passed", "passed_with_findings", "failed"]
LoadStatus = Literal["loaded", "loaded_with_findings", "rejected"]

WORKING_SAVE_ROLE: StorageRole = "working_save"
COMMIT_SNAPSHOT_ROLE: StorageRole = "commit_snapshot"
ALLOWED_STORAGE_ROLES = {WORKING_SAVE_ROLE, COMMIT_SNAPSHOT_ROLE}


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    category: FindingCategory
    severity: FindingSeverity
    blocking: bool
    location: Optional[str]
    message: str
    hint: Optional[str] = None


@dataclass(frozen=True)
class ValidationReport:
    role: StorageRole
    findings: list[ValidationFinding]
    blocking_count: int
    warning_count: int
    result: ValidationResult
