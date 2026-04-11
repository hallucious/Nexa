from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from src.server.workspace_onboarding_api import WorkspaceRegistryService
from src.server.workspace_onboarding_models import ProductWorkspaceSummaryView
from src.server.auth_models import RequestAuthContext
from src.server.recent_activity_models import (
    HistorySummaryReadOutcome,
    ProductHistorySummaryResponse,
    ProductRecentActivityAppliedFilters,
    ProductRecentActivityItemView,
    ProductRecentActivityLinks,
    ProductRecentActivityRejectedResponse,
    ProductRecentActivityResponse,
    RecentActivityReadOutcome,
)


def _visible_workspaces(
    *,
    request_auth: RequestAuthContext,
    workspace_rows: Sequence[Mapping[str, Any]],
    membership_rows: Sequence[Mapping[str, Any]],
    run_rows: Sequence[Mapping[str, Any]],
) -> tuple[ProductWorkspaceSummaryView, ...]:
    outcome = WorkspaceRegistryService.list_workspaces(
        request_auth=request_auth,
        workspace_rows=workspace_rows,
        membership_rows=membership_rows,
        recent_run_rows=run_rows,
    )
    if outcome.response is None:
        return ()
    return outcome.response.workspaces


def _workspace_title_map(workspaces: Sequence[ProductWorkspaceSummaryView]) -> dict[str, str]:
    return {item.workspace_id: item.title for item in workspaces}


def _run_activity_type(row: Mapping[str, Any]) -> str:
    status_family = str(row.get('status_family') or '').strip().lower()
    if status_family == 'pending':
        return 'run_queued'
    if status_family == 'active':
        return 'run_running'
    if status_family == 'terminal_success':
        return 'run_completed'
    if status_family == 'terminal_failure':
        return 'run_failed'
    return 'run_updated'


def _probe_activity_type(row: Mapping[str, Any]) -> str:
    probe_status = str(row.get('probe_status') or '').strip().lower()
    if probe_status == 'reachable':
        return 'provider_probe_reachable'
    if probe_status == 'warning':
        return 'provider_probe_warning'
    return 'provider_probe_failed'


