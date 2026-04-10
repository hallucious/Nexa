from __future__ import annotations

from dataclasses import asdict
from time import time
from typing import Any, Iterable, Mapping, Optional

from src.server.auth_models import (
    AuthenticatedIdentity,
    AuthorizationDecision,
    AuthorizationInput,
    RequestAuthContext,
    RunAuthorizationContext,
    SessionContext,
    WorkspaceAuthorizationContext,
)


def _as_header_map(headers: Mapping[str, Any] | None) -> dict[str, str]:
    if headers is None:
        return {}
    return {str(key).lower(): str(value) for key, value in headers.items() if value is not None}


def _extract_authorization_scheme(auth_header: str | None) -> tuple[Optional[str], bool]:
    if not auth_header:
        return None, False
    pieces = auth_header.strip().split(None, 1)
    if not pieces:
        return None, False
    scheme = pieces[0].lower()
    token_present = len(pieces) == 2 and bool(pieces[1].strip())
    return scheme, token_present


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _coerce_str_list(*values: Any) -> tuple[str, ...]:
    collected: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                collected.append(stripped)
            continue
        if isinstance(value, Mapping):
            for key in ("id", "ref", "slug", "name"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    collected.append(candidate.strip())
                    break
            continue
        if isinstance(value, Iterable):
            for item in value:
                collected.extend(_coerce_str_list(item))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in collected:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return tuple(deduped)


class ClerkAuthAdapter:
    provider_name = "clerk"

    @classmethod
    def normalize_identity(cls, session_claims: Mapping[str, Any]) -> AuthenticatedIdentity:
        user_id = str(
            session_claims.get("user_id")
            or session_claims.get("sub")
            or session_claims.get("subject")
            or ""
        ).strip()
        if not user_id:
            raise ValueError("ClerkAuthAdapter requires a user subject in session_claims")

        email = session_claims.get("email") or session_claims.get("primary_email_address")
        display_name = (
            session_claims.get("name")
            or session_claims.get("display_name")
            or session_claims.get("username")
            or session_claims.get("first_name")
        )
        organization_refs = _coerce_str_list(
            session_claims.get("org_id"),
            session_claims.get("org_ids"),
            session_claims.get("organization_refs"),
            session_claims.get("organizations"),
        )
        role_refs = _coerce_str_list(
            session_claims.get("org_role"),
            session_claims.get("roles"),
            session_claims.get("role"),
        )
        return AuthenticatedIdentity(
            user_id=user_id,
            email=str(email).strip() if isinstance(email, str) and email.strip() else None,
            display_name=str(display_name).strip() if isinstance(display_name, str) and display_name.strip() else None,
            organization_refs=organization_refs,
            role_refs=role_refs,
            provider_name=cls.provider_name,
            provider_subject_ref=user_id,
        )

    @classmethod
    def normalize_session(
        cls,
        session_claims: Mapping[str, Any],
        *,
        authenticated_user_id: str,
        now_epoch_s: int | None = None,
    ) -> SessionContext:
        session_id = str(
            session_claims.get("session_id")
            or session_claims.get("sid")
            or session_claims.get("session")
            or ""
        ).strip()
        if not session_id:
            raise ValueError("ClerkAuthAdapter requires a session id in session_claims")

        issued_at = _safe_int(session_claims.get("iat") or session_claims.get("issued_at"))
        expires_at = _safe_int(session_claims.get("exp") or session_claims.get("expires_at"))
        now_epoch_s = int(time()) if now_epoch_s is None else int(now_epoch_s)
        is_valid = bool(expires_at is None or expires_at > now_epoch_s)
        if issued_at is not None and issued_at > now_epoch_s:
            is_valid = False

        return SessionContext(
            session_id=session_id,
            authenticated_user_id=authenticated_user_id,
            issued_at=issued_at,
            expires_at=expires_at,
            is_valid=is_valid,
            provider_name=cls.provider_name,
        )

    @classmethod
    def build_request_auth_context(
        cls,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        now_epoch_s: int | None = None,
    ) -> RequestAuthContext:
        header_map = _as_header_map(headers)
        authorization_scheme, bearer_token_present = _extract_authorization_scheme(header_map.get("authorization"))
        request_id = header_map.get("x-request-id")
        remote_address = header_map.get("x-forwarded-for") or header_map.get("x-real-ip")
        user_agent = header_map.get("user-agent")

        metadata = {
            "request_id": request_id,
            "remote_address": remote_address,
            "user_agent": user_agent,
            "provider_name": cls.provider_name,
        }

        if not session_claims:
            return RequestAuthContext(
                auth_context_ref="authctx:anonymous",
                request_id=request_id,
                authorization_scheme=authorization_scheme,
                bearer_token_present=bearer_token_present,
                remote_address=remote_address,
                user_agent=user_agent,
                request_metadata=metadata,
            )

        identity = cls.normalize_identity(session_claims)
        session = cls.normalize_session(
            session_claims,
            authenticated_user_id=identity.user_id,
            now_epoch_s=now_epoch_s,
        )
        auth_context_ref = f"authctx:{cls.provider_name}:{session.session_id}:{identity.user_id}"
        metadata["organization_refs"] = list(identity.organization_refs)
        metadata["role_refs"] = list(identity.role_refs)
        return RequestAuthContext(
            auth_context_ref=auth_context_ref,
            authenticated_identity=identity,
            session_context=session,
            request_id=request_id,
            authorization_scheme=authorization_scheme,
            bearer_token_present=bearer_token_present,
            remote_address=remote_address,
            user_agent=user_agent,
            request_metadata=metadata,
        )


class RequestAuthResolver:
    @staticmethod
    def resolve(
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        now_epoch_s: int | None = None,
    ) -> RequestAuthContext:
        return ClerkAuthAdapter.build_request_auth_context(
            headers=headers,
            session_claims=session_claims,
            now_epoch_s=now_epoch_s,
        )


class AuthorizationGate:
    @staticmethod
    def _resolve_workspace_role(
        user_id: str,
        role_context: Iterable[str],
        workspace_context: WorkspaceAuthorizationContext,
    ) -> Optional[str]:
        normalized_roles = {str(item).strip().lower() for item in role_context if str(item).strip()}
        if "admin" in normalized_roles:
            return "admin"
        if workspace_context.owner_user_ref and user_id == workspace_context.owner_user_ref:
            return "owner"
        if user_id in workspace_context.collaborator_user_refs:
            return "collaborator"
        if user_id in workspace_context.reviewer_user_refs:
            return "reviewer"
        if user_id in workspace_context.viewer_user_refs:
            return "viewer"
        for candidate in ("editor", "collaborator", "reviewer", "viewer"):
            if candidate in normalized_roles:
                return candidate
        return None

    @classmethod
    def authorize_workspace_scope(
        cls,
        auth_input: AuthorizationInput,
        workspace_context: WorkspaceAuthorizationContext,
    ) -> AuthorizationDecision:
        if auth_input.workspace_id != workspace_context.workspace_id:
            return AuthorizationDecision(
                allowed=False,
                reason_code="authorization.workspace_mismatch",
                scope_ref=workspace_context.workspace_id,
            )

        resolved_role = cls._resolve_workspace_role(
            auth_input.user_id,
            auth_input.role_context,
            workspace_context,
        )
        if resolved_role is None:
            return AuthorizationDecision(
                allowed=False,
                reason_code="authorization.workspace_forbidden",
                scope_ref=workspace_context.workspace_id,
            )
        if resolved_role not in auth_input.allowed_roles:
            return AuthorizationDecision(
                allowed=False,
                reason_code="authorization.role_insufficient",
                resolved_role=resolved_role,
                scope_ref=workspace_context.workspace_id,
            )
        return AuthorizationDecision(
            allowed=True,
            reason_code="authorization.allowed",
            resolved_role=resolved_role,
            scope_ref=workspace_context.workspace_id,
        )

    @classmethod
    def authorize_run_scope(
        cls,
        auth_input: AuthorizationInput,
        run_context: RunAuthorizationContext,
    ) -> AuthorizationDecision:
        if auth_input.run_id is not None and auth_input.run_id != run_context.run_id:
            return AuthorizationDecision(
                allowed=False,
                reason_code="authorization.run_mismatch",
                scope_ref=run_context.run_id,
            )
        if run_context.run_owner_user_ref and auth_input.user_id == run_context.run_owner_user_ref:
            return AuthorizationDecision(
                allowed=True,
                reason_code="authorization.allowed",
                resolved_role="run_owner",
                scope_ref=run_context.run_id,
            )
        workspace_decision = cls.authorize_workspace_scope(auth_input, run_context.workspace_context)
        if not workspace_decision.allowed:
            return AuthorizationDecision(
                allowed=False,
                reason_code=workspace_decision.reason_code,
                resolved_role=workspace_decision.resolved_role,
                scope_ref=run_context.run_id,
            )
        return AuthorizationDecision(
            allowed=True,
            reason_code="authorization.allowed",
            resolved_role=workspace_decision.resolved_role,
            scope_ref=run_context.run_id,
        )


def build_engine_auth_context_refs(request_auth: RequestAuthContext) -> dict[str, Optional[str]]:
    return {
        "auth_context_ref": request_auth.auth_context_ref,
        "requested_by_user_ref": request_auth.requested_by_user_ref,
    }


def describe_request_auth_context(request_auth: RequestAuthContext) -> dict[str, Any]:
    identity = asdict(request_auth.authenticated_identity) if request_auth.authenticated_identity else None
    session = asdict(request_auth.session_context) if request_auth.session_context else None
    return {
        "auth_context_ref": request_auth.auth_context_ref,
        "is_authenticated": request_auth.is_authenticated,
        "authorization_scheme": request_auth.authorization_scheme,
        "bearer_token_present": request_auth.bearer_token_present,
        "identity": identity,
        "session": session,
        "request_id": request_auth.request_id,
        "remote_address": request_auth.remote_address,
        "user_agent": request_auth.user_agent,
        "request_metadata": dict(request_auth.request_metadata),
    }
