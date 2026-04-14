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
from typing import Mapping

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
    "PublicTypeRef",
    "PublicMcpToolDescriptor",
    "PublicMcpResourceDescriptor",
    "PublicMcpCompatibilitySurface",
    "build_public_mcp_tools",
    "build_public_mcp_resources",
    "build_public_mcp_compatibility_surface",
]
