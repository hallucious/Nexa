from __future__ import annotations

from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE

COMMIT_SNAPSHOT_REQUIRED_SECTIONS = (
    "meta",
    "circuit",
    "resources",
    "state",
    "validation",
    "approval",
    "lineage",
)
COMMIT_SNAPSHOT_FORBIDDEN_SECTIONS = ("runtime", "ui", "designer")
COMMIT_SNAPSHOT_ALLOWED_VALIDATION_RESULTS = {
    "passed",
    "passed_with_warnings",
}
COMMIT_SNAPSHOT_IDENTITY_FIELD = "commit_id"
COMMIT_SNAPSHOT_STORAGE_ROLE = COMMIT_SNAPSHOT_ROLE
