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

PUBLIC_INTEGRATION_SDK_SURFACE_VERSION = "1.7"


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
class PublicMcpResponseContract:
    name: str
    route_name: str
    kind: str
    route_family: str
    response_shape: str
    success_status_codes: tuple[int, ...]
    response_media_type: str = "application/json"
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
            "response_type": _type_ref_dict(self.response_type),
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
        }


@dataclass(frozen=True)
class PublicMcpCompatibilitySurface:
    version: str
    tools: tuple[PublicMcpToolDescriptor, ...]
    resources: tuple[PublicMcpResourceDescriptor, ...]


@dataclass(frozen=True)
class PublicMcpCompatibilityPolicy:
    policy_version: str
    manifest_version: str
    schema_version: str
    surface_version: str
    adapter_version: str
    host_bridge_version: str
    supported_manifest_versions: tuple[str, ...] = ()
    supported_schema_versions: tuple[str, ...] = ()

    def supports_manifest_version(self, version: str) -> bool:
        return version in self.supported_manifest_versions

    def supports_schema_version(self, version: str) -> bool:
        return version in self.supported_schema_versions

    def assert_supported(
        self,
        *,
        manifest_version: str | None = None,
        schema_version: str | None = None,
    ) -> None:
        if manifest_version is not None and not self.supports_manifest_version(manifest_version):
            raise ValueError(
                f"Unsupported public MCP manifest version: {manifest_version}; supported versions: {', '.join(self.supported_manifest_versions)}"
            )
        if schema_version is not None and not self.supports_schema_version(schema_version):
            raise ValueError(
                f"Unsupported public MCP schema version: {schema_version}; supported versions: {', '.join(self.supported_schema_versions)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "manifest_version": self.manifest_version,
            "schema_version": self.schema_version,
            "surface_version": self.surface_version,
            "adapter_version": self.adapter_version,
            "host_bridge_version": self.host_bridge_version,
            "supported_manifest_versions": list(self.supported_manifest_versions),
            "supported_schema_versions": list(self.supported_schema_versions),
        }


PUBLIC_MCP_MANIFEST_VERSION = "1.3"
PUBLIC_MCP_SCHEMA_VERSION = "1.3"
PUBLIC_MCP_COMPATIBILITY_POLICY_VERSION = "1.0"


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
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpManifest:
    manifest_version: str
    schema_version: str
    adapter_version: str
    surface_version: str
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
            "manifest_version": self.manifest_version,
            "schema_version": self.schema_version,
            "adapter_version": self.adapter_version,
            "surface_version": self.surface_version,
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
                    "tags": list(resource.tags),
                }
                for resource in self.resources
            ],
        }


MCP_ADAPTER_SCAFFOLD_VERSION = "1.0"


MCP_HOST_BRIDGE_SCAFFOLD_VERSION = "1.5"


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
    handler_name: str
    request: FrameworkInboundRequest
    route_contract: PublicMcpRouteContract | None = None


@dataclass(frozen=True)
class PublicMcpHttpDispatch:
    name: str
    route_name: str
    request: HttpRouteRequest
    route_contract: PublicMcpRouteContract | None = None


@dataclass(frozen=True)
class PublicMcpHostBridgeExport:
    bridge_version: str
    adapter_version: str
    schema_version: str
    surface_version: str
    compatibility_policy: PublicMcpCompatibilityPolicy
    framework_binding_class: str
    tool_bindings: tuple[PublicMcpHostRouteBinding, ...]
    resource_bindings: tuple[PublicMcpHostRouteBinding, ...]


@dataclass(frozen=True)
class PublicMcpHostBridgeScaffold:
    bridge_version: str
    adapter_scaffold: PublicMcpAdapterScaffold

    def export(self) -> PublicMcpHostBridgeExport:
        return PublicMcpHostBridgeExport(
            bridge_version=self.bridge_version,
            adapter_version=self.adapter_scaffold.adapter_version,
            schema_version=PUBLIC_MCP_SCHEMA_VERSION,
            surface_version=self.adapter_scaffold.surface.version,
            compatibility_policy=self.adapter_scaffold.compatibility_policy(),
            framework_binding_class="FrameworkRouteBindings",
            tool_bindings=tuple(self._tool_binding(tool) for tool in self.adapter_scaffold.surface.tools),
            resource_bindings=tuple(self._resource_binding(resource) for resource in self.adapter_scaffold.surface.resources),
        )

    def assert_consumer_compatibility(
        self,
        *,
        manifest_version: str | None = None,
        schema_version: str | None = None,
    ) -> None:
        self.adapter_scaffold.assert_consumer_compatibility(
            manifest_version=manifest_version,
            schema_version=schema_version,
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
            handler_name=_framework_handler_name(descriptor.route_name),
            request=request,
            route_contract=self.adapter_scaffold.export_tool_contract(tool_name),
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
            handler_name=_framework_handler_name(descriptor.route_name),
            request=request,
            route_contract=self.adapter_scaffold.export_resource_contract(resource_name),
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
            request=request,
            route_contract=self.adapter_scaffold.export_tool_contract(tool_name),
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
            request=request,
            route_contract=self.adapter_scaffold.export_resource_contract(resource_name),
        )

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
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpAdapterExport:
    adapter_version: str
    schema_version: str
    surface_version: str
    transport_kind: str
    stability: str
    compatibility_policy: PublicMcpCompatibilityPolicy
    tools: tuple[PublicMcpToolExport, ...]
    resources: tuple[PublicMcpResourceExport, ...]


