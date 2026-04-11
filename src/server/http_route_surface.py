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
