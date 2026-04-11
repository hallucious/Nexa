from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Mapping, Optional

from src.server.auth_adapter import RequestAuthResolver
from src.server.auth_models import RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.boundary_models import EngineResultEnvelope, EngineRunLaunchRequest, EngineRunLaunchResponse, EngineRunStatusSnapshot
from src.server.http_route_models import HttpRouteRequest, HttpRouteResponse
from src.server.run_admission import RunAdmissionService
from src.server.run_admission_models import (
    ExecutionTargetCatalogEntry,
    ProductAdmissionPolicy,
    ProductClientContext,
    ProductExecutionTarget,
    ProductLaunchOptions,
    ProductRunLaunchRequest,
)
from src.server.run_read_api import RunResultReadService, RunStatusReadService
from src.server.run_list_api import RunListReadService
from src.server.artifact_trace_read_api import ArtifactReadService, TraceReadService
from src.server.workspace_onboarding_api import OnboardingContinuityService, WorkspaceRegistryService
from src.server.workspace_onboarding_models import ProductOnboardingWriteRequest, ProductWorkspaceCreateRequest
from src.server.recent_activity_api import RecentActivityService
from src.server.provider_secret_api import ProviderSecretIntegrationService
from src.server.provider_health_api import ProviderHealthService, SecretMetadataReader
from src.server.provider_probe_api import ProviderProbeRunner, ProviderProbeService
from src.server.provider_secret_models import ProductProviderBindingWriteRequest
from src.server.provider_probe_models import ProductProviderProbeRequest


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def _route_response(status_code: int, body: Mapping[str, Any]) -> HttpRouteResponse:
    return HttpRouteResponse(status_code=status_code, body=_to_jsonable(dict(body)))


def _reason_to_status_code(reason_code: str) -> int:
    normalized = str(reason_code or "").strip().lower()
    if "authentication_required" in normalized:
        return 401
    if "forbidden" in normalized or "role_insufficient" in normalized:
        return 403
    if "not_found" in normalized:
        return 404
    if "quota" in normalized:
        return 429
    if "invalid" in normalized or "malformed" in normalized or "mismatch" in normalized:
        return 400
    return 409


def _request_auth(request: HttpRouteRequest):
    return RequestAuthResolver.resolve(
        headers=request.headers,
        session_claims=request.session_claims,
    )


