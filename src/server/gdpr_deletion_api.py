from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from src.server.gdpr_deletion_runtime import (
    AuditWriter,
    GdprDeletionPolicyError,
    GdprDeletionRequest,
    IdentityDeleter,
    MutableRowDeleter,
    ObjectStorageDeleter,
    TtlRowCleaner,
    build_gdpr_deletion_plan,
    execute_gdpr_deletion_plan,
)
from src.server.observability_payload_guard import sanitize_observability_payload

GDPR_DELETION_PERMISSION = "admin.gdpr_delete_user"
GDPR_DELETION_DENIED_REASON = "gdpr_deletion_permission_denied"
GDPR_DELETION_POLICY_DENIED_REASON = "gdpr_deletion_policy_denied"
GDPR_DELETION_ROUTE = "/api/admin/privacy/user-deletions"

_ALLOWED_ROLE_NAMES = frozenset({"owner", "admin", "operator"})
_PERMISSION_KEYS = ("permissions", "ops_permissions", "admin_permissions", "scopes", "scope")
_ROLE_KEYS = ("role", "roles", "actor_role", "actor_roles")

SessionClaimsResolver = Callable[[Request], Mapping[str, Any] | None]


@dataclass(frozen=True)
class GdprDeletionAuthorizationResult:
    allowed: bool
    actor_ref: str | None = None
    reason: str | None = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"allowed": self.allowed}
        if self.actor_ref:
            payload["actor_ref"] = self.actor_ref
        if self.reason:
            payload["reason"] = self.reason
        return payload


