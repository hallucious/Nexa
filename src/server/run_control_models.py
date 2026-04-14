from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from src.server.run_read_models import ProductRunControlActionsView, ProductRunRecoveryView, ProductSourceArtifactView
from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

RunControlFailureFamily = Literal["product_write_failure", "run_not_found"]
RunControlAction = Literal["retry", "force_reset", "mark_reviewed"]
_ALLOWED_FAILURE_FAMILIES = {"product_write_failure", "run_not_found"}
_ALLOWED_ACTIONS = {"retry", "force_reset", "mark_reviewed"}


@dataclass(frozen=True)
class ProductRunControlAcceptedResponse:
    run_id: str
    workspace_id: str
    action: RunControlAction
    status: str
    status_family: str
    recovery: Optional[ProductRunRecoveryView] = None
    actions: Optional[ProductRunControlActionsView] = None
    worker_attempt_number: int = 0
    queue_job_id: Optional[str] = None
    message: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    source_artifact: Optional[ProductSourceArtifactView] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductRunControlAcceptedResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunControlAcceptedResponse.workspace_id must be non-empty")
        if self.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported ProductRunControlAcceptedResponse.action: {self.action}")
        if not self.status:
            raise ValueError("ProductRunControlAcceptedResponse.status must be non-empty")
        if not self.status_family:
            raise ValueError("ProductRunControlAcceptedResponse.status_family must be non-empty")
        if self.worker_attempt_number < 0:
            raise ValueError("ProductRunControlAcceptedResponse.worker_attempt_number must be >= 0")


@dataclass(frozen=True)
class ProductRunControlRejectedResponse:
    failure_family: RunControlFailureFamily
    reason_code: str
    message: str
    run_id: Optional[str] = None
    workspace_id: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    source_artifact: Optional[ProductSourceArtifactView] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductRunControlRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductRunControlRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductRunControlRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class RunControlOutcome:
    accepted: Optional[ProductRunControlAcceptedResponse] = None
    rejected: Optional[ProductRunControlRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.accepted is not None
