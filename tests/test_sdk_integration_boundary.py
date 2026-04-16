from __future__ import annotations

from dataclasses import replace

from src import integration as root_integration
from src import sdk
from src.sdk import integration
from src.server import EngineRunStatusSnapshot, EngineSignal, RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.framework_binding_models import FrameworkOutboundResponse
from src.server.http_route_models import HttpRouteResponse

from src.sdk.integration import (
    PublicMcpAdapterScaffold,
    PublicMcpArgumentSchema,
    PublicMcpCompatibilitySurface,
    PublicMcpCompatibilityPolicy,
    PublicMcpFrameworkDispatch,
    PublicMcpHostBridgeScaffold,
    PublicMcpHttpDispatch,
    PublicMcpManifest,
    PublicMcpNormalizedArguments,
    PublicMcpNormalizedResponse,
    PublicMcpRecoveryHint,
    PublicMcpRecoveryPolicy,
    PublicMcpSessionContract,
    PublicMcpTransportContract,
    PublicMcpTransportContext,
    PublicMcpTransportAssessment,
    PublicMcpPreflightAssessment,
    PublicMcpLifecycleControlProfile,
    PublicMcpLifecycleStateHint,
    PublicMcpOrchestrationSummary,
    PublicMcpFrameworkEnvelope,
    PublicMcpHttpEnvelope,
    PublicMcpResultShapeProfile,
    PublicMcpResponseContract,
    PublicMcpResourceDescriptor,
    PublicMcpRouteContract,
    PublicMcpToolDescriptor,
    build_public_mcp_adapter_scaffold,
    build_public_mcp_argument_schemas,
    build_public_mcp_route_contracts,
    build_public_mcp_transport_contracts,
    build_public_mcp_result_shape_profiles,
    build_public_mcp_response_contracts,
    build_public_mcp_recovery_policies,
    build_public_mcp_lifecycle_control_profiles,
    build_public_mcp_compatibility_policy,
    build_public_mcp_compatibility_surface,
    build_public_mcp_manifest,
    build_public_mcp_host_bridge_scaffold,
    build_public_mcp_resources,
    build_public_mcp_tools,
)


def _workspace() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        viewer_user_refs=("user-viewer",),
    )


def _run_context(*, owner: str = "user-owner") -> RunAuthorizationContext:
    return RunAuthorizationContext(
        run_id="run-001",
        workspace_context=_workspace(),
        run_owner_user_ref=owner,
    )


def _run_row(*, status: str = "running", status_family: str = "active") -> dict:
    return {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-001",
        "status": status,
        "status_family": status_family,
        "created_at": "2026-04-11T12:00:00+00:00",
        "started_at": "2026-04-11T12:00:05+00:00",
        "updated_at": "2026-04-11T12:00:10+00:00",
        "finished_at": None,
        "requested_by_user_id": "user-owner",
        "trace_available": False,
    }



def test_sdk_root_exposes_integration_module() -> None:
    assert not hasattr(sdk, "PUBLIC_SDK_SURFACE_VERSION")
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
    assert indexed["put_workspace_shell_draft"].path.endswith("/shell/draft")
    assert indexed["launch_workspace_shell"].path.endswith("/shell/launch")
    assert indexed["commit_workspace_shell"].path.endswith("/shell/commit")
    assert indexed["checkout_workspace_shell"].path.endswith("/shell/checkout")
    assert "public-consumption" in indexed["checkout_workspace_shell"].tags
    assert indexed["retry_run"].response_type is not None
    assert indexed["revoke_issuer_public_shares"].path == "/api/users/me/public-shares/actions/revoke"
    assert indexed["extend_issuer_public_shares"].path == "/api/users/me/public-shares/actions/extend"
    assert indexed["archive_issuer_public_shares"].path == "/api/users/me/public-shares/actions/archive"
    assert indexed["delete_issuer_public_shares"].path == "/api/users/me/public-shares/actions/delete"
    assert indexed["create_workspace"].path == "/api/workspaces"
    assert indexed["put_workspace_provider_binding"].path == "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}"
    assert indexed["probe_workspace_provider"].path == "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe"
    assert indexed["put_onboarding"].path == "/api/users/me/onboarding"


def test_mcp_resource_descriptors_follow_public_route_surface() -> None:
    resources = build_public_mcp_resources()
    indexed = {resource.route_name: resource for resource in resources}

    assert all(isinstance(resource, PublicMcpResourceDescriptor) for resource in resources)
    assert indexed["get_run_status"].method == "GET"
    assert indexed["get_run_status"].path == "/api/runs/{run_id}"
    assert indexed["get_run_result"].response_type is not None
    assert indexed["list_run_artifacts"].path.endswith("/artifacts")
    assert indexed["get_recent_activity"].path == "/api/users/me/activity"
    assert indexed["list_issuer_public_shares"].path == "/api/users/me/public-shares"
    assert indexed["get_issuer_public_share_summary"].path == "/api/users/me/public-shares/summary"
    assert indexed["get_workspace_shell"].path.endswith("/shell")
    assert indexed["list_issuer_public_share_action_reports"].path == "/api/users/me/public-shares/action-reports"
    assert indexed["get_issuer_public_share_action_report_summary"].path == "/api/users/me/public-shares/action-reports/summary"
    assert indexed["get_provider_catalog"].path == "/api/providers/catalog"
    assert indexed["list_workspace_provider_bindings"].path == "/api/workspaces/{workspace_id}/provider-bindings"
    assert indexed["list_workspace_provider_health"].path == "/api/workspaces/{workspace_id}/provider-bindings/health"
    assert indexed["get_workspace_provider_health"].path == "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/health"
    assert indexed["list_provider_probe_history"].path == "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe-history"
    assert indexed["get_onboarding"].path == "/api/users/me/onboarding"


def test_build_public_mcp_compatibility_surface_returns_curated_surface() -> None:
    surface = build_public_mcp_compatibility_surface()

    assert isinstance(surface, PublicMcpCompatibilitySurface)
    assert "argument-schema" in surface.contract_markers
    assert "execution-report" in surface.runtime_markers
    assert len(surface.tools) >= 5
    assert len(surface.resources) >= 8
    assert any(tool.route_name == "launch_run" for tool in surface.tools)
    assert any(resource.route_name == "get_run_trace" for resource in surface.resources)
    assert any(tool.route_name == "create_workspace" for tool in surface.tools)
    assert any(tool.route_name == "submit_workspace_feedback" for tool in surface.tools)
    assert any(resource.route_name == "get_provider_catalog" for resource in surface.resources)
    assert any(resource.route_name == "get_history_summary" for resource in surface.resources)
    assert any(resource.route_name == "get_workspace_result_history" for resource in surface.resources)
    assert any(resource.route_name == "get_workspace_feedback" for resource in surface.resources)


