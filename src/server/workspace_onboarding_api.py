from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.provider_probe_history_models import ProviderProbeHistoryRecord
from src.server.run_recovery_projection import aggregate_recovery_projection_for_runs
from src.storage.share_api import describe_public_nex_link_share
from src.server.workspace_onboarding_models import (
    OnboardingReadOutcome,
    OnboardingWriteOutcome,
    ProductOnboardingLinks,
    ProductOnboardingReadResponse,
    ProductActivityContinuitySummary,
    ProductProviderContinuitySummary,
    ProductOnboardingRejectedResponse,
    ProductOnboardingStateView,
    ProductOnboardingWriteAcceptedResponse,
    ProductOnboardingWriteRequest,
    ProductWorkspaceCreateRequest,
    ProductWorkspaceDetailResponse,
    ProductWorkspaceLinks,
    ProductWorkspaceListResponse,
    ProductWorkspaceReadRejectedResponse,
    ProductWorkspaceSummaryView,
    ProductWorkspaceWriteAcceptedResponse,
    ProductWorkspaceWriteRejectedResponse,
    WorkspaceListOutcome,
    WorkspaceReadOutcome,
    WorkspaceWriteOutcome,
)

_ALLOWED_LIST_ROLES = ('owner', 'admin', 'editor', 'collaborator', 'reviewer', 'viewer')


def _workspace_links(workspace_id: str) -> ProductWorkspaceLinks:
    return ProductWorkspaceLinks(
        detail=f'/api/workspaces/{workspace_id}',
        runs=f'/api/workspaces/{workspace_id}/runs',
        onboarding=f'/api/users/me/onboarding?workspace_id={workspace_id}',
    )


def _normalize_role(value: Any) -> Optional[str]:
    role = str(value or '').strip().lower()
    return role or None


def _lookup_membership_role(user_id: str, workspace_id: str, membership_rows: Sequence[Mapping[str, Any]]) -> Optional[str]:
    for row in membership_rows:
        if str(row.get('workspace_id') or '').strip() != workspace_id:
            continue
        if str(row.get('user_id') or '').strip() != user_id:
            continue
        role = _normalize_role(row.get('role'))
        if role:
            return role
    return None


def _resolved_workspace_role(user_id: str, workspace_row: Mapping[str, Any], membership_rows: Sequence[Mapping[str, Any]]) -> Optional[str]:
    workspace_id = str(workspace_row.get('workspace_id') or '').strip()
    owner_user_id = str(workspace_row.get('owner_user_id') or '').strip()
    if user_id and owner_user_id and user_id == owner_user_id:
        return 'owner'
    membership_role = _lookup_membership_role(user_id, workspace_id, membership_rows)
    if membership_role in _ALLOWED_LIST_ROLES:
        return membership_role
    return None


