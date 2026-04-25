from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional, Sequence
from uuid import uuid4

from src.server.adapters import EngineLaunchAdapter
from src.server.provider_setup_readiness import evaluate_required_provider_setup
from src.server.auth_adapter import AuthorizationGate, build_engine_auth_context_refs
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.boundary_models import EngineRunLaunchRequest, EngineRunLaunchResponse
from src.server.workspace_onboarding_api import _activity_continuity_summary_for_workspace, _provider_continuity_summary_for_workspace, _continuity_projection_for_workspace
from src.server.run_admission_models import (
    ExecutionTargetCatalogEntry,
    ProductAdmissionPolicy,
    ProductExecutionTarget,
    ProductRunLaunchAcceptedResponse,
    ProductRunLaunchLinks,
    ProductRunLaunchRejectedResponse,
    ProductRunLaunchRequest,
    ResolvedExecutionTarget,
    RunAdmissionOutcome,
    RunRecordProjection,
)
from src.server.run_read_models import ProductSourceArtifactView
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.nex_api import coerce_nex_loaded_artifact, resolve_nex_execution_target


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_target_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "approved_snapshot":
        return "commit_snapshot"
    return normalized


def _status_family(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"queued", "starting"}:
        return "pending"
    if normalized in {"running"}:
        return "active"
    if normalized in {"completed"}:
        return "terminal_success"
    if normalized in {"failed", "cancelled"}:
        return "terminal_failure"
    if normalized in {"partial", "paused"}:
        return "terminal_partial"
    return "unknown"


def _source_artifact_view_from_resolved_target(resolved_target: ResolvedExecutionTarget) -> ProductSourceArtifactView | None:
    source_payload = resolved_target.source_payload

    def _from_mapping(payload: Mapping[str, Any]) -> ProductSourceArtifactView | None:
        meta = payload.get("meta") if isinstance(payload.get("meta"), Mapping) else {}
        storage_role = str(meta.get("storage_role") or resolved_target.storage_role or "").strip() or None
        if storage_role == "working_save":
            working_save_id = str(meta.get("working_save_id") or resolved_target.resolved_target_ref or "").strip() or None
            if working_save_id is None:
                return None
            return ProductSourceArtifactView(
                storage_role="working_save",
                canonical_ref=working_save_id,
                working_save_id=working_save_id,
            )
        if storage_role == "commit_snapshot":
            commit_id = str(meta.get("commit_id") or resolved_target.resolved_target_ref or "").strip() or None
            source_working_save_id = str(meta.get("source_working_save_id") or "").strip() or None
            if source_working_save_id is None:
                lineage = payload.get("lineage") if isinstance(payload.get("lineage"), Mapping) else {}
                source_working_save_id = str(lineage.get("source_working_save_id") or "").strip() or None
            if commit_id is None:
                return None
            return ProductSourceArtifactView(
                storage_role="commit_snapshot",
                canonical_ref=commit_id,
                working_save_id=source_working_save_id,
                commit_id=commit_id,
                source_working_save_id=source_working_save_id,
            )
        return None

    if isinstance(source_payload, LoadedNexArtifact):
        parsed_model = source_payload.parsed_model
        if parsed_model is not None:
            source_payload = parsed_model
        else:
            source_payload = source_payload.raw
    if isinstance(source_payload, WorkingSaveModel):
        return ProductSourceArtifactView(
            storage_role="working_save",
            canonical_ref=source_payload.meta.working_save_id,
            working_save_id=source_payload.meta.working_save_id,
        )
    if isinstance(source_payload, CommitSnapshotModel):
        return ProductSourceArtifactView(
            storage_role="commit_snapshot",
            canonical_ref=source_payload.meta.commit_id,
            working_save_id=source_payload.meta.source_working_save_id,
            commit_id=source_payload.meta.commit_id,
            source_working_save_id=source_payload.meta.source_working_save_id,
        )
    if isinstance(source_payload, Mapping):
        return _from_mapping(source_payload)
    return None