def test_build_public_mcp_adapter_scaffold_exports_runnable_bridge_shape() -> None:
    scaffold = build_public_mcp_adapter_scaffold(base_url="https://api.nexa.test")

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

    assert isinstance(manifest, PublicMcpManifest)
    assert not hasattr(manifest, "manifest_version")
    assert not hasattr(manifest, "schema_version")
    assert manifest.server_name == "nexa-phase92"
    assert manifest.server_title == "Nexa Phase 9.2"
    assert manifest.base_url == "https://api.nexa.test"
    assert manifest.resource_uri_prefix == "nexa://phase92"
    assert any(tool.route_name == "launch_run" for tool in manifest.tools)
    assert any(resource.uri_template == "nexa://phase92/api/runs/{run_id}" for resource in manifest.resources)
    assert manifest_dict["server"]["name"] == "nexa-phase92"
    assert "argument-schema" in manifest_dict["compatibility_policy"]["supported_contract_markers"]
    assert "execution-report" in manifest_dict["compatibility_policy"]["supported_runtime_markers"]
    assert manifest_dict["tools"][0]["request_type"] is None or "module" in manifest_dict["tools"][0]["request_type"]
    checkout_manifest = next(tool for tool in manifest.tools if tool.route_name == "checkout_workspace_shell")
    assert checkout_manifest.argument_schema is not None
    assert [field.name for field in checkout_manifest.argument_schema.body_fields] == ["working_save_id", "share_id"]
    assert checkout_manifest.lifecycle_control_profile is not None
    assert checkout_manifest.lifecycle_control_profile.source_resource_names == (
        "get_public_share",
        "get_public_share_history",
        "get_public_share_artifact",
    )
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
    checkout_schema = scaffold.export_tool_schema("checkout_workspace_shell")
    assert [field.name for field in checkout_schema.body_fields] == ["working_save_id", "share_id"]
    create_workspace_schema = scaffold.export_tool_schema("create_workspace")
    assert [field.name for field in create_workspace_schema.body_fields] == ["title", "description"]
    provider_probe_schema = scaffold.export_tool_schema("probe_workspace_provider")
    assert [field.name for field in provider_probe_schema.path_fields] == ["workspace_id", "provider_key"]
    onboarding_schema = scaffold.export_tool_schema("put_onboarding")
    assert [field.name for field in onboarding_schema.body_fields][-1] == "current_step"
    history_summary_schema = scaffold.export_resource_schema("get_history_summary")
    result_history_schema = scaffold.export_resource_schema("get_workspace_result_history")
    feedback_schema = scaffold.export_tool_schema("submit_workspace_feedback")
    assert [field.name for field in history_summary_schema.query_fields] == ["workspace_id"]
    assert [field.name for field in result_history_schema.path_fields] == ["workspace_id"]
    assert [field.name for field in result_history_schema.query_fields] == ["run_id", "app_language"]
    assert [field.name for field in feedback_schema.body_fields] == ["category", "surface", "message", "run_id"]
    launch_manifest = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    assert launch_manifest.argument_schema is not None
    assert launch_manifest.argument_schema.to_dict()["body_fields"][0]["name"] == "workspace_id"
    manifest_dict = manifest.to_dict()
    manifest_tool = next(tool for tool in manifest_dict["tools"] if tool["route_name"] == "launch_run")
    assert manifest_tool["argument_schema"]["body_fields"][1]["name"] == "execution_target"


def test_build_public_mcp_host_bridge_scaffold_builds_framework_and_http_requests() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

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


def test_build_public_mcp_host_bridge_scaffold_normalizes_share_sourced_checkout_arguments() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

    request = bridge.build_framework_tool_request_from_arguments(
        "checkout_workspace_shell",
        {
            "workspace_id": "ws-1",
            "working_save_id": "ws-reopened-1",
            "share_id": "share-1",
        },
    )

    assert request.method == "POST"
    assert request.path == "/api/workspaces/ws-1/shell/checkout"
    assert request.path_params == {"workspace_id": "ws-1"}
    assert request.json_body == {"working_save_id": "ws-reopened-1", "share_id": "share-1"}




def test_build_public_mcp_host_bridge_scaffold_normalizes_workspace_feedback_arguments() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

    request = bridge.build_framework_tool_request_from_arguments(
        "submit_workspace_feedback",
        {
            "workspace_id": "ws-1",
            "category": "friction_note",
            "surface": "workspace_shell",
            "message": "The first-run guidance is still too dense.",
            "run_id": "run-1",
        },
    )

    assert request.method == "POST"
    assert request.path == "/api/workspaces/ws-1/feedback"
    assert request.path_params == {"workspace_id": "ws-1"}
    assert request.json_body == {
        "category": "friction_note",
        "surface": "workspace_shell",
        "message": "The first-run guidance is still too dense.",
        "run_id": "run-1",
    }

def test_build_public_mcp_host_bridge_scaffold_normalizes_workspace_bootstrap_arguments() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

    create_request = bridge.build_framework_tool_request_from_arguments(
        "create_workspace",
        {"title": "Alpha Workspace", "description": "Initial bootstrap workspace"},
    )
    probe_request = bridge.build_framework_tool_request_from_arguments(
        "probe_workspace_provider",
        {
            "workspace_id": "ws-1",
            "provider_key": "openai",
            "model_ref": "gpt-5",
            "timeout_ms": 2000,
        },
    )
    onboarding_request = bridge.build_framework_tool_request_from_arguments(
        "put_onboarding",
        {
            "workspace_id": "ws-1",
            "first_success_achieved": True,
            "advanced_surfaces_unlocked": True,
            "current_step": "completed",
        },
    )

    assert create_request.path == "/api/workspaces"
    assert create_request.json_body == {"title": "Alpha Workspace", "description": "Initial bootstrap workspace"}
    assert probe_request.path == "/api/workspaces/ws-1/provider-bindings/openai/probe"
    assert probe_request.json_body == {"model_ref": "gpt-5", "timeout_ms": 2000}
    assert onboarding_request.path == "/api/users/me/onboarding"
    assert onboarding_request.json_body["current_step"] == "completed"


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

    create_dispatch = bridge.build_framework_tool_dispatch(
        "create_workspace",
        {"title": "Alpha Workspace"},
    )
    onboarding_dispatch = bridge.build_framework_tool_dispatch(
        "put_onboarding",
        {"workspace_id": "ws-1", "current_step": "designer", "advanced_surfaces_unlocked": False},
    )

    assert create_dispatch.handler_name == "handle_create_workspace"
    assert create_dispatch.request.path == "/api/workspaces"
    assert onboarding_dispatch.handler_name == "handle_put_onboarding"
    assert onboarding_dispatch.request.path == "/api/users/me/onboarding"

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


