from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.contracts.nex_contract import (
    IssuerPublicShareManagementActionReportEntry,
    IssuerPublicShareManagementActionReportSummary,
    IssuerPublicShareGovernanceSummary,
    IssuerPublicShareManagementEntry,
    IssuerPublicShareManagementSummary,
    PublicNexShareBoundary,
    PublicNexShareDescriptor,
    ShareAuditEventType,
    ShareLifecycleState,
    ShareOperation,
)
from src.storage.nex_api import (
    describe_public_nex_artifact,
    export_public_nex_artifact,
    get_public_nex_format_boundary,
)

_ALLOWED_SHARE_LIFECYCLE_STATES: tuple[ShareLifecycleState, ...] = ("active", "expired", "revoked")
_TERMINAL_LIFECYCLE_STATES: tuple[ShareLifecycleState, ...] = ("expired", "revoked")
_MANAGEMENT_OPERATIONS: tuple[str, ...] = ("revoke", "extend_expiration", "delete", "archive")

_ALLOWED_AUDIT_EVENT_TYPES: tuple[ShareAuditEventType, ...] = ("created", "expiration_extended", "revoked", "archived", "unarchived")
_MAX_ISSUER_MANAGEMENT_ACTION_SHARES = 20
_MAX_ISSUER_MANAGEMENT_PAGE_LIMIT = 50
_MAX_ISSUER_ACTION_REPORT_PAGE_LIMIT = 50
_DEFAULT_RECENT_GOVERNANCE_ACTION_REPORT_LIMIT = 5
_UNSET = object()

_PUBLIC_NEX_SHARE_BOUNDARY = PublicNexShareBoundary(
    share_family="nex.public-link-share",
    transport_modes=("link",),
    access_modes=("public_readonly",),
    supported_roles=get_public_nex_format_boundary().supported_roles,
    artifact_format_family=get_public_nex_format_boundary().format_family,
    viewer_capabilities=("inspect_metadata", "download_artifact", "import_copy"),
    supported_operations=("inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy"),
    supported_lifecycle_states=_ALLOWED_SHARE_LIFECYCLE_STATES,
    terminal_lifecycle_states=_TERMINAL_LIFECYCLE_STATES,
    management_operations=_MANAGEMENT_OPERATIONS,
)


def get_public_nex_share_boundary() -> PublicNexShareBoundary:
    return _PUBLIC_NEX_SHARE_BOUNDARY


def _operation_capabilities_for_role(storage_role: str) -> tuple[ShareOperation, ...]:
    if storage_role == "working_save":
        return ("inspect_metadata", "download_artifact", "import_copy", "run_artifact")
    if storage_role == "commit_snapshot":
        return ("inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy")
    raise ValueError(f"Unsupported public link share storage_role: {storage_role}")




def _normalize_requested_share_ids(share_ids: list[str] | tuple[str, ...] | Sequence[str]) -> tuple[str, ...]:
    resolved: list[str] = []
    for raw in share_ids:
        if not isinstance(raw, str):
            raise ValueError("share_ids must contain only strings")
        share_id = raw.strip()
        if not share_id:
            raise ValueError("share_ids must not contain empty values")
        if share_id not in resolved:
            resolved.append(share_id)
    if not resolved:
        raise ValueError("share_ids must contain at least one share id")
    if len(resolved) > _MAX_ISSUER_MANAGEMENT_ACTION_SHARES:
        raise ValueError(f"share_ids exceeds bounded action limit ({_MAX_ISSUER_MANAGEMENT_ACTION_SHARES})")
    return tuple(resolved)


def _issuer_public_share_management_entry_from_descriptor(descriptor: PublicNexShareDescriptor) -> IssuerPublicShareManagementEntry:
    return IssuerPublicShareManagementEntry(
        share_id=descriptor.share_id,
        share_path=descriptor.share_path,
        title=descriptor.title,
        summary=descriptor.summary,
        storage_role=descriptor.storage_role,
        lifecycle_state=descriptor.lifecycle_state,
        stored_lifecycle_state=descriptor.stored_lifecycle_state,
        operation_capabilities=descriptor.operation_capabilities,
        canonical_ref=descriptor.canonical_ref,
        created_at=descriptor.created_at,
        updated_at=descriptor.updated_at,
        expires_at=descriptor.expires_at,
        audit_event_count=descriptor.audit_event_count,
        last_audit_event_type=descriptor.last_audit_event_type,
        last_audit_event_at=descriptor.last_audit_event_at,
    )


def _resolve_issuer_share_targets(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    share_ids: list[str] | tuple[str, ...] | Sequence[str],
    *,
    now_iso: str | None = None,
) -> tuple[dict[str, Any], ...]:
    issuer = issuer_user_ref.strip()
    if not issuer:
        raise ValueError("issuer_user_ref must be non-empty")
    requested_ids = _normalize_requested_share_ids(share_ids)
    matched: dict[str, dict[str, Any]] = {}
    for source in sources:
        payload = load_public_nex_link_share(source)
        descriptor = describe_public_nex_link_share(payload, now_iso=now_iso)
        if descriptor.issued_by_user_ref != issuer:
            continue
        if descriptor.share_id in requested_ids and descriptor.share_id not in matched:
            matched[descriptor.share_id] = payload
    missing = [share_id for share_id in requested_ids if share_id not in matched]
    if missing:
        raise ValueError("requested issuer public shares were not found or not owned: " + ", ".join(missing))
    return tuple(matched[share_id] for share_id in requested_ids)


