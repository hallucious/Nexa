from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from src.server.artifact_trace_read_models import (
    ArtifactDetailReadOutcome,
    ArtifactListReadOutcome,
    ProductArtifactDetailResponse,
    ProductArtifactPayloadAccess,
    ProductArtifactSummary,
    ProductArtifactTraceReadRejectedResponse,
    ProductRunArtifactsResponse,
    ProductRunTraceResponse,
    ProductTraceEventView,
    ProductTraceFocusView,
    TraceReadOutcome,
)
from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.run_read_api import _source_artifact_view_from_sources
from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace


def _artifact_label(row: Mapping[str, Any]) -> Optional[str]:
    metadata = row.get('metadata_json') if isinstance(row.get('metadata_json'), dict) else None
    if metadata and isinstance(metadata.get('label'), str) and metadata.get('label').strip():
        return metadata.get('label').strip()
    preview = row.get('payload_preview')
    if isinstance(preview, str) and preview.strip():
        return preview.strip()
    return None


def _artifact_value_type(row: Mapping[str, Any]) -> Optional[str]:
    metadata = row.get('metadata_json') if isinstance(row.get('metadata_json'), dict) else None
    if metadata and isinstance(metadata.get('value_type'), str) and metadata.get('value_type').strip():
        return metadata.get('value_type').strip()
    return None


def _artifact_payload_access(row: Mapping[str, Any]) -> Optional[ProductArtifactPayloadAccess]:
    metadata = row.get('metadata_json') if isinstance(row.get('metadata_json'), dict) else None
    if metadata and isinstance(metadata.get('inline_value'), str):
        return ProductArtifactPayloadAccess(mode='inline', value=metadata.get('inline_value'))
    storage_ref = row.get('storage_ref')
    if isinstance(storage_ref, str) and storage_ref.strip():
        return ProductArtifactPayloadAccess(mode='reference_only', reference=storage_ref.strip())
    return None


