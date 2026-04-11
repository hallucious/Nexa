from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

ProviderHealthReadFailureFamily = Literal["product_read_failure", "workspace_not_found", "provider_not_supported"]
ProviderHealthSeverity = Literal["blocked", "warning", "info"]
ProviderBindingHealthStatus = Literal["healthy", "warning", "blocked", "disabled", "missing"]
ProviderSecretResolutionStatus = Literal["not_checked", "resolved", "missing", "error"]

_ALLOWED_FAILURE_FAMILIES = {"product_read_failure", "workspace_not_found", "provider_not_supported"}
_ALLOWED_FINDING_SEVERITIES = {"blocked", "warning", "info"}
_ALLOWED_HEALTH_STATUSES = {"healthy", "warning", "blocked", "disabled", "missing"}
_ALLOWED_SECRET_RESOLUTION_STATUSES = {"not_checked", "resolved", "missing", "error"}


@dataclass(frozen=True)
class ProductProviderHealthFindingView:
    severity: str
    reason_code: str
    message: str
    field_name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.severity not in _ALLOWED_FINDING_SEVERITIES:
            raise ValueError(f"Unsupported ProductProviderHealthFindingView.severity: {self.severity}")
        if not self.reason_code:
            raise ValueError("ProductProviderHealthFindingView.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductProviderHealthFindingView.message must be non-empty")


@dataclass(frozen=True)
class ProductProviderHealthLinks:
    binding: str
    upsert: str
    catalog: str

    def __post_init__(self) -> None:
        for field_name in ("binding", "upsert", "catalog"):
            if not getattr(self, field_name):
                raise ValueError(f"ProductProviderHealthLinks.{field_name} must be non-empty")


@dataclass(frozen=True)
class ProductProviderBindingHealthView:
    workspace_id: str
    provider_key: str
    provider_family: str
    display_name: str
    health_status: str
    binding_present: bool
    enabled: bool
    credential_source: Optional[str] = None
    default_model_ref: Optional[str] = None
    allowed_model_ref_count: int = 0
    secret_ref_present: bool = False
    secret_authority: Optional[str] = None
    secret_resolution_status: str = "not_checked"
    blocked_count: int = 0
    warning_count: int = 0
    findings: tuple[ProductProviderHealthFindingView, ...] = ()
    links: ProductProviderHealthLinks = field(default_factory=lambda: ProductProviderHealthLinks(
        binding="/placeholder/binding",
        upsert="/placeholder/upsert",
        catalog="/api/providers/catalog",
    ))

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("ProductProviderBindingHealthView.workspace_id must be non-empty")
        if not self.provider_key:
            raise ValueError("ProductProviderBindingHealthView.provider_key must be non-empty")
        if not self.provider_family:
            raise ValueError("ProductProviderBindingHealthView.provider_family must be non-empty")
        if not self.display_name:
            raise ValueError("ProductProviderBindingHealthView.display_name must be non-empty")
        if self.health_status not in _ALLOWED_HEALTH_STATUSES:
            raise ValueError(f"Unsupported ProductProviderBindingHealthView.health_status: {self.health_status}")
        if self.secret_resolution_status not in _ALLOWED_SECRET_RESOLUTION_STATUSES:
            raise ValueError(f"Unsupported ProductProviderBindingHealthView.secret_resolution_status: {self.secret_resolution_status}")
        if self.allowed_model_ref_count < 0:
            raise ValueError("ProductProviderBindingHealthView.allowed_model_ref_count must be >= 0")
        if self.blocked_count < 0:
            raise ValueError("ProductProviderBindingHealthView.blocked_count must be >= 0")
        if self.warning_count < 0:
            raise ValueError("ProductProviderBindingHealthView.warning_count must be >= 0")


@dataclass(frozen=True)
class ProductWorkspaceProviderHealthResponse:
    workspace_id: str
    returned_count: int
    providers: tuple[ProductProviderBindingHealthView, ...] = ()
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceProviderHealthResponse.workspace_id must be non-empty")
        if self.returned_count < 0:
            raise ValueError("ProductWorkspaceProviderHealthResponse.returned_count must be >= 0")


@dataclass(frozen=True)
class ProductProviderHealthRejectedResponse:
    failure_family: ProviderHealthReadFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    provider_key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductProviderHealthRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductProviderHealthRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductProviderHealthRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class ProviderHealthListOutcome:
    response: Optional[ProductWorkspaceProviderHealthResponse] = None
    rejected: Optional[ProductProviderHealthRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class ProviderHealthDetailOutcome:
    response: Optional[ProductProviderBindingHealthView] = None
    rejected: Optional[ProductProviderHealthRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
