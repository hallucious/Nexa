from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

ProviderProbeHistoryFailureFamily = Literal["product_read_failure", "workspace_not_found"]
ProviderProbeHistoryStatus = Literal["reachable", "warning", "failed", "blocked", "disabled", "missing"]
ProviderProbeHistoryConnectivityState = Literal["ok", "provider_error", "auth_failed", "transport_error", "timeout", "unknown", "not_checked"]

_ALLOWED_FAILURE_FAMILIES = {"product_read_failure", "workspace_not_found"}
_ALLOWED_PROBE_STATUSES = {"reachable", "warning", "failed", "blocked", "disabled", "missing"}
_ALLOWED_CONNECTIVITY_STATES = {"ok", "provider_error", "auth_failed", "transport_error", "timeout", "unknown", "not_checked"}


@dataclass(frozen=True)
class ProductProviderProbeHistoryLinks:
    binding: str
    health: str
    probe: str

    def __post_init__(self) -> None:
        for field_name in ("binding", "health", "probe"):
            if not getattr(self, field_name):
                raise ValueError(f"ProductProviderProbeHistoryLinks.{field_name} must be non-empty")


@dataclass(frozen=True)
class ProviderProbeHistoryRecord:
    probe_event_id: str
    workspace_id: str
    provider_key: str
    provider_family: str
    display_name: str
    probe_status: str
    connectivity_state: str
    occurred_at: str
    binding_id: Optional[str] = None
    secret_resolution_status: Optional[str] = None
    requested_model_ref: Optional[str] = None
    effective_model_ref: Optional[str] = None
    round_trip_latency_ms: Optional[int] = None
    requested_by_user_id: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in (
            "probe_event_id",
            "workspace_id",
            "provider_key",
            "provider_family",
            "display_name",
            "occurred_at",
        ):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"ProviderProbeHistoryRecord.{field_name} must be non-empty")
        if self.probe_status not in _ALLOWED_PROBE_STATUSES:
            raise ValueError(f"Unsupported ProviderProbeHistoryRecord.probe_status: {self.probe_status}")
        if self.connectivity_state not in _ALLOWED_CONNECTIVITY_STATES:
            raise ValueError(f"Unsupported ProviderProbeHistoryRecord.connectivity_state: {self.connectivity_state}")
        if self.round_trip_latency_ms is not None and self.round_trip_latency_ms < 0:
            raise ValueError("ProviderProbeHistoryRecord.round_trip_latency_ms must be >= 0 when provided")

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> Optional["ProviderProbeHistoryRecord"]:
        probe_event_id = str(row.get("probe_event_id") or row.get("probe_id") or "").strip()
        workspace_id = str(row.get("workspace_id") or "").strip()
        provider_key = str(row.get("provider_key") or "").strip().lower()
        occurred_at = str(row.get("occurred_at") or row.get("updated_at") or row.get("created_at") or "").strip()
        if not probe_event_id or not workspace_id or not provider_key or not occurred_at:
            return None
        raw_latency = row.get("round_trip_latency_ms")
        round_trip_latency_ms = int(raw_latency) if raw_latency is not None else None
        return cls(
            probe_event_id=probe_event_id,
            workspace_id=workspace_id,
            binding_id=str(row.get("binding_id") or "").strip() or None,
            provider_key=provider_key,
            provider_family=str(row.get("provider_family") or provider_key).strip() or provider_key,
            display_name=str(row.get("display_name") or provider_key).strip() or provider_key,
            probe_status=str(row.get("probe_status") or "failed").strip(),
            connectivity_state=str(row.get("connectivity_state") or "unknown").strip(),
            secret_resolution_status=str(row.get("secret_resolution_status") or "").strip() or None,
            requested_model_ref=str(row.get("requested_model_ref") or "").strip() or None,
            effective_model_ref=str(row.get("effective_model_ref") or "").strip() or None,
            round_trip_latency_ms=round_trip_latency_ms,
            requested_by_user_id=str(row.get("requested_by_user_id") or "").strip() or None,
            occurred_at=occurred_at,
            message=str(row.get("message") or "").strip() or None,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "probe_event_id": self.probe_event_id,
            "workspace_id": self.workspace_id,
            "binding_id": self.binding_id,
            "provider_key": self.provider_key,
            "provider_family": self.provider_family,
            "display_name": self.display_name,
            "probe_status": self.probe_status,
            "connectivity_state": self.connectivity_state,
            "secret_resolution_status": self.secret_resolution_status,
            "requested_model_ref": self.requested_model_ref,
            "effective_model_ref": self.effective_model_ref,
            "round_trip_latency_ms": self.round_trip_latency_ms,
            "requested_by_user_id": self.requested_by_user_id,
            "occurred_at": self.occurred_at,
            "message": self.message,
        }


