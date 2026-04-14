from __future__ import annotations

"""Curated public SDK boundary for Nexa.

`src.sdk.artifacts` contains the public role-aware `.nex` artifact surface.
`src.sdk.server` contains the public request/response and binding surface for
server-backed integrations.
`src.sdk.integration` contains the protocol-mapping surface for external
integration shapes such as MCP-style tools/resources.
"""

from src.sdk import artifacts, integration, server
from src.sdk.artifacts import (
    PUBLIC_ARTIFACT_SDK_SURFACE_VERSION,
    COMMIT_SNAPSHOT_ROLE,
    WORKING_SAVE_ROLE,
    CommitSnapshotModel,
    ExecutionRecordModel,
    LoadedNexArtifact,
    WorkingSaveModel,
    create_commit_snapshot_from_working_save,
    create_execution_record_from_commit_snapshot,
    create_execution_record_from_snapshot,
    create_working_save_from_commit_snapshot,
    load_nex,
    validate_commit_snapshot,
    validate_working_save,
)
from src.sdk.integration import (
    PUBLIC_INTEGRATION_SDK_SURFACE_VERSION,
    PublicMcpCompatibilitySurface,
    PublicMcpResourceDescriptor,
    PublicMcpToolDescriptor,
    build_public_mcp_compatibility_surface,
    build_public_mcp_resources,
    build_public_mcp_tools,
)
from src.sdk.server import (
    PUBLIC_SERVER_SDK_SURFACE_VERSION,
    ProductExecutionTarget,
    ProductRunLaunchAcceptedResponse,
    ProductRunLaunchRejectedResponse,
    ProductRunLaunchRequest,
    ProductRunResultResponse,
    ProductRunStatusResponse,
    ProductSourceArtifactView,
    ProductWorkspaceRunListResponse,
    RunHttpRouteSurface,
)

PUBLIC_SDK_SURFACE_VERSION = "1.1"
PUBLIC_SDK_MODULES = ("artifacts", "server", "integration")

__all__ = [
    "PUBLIC_SDK_SURFACE_VERSION",
    "PUBLIC_SDK_MODULES",
    "PUBLIC_ARTIFACT_SDK_SURFACE_VERSION",
    "PUBLIC_SERVER_SDK_SURFACE_VERSION",
    "PUBLIC_INTEGRATION_SDK_SURFACE_VERSION",
    "artifacts",
    "server",
    "integration",
    "WORKING_SAVE_ROLE",
    "COMMIT_SNAPSHOT_ROLE",
    "WorkingSaveModel",
    "CommitSnapshotModel",
    "ExecutionRecordModel",
    "LoadedNexArtifact",
    "load_nex",
    "validate_working_save",
    "validate_commit_snapshot",
    "create_commit_snapshot_from_working_save",
    "create_working_save_from_commit_snapshot",
    "create_execution_record_from_snapshot",
    "create_execution_record_from_commit_snapshot",
    "RunHttpRouteSurface",
    "ProductExecutionTarget",
    "ProductRunLaunchRequest",
    "ProductRunLaunchAcceptedResponse",
    "ProductRunLaunchRejectedResponse",
    "ProductSourceArtifactView",
    "ProductRunStatusResponse",
    "ProductRunResultResponse",
    "ProductWorkspaceRunListResponse",
    "PublicMcpToolDescriptor",
    "PublicMcpResourceDescriptor",
    "PublicMcpCompatibilitySurface",
    "build_public_mcp_tools",
    "build_public_mcp_resources",
    "build_public_mcp_compatibility_surface",
]