def _resolve_run_record_row(
    run_id: str | None,
    run_record_row: Mapping[str, Any] | None,
    recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> Mapping[str, Any] | None:
    if isinstance(run_record_row, Mapping):
        return run_record_row
    normalized_run_id = str(run_id or '').strip()
    if not normalized_run_id:
        return None
    for row in recent_run_rows:
        if str(row.get('run_id') or '').strip() == normalized_run_id:
            return row
    return None


class ArtifactReadService:
    @staticmethod
    def _reject(*, family: str, code: str, message: str, run_id: str | None = None, artifact_id: str | None = None, workspace_title: str | None = None, provider_continuity=None, activity_continuity=None) -> ProductArtifactTraceReadRejectedResponse:
        return ProductArtifactTraceReadRejectedResponse(
            failure_family=family,  # type: ignore[arg-type]
            reason_code=code,
            message=message,
            run_id=run_id,
            artifact_id=artifact_id,
            workspace_title=workspace_title,
            provider_continuity=provider_continuity,
            activity_continuity=activity_continuity,
        )

    @classmethod
    def list_run_artifacts(
        cls,
        *,
        request_auth: RequestAuthContext,
        run_context: Optional[RunAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        run_record_row: Optional[Mapping[str, Any]] = None,
    ) -> ArtifactListReadOutcome:
        run_id = run_context.run_id if run_context is not None else None
        resolved_run_record_row = _resolve_run_record_row(run_id, run_record_row, recent_run_rows)
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id=run_context.workspace_context.workspace_id if run_context is not None else None,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or "",
            provider_binding_rows=provider_binding_rows,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated or request_auth.requested_by_user_ref is None:
            return ArtifactListReadOutcome(rejected=cls._reject(family='product_read_failure', code='artifacts.authentication_required', message='Authentication is required to read run artifacts.', run_id=run_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        if run_context is None:
            return ArtifactListReadOutcome(rejected=cls._reject(family='run_not_found', code='artifacts.run_not_found', message='The requested run could not be found in the server continuity scope.', run_id=run_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        decision = AuthorizationGate.authorize_run_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref,
                workspace_id=run_context.workspace_context.workspace_id,
                requested_action='read',
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
                run_id=run_context.run_id,
            ),
            run_context,
        )
        if not decision.allowed:
            return ArtifactListReadOutcome(rejected=cls._reject(family='product_read_failure', code=decision.reason_code, message='The caller is not allowed to read artifacts for this run.', run_id=run_context.run_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        artifacts = tuple(
            ProductArtifactSummary(
                artifact_id=str(row.get('artifact_id') or ''),
                run_id=str(row.get('run_id') or run_context.run_id),
                workspace_id=str(row.get('workspace_id') or run_context.workspace_context.workspace_id),
                kind=str(row.get('artifact_type') or row.get('kind') or ''),
                label=_artifact_label(row),
                value_type=_artifact_value_type(row),
                preview=str(row.get('payload_preview')) if row.get('payload_preview') is not None else None,
                created_at=str(row.get('created_at')) if row.get('created_at') is not None else None,
            )
            for row in artifact_rows
        )
        workspace_title = str((workspace_row or {}).get('title') or '').strip() or None
        provider_continuity = _provider_continuity_summary_for_workspace(
            run_context.workspace_context.workspace_id,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        activity_continuity = _activity_continuity_summary_for_workspace(
            run_context.workspace_context.workspace_id,
            user_id=request_auth.requested_by_user_ref or '',
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return ArtifactListReadOutcome(
            response=ProductRunArtifactsResponse(
                run_id=run_context.run_id,
                workspace_id=run_context.workspace_context.workspace_id,
                artifact_count=len(artifacts),
                source_artifact=_source_artifact_view_from_sources(resolved_run_record_row),
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                artifacts=artifacts,
            )
        )

    @classmethod
    def read_artifact(
        cls,
        *,
        request_auth: RequestAuthContext,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_row: Optional[Mapping[str, Any]],
        run_record_row: Optional[Mapping[str, Any]] = None,
    ) -> ArtifactDetailReadOutcome:
        artifact_id = str(artifact_row.get('artifact_id') or '') if artifact_row is not None else None
        artifact_run_id = str(artifact_row.get('run_id') or '') if artifact_row is not None else None
        resolved_run_record_row = _resolve_run_record_row(artifact_run_id, run_record_row, recent_run_rows)
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id=workspace_context.workspace_id if workspace_context is not None else None,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or "",
            provider_binding_rows=provider_binding_rows,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated or request_auth.requested_by_user_ref is None:
            return ArtifactDetailReadOutcome(rejected=cls._reject(family='product_read_failure', code='artifact.authentication_required', message='Authentication is required to read artifact details.', artifact_id=artifact_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        if artifact_row is None or workspace_context is None:
            return ArtifactDetailReadOutcome(rejected=cls._reject(family='artifact_not_found', code='artifact.not_found', message='The requested artifact could not be found in the server continuity scope.', artifact_id=artifact_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        decision = AuthorizationGate.authorize_workspace_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref,
                workspace_id=workspace_context.workspace_id,
                requested_action='read',
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
            ),
            workspace_context,
        )
        if not decision.allowed:
            return ArtifactDetailReadOutcome(rejected=cls._reject(family='product_read_failure', code=decision.reason_code, message='The caller is not allowed to read this artifact.', artifact_id=str(artifact_row.get('artifact_id') or ''), workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        workspace_title = str((workspace_row or {}).get('title') or '').strip() or None
        provider_continuity = _provider_continuity_summary_for_workspace(
            workspace_context.workspace_id,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        activity_continuity = _activity_continuity_summary_for_workspace(
            workspace_context.workspace_id,
            user_id=request_auth.requested_by_user_ref or '',
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return ArtifactDetailReadOutcome(
            response=ProductArtifactDetailResponse(
                artifact_id=str(artifact_row.get('artifact_id') or ''),
                run_id=str(artifact_row.get('run_id') or ''),
                workspace_id=str(artifact_row.get('workspace_id') or workspace_context.workspace_id),
                kind=str(artifact_row.get('artifact_type') or artifact_row.get('kind') or ''),
                source_artifact=_source_artifact_view_from_sources(resolved_run_record_row),
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                label=_artifact_label(artifact_row),
                value_type=_artifact_value_type(artifact_row),
                preview=str(artifact_row.get('payload_preview')) if artifact_row.get('payload_preview') is not None else None,
                payload_access=_artifact_payload_access(artifact_row),
                append_only=True,
                created_at=str(artifact_row.get('created_at')) if artifact_row.get('created_at') is not None else None,
            )
        )


class TraceReadService:
    @staticmethod
    def _reject(*, family: str, code: str, message: str, run_id: str | None = None, workspace_title: str | None = None, provider_continuity=None, activity_continuity=None) -> ProductArtifactTraceReadRejectedResponse:
        return ProductArtifactTraceReadRejectedResponse(
            failure_family=family,  # type: ignore[arg-type]
            reason_code=code,
            message=message,
            run_id=run_id,
            workspace_title=workspace_title,
            provider_continuity=provider_continuity,
            activity_continuity=activity_continuity,
        )

    @classmethod
    def read_run_trace(
        cls,
        *,
        request_auth: RequestAuthContext,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        trace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> TraceReadOutcome:
        run_id = run_context.run_id if run_context is not None else None
        resolved_run_record_row = _resolve_run_record_row(run_id, run_record_row, recent_run_rows)
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id=run_context.workspace_context.workspace_id if run_context is not None else None,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or "",
            provider_binding_rows=provider_binding_rows,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated or request_auth.requested_by_user_ref is None:
            return TraceReadOutcome(rejected=cls._reject(family='product_read_failure', code='trace.authentication_required', message='Authentication is required to read run trace.', run_id=run_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        if run_context is None or run_record_row is None:
            return TraceReadOutcome(rejected=cls._reject(family='run_not_found', code='trace.run_not_found', message='The requested run could not be found in the server continuity scope.', run_id=run_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        decision = AuthorizationGate.authorize_run_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref,
                workspace_id=run_context.workspace_context.workspace_id,
                requested_action='read',
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
                run_id=run_context.run_id,
            ),
            run_context,
        )
        if not decision.allowed:
            return TraceReadOutcome(rejected=cls._reject(family='product_read_failure', code=decision.reason_code, message='The caller is not allowed to read this run trace.', run_id=run_context.run_id, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))

        normalized_limit = max(1, min(int(limit), 200))
        start = 0
        if cursor is not None and str(cursor).strip():
            try:
                start = max(0, int(str(cursor).strip()))
            except ValueError:
                start = 0
        ordered_rows = sorted(
            trace_rows,
            key=lambda row: (
                int(row.get('sequence_number') or 0),
                str(row.get('occurred_at') or ''),
                str(row.get('trace_event_ref') or ''),
            ),
        )
        sliced_rows = ordered_rows[start:start + normalized_limit]
        next_cursor = None
        if start + normalized_limit < len(ordered_rows):
            next_cursor = str(start + normalized_limit)
        events = tuple(
            ProductTraceEventView(
                event_id=str(row.get('trace_event_ref') or ''),
                sequence=int(row.get('sequence_number') or 0),
                event_type=str(row.get('event_type') or ''),
                timestamp=str(row.get('occurred_at') or ''),
                severity=str(row.get('severity')) if row.get('severity') is not None else None,
                node_id=str(row.get('node_id')) if row.get('node_id') is not None else None,
                message=str(row.get('message_preview')) if row.get('message_preview') is not None else None,
            )
            for row in sliced_rows
        )
        current_focus = None
        for row in reversed(ordered_rows):
            node_id = row.get('node_id')
            if isinstance(node_id, str) and node_id.strip():
                current_focus = ProductTraceFocusView(node_id=node_id.strip(), label=node_id.strip())
                break
        latest_event_time = str(ordered_rows[-1].get('occurred_at') or '') if ordered_rows else None
        message = None
        if not ordered_rows and not bool(run_record_row.get('trace_available')):
            message = 'Trace is not available yet.'
        workspace_title = str((workspace_row or {}).get('title') or '').strip() or None
        provider_continuity = _provider_continuity_summary_for_workspace(
            run_context.workspace_context.workspace_id,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        activity_continuity = _activity_continuity_summary_for_workspace(
            run_context.workspace_context.workspace_id,
            user_id=request_auth.requested_by_user_ref or '',
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return TraceReadOutcome(
            response=ProductRunTraceResponse(
                run_id=run_context.run_id,
                workspace_id=run_context.workspace_context.workspace_id,
                status=str(run_record_row.get('status') or 'unknown'),
                source_artifact=_source_artifact_view_from_sources(run_record_row),
                latest_event_time=latest_event_time,
                event_count=len(ordered_rows),
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                current_focus=current_focus,
                events=events,
                next_cursor=next_cursor,
                message=message,
            )
        )
