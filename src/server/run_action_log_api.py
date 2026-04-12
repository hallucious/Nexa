from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, RunAuthorizationContext
from src.server.run_action_log_models import (
    ProductRunActionLogEventView,
    ProductRunActionLogRejectedResponse,
    ProductRunActionLogResponse,
    ProductRunLastActionView,
    RunActionLogReadOutcome,
)
from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace


def normalize_action_log_entries(run_record_row: Mapping[str, Any] | None) -> tuple[ProductRunActionLogEventView, ...]:
    if not isinstance(run_record_row, Mapping):
        return ()
    raw_entries = run_record_row.get("action_log")
    if not isinstance(raw_entries, Sequence) or isinstance(raw_entries, (str, bytes, bytearray)):
        return ()
    events: list[ProductRunActionLogEventView] = []
    for entry in raw_entries:
        if not isinstance(entry, Mapping):
            continue
        action = str(entry.get("action") or "").strip()
        actor_user_id = str(entry.get("actor_user_id") or "").strip()
        timestamp = str(entry.get("timestamp") or "").strip()
        event_id = str(entry.get("event_id") or "").strip()
        if not action or not actor_user_id or not timestamp or not event_id:
            continue
        try:
            events.append(
                ProductRunActionLogEventView(
                    event_id=event_id,
                    action=action,
                    actor_user_id=actor_user_id,
                    timestamp=timestamp,
                    before_state=dict(entry.get("before_state") or {}),
                    after_state=dict(entry.get("after_state") or {}),
                )
            )
        except ValueError:
            continue
    return tuple(events)


def latest_action_from_run_record(run_record_row: Mapping[str, Any] | None) -> ProductRunLastActionView | None:
    events = normalize_action_log_entries(run_record_row)
    if not events:
        return None
    event = events[-1]
    return ProductRunLastActionView(action=event.action, actor_user_id=event.actor_user_id, timestamp=event.timestamp)


class RunActionLogReadService:
    @staticmethod
    def _reject(*, run_id: str | None, workspace_id: str | None, family: str, code: str, message: str, workspace_title=None, provider_continuity=None, activity_continuity=None) -> RunActionLogReadOutcome:
        return RunActionLogReadOutcome(
            rejected=ProductRunActionLogRejectedResponse(
                failure_family=family,  # type: ignore[arg-type]
                reason_code=code,
                message=message,
                run_id=run_id,
                workspace_id=workspace_id,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )

    @classmethod
    def read_actions(
        cls,
        *,
        request_auth: RequestAuthContext,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> RunActionLogReadOutcome:
        run_id = run_context.run_id if run_context is not None else str((run_record_row or {}).get("run_id") or "").strip() or None
        workspace_id = run_context.workspace_context.workspace_id if run_context is not None else str((run_record_row or {}).get("workspace_id") or "").strip() or None
        workspace_title, provider_continuity, activity_continuity = (None, None, None)
        if workspace_id:
            workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
                workspace_id,
                workspace_row=workspace_row,
                user_id=request_auth.requested_by_user_ref or "",
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
            )
        if not request_auth.is_authenticated:
            return cls._reject(run_id=run_id, workspace_id=workspace_id, family="product_read_failure", code="run_actions.authentication_required", message="Run action history requires an authenticated session.", workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
        if run_context is None or run_record_row is None:
            return cls._reject(run_id=run_id, workspace_id=workspace_id, family="run_not_found", code="run_actions.run_not_found", message="Requested run could not be found.", workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
        decision = AuthorizationGate.authorize_run_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref or "",
                workspace_id=run_context.workspace_context.workspace_id,
                requested_action="history",
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
                run_id=run_context.run_id,
            ),
            run_context,
        )
        if not decision.allowed:
            return cls._reject(run_id=run_id, workspace_id=workspace_id, family="product_read_failure", code=f"run_actions.{decision.reason_code}", message="Current user is not allowed to read run action history.", workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
        events = normalize_action_log_entries(run_record_row)
        return RunActionLogReadOutcome(
            response=ProductRunActionLogResponse(
                run_id=run_context.run_id,
                workspace_id=run_context.workspace_context.workspace_id,
                returned_count=len(events),
                actions=events,
                workspace_title=workspace_title,
                provider_continuity=_provider_continuity_summary_for_workspace(run_context.workspace_context.workspace_id, provider_binding_rows=provider_binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows),
                activity_continuity=_activity_continuity_summary_for_workspace(run_context.workspace_context.workspace_id, user_id=request_auth.requested_by_user_ref or '', recent_run_rows=recent_run_rows, provider_binding_rows=provider_binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows, onboarding_rows=onboarding_rows),
            )
        )
