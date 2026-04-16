from __future__ import annotations

from src import sdk
from src.sdk import artifacts, server
from src.sdk.artifacts import (
    COMMIT_SNAPSHOT_ROLE,
    WORKING_SAVE_ROLE,
    CircuitModel,
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitValidationModel,
    ResourcesModel,
    RuntimeModel,
    StateModel,
    UIModel,
    WorkingSaveMeta,
    WorkingSaveModel,
    create_commit_snapshot_from_working_save,
    create_working_save_from_commit_snapshot,
)
from src.server.framework_binding_models import FrameworkOutboundResponse

from src.sdk.server import (
    ProductExecutionTarget,
    ProductOnboardingReadResponse,
    ProductHistorySummaryResponse,
    ProductCircuitLibraryResponse,
    ProductOnboardingWriteAcceptedResponse,
    ProductOnboardingWriteRequest,
    ProductProviderBindingWriteAcceptedResponse,
    ProductProviderBindingWriteRequest,
    ProductProviderCatalogResponse,
    ProductProviderHealthDetailResponse,
    ProductProviderProbeHistoryResponse,
    ProductProviderProbeRequest,
    ProductProviderProbeResponse,
    ProductWorkspaceCreateRequest,
    ProductWorkspaceProviderBindingsResponse,
    ProductWorkspaceProviderHealthResponse,
    ProductWorkspaceWriteAcceptedResponse,
    ProductIssuerPublicShareActionReportListResponse,
    ProductIssuerPublicShareActionReportSummaryResponse,
    ProductIssuerPublicShareBulkMutationResponse,
    ProductIssuerPublicShareListResponse,
    ProductIssuerPublicShareSummaryResponse,
    ProductLaunchOptions,
    ProductPublicShareArtifactResponse,
    ProductPublicShareDetailResponse,
    ProductPublicShareHistoryResponse,
    ProductPublicShareMutationResponse,
    ProductRunLaunchRequest,
    ProductRunStatusResponse,
    ProductSourceArtifactView,
    ProductWorkspaceRunListResponse,
    ProductWorkspaceResultHistoryResponse,
    ProductWorkspaceFeedbackReadResponse,
    ProductWorkspaceFeedbackWriteRequest,
    ProductWorkspaceFeedbackWriteAcceptedResponse,
    ProductWorkspaceShellRuntimeResponse,
    ProductWorkspaceShellDraftSavedResponse,
    ProductWorkspaceShellCommitResponse,
    ProductWorkspaceShellCheckoutResponse,
    ProductWorkspaceShellLaunchAcceptedResponse,
    ProductWorkspaceShellShareCreatedResponse,
)
from src.server.public_share_models import (
    ProductPublicShareAuditSummaryView,
    ProductPublicShareHistoryEntryView,
    ProductPublicShareLifecycleView,
    ProductPublicShareLinks,
    ProductPublicShareManagementView,
    ProductPublicShareSourceArtifactView,
)
from src.server.workspace_shell_models import (
    ProductWorkspaceShellActionAvailabilityView,
    ProductWorkspaceShellRoutesView,
)
from src.server.run_read_models import ProductExecutionTargetView, ProductRunLinks
from src.server.run_admission_models import ProductRunLaunchLinks


