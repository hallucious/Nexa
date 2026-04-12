from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

RunActionLogFailureFamily = Literal["product_read_failure", "run_not_found"]
_ALLOWED_FAILURE_FAMILIES = {"product_read_failure", "run_not_found"}
_ALLOWED_ACTIONS = {"retry", "force_reset", "mark_reviewed"}


@dataclass(frozen=True)
class ProductRunActionLogEventView:
    event_id: str
    action: str
    actor_user_id: str
    timestamp: str
    before_state: dict[str, object] = field(default_factory=dict)
    after_state: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("ProductRunActionLogEventView.event_id must be non-empty")
        if self.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported ProductRunActionLogEventView.action: {self.action}")
        if not self.actor_user_id:
            raise ValueError("ProductRunActionLogEventView.actor_user_id must be non-empty")
        if not self.timestamp:
            raise ValueError("ProductRunActionLogEventView.timestamp must be non-empty")


@dataclass(frozen=True)
class ProductRunLastActionView:
    action: str
    actor_user_id: str
    timestamp: str

    def __post_init__(self) -> None:
        if self.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported ProductRunLastActionView.action: {self.action}")
        if not self.actor_user_id:
            raise ValueError("ProductRunLastActionView.actor_user_id must be non-empty")
        if not self.timestamp:
            raise ValueError("ProductRunLastActionView.timestamp must be non-empty")


@dataclass(frozen=True)
class ProductRunActionLogResponse:
    run_id: str
    workspace_id: str
    returned_count: int
    actions: tuple[ProductRunActionLogEventView, ...] = ()
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductRunActionLogResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunActionLogResponse.workspace_id must be non-empty")
        if self.returned_count < 0:
            raise ValueError("ProductRunActionLogResponse.returned_count must be >= 0")


@dataclass(frozen=True)
class ProductRunActionLogRejectedResponse:
    failure_family: RunActionLogFailureFamily
    reason_code: str
    message: str
    run_id: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductRunActionLogRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductRunActionLogRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductRunActionLogRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class RunActionLogReadOutcome:
    response: Optional[ProductRunActionLogResponse] = None
    rejected: Optional[ProductRunActionLogRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
