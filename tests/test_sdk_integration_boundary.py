from __future__ import annotations

from src import integration as root_integration
from src import sdk
from src.sdk import integration
from src.sdk.integration import (
    MCP_ADAPTER_SCAFFOLD_VERSION,
    MCP_HOST_BRIDGE_SCAFFOLD_VERSION,
    PUBLIC_MCP_MANIFEST_VERSION,
    PUBLIC_INTEGRATION_SDK_SURFACE_VERSION,
    PublicMcpAdapterScaffold,
    PublicMcpArgumentSchema,
    PublicMcpCompatibilitySurface,
    PublicMcpFrameworkDispatch,
    PublicMcpHostBridgeScaffold,
    PublicMcpHttpDispatch,
    PublicMcpManifest,
    PublicMcpResourceDescriptor,
    PublicMcpToolDescriptor,
    build_public_mcp_adapter_scaffold,
    build_public_mcp_compatibility_surface,
    build_public_mcp_manifest,
    build_public_mcp_host_bridge_scaffold,
    build_public_mcp_resources,
    build_public_mcp_tools,
)


def test_sdk_root_exposes_integration_module() -> None:
    assert sdk.PUBLIC_SDK_SURFACE_VERSION == "1.6"
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

    assert PUBLIC_INTEGRATION_SDK_SURFACE_VERSION == "1.4"
    assert isinstance(surface, PublicMcpCompatibilitySurface)
    assert surface.version == "1.4"
    assert len(surface.tools) >= 5
    assert len(surface.resources) >= 8
    assert any(tool.route_name == "launch_run" for tool in surface.tools)
    assert any(resource.route_name == "get_run_trace" for resource in surface.resources)


def test_build_public_mcp_adapter_scaffold_exports_runnable_bridge_shape() -> None:
    scaffold = build_public_mcp_adapter_scaffold(base_url="https://api.nexa.test")

    assert MCP_ADAPTER_SCAFFOLD_VERSION == "1.0"
    assert isinstance(scaffold, PublicMcpAdapterScaffold)

    launch_export = scaffold.export_tool("launch_run", json_body={"workspace_id": "ws-1"})
    status_export = scaffold.export_resource("get_run_status", path_params={"run_id": "run-1"})
    export = scaffold.export()

    assert launch_export.invocation.method == "POST"
    assert launch_export.invocation.url == "https://api.nexa.test/api/runs"
    assert launch_export.invocation.json_body == {"workspace_id": "ws-1"}
    assert status_export.uri_template == "nexa://public/api/runs/{run_id}"
    assert status_export.invocation.path == "/api/runs/run-1"
    assert status_export.invocation.url == "https://api.nexa.test/api/runs/run-1"
    assert export.transport_kind == "http-route-bridge"
    assert export.stability == "scaffold"
    assert any(tool.route_name == "launch_run" for tool in export.tools)
    assert any(resource.route_name == "get_run_status" for resource in export.resources)


def test_build_public_mcp_adapter_scaffold_rejects_missing_path_params() -> None:
    scaffold = build_public_mcp_adapter_scaffold()

    try:
        scaffold.export_resource("get_run_status")
    except ValueError as exc:
        assert "Missing path parameters" in str(exc)
    else:
        raise AssertionError("Expected missing path parameter validation")


