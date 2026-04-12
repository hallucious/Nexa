from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from src.server.workspace_onboarding_api import WorkspaceRegistryService, _continuity_projection_for_workspace, _continuity_projection_for_workspace_ids
from src.server.workspace_onboarding_models import ProductWorkspaceSummaryView
from src.server.auth_models import RequestAuthContext
from src.server.provider_probe_history_models import ProviderProbeHistoryRecord
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


def _workspace_row_by_id(workspace_rows: Sequence[Mapping[str, Any]], workspace_id: str | None) -> Mapping[str, Any] | None:
    normalized = str(workspace_id or '').strip()
    if not normalized:
        return None
    for row in workspace_rows:
        if str(row.get('workspace_id') or '').strip() == normalized:
            return row
    return None


def _response_continuity_projection(
    *,
    request_auth: RequestAuthContext,
    workspace_rows: Sequence[Mapping[str, Any]],
    visible_workspace_ids: Sequence[str],
    workspace_id: Optional[str],
    onboarding_rows: Sequence[Mapping[str, Any]],
    run_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
    provider_binding_rows: Sequence[Mapping[str, Any]],
    managed_secret_rows: Sequence[Mapping[str, Any]],
) -> tuple[Optional[ProductProviderContinuitySummary], Optional[ProductActivityContinuitySummary]]:
    normalized_workspace_id = str(workspace_id or '').strip() or None
    if normalized_workspace_id is not None:
        workspace_row = _workspace_row_by_id(workspace_rows, normalized_workspace_id)
        _, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            normalized_workspace_id,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or '',
            recent_run_rows=run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return provider_continuity, activity_continuity
    return _continuity_projection_for_workspace_ids(
        tuple(visible_workspace_ids),
        user_id=request_auth.requested_by_user_ref or '',
        recent_run_rows=run_rows,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
        onboarding_rows=onboarding_rows,
    )


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


def _binding_activity_status(row: Mapping[str, Any]) -> str:
    enabled = bool(row.get('enabled', True))
    secret_ref = str(row.get('secret_ref') or '').strip()
    if not enabled:
        return 'disabled'
    if not secret_ref:
        return 'missing_secret'
    return 'configured'


