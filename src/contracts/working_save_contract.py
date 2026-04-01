from __future__ import annotations

from src.contracts.nex_contract import WORKING_SAVE_ROLE

WORKING_SAVE_REQUIRED_SECTIONS = (
    "meta",
    "circuit",
    "resources",
    "state",
    "runtime",
    "ui",
)
WORKING_SAVE_OPTIONAL_SECTIONS = ("designer",)
WORKING_SAVE_ALLOWED_RUNTIME_STATUSES = {
    "draft",
    "validation_failed",
    "ready_for_review",
    "validated",
    "execution_failed",
    "executed",
}
WORKING_SAVE_IDENTITY_FIELD = "working_save_id"
WORKING_SAVE_STORAGE_ROLE = WORKING_SAVE_ROLE
