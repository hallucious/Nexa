from __future__ import annotations

import json

"""Public integration-side SDK boundary for Nexa.

This module does not implement a full MCP server. Instead, it defines the
curated compatibility shape that external integrations can use when mapping the
public Nexa server surface into tool/resource style protocols such as MCP.

The goal is to make the public integration boundary explicit:
- which public routes are action-oriented tools
- which public routes are read-oriented resources
- which public SDK request/response models represent those routes
"""

from dataclasses import dataclass
from typing import Any, Mapping

from src.server.framework_binding import FrameworkRouteBindings
from src.server.framework_binding_models import FrameworkInboundRequest, FrameworkRouteDefinition
from src.server.http_route_models import HttpRouteRequest
from src.server.http_route_surface import RunHttpRouteSurface

@dataclass(frozen=True)
class PublicTypeRef:
    module: str
    name: str


@dataclass(frozen=True)
class PublicMcpToolDescriptor:
    name: str
    route_name: str
    method: str
    path: str
    description: str
    request_type: PublicTypeRef | None = None
    response_type: PublicTypeRef | None = None
    argument_schema: PublicMcpArgumentSchema | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpResourceDescriptor:
    name: str
    route_name: str
    method: str
    path: str
    description: str
    response_type: PublicTypeRef | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpArgumentField:
    name: str
    location: str
    value_kind: str
    required: bool = False
    description: str = ""
    enum_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpArgumentSchema:
    name: str
    route_name: str
    path_fields: tuple[PublicMcpArgumentField, ...] = ()
    query_fields: tuple[PublicMcpArgumentField, ...] = ()
    body_fields: tuple[PublicMcpArgumentField, ...] = ()
    allow_additional_query_params: bool = False
    allow_additional_body_fields: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "path_fields": [_argument_field_dict(field) for field in self.path_fields],
            "query_fields": [_argument_field_dict(field) for field in self.query_fields],
            "body_fields": [_argument_field_dict(field) for field in self.body_fields],
            "allow_additional_query_params": self.allow_additional_query_params,
            "allow_additional_body_fields": self.allow_additional_body_fields,
        }


@dataclass(frozen=True)
class PublicMcpRouteContract:
    name: str
    route_name: str
    kind: str
    route_family: str
    transport_profile: str
    path_param_names: tuple[str, ...] = ()
    query_param_names: tuple[str, ...] = ()
    body_field_names: tuple[str, ...] = ()
    allow_additional_query_params: bool = False
    allow_additional_body_fields: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "route_family": self.route_family,
            "transport_profile": self.transport_profile,
            "path_param_names": list(self.path_param_names),
            "query_param_names": list(self.query_param_names),
            "body_field_names": list(self.body_field_names),
            "allow_additional_query_params": self.allow_additional_query_params,
            "allow_additional_body_fields": self.allow_additional_body_fields,
        }


@dataclass(frozen=True)
class PublicMcpNormalizedArguments:
    name: str
    route_name: str
    kind: str
    route_contract: PublicMcpRouteContract
    path_params: Mapping[str, str]
    query_params: Mapping[str, str]
    json_body: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "route_contract": self.route_contract.to_dict(),
            "path_params": dict(self.path_params),
            "query_params": dict(self.query_params),
            "json_body": dict(self.json_body) if self.json_body is not None else None,
        }


@dataclass(frozen=True)
class PublicMcpResultShapeProfile:
    profile_kind: str
    identity_keys: tuple[str, ...] = ()
    state_keys: tuple[str, ...] = ()
    collection_field_name: str | None = None
    count_field_name: str | None = None
    collection_item_identity_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_kind": self.profile_kind,
            "identity_keys": list(self.identity_keys),
            "state_keys": list(self.state_keys),
            "collection_field_name": self.collection_field_name,
            "count_field_name": self.count_field_name,
            "collection_item_identity_keys": list(self.collection_item_identity_keys),
        }


@dataclass(frozen=True)
class PublicMcpResponseContract:
    name: str
    route_name: str
    kind: str
    route_family: str
    response_shape: str
    success_status_codes: tuple[int, ...]
    response_media_type: str = "application/json"
    body_kind: str = "object"
    required_top_level_keys: tuple[str, ...] = ()
    result_shape_profile: PublicMcpResultShapeProfile | None = None
    response_type: PublicTypeRef | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "route_family": self.route_family,
            "response_shape": self.response_shape,
            "success_status_codes": list(self.success_status_codes),
            "response_media_type": self.response_media_type,
            "body_kind": self.body_kind,
            "required_top_level_keys": list(self.required_top_level_keys),
            "result_shape_profile": self.result_shape_profile.to_dict() if self.result_shape_profile is not None else None,
            "response_type": _type_ref_dict(self.response_type),
        }


@dataclass(frozen=True)
class PublicMcpRecoveryPolicy:
    name: str
    route_name: str
    kind: str
    route_family: str
    idempotency_class: str
    timeout_retryable: bool
    safe_to_retry_same_request_on_timeout: bool
    timeout_recommended_action: str
    response_timeout_retryable: bool
    safe_to_retry_same_request_on_response_timeout: bool
    response_timeout_recommended_action: str
    request_contract_recommended_action: str = "fix_request_arguments"
    binding_error_recommended_action: str = "inspect_route_binding"
    handler_error_recommended_action: str = "inspect_handler_failure"
    response_contract_recommended_action: str = "inspect_response_contract"
    response_decode_recommended_action: str = "inspect_response_serialization"
    response_error_recommended_action: str = "inspect_response_handling"
    unexpected_error_recommended_action: str = "inspect_unexpected_failure"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "route_family": self.route_family,
            "idempotency_class": self.idempotency_class,
            "timeout_retryable": self.timeout_retryable,
            "safe_to_retry_same_request_on_timeout": self.safe_to_retry_same_request_on_timeout,
            "timeout_recommended_action": self.timeout_recommended_action,
            "response_timeout_retryable": self.response_timeout_retryable,
            "safe_to_retry_same_request_on_response_timeout": self.safe_to_retry_same_request_on_response_timeout,
            "response_timeout_recommended_action": self.response_timeout_recommended_action,
            "request_contract_recommended_action": self.request_contract_recommended_action,
            "binding_error_recommended_action": self.binding_error_recommended_action,
            "handler_error_recommended_action": self.handler_error_recommended_action,
            "response_contract_recommended_action": self.response_contract_recommended_action,
            "response_decode_recommended_action": self.response_decode_recommended_action,
            "response_error_recommended_action": self.response_error_recommended_action,
            "unexpected_error_recommended_action": self.unexpected_error_recommended_action,
        }


@dataclass(frozen=True)
class PublicMcpNormalizedResponse:
    name: str
    route_name: str
    kind: str
    response_contract: PublicMcpResponseContract
    status_code: int
    media_type: str
    body: Any
    lifecycle_state_hint: PublicMcpLifecycleStateHint | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "response_contract": self.response_contract.to_dict(),
            "status_code": self.status_code,
            "media_type": self.media_type,
            "ok": self.ok,
            "body": self.body,
            "lifecycle_state_hint": self.lifecycle_state_hint.to_dict() if self.lifecycle_state_hint is not None else None,
        }


@dataclass(frozen=True)
class PublicMcpRecoveryHint:
    retryable: bool
    safe_to_retry_same_request: bool
    recoverability: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "retryable": self.retryable,
            "safe_to_retry_same_request": self.safe_to_retry_same_request,
            "recoverability": self.recoverability,
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True)
class PublicMcpExecutionError:
    category: str
    phase: str
    message: str
    exception_type: str
    recovery_hint: PublicMcpRecoveryHint | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "phase": self.phase,
            "message": self.message,
            "exception_type": self.exception_type,
            "recovery_hint": self.recovery_hint.to_dict() if self.recovery_hint is not None else None,
        }


@dataclass(frozen=True)
class PublicMcpExecutionReport:
    name: str
    route_name: str
    kind: str
    transport_kind: str
    phase: str
    transport_context: PublicMcpTransportContext | None = None
    transport_assessment: PublicMcpTransportAssessment | None = None
    preflight_assessment: PublicMcpPreflightAssessment | None = None
    orchestration_summary: PublicMcpOrchestrationSummary | None = None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None
    lifecycle_state_hint: PublicMcpLifecycleStateHint | None = None
    normalized_response: PublicMcpNormalizedResponse | None = None
    error: PublicMcpExecutionError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.normalized_response is not None and self.phase == "completed"

    @property
    def retryable(self) -> bool:
        return bool(self.error is not None and self.error.recovery_hint is not None and self.error.recovery_hint.retryable)

    @property
    def safe_to_retry_same_request(self) -> bool:
        return bool(
            self.error is not None
            and self.error.recovery_hint is not None
            and self.error.recovery_hint.safe_to_retry_same_request
        )

    @property
    def recommended_action(self) -> str | None:
        if self.error is None or self.error.recovery_hint is None:
            return None
        return self.error.recovery_hint.recommended_action

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "transport_kind": self.transport_kind,
            "phase": self.phase,
            "ok": self.ok,
            "retryable": self.retryable,
            "safe_to_retry_same_request": self.safe_to_retry_same_request,
            "recommended_action": self.recommended_action,
            "transport_context": self.transport_context.to_dict() if self.transport_context is not None else None,
            "transport_assessment": self.transport_assessment.to_dict() if self.transport_assessment is not None else None,
            "preflight_assessment": self.preflight_assessment.to_dict() if self.preflight_assessment is not None else None,
            "orchestration_summary": self.orchestration_summary.to_dict() if self.orchestration_summary is not None else None,
            "lifecycle_control_profile": self.lifecycle_control_profile.to_dict() if self.lifecycle_control_profile is not None else None,
            "lifecycle_state_hint": self.lifecycle_state_hint.to_dict() if self.lifecycle_state_hint is not None else None,
            "normalized_response": self.normalized_response.to_dict() if self.normalized_response is not None else None,
            "error": self.error.to_dict() if self.error is not None else None,
        }


@dataclass(frozen=True)
class PublicMcpCompatibilitySurface:
    contract_markers: tuple[str, ...]
    runtime_markers: tuple[str, ...]
    tools: tuple[PublicMcpToolDescriptor, ...]
    resources: tuple[PublicMcpResourceDescriptor, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_markers": list(self.contract_markers),
            "runtime_markers": list(self.runtime_markers),
            "tools": [tool.route_name for tool in self.tools],
            "resources": [resource.route_name for resource in self.resources],
        }


@dataclass(frozen=True)
class PublicMcpCompatibilityPolicy:
    supported_contract_markers: tuple[str, ...] = ()
    supported_runtime_markers: tuple[str, ...] = ()
    supported_transport_kinds: tuple[str, ...] = ()

    def supports_contract_marker(self, marker: str) -> bool:
        return marker in self.supported_contract_markers

    def supports_runtime_marker(self, marker: str) -> bool:
        return marker in self.supported_runtime_markers

    def supports_transport_kind(self, transport_kind: str) -> bool:
        return transport_kind in self.supported_transport_kinds

    def assert_supported(
        self,
        *,
        required_contract_markers: tuple[str, ...] = (),
        required_runtime_markers: tuple[str, ...] = (),
        transport_kind: str | None = None,
    ) -> None:
        missing_contract = [marker for marker in required_contract_markers if marker not in self.supported_contract_markers]
        if missing_contract:
            raise ValueError(
                "Unsupported public MCP contract markers: "
                + ", ".join(missing_contract)
                + "; supported markers: "
                + ", ".join(self.supported_contract_markers)
            )
        missing_runtime = [marker for marker in required_runtime_markers if marker not in self.supported_runtime_markers]
        if missing_runtime:
            raise ValueError(
                "Unsupported public MCP runtime markers: "
                + ", ".join(missing_runtime)
                + "; supported markers: "
                + ", ".join(self.supported_runtime_markers)
            )
        if transport_kind is not None and transport_kind not in self.supported_transport_kinds:
            raise ValueError(
                f"Unsupported public MCP transport kind: {transport_kind}; supported kinds: {', '.join(self.supported_transport_kinds)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "supported_contract_markers": list(self.supported_contract_markers),
            "supported_runtime_markers": list(self.supported_runtime_markers),
            "supported_transport_kinds": list(self.supported_transport_kinds),
        }


@dataclass(frozen=True)
class PublicMcpSessionContract:
    mode: str
    subject_claim_names: tuple[str, ...] = ()
    session_id_claim_names: tuple[str, ...] = ()
    optional_claim_names: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "subject_claim_names": list(self.subject_claim_names),
            "session_id_claim_names": list(self.session_id_claim_names),
            "optional_claim_names": list(self.optional_claim_names),
        }


@dataclass(frozen=True)
class PublicMcpTransportContract:
    name: str
    route_name: str
    kind: str
    route_family: str
    transport_profile: str
    header_mode: str
    session_mode: str
    request_id_mode: str = "recommended"
    language_mode: str = "optional"
    authorization_mode: str = "optional-pass-through"
    session_subject_mode: str = "optional-pass-through"
    request_id_header_name: str = "x-request-id"
    language_header_name: str = "accept-language"
    authorization_header_name: str = "authorization"
    session_claims_header_name: str = "x-nexa-session-claims"
    allow_additional_headers: bool = True
    session_contract: PublicMcpSessionContract | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "route_family": self.route_family,
            "transport_profile": self.transport_profile,
            "header_mode": self.header_mode,
            "session_mode": self.session_mode,
            "request_id_mode": self.request_id_mode,
            "language_mode": self.language_mode,
            "authorization_mode": self.authorization_mode,
            "session_subject_mode": self.session_subject_mode,
            "request_id_header_name": self.request_id_header_name,
            "language_header_name": self.language_header_name,
            "authorization_header_name": self.authorization_header_name,
            "session_claims_header_name": self.session_claims_header_name,
            "allow_additional_headers": self.allow_additional_headers,
            "session_contract": self.session_contract.to_dict() if self.session_contract is not None else None,
        }


@dataclass(frozen=True)
class PublicMcpTransportContext:
    name: str
    route_name: str
    kind: str
    transport_contract: PublicMcpTransportContract
    headers: Mapping[str, str]
    session_claims: Mapping[str, Any] | None
    request_id: str | None
    language: str | None
    authorization_present: bool
    session_present: bool
    session_subject: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "transport_contract": self.transport_contract.to_dict(),
            "headers": dict(self.headers),
            "session_claims": dict(self.session_claims) if self.session_claims is not None else None,
            "request_id": self.request_id,
            "language": self.language,
            "authorization_present": self.authorization_present,
            "session_present": self.session_present,
            "session_subject": self.session_subject,
        }


@dataclass(frozen=True)
class PublicMcpTransportAssessment:
    name: str
    route_name: str
    kind: str
    transport_contract: PublicMcpTransportContract
    transport_context: PublicMcpTransportContext
    warnings: tuple[str, ...] = ()
    suggested_actions: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return len(self.warnings) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "transport_contract": self.transport_contract.to_dict(),
            "transport_context": self.transport_context.to_dict(),
            "ok": self.ok,
            "warnings": list(self.warnings),
            "suggested_actions": list(self.suggested_actions),
        }


@dataclass(frozen=True)
class PublicMcpPreflightAssessment:
    name: str
    route_name: str
    kind: str
    transport_kind: str
    route_contract: PublicMcpRouteContract | None
    response_contract: PublicMcpResponseContract | None
    recovery_policy: PublicMcpRecoveryPolicy | None
    transport_contract: PublicMcpTransportContract | None
    transport_context: PublicMcpTransportContext | None
    transport_assessment: PublicMcpTransportAssessment | None
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    suggested_actions: tuple[str, ...] = ()
    risk_level: str = "low"

    @property
    def ready(self) -> bool:
        return len(self.blockers) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "transport_kind": self.transport_kind,
            "route_contract": self.route_contract.to_dict() if self.route_contract is not None else None,
            "response_contract": self.response_contract.to_dict() if self.response_contract is not None else None,
            "recovery_policy": self.recovery_policy.to_dict() if self.recovery_policy is not None else None,
            "transport_contract": self.transport_contract.to_dict() if self.transport_contract is not None else None,
            "transport_context": self.transport_context.to_dict() if self.transport_context is not None else None,
            "transport_assessment": self.transport_assessment.to_dict() if self.transport_assessment is not None else None,
            "ready": self.ready,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "suggested_actions": list(self.suggested_actions),
            "risk_level": self.risk_level,
        }


@dataclass(frozen=True)
class PublicMcpLifecycleControlProfile:
    name: str
    route_name: str
    kind: str
    route_family: str
    lifecycle_class: str
    status_resource_name: str | None = None
    result_resource_name: str | None = None
    actions_resource_name: str | None = None
    trace_resource_name: str | None = None
    artifacts_resource_name: str | None = None
    source_resource_names: tuple[str, ...] = ()
    preferred_control_tool_names: tuple[str, ...] = ()
    followup_route_names: tuple[str, ...] = ()
    review_tool_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "route_family": self.route_family,
            "lifecycle_class": self.lifecycle_class,
            "status_resource_name": self.status_resource_name,
            "result_resource_name": self.result_resource_name,
            "actions_resource_name": self.actions_resource_name,
            "trace_resource_name": self.trace_resource_name,
            "artifacts_resource_name": self.artifacts_resource_name,
            "source_resource_names": list(self.source_resource_names),
            "preferred_control_tool_names": list(self.preferred_control_tool_names),
            "followup_route_names": list(self.followup_route_names),
            "review_tool_name": self.review_tool_name,
        }


@dataclass(frozen=True)
class PublicMcpLifecycleStateHint:
    route_name: str
    kind: str
    lifecycle_class: str | None
    observed_state: str | None
    state_family: str
    terminal: bool
    recommended_followup_route_names: tuple[str, ...] = ()
    recommended_control_tool_names: tuple[str, ...] = ()
    recommended_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_name": self.route_name,
            "kind": self.kind,
            "lifecycle_class": self.lifecycle_class,
            "observed_state": self.observed_state,
            "state_family": self.state_family,
            "terminal": self.terminal,
            "recommended_followup_route_names": list(self.recommended_followup_route_names),
            "recommended_control_tool_names": list(self.recommended_control_tool_names),
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True)
class PublicMcpOrchestrationSummary:
    name: str
    route_name: str
    kind: str
    transport_kind: str
    route_family: str | None
    idempotency_class: str | None
    ready: bool
    risk_level: str
    authorization_present: bool
    session_present: bool
    session_subject_present: bool
    recommended_action: str | None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None
    summary_labels: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "route_name": self.route_name,
            "kind": self.kind,
            "transport_kind": self.transport_kind,
            "route_family": self.route_family,
            "idempotency_class": self.idempotency_class,
            "ready": self.ready,
            "risk_level": self.risk_level,
            "authorization_present": self.authorization_present,
            "session_present": self.session_present,
            "session_subject_present": self.session_subject_present,
            "recommended_action": self.recommended_action,
            "lifecycle_control_profile": self.lifecycle_control_profile.to_dict() if self.lifecycle_control_profile is not None else None,
            "summary_labels": list(self.summary_labels),
            "next_actions": list(self.next_actions),
        }


@dataclass(frozen=True)
class PublicMcpManifestTool:
    name: str
    description: str
    route_name: str
    method: str
    path: str
    request_type: PublicTypeRef | None = None
    response_type: PublicTypeRef | None = None
    argument_schema: PublicMcpArgumentSchema | None = None
    route_contract: PublicMcpRouteContract | None = None
    response_contract: PublicMcpResponseContract | None = None
    recovery_policy: PublicMcpRecoveryPolicy | None = None
    transport_contract: PublicMcpTransportContract | None = None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpManifestResource:
    name: str
    description: str
    route_name: str
    method: str
    path: str
    uri_template: str
    response_type: PublicTypeRef | None = None
    argument_schema: PublicMcpArgumentSchema | None = None
    route_contract: PublicMcpRouteContract | None = None
    response_contract: PublicMcpResponseContract | None = None
    recovery_policy: PublicMcpRecoveryPolicy | None = None
    transport_contract: PublicMcpTransportContract | None = None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpManifest:
    compatibility_policy: PublicMcpCompatibilityPolicy
    server_name: str
    server_title: str
    transport_kind: str
    stability: str
    base_url: str | None
    resource_uri_prefix: str
    tools: tuple[PublicMcpManifestTool, ...]
    resources: tuple[PublicMcpManifestResource, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatibility_policy": self.compatibility_policy.to_dict(),
            "server": {
                "name": self.server_name,
                "title": self.server_title,
                "transport_kind": self.transport_kind,
                "stability": self.stability,
            },
            "base_url": self.base_url,
            "resource_uri_prefix": self.resource_uri_prefix,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "route_name": tool.route_name,
                    "method": tool.method,
                    "path": tool.path,
                    "request_type": _type_ref_dict(tool.request_type),
                    "response_type": _type_ref_dict(tool.response_type),
                    "argument_schema": _argument_schema_dict(tool.argument_schema),
                    "route_contract": tool.route_contract.to_dict() if tool.route_contract is not None else None,
                    "response_contract": tool.response_contract.to_dict() if tool.response_contract is not None else None,
                    "recovery_policy": tool.recovery_policy.to_dict() if tool.recovery_policy is not None else None,
                    "transport_contract": tool.transport_contract.to_dict() if tool.transport_contract is not None else None,
                    "lifecycle_control_profile": tool.lifecycle_control_profile.to_dict() if tool.lifecycle_control_profile is not None else None,
                    "tags": list(tool.tags),
                }
                for tool in self.tools
            ],
            "resources": [
                {
                    "name": resource.name,
                    "description": resource.description,
                    "route_name": resource.route_name,
                    "method": resource.method,
                    "path": resource.path,
                    "uri_template": resource.uri_template,
                    "response_type": _type_ref_dict(resource.response_type),
                    "argument_schema": _argument_schema_dict(resource.argument_schema),
                    "route_contract": resource.route_contract.to_dict() if resource.route_contract is not None else None,
                    "response_contract": resource.response_contract.to_dict() if resource.response_contract is not None else None,
                    "recovery_policy": resource.recovery_policy.to_dict() if resource.recovery_policy is not None else None,
                    "transport_contract": resource.transport_contract.to_dict() if resource.transport_contract is not None else None,
                    "lifecycle_control_profile": resource.lifecycle_control_profile.to_dict() if resource.lifecycle_control_profile is not None else None,
                    "tags": list(resource.tags),
                }
                for resource in self.resources
            ],
        }


_HTTP_QUERY_CAPABLE_METHODS = frozenset({"GET", "DELETE"})
_HTTP_BODY_CAPABLE_METHODS = frozenset({"POST", "PUT", "PATCH"})


@dataclass(frozen=True)
class PublicMcpHostRouteBinding:
    name: str
    route_name: str
    binding_kind: str
    method: str
    path_template: str
    framework_handler_name: str
    path_param_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpFrameworkDispatch:
    name: str
    route_name: str
    kind: str
    handler_name: str
    request: FrameworkInboundRequest
    route_contract: PublicMcpRouteContract | None = None
    response_contract: PublicMcpResponseContract | None = None
    recovery_policy: PublicMcpRecoveryPolicy | None = None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None


@dataclass(frozen=True)
class PublicMcpHttpDispatch:
    name: str
    route_name: str
    kind: str
    request: HttpRouteRequest
    route_contract: PublicMcpRouteContract | None = None
    response_contract: PublicMcpResponseContract | None = None
    recovery_policy: PublicMcpRecoveryPolicy | None = None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None


@dataclass(frozen=True)
class PublicMcpFrameworkEnvelope:
    name: str
    route_name: str
    kind: str
    transport_contract: PublicMcpTransportContract | None
    transport_context: PublicMcpTransportContext
    transport_assessment: PublicMcpTransportAssessment
    preflight_assessment: PublicMcpPreflightAssessment
    orchestration_summary: PublicMcpOrchestrationSummary
    dispatch: PublicMcpFrameworkDispatch
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None


@dataclass(frozen=True)
class PublicMcpHttpEnvelope:
    name: str
    route_name: str
    kind: str
    transport_contract: PublicMcpTransportContract | None
    transport_context: PublicMcpTransportContext
    transport_assessment: PublicMcpTransportAssessment
    preflight_assessment: PublicMcpPreflightAssessment
    orchestration_summary: PublicMcpOrchestrationSummary
    dispatch: PublicMcpHttpDispatch
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None


@dataclass(frozen=True)
class PublicMcpHostBridgeExport:
    compatibility_policy: PublicMcpCompatibilityPolicy
    framework_binding_class: str
    tool_bindings: tuple[PublicMcpHostRouteBinding, ...]
    resource_bindings: tuple[PublicMcpHostRouteBinding, ...]


