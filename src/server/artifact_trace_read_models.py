from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

ArtifactTraceReadFailureFamily = Literal["product_read_failure", "run_not_found", "artifact_not_found"]
PayloadAccessMode = Literal["inline", "download", "signed_url", "reference_only"]

_ALLOWED_FAILURE_FAMILIES = {"product_read_failure", "run_not_found", "artifact_not_found"}
_ALLOWED_PAYLOAD_ACCESS_MODES = {"inline", "download", "signed_url", "reference_only"}


@dataclass(frozen=True)
class ProductArtifactPayloadAccess:
    mode: PayloadAccessMode
    value: Optional[str] = None
    reference: Optional[str] = None

    def __post_init__(self) -> None:
        if self.mode not in _ALLOWED_PAYLOAD_ACCESS_MODES:
            raise ValueError(f"Unsupported ProductArtifactPayloadAccess.mode: {self.mode}")
        if self.mode == "inline" and self.value is None:
            raise ValueError("ProductArtifactPayloadAccess.value must be provided for inline mode")
        if self.mode in {"download", "signed_url", "reference_only"} and self.reference is None:
            raise ValueError("ProductArtifactPayloadAccess.reference must be provided for non-inline reference modes")


@dataclass(frozen=True)
class ProductArtifactSummary:
    artifact_id: str
    run_id: str
    workspace_id: str
    kind: str
    label: Optional[str] = None
    value_type: Optional[str] = None
    preview: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("ProductArtifactSummary.artifact_id must be non-empty")
        if not self.run_id:
            raise ValueError("ProductArtifactSummary.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductArtifactSummary.workspace_id must be non-empty")
        if not self.kind:
            raise ValueError("ProductArtifactSummary.kind must be non-empty")


@dataclass(frozen=True)
class ProductRunArtifactsResponse:
    run_id: str
    workspace_id: str
    artifact_count: int
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    artifacts: tuple[ProductArtifactSummary, ...] = ()

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductRunArtifactsResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunArtifactsResponse.workspace_id must be non-empty")
        if self.artifact_count < 0:
            raise ValueError("ProductRunArtifactsResponse.artifact_count must be >= 0")


@dataclass(frozen=True)
class ProductArtifactDetailResponse:
    artifact_id: str
    run_id: str
    workspace_id: str
    kind: str
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    label: Optional[str] = None
    value_type: Optional[str] = None
    preview: Optional[str] = None
    payload_access: Optional[ProductArtifactPayloadAccess] = None
    append_only: bool = True
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("ProductArtifactDetailResponse.artifact_id must be non-empty")
        if not self.run_id:
            raise ValueError("ProductArtifactDetailResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductArtifactDetailResponse.workspace_id must be non-empty")
        if not self.kind:
            raise ValueError("ProductArtifactDetailResponse.kind must be non-empty")


@dataclass(frozen=True)
class ProductTraceFocusView:
    node_id: Optional[str] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class ProductTraceEventView:
    event_id: str
    sequence: int
    event_type: str
    timestamp: str
    severity: Optional[str] = None
    node_id: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("ProductTraceEventView.event_id must be non-empty")
        if self.sequence < 0:
            raise ValueError("ProductTraceEventView.sequence must be >= 0")
        if not self.event_type:
            raise ValueError("ProductTraceEventView.event_type must be non-empty")
        if not self.timestamp:
            raise ValueError("ProductTraceEventView.timestamp must be non-empty")


@dataclass(frozen=True)
class ProductRunTraceResponse:
    run_id: str
    workspace_id: str
    status: str
    latest_event_time: Optional[str]
    event_count: int
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    current_focus: Optional[ProductTraceFocusView] = None
    events: tuple[ProductTraceEventView, ...] = ()
    next_cursor: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductRunTraceResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunTraceResponse.workspace_id must be non-empty")
        if not self.status:
            raise ValueError("ProductRunTraceResponse.status must be non-empty")
        if self.event_count < 0:
            raise ValueError("ProductRunTraceResponse.event_count must be >= 0")


@dataclass(frozen=True)
class ProductArtifactTraceReadRejectedResponse:
    failure_family: ArtifactTraceReadFailureFamily
    reason_code: str
    message: str
    run_id: Optional[str] = None
    artifact_id: Optional[str] = None
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductArtifactTraceReadRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductArtifactTraceReadRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductArtifactTraceReadRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class ArtifactListReadOutcome:
    response: Optional[ProductRunArtifactsResponse] = None
    rejected: Optional[ProductArtifactTraceReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class ArtifactDetailReadOutcome:
    response: Optional[ProductArtifactDetailResponse] = None
    rejected: Optional[ProductArtifactTraceReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class TraceReadOutcome:
    response: Optional[ProductRunTraceResponse] = None
    rejected: Optional[ProductArtifactTraceReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