@dataclass(frozen=True)
class PublicMcpAdapterScaffold:
    adapter_version: str
    surface: PublicMcpCompatibilitySurface
    base_url: str | None = None
    resource_uri_prefix: str = "nexa://public"

    def export(self) -> PublicMcpAdapterExport:
        return PublicMcpAdapterExport(
            adapter_version=self.adapter_version,
            schema_version=PUBLIC_MCP_SCHEMA_VERSION,
            surface_version=self.surface.version,
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
            manifest_version=PUBLIC_MCP_MANIFEST_VERSION,
            schema_version=PUBLIC_MCP_SCHEMA_VERSION,
            adapter_version=self.adapter_version,
            surface_version=self.surface.version,
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
            policy_version=PUBLIC_MCP_COMPATIBILITY_POLICY_VERSION,
            manifest_version=PUBLIC_MCP_MANIFEST_VERSION,
            schema_version=PUBLIC_MCP_SCHEMA_VERSION,
            surface_version=self.surface.version,
            adapter_version=self.adapter_version,
            host_bridge_version=MCP_HOST_BRIDGE_SCAFFOLD_VERSION,
            supported_manifest_versions=(PUBLIC_MCP_MANIFEST_VERSION,),
            supported_schema_versions=(PUBLIC_MCP_SCHEMA_VERSION,),
        )

    def assert_consumer_compatibility(
        self,
        *,
        manifest_version: str | None = None,
        schema_version: str | None = None,
    ) -> None:
        self.compatibility_policy().assert_supported(
            manifest_version=manifest_version,
            schema_version=schema_version,
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
            tags=descriptor.tags,
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
            response_type=getattr(descriptor, "response_type", None),
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


def _normalize_public_framework_response(
    name: str,
    route_name: str,
    kind: str,
    response_contract: PublicMcpResponseContract,
    response: "FrameworkOutboundResponse",
) -> PublicMcpNormalizedResponse:
    _assert_public_response_matches_contract(
        response_contract,
        status_code=response.status_code,
        media_type=response.media_type,
    )
    return PublicMcpNormalizedResponse(
        name=name,
        route_name=route_name,
        kind=kind,
        response_contract=response_contract,
        status_code=response.status_code,
        media_type=response.media_type,
        body=_decode_public_response_body(media_type=response.media_type, body_text=response.body_text),
    )


def _normalize_public_http_response(
    name: str,
    route_name: str,
    kind: str,
    response_contract: PublicMcpResponseContract,
    response: "HttpRouteResponse",
) -> PublicMcpNormalizedResponse:
    media_type = str(dict(response.headers).get("content-type", "application/json"))
    _assert_public_response_matches_contract(
        response_contract,
        status_code=response.status_code,
        media_type=media_type,
    )
    return PublicMcpNormalizedResponse(
        name=name,
        route_name=route_name,
        kind=kind,
        response_contract=response_contract,
        status_code=response.status_code,
        media_type=media_type,
        body=dict(response.body),
    )


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
        adapter_version=MCP_ADAPTER_SCAFFOLD_VERSION,
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
        bridge_version=MCP_HOST_BRIDGE_SCAFFOLD_VERSION,
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
    "list_workspaces": {
    },
}


_ROUTE_CONTRACT_BY_ROUTE_NAME: dict[str, dict[str, str]] = {
    "launch_run": {"route_family": "run-launch", "transport_profile": "body-only"},
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
    "list_workspaces": {"route_family": "workspace-list", "transport_profile": "no-arguments"},
}


