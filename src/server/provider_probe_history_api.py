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
    ProviderProbeHistoryRecord,
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
        records: list[ProviderProbeHistoryRecord] = []
        for row in probe_history_rows:
            record = ProviderProbeHistoryRecord.from_mapping(row)
            if record is None:
                continue
            if record.workspace_id != workspace_context.workspace_id or record.provider_key != provider_key:
                continue
            records.append(record)
        records.sort(key=lambda item: (item.occurred_at, item.probe_event_id), reverse=True)
        total_visible_count = len(records)
        start_index = 0
        if cursor is not None:
            matching_index = next((index for index, item in enumerate(records) if item.probe_event_id == cursor), None)
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
        page_records = tuple(records[start_index:start_index + limit])
        page = tuple(
            ProductProviderProbeHistoryItemView(
                probe_event_id=record.probe_event_id,
                occurred_at=record.occurred_at,
                workspace_id=record.workspace_id,
                provider_key=record.provider_key,
                provider_family=record.provider_family,
                display_name=record.display_name,
                probe_status=record.probe_status,
                connectivity_state=record.connectivity_state,
                secret_resolution_status=record.secret_resolution_status,
                requested_model_ref=record.requested_model_ref,
                effective_model_ref=record.effective_model_ref,
                round_trip_latency_ms=record.round_trip_latency_ms,
                requested_by_user_id=record.requested_by_user_id,
                message=record.message,
                links=_probe_links(record.workspace_id, record.provider_key),
            )
            for record in page_records
        )
        next_cursor = page[-1].probe_event_id if len(page) == limit and (start_index + limit) < total_visible_count else None
        latest_probe_at = records[0].occurred_at if records else None
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
                message='No provider probe history is available yet.' if not records else None,
            )
        )