def _merge_updated_share_sources(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    updated_payloads: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    replacements = {describe_public_nex_link_share(payload).share_id: load_public_nex_link_share(payload) for payload in updated_payloads}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        payload = load_public_nex_link_share(source)
        share_id = describe_public_nex_link_share(payload).share_id
        if share_id in replacements:
            merged.append(replacements[share_id])
            seen.add(share_id)
        else:
            merged.append(payload)
    for share_id, payload in replacements.items():
        if share_id not in seen:
            merged.append(payload)
    return tuple(merged)

def _optional_string(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string when present")
    resolved = value.strip()
    return resolved or None


def _parse_iso_datetime(value: str, *, field_name: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError(f"{field_name} must be a non-empty ISO datetime string")
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        resolved = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO datetime string") from exc
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=UTC)
    return resolved.astimezone(UTC)


def _resolve_now(now_iso: str | None = None) -> datetime:
    if now_iso is None:
        return datetime.now(UTC)
    return _parse_iso_datetime(now_iso, field_name="now_iso")


def _effective_share_lifecycle_state(*, stored_state: ShareLifecycleState, expires_at: str | None, now_iso: str | None = None) -> ShareLifecycleState:
    if stored_state != "active":
        return stored_state
    if not expires_at:
        return stored_state
    expires_at_dt = _parse_iso_datetime(expires_at, field_name="public link share payload share.lifecycle.expires_at")
    now_dt = _resolve_now(now_iso)
    return "expired" if expires_at_dt <= now_dt else stored_state


def _validate_lifecycle_mutation_allowed(*, descriptor: PublicNexShareDescriptor, target_operation: ShareOperation, target_state: ShareLifecycleState | None = None) -> None:
    effective_state = descriptor.lifecycle_state
    if effective_state == "revoked":
        raise ValueError(f"public link share lifecycle is terminal (state={effective_state}); operation={target_operation} is not allowed")
    if effective_state == "expired":
        raise ValueError(f"public link share lifecycle is terminal (state={effective_state}); operation={target_operation} is not allowed")
    if target_state == "expired":
        raise ValueError("public link share lifecycle state 'expired' is time-derived and cannot be set directly")


def _canonicalize_share_lifecycle(
    share: Mapping[str, Any],
    *,
    created_at: str | None = None,
    updated_at: str | None = None,
    expires_at: str | None = None,
    issued_by_user_ref: str | None = None,
    lifecycle_state: ShareLifecycleState = "active",
) -> dict[str, Any]:
    raw_lifecycle = share.get("lifecycle")
    if raw_lifecycle is None:
        lifecycle: dict[str, Any] = {}
    elif isinstance(raw_lifecycle, Mapping):
        lifecycle = dict(raw_lifecycle)
    else:
        raise ValueError("public link share payload share.lifecycle must be an object when present")
    state_value = _optional_string(lifecycle.get("state"), field_name="public link share payload share.lifecycle.state") or lifecycle_state
    if state_value not in _ALLOWED_SHARE_LIFECYCLE_STATES:
        raise ValueError("public link share payload share.lifecycle.state is unsupported")
    created = _optional_string(lifecycle.get("created_at"), field_name="public link share payload share.lifecycle.created_at")
    updated = _optional_string(lifecycle.get("updated_at"), field_name="public link share payload share.lifecycle.updated_at")
    expires = _optional_string(lifecycle.get("expires_at"), field_name="public link share payload share.lifecycle.expires_at")
    issued_by = _optional_string(lifecycle.get("issued_by_user_ref"), field_name="public link share payload share.lifecycle.issued_by_user_ref")
    if created_at is not None:
        _parse_iso_datetime(created_at, field_name="public link share payload share.lifecycle.created_at")
    if updated_at is not None:
        _parse_iso_datetime(updated_at, field_name="public link share payload share.lifecycle.updated_at")
    effective_expires = expires_at if expires_at is not None else expires
    if effective_expires is not None:
        _parse_iso_datetime(effective_expires, field_name="public link share payload share.lifecycle.expires_at")
    return {
        "state": state_value,
        "created_at": created_at or created,
        "updated_at": updated_at or updated or created_at or created,
        "expires_at": effective_expires,
        "issued_by_user_ref": issued_by_user_ref if issued_by_user_ref is not None else issued_by,
    }


def _canonicalize_share_management(
    share: Mapping[str, Any],
    *,
    archived: bool | None = None,
    archived_at: str | None | object = _UNSET,
) -> dict[str, Any]:
    raw_management = share.get("management")
    if raw_management is None:
        management: dict[str, Any] = {}
    elif isinstance(raw_management, Mapping):
        management = dict(raw_management)
    else:
        raise ValueError("public link share payload share.management must be an object when present")
    existing_archived = bool(management.get("archived", False))
    resolved_archived = existing_archived if archived is None else bool(archived)
    existing_archived_at = _optional_string(management.get("archived_at"), field_name="public link share payload share.management.archived_at")
    if archived_at is _UNSET:
        resolved_archived_at = existing_archived_at
    else:
        resolved_archived_at = archived_at
    if resolved_archived_at is not None:
        _parse_iso_datetime(resolved_archived_at, field_name="public link share payload share.management.archived_at")
    if not resolved_archived:
        resolved_archived_at = None
    elif resolved_archived_at is None:
        resolved_archived_at = existing_archived_at
    return {
        "archived": resolved_archived,
        "archived_at": resolved_archived_at,
    }


def _canonicalize_audit_history(
    share: Mapping[str, Any],
    *,
    lifecycle: Mapping[str, Any],
    audit_history: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] | None = None,
) -> list[dict[str, Any]]:
    raw_audit = share.get("audit")
    if raw_audit is None:
        audit_obj: dict[str, Any] = {}
    elif isinstance(raw_audit, Mapping):
        audit_obj = dict(raw_audit)
    else:
        raise ValueError("public link share payload share.audit must be an object when present")
    history_source = audit_history if audit_history is not None else audit_obj.get("history")
    if history_source is None:
        default_at = lifecycle.get("created_at") or lifecycle.get("updated_at")
        if default_at:
            history_source = [{
                "sequence": 1,
                "event_type": "created",
                "at": default_at,
                "actor_user_ref": lifecycle.get("issued_by_user_ref"),
                "stored_lifecycle_state": lifecycle.get("state", "active"),
                "effective_lifecycle_state": _effective_share_lifecycle_state(stored_state=lifecycle.get("state", "active"), expires_at=lifecycle.get("expires_at"), now_iso=default_at),
                "details": None,
            }]
        else:
            history_source = []
    if not isinstance(history_source, (list, tuple)):
        raise ValueError("public link share payload share.audit.history must be a list when present")
    resolved: list[dict[str, Any]] = []
    for index, entry in enumerate(history_source, start=1):
        if not isinstance(entry, Mapping):
            raise ValueError("public link share payload share.audit.history entries must be objects")
        sequence_value = entry.get("sequence", index)
        if not isinstance(sequence_value, int) or sequence_value <= 0:
            raise ValueError("public link share payload share.audit.history.sequence must be a positive integer")
        event_type = _optional_string(entry.get("event_type"), field_name="public link share payload share.audit.history.event_type")
        if event_type not in _ALLOWED_AUDIT_EVENT_TYPES:
            raise ValueError("public link share payload share.audit.history.event_type is unsupported")
        at_value = _optional_string(entry.get("at"), field_name="public link share payload share.audit.history.at")
        if not at_value:
            raise ValueError("public link share payload share.audit.history.at must be present")
        _parse_iso_datetime(at_value, field_name="public link share payload share.audit.history.at")
        actor_user_ref = _optional_string(entry.get("actor_user_ref"), field_name="public link share payload share.audit.history.actor_user_ref")
        stored_state = _optional_string(entry.get("stored_lifecycle_state"), field_name="public link share payload share.audit.history.stored_lifecycle_state") or lifecycle.get("state", "active")
        if stored_state not in _ALLOWED_SHARE_LIFECYCLE_STATES:
            raise ValueError("public link share payload share.audit.history.stored_lifecycle_state is unsupported")
        effective_state = _optional_string(entry.get("effective_lifecycle_state"), field_name="public link share payload share.audit.history.effective_lifecycle_state")
        if effective_state is None:
            effective_state = _effective_share_lifecycle_state(stored_state=stored_state, expires_at=lifecycle.get("expires_at"), now_iso=at_value)
        if effective_state not in _ALLOWED_SHARE_LIFECYCLE_STATES:
            raise ValueError("public link share payload share.audit.history.effective_lifecycle_state is unsupported")
        details_raw = entry.get("details")
        details: dict[str, str] | None
        if details_raw is None:
            details = None
        elif isinstance(details_raw, Mapping):
            details = {}
            for k, v in details_raw.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ValueError("public link share payload share.audit.history.details must be a string map when present")
                details[k] = v
        else:
            raise ValueError("public link share payload share.audit.history.details must be an object when present")
        resolved.append({
            "sequence": index,
            "event_type": event_type,
            "at": at_value,
            "actor_user_ref": actor_user_ref,
            "stored_lifecycle_state": stored_state,
            "effective_lifecycle_state": effective_state,
            "details": details,
        })
    return resolved


def _with_appended_audit_event(
    payload: dict[str, Any],
    *,
    event_type: ShareAuditEventType,
    actor_user_ref: str | None = None,
    at: str | None = None,
    details: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    share = payload.get("share")
    if not isinstance(share, dict):
        raise ValueError("public link share payload must include object section 'share'")
    lifecycle = share.get("lifecycle")
    if not isinstance(lifecycle, Mapping):
        raise ValueError("public link share payload share.lifecycle must be an object")
    audit_history = _canonicalize_audit_history(share, lifecycle=lifecycle)
    event_at = at or lifecycle.get("updated_at") or lifecycle.get("created_at")
    if not event_at:
        raise ValueError("public link share audit event requires a timestamp")
    _parse_iso_datetime(event_at, field_name="public link share payload share.audit.history.at")
    entry = {
        "sequence": len(audit_history) + 1,
        "event_type": event_type,
        "at": event_at,
        "actor_user_ref": actor_user_ref or lifecycle.get("issued_by_user_ref"),
        "stored_lifecycle_state": lifecycle.get("state", "active"),
        "effective_lifecycle_state": _effective_share_lifecycle_state(stored_state=lifecycle.get("state", "active"), expires_at=lifecycle.get("expires_at"), now_iso=event_at),
        "details": dict(details) if details is not None else None,
    }
    audit_history.append(entry)
    management = share.get("management", {}) if isinstance(share.get("management"), Mapping) else {}
    exported = export_public_nex_link_share(
        payload["artifact"],
        share_id=share.get("share_id"),
        title=share.get("title"),
        summary=share.get("summary"),
        lifecycle_state=lifecycle.get("state", "active"),
        created_at=lifecycle.get("created_at"),
        updated_at=lifecycle.get("updated_at"),
        expires_at=lifecycle.get("expires_at"),
        issued_by_user_ref=lifecycle.get("issued_by_user_ref"),
        audit_history=audit_history,
        archived=bool(management.get("archived", False)),
        archived_at=management.get("archived_at"),
    )
    return exported


def list_public_nex_link_share_audit_history(
    source: str | Path | dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    payload = load_public_nex_link_share(source)
    share = payload.get("share")
    lifecycle = share.get("lifecycle", {}) if isinstance(share, dict) and isinstance(share.get("lifecycle"), Mapping) else {}
    if not isinstance(share, Mapping):
        raise ValueError("public link share payload must include object section 'share'")
    history = _canonicalize_audit_history(share, lifecycle=lifecycle)
    return tuple(dict(entry) for entry in history)


def _normalize_issuer_management_filter_value(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    resolved = value.strip()
    return resolved or None


def _filter_issuer_public_share_entries(
    entries: Sequence[IssuerPublicShareManagementEntry],
    *,
    lifecycle_state: ShareLifecycleState | None = None,
    stored_lifecycle_state: ShareLifecycleState | None = None,
    storage_role: str | None = None,
    requires_operation: ShareOperation | None = None,
    archived: bool | None = None,
) -> tuple[IssuerPublicShareManagementEntry, ...]:
    normalized_lifecycle_state = _normalize_issuer_management_filter_value(lifecycle_state, field_name="lifecycle_state")
    normalized_stored_state = _normalize_issuer_management_filter_value(stored_lifecycle_state, field_name="stored_lifecycle_state")
    normalized_storage_role = _normalize_issuer_management_filter_value(storage_role, field_name="storage_role")
    normalized_operation = _normalize_issuer_management_filter_value(requires_operation, field_name="requires_operation")
    normalized_archived = archived
    if normalized_lifecycle_state is not None and normalized_lifecycle_state not in _ALLOWED_SHARE_LIFECYCLE_STATES:
        raise ValueError("issuer public share lifecycle_state filter is unsupported")
    if normalized_stored_state is not None and normalized_stored_state not in _ALLOWED_SHARE_LIFECYCLE_STATES:
        raise ValueError("issuer public share stored_lifecycle_state filter is unsupported")
    if normalized_storage_role is not None and normalized_storage_role not in get_public_nex_format_boundary().supported_roles:
        raise ValueError("issuer public share storage_role filter is unsupported")
    if normalized_operation is not None and normalized_operation not in _PUBLIC_NEX_SHARE_BOUNDARY.supported_operations:
        raise ValueError("issuer public share operation filter is unsupported")
    resolved: list[IssuerPublicShareManagementEntry] = []
    for entry in entries:
        if normalized_lifecycle_state is not None and entry.lifecycle_state != normalized_lifecycle_state:
            continue
        if normalized_stored_state is not None and entry.stored_lifecycle_state != normalized_stored_state:
            continue
        if normalized_storage_role is not None and entry.storage_role != normalized_storage_role:
            continue
        if normalized_operation is not None and normalized_operation not in entry.operation_capabilities:
            continue
        if normalized_archived is not None and entry.archived is not normalized_archived:
            continue
        resolved.append(entry)
    return tuple(resolved)


def normalize_issuer_public_share_management_pagination(*, limit: int | None = None, offset: int = 0) -> tuple[int, int]:
    resolved_limit = 20 if limit is None else limit
    resolved_offset = offset
    if resolved_limit <= 0:
        raise ValueError("issuer public share management limit must be > 0")
    if resolved_limit > _MAX_ISSUER_MANAGEMENT_PAGE_LIMIT:
        raise ValueError(f"issuer public share management limit exceeds bounded page limit ({_MAX_ISSUER_MANAGEMENT_PAGE_LIMIT})")
    if resolved_offset < 0:
        raise ValueError("issuer public share management offset must be >= 0")
    return resolved_limit, resolved_offset


def list_public_nex_link_shares_for_issuer(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    *,
    now_iso: str | None = None,
    lifecycle_state: ShareLifecycleState | None = None,
    stored_lifecycle_state: ShareLifecycleState | None = None,
    storage_role: str | None = None,
    requires_operation: ShareOperation | None = None,
    archived: bool | None = None,
) -> tuple[IssuerPublicShareManagementEntry, ...]:
    issuer = issuer_user_ref.strip()
    if not issuer:
        raise ValueError("issuer_user_ref must be non-empty")
    resolved: list[IssuerPublicShareManagementEntry] = []
    for source in sources:
        descriptor = describe_public_nex_link_share(source, now_iso=now_iso)
        if descriptor.issued_by_user_ref != issuer:
            continue
        resolved.append(_issuer_public_share_management_entry_from_descriptor(descriptor))
    resolved.sort(key=lambda entry: (
        entry.updated_at or "",
        entry.created_at or "",
        entry.last_audit_event_at or "",
        entry.share_id,
    ), reverse=True)
    return _filter_issuer_public_share_entries(
        tuple(resolved),
        lifecycle_state=lifecycle_state,
        stored_lifecycle_state=stored_lifecycle_state,
        storage_role=storage_role,
        requires_operation=requires_operation,
        archived=archived,
    )


def summarize_public_nex_link_shares_for_issuer(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    *,
    now_iso: str | None = None,
    lifecycle_state: ShareLifecycleState | None = None,
    stored_lifecycle_state: ShareLifecycleState | None = None,
    storage_role: str | None = None,
    requires_operation: ShareOperation | None = None,
    archived: bool | None = None,
) -> IssuerPublicShareManagementSummary:
    entries = list_public_nex_link_shares_for_issuer(
        sources,
        issuer_user_ref,
        now_iso=now_iso,
        lifecycle_state=lifecycle_state,
        stored_lifecycle_state=stored_lifecycle_state,
        storage_role=storage_role,
        requires_operation=requires_operation,
        archived=archived,
    )
    active_count = sum(1 for entry in entries if entry.lifecycle_state == "active")
    expired_count = sum(1 for entry in entries if entry.lifecycle_state == "expired")
    revoked_count = sum(1 for entry in entries if entry.lifecycle_state == "revoked")
    archived_count = sum(1 for entry in entries if entry.archived)
    working_save_count = sum(1 for entry in entries if entry.storage_role == "working_save")
    commit_snapshot_count = sum(1 for entry in entries if entry.storage_role == "commit_snapshot")
    runnable_count = sum(1 for entry in entries if entry.lifecycle_state == "active" and "run_artifact" in entry.operation_capabilities)
    checkoutable_count = sum(1 for entry in entries if entry.lifecycle_state == "active" and "checkout_working_copy" in entry.operation_capabilities)
    latest_created_at = max((entry.created_at for entry in entries if entry.created_at), default=None)
    latest_updated_at = max((entry.updated_at for entry in entries if entry.updated_at), default=None)
    latest_audit_event_at = max((entry.last_audit_event_at for entry in entries if entry.last_audit_event_at), default=None)
    return IssuerPublicShareManagementSummary(
        issuer_user_ref=issuer_user_ref.strip(),
        total_share_count=len(entries),
        active_share_count=active_count,
        expired_share_count=expired_count,
        revoked_share_count=revoked_count,
        archived_share_count=archived_count,
        working_save_share_count=working_save_count,
        commit_snapshot_share_count=commit_snapshot_count,
        runnable_share_count=runnable_count,
        checkoutable_share_count=checkoutable_count,
        latest_created_at=latest_created_at,
        latest_updated_at=latest_updated_at,
        latest_audit_event_at=latest_audit_event_at,
    )


def ensure_public_nex_link_share_operation_allowed(
    source: str | Path | dict[str, Any],
    operation: ShareOperation,
    *,
    now_iso: str | None = None,
) -> PublicNexShareDescriptor:
    descriptor = describe_public_nex_link_share(source, now_iso=now_iso)
    if descriptor.lifecycle_state != "active":
        raise ValueError(
            f"public link share is not active (state={descriptor.lifecycle_state}); operation={operation} is not allowed"
        )
    if operation not in descriptor.operation_capabilities:
        raise ValueError(
            f"public link share does not allow operation={operation} for storage_role={descriptor.storage_role}"
        )
    return descriptor


def is_public_nex_link_share_payload(data: Mapping[str, Any]) -> bool:
    if not isinstance(data, Mapping):
        return False
    share = data.get("share")
    artifact = data.get("artifact")
    if not isinstance(share, Mapping) or not isinstance(artifact, Mapping):
        return False
    return share.get("share_family") == _PUBLIC_NEX_SHARE_BOUNDARY.share_family


def extract_public_nex_link_share_artifact(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    payload = load_public_nex_link_share(source)
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError("public link share payload must contain a canonical artifact object")
    return dict(artifact)


def _stable_share_id(artifact_payload: dict[str, Any]) -> str:
    canonical = json.dumps(artifact_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"share_{sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def _stable_action_report_id(*, issuer_user_ref: str, action: str, created_at: str, requested_share_ids: Sequence[str], affected_share_ids: Sequence[str]) -> str:
    canonical = json.dumps(
        {
            "issuer_user_ref": issuer_user_ref,
            "action": action,
            "created_at": created_at,
            "requested_share_ids": list(requested_share_ids),
            "affected_share_ids": list(affected_share_ids),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"share_report_{sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def export_public_nex_link_share(
    model_or_data: Any,
    *,
    share_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    lifecycle_state: ShareLifecycleState = "active",
    created_at: str | None = None,
    updated_at: str | None = None,
    expires_at: str | None = None,
    issued_by_user_ref: str | None = None,
    audit_history: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] | None = None,
    archived: bool = False,
    archived_at: str | None = None,
) -> dict[str, Any]:
    artifact = export_public_nex_artifact(model_or_data)
    descriptor = describe_public_nex_artifact(artifact)
    meta = artifact.get("meta", {}) if isinstance(artifact.get("meta"), dict) else {}
    resolved_share_id = share_id or _stable_share_id(artifact)
    if not isinstance(resolved_share_id, str) or not resolved_share_id.strip():
        raise ValueError("public link share requires a non-empty share_id")
    resolved_title = title or str(meta.get("name") or descriptor.canonical_ref)
    resolved_summary = summary if summary is not None else (str(meta.get("description")) if meta.get("description") is not None else None)
    lifecycle = _canonicalize_share_lifecycle({}, created_at=created_at, updated_at=updated_at, expires_at=expires_at, issued_by_user_ref=issued_by_user_ref, lifecycle_state=lifecycle_state)
    management = _canonicalize_share_management({}, archived=archived, archived_at=archived_at)
    audit_payload = {"history": _canonicalize_audit_history({}, lifecycle=lifecycle, audit_history=audit_history)}
    return {
        "share": {
            "share_family": _PUBLIC_NEX_SHARE_BOUNDARY.share_family,
            "transport": "link",
            "access_mode": "public_readonly",
            "share_id": resolved_share_id.strip(),
            "share_path": f"/share/{resolved_share_id.strip()}",
            "artifact_format_family": _PUBLIC_NEX_SHARE_BOUNDARY.artifact_format_family,
            "storage_role": descriptor.storage_role,
            "canonical_ref": descriptor.canonical_ref,
            "title": resolved_title,
            "summary": resolved_summary,
            "viewer_capabilities": list(_PUBLIC_NEX_SHARE_BOUNDARY.viewer_capabilities),
            "operation_capabilities": list(_operation_capabilities_for_role(descriptor.storage_role)),
            "lifecycle": lifecycle,
            "management": management,
            "audit": audit_payload,
        },
        "artifact": artifact,
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("public link share payload must be a JSON object")
    return data


def load_public_nex_link_share(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    payload = _read_json_object(Path(source)) if isinstance(source, (str, Path)) else dict(source)
    share = payload.get("share")
    artifact = payload.get("artifact")
    if not isinstance(share, dict):
        raise ValueError("public link share payload must include object section 'share'")
    if not isinstance(artifact, dict):
        raise ValueError("public link share payload must include object section 'artifact'")
    if share.get("share_family") != _PUBLIC_NEX_SHARE_BOUNDARY.share_family:
        raise ValueError("unsupported public link share family")
    if share.get("transport") != "link":
        raise ValueError("public link share payload must declare transport=link")
    if share.get("access_mode") != "public_readonly":
        raise ValueError("public link share payload must declare access_mode=public_readonly")
    share_id = share.get("share_id")
    if not isinstance(share_id, str) or not share_id.strip():
        raise ValueError("public link share payload must include non-empty share.share_id")
    exported_artifact = export_public_nex_artifact(artifact)
    artifact_descriptor = describe_public_nex_artifact(exported_artifact)
    title = share.get("title")
    if not isinstance(title, str) or not title.strip():
        meta = exported_artifact.get("meta", {}) if isinstance(exported_artifact.get("meta"), dict) else {}
        title = str(meta.get("name") or artifact_descriptor.canonical_ref)
    summary = share.get("summary")
    if summary is not None and not isinstance(summary, str):
        raise ValueError("public link share payload share.summary must be a string when present")
    lifecycle = _canonicalize_share_lifecycle(share)
    management = _canonicalize_share_management(share)
    audit_history = _canonicalize_audit_history(share, lifecycle=lifecycle)
    return export_public_nex_link_share(
        exported_artifact,
        share_id=share_id.strip(),
        title=title.strip(),
        summary=summary,
        lifecycle_state=lifecycle["state"],
        created_at=lifecycle["created_at"],
        updated_at=lifecycle["updated_at"],
        expires_at=lifecycle["expires_at"],
        issued_by_user_ref=lifecycle["issued_by_user_ref"],
        audit_history=audit_history,
        archived=management["archived"],
        archived_at=management["archived_at"],
    )


def describe_public_nex_link_share(
    source: str | Path | dict[str, Any],
    *,
    now_iso: str | None = None,
) -> PublicNexShareDescriptor:
    payload = load_public_nex_link_share(source)
    share = payload["share"]
    descriptor = describe_public_nex_artifact(payload["artifact"])
    lifecycle = share.get("lifecycle", {}) if isinstance(share.get("lifecycle"), dict) else {}
    history = list_public_nex_link_share_audit_history(payload)
    management = share.get("management", {}) if isinstance(share.get("management"), dict) else {}
    stored_state = lifecycle.get("state", "active")
    effective_state = _effective_share_lifecycle_state(
        stored_state=stored_state,
        expires_at=lifecycle.get("expires_at"),
        now_iso=now_iso,
    )
    return PublicNexShareDescriptor(
        share_id=share["share_id"],
        share_path=share["share_path"],
        transport="link",
        access_mode="public_readonly",
        storage_role=descriptor.storage_role,
        canonical_ref=descriptor.canonical_ref,
        title=share["title"],
        summary=share.get("summary"),
        artifact_format_family=_PUBLIC_NEX_SHARE_BOUNDARY.artifact_format_family,
        viewer_capabilities=_PUBLIC_NEX_SHARE_BOUNDARY.viewer_capabilities,
        operation_capabilities=_operation_capabilities_for_role(descriptor.storage_role),
        stored_lifecycle_state=stored_state,
        lifecycle_state=effective_state,
        created_at=lifecycle.get("created_at"),
        updated_at=lifecycle.get("updated_at"),
        expires_at=lifecycle.get("expires_at"),
        issued_by_user_ref=lifecycle.get("issued_by_user_ref"),
        archived=bool(management.get("archived", False)),
        archived_at=management.get("archived_at"),
        source_working_save_id=descriptor.source_working_save_id,
        audit_event_count=len(history),
        last_audit_event_type=history[-1]["event_type"] if history else None,
        last_audit_event_at=history[-1]["at"] if history else None,
    )


def update_public_nex_link_share_lifecycle(
    source: str | Path | dict[str, Any],
    *,
    lifecycle_state: ShareLifecycleState | None = None,
    expires_at: str | None | object = _UNSET,
    updated_at: str | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    payload = load_public_nex_link_share(source)
    share = payload["share"]
    lifecycle = share.get("lifecycle", {}) if isinstance(share.get("lifecycle"), dict) else {}
    descriptor = describe_public_nex_link_share(payload, now_iso=now_iso or updated_at)
    target_state = lifecycle_state or descriptor.stored_lifecycle_state
    if lifecycle_state is not None:
        _validate_lifecycle_mutation_allowed(descriptor=descriptor, target_operation="revoke" if lifecycle_state == "revoked" else "extend_expiration", target_state=target_state)
    if expires_at is not _UNSET:
        _validate_lifecycle_mutation_allowed(descriptor=descriptor, target_operation="extend_expiration", target_state=target_state)
        if expires_at is not None:
            new_expires_at = _parse_iso_datetime(expires_at, field_name="public link share payload share.lifecycle.expires_at")
            reference_now = _resolve_now(now_iso or updated_at)
            if new_expires_at <= reference_now:
                raise ValueError("public link share expiration extension must be in the future")
            current_expires_at = lifecycle.get("expires_at")
            if current_expires_at:
                current_expires_dt = _parse_iso_datetime(current_expires_at, field_name="public link share payload share.lifecycle.expires_at")
                if new_expires_at <= current_expires_dt:
                    raise ValueError("public link share expiration extension must move forward")
    next_expires = lifecycle.get("expires_at") if expires_at is _UNSET else expires_at
    management = share.get("management", {}) if isinstance(share.get("management"), Mapping) else {}
    return export_public_nex_link_share(
        payload["artifact"],
        share_id=share["share_id"],
        title=share.get("title"),
        summary=share.get("summary"),
        lifecycle_state=target_state,
        created_at=lifecycle.get("created_at"),
        updated_at=updated_at or lifecycle.get("updated_at") or now_iso,
        expires_at=next_expires,
        issued_by_user_ref=lifecycle.get("issued_by_user_ref"),
        audit_history=_canonicalize_audit_history(share, lifecycle=lifecycle),
        archived=bool(management.get("archived", False)),
        archived_at=management.get("archived_at"),
    )


def revoke_public_nex_link_share(
    source: str | Path | dict[str, Any],
    *,
    now_iso: str | None = None,
    actor_user_ref: str | None = None,
) -> dict[str, Any]:
    updated = update_public_nex_link_share_lifecycle(
        source,
        lifecycle_state="revoked",
        updated_at=now_iso or datetime.now(UTC).isoformat(),
        now_iso=now_iso,
    )
    return _with_appended_audit_event(updated, event_type="revoked", actor_user_ref=actor_user_ref, at=now_iso or datetime.now(UTC).isoformat())


def extend_public_nex_link_share_expiration(
    source: str | Path | dict[str, Any],
    *,
    expires_at: str,
    now_iso: str | None = None,
    actor_user_ref: str | None = None,
) -> dict[str, Any]:
    updated = update_public_nex_link_share_lifecycle(
        source,
        expires_at=expires_at,
        updated_at=now_iso or datetime.now(UTC).isoformat(),
        now_iso=now_iso,
    )
    return _with_appended_audit_event(updated, event_type="expiration_extended", actor_user_ref=actor_user_ref, at=now_iso or datetime.now(UTC).isoformat(), details={"expires_at": expires_at})




def revoke_public_nex_link_shares_for_issuer(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    share_ids: list[str] | tuple[str, ...] | Sequence[str],
    *,
    now_iso: str | None = None,
    actor_user_ref: str | None = None,
) -> tuple[dict[str, Any], ...]:
    targets = _resolve_issuer_share_targets(sources, issuer_user_ref, share_ids, now_iso=now_iso)
    return tuple(
        revoke_public_nex_link_share(
            payload,
            now_iso=now_iso,
            actor_user_ref=actor_user_ref or issuer_user_ref.strip(),
        )
        for payload in targets
    )


def extend_public_nex_link_shares_for_issuer_expiration(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    share_ids: list[str] | tuple[str, ...] | Sequence[str],
    *,
    expires_at: str,
    now_iso: str | None = None,
    actor_user_ref: str | None = None,
) -> tuple[dict[str, Any], ...]:
    targets = _resolve_issuer_share_targets(sources, issuer_user_ref, share_ids, now_iso=now_iso)
    return tuple(
        extend_public_nex_link_share_expiration(
            payload,
            expires_at=expires_at,
            now_iso=now_iso,
            actor_user_ref=actor_user_ref or issuer_user_ref.strip(),
        )
        for payload in targets
    )


def update_public_nex_link_share_archive(
    source: str | Path | dict[str, Any],
    *,
    archived: bool = True,
    updated_at: str | None = None,
    now_iso: str | None = None,
    actor_user_ref: str | None = None,
) -> dict[str, Any]:
    payload = load_public_nex_link_share(source)
    share = payload["share"]
    lifecycle = share.get("lifecycle", {}) if isinstance(share.get("lifecycle"), Mapping) else {}
    management = share.get("management", {}) if isinstance(share.get("management"), Mapping) else {}
    event_at = updated_at or now_iso or datetime.now(UTC).isoformat()
    next_archived_at = event_at if archived else None
    updated = export_public_nex_link_share(
        payload["artifact"],
        share_id=share.get("share_id"),
        title=share.get("title"),
        summary=share.get("summary"),
        lifecycle_state=lifecycle.get("state", "active"),
        created_at=lifecycle.get("created_at"),
        updated_at=event_at,
        expires_at=lifecycle.get("expires_at"),
        issued_by_user_ref=lifecycle.get("issued_by_user_ref"),
        audit_history=_canonicalize_audit_history(share, lifecycle=lifecycle),
        archived=archived,
        archived_at=next_archived_at,
    )
    event_type: ShareAuditEventType = "archived" if archived else "unarchived"
    return _with_appended_audit_event(updated, event_type=event_type, actor_user_ref=actor_user_ref, at=event_at)


def archive_public_nex_link_shares_for_issuer(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    share_ids: list[str] | tuple[str, ...] | Sequence[str],
    *,
    archived: bool = True,
    now_iso: str | None = None,
    actor_user_ref: str | None = None,
) -> tuple[dict[str, Any], ...]:
    targets = _resolve_issuer_share_targets(sources, issuer_user_ref, share_ids, now_iso=now_iso)
    return tuple(
        update_public_nex_link_share_archive(
            payload,
            archived=archived,
            updated_at=now_iso or datetime.now(UTC).isoformat(),
            now_iso=now_iso,
            actor_user_ref=actor_user_ref or issuer_user_ref.strip(),
        )
        for payload in targets
    )



def delete_public_nex_link_shares_for_issuer(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    share_ids: list[str] | tuple[str, ...] | Sequence[str],
    *,
    now_iso: str | None = None,
) -> tuple[IssuerPublicShareManagementEntry, ...]:
    targets = _resolve_issuer_share_targets(sources, issuer_user_ref, share_ids, now_iso=now_iso)
    return tuple(
        _issuer_public_share_management_entry_from_descriptor(describe_public_nex_link_share(payload, now_iso=now_iso))
        for payload in targets
    )


def build_issuer_public_share_management_action_report(
    *,
    issuer_user_ref: str,
    action: str,
    scope: str,
    created_at: str,
    requested_share_ids: Sequence[str],
    affected_share_ids: Sequence[str],
    before_summary: IssuerPublicShareManagementSummary,
    after_summary: IssuerPublicShareManagementSummary,
    actor_user_ref: str | None = None,
    expires_at: str | None = None,
    archived: bool | None = None,
) -> dict[str, Any]:
    issuer = issuer_user_ref.strip()
    if not issuer:
        raise ValueError("issuer_user_ref must be non-empty")
    requested = _normalize_requested_share_ids(requested_share_ids)
    affected = _normalize_requested_share_ids(affected_share_ids) if affected_share_ids else ()
    _parse_iso_datetime(created_at, field_name="issuer public share management action report created_at")
    if expires_at is not None:
        _parse_iso_datetime(expires_at, field_name="issuer public share management action report expires_at")
    return {
        "report_id": _stable_action_report_id(
            issuer_user_ref=issuer,
            action=action,
            created_at=created_at,
            requested_share_ids=requested,
            affected_share_ids=affected,
        ),
        "issuer_user_ref": issuer,
        "action": action,
        "scope": scope,
        "created_at": created_at,
        "requested_share_ids": list(requested),
        "affected_share_ids": list(affected),
        "affected_share_count": len(affected),
        "before_total_share_count": before_summary.total_share_count,
        "after_total_share_count": after_summary.total_share_count,
        "actor_user_ref": actor_user_ref or issuer,
        "expires_at": expires_at,
        "archived": archived,
    }


def _canonicalize_management_action_report_row(row: Mapping[str, Any]) -> IssuerPublicShareManagementActionReportEntry:
    report_id = _optional_string(row.get("report_id"), field_name="issuer public share management action report report_id")
    issuer_user_ref = _optional_string(row.get("issuer_user_ref"), field_name="issuer public share management action report issuer_user_ref")
    action = _optional_string(row.get("action"), field_name="issuer public share management action report action")
    scope = _optional_string(row.get("scope"), field_name="issuer public share management action report scope")
    created_at = _optional_string(row.get("created_at"), field_name="issuer public share management action report created_at")
    if not report_id or not issuer_user_ref or not action or not scope or not created_at:
        raise ValueError("issuer public share management action report is missing required fields")
    if action not in _MANAGEMENT_OPERATIONS:
        raise ValueError("issuer public share management action report action is unsupported")
    if scope not in ("issuer_bulk", "single_share"):
        raise ValueError("issuer public share management action report scope is unsupported")
    _parse_iso_datetime(created_at, field_name="issuer public share management action report created_at")
    requested_raw = row.get("requested_share_ids") or ()
    if not isinstance(requested_raw, (list, tuple)):
        raise ValueError("issuer public share management action report requested_share_ids must be a list")
    requested_share_ids = _normalize_requested_share_ids(requested_raw) if requested_raw else ()
    affected_raw = row.get("affected_share_ids") or ()
    if not isinstance(affected_raw, (list, tuple)):
        raise ValueError("issuer public share management action report affected_share_ids must be a list")
    affected_share_ids = _normalize_requested_share_ids(affected_raw) if affected_raw else ()
    affected_share_count = row.get("affected_share_count", len(affected_share_ids))
    if not isinstance(affected_share_count, int) or affected_share_count < 0:
        raise ValueError("issuer public share management action report affected_share_count must be a non-negative integer")
    before_total = row.get("before_total_share_count")
    after_total = row.get("after_total_share_count")
    if not isinstance(before_total, int) or before_total < 0 or not isinstance(after_total, int) or after_total < 0:
        raise ValueError("issuer public share management action report before/after totals must be non-negative integers")
    expires_at = _optional_string(row.get("expires_at"), field_name="issuer public share management action report expires_at")
    if expires_at is not None:
        _parse_iso_datetime(expires_at, field_name="issuer public share management action report expires_at")
    archived = row.get("archived")
    if archived is not None and not isinstance(archived, bool):
        raise ValueError("issuer public share management action report archived must be a boolean when present")
    actor_user_ref = _optional_string(row.get("actor_user_ref"), field_name="issuer public share management action report actor_user_ref")
    return IssuerPublicShareManagementActionReportEntry(
        report_id=report_id,
        issuer_user_ref=issuer_user_ref,
        action=action,
        scope=scope,
        created_at=created_at,
        requested_share_ids=requested_share_ids,
        affected_share_ids=affected_share_ids,
        affected_share_count=affected_share_count,
        before_total_share_count=before_total,
        after_total_share_count=after_total,
        actor_user_ref=actor_user_ref,
        expires_at=expires_at,
        archived=archived,
    )


def normalize_issuer_public_share_management_action_report_pagination(*, limit: int | None = None, offset: int = 0) -> tuple[int, int]:
    resolved_limit = 20 if limit is None else limit
    resolved_offset = offset
    if resolved_limit <= 0:
        raise ValueError("issuer public share management action report limit must be > 0")
    if resolved_limit > _MAX_ISSUER_ACTION_REPORT_PAGE_LIMIT:
        raise ValueError(f"issuer public share management action report limit exceeds bounded page limit ({_MAX_ISSUER_ACTION_REPORT_PAGE_LIMIT})")
    if resolved_offset < 0:
        raise ValueError("issuer public share management action report offset must be >= 0")
    return resolved_limit, resolved_offset


def list_issuer_public_share_management_action_reports_for_issuer(
    rows: Sequence[Mapping[str, Any]],
    issuer_user_ref: str,
    *,
    action: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[IssuerPublicShareManagementActionReportEntry, ...]:
    issuer = issuer_user_ref.strip()
    if not issuer:
        raise ValueError("issuer_user_ref must be non-empty")
    normalized_action = _normalize_issuer_management_filter_value(action, field_name="action")
    if normalized_action is not None and normalized_action not in _MANAGEMENT_OPERATIONS:
        raise ValueError("issuer public share management action report action filter is unsupported")
    entries=[]
    for row in rows:
        entry = _canonicalize_management_action_report_row(row)
        if entry.issuer_user_ref != issuer:
            continue
        if normalized_action is not None and entry.action != normalized_action:
            continue
        entries.append(entry)
    entries.sort(key=lambda entry: (entry.created_at, entry.report_id), reverse=True)
    resolved_limit, resolved_offset = normalize_issuer_public_share_management_action_report_pagination(limit=limit, offset=offset)
    return tuple(entries[resolved_offset: resolved_offset + resolved_limit])


def summarize_issuer_public_share_management_action_reports_for_issuer(
    rows: Sequence[Mapping[str, Any]],
    issuer_user_ref: str,
    *,
    action: str | None = None,
) -> IssuerPublicShareManagementActionReportSummary:
    issuer = issuer_user_ref.strip()
    if not issuer:
        raise ValueError("issuer_user_ref must be non-empty")
    normalized_action = _normalize_issuer_management_filter_value(action, field_name="action")
    if normalized_action is not None and normalized_action not in _MANAGEMENT_OPERATIONS:
        raise ValueError("issuer public share management action report action filter is unsupported")
    entries=[]
    for row in rows:
        entry = _canonicalize_management_action_report_row(row)
        if entry.issuer_user_ref != issuer:
            continue
        if normalized_action is not None and entry.action != normalized_action:
            continue
        entries.append(entry)
    return IssuerPublicShareManagementActionReportSummary(
        issuer_user_ref=issuer,
        total_report_count=len(entries),
        revoke_report_count=sum(1 for entry in entries if entry.action == "revoke"),
        extend_report_count=sum(1 for entry in entries if entry.action == "extend_expiration"),
        archive_report_count=sum(1 for entry in entries if entry.action == "archive"),
        delete_report_count=sum(1 for entry in entries if entry.action == "delete"),
        total_requested_share_count=sum(len(entry.requested_share_ids) for entry in entries),
        total_affected_share_count=sum(entry.affected_share_count for entry in entries),
        latest_report_at=max((entry.created_at for entry in entries), default=None),
    )


def summarize_issuer_public_share_governance_for_issuer(
    share_sources: Sequence[str | Path | dict[str, Any]],
    action_report_rows: Sequence[Mapping[str, Any]],
    issuer_user_ref: str,
    *,
    now_iso: str | None = None,
    recent_action_report_limit: int = _DEFAULT_RECENT_GOVERNANCE_ACTION_REPORT_LIMIT,
) -> IssuerPublicShareGovernanceSummary:
    issuer = issuer_user_ref.strip()
    if not issuer:
        raise ValueError("issuer_user_ref must be non-empty")
    if recent_action_report_limit <= 0:
        raise ValueError("recent_action_report_limit must be > 0")
    if recent_action_report_limit > _MAX_ISSUER_ACTION_REPORT_PAGE_LIMIT:
        raise ValueError(
            f"recent_action_report_limit exceeds bounded page limit ({_MAX_ISSUER_ACTION_REPORT_PAGE_LIMIT})"
        )
    inventory_summary = summarize_public_nex_link_shares_for_issuer(share_sources, issuer, now_iso=now_iso)
    action_report_summary = summarize_issuer_public_share_management_action_reports_for_issuer(action_report_rows, issuer)
    recent_action_reports = list_issuer_public_share_management_action_reports_for_issuer(
        action_report_rows,
        issuer,
        limit=recent_action_report_limit,
        offset=0,
    )
    return IssuerPublicShareGovernanceSummary(
        issuer_user_ref=issuer,
        total_share_count=inventory_summary.total_share_count,
        active_share_count=inventory_summary.active_share_count,
        expired_share_count=inventory_summary.expired_share_count,
        revoked_share_count=inventory_summary.revoked_share_count,
        archived_share_count=inventory_summary.archived_share_count,
        working_save_share_count=inventory_summary.working_save_share_count,
        commit_snapshot_share_count=inventory_summary.commit_snapshot_share_count,
        runnable_share_count=inventory_summary.runnable_share_count,
        checkoutable_share_count=inventory_summary.checkoutable_share_count,
        total_action_report_count=action_report_summary.total_report_count,
        revoke_action_report_count=action_report_summary.revoke_report_count,
        extend_action_report_count=action_report_summary.extend_report_count,
        archive_action_report_count=action_report_summary.archive_report_count,
        delete_action_report_count=action_report_summary.delete_report_count,
        latest_created_at=inventory_summary.latest_created_at,
        latest_updated_at=inventory_summary.latest_updated_at,
        latest_audit_event_at=inventory_summary.latest_audit_event_at,
        latest_action_report_at=action_report_summary.latest_report_at,
        recent_action_reports=recent_action_reports,
    )


def save_public_nex_link_share_file(
    model_or_data: Any,
    destination: str | Path,
    *,
    share_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    lifecycle_state: ShareLifecycleState = "active",
    created_at: str | None = None,
    updated_at: str | None = None,
    expires_at: str | None = None,
    issued_by_user_ref: str | None = None,
    archived: bool = False,
    archived_at: str | None = None,
) -> Path:
    path = Path(destination)
    payload = export_public_nex_link_share(model_or_data, share_id=share_id, title=title, summary=summary, lifecycle_state=lifecycle_state, created_at=created_at, updated_at=updated_at, expires_at=expires_at, issued_by_user_ref=issued_by_user_ref, archived=archived, archived_at=archived_at)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


__all__ = [
    "get_public_nex_share_boundary",
    "is_public_nex_link_share_payload",
    "extract_public_nex_link_share_artifact",
    "export_public_nex_link_share",
    "load_public_nex_link_share",
    "describe_public_nex_link_share",
    "list_public_nex_link_share_audit_history",
    "list_public_nex_link_shares_for_issuer",
    "summarize_public_nex_link_shares_for_issuer",
    "normalize_issuer_public_share_management_pagination",
    "build_issuer_public_share_management_action_report",
    "normalize_issuer_public_share_management_action_report_pagination",
    "list_issuer_public_share_management_action_reports_for_issuer",
    "summarize_issuer_public_share_management_action_reports_for_issuer",
    "summarize_issuer_public_share_governance_for_issuer",
    "revoke_public_nex_link_shares_for_issuer",
    "extend_public_nex_link_shares_for_issuer_expiration",
    "archive_public_nex_link_shares_for_issuer",
    "delete_public_nex_link_shares_for_issuer",
    "update_public_nex_link_share_lifecycle",
    "revoke_public_nex_link_share",
    "extend_public_nex_link_share_expiration",
    "update_public_nex_link_share_archive",
    "save_public_nex_link_share_file",
    "ensure_public_nex_link_share_operation_allowed",
]
