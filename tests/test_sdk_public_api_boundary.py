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
from src.sdk.server import (
    ProductExecutionTarget,
    ProductLaunchOptions,
    ProductRunLaunchRequest,
    ProductRunStatusResponse,
    ProductSourceArtifactView,
    ProductWorkspaceRunListResponse,
)
from src.server.run_read_models import ProductExecutionTargetView, ProductRunLinks


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
    assert sdk.PUBLIC_SDK_SURFACE_VERSION == "1.4"
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


def test_sdk_root_exposes_public_mcp_manifest_surface() -> None:
    manifest = sdk.build_public_mcp_manifest(base_url="https://api.nexa.test")

    assert sdk.PUBLIC_MCP_MANIFEST_VERSION == "1.0"
    assert manifest.server_name == "nexa-public"
    assert any(tool.route_name == "launch_run" for tool in manifest.tools)


def test_sdk_root_exposes_public_mcp_host_bridge_surface() -> None:
    bridge = sdk.build_public_mcp_host_bridge_scaffold()
    framework_request = bridge.build_framework_resource_request(
        "get_run_status",
        path_params={"run_id": "run-1"},
    )

    assert sdk.MCP_HOST_BRIDGE_SCAFFOLD_VERSION == "1.0"
    assert framework_request.path == "/api/runs/run-1"
    assert any(binding.route_name == "get_run_status" for binding in bridge.export().resource_bindings)
