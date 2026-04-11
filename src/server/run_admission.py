from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional
from uuid import uuid4

from src.server.adapters import EngineLaunchAdapter
from src.server.auth_adapter import AuthorizationGate, build_engine_auth_context_refs
from src.server.auth_models import AuthorizationInput, RequestAuthContext, WorkspaceAuthorizationContext
from src.server.boundary_models import EngineRunLaunchRequest, EngineRunLaunchResponse
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
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.nex_api import load_nex


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


class ExecutionTargetResolver:
    @staticmethod
    def _load_source(source: Any) -> LoadedNexArtifact:
        if isinstance(source, LoadedNexArtifact):
            return source
        if isinstance(source, (WorkingSaveModel, CommitSnapshotModel)):
            if isinstance(source, WorkingSaveModel):
                raw = {
                    "meta": {
                        "format_version": source.meta.format_version,
                        "storage_role": "working_save",
                        "working_save_id": source.meta.working_save_id,
                    },
                    "circuit": {
                        "nodes": [dict(node) for node in source.circuit.nodes],
                        "edges": [dict(edge) for edge in source.circuit.edges],
                        "entry": source.circuit.entry,
                        "outputs": [dict(output) for output in source.circuit.outputs],
                        "subcircuits": dict(source.circuit.subcircuits),
                    },
                    "resources": {
                        "prompts": dict(source.resources.prompts),
                        "providers": dict(source.resources.providers),
                        "plugins": dict(source.resources.plugins),
                    },
                    "state": {
                        "input": dict(source.state.input),
                        "working": dict(source.state.working),
                        "memory": dict(source.state.memory),
                    },
                    "runtime": {
                        "status": source.runtime.status,
                        "validation_summary": dict(source.runtime.validation_summary),
                        "last_run": dict(source.runtime.last_run),
                        "errors": list(source.runtime.errors),
                    },
                    "ui": {
                        "layout": dict(source.ui.layout),
                        "metadata": dict(source.ui.metadata),
                    },
                }
            else:
                raw = {
                    "meta": {
                        "format_version": source.meta.format_version,
                        "storage_role": "commit_snapshot",
                        "commit_id": source.meta.commit_id,
                    },
                    "circuit": {
                        "nodes": [dict(node) for node in source.circuit.nodes],
                        "edges": [dict(edge) for edge in source.circuit.edges],
                        "entry": source.circuit.entry,
                        "outputs": [dict(output) for output in source.circuit.outputs],
                        "subcircuits": dict(source.circuit.subcircuits),
                    },
                    "resources": {
                        "prompts": dict(source.resources.prompts),
                        "providers": dict(source.resources.providers),
                        "plugins": dict(source.resources.plugins),
                    },
                    "state": {
                        "input": dict(source.state.input),
                        "working": dict(source.state.working),
                        "memory": dict(source.state.memory),
                    },
                    "validation": {
                        "validation_result": source.validation.validation_result,
                        "summary": dict(source.validation.summary),
                    },
                    "approval": {
                        "approval_completed": source.approval.approval_completed,
                        "approval_status": source.approval.approval_status,
                        "summary": dict(source.approval.summary),
                    },
                    "lineage": {
                        "parent_commit_id": source.lineage.parent_commit_id,
                        "source_working_save_id": source.lineage.source_working_save_id,
                        "metadata": dict(source.lineage.metadata),
                    },
                }
            return load_nex(raw)
        return load_nex(source)

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
        if storage_role == "commit_snapshot":
            canonical_ref = parsed.meta.commit_id  # type: ignore[union-attr]
            allowed_type = "commit_snapshot"
        elif storage_role == "working_save":
            canonical_ref = parsed.meta.working_save_id  # type: ignore[union-attr]
            allowed_type = "working_save"
        else:
            return None, ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code="launch.target_role_unsupported",
                message="Requested execution target resolved to an unsupported storage role.",
                workspace_id=request.workspace_id,
            )
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
    def _reject(*, workspace_id: Optional[str], reason_code: str, message: str) -> RunAdmissionOutcome:
        return RunAdmissionOutcome(
            rejected_response=ProductRunLaunchRejectedResponse(
                status="rejected",
                failure_family="product_rejection",
                reason_code=reason_code,
                message=message,
                workspace_id=workspace_id,
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
    ) -> RunAdmissionOutcome:
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code="launch.authentication_required",
                message="Authenticated product launch is required before asking the engine to run.",
            )
        if not policy.workspace_launch_enabled or policy.workspace_suspended:
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code="launch.workspace_blocked",
                message="Workspace launch is currently blocked by product policy.",
            )
        if not policy.quota_available:
            return cls._reject(
                workspace_id=request.workspace_id,
                reason_code="launch.quota_blocked",
                message="Product-level quota blocked this run before engine admission.",
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
            )

        resolved_target, target_rejection = ExecutionTargetResolver.resolve(
            request=request,
            catalog=target_catalog,
            policy=policy,
        )
        if target_rejection is not None:
            return RunAdmissionOutcome(rejected_response=target_rejection)
        assert resolved_target is not None

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
        )
        return RunAdmissionOutcome(
            accepted_response=accepted,
            engine_request=engine_request,
            engine_response=engine_response,
            run_record=record,
            resolved_target=resolved_target,
        )