def test_adapter_scaffold_exports_route_family_standardized_schemas() -> None:
    scaffold = build_public_mcp_adapter_scaffold()

    workspace_schema = scaffold.export_resource_schema("get_workspace")
    list_workspaces_schema = scaffold.export_resource_schema("list_workspaces")
    recent_activity_schema = scaffold.export_resource_schema("get_recent_activity")
    run_list_schema = scaffold.export_resource_schema("list_workspace_runs")

    assert workspace_schema is not None
    assert [field.name for field in workspace_schema.path_fields] == ["workspace_id"]
    assert list_workspaces_schema is not None
    assert list_workspaces_schema.path_fields == ()
    assert list_workspaces_schema.query_fields == ()
    assert recent_activity_schema is not None
    assert [field.name for field in recent_activity_schema.query_fields] == ["workspace_id", "limit", "cursor"]
    assert run_list_schema is not None
    assert [field.name for field in run_list_schema.query_fields] == ["limit", "cursor", "status_family", "requested_by_user_id"]


def test_build_public_mcp_argument_schemas_returns_curated_contract_set() -> None:
    schemas = build_public_mcp_argument_schemas()
    indexed = {schema.route_name: schema for schema in schemas}

    assert indexed["get_workspace"].path_fields[0].name == "workspace_id"
    assert indexed["list_workspaces"].route_name == "list_workspaces"
    assert indexed["get_recent_activity"].query_fields[1].name == "limit"
    assert [field.name for field in indexed["checkout_workspace_shell"].body_fields] == ["working_save_id", "share_id"]


def test_build_public_mcp_compatibility_policy_exports_supported_markers() -> None:
    policy = build_public_mcp_compatibility_policy()

    assert isinstance(policy, PublicMcpCompatibilityPolicy)
    assert "argument-schema" in policy.supported_contract_markers
    assert "execution-report" in policy.supported_runtime_markers
    assert "http-route-bridge" in policy.supported_transport_kinds
    policy.assert_supported(
        required_contract_markers=("argument-schema",),
        required_runtime_markers=("execution-report",),
        transport_kind="http-route-bridge",
    )


def test_build_public_mcp_compatibility_policy_rejects_unsupported_markers() -> None:
    policy = build_public_mcp_compatibility_policy()

    try:
        policy.assert_supported(required_contract_markers=("missing-contract",))
    except ValueError as exc:
        assert "Unsupported public MCP contract markers" in str(exc)
    else:
        raise AssertionError("Expected unsupported contract marker rejection")

    try:
        policy.assert_supported(required_runtime_markers=("missing-runtime",))
    except ValueError as exc:
        assert "Unsupported public MCP runtime markers" in str(exc)
    else:
        raise AssertionError("Expected unsupported runtime marker rejection")

    try:
        policy.assert_supported(transport_kind="missing-transport")
    except ValueError as exc:
        assert "Unsupported public MCP transport kind" in str(exc)
    else:
        raise AssertionError("Expected unsupported transport kind rejection")


def test_host_bridge_exposes_and_enforces_compatibility_policy() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    export = bridge.export()

    assert "framework-bridge" in export.compatibility_policy.supported_transport_kinds
    bridge.assert_consumer_compatibility(required_contract_markers=("argument-schema",), required_runtime_markers=("execution-report",), transport_kind="framework-bridge")

    try:
        bridge.assert_consumer_compatibility(required_contract_markers=("missing-contract",))
    except ValueError as exc:
        assert "Unsupported public MCP contract markers" in str(exc)
    else:
        raise AssertionError("Expected bridge manifest compatibility rejection")


def test_build_public_mcp_route_contracts_exports_transport_profiles() -> None:
    contracts = build_public_mcp_route_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert isinstance(indexed["launch_run"], PublicMcpRouteContract)
    assert indexed["launch_run"].transport_profile == "body-only"
    assert indexed["launch_workspace_shell"].transport_profile == "path-and-body"
    assert indexed["get_run_status"].transport_profile == "path-and-query"
    assert indexed["get_recent_activity"].transport_profile == "query-only"
    assert indexed["list_workspaces"].transport_profile == "no-arguments"


def test_adapter_scaffold_normalize_arguments_returns_typed_contract_result() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    normalized = adapter.normalize_tool_arguments(
        "launch_workspace_shell",
        {
            "workspace_id": "ws-1",
            "launch_options": {"mode": "standard"},
            "app_language": "ko",
        },
    )

    assert isinstance(normalized, PublicMcpNormalizedArguments)
    assert normalized.route_name == "launch_workspace_shell"
    assert normalized.route_contract.transport_profile == "path-and-body"
    assert normalized.path_params == {"workspace_id": "ws-1"}
    assert normalized.json_body == {"launch_options": {"mode": "standard"}, "app_language": "ko"}


def test_manifest_includes_route_contracts() -> None:
    manifest = build_public_mcp_manifest()
    launch_tool = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    activity_resource = next(resource for resource in manifest.resources if resource.route_name == "get_recent_activity")
    manifest_dict = manifest.to_dict()
    list_workspaces = next(resource for resource in manifest_dict["resources"] if resource["route_name"] == "list_workspaces")

    assert launch_tool.route_contract is not None
    assert launch_tool.route_contract.transport_profile == "body-only"
    assert activity_resource.route_contract is not None
    assert activity_resource.route_contract.transport_profile == "query-only"
    assert list_workspaces["route_contract"]["transport_profile"] == "no-arguments"


