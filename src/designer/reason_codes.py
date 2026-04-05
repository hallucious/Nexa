from __future__ import annotations

from typing import Any, Mapping

MIXED_REFERENTIAL_ACTION = "MIXED_REFERENTIAL_ACTION"
MIXED_REFERENTIAL_PROVIDER_CHANGE = "MIXED_REFERENTIAL_PROVIDER_CHANGE"
MIXED_REFERENTIAL_PLUGIN_ATTACH = "MIXED_REFERENTIAL_PLUGIN_ATTACH"
MIXED_REFERENTIAL_RENAME = "MIXED_REFERENTIAL_RENAME"
MIXED_REFERENTIAL_INSERT = "MIXED_REFERENTIAL_INSERT"
MIXED_REFERENTIAL_DELETE = "MIXED_REFERENTIAL_DELETE"
MIXED_REFERENTIAL_REVIEW_GATE = "MIXED_REFERENTIAL_REVIEW_GATE"
MIXED_REFERENTIAL_OPTIMIZE_REPAIR = "MIXED_REFERENTIAL_OPTIMIZE_REPAIR"

DESIGNER_MIXED_REFERENTIAL_REASON_CODES = frozenset(
    {
        MIXED_REFERENTIAL_ACTION,
        MIXED_REFERENTIAL_PROVIDER_CHANGE,
        MIXED_REFERENTIAL_PLUGIN_ATTACH,
        MIXED_REFERENTIAL_RENAME,
        MIXED_REFERENTIAL_INSERT,
        MIXED_REFERENTIAL_DELETE,
        MIXED_REFERENTIAL_REVIEW_GATE,
        MIXED_REFERENTIAL_OPTIMIZE_REPAIR,
    }
)

FLAG_TYPE_BY_REASON_CODE = {
    MIXED_REFERENTIAL_ACTION: "mixed_referential_action",
    MIXED_REFERENTIAL_PROVIDER_CHANGE: "mixed_referential_provider_change",
    MIXED_REFERENTIAL_PLUGIN_ATTACH: "mixed_referential_plugin_attach",
    MIXED_REFERENTIAL_RENAME: "mixed_referential_rename",
    MIXED_REFERENTIAL_INSERT: "mixed_referential_insert",
    MIXED_REFERENTIAL_DELETE: "mixed_referential_delete",
    MIXED_REFERENTIAL_REVIEW_GATE: "mixed_referential_review_gate",
    MIXED_REFERENTIAL_OPTIMIZE_REPAIR: "mixed_referential_optimize_repair",
}
REASON_CODE_BY_FLAG_TYPE = {value: key for key, value in FLAG_TYPE_BY_REASON_CODE.items()}

CONFIRMATION_MESSAGE_BY_REASON_CODE = {
    MIXED_REFERENTIAL_PROVIDER_CHANGE: "The request mixes rollback language with a provider change and must be confirmed (reason_code=MIXED_REFERENTIAL_PROVIDER_CHANGE).",
    MIXED_REFERENTIAL_PLUGIN_ATTACH: "The request mixes rollback language with plugin attachment and must be confirmed (reason_code=MIXED_REFERENTIAL_PLUGIN_ATTACH).",
    MIXED_REFERENTIAL_RENAME: "The request mixes rollback language with a rename operation and must be confirmed (reason_code=MIXED_REFERENTIAL_RENAME).",
    MIXED_REFERENTIAL_INSERT: "The request mixes rollback language with an insert operation and must be confirmed (reason_code=MIXED_REFERENTIAL_INSERT).",
    MIXED_REFERENTIAL_DELETE: "The request mixes rollback language with a delete/remove action and must be confirmed (reason_code=MIXED_REFERENTIAL_DELETE).",
    MIXED_REFERENTIAL_REVIEW_GATE: "The request mixes rollback language with review-gate changes and must be confirmed (reason_code=MIXED_REFERENTIAL_REVIEW_GATE).",
    MIXED_REFERENTIAL_OPTIMIZE_REPAIR: "The request mixes rollback language with optimize/repair intent and must be confirmed (reason_code=MIXED_REFERENTIAL_OPTIMIZE_REPAIR).",
    MIXED_REFERENTIAL_ACTION: "The request mixes rollback language with another structural action and must be confirmed (reason_code=MIXED_REFERENTIAL_ACTION).",
}


