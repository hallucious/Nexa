from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence
from uuid import uuid4

from src.server.observability_payload_guard import REDACTED_VALUE, sanitize_observability_payload

GDPR_DELETION_STATUS_PLANNED = "planned"
GDPR_DELETION_STATUS_COMPLETED = "completed"
GDPR_DELETION_STATUS_FAILED = "failed"

GDPR_ACTION_DELETE_IDENTITY = "delete_identity"
GDPR_ACTION_DELETE_MUTABLE_ROWS = "delete_mutable_rows"
GDPR_ACTION_DELETE_OBJECT = "delete_object"
GDPR_ACTION_PRESERVE_IMMUTABLE_HISTORY = "preserve_immutable_history"
GDPR_ACTION_WRITE_AUDIT = "write_audit"

CATEGORY_A_APPEND_ONLY = "A_append_only"
CATEGORY_B_MUTABLE = "B_mutable"
CATEGORY_C_TTL_DELETABLE = "C_ttl_deletable"
CATEGORY_D_PERMANENT_AUDIT = "D_permanent_audit"

IMMUTABLE_HISTORY_TABLES = frozenset(
    {
        "execution_record",
        "file_upload_events",
        "run_action_log",
        "execution_record_archive_index",
        "execution_retention_audit",
        "admin_action_audit",
        "user_deletion_audit",
        "artifact_index",
        "trace_event_index",
        "artifact_lineage_links",
    }
)

PERMANENT_AUDIT_TABLES = frozenset(
    {
        "admin_action_audit",
        "user_deletion_audit",
        "execution_retention_audit",
        "file_upload_events",
    }
)

DEFAULT_MUTABLE_USER_TABLES = (
    "workspace_memberships",
    "user_subscriptions",
    "user_preferences",
    "push_notification_tokens",
    "file_uploads",
)

DEFAULT_TTL_USER_TABLES = (
    "run_submissions",
    "run_submission_dedupe",
    "quota_usage",
)

_GDPR_SAFE_ACTIONS = frozenset(
    {
        GDPR_ACTION_DELETE_IDENTITY,
        GDPR_ACTION_DELETE_MUTABLE_ROWS,
        GDPR_ACTION_DELETE_OBJECT,
        GDPR_ACTION_PRESERVE_IMMUTABLE_HISTORY,
        GDPR_ACTION_WRITE_AUDIT,
    }
)


class GdprDeletionPolicyError(ValueError):
    """Raised when a deletion plan would violate SaaS governance rules."""


@dataclass(frozen=True)
class GdprDeletionRequest:
    """Input for a GDPR/user deletion plan.

    ``user_ref`` must be an opaque identifier, not raw email, display name, IP,
    Clerk subject, or provider customer id. Optional raw identity hints are
    accepted only so callers can prove they are not copied into audit output.
    """

    user_ref: str
    requested_by_ref: str
    deletion_request_id: str | None = None
    object_storage_refs: tuple[str, ...] = ()
    mutable_table_names: tuple[str, ...] = DEFAULT_MUTABLE_USER_TABLES
    ttl_table_names: tuple[str, ...] = DEFAULT_TTL_USER_TABLES
    raw_identity_hint: str | None = None
    reason: str = "user_requested_deletion"

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_ref", _require_opaque_ref(self.user_ref, field_name="user_ref"))
        object.__setattr__(
            self,
            "requested_by_ref",
            _require_opaque_ref(self.requested_by_ref, field_name="requested_by_ref"),
        )
        request_id = str(self.deletion_request_id or "").strip() or f"gdpr_{uuid4().hex}"
        object.__setattr__(self, "deletion_request_id", request_id)
        object.__setattr__(self, "object_storage_refs", _normalize_text_tuple(self.object_storage_refs))
        object.__setattr__(self, "mutable_table_names", _normalize_table_tuple(self.mutable_table_names))
        object.__setattr__(self, "ttl_table_names", _normalize_table_tuple(self.ttl_table_names))
        object.__setattr__(self, "reason", str(self.reason or "user_requested_deletion").strip() or "user_requested_deletion")


@dataclass(frozen=True)
class GdprDeletionAction:
    action_type: str
    target: str
    category: str
    detail: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action_type not in _GDPR_SAFE_ACTIONS:
            raise GdprDeletionPolicyError(f"Unsupported GDPR deletion action: {self.action_type}")
        if not str(self.target or "").strip():
            raise GdprDeletionPolicyError("GDPR deletion action target must be non-empty")

    def as_payload(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "category": self.category,
            "detail": sanitize_observability_payload(dict(self.detail)),
        }