def test_build_public_mcp_host_bridge_scaffold_exposes_route_contracts_on_dispatch() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    dispatch = bridge.build_framework_tool_dispatch(
        "launch_run",
        {
            "workspace_id": "ws-1",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-1"},
        },
    )

    assert isinstance(dispatch, PublicMcpFrameworkDispatch)
    assert dispatch.route_contract is not None
    assert dispatch.route_contract.route_family == "run-launch"
    assert dispatch.route_contract.transport_profile == "body-only"


def test_route_contract_rejects_arguments_for_no_arguments_resource() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    try:
        adapter.normalize_resource_arguments("list_workspaces", {"limit": 10})
    except ValueError as exc:
        assert "Unexpected query field" in str(exc) or "does not accept arguments" in str(exc)
    else:
        raise AssertionError("Expected no-arguments route contract validation")


def test_route_contract_rejects_query_params_for_path_only_resource() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    try:
        adapter.normalize_resource_arguments("get_workspace", {"workspace_id": "ws-1", "lang": "ko"})
    except ValueError as exc:
        assert "Unexpected query field" in str(exc) or "does not accept query params" in str(exc)
    else:
        raise AssertionError("Expected path-only route contract validation")


def test_build_public_mcp_result_shape_profiles_exports_family_profiles() -> None:
    profiles = build_public_mcp_result_shape_profiles()

    assert any(isinstance(profile, PublicMcpResultShapeProfile) for profile in profiles)
    assert any(profile.profile_kind == "run-status-detail" and profile.identity_keys == ("run_id",) for profile in profiles)
    assert any(profile.collection_field_name == "runs" and profile.collection_item_identity_keys == ("run_id",) for profile in profiles)


def test_build_public_mcp_response_contracts_exports_curated_success_shapes() -> None:
    contracts = build_public_mcp_response_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert isinstance(indexed["launch_run"], PublicMcpResponseContract)
    assert indexed["launch_run"].response_shape == "accepted"
    assert indexed["launch_run"].success_status_codes == (202,)
    assert indexed["get_run_status"].response_shape == "status"
    assert indexed["get_run_status"].success_status_codes == (200,)
    assert indexed["get_run_status"].result_shape_profile is not None
    assert indexed["get_run_status"].result_shape_profile.identity_keys == ("run_id",)


def test_manifest_includes_response_contracts() -> None:
    manifest = build_public_mcp_manifest()
    launch_tool = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    status_resource = next(resource for resource in manifest.resources if resource.route_name == "get_run_status")
    manifest_dict = manifest.to_dict()
    status_dict = next(resource for resource in manifest_dict["resources"] if resource["route_name"] == "get_run_status")

    assert launch_tool.response_contract is not None
    assert launch_tool.response_contract.success_status_codes == (202,)
    assert status_resource.response_contract is not None
    assert status_resource.response_contract.response_shape == "status"
    assert status_resource.response_contract.result_shape_profile is not None
    assert status_dict["response_contract"]["success_status_codes"] == [200]
    assert status_dict["response_contract"]["result_shape_profile"]["identity_keys"] == ["run_id"]


def test_adapter_scaffold_normalizes_framework_response_against_public_contract() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    normalized = adapter.normalize_framework_resource_response(
        "get_run_status",
        FrameworkOutboundResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body_text='{"run_id": "run-1", "status": "queued"}',
            media_type="application/json",
        ),
    )

    assert isinstance(normalized, PublicMcpNormalizedResponse)
    assert normalized.ok is True
    assert normalized.response_contract.response_shape == "status"
    assert normalized.body["run_id"] == "run-1"


def test_adapter_scaffold_normalizes_http_response_against_public_contract() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    normalized = adapter.normalize_http_tool_response(
        "launch_run",
        HttpRouteResponse(
            status_code=202,
            body={"run_id": "run-1", "status": "queued"},
            headers={"content-type": "application/json"},
        ),
    )

    assert isinstance(normalized, PublicMcpNormalizedResponse)
    assert normalized.ok is True
    assert normalized.response_contract.success_status_codes == (202,)
    assert normalized.body["status"] == "queued"


def test_adapter_scaffold_rejects_unexpected_success_status_for_response_contract() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    try:
        adapter.normalize_http_tool_response(
            "launch_run",
            HttpRouteResponse(
                status_code=200,
                body={"run_id": "run-1"},
                headers={"content-type": "application/json"},
            ),
        )
    except ValueError as exc:
        assert "Unexpected success status code" in str(exc)
    else:
        raise AssertionError("Expected response-contract success status validation")


def test_response_contract_exports_body_kind_and_required_keys() -> None:
    contracts = build_public_mcp_response_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert indexed["get_run_status"].body_kind == "object"
    assert indexed["get_run_status"].required_top_level_keys == ("run_id", "status")
    assert indexed["launch_run"].required_top_level_keys == ("status",)


def test_response_contract_exports_result_shape_profiles() -> None:
    contracts = build_public_mcp_response_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    workspace_runs = indexed["list_workspace_runs"].result_shape_profile
    assert workspace_runs is not None
    assert workspace_runs.collection_field_name == "runs"
    assert workspace_runs.count_field_name == "returned_count"
    assert workspace_runs.collection_item_identity_keys == ("run_id",)


def test_adapter_scaffold_rejects_response_missing_collection_item_identity_key() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    try:
        adapter.normalize_http_resource_response(
            "list_workspace_runs",
            HttpRouteResponse(
                status_code=200,
                body={"workspace_id": "ws-1", "returned_count": 1, "runs": [{"status": "queued"}]},
                headers={"content-type": "application/json"},
            ),
        )
    except ValueError as exc:
        assert "Missing collection item identity keys" in str(exc)
    else:
        raise AssertionError("Expected collection item identity validation")


def test_adapter_scaffold_rejects_response_with_invalid_count_field_type() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    try:
        adapter.normalize_http_resource_response(
            "list_workspaces",
            HttpRouteResponse(
                status_code=200,
                body={"returned_count": "1", "workspaces": [{"workspace_id": "ws-1"}]},
                headers={"content-type": "application/json"},
            ),
        )
    except ValueError as exc:
        assert "must be int" in str(exc)
    else:
        raise AssertionError("Expected count field type validation")