def reason_code_for_mixed_referential_request(request_text: str) -> str:
    text = request_text.casefold()
    if "replace provider" in text or "switch provider" in text or "change provider" in text:
        return MIXED_REFERENTIAL_PROVIDER_CHANGE
    if "attach plugin" in text or "add plugin" in text or "use plugin" in text:
        return MIXED_REFERENTIAL_PLUGIN_ATTACH
    if "rename" in text:
        return MIXED_REFERENTIAL_RENAME
    if "insert" in text:
        return MIXED_REFERENTIAL_INSERT
    if "remove" in text or "delete" in text:
        return MIXED_REFERENTIAL_DELETE
    if "add review" in text or "remove review" in text:
        return MIXED_REFERENTIAL_REVIEW_GATE
    if "optimize" in text or "optimise" in text or "repair" in text:
        return MIXED_REFERENTIAL_OPTIMIZE_REPAIR
    return MIXED_REFERENTIAL_ACTION


def flag_type_for_reason_code(reason_code: str) -> str:
    return FLAG_TYPE_BY_REASON_CODE.get(reason_code, FLAG_TYPE_BY_REASON_CODE[MIXED_REFERENTIAL_ACTION])


def reason_code_for_flag_type(flag_type: str) -> str:
    return REASON_CODE_BY_FLAG_TYPE.get(flag_type, MIXED_REFERENTIAL_ACTION)


def is_mixed_referential_flag_type(flag_type: str) -> bool:
    return flag_type in REASON_CODE_BY_FLAG_TYPE


def confirmation_message_for_reason_code(reason_code: str) -> str:
    return CONFIRMATION_MESSAGE_BY_REASON_CODE.get(reason_code, CONFIRMATION_MESSAGE_BY_REASON_CODE[MIXED_REFERENTIAL_ACTION])



def is_designer_mixed_referential_reason_code(reason_code: str) -> bool:
    return reason_code in DESIGNER_MIXED_REFERENTIAL_REASON_CODES


def first_mixed_referential_reason_from_findings(findings) -> tuple[str | None, str | None]:
    for finding in findings:
        issue_code = getattr(finding, "issue_code", "")
        if issue_code in DESIGNER_MIXED_REFERENTIAL_REASON_CODES:
            return issue_code, getattr(finding, "message", "") or confirmation_message_for_reason_code(issue_code)
    return None, None


def first_mixed_referential_reason_code_from_decision_ids(decision_ids) -> str | None:
    for decision_id in decision_ids:
        if is_mixed_referential_flag_type(decision_id):
            return reason_code_for_flag_type(decision_id)
    return None


_ACTIVE_MIXED_REFERENTIAL_NOTE_KEYS = frozenset(
    {
        "active_mixed_referential_reason_code",
        "active_mixed_referential_reason_stage",
        "active_mixed_referential_reason_status",
        "active_mixed_referential_reason_source_note_key",
        "active_mixed_referential_reason_retention_state",
    }
)
_MIXED_REFERENTIAL_REASON_HISTORY_KEY = "mixed_referential_reason_history"
_MIXED_REFERENTIAL_REASON_HISTORY_RETENTION_LIMIT = 5


def activate_mixed_referential_reason_notes(
    notes: Mapping[str, Any],
    *,
    reason_code: str,
    stage: str,
    status: str,
    source_note_key: str,
) -> dict[str, Any]:
    next_notes = dict(notes)
    if not is_designer_mixed_referential_reason_code(reason_code):
        return clear_active_mixed_referential_reason_notes(next_notes)
    next_notes.update(
        {
            "active_mixed_referential_reason_code": reason_code,
            "active_mixed_referential_reason_stage": stage,
            "active_mixed_referential_reason_status": status,
            "active_mixed_referential_reason_source_note_key": source_note_key,
            "active_mixed_referential_reason_retention_state": "active",
        }
    )
    return next_notes