@dataclass(frozen=True)
class GdprDeletionAuditRecord:
    deletion_request_id: str
    user_ref: str
    requested_by_ref: str
    status: str
    mutable_tables_cleared: tuple[str, ...]
    ttl_tables_reviewed: tuple[str, ...]
    object_storage_refs_deleted: tuple[str, ...]
    immutable_tables_preserved: tuple[str, ...]
    permanent_audit_tables_preserved: tuple[str, ...]
    reason: str
    error_code: str | None = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "deletion_request_id": self.deletion_request_id,
            "user_ref": self.user_ref,
            "requested_by_ref": self.requested_by_ref,
            "status": self.status,
            "mutable_tables_cleared": list(self.mutable_tables_cleared),
            "ttl_tables_reviewed": list(self.ttl_tables_reviewed),
            "object_storage_refs_deleted": list(self.object_storage_refs_deleted),
            "immutable_tables_preserved": list(self.immutable_tables_preserved),
            "permanent_audit_tables_preserved": list(self.permanent_audit_tables_preserved),
            "reason": self.reason,
        }
        if self.error_code:
            payload["error_code"] = self.error_code
        return sanitize_observability_payload(payload)


@dataclass(frozen=True)
class GdprDeletionPlan:
    request: GdprDeletionRequest
    actions: tuple[GdprDeletionAction, ...]
    audit_record: GdprDeletionAuditRecord

    def as_payload(self) -> dict[str, Any]:
        return {
            "deletion_request_id": self.request.deletion_request_id,
            "status": GDPR_DELETION_STATUS_PLANNED,
            "actions": [action.as_payload() for action in self.actions],
            "audit_record": self.audit_record.as_payload(),
        }


@dataclass(frozen=True)
class GdprDeletionExecutionResult:
    deletion_request_id: str
    status: str
    completed_actions: tuple[dict[str, Any], ...]
    audit_record: GdprDeletionAuditRecord
    error_code: str | None = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "deletion_request_id": self.deletion_request_id,
            "status": self.status,
            "completed_actions": list(self.completed_actions),
            "audit_record": self.audit_record.as_payload(),
        }
        if self.error_code:
            payload["error_code"] = self.error_code
        return sanitize_observability_payload(payload)


MutableRowDeleter = Callable[[str, str], int]
TtlRowCleaner = Callable[[str, str], int]
ObjectStorageDeleter = Callable[[str], bool]
IdentityDeleter = Callable[[str], bool]
AuditWriter = Callable[[Mapping[str, Any]], Any]


def table_gdpr_category(table_name: str) -> str:
    normalized = _normalize_table_name(table_name)
    if normalized in PERMANENT_AUDIT_TABLES:
        return CATEGORY_D_PERMANENT_AUDIT
    if normalized in IMMUTABLE_HISTORY_TABLES:
        return CATEGORY_A_APPEND_ONLY
    if normalized in DEFAULT_TTL_USER_TABLES:
        return CATEGORY_C_TTL_DELETABLE
    return CATEGORY_B_MUTABLE