@dataclass(frozen=True)
class ProductProviderProbeHistoryItemView:
    probe_event_id: str
    occurred_at: str
    workspace_id: str
    provider_key: str
    provider_family: str
    display_name: str
    probe_status: str
    connectivity_state: str
    secret_resolution_status: Optional[str] = None
    requested_model_ref: Optional[str] = None
    effective_model_ref: Optional[str] = None
    round_trip_latency_ms: Optional[int] = None
    requested_by_user_id: Optional[str] = None
    message: Optional[str] = None
    links: ProductProviderProbeHistoryLinks = field(default_factory=lambda: ProductProviderProbeHistoryLinks(binding='/placeholder/binding', health='/placeholder/health', probe='/placeholder/probe'))

    def __post_init__(self) -> None:
        for field_name in ("probe_event_id", "occurred_at", "workspace_id", "provider_key", "provider_family", "display_name"):
            if not str(getattr(self, field_name) or '').strip():
                raise ValueError(f"ProductProviderProbeHistoryItemView.{field_name} must be non-empty")
        if self.probe_status not in _ALLOWED_PROBE_STATUSES:
            raise ValueError(f"Unsupported ProductProviderProbeHistoryItemView.probe_status: {self.probe_status}")
        if self.connectivity_state not in _ALLOWED_CONNECTIVITY_STATES:
            raise ValueError(f"Unsupported ProductProviderProbeHistoryItemView.connectivity_state: {self.connectivity_state}")
        if self.round_trip_latency_ms is not None and self.round_trip_latency_ms < 0:
            raise ValueError("ProductProviderProbeHistoryItemView.round_trip_latency_ms must be >= 0 when provided")


@dataclass(frozen=True)
class ProductProviderProbeHistoryAppliedFilters:
    limit: int = 20
    cursor: Optional[str] = None

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("ProductProviderProbeHistoryAppliedFilters.limit must be > 0")


@dataclass(frozen=True)
class ProductProviderProbeHistoryResponse:
    workspace_id: str
    provider_key: str
    returned_count: int
    total_visible_count: int
    items: tuple[ProductProviderProbeHistoryItemView, ...] = ()
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    applied_filters: ProductProviderProbeHistoryAppliedFilters = field(default_factory=ProductProviderProbeHistoryAppliedFilters)
    next_cursor: Optional[str] = None
    latest_probe_at: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not str(self.workspace_id or '').strip():
            raise ValueError("ProductProviderProbeHistoryResponse.workspace_id must be non-empty")
        if not str(self.provider_key or '').strip():
            raise ValueError("ProductProviderProbeHistoryResponse.provider_key must be non-empty")
        if self.returned_count < 0:
            raise ValueError("ProductProviderProbeHistoryResponse.returned_count must be >= 0")
        if self.total_visible_count < 0:
            raise ValueError("ProductProviderProbeHistoryResponse.total_visible_count must be >= 0")


@dataclass(frozen=True)
class ProductProviderProbeHistoryRejectedResponse:
    failure_family: ProviderProbeHistoryFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    provider_key: Optional[str] = None

    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductProviderProbeHistoryRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductProviderProbeHistoryRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductProviderProbeHistoryRejectedResponse.message must be non-empty")

@dataclass(frozen=True)
class ProviderProbeHistoryReadOutcome:
    response: Optional[ProductProviderProbeHistoryResponse] = None
    rejected: Optional[ProductProviderProbeHistoryRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