class ExecutionTargetResolver:
    @staticmethod
    def _load_source(source: Any) -> LoadedNexArtifact:
        return coerce_nex_loaded_artifact(source)

    @classmethod
    def resolve(
        cls,
        *,
        request: ProductRunLaunchRequest,
        catalog: Mapping[str, ExecutionTargetCatalogEntry],
        policy: ProductAdmissionPolicy,
    ) -> tuple[Optional[ResolvedExecutionTarget], Optional[ProductRunLaunchRejectedResponse]]:
        entry = catalog.get(request.execution_target.target_ref)
        if entry is None:
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.target_not_found",
                message="Requested execution target was not found.",
                workspace_id=request.workspace_id,
            )
        if entry.workspace_id != request.workspace_id:
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.target_workspace_mismatch",
                message="Requested execution target does not belong to the requested workspace.",
                workspace_id=request.workspace_id,
            )

        loaded = cls._load_source(entry.source)
        if loaded.parsed_model is None:
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.target_invalid",
                message="Requested execution target could not be loaded as a canonical Nexa artifact.",
                workspace_id=request.workspace_id,
                blocking_findings=[asdict(item) for item in loaded.findings if item.blocking],
            )
        parsed = loaded.parsed_model
        storage_role = loaded.storage_role
        resolved_target_type = _normalize_target_type(request.execution_target.target_type)
        try:
            descriptor = resolve_nex_execution_target(loaded)
        except ValueError:
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.target_role_unsupported",
                message="Requested execution target resolved to an unsupported storage role.",
                workspace_id=request.workspace_id,
            )
        canonical_ref = descriptor.target_ref
        allowed_type = descriptor.target_type
        if canonical_ref != entry.target_ref or canonical_ref != request.execution_target.target_ref:
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.target_ref_mismatch",
                message="Requested execution target ref does not match the resolved canonical artifact identity.",
                workspace_id=request.workspace_id,
            )
        if resolved_target_type != allowed_type:
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.target_type_mismatch",
                message="Requested execution target type does not match the resolved canonical artifact type.",
                workspace_id=request.workspace_id,
            )
        if resolved_target_type == "working_save" and not (policy.allow_working_save_execution or request.launch_options.allow_working_save_execution):
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.working_save_execution_disabled",
                message="Working-save execution is not enabled for this product path.",
                workspace_id=request.workspace_id,
            )
        return ResolvedExecutionTarget(
            workspace_id=request.workspace_id,
            requested_target_type=request.execution_target.target_type,
            requested_target_ref=request.execution_target.target_ref,
            resolved_target_type=resolved_target_type,
            resolved_target_ref=canonical_ref,
            storage_role=storage_role,
            source_payload=entry.source,
        ), None