def test_build_public_mcp_manifest_returns_serializable_public_contract() -> None:
    scaffold = build_public_mcp_adapter_scaffold(
        base_url="https://api.nexa.test",
        resource_uri_prefix="nexa://phase92",
    )

    manifest = scaffold.export_manifest(server_name="nexa-phase92", server_title="Nexa Phase 9.2")
    manifest_dict = manifest.to_dict()
    direct_manifest = build_public_mcp_manifest(
        base_url="https://api.nexa.test",
        resource_uri_prefix="nexa://phase92",
        server_name="nexa-phase92",
        server_title="Nexa Phase 9.2",
    )

    assert PUBLIC_MCP_MANIFEST_VERSION == "1.0"
    assert isinstance(manifest, PublicMcpManifest)
    assert manifest.manifest_version == "1.0"
    assert manifest.server_name == "nexa-phase92"
    assert manifest.server_title == "Nexa Phase 9.2"
    assert manifest.base_url == "https://api.nexa.test"
    assert manifest.resource_uri_prefix == "nexa://phase92"
    assert any(tool.route_name == "launch_run" for tool in manifest.tools)
    assert any(resource.uri_template == "nexa://phase92/api/runs/{run_id}" for resource in manifest.resources)
    assert manifest_dict["server"]["name"] == "nexa-phase92"
    assert manifest_dict["tools"][0]["request_type"] is None or "module" in manifest_dict["tools"][0]["request_type"]
    assert direct_manifest.to_dict() == manifest_dict


def test_adapter_scaffold_exports_argument_schema_contracts() -> None:
    scaffold = build_public_mcp_adapter_scaffold(base_url="https://api.nexa.test")

    launch_schema = scaffold.export_tool_schema("launch_run")
    status_schema = scaffold.export_resource_schema("get_run_status")
    manifest = scaffold.export_manifest()

    assert isinstance(launch_schema, PublicMcpArgumentSchema)
    assert [field.name for field in launch_schema.body_fields if field.required] == ["workspace_id", "execution_target"]
    assert status_schema is not None
    assert [field.name for field in status_schema.path_fields] == ["run_id"]
    assert [field.name for field in status_schema.query_fields] == ["include", "lang"]
    launch_manifest = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    assert launch_manifest.argument_schema is not None
    assert launch_manifest.argument_schema.to_dict()["body_fields"][0]["name"] == "workspace_id"
    manifest_dict = manifest.to_dict()
    manifest_tool = next(tool for tool in manifest_dict["tools"] if tool["route_name"] == "launch_run")
    assert manifest_tool["argument_schema"]["body_fields"][1]["name"] == "execution_target"


def test_build_public_mcp_host_bridge_scaffold_builds_framework_and_http_requests() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

    assert MCP_HOST_BRIDGE_SCAFFOLD_VERSION == "1.2"
    assert isinstance(bridge, PublicMcpHostBridgeScaffold)

    framework_request = bridge.build_framework_tool_request(
        "launch_run",
        json_body={"workspace_id": "ws-1"},
        headers={"Authorization": "Bearer host-token"},
        session_claims={"sub": "user-1"},
    )
    http_request = bridge.build_http_resource_request(
        "get_run_status",
        path_params={"run_id": "run-1"},
        query_params={"include": "summary"},
    )
    export = bridge.export()

    assert framework_request.method == "POST"
    assert framework_request.path == "/api/runs"
    assert framework_request.headers["Authorization"] == "Bearer host-token"
    assert framework_request.json_body == {"workspace_id": "ws-1"}
    assert framework_request.session_claims == {"sub": "user-1"}
    assert http_request.method == "GET"
    assert http_request.path == "/api/runs/run-1"
    assert http_request.path_params == {"run_id": "run-1"}
    assert http_request.query_params == {"include": "summary"}
    assert export.framework_binding_class == "FrameworkRouteBindings"
    assert any(binding.route_name == "launch_run" and binding.framework_handler_name == "handle_launch" for binding in export.tool_bindings)
    assert any(binding.route_name == "get_run_status" and binding.framework_handler_name == "handle_run_status" for binding in export.resource_bindings)


def test_build_public_mcp_host_bridge_scaffold_rejects_missing_path_params() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    try:
        bridge.build_framework_resource_request("get_run_status")
    except ValueError as exc:
        assert "Missing path parameters" in str(exc)
    else:
        raise AssertionError("Expected missing path parameter validation")