def _visible_workspace_ids_for_user(
    user_id: str,
    workspace_rows: Sequence[Mapping[str, Any]],
    membership_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    normalized_user_id = str(user_id or '').strip()
    return [
        str(row.get('workspace_id') or '').strip()
        for row in workspace_rows
        if _resolved_workspace_role(normalized_user_id, row, membership_rows) is not None
    ]


def _share_workspace_id_from_descriptor(descriptor: Any) -> str | None:
    storage_role = str(getattr(descriptor, 'storage_role', '') or '').strip()
    source_working_save_id = str(getattr(descriptor, 'source_working_save_id', '') or '').strip()
    canonical_ref = str(getattr(descriptor, 'canonical_ref', '') or '').strip()
    if source_working_save_id:
        return source_working_save_id
    if storage_role == 'working_save' and canonical_ref:
        return canonical_ref
    return None


def _visible_share_descriptors_for_workspace_ids(
    workspace_ids: Sequence[str],
    *,
    user_id: str,
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
) -> list[Any]:
    normalized_ids = {str(workspace_id or '').strip() for workspace_id in workspace_ids if str(workspace_id or '').strip()}
    normalized_user_id = str(user_id or '').strip()
    descriptors: list[Any] = []
    if not normalized_ids or not normalized_user_id:
        return descriptors
    for row in share_payload_rows:
        if not isinstance(row, Mapping):
            continue
        try:
            descriptor = describe_public_nex_link_share(row)
        except (TypeError, ValueError):
            continue
        if str(getattr(descriptor, 'issued_by_user_ref', '') or '').strip() != normalized_user_id:
            continue
        workspace_id = _share_workspace_id_from_descriptor(descriptor)
        if workspace_id not in normalized_ids:
            continue
        descriptors.append(descriptor)
    return descriptors


def _share_descriptor_sort_key(descriptor: Any) -> tuple[str, str]:
    return (
        str(getattr(descriptor, 'updated_at', '') or getattr(descriptor, 'created_at', '') or '').strip(),
        str(getattr(descriptor, 'share_id', '') or '').strip(),
    )


def _share_continuity_projection_for_workspace_ids(
    workspace_ids: Sequence[str],
    *,
    user_id: str,
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
) -> tuple[int, str | None, str | None]:
    descriptors = _visible_share_descriptors_for_workspace_ids(
        workspace_ids,
        user_id=user_id,
        share_payload_rows=share_payload_rows,
    )
    descriptors.sort(key=_share_descriptor_sort_key, reverse=True)
    if not descriptors:
        return 0, None, None
    latest = descriptors[0]
    latest_share_at = _share_descriptor_sort_key(latest)[0] or None
    latest_share_id = str(getattr(latest, 'share_id', '') or '').strip() or None
    return len(descriptors), latest_share_id, latest_share_at


def _latest_run_for_workspace(workspace_id: str, run_rows: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    candidates = [row for row in run_rows if str(row.get('workspace_id') or '').strip() == workspace_id]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: (str(row.get('created_at') or ''), str(row.get('run_id') or '')), reverse=True)[0]


def _provider_continuity_summary_for_workspace(
    workspace_id: str,
    *,
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
) -> Optional[ProductProviderContinuitySummary]:
    normalized_workspace_id = str(workspace_id or '').strip()
    if not normalized_workspace_id:
        return None
    filtered_binding_rows = [
        row for row in provider_binding_rows
        if str(row.get('workspace_id') or '').strip() == normalized_workspace_id
    ]
    filtered_secret_rows = [
        row for row in managed_secret_rows
        if str(row.get('workspace_id') or '').strip() == normalized_workspace_id
    ]
    filtered_probe_rows = [
        record for record in (ProviderProbeHistoryRecord.from_mapping(row) for row in provider_probe_rows)
        if record is not None and record.workspace_id == normalized_workspace_id
    ]
    if not filtered_binding_rows and not filtered_secret_rows and not filtered_probe_rows:
        return None
    latest_binding_at = None
    latest_binding_id = None
    if filtered_binding_rows:
        filtered_binding_rows.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('binding_id') or '')), reverse=True)
        latest_binding_at = str(filtered_binding_rows[0].get('updated_at') or filtered_binding_rows[0].get('created_at') or '').strip() or None
        latest_binding_id = str(filtered_binding_rows[0].get('binding_id') or '').strip() or None
    latest_secret_at = None
    latest_secret_ref = None
    if filtered_secret_rows:
        filtered_secret_rows.sort(key=lambda row: (str(row.get('last_rotated_at') or ''), str(row.get('secret_ref') or '')), reverse=True)
        latest_secret_at = str(filtered_secret_rows[0].get('last_rotated_at') or '').strip() or None
        latest_secret_ref = str(filtered_secret_rows[0].get('secret_ref') or '').strip() or None
    latest_probe = None
    if filtered_probe_rows:
        filtered_probe_rows.sort(key=lambda record: (record.occurred_at, record.probe_event_id), reverse=True)
        latest_probe = filtered_probe_rows[0]
    latest_provider_activity_at = max(
        [value for value in (latest_binding_at, latest_secret_at, latest_probe.occurred_at if latest_probe is not None else None) if value],
        default=None,
    )
    return ProductProviderContinuitySummary(
        provider_binding_count=len(filtered_binding_rows),
        managed_secret_count=len(filtered_secret_rows),
        recent_probe_count=len(filtered_probe_rows),
        latest_provider_binding_id=latest_binding_id,
        latest_managed_secret_ref=latest_secret_ref,
        latest_probe_event_id=latest_probe.probe_event_id if latest_probe is not None else None,
        latest_provider_activity_at=latest_provider_activity_at,
    )


