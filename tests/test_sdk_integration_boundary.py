from __future__ import annotations

from src import integration as root_integration
from src import sdk
from src.sdk import integration
from src.sdk.integration import (
    PUBLIC_INTEGRATION_SDK_SURFACE_VERSION,
    PublicMcpCompatibilitySurface,
    PublicMcpResourceDescriptor,
    PublicMcpToolDescriptor,
    build_public_mcp_compatibility_surface,
    build_public_mcp_resources,
    build_public_mcp_tools,
)


def test_sdk_root_exposes_integration_module() -> None:
    assert sdk.PUBLIC_SDK_SURFACE_VERSION == "1.1"
    assert sdk.PUBLIC_SDK_MODULES == ("artifacts", "server", "integration")
    assert sdk.integration is integration
    assert root_integration is integration


def test_mcp_tool_descriptors_follow_public_route_surface() -> None:
    tools = build_public_mcp_tools()
    indexed = {tool.route_name: tool for tool in tools}

    assert all(isinstance(tool, PublicMcpToolDescriptor) for tool in tools)
    assert indexed["launch_run"].method == "POST"
    assert indexed["launch_run"].path == "/api/runs"
    assert indexed["launch_run"].request_type is not None
    assert indexed["launch_workspace_shell"].path.endswith("/shell/launch")
    assert indexed["commit_workspace_shell"].path.endswith("/shell/commit")
    assert indexed["retry_run"].response_type is not None


def test_mcp_resource_descriptors_follow_public_route_surface() -> None:
    resources = build_public_mcp_resources()
    indexed = {resource.route_name: resource for resource in resources}

    assert all(isinstance(resource, PublicMcpResourceDescriptor) for resource in resources)
    assert indexed["get_run_status"].method == "GET"
    assert indexed["get_run_status"].path == "/api/runs/{run_id}"
    assert indexed["get_run_result"].response_type is not None
    assert indexed["list_run_artifacts"].path.endswith("/artifacts")
    assert indexed["get_recent_activity"].path == "/api/users/me/activity"


def test_build_public_mcp_compatibility_surface_returns_curated_surface() -> None:
    surface = build_public_mcp_compatibility_surface()

    assert PUBLIC_INTEGRATION_SDK_SURFACE_VERSION == "1.0"
    assert isinstance(surface, PublicMcpCompatibilitySurface)
    assert surface.version == "1.0"
    assert len(surface.tools) >= 5
    assert len(surface.resources) >= 8
    assert any(tool.route_name == "launch_run" for tool in surface.tools)
    assert any(resource.route_name == "get_run_trace" for resource in surface.resources)
