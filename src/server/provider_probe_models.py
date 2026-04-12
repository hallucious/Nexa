from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

ProviderProbeFailureFamily = Literal["product_probe_failure", "workspace_not_found", "provider_not_supported"]
ProviderProbeSeverity = Literal["blocked", "warning", "info"]
ProviderProbeStatus = Literal["reachable", "warning", "failed", "blocked", "disabled", "missing"]
ProviderConnectivityState = Literal["ok", "provider_error", "auth_failed", "transport_error", "timeout", "unknown", "not_checked"]
ProviderSecretResolutionStatus = Literal["not_checked", "resolved", "missing", "error"]

_ALLOWED_FAILURE_FAMILIES = {"product_probe_failure", "workspace_not_found", "provider_not_supported"}
_ALLOWED_FINDING_SEVERITIES = {"blocked", "warning", "info"}
_ALLOWED_PROBE_STATUSES = {"reachable", "warning", "failed", "blocked", "disabled", "missing"}
_ALLOWED_CONNECTIVITY_STATES = {"ok", "provider_error", "auth_failed", "transport_error", "timeout", "unknown", "not_checked"}
_ALLOWED_SECRET_RESOLUTION_STATUSES = {"not_checked", "resolved", "missing", "error"}


@dataclass(frozen=True)
class ProductProviderProbeFindingView:
    severity: str
    reason_code: str
    message: str
    field_name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.severity not in _ALLOWED_FINDING_SEVERITIES:
            raise ValueError(f"Unsupported ProductProviderProbeFindingView.severity: {self.severity}")
        if not self.reason_code:
            raise ValueError("ProductProviderProbeFindingView.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductProviderProbeFindingView.message must be non-empty")


@dataclass(frozen=True)
class ProductProviderProbeLinks:
    binding: str
    health: str
    catalog: str

    def __post_init__(self) -> None:
        for field_name in ("binding", "health", "catalog"):
            if not getattr(self, field_name):
                raise ValueError(f"ProductProviderProbeLinks.{field_name} must be non-empty")


@dataclass(frozen=True)
class ProductProviderProbeRequest:
    model_ref: Optional[str] = None
    probe_message: Optional[str] = None
    timeout_ms: Optional[int] = None

    def __post_init__(self) -> None:
        if self.model_ref is not None and not str(self.model_ref).strip():
            raise ValueError("ProductProviderProbeRequest.model_ref must be non-empty when provided")
        if self.probe_message is not None and not str(self.probe_message).strip():
            raise ValueError("ProductProviderProbeRequest.probe_message must be non-empty when provided")
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("ProductProviderProbeRequest.timeout_ms must be > 0 when provided")


@dataclass(frozen=True)
class ProviderProbeExecutionInput:
    workspace_id: str
    provider_key: str
    provider_family: str
    display_name: str
    secret_ref: str
    secret_authority: Optional[str] = None
    default_model_ref: Optional[str] = None
    allowed_model_refs: tuple[str, ...] = ()
    requested_model_ref: Optional[str] = None
    probe_message: Optional[str] = None
    timeout_ms: Optional[int] = None
    now_iso: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in ("workspace_id", "provider_key", "provider_family", "display_name", "secret_ref"):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"ProviderProbeExecutionInput.{field_name} must be non-empty")


@dataclass(frozen=True)
class ProviderProbeExecutionResult:
    probe_status: str
    connectivity_state: str = "not_checked"
    message: Optional[str] = None
    reason_code: Optional[str] = None
    effective_model_ref: Optional[str] = None
    round_trip_latency_ms: Optional[int] = None
    provider_account_ref: Optional[str] = None
    findings: tuple[ProductProviderProbeFindingView, ...] = ()

    def __post_init__(self) -> None:
        if self.probe_status not in _ALLOWED_PROBE_STATUSES:
            raise ValueError(f"Unsupported ProviderProbeExecutionResult.probe_status: {self.probe_status}")
        if self.connectivity_state not in _ALLOWED_CONNECTIVITY_STATES:
            raise ValueError(f"Unsupported ProviderProbeExecutionResult.connectivity_state: {self.connectivity_state}")
        if self.round_trip_latency_ms is not None and self.round_trip_latency_ms < 0:
            raise ValueError("ProviderProbeExecutionResult.round_trip_latency_ms must be >= 0 when provided")


@dataclass(frozen=True)
class ProductProviderProbeResponse:
    workspace_id: str
    provider_key: str
    provider_family: str
    display_name: str
    probe_status: str
    connectivity_state: str
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    credential_source: Optional[str] = None
    secret_authority: Optional[str] = None
    secret_resolution_status: str = "not_checked"
    effective_model_ref: Optional[str] = None
    provider_account_ref: Optional[str] = None
    round_trip_latency_ms: Optional[int] = None
    message: Optional[str] = None
    findings: tuple[ProductProviderProbeFindingView, ...] = ()
    links: ProductProviderProbeLinks = field(default_factory=lambda: ProductProviderProbeLinks(
        binding="/placeholder/binding",
        health="/placeholder/health",
        catalog="/api/providers/catalog",
    ))

    def __post_init__(self) -> None:
        for field_name in ("workspace_id", "provider_key", "provider_family", "display_name"):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"ProductProviderProbeResponse.{field_name} must be non-empty")
        if self.probe_status not in _ALLOWED_PROBE_STATUSES:
            raise ValueError(f"Unsupported ProductProviderProbeResponse.probe_status: {self.probe_status}")
        if self.connectivity_state not in _ALLOWED_CONNECTIVITY_STATES:
            raise ValueError(f"Unsupported ProductProviderProbeResponse.connectivity_state: {self.connectivity_state}")
        if self.secret_resolution_status not in _ALLOWED_SECRET_RESOLUTION_STATUSES:
            raise ValueError(f"Unsupported ProductProviderProbeResponse.secret_resolution_status: {self.secret_resolution_status}")
        if self.round_trip_latency_ms is not None and self.round_trip_latency_ms < 0:
            raise ValueError("ProductProviderProbeResponse.round_trip_latency_ms must be >= 0 when provided")


@dataclass(frozen=True)
class ProductProviderProbeRejectedResponse:
    failure_family: ProviderProbeFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    provider_key: Optional[str] = None

    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductProviderProbeRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductProviderProbeRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductProviderProbeRejectedResponse.message must be non-empty")

@dataclass(frozen=True)
class ProviderProbeOutcome:
    response: Optional[ProductProviderProbeResponse] = None
    rejected: Optional[ProductProviderProbeRejectedResponse] = None
    persisted_probe_row: Optional[dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
