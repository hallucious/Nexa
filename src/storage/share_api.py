from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.contracts.nex_contract import (
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
_MANAGEMENT_OPERATIONS: tuple[str, ...] = ("revoke", "extend_expiration")

_ALLOWED_AUDIT_EVENT_TYPES: tuple[ShareAuditEventType, ...] = ("created", "expiration_extended", "revoked")
_MAX_ISSUER_MANAGEMENT_ACTION_SHARES = 20
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


def list_public_nex_link_shares_for_issuer(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    *,
    now_iso: str | None = None,
) -> tuple[IssuerPublicShareManagementEntry, ...]:
    issuer = issuer_user_ref.strip()
    if not issuer:
        raise ValueError("issuer_user_ref must be non-empty")
    resolved: list[IssuerPublicShareManagementEntry] = []
    for source in sources:
        descriptor = describe_public_nex_link_share(source, now_iso=now_iso)
        if descriptor.issued_by_user_ref != issuer:
            continue
        resolved.append(IssuerPublicShareManagementEntry(
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
        ))
    resolved.sort(key=lambda entry: (
        entry.updated_at or "",
        entry.created_at or "",
        entry.last_audit_event_at or "",
        entry.share_id,
    ), reverse=True)
    return tuple(resolved)


def summarize_public_nex_link_shares_for_issuer(
    sources: list[str | Path | dict[str, Any]] | tuple[str | Path | dict[str, Any], ...],
    issuer_user_ref: str,
    *,
    now_iso: str | None = None,
) -> IssuerPublicShareManagementSummary:
    entries = list_public_nex_link_shares_for_issuer(sources, issuer_user_ref, now_iso=now_iso)
    active_count = sum(1 for entry in entries if entry.lifecycle_state == "active")
    expired_count = sum(1 for entry in entries if entry.lifecycle_state == "expired")
    revoked_count = sum(1 for entry in entries if entry.lifecycle_state == "revoked")
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
) -> Path:
    path = Path(destination)
    payload = export_public_nex_link_share(model_or_data, share_id=share_id, title=title, summary=summary, lifecycle_state=lifecycle_state, created_at=created_at, updated_at=updated_at, expires_at=expires_at, issued_by_user_ref=issued_by_user_ref)
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
    "revoke_public_nex_link_shares_for_issuer",
    "extend_public_nex_link_shares_for_issuer_expiration",
    "update_public_nex_link_share_lifecycle",
    "revoke_public_nex_link_share",
    "extend_public_nex_link_share_expiration",
    "save_public_nex_link_share_file",
    "ensure_public_nex_link_share_operation_allowed",
]