def clear_active_mixed_referential_reason_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    next_notes = dict(notes)
    for key in _ACTIVE_MIXED_REFERENTIAL_NOTE_KEYS:
        next_notes.pop(key, None)
    return next_notes


def clear_transient_mixed_referential_reason_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    next_notes = clear_active_mixed_referential_reason_notes(notes)
    if is_designer_mixed_referential_reason_code(str(next_notes.get("last_attempt_reason_code", ""))):
        next_notes.pop("last_attempt_reason_code", None)
        next_notes.pop("last_attempt_stage", None)
        next_notes.pop("last_attempt_outcome", None)
    if is_designer_mixed_referential_reason_code(str(next_notes.get("last_revision_reason_code", ""))):
        next_notes.pop("last_revision_reason_code", None)
    return next_notes


def archive_latest_mixed_referential_reason_notes(
    notes: Mapping[str, Any],
    *,
    retention_state: str,
    commit_id: str | None = None,
    request_text: str | None = None,
) -> dict[str, Any]:
    next_notes = dict(notes)
    latest = _latest_mixed_referential_reason_note_context(next_notes)
    if latest is None:
        return clear_transient_mixed_referential_reason_notes(next_notes)

    entry = {
        "reason_code": latest["reason_code"],
        "stage": latest["stage"],
        "status": latest["status"],
        "retention_state": retention_state,
    }
    if commit_id is not None:
        entry["commit_id"] = commit_id
    if request_text is not None and request_text.strip():
        entry["request_text"] = request_text.strip()

    next_notes[_MIXED_REFERENTIAL_REASON_HISTORY_KEY] = _rotate_mixed_referential_reason_history(
        next_notes.get(_MIXED_REFERENTIAL_REASON_HISTORY_KEY),
        entry,
    )
    next_notes["last_mixed_referential_reason_code"] = latest["reason_code"]
    next_notes["last_mixed_referential_reason_stage"] = latest["stage"]
    next_notes["last_mixed_referential_reason_status"] = latest["status"]
    next_notes["last_mixed_referential_reason_retention_state"] = retention_state
    return clear_transient_mixed_referential_reason_notes(next_notes)


def _latest_mixed_referential_reason_note_context(notes: Mapping[str, Any]) -> dict[str, str] | None:
    active_reason_code = str(notes.get("active_mixed_referential_reason_code", ""))
    if is_designer_mixed_referential_reason_code(active_reason_code):
        return {
            "reason_code": active_reason_code,
            "stage": str(notes.get("active_mixed_referential_reason_stage", "unknown")),
            "status": str(notes.get("active_mixed_referential_reason_status", "unknown")),
        }

    revision_reason_code = str(notes.get("last_revision_reason_code", ""))
    if is_designer_mixed_referential_reason_code(revision_reason_code):
        return {
            "reason_code": revision_reason_code,
            "stage": "approval_revision",
            "status": "revision_requested",
        }

    attempt_reason_code = str(notes.get("last_attempt_reason_code", ""))
    if is_designer_mixed_referential_reason_code(attempt_reason_code):
        return {
            "reason_code": attempt_reason_code,
            "stage": str(notes.get("last_attempt_stage", "unknown")),
            "status": str(notes.get("last_attempt_outcome", "unknown")),
        }
    return None


def _rotate_mixed_referential_reason_history(existing_history: Any, latest_entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    if isinstance(existing_history, list):
        history = [dict(item) for item in existing_history if isinstance(item, Mapping)]
    deduped = [
        dict(item)
        for item in history
        if not (
            str(item.get("reason_code", "")) == str(latest_entry.get("reason_code", ""))
            and str(item.get("stage", "")) == str(latest_entry.get("stage", ""))
            and str(item.get("status", "")) == str(latest_entry.get("status", ""))
            and str(item.get("retention_state", "")) == str(latest_entry.get("retention_state", ""))
            and str(item.get("commit_id", "")) == str(latest_entry.get("commit_id", ""))
        )
    ]
    rotated = [dict(latest_entry), *deduped]
    return rotated[:_MIXED_REFERENTIAL_REASON_HISTORY_RETENTION_LIMIT]