_RESPONSE_CONTRACT_BY_ROUTE_NAME: dict[str, dict[str, object]] = {
    "launch_run": {"response_shape": "accepted", "success_status_codes": (202,)},
    "launch_workspace_shell": {"response_shape": "accepted", "success_status_codes": (202,)},
    "commit_workspace_shell": {"response_shape": "snapshot-commit", "success_status_codes": (200,)},
    "checkout_workspace_shell": {"response_shape": "working-save-checkout", "success_status_codes": (200,)},
    "retry_run": {"response_shape": "run-control", "success_status_codes": (200,)},
    "force_reset_run": {"response_shape": "run-control", "success_status_codes": (200,)},
    "mark_run_reviewed": {"response_shape": "run-control", "success_status_codes": (200,)},
    "get_run_status": {"response_shape": "status", "success_status_codes": (200,)},
    "get_run_result": {"response_shape": "result", "success_status_codes": (200,)},
    "list_workspace_runs": {"response_shape": "list", "success_status_codes": (200,)},
    "get_run_trace": {"response_shape": "trace", "success_status_codes": (200,)},
    "list_run_artifacts": {"response_shape": "list", "success_status_codes": (200,)},
    "get_artifact_detail": {"response_shape": "detail", "success_status_codes": (200,)},
    "get_run_actions": {"response_shape": "action-log", "success_status_codes": (200,)},
    "get_recent_activity": {"response_shape": "activity", "success_status_codes": (200,)},
    "get_workspace": {"response_shape": "detail", "success_status_codes": (200,)},
    "list_workspaces": {"response_shape": "list", "success_status_codes": (200,)},
}


def build_public_mcp_response_contracts() -> tuple[PublicMcpResponseContract, ...]:
    """Return exported response contracts for the curated public MCP surface."""

    adapter = build_public_mcp_adapter_scaffold()
    contracts: list[PublicMcpResponseContract] = []
    for tool in build_public_mcp_tools():
        contracts.append(adapter.export_tool_response_contract(tool.name))
    for resource in build_public_mcp_resources():
        contracts.append(adapter.export_resource_response_contract(resource.name))
    return tuple(contracts)


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
        "name": "launch_workspace_shell",
        "route_name": "launch_workspace_shell",
        "description": "Launch a run from the current workspace shell artifact.",
        "request_type": PublicTypeRef("src.sdk.server", "ProductRunLaunchRequest"),
        "response_type": PublicTypeRef("src.sdk.server", "ProductRunLaunchAcceptedResponse"),
        "tags": ("workspace-shell", "launch", "public-boundary"),
    },
    {
        "name": "commit_workspace_shell",
        "route_name": "commit_workspace_shell",
        "description": "Convert the current workspace shell working_save into a commit_snapshot.",
        "tags": ("workspace-shell", "lifecycle", "commit"),
    },
    {
        "name": "checkout_workspace_shell",
        "route_name": "checkout_workspace_shell",
        "description": "Reopen the current workspace shell commit_snapshot as a working_save.",
        "tags": ("workspace-shell", "lifecycle", "checkout"),
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


def build_public_mcp_compatibility_policy() -> PublicMcpCompatibilityPolicy:
    """Return the version-compatibility policy for the curated public MCP surface."""

    return build_public_mcp_adapter_scaffold().compatibility_policy()


def build_public_mcp_compatibility_surface() -> PublicMcpCompatibilitySurface:
    """Return the complete MCP compatibility shape for the public SDK boundary."""

    return PublicMcpCompatibilitySurface(
        version=PUBLIC_INTEGRATION_SDK_SURFACE_VERSION,
        tools=build_public_mcp_tools(),
        resources=build_public_mcp_resources(),
    )


__all__ = [
    "PUBLIC_INTEGRATION_SDK_SURFACE_VERSION",
    "MCP_ADAPTER_SCAFFOLD_VERSION",
    "MCP_HOST_BRIDGE_SCAFFOLD_VERSION",
    "PUBLIC_MCP_MANIFEST_VERSION",
    "PUBLIC_MCP_SCHEMA_VERSION",
    "PUBLIC_MCP_COMPATIBILITY_POLICY_VERSION",
    "PublicTypeRef",
    "PublicMcpToolDescriptor",
    "PublicMcpResourceDescriptor",
    "PublicMcpArgumentField",
    "PublicMcpArgumentSchema",
    "PublicMcpRouteContract",
    "PublicMcpNormalizedArguments",
    "PublicMcpResponseContract",
    "PublicMcpNormalizedResponse",
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
    "PublicMcpHostBridgeExport",
    "PublicMcpHostBridgeScaffold",
    "build_public_mcp_tools",
    "build_public_mcp_resources",
    "build_public_mcp_argument_schemas",
    "build_public_mcp_route_contracts",
    "build_public_mcp_response_contracts",
    "build_public_mcp_compatibility_policy",
    "build_public_mcp_compatibility_surface",
    "build_public_mcp_adapter_scaffold",
    "build_public_mcp_manifest",
    "build_public_mcp_host_bridge_scaffold",
]