@dataclass(frozen=True)
class PublicMcpHostBridgeScaffold:
    adapter_scaffold: PublicMcpAdapterScaffold

    def export(self) -> PublicMcpHostBridgeExport:
        return PublicMcpHostBridgeExport(
            compatibility_policy=self.adapter_scaffold.compatibility_policy(),
            framework_binding_class="FrameworkRouteBindings",
            tool_bindings=tuple(self._tool_binding(tool) for tool in self.adapter_scaffold.surface.tools),
            resource_bindings=tuple(self._resource_binding(resource) for resource in self.adapter_scaffold.surface.resources),
        )

    def assert_consumer_compatibility(
        self,
        *,
        required_contract_markers: tuple[str, ...] = (),
        required_runtime_markers: tuple[str, ...] = (),
        transport_kind: str | None = None,
    ) -> None:
        self.adapter_scaffold.assert_consumer_compatibility(
            required_contract_markers=required_contract_markers,
            required_runtime_markers=required_runtime_markers,
            transport_kind=transport_kind,
        )

    def build_framework_tool_request(
        self,
        tool_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query_params: Mapping[str, object] | None = None,
        json_body: Mapping[str, Any] | None = None,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> FrameworkInboundRequest:
        export = self.adapter_scaffold.export_tool(
            tool_name,
            path_params=path_params,
            query_params=query_params,
            json_body=json_body,
        )
        return self._framework_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_framework_tool_request_from_arguments(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> FrameworkInboundRequest:
        export = self.adapter_scaffold.export_tool_from_arguments(tool_name, arguments)
        return self._framework_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_framework_resource_request(
        self,
        resource_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query_params: Mapping[str, object] | None = None,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> FrameworkInboundRequest:
        export = self.adapter_scaffold.export_resource(
            resource_name,
            path_params=path_params,
            query_params=query_params,
        )
        return self._framework_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_framework_resource_request_from_arguments(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> FrameworkInboundRequest:
        export = self.adapter_scaffold.export_resource_from_arguments(resource_name, arguments)
        return self._framework_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_http_tool_request(
        self,
        tool_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query_params: Mapping[str, object] | None = None,
        json_body: Mapping[str, Any] | None = None,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> HttpRouteRequest:
        export = self.adapter_scaffold.export_tool(
            tool_name,
            path_params=path_params,
            query_params=query_params,
            json_body=json_body,
        )
        return self._http_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_http_tool_request_from_arguments(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> HttpRouteRequest:
        export = self.adapter_scaffold.export_tool_from_arguments(tool_name, arguments)
        return self._http_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_http_resource_request(
        self,
        resource_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query_params: Mapping[str, object] | None = None,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> HttpRouteRequest:
        export = self.adapter_scaffold.export_resource(
            resource_name,
            path_params=path_params,
            query_params=query_params,
        )
        return self._http_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_http_resource_request_from_arguments(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> HttpRouteRequest:
        export = self.adapter_scaffold.export_resource_from_arguments(resource_name, arguments)
        return self._http_request_from_invocation(
            export.invocation,
            headers=headers,
            session_claims=session_claims,
        )

    def build_framework_tool_dispatch(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpFrameworkDispatch:
        request = self.build_framework_tool_request_from_arguments(
            tool_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        descriptor = self.adapter_scaffold._tool_by_name(tool_name)
        return PublicMcpFrameworkDispatch(
            name=tool_name,
            route_name=descriptor.route_name,
            kind="tool",
            handler_name=_framework_handler_name(descriptor.route_name),
            request=request,
            route_contract=self.adapter_scaffold.export_tool_contract(tool_name),
            response_contract=self.adapter_scaffold.export_tool_response_contract(tool_name),
            recovery_policy=self.adapter_scaffold.export_tool_recovery_policy(tool_name),
            lifecycle_control_profile=self.adapter_scaffold.export_tool_lifecycle_control_profile(tool_name),
        )

    def build_framework_resource_dispatch(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpFrameworkDispatch:
        request = self.build_framework_resource_request_from_arguments(
            resource_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        descriptor = self.adapter_scaffold._resource_by_name(resource_name)
        return PublicMcpFrameworkDispatch(
            name=resource_name,
            route_name=descriptor.route_name,
            kind="resource",
            handler_name=_framework_handler_name(descriptor.route_name),
            request=request,
            route_contract=self.adapter_scaffold.export_resource_contract(resource_name),
            response_contract=self.adapter_scaffold.export_resource_response_contract(resource_name),
            recovery_policy=self.adapter_scaffold.export_resource_recovery_policy(resource_name),
            lifecycle_control_profile=self.adapter_scaffold.export_resource_lifecycle_control_profile(resource_name),
        )

    def build_http_tool_dispatch(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpHttpDispatch:
        request = self.build_http_tool_request_from_arguments(
            tool_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        descriptor = self.adapter_scaffold._tool_by_name(tool_name)
        return PublicMcpHttpDispatch(
            name=tool_name,
            route_name=descriptor.route_name,
            kind="tool",
            request=request,
            route_contract=self.adapter_scaffold.export_tool_contract(tool_name),
            response_contract=self.adapter_scaffold.export_tool_response_contract(tool_name),
            recovery_policy=self.adapter_scaffold.export_tool_recovery_policy(tool_name),
            lifecycle_control_profile=self.adapter_scaffold.export_tool_lifecycle_control_profile(tool_name),
        )

    def build_http_resource_dispatch(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpHttpDispatch:
        request = self.build_http_resource_request_from_arguments(
            resource_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        descriptor = self.adapter_scaffold._resource_by_name(resource_name)
        return PublicMcpHttpDispatch(
            name=resource_name,
            route_name=descriptor.route_name,
            kind="resource",
            request=request,
            route_contract=self.adapter_scaffold.export_resource_contract(resource_name),
            response_contract=self.adapter_scaffold.export_resource_response_contract(resource_name),
            recovery_policy=self.adapter_scaffold.export_resource_recovery_policy(resource_name),
            lifecycle_control_profile=self.adapter_scaffold.export_resource_lifecycle_control_profile(resource_name),
        )

    def normalize_transport_context(
        self,
        *,
        name: str,
        route_name: str,
        kind: str,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        transport_contract: PublicMcpTransportContract | None = None,
    ) -> PublicMcpTransportContext:
        if transport_contract is None:
            transport_contract = (
                self.adapter_scaffold.export_tool_transport_contract(name)
                if kind == "tool"
                else self.adapter_scaffold.export_resource_transport_contract(name)
            )
        normalized_headers = _normalize_public_headers(headers)
        normalized_claims = _normalize_public_session_claims(session_claims)
        session_contract = transport_contract.session_contract
        subject = _resolve_session_subject(normalized_claims, session_contract)
        request_id = normalized_headers.get(transport_contract.request_id_header_name)
        language = normalized_headers.get(transport_contract.language_header_name)
        auth_present = transport_contract.authorization_header_name in normalized_headers
        return PublicMcpTransportContext(
            name=name,
            route_name=route_name,
            kind=kind,
            transport_contract=transport_contract,
            headers=normalized_headers,
            session_claims=normalized_claims,
            request_id=request_id,
            language=language,
            authorization_present=auth_present,
            session_present=normalized_claims is not None,
            session_subject=subject,
        )

    def assess_transport_context(
        self,
        *,
        name: str,
        route_name: str,
        kind: str,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        transport_contract: PublicMcpTransportContract | None = None,
    ) -> PublicMcpTransportAssessment:
        context = self.normalize_transport_context(
            name=name,
            route_name=route_name,
            kind=kind,
            headers=headers,
            session_claims=session_claims,
            transport_contract=transport_contract,
        )
        return _assess_public_transport_context(context)

    def assess_tool_transport_context(
        self,
        tool_name: str,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpTransportAssessment:
        contract = self.adapter_scaffold.export_tool_transport_contract(tool_name)
        return self.assess_transport_context(
            name=tool_name,
            route_name=tool_name,
            kind="tool",
            headers=headers,
            session_claims=session_claims,
            transport_contract=contract,
        )

    def assess_resource_transport_context(
        self,
        resource_name: str,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpTransportAssessment:
        contract = self.adapter_scaffold.export_resource_transport_contract(resource_name)
        return self.assess_transport_context(
            name=resource_name,
            route_name=resource_name,
            kind="resource",
            headers=headers,
            session_claims=session_claims,
            transport_contract=contract,
        )

    def assess_preflight(
        self,
        *,
        name: str,
        route_name: str,
        kind: str,
        transport_kind: str,
        route_contract: PublicMcpRouteContract | None,
        response_contract: PublicMcpResponseContract | None,
        recovery_policy: PublicMcpRecoveryPolicy | None,
        transport_contract: PublicMcpTransportContract | None,
        transport_context: PublicMcpTransportContext | None,
        transport_assessment: PublicMcpTransportAssessment | None,
    ) -> PublicMcpPreflightAssessment:
        return _build_public_preflight_assessment(
            name=name,
            route_name=route_name,
            kind=kind,
            transport_kind=transport_kind,
            route_contract=route_contract,
            response_contract=response_contract,
            recovery_policy=recovery_policy,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
        )

    def preflight_framework_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpPreflightAssessment:
        envelope = self.build_framework_tool_envelope(tool_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.preflight_assessment

    def preflight_framework_resource(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpPreflightAssessment:
        envelope = self.build_framework_resource_envelope(resource_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.preflight_assessment

    def preflight_http_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpPreflightAssessment:
        envelope = self.build_http_tool_envelope(tool_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.preflight_assessment

    def preflight_http_resource(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpPreflightAssessment:
        envelope = self.build_http_resource_envelope(resource_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.preflight_assessment

    def summarize_orchestration(
        self,
        *,
        name: str,
        route_name: str,
        kind: str,
        transport_kind: str,
        route_contract: PublicMcpRouteContract | None,
        recovery_policy: PublicMcpRecoveryPolicy | None,
        lifecycle_control_profile: PublicMcpLifecycleControlProfile | None,
        transport_context: PublicMcpTransportContext | None,
        preflight_assessment: PublicMcpPreflightAssessment | None,
    ) -> PublicMcpOrchestrationSummary:
        return _build_public_orchestration_summary(
            name=name,
            route_name=route_name,
            kind=kind,
            transport_kind=transport_kind,
            route_contract=route_contract,
            recovery_policy=recovery_policy,
            lifecycle_control_profile=lifecycle_control_profile,
            transport_context=transport_context,
            preflight_assessment=preflight_assessment,
        )

    def summarize_framework_tool_orchestration(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpOrchestrationSummary:
        envelope = self.build_framework_tool_envelope(tool_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.orchestration_summary

    def summarize_framework_resource_orchestration(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpOrchestrationSummary:
        envelope = self.build_framework_resource_envelope(resource_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.orchestration_summary

    def summarize_http_tool_orchestration(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpOrchestrationSummary:
        envelope = self.build_http_tool_envelope(tool_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.orchestration_summary

    def summarize_http_resource_orchestration(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpOrchestrationSummary:
        envelope = self.build_http_resource_envelope(resource_name, arguments, headers=headers, session_claims=session_claims)
        return envelope.orchestration_summary

    def build_framework_tool_envelope(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpFrameworkEnvelope:
        dispatch = self.build_framework_tool_dispatch(tool_name, arguments, headers=headers, session_claims=session_claims)
        transport_contract = self.adapter_scaffold.export_tool_transport_contract(tool_name)
        transport_context = self.normalize_transport_context(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            headers=headers,
            session_claims=session_claims,
            transport_contract=transport_contract,
        )
        transport_assessment = _assess_public_transport_context(transport_context)
        preflight_assessment = self.assess_preflight(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_kind="framework",
            route_contract=dispatch.route_contract,
            response_contract=dispatch.response_contract,
            recovery_policy=dispatch.recovery_policy,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
        )
        return PublicMcpFrameworkEnvelope(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
            preflight_assessment=preflight_assessment,
            orchestration_summary=self.summarize_orchestration(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="framework",
                route_contract=dispatch.route_contract,
                recovery_policy=dispatch.recovery_policy,
                lifecycle_control_profile=self.adapter_scaffold.export_tool_lifecycle_control_profile(tool_name),
                transport_context=transport_context,
                preflight_assessment=preflight_assessment,
            ),
            dispatch=dispatch,
            lifecycle_control_profile=self.adapter_scaffold.export_tool_lifecycle_control_profile(tool_name),
        )

    def build_framework_resource_envelope(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpFrameworkEnvelope:
        dispatch = self.build_framework_resource_dispatch(resource_name, arguments, headers=headers, session_claims=session_claims)
        transport_contract = self.adapter_scaffold.export_resource_transport_contract(resource_name)
        transport_context = self.normalize_transport_context(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            headers=headers,
            session_claims=session_claims,
            transport_contract=transport_contract,
        )
        transport_assessment = _assess_public_transport_context(transport_context)
        preflight_assessment = self.assess_preflight(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_kind="framework",
            route_contract=dispatch.route_contract,
            response_contract=dispatch.response_contract,
            recovery_policy=dispatch.recovery_policy,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
        )
        return PublicMcpFrameworkEnvelope(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
            preflight_assessment=preflight_assessment,
            orchestration_summary=self.summarize_orchestration(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="framework",
                route_contract=dispatch.route_contract,
                recovery_policy=dispatch.recovery_policy,
                lifecycle_control_profile=self.adapter_scaffold.export_resource_lifecycle_control_profile(resource_name),
                transport_context=transport_context,
                preflight_assessment=preflight_assessment,
            ),
            dispatch=dispatch,
            lifecycle_control_profile=self.adapter_scaffold.export_resource_lifecycle_control_profile(resource_name),
        )

    def build_http_tool_envelope(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpHttpEnvelope:
        dispatch = self.build_http_tool_dispatch(tool_name, arguments, headers=headers, session_claims=session_claims)
        transport_contract = self.adapter_scaffold.export_tool_transport_contract(tool_name)
        transport_context = self.normalize_transport_context(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            headers=headers,
            session_claims=session_claims,
            transport_contract=transport_contract,
        )
        transport_assessment = _assess_public_transport_context(transport_context)
        preflight_assessment = self.assess_preflight(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_kind="http",
            route_contract=dispatch.route_contract,
            response_contract=dispatch.response_contract,
            recovery_policy=dispatch.recovery_policy,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
        )
        return PublicMcpHttpEnvelope(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
            preflight_assessment=preflight_assessment,
            orchestration_summary=self.summarize_orchestration(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="http",
                route_contract=dispatch.route_contract,
                recovery_policy=dispatch.recovery_policy,
                lifecycle_control_profile=self.adapter_scaffold.export_tool_lifecycle_control_profile(tool_name),
                transport_context=transport_context,
                preflight_assessment=preflight_assessment,
            ),
            dispatch=dispatch,
            lifecycle_control_profile=self.adapter_scaffold.export_tool_lifecycle_control_profile(tool_name),
        )

    def build_http_resource_envelope(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
    ) -> PublicMcpHttpEnvelope:
        dispatch = self.build_http_resource_dispatch(resource_name, arguments, headers=headers, session_claims=session_claims)
        transport_contract = self.adapter_scaffold.export_resource_transport_contract(resource_name)
        transport_context = self.normalize_transport_context(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            headers=headers,
            session_claims=session_claims,
            transport_contract=transport_contract,
        )
        transport_assessment = _assess_public_transport_context(transport_context)
        preflight_assessment = self.assess_preflight(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_kind="http",
            route_contract=dispatch.route_contract,
            response_contract=dispatch.response_contract,
            recovery_policy=dispatch.recovery_policy,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
        )
        return PublicMcpHttpEnvelope(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_contract=transport_contract,
            transport_context=transport_context,
            transport_assessment=transport_assessment,
            preflight_assessment=preflight_assessment,
            orchestration_summary=self.summarize_orchestration(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="http",
                route_contract=dispatch.route_contract,
                recovery_policy=dispatch.recovery_policy,
                lifecycle_control_profile=self.adapter_scaffold.export_resource_lifecycle_control_profile(resource_name),
                transport_context=transport_context,
                preflight_assessment=preflight_assessment,
            ),
            dispatch=dispatch,
            lifecycle_control_profile=self.adapter_scaffold.export_resource_lifecycle_control_profile(resource_name),
        )

    def execute_framework_dispatch(
        self,
        dispatch: PublicMcpFrameworkDispatch,
        **handler_kwargs: Any,
    ) -> PublicMcpNormalizedResponse:
        handler = getattr(FrameworkRouteBindings, dispatch.handler_name)
        response = handler(request=dispatch.request, **handler_kwargs)
        response_contract = dispatch.response_contract
        if response_contract is None:
            raise ValueError(f"Missing public MCP response contract for framework dispatch: {dispatch.route_name}")
        return _normalize_public_framework_response(
            dispatch.name,
            dispatch.route_name,
            dispatch.kind,
            response_contract,
            response,
            lifecycle_control_profile=dispatch.lifecycle_control_profile,
        )

    def execute_framework_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpNormalizedResponse:
        dispatch = self.build_framework_tool_dispatch(
            tool_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        return self.execute_framework_dispatch(dispatch, **handler_kwargs)

    def execute_framework_resource(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpNormalizedResponse:
        dispatch = self.build_framework_resource_dispatch(
            resource_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        return self.execute_framework_dispatch(dispatch, **handler_kwargs)

    def execute_http_dispatch(
        self,
        dispatch: PublicMcpHttpDispatch,
        **handler_kwargs: Any,
    ) -> PublicMcpNormalizedResponse:
        handler = getattr(RunHttpRouteSurface, _framework_handler_name(dispatch.route_name))
        response = handler(http_request=dispatch.request, **handler_kwargs)
        response_contract = dispatch.response_contract
        if response_contract is None:
            raise ValueError(f"Missing public MCP response contract for http dispatch: {dispatch.route_name}")
        return _normalize_public_http_response(
            dispatch.name,
            dispatch.route_name,
            dispatch.kind,
            response_contract,
            response,
            lifecycle_control_profile=dispatch.lifecycle_control_profile,
        )

    def execute_http_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpNormalizedResponse:
        dispatch = self.build_http_tool_dispatch(
            tool_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        return self.execute_http_dispatch(dispatch, **handler_kwargs)

    def execute_http_resource(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpNormalizedResponse:
        dispatch = self.build_http_resource_dispatch(
            resource_name,
            arguments,
            headers=headers,
            session_claims=session_claims,
        )
        return self.execute_http_dispatch(dispatch, **handler_kwargs)

    def _framework_request_from_invocation(
        self,
        invocation: PublicMcpInvocation,
        *,
        headers: Mapping[str, Any] | None,
        session_claims: Mapping[str, Any] | None,
    ) -> FrameworkInboundRequest:
        return FrameworkInboundRequest(
            method=invocation.method,
            path=invocation.path,
            headers=dict(headers or {}),
            path_params=dict(invocation.path_params),
            query_params=dict(invocation.query_params),
            json_body=invocation.json_body,
            session_claims=dict(session_claims) if session_claims is not None else None,
        )

    def _http_request_from_invocation(
        self,
        invocation: PublicMcpInvocation,
        *,
        headers: Mapping[str, Any] | None,
        session_claims: Mapping[str, Any] | None,
    ) -> HttpRouteRequest:
        return HttpRouteRequest(
            method=invocation.method,
            path=invocation.path,
            headers=dict(headers or {}),
            path_params=dict(invocation.path_params),
            query_params=dict(invocation.query_params),
            json_body=invocation.json_body,
            session_claims=dict(session_claims) if session_claims is not None else None,
        )

    def _tool_binding(self, descriptor: PublicMcpToolDescriptor) -> PublicMcpHostRouteBinding:
        framework_definition = _framework_route_definition(descriptor.route_name)
        return PublicMcpHostRouteBinding(
            name=descriptor.name,
            route_name=descriptor.route_name,
            binding_kind="tool",
            method=framework_definition.method,
            path_template=framework_definition.path_template,
            framework_handler_name=_framework_handler_name(descriptor.route_name),
            path_param_names=_path_template_keys(framework_definition.path_template),
        )

    def _resource_binding(self, descriptor: PublicMcpResourceDescriptor) -> PublicMcpHostRouteBinding:
        framework_definition = _framework_route_definition(descriptor.route_name)
        return PublicMcpHostRouteBinding(
            name=descriptor.name,
            route_name=descriptor.route_name,
            binding_kind="resource",
            method=framework_definition.method,
            path_template=framework_definition.path_template,
            framework_handler_name=_framework_handler_name(descriptor.route_name),
            path_param_names=_path_template_keys(framework_definition.path_template),
        )


    def execute_framework_dispatch_report(
        self,
        dispatch: PublicMcpFrameworkDispatch,
        *,
        transport_context: PublicMcpTransportContext | None = None,
        transport_assessment: PublicMcpTransportAssessment | None = None,
        preflight_assessment: PublicMcpPreflightAssessment | None = None,
        orchestration_summary: PublicMcpOrchestrationSummary | None = None,
        lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpExecutionReport:
        try:
            handler = getattr(FrameworkRouteBindings, dispatch.handler_name)
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="framework",
                phase="binding_lookup",
                exc=exc,
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                orchestration_summary=orchestration_summary,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        try:
            response = handler(request=dispatch.request, **handler_kwargs)
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="framework",
                phase="handler_execution",
                exc=exc,
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                orchestration_summary=orchestration_summary,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        response_contract = dispatch.response_contract
        if response_contract is None:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="framework",
                phase="response_normalization",
                exc=ValueError(f"Missing public MCP response contract for framework dispatch: {dispatch.route_name}"),
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        try:
            normalized = _normalize_public_framework_response(
                dispatch.name,
                dispatch.route_name,
                dispatch.kind,
                response_contract,
                response,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="framework",
                phase="response_normalization",
                exc=exc,
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        return PublicMcpExecutionReport(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_kind="framework",
            phase="completed",
            transport_context=transport_context,
            transport_assessment=transport_assessment,
            preflight_assessment=preflight_assessment,
            lifecycle_control_profile=lifecycle_control_profile,
            lifecycle_state_hint=normalized.lifecycle_state_hint,
            normalized_response=normalized,
        )

    def execute_framework_tool_report(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpExecutionReport:
        try:
            envelope = self.build_framework_tool_envelope(
                tool_name,
                arguments,
                headers=headers,
                session_claims=session_claims,
            )
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=tool_name,
                route_name=tool_name,
                kind="tool",
                transport_kind="framework",
                phase="dispatch_build",
                exc=exc,
            )
        return self.execute_framework_dispatch_report(
            envelope.dispatch,
            transport_context=envelope.transport_context,
            transport_assessment=envelope.transport_assessment,
            preflight_assessment=envelope.preflight_assessment,
            orchestration_summary=envelope.orchestration_summary,
            lifecycle_control_profile=envelope.lifecycle_control_profile,
            **handler_kwargs,
        )

    def execute_framework_resource_report(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpExecutionReport:
        try:
            envelope = self.build_framework_resource_envelope(
                resource_name,
                arguments,
                headers=headers,
                session_claims=session_claims,
            )
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=resource_name,
                route_name=resource_name,
                kind="resource",
                transport_kind="framework",
                phase="dispatch_build",
                exc=exc,
            )
        return self.execute_framework_dispatch_report(
            envelope.dispatch,
            transport_context=envelope.transport_context,
            transport_assessment=envelope.transport_assessment,
            preflight_assessment=envelope.preflight_assessment,
            orchestration_summary=envelope.orchestration_summary,
            lifecycle_control_profile=envelope.lifecycle_control_profile,
            **handler_kwargs,
        )

    def execute_http_dispatch_report(
        self,
        dispatch: PublicMcpHttpDispatch,
        *,
        transport_context: PublicMcpTransportContext | None = None,
        transport_assessment: PublicMcpTransportAssessment | None = None,
        preflight_assessment: PublicMcpPreflightAssessment | None = None,
        orchestration_summary: PublicMcpOrchestrationSummary | None = None,
        lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpExecutionReport:
        try:
            handler = getattr(RunHttpRouteSurface, _framework_handler_name(dispatch.route_name))
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="http",
                phase="binding_lookup",
                exc=exc,
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        try:
            response = handler(http_request=dispatch.request, **handler_kwargs)
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="http",
                phase="handler_execution",
                exc=exc,
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        response_contract = dispatch.response_contract
        if response_contract is None:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="http",
                phase="response_normalization",
                exc=ValueError(f"Missing public MCP response contract for http dispatch: {dispatch.route_name}"),
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        try:
            normalized = _normalize_public_http_response(
                dispatch.name,
                dispatch.route_name,
                dispatch.kind,
                response_contract,
                response,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=dispatch.name,
                route_name=dispatch.route_name,
                kind=dispatch.kind,
                transport_kind="http",
                phase="response_normalization",
                exc=exc,
                recovery_policy=dispatch.recovery_policy,
                transport_context=transport_context,
                transport_assessment=transport_assessment,
                preflight_assessment=preflight_assessment,
                lifecycle_control_profile=lifecycle_control_profile,
            )
        return PublicMcpExecutionReport(
            name=dispatch.name,
            route_name=dispatch.route_name,
            kind=dispatch.kind,
            transport_kind="http",
            phase="completed",
            transport_context=transport_context,
            transport_assessment=transport_assessment,
            preflight_assessment=preflight_assessment,
            lifecycle_control_profile=lifecycle_control_profile,
            lifecycle_state_hint=normalized.lifecycle_state_hint,
            normalized_response=normalized,
        )

    def execute_http_tool_report(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpExecutionReport:
        try:
            envelope = self.build_http_tool_envelope(
                tool_name,
                arguments,
                headers=headers,
                session_claims=session_claims,
            )
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=tool_name,
                route_name=tool_name,
                kind="tool",
                transport_kind="http",
                phase="dispatch_build",
                exc=exc,
            )
        return self.execute_http_dispatch_report(
            envelope.dispatch,
            transport_context=envelope.transport_context,
            transport_assessment=envelope.transport_assessment,
            preflight_assessment=envelope.preflight_assessment,
            **handler_kwargs,
        )

    def execute_http_resource_report(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, Any] | None = None,
        session_claims: Mapping[str, Any] | None = None,
        **handler_kwargs: Any,
    ) -> PublicMcpExecutionReport:
        try:
            envelope = self.build_http_resource_envelope(
                resource_name,
                arguments,
                headers=headers,
                session_claims=session_claims,
            )
        except Exception as exc:
            return _public_mcp_execution_report_error(
                name=resource_name,
                route_name=resource_name,
                kind="resource",
                transport_kind="http",
                phase="dispatch_build",
                exc=exc,
            )
        return self.execute_http_dispatch_report(
            envelope.dispatch,
            transport_context=envelope.transport_context,
            transport_assessment=envelope.transport_assessment,
            preflight_assessment=envelope.preflight_assessment,
            **handler_kwargs,
        )


@dataclass(frozen=True)
class PublicMcpInvocation:
    route_name: str
    kind: str
    method: str
    path: str
    url: str | None
    path_params: Mapping[str, str]
    query_params: Mapping[str, str]
    json_body: Mapping[str, Any] | None


@dataclass(frozen=True)
class PublicMcpToolExport:
    name: str
    description: str
    route_name: str
    invocation: PublicMcpInvocation
    request_type: PublicTypeRef | None = None
    response_type: PublicTypeRef | None = None
    argument_schema: PublicMcpArgumentSchema | None = None
    route_contract: PublicMcpRouteContract | None = None
    response_contract: PublicMcpResponseContract | None = None
    recovery_policy: PublicMcpRecoveryPolicy | None = None
    transport_contract: PublicMcpTransportContract | None = None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpResourceExport:
    name: str
    description: str
    route_name: str
    uri_template: str
    invocation: PublicMcpInvocation
    response_type: PublicTypeRef | None = None
    argument_schema: PublicMcpArgumentSchema | None = None
    route_contract: PublicMcpRouteContract | None = None
    response_contract: PublicMcpResponseContract | None = None
    recovery_policy: PublicMcpRecoveryPolicy | None = None
    transport_contract: PublicMcpTransportContract | None = None
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpAdapterExport:
    transport_kind: str
    stability: str
    compatibility_policy: PublicMcpCompatibilityPolicy
    tools: tuple[PublicMcpToolExport, ...]
    resources: tuple[PublicMcpResourceExport, ...]


@dataclass(frozen=True)
class PublicMcpAdapterScaffold:
    surface: PublicMcpCompatibilitySurface
    base_url: str | None = None
    resource_uri_prefix: str = "nexa://public"

    def export(self) -> PublicMcpAdapterExport:
        return PublicMcpAdapterExport(
            transport_kind="http-route-bridge",
            stability="scaffold",
            compatibility_policy=self.compatibility_policy(),
            tools=tuple(self._export_tool_descriptor(tool) for tool in self.surface.tools),
            resources=tuple(self._export_resource_descriptor(resource) for resource in self.surface.resources),
        )

    def export_manifest(
        self,
        *,
        server_name: str = "nexa-public",
        server_title: str = "Nexa Public Integration Surface",
    ) -> PublicMcpManifest:
        return PublicMcpManifest(
            compatibility_policy=self.compatibility_policy(),
            server_name=server_name,
            server_title=server_title,
            transport_kind="http-route-bridge",
            stability="scaffold",
            base_url=self.base_url,
            resource_uri_prefix=self.resource_uri_prefix,
            tools=tuple(self._manifest_tool(tool) for tool in self.surface.tools),
            resources=tuple(self._manifest_resource(resource) for resource in self.surface.resources),
        )

    def compatibility_policy(self) -> PublicMcpCompatibilityPolicy:
        return PublicMcpCompatibilityPolicy(
            supported_contract_markers=build_public_mcp_contract_markers(),
            supported_runtime_markers=build_public_mcp_runtime_markers(),
            supported_transport_kinds=("http-route-bridge", "framework-bridge"),
        )

    def assert_consumer_compatibility(
        self,
        *,
        required_contract_markers: tuple[str, ...] = (),
        required_runtime_markers: tuple[str, ...] = (),
        transport_kind: str | None = None,
    ) -> None:
        self.compatibility_policy().assert_supported(
            required_contract_markers=required_contract_markers,
            required_runtime_markers=required_runtime_markers,
            transport_kind=transport_kind,
        )

    def export_tool_schema(self, tool_name: str) -> PublicMcpArgumentSchema | None:
        descriptor = self._tool_by_name(tool_name)
        return self._argument_schema_for_descriptor(descriptor)

    def export_resource_schema(self, resource_name: str) -> PublicMcpArgumentSchema | None:
        descriptor = self._resource_by_name(resource_name)
        return self._argument_schema_for_descriptor(descriptor)

    def export_tool_contract(self, tool_name: str) -> PublicMcpRouteContract:
        descriptor = self._tool_by_name(tool_name)
        return self._route_contract_for_descriptor(descriptor, kind="tool")

    def export_resource_contract(self, resource_name: str) -> PublicMcpRouteContract:
        descriptor = self._resource_by_name(resource_name)
        return self._route_contract_for_descriptor(descriptor, kind="resource")

    def export_tool_response_contract(self, tool_name: str) -> PublicMcpResponseContract:
        descriptor = self._tool_by_name(tool_name)
        return self._response_contract_for_descriptor(descriptor, kind="tool")

    def export_resource_response_contract(self, resource_name: str) -> PublicMcpResponseContract:
        descriptor = self._resource_by_name(resource_name)
        return self._response_contract_for_descriptor(descriptor, kind="resource")

    def export_tool_recovery_policy(self, tool_name: str) -> PublicMcpRecoveryPolicy:
        descriptor = self._tool_by_name(tool_name)
        return self._recovery_policy_for_descriptor(descriptor, kind="tool")

    def export_resource_recovery_policy(self, resource_name: str) -> PublicMcpRecoveryPolicy:
        descriptor = self._resource_by_name(resource_name)
        return self._recovery_policy_for_descriptor(descriptor, kind="resource")

    def export_tool_transport_contract(self, tool_name: str) -> PublicMcpTransportContract:
        descriptor = self._tool_by_name(tool_name)
        return self._transport_contract_for_descriptor(descriptor, kind="tool")

    def export_resource_transport_contract(self, resource_name: str) -> PublicMcpTransportContract:
        descriptor = self._resource_by_name(resource_name)
        return self._transport_contract_for_descriptor(descriptor, kind="resource")

    def export_tool_lifecycle_control_profile(self, tool_name: str) -> PublicMcpLifecycleControlProfile:
        descriptor = self._tool_by_name(tool_name)
        return self._lifecycle_control_profile_for_descriptor(descriptor, kind="tool")

    def export_resource_lifecycle_control_profile(self, resource_name: str) -> PublicMcpLifecycleControlProfile:
        descriptor = self._resource_by_name(resource_name)
        return self._lifecycle_control_profile_for_descriptor(descriptor, kind="resource")

    def normalize_tool_arguments(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> PublicMcpNormalizedArguments:
        descriptor = self._tool_by_name(tool_name)
        route_contract = self._route_contract_for_descriptor(descriptor, kind="tool")
        normalized = _normalize_public_mcp_arguments(
            method=descriptor.method,
            path_template=descriptor.path,
            arguments=arguments,
            kind="tool",
            schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=route_contract,
        )
        return PublicMcpNormalizedArguments(
            name=descriptor.name,
            route_name=descriptor.route_name,
            kind="tool",
            route_contract=route_contract,
            path_params=normalized["path_params"],
            query_params=normalized["query_params"],
            json_body=normalized["json_body"],
        )

    def normalize_resource_arguments(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> PublicMcpNormalizedArguments:
        descriptor = self._resource_by_name(resource_name)
        route_contract = self._route_contract_for_descriptor(descriptor, kind="resource")
        normalized = _normalize_public_mcp_arguments(
            method=descriptor.method,
            path_template=descriptor.path,
            arguments=arguments,
            kind="resource",
            schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=route_contract,
        )
        return PublicMcpNormalizedArguments(
            name=descriptor.name,
            route_name=descriptor.route_name,
            kind="resource",
            route_contract=route_contract,
            path_params=normalized["path_params"],
            query_params=normalized["query_params"],
            json_body=normalized["json_body"],
        )

    def normalize_framework_tool_response(
        self,
        tool_name: str,
        response: "FrameworkOutboundResponse",
    ) -> PublicMcpNormalizedResponse:
        descriptor = self._tool_by_name(tool_name)
        return _normalize_public_framework_response(
            descriptor.name,
            descriptor.route_name,
            "tool",
            self._response_contract_for_descriptor(descriptor, kind="tool"),
            response,
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="tool"),
        )

    def normalize_framework_resource_response(
        self,
        resource_name: str,
        response: "FrameworkOutboundResponse",
    ) -> PublicMcpNormalizedResponse:
        descriptor = self._resource_by_name(resource_name)
        return _normalize_public_framework_response(
            descriptor.name,
            descriptor.route_name,
            "resource",
            self._response_contract_for_descriptor(descriptor, kind="resource"),
            response,
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="resource"),
        )

    def normalize_http_tool_response(
        self,
        tool_name: str,
        response: "HttpRouteResponse",
    ) -> PublicMcpNormalizedResponse:
        descriptor = self._tool_by_name(tool_name)
        return _normalize_public_http_response(
            descriptor.name,
            descriptor.route_name,
            "tool",
            self._response_contract_for_descriptor(descriptor, kind="tool"),
            response,
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="tool"),
        )

    def normalize_http_resource_response(
        self,
        resource_name: str,
        response: "HttpRouteResponse",
    ) -> PublicMcpNormalizedResponse:
        descriptor = self._resource_by_name(resource_name)
        return _normalize_public_http_response(
            descriptor.name,
            descriptor.route_name,
            "resource",
            self._response_contract_for_descriptor(descriptor, kind="resource"),
            response,
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="resource"),
        )

    def export_tool(
        self,
        tool_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query_params: Mapping[str, object] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> PublicMcpToolExport:
        descriptor = self._tool_by_name(tool_name)
        invocation = self._build_invocation(
            descriptor.route_name,
            kind="tool",
            method=descriptor.method,
            path_template=descriptor.path,
            path_params=path_params,
            query_params=query_params,
            json_body=json_body,
        )
        return PublicMcpToolExport(
            name=descriptor.name,
            description=descriptor.description,
            route_name=descriptor.route_name,
            invocation=invocation,
            request_type=descriptor.request_type,
            response_type=descriptor.response_type,
            argument_schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=self._route_contract_for_descriptor(descriptor, kind="tool"),
            response_contract=self._response_contract_for_descriptor(descriptor, kind="tool"),
            recovery_policy=self._recovery_policy_for_descriptor(descriptor, kind="tool"),
            transport_contract=self._transport_contract_for_descriptor(descriptor, kind="tool"),
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="tool"),
            tags=descriptor.tags,
        )

    def export_resource(
        self,
        resource_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query_params: Mapping[str, object] | None = None,
    ) -> PublicMcpResourceExport:
        descriptor = self._resource_by_name(resource_name)
        invocation = self._build_invocation(
            descriptor.route_name,
            kind="resource",
            method=descriptor.method,
            path_template=descriptor.path,
            path_params=path_params,
            query_params=query_params,
            json_body=None,
        )
        uri_template = self._resource_uri_template(descriptor.path)
        return PublicMcpResourceExport(
            name=descriptor.name,
            description=descriptor.description,
            route_name=descriptor.route_name,
            uri_template=uri_template,
            invocation=invocation,
            response_type=descriptor.response_type,
            argument_schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=self._route_contract_for_descriptor(descriptor, kind="resource"),
            response_contract=self._response_contract_for_descriptor(descriptor, kind="resource"),
            recovery_policy=self._recovery_policy_for_descriptor(descriptor, kind="resource"),
            transport_contract=self._transport_contract_for_descriptor(descriptor, kind="resource"),
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="resource"),
            tags=descriptor.tags,
        )

    def export_tool_from_arguments(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> PublicMcpToolExport:
        normalized = self.normalize_tool_arguments(tool_name, arguments)
        return self.export_tool(
            tool_name,
            path_params=normalized.path_params,
            query_params=normalized.query_params,
            json_body=normalized.json_body,
        )

    def export_resource_from_arguments(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> PublicMcpResourceExport:
        normalized = self.normalize_resource_arguments(resource_name, arguments)
        return self.export_resource(
            resource_name,
            path_params=normalized.path_params,
            query_params=normalized.query_params,
        )


    def _export_tool_descriptor(self, descriptor: PublicMcpToolDescriptor) -> PublicMcpToolExport:
        invocation = self._build_invocation(
            descriptor.route_name,
            kind="tool",
            method=descriptor.method,
            path_template=descriptor.path,
            path_params=None,
            query_params=None,
            json_body=None,
            allow_unresolved_template=True,
        )
        return PublicMcpToolExport(
            name=descriptor.name,
            description=descriptor.description,
            route_name=descriptor.route_name,
            invocation=invocation,
            request_type=descriptor.request_type,
            response_type=descriptor.response_type,
            argument_schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=self._route_contract_for_descriptor(descriptor, kind="tool"),
            response_contract=self._response_contract_for_descriptor(descriptor, kind="tool"),
            recovery_policy=self._recovery_policy_for_descriptor(descriptor, kind="tool"),
            transport_contract=self._transport_contract_for_descriptor(descriptor, kind="tool"),
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="tool"),
            tags=descriptor.tags,
        )

    def _export_resource_descriptor(self, descriptor: PublicMcpResourceDescriptor) -> PublicMcpResourceExport:
        invocation = self._build_invocation(
            descriptor.route_name,
            kind="resource",
            method=descriptor.method,
            path_template=descriptor.path,
            path_params=None,
            query_params=None,
            json_body=None,
            allow_unresolved_template=True,
        )
        return PublicMcpResourceExport(
            name=descriptor.name,
            description=descriptor.description,
            route_name=descriptor.route_name,
            uri_template=self._resource_uri_template(descriptor.path),
            invocation=invocation,
            response_type=descriptor.response_type,
            argument_schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=self._route_contract_for_descriptor(descriptor, kind="resource"),
            response_contract=self._response_contract_for_descriptor(descriptor, kind="resource"),
            recovery_policy=self._recovery_policy_for_descriptor(descriptor, kind="resource"),
            transport_contract=self._transport_contract_for_descriptor(descriptor, kind="resource"),
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="resource"),
            tags=descriptor.tags,
        )

    def _manifest_tool(self, descriptor: PublicMcpToolDescriptor) -> PublicMcpManifestTool:
        return PublicMcpManifestTool(
            name=descriptor.name,
            description=descriptor.description,
            route_name=descriptor.route_name,
            method=descriptor.method,
            path=descriptor.path,
            request_type=descriptor.request_type,
            response_type=descriptor.response_type,
            argument_schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=self._route_contract_for_descriptor(descriptor, kind="tool"),
            response_contract=self._response_contract_for_descriptor(descriptor, kind="tool"),
            recovery_policy=self._recovery_policy_for_descriptor(descriptor, kind="tool"),
            transport_contract=self._transport_contract_for_descriptor(descriptor, kind="tool"),
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="tool"),
            tags=descriptor.tags,
        )

    def _manifest_resource(self, descriptor: PublicMcpResourceDescriptor) -> PublicMcpManifestResource:
        return PublicMcpManifestResource(
            name=descriptor.name,
            description=descriptor.description,
            route_name=descriptor.route_name,
            method=descriptor.method,
            path=descriptor.path,
            uri_template=self._resource_uri_template(descriptor.path),
            response_type=descriptor.response_type,
            argument_schema=self._argument_schema_for_descriptor(descriptor),
            route_contract=self._route_contract_for_descriptor(descriptor, kind="resource"),
            response_contract=self._response_contract_for_descriptor(descriptor, kind="resource"),
            recovery_policy=self._recovery_policy_for_descriptor(descriptor, kind="resource"),
            transport_contract=self._transport_contract_for_descriptor(descriptor, kind="resource"),
            lifecycle_control_profile=self._lifecycle_control_profile_for_descriptor(descriptor, kind="resource"),
            tags=descriptor.tags,
        )

    def _lifecycle_control_profile_for_descriptor(
        self,
        descriptor: PublicMcpToolDescriptor | PublicMcpResourceDescriptor,
        *,
        kind: str,
    ) -> PublicMcpLifecycleControlProfile:
        route_contract = self._route_contract_for_descriptor(descriptor, kind=kind)
        spec = _LIFECYCLE_CONTROL_BY_ROUTE_FAMILY.get(route_contract.route_family)
        if spec is None:
            raise ValueError(f"Missing public MCP lifecycle control profile for route_family: {route_contract.route_family}")
        return PublicMcpLifecycleControlProfile(
            name=descriptor.name,
            route_name=descriptor.route_name,
            kind=kind,
            route_family=route_contract.route_family,
            lifecycle_class=str(spec["lifecycle_class"]),
            status_resource_name=spec.get("status_resource_name"),
            result_resource_name=spec.get("result_resource_name"),
            actions_resource_name=spec.get("actions_resource_name"),
            trace_resource_name=spec.get("trace_resource_name"),
            artifacts_resource_name=spec.get("artifacts_resource_name"),
            source_resource_names=tuple(spec.get("source_resource_names", ())),
            preferred_control_tool_names=tuple(spec.get("preferred_control_tool_names", ())),
            followup_route_names=tuple(spec.get("followup_route_names", ())),
            review_tool_name=spec.get("review_tool_name"),
        )

    def _tool_by_name(self, tool_name: str) -> PublicMcpToolDescriptor:
        for tool in self.surface.tools:
            if tool.name == tool_name:
                return tool
        raise ValueError(f"Unknown MCP tool export name: {tool_name}")

    def _resource_by_name(self, resource_name: str) -> PublicMcpResourceDescriptor:
        for resource in self.surface.resources:
            if resource.name == resource_name:
                return resource
        raise ValueError(f"Unknown MCP resource export name: {resource_name}")

    def _argument_schema_for_descriptor(
        self,
        descriptor: PublicMcpToolDescriptor | PublicMcpResourceDescriptor,
    ) -> PublicMcpArgumentSchema | None:
        spec = _ARGUMENT_SCHEMA_BY_ROUTE_NAME.get(descriptor.route_name)
        if spec is None:
            return None
        return PublicMcpArgumentSchema(
            name=descriptor.name,
            route_name=descriptor.route_name,
            path_fields=tuple(spec.get("path_fields", ())),
            query_fields=tuple(spec.get("query_fields", ())),
            body_fields=tuple(spec.get("body_fields", ())),
            allow_additional_query_params=bool(spec.get("allow_additional_query_params", False)),
            allow_additional_body_fields=bool(spec.get("allow_additional_body_fields", False)),
        )

    def _route_contract_for_descriptor(
        self,
        descriptor: PublicMcpToolDescriptor | PublicMcpResourceDescriptor,
        *,
        kind: str,
    ) -> PublicMcpRouteContract:
        spec = _ROUTE_CONTRACT_BY_ROUTE_NAME.get(descriptor.route_name)
        if spec is None:
            raise ValueError(f"Missing public MCP route contract for route_name: {descriptor.route_name}")
        schema = self._argument_schema_for_descriptor(descriptor)
        return PublicMcpRouteContract(
            name=descriptor.name,
            route_name=descriptor.route_name,
            kind=kind,
            route_family=str(spec["route_family"]),
            transport_profile=str(spec["transport_profile"]),
            path_param_names=tuple(field.name for field in schema.path_fields) if schema is not None else (),
            query_param_names=tuple(field.name for field in schema.query_fields) if schema is not None else (),
            body_field_names=tuple(field.name for field in schema.body_fields) if schema is not None else (),
            allow_additional_query_params=bool(schema.allow_additional_query_params) if schema is not None else False,
            allow_additional_body_fields=bool(schema.allow_additional_body_fields) if schema is not None else False,
        )

    def _response_contract_for_descriptor(
        self,
        descriptor: PublicMcpToolDescriptor | PublicMcpResourceDescriptor,
        *,
        kind: str,
    ) -> PublicMcpResponseContract:
        spec = _RESPONSE_CONTRACT_BY_ROUTE_NAME.get(descriptor.route_name)
        if spec is None:
            raise ValueError(f"Missing public MCP response contract for route_name: {descriptor.route_name}")
        route_contract = self._route_contract_for_descriptor(descriptor, kind=kind)
        return PublicMcpResponseContract(
            name=descriptor.name,
            route_name=descriptor.route_name,
            kind=kind,
            route_family=route_contract.route_family,
            response_shape=str(spec["response_shape"]),
            success_status_codes=tuple(int(code) for code in spec["success_status_codes"]),
            response_media_type=str(spec.get("response_media_type", "application/json")),
            body_kind=str(spec.get("body_kind", "object")),
            required_top_level_keys=tuple(str(key) for key in spec.get("required_top_level_keys", ())),
            result_shape_profile=self._result_shape_profile_for_descriptor(descriptor, kind=kind),
            response_type=getattr(descriptor, "response_type", None),
        )

    def _result_shape_profile_for_descriptor(
        self,
        descriptor: PublicMcpToolDescriptor | PublicMcpResourceDescriptor,
        *,
        kind: str,
    ) -> PublicMcpResultShapeProfile:
        route_contract = self._route_contract_for_descriptor(descriptor, kind=kind)
        spec = _RESULT_SHAPE_PROFILE_BY_ROUTE_NAME.get(descriptor.route_name)
        if spec is None:
            raise ValueError(f"Missing public MCP result-shape profile for route_name: {descriptor.route_name}")
        return PublicMcpResultShapeProfile(
            profile_kind=str(spec["profile_kind"]),
            identity_keys=tuple(str(key) for key in spec.get("identity_keys", ())),
            state_keys=tuple(str(key) for key in spec.get("state_keys", ())),
            collection_field_name=(str(spec["collection_field_name"]) if spec.get("collection_field_name") is not None else None),
            count_field_name=(str(spec["count_field_name"]) if spec.get("count_field_name") is not None else None),
            collection_item_identity_keys=tuple(str(key) for key in spec.get("collection_item_identity_keys", ())),
        )

    def _recovery_policy_for_descriptor(
        self,
        descriptor: PublicMcpToolDescriptor | PublicMcpResourceDescriptor,
        *,
        kind: str,
    ) -> PublicMcpRecoveryPolicy:
        route_contract = self._route_contract_for_descriptor(descriptor, kind=kind)
        spec = _RECOVERY_POLICY_BY_ROUTE_FAMILY.get(route_contract.route_family)
        if spec is None:
            raise ValueError(f"Missing public MCP recovery policy for route_family: {route_contract.route_family}")
        return PublicMcpRecoveryPolicy(
            name=descriptor.name,
            route_name=descriptor.route_name,
            kind=kind,
            route_family=route_contract.route_family,
            idempotency_class=str(spec["idempotency_class"]),
            timeout_retryable=bool(spec["timeout_retryable"]),
            safe_to_retry_same_request_on_timeout=bool(spec["safe_to_retry_same_request_on_timeout"]),
            timeout_recommended_action=str(spec["timeout_recommended_action"]),
            response_timeout_retryable=bool(spec["response_timeout_retryable"]),
            safe_to_retry_same_request_on_response_timeout=bool(spec["safe_to_retry_same_request_on_response_timeout"]),
            response_timeout_recommended_action=str(spec["response_timeout_recommended_action"]),
            request_contract_recommended_action=str(spec.get("request_contract_recommended_action", "fix_request_arguments")),
            binding_error_recommended_action=str(spec.get("binding_error_recommended_action", "inspect_route_binding")),
            handler_error_recommended_action=str(spec.get("handler_error_recommended_action", "inspect_handler_failure")),
            response_contract_recommended_action=str(spec.get("response_contract_recommended_action", "inspect_response_contract")),
            response_decode_recommended_action=str(spec.get("response_decode_recommended_action", "inspect_response_serialization")),
            response_error_recommended_action=str(spec.get("response_error_recommended_action", "inspect_response_handling")),
            unexpected_error_recommended_action=str(spec.get("unexpected_error_recommended_action", "inspect_unexpected_failure")),
        )

    def _transport_contract_for_descriptor(
        self,
        descriptor: PublicMcpToolDescriptor | PublicMcpResourceDescriptor,
        *,
        kind: str,
    ) -> PublicMcpTransportContract:
        route_contract = self._route_contract_for_descriptor(descriptor, kind=kind)
        session_mode = (
            "recommended-pass-through"
            if route_contract.route_family in {
                "run-launch",
                "workspace-shell-launch",
                "workspace-shell-commit",
                "workspace-shell-checkout",
                "workspace-create",
                "workspace-provider-binding-write",
                "workspace-provider-probe",
                "onboarding-write",
                "run-control",
            }
            else "optional-pass-through"
        )
        session_contract = PublicMcpSessionContract(
            mode=session_mode,
            subject_claim_names=("user_id", "sub", "subject"),
            session_id_claim_names=("session_id", "sid", "session"),
            optional_claim_names=("email", "name", "display_name", "username", "org_id", "roles"),
        )
        return PublicMcpTransportContract(
            name=descriptor.name,
            route_name=descriptor.route_name,
            kind=kind,
            route_family=route_contract.route_family,
            transport_profile=route_contract.transport_profile,
            header_mode="selective-forward",
            session_mode=session_mode,
            request_id_mode="recommended",
            language_mode="optional",
            authorization_mode=("recommended-pass-through" if session_mode == "recommended-pass-through" else "optional-pass-through"),
            session_subject_mode=("recommended-pass-through" if session_mode == "recommended-pass-through" else "optional-pass-through"),
            session_contract=session_contract,
        )

    def _build_invocation(
        self,
        route_name: str,
        *,
        kind: str,
        method: str,
        path_template: str,
        path_params: Mapping[str, object] | None,
        query_params: Mapping[str, object] | None,
        json_body: Mapping[str, Any] | None,
        allow_unresolved_template: bool = False,
    ) -> PublicMcpInvocation:
        normalized_path_params = _normalize_string_mapping(path_params)
        normalized_query_params = _normalize_string_mapping(query_params)
        resolved_path = _resolve_path_template(
            path_template,
            normalized_path_params,
            allow_unresolved_template=allow_unresolved_template,
        )
        return PublicMcpInvocation(
            route_name=route_name,
            kind=kind,
            method=method,
            path=resolved_path,
            url=_compose_url(self.base_url, resolved_path, normalized_query_params),
            path_params=normalized_path_params,
            query_params=normalized_query_params,
            json_body=dict(json_body) if json_body is not None else None,
        )

    def _resource_uri_template(self, path_template: str) -> str:
        normalized_prefix = self.resource_uri_prefix.rstrip("/")
        if not normalized_prefix:
            raise ValueError("resource_uri_prefix must not be empty")
        return f"{normalized_prefix}{path_template}"


def _type_ref_dict(type_ref: PublicTypeRef | None) -> dict[str, str] | None:
    if type_ref is None:
        return None
    return {"module": type_ref.module, "name": type_ref.name}


def _argument_field_dict(field: PublicMcpArgumentField) -> dict[str, Any]:
    return {
        "name": field.name,
        "location": field.location,
        "value_kind": field.value_kind,
        "required": field.required,
        "description": field.description,
        "enum_values": list(field.enum_values),
    }


def _argument_schema_dict(schema: PublicMcpArgumentSchema | None) -> dict[str, Any] | None:
    if schema is None:
        return None
    return schema.to_dict()



def _assert_public_result_shape_profile_matches_body(
    result_shape_profile: PublicMcpResultShapeProfile | None,
    *,
    route_name: str,
    body: Any,
) -> None:
    if result_shape_profile is None:
        return
    if not isinstance(body, Mapping):
        raise ValueError(
            f"Result-shape profile cannot be checked for public route {route_name}: body is not an object"
        )
    missing_identity = [key for key in result_shape_profile.identity_keys if key not in body]
    if missing_identity:
        raise ValueError(
            f"Missing required identity keys for public route {route_name}: {', '.join(missing_identity)}"
        )
    missing_state = [key for key in result_shape_profile.state_keys if key not in body]
    if missing_state:
        raise ValueError(
            f"Missing required state keys for public route {route_name}: {', '.join(missing_state)}"
        )
    if result_shape_profile.count_field_name is not None:
        if result_shape_profile.count_field_name not in body:
            raise ValueError(
                f"Missing required count field for public route {route_name}: {result_shape_profile.count_field_name}"
            )
        if not isinstance(body[result_shape_profile.count_field_name], int):
            raise ValueError(
                f"Invalid count field for public route {route_name}: {result_shape_profile.count_field_name} must be int"
            )
    if result_shape_profile.collection_field_name is not None:
        if result_shape_profile.collection_field_name not in body:
            raise ValueError(
                f"Missing required collection field for public route {route_name}: {result_shape_profile.collection_field_name}"
            )
        collection = body[result_shape_profile.collection_field_name]
        if not isinstance(collection, list):
            raise ValueError(
                f"Invalid collection field for public route {route_name}: {result_shape_profile.collection_field_name} must be list"
            )
        if result_shape_profile.collection_item_identity_keys:
            for index, item in enumerate(collection):
                if not isinstance(item, Mapping):
                    raise ValueError(
                        f"Invalid collection item for public route {route_name}: item {index} is not an object"
                    )
                missing_item_keys = [
                    key for key in result_shape_profile.collection_item_identity_keys if key not in item
                ]
                if missing_item_keys:
                    raise ValueError(
                        f"Missing collection item identity keys for public route {route_name} item {index}: {', '.join(missing_item_keys)}"
                    )


def _classify_public_mcp_execution_error(*, phase: str, exc: Exception) -> str:
    if phase == "dispatch_build":
        return "request_contract_error"
    if phase == "binding_lookup":
        return "binding_error"
    if phase == "handler_execution":
        return "handler_error"
    if phase == "response_normalization":
        if isinstance(exc, json.JSONDecodeError):
            return "response_decode_error"
        if isinstance(exc, ValueError):
            return "response_contract_error"
        return "response_error"
    return "unexpected_error"


def _public_mcp_execution_recovery_hint(*, category: str, phase: str, exc: Exception, recovery_policy: PublicMcpRecoveryPolicy | None = None) -> PublicMcpRecoveryHint:
    transient = isinstance(exc, (TimeoutError, ConnectionError))
    if category == "request_contract_error":
        return PublicMcpRecoveryHint(
            retryable=False,
            safe_to_retry_same_request=False,
            recoverability="caller_fix_required",
            recommended_action=(recovery_policy.request_contract_recommended_action if recovery_policy is not None else "fix_request_arguments"),
        )
    if category == "binding_error":
        return PublicMcpRecoveryHint(
            retryable=False,
            safe_to_retry_same_request=False,
            recoverability="integration_fix_required",
            recommended_action=(recovery_policy.binding_error_recommended_action if recovery_policy is not None else "inspect_route_binding"),
        )
    if category == "handler_error":
        if transient:
            retryable = recovery_policy.timeout_retryable if recovery_policy is not None else True
            safe_same = recovery_policy.safe_to_retry_same_request_on_timeout if recovery_policy is not None else True
            action = recovery_policy.timeout_recommended_action if recovery_policy is not None else "retry_same_request"
            recoverability = "transient_retry_possible" if safe_same else "manual_verification_before_retry"
            return PublicMcpRecoveryHint(
                retryable=retryable,
                safe_to_retry_same_request=safe_same if retryable else False,
                recoverability=recoverability if retryable else "handler_investigation_required",
                recommended_action=action if retryable else (recovery_policy.handler_error_recommended_action if recovery_policy is not None else "inspect_handler_failure"),
            )
        return PublicMcpRecoveryHint(
            retryable=False,
            safe_to_retry_same_request=False,
            recoverability="handler_investigation_required",
            recommended_action=(recovery_policy.handler_error_recommended_action if recovery_policy is not None else "inspect_handler_failure"),
        )
    if category == "response_contract_error":
        return PublicMcpRecoveryHint(
            retryable=False,
            safe_to_retry_same_request=False,
            recoverability="integration_fix_required",
            recommended_action=(recovery_policy.response_contract_recommended_action if recovery_policy is not None else "inspect_response_contract"),
        )
    if category == "response_decode_error":
        return PublicMcpRecoveryHint(
            retryable=False,
            safe_to_retry_same_request=False,
            recoverability="integration_fix_required",
            recommended_action=(recovery_policy.response_decode_recommended_action if recovery_policy is not None else "inspect_response_serialization"),
        )
    if category == "response_error":
        if transient:
            retryable = recovery_policy.response_timeout_retryable if recovery_policy is not None else True
            safe_same = recovery_policy.safe_to_retry_same_request_on_response_timeout if recovery_policy is not None else True
            action = recovery_policy.response_timeout_recommended_action if recovery_policy is not None else "retry_same_request"
            recoverability = "transient_retry_possible" if safe_same else "manual_verification_before_retry"
            return PublicMcpRecoveryHint(
                retryable=retryable,
                safe_to_retry_same_request=safe_same if retryable else False,
                recoverability=recoverability if retryable else "integration_fix_required",
                recommended_action=action if retryable else (recovery_policy.response_error_recommended_action if recovery_policy is not None else "inspect_response_handling"),
            )
        return PublicMcpRecoveryHint(
            retryable=False,
            safe_to_retry_same_request=False,
            recoverability="integration_fix_required",
            recommended_action=(recovery_policy.response_error_recommended_action if recovery_policy is not None else "inspect_response_handling"),
        )
    return PublicMcpRecoveryHint(
        retryable=transient and (recovery_policy.timeout_retryable if recovery_policy is not None else True),
        safe_to_retry_same_request=transient and (recovery_policy.safe_to_retry_same_request_on_timeout if recovery_policy is not None else True),
        recoverability=("manual_verification_before_retry" if transient and recovery_policy is not None and not recovery_policy.safe_to_retry_same_request_on_timeout else ("transient_retry_possible" if transient else "unknown_investigation_required")),
        recommended_action=((recovery_policy.timeout_recommended_action if recovery_policy is not None else "retry_same_request") if transient else (recovery_policy.unexpected_error_recommended_action if recovery_policy is not None else "inspect_unexpected_failure")),
    )


def _build_public_orchestration_summary(
    *,
    name: str,
    route_name: str,
    kind: str,
    transport_kind: str,
    route_contract: PublicMcpRouteContract | None,
    recovery_policy: PublicMcpRecoveryPolicy | None,
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None,
    transport_context: PublicMcpTransportContext | None,
    preflight_assessment: PublicMcpPreflightAssessment | None,
) -> PublicMcpOrchestrationSummary:
    labels: list[str] = []
    next_actions: list[str] = []
    route_family = route_contract.route_family if route_contract is not None else None
    idempotency_class = recovery_policy.idempotency_class if recovery_policy is not None else None
    ready = preflight_assessment.ready if preflight_assessment is not None else True
    risk_level = preflight_assessment.risk_level if preflight_assessment is not None else "unknown"

    if route_family:
        labels.append(route_family)
    if lifecycle_control_profile is not None:
        labels.append(f"lifecycle:{lifecycle_control_profile.lifecycle_class}")
    if idempotency_class:
        labels.append(idempotency_class)
    labels.append(f"transport:{transport_kind}")
    labels.append(f"risk:{risk_level}")
    labels.append("ready" if ready else "not-ready")

    authorization_present = bool(transport_context is not None and transport_context.authorization_present)
    session_present = bool(transport_context is not None and transport_context.session_present)
    session_subject_present = bool(transport_context is not None and transport_context.session_subject is not None)

    if authorization_present:
        labels.append("authorization-present")
    if session_subject_present:
        labels.append("identity-present")

    recommended_action = None
    if preflight_assessment is not None:
        for action in preflight_assessment.suggested_actions:
            _append_unique(next_actions, action)
        if preflight_assessment.blockers:
            _append_unique(next_actions, "resolve_preflight_blockers")
    if recovery_policy is not None:
        _append_unique(next_actions, recovery_policy.timeout_recommended_action)
    if lifecycle_control_profile is not None:
        for route_name_candidate in lifecycle_control_profile.followup_route_names:
            _append_unique(next_actions, route_name_candidate)
        for control_name in lifecycle_control_profile.preferred_control_tool_names:
            _append_unique(next_actions, control_name)
        if lifecycle_control_profile.review_tool_name is not None:
            _append_unique(next_actions, lifecycle_control_profile.review_tool_name)
    if not authorization_present and route_family in {"run-launch", "run-control", "workspace-shell-control"}:
        _append_unique(next_actions, "attach_authorization_before_execution")
    if not session_subject_present and route_family in {"run-launch", "run-control", "workspace-shell-control"}:
        _append_unique(next_actions, "attach_identity_context_before_execution")

    priority_order = (
        "attach_identity_context_before_execution",
        "attach_authorization_before_execution",
        "resolve_preflight_blockers",
        "forward_subject_session_claim",
        "forward_authorization_header",
        "verify_execution_intent",
        "retry_same_request",
    )
    for candidate in priority_order:
        if candidate in next_actions:
            recommended_action = candidate
            break
    if recommended_action is None and next_actions:
        recommended_action = next_actions[0]

    return PublicMcpOrchestrationSummary(
        name=name,
        route_name=route_name,
        kind=kind,
        transport_kind=transport_kind,
        route_family=route_family,
        idempotency_class=idempotency_class,
        ready=ready,
        risk_level=risk_level,
        authorization_present=authorization_present,
        session_present=session_present,
        session_subject_present=session_subject_present,
        recommended_action=recommended_action,
        lifecycle_control_profile=lifecycle_control_profile,
        summary_labels=tuple(labels),
        next_actions=tuple(next_actions),
    )


def _extract_public_lifecycle_observed_state(body: Any) -> str | None:
    if not isinstance(body, Mapping):
        return None
    for key in ("status", "initial_run_status", "final_status", "result_state"):
        value = body.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _classify_public_lifecycle_state_family(observed_state: str | None) -> tuple[str, bool]:
    if observed_state is None:
        return ("unknown", False)
    value = observed_state.lower()
    if value in {"accepted", "queued", "pending"}:
        return ("accepted", False)
    if value in {"running", "in_progress", "streaming"}:
        return ("running", False)
    if value in {"not_ready"}:
        return ("not-ready", False)
    if value in {"succeeded", "completed", "ready"}:
        return ("succeeded", True)
    if value in {"failed", "cancelled", "blocked"}:
        return ("failed", True)
    return ("unknown", False)


def _build_public_lifecycle_state_hint(*, route_name: str, kind: str, lifecycle_control_profile: PublicMcpLifecycleControlProfile | None, body: Any) -> PublicMcpLifecycleStateHint | None:
    if lifecycle_control_profile is None:
        return None
    observed_state = _extract_public_lifecycle_observed_state(body)
    if observed_state is None:
        return None
    state_family, terminal = _classify_public_lifecycle_state_family(observed_state)
    followup: list[str] = []
    controls: list[str] = []
    recommended_action: str | None = None
    if state_family in {"accepted", "running", "not-ready"}:
        _append_unique(followup, lifecycle_control_profile.status_resource_name)
        _append_unique(followup, lifecycle_control_profile.trace_resource_name)
        _append_unique(followup, lifecycle_control_profile.actions_resource_name)
        recommended_action = lifecycle_control_profile.status_resource_name or lifecycle_control_profile.trace_resource_name
    elif state_family == "succeeded":
        _append_unique(followup, lifecycle_control_profile.result_resource_name)
        _append_unique(followup, lifecycle_control_profile.artifacts_resource_name)
        _append_unique(followup, lifecycle_control_profile.trace_resource_name)
        if lifecycle_control_profile.review_tool_name is not None:
            _append_unique(controls, lifecycle_control_profile.review_tool_name)
        recommended_action = lifecycle_control_profile.result_resource_name or lifecycle_control_profile.artifacts_resource_name or lifecycle_control_profile.review_tool_name
    elif state_family == "failed":
        _append_unique(followup, lifecycle_control_profile.result_resource_name)
        _append_unique(followup, lifecycle_control_profile.trace_resource_name)
        _append_unique(followup, lifecycle_control_profile.actions_resource_name)
        for control_name in lifecycle_control_profile.preferred_control_tool_names:
            _append_unique(controls, control_name)
        recommended_action = lifecycle_control_profile.trace_resource_name or (controls[0] if controls else None)
    else:
        for route_name_candidate in lifecycle_control_profile.followup_route_names:
            _append_unique(followup, route_name_candidate)
        for control_name in lifecycle_control_profile.preferred_control_tool_names:
            _append_unique(controls, control_name)
        recommended_action = followup[0] if followup else (controls[0] if controls else None)
    return PublicMcpLifecycleStateHint(
        route_name=route_name,
        kind=kind,
        lifecycle_class=lifecycle_control_profile.lifecycle_class,
        observed_state=observed_state,
        state_family=state_family,
        terminal=terminal,
        recommended_followup_route_names=tuple(followup),
        recommended_control_tool_names=tuple(controls),
        recommended_action=recommended_action,
    )


def _public_mcp_execution_report_error(
    *,
    name: str,
    route_name: str,
    kind: str,
    transport_kind: str,
    phase: str,
    exc: Exception,
    recovery_policy: PublicMcpRecoveryPolicy | None = None,
    transport_context: PublicMcpTransportContext | None = None,
    transport_assessment: PublicMcpTransportAssessment | None = None,
    preflight_assessment: PublicMcpPreflightAssessment | None = None,
    orchestration_summary: PublicMcpOrchestrationSummary | None = None,
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None,
) -> PublicMcpExecutionReport:
    category = _classify_public_mcp_execution_error(phase=phase, exc=exc)
    return PublicMcpExecutionReport(
        name=name,
        route_name=route_name,
        kind=kind,
        transport_kind=transport_kind,
        phase=phase,
        transport_context=transport_context,
        transport_assessment=transport_assessment,
        preflight_assessment=preflight_assessment,
        orchestration_summary=orchestration_summary,
        lifecycle_control_profile=lifecycle_control_profile,
        lifecycle_state_hint=None,
        error=PublicMcpExecutionError(
            category=category,
            phase=phase,
            message=str(exc),
            exception_type=type(exc).__name__,
            recovery_hint=_public_mcp_execution_recovery_hint(category=category, phase=phase, exc=exc, recovery_policy=recovery_policy),
        ),
    )

def _decode_public_response_body(*, media_type: str, body_text: str) -> Any:
    if "json" in media_type.lower():
        return json.loads(body_text)
    return body_text


def _assert_public_response_matches_contract(
    response_contract: PublicMcpResponseContract,
    *,
    status_code: int,
    media_type: str,
) -> None:
    if 200 <= status_code < 300 and status_code not in response_contract.success_status_codes:
        raise ValueError(
            f"Unexpected success status code for public route {response_contract.route_name}: {status_code}; expected one of {', '.join(map(str, response_contract.success_status_codes))}"
        )
    if response_contract.response_media_type and response_contract.response_media_type not in media_type.lower():
        raise ValueError(
            f"Unexpected media type for public route {response_contract.route_name}: {media_type}; expected {response_contract.response_media_type}"
        )


def _assert_public_response_body_matches_contract(
    response_contract: PublicMcpResponseContract,
    *,
    body: Any,
) -> None:
    if response_contract.body_kind == "object" and not isinstance(body, Mapping):
        raise ValueError(
            f"Unexpected response body kind for public route {response_contract.route_name}: expected object"
        )
    if response_contract.required_top_level_keys:
        if not isinstance(body, Mapping):
            raise ValueError(
                f"Required response keys cannot be checked for public route {response_contract.route_name}: body is not an object"
            )
        missing = [key for key in response_contract.required_top_level_keys if key not in body]
        if missing:
            raise ValueError(
                f"Missing required response keys for public route {response_contract.route_name}: {', '.join(missing)}"
            )
    _assert_public_result_shape_profile_matches_body(
        response_contract.result_shape_profile,
        route_name=response_contract.route_name,
        body=body,
    )


def _normalize_public_framework_response(
    name: str,
    route_name: str,
    kind: str,
    response_contract: PublicMcpResponseContract,
    response: "FrameworkOutboundResponse",
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None,
) -> PublicMcpNormalizedResponse:
    _assert_public_response_matches_contract(
        response_contract,
        status_code=response.status_code,
        media_type=response.media_type,
    )
    decoded_body = _decode_public_response_body(media_type=response.media_type, body_text=response.body_text)
    _assert_public_response_body_matches_contract(response_contract, body=decoded_body)
    return PublicMcpNormalizedResponse(
        name=name,
        route_name=route_name,
        kind=kind,
        response_contract=response_contract,
        status_code=response.status_code,
        media_type=response.media_type,
        body=decoded_body,
        lifecycle_state_hint=_build_public_lifecycle_state_hint(route_name=route_name, kind=kind, lifecycle_control_profile=lifecycle_control_profile, body=decoded_body),
    )


def _normalize_public_http_response(
    name: str,
    route_name: str,
    kind: str,
    response_contract: PublicMcpResponseContract,
    response: "HttpRouteResponse",
    lifecycle_control_profile: PublicMcpLifecycleControlProfile | None = None,
) -> PublicMcpNormalizedResponse:
    media_type = str(dict(response.headers).get("content-type", "application/json"))
    _assert_public_response_matches_contract(
        response_contract,
        status_code=response.status_code,
        media_type=media_type,
    )
    decoded_body = dict(response.body)
    _assert_public_response_body_matches_contract(response_contract, body=decoded_body)
    return PublicMcpNormalizedResponse(
        name=name,
        route_name=route_name,
        kind=kind,
        response_contract=response_contract,
        status_code=response.status_code,
        media_type=media_type,
        body=decoded_body,
        lifecycle_state_hint=_build_public_lifecycle_state_hint(route_name=route_name, kind=kind, lifecycle_control_profile=lifecycle_control_profile, body=decoded_body),
    )


def _normalize_public_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
    if headers is None:
        return {}
    normalized: dict[str, str] = {}
    for key, value in headers.items():
        if not isinstance(key, str):
            raise ValueError("Public MCP headers must use string keys")
        normalized[key.strip().lower()] = str(value)
    return normalized


def _normalize_public_session_claims(session_claims: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if session_claims is None:
        return None
    normalized: dict[str, Any] = {}
    for key, value in session_claims.items():
        if not isinstance(key, str):
            raise ValueError("Public MCP session_claims must use string keys")
        normalized[key] = value
    return normalized


def _resolve_session_subject(
    session_claims: Mapping[str, Any] | None,
    session_contract: PublicMcpSessionContract | None,
) -> str | None:
    if not session_claims or session_contract is None:
        return None
    for claim_name in session_contract.subject_claim_names:
        value = session_claims.get(claim_name)
        if value is not None:
            return str(value)
    return None


def _normalize_string_mapping(values: Mapping[str, object] | None) -> Mapping[str, str]:
    if not values:
        return {}
    return {str(key): str(value) for key, value in values.items()}


def _normalize_public_mcp_arguments(
    *,
    method: str,
    path_template: str,
    arguments: Mapping[str, Any] | None,
    kind: str,
    schema: PublicMcpArgumentSchema | None = None,
    route_contract: PublicMcpRouteContract | None = None,
) -> dict[str, Any]:
    raw_arguments = dict(arguments or {})
    path_keys = set(_path_template_keys(path_template))

    nested_path_params = _coerce_mapping(raw_arguments.pop("path_params", None), field_name="path_params")
    nested_query_params = _coerce_mapping(raw_arguments.pop("query_params", None), field_name="query_params")
    body = raw_arguments.pop("json_body", None)
    legacy_body = raw_arguments.pop("body", None)
    if body is not None and legacy_body is not None:
        raise ValueError("Only one of json_body or body may be provided for public MCP export")
    if body is None:
        body = legacy_body
    if body is not None and not isinstance(body, Mapping):
        raise ValueError("json_body/body must be a mapping for public MCP export")

    flat_path_params = {key: raw_arguments.pop(key) for key in list(raw_arguments.keys()) if key in path_keys}
    path_params = _merge_argument_mappings(nested_path_params, flat_path_params, field_name="path_params")

    normalized_method = method.upper()
    if normalized_method in _HTTP_QUERY_CAPABLE_METHODS:
        query_params = _merge_argument_mappings(nested_query_params, raw_arguments, field_name="query_params")
        if body is not None:
            raise ValueError(f"{kind} route {path_template} does not accept json_body/body for method {normalized_method}")
        json_body = None
    else:
        query_params = dict(_normalize_string_mapping(nested_query_params))
        if normalized_method in _HTTP_BODY_CAPABLE_METHODS:
            if body is None and raw_arguments:
                body = dict(raw_arguments)
                raw_arguments = {}
            elif body is not None and raw_arguments:
                raise ValueError(
                    f"Unexpected flat arguments for public {kind} route {path_template}; use json_body/body or query_params"
                )
            json_body = dict(body) if body is not None else None
        else:
            if body is not None:
                raise ValueError(f"{kind} route {path_template} does not accept json_body/body for method {normalized_method}")
            if raw_arguments:
                raise ValueError(
                    f"Unexpected flat arguments for public {kind} route {path_template}: {', '.join(sorted(map(str, raw_arguments)))}"
                )
            json_body = None

    normalized = {
        "path_params": _normalize_string_mapping(path_params),
        "query_params": _normalize_string_mapping(query_params),
        "json_body": json_body,
    }
    if schema is not None:
        _validate_public_mcp_arguments_against_schema(schema, normalized)
    if route_contract is not None:
        _validate_public_mcp_arguments_against_route_contract(route_contract, normalized)
    return normalized


def _validate_public_mcp_arguments_against_schema(
    schema: PublicMcpArgumentSchema,
    normalized: Mapping[str, Any],
) -> None:
    path_params = dict(normalized.get("path_params") or {})
    query_params = dict(normalized.get("query_params") or {})
    body = normalized.get("json_body")
    body_mapping = dict(body) if isinstance(body, Mapping) else {}

    _validate_required_field_presence(path_params, schema.path_fields, location="path")
    _validate_required_field_presence(query_params, schema.query_fields, location="query")
    _validate_required_field_presence(body_mapping, schema.body_fields, location="body")
    _validate_unknown_field_names(
        query_params,
        schema.query_fields,
        allow_additional=schema.allow_additional_query_params,
        location="query",
        route_name=schema.route_name,
    )
    _validate_unknown_field_names(
        body_mapping,
        schema.body_fields,
        allow_additional=schema.allow_additional_body_fields,
        location="body",
        route_name=schema.route_name,
    )


def _validate_required_field_presence(
    values: Mapping[str, Any],
    fields: tuple[PublicMcpArgumentField, ...],
    *,
    location: str,
) -> None:
    missing = [field.name for field in fields if field.required and field.name not in values]
    if missing:
        raise ValueError(f"Missing required {location} field(s) for public MCP export: {', '.join(sorted(missing))}")


def _validate_unknown_field_names(
    values: Mapping[str, Any],
    fields: tuple[PublicMcpArgumentField, ...],
    *,
    allow_additional: bool,
    location: str,
    route_name: str,
) -> None:
    if allow_additional:
        return
    allowed = {field.name for field in fields}
    extras = sorted(set(values) - allowed)
    if extras:
        raise ValueError(f"Unexpected {location} field(s) for public route {route_name}: {', '.join(extras)}")


def _validate_public_mcp_arguments_against_route_contract(
    route_contract: PublicMcpRouteContract,
    normalized: Mapping[str, Any],
) -> None:
    path_params = dict(normalized.get("path_params") or {})
    query_params = dict(normalized.get("query_params") or {})
    body = normalized.get("json_body")
    body_mapping = dict(body) if isinstance(body, Mapping) else {}

    profile = route_contract.transport_profile
    if profile == "body-only":
        if path_params:
            raise ValueError(f"Public route {route_contract.route_name} does not accept path params under transport profile {profile}")
        if query_params:
            raise ValueError(f"Public route {route_contract.route_name} does not accept query params under transport profile {profile}")
    elif profile == "path-and-body":
        if query_params:
            raise ValueError(f"Public route {route_contract.route_name} does not accept query params under transport profile {profile}")
    elif profile == "path-and-query":
        if body_mapping:
            raise ValueError(f"Public route {route_contract.route_name} does not accept body payload under transport profile {profile}")
    elif profile == "path-only":
        if query_params:
            raise ValueError(f"Public route {route_contract.route_name} does not accept query params under transport profile {profile}")
        if body_mapping:
            raise ValueError(f"Public route {route_contract.route_name} does not accept body payload under transport profile {profile}")
    elif profile == "query-only":
        if path_params:
            raise ValueError(f"Public route {route_contract.route_name} does not accept path params under transport profile {profile}")
        if body_mapping:
            raise ValueError(f"Public route {route_contract.route_name} does not accept body payload under transport profile {profile}")
    elif profile == "no-arguments":
        if path_params or query_params or body_mapping:
            raise ValueError(f"Public route {route_contract.route_name} does not accept arguments under transport profile {profile}")
    else:
        raise ValueError(f"Unknown public MCP transport profile: {profile}")


def _coerce_mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping for public MCP export")
    return {str(key): item for key, item in value.items()}


def _merge_argument_mappings(
    primary: Mapping[str, Any],
    secondary: Mapping[str, Any],
    *,
    field_name: str,
) -> Mapping[str, Any]:
    merged = dict(primary)
    for key, value in secondary.items():
        if key in merged:
            raise ValueError(f"Duplicate {field_name} value for key: {key}")
        merged[str(key)] = value
    return merged


def _path_template_keys(path_template: str) -> tuple[str, ...]:
    keys: list[str] = []
    cursor = 0
    while True:
        start = path_template.find("{", cursor)
        if start == -1:
            break
        end = path_template.find("}", start + 1)
        if end == -1:
            raise ValueError(f"Invalid public path template: {path_template}")
        key = path_template[start + 1 : end].strip()
        if not key:
            raise ValueError(f"Invalid public path template: {path_template}")
        keys.append(key)
        cursor = end + 1
    return tuple(keys)


def _resolve_path_template(
    path_template: str,
    path_params: Mapping[str, str],
    *,
    allow_unresolved_template: bool = False,
) -> str:
    required = _path_template_keys(path_template)
    missing = [key for key in required if key not in path_params]
    if missing:
        if allow_unresolved_template:
            return path_template
        raise ValueError(
            f"Missing path parameters for public route template {path_template}: {', '.join(missing)}"
        )
    extra = sorted(set(path_params) - set(required))
    if extra:
        raise ValueError(
            f"Unexpected path parameters for public route template {path_template}: {', '.join(extra)}"
        )
    resolved = path_template
    for key in required:
        resolved = resolved.replace("{" + key + "}", path_params[key])
    return resolved


def _compose_url(base_url: str | None, path: str, query_params: Mapping[str, str]) -> str | None:
    if base_url is None:
        return None
    normalized_base = base_url.rstrip("/")
    if not normalized_base:
        raise ValueError("base_url must not be empty when provided")
    query = ""
    if query_params:
        query = "?" + "&".join(f"{key}={value}" for key, value in query_params.items())
    return f"{normalized_base}{path}{query}"


def build_public_mcp_adapter_scaffold(
    *,
    base_url: str | None = None,
    surface: PublicMcpCompatibilitySurface | None = None,
    resource_uri_prefix: str = "nexa://public",
) -> PublicMcpAdapterScaffold:
    """Return the minimal MCP adapter/export scaffold over the public SDK surface."""

    return PublicMcpAdapterScaffold(
        surface=surface or build_public_mcp_compatibility_surface(),
        base_url=base_url,
        resource_uri_prefix=resource_uri_prefix,
    )


def build_public_mcp_manifest(
    *,
    base_url: str | None = None,
    surface: PublicMcpCompatibilitySurface | None = None,
    resource_uri_prefix: str = "nexa://public",
    server_name: str = "nexa-public",
    server_title: str = "Nexa Public Integration Surface",
) -> PublicMcpManifest:
    """Return the manifest-level export over the public MCP adapter scaffold."""

    return build_public_mcp_adapter_scaffold(
        base_url=base_url,
        surface=surface,
        resource_uri_prefix=resource_uri_prefix,
    ).export_manifest(server_name=server_name, server_title=server_title)


def build_public_mcp_host_bridge_scaffold(
    *,
    base_url: str | None = None,
    surface: PublicMcpCompatibilitySurface | None = None,
    resource_uri_prefix: str = "nexa://public",
) -> PublicMcpHostBridgeScaffold:
    """Return the minimal in-process host bridge over the public MCP adapter scaffold."""

    return PublicMcpHostBridgeScaffold(
        adapter_scaffold=build_public_mcp_adapter_scaffold(
            base_url=base_url,
            surface=surface,
            resource_uri_prefix=resource_uri_prefix,
        ),
    )


_ROUTE_INDEX = {
    name: (method, path)
    for name, method, path in RunHttpRouteSurface._ROUTE_DEFINITIONS
}


_FRAMEWORK_ROUTE_INDEX = {
    definition.route_name: definition
    for definition in FrameworkRouteBindings.route_definitions()
}


_FRAMEWORK_HANDLER_BY_ROUTE_NAME: dict[str, str] = {
    "get_recent_activity": "handle_recent_activity",
    "get_history_summary": "handle_history_summary",
    "list_workspaces": "handle_list_workspaces",
    "get_circuit_library": "handle_circuit_library",
    "list_starter_circuit_templates": "handle_list_starter_circuit_templates",
    "get_starter_circuit_template": "handle_get_starter_circuit_template",
    "apply_starter_circuit_template": "handle_apply_starter_circuit_template",
    "get_public_nex_format": "handle_public_nex_format",
    "get_public_mcp_manifest": "handle_public_mcp_manifest",
    "get_public_mcp_host_bridge": "handle_public_mcp_host_bridge",
    "get_workspace_result_history": "handle_workspace_result_history",
    "get_workspace_feedback": "handle_workspace_feedback",
    "submit_workspace_feedback": "handle_submit_workspace_feedback",
    "get_workspace": "handle_get_workspace",
    "create_workspace": "handle_create_workspace",
    "get_provider_catalog": "handle_list_provider_catalog",
    "list_workspace_provider_bindings": "handle_list_workspace_provider_bindings",
    "put_workspace_provider_binding": "handle_put_workspace_provider_binding",
    "list_workspace_provider_health": "handle_list_workspace_provider_health",
    "get_workspace_provider_health": "handle_get_workspace_provider_health",
    "probe_workspace_provider": "handle_probe_workspace_provider",
    "list_provider_probe_history": "handle_list_provider_probe_history",
    "get_onboarding": "handle_get_onboarding",
    "create_workspace_shell_share": "handle_create_workspace_shell_share",
    "get_public_share": "handle_get_public_share",
    "get_public_share_history": "handle_get_public_share_history",
    "get_public_share_artifact": "handle_get_public_share_artifact",
    "extend_public_share": "handle_extend_public_share",
    "revoke_public_share": "handle_revoke_public_share",
    "archive_public_share": "handle_archive_public_share",
    "delete_public_share": "handle_delete_public_share",
    "list_issuer_public_shares": "handle_list_issuer_public_shares",
    "get_issuer_public_share_summary": "handle_get_issuer_public_share_summary",
    "list_issuer_public_share_action_reports": "handle_list_issuer_public_share_action_reports",
    "get_issuer_public_share_action_report_summary": "handle_get_issuer_public_share_action_report_summary",
    "revoke_issuer_public_shares": "handle_revoke_issuer_public_shares",
    "extend_issuer_public_shares": "handle_extend_issuer_public_shares",
    "archive_issuer_public_shares": "handle_archive_issuer_public_shares",
    "delete_issuer_public_shares": "handle_delete_issuer_public_shares",
    "put_onboarding": "handle_put_onboarding",
    "list_workspace_runs": "handle_list_workspace_runs",
    "get_workspace_shell": "handle_workspace_shell",
    "put_workspace_shell_draft": "handle_put_workspace_shell_draft",
    "commit_workspace_shell": "handle_commit_workspace_shell",
    "checkout_workspace_shell": "handle_checkout_workspace_shell",
    "launch_workspace_shell": "handle_launch_workspace_shell",
    "launch_run": "handle_launch",
    "get_run_status": "handle_run_status",
    "get_run_result": "handle_run_result",
    "get_run_actions": "handle_run_actions",
    "retry_run": "handle_retry_run",
    "force_reset_run": "handle_force_reset_run",
    "mark_run_reviewed": "handle_mark_run_reviewed",
    "list_run_artifacts": "handle_run_artifacts",
    "get_artifact_detail": "handle_artifact_detail",
    "get_run_trace": "handle_run_trace",
}


def _framework_route_definition(route_name: str) -> FrameworkRouteDefinition:
    try:
        return _FRAMEWORK_ROUTE_INDEX[route_name]
    except KeyError as exc:
        raise ValueError(f"Unknown framework route definition for public route_name: {route_name}") from exc


def _framework_handler_name(route_name: str) -> str:
    try:
        return _FRAMEWORK_HANDLER_BY_ROUTE_NAME[route_name]
    except KeyError as exc:
        raise ValueError(f"Unknown framework handler mapping for public route_name: {route_name}") from exc


def _schema_field(
    name: str,
    location: str,
    value_kind: str,
    *,
    required: bool = False,
    description: str = "",
    enum_values: tuple[str, ...] = (),
) -> PublicMcpArgumentField:
    return PublicMcpArgumentField(
        name=name,
        location=location,
        value_kind=value_kind,
        required=required,
        description=description,
        enum_values=enum_values,
    )


_ARGUMENT_SCHEMA_BY_ROUTE_NAME: dict[str, dict[str, object]] = {
    "launch_run": {
        "body_fields": (
            _schema_field("workspace_id", "body", "string", required=True, description="Workspace to launch against."),
            _schema_field("execution_target", "body", "object", required=True, description="Target artifact identity and role."),
            _schema_field("input_payload", "body", "any", description="Optional launch input payload."),
            _schema_field("launch_options", "body", "object", description="Optional launch mode and priority options."),
            _schema_field("client_context", "body", "object", description="Optional client/source correlation metadata."),
        ),
    },
    "get_workspace_shell": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace shell owner."),
        ),
    },
    "put_workspace_shell_draft": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose shell draft is being updated."),
        ),
        "body_fields": (
            _schema_field("request_text", "body", "string", description="Optional designer request text to persist in the server-backed shell draft."),
            _schema_field("updated_at", "body", "string", description="Optional client-side updated timestamp hint."),
            _schema_field("validation_action", "body", "string", description="Optional validation action marker for continuity state."),
            _schema_field("validation_status", "body", "string", description="Optional validation status marker for continuity state."),
            _schema_field("validation_message", "body", "string", description="Optional validation message marker for continuity state."),
        ),
    },
    "launch_workspace_shell": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace shell owner."),
        ),
        "body_fields": (
            _schema_field("input_payload", "body", "object", description="Optional shell launch input payload."),
            _schema_field("launch_options", "body", "object", description="Optional shell launch options."),
            _schema_field("client_context", "body", "object", description="Optional client/source metadata."),
            _schema_field("app_language", "body", "string", description="Optional compatibility app language hint."),
            _schema_field("execution_target", "body", "object", description="Optional compatibility execution target hint."),
        ),
    },
    "commit_workspace_shell": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose shell is being committed."),
        ),
        "body_fields": (
            _schema_field("commit_id", "body", "string", required=True, description="New commit snapshot identifier."),
            _schema_field("parent_commit_id", "body", "string", description="Optional parent commit identifier."),
        ),
    },
    "checkout_workspace_shell": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose shell is being checked out."),
        ),
        "body_fields": (
            _schema_field("working_save_id", "body", "string", description="Optional reopened working_save identifier."),
            _schema_field("share_id", "body", "string", description="Optional public share identifier to consume as the checkout source."),
        ),
    },
    "retry_run": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run to retry."),),
        "query_fields": (_schema_field("reason", "query", "string", description="Optional retry reason hint."),),
        "allow_additional_query_params": True,
    },
    "force_reset_run": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run to force-reset."),),
        "query_fields": (_schema_field("reason", "query", "string", description="Optional force-reset reason hint."),),
        "allow_additional_query_params": True,
    },
    "mark_run_reviewed": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run to mark reviewed."),),
        "query_fields": (_schema_field("reason", "query", "string", description="Optional review-note hint."),),
        "allow_additional_query_params": True,
    },
    "get_run_status": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run whose status should be read."),),
        "query_fields": (
            _schema_field("include", "query", "string", description="Optional response expansion hint."),
            _schema_field("lang", "query", "string", description="Optional language hint."),
        ),
    },
    "get_run_result": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run whose result should be read."),),
        "allow_additional_query_params": True,
    },
    "list_workspace_runs": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace whose runs should be listed."),),
        "query_fields": (
            _schema_field("limit", "query", "integer", description="Optional page size hint."),
            _schema_field("cursor", "query", "string", description="Optional pagination cursor."),
            _schema_field("status_family", "query", "string", description="Optional run-status family filter."),
            _schema_field("requested_by_user_id", "query", "string", description="Optional requester filter."),
        ),
    },
    "get_run_trace": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run whose trace should be read."),),
        "allow_additional_query_params": True,
    },
    "list_run_artifacts": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run whose artifacts should be listed."),),
        "allow_additional_query_params": True,
    },
    "get_artifact_detail": {
        "path_fields": (_schema_field("artifact_id", "path", "string", required=True, description="Artifact to read."),),
        "allow_additional_query_params": True,
    },
    "get_run_actions": {
        "path_fields": (_schema_field("run_id", "path", "string", required=True, description="Run whose actions should be listed."),),
        "allow_additional_query_params": True,
    },
    "get_recent_activity": {
        "query_fields": (
            _schema_field("workspace_id", "query", "string", description="Optional workspace activity filter."),
            _schema_field("limit", "query", "integer", description="Optional activity page size hint."),
            _schema_field("cursor", "query", "string", description="Optional activity pagination cursor."),
        ),
    },
    "get_workspace": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace to read."),),
    },
    "create_workspace": {
        "body_fields": (
            _schema_field("title", "body", "string", required=True, description="Workspace title."),
            _schema_field("description", "body", "string", description="Optional workspace description."),
        ),
    },
    "get_provider_catalog": {
        "allow_additional_query_params": False,
    },
    "list_workspace_provider_bindings": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace whose provider bindings should be listed."),),
    },
    "put_workspace_provider_binding": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose provider binding should be updated."),
            _schema_field("provider_key", "path", "string", required=True, description="Provider binding key to update."),
        ),
        "body_fields": (
            _schema_field("display_name", "body", "string", description="Optional provider display name."),
            _schema_field("enabled", "body", "boolean", description="Whether the provider binding should be enabled."),
            _schema_field("credential_source", "body", "string", description="Credential-source selector for the binding."),
            _schema_field("secret_value", "body", "string", description="Optional raw secret value for direct credential submission."),
            _schema_field("secret_ref_hint", "body", "string", description="Optional managed-secret reference hint."),
            _schema_field("default_model_ref", "body", "string", description="Optional default model reference."),
            _schema_field("allowed_model_refs", "body", "array", description="Optional allowed model reference list."),
            _schema_field("notes", "body", "string", description="Optional operator notes for the provider binding."),
        ),
    },
    "list_workspace_provider_health": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace whose provider health should be listed."),),
    },
    "get_workspace_provider_health": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose provider health detail should be read."),
            _schema_field("provider_key", "path", "string", required=True, description="Provider key whose health detail should be read."),
        ),
    },
    "probe_workspace_provider": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose provider binding should be probed."),
            _schema_field("provider_key", "path", "string", required=True, description="Provider key to probe."),
        ),
        "body_fields": (
            _schema_field("model_ref", "body", "string", description="Optional model reference override for the probe."),
            _schema_field("probe_message", "body", "string", description="Optional probe message payload."),
            _schema_field("timeout_ms", "body", "integer", description="Optional provider probe timeout in milliseconds."),
        ),
    },
    "list_provider_probe_history": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose provider probe history should be listed."),
            _schema_field("provider_key", "path", "string", required=True, description="Provider key whose probe history should be listed."),
        ),
        "query_fields": (
            _schema_field("limit", "query", "integer", description="Optional page size hint."),
            _schema_field("cursor", "query", "string", description="Optional pagination cursor."),
            _schema_field("probe_status", "query", "string", description="Optional probe-status filter."),
            _schema_field("connectivity_state", "query", "string", description="Optional connectivity-state filter."),
        ),
    },
    "get_onboarding": {
        "allow_additional_query_params": False,
    },
    "put_onboarding": {
        "body_fields": (
            _schema_field("workspace_id", "body", "string", description="Optional workspace associated with the onboarding continuity update."),
            _schema_field("first_success_achieved", "body", "boolean", description="Whether the caller has reached first success."),
            _schema_field("advanced_surfaces_unlocked", "body", "boolean", description="Whether advanced surfaces should be unlocked."),
            _schema_field("dismissed_guidance_state", "body", "object", description="Optional dismissed-guidance state mapping."),
            _schema_field("current_step", "body", "string", description="Optional onboarding step marker."),
        ),
    },
    "create_workspace_shell_share": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace whose shell should be shared publicly."),),
        "body_fields": (
            _schema_field("share_id", "body", "string", description="Optional explicit public share identifier."),
            _schema_field("title", "body", "string", description="Optional public share title."),
            _schema_field("summary", "body", "string", description="Optional public share summary."),
            _schema_field("expires_at", "body", "string", description="Optional expiration timestamp for the share."),
        ),
    },
    "get_public_share": {
        "path_fields": (_schema_field("share_id", "path", "string", required=True, description="Public share to read."),),
    },
    "get_public_share_history": {
        "path_fields": (_schema_field("share_id", "path", "string", required=True, description="Public share whose history should be read."),),
    },
    "get_public_share_artifact": {
        "path_fields": (_schema_field("share_id", "path", "string", required=True, description="Public share whose artifact should be read."),),
    },
    "extend_public_share": {
        "path_fields": (_schema_field("share_id", "path", "string", required=True, description="Public share whose expiration should be extended."),),
        "body_fields": (
            _schema_field("expires_at", "body", "string", required=True, description="New expiration timestamp."),
        ),
    },
    "revoke_public_share": {
        "path_fields": (_schema_field("share_id", "path", "string", required=True, description="Public share to revoke."),),
    },
    "archive_public_share": {
        "path_fields": (_schema_field("share_id", "path", "string", required=True, description="Public share to archive or unarchive."),),
        "body_fields": (
            _schema_field("archived", "body", "boolean", description="Whether the share should be archived."),
        ),
    },
    "delete_public_share": {
        "path_fields": (_schema_field("share_id", "path", "string", required=True, description="Public share to delete."),),
    },
    "list_issuer_public_shares": {
        "query_fields": (
            _schema_field("lifecycle_state", "query", "string", description="Optional effective lifecycle filter."),
            _schema_field("stored_lifecycle_state", "query", "string", description="Optional stored lifecycle filter."),
            _schema_field("storage_role", "query", "string", description="Optional storage role filter."),
            _schema_field("operation", "query", "string", description="Optional required operation capability filter."),
            _schema_field("archived", "query", "boolean", description="Optional archived-state filter."),
            _schema_field("limit", "query", "integer", description="Optional page size hint."),
            _schema_field("offset", "query", "integer", description="Optional pagination offset."),
        ),
    },
    "get_issuer_public_share_summary": {
        "query_fields": (
            _schema_field("lifecycle_state", "query", "string", description="Optional effective lifecycle filter."),
            _schema_field("stored_lifecycle_state", "query", "string", description="Optional stored lifecycle filter."),
            _schema_field("storage_role", "query", "string", description="Optional storage role filter."),
            _schema_field("operation", "query", "string", description="Optional required operation capability filter."),
            _schema_field("archived", "query", "boolean", description="Optional archived-state filter."),
        ),
    },
    "list_issuer_public_share_action_reports": {
        "query_fields": (
            _schema_field("action", "query", "string", description="Optional action filter."),
            _schema_field("limit", "query", "integer", description="Optional page size hint."),
            _schema_field("offset", "query", "integer", description="Optional pagination offset."),
        ),
    },
    "get_issuer_public_share_action_report_summary": {
        "query_fields": (
            _schema_field("action", "query", "string", description="Optional action filter."),
        ),
    },
    "revoke_issuer_public_shares": {
        "body_fields": (
            _schema_field("share_ids", "body", "array[string]", required=True, description="Issuer-owned public shares to revoke."),
        ),
    },
    "extend_issuer_public_shares": {
        "body_fields": (
            _schema_field("share_ids", "body", "array[string]", required=True, description="Issuer-owned public shares to extend."),
            _schema_field("expires_at", "body", "string", required=True, description="New expiration timestamp."),
        ),
    },
    "archive_issuer_public_shares": {
        "body_fields": (
            _schema_field("share_ids", "body", "array[string]", required=True, description="Issuer-owned public shares to archive or unarchive."),
            _schema_field("archived", "body", "boolean", description="Whether the requested shares should be archived."),
        ),
    },
    "delete_issuer_public_shares": {
        "body_fields": (
            _schema_field("share_ids", "body", "array[string]", required=True, description="Issuer-owned public shares to delete."),
        ),
    },
    "get_history_summary": {
        "query_fields": (
            _schema_field("workspace_id", "query", "string", description="Optional workspace scope for the history summary."),
        ),
    },
    "get_circuit_library": {
        "query_fields": (
            _schema_field("app_language", "query", "string", description="Optional language hint for localized circuit-library summaries."),
        ),
    },
    "list_starter_circuit_templates": {
        "query_fields": (
            _schema_field("app_language", "query", "string", description="Optional language hint for localized starter-template catalog summaries."),
        ),
    },
    "get_starter_circuit_template": {
        "path_fields": (_schema_field("template_id", "path", "string", required=True, description="Starter template lookup value to read. Accepts a legacy template_id or canonical template_ref."),),
        "query_fields": (
            _schema_field("app_language", "query", "string", description="Optional language hint for localized starter-template detail."),
        ),
    },
    "apply_starter_circuit_template": {
        "path_fields": (
            _schema_field("workspace_id", "path", "string", required=True, description="Workspace whose shell draft should receive the starter template."),
            _schema_field("template_id", "path", "string", required=True, description="Starter template lookup value to apply. Accepts a legacy template_id or canonical template_ref."),
        ),
        "query_fields": (
            _schema_field("app_language", "query", "string", description="Optional language hint for localized shell projection after template apply."),
        ),
    },
    "get_public_nex_format": {
    },
    "get_public_mcp_manifest": {
        "query_fields": (
            _schema_field("base_url", "query", "string", description="Optional public base URL to embed in manifest exports."),
            _schema_field("resource_uri_prefix", "query", "string", description="Optional MCP resource URI prefix."),
            _schema_field("server_name", "query", "string", description="Optional server name override for manifest export."),
            _schema_field("server_title", "query", "string", description="Optional server title override for manifest export."),
        ),
    },
    "get_public_mcp_host_bridge": {
        "query_fields": (
            _schema_field("base_url", "query", "string", description="Optional public base URL to embed in host-bridge exports."),
            _schema_field("resource_uri_prefix", "query", "string", description="Optional MCP resource URI prefix."),
        ),
    },
    "get_workspace_result_history": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace whose result history should be read."),),
        "query_fields": (
            _schema_field("run_id", "query", "string", description="Optional run to preselect in the result history view."),
            _schema_field("app_language", "query", "string", description="Optional language hint for localized result-history summaries."),
        ),
    },
    "get_workspace_feedback": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace whose feedback channel should be read."),),
        "query_fields": (
            _schema_field("category", "query", "string", description="Optional prefilled feedback category."),
            _schema_field("surface", "query", "string", description="Optional prefilled surface identifier."),
            _schema_field("run_id", "query", "string", description="Optional run identifier to prefill in the feedback channel."),
            _schema_field("feedback_id", "query", "string", description="Optional feedback identifier whose confirmation state should be highlighted."),
            _schema_field("app_language", "query", "string", description="Optional language hint for localized feedback copy."),
        ),
    },
    "submit_workspace_feedback": {
        "path_fields": (_schema_field("workspace_id", "path", "string", required=True, description="Workspace whose feedback channel should receive a new entry."),),
        "body_fields": (
            _schema_field("category", "body", "string", required=True, description="Feedback category to record."),
            _schema_field("surface", "body", "string", required=True, description="Surface where the feedback was captured."),
            _schema_field("message", "body", "string", required=True, description="Human feedback message to persist."),
            _schema_field("run_id", "body", "string", description="Optional run identifier linked to the feedback submission."),
        ),
    },
    "list_workspaces": {
    },
}


_ROUTE_CONTRACT_BY_ROUTE_NAME: dict[str, dict[str, str]] = {
    "launch_run": {"route_family": "run-launch", "transport_profile": "body-only"},
    "get_workspace_shell": {"route_family": "workspace-shell-read", "transport_profile": "path-and-query"},
    "put_workspace_shell_draft": {"route_family": "workspace-shell-draft-write", "transport_profile": "path-and-body"},
    "apply_starter_circuit_template": {"route_family": "starter-template-apply", "transport_profile": "path-and-query"},
    "launch_workspace_shell": {"route_family": "workspace-shell-launch", "transport_profile": "path-and-body"},
    "commit_workspace_shell": {"route_family": "workspace-shell-commit", "transport_profile": "path-and-body"},
    "checkout_workspace_shell": {"route_family": "workspace-shell-checkout", "transport_profile": "path-and-body"},
    "retry_run": {"route_family": "run-control", "transport_profile": "path-and-query"},
    "force_reset_run": {"route_family": "run-control", "transport_profile": "path-and-query"},
    "mark_run_reviewed": {"route_family": "run-control", "transport_profile": "path-and-query"},
    "get_run_status": {"route_family": "run-read", "transport_profile": "path-and-query"},
    "get_run_result": {"route_family": "run-read", "transport_profile": "path-and-query"},
    "list_workspace_runs": {"route_family": "workspace-run-list", "transport_profile": "path-and-query"},
    "get_run_trace": {"route_family": "run-trace", "transport_profile": "path-and-query"},
    "list_run_artifacts": {"route_family": "run-artifacts", "transport_profile": "path-and-query"},
    "get_artifact_detail": {"route_family": "artifact-read", "transport_profile": "path-and-query"},
    "get_run_actions": {"route_family": "run-actions", "transport_profile": "path-and-query"},
    "get_recent_activity": {"route_family": "activity-read", "transport_profile": "query-only"},
    "get_workspace": {"route_family": "workspace-read", "transport_profile": "path-only"},
    "create_workspace": {"route_family": "workspace-create", "transport_profile": "body-only"},
    "get_provider_catalog": {"route_family": "provider-catalog-read", "transport_profile": "no-arguments"},
    "list_workspace_provider_bindings": {"route_family": "workspace-provider-binding-list", "transport_profile": "path-only"},
    "put_workspace_provider_binding": {"route_family": "workspace-provider-binding-write", "transport_profile": "path-and-body"},
    "list_workspace_provider_health": {"route_family": "workspace-provider-health-list", "transport_profile": "path-only"},
    "get_workspace_provider_health": {"route_family": "workspace-provider-health-detail", "transport_profile": "path-only"},
    "probe_workspace_provider": {"route_family": "workspace-provider-probe", "transport_profile": "path-and-body"},
    "list_provider_probe_history": {"route_family": "workspace-provider-probe-history", "transport_profile": "path-and-query"},
    "get_onboarding": {"route_family": "onboarding-read", "transport_profile": "no-arguments"},
    "put_onboarding": {"route_family": "onboarding-write", "transport_profile": "body-only"},
    "create_workspace_shell_share": {"route_family": "public-share-create", "transport_profile": "path-and-body"},
    "get_public_share": {"route_family": "public-share-read", "transport_profile": "path-only"},
    "get_public_share_history": {"route_family": "public-share-history", "transport_profile": "path-only"},
    "get_public_share_artifact": {"route_family": "public-share-artifact", "transport_profile": "path-only"},
    "extend_public_share": {"route_family": "public-share-management", "transport_profile": "path-and-body"},
    "revoke_public_share": {"route_family": "public-share-management", "transport_profile": "path-only"},
    "archive_public_share": {"route_family": "public-share-management", "transport_profile": "path-and-body"},
    "delete_public_share": {"route_family": "public-share-management", "transport_profile": "path-only"},
    "list_issuer_public_shares": {"route_family": "issuer-public-share-list", "transport_profile": "query-only"},
    "get_issuer_public_share_summary": {"route_family": "issuer-public-share-summary", "transport_profile": "query-only"},
    "list_issuer_public_share_action_reports": {"route_family": "issuer-public-share-action-reports", "transport_profile": "query-only"},
    "get_issuer_public_share_action_report_summary": {"route_family": "issuer-public-share-action-report-summary", "transport_profile": "query-only"},
    "revoke_issuer_public_shares": {"route_family": "issuer-public-share-management", "transport_profile": "body-only"},
    "extend_issuer_public_shares": {"route_family": "issuer-public-share-management", "transport_profile": "body-only"},
    "archive_issuer_public_shares": {"route_family": "issuer-public-share-management", "transport_profile": "body-only"},
    "delete_issuer_public_shares": {"route_family": "issuer-public-share-management", "transport_profile": "body-only"},
    "get_history_summary": {"route_family": "history-summary-read", "transport_profile": "query-only"},
    "get_circuit_library": {"route_family": "circuit-library-read", "transport_profile": "query-only"},
    "list_starter_circuit_templates": {"route_family": "starter-template-catalog-read", "transport_profile": "query-only"},
    "get_starter_circuit_template": {"route_family": "starter-template-detail-read", "transport_profile": "path-and-query"},
    "get_public_nex_format": {"route_family": "public-nex-format-read", "transport_profile": "no-arguments"},
    "get_public_mcp_manifest": {"route_family": "public-mcp-manifest-read", "transport_profile": "query-only"},
    "get_public_mcp_host_bridge": {"route_family": "public-mcp-host-bridge-read", "transport_profile": "query-only"},
    "get_workspace_result_history": {"route_family": "workspace-result-history-read", "transport_profile": "path-and-query"},
    "get_workspace_feedback": {"route_family": "workspace-feedback-read", "transport_profile": "path-and-query"},
    "submit_workspace_feedback": {"route_family": "workspace-feedback-write", "transport_profile": "path-and-body"},
    "list_workspaces": {"route_family": "workspace-list", "transport_profile": "no-arguments"},
}


_RECOVERY_POLICY_BY_ROUTE_FAMILY: dict[str, dict[str, object]] = {
    "run-launch": {
        "idempotency_class": "launch-non-idempotent",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_launch_outcome_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_launch_outcome_before_retry",
    },
    "workspace-shell-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_read_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_read_request",
    },
    "workspace-shell-draft-write": {
        "idempotency_class": "state-mutation",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_workspace_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_workspace_state_before_retry",
    },
    "workspace-shell-launch": {
        "idempotency_class": "launch-non-idempotent",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_launch_outcome_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_launch_outcome_before_retry",
    },
    "workspace-shell-commit": {
        "idempotency_class": "state-mutation",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_workspace_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_workspace_state_before_retry",
    },
    "workspace-shell-checkout": {
        "idempotency_class": "state-mutation",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_workspace_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_workspace_state_before_retry",
    },
    "run-control": {
        "idempotency_class": "state-mutation",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_run_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_run_state_before_retry",
    },
    "run-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-run-list": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "run-trace": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "run-artifacts": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "artifact-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "run-actions": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "activity-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "history-summary-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "circuit-library-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "starter-template-catalog-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "starter-template-detail-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "starter-template-apply": {
        "idempotency_class": "idempotent-write",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "read_status_resource",
    },
    "public-nex-format-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "public-mcp-manifest-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "public-mcp-host-bridge-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-result-history-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-feedback-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-feedback-write": {
        "idempotency_class": "state-mutation",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_workspace_feedback_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_workspace_feedback_state_before_retry",
    },
    "workspace-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-create": {
        "idempotency_class": "create-non-idempotent",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_workspace_creation_outcome_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_workspace_creation_outcome_before_retry",
    },
    "provider-catalog-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-provider-binding-list": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-provider-binding-write": {
        "idempotency_class": "state-mutation",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_provider_binding_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_provider_binding_state_before_retry",
    },
    "workspace-provider-health-list": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-provider-health-detail": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "workspace-provider-probe": {
        "idempotency_class": "mutation-non-idempotent",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_provider_probe_outcome_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_provider_probe_outcome_before_retry",
    },
    "workspace-provider-probe-history": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "onboarding-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "onboarding-write": {
        "idempotency_class": "state-mutation",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_onboarding_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_onboarding_state_before_retry",
    },
    "public-share-create": {
        "idempotency_class": "create-non-idempotent",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_share_creation_outcome_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_share_creation_outcome_before_retry",
    },
    "public-share-read": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "public-share-history": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "public-share-artifact": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "public-share-management": {
        "idempotency_class": "mutation-non-idempotent",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_public_share_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_public_share_state_before_retry",
    },
    "issuer-public-share-list": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "issuer-public-share-summary": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "issuer-public-share-action-reports": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "issuer-public-share-action-report-summary": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
    "issuer-public-share-management": {
        "idempotency_class": "mutation-non-idempotent",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": False,
        "timeout_recommended_action": "inspect_issuer_share_state_before_retry",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": False,
        "response_timeout_recommended_action": "inspect_issuer_share_state_before_retry",
    },
    "workspace-list": {
        "idempotency_class": "read-only",
        "timeout_retryable": True,
        "safe_to_retry_same_request_on_timeout": True,
        "timeout_recommended_action": "retry_same_request",
        "response_timeout_retryable": True,
        "safe_to_retry_same_request_on_response_timeout": True,
        "response_timeout_recommended_action": "retry_same_request",
    },
}


_LIFECYCLE_CONTROL_BY_ROUTE_FAMILY: dict[str, dict[str, object]] = {
    "run-launch": {
        "lifecycle_class": "run-entry",
        "status_resource_name": "get_run_status",
        "result_resource_name": "get_run_result",
        "actions_resource_name": "get_run_actions",
        "trace_resource_name": "get_run_trace",
        "artifacts_resource_name": "list_run_artifacts",
        "preferred_control_tool_names": ("retry_run", "force_reset_run", "mark_run_reviewed"),
        "followup_route_names": ("get_run_status", "get_run_result", "get_run_actions", "list_run_artifacts", "get_run_trace"),
        "review_tool_name": "mark_run_reviewed",
    },
    "workspace-shell-read": {
        "lifecycle_class": "workspace-shell-read",
        "status_resource_name": "get_workspace_shell",
        "preferred_control_tool_names": ("put_workspace_shell_draft", "commit_workspace_shell", "checkout_workspace_shell", "launch_workspace_shell", "create_workspace_shell_share"),
        "followup_route_names": ("put_workspace_shell_draft", "commit_workspace_shell", "checkout_workspace_shell", "launch_workspace_shell", "create_workspace_shell_share", "list_workspace_runs"),
    },
    "workspace-shell-draft-write": {
        "lifecycle_class": "workspace-shell-edit",
        "status_resource_name": "get_workspace_shell",
        "preferred_control_tool_names": ("commit_workspace_shell", "launch_workspace_shell", "create_workspace_shell_share"),
        "followup_route_names": ("get_workspace_shell", "commit_workspace_shell", "launch_workspace_shell", "create_workspace_shell_share", "list_workspace_runs"),
    },
    "workspace-shell-launch": {
        "lifecycle_class": "run-entry",
        "source_resource_names": ("get_workspace_shell",),
        "status_resource_name": "get_run_status",
        "result_resource_name": "get_run_result",
        "actions_resource_name": "get_run_actions",
        "trace_resource_name": "get_run_trace",
        "artifacts_resource_name": "list_run_artifacts",
        "preferred_control_tool_names": ("retry_run", "force_reset_run", "mark_run_reviewed"),
        "followup_route_names": ("get_run_status", "get_run_result", "get_run_actions", "list_run_artifacts", "get_run_trace"),
        "review_tool_name": "mark_run_reviewed",
    },
    "run-control": {
        "lifecycle_class": "run-control",
        "status_resource_name": "get_run_status",
        "result_resource_name": "get_run_result",
        "actions_resource_name": "get_run_actions",
        "trace_resource_name": "get_run_trace",
        "artifacts_resource_name": "list_run_artifacts",
        "preferred_control_tool_names": ("retry_run", "force_reset_run", "mark_run_reviewed"),
        "followup_route_names": ("get_run_status", "get_run_actions", "get_run_result"),
        "review_tool_name": "mark_run_reviewed",
    },
    "run-read": {
        "lifecycle_class": "run-read",
        "status_resource_name": "get_run_status",
        "result_resource_name": "get_run_result",
        "actions_resource_name": "get_run_actions",
        "trace_resource_name": "get_run_trace",
        "artifacts_resource_name": "list_run_artifacts",
        "preferred_control_tool_names": ("retry_run", "force_reset_run", "mark_run_reviewed"),
        "followup_route_names": ("get_run_result", "get_run_actions", "list_run_artifacts", "get_run_trace"),
        "review_tool_name": "mark_run_reviewed",
    },
    "run-trace": {
        "lifecycle_class": "run-observability",
        "status_resource_name": "get_run_status",
        "actions_resource_name": "get_run_actions",
        "trace_resource_name": "get_run_trace",
        "artifacts_resource_name": "list_run_artifacts",
        "followup_route_names": ("get_run_status", "get_run_actions"),
    },
    "run-artifacts": {
        "lifecycle_class": "run-observability",
        "status_resource_name": "get_run_status",
        "actions_resource_name": "get_run_actions",
        "trace_resource_name": "get_run_trace",
        "artifacts_resource_name": "list_run_artifacts",
        "followup_route_names": ("get_run_status", "get_run_actions", "get_artifact_detail"),
    },
    "artifact-read": {
        "lifecycle_class": "artifact-read",
        "status_resource_name": "get_run_status",
        "actions_resource_name": "get_run_actions",
        "artifacts_resource_name": "list_run_artifacts",
        "followup_route_names": ("list_run_artifacts", "get_run_status"),
    },
    "run-actions": {
        "lifecycle_class": "run-control-introspection",
        "status_resource_name": "get_run_status",
        "actions_resource_name": "get_run_actions",
        "followup_route_names": ("retry_run", "force_reset_run", "mark_run_reviewed"),
        "review_tool_name": "mark_run_reviewed",
    },
    "workspace-shell-commit": {
        "lifecycle_class": "workspace-shell-lifecycle",
        "status_resource_name": "get_workspace_shell",
        "followup_route_names": ("get_workspace_shell", "checkout_workspace_shell", "create_workspace_shell_share", "launch_workspace_shell", "list_workspace_runs"),
    },
    "workspace-shell-checkout": {
        "lifecycle_class": "workspace-shell-lifecycle",
        "status_resource_name": "get_workspace_shell",
        "source_resource_names": ("get_public_share", "get_public_share_history", "get_public_share_artifact"),
        "followup_route_names": ("get_workspace", "get_workspace_shell", "launch_workspace_shell", "create_workspace_shell_share", "get_public_share", "get_public_share_history", "get_public_share_artifact", "list_workspace_runs"),
    },
    "workspace-run-list": {
        "lifecycle_class": "workspace-observability",
        "followup_route_names": ("get_run_status", "get_run_result"),
    },
    "workspace-read": {
        "lifecycle_class": "workspace-read",
        "followup_route_names": ("list_workspace_runs",),
    },
    "workspace-list": {
        "lifecycle_class": "workspace-list",
        "followup_route_names": ("get_workspace",),
    },
    "workspace-create": {
        "lifecycle_class": "workspace-bootstrap",
        "status_resource_name": "get_workspace",
        "followup_route_names": ("get_workspace", "get_workspace_shell", "get_onboarding", "get_provider_catalog", "list_workspace_provider_bindings", "list_workspace_provider_health"),
    },
    "provider-catalog-read": {
        "lifecycle_class": "provider-bootstrap-read",
        "followup_route_names": ("put_workspace_provider_binding", "list_workspace_provider_bindings"),
    },
    "workspace-provider-binding-list": {
        "lifecycle_class": "provider-bootstrap-read",
        "followup_route_names": ("put_workspace_provider_binding", "list_workspace_provider_health", "get_provider_catalog", "probe_workspace_provider"),
    },
    "workspace-provider-binding-write": {
        "lifecycle_class": "provider-bootstrap-write",
        "status_resource_name": "list_workspace_provider_bindings",
        "followup_route_names": ("list_workspace_provider_bindings", "list_workspace_provider_health", "get_provider_catalog", "probe_workspace_provider"),
    },
    "workspace-provider-health-list": {
        "lifecycle_class": "provider-health-read",
        "followup_route_names": ("get_workspace_provider_health", "probe_workspace_provider", "list_provider_probe_history"),
    },
    "workspace-provider-health-detail": {
        "lifecycle_class": "provider-health-read",
        "followup_route_names": ("probe_workspace_provider", "list_provider_probe_history", "list_workspace_provider_health"),
    },
    "workspace-provider-probe": {
        "lifecycle_class": "provider-probe",
        "status_resource_name": "get_workspace_provider_health",
        "result_resource_name": "list_provider_probe_history",
        "followup_route_names": ("get_workspace_provider_health", "list_provider_probe_history", "list_workspace_provider_health"),
    },
    "workspace-provider-probe-history": {
        "lifecycle_class": "provider-probe-history",
        "status_resource_name": "get_workspace_provider_health",
        "followup_route_names": ("get_workspace_provider_health", "probe_workspace_provider", "list_workspace_provider_bindings"),
    },
    "onboarding-read": {
        "lifecycle_class": "onboarding-read",
        "status_resource_name": "get_onboarding",
        "followup_route_names": ("put_onboarding", "get_workspace", "get_workspace_shell"),
    },
    "onboarding-write": {
        "lifecycle_class": "onboarding-write",
        "status_resource_name": "get_onboarding",
        "followup_route_names": ("get_onboarding", "get_workspace_shell", "launch_workspace_shell"),
    },
    "activity-read": {
        "lifecycle_class": "activity-read",
        "followup_route_names": ("get_workspace", "list_workspace_runs"),
    },
    "history-summary-read": {
        "lifecycle_class": "history-summary-read",
        "followup_route_names": ("get_recent_activity", "list_workspaces", "get_workspace"),
    },
    "circuit-library-read": {
        "lifecycle_class": "circuit-library-read",
        "status_resource_name": "get_history_summary",
        "result_resource_name": "get_circuit_library",
        "followup_route_names": ("get_circuit_library", "list_workspaces", "get_workspace_result_history", "get_workspace_feedback", "get_workspace_shell", "get_onboarding"),
    },
    "starter-template-catalog-read": {
        "lifecycle_class": "starter-template-catalog-read",
        "result_resource_name": "list_starter_circuit_templates",
        "followup_route_names": ("list_starter_circuit_templates", "get_starter_circuit_template", "apply_starter_circuit_template", "get_circuit_library", "create_workspace"),
    },
    "starter-template-detail-read": {
        "lifecycle_class": "starter-template-detail-read",
        "result_resource_name": "get_starter_circuit_template",
        "followup_route_names": ("get_starter_circuit_template", "apply_starter_circuit_template", "list_starter_circuit_templates", "put_workspace_shell_draft", "launch_workspace_shell"),
    },
    "starter-template-apply": {
        "lifecycle_class": "starter-template-apply",
        "status_resource_name": "get_workspace_shell",
        "result_resource_name": "put_workspace_shell_draft",
        "followup_route_names": ("apply_starter_circuit_template", "get_workspace_shell", "put_workspace_shell_draft", "launch_workspace_shell", "list_starter_circuit_templates", "get_starter_circuit_template"),
    },
    "public-nex-format-read": {
        "lifecycle_class": "public-nex-format-read",
        "result_resource_name": "get_public_nex_format",
        "followup_route_names": ("get_public_nex_format", "get_public_share_artifact", "create_workspace_shell_share", "commit_workspace_shell", "checkout_workspace_shell"),
    },
    "public-mcp-manifest-read": {
        "lifecycle_class": "public-mcp-manifest-read",
        "result_resource_name": "get_public_mcp_manifest",
        "followup_route_names": ("get_public_mcp_manifest", "get_public_mcp_host_bridge", "get_public_nex_format", "get_circuit_library"),
    },
    "public-mcp-host-bridge-read": {
        "lifecycle_class": "public-mcp-host-bridge-read",
        "result_resource_name": "get_public_mcp_host_bridge",
        "followup_route_names": ("get_public_mcp_host_bridge", "get_public_mcp_manifest", "launch_run", "get_workspace_shell"),
    },
    "workspace-result-history-read": {
        "lifecycle_class": "workspace-result-history-read",
        "status_resource_name": "get_workspace",
        "result_resource_name": "get_workspace_result_history",
        "followup_route_names": ("get_workspace_result_history", "get_workspace_feedback", "get_workspace_shell", "list_workspace_runs"),
    },
    "workspace-feedback-read": {
        "lifecycle_class": "workspace-feedback-read",
        "status_resource_name": "get_workspace",
        "result_resource_name": "get_workspace_feedback",
        "followup_route_names": ("get_workspace_feedback", "submit_workspace_feedback", "get_workspace_result_history", "get_workspace_shell"),
    },
    "workspace-feedback-write": {
        "lifecycle_class": "workspace-feedback-write",
        "status_resource_name": "get_workspace_feedback",
        "followup_route_names": ("get_workspace_feedback", "get_workspace_result_history", "get_workspace_shell"),
    },
    "public-share-create": {
        "lifecycle_class": "public-share-entry",
        "status_resource_name": "get_public_share",
        "result_resource_name": "get_public_share_artifact",
        "actions_resource_name": "get_public_share_history",
        "followup_route_names": ("get_public_share", "get_public_share_history", "get_public_share_artifact"),
    },
    "public-share-read": {
        "lifecycle_class": "public-share-read",
        "status_resource_name": "get_public_share",
        "result_resource_name": "get_public_share_artifact",
        "actions_resource_name": "get_public_share_history",
        "followup_route_names": ("get_public_share_history", "get_public_share_artifact"),
    },
    "public-share-history": {
        "lifecycle_class": "public-share-history",
        "status_resource_name": "get_public_share",
        "actions_resource_name": "get_public_share_history",
        "followup_route_names": ("get_public_share", "get_public_share_artifact"),
    },
    "public-share-artifact": {
        "lifecycle_class": "public-share-artifact",
        "status_resource_name": "get_public_share",
        "result_resource_name": "get_public_share_artifact",
        "followup_route_names": ("get_public_share", "get_public_share_history"),
    },
    "public-share-management": {
        "lifecycle_class": "public-share-management",
        "status_resource_name": "get_public_share",
        "result_resource_name": "get_public_share_artifact",
        "actions_resource_name": "get_public_share_history",
        "preferred_control_tool_names": ("extend_public_share", "revoke_public_share", "archive_public_share", "delete_public_share"),
        "followup_route_names": ("get_public_share", "get_public_share_history", "get_public_share_artifact"),
    },
    "issuer-public-share-list": {
        "lifecycle_class": "issuer-public-share-read",
        "status_resource_name": "get_issuer_public_share_summary",
        "actions_resource_name": "list_issuer_public_share_action_reports",
        "preferred_control_tool_names": ("extend_issuer_public_shares", "revoke_issuer_public_shares", "archive_issuer_public_shares", "delete_issuer_public_shares"),
        "followup_route_names": ("get_issuer_public_share_summary", "list_issuer_public_share_action_reports", "get_issuer_public_share_action_report_summary"),
    },
    "issuer-public-share-summary": {
        "lifecycle_class": "issuer-public-share-read",
        "status_resource_name": "get_issuer_public_share_summary",
        "actions_resource_name": "list_issuer_public_share_action_reports",
        "preferred_control_tool_names": ("extend_issuer_public_shares", "revoke_issuer_public_shares", "archive_issuer_public_shares", "delete_issuer_public_shares"),
        "followup_route_names": ("list_issuer_public_shares", "list_issuer_public_share_action_reports", "get_issuer_public_share_action_report_summary"),
    },
    "issuer-public-share-action-reports": {
        "lifecycle_class": "issuer-public-share-governance",
        "status_resource_name": "get_issuer_public_share_summary",
        "actions_resource_name": "list_issuer_public_share_action_reports",
        "preferred_control_tool_names": ("extend_issuer_public_shares", "revoke_issuer_public_shares", "archive_issuer_public_shares", "delete_issuer_public_shares"),
        "followup_route_names": ("list_issuer_public_shares", "get_issuer_public_share_summary", "get_issuer_public_share_action_report_summary"),
    },
    "issuer-public-share-action-report-summary": {
        "lifecycle_class": "issuer-public-share-governance",
        "status_resource_name": "get_issuer_public_share_summary",
        "actions_resource_name": "list_issuer_public_share_action_reports",
        "preferred_control_tool_names": ("extend_issuer_public_shares", "revoke_issuer_public_shares", "archive_issuer_public_shares", "delete_issuer_public_shares"),
        "followup_route_names": ("list_issuer_public_shares", "get_issuer_public_share_summary", "list_issuer_public_share_action_reports"),
    },
    "issuer-public-share-management": {
        "lifecycle_class": "issuer-public-share-management",
        "status_resource_name": "get_issuer_public_share_summary",
        "actions_resource_name": "list_issuer_public_share_action_reports",
        "preferred_control_tool_names": ("extend_issuer_public_shares", "revoke_issuer_public_shares", "archive_issuer_public_shares", "delete_issuer_public_shares"),
        "followup_route_names": ("list_issuer_public_shares", "get_issuer_public_share_summary", "list_issuer_public_share_action_reports", "get_issuer_public_share_action_report_summary"),
    },
}


_RESULT_SHAPE_PROFILE_BY_ROUTE_NAME: dict[str, dict[str, object]] = {
    "launch_run": {
        "profile_kind": "accepted-status",
        "state_keys": ("status",),
    },
    "get_workspace_shell": {
        "profile_kind": "workspace-shell-runtime",
        "identity_keys": ("workspace_id",),
        "state_keys": ("storage_role",),
    },
    "put_workspace_shell_draft": {
        "profile_kind": "workspace-shell-runtime",
        "identity_keys": ("workspace_id",),
        "state_keys": ("storage_role",),
    },
    "apply_starter_circuit_template": {
        "profile_kind": "starter-template-apply",
        "identity_keys": ("workspace_id", "template.template_ref", "template.template_id", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "launch_workspace_shell": {
        "profile_kind": "workspace-shell-launch",
        "identity_keys": ("workspace_id", "run_id"),
        "state_keys": ("status",),
    },
    "commit_workspace_shell": {
        "profile_kind": "workspace-commit",
        "identity_keys": ("workspace_id",),
        "state_keys": ("storage_role",),
    },
    "checkout_workspace_shell": {
        "profile_kind": "workspace-checkout",
        "identity_keys": ("workspace_id",),
        "state_keys": ("storage_role",),
    },
    "retry_run": {
        "profile_kind": "run-control-status",
        "state_keys": ("status",),
    },
    "force_reset_run": {
        "profile_kind": "run-control-status",
        "state_keys": ("status",),
    },
    "mark_run_reviewed": {
        "profile_kind": "run-control-status",
        "state_keys": ("status",),
    },
    "get_run_status": {
        "profile_kind": "run-status-detail",
        "identity_keys": ("run_id",),
        "state_keys": ("status",),
    },
    "get_run_result": {
        "profile_kind": "run-result-detail",
        "identity_keys": ("run_id",),
        "state_keys": ("result_state",),
    },
    "list_workspace_runs": {
        "profile_kind": "workspace-run-collection",
        "identity_keys": ("workspace_id",),
        "collection_field_name": "runs",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("run_id",),
    },
    "get_run_trace": {
        "profile_kind": "run-trace-events",
        "collection_field_name": "events",
        "collection_item_identity_keys": ("sequence",),
    },
    "list_run_artifacts": {
        "profile_kind": "run-artifact-collection",
        "collection_field_name": "artifacts",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("artifact_id",),
    },
    "get_artifact_detail": {
        "profile_kind": "artifact-detail",
        "identity_keys": ("artifact_id",),
    },
    "get_run_actions": {
        "profile_kind": "run-action-log",
        "collection_field_name": "actions",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("action_id",),
    },
    "get_recent_activity": {
        "profile_kind": "activity-collection",
        "collection_field_name": "activities",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("activity_id",),
    },
    "get_history_summary": {
        "profile_kind": "history-summary",
        "identity_keys": ("scope",),
        "state_keys": ("latest_activity_at",),
    },
    "get_circuit_library": {
        "profile_kind": "circuit-library",
        "identity_keys": ("source_of_truth",),
        "state_keys": ("status", "app_language"),
        "collection_field_name": "item_sections",
        "collection_item_identity_keys": ("workspace_id",),
    },
    "list_starter_circuit_templates": {
        "profile_kind": "starter-template-catalog",
        "identity_keys": ("identity_policy", "namespace_policy"),
        "state_keys": ("status", "app_language"),
        "collection_field_name": "templates",
        "collection_item_identity_keys": ("template_ref", "template_id"),
    },
    "get_starter_circuit_template": {
        "profile_kind": "starter-template-detail",
        "identity_keys": ("template.template_ref", "template.template_id", "identity_policy", "namespace_policy"),
        "state_keys": ("status", "app_language"),
    },
    "get_public_nex_format": {
        "profile_kind": "public-nex-format",
        "identity_keys": ("format_boundary", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
        "collection_field_name": "artifact_operation_boundaries",
        "collection_item_identity_keys": ("operation",),
    },
    "get_public_mcp_manifest": {
        "profile_kind": "public-mcp-manifest",
        "identity_keys": ("manifest", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
        "collection_field_name": "tools",
        "collection_item_identity_keys": ("route_name",),
    },
    "get_public_mcp_host_bridge": {
        "profile_kind": "public-mcp-host-bridge",
        "identity_keys": ("host_bridge", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
        "collection_field_name": "tool_bindings",
        "collection_item_identity_keys": ("route_name",),
    },
    "get_workspace_result_history": {
        "profile_kind": "workspace-result-history",
        "identity_keys": ("workspace_id",),
        "state_keys": ("status",),
        "collection_field_name": "item_sections",
        "collection_item_identity_keys": ("run_id",),
    },
    "get_workspace_feedback": {
        "profile_kind": "workspace-feedback-read",
        "identity_keys": ("workspace_id",),
        "state_keys": ("status",),
    },
    "submit_workspace_feedback": {
        "profile_kind": "workspace-feedback-write",
        "state_keys": ("status",),
    },
    "get_workspace": {
        "profile_kind": "workspace-detail",
        "identity_keys": ("workspace_id",),
    },
    "create_workspace": {
        "profile_kind": "workspace-create",
        "state_keys": ("status",),
    },
    "get_provider_catalog": {
        "profile_kind": "provider-catalog",
        "collection_field_name": "providers",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("provider_key",),
    },
    "list_workspace_provider_bindings": {
        "profile_kind": "workspace-provider-binding-collection",
        "identity_keys": ("workspace_id",),
        "collection_field_name": "bindings",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("binding_id",),
    },
    "put_workspace_provider_binding": {
        "profile_kind": "workspace-provider-binding-write",
        "state_keys": ("status",),
    },
    "list_workspace_provider_health": {
        "profile_kind": "workspace-provider-health-collection",
        "identity_keys": ("workspace_id",),
        "collection_field_name": "providers",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("binding_id",),
    },
    "get_workspace_provider_health": {
        "profile_kind": "workspace-provider-health-detail",
        "identity_keys": ("workspace_id", "provider_key"),
    },
    "probe_workspace_provider": {
        "profile_kind": "workspace-provider-probe",
        "identity_keys": ("workspace_id", "provider_key"),
        "state_keys": ("probe_status", "connectivity_state"),
    },
    "list_provider_probe_history": {
        "profile_kind": "workspace-provider-probe-history",
        "identity_keys": ("workspace_id", "provider_key"),
        "collection_field_name": "items",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("probe_event_id",),
    },
    "get_onboarding": {
        "profile_kind": "onboarding-read",
        "identity_keys": ("continuity_scope",),
    },
    "put_onboarding": {
        "profile_kind": "onboarding-write",
        "identity_keys": ("continuity_scope",),
        "state_keys": ("status",),
    },
    "create_workspace_shell_share": {
        "profile_kind": "public-share-created",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "get_public_share": {
        "profile_kind": "public-share-detail",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "get_public_share_history": {
        "profile_kind": "public-share-history",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "collection_field_name": "history",
        "count_field_name": "event_count",
        "collection_item_identity_keys": ("event_id",),
    },
    "get_public_share_artifact": {
        "profile_kind": "public-share-artifact",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "extend_public_share": {
        "profile_kind": "public-share-mutation",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "revoke_public_share": {
        "profile_kind": "public-share-mutation",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "archive_public_share": {
        "profile_kind": "public-share-mutation",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "delete_public_share": {
        "profile_kind": "public-share-mutation",
        "identity_keys": ("share_id", "identity", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "list_issuer_public_shares": {
        "profile_kind": "issuer-public-share-collection",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "collection_field_name": "shares",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("share_id", "identity"),
    },
    "get_issuer_public_share_summary": {
        "profile_kind": "issuer-public-share-summary",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "list_issuer_public_share_action_reports": {
        "profile_kind": "issuer-public-share-action-report-collection",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "collection_field_name": "reports",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("report_id",),
    },
    "get_issuer_public_share_action_report_summary": {
        "profile_kind": "issuer-public-share-action-report-summary",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "revoke_issuer_public_shares": {
        "profile_kind": "issuer-public-share-bulk-mutation",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "extend_issuer_public_shares": {
        "profile_kind": "issuer-public-share-bulk-mutation",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "archive_issuer_public_shares": {
        "profile_kind": "issuer-public-share-bulk-mutation",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "delete_issuer_public_shares": {
        "profile_kind": "issuer-public-share-bulk-mutation",
        "identity_keys": ("issuer_user_ref", "identity_policy", "namespace_policy"),
        "state_keys": ("status",),
    },
    "list_workspaces": {
        "profile_kind": "workspace-collection",
        "collection_field_name": "workspaces",
        "count_field_name": "returned_count",
        "collection_item_identity_keys": ("workspace_id",),
    },
}


_RESPONSE_CONTRACT_BY_ROUTE_NAME: dict[str, dict[str, object]] = {
    "launch_run": {
        "response_shape": "accepted",
        "success_status_codes": (202,),
        "body_kind": "object",
        "required_top_level_keys": ("status",),
    },
    "get_workspace_shell": {
        "response_shape": "workspace-shell-runtime",
        "success_status_codes": (200,),
        "body_kind": "object",
        "required_top_level_keys": ("workspace_id", "storage_role", "action_availability", "shell", "routes"),
    },
    "put_workspace_shell_draft": {
        "response_shape": "workspace-shell-runtime",
        "success_status_codes": (200,),
        "body_kind": "object",
        "required_top_level_keys": ("workspace_id", "storage_role", "action_availability", "shell", "routes"),
    },
    "apply_starter_circuit_template": {
        "response_shape": "starter-template-apply",
        "success_status_codes": (200,),
        "body_kind": "object",
        "required_top_level_keys": ("status", "workspace_id", "template", "shell", "routes", "identity_policy", "namespace_policy"),
    },
    "launch_workspace_shell": {
        "response_shape": "workspace-shell-launch",
        "success_status_codes": (202,),
        "body_kind": "object",
        "required_top_level_keys": ("status", "run_id", "workspace_id", "launch_context"),
    },
    "commit_workspace_shell": {
        "response_shape": "snapshot-commit",
        "success_status_codes": (200,),
        "body_kind": "object",
        "required_top_level_keys": ("workspace_id", "storage_role", "transition"),
    },
    "checkout_workspace_shell": {
        "response_shape": "working-save-checkout",
        "success_status_codes": (200,),
        "body_kind": "object",
        "required_top_level_keys": ("workspace_id", "storage_role", "transition"),
    },
    "retry_run": {"response_shape": "run-control", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status",)},
    "force_reset_run": {"response_shape": "run-control", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status",)},
    "mark_run_reviewed": {"response_shape": "run-control", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status",)},
    "get_run_status": {"response_shape": "status", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("run_id", "status")},
    "get_run_result": {"response_shape": "result", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("run_id", "result_state")},
    "list_workspace_runs": {"response_shape": "list", "success_status_codes": (200,), "body_kind": "object"},
    "get_run_trace": {"response_shape": "trace", "success_status_codes": (200,), "body_kind": "object"},
    "list_run_artifacts": {"response_shape": "list", "success_status_codes": (200,), "body_kind": "object"},
    "get_artifact_detail": {"response_shape": "detail", "success_status_codes": (200,), "body_kind": "object"},
    "get_run_actions": {"response_shape": "action-log", "success_status_codes": (200,), "body_kind": "object"},
    "get_recent_activity": {"response_shape": "activity", "success_status_codes": (200,), "body_kind": "object"},
    "get_history_summary": {"response_shape": "history-summary", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("scope",)},
    "get_circuit_library": {"response_shape": "circuit-library", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "source_of_truth", "library", "overview_section", "item_sections", "routes")},
    "list_starter_circuit_templates": {"response_shape": "starter-template-catalog", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "catalog", "templates", "routes", "identity_policy", "namespace_policy")},
    "get_starter_circuit_template": {"response_shape": "starter-template-detail", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "template", "routes", "identity_policy", "namespace_policy")},
    "get_public_nex_format": {"response_shape": "public-nex-format", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "format_boundary", "role_boundaries", "public_sdk_entrypoints", "identity_policy", "namespace_policy", "routes")},
    "get_public_mcp_manifest": {"response_shape": "public-mcp-manifest", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "manifest", "identity_policy", "namespace_policy", "routes")},
    "get_public_mcp_host_bridge": {"response_shape": "public-mcp-host-bridge", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "host_bridge", "identity_policy", "namespace_policy", "routes")},
    "get_workspace_result_history": {"response_shape": "workspace-result-history", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "workspace_id", "result_history")},
    "get_workspace_feedback": {"response_shape": "workspace-feedback-read", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "workspace_id", "feedback_channel")},
    "submit_workspace_feedback": {"response_shape": "workspace-feedback-write", "success_status_codes": (202,), "body_kind": "object", "required_top_level_keys": ("status", "feedback", "links")},
    "get_workspace": {"response_shape": "detail", "success_status_codes": (200,), "body_kind": "object"},
    "create_workspace": {"response_shape": "workspace-created", "success_status_codes": (201,), "body_kind": "object", "required_top_level_keys": ("status", "workspace", "owner_membership_id")},
    "get_provider_catalog": {"response_shape": "provider-catalog", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("returned_count", "providers")},
    "list_workspace_provider_bindings": {"response_shape": "workspace-provider-binding-list", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("workspace_id", "returned_count", "bindings")},
    "put_workspace_provider_binding": {"response_shape": "workspace-provider-binding-write", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "binding", "was_created", "secret_rotated")},
    "list_workspace_provider_health": {"response_shape": "workspace-provider-health-list", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("workspace_id", "returned_count", "providers")},
    "get_workspace_provider_health": {"response_shape": "workspace-provider-health-detail", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("workspace_id", "health")},
    "probe_workspace_provider": {"response_shape": "workspace-provider-probe", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("workspace_id", "provider_key", "probe_status", "connectivity_state", "findings", "links")},
    "list_provider_probe_history": {"response_shape": "workspace-provider-probe-history", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("workspace_id", "provider_key", "returned_count", "total_visible_count", "items", "applied_filters")},
    "get_onboarding": {"response_shape": "onboarding-read", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("continuity_scope", "state", "links")},
    "put_onboarding": {"response_shape": "onboarding-write", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("status", "continuity_scope", "state", "links", "was_created")},
    "create_workspace_shell_share": {"response_shape": "public-share-created", "success_status_codes": (201,), "body_kind": "object", "required_top_level_keys": ("share_id", "status", "identity_policy", "namespace_policy")},
    "get_public_share": {"response_shape": "public-share-detail", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("share_id", "status", "identity_policy", "namespace_policy")},
    "get_public_share_history": {"response_shape": "public-share-history", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("share_id", "history", "identity_policy", "namespace_policy")},
    "get_public_share_artifact": {"response_shape": "public-share-artifact", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("share_id", "artifact", "identity_policy", "namespace_policy")},
    "extend_public_share": {"response_shape": "public-share-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("share_id", "status", "identity_policy", "namespace_policy")},
    "revoke_public_share": {"response_shape": "public-share-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("share_id", "status", "identity_policy", "namespace_policy")},
    "archive_public_share": {"response_shape": "public-share-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("share_id", "status", "identity_policy", "namespace_policy")},
    "delete_public_share": {"response_shape": "public-share-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("share_id", "status", "identity_policy", "namespace_policy")},
    "list_issuer_public_shares": {"response_shape": "issuer-public-share-list", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "shares", "status", "identity_policy", "namespace_policy")},
    "get_issuer_public_share_summary": {"response_shape": "issuer-public-share-summary", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "summary", "status", "identity_policy", "namespace_policy")},
    "list_issuer_public_share_action_reports": {"response_shape": "issuer-public-share-action-report-list", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "reports", "status", "identity_policy", "namespace_policy")},
    "get_issuer_public_share_action_report_summary": {"response_shape": "issuer-public-share-action-report-summary", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "summary", "status", "identity_policy", "namespace_policy")},
    "revoke_issuer_public_shares": {"response_shape": "issuer-public-share-bulk-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "status", "action", "identity_policy", "namespace_policy")},
    "extend_issuer_public_shares": {"response_shape": "issuer-public-share-bulk-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "status", "action", "identity_policy", "namespace_policy")},
    "archive_issuer_public_shares": {"response_shape": "issuer-public-share-bulk-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "status", "action", "identity_policy", "namespace_policy")},
    "delete_issuer_public_shares": {"response_shape": "issuer-public-share-bulk-mutation", "success_status_codes": (200,), "body_kind": "object", "required_top_level_keys": ("issuer_user_ref", "status", "action", "identity_policy", "namespace_policy")},
    "list_workspaces": {"response_shape": "list", "success_status_codes": (200,), "body_kind": "object"},
}


def build_public_mcp_result_shape_profiles() -> tuple[PublicMcpResultShapeProfile, ...]:
    """Return exported response result-shape profiles for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    profiles: list[PublicMcpResultShapeProfile] = []
    seen: set[tuple[str, tuple[str, ...], tuple[str, ...], str | None, str | None, tuple[str, ...]]] = set()
    for descriptor in (*build_public_mcp_tools(), *build_public_mcp_resources()):
        profile = adapter._result_shape_profile_for_descriptor(descriptor, kind=("tool" if isinstance(descriptor, PublicMcpToolDescriptor) else "resource"))
        sig = (
            profile.profile_kind,
            profile.identity_keys,
            profile.state_keys,
            profile.collection_field_name,
            profile.count_field_name,
            profile.collection_item_identity_keys,
        )
        if sig not in seen:
            seen.add(sig)
            profiles.append(profile)
    return tuple(profiles)


def build_public_mcp_response_contracts() -> tuple[PublicMcpResponseContract, ...]:
    """Return exported response contracts for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    contracts: list[PublicMcpResponseContract] = []
    for tool in build_public_mcp_tools():
        contracts.append(adapter.export_tool_response_contract(tool.name))
    for resource in build_public_mcp_resources():
        contracts.append(adapter.export_resource_response_contract(resource.name))
    return tuple(contracts)


def build_public_mcp_transport_contracts() -> tuple[PublicMcpTransportContract, ...]:
    """Return exported transport/session contracts for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    contracts: list[PublicMcpTransportContract] = []
    for tool in build_public_mcp_tools():
        contracts.append(adapter.export_tool_transport_contract(tool.name))
    for resource in build_public_mcp_resources():
        contracts.append(adapter.export_resource_transport_contract(resource.name))
    return tuple(contracts)


def build_public_mcp_recovery_policies() -> tuple[PublicMcpRecoveryPolicy, ...]:
    """Return exported recovery policies for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    policies: list[PublicMcpRecoveryPolicy] = []
    for tool in build_public_mcp_tools():
        policies.append(adapter.export_tool_recovery_policy(tool.name))
    for resource in build_public_mcp_resources():
        policies.append(adapter.export_resource_recovery_policy(resource.name))
    return tuple(policies)


def build_public_mcp_lifecycle_control_profiles() -> tuple[PublicMcpLifecycleControlProfile, ...]:
    """Return exported lifecycle control profiles for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    profiles: list[PublicMcpLifecycleControlProfile] = []
    for tool in build_public_mcp_tools():
        profiles.append(adapter.export_tool_lifecycle_control_profile(tool.name))
    for resource in build_public_mcp_resources():
        profiles.append(adapter.export_resource_lifecycle_control_profile(resource.name))
    return tuple(profiles)


_TOOL_SPECS: tuple[dict[str, object], ...] = (
    {
        "name": "launch_run",
        "route_name": "launch_run",
        "description": "Launch a run against an explicit public execution target.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductRunLaunchRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunLaunchAcceptedResponse"),
        "tags": ("runs", "launch", "public-boundary"),
    },
    {
        "name": "put_workspace_shell_draft",
        "route_name": "put_workspace_shell_draft",
        "description": "Persist server-backed workspace shell draft continuity and builder state.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceShellDraftSavedResponse"),
        "tags": ("workspace-shell", "draft", "write", "public-boundary"),
    },
    {
        "name": "apply_starter_circuit_template",
        "route_name": "apply_starter_circuit_template",
        "description": "Apply a public starter template to a workspace shell draft and project the updated shell state.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductStarterTemplateApplyAcceptedResponse"),
        "tags": ("templates", "ecosystem", "apply", "workspace-shell"),
    },
    {
        "name": "launch_workspace_shell",
        "route_name": "launch_workspace_shell",
        "description": "Launch a run from the current workspace shell artifact.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductRunLaunchRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceShellLaunchAcceptedResponse"),
        "tags": ("workspace-shell", "launch", "public-boundary"),
    },
    {
        "name": "commit_workspace_shell",
        "route_name": "commit_workspace_shell",
        "description": "Convert the current workspace shell working_save into a commit_snapshot.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceShellCommitResponse"),
        "tags": ("workspace-shell", "lifecycle", "commit"),
    },
    {
        "name": "create_workspace_shell_share",
        "route_name": "create_workspace_shell_share",
        "description": "Create a public share for the current workspace shell artifact.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceShellShareCreatedResponse"),
        "tags": ("workspace-shell", "sharing", "public-boundary"),
    },
    {
        "name": "checkout_workspace_shell",
        "route_name": "checkout_workspace_shell",
        "description": "Reopen a workspace shell commit_snapshot as a working_save, including checkout from a public share when share_id is provided.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceShellCheckoutResponse"),
        "tags": ("workspace-shell", "lifecycle", "checkout", "sharing", "public-consumption"),
    },
    {
        "name": "create_workspace",
        "route_name": "create_workspace",
        "description": "Create a workspace and return the new workspace continuity surface.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceCreateRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceWriteAcceptedResponse"),
        "tags": ("workspace", "bootstrap", "create"),
    },
    {
        "name": "put_workspace_provider_binding",
        "route_name": "put_workspace_provider_binding",
        "description": "Create or update a workspace provider binding and its secret/source policy.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductProviderBindingWriteRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductProviderBindingWriteAcceptedResponse"),
        "tags": ("workspace", "providers", "bootstrap"),
    },
    {
        "name": "probe_workspace_provider",
        "route_name": "probe_workspace_provider",
        "description": "Probe a workspace provider binding and record a provider connectivity event.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductProviderProbeRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductProviderProbeResponse"),
        "tags": ("workspace", "providers", "probe"),
    },
    {
        "name": "put_onboarding",
        "route_name": "put_onboarding",
        "description": "Persist onboarding continuity and first-success state for the current user.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductOnboardingWriteRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductOnboardingWriteAcceptedResponse"),
        "tags": ("workspace", "onboarding", "continuity"),
    },
    {
        "name": "retry_run",
        "route_name": "retry_run",
        "description": "Retry a previously launched run.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunControlAcceptedResponse"),
        "tags": ("runs", "control", "retry"),
    },
    {
        "name": "force_reset_run",
        "route_name": "force_reset_run",
        "description": "Force-reset a run into a clean execution state.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunControlAcceptedResponse"),
        "tags": ("runs", "control", "reset"),
    },
    {
        "name": "mark_run_reviewed",
        "route_name": "mark_run_reviewed",
        "description": "Mark a run as reviewed without mutating its source artifact role.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunControlAcceptedResponse"),
        "tags": ("runs", "control", "review"),
    },
    {
        "name": "submit_workspace_feedback",
        "route_name": "submit_workspace_feedback",
        "description": "Submit a workspace-scoped product feedback note tied to the current workflow or result-history surface.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceFeedbackWriteRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceFeedbackWriteAcceptedResponse"),
        "tags": ("workspace", "feedback", "write"),
    },
    {
        "name": "extend_public_share",
        "route_name": "extend_public_share",
        "description": "Extend the expiration of a public share you issued.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicShareMutationResponse"),
        "tags": ("sharing", "public-boundary", "lifecycle"),
    },
    {
        "name": "revoke_public_share",
        "route_name": "revoke_public_share",
        "description": "Revoke a public share you issued.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicShareMutationResponse"),
        "tags": ("sharing", "public-boundary", "lifecycle"),
    },
    {
        "name": "archive_public_share",
        "route_name": "archive_public_share",
        "description": "Archive or unarchive a public share you issued.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicShareMutationResponse"),
        "tags": ("sharing", "public-boundary", "lifecycle"),
    },
    {
        "name": "delete_public_share",
        "route_name": "delete_public_share",
        "description": "Delete a public share you issued.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicShareMutationResponse"),
        "tags": ("sharing", "public-boundary", "lifecycle"),
    },
    {
        "name": "revoke_issuer_public_shares",
        "route_name": "revoke_issuer_public_shares",
        "description": "Revoke multiple issuer-owned public shares in one authenticated management action.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareBulkMutationResponse"),
        "tags": ("sharing", "issuer-management", "bulk-action"),
    },
    {
        "name": "extend_issuer_public_shares",
        "route_name": "extend_issuer_public_shares",
        "description": "Extend expiration for multiple issuer-owned public shares in one authenticated management action.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareBulkMutationResponse"),
        "tags": ("sharing", "issuer-management", "bulk-action"),
    },
    {
        "name": "archive_issuer_public_shares",
        "route_name": "archive_issuer_public_shares",
        "description": "Archive or unarchive multiple issuer-owned public shares in one authenticated management action.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareBulkMutationResponse"),
        "tags": ("sharing", "issuer-management", "bulk-action"),
    },
    {
        "name": "delete_issuer_public_shares",
        "route_name": "delete_issuer_public_shares",
        "description": "Delete multiple issuer-owned public shares in one authenticated management action.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareBulkMutationResponse"),
        "tags": ("sharing", "issuer-management", "bulk-action"),
    },
)

_RESOURCE_SPECS: tuple[dict[str, object], ...] = (
    {
        "name": "get_run_status",
        "route_name": "get_run_status",
        "description": "Read the current run status and public source artifact identity.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunStatusResponse"),
        "tags": ("runs", "read", "status"),
    },
    {
        "name": "get_run_result",
        "route_name": "get_run_result",
        "description": "Read the final run result and public source artifact identity.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunResultResponse"),
        "tags": ("runs", "read", "result"),
    },
    {
        "name": "list_workspace_runs",
        "route_name": "list_workspace_runs",
        "description": "List workspace runs with public source artifact identity.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceRunListResponse"),
        "tags": ("workspace", "runs", "list"),
    },
    {
        "name": "get_run_trace",
        "route_name": "get_run_trace",
        "description": "Read the execution trace for a run.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunTraceResponse"),
        "tags": ("runs", "trace", "read"),
    },
    {
        "name": "list_run_artifacts",
        "route_name": "list_run_artifacts",
        "description": "List artifacts produced by a run.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunArtifactsResponse"),
        "tags": ("runs", "artifacts", "list"),
    },
    {
        "name": "get_artifact_detail",
        "route_name": "get_artifact_detail",
        "description": "Read a single artifact together with its public source artifact identity.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductArtifactDetailResponse"),
        "tags": ("artifacts", "read"),
    },
    {
        "name": "get_run_actions",
        "route_name": "get_run_actions",
        "description": "Read action-history entries for a run.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunActionLogResponse"),
        "tags": ("runs", "actions", "history"),
    },
    {
        "name": "get_recent_activity",
        "route_name": "get_recent_activity",
        "description": "Read recent user activity with public run source identity when available.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductRecentActivityResponse"),
        "tags": ("history", "activity", "reentry"),
    },
    {
        "name": "get_history_summary",
        "route_name": "get_history_summary",
        "description": "Read account or workspace history rollup counts for reentry and continuity decisions.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductHistorySummaryResponse"),
        "tags": ("history", "summary", "reentry"),
    },
    {
        "name": "get_circuit_library",
        "route_name": "get_circuit_library",
        "description": "Read the beginner-facing workflow library and continue/result-history reentry surfaces.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductCircuitLibraryResponse"),
        "tags": ("workspace", "library", "reentry"),
    },
    {
        "name": "list_starter_circuit_templates",
        "route_name": "list_starter_circuit_templates",
        "description": "Read the public starter-template catalog as a bounded ecosystem surface.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductStarterTemplateCatalogResponse"),
        "tags": ("templates", "ecosystem", "catalog"),
    },
    {
        "name": "get_starter_circuit_template",
        "route_name": "get_starter_circuit_template",
        "description": "Read one starter-template detail entry from the public ecosystem surface.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductStarterTemplateDetailResponse"),
        "tags": ("templates", "ecosystem", "detail"),
    },
    {
        "name": "get_public_nex_format",
        "route_name": "get_public_nex_format",
        "description": "Read the public .nex format boundary, role-aware operation catalog, and SDK entrypoints.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicNexFormatResponse"),
        "tags": ("artifacts", "public-nex", "standardization"),
    },
    {
        "name": "get_public_mcp_manifest",
        "route_name": "get_public_mcp_manifest",
        "description": "Read the public MCP manifest export surface for packaging and ecosystem discovery.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicMcpManifestResponse"),
        "tags": ("integration", "mcp", "manifest"),
    },
    {
        "name": "get_public_mcp_host_bridge",
        "route_name": "get_public_mcp_host_bridge",
        "description": "Read the public MCP host bridge export surface for framework dispatch and transport binding.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicMcpHostBridgeResponse"),
        "tags": ("integration", "mcp", "host-bridge"),
    },
    {
        "name": "get_workspace_result_history",
        "route_name": "get_workspace_result_history",
        "description": "Read workspace result-history reentry surfaces together with onboarding projection and selected result detail.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceResultHistoryResponse"),
        "tags": ("workspace", "history", "results"),
    },
    {
        "name": "get_workspace_feedback",
        "route_name": "get_workspace_feedback",
        "description": "Read the workspace feedback channel and prefilled product-learning entry surface.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceFeedbackReadResponse"),
        "tags": ("workspace", "feedback", "read"),
    },
    {
        "name": "get_public_share",
        "route_name": "get_public_share",
        "description": "Read the public share descriptor and contract surface for a shared artifact.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicShareDetailResponse"),
        "tags": ("sharing", "public-boundary", "read"),
    },
    {
        "name": "get_public_share_history",
        "route_name": "get_public_share_history",
        "description": "Read the public audit history for a shared artifact.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicShareHistoryResponse"),
        "tags": ("sharing", "public-boundary", "history"),
    },
    {
        "name": "get_public_share_artifact",
        "route_name": "get_public_share_artifact",
        "description": "Read the shared artifact payload and boundary metadata for a public share.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductPublicShareArtifactResponse"),
        "tags": ("sharing", "public-boundary", "artifact"),
    },
    {
        "name": "list_issuer_public_shares",
        "route_name": "list_issuer_public_shares",
        "description": "List issuer-owned public shares together with management and governance summaries.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareListResponse"),
        "tags": ("sharing", "issuer-management", "list"),
    },
    {
        "name": "get_issuer_public_share_summary",
        "route_name": "get_issuer_public_share_summary",
        "description": "Read issuer share inventory and governance summary for authenticated public-share management.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareSummaryResponse"),
        "tags": ("sharing", "issuer-management", "summary"),
    },
    {
        "name": "list_issuer_public_share_action_reports",
        "route_name": "list_issuer_public_share_action_reports",
        "description": "List issuer public-share action reports with governance summary and pagination context.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareActionReportListResponse"),
        "tags": ("sharing", "issuer-management", "governance"),
    },
    {
        "name": "get_issuer_public_share_action_report_summary",
        "route_name": "get_issuer_public_share_action_report_summary",
        "description": "Read issuer public-share action-report summary with governance rollup context.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductIssuerPublicShareActionReportSummaryResponse"),
        "tags": ("sharing", "issuer-management", "governance"),
    },
    {
        "name": "get_workspace_shell",
        "route_name": "get_workspace_shell",
        "description": "Read the current workspace shell runtime projection and action availability.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceShellRuntimeResponse"),
        "tags": ("workspace-shell", "read", "public-boundary"),
    },
    {
        "name": "get_provider_catalog",
        "route_name": "get_provider_catalog",
        "description": "Read the provider catalog and bootstrap guidance for workspace provider setup.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductProviderCatalogResponse"),
        "tags": ("workspace", "providers", "catalog"),
    },
    {
        "name": "list_workspace_provider_bindings",
        "route_name": "list_workspace_provider_bindings",
        "description": "List provider bindings configured for a workspace.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceProviderBindingsResponse"),
        "tags": ("workspace", "providers", "list"),
    },
    {
        "name": "list_workspace_provider_health",
        "route_name": "list_workspace_provider_health",
        "description": "Read the provider health rollup for a workspace.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceProviderHealthResponse"),
        "tags": ("workspace", "providers", "health"),
    },
    {
        "name": "get_workspace_provider_health",
        "route_name": "get_workspace_provider_health",
        "description": "Read health details for a single workspace provider binding.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductProviderHealthDetailResponse"),
        "tags": ("workspace", "providers", "health"),
    },
    {
        "name": "list_provider_probe_history",
        "route_name": "list_provider_probe_history",
        "description": "Read probe history for a single workspace provider binding.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductProviderProbeHistoryResponse"),
        "tags": ("workspace", "providers", "probe-history"),
    },
    {
        "name": "get_onboarding",
        "route_name": "get_onboarding",
        "description": "Read onboarding continuity and first-success state for the current user.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductOnboardingReadResponse"),
        "tags": ("workspace", "onboarding", "continuity"),
    },
    {
        "name": "get_workspace",
        "route_name": "get_workspace",
        "description": "Read workspace metadata and continuity state.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceDetailResponse"),
        "tags": ("workspace", "read"),
    },
    {
        "name": "list_workspaces",
        "route_name": "list_workspaces",
        "description": "List workspaces visible to the current integration caller.",
        "response_type": PublicTypeRef("src.sdk.server", "ProductWorkspaceListResponse"),
        "tags": ("workspace", "list"),
    },
)


def _resolve_route(route_name: str) -> tuple[str, str]:
    try:
        return _ROUTE_INDEX[route_name]
    except KeyError as exc:
        raise ValueError(f"Unknown public route_name for MCP compatibility surface: {route_name}") from exc


def _tool_from_spec(spec: Mapping[str, object]) -> PublicMcpToolDescriptor:
    route_name = str(spec["route_name"])
    method, path = _resolve_route(route_name)
    return PublicMcpToolDescriptor(
        name=str(spec["name"]),
        route_name=route_name,
        method=method,
        path=path,
        description=str(spec["description"]),
        request_type=spec.get("request_type"),  # type: ignore[arg-type]
        response_type=spec.get("response_type"),  # type: ignore[arg-type]
        tags=tuple(str(tag) for tag in spec.get("tags", ())),
    )


def _resource_from_spec(spec: Mapping[str, object]) -> PublicMcpResourceDescriptor:
    route_name = str(spec["route_name"])
    method, path = _resolve_route(route_name)
    return PublicMcpResourceDescriptor(
        name=str(spec["name"]),
        route_name=route_name,
        method=method,
        path=path,
        description=str(spec["description"]),
        response_type=spec.get("response_type"),  # type: ignore[arg-type]
        tags=tuple(str(tag) for tag in spec.get("tags", ())),
    )


def build_public_mcp_tools() -> tuple[PublicMcpToolDescriptor, ...]:
    """Return the curated MCP-style tool mapping for the public Nexa server surface."""

    return tuple(_tool_from_spec(spec) for spec in _TOOL_SPECS)


def build_public_mcp_resources() -> tuple[PublicMcpResourceDescriptor, ...]:
    """Return the curated MCP-style resource mapping for the public Nexa server surface."""

    return tuple(_resource_from_spec(spec) for spec in _RESOURCE_SPECS)


def build_public_mcp_argument_schemas() -> tuple[PublicMcpArgumentSchema, ...]:
    """Return exported argument schemas for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    schemas: list[PublicMcpArgumentSchema] = []
    for tool in build_public_mcp_tools():
        schema = adapter.export_tool_schema(tool.name)
        if schema is not None:
            schemas.append(schema)
    for resource in build_public_mcp_resources():
        schema = adapter.export_resource_schema(resource.name)
        if schema is not None:
            schemas.append(schema)
    return tuple(schemas)


def build_public_mcp_route_contracts() -> tuple[PublicMcpRouteContract, ...]:
    """Return exported route-family normalization contracts for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    contracts: list[PublicMcpRouteContract] = []
    for tool in build_public_mcp_tools():
        contracts.append(adapter.export_tool_contract(tool.name))
    for resource in build_public_mcp_resources():
        contracts.append(adapter.export_resource_contract(resource.name))
    return tuple(contracts)



def build_public_mcp_contract_markers() -> tuple[str, ...]:
    """Return exported contract capability markers for the curated public MCP surface."""

    return (
        "argument-schema",
        "route-contract",
        "response-contract",
        "result-shape-profile",
        "transport-contract",
        "recovery-policy",
        "lifecycle-control-profile",
    )


def build_public_mcp_runtime_markers() -> tuple[str, ...]:
    """Return exported runtime capability markers for the curated public MCP surface."""

    return (
        "request-normalization",
        "transport-assessment",
        "preflight-assessment",
        "dispatch-planning",
        "dispatch-execution",
        "execution-report",
        "recovery-hints",
        "lifecycle-state-hint",
        "orchestration-summary",
    )

def build_public_mcp_compatibility_policy() -> PublicMcpCompatibilityPolicy:
    """Return the capability-based compatibility policy for the curated public MCP surface."""

    return build_public_mcp_adapter_scaffold().compatibility_policy()


def build_public_mcp_compatibility_surface() -> PublicMcpCompatibilitySurface:
    """Return the complete MCP compatibility shape for the public SDK boundary."""

    return PublicMcpCompatibilitySurface(
        contract_markers=build_public_mcp_contract_markers(),
        runtime_markers=build_public_mcp_runtime_markers(),
        tools=build_public_mcp_tools(),
        resources=build_public_mcp_resources(),
    )


__all__ = [
    "PublicTypeRef",
    "PublicMcpToolDescriptor",
    "PublicMcpResourceDescriptor",
    "PublicMcpArgumentField",
    "PublicMcpArgumentSchema",
    "PublicMcpRouteContract",
    "PublicMcpNormalizedArguments",
    "PublicMcpSessionContract",
    "PublicMcpTransportContract",
    "PublicMcpTransportContext",
    "PublicMcpTransportAssessment",
    "PublicMcpPreflightAssessment",
    "PublicMcpLifecycleControlProfile",
    "PublicMcpLifecycleStateHint",
    "PublicMcpOrchestrationSummary",
    "PublicMcpResultShapeProfile",
    "PublicMcpResponseContract",
    "PublicMcpRecoveryPolicy",
    "PublicMcpNormalizedResponse",
    "PublicMcpRecoveryHint",
    "PublicMcpExecutionError",
    "PublicMcpExecutionReport",
    "PublicMcpCompatibilitySurface",
    "PublicMcpCompatibilityPolicy",
    "PublicMcpManifestTool",
    "PublicMcpManifestResource",
    "PublicMcpManifest",
    "PublicMcpInvocation",
    "PublicMcpToolExport",
    "PublicMcpResourceExport",
    "PublicMcpAdapterExport",
    "PublicMcpAdapterScaffold",
    "PublicMcpHostRouteBinding",
    "PublicMcpFrameworkDispatch",
    "PublicMcpHttpDispatch",
    "PublicMcpFrameworkEnvelope",
    "PublicMcpHttpEnvelope",
    "PublicMcpHostBridgeExport",
    "PublicMcpHostBridgeScaffold",
    "build_public_mcp_tools",
    "build_public_mcp_resources",
    "build_public_mcp_argument_schemas",
    "build_public_mcp_route_contracts",
    "build_public_mcp_transport_contracts",
    "build_public_mcp_result_shape_profiles",
    "build_public_mcp_response_contracts",
    "build_public_mcp_recovery_policies",
    "build_public_mcp_lifecycle_control_profiles",
    "build_public_mcp_contract_markers",
    "build_public_mcp_runtime_markers",
    "build_public_mcp_compatibility_policy",
    "build_public_mcp_compatibility_surface",
    "build_public_mcp_adapter_scaffold",
    "build_public_mcp_manifest",
    "build_public_mcp_host_bridge_scaffold",
]

def _append_unique(values: list[str], value: str | None) -> None:
    if value and value not in values:
        values.append(value)


def _assess_public_transport_context(context: PublicMcpTransportContext) -> PublicMcpTransportAssessment:
    contract = context.transport_contract
    warnings: list[str] = []
    actions: list[str] = []

    if contract.request_id_mode == "recommended" and not context.request_id:
        warnings.append("missing_request_id")
        _append_unique(actions, "attach_request_id")

    if contract.authorization_mode == "recommended-pass-through" and not context.authorization_present:
        warnings.append("missing_authorization_header")
        _append_unique(actions, "forward_authorization_header")

    if contract.session_subject_mode == "recommended-pass-through":
        if not context.session_present:
            warnings.append("missing_session_claims")
            _append_unique(actions, "forward_session_claims")
        elif context.session_subject is None:
            warnings.append("missing_session_subject_claim")
            _append_unique(actions, "forward_subject_session_claim")

    if contract.session_mode == "recommended-pass-through" and not context.authorization_present and not context.session_present:
        warnings.append("missing_identity_context")
        _append_unique(actions, "forward_identity_context")

    return PublicMcpTransportAssessment(
        name=context.name,
        route_name=context.route_name,
        kind=context.kind,
        transport_contract=contract,
        transport_context=context,
        warnings=tuple(warnings),
        suggested_actions=tuple(actions),
    )


def _build_public_preflight_assessment(
    *,
    name: str,
    route_name: str,
    kind: str,
    transport_kind: str,
    route_contract: PublicMcpRouteContract | None,
    response_contract: PublicMcpResponseContract | None,
    recovery_policy: PublicMcpRecoveryPolicy | None,
    transport_contract: PublicMcpTransportContract | None,
    transport_context: PublicMcpTransportContext | None,
    transport_assessment: PublicMcpTransportAssessment | None,
) -> PublicMcpPreflightAssessment:
    blockers: list[str] = []
    warnings: list[str] = []
    actions: list[str] = []

    if transport_assessment is not None:
        warnings.extend(list(transport_assessment.warnings))
        actions.extend(list(transport_assessment.suggested_actions))

    idempotency = recovery_policy.idempotency_class if recovery_policy is not None else "unknown"
    if idempotency != "read-only":
        _append_unique(warnings, "non_idempotent_route_family")
        _append_unique(actions, "verify_execution_intent")

    if transport_assessment is not None and transport_contract is not None and idempotency != "read-only":
        if "missing_identity_context" in transport_assessment.warnings:
            _append_unique(warnings, "missing_identity_context_for_mutation_route")
            _append_unique(actions, "attach_identity_context_before_execution")
        if "missing_request_id" in transport_assessment.warnings:
            _append_unique(warnings, "missing_request_id_for_mutation_route")
            _append_unique(actions, "attach_request_id_before_execution")

    if transport_contract is not None and transport_context is not None:
        if transport_contract.authorization_mode == "required-pass-through" and not transport_context.authorization_present:
            blockers.append("authorization_header_required")
            _append_unique(actions, "forward_authorization_header")
        if transport_contract.session_subject_mode == "required-pass-through" and transport_context.session_subject is None:
            blockers.append("session_subject_required")
            _append_unique(actions, "forward_subject_session_claim")
        if transport_contract.request_id_mode == "required" and not transport_context.request_id:
            blockers.append("request_id_required")
            _append_unique(actions, "attach_request_id")

    risk_level = "low"
    if warnings:
        risk_level = "elevated"
    if blockers or any(flag in warnings for flag in ("missing_identity_context_for_mutation_route", "missing_request_id_for_mutation_route")):
        risk_level = "high"

    return PublicMcpPreflightAssessment(
        name=name,
        route_name=route_name,
        kind=kind,
        transport_kind=transport_kind,
        route_contract=route_contract,
        response_contract=response_contract,
        recovery_policy=recovery_policy,
        transport_contract=transport_contract,
        transport_context=transport_context,
        transport_assessment=transport_assessment,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        suggested_actions=tuple(actions),
        risk_level=risk_level,
    )

