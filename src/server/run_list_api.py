from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.run_list_models import (
    ProductRunListAppliedFilters,
    ProductRunListItemView,
    ProductRunListLinks,
    ProductRunListRejectedResponse,
    ProductWorkspaceRunListResponse,
    RunListReadOutcome,
)
from src.server.run_read_models import ProductExecutionTargetView, ProductResultSummaryView
from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace
from src.server.run_read_api import _recovery_view_from_run_row


_ALLOWED_WORKSPACE_LIST_ROLES = ("owner", "admin", "collaborator", "reviewer", "viewer")


def _status_family_for_row(row: Mapping[str, Any]) -> str:
    value = str(row.get("status_family") or "").strip().lower()
    if value:
        return value
    status = str(row.get("status") or "").strip().lower()
    if status in {"queued", "starting"}:
        return "pending"
    if status in {"running", "paused"}:
        return "active"
    if status == "completed":
        return "terminal_success"
    if status in {"failed", "cancelled"}:
        return "terminal_failure"
    if status == "partial":
        return "terminal_partial"
    return "unknown"


def _build_links(run_id: str) -> ProductRunListLinks:
    return ProductRunListLinks(
        status=f"/api/runs/{run_id}",
        result=f"/api/runs/{run_id}/result",
        trace=f"/api/runs/{run_id}/trace",
        artifacts=f"/api/runs/{run_id}/artifacts",
    )


def _summary_from_result_row(result_row: Mapping[str, Any] | None) -> ProductResultSummaryView | None:
    if not result_row:
        return None
    summary = result_row.get("result_summary")
    if isinstance(summary, str) and summary.strip():
        final_status = str(result_row.get("final_status") or "").strip().lower()
        if final_status == "completed":
            title = "Run completed"
        elif final_status == "partial":
            title = "Run partially completed"
        elif final_status == "failed":
            title = "Run failed"
        else:
            title = "Run result"
        return ProductResultSummaryView(title=title, description=summary.strip())
    return None


def _sort_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return (str(row.get("created_at") or ""), str(row.get("run_id") or ""))


class RunListReadService:
    @classmethod
    def list_workspace_runs(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        cursor: Optional[str] = None,
        limit: int = 20,
        status_family: Optional[str] = None,
        requested_by_user_id: Optional[str] = None,
    ) -> RunListReadOutcome:
        workspace_title, provider_continuity, activity_continuity = (None, None, None)
        if workspace_context is not None:
            workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
                workspace_context.workspace_id,
                workspace_row=workspace_row,
                user_id=request_auth.requested_by_user_ref or "",
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
            )
        if not request_auth.is_authenticated:
            return RunListReadOutcome(
                rejected=ProductRunListRejectedResponse(
                    failure_family="product_read_failure",
                    reason_code="run_list.authentication_required",
                    message="Workspace run list requires an authenticated session.",
                    workspace_id=workspace_context.workspace_id if workspace_context else None,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        if workspace_context is None:
            return RunListReadOutcome(
                rejected=ProductRunListRejectedResponse(
                    failure_family="workspace_not_found",
                    reason_code="run_list.workspace_not_found",
                    message="Requested workspace was not found.",
                )
            )
        if limit <= 0 or limit > 100:
            return RunListReadOutcome(
                rejected=ProductRunListRejectedResponse(
                    failure_family="product_read_failure",
                    reason_code="run_list.limit_invalid",
                    message="Run list limit must be between 1 and 100.",
                    workspace_id=workspace_context.workspace_id,
                                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="history",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return RunListReadOutcome(
                rejected=ProductRunListRejectedResponse(
                    failure_family="product_read_failure",
                    reason_code=f"run_list.{decision.reason_code}",
                    message="Current user is not allowed to read workspace runs.",
                    workspace_id=workspace_context.workspace_id,
                                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )

        filtered = [
            dict(row)
            for row in run_rows
            if str(row.get("workspace_id") or "").strip() == workspace_context.workspace_id
        ]
        normalized_status_family = str(status_family).strip().lower() if status_family is not None else None
        if normalized_status_family:
            filtered = [row for row in filtered if _status_family_for_row(row) == normalized_status_family]
        normalized_requested_by = str(requested_by_user_id).strip() if requested_by_user_id is not None else None
        if normalized_requested_by:
            filtered = [row for row in filtered if str(row.get("requested_by_user_id") or "").strip() == normalized_requested_by]

        ordered = sorted(filtered, key=_sort_key, reverse=True)
        start_index = 0
        normalized_cursor = str(cursor).strip() if cursor is not None else None
        if normalized_cursor:
            run_ids = [str(row.get("run_id") or "") for row in ordered]
            if normalized_cursor not in run_ids:
                return RunListReadOutcome(
                    rejected=ProductRunListRejectedResponse(
                        failure_family="invalid_cursor",
                        reason_code="run_list.cursor_invalid",
                        message="Run list cursor is invalid for the current filter set.",
                        workspace_id=workspace_context.workspace_id,
                                        workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
                )
            start_index = run_ids.index(normalized_cursor) + 1

        page = ordered[start_index:start_index + limit]
        next_cursor = None
        if start_index + limit < len(ordered) and page:
            next_cursor = str(page[-1].get("run_id") or "")

        result_index = dict(result_rows_by_run_id or {})
        items: list[ProductRunListItemView] = []
        for row in page:
            run_id = str(row.get("run_id") or "")
            result_row = result_index.get(run_id)
            items.append(
                ProductRunListItemView(
                    run_id=run_id,
                    workspace_id=workspace_context.workspace_id,
                    execution_target=ProductExecutionTargetView(
                        target_type=str(row.get("execution_target_type") or ""),
                        target_ref=str(row.get("execution_target_ref") or ""),
                    ),
                    status=str(row.get("status") or "unknown"),
                    status_family=_status_family_for_row(row),
                    created_at=str(row.get("created_at") or ""),
                    updated_at=str(row.get("updated_at") or ""),
                    started_at=str(row.get("started_at") or "") or None,
                    completed_at=str(row.get("finished_at") or "") or None,
                    requested_by_user_id=str(row.get("requested_by_user_id") or "") or None,
                    result_state=str((result_row or {}).get("result_state") or row.get("result_state") or "") or None,
                    latest_error_family=str(row.get("latest_error_family") or "") or None,
                    trace_available=bool(row.get("trace_available")),
                    artifact_count=int(row.get("artifact_count") or 0),
                    result_summary=_summary_from_result_row(result_row),
                    recovery=_recovery_view_from_run_row(row),
                    links=_build_links(run_id),
                )
            )

        response = ProductWorkspaceRunListResponse(
            workspace_id=workspace_context.workspace_id,
            returned_count=len(items),
            total_visible_count=len(ordered),
            workspace_title=str((workspace_row or {}).get("title") or "").strip() or None,
            provider_continuity=_provider_continuity_summary_for_workspace(
                workspace_context.workspace_id,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
            ),
            activity_continuity=_activity_continuity_summary_for_workspace(
                workspace_context.workspace_id,
                user_id=request_auth.requested_by_user_ref or '',
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
            ),
            runs=tuple(items),
            next_cursor=next_cursor,
            applied_filters=ProductRunListAppliedFilters(
                status_family=normalized_status_family,
                requested_by_user_id=normalized_requested_by,
                limit=limit,
                cursor=normalized_cursor,
            ),
        )
        return RunListReadOutcome(response=response)