def test_adapter_scaffold_rejects_framework_response_with_wrong_body_kind() -> None:
    adapter = build_public_mcp_adapter_scaffold()

    try:
        adapter.normalize_framework_resource_response(
            "get_run_status",
            FrameworkOutboundResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body_text='["not", "an", "object"]',
                media_type="application/json",
            ),
        )
    except ValueError as exc:
        assert "expected object" in str(exc)
    else:
        raise AssertionError("Expected response body kind validation")


def test_host_bridge_can_execute_framework_resource_and_normalize_response() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    normalized = bridge.execute_framework_resource(
        "get_run_status",
        {"run_id": "run-001"},
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-framework-bridge-1"},
        session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        run_context=_run_context(),
        run_record_row=_run_row(),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-1",
            active_node_label="Node 1",
            progress_percent=20,
            progress_summary="Working",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Node 1 is executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert isinstance(normalized, PublicMcpNormalizedResponse)
    assert normalized.response_contract.response_shape == "status"
    assert normalized.body["run_id"] == "run-001"
    assert normalized.body["status"] == "running"


def test_host_bridge_can_execute_http_resource_and_normalize_response() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    normalized = bridge.execute_http_resource(
        "get_run_status",
        {"run_id": "run-001"},
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-http-bridge-1"},
        session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        run_context=_run_context(),
        run_record_row=_run_row(),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-1",
            active_node_label="Node 1",
            progress_percent=42,
            progress_summary="Running review stage",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Review Bundle is currently executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert isinstance(normalized, PublicMcpNormalizedResponse)
    assert normalized.response_contract.response_shape == "status"
    assert normalized.body["run_id"] == "run-001"
    assert normalized.body["status"] == "running"


def test_host_bridge_framework_resource_normalized_response_includes_lifecycle_state_hint() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    normalized = bridge.execute_framework_resource(
        "get_run_status",
        {"run_id": "run-001"},
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-framework-bridge-2"},
        session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        run_context=_run_context(),
        run_record_row=_run_row(),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-1",
            active_node_label="Node 1",
            progress_percent=35,
            progress_summary="Still running",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Node 1 is executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert isinstance(normalized.lifecycle_state_hint, PublicMcpLifecycleStateHint)
    assert normalized.lifecycle_state_hint.observed_state == "running"
    assert normalized.lifecycle_state_hint.state_family == "running"
    assert normalized.lifecycle_state_hint.terminal is False
    assert "get_run_status" in normalized.lifecycle_state_hint.recommended_followup_route_names
    assert normalized.lifecycle_state_hint.recommended_action == "get_run_status"


def test_host_bridge_framework_resource_report_successfully_tracks_completed_lifecycle() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    report = bridge.execute_framework_resource_report(
        "get_run_status",
        {"run_id": "run-001"},
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-framework-report-1"},
        session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        run_context=_run_context(),
        run_record_row=_run_row(),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-1",
            active_node_label="Node 1",
            progress_percent=20,
            progress_summary="Working",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Node 1 is executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert report.ok is True
    assert report.phase == "completed"
    assert report.transport_kind == "framework"
    assert report.normalized_response is not None
    assert report.normalized_response.body["status"] == "running"
    assert report.error is None


def test_execution_report_includes_lifecycle_state_hint_for_running_status() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    report = bridge.execute_framework_resource_report(
        "get_run_status",
        {"run_id": "run-001"},
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-framework-report-2"},
        session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        run_context=_run_context(),
        run_record_row=_run_row(),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-1",
            active_node_label="Node 1",
            progress_percent=20,
            progress_summary="Working",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Node 1 is executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert report.lifecycle_state_hint is not None
    assert report.lifecycle_state_hint.state_family == "running"
    assert report.lifecycle_state_hint.recommended_action == "get_run_status"
    assert report.to_dict()["lifecycle_state_hint"]["state_family"] == "running"


def test_host_bridge_resource_report_captures_dispatch_build_error_category() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    report = bridge.execute_framework_resource_report("get_run_status", {"include": "summary"})

    assert report.ok is False
    assert report.phase == "dispatch_build"
    assert report.error is not None
    assert report.error.category == "request_contract_error"
    assert report.error.recovery_hint is not None
    assert isinstance(report.error.recovery_hint, PublicMcpRecoveryHint)
    assert report.retryable is False
    assert report.safe_to_retry_same_request is False
    assert report.recommended_action == "fix_request_arguments"
    assert report.error.recovery_hint.recoverability == "caller_fix_required"
    assert "Missing required path field(s) for public MCP export" in report.error.message


def test_host_bridge_framework_dispatch_report_marks_transient_handler_error_as_retryable(monkeypatch) -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    def _raise_timeout(*args, **kwargs):
        raise TimeoutError("framework handler timed out")

    monkeypatch.setattr("src.server.framework_binding.FrameworkRouteBindings.handle_run_status", _raise_timeout)

    report = bridge.execute_framework_resource_report("get_run_status", {"run_id": "run-001"})

    assert report.ok is False
    assert report.phase == "handler_execution"
    assert report.error is not None
    assert report.error.category == "handler_error"
    assert report.error.recovery_hint is not None
    assert report.retryable is True
    assert report.safe_to_retry_same_request is True
    assert report.recommended_action == "retry_same_request"
    assert report.error.recovery_hint.recoverability == "transient_retry_possible"


def test_host_bridge_framework_dispatch_report_captures_response_contract_error() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    dispatch = bridge.build_framework_resource_dispatch("get_run_status", {"run_id": "run-001"})
    strict_contract = replace(
        bridge.adapter_scaffold.export_resource_response_contract("get_run_status"),
        required_top_level_keys=("run_id", "status", "missing"),
    )
    strict_dispatch = PublicMcpFrameworkDispatch(
        name=dispatch.name,
        route_name=dispatch.route_name,
        kind=dispatch.kind,
        handler_name=dispatch.handler_name,
        request=dispatch.request,
        route_contract=dispatch.route_contract,
        response_contract=strict_contract,
    )

    report = bridge.execute_framework_dispatch_report(
        strict_dispatch,
        run_context=_run_context(),
        run_record_row=_run_row(),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-1",
            active_node_label="Node 1",
            progress_percent=20,
            progress_summary="Working",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Node 1 is executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert report.ok is False
    assert report.phase == "response_normalization"
    assert report.error is not None
    assert report.error.category == "response_contract_error"
    assert "Missing required response keys" in report.error.message


def test_host_bridge_http_dispatch_report_captures_binding_error() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    dispatch = PublicMcpHttpDispatch(
        name="broken_resource",
        route_name="missing_http_route",
        kind="resource",
        request=bridge.build_http_resource_request_from_arguments("get_run_status", {"run_id": "run-001"}),
        response_contract=bridge.adapter_scaffold.export_resource_response_contract("get_run_status"),
    )

    report = bridge.execute_http_dispatch_report(dispatch)

    assert report.ok is False
    assert report.phase == "binding_lookup"
    assert report.error is not None
    assert report.error.category == "binding_error"


def test_build_public_mcp_recovery_policies_exports_route_family_retry_profiles() -> None:
    policies = build_public_mcp_recovery_policies()
    indexed = {policy.route_name: policy for policy in policies}

    assert isinstance(indexed["launch_run"], PublicMcpRecoveryPolicy)
    assert indexed["launch_run"].idempotency_class == "launch-non-idempotent"
    assert indexed["launch_run"].safe_to_retry_same_request_on_timeout is False
    assert indexed["launch_run"].timeout_recommended_action == "inspect_launch_outcome_before_retry"
    assert indexed["get_run_status"].idempotency_class == "read-only"
    assert indexed["get_run_status"].safe_to_retry_same_request_on_timeout is True


def test_build_public_mcp_transport_contracts_exports_session_boundary() -> None:
    contracts = build_public_mcp_transport_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert isinstance(indexed["launch_run"], PublicMcpTransportContract)
    assert indexed["launch_run"].session_mode == "recommended-pass-through"
    assert indexed["launch_run"].session_contract is not None
    assert indexed["launch_run"].session_contract.subject_claim_names == ("user_id", "sub", "subject")
    assert indexed["get_run_status"].session_mode == "optional-pass-through"


def test_manifest_includes_transport_contracts() -> None:
    manifest = build_public_mcp_manifest(base_url="https://api.nexa.test")
    launch_tool = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    status_resource = next(resource for resource in manifest.resources if resource.route_name == "get_run_status")
    manifest_dict = manifest.to_dict()
    launch_tool_dict = next(tool for tool in manifest_dict["tools"] if tool["route_name"] == "launch_run")

    assert launch_tool.transport_contract is not None
    assert launch_tool.transport_contract.session_mode == "recommended-pass-through"
    assert status_resource.transport_contract is not None
    assert status_resource.transport_contract.request_id_header_name == "x-request-id"
    assert launch_tool_dict["transport_contract"]["session_contract"]["subject_claim_names"] == ["user_id", "sub", "subject"]


def test_host_bridge_builds_framework_envelope_with_transport_context() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")
    envelope = bridge.build_framework_tool_envelope(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-123", "Accept-Language": "ko"},
        session_claims={"sub": "user-123", "session_id": "sess-1"},
    )

    assert isinstance(envelope, PublicMcpFrameworkEnvelope)
    assert isinstance(envelope.transport_context, PublicMcpTransportContext)
    assert envelope.transport_contract is not None
    assert envelope.transport_context.request_id == "req-123"
    assert envelope.transport_context.language == "ko"
    assert envelope.transport_context.authorization_present is True
    assert envelope.transport_context.session_present is True
    assert envelope.transport_context.session_subject == "user-123"


def test_host_bridge_builds_http_envelope_with_transport_context() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")
    envelope = bridge.build_http_resource_envelope(
        "get_run_status",
        {"run_id": "run-1", "include": "summary"},
        headers={"X-Request-Id": "req-456"},
        session_claims={"user_id": "user-456"},
    )

    assert isinstance(envelope, PublicMcpHttpEnvelope)
    assert envelope.transport_context.request_id == "req-456"
    assert envelope.transport_context.session_subject == "user-456"
    assert envelope.dispatch.request.path == "/api/runs/run-1"


def test_host_bridge_assesses_transport_context_for_mutating_route() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")
    assessment = bridge.assess_tool_transport_context(
        "launch_run",
        headers={"X-Request-Id": "req-999"},
    )

    assert isinstance(assessment, PublicMcpTransportAssessment)
    assert assessment.ok is False
    assert "missing_authorization_header" in assessment.warnings
    assert "missing_session_claims" in assessment.warnings
    assert "forward_authorization_header" in assessment.suggested_actions
    assert "forward_identity_context" in assessment.suggested_actions


def test_host_bridge_transport_context_rejects_non_string_session_claim_keys() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    try:
        bridge.normalize_transport_context(
            name="get_run_status",
            route_name="get_run_status",
            kind="resource",
            session_claims={1: "bad-key"},  # type: ignore[dict-item]
        )
    except ValueError as exc:
        assert "session_claims" in str(exc)
    else:
        raise AssertionError("Expected session_claim key validation")


def test_transport_contract_exports_posture_modes() -> None:
    contracts = build_public_mcp_transport_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert indexed["launch_run"].request_id_mode == "recommended"
    assert indexed["launch_run"].authorization_mode == "recommended-pass-through"
    assert indexed["launch_run"].session_subject_mode == "recommended-pass-through"
    assert indexed["get_run_status"].authorization_mode == "optional-pass-through"


def test_manifest_includes_recovery_policies() -> None:
    manifest = build_public_mcp_manifest(base_url="https://api.nexa.test")
    launch_tool = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    status_resource = next(resource for resource in manifest.resources if resource.route_name == "get_run_status")
    manifest_dict = manifest.to_dict()
    launch_tool_dict = next(tool for tool in manifest_dict["tools"] if tool["route_name"] == "launch_run")

    assert launch_tool.recovery_policy is not None
    assert launch_tool.recovery_policy.idempotency_class == "launch-non-idempotent"
    assert status_resource.recovery_policy is not None
    assert status_resource.recovery_policy.safe_to_retry_same_request_on_timeout is True
    assert launch_tool_dict["recovery_policy"]["timeout_recommended_action"] == "inspect_launch_outcome_before_retry"


def test_build_public_mcp_lifecycle_control_profiles_exports_curated_followups() -> None:
    profiles = build_public_mcp_lifecycle_control_profiles()
    indexed = {(profile.kind, profile.route_name): profile for profile in profiles}

    launch_profile = indexed[("tool", "launch_run")]
    status_profile = indexed[("resource", "get_run_status")]

    assert isinstance(launch_profile, PublicMcpLifecycleControlProfile)
    assert launch_profile.lifecycle_class == "run-entry"
    assert launch_profile.status_resource_name == "get_run_status"
    assert "get_run_actions" in launch_profile.followup_route_names
    assert "retry_run" in launch_profile.preferred_control_tool_names
    assert status_profile.lifecycle_class == "run-read"
    assert status_profile.result_resource_name == "get_run_result"
    checkout_profile = indexed[("tool", "checkout_workspace_shell")]
    assert checkout_profile.source_resource_names == (
        "get_public_share",
        "get_public_share_history",
        "get_public_share_artifact",
    )
    assert "get_workspace" in checkout_profile.followup_route_names


def test_manifest_includes_lifecycle_control_profiles() -> None:
    manifest = build_public_mcp_manifest(base_url="https://api.nexa.test")
    launch_tool = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    launch_tool_dict = next(tool for tool in manifest.to_dict()["tools"] if tool["route_name"] == "launch_run")

    assert launch_tool.lifecycle_control_profile is not None
    assert launch_tool.lifecycle_control_profile.lifecycle_class == "run-entry"
    assert launch_tool.lifecycle_control_profile.status_resource_name == "get_run_status"
    assert "get_run_result" in launch_tool.lifecycle_control_profile.followup_route_names
    assert launch_tool_dict["lifecycle_control_profile"]["preferred_control_tool_names"] == ["retry_run", "force_reset_run", "mark_run_reviewed"]
    checkout_tool = next(tool for tool in manifest.tools if tool.route_name == "checkout_workspace_shell")
    assert checkout_tool.lifecycle_control_profile is not None
    assert checkout_tool.lifecycle_control_profile.source_resource_names == (
        "get_public_share",
        "get_public_share_history",
        "get_public_share_artifact",
    )


def test_host_bridge_framework_tool_report_uses_route_recovery_policy_for_launch_timeout(monkeypatch) -> None:
    bridge = build_public_mcp_host_bridge_scaffold()

    def _raise_timeout(*args, **kwargs):
        raise TimeoutError("launch handler timed out")

    monkeypatch.setattr("src.server.framework_binding.FrameworkRouteBindings.handle_launch", _raise_timeout)

    report = bridge.execute_framework_tool_report(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
    )

    assert report.ok is False
    assert report.phase == "handler_execution"
    assert report.error is not None
    assert report.error.category == "handler_error"
    assert report.error.recovery_hint is not None
    assert report.retryable is True
    assert report.safe_to_retry_same_request is False
    assert report.recommended_action == "inspect_launch_outcome_before_retry"
    assert report.error.recovery_hint.recoverability == "manual_verification_before_retry"


def test_execution_report_includes_transport_assessment_for_launch_run() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    report = bridge.execute_framework_tool_report(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"X-Request-Id": "req-111"},
    )

    assert report.transport_context is not None
    assert report.transport_assessment is not None
    assert report.transport_assessment.ok is False
    assert report.transport_context.request_id == "req-111"
    assert "missing_authorization_header" in report.transport_assessment.warnings
    assert "missing_identity_context" in report.transport_assessment.warnings




def test_framework_tool_envelope_includes_preflight_assessment() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    envelope = bridge.build_framework_tool_envelope(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"X-Request-Id": "req-100"},
    )

    assert isinstance(envelope.preflight_assessment, PublicMcpPreflightAssessment)
    assert envelope.preflight_assessment.ready is True
    assert envelope.preflight_assessment.risk_level == "high"
    assert "non_idempotent_route_family" in envelope.preflight_assessment.warnings
    assert "missing_identity_context_for_mutation_route" in envelope.preflight_assessment.warnings
    assert "attach_identity_context_before_execution" in envelope.preflight_assessment.suggested_actions


def test_preflight_framework_resource_low_risk_with_full_transport_context() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    preflight = bridge.preflight_framework_resource(
        "get_run_status",
        {"run_id": "run-001"},
        headers={"X-Request-Id": "req-200", "Accept-Language": "ko"},
    )

    assert preflight.ready is True
    assert preflight.risk_level == "low"
    assert preflight.warnings == ()


def test_execution_report_includes_preflight_assessment_for_launch_run() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    report = bridge.execute_framework_tool_report(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"X-Request-Id": "req-111"},
    )

    assert report.preflight_assessment is not None
    assert report.preflight_assessment.risk_level == "high"
    assert "attach_identity_context_before_execution" in report.preflight_assessment.suggested_actions
    assert report.to_dict()["preflight_assessment"]["risk_level"] == "high"


def test_framework_tool_envelope_includes_orchestration_summary() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    envelope = bridge.build_framework_tool_envelope(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"X-Request-Id": "req-300"},
    )

    assert isinstance(envelope.orchestration_summary, PublicMcpOrchestrationSummary)
    assert envelope.orchestration_summary.route_family == "run-launch"
    assert envelope.orchestration_summary.idempotency_class == "launch-non-idempotent"
    assert envelope.orchestration_summary.ready is True
    assert envelope.orchestration_summary.risk_level == "high"
    assert envelope.orchestration_summary.authorization_present is False
    assert envelope.orchestration_summary.session_subject_present is False
    assert "run-launch" in envelope.orchestration_summary.summary_labels
    assert "risk:high" in envelope.orchestration_summary.summary_labels
    assert "attach_authorization_before_execution" in envelope.orchestration_summary.next_actions
    assert envelope.orchestration_summary.to_dict()["ready"] is True


def test_execution_report_includes_orchestration_summary_for_launch_run() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    report = bridge.execute_framework_tool_report(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"X-Request-Id": "req-301"},
    )

    assert report.orchestration_summary is not None
    assert report.orchestration_summary.route_family == "run-launch"
    assert report.orchestration_summary.recommended_action == "attach_identity_context_before_execution"
    assert "attach_authorization_before_execution" in report.orchestration_summary.next_actions
    assert report.to_dict()["orchestration_summary"]["risk_level"] == "high"


def test_summarize_framework_resource_orchestration_returns_low_risk_read_profile() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    summary = bridge.summarize_framework_resource_orchestration(
        "get_run_status",
        {"run_id": "run-001"},
        headers={"X-Request-Id": "req-302", "Accept-Language": "ko"},
    )

    assert isinstance(summary, PublicMcpOrchestrationSummary)
    assert summary.route_family == "run-read"
    assert summary.risk_level == "low"
    assert summary.ready is True
    assert summary.authorization_present is False
    assert summary.lifecycle_control_profile is not None
    assert summary.lifecycle_control_profile.status_resource_name == "get_run_status"
    assert "get_run_result" in summary.next_actions


def test_framework_tool_envelope_includes_lifecycle_control_profile() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    envelope = bridge.build_framework_tool_envelope(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"X-Request-Id": "req-400"},
    )

    assert envelope.lifecycle_control_profile is not None
    assert envelope.lifecycle_control_profile.lifecycle_class == "run-entry"
    assert envelope.lifecycle_control_profile.status_resource_name == "get_run_status"
    assert envelope.orchestration_summary.lifecycle_control_profile is not None
    assert "get_run_status" in envelope.orchestration_summary.next_actions
    assert "retry_run" in envelope.orchestration_summary.next_actions