def _activity_continuity_summary_for_workspace(
    workspace_id: str,
    *,
    user_id: str,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
) -> Optional[ProductActivityContinuitySummary]:
    normalized_workspace_id = str(workspace_id or '').strip()
    normalized_user_id = str(user_id or '').strip()
    if not normalized_workspace_id:
        return None
    filtered_runs = [
        row for row in recent_run_rows
        if str(row.get('workspace_id') or '').strip() == normalized_workspace_id
    ]
    filtered_binding_rows = [
        row for row in provider_binding_rows
        if str(row.get('workspace_id') or '').strip() == normalized_workspace_id
    ]
    filtered_secret_rows = [
        row for row in managed_secret_rows
        if str(row.get('workspace_id') or '').strip() == normalized_workspace_id
    ]
    filtered_probe_rows = [
        record for record in (ProviderProbeHistoryRecord.from_mapping(row) for row in provider_probe_rows)
        if record is not None and record.workspace_id == normalized_workspace_id
    ]
    filtered_onboarding_rows = [
        row for row in onboarding_rows
        if str(row.get('workspace_id') or '').strip() == normalized_workspace_id
        and str(row.get('user_id') or '').strip() == normalized_user_id
    ]
    recent_share_history_count, latest_share_id, latest_share_at = _share_continuity_projection_for_workspace_ids(
        (normalized_workspace_id,),
        user_id=normalized_user_id,
        share_payload_rows=share_payload_rows,
    )
    if not filtered_runs and not filtered_binding_rows and not filtered_secret_rows and not filtered_probe_rows and not filtered_onboarding_rows and recent_share_history_count <= 0:
        return None
    latest_run_at = None
    latest_run_id = None
    if filtered_runs:
        filtered_runs.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('run_id') or '')), reverse=True)
        latest_run_at = str(filtered_runs[0].get('updated_at') or filtered_runs[0].get('created_at') or '').strip() or None
        latest_run_id = str(filtered_runs[0].get('run_id') or '').strip() or None
    latest_binding_at = None
    latest_binding_id = None
    if filtered_binding_rows:
        filtered_binding_rows.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('binding_id') or '')), reverse=True)
        latest_binding_at = str(filtered_binding_rows[0].get('updated_at') or filtered_binding_rows[0].get('created_at') or '').strip() or None
        latest_binding_id = str(filtered_binding_rows[0].get('binding_id') or '').strip() or None
    latest_secret_at = None
    latest_secret_ref = None
    if filtered_secret_rows:
        filtered_secret_rows.sort(key=lambda row: (str(row.get('last_rotated_at') or ''), str(row.get('secret_ref') or '')), reverse=True)
        latest_secret_at = str(filtered_secret_rows[0].get('last_rotated_at') or '').strip() or None
        latest_secret_ref = str(filtered_secret_rows[0].get('secret_ref') or '').strip() or None
    latest_probe = None
    if filtered_probe_rows:
        filtered_probe_rows.sort(key=lambda record: (record.occurred_at, record.probe_event_id), reverse=True)
        latest_probe = filtered_probe_rows[0]
    latest_onboarding_at = None
    latest_onboarding_state_id = None
    if filtered_onboarding_rows:
        filtered_onboarding_rows.sort(key=lambda row: (str(row.get('updated_at') or ''), str(row.get('onboarding_state_id') or '')), reverse=True)
        latest_onboarding_at = str(filtered_onboarding_rows[0].get('updated_at') or '').strip() or None
        latest_onboarding_state_id = str(filtered_onboarding_rows[0].get('onboarding_state_id') or '').strip() or None
    latest_activity_at = max([
        value for value in (
            latest_run_at,
            latest_binding_at,
            latest_secret_at,
            latest_probe.occurred_at if latest_probe is not None else None,
            latest_onboarding_at,
            latest_share_at,
        ) if value
    ], default=None)
    pending_run_count = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'pending')
    active_run_count = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'active')
    terminal_failure_run_count = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'terminal_failure')
    failed_probe_count = sum(1 for record in filtered_probe_rows if record.probe_status.lower() not in {'reachable', 'warning'})
    return ProductActivityContinuitySummary(
        recent_run_count=len(filtered_runs),
        pending_run_count=pending_run_count,
        active_run_count=active_run_count,
        terminal_failure_run_count=terminal_failure_run_count,
        recent_probe_count=len(filtered_probe_rows),
        failed_probe_count=failed_probe_count,
        recent_provider_binding_count=len(filtered_binding_rows),
        recent_managed_secret_count=len(filtered_secret_rows),
        recent_onboarding_count=len(filtered_onboarding_rows),
        recent_share_history_count=recent_share_history_count,
        latest_activity_at=latest_activity_at,
        latest_run_id=latest_run_id,
        latest_probe_event_id=latest_probe.probe_event_id if latest_probe is not None else None,
        latest_provider_binding_id=latest_binding_id,
        latest_managed_secret_ref=latest_secret_ref,
        latest_onboarding_state_id=latest_onboarding_state_id,
        latest_share_id=latest_share_id,
    )




def _provider_continuity_summary_for_workspace_ids(
    workspace_ids: Sequence[str],
    *,
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
) -> Optional[ProductProviderContinuitySummary]:
    normalized_ids = {str(workspace_id or '').strip() for workspace_id in workspace_ids if str(workspace_id or '').strip()}
    if not normalized_ids:
        return None
    filtered_binding_rows = [
        row for row in provider_binding_rows
        if str(row.get('workspace_id') or '').strip() in normalized_ids
    ]
    filtered_secret_rows = [
        row for row in managed_secret_rows
        if str(row.get('workspace_id') or '').strip() in normalized_ids
    ]
    filtered_probe_rows = [
        record for record in (ProviderProbeHistoryRecord.from_mapping(row) for row in provider_probe_rows)
        if record is not None and record.workspace_id in normalized_ids
    ]
    if not filtered_binding_rows and not filtered_secret_rows and not filtered_probe_rows:
        return None
    latest_binding_at = None
    latest_binding_id = None
    if filtered_binding_rows:
        filtered_binding_rows.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('binding_id') or '')), reverse=True)
        latest_binding_at = str(filtered_binding_rows[0].get('updated_at') or filtered_binding_rows[0].get('created_at') or '').strip() or None
        latest_binding_id = str(filtered_binding_rows[0].get('binding_id') or '').strip() or None
    latest_secret_at = None
    latest_secret_ref = None
    if filtered_secret_rows:
        filtered_secret_rows.sort(key=lambda row: (str(row.get('last_rotated_at') or ''), str(row.get('secret_ref') or '')), reverse=True)
        latest_secret_at = str(filtered_secret_rows[0].get('last_rotated_at') or '').strip() or None
        latest_secret_ref = str(filtered_secret_rows[0].get('secret_ref') or '').strip() or None
    latest_probe = None
    if filtered_probe_rows:
        filtered_probe_rows.sort(key=lambda record: (record.occurred_at, record.probe_event_id), reverse=True)
        latest_probe = filtered_probe_rows[0]
    latest_provider_activity_at = max(
        [value for value in (latest_binding_at, latest_secret_at, latest_probe.occurred_at if latest_probe is not None else None) if value],
        default=None,
    )
    return ProductProviderContinuitySummary(
        provider_binding_count=len(filtered_binding_rows),
        managed_secret_count=len(filtered_secret_rows),
        recent_probe_count=len(filtered_probe_rows),
        latest_provider_binding_id=latest_binding_id,
        latest_managed_secret_ref=latest_secret_ref,
        latest_probe_event_id=latest_probe.probe_event_id if latest_probe is not None else None,
        latest_provider_activity_at=latest_provider_activity_at,
    )


