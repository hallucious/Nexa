from __future__ import annotations

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

from src.server.http_route_surface import RunHttpRouteSurface

PUBLIC_INTEGRATION_SDK_SURFACE_VERSION = "1.0"


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
class PublicMcpCompatibilitySurface:
    version: str
    tools: tuple[PublicMcpToolDescriptor, ...]
    resources: tuple[PublicMcpResourceDescriptor, ...]


MCP_ADAPTER_SCAFFOLD_VERSION = "1.0"


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
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpResourceExport:
    name: str
    description: str
    route_name: str
    uri_template: str
    invocation: PublicMcpInvocation
    response_type: PublicTypeRef | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicMcpAdapterExport:
    adapter_version: str
    surface_version: str
    transport_kind: str
    stability: str
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
            surface_version=self.surface.version,
            transport_kind="http-route-bridge",
            stability="scaffold",
            tools=tuple(self._export_tool_descriptor(tool) for tool in self.surface.tools),
            resources=tuple(self._export_resource_descriptor(resource) for resource in self.surface.resources),
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
            tags=descriptor.tags,
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


def _normalize_string_mapping(values: Mapping[str, object] | None) -> Mapping[str, str]:
    if not values:
        return {}
    return {str(key): str(value) for key, value in values.items()}


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


_ROUTE_INDEX = {
    name: (method, path)
    for name, method, path in RunHttpRouteSurface._ROUTE_DEFINITIONS
}


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
    "PublicTypeRef",
    "PublicMcpToolDescriptor",
    "PublicMcpResourceDescriptor",
    "PublicMcpCompatibilitySurface",
    "PublicMcpInvocation",
    "PublicMcpToolExport",
    "PublicMcpResourceExport",
    "PublicMcpAdapterExport",
    "PublicMcpAdapterScaffold",
    "build_public_mcp_tools",
    "build_public_mcp_resources",
    "build_public_mcp_compatibility_surface",
    "build_public_mcp_adapter_scaffold",
]