def _working_save_model() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role=WORKING_SAVE_ROLE,
            working_save_id="ws-public-1",
            name="Public Draft",
        ),
        circuit=CircuitModel(
            nodes=[{"id": "node1", "type": "provider"}],
            edges=[],
            entry="node1",
            outputs=[{"name": "result", "source": "node1"}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="validated", validation_summary={"blocking_count": 0}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def test_sdk_root_exposes_curated_public_modules() -> None:
    assert not hasattr(sdk, "PUBLIC_SDK_SURFACE_VERSION")
    assert sdk.PUBLIC_SDK_MODULES == ("artifacts", "server", "integration")
    assert sdk.artifacts is artifacts
    assert sdk.server is server


def test_artifact_sdk_surface_exposes_role_aware_lifecycle_api() -> None:
    working = _working_save_model()

    snapshot = create_commit_snapshot_from_working_save(
        working,
        commit_id="commit-public-1",
    )
    reopened = create_working_save_from_commit_snapshot(
        snapshot,
        working_save_id="ws-public-2",
    )

    assert artifacts.PUBLIC_ARTIFACT_SDK_SURFACE_VERSION == "1.0"
    assert snapshot.meta.storage_role == COMMIT_SNAPSHOT_ROLE
    assert snapshot.meta.commit_id == "commit-public-1"
    assert reopened.meta.storage_role == WORKING_SAVE_ROLE
    assert reopened.meta.working_save_id == "ws-public-2"
    assert snapshot.meta.source_working_save_id == "ws-public-1"


def test_server_sdk_surface_exposes_public_launch_and_read_models() -> None:
    request = ProductRunLaunchRequest(
        workspace_id="ws-1",
        execution_target=ProductExecutionTarget(target_type="working_save", target_ref="working_save:ws-1"),
        launch_options=ProductLaunchOptions(mode="standard", priority="normal", allow_working_save_execution=True),
    )
    source_artifact = ProductSourceArtifactView(
        storage_role=WORKING_SAVE_ROLE,
        canonical_ref="working_save:ws-1",
        working_save_id="ws-1",
    )
    status = ProductRunStatusResponse(
        run_id="run-1",
        workspace_id="ws-1",
        execution_target=ProductExecutionTargetView(target_type="working_save", target_ref="working_save:ws-1"),
        status="queued",
        status_family="pending",
        created_at="2026-04-14T00:00:00Z",
        started_at=None,
        updated_at="2026-04-14T00:00:01Z",
        links=ProductRunLinks(result="/runs/run-1/result", trace="/runs/run-1/trace", artifacts="/runs/run-1/artifacts"),
        source_artifact=source_artifact,
    )

    assert server.PUBLIC_SERVER_SDK_SURFACE_VERSION == "1.0"
    assert request.execution_target.target_type == "working_save"
    assert status.source_artifact is not None
    assert status.source_artifact.canonical_ref == "working_save:ws-1"
    assert ProductWorkspaceRunListResponse is not None
    assert ProductIssuerPublicShareListResponse is not None
    assert ProductIssuerPublicShareSummaryResponse is not None
    assert ProductIssuerPublicShareActionReportListResponse is not None
    assert ProductIssuerPublicShareActionReportSummaryResponse is not None
    assert ProductIssuerPublicShareBulkMutationResponse is not None
    assert ProductWorkspaceCreateRequest is not None
    assert ProductWorkspaceWriteAcceptedResponse is not None
    assert ProductProviderCatalogResponse is not None
    assert ProductWorkspaceProviderBindingsResponse is not None
    assert ProductProviderBindingWriteRequest is not None
    assert ProductProviderBindingWriteAcceptedResponse is not None
    assert ProductWorkspaceProviderHealthResponse is not None
    assert ProductProviderHealthDetailResponse is not None
    assert ProductProviderProbeRequest is not None
    assert ProductProviderProbeResponse is not None
    assert ProductProviderProbeHistoryResponse is not None
    assert ProductOnboardingReadResponse is not None
    assert ProductOnboardingWriteRequest is not None
    assert ProductOnboardingWriteAcceptedResponse is not None
    assert ProductHistorySummaryResponse is not None
    assert ProductCircuitLibraryResponse is not None
    assert ProductWorkspaceResultHistoryResponse is not None
    assert ProductWorkspaceFeedbackReadResponse is not None
    assert ProductWorkspaceFeedbackWriteRequest is not None
    assert ProductWorkspaceFeedbackWriteAcceptedResponse is not None


def test_sdk_root_exposes_public_mcp_manifest_surface() -> None:
    manifest = sdk.build_public_mcp_manifest(base_url="https://api.nexa.test")

    assert not hasattr(sdk, "PUBLIC_MCP_MANIFEST_VERSION")
    assert not hasattr(sdk, "PUBLIC_MCP_SCHEMA_VERSION")
    assert not hasattr(sdk, "PUBLIC_MCP_COMPATIBILITY_POLICY_VERSION")
    assert manifest.server_name == "nexa-public"
    assert any(tool.route_name == "launch_run" for tool in manifest.tools)
    assert any(tool.route_name == "create_workspace" for tool in manifest.tools)
    assert any(tool.route_name == "submit_workspace_feedback" for tool in manifest.tools)
    assert any(resource.route_name == "get_provider_catalog" for resource in manifest.resources)
    assert any(resource.route_name == "get_history_summary" for resource in manifest.resources)
    assert any(resource.route_name == "get_circuit_library" for resource in manifest.resources)
    assert any(resource.route_name == "get_workspace_result_history" for resource in manifest.resources)
    assert any(resource.route_name == "get_workspace_feedback" for resource in manifest.resources)
    launch_manifest = next(tool for tool in manifest.tools if tool.route_name == "launch_run")
    assert launch_manifest.argument_schema is not None
    assert launch_manifest.argument_schema.body_fields[0].name == "workspace_id"


def test_sdk_root_exposes_public_mcp_argument_schema_types() -> None:
    schema = sdk.build_public_mcp_adapter_scaffold().export_tool_schema("launch_run")

    assert isinstance(schema, sdk.PublicMcpArgumentSchema)
    assert isinstance(schema.body_fields[0], sdk.PublicMcpArgumentField)
    assert schema.body_fields[0].name == "workspace_id"


def test_sdk_root_exposes_public_mcp_host_bridge_surface() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    dispatch = bridge.build_framework_resource_dispatch(
        "get_run_status",
        {"run_id": "run-1", "include": "summary"},
    )

    assert not hasattr(sdk, "MCP_HOST_BRIDGE_SCAFFOLD_VERSION")
    assert dispatch.request.path == "/api/runs/run-1"
    assert dispatch.request.query_params == {"include": "summary"}
    assert dispatch.handler_name == "handle_run_status"
    assert any(binding.route_name == "get_run_status" for binding in bridge.export().resource_bindings)


def test_sdk_root_exposes_public_mcp_argument_schema_catalog() -> None:
    schemas = sdk.build_public_mcp_argument_schemas()
    indexed = {schema.route_name: schema for schema in schemas}

    assert indexed["get_workspace"].path_fields[0].name == "workspace_id"
    assert indexed["create_workspace"].body_fields[0].name == "title"
    assert indexed["put_workspace_provider_binding"].path_fields[1].name == "provider_key"
    assert indexed["put_onboarding"].body_fields[-1].name == "current_step"
    assert indexed["get_history_summary"].query_fields[0].name == "workspace_id"
    assert indexed["get_workspace_result_history"].path_fields[0].name == "workspace_id"
    assert [field.name for field in indexed["submit_workspace_feedback"].body_fields] == ["category", "surface", "message", "run_id"]
    assert indexed["list_workspaces"].route_name == "list_workspaces"


def test_sdk_root_exposes_public_mcp_compatibility_policy() -> None:
    policy = sdk.build_public_mcp_compatibility_policy()

    assert isinstance(policy, sdk.PublicMcpCompatibilityPolicy)
    assert "argument-schema" in policy.supported_contract_markers
    assert "execution-report" in policy.supported_runtime_markers
    policy.assert_supported(required_contract_markers=("argument-schema",), required_runtime_markers=("execution-report",), transport_kind="http-route-bridge")


def test_sdk_root_exposes_public_mcp_lifecycle_control_profiles() -> None:
    profiles = sdk.build_public_mcp_lifecycle_control_profiles()
    indexed = {(profile.kind, profile.route_name): profile for profile in profiles}

    assert isinstance(indexed[("tool", "launch_run")], sdk.PublicMcpLifecycleControlProfile)
    assert indexed[("tool", "launch_run")].status_resource_name == "get_run_status"
    assert "retry_run" in indexed[("tool", "launch_run")].preferred_control_tool_names
    assert indexed[("resource", "get_run_status")].result_resource_name == "get_run_result"
    assert indexed[("tool", "create_workspace")].status_resource_name == "get_workspace"
    assert indexed[("tool", "probe_workspace_provider")].result_resource_name == "list_provider_probe_history"
    assert indexed[("resource", "get_onboarding")].status_resource_name == "get_onboarding"


def test_sdk_root_exposes_public_mcp_transport_contracts() -> None:
    contracts = sdk.build_public_mcp_transport_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert isinstance(indexed["launch_run"], sdk.PublicMcpTransportContract)
    assert isinstance(indexed["launch_run"].session_contract, sdk.PublicMcpSessionContract)
    assert indexed["launch_run"].session_mode == "recommended-pass-through"
    assert indexed["get_run_status"].session_mode == "optional-pass-through"
    assert indexed["create_workspace"].session_mode == "recommended-pass-through"
    assert indexed["put_workspace_provider_binding"].session_mode == "recommended-pass-through"
    assert indexed["put_onboarding"].session_mode == "recommended-pass-through"


def test_sdk_root_exposes_public_mcp_transport_envelopes() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    envelope = bridge.build_framework_resource_envelope(
        "get_run_status",
        {"run_id": "run-1"},
        headers={"X-Request-Id": "req-789"},
        session_claims={"sub": "user-789"},
    )

    assert isinstance(envelope, sdk.PublicMcpFrameworkEnvelope)
    assert isinstance(envelope.transport_context, sdk.PublicMcpTransportContext)
    assert envelope.transport_context.request_id == "req-789"
    assert envelope.transport_context.session_subject == "user-789"
    assert envelope.lifecycle_control_profile is not None
    assert envelope.lifecycle_control_profile.status_resource_name == "get_run_status"


def test_sdk_root_exposes_public_mcp_transport_assessment() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    assessment = bridge.assess_tool_transport_context(
        "launch_run",
        headers={"X-Request-Id": "req-321"},
    )

    assert isinstance(assessment, sdk.PublicMcpTransportAssessment)
    assert assessment.ok is False
    assert "missing_authorization_header" in assessment.warnings
    assert "missing_identity_context" in assessment.warnings
    assert "forward_identity_context" in assessment.suggested_actions


def test_sdk_root_exposes_public_mcp_route_contracts() -> None:
    contracts = sdk.build_public_mcp_route_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert isinstance(indexed["launch_run"], sdk.PublicMcpRouteContract)
    assert indexed["launch_run"].transport_profile == "body-only"
    assert indexed["list_workspaces"].transport_profile == "no-arguments"
    assert indexed["create_workspace"].transport_profile == "body-only"
    assert indexed["get_provider_catalog"].transport_profile == "no-arguments"
    assert indexed["put_onboarding"].transport_profile == "body-only"


def test_sdk_root_exposes_typed_normalized_arguments() -> None:
    normalized = sdk.build_public_mcp_adapter_scaffold().normalize_resource_arguments(
        "get_recent_activity",
        {"workspace_id": "ws-1", "limit": 5},
    )

    assert isinstance(normalized, sdk.PublicMcpNormalizedArguments)
    assert normalized.route_contract.route_family == "activity-read"
    assert normalized.query_params == {"workspace_id": "ws-1", "limit": "5"}
    assert normalized.json_body is None


def test_sdk_root_exposes_public_mcp_response_contracts() -> None:
    contracts = sdk.build_public_mcp_response_contracts()
    indexed = {contract.route_name: contract for contract in contracts}

    assert isinstance(indexed["launch_run"], sdk.PublicMcpResponseContract)
    assert indexed["launch_run"].success_status_codes == (202,)
    assert indexed["get_run_status"].response_shape == "status"
    assert indexed["create_workspace"].response_shape == "workspace-created"
    assert indexed["get_provider_catalog"].response_shape == "provider-catalog"
    assert indexed["put_onboarding"].response_shape == "onboarding-write"


def test_sdk_root_exposes_public_mcp_normalized_response() -> None:
    normalized = sdk.build_public_mcp_adapter_scaffold().normalize_framework_resource_response(
        "get_run_status",
        FrameworkOutboundResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body_text='{"run_id": "run-1", "status": "queued"}',
            media_type="application/json",
        ),
    )

    assert isinstance(normalized, sdk.PublicMcpNormalizedResponse)
    assert normalized.response_contract.route_family == "run-read"
    assert normalized.body["status"] == "queued"


def test_sdk_root_exposes_public_mcp_execution_report_types() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    report = bridge.execute_framework_resource_report("get_run_status", {"include": "summary"})

    assert isinstance(report, sdk.PublicMcpExecutionReport)
    assert isinstance(report.error, sdk.PublicMcpExecutionError)
    assert isinstance(report.error.recovery_hint, sdk.PublicMcpRecoveryHint)
    assert report.phase == "dispatch_build"
    assert report.error.category == "request_contract_error"
    assert report.retryable is False
    assert report.lifecycle_control_profile is None or report.lifecycle_control_profile.status_resource_name == "get_run_status"
    assert report.recommended_action == "fix_request_arguments"


def test_sdk_root_execution_report_includes_transport_assessment() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    report = bridge.execute_framework_tool_report(
        "launch_run",
        {
            "workspace_id": "ws-1",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-1"},
        },
        headers={"X-Request-Id": "req-555"},
    )

    assert report.transport_context is not None
    assert report.transport_assessment is not None
    assert report.transport_assessment.ok is False
    assert "missing_authorization_header" in report.transport_assessment.warnings


def test_sdk_root_exposes_public_mcp_recovery_policies() -> None:
    policies = sdk.build_public_mcp_recovery_policies()
    indexed = {policy.route_name: policy for policy in policies}

    assert isinstance(indexed["launch_run"], sdk.PublicMcpRecoveryPolicy)
    assert indexed["launch_run"].timeout_recommended_action == "inspect_launch_outcome_before_retry"
    assert indexed["get_run_status"].safe_to_retry_same_request_on_timeout is True
    assert indexed["create_workspace"].safe_to_retry_same_request_on_timeout is False
    assert indexed["get_provider_catalog"].safe_to_retry_same_request_on_timeout is True
    assert indexed["put_onboarding"].timeout_recommended_action == "inspect_onboarding_state_before_retry"


def test_sdk_root_exposes_public_mcp_preflight_assessment() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    preflight = bridge.preflight_framework_tool(
        "launch_run",
        {
            "workspace_id": "ws-1",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-1"},
        },
        headers={"X-Request-Id": "req-500"},
    )

    assert isinstance(preflight, sdk.PublicMcpPreflightAssessment)
    assert preflight.risk_level == "high"
    assert preflight.ready is True
    assert "non_idempotent_route_family" in preflight.warnings


def test_sdk_root_execution_report_includes_preflight_assessment() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    report = bridge.execute_framework_tool_report(
        "launch_run",
        {
            "workspace_id": "ws-1",
            "execution_target": {"target_type": "working_save", "target_ref": "working_save:ws-1"},
        },
        headers={"X-Request-Id": "req-501"},
    )

    assert isinstance(report.preflight_assessment, sdk.PublicMcpPreflightAssessment)
    assert report.preflight_assessment is not None
    assert report.preflight_assessment.risk_level == "high"


def test_sdk_root_exposes_result_shape_profile_builder() -> None:
    assert hasattr(sdk, "PublicMcpResultShapeProfile")
    assert hasattr(sdk, "build_public_mcp_result_shape_profiles")


def test_server_sdk_surface_exposes_public_share_models() -> None:
    detail = ProductPublicShareDetailResponse(
        status="ready",
        share_id="share-1",
        share_path="https://nexa.test/s/share-1",
        transport="link",
        access_mode="public_read",
        lifecycle=ProductPublicShareLifecycleView(
            stored_state="active",
            state="active",
            created_at="2026-04-16T00:00:00Z",
            updated_at="2026-04-16T00:00:01Z",
        ),
        management=ProductPublicShareManagementView(archived=False),
        audit_summary=ProductPublicShareAuditSummaryView(event_count=1),
        source_artifact=ProductPublicShareSourceArtifactView(
            storage_role="commit_snapshot",
            canonical_ref="commit_snapshot:commit-1",
            artifact_format_family=".nex",
        ),
        share_boundary={"share_family": "public_nex_link_share"},
        artifact_boundary={"format_family": ".nex"},
        links=ProductPublicShareLinks({"self": "/api/public-shares/share-1"}),
    )
    created = ProductWorkspaceShellShareCreatedResponse(
        status="created",
        workspace_id="ws-1",
        share_id="share-1",
        share_path="https://nexa.test/s/share-1",
        transport="link",
        access_mode="public_read",
        lifecycle=detail.lifecycle,
        management=detail.management,
        audit_summary=detail.audit_summary,
        source_artifact=detail.source_artifact,
        share_boundary=detail.share_boundary,
        artifact_boundary=detail.artifact_boundary,
        links=detail.links,
    )
    history = ProductPublicShareHistoryResponse(
        status="ready",
        share_id="share-1",
        share_path="https://nexa.test/s/share-1",
        audit_summary=detail.audit_summary,
        share_boundary=detail.share_boundary,
        artifact_boundary=detail.artifact_boundary,
        history=(
            ProductPublicShareHistoryEntryView(
                event_id="evt-1",
                event_type="created",
                timestamp="2026-04-16T00:00:00Z",
            ),
        ),
        links=detail.links,
    )
    artifact = ProductPublicShareArtifactResponse(
        status="ready",
        share_id="share-1",
        share_title="Share",
        share_boundary=detail.share_boundary,
        artifact_boundary=detail.artifact_boundary,
        artifact={"meta": {"storage_role": "commit_snapshot"}},
        links=detail.links,
    )
    mutation = ProductPublicShareMutationResponse(
        status="updated",
        share_id="share-1",
        share_path="https://nexa.test/s/share-1",
        transport="link",
        access_mode="public_read",
        lifecycle=detail.lifecycle,
        management=detail.management,
        audit_summary=detail.audit_summary,
        source_artifact=detail.source_artifact,
        share_boundary=detail.share_boundary,
        artifact_boundary=detail.artifact_boundary,
        links=detail.links,
        governance_summary={"total_share_count": 1},
    )

    assert server.PUBLIC_SERVER_SDK_SURFACE_VERSION == "1.0"
    assert created.workspace_id == "ws-1"
    assert history.history[0].event_id == "evt-1"
    assert artifact.artifact["meta"]["storage_role"] == "commit_snapshot"
    assert mutation.governance_summary == {"total_share_count": 1}


def test_server_sdk_surface_exposes_workspace_shell_models() -> None:
    runtime = ProductWorkspaceShellRuntimeResponse(
        workspace_id="ws-1",
        workspace_title="Primary Workspace",
        storage_role="working_save",
        action_availability=ProductWorkspaceShellActionAvailabilityView({"launch": {"allowed": True}}),
        shell={"mode": "build"},
        routes=ProductWorkspaceShellRoutesView({"self": "/api/workspaces/ws-1/shell"}),
    )
    draft = ProductWorkspaceShellDraftSavedResponse(
        workspace_id="ws-1",
        storage_role="working_save",
        action_availability=runtime.action_availability,
        shell=runtime.shell,
        routes=runtime.routes,
    )
    commit = ProductWorkspaceShellCommitResponse(
        workspace_id="ws-1",
        storage_role="commit_snapshot",
        action_availability=runtime.action_availability,
        shell=runtime.shell,
        routes=runtime.routes,
        transition={"action": "commit_workspace_shell"},
    )
    checkout = ProductWorkspaceShellCheckoutResponse(
        workspace_id="ws-1",
        storage_role="working_save",
        action_availability=runtime.action_availability,
        shell=runtime.shell,
        routes=runtime.routes,
        transition={"action": "checkout_workspace_shell"},
    )
    launch = ProductWorkspaceShellLaunchAcceptedResponse(
        status="accepted",
        run_id="run-1",
        workspace_id="ws-1",
        execution_target=ProductExecutionTarget(target_type="working_save", target_ref="working_save:ws-1"),
        initial_run_status="queued",
        links=ProductRunLaunchLinks(run_status="/api/runs/run-1", run_result="/api/runs/run-1/result"),
        launch_context={"action": "launch_workspace_shell", "workspace_id": "ws-1"},
    )

    assert runtime.routes.values["self"] == "/api/workspaces/ws-1/shell"
    assert draft.persistence_action == "put_workspace_shell_draft"
    assert commit.transition["action"] == "commit_workspace_shell"
    assert checkout.transition["action"] == "checkout_workspace_shell"
    assert launch.launch_context["action"] == "launch_workspace_shell"


def test_sdk_root_exposes_public_share_mcp_surface() -> None:
    manifest = sdk.build_public_mcp_manifest(base_url="https://api.nexa.test")
    resource_names = {resource.route_name for resource in manifest.resources}
    tool_names = {tool.route_name for tool in manifest.tools}

    assert "get_public_share" in resource_names
    assert "get_public_share_history" in resource_names
    assert "get_public_share_artifact" in resource_names
    assert "get_workspace_shell" in resource_names
    assert "put_workspace_shell_draft" in tool_names
    assert "create_workspace_shell_share" in tool_names
    assert "extend_public_share" in tool_names
    assert "delete_public_share" in tool_names
