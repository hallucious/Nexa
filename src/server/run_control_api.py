from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, Callable, Optional
import uuid

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, RunAuthorizationContext
from src.server.run_control_models import (
    ProductRunControlAcceptedResponse,
    ProductRunControlRejectedResponse,
    RunControlOutcome,
)
from src.server.run_read_models import ProductRunControlActionsView, ProductRunRecoveryView
from src.server.run_recovery_projection import recovery_projection_from_run_row
from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace
from src.server.run_action_log_api import latest_action_from_run_record

RunRecordWriter = Callable[[Mapping[str, Any]], Any]
NowIsoFactory = Callable[[], str]
QueueJobIdFactory = Callable[[], str]


def _status_family_for_status(status: str | None) -> str:
    normalized = str(status or '').strip().lower()
    if normalized in {'queued', 'starting'}:
        return 'pending'
    if normalized in {'running', 'paused'}:
        return 'active'
    if normalized == 'completed':
        return 'terminal_success'
    if normalized in {'failed', 'cancelled'}:
        return 'terminal_failure'
    if normalized == 'partial':
        return 'terminal_partial'
    return 'unknown'


def _recovery_view_from_run_row(run_record_row: Mapping[str, Any]) -> ProductRunRecoveryView | None:
    projection = recovery_projection_from_run_row(run_record_row)
    if projection is None:
        return None
    return ProductRunRecoveryView(
        recovery_state=projection.recovery_state,
        worker_attempt_number=projection.worker_attempt_number,
        queue_job_id=projection.queue_job_id,
        claimed_by_worker_ref=projection.claimed_by_worker_ref,
        lease_expires_at=projection.lease_expires_at,
        orphan_review_required=projection.orphan_review_required,
        latest_error_family=projection.latest_error_family,
        summary=projection.summary,
        fallback_trace=projection.fallback_trace,
    )


def _is_worker_infra_failure(run_record_row: Mapping[str, Any]) -> bool:
    return str(run_record_row.get("latest_error_family") or "").strip() == "worker_infrastructure_failure"


def _append_action_log(updated_row: dict[str, Any], *, action: str, actor_user_id: str, timestamp: str | None, before_row: Mapping[str, Any], after_row: Mapping[str, Any]) -> None:
    existing = updated_row.get("action_log")
    entries = list(existing) if isinstance(existing, Sequence) and not isinstance(existing, (str, bytes, bytearray)) else []
    entries.append({
        "event_id": f"act_{uuid.uuid4().hex}",
        "action": action,
        "actor_user_id": actor_user_id,
        "timestamp": timestamp or "",
        "before_state": {
            "status": str(before_row.get("status") or ""),
            "status_family": str(before_row.get("status_family") or ""),
            "queue_job_id": before_row.get("queue_job_id"),
            "worker_attempt_number": int(before_row.get("worker_attempt_number") or 0),
            "orphan_review_required": bool(before_row.get("orphan_review_required")),
            "latest_error_family": before_row.get("latest_error_family"),
        },
        "after_state": {
            "status": str(after_row.get("status") or ""),
            "status_family": str(after_row.get("status_family") or ""),
            "queue_job_id": after_row.get("queue_job_id"),
            "worker_attempt_number": int(after_row.get("worker_attempt_number") or 0),
            "orphan_review_required": bool(after_row.get("orphan_review_required")),
            "latest_error_family": after_row.get("latest_error_family"),
        },
    })
    updated_row["action_log"] = entries


def build_run_control_actions(*, request_auth: RequestAuthContext, run_context: Optional[RunAuthorizationContext], run_record_row: Optional[Mapping[str, Any]]) -> ProductRunControlActionsView | None:
    if run_context is None or run_record_row is None or not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
        return None
    recovery = recovery_projection_from_run_row(run_record_row, include_healthy_without_signal=True)
    recovery_state = recovery.recovery_state if recovery is not None else "healthy"
    status = str(run_record_row.get("status") or "").strip().lower()
    role_context = request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else ()

    manage_decision = AuthorizationGate.authorize_run_scope(
        AuthorizationInput(
            user_id=request_auth.requested_by_user_ref,
            workspace_id=run_context.workspace_context.workspace_id,
            requested_action="manage",
            role_context=role_context,
            run_id=run_context.run_id,
        ),
        run_context,
    )
    review_decision = AuthorizationGate.authorize_run_scope(
        AuthorizationInput(
            user_id=request_auth.requested_by_user_ref,
            workspace_id=run_context.workspace_context.workspace_id,
            requested_action="review",
            role_context=role_context,
            run_id=run_context.run_id,
        ),
        run_context,
    )
    return ProductRunControlActionsView(
        can_retry=manage_decision.allowed and (status == "failed" or recovery_state == "retry_pending"),
        can_force_reset=manage_decision.allowed and recovery_state == "leased",
        can_mark_reviewed=review_decision.allowed and recovery_state == "manual_review_required",
    )


def _reject(*, family: str, code: str, message: str, run_id: str | None = None, workspace_id: str | None = None, provider_continuity=None, activity_continuity=None) -> RunControlOutcome:
    return RunControlOutcome(
        rejected=ProductRunControlRejectedResponse(
            failure_family=family,  # type: ignore[arg-type]
            reason_code=code,
            message=message,
            run_id=run_id,
            workspace_id=workspace_id,
            provider_continuity=provider_continuity,
            activity_continuity=activity_continuity,
        )
    )


