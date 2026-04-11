from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.provider_probe_history_models import (
    ProductProviderProbeHistoryAppliedFilters,
    ProductProviderProbeHistoryItemView,
    ProductProviderProbeHistoryLinks,
    ProductProviderProbeHistoryRejectedResponse,
    ProductProviderProbeHistoryResponse,
    ProviderProbeHistoryReadOutcome,
)


def _probe_links(workspace_id: str, provider_key: str) -> ProductProviderProbeHistoryLinks:
    base = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}"
    return ProductProviderProbeHistoryLinks(
        binding=base,
        health=f"{base}/health",
        probe=f"{base}/probe",
    )


class ProviderProbeHistoryService:
    @classmethod
    def list_workspace_provider_probe_history(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        probe_history_rows: Sequence[Mapping[str, Any]] = (),
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> ProviderProbeHistoryReadOutcome:
        provider_key = str(provider_key or '').strip().lower()
        if not request_auth.is_authenticated:
            return ProviderProbeHistoryReadOutcome(
                rejected=ProductProviderProbeHistoryRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='provider_probe_history.authentication_required',
                    message='Provider probe history requires an authenticated session.',
                    workspace_id=workspace_context.workspace_id if workspace_context else None,
                    provider_key=provider_key or None,
                )
            )
        if workspace_context is None:
            return ProviderProbeHistoryReadOutcome(
                rejected=ProductProviderProbeHistoryRejectedResponse(
                    failure_family='workspace_not_found',
                    reason_code='provider_probe_history.workspace_not_found',
                    message='Requested workspace was not found.',
                    provider_key=provider_key or None,
                )
            )
        if limit <= 0:
            return ProviderProbeHistoryReadOutcome(
                rejected=ProductProviderProbeHistoryRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code='provider_probe_history.limit_invalid',
                    message='Provider probe history limit must be greater than zero.',
                    workspace_id=workspace_context.workspace_id,
                    provider_key=provider_key,
                )
            )
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or '',
            workspace_id=workspace_context.workspace_id,
            requested_action='manage',
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return ProviderProbeHistoryReadOutcome(
                rejected=ProductProviderProbeHistoryRejectedResponse(
                    failure_family='product_read_failure',
                    reason_code=f'provider_probe_history.{decision.reason_code}',
                    message='Current user is not allowed to read provider probe history for this workspace.',
                    workspace_id=workspace_context.workspace_id,
                    provider_key=provider_key,
                )
            )
        items: list[ProductProviderProbeHistoryItemView] = []
        for row in probe_history_rows:
            row_workspace_id = str(row.get('workspace_id') or '').strip()
            row_provider_key = str(row.get('provider_key') or '').strip().lower()
            if row_workspace_id != workspace_context.workspace_id or row_provider_key != provider_key:
                continue
            probe_event_id = str(row.get('probe_event_id') or row.get('probe_id') or '').strip()
            occurred_at = str(row.get('occurred_at') or row.get('updated_at') or row.get('created_at') or '').strip()
            if not probe_event_id or not occurred_at:
                continue
            items.append(ProductProviderProbeHistoryItemView(
                probe_event_id=probe_event_id,
                occurred_at=occurred_at,
                workspace_id=row_workspace_id,
                provider_key=row_provider_key,
                provider_family=str(row.get('provider_family') or row_provider_key).strip() or row_provider_key,
                display_name=str(row.get('display_name') or row_provider_key).strip() or row_provider_key,
                probe_status=str(row.get('probe_status') or 'failed').strip(),
                connectivity_state=str(row.get('connectivity_state') or 'unknown').strip(),
                secret_resolution_status=str(row.get('secret_resolution_status') or '').strip() or None,
                requested_model_ref=str(row.get('requested_model_ref') or '').strip() or None,
                effective_model_ref=str(row.get('effective_model_ref') or '').strip() or None,
                round_trip_latency_ms=int(row.get('round_trip_latency_ms')) if row.get('round_trip_latency_ms') is not None else None,
                requested_by_user_id=str(row.get('requested_by_user_id') or '').strip() or None,
                message=str(row.get('message') or '').strip() or None,
                links=_probe_links(row_workspace_id, row_provider_key),
            ))
        items.sort(key=lambda item: (item.occurred_at, item.probe_event_id), reverse=True)
        total_visible_count = len(items)
        start_index = 0
        if cursor is not None:
            matching_index = next((index for index, item in enumerate(items) if item.probe_event_id == cursor), None)
            if matching_index is None:
                return ProviderProbeHistoryReadOutcome(
                    rejected=ProductProviderProbeHistoryRejectedResponse(
                        failure_family='product_read_failure',
                        reason_code='provider_probe_history.cursor_invalid',
                        message='Provider probe history cursor is invalid.',
                        workspace_id=workspace_context.workspace_id,
                        provider_key=provider_key,
                    )
                )
            start_index = matching_index + 1
        page = tuple(items[start_index:start_index + limit])
        next_cursor = page[-1].probe_event_id if len(page) == limit and (start_index + limit) < total_visible_count else None
        latest_probe_at = items[0].occurred_at if items else None
        return ProviderProbeHistoryReadOutcome(
            response=ProductProviderProbeHistoryResponse(
                workspace_id=workspace_context.workspace_id,
                provider_key=provider_key,
                returned_count=len(page),
                total_visible_count=total_visible_count,
                items=page,
                applied_filters=ProductProviderProbeHistoryAppliedFilters(limit=limit, cursor=cursor),
                next_cursor=next_cursor,
                latest_probe_at=latest_probe_at,
                message='No provider probe history is available yet.' if not items else None,
            )
        )