class RunHttpRouteSurface:
    @staticmethod
    def _parse_launch_request(http_request: HttpRouteRequest) -> ProductRunLaunchRequest:
        body = http_request.json_body
        if not isinstance(body, Mapping):
            raise ValueError("launch.request_body_invalid")
        execution_target = body.get("execution_target")
        if not isinstance(execution_target, Mapping):
            raise ValueError("launch.execution_target_missing")
        return ProductRunLaunchRequest(
            workspace_id=str(body.get("workspace_id") or "").strip(),
            execution_target=ProductExecutionTarget(
                target_type=str(execution_target.get("target_type") or ""),
                target_ref=str(execution_target.get("target_ref") or ""),
            ),
            input_payload=body.get("input_payload"),
            launch_options=ProductLaunchOptions(**dict(body.get("launch_options") or {})),
            client_context=ProductClientContext(**dict(body.get("client_context") or {})),
        )

    @staticmethod
    def _parse_provider_binding_write_request(http_request: HttpRouteRequest) -> ProductProviderBindingWriteRequest:
        body = http_request.json_body
        if not isinstance(body, Mapping):
            raise ValueError("provider_binding_write.request_body_invalid")
        allowed_model_refs_raw = body.get("allowed_model_refs") or ()
        if isinstance(allowed_model_refs_raw, str):
            allowed_model_refs = (allowed_model_refs_raw.strip(),) if allowed_model_refs_raw.strip() else ()
        else:
            allowed_model_refs = tuple(str(item).strip() for item in allowed_model_refs_raw if str(item).strip())
        return ProductProviderBindingWriteRequest(
            display_name=str(body.get("display_name") or "").strip() or None,
            enabled=bool(body.get("enabled", True)),
            credential_source=str(body.get("credential_source") or "managed").strip() or "managed",
            secret_value=str(body.get("secret_value") or "").strip() or None,
            secret_ref_hint=str(body.get("secret_ref_hint") or "").strip() or None,
            default_model_ref=str(body.get("default_model_ref") or "").strip() or None,
            allowed_model_refs=allowed_model_refs,
            notes=str(body.get("notes") or "").strip() or None,
        )

    @staticmethod
    def _parse_provider_probe_request(http_request: HttpRouteRequest) -> ProductProviderProbeRequest:
        body = http_request.json_body
        if body is None:
            body = {}
        if not isinstance(body, Mapping):
            raise ValueError("provider_probe.request_body_invalid")
        return ProductProviderProbeRequest(
            model_ref=str(body.get("model_ref") or "").strip() or None,
            probe_message=str(body.get("probe_message") or "").strip() or None,
            timeout_ms=int(body.get("timeout_ms")) if body.get("timeout_ms") is not None else None,
        )

    @classmethod
    def handle_launch(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: WorkspaceAuthorizationContext,
        target_catalog: Mapping[str, ExecutionTargetCatalogEntry],
        policy: ProductAdmissionPolicy = ProductAdmissionPolicy(),
        engine_launch_decider: Optional[Callable[[EngineRunLaunchRequest], EngineRunLaunchResponse]] = None,
        run_id_factory: Optional[Callable[[], str]] = None,
        run_request_id_factory: Optional[Callable[[], str]] = None,
        now_iso: Optional[str] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Launch route only supports POST."})
        if http_request.path.rstrip("/") != "/api/runs":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            launch_request = cls._parse_launch_request(http_request)
        except Exception as exc:  # noqa: BLE001
            return _route_response(
                400,
                {
                    "status": "rejected",
                    "error_family": "product_rejection",
                    "reason_code": getattr(exc, "args", ["launch.invalid_request"])[0] or "launch.invalid_request",
                    "message": "Launch request payload is invalid.",
                },
            )

        outcome = RunAdmissionService.admit(
            request=launch_request,
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            target_catalog=target_catalog,
            policy=policy,
            engine_launch_decider=engine_launch_decider,
            run_id_factory=run_id_factory,
            run_request_id_factory=run_request_id_factory,
            now_iso=now_iso,
        )
        if outcome.accepted:
            assert outcome.accepted_response is not None
            return _route_response(202, asdict(outcome.accepted_response))
        assert outcome.rejected_response is not None
        rejected = asdict(outcome.rejected_response)
        if outcome.rejected_response.failure_family == "engine_rejection":
            rejected["status"] = "rejected_by_engine"
            rejected["error_family"] = "engine_launch_rejection"
            return _route_response(409, rejected)
        rejected["error_family"] = outcome.rejected_response.failure_family
        return _route_response(_reason_to_status_code(outcome.rejected_response.reason_code), rejected)

    @classmethod
    def handle_run_status(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        engine_status: Optional[EngineRunStatusSnapshot] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run status route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = RunStatusReadService.read_status(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            engine_status=engine_status,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_run_artifacts(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run artifacts route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}/artifacts"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = ArtifactReadService.list_run_artifacts(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            artifact_rows=artifact_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_artifact_detail(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        artifact_row: Optional[Mapping[str, Any]],
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Artifact detail route only supports GET."})
        artifact_id = str(http_request.path_params.get("artifact_id") or "").strip() if http_request.path_params else ""
        if not artifact_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.artifact_id_missing", "message": "Artifact id path parameter is required."})
        expected_path = f"/api/artifacts/{artifact_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = ArtifactReadService.read_artifact(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            artifact_row=artifact_row,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_run_trace(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        trace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run trace route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}/trace"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        limit = http_request.query_params.get("limit", 100) if http_request.query_params else 100
        cursor = http_request.query_params.get("cursor") if http_request.query_params else None
        outcome = TraceReadService.read_run_trace(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            trace_rows=trace_rows,
            cursor=str(cursor) if cursor is not None else None,
            limit=int(limit),
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))


    @classmethod
    def handle_list_workspaces(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace list route only supports GET."})
        if http_request.path.rstrip("/") != "/api/workspaces":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = WorkspaceRegistryService.list_workspaces(
            request_auth=_request_auth(http_request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_get_workspace(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace detail route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = WorkspaceRegistryService.read_workspace(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_create_workspace(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_id_factory: Callable[[], str],
        membership_id_factory: Callable[[], str],
        now_iso: str,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace create route only supports POST."})
        if http_request.path.rstrip("/") != "/api/workspaces":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            body = http_request.json_body
            if not isinstance(body, Mapping):
                raise ValueError('workspace_write.request_body_invalid')
            create_request = ProductWorkspaceCreateRequest(
                title=str(body.get('title') or ''),
                description=str(body.get('description') or '').strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                'status': 'rejected',
                'error_family': 'product_write_failure',
                'reason_code': getattr(exc, 'args', ['workspace_write.invalid_request'])[0] or 'workspace_write.invalid_request',
                'message': 'Workspace create request payload is invalid.',
            })
        outcome = WorkspaceRegistryService.create_workspace(
            request_auth=_request_auth(http_request),
            request=create_request,
            workspace_id_factory=workspace_id_factory,
            membership_id_factory=membership_id_factory,
            now_iso=now_iso,
        )
        if outcome.ok:
            assert outcome.accepted is not None
            return _route_response(201, asdict(outcome.accepted))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_get_onboarding(
        cls,
        *,
        http_request: HttpRouteRequest,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Onboarding route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/onboarding":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        query_params = dict(http_request.query_params or {})
        workspace_id = str(query_params.get('workspace_id') or '').strip() or None
        outcome = OnboardingContinuityService.read_onboarding_state(
            request_auth=_request_auth(http_request),
            onboarding_rows=onboarding_rows,
            workspace_context=workspace_context,
            workspace_id=workspace_id,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_put_onboarding(
        cls,
        *,
        http_request: HttpRouteRequest,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
        onboarding_state_id_factory: Callable[[], str],
        now_iso: str,
    ) -> HttpRouteResponse:
        if http_request.method != "PUT":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Onboarding write route only supports PUT."})
        if http_request.path.rstrip("/") != "/api/users/me/onboarding":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            body = http_request.json_body
            if not isinstance(body, Mapping):
                raise ValueError('onboarding_write.request_body_invalid')
            write_request = ProductOnboardingWriteRequest(
                workspace_id=str(body.get('workspace_id') or '').strip() or None,
                first_success_achieved=body.get('first_success_achieved'),
                advanced_surfaces_unlocked=body.get('advanced_surfaces_unlocked'),
                dismissed_guidance_state=dict(body.get('dismissed_guidance_state')) if body.get('dismissed_guidance_state') is not None else None,
                current_step=str(body.get('current_step') or '').strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                'status': 'rejected',
                'error_family': 'product_write_failure',
                'reason_code': getattr(exc, 'args', ['onboarding_write.invalid_request'])[0] or 'onboarding_write.invalid_request',
                'message': 'Onboarding continuity request payload is invalid.',
            })
        outcome = OnboardingContinuityService.upsert_onboarding_state(
            request_auth=_request_auth(http_request),
            request=write_request,
            onboarding_rows=onboarding_rows,
            workspace_context=workspace_context,
            onboarding_state_id_factory=onboarding_state_id_factory,
            now_iso=now_iso,
        )
        if outcome.ok:
            assert outcome.accepted is not None
            return _route_response(200, asdict(outcome.accepted))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_recent_activity(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Recent activity route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/activity":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        query_params = dict(http_request.query_params or {})
        workspace_id = str(query_params.get('workspace_id') or '').strip() or None
        limit = int(query_params.get('limit', 20))
        cursor = str(query_params.get('cursor') or '').strip() or None
        outcome = RecentActivityService.list_recent_activity(
            request_auth=_request_auth(http_request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            run_rows=run_rows,
            workspace_id=workspace_id,
            limit=limit,
            cursor=cursor,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_history_summary(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "History summary route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/history-summary":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        query_params = dict(http_request.query_params or {})
        workspace_id = str(query_params.get('workspace_id') or '').strip() or None
        outcome = RecentActivityService.read_history_summary(
            request_auth=_request_auth(http_request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            run_rows=run_rows,
            workspace_id=workspace_id,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_workspace_provider_health(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace provider health route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/health"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderHealthService.list_workspace_provider_health(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            secret_metadata_reader=secret_metadata_reader,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_get_workspace_provider_health(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Provider health detail route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        provider_key = str(http_request.path_params.get("provider_key") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not provider_key:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.provider_key_missing", "message": "Provider key path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/health"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderHealthService.read_workspace_provider_health(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            secret_metadata_reader=secret_metadata_reader,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_probe_workspace_provider(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        probe_runner: Optional[ProviderProbeRunner] = None,
        now_iso: Optional[str] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Provider probe route only supports POST."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not provider_key:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.provider_key_missing", "message": "Provider key path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            probe_request = cls._parse_provider_probe_request(http_request)
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                "status": "rejected",
                "error_family": "product_probe_failure",
                "reason_code": getattr(exc, "args", ["provider_probe.invalid_request"])[0] or "provider_probe.invalid_request",
                "message": "Provider probe request payload is invalid.",
            })
        outcome = ProviderProbeService.probe_workspace_provider(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            request=probe_request,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            secret_metadata_reader=secret_metadata_reader,
            probe_runner=probe_runner,
            now_iso=now_iso,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))


    @classmethod
    def handle_list_provider_catalog(
        cls,
        *,
        http_request: HttpRouteRequest,
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Provider catalog route only supports GET."})
        if http_request.path.rstrip("/") != "/api/providers/catalog":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderSecretIntegrationService.list_provider_catalog(
            request_auth=_request_auth(http_request),
            provider_catalog_rows=provider_catalog_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_workspace_provider_bindings(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace provider bindings route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderSecretIntegrationService.list_workspace_provider_bindings(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_put_workspace_provider_binding(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        existing_binding_row: Optional[Mapping[str, Any]],
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        binding_id_factory: Callable[[], str],
        secret_writer,
        now_iso: str,
    ) -> HttpRouteResponse:
        if http_request.method != "PUT":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace provider binding route only supports PUT."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        provider_key = str(http_request.path_params.get("provider_key") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not provider_key:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.provider_key_missing", "message": "Provider key path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            write_request = cls._parse_provider_binding_write_request(http_request)
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                "status": "rejected",
                "error_family": "product_write_failure",
                "reason_code": getattr(exc, "args", ["provider_binding_write.invalid_request"])[0] or "provider_binding_write.invalid_request",
                "message": "Provider binding request payload is invalid.",
            })
        outcome = ProviderSecretIntegrationService.upsert_workspace_provider_binding(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            request=write_request,
            existing_binding_row=existing_binding_row,
            provider_catalog_rows=provider_catalog_rows,
            binding_id_factory=binding_id_factory,
            secret_writer=secret_writer,
            now_iso=now_iso,
        )
        if outcome.ok:
            assert outcome.accepted is not None
            return _route_response(200, asdict(outcome.accepted))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_workspace_runs(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace run list route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/runs"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        query_params = dict(http_request.query_params or {})
        limit = int(query_params.get("limit", 20))
        cursor = query_params.get("cursor")
        status_family = query_params.get("status_family")
        requested_by_user_id = query_params.get("requested_by_user_id")
        outcome = RunListReadService.list_workspace_runs(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            run_rows=run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            cursor=str(cursor) if cursor is not None else None,
            limit=limit,
            status_family=str(status_family) if status_family is not None else None,
            requested_by_user_id=str(requested_by_user_id) if requested_by_user_id is not None else None,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_run_result(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        result_row: Optional[Mapping[str, Any]] = None,
        artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        engine_result: Optional[EngineResultEnvelope] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run result route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}/result"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = RunResultReadService.read_result(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            result_row=result_row,
            artifact_rows=artifact_rows,
            engine_result=engine_result,
        )
        if outcome.ok:
            assert outcome.response is not None
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))