def _activity_continuity_summary_for_workspace_ids(
    workspace_ids: Sequence[str],
    *,
    user_id: str,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
) -> Optional[ProductActivityContinuitySummary]:
    normalized_ids = {str(workspace_id or '').strip() for workspace_id in workspace_ids if str(workspace_id or '').strip()}
    normalized_user_id = str(user_id or '').strip()
    if not normalized_ids:
        return None
    filtered_runs = [
        row for row in recent_run_rows
        if str(row.get('workspace_id') or '').strip() in normalized_ids
    ]
    filtered_binding_rows = [
        row for row in provider_binding_rows
        if str(row.get('workspace_id') or '').strip() in normalized_ids
    ]
    filtered_secret_rows = [
        row for row in managed_secret_rows
        if str(row.get('workspace_id') or '').strip() in normalized_ids
    ]
    filtered_probe_rows = [
        record for record in (ProviderProbeHistoryRecord.from_mapping(row) for row in provider_probe_rows)
        if record is not None and record.workspace_id in normalized_ids
    ]
    filtered_onboarding_rows = [
        row for row in onboarding_rows
        if str(row.get('workspace_id') or '').strip() in normalized_ids
        and str(row.get('user_id') or '').strip() == normalized_user_id
    ]
    recent_share_history_count, latest_share_id, latest_share_at = _share_continuity_projection_for_workspace_ids(
        tuple(normalized_ids),
        user_id=normalized_user_id,
        share_payload_rows=share_payload_rows,
    )
    if not filtered_runs and not filtered_binding_rows and not filtered_secret_rows and not filtered_probe_rows and not filtered_onboarding_rows and recent_share_history_count <= 0:
        return None
    latest_run_at = None
    latest_run_id = None
    if filtered_runs:
        filtered_runs.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('run_id') or '')), reverse=True)
        latest_run_at = str(filtered_runs[0].get('updated_at') or filtered_runs[0].get('created_at') or '').strip() or None
        latest_run_id = str(filtered_runs[0].get('run_id') or '').strip() or None
    latest_binding_at = None
    latest_binding_id = None
    if filtered_binding_rows:
        filtered_binding_rows.sort(key=lambda row: (str(row.get('updated_at') or row.get('created_at') or ''), str(row.get('binding_id') or '')), reverse=True)
        latest_binding_at = str(filtered_binding_rows[0].get('updated_at') or filtered_binding_rows[0].get('created_at') or '').strip() or None
        latest_binding_id = str(filtered_binding_rows[0].get('binding_id') or '').strip() or None
    latest_secret_at = None
    latest_secret_ref = None
    if filtered_secret_rows:
        filtered_secret_rows.sort(key=lambda row: (str(row.get('last_rotated_at') or ''), str(row.get('secret_ref') or '')), reverse=True)
        latest_secret_at = str(filtered_secret_rows[0].get('last_rotated_at') or '').strip() or None
        latest_secret_ref = str(filtered_secret_rows[0].get('secret_ref') or '').strip() or None
    latest_probe = None
    if filtered_probe_rows:
        filtered_probe_rows.sort(key=lambda record: (record.occurred_at, record.probe_event_id), reverse=True)
        latest_probe = filtered_probe_rows[0]
    latest_onboarding_at = None
    latest_onboarding_state_id = None
    if filtered_onboarding_rows:
        filtered_onboarding_rows.sort(key=lambda row: (str(row.get('updated_at') or ''), str(row.get('onboarding_state_id') or '')), reverse=True)
        latest_onboarding_at = str(filtered_onboarding_rows[0].get('updated_at') or '').strip() or None
        latest_onboarding_state_id = str(filtered_onboarding_rows[0].get('onboarding_state_id') or '').strip() or None
    latest_activity_at = max([
        value for value in (
            latest_run_at,
            latest_binding_at,
            latest_secret_at,
            latest_probe.occurred_at if latest_probe is not None else None,
            latest_onboarding_at,
            latest_share_at,
        ) if value
    ], default=None)
    pending_run_count = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'pending')
    active_run_count = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'active')
    terminal_failure_run_count = sum(1 for row in filtered_runs if str(row.get('status_family') or '').strip() == 'terminal_failure')
    failed_probe_count = sum(1 for record in filtered_probe_rows if record.probe_status.lower() not in {'reachable', 'warning'})
    return ProductActivityContinuitySummary(
        recent_run_count=len(filtered_runs),
        pending_run_count=pending_run_count,
        active_run_count=active_run_count,
        terminal_failure_run_count=terminal_failure_run_count,
        recent_probe_count=len(filtered_probe_rows),
        failed_probe_count=failed_probe_count,
        recent_provider_binding_count=len(filtered_binding_rows),
        recent_managed_secret_count=len(filtered_secret_rows),
        recent_onboarding_count=len(filtered_onboarding_rows),
        recent_share_history_count=recent_share_history_count,
        latest_activity_at=latest_activity_at,
        latest_run_id=latest_run_id,
        latest_probe_event_id=latest_probe.probe_event_id if latest_probe is not None else None,
        latest_provider_binding_id=latest_binding_id,
        latest_managed_secret_ref=latest_secret_ref,
        latest_onboarding_state_id=latest_onboarding_state_id,
        latest_share_id=latest_share_id,
    )