class RecentActivityService:
    @classmethod
    def list_recent_activity(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        workspace_id: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> RecentActivityReadOutcome:
        if not request_auth.is_authenticated:
            workspace_title = str((_workspace_row_by_id(workspace_rows, workspace_id) or {}).get('title') or '').strip() or None
            return RecentActivityReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='recent_activity.authentication_required',
                    message='Recent activity requires an authenticated session.',
                    workspace_id=workspace_id,
                    workspace_title=workspace_title,
                )
            )
        if limit <= 0:
            workspace_row = _workspace_row_by_id(workspace_rows, workspace_id)
            workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
                str(workspace_id or ''),
                workspace_row=workspace_row,
                user_id=request_auth.requested_by_user_ref or '',
                recent_run_rows=run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
            )
            return RecentActivityReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='recent_activity.limit_invalid',
                    message='Recent activity limit must be greater than zero.',
                    workspace_id=workspace_id,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
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
            workspace_title = str((_workspace_row_by_id(workspace_rows, workspace_id) or {}).get('title') or '').strip() or None
            return RecentActivityReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='recent_activity.workspace_forbidden',
                    message='Current user is not allowed to read recent activity for the requested workspace.',
                    workspace_id=workspace_id,
                    workspace_title=workspace_title,
                )
            )
        titles = _workspace_title_map(visible_workspaces)
        activities: list[ProductRecentActivityItemView] = []
        for item in visible_workspaces:
            if workspace_id is not None and item.workspace_id != workspace_id:
                continue
            activity_type = 'workspace_updated'
            summary = f'Workspace \"{item.title}\" was updated.'
            occurred_at = item.updated_at
            if item.created_at and item.created_at == item.updated_at:
                activity_type = 'workspace_created'
                summary = f'Workspace \"{item.title}\" was created.'
                occurred_at = item.created_at
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'workspace:{item.workspace_id}:{occurred_at}',
                    activity_type=activity_type,
                    occurred_at=occurred_at,
                    workspace_id=item.workspace_id,
                    workspace_title=item.title,
                    summary=summary,
                    links=ProductRecentActivityLinks(workspace=item.links.detail),
                )
            )
        user_id = request_auth.requested_by_user_ref or ''
        for row in onboarding_rows:
            row_user_id = str(row.get('user_id') or '').strip()
            row_workspace_id = str(row.get('workspace_id') or '').strip()
            if row_user_id != user_id or not row_workspace_id:
                continue
            if row_workspace_id not in visible_ids:
                continue
            if workspace_id is not None and row_workspace_id != workspace_id:
                continue
            onboarding_state_id = str(row.get('onboarding_state_id') or '').strip()
            occurred_at = str(row.get('updated_at') or '').strip()
            if not onboarding_state_id or not occurred_at:
                continue
            workspace_title = titles.get(row_workspace_id, row_workspace_id)
            current_step = str(row.get('current_step') or '').strip() or 'updated'
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'onboarding:{onboarding_state_id}:{occurred_at}',
                    activity_type='onboarding_updated',
                    occurred_at=occurred_at,
                    workspace_id=row_workspace_id,
                    workspace_title=workspace_title,
                    summary=f'Onboarding state moved to {current_step}.',
                    actor_user_id=row_user_id or None,
                    links=ProductRecentActivityLinks(
                        workspace=f'/api/workspaces/{row_workspace_id}',
                        onboarding=f'/api/users/me/onboarding?workspace_id={row_workspace_id}',
                    ),
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
        for row in provider_binding_rows:
            row_workspace_id = str(row.get('workspace_id') or '').strip()
            if row_workspace_id not in visible_ids:
                continue
            if workspace_id is not None and row_workspace_id != workspace_id:
                continue
            provider_key = str(row.get('provider_key') or '').strip().lower()
            display_name = str(row.get('display_name') or provider_key).strip() or provider_key
            occurred_at = str(row.get('updated_at') or row.get('created_at') or '').strip()
            binding_id = str(row.get('binding_id') or '').strip()
            if not provider_key or not occurred_at or not binding_id:
                continue
            workspace_title = titles.get(row_workspace_id, row_workspace_id)
            status = _binding_activity_status(row)
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'binding:{binding_id}:{occurred_at}',
                    activity_type='provider_binding_updated',
                    occurred_at=occurred_at,
                    workspace_id=row_workspace_id,
                    workspace_title=workspace_title,
                    status=status,
                    summary=f'Provider binding for {display_name} is {status}.',
                    actor_user_id=str(row.get('updated_by_user_id') or '').strip() or None,
                    links=ProductRecentActivityLinks(
                        workspace=f'/api/workspaces/{row_workspace_id}',
                        provider_binding=f'/api/workspaces/{row_workspace_id}/provider-bindings/{provider_key}',
                        provider_health=f'/api/workspaces/{row_workspace_id}/provider-bindings/{provider_key}/health',
                    ),
                )
            )
        for row in managed_secret_rows:
            row_workspace_id = str(row.get('workspace_id') or '').strip()
            if row_workspace_id not in visible_ids:
                continue
            if workspace_id is not None and row_workspace_id != workspace_id:
                continue
            provider_key = str(row.get('provider_key') or '').strip().lower()
            secret_ref = str(row.get('secret_ref') or '').strip()
            occurred_at = str(row.get('last_rotated_at') or '').strip()
            if not row_workspace_id or not provider_key or not secret_ref or not occurred_at:
                continue
            workspace_title = titles.get(row_workspace_id, row_workspace_id)
            display_name = provider_key
            binding_match = next((binding for binding in provider_binding_rows if str(binding.get('workspace_id') or '').strip() == row_workspace_id and str(binding.get('provider_key') or '').strip().lower() == provider_key), None)
            if binding_match is not None:
                display_name = str(binding_match.get('display_name') or provider_key).strip() or provider_key
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'secret:{provider_key}:{secret_ref}:{occurred_at}',
                    activity_type='managed_secret_updated',
                    occurred_at=occurred_at,
                    workspace_id=row_workspace_id,
                    workspace_title=workspace_title,
                    status='resolved',
                    summary=f'Managed secret for {display_name} was updated.',
                    links=ProductRecentActivityLinks(
                        workspace=f'/api/workspaces/{row_workspace_id}',
                        provider_binding=f'/api/workspaces/{row_workspace_id}/provider-bindings/{provider_key}',
                        provider_health=f'/api/workspaces/{row_workspace_id}/provider-bindings/{provider_key}/health',
                        managed_secret=secret_ref,
                    ),
                )
            )

        for row in provider_probe_rows:
            record = ProviderProbeHistoryRecord.from_mapping(row)
            if record is None:
                continue
            if record.workspace_id not in visible_ids:
                continue
            if workspace_id is not None and record.workspace_id != workspace_id:
                continue
            workspace_title = titles.get(record.workspace_id, record.workspace_id)
            probe_status = record.probe_status or None
            activities.append(
                ProductRecentActivityItemView(
                    activity_id=f'probe:{record.probe_event_id}:{record.occurred_at}',
                    activity_type=_probe_activity_type({"probe_status": record.probe_status}),
                    occurred_at=record.occurred_at,
                    workspace_id=record.workspace_id,
                    workspace_title=workspace_title,
                    status=probe_status,
                    summary=f'Provider probe for {record.display_name} is {probe_status or "updated"}.',
                    actor_user_id=record.requested_by_user_id,
                    links=ProductRecentActivityLinks(
                        workspace=f'/api/workspaces/{record.workspace_id}',
                        provider_binding=f'/api/workspaces/{record.workspace_id}/provider-bindings/{record.provider_key}',
                        provider_health=f'/api/workspaces/{record.workspace_id}/provider-bindings/{record.provider_key}/health',
                        provider_probe_history=f'/api/workspaces/{record.workspace_id}/provider-bindings/{record.provider_key}/probe-history',
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
        provider_continuity, activity_continuity = _response_continuity_projection(
            request_auth=request_auth,
            workspace_rows=workspace_rows,
            visible_workspace_ids=tuple(visible_ids),
            workspace_id=workspace_id,
            onboarding_rows=onboarding_rows,
            run_rows=run_rows,
            provider_probe_rows=provider_probe_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
        )
        return RecentActivityReadOutcome(
            response=ProductRecentActivityResponse(
                returned_count=len(page),
                total_visible_count=total_visible_count,
                activities=page,
                applied_filters=ProductRecentActivityAppliedFilters(workspace_id=workspace_id, cursor=cursor, limit=limit),
                next_cursor=next_cursor,
                latest_activity_at=latest_activity_at,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
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
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        workspace_id: Optional[str] = None,
    ) -> HistorySummaryReadOutcome:
        if not request_auth.is_authenticated:
            workspace_title = str((_workspace_row_by_id(workspace_rows, workspace_id) or {}).get('title') or '').strip() or None
            return HistorySummaryReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='history_summary.authentication_required',
                    message='History summary requires an authenticated session.',
                    workspace_id=workspace_id,
                    workspace_title=workspace_title,
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
            workspace_title = str((_workspace_row_by_id(workspace_rows, workspace_id) or {}).get('title') or '').strip() or None
            return HistorySummaryReadOutcome(
                rejected=ProductRecentActivityRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='history_summary.workspace_forbidden',
                    message='Current user is not allowed to read aggregate history for the requested workspace.',
                    workspace_id=workspace_id,
                    workspace_title=workspace_title,
                )
            )
        filtered_workspaces = [
            item for item in visible_workspaces
            if workspace_id is None or item.workspace_id == workspace_id
        ]
        latest_workspace_at = None
        latest_workspace_id = None
        if filtered_workspaces:
            filtered_workspaces = sorted(
                filtered_workspaces,
                key=lambda item: (item.updated_at or item.created_at or '', item.workspace_id),
                reverse=True,
            )
            latest_workspace = filtered_workspaces[0]
            latest_workspace_at = latest_workspace.updated_at or latest_workspace.created_at or None
            latest_workspace_id = latest_workspace.workspace_id
        filtered_runs = [
            row for row in run_rows
            if str(row.get('workspace_id') or '').strip() in visible_ids
            and (workspace_id is None or str(row.get('workspace_id') or '').strip() == workspace_id)
        ]
        latest_run = None
        latest_activity_at = latest_workspace_at
        if filtered_runs:
            filtered_runs.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('run_id') or '')), reverse=True)
            latest_run = filtered_runs[0]
            latest_activity_at = str(latest_run.get('updated_at') or latest_run.get('created_at') or '').strip() or None
        filtered_probe_rows = [
            record for record in (ProviderProbeHistoryRecord.from_mapping(row) for row in provider_probe_rows)
            if record is not None
            and record.workspace_id in visible_ids
            and (workspace_id is None or record.workspace_id == workspace_id)
        ]
        latest_probe = None
        if filtered_probe_rows:
            filtered_probe_rows.sort(key=lambda record: (record.occurred_at, record.probe_event_id), reverse=True)
            latest_probe = filtered_probe_rows[0]
        latest_binding_at = None
        latest_binding_id = None
        filtered_binding_rows = [
            row for row in provider_binding_rows
            if str(row.get('workspace_id') or '').strip() in visible_ids
            and (workspace_id is None or str(row.get('workspace_id') or '').strip() == workspace_id)
            and str(row.get('updated_at') or row.get('created_at') or '').strip()
        ]
        if filtered_binding_rows:
            filtered_binding_rows.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('binding_id') or '')), reverse=True)
            latest_binding_at = str(filtered_binding_rows[0].get('updated_at') or filtered_binding_rows[0].get('created_at') or '').strip() or None
            latest_binding_id = str(filtered_binding_rows[0].get('binding_id') or '').strip() or None
        user_id = request_auth.requested_by_user_ref or ''
        latest_onboarding_at = None
        latest_onboarding_state_id = None
        filtered_onboarding_rows = [
            row for row in onboarding_rows
            if str(row.get('user_id') or '').strip() == user_id
            and str(row.get('workspace_id') or '').strip() in visible_ids
            and (workspace_id is None or str(row.get('workspace_id') or '').strip() == workspace_id)
            and str(row.get('updated_at') or '').strip()
        ]
        if filtered_onboarding_rows:
            filtered_onboarding_rows.sort(key=lambda row: (str(row.get('updated_at') or ''), str(row.get('onboarding_state_id') or '')), reverse=True)
            latest_onboarding_at = str(filtered_onboarding_rows[0].get('updated_at') or '').strip() or None
            latest_onboarding_state_id = str(filtered_onboarding_rows[0].get('onboarding_state_id') or '').strip() or None

        latest_secret_at = None
        latest_secret_ref = None
        filtered_secret_rows = [
            row for row in managed_secret_rows
            if str(row.get('workspace_id') or '').strip() in visible_ids
            and (workspace_id is None or str(row.get('workspace_id') or '').strip() == workspace_id)
            and str(row.get('last_rotated_at') or '').strip()
        ]
        if filtered_secret_rows:
            filtered_secret_rows.sort(key=lambda row: (str(row.get('last_rotated_at') or ''), str(row.get('secret_ref') or '')), reverse=True)
            latest_secret_at = str(filtered_secret_rows[0].get('last_rotated_at') or '').strip() or None
            latest_secret_ref = str(filtered_secret_rows[0].get('secret_ref') or '').strip() or None
        candidate_times = [value for value in (
            latest_activity_at,
            latest_workspace_at,
            latest_binding_at,
            latest_secret_at,
            latest_onboarding_at,
            latest_probe.occurred_at if latest_probe is not None else None,
        ) if value]
        latest_activity_at = max(candidate_times) if candidate_times else None
        pending_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'pending')
        active_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'active')
        terminal_success_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'terminal_success')
        terminal_failure_runs = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'terminal_failure')
        recent_probe_count = len(filtered_probe_rows)
        failed_probe_count = sum(1 for record in filtered_probe_rows if record.probe_status.lower() not in {'reachable', 'warning'})
        recent_provider_binding_count = len(filtered_binding_rows)
        recent_managed_secret_count = len(filtered_secret_rows)
        recent_onboarding_count = len(filtered_onboarding_rows)
        provider_continuity, activity_continuity = _response_continuity_projection(
            request_auth=request_auth,
            workspace_rows=workspace_rows,
            visible_workspace_ids=tuple(visible_ids),
            workspace_id=workspace_id,
            onboarding_rows=onboarding_rows,
            run_rows=run_rows,
            provider_probe_rows=provider_probe_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
        )
        return HistorySummaryReadOutcome(
            response=ProductHistorySummaryResponse(
                scope='workspace' if workspace_id is not None else 'account',
                workspace_id=workspace_id,
                visible_workspace_count=sum(1 for item in visible_workspaces if workspace_id is None or item.workspace_id == workspace_id),
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                total_visible_runs=len(filtered_runs),
                pending_runs=pending_runs,
                active_runs=active_runs,
                terminal_success_runs=terminal_success_runs,
                terminal_failure_runs=terminal_failure_runs,
                recent_workspace_count=len(filtered_workspaces),
                recent_probe_count=recent_probe_count,
                failed_probe_count=failed_probe_count,
                recent_provider_binding_count=recent_provider_binding_count,
                recent_managed_secret_count=recent_managed_secret_count,
                recent_onboarding_count=recent_onboarding_count,
                latest_activity_at=latest_activity_at,
                latest_workspace_id=latest_workspace_id,
                latest_run_id=str(latest_run.get('run_id') or '').strip() or None if latest_run is not None else None,
                latest_probe_event_id=latest_probe.probe_event_id if latest_probe is not None else None,
                latest_provider_binding_id=latest_binding_id,
                latest_managed_secret_ref=latest_secret_ref,
                latest_onboarding_state_id=latest_onboarding_state_id,
            )
        )