class RunControlService:
    @classmethod
    def apply_action(
        cls,
        *,
        action: str,
        request_auth: RequestAuthContext,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_record_writer: Optional[RunRecordWriter] = None,
        now_iso_factory: Optional[NowIsoFactory] = None,
        queue_job_id_factory: Optional[QueueJobIdFactory] = None,
    ) -> RunControlOutcome:
        run_id = str((run_record_row or {}).get("run_id") or (run_context.run_id if run_context else "")).strip() or None
        workspace_id = str((run_record_row or {}).get("workspace_id") or (run_context.workspace_context.workspace_id if run_context else "")).strip() or None
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
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _reject(family="product_write_failure", code=f"run_control.{action}.authentication_required", message="Run control action requires an authenticated session.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
        if run_context is None or run_record_row is None:
            return _reject(family="run_not_found", code=f"run_control.{action}.run_not_found", message="Requested run could not be found.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)

        requested_action = "review" if action == "mark_reviewed" else "manage"
        decision = AuthorizationGate.authorize_run_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref,
                workspace_id=run_context.workspace_context.workspace_id,
                requested_action=requested_action,
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
                run_id=run_context.run_id,
            ),
            run_context,
        )
        if not decision.allowed:
            return _reject(family="product_write_failure", code=f"run_control.{action}.{decision.reason_code}", message="Current user is not allowed to control this run.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)

        actions = build_run_control_actions(request_auth=request_auth, run_context=run_context, run_record_row=run_record_row)
        if actions is None:
            return _reject(family="product_write_failure", code=f"run_control.{action}.actions_unavailable", message="Run control actions are currently unavailable.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
        now_iso_factory = now_iso_factory or (lambda: "")
        queue_job_id_factory = queue_job_id_factory or (lambda: f"job_{uuid.uuid4().hex}")
        now_iso = str(now_iso_factory() or "").strip() or None
        updated_row = deepcopy(dict(run_record_row))

        if action == "retry":
            if not actions.can_retry:
                return _reject(family="product_write_failure", code="run_control.retry.invalid_state", message="Retry is not allowed for the current run state.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
            updated_row.update({
                "status": "queued",
                "status_family": "pending",
                "queue_job_id": queue_job_id_factory(),
                "claimed_by_worker_ref": None,
                "claimed_at": None,
                "lease_expires_at": None,
                "last_heartbeat_at": None,
                "worker_attempt_number": int(updated_row.get("worker_attempt_number") or 0) + 1,
                "orphan_review_required": False,
                "latest_error_family": "worker_infrastructure_failure" if _is_worker_infra_failure(updated_row) or str(updated_row.get("status") or "").strip().lower() == "failed" else updated_row.get("latest_error_family"),
            })
            message = "Run was re-queued for another worker attempt."
        elif action == "force_reset":
            if not actions.can_force_reset:
                return _reject(family="product_write_failure", code="run_control.force_reset.invalid_state", message="Force reset is not allowed unless the run is currently leased.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
            updated_row.update({
                "status": "queued",
                "status_family": "pending",
                "claimed_by_worker_ref": None,
                "claimed_at": None,
                "lease_expires_at": None,
                "last_heartbeat_at": None,
                "orphan_review_required": True,
                "latest_error_family": "worker_infrastructure_failure",
            })
            message = "Worker lease was cleared and the run now requires orphan review."
        elif action == "mark_reviewed":
            if not actions.can_mark_reviewed:
                return _reject(family="product_write_failure", code="run_control.mark_reviewed.invalid_state", message="Mark reviewed is only allowed when orphan review is required.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
            updated_row.update({"orphan_review_required": False})
            message = "Orphan review requirement was cleared for the run."
        else:
            return _reject(family="product_write_failure", code="run_control.action_invalid", message="Unsupported run control action.", run_id=run_id, workspace_id=workspace_id, provider_continuity=provider_continuity, activity_continuity=activity_continuity)

        if now_iso is not None:
            updated_row["updated_at"] = now_iso
        _append_action_log(updated_row, action=action, actor_user_id=request_auth.requested_by_user_ref, timestamp=now_iso, before_row=run_record_row, after_row=updated_row)
        if run_record_writer is not None:
            run_record_writer(updated_row)

        recovery = _recovery_view_from_run_row(updated_row)
        actions_after = build_run_control_actions(request_auth=request_auth, run_context=run_context, run_record_row=updated_row)
        return RunControlOutcome(
            accepted=ProductRunControlAcceptedResponse(
                run_id=str(updated_row.get("run_id") or run_context.run_id),
                workspace_id=str(updated_row.get("workspace_id") or run_context.workspace_context.workspace_id),
                action=action,  # type: ignore[arg-type]
                status=str(updated_row.get("status") or "unknown"),
                status_family=str(updated_row.get("status_family") or _status_family_for_status(str(updated_row.get("status") or "unknown"))),
                recovery=recovery,
                actions=actions_after,
                worker_attempt_number=int(updated_row.get("worker_attempt_number") or 0),
                queue_job_id=str(updated_row.get("queue_job_id") or "").strip() or None,
                message=message,
                provider_continuity=_provider_continuity_summary_for_workspace(run_context.workspace_context.workspace_id, provider_binding_rows=provider_binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows),
                activity_continuity=_activity_continuity_summary_for_workspace(run_context.workspace_context.workspace_id, user_id=request_auth.requested_by_user_ref or "", recent_run_rows=recent_run_rows, provider_binding_rows=provider_binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows, onboarding_rows=onboarding_rows),
            )
        )
