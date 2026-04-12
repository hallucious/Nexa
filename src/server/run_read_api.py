from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Optional

from src.server.auth_adapter import AuthorizationGate
from src.server.auth_models import AuthorizationInput, RequestAuthContext, RunAuthorizationContext
from src.server.boundary_models import EngineResultEnvelope, EngineRunStatusSnapshot
from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace
from src.server.run_recovery_projection import recovery_projection_from_run_row
from src.server.run_read_models import (
    ProductArtifactRefView,
    ProductEngineSignalView,
    ProductExecutionTargetView,
    ProductFinalOutputView,
    ProductResultSummaryView,
    ProductRunLinks,
    ProductRunProgressView,
    ProductRunReadRejectedResponse,
    ProductRunRecoveryView,
    ProductRunResultResponse,
    ProductRunStatusResponse,
    ProductTraceRefView,
    RunResultReadOutcome,
    RunStatusReadOutcome,
)


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


def _status_value(run_record_row: Mapping[str, Any], engine_status: EngineRunStatusSnapshot | None) -> str:
    if engine_status is not None:
        return engine_status.status
    return str(run_record_row.get('status') or '').strip().lower() or 'unknown'


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
    )


def _build_links(run_id: str) -> ProductRunLinks:
    return ProductRunLinks(
        result=f'/api/runs/{run_id}/result',
        trace=f'/api/runs/{run_id}/trace',
        artifacts=f'/api/runs/{run_id}/artifacts',
    )