def build_gdpr_deletion_plan(request: GdprDeletionRequest) -> GdprDeletionPlan:
    _assert_deletable_table_set(request.mutable_table_names, kind="mutable_table_names")
    _assert_no_permanent_or_immutable_targets(request.ttl_table_names, kind="ttl_table_names")

    actions: list[GdprDeletionAction] = [
        GdprDeletionAction(
            action_type=GDPR_ACTION_DELETE_IDENTITY,
            target="identity_authority",
            category=CATEGORY_B_MUTABLE,
            detail={"user_ref": request.user_ref},
        )
    ]
    for table_name in request.mutable_table_names:
        actions.append(
            GdprDeletionAction(
                action_type=GDPR_ACTION_DELETE_MUTABLE_ROWS,
                target=table_name,
                category=CATEGORY_B_MUTABLE,
                detail={"user_ref": request.user_ref},
            )
        )
    for object_ref in request.object_storage_refs:
        actions.append(
            GdprDeletionAction(
                action_type=GDPR_ACTION_DELETE_OBJECT,
                target=object_ref,
                category=CATEGORY_B_MUTABLE,
                detail={"object_ref": object_ref},
            )
        )
    for table_name in sorted(IMMUTABLE_HISTORY_TABLES):
        actions.append(
            GdprDeletionAction(
                action_type=GDPR_ACTION_PRESERVE_IMMUTABLE_HISTORY,
                target=table_name,
                category=table_gdpr_category(table_name),
                detail={"policy": "preserve_without_mutation"},
            )
        )
    actions.append(
        GdprDeletionAction(
            action_type=GDPR_ACTION_WRITE_AUDIT,
            target="user_deletion_audit",
            category=CATEGORY_D_PERMANENT_AUDIT,
            detail={"deletion_request_id": request.deletion_request_id},
        )
    )

    audit = GdprDeletionAuditRecord(
        deletion_request_id=str(request.deletion_request_id),
        user_ref=request.user_ref,
        requested_by_ref=request.requested_by_ref,
        status=GDPR_DELETION_STATUS_PLANNED,
        mutable_tables_cleared=request.mutable_table_names,
        ttl_tables_reviewed=request.ttl_table_names,
        object_storage_refs_deleted=request.object_storage_refs,
        immutable_tables_preserved=tuple(sorted(IMMUTABLE_HISTORY_TABLES)),
        permanent_audit_tables_preserved=tuple(sorted(PERMANENT_AUDIT_TABLES)),
        reason=request.reason,
    )
    return GdprDeletionPlan(request=request, actions=tuple(actions), audit_record=audit)


def execute_gdpr_deletion_plan(
    plan: GdprDeletionPlan,
    *,
    mutable_row_deleter: MutableRowDeleter,
    object_storage_deleter: ObjectStorageDeleter,
    audit_writer: AuditWriter,
    identity_deleter: IdentityDeleter | None = None,
    ttl_row_cleaner: TtlRowCleaner | None = None,
) -> GdprDeletionExecutionResult:
    completed: list[dict[str, Any]] = []
    error_code: str | None = None
    status = GDPR_DELETION_STATUS_COMPLETED

    try:
        for action in plan.actions:
            if action.action_type == GDPR_ACTION_DELETE_IDENTITY:
                deleted = True if identity_deleter is None else bool(identity_deleter(plan.request.user_ref))
                completed.append({**action.as_payload(), "deleted": deleted})
            elif action.action_type == GDPR_ACTION_DELETE_MUTABLE_ROWS:
                _assert_deletable_table_set((action.target,), kind="execute_target")
                deleted_count = int(mutable_row_deleter(action.target, plan.request.user_ref))
                completed.append({**action.as_payload(), "deleted_count": max(0, deleted_count)})
            elif action.action_type == GDPR_ACTION_DELETE_OBJECT:
                deleted = bool(object_storage_deleter(action.target))
                completed.append({**action.as_payload(), "deleted": deleted})
            elif action.action_type == GDPR_ACTION_PRESERVE_IMMUTABLE_HISTORY:
                if table_gdpr_category(action.target) not in {CATEGORY_A_APPEND_ONLY, CATEGORY_D_PERMANENT_AUDIT}:
                    raise GdprDeletionPolicyError(f"Preserve action target is not immutable: {action.target}")
                completed.append({**action.as_payload(), "preserved": True})
            elif action.action_type == GDPR_ACTION_WRITE_AUDIT:
                continue
        if ttl_row_cleaner is not None:
            for table_name in plan.request.ttl_table_names:
                cleaned_count = int(ttl_row_cleaner(table_name, plan.request.user_ref))
                completed.append(
                    {
                        "action_type": "cleanup_ttl_rows",
                        "target": table_name,
                        "category": CATEGORY_C_TTL_DELETABLE,
                        "cleaned_count": max(0, cleaned_count),
                    }
                )
    except Exception as exc:  # noqa: BLE001
        status = GDPR_DELETION_STATUS_FAILED
        error_code = _safe_error_code(exc)

    audit_record = GdprDeletionAuditRecord(
        deletion_request_id=plan.audit_record.deletion_request_id,
        user_ref=plan.audit_record.user_ref,
        requested_by_ref=plan.audit_record.requested_by_ref,
        status=status,
        mutable_tables_cleared=plan.audit_record.mutable_tables_cleared,
        ttl_tables_reviewed=plan.audit_record.ttl_tables_reviewed,
        object_storage_refs_deleted=plan.audit_record.object_storage_refs_deleted,
        immutable_tables_preserved=plan.audit_record.immutable_tables_preserved,
        permanent_audit_tables_preserved=plan.audit_record.permanent_audit_tables_preserved,
        reason=plan.audit_record.reason,
        error_code=error_code,
    )
    try:
        audit_writer(audit_record.as_payload())
    except Exception:
        # Audit writer failures must be visible in the result, but the runtime
        # must not attempt to compensate by mutating immutable history.
        status = GDPR_DELETION_STATUS_FAILED
        error_code = "audit_write_failed"
        audit_record = GdprDeletionAuditRecord(
            deletion_request_id=audit_record.deletion_request_id,
            user_ref=audit_record.user_ref,
            requested_by_ref=audit_record.requested_by_ref,
            status=status,
            mutable_tables_cleared=audit_record.mutable_tables_cleared,
            ttl_tables_reviewed=audit_record.ttl_tables_reviewed,
            object_storage_refs_deleted=audit_record.object_storage_refs_deleted,
            immutable_tables_preserved=audit_record.immutable_tables_preserved,
            permanent_audit_tables_preserved=audit_record.permanent_audit_tables_preserved,
            reason=audit_record.reason,
            error_code=error_code,
        )

    return GdprDeletionExecutionResult(
        deletion_request_id=plan.audit_record.deletion_request_id,
        status=status,
        completed_actions=tuple(completed),
        audit_record=audit_record,
        error_code=error_code,
    )