def test_execution_report_includes_lifecycle_control_profile() -> None:
    bridge = build_public_mcp_host_bridge_scaffold()
    report = bridge.execute_framework_tool_report(
        "launch_run",
        {
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-001"},
        },
        headers={"X-Request-Id": "req-401"},
    )

    assert report.lifecycle_control_profile is not None
    assert report.lifecycle_control_profile.lifecycle_class == "run-entry"
    assert report.lifecycle_control_profile.review_tool_name == "mark_run_reviewed"
    assert report.to_dict()["lifecycle_control_profile"]["status_resource_name"] == "get_run_status"


def test_build_public_mcp_surface_includes_public_share_resources_and_tools() -> None:
    tools = {tool.route_name for tool in build_public_mcp_tools()}
    resources = {resource.route_name for resource in build_public_mcp_resources()}

    assert "put_workspace_shell_draft" in tools
    assert "create_workspace_shell_share" in tools
    assert "extend_public_share" in tools
    assert "revoke_public_share" in tools
    assert "archive_public_share" in tools
    assert "delete_public_share" in tools
    assert "get_workspace_shell" in resources
    assert "get_public_share" in resources
    assert "get_public_share_history" in resources
    assert "get_public_share_artifact" in resources


def test_build_public_mcp_host_bridge_scaffold_dispatches_public_share_routes() -> None:
    bridge = build_public_mcp_host_bridge_scaffold(base_url="https://api.nexa.test")

    shell_dispatch = bridge.build_framework_resource_dispatch(
        "get_workspace_shell",
        {"workspace_id": "ws-1"},
    )
    draft_dispatch = bridge.build_framework_tool_dispatch(
        "put_workspace_shell_draft",
        {"workspace_id": "ws-1", "request_text": "Help me improve this shell."},
    )
    create_dispatch = bridge.build_framework_tool_dispatch(
        "create_workspace_shell_share",
        {"workspace_id": "ws-1", "title": "Public Share"},
    )
    share_dispatch = bridge.build_framework_resource_dispatch(
        "get_public_share",
        {"share_id": "share-1"},
    )
    history_dispatch = bridge.build_http_resource_dispatch(
        "get_public_share_history",
        {"share_id": "share-1"},
    )
    artifact_dispatch = bridge.build_http_resource_dispatch(
        "get_public_share_artifact",
        {"share_id": "share-1"},
    )

    assert shell_dispatch.handler_name == "handle_workspace_shell"
    assert shell_dispatch.request.path == "/api/workspaces/ws-1/shell"

    assert draft_dispatch.handler_name == "handle_put_workspace_shell_draft"
    assert draft_dispatch.request.path == "/api/workspaces/ws-1/shell/draft"
    assert draft_dispatch.request.json_body == {"request_text": "Help me improve this shell."}

    assert create_dispatch.handler_name == "handle_create_workspace_shell_share"
    assert create_dispatch.request.path == "/api/workspaces/ws-1/shell/share"
    assert create_dispatch.request.json_body == {"title": "Public Share"}

    assert share_dispatch.handler_name == "handle_get_public_share"
    assert share_dispatch.request.path == "/api/public-shares/share-1"

    assert history_dispatch.request.method == "GET"
    assert history_dispatch.request.path == "/api/public-shares/share-1/history"

    assert artifact_dispatch.request.method == "GET"
    assert artifact_dispatch.request.path == "/api/public-shares/share-1/artifact"


