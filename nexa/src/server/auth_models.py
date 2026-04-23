from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


_REQUEST_ACTION_ROLE_FAMILIES: dict[str, tuple[str, ...]] = {
    "read": ("owner", "admin", "editor", "collaborator", "reviewer", "viewer"),
    "view": ("owner", "admin", "editor", "collaborator", "reviewer", "viewer"),
    "status": ("owner", "admin", "editor", "collaborator", "reviewer", "viewer"),
    "result": ("owner", "admin", "editor", "collaborator", "reviewer", "viewer"),
    "history": ("owner", "admin", "editor", "collaborator", "reviewer", "viewer"),
    "launch": ("owner", "admin", "editor", "collaborator"),
    "run": ("owner", "admin", "editor", "collaborator"),
    "execute": ("owner", "admin", "editor", "collaborator"),
    "write": ("owner", "admin", "editor", "collaborator"),
    "update": ("owner", "admin", "editor", "collaborator"),
    "review": ("owner", "admin", "reviewer"),
    "approve": ("owner", "admin", "reviewer"),
    "manage": ("owner", "admin"),
    "delete": ("owner", "admin"),
}


@dataclass(frozen=True)
class AuthenticatedIdentity:
    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    organization_refs: tuple[str, ...] = ()
    role_refs: tuple[str, ...] = ()
    provider_name: str = "clerk"
    provider_subject_ref: str = ""

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("AuthenticatedIdentity.user_id must be non-empty")
        if not self.provider_name:
            raise ValueError("AuthenticatedIdentity.provider_name must be non-empty")
        if not self.provider_subject_ref:
            raise ValueError("AuthenticatedIdentity.provider_subject_ref must be non-empty")


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    authenticated_user_id: str
    issued_at: Optional[int] = None
    expires_at: Optional[int] = None
    is_valid: bool = False
    provider_name: str = "clerk"

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("SessionContext.session_id must be non-empty")
        if not self.authenticated_user_id:
            raise ValueError("SessionContext.authenticated_user_id must be non-empty")
        if not self.provider_name:
            raise ValueError("SessionContext.provider_name must be non-empty")
        if self.issued_at is not None and self.issued_at < 0:
            raise ValueError("SessionContext.issued_at must be >= 0 when provided")
        if self.expires_at is not None and self.expires_at < 0:
            raise ValueError("SessionContext.expires_at must be >= 0 when provided")


@dataclass(frozen=True)
class AuthorizationInput:
    user_id: str
    workspace_id: str
    requested_action: str
    role_context: tuple[str, ...] = ()
    run_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("AuthorizationInput.user_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("AuthorizationInput.workspace_id must be non-empty")
        if not self.requested_action:
            raise ValueError("AuthorizationInput.requested_action must be non-empty")

    @property
    def normalized_action(self) -> str:
        return self.requested_action.strip().lower()

    @property
    def allowed_roles(self) -> tuple[str, ...]:
        return _REQUEST_ACTION_ROLE_FAMILIES.get(self.normalized_action, ("owner", "admin"))


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str
    resolved_role: Optional[str] = None
    scope_ref: Optional[str] = None


@dataclass(frozen=True)
class RequestAuthContext:
    auth_context_ref: str
    authenticated_identity: Optional[AuthenticatedIdentity] = None
    session_context: Optional[SessionContext] = None
    request_id: Optional[str] = None
    authorization_scheme: Optional[str] = None
    bearer_token_present: bool = False
    remote_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.auth_context_ref:
            raise ValueError("RequestAuthContext.auth_context_ref must be non-empty")
        if not isinstance(self.request_metadata, dict):
            raise TypeError("RequestAuthContext.request_metadata must be a dict")

    @property
    def is_authenticated(self) -> bool:
        return bool(
            self.authenticated_identity is not None
            and self.session_context is not None
            and self.session_context.is_valid
        )

    @property
    def requested_by_user_ref(self) -> Optional[str]:
        if self.authenticated_identity is None:
            return None
        return self.authenticated_identity.user_id


@dataclass(frozen=True)
class WorkspaceAuthorizationContext:
    workspace_id: str
    owner_user_ref: Optional[str] = None
    collaborator_user_refs: tuple[str, ...] = ()
    viewer_user_refs: tuple[str, ...] = ()
    reviewer_user_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("WorkspaceAuthorizationContext.workspace_id must be non-empty")


@dataclass(frozen=True)
class RunAuthorizationContext:
    run_id: str
    workspace_context: WorkspaceAuthorizationContext
    run_owner_user_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("RunAuthorizationContext.run_id must be non-empty")