def _normalize_text_tuple(values: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            normalized.append(text)
    return tuple(dict.fromkeys(normalized))


def _normalize_table_tuple(values: Sequence[str]) -> tuple[str, ...]:
    normalized = [_normalize_table_name(value) for value in values]
    return tuple(dict.fromkeys(item for item in normalized if item))


def _normalize_table_name(value: str) -> str:
    return str(value or "").strip().lower()


def _require_opaque_ref(value: str, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise GdprDeletionPolicyError(f"{field_name} must be non-empty")
    lowered = text.lower()
    if "@" in text or "clerk" in lowered or "customer" in lowered or "stripe" in lowered:
        raise GdprDeletionPolicyError(f"{field_name} must be opaque and must not contain direct identity")
    return text


def _assert_deletable_table_set(table_names: Sequence[str], *, kind: str) -> None:
    _assert_no_permanent_or_immutable_targets(table_names, kind=kind)
    for table_name in table_names:
        category = table_gdpr_category(table_name)
        if category not in {CATEGORY_B_MUTABLE, CATEGORY_C_TTL_DELETABLE}:
            raise GdprDeletionPolicyError(f"{kind} contains non-deletable table: {table_name}")


def _assert_no_permanent_or_immutable_targets(table_names: Sequence[str], *, kind: str) -> None:
    for table_name in table_names:
        normalized = _normalize_table_name(table_name)
        if normalized in IMMUTABLE_HISTORY_TABLES or normalized in PERMANENT_AUDIT_TABLES:
            raise GdprDeletionPolicyError(f"{kind} must not target immutable history table: {normalized}")


def _safe_error_code(exc: BaseException) -> str:
    text = exc.__class__.__name__ or "GdprDeletionError"
    return text[:80]


__all__ = [
    "CATEGORY_A_APPEND_ONLY",
    "CATEGORY_B_MUTABLE",
    "CATEGORY_C_TTL_DELETABLE",
    "CATEGORY_D_PERMANENT_AUDIT",
    "DEFAULT_MUTABLE_USER_TABLES",
    "DEFAULT_TTL_USER_TABLES",
    "GDPR_ACTION_DELETE_IDENTITY",
    "GDPR_ACTION_DELETE_MUTABLE_ROWS",
    "GDPR_ACTION_DELETE_OBJECT",
    "GDPR_ACTION_PRESERVE_IMMUTABLE_HISTORY",
    "GDPR_ACTION_WRITE_AUDIT",
    "GDPR_DELETION_STATUS_COMPLETED",
    "GDPR_DELETION_STATUS_FAILED",
    "GDPR_DELETION_STATUS_PLANNED",
    "IMMUTABLE_HISTORY_TABLES",
    "PERMANENT_AUDIT_TABLES",
    "GdprDeletionAction",
    "GdprDeletionAuditRecord",
    "GdprDeletionExecutionResult",
    "GdprDeletionPlan",
    "GdprDeletionPolicyError",
    "GdprDeletionRequest",
    "build_gdpr_deletion_plan",
    "execute_gdpr_deletion_plan",
    "table_gdpr_category",
]