def test_build_public_mcp_contracts_include_public_share_route_families() -> None:
    route_contracts = {contract.route_name: contract for contract in build_public_mcp_route_contracts()}
    responses = {contract.route_name: contract for contract in build_public_mcp_response_contracts()}
    lifecycles = {(profile.kind, profile.route_name): profile for profile in build_public_mcp_lifecycle_control_profiles()}

    assert route_contracts["get_workspace_shell"].route_family == "workspace-shell-read"
    assert route_contracts["put_workspace_shell_draft"].route_family == "workspace-shell-draft-write"
    assert route_contracts["create_workspace_shell_share"].route_family == "public-share-create"
    assert route_contracts["get_public_share"].route_family == "public-share-read"
    assert route_contracts["get_public_share_history"].route_family == "public-share-history"
    assert route_contracts["get_public_share_artifact"].route_family == "public-share-artifact"
    assert route_contracts["extend_public_share"].route_family == "public-share-management"

    assert responses["get_workspace_shell"].required_top_level_keys == ("workspace_id", "storage_role", "action_availability", "shell", "routes")
    assert responses["put_workspace_shell_draft"].required_top_level_keys == ("workspace_id", "storage_role", "action_availability", "shell", "routes")
    assert responses["create_workspace_shell_share"].success_status_codes == (201,)
    assert responses["get_public_share_history"].required_top_level_keys == ("share_id", "history")

    assert lifecycles[("resource", "get_workspace_shell")].status_resource_name == "get_workspace_shell"
    assert "commit_workspace_shell" in lifecycles[("resource", "get_workspace_shell")].followup_route_names
    assert lifecycles[("tool", "put_workspace_shell_draft")].status_resource_name == "get_workspace_shell"
    assert lifecycles[("tool", "create_workspace_shell_share")].status_resource_name == "get_public_share"
    assert "get_public_share_artifact" in lifecycles[("resource", "get_public_share")].followup_route_names
    assert lifecycles[("tool", "checkout_workspace_shell")].source_resource_names == (
        "get_public_share",
        "get_public_share_history",
        "get_public_share_artifact",
    )