def test_build_public_mcp_host_bridge_scaffold_normalizes_flat_tool_arguments() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

    request = bridge.build_framework_tool_request_from_arguments(
        "launch_workspace_shell",
        {
            "workspace_id": "ws-1",
            "app_language": "ko",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-1"},
            "launch_options": {"mode": "standard", "priority": "normal"},
        },
    )

    assert request.method == "POST"
    assert request.path == "/api/workspaces/ws-1/shell/launch"
    assert request.path_params == {"workspace_id": "ws-1"}
    assert request.json_body == {
        "app_language": "ko",
        "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-1"},
        "launch_options": {"mode": "standard", "priority": "normal"},
    }


def test_build_public_mcp_host_bridge_scaffold_normalizes_flat_resource_arguments() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

    request = bridge.build_http_resource_request_from_arguments(
        "get_run_status",
        {
            "run_id": "run-1",
            "include": "summary",
            "lang": "ko",
        },
    )

    assert request.method == "GET"
    assert request.path == "/api/runs/run-1"
    assert request.path_params == {"run_id": "run-1"}
    assert request.query_params == {"include": "summary", "lang": "ko"}
    assert request.json_body is None


def test_build_public_mcp_host_bridge_scaffold_builds_dispatch_plans() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    framework_dispatch = bridge.build_framework_resource_dispatch(
        "get_run_status",
        {"run_id": "run-1", "include": "summary"},
    )
    http_dispatch = bridge.build_http_tool_dispatch(
        "retry_run",
        {"run_id": "run-1", "query_params": {"reason": "host"}},
    )

    assert isinstance(framework_dispatch, PublicMcpFrameworkDispatch)
    assert framework_dispatch.handler_name == "handle_run_status"
    assert framework_dispatch.request.path == "/api/runs/run-1"
    assert framework_dispatch.request.query_params == {"include": "summary"}

    assert isinstance(http_dispatch, PublicMcpHttpDispatch)
    assert http_dispatch.route_name == "retry_run"
    assert http_dispatch.request.path == "/api/runs/run-1/retry"
    assert http_dispatch.request.query_params == {"reason": "host"}


def test_build_public_mcp_host_bridge_scaffold_rejects_missing_required_body_fields() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    try:
        bridge.build_framework_tool_request_from_arguments(
            "launch_run",
            {"workspace_id": "ws-1"},
        )
    except ValueError as exc:
        assert "Missing required body field(s)" in str(exc)
    else:
        raise AssertionError("Expected required body field validation")


def test_build_public_mcp_host_bridge_scaffold_rejects_unexpected_body_fields() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    try:
        bridge.build_framework_tool_request_from_arguments(
            "launch_workspace_shell",
            {"workspace_id": "ws-1", "unexpected": True},
        )
    except ValueError as exc:
        assert "Unexpected body field(s)" in str(exc)
    else:
        raise AssertionError("Expected unexpected body field validation")


def test_build_public_mcp_host_bridge_scaffold_rejects_unexpected_query_fields() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    try:
        bridge.build_http_resource_request_from_arguments(
            "get_run_status",
            {"run_id": "run-1", "include": "summary", "unexpected": "boom"},
        )
    except ValueError as exc:
        assert "Unexpected query field(s)" in str(exc)
    else:
        raise AssertionError("Expected unexpected query field validation")


def test_build_public_mcp_host_bridge_scaffold_rejects_conflicting_argument_sources() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    try:
        bridge.build_framework_resource_request_from_arguments(
            "get_run_status",
            {"path_params": {"run_id": "run-1"}, "run_id": "run-2"},
        )
    except ValueError as exc:
        assert "Duplicate path_params value" in str(exc)
    else:
        raise AssertionError("Expected duplicate path parameter validation")


def test_build_public_mcp_host_bridge_scaffold_rejects_body_on_resource_arguments() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    try:
        bridge.build_http_resource_request_from_arguments(
            "get_run_status",
            {"run_id": "run-1", "json_body": {"unexpected": True}},
        )
    except ValueError as exc:
        assert "does not accept json_body/body" in str(exc)
    else:
        raise AssertionError("Expected body rejection for resource arguments")