class RecentActivityService:
    @classmethod
    def list_recent_activity(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        run_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        workspace_id: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> RecentActivityReadOutcome:
        if not request_auth.is_authenticated:
            return RecentActivityReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='recent_activity.authentication_required',
                    message='Recent activity requires an authenticated session.',
                    workspace_id=workspace_id,
                )
            )
        if limit <= 0:
            return RecentActivityReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='recent_activity.limit_invalid',
                    message='Recent activity limit must be greater than zero.',
                    workspace_id=workspace_id,
                )
            )
        visible_workspaces = _visible_workspaces(
            request_auth=request_auth,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            run_rows=run_rows,
        )
        visible_ids = {item.workspace_id for item in visible_workspaces}
        if workspace_id is not None and workspace_id not in visible_ids:
            return RecentActivityReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='recent_activity.workspace_forbidden',
                    message='Current user is not allowed to read recent activity for the requested workspace.',
                    workspace_id=workspace_id,
                )
            )
        titles = _workspace_title_map(visible_workspaces)
        activities: list[ProductRecentActivityItemView] = []
        for item in visible_workspaces:
            if workspace_id is not None and item.workspace_id != workspace_id:
                continue
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'workspace:{item.workspace_id}:{item.updated_at}',
                    activity_type='workspace_updated',
                    occurred_at=item.updated_at,
                    workspace_id=item.workspace_id,
                    workspace_title=item.title,
                    summary=f'Workspace "{item.title}" was updated.',
                    links=ProductRecentActivityLinks(workspace=item.links.detail),
                )
            )
        for row in run_rows:
            row_workspace_id = str(row.get('workspace_id') or '').strip()
            if row_workspace_id not in visible_ids:
                continue
            if workspace_id is not None and row_workspace_id != workspace_id:
                continue
            run_id = str(row.get('run_id') or '').strip()
            occurred_at = str(row.get('updated_at') or row.get('created_at') or '').strip()
            if not run_id or not occurred_at:
                continue
            activity_type = _run_activity_type(row)
            status = str(row.get('status') or '').strip() or None
            status_family = str(row.get('status_family') or '').strip() or None
            workspace_title = titles.get(row_workspace_id, row_workspace_id)
            summary = f'Run {run_id} is {status or "updated"}.'
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'run:{run_id}:{occurred_at}',
                    activity_type=activity_type,
                    occurred_at=occurred_at,
                    workspace_id=row_workspace_id,
                    workspace_title=workspace_title,
                    run_id=run_id,
                    status=status,
                    status_family=status_family,
                    summary=summary,
                    actor_user_id=str(row.get('requested_by_user_id') or '').strip() or None,
                    links=ProductRecentActivityLinks(
                        workspace=f'/api/workspaces/{row_workspace_id}',
                        run_status=f'/api/runs/{run_id}',
                        run_result=f'/api/runs/{run_id}/result',
                    ),
                )
            )
        for row in provider_probe_rows:
            row_workspace_id = str(row.get('workspace_id') or '').strip()
            if row_workspace_id not in visible_ids:
                continue
            if workspace_id is not None and row_workspace_id != workspace_id:
                continue
            probe_event_id = str(row.get('probe_event_id') or row.get('probe_id') or '').strip()
            occurred_at = str(row.get('occurred_at') or row.get('updated_at') or row.get('created_at') or '').strip()
            provider_key = str(row.get('provider_key') or '').strip().lower()
            if not probe_event_id or not occurred_at or not provider_key:
                continue
            workspace_title = titles.get(row_workspace_id, row_workspace_id)
            display_name = str(row.get('display_name') or provider_key).strip() or provider_key
            probe_status = str(row.get('probe_status') or '').strip() or None
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'probe:{probe_event_id}:{occurred_at}',
                    activity_type=_probe_activity_type(row),
                    occurred_at=occurred_at,
                    workspace_id=row_workspace_id,
                    workspace_title=workspace_title,
                    status=probe_status,
                    summary=f'Provider probe for {display_name} is {probe_status or "updated"}.',
                    actor_user_id=str(row.get('requested_by_user_id') or '').strip() or None,
                    links=ProductRecentActivityLinks(
                        workspace=f'/api/workspaces/{row_workspace_id}',
                        provider_binding=f'/api/workspaces/{row_workspace_id}/provider-bindings/{provider_key}',
                        provider_health=f'/api/workspaces/{row_workspace_id}/provider-bindings/{provider_key}/health',
                        provider_probe_history=f'/api/workspaces/{row_workspace_id}/provider-bindings/{provider_key}/probe-history',
                    ),
                )
            )
        activities.sort(key=lambda item: (item.occurred_at, item.activity_id), reverse=True)
        total_visible_count = len(activities)
        start_index = 0
        if cursor is not None:
            matching_index = next((index for index, item in enumerate(activities) if item.activity_id == cursor), None)
            if matching_index is None:
                return RecentActivityReadOutcome(
                    rejected=ProductRecentActivityRejectedResponse(
                        failure_family='product_read_failure',
                        reason_code='recent_activity.cursor_invalid',
                        message='Recent activity cursor is invalid.',
                        workspace_id=workspace_id,
                    )
                )
            start_index = matching_index + 1
        page = tuple(activities[start_index : start_index + limit])
        next_cursor = page[-1].activity_id if len(page) == limit and (start_index + limit) < total_visible_count else None
        latest_activity_at = activities[0].occurred_at if activities else None
        return RecentActivityReadOutcome(
            response=ProductRecentActivityResponse(
                returned_count=len(page),
                total_visible_count=total_visible_count,
                activities=page,
                applied_filters=ProductRecentActivityAppliedFilters(workspace_id=workspace_id, cursor=cursor, limit=limit),
                next_cursor=next_cursor,
                latest_activity_at=latest_activity_at,
                message='No recent activity is available yet.' if not activities else None,
            )
        )

    @classmethod
    def read_history_summary(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        run_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        workspace_id: Optional[str] = None,
    ) -> HistorySummaryReadOutcome:
        if not request_auth.is_authenticated:
            return HistorySummaryReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='history_summary.authentication_required',
                    message='History summary requires an authenticated session.',
                    workspace_id=workspace_id,
                )
            )
        visible_workspaces = _visible_workspaces(
            request_auth=request_auth,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            run_rows=run_rows,
        )
        visible_ids = {item.workspace_id for item in visible_workspaces}
        if workspace_id is not None and workspace_id not in visible_ids:
            return HistorySummaryReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='history_summary.workspace_forbidden',
                    message='Current user is not allowed to read aggregate history for the requested workspace.',
                    workspace_id=workspace_id,
                )
            )
        filtered_runs = [
            row for row in run_rows
            if str(row.get('workspace_id') or '').strip() in visible_ids
            and (workspace_id is None or str(row.get('workspace_id') or '').strip() == workspace_id)
        ]
        latest_run = None
        latest_activity_at = None
        if filtered_runs:
            filtered_runs.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('run_id') or '')), reverse=True)
            latest_run = filtered_runs[0]
            latest_activity_at = str(latest_run.get('updated_at') or latest_run.get('created_at') or '').strip() or None
        filtered_probe_rows = [
            row for row in provider_probe_rows
            if str(row.get('workspace_id') or '').strip() in visible_ids
            and (workspace_id is None or str(row.get('workspace_id') or '').strip() == workspace_id)
        ]
        latest_probe = None
        if filtered_probe_rows:
            filtered_probe_rows.sort(key=lambda row: (str(row.get('occurred_at') or row.get('updated_at') or row.get('created_at') or ''), str(row.get('probe_event_id') or row.get('probe_id') or '')), reverse=True)
            latest_probe = filtered_probe_rows[0]
        candidate_times = [value for value in (
            latest_activity_at,
            str(latest_probe.get('occurred_at') or latest_probe.get('updated_at') or latest_probe.get('created_at') or '').strip() if latest_probe is not None else None,
        ) if value]
        latest_activity_at = max(candidate_times) if candidate_times else None
        pending_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'pending')
        active_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'active')
        terminal_success_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'terminal_success')
        terminal_failure_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'terminal_failure')
        recent_probe_count = len(filtered_probe_rows)
        failed_probe_count = sum(1 for row in filtered_probe_rows if str(row.get('probe_status') or '').strip().lower() not in {'reachable', 'warning'})
        return HistorySummaryReadOutcome(
            response=ProductHistorySummaryResponse(
                scope='workspace' if workspace_id is not None else 'account',
                workspace_id=workspace_id,
                visible_workspace_count=sum(1 for item in visible_workspaces if workspace_id is None or item.workspace_id == workspace_id),
                total_visible_runs=len(filtered_runs),
                pending_runs=pending_runs,
                active_runs=active_runs,
                terminal_success_runs=terminal_success_runs,
                terminal_failure_runs=terminal_failure_runs,
                recent_probe_count=recent_probe_count,
                failed_probe_count=failed_probe_count,
                latest_activity_at=latest_activity_at,
                latest_run_id=str(latest_run.get('run_id') or '').strip() or None if latest_run is not None else None,
                latest_probe_event_id=str(latest_probe.get('probe_event_id') or latest_probe.get('probe_id') or '').strip() or None if latest_probe is not None else None,
            )
        )