def _artifact_refs_from_rows(artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> tuple[ProductArtifactRefView, ...]:
    refs: list[ProductArtifactRefView] = []
    for row in artifact_rows:
        metadata = row.get('metadata_json') if isinstance(row.get('metadata_json'), dict) else None
        label = None
        if metadata and isinstance(metadata.get('label'), str) and metadata.get('label').strip():
            label = metadata.get('label').strip()
        elif isinstance(row.get('payload_preview'), str) and row.get('payload_preview').strip():
            label = row.get('payload_preview').strip()
        refs.append(
            ProductArtifactRefView(
                artifact_id=str(row.get('artifact_id') or ''),
                kind=str(row.get('artifact_type') or row.get('kind') or ''),
                label=label,
            )
        )
    return tuple(refs)


def _result_summary_from_value(value: str | None, final_status: str | None) -> ProductResultSummaryView | None:
    if not value:
        return None
    normalized = str(final_status or '').strip().lower()
    if normalized == 'completed':
        title = 'Run completed'
    elif normalized == 'partial':
        title = 'Run completed partially'
    elif normalized == 'failed':
        title = 'Run failed'
    else:
        title = 'Run result available'
    return ProductResultSummaryView(title=title, description=str(value))


class RunStatusReadService:
    @staticmethod
    def _reject(*, run_id: str | None, family: str, code: str, message: str, workspace_title: str | None = None, provider_continuity=None, activity_continuity=None) -> RunStatusReadOutcome:
        return RunStatusReadOutcome(
            rejected=ProductRunReadRejectedResponse(
                failure_family=family,  # type: ignore[arg-type]
                reason_code=code,
                message=message,
                run_id=run_id,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )

    @classmethod
    def read_status(
        cls,
        *,
        request_auth: RequestAuthContext,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        provider_binding_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        managed_secret_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        provider_probe_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        onboarding_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        engine_status: Optional[EngineRunStatusSnapshot] = None,
    ) -> RunStatusReadOutcome:
        run_id = None
        if run_record_row is not None:
            run_id = str(run_record_row.get('run_id') or '') or None
        elif run_context is not None:
            run_id = run_context.run_id
        workspace_id = run_context.workspace_context.workspace_id if run_context is not None else str((run_record_row or {}).get('workspace_id') or '').strip()
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or '',
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated or request_auth.requested_by_user_ref is None:
            return cls._reject(run_id=run_id, family='product_read_failure', code='status.authentication_required', message='Authentication is required to read run status.', workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
        if run_context is None or run_record_row is None:
            return cls._reject(run_id=run_id, family='run_not_found', code='status.run_not_found', message='The requested run could not be found in the server continuity scope.', workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)

        decision = AuthorizationGate.authorize_run_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref,
                workspace_id=run_context.workspace_context.workspace_id,
                requested_action='status',
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
                run_id=run_context.run_id,
            ),
            run_context,
        )
        if not decision.allowed:
            return cls._reject(run_id=run_context.run_id, family='product_read_failure', code=decision.reason_code, message='The caller is not allowed to read this run status.', workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)

        status = _status_value(run_record_row, engine_status)
        status_family = str(run_record_row.get('status_family') or _status_family_for_status(status))
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
        if status == 'unknown' and not run_record_row.get('status') and engine_status is None:
            return RunStatusReadOutcome(
                response=ProductRunStatusResponse(
                    run_id=run_context.run_id,
                    workspace_id=run_context.workspace_context.workspace_id,
                    execution_target=ProductExecutionTargetView(
                        target_type=str(run_record_row.get('execution_target_type') or 'unknown'),
                        target_ref=str(run_record_row.get('execution_target_ref') or 'unknown'),
                    ),
                    status='unknown',
                    status_family='unknown',
                    created_at=str(run_record_row.get('created_at') or run_record_row.get('updated_at') or ''),
                    started_at=run_record_row.get('started_at'),
                    updated_at=str(run_record_row.get('updated_at') or ''),
                    workspace_title=str((workspace_row or {}).get('title') or '').strip() or None,
                    provider_continuity=_provider_continuity_summary_for_workspace(
                        run_context.workspace_context.workspace_id,
                        provider_binding_rows=provider_binding_rows,
                        managed_secret_rows=managed_secret_rows,
                        provider_probe_rows=provider_probe_rows,
                    ),
                    activity_continuity=_activity_continuity_summary_for_workspace(
                        run_context.workspace_context.workspace_id,
                        user_id=request_auth.requested_by_user_ref or '',
                        recent_run_rows=recent_run_rows,
                        provider_binding_rows=provider_binding_rows,
                        managed_secret_rows=managed_secret_rows,
                        provider_probe_rows=provider_probe_rows,
                        onboarding_rows=onboarding_rows,
                    ),
                    recovery=_recovery_view_from_run_row(run_record_row),
                    links=_build_links(run_context.run_id),
                    message='Run exists, but current status is temporarily unavailable.',
                )
            )

        progress = None
        latest_signal = None
        if engine_status is not None:
            if any(
                value is not None
                for value in (
                    engine_status.progress_percent,
                    engine_status.active_node_id,
                    engine_status.active_node_label,
                    engine_status.progress_summary,
                )
            ):
                progress = ProductRunProgressView(
                    percent=engine_status.progress_percent,
                    active_node_id=engine_status.active_node_id,
                    active_node_label=engine_status.active_node_label,
                    summary=engine_status.progress_summary,
                )
            if engine_status.latest_signal is not None:
                latest_signal = ProductEngineSignalView(
                    severity=engine_status.latest_signal.severity,
                    code=engine_status.latest_signal.code,
                    message=engine_status.latest_signal.message,
                )
        return RunStatusReadOutcome(
            response=ProductRunStatusResponse(
                run_id=run_context.run_id,
                workspace_id=run_context.workspace_context.workspace_id,
                execution_target=ProductExecutionTargetView(
                    target_type=str(run_record_row.get('execution_target_type') or 'unknown'),
                    target_ref=str(run_record_row.get('execution_target_ref') or 'unknown'),
                ),
                status=status,
                status_family=status_family,  # type: ignore[arg-type]
                created_at=str(run_record_row.get('created_at') or ''),
                started_at=run_record_row.get('started_at'),
                updated_at=str(run_record_row.get('updated_at') or ''),
                completed_at=run_record_row.get('finished_at'),
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                progress=progress,
                latest_engine_signal=latest_signal,
                recovery=_recovery_view_from_run_row(run_record_row),
                links=_build_links(run_context.run_id),
            )
        )


class RunResultReadService:
    @staticmethod
    def _reject(*, run_id: str | None, family: str, code: str, message: str, workspace_title: str | None = None, provider_continuity=None, activity_continuity=None) -> RunResultReadOutcome:
        return RunResultReadOutcome(
            rejected=ProductRunReadRejectedResponse(
                failure_family=family,  # type: ignore[arg-type]
                reason_code=code,
                message=message,
                run_id=run_id,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        )

    @classmethod
    def _response_from_engine_envelope(
        cls,
        *,
        workspace_id: str,
        updated_at: Optional[str],
        envelope: EngineResultEnvelope,
        workspace_title: Optional[str] = None,
        provider_continuity=None,
        activity_continuity=None,
    ) -> ProductRunResultResponse:
        artifact_refs = tuple(
            ProductArtifactRefView(
                artifact_id=item.artifact_id,
                kind=item.artifact_type,
                label=(item.metadata or {}).get('label') if isinstance(item.metadata, dict) else None,
            )
            for item in envelope.artifact_refs
        )
        final_output = None
        if envelope.final_output is not None:
            final_output = ProductFinalOutputView(
                output_key=envelope.final_output.output_key,
                value_preview=envelope.final_output.value_preview,
                value_type=envelope.final_output.value_type,
            )
        trace_ref = None
        if envelope.trace_ref:
            trace_ref = ProductTraceRefView(run_id=envelope.run_id, endpoint=f'/api/runs/{envelope.run_id}/trace')
        return ProductRunResultResponse(
            run_id=envelope.run_id,
            workspace_id=workspace_id,
            result_state=envelope.result_state,  # type: ignore[arg-type]
            final_status=envelope.final_status,
            workspace_title=workspace_title,
            provider_continuity=provider_continuity,
            activity_continuity=activity_continuity,
            result_summary=_result_summary_from_value(envelope.result_summary, envelope.final_status),
            final_output=final_output,
            artifact_refs=artifact_refs,
            trace_ref=trace_ref,
            recovery=None,
            metrics=deepcopy(envelope.metrics),
            updated_at=updated_at,
        )

    @classmethod
    def _response_from_rows(
        cls,
        *,
        workspace_id: str,
        run_id: str,
        result_row: Mapping[str, Any],
        artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
        updated_at: Optional[str],
        workspace_title: Optional[str] = None,
        provider_continuity=None,
        activity_continuity=None,
        recovery: ProductRunRecoveryView | None = None,
    ) -> ProductRunResultResponse:
        final_output = None
        final_output_row = result_row.get('final_output') if isinstance(result_row.get('final_output'), Mapping) else None
        if final_output_row is not None:
            final_output = ProductFinalOutputView(
                output_key=str(final_output_row.get('output_key') or ''),
                value_preview=str(final_output_row.get('value_preview') or ''),
                value_type=final_output_row.get('value_type'),
            )
        trace_ref = None
        if result_row.get('trace_ref'):
            trace_ref = ProductTraceRefView(run_id=run_id, endpoint=f'/api/runs/{run_id}/trace')
        final_status = (str(result_row.get('final_status')).strip() or None) if result_row.get('final_status') is not None else None
        return ProductRunResultResponse(
            run_id=run_id,
            workspace_id=workspace_id,
            result_state=str(result_row.get('result_state') or 'not_ready'),  # type: ignore[arg-type]
            final_status=final_status,
            workspace_title=workspace_title,
            provider_continuity=provider_continuity,
            activity_continuity=activity_continuity,
            result_summary=_result_summary_from_value(str(result_row.get('result_summary') or ''), final_status),
            final_output=final_output,
            artifact_refs=_artifact_refs_from_rows(artifact_rows),
            trace_ref=trace_ref,
            recovery=recovery,
            metrics=deepcopy(result_row.get('metrics')) if isinstance(result_row.get('metrics'), dict) else {},
            updated_at=updated_at,
        )

    @classmethod
    def read_result(
        cls,
        *,
        request_auth: RequestAuthContext,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        result_row: Optional[Mapping[str, Any]] = None,
        artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        provider_binding_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        managed_secret_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        provider_probe_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        onboarding_rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
        engine_result: Optional[EngineResultEnvelope] = None,
    ) -> RunResultReadOutcome:
        run_id = None
        if run_record_row is not None:
            run_id = str(run_record_row.get('run_id') or '') or None
        elif run_context is not None:
            run_id = run_context.run_id
        workspace_id = run_context.workspace_context.workspace_id if run_context is not None else str((run_record_row or {}).get('workspace_id') or '').strip()
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            workspace_id,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or '',
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated or request_auth.requested_by_user_ref is None:
            return cls._reject(run_id=run_id, family='product_read_failure', code='result.authentication_required', message='Authentication is required to read run results.', workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)
        if run_context is None or run_record_row is None:
            return cls._reject(run_id=run_id, family='run_not_found', code='result.run_not_found', message='The requested run could not be found in the server continuity scope.', workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)

        decision = AuthorizationGate.authorize_run_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref,
                workspace_id=run_context.workspace_context.workspace_id,
                requested_action='result',
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
                run_id=run_context.run_id,
            ),
            run_context,
        )
        if not decision.allowed:
            return cls._reject(run_id=run_context.run_id, family='product_read_failure', code=decision.reason_code, message='The caller is not allowed to read this run result.', workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity)

        updated_at = str(run_record_row.get('updated_at') or '') or None
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
        if engine_result is not None:
            return RunResultReadOutcome(response=cls._response_from_engine_envelope(workspace_id=run_context.workspace_context.workspace_id, updated_at=updated_at, envelope=engine_result, workspace_title=workspace_title, provider_continuity=provider_continuity, activity_continuity=activity_continuity))
        if result_row is not None:
            return RunResultReadOutcome(
                response=cls._response_from_rows(
                    workspace_id=run_context.workspace_context.workspace_id,
                    run_id=run_context.run_id,
                    result_row=result_row,
                    artifact_rows=artifact_rows,
                    updated_at=updated_at,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                    recovery=_recovery_view_from_run_row(run_record_row),
                )
            )
        return RunResultReadOutcome(
            response=ProductRunResultResponse(
                run_id=run_context.run_id,
                workspace_id=run_context.workspace_context.workspace_id,
                result_state='not_ready',
                final_status=None,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                recovery=_recovery_view_from_run_row(run_record_row),
                updated_at=updated_at,
                message='The run result is not available yet.',
            )
        )
