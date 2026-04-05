from __future__ import annotations

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