class RunAdmissionService:
    @staticmethod
    def _reject(*, workspace_id: Optional[str], reason_code: str, message: str, workspace_title: Optional[str] = None, provider_continuity=None, activity_continuity=None, blocking_findings: Sequence[Mapping[str, Any]] = ()) -> RunAdmissionOutcome:
        return RunAdmissionOutcome(
            rejected_response=ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code=reason_code,
                message=message,
                workspace_id=workspace_id,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                blocking_findings=[dict(item) for item in blocking_findings],
            )
        )

    @classmethod
    def admit(
        cls,
        *,
        request: ProductRunLaunchRequest,
        request_auth: RequestAuthContext,
        workspace_context: WorkspaceAuthorizationContext,
        target_catalog: Mapping[str, ExecutionTargetCatalogEntry],
        policy: ProductAdmissionPolicy = ProductAdmissionPolicy(),
        engine_launch_decider: Optional[Callable[[EngineRunLaunchRequest], EngineRunLaunchResponse]] = None,
        run_id_factory: Optional[Callable[[], str]] = None,
        run_request_id_factory: Optional[Callable[[], str]] = None,
        now_iso: Optional[str] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> RunAdmissionOutcome:
        workspace_title, provider_continuity, activity_continuity = _continuity_projection_for_workspace(
            request.workspace_id,
            workspace_row=workspace_row,
            user_id=request_auth.requested_by_user_ref or "",
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code="launch.authentication_required",
                message="Authenticated product launch is required before asking the engine to run.",
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        if not policy.workspace_launch_enabled or policy.workspace_suspended:
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code="launch.workspace_blocked",
                message="Workspace launch is currently blocked by product policy.",
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )
        if not policy.quota_available:
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code="launch.quota_blocked",
                message="Product-level quota blocked this run before engine admission.",
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )

        authorization = AuthorizationGate.authorize_workspace_scope(
            AuthorizationInput(
                user_id=request_auth.requested_by_user_ref,
                workspace_id=request.workspace_id,
                requested_action="launch",
                role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
            ),
            workspace_context,
        )
        if not authorization.allowed:
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code=authorization.reason_code,
                message="Workspace authorization did not allow run launch for this caller.",
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
            )

        resolved_target, target_rejection = ExecutionTargetResolver.resolve(
            request=request,
            catalog=target_catalog,
            policy=policy,
        )
        if target_rejection is not None:
            return RunAdmissionOutcome(
                rejected_response=ProductRunLaunchRejectedResponse(
                    status=target_rejection.status,
                    failure_family=target_rejection.failure_family,
                    reason_code=target_rejection.reason_code,
                    message=target_rejection.message,
                    workspace_id=target_rejection.workspace_id,
                    blocking_findings=list(target_rejection.blocking_findings),
                    engine_error_code=target_rejection.engine_error_code,
                    engine_message=target_rejection.engine_message,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                )
            )
        assert resolved_target is not None

        provider_setup = evaluate_required_provider_setup(
            workspace_id=request.workspace_id,
            source_payload=resolved_target.source_payload,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        if provider_setup.requires_provider_setup:
            primary_finding = provider_setup.primary_finding
            assert primary_finding is not None
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code=primary_finding.reason_code,
                message=primary_finding.message,
                workspace_title=workspace_title,
                provider_continuity=provider_continuity,
                activity_continuity=activity_continuity,
                blocking_findings=tuple(item.to_payload() for item in provider_setup.blocking_findings),
            )

        run_request_id_factory = run_request_id_factory or (lambda: f"req_{uuid4().hex}")
        run_id_factory = run_id_factory or (lambda: f"run_{uuid4().hex}")
        request_id = request.client_context.request_id or run_request_id_factory()
        auth_refs = build_engine_auth_context_refs(request_auth)
        engine_request = EngineLaunchAdapter.build_request(
            run_request_id=request_id,
            workspace_ref=request.workspace_id,
            target_type=resolved_target.resolved_target_type,
            target_ref=resolved_target.resolved_target_ref,
            input_payload=request.input_payload,
            trigger_source=request.client_context.source or "api",
            auth_context_ref=auth_refs["auth_context_ref"],
            requested_by_user_ref=auth_refs["requested_by_user_ref"],
            correlation_metadata={
                "client_source": request.client_context.source,
                "client_request_id": request.client_context.request_id,
                "correlation_token": request.client_context.correlation_token,
                "workspace_role": authorization.resolved_role,
                "launch_mode": request.launch_options.mode,
                "launch_priority": request.launch_options.priority,
            },
        )

        run_id = run_id_factory()
        decider = engine_launch_decider or (lambda payload: EngineLaunchAdapter.accepted(run_id=run_id, initial_status="queued"))
        engine_response = decider(engine_request)
        if engine_response.launch_status == "rejected":
            return RunAdmissionOutcome(
                rejected_response=ProductRunLaunchRejectedResponse(
                    status="rejected",
                    failure_family="engine_rejection",
                    reason_code="launch.engine_rejected",
                    message="The engine rejected this run after the product layer approved the request.",
                    workspace_id=request.workspace_id,
                    blocking_findings=[asdict(item) for item in engine_response.blocking_findings],
                    engine_error_code=engine_response.engine_error_code,
                    engine_message=engine_response.engine_message,
                    workspace_title=workspace_title,
                    provider_continuity=provider_continuity,
                    activity_continuity=activity_continuity,
                ),
                engine_request=engine_request,
                engine_response=engine_response,
                resolved_target=resolved_target,
            )

        now_value = now_iso or _iso_now()
        record = RunRecordProjection(
            run_id=engine_response.run_id or run_id,
            workspace_id=request.workspace_id,
            launch_request_id=engine_request.run_request_id,
            execution_target_type=resolved_target.resolved_target_type,
            execution_target_ref=resolved_target.resolved_target_ref,
            status=engine_response.initial_status or "queued",
            status_family=_status_family(engine_response.initial_status or "queued"),
            result_state=None,
            latest_error_family=None,
            requested_by_user_id=request_auth.requested_by_user_ref,
            auth_context_ref=request_auth.auth_context_ref,
            trace_available=False,
            artifact_count=0,
            trace_event_count=0,
            created_at=now_value,
            started_at=None,
            finished_at=None,
            updated_at=now_value,
        )
        launch_recent_run_rows = tuple(recent_run_rows) + (record.to_row(),)
        accepted = ProductRunLaunchAcceptedResponse(
            status="accepted",
            run_id=record.run_id,
            workspace_id=request.workspace_id,
            execution_target=ProductExecutionTarget(
                target_type=resolved_target.resolved_target_type,
                target_ref=resolved_target.resolved_target_ref,
            ),
            initial_run_status=record.status,
            links=ProductRunLaunchLinks(
                run_status=f"/api/runs/{record.run_id}",
                run_result=f"/api/runs/{record.run_id}/result",
            ),
            source_artifact=_source_artifact_view_from_resolved_target(resolved_target),
            workspace_title=str((workspace_row or {}).get("title") or "").strip() or None,
            provider_continuity=_provider_continuity_summary_for_workspace(
                request.workspace_id,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
            ),
            activity_continuity=_activity_continuity_summary_for_workspace(
                request.workspace_id,
                user_id=request_auth.requested_by_user_ref or "",
                recent_run_rows=launch_recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
            ),
        )
        return RunAdmissionOutcome(
            accepted_response=accepted,
            engine_request=engine_request,
            engine_response=engine_response,
            run_record=record,
            resolved_target=resolved_target,
        )
