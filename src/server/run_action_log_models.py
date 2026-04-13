from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

RunActionLogFailureFamily = Literal["product_read_failure", "run_not_found"]
_ALLOWED_FAILURE_FAMILIES = {"product_read_failure", "run_not_found"}
_ALLOWED_ACTIONS = {"retry", "force_reset", "mark_reviewed", "auto_retry", "auto_mark_review_required", "auto_fallback_retry", "fallback_scoring_evaluated"}


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




@dataclass(frozen=True)
class ProductRunFallbackScoringEntryView:
    provider_key: str
    health_score: float
    cost_score: float
    priority_score: float
    final_score: float
    selected: bool = False

    def __post_init__(self) -> None:
        if not self.provider_key:
            raise ValueError("ProductRunFallbackScoringEntryView.provider_key must be non-empty")


@dataclass(frozen=True)
class ProductRunFallbackScoringAuditView:
    timestamp: str
    selected_provider_key: str
    entries: tuple[ProductRunFallbackScoringEntryView, ...] = ()
    action: str = "fallback_scoring_evaluated"

    def __post_init__(self) -> None:
        if self.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported ProductRunFallbackScoringAuditView.action: {self.action}")
        if not self.timestamp:
            raise ValueError("ProductRunFallbackScoringAuditView.timestamp must be non-empty")
        if not self.selected_provider_key:
            raise ValueError("ProductRunFallbackScoringAuditView.selected_provider_key must be non-empty")


def fallback_scoring_audit_from_action_log_event(event: dict[str, Any]) -> ProductRunFallbackScoringAuditView | None:
    if str(event.get("action") or "").strip() != "fallback_scoring_evaluated":
        return None
    after_state = event.get("after_state")
    if not isinstance(after_state, dict):
        return None
    timestamp = str(event.get("timestamp") or "").strip()
    selected_provider_key = str(after_state.get("selected_provider_key") or "").strip()
    raw_entries = after_state.get("scoring_trace")
    if not (timestamp and selected_provider_key and isinstance(raw_entries, list)):
        return None
    entries: list[ProductRunFallbackScoringEntryView] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        provider_key = str(item.get("provider") or item.get("provider_key") or "").strip()
        if not provider_key:
            continue
        entries.append(ProductRunFallbackScoringEntryView(
            provider_key=provider_key,
            health_score=float(item.get("health_score") or 0.0),
            cost_score=float(item.get("cost_score") or 0.0),
            priority_score=float(item.get("priority_score") or 0.0),
            final_score=float(item.get("final_score") or 0.0),
            selected=bool(item.get("selected")),
        ))
    if not entries:
        return None
    return ProductRunFallbackScoringAuditView(
        timestamp=timestamp,
        selected_provider_key=selected_provider_key,
        entries=tuple(entries),
        action="fallback_scoring_evaluated",
    )

@dataclass(frozen=True)
class ProductRunFallbackAuditView:
    timestamp: str
    from_provider_key: str
    to_provider_key: str
    reason: str
    action: str = "auto_fallback_retry"

    def __post_init__(self) -> None:
        if self.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported ProductRunFallbackAuditView.action: {self.action}")
        if not self.timestamp:
            raise ValueError("ProductRunFallbackAuditView.timestamp must be non-empty")
        if not self.from_provider_key:
            raise ValueError("ProductRunFallbackAuditView.from_provider_key must be non-empty")
        if not self.to_provider_key:
            raise ValueError("ProductRunFallbackAuditView.to_provider_key must be non-empty")
        if not self.reason:
            raise ValueError("ProductRunFallbackAuditView.reason must be non-empty")


def fallback_audit_from_action_log_event(event: dict[str, Any]) -> ProductRunFallbackAuditView | None:
    if str(event.get("action") or "").strip() != "auto_fallback_retry":
        return None
    after_state = event.get("after_state")
    before_state = event.get("before_state")
    if not isinstance(after_state, dict) or not isinstance(before_state, dict):
        return None
    to_provider_key = str(
        after_state.get("fallback_to_provider")
        or after_state.get("fallback_provider_key")
        or ""
    ).strip()
    from_provider_key = str(
        after_state.get("fallback_from_provider")
        or before_state.get("provider_key")
        or before_state.get("fallback_from_provider")
        or ""
    ).strip()
    reason = str(
        after_state.get("fallback_reason")
        or after_state.get("fallback_reason_code")
        or ""
    ).strip()
    timestamp = str(event.get("timestamp") or "").strip()
    if not (timestamp and from_provider_key and to_provider_key and reason):
        return None
    return ProductRunFallbackAuditView(
        timestamp=timestamp,
        from_provider_key=from_provider_key,
        to_provider_key=to_provider_key,
        reason=reason,
        action="auto_fallback_retry",
    )