def _continuity_projection_for_workspace_ids(
    workspace_ids: Sequence[str],
    *,
    user_id: str,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
) -> tuple[Optional[ProductProviderContinuitySummary], Optional[ProductActivityContinuitySummary]]:
    return (
        _provider_continuity_summary_for_workspace_ids(
            workspace_ids,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        ),
        _activity_continuity_summary_for_workspace_ids(
            workspace_ids,
            user_id=user_id,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            share_payload_rows=share_payload_rows,
        ),
    )

def _detail_from_workspace_row(
    workspace_row: Mapping[str, Any],
    *,
    role: str,
    current_user_id: str,
    membership_rows: Sequence[Mapping[str, Any]] = (),
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
) -> ProductWorkspaceDetailResponse:
    workspace_id = str(workspace_row.get('workspace_id') or '').strip()
    latest_run = _latest_run_for_workspace(workspace_id, recent_run_rows)
    workspace_run_rows = [
        row for row in recent_run_rows
        if str(row.get('workspace_id') or '').strip() == workspace_id
    ]
    recovery_projection = aggregate_recovery_projection_for_runs(workspace_run_rows)
    last_run_id = str(workspace_row.get('last_run_id') or '').strip() or (str(latest_run.get('run_id') or '').strip() if latest_run else None)
    last_result_status = str(workspace_row.get('last_result_status') or '').strip() or (str(latest_run.get('status') or '').strip() if latest_run else None)
    collaborator_ids = {
        str(row.get('user_id') or '').strip()
        for row in membership_rows
        if str(row.get('workspace_id') or '').strip() == workspace_id and str(row.get('user_id') or '').strip()
    }
    provider_continuity = _provider_continuity_summary_for_workspace(
        workspace_id,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    activity_continuity = _activity_continuity_summary_for_workspace(
        workspace_id,
        user_id=current_user_id,
        recent_run_rows=recent_run_rows,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
        onboarding_rows=onboarding_rows,
        share_payload_rows=share_payload_rows,
    )
    return ProductWorkspaceDetailResponse(
        workspace_id=workspace_id,
        title=str(workspace_row.get('title') or '').strip() or workspace_id,
        description=str(workspace_row.get('description') or '').strip() or None,
        role=role,
        owner_user_id=str(workspace_row.get('owner_user_id') or '').strip() or None,
        collaborator_count=len(collaborator_ids),
        last_run_id=last_run_id,
        last_result_status=last_result_status,
        recovery_state=recovery_projection.recovery_state if recovery_projection is not None else None,
        latest_error_family=recovery_projection.latest_error_family if recovery_projection is not None else None,
        orphan_review_required=recovery_projection.orphan_review_required if recovery_projection is not None else False,
        worker_attempt_number=recovery_projection.worker_attempt_number if recovery_projection is not None else 0,
        continuity_source=str(workspace_row.get('continuity_source') or '').strip() or None,
        archived=bool(workspace_row.get('archived')),
        provider_continuity=provider_continuity,
        activity_continuity=activity_continuity,
        created_at=str(workspace_row.get('created_at') or '').strip() or None,
        updated_at=str(workspace_row.get('updated_at') or '').strip() or (str(latest_run.get('updated_at') or '').strip() if latest_run else ''),
        links=_workspace_links(workspace_id),
    )

def _continuity_projection_for_workspace(
    workspace_id: str,
    *,
    workspace_row: Mapping[str, Any] | None = None,
    user_id: str,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
) -> tuple[Optional[str], Optional[ProductProviderContinuitySummary], Optional[ProductActivityContinuitySummary]]:
    normalized_workspace_id = str(workspace_id or '').strip()
    if not normalized_workspace_id:
        return None, None, None
    workspace_title = str((workspace_row or {}).get('title') or '').strip() or None
    provider_continuity = _provider_continuity_summary_for_workspace(
        normalized_workspace_id,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    activity_continuity = _activity_continuity_summary_for_workspace(
        normalized_workspace_id,
        user_id=user_id,
        recent_run_rows=recent_run_rows,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
        onboarding_rows=onboarding_rows,
        share_payload_rows=share_payload_rows,
    )
    return workspace_title, provider_continuity, activity_continuity



class WorkspaceRegistryService:
    @classmethod
    def list_workspaces(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        share_payload_rows: Sequence[Mapping[str, Any]] = (),
    ) -> WorkspaceListOutcome:
        if not request_auth.is_authenticated:
            return WorkspaceListOutcome(
                rejected=ProductWorkspaceReadRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='workspace_list.authentication_required',
                    message='Workspace list requires an authenticated session.',
                )
            )
        user_id = request_auth.requested_by_user_ref or ''
        visible: list[ProductWorkspaceSummaryView] = []
        for row in workspace_rows:
            role = _resolved_workspace_role(user_id, row, membership_rows)
            if role is None:
                continue
            detail = _detail_from_workspace_row(
                row,
                role=role,
                current_user_id=user_id,
                membership_rows=membership_rows,
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
                share_payload_rows=share_payload_rows,
            )
            visible.append(
                ProductWorkspaceSummaryView(
                    workspace_id=detail.workspace_id,
                    title=detail.title,
                    role=detail.role,
                    updated_at=detail.updated_at,
                    created_at=detail.created_at,
                    last_run_id=detail.last_run_id,
                    last_result_status=detail.last_result_status,
                    recovery_state=detail.recovery_state,
                    latest_error_family=detail.latest_error_family,
                    orphan_review_required=detail.orphan_review_required,
                    worker_attempt_number=detail.worker_attempt_number,
                    archived=detail.archived,
                    provider_continuity=detail.provider_continuity,
                    activity_continuity=detail.activity_continuity,
                    links=detail.links,
                )
            )
        visible.sort(key=lambda item: (item.updated_at, item.workspace_id), reverse=True)
        workspace_ids = tuple(item.workspace_id for item in visible)
        provider_continuity, activity_continuity = _continuity_projection_for_workspace_ids(
            workspace_ids,
            user_id=user_id,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            share_payload_rows=share_payload_rows,
        )
        return WorkspaceListOutcome(
            response=ProductWorkspaceListResponse(
                returned_count=len(visible),
                workspaces=tuple(visible),
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )

    @classmethod
    def read_workspace(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        share_payload_rows: Sequence[Mapping[str, Any]] = (),
    ) -> WorkspaceReadOutcome:
        if not request_auth.is_authenticated:
            return WorkspaceReadOutcome(
                rejected=ProductWorkspaceReadRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='workspace_read.authentication_required',
                    message='Workspace detail requires an authenticated session.',
                    workspace_id=workspace_context.workspace_id if workspace_context else None,
                    workspace_title=str((workspace_row or {}).get('title') or '').strip() or None,
                )
            )
        if workspace_context is None or workspace_row is None:
            return WorkspaceReadOutcome(
                rejected=ProductWorkspaceReadRejectedResponse(
                    failure_family='workspace_not_found',
                    reason_code='workspace_read.workspace_not_found',
                    message='Requested workspace was not found.',
                    workspace_id=workspace_context.workspace_id if workspace_context else None,
                    workspace_title=str((workspace_row or {}).get('title') or '').strip() or None,
                )
            )
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or '',
            workspace_id=workspace_context.workspace_id,
            requested_action='read',
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
                workspace_context.workspace_id,
                workspace_row=workspace_row,
                user_id=request_auth.requested_by_user_ref or '',
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
                share_payload_rows=share_payload_rows,
            )
            return WorkspaceReadOutcome(
                rejected=ProductWorkspaceReadRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code=f'workspace_read.{decision.reason_code}',
                    message='Current user is not allowed to read the requested workspace.',
                    workspace_id=workspace_context.workspace_id,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        detail = _detail_from_workspace_row(
            workspace_row,
            role=decision.resolved_role or 'viewer',
            current_user_id=request_auth.requested_by_user_ref or '',
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            share_payload_rows=share_payload_rows,
        )
        return WorkspaceReadOutcome(response=detail)

    @classmethod
    def create_workspace(
        cls,
        *,
        request_auth: RequestAuthContext,
        request: ProductWorkspaceCreateRequest,
        workspace_id_factory,
        membership_id_factory,
        now_iso: str,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        share_payload_rows: Sequence[Mapping[str, Any]] = (),
    ) -> WorkspaceWriteOutcome:
        if not request_auth.is_authenticated:
            return WorkspaceWriteOutcome(
                rejected=ProductWorkspaceWriteRejectedResponse(
                    failure_family='product_write_failure',
                    reason_code='workspace_write.authentication_required',
                    message='Workspace creation requires an authenticated session.',
                )
            )
        workspace_id = workspace_id_factory()
        owner_user_id = request_auth.requested_by_user_ref or ''
        workspace_row = {
            'workspace_id': workspace_id,
            'owner_user_id': owner_user_id,
            'description': request.description,
            'title': request.title.strip(),
            'created_at': now_iso,
            'updated_at': now_iso,
            'last_run_id': None,
            'last_result_status': None,
            'continuity_source': 'server',
            'archived': False,
        }
        membership_row = {
            'membership_id': membership_id_factory(),
            'workspace_id': workspace_id,
            'user_id': owner_user_id,
            'role': 'owner',
            'created_at': now_iso,
            'updated_at': now_iso,
        }
        combined_workspace_rows = tuple(workspace_rows) + (workspace_row,)
        combined_membership_rows = tuple(membership_rows) + (membership_row,)
        detail = _detail_from_workspace_row(
            workspace_row,
            role='owner',
            current_user_id=owner_user_id,
            membership_rows=combined_membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            share_payload_rows=share_payload_rows,
        )
        visible_workspace_ids = _visible_workspace_ids_for_user(owner_user_id, combined_workspace_rows, combined_membership_rows)
        provider_continuity, activity_continuity = _continuity_projection_for_workspace_ids(
            visible_workspace_ids,
            user_id=owner_user_id,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            share_payload_rows=share_payload_rows,
        )
        return WorkspaceWriteOutcome(
            accepted=ProductWorkspaceWriteAcceptedResponse(
                status='accepted',
                workspace=detail,
                owner_membership_id=str(membership_row['membership_id']),
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                message='Workspace continuity has been initialized on the server.',
            ),
            created_workspace_row=workspace_row,
            created_membership_row=membership_row,
        )


class OnboardingContinuityService:
    @staticmethod
    def _scope(workspace_id: Optional[str]) -> str:
        return 'workspace' if workspace_id else 'user'

    @staticmethod
    def _links(workspace_id: Optional[str]) -> ProductOnboardingLinks:
        self_ref = '/api/users/me/onboarding'
        if workspace_id:
            self_ref = f'{self_ref}?workspace_id={workspace_id}'
        return ProductOnboardingLinks(self_ref=self_ref, workspace=f'/api/workspaces/{workspace_id}' if workspace_id else None)

    @classmethod
    def _resolve_state_row(
        cls,
        *,
        request_auth: RequestAuthContext,
        onboarding_rows: Sequence[Mapping[str, Any]],
        workspace_id: Optional[str],
    ) -> Optional[Mapping[str, Any]]:
        user_id = request_auth.requested_by_user_ref or ''
        target_workspace = str(workspace_id).strip() if workspace_id else None
        for row in onboarding_rows:
            if str(row.get('user_id') or '').strip() != user_id:
                continue
            row_workspace = str(row.get('workspace_id') or '').strip() or None
            if row_workspace == target_workspace:
                return row
        return None

    @classmethod
    def read_onboarding_state(
        cls,
        *,
        request_auth: RequestAuthContext,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
        workspace_id: Optional[str] = None,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        share_payload_rows: Sequence[Mapping[str, Any]] = (),
    ) -> OnboardingReadOutcome:
        if not request_auth.is_authenticated:
            return OnboardingReadOutcome(
                rejected=ProductOnboardingRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='onboarding.authentication_required',
                    message='Onboarding continuity requires an authenticated session.',
                    workspace_id=workspace_id,
                )
            )
        normalized_workspace_id = str(workspace_id or '').strip() or None
        if normalized_workspace_id is not None:
            if workspace_context is None:
                return OnboardingReadOutcome(
                    rejected=ProductOnboardingRejectedResponse(
                        failure_family='product_read_failure',
                        reason_code='onboarding.workspace_not_found',
                        message='Requested workspace continuity scope was not found.',
                        workspace_id=normalized_workspace_id,
                    )
                )
            auth_input = AuthorizationInput(
                user_id=request_auth.requested_by_user_ref or '',
                workspace_id=workspace_context.workspace_id,
                requested_action='read',
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
            )
            decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
            if not decision.allowed:
                workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
                    normalized_workspace_id or '',
                    workspace_row=None,
                    user_id=request_auth.requested_by_user_ref or '',
                    recent_run_rows=recent_run_rows,
                    provider_binding_rows=provider_binding_rows,
                    managed_secret_rows=managed_secret_rows,
                    provider_probe_rows=provider_probe_rows,
                    onboarding_rows=onboarding_rows,
                    share_payload_rows=share_payload_rows,
                )
                return OnboardingReadOutcome(
                    rejected=ProductOnboardingRejectedResponse(
                        failure_family='product_read_failure',
                        reason_code=f'onboarding.{decision.reason_code}',
                        message='Current user is not allowed to read onboarding continuity for this workspace.',
                        workspace_id=normalized_workspace_id,
                        workspace_title=workspace_title,
                        provider_continuity=provider_continuity,
                        activity_continuity=activity_continuity,
                    )
                )
        row = cls._resolve_state_row(request_auth=request_auth, onboarding_rows=onboarding_rows, workspace_id=normalized_workspace_id)
        state = ProductOnboardingStateView(
            onboarding_state_id=str(row.get('onboarding_state_id') or '').strip() or None if row else None,
            user_id=request_auth.requested_by_user_ref or '',
            workspace_id=normalized_workspace_id,
            first_success_achieved=bool(row.get('first_success_achieved')) if row else False,
            advanced_surfaces_unlocked=bool(row.get('advanced_surfaces_unlocked')) if row else False,
            dismissed_guidance_state=dict(row.get('dismissed_guidance_state') or {}) if row else {},
            current_step=str(row.get('current_step') or '').strip() or None if row else None,
            updated_at=str(row.get('updated_at') or '').strip() or None if row else None,
        )
        if normalized_workspace_id is not None:
            provider_continuity = _provider_continuity_summary_for_workspace(
                normalized_workspace_id or '',
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
            )
            activity_continuity = _activity_continuity_summary_for_workspace(
                normalized_workspace_id or '',
                user_id=request_auth.requested_by_user_ref or '',
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
                share_payload_rows=share_payload_rows,
            )
        else:
            visible_workspace_ids = _visible_workspace_ids_for_user(
                request_auth.requested_by_user_ref or '',
                workspace_rows,
                membership_rows,
            )
            provider_continuity, activity_continuity = _continuity_projection_for_workspace_ids(
                visible_workspace_ids,
                user_id=request_auth.requested_by_user_ref or '',
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
                share_payload_rows=share_payload_rows,
            )
        return OnboardingReadOutcome(
            response=ProductOnboardingReadResponse(
                continuity_scope=cls._scope(normalized_workspace_id),
                state=state,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                links=cls._links(normalized_workspace_id),
                message=None if row else 'No canonical onboarding continuity has been recorded yet.',
            )
        )

    @classmethod
    def upsert_onboarding_state(
        cls,
        *,
        request_auth: RequestAuthContext,
        request: ProductOnboardingWriteRequest,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
        onboarding_state_id_factory,
        now_iso: str,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        share_payload_rows: Sequence[Mapping[str, Any]] = (),
    ) -> OnboardingWriteOutcome:
        if not request_auth.is_authenticated:
            return OnboardingWriteOutcome(
                rejected=ProductOnboardingRejectedResponse(
                    failure_family='product_write_failure',
                    reason_code='onboarding_write.authentication_required',
                    message='Writing onboarding continuity requires an authenticated session.',
                    workspace_id=request.workspace_id,
                )
            )
        normalized_workspace_id = str(request.workspace_id or '').strip() or None
        if normalized_workspace_id is not None:
            if workspace_context is None:
                return OnboardingWriteOutcome(
                    rejected=ProductOnboardingRejectedResponse(
                        failure_family='product_write_failure',
                        reason_code='onboarding_write.workspace_not_found',
                        message='Requested workspace continuity scope was not found.',
                        workspace_id=normalized_workspace_id,
                    )
                )
            auth_input = AuthorizationInput(
                user_id=request_auth.requested_by_user_ref or '',
                workspace_id=workspace_context.workspace_id,
                requested_action='update',
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
            )
            decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
            if not decision.allowed:
                workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
                    normalized_workspace_id or '',
                    workspace_row=None,
                    user_id=request_auth.requested_by_user_ref or '',
                    recent_run_rows=recent_run_rows,
                    provider_binding_rows=provider_binding_rows,
                    managed_secret_rows=managed_secret_rows,
                    provider_probe_rows=provider_probe_rows,
                    onboarding_rows=onboarding_rows,
                    share_payload_rows=share_payload_rows,
                )
                return OnboardingWriteOutcome(
                    rejected=ProductOnboardingRejectedResponse(
                        failure_family='product_write_failure',
                        reason_code=f'onboarding_write.{decision.reason_code}',
                        message='Current user is not allowed to update onboarding continuity for this workspace.',
                        workspace_id=normalized_workspace_id,
                        workspace_title=workspace_title,
                        provider_continuity=provider_continuity,
                        activity_continuity=activity_continuity,
                    )
                )
        existing = cls._resolve_state_row(request_auth=request_auth, onboarding_rows=onboarding_rows, workspace_id=normalized_workspace_id)
        dismissed_state = dict(existing.get('dismissed_guidance_state') or {}) if existing else {}
        if request.dismissed_guidance_state is not None:
            dismissed_state = dict(request.dismissed_guidance_state)
        persisted = {
            'onboarding_state_id': str(existing.get('onboarding_state_id') or '').strip() if existing else onboarding_state_id_factory(),
            'user_id': request_auth.requested_by_user_ref or '',
            'workspace_id': normalized_workspace_id,
            'first_success_achieved': request.first_success_achieved if request.first_success_achieved is not None else bool(existing.get('first_success_achieved')) if existing else False,
            'advanced_surfaces_unlocked': request.advanced_surfaces_unlocked if request.advanced_surfaces_unlocked is not None else bool(existing.get('advanced_surfaces_unlocked')) if existing else False,
            'dismissed_guidance_state': dismissed_state,
            'current_step': request.current_step if request.current_step is not None else (str(existing.get('current_step') or '').strip() or None if existing else None),
            'updated_at': now_iso,
        }
        state = ProductOnboardingStateView(
            onboarding_state_id=str(persisted['onboarding_state_id']),
            user_id=str(persisted['user_id']),
            workspace_id=normalized_workspace_id,
            first_success_achieved=bool(persisted['first_success_achieved']),
            advanced_surfaces_unlocked=bool(persisted['advanced_surfaces_unlocked']),
            dismissed_guidance_state=dict(persisted['dismissed_guidance_state'] or {}),
            current_step=persisted['current_step'],
            updated_at=now_iso,
        )
        activity_rows = tuple(onboarding_rows) + (persisted,)
        if normalized_workspace_id is not None:
            provider_continuity = _provider_continuity_summary_for_workspace(
                normalized_workspace_id or '',
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
            )
            activity_continuity = _activity_continuity_summary_for_workspace(
                normalized_workspace_id or '',
                user_id=request_auth.requested_by_user_ref or '',
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=activity_rows,
                share_payload_rows=share_payload_rows,
            )
        else:
            visible_workspace_ids = _visible_workspace_ids_for_user(
                request_auth.requested_by_user_ref or '',
                workspace_rows,
                membership_rows,
            )
            provider_continuity, activity_continuity = _continuity_projection_for_workspace_ids(
                visible_workspace_ids,
                user_id=request_auth.requested_by_user_ref or '',
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=activity_rows,
                share_payload_rows=share_payload_rows,
            )
        return OnboardingWriteOutcome(
            accepted=ProductOnboardingWriteAcceptedResponse(
                status='accepted',
                continuity_scope=cls._scope(normalized_workspace_id),
                state=state,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                links=cls._links(normalized_workspace_id),
                was_created=existing is None,
                message='Onboarding continuity has been stored as canonical server state.',
            ),
            persisted_onboarding_row=persisted,
        )
