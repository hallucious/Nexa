from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

ProviderSecretReadFailureFamily = Literal[
    "product_read_failure",
    "workspace_not_found",
]
ProviderSecretWriteFailureFamily = Literal[
    "product_write_failure",
    "workspace_not_found",
    "provider_not_supported",
]

_ALLOWED_READ_FAILURE_FAMILIES = {"product_read_failure", "workspace_not_found"}
_ALLOWED_WRITE_FAILURE_FAMILIES = {"product_write_failure", "workspace_not_found", "provider_not_supported"}
_ALLOWED_PROVIDER_STATUSES = {"configured", "missing_secret", "disabled"}
_ALLOWED_CREDENTIAL_SOURCES = {"managed"}
_ALLOWED_SCOPES = {"workspace"}


@dataclass(frozen=True)
class ProductProviderCatalogEntryView:
    provider_key: str
    provider_family: str
    display_name: str
    managed_supported: bool = True
    recommended_scope: str = "workspace"
    local_env_var_hint: Optional[str] = None
    default_secret_name_template: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.provider_key:
            raise ValueError("ProductProviderCatalogEntryView.provider_key must be non-empty")
        if not self.provider_family:
            raise ValueError("ProductProviderCatalogEntryView.provider_family must be non-empty")
        if not self.display_name:
            raise ValueError("ProductProviderCatalogEntryView.display_name must be non-empty")
        if self.recommended_scope not in _ALLOWED_SCOPES:
            raise ValueError(f"Unsupported ProductProviderCatalogEntryView.recommended_scope: {self.recommended_scope}")


@dataclass(frozen=True)
class ProductProviderCatalogResponse:
    returned_count: int
    providers: tuple[ProductProviderCatalogEntryView, ...] = ()
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.returned_count < 0:
            raise ValueError("ProductProviderCatalogResponse.returned_count must be >= 0")


@dataclass(frozen=True)
class ProductProviderBindingLinks:
    workspace: str
    upsert: str
    catalog: str

    def __post_init__(self) -> None:
        for field_name in ("workspace", "upsert", "catalog"):
            if not getattr(self, field_name):
                raise ValueError(f"ProductProviderBindingLinks.{field_name} must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceProviderBindingView:
    binding_id: str
    workspace_id: str
    provider_key: str
    provider_family: str
    display_name: str
    status: str
    enabled: bool = True
    credential_source: str = "managed"
    secret_ref: Optional[str] = None
    secret_version_ref: Optional[str] = None
    default_model_ref: Optional[str] = None
    allowed_model_refs: tuple[str, ...] = ()
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_rotated_at: Optional[str] = None
    updated_by_user_id: Optional[str] = None
    links: ProductProviderBindingLinks = field(default_factory=lambda: ProductProviderBindingLinks(
        workspace="/placeholder/workspace",
        upsert="/placeholder/upsert",
        catalog="/api/providers/catalog",
    ))

    def __post_init__(self) -> None:
        if not self.binding_id:
            raise ValueError("ProductWorkspaceProviderBindingView.binding_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceProviderBindingView.workspace_id must be non-empty")
        if not self.provider_key:
            raise ValueError("ProductWorkspaceProviderBindingView.provider_key must be non-empty")
        if not self.provider_family:
            raise ValueError("ProductWorkspaceProviderBindingView.provider_family must be non-empty")
        if not self.display_name:
            raise ValueError("ProductWorkspaceProviderBindingView.display_name must be non-empty")
        if self.status not in _ALLOWED_PROVIDER_STATUSES:
            raise ValueError(f"Unsupported ProductWorkspaceProviderBindingView.status: {self.status}")
        if self.credential_source not in _ALLOWED_CREDENTIAL_SOURCES:
            raise ValueError(f"Unsupported ProductWorkspaceProviderBindingView.credential_source: {self.credential_source}")


@dataclass(frozen=True)
class ProductWorkspaceProviderBindingsResponse:
    workspace_id: str
    returned_count: int
    bindings: tuple[ProductWorkspaceProviderBindingView, ...] = ()
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceProviderBindingsResponse.workspace_id must be non-empty")
        if self.returned_count < 0:
            raise ValueError("ProductWorkspaceProviderBindingsResponse.returned_count must be >= 0")


@dataclass(frozen=True)
class ProductProviderBindingWriteRequest:
    display_name: Optional[str] = None
    enabled: bool = True
    credential_source: str = "managed"
    secret_value: Optional[str] = None
    secret_ref_hint: Optional[str] = None
    default_model_ref: Optional[str] = None
    allowed_model_refs: tuple[str, ...] = ()
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.credential_source not in _ALLOWED_CREDENTIAL_SOURCES:
            raise ValueError(f"Unsupported ProductProviderBindingWriteRequest.credential_source: {self.credential_source}")
        if self.display_name is not None and not str(self.display_name).strip():
            raise ValueError("ProductProviderBindingWriteRequest.display_name must be non-empty when provided")
        if self.secret_value is not None and not str(self.secret_value).strip():
            raise ValueError("ProductProviderBindingWriteRequest.secret_value must be non-empty when provided")
        if self.secret_ref_hint is not None and not str(self.secret_ref_hint).strip():
            raise ValueError("ProductProviderBindingWriteRequest.secret_ref_hint must be non-empty when provided")


@dataclass(frozen=True)
class ProductProviderBindingWriteAcceptedResponse:
    status: str
    binding: ProductWorkspaceProviderBindingView
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    was_created: bool = False
    secret_rotated: bool = False
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductProviderBindingWriteAcceptedResponse.status must be non-empty")


@dataclass(frozen=True)
class ProductProviderSecretReadRejectedResponse:
    failure_family: ProviderSecretReadFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    provider_key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_READ_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductProviderSecretReadRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductProviderSecretReadRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductProviderSecretReadRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class ProductProviderSecretWriteRejectedResponse:
    failure_family: ProviderSecretWriteFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    provider_key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_WRITE_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductProviderSecretWriteRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductProviderSecretWriteRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductProviderSecretWriteRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class ProviderCatalogReadOutcome:
    response: Optional[ProductProviderCatalogResponse] = None
    rejected: Optional[ProductProviderSecretReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class ProviderBindingListOutcome:
    response: Optional[ProductWorkspaceProviderBindingsResponse] = None
    rejected: Optional[ProductProviderSecretReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class ProviderBindingWriteOutcome:
    accepted: Optional[ProductProviderBindingWriteAcceptedResponse] = None
    rejected: Optional[ProductProviderSecretWriteRejectedResponse] = None
    created_or_updated_binding_row: Optional[dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return self.accepted is not None