def build_gdpr_deletion_router(
    *,
    mutable_row_deleter: MutableRowDeleter,
    object_storage_deleter: ObjectStorageDeleter,
    audit_writer: AuditWriter,
    identity_deleter: IdentityDeleter | None = None,
    ttl_row_cleaner: TtlRowCleaner | None = None,
    session_claims_resolver: SessionClaimsResolver | None = None,
) -> APIRouter:
    """Build the internal/admin GDPR deletion API router.

    The route is deliberately not mounted by public/workspace route families. It
    requires an explicit admin deletion permission before plan construction,
    object lookup, row deletion, or model/source work can occur.
    """

    router = APIRouter()
    resolve_claims = session_claims_resolver or default_gdpr_session_claims_resolver

    @router.post(GDPR_DELETION_ROUTE)
    async def post_gdpr_user_deletion(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> JSONResponse:
        claims = resolve_claims(request)
        auth = authorize_gdpr_deletion(claims)
        if not auth.allowed:
            _write_gdpr_route_audit(
                audit_writer,
                {
                    "event_type": "gdpr_deletion_denied",
                    "route": GDPR_DELETION_ROUTE,
                    "actor_ref": auth.actor_ref,
                    "reason": auth.reason or GDPR_DELETION_DENIED_REASON,
                    "source_lookup_attempted": False,
                    "deletion_attempted": False,
                    "model_invocation_attempted": False,
                },
            )
            return JSONResponse(status_code=403, content={"status": "denied", "reason": auth.reason or GDPR_DELETION_DENIED_REASON})

        body = dict(payload or {})
        try:
            deletion_request = GdprDeletionRequest(
                user_ref=str(body.get("user_ref") or ""),
                requested_by_ref=auth.actor_ref or "actor_unknown",
                deletion_request_id=str(body.get("deletion_request_id") or "").strip() or None,
                object_storage_refs=_as_text_tuple(body.get("object_storage_refs")),
                mutable_table_names=_as_text_tuple(body.get("mutable_table_names")) or GdprDeletionRequest.__dataclass_fields__["mutable_table_names"].default,
                ttl_table_names=_as_text_tuple(body.get("ttl_table_names")) or GdprDeletionRequest.__dataclass_fields__["ttl_table_names"].default,
                raw_identity_hint=str(body.get("raw_identity_hint") or "").strip() or None,
                reason=str(body.get("reason") or "user_requested_deletion"),
            )
            plan = build_gdpr_deletion_plan(deletion_request)
        except GdprDeletionPolicyError as exc:
            _write_gdpr_route_audit(
                audit_writer,
                {
                    "event_type": "gdpr_deletion_policy_denied",
                    "route": GDPR_DELETION_ROUTE,
                    "actor_ref": auth.actor_ref,
                    "reason": GDPR_DELETION_POLICY_DENIED_REASON,
                    "error_type": exc.__class__.__name__,
                    "source_lookup_attempted": False,
                    "deletion_attempted": False,
                    "model_invocation_attempted": False,
                },
            )
            return JSONResponse(status_code=400, content={"status": "denied", "reason": GDPR_DELETION_POLICY_DENIED_REASON})

        result = execute_gdpr_deletion_plan(
            plan,
            mutable_row_deleter=mutable_row_deleter,
            object_storage_deleter=object_storage_deleter,
            audit_writer=audit_writer,
            identity_deleter=identity_deleter,
            ttl_row_cleaner=ttl_row_cleaner,
        )
        status_code = 200 if result.status == "completed" else 500
        return JSONResponse(status_code=status_code, content=result.as_payload())

    return router


def authorize_gdpr_deletion(session_claims: Mapping[str, Any] | None) -> GdprDeletionAuthorizationResult:
    if not isinstance(session_claims, Mapping):
        return GdprDeletionAuthorizationResult(allowed=False, reason=GDPR_DELETION_DENIED_REASON)
    actor_ref = _opaque_actor_ref(session_claims)
    permissions = _extract_claim_values(session_claims, _PERMISSION_KEYS)
    roles = _extract_claim_values(session_claims, _ROLE_KEYS)
    if GDPR_DELETION_PERMISSION in permissions and roles.intersection(_ALLOWED_ROLE_NAMES):
        return GdprDeletionAuthorizationResult(allowed=True, actor_ref=actor_ref)
    return GdprDeletionAuthorizationResult(allowed=False, actor_ref=actor_ref, reason=GDPR_DELETION_DENIED_REASON)


def default_gdpr_session_claims_resolver(request: Request) -> Mapping[str, Any] | None:
    state_claims = getattr(request.state, "session_claims", None)
    if isinstance(state_claims, Mapping):
        return dict(state_claims)
    header_value = request.headers.get("x-nexa-session-claims")
    if not header_value:
        return None
    try:
        parsed = json.loads(header_value)
    except json.JSONDecodeError:
        return None
    return dict(parsed) if isinstance(parsed, Mapping) else None


def _write_gdpr_route_audit(audit_writer: AuditWriter, payload: Mapping[str, Any]) -> None:
    try:
        audit_writer(sanitize_observability_payload(dict(payload)))
    except Exception:
        return


def _extract_claim_values(claims: Mapping[str, Any], keys: Sequence[str]) -> set[str]:
    values: set[str] = set()
    for key in keys:
        raw = claims.get(key)
        if isinstance(raw, str):
            for item in raw.replace(",", " ").split():
                text = item.strip().lower()
                if text:
                    values.add(text)
        elif isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray)):
            for item in raw:
                text = str(item or "").strip().lower()
                if text:
                    values.add(text)
    return values


def _opaque_actor_ref(claims: Mapping[str, Any]) -> str:
    explicit = str(claims.get("user_ref") or claims.get("actor_ref") or "").strip()
    if explicit and "@" not in explicit.lower() and "clerk" not in explicit.lower() and "stripe" not in explicit.lower():
        return explicit
    raw_identity = str(claims.get("sub") or claims.get("user_id") or claims.get("subject") or "anonymous").strip() or "anonymous"
    digest = sha256(raw_identity.encode("utf-8")).hexdigest()[:16]
    return f"actor_{digest}"


def _as_text_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        raw_items = [str(item or "") for item in value]
    else:
        raw_items = [str(value or "")]
    normalized = [item.strip() for item in raw_items if item.strip()]
    return tuple(dict.fromkeys(normalized))


__all__ = [
    "GDPR_DELETION_DENIED_REASON",
    "GDPR_DELETION_PERMISSION",
    "GDPR_DELETION_POLICY_DENIED_REASON",
    "GDPR_DELETION_ROUTE",
    "GdprDeletionAuthorizationResult",
    "authorize_gdpr_deletion",
    "build_gdpr_deletion_router",
    "default_gdpr_session_claims_resolver",
]
